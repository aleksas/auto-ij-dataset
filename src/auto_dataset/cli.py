from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from auto_dataset.publishing import (
    DEFAULT_STAGING_ROOT,
    PublishError,
    build_intermediate_snapshot,
    commit_repo_changes,
    get_repo_root,
    publish_snapshot_to_huggingface,
    push_repo_changes,
    resolve_hf_repo_id,
    resolve_hf_token,
)
from auto_dataset.validation import ValidationError, load_suite, render_agent_brief, summarize_cases


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-dataset")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a suite manifest and its cases.")
    validate_parser.add_argument("manifest", type=Path)

    summary_parser = subparsers.add_parser("summary", help="Summarize a suite manifest.")
    summary_parser.add_argument("manifest", type=Path)

    brief_parser = subparsers.add_parser("brief", help="Render the autonomous operator brief for a suite.")
    brief_parser.add_argument("manifest", type=Path)

    export_parser = subparsers.add_parser(
        "export",
        help="Build an intermediate suite snapshot in an ignored staging directory.",
    )
    export_parser.add_argument("manifest", type=Path)
    export_parser.add_argument("--output-root", type=Path, default=DEFAULT_STAGING_ROOT)

    publish_parser = subparsers.add_parser(
        "publish",
        help="Export the suite, publish it to Hugging Face, and optionally commit/push repo changes.",
    )
    publish_parser.add_argument("manifest", type=Path)
    publish_parser.add_argument("--output-root", type=Path, default=DEFAULT_STAGING_ROOT)
    publish_parser.add_argument("--hf-token")
    publish_parser.add_argument("--repo-id")
    publish_parser.add_argument("--repo-name", default="auto-ij-dataset")
    publish_parser.add_argument("--private", action="store_true")
    publish_parser.add_argument("--skip-git-commit", action="store_true")
    publish_parser.add_argument("--skip-git-push", action="store_true")
    publish_parser.add_argument("--git-commit-message")
    publish_parser.add_argument("--hf-commit-message")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        manifest, cases = load_suite(args.manifest)
    except (PublishError, ValidationError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1

    if args.command == "validate":
        print(f"validation ok: {manifest['suite_id']} ({len(cases)} cases)")
        return 0

    if args.command == "summary":
        summary = summarize_cases(cases)
        print(json.dumps({"suite_id": manifest["suite_id"], **summary}, indent=2))
        return 0

    if args.command == "brief":
        print(render_agent_brief(manifest, cases))
        return 0

    if args.command == "export":
        snapshot_dir = build_intermediate_snapshot(args.manifest, manifest, cases, args.output_root)
        print(snapshot_dir)
        return 0

    if args.command == "publish":
        repo_root = get_repo_root(args.manifest.parent)
        commit_sha = None
        pushed_branch = None

        if not args.skip_git_commit:
            commit_message = args.git_commit_message or f"Update {manifest['suite_id']} dataset sources"
            commit_sha = commit_repo_changes(repo_root, commit_message)
            if commit_sha and not args.skip_git_push:
                pushed_branch = push_repo_changes(repo_root)

        snapshot_dir = build_intermediate_snapshot(args.manifest, manifest, cases, args.output_root)
        token = resolve_hf_token(args.hf_token)
        repo_id = resolve_hf_repo_id(args.repo_id, token, args.repo_name)
        hf_commit_message = args.hf_commit_message or f"Update intermediate snapshot for {manifest['suite_id']}"
        dataset_url = publish_snapshot_to_huggingface(
            snapshot_dir=snapshot_dir,
            repo_id=repo_id,
            token=token,
            public=not args.private,
            commit_message=hf_commit_message,
        )
        print(
            json.dumps(
                {
                    "snapshot_dir": str(snapshot_dir),
                    "repo_id": repo_id,
                    "dataset_url": dataset_url,
                    "git_commit": commit_sha,
                    "git_pushed_branch": pushed_branch,
                },
                indent=2,
            )
        )
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
