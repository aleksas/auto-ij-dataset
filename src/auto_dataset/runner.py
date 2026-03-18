from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from auto_dataset.publishing import (
    PublishError,
    build_intermediate_snapshot,
    commit_repo_changes,
    get_repo_root,
    publish_snapshot_to_huggingface,
    push_repo_changes,
    repo_has_changes,
    resolve_hf_repo_id,
    resolve_hf_token,
)
from auto_dataset.validation import ValidationError, load_suite, render_agent_brief, summarize_cases


class RunnerError(RuntimeError):
    pass


DEFAULT_PUBLISH_EVERY = 3


def _clean_tsv_value(value: str) -> str:
    return value.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def _resolve_results_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    logging = manifest["autonomous_loop"]["logging"]
    return (manifest_path.parent / logging["results_path"]).resolve()


def _append_run_log(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    run_id: str,
    cases_total: int,
    validation_status: str,
    change_kind: str,
    source_family: str,
    kept: bool,
    description: str,
) -> None:
    results_path = _resolve_results_path(manifest_path, manifest)
    row = [
        run_id,
        datetime.now(UTC).replace(microsecond=0).isoformat(),
        str(manifest_path),
        str(cases_total),
        validation_status,
        change_kind,
        source_family,
        "true" if kept else "false",
        _clean_tsv_value(description),
    ]
    with results_path.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(row) + "\n")


def _collect_snapshot(repo_root: Path, relative_paths: list[str]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for relative_path in relative_paths:
        target = (repo_root / relative_path).resolve()
        if not target.exists():
            continue
        if target.is_file():
            snapshot[str(target.relative_to(repo_root))] = hashlib.sha256(target.read_bytes()).hexdigest()
            continue
        for path in sorted(candidate for candidate in target.rglob("*") if candidate.is_file()):
            snapshot[str(path.relative_to(repo_root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def _changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    keys = sorted(set(before) | set(after))
    return [key for key in keys if before.get(key) != after.get(key)]


def _list_git_changed_paths(repo_root: Path) -> list[str]:
    process = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise PublishError(process.stderr.strip() or process.stdout.strip() or "git status failed")
    paths: list[str] = []
    for line in process.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def _path_allowed(path: str, allowed_roots: list[str]) -> bool:
    normalized = path.rstrip("/")
    for root in allowed_roots:
        normalized_root = root.rstrip("/")
        if normalized == normalized_root or normalized.startswith(f"{normalized_root}/"):
            return True
    return False


def _write_prompt_file(repo_root: Path, suite_id: str, run_number: int, prompt: str) -> Path:
    prompt_dir = repo_root / "artifacts" / "run-prompts" / suite_id
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"run-{run_number:03d}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _build_worker_prompt(
    repo_root: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    cases: list[dict[str, Any]],
    run_number: int,
    max_runs: int,
) -> str:
    summary = summarize_cases(cases)
    summary_json = json.dumps(summary, indent=2)
    brief = render_agent_brief(manifest, cases)
    return "\n".join(
        [
            "You are running one bounded auto-dataset cycle.",
            "",
            f"Repository root: {repo_root}",
            f"Manifest: {manifest_path}",
            f"Run: {run_number}/{max_runs}",
            "",
            "Required behavior:",
            "- Follow program.md and the rendered brief.",
            "- Mutate only the allowed dataset/docs/rubric surfaces.",
            "- Ship one bounded accepted batch if you can.",
            "- Do not run git commit, git push, or Hugging Face publish; the runner handles that.",
            "- Stop after making the batch and leave the repo ready for validation.",
            "",
            "Current summary:",
            summary_json,
            "",
            "Rendered brief:",
            brief,
            "",
            "Now make one bounded improvement batch.",
        ]
    )


def _run_worker(
    repo_root: Path,
    manifest_path: Path,
    worker_command: str,
    prompt: str,
    prompt_path: Path,
    timeout_seconds: int | None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "AUTO_DATASET_REPO_ROOT": str(repo_root),
        "AUTO_DATASET_MANIFEST": str(manifest_path),
        "AUTO_DATASET_RUN_PROMPT_FILE": str(prompt_path),
    }
    return subprocess.run(
        ["/bin/bash", "-c", worker_command],
        cwd=repo_root,
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        env=env,
    )


def _publish_current_state(
    manifest_path: Path,
    manifest: dict[str, Any],
    cases: list[dict[str, Any]],
    *,
    output_root: Path,
    hf_token: str,
    repo_id: str,
    public: bool,
    git_commit_message: str,
    hf_commit_message: str,
) -> dict[str, str | None]:
    repo_root = get_repo_root(manifest_path.parent)
    commit_sha = commit_repo_changes(repo_root, git_commit_message)
    pushed_branch = None
    if commit_sha:
        pushed_branch = push_repo_changes(repo_root)

    snapshot_dir = build_intermediate_snapshot(manifest_path, manifest, cases, output_root)
    dataset_url = publish_snapshot_to_huggingface(
        snapshot_dir=snapshot_dir,
        repo_id=repo_id,
        token=hf_token,
        public=public,
        commit_message=hf_commit_message,
    )
    return {
        "snapshot_dir": str(snapshot_dir),
        "dataset_url": dataset_url,
        "git_commit": commit_sha,
        "git_pushed_branch": pushed_branch,
    }


def run_autonomous_loop(
    manifest_path: Path,
    *,
    worker_command: str,
    max_runs: int | None = None,
    publish_every: int = DEFAULT_PUBLISH_EVERY,
    publish_enabled: bool = True,
    output_root: Path,
    hf_token: str | None = None,
    hf_repo_id: str | None = None,
    hf_repo_name: str = "auto-ij-dataset",
    hf_public: bool = True,
    worker_timeout_seconds: int | None = None,
    sleep_seconds: float = 0.0,
) -> dict[str, Any]:
    manifest, cases = load_suite(manifest_path)
    autonomous_loop = manifest.get("autonomous_loop")
    if not autonomous_loop:
        raise RunnerError("manifest is missing autonomous_loop")

    repo_root = get_repo_root(manifest_path.parent)
    max_runs = max_runs or autonomous_loop["run_budget"]["max_total_runs"]
    if max_runs <= 0:
        raise RunnerError("max_runs must be positive")
    mutable_paths = list(autonomous_loop["mutable_paths"])
    results_relative_path = str(_resolve_results_path(manifest_path, manifest).relative_to(repo_root))
    allowed_git_paths = [*mutable_paths, results_relative_path]

    accepted_runs = 0
    published_runs = 0
    last_publish: dict[str, str | None] | None = None

    hf_token_value = None
    hf_repo_id_value = None
    if publish_enabled:
        hf_token_value = resolve_hf_token(hf_token)
        hf_repo_id_value = resolve_hf_repo_id(hf_repo_id, hf_token_value, hf_repo_name)

    for run_number in range(1, max_runs + 1):
        manifest, cases = load_suite(manifest_path)
        before = _collect_snapshot(repo_root, mutable_paths)
        prompt = _build_worker_prompt(repo_root, manifest_path, manifest, cases, run_number, max_runs)
        prompt_path = _write_prompt_file(repo_root, manifest["suite_id"], run_number, prompt)

        print(f"run {run_number}/{max_runs}: invoking worker", flush=True)
        try:
            worker_result = _run_worker(
                repo_root,
                manifest_path,
                worker_command,
                prompt,
                prompt_path,
                worker_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            _append_run_log(
                manifest_path,
                manifest,
                run_id=f"run-{run_number:03d}",
                cases_total=len(cases),
                validation_status="worker_timeout",
                change_kind="worker_batch",
                source_family="autonomous_loop",
                kept=False,
                description=f"worker timed out after {exc.timeout} seconds",
            )
            raise RunnerError(f"worker timed out after {exc.timeout} seconds") from exc

        if worker_result.returncode != 0:
            _append_run_log(
                manifest_path,
                manifest,
                run_id=f"run-{run_number:03d}",
                cases_total=len(cases),
                validation_status="worker_failed",
                change_kind="worker_batch",
                source_family="autonomous_loop",
                kept=False,
                description=worker_result.stderr or worker_result.stdout or "worker command failed",
            )
            raise RunnerError(worker_result.stderr.strip() or worker_result.stdout.strip() or "worker command failed")

        after = _collect_snapshot(repo_root, mutable_paths)
        changed_paths = _changed_paths(before, after)
        try:
            git_changed_paths = _list_git_changed_paths(repo_root)
        except (FileNotFoundError, PublishError):
            git_changed_paths = []

        disallowed_changes = [path for path in git_changed_paths if not _path_allowed(path, allowed_git_paths)]
        if disallowed_changes:
            _append_run_log(
                manifest_path,
                manifest,
                run_id=f"run-{run_number:03d}",
                cases_total=len(cases),
                validation_status="disallowed_changes",
                change_kind="worker_batch",
                source_family="autonomous_loop",
                kept=False,
                description=f"worker touched disallowed files: {', '.join(disallowed_changes)}",
            )
            raise RunnerError(f"worker touched disallowed files: {', '.join(disallowed_changes)}")

        if not changed_paths:
            _append_run_log(
                manifest_path,
                manifest,
                run_id=f"run-{run_number:03d}",
                cases_total=len(cases),
                validation_status="no_changes",
                change_kind="worker_batch",
                source_family="autonomous_loop",
                kept=False,
                description="worker completed without changing mutable files",
            )
            print(f"run {run_number}: no changes; stopping", flush=True)
            break

        try:
            manifest, cases = load_suite(manifest_path)
        except ValidationError as exc:
            _append_run_log(
                manifest_path,
                manifest,
                run_id=f"run-{run_number:03d}",
                cases_total=len(cases),
                validation_status="failed",
                change_kind="worker_batch",
                source_family="autonomous_loop",
                kept=False,
                description=str(exc),
            )
            raise RunnerError(f"validation failed after worker run: {exc}") from exc

        accepted_runs += 1
        _append_run_log(
            manifest_path,
            manifest,
            run_id=f"run-{run_number:03d}",
            cases_total=len(cases),
            validation_status="ok",
            change_kind="worker_batch",
            source_family="autonomous_loop",
            kept=True,
            description=f"accepted autonomous batch; {len(changed_paths)} mutable file(s) changed",
        )
        print(f"run {run_number}: accepted ({len(changed_paths)} mutable file(s) changed)", flush=True)

        should_publish = publish_enabled and publish_every > 0 and accepted_runs % publish_every == 0
        if should_publish:
            git_commit_message = f"Update {manifest['suite_id']} dataset sources after run {run_number:03d}"
            hf_commit_message = f"Update intermediate snapshot for {manifest['suite_id']} after run {run_number:03d}"
            last_publish = _publish_current_state(
                manifest_path,
                manifest,
                cases,
                output_root=output_root,
                hf_token=hf_token_value,
                repo_id=hf_repo_id_value,
                public=hf_public,
                git_commit_message=git_commit_message,
                hf_commit_message=hf_commit_message,
            )
            published_runs += 1
            print(f"run {run_number}: pushed GitHub and Hugging Face sync", flush=True)

        if sleep_seconds > 0 and run_number < max_runs:
            time.sleep(sleep_seconds)

    if publish_enabled:
        manifest, cases = load_suite(manifest_path)
        try:
            pending_changes = repo_has_changes(repo_root)
        except (FileNotFoundError, PublishError):
            pending_changes = False

        if pending_changes:
            last_publish = _publish_current_state(
                manifest_path,
                manifest,
                cases,
                output_root=output_root,
                hf_token=hf_token_value,
                repo_id=hf_repo_id_value,
                public=hf_public,
                git_commit_message=f"Finalize {manifest['suite_id']} dataset sources after autonomous run",
                hf_commit_message=f"Finalize intermediate snapshot for {manifest['suite_id']}",
            )
            published_runs += 1
            print("final sync: pushed GitHub and Hugging Face", flush=True)

    final_manifest, final_cases = load_suite(manifest_path)
    return {
        "suite_id": final_manifest["suite_id"],
        "accepted_runs": accepted_runs,
        "published_runs": published_runs,
        "final_cases_total": len(final_cases),
        "last_publish": last_publish,
    }
