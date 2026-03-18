from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from auto_dataset.validation import render_agent_brief, summarize_cases


class PublishError(RuntimeError):
    pass


DEFAULT_STAGING_ROOT = Path("artifacts/hf-staging")


def _run_git(repo_root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise PublishError(process.stderr.strip() or process.stdout.strip() or "git command failed")
    return process.stdout.strip()


def _find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return None


def get_repo_root(start: Path) -> Path:
    try:
        return Path(_run_git(start, ["rev-parse", "--show-toplevel"]))
    except (FileNotFoundError, PublishError):
        fallback = _find_project_root(start)
        if fallback is None:
            raise PublishError("unable to determine project root")
        return fallback


def get_head_commit(repo_root: Path) -> str | None:
    try:
        value = _run_git(repo_root, ["rev-parse", "HEAD"])
    except (FileNotFoundError, PublishError):
        return None
    return value or None


def get_current_branch(repo_root: Path) -> str:
    return _run_git(repo_root, ["branch", "--show-current"])


def repo_has_changes(repo_root: Path) -> bool:
    status = _run_git(repo_root, ["status", "--porcelain"])
    return bool(status.strip())


def commit_repo_changes(repo_root: Path, message: str) -> str | None:
    if not repo_has_changes(repo_root):
        return None

    _run_git(repo_root, ["add", "-A"])
    _run_git(repo_root, ["commit", "-m", message])
    return get_head_commit(repo_root)


def push_repo_changes(repo_root: Path, remote: str = "origin") -> str:
    branch = get_current_branch(repo_root)
    _run_git(repo_root, ["push", remote, branch])
    return branch


def resolve_hf_token(explicit_token: str | None = None) -> str:
    token = explicit_token or os.environ.get("HF_TOKEN")
    if not token:
        raise PublishError("missing Hugging Face token; pass --hf-token or set HF_TOKEN")
    return token


def _load_hf_api() -> Any:
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise PublishError(
            "huggingface_hub is not installed; install project dependencies or pip install huggingface_hub"
        ) from exc
    return HfApi


def resolve_hf_repo_id(explicit_repo_id: str | None, token: str, repo_name: str = "auto-ij-dataset") -> str:
    if explicit_repo_id:
        return explicit_repo_id

    HfApi = _load_hf_api()
    api = HfApi(token=token)
    whoami = api.whoami(token=token)
    username = whoami.get("name")
    if not username:
        raise PublishError("unable to resolve Hugging Face username from token")
    return f"{username}/{repo_name}"


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_dataset_card(
    manifest: dict[str, Any],
    summary: dict[str, Any],
    source_commit: str | None,
    exported_at: str,
) -> str:
    objective = " ".join(str(manifest["objective"]).split())
    source_commit_text = source_commit or "uncommitted"
    lines = [
        f"# {manifest['suite_id']}",
        "",
        "Intermediate export of the investigative-journalism validation suite.",
        "",
        f"- suite version: `{manifest['version']}`",
        f"- exported at: `{exported_at}`",
        f"- source commit: `{source_commit_text}`",
        f"- cases total: `{summary['cases_total']}`",
        "",
        "## Objective",
        "",
        objective,
        "",
        "## Contents",
        "",
        "- `datasets/`: suite manifest and case files",
        "- `rubrics/`: rubric markdown files referenced by the cases",
        "- `results/runs.tsv`: intermediate run log",
        "- `summary.json`: suite counts at export time",
        "- `brief.txt`: current operator brief",
        "",
        "## Notes",
        "",
        "This dataset repo is an intermediate publishing target for in-progress suite building.",
    ]
    return "\n".join(lines) + "\n"


def build_intermediate_snapshot(
    manifest_path: Path,
    manifest: dict[str, Any],
    cases: list[dict[str, Any]],
    output_root: Path | None = None,
) -> Path:
    repo_root = get_repo_root(manifest_path.parent)
    staging_root = output_root or DEFAULT_STAGING_ROOT
    if not staging_root.is_absolute():
        staging_root = repo_root / staging_root

    snapshot_dir = staging_root / manifest["suite_id"]
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    base_dir = manifest_path.parent
    source_commit = get_head_commit(repo_root)
    exported_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    summary = summarize_cases(cases)

    _copy_file(manifest_path, snapshot_dir / "datasets" / manifest_path.name)

    for relative_case_path in manifest["case_files"]:
        case_source = base_dir / relative_case_path
        case_destination = snapshot_dir / "datasets" / relative_case_path
        _copy_file(case_source, case_destination)

    copied_rubrics: set[Path] = set()
    for relative_case_path, case in zip(manifest["case_files"], cases, strict=True):
        rubric = case.get("rubric")
        if not rubric:
            continue
        case_source = base_dir / relative_case_path
        rubric_source = (case_source.parent / rubric).resolve()
        if rubric_source in copied_rubrics:
            continue
        rubric_destination = snapshot_dir / rubric_source.relative_to(repo_root)
        _copy_file(rubric_source, rubric_destination)
        copied_rubrics.add(rubric_source)

    runs_path = repo_root / "results" / "runs.tsv"
    if runs_path.exists():
        _copy_file(runs_path, snapshot_dir / "results" / "runs.tsv")

    _write_json(
        snapshot_dir / "summary.json",
        {
            "suite_id": manifest["suite_id"],
            "version": manifest["version"],
            "exported_at": exported_at,
            "source_commit": source_commit,
            **summary,
        },
    )
    _write_text(snapshot_dir / "brief.txt", render_agent_brief(manifest, cases) + "\n")
    _write_text(snapshot_dir / "README.md", _build_dataset_card(manifest, summary, source_commit, exported_at))
    return snapshot_dir


def publish_snapshot_to_huggingface(
    snapshot_dir: Path,
    repo_id: str,
    token: str,
    public: bool = True,
    commit_message: str | None = None,
) -> str:
    HfApi = _load_hf_api()
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=not public, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(snapshot_dir),
        path_in_repo=".",
        commit_message=commit_message or f"Update intermediate snapshot from {snapshot_dir.name}",
    )
    return f"https://huggingface.co/datasets/{repo_id}"
