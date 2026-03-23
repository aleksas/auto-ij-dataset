from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from auto_dataset.validation import (
    render_agent_brief,
    resolve_publish_policy,
    summarize_lifecycle_readiness,
    summarize_suite,
)


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
    lifecycle: dict[str, Any],
    source_commit: str | None,
    exported_at: str,
) -> str:
    objective = " ".join(str(manifest["objective"]).split())
    source_commit_text = source_commit or "uncommitted"
    card_header = [
        "---",
        f"pretty_name: {manifest['suite_id']}",
        "language:",
        "  - en",
        "task_categories:",
        "  - question-answering",
        "size_categories:",
        "  - n<1K",
        "tags:",
        "  - investigative-journalism",
        "  - evaluation",
        "  - public-records",
        "---",
        "",
    ]
    lines = [
        f"# {manifest['suite_id']}",
        "",
        "Intermediate export of the investigative-journalism validation suite.",
        "",
        f"- suite version: `{manifest['version']}`",
        f"- exported at: `{exported_at}`",
        f"- source commit: `{source_commit_text}`",
        f"- cases total: `{summary['cases_total']}`",
        f"- included publish statuses: `{', '.join(lifecycle['publish_policy']['included_statuses'])}`",
        (
            "- default downstream-eval statuses: "
            f"`{', '.join(lifecycle['publish_policy']['default_consumption_statuses'])}`"
        ),
        "",
        "## Objective",
        "",
        objective,
        "",
        "## Contents",
        "",
        "- `datasets/`: suite manifest and case files",
        "- `source_documents/`: materialized markdown source documents and artifact index",
        "- `datasets/<suite>/source_artifacts/`: preserved original upstream PDFs, XML files, and HTML snapshots",
        "- `rubrics/`: rubric markdown files referenced by the cases",
        "- `results/runs.tsv`: intermediate run log",
        "- `summary.json`: suite counts at export time",
        "- `readiness.json`: lifecycle-aware publish and downstream-consumption guidance",
        "- `brief.txt`: current operator brief",
        "",
        "## Notes",
        "",
        "This dataset repo is an intermediate publishing target for in-progress suite building.",
        "",
        "Lifecycle readiness:",
        "",
        f"- evaluation-ready cases: `{lifecycle['evaluation_ready_cases_total']}`",
        f"- benchmark-ready cases: `{lifecycle['benchmark_ready_cases_total']}`",
        f"- under-construction cases: `{lifecycle['under_construction_cases_total']}`",
        f"- publish policy: {lifecycle['publish_policy']['notes']}",
    ]
    return "\n".join([*card_header, *lines]) + "\n"


def _materialize_case_source_document(snapshot_dir: Path, relative_case_path: str, case: dict[str, Any]) -> str | None:
    evidence_bundle = case.get("evidence_bundle")
    if not isinstance(evidence_bundle, dict):
        return None

    content_markdown = evidence_bundle.get("content_markdown")
    if not isinstance(content_markdown, str) or not content_markdown.strip():
        return None

    relative_document_path = Path("source_documents") / Path(relative_case_path).with_suffix(".md")
    _write_text(snapshot_dir / relative_document_path, content_markdown.rstrip() + "\n")
    return str(relative_document_path)


def _copy_declared_evidence_artifacts(
    repo_root: Path,
    snapshot_dir: Path,
    case: dict[str, Any],
    copied_artifact_paths: set[Path],
) -> list[dict[str, str]]:
    evidence_bundle = case.get("evidence_bundle")
    if not isinstance(evidence_bundle, dict):
        return []

    artifacts = evidence_bundle.get("artifacts")
    if not isinstance(artifacts, list):
        return []

    copied_entries: list[dict[str, str]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_path_text = artifact.get("path")
        artifact_id = artifact.get("id")
        if not isinstance(artifact_path_text, str) or not artifact_path_text.strip():
            continue
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            continue

        artifact_path = Path(artifact_path_text)
        artifact_source = (repo_root / artifact_path).resolve()
        if artifact_source not in copied_artifact_paths:
            _copy_file(artifact_source, snapshot_dir / artifact_path)
            copied_artifact_paths.add(artifact_source)

        copied_entry = {
            key: value
            for key, value in artifact.items()
            if isinstance(key, str) and isinstance(value, str) and value.strip()
        }
        copied_entry["path"] = artifact_path.as_posix()
        copied_entries.append(copied_entry)

    return copied_entries


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
    summary = summarize_suite(manifest_path, manifest, cases)
    lifecycle = summarize_lifecycle_readiness(manifest, cases)
    publish_policy = resolve_publish_policy(manifest)
    source_document_index: dict[str, dict[str, Any]] = {}

    _copy_file(manifest_path, snapshot_dir / "datasets" / manifest_path.name)

    for relative_case_path in manifest["case_files"]:
        case_source = base_dir / relative_case_path
        case_destination = snapshot_dir / "datasets" / relative_case_path
        _copy_file(case_source, case_destination)

    copied_rubrics: set[Path] = set()
    copied_artifact_paths: set[Path] = set()
    for relative_case_path, case in zip(manifest["case_files"], cases, strict=True):
        case_source_document = _materialize_case_source_document(snapshot_dir, relative_case_path, case)
        copied_case_artifacts = _copy_declared_evidence_artifacts(
            repo_root,
            snapshot_dir,
            case,
            copied_artifact_paths,
        )
        if case_source_document or copied_case_artifacts:
            source_document_index[case["id"]] = {
                "case_file": relative_case_path,
                "status": case.get("status", "unspecified"),
                "pipeline_stage": next(
                    (
                        row["pipeline_stage"]
                        for row in lifecycle["status_rows"]
                        if row["status"] == case.get("status", "unspecified")
                    ),
                    "unspecified",
                ),
                "included_in_publish": case.get("status") in publish_policy["included_statuses"],
                "evaluation_ready": case.get("status") in publish_policy["evaluation_ready_statuses"],
                "default_downstream_consumption": (
                    case.get("status") in publish_policy["default_consumption_statuses"]
                ),
                "materialized_source_document": case_source_document,
                "artifacts": copied_case_artifacts,
            }

        rubric = case.get("rubric")
        # Inlined rubrics are usually long multi-line strings; relative paths are short.
        # Skip if missing, not a string, or clearly too long to be a relative path.
        if not rubric or not isinstance(rubric, str) or len(rubric) > 255 or "\n" in rubric:
            continue
        case_source = base_dir / relative_case_path
        try:
            rubric_source = (case_source.parent / rubric).resolve()
            if not rubric_source.exists() or not rubric_source.is_file():
                continue
        except OSError:
            # Handle cases where the string might still trigger FS errors on some platforms
            continue

        if rubric_source in copied_rubrics:
            continue
        rubric_destination = snapshot_dir / rubric_source.relative_to(repo_root)
        _copy_file(rubric_source, rubric_destination)
        copied_rubrics.add(rubric_source)

    runs_path = repo_root / "results" / "runs.tsv"
    if runs_path.exists():
        _copy_file(runs_path, snapshot_dir / "results" / "runs.tsv")

    _write_json(snapshot_dir / "source_documents" / "index.json", source_document_index)
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
    _write_json(
        snapshot_dir / "readiness.json",
        {
            "suite_id": manifest["suite_id"],
            "version": manifest["version"],
            "exported_at": exported_at,
            "publish_policy": publish_policy,
            "lifecycle": lifecycle,
        },
    )
    _write_text(snapshot_dir / "brief.txt", render_agent_brief(manifest, cases) + "\n")
    _write_text(
        snapshot_dir / "README.md",
        _build_dataset_card(manifest, summary, lifecycle, source_commit, exported_at),
    )
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
