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
from auto_dataset.runner import DEFAULT_PUBLISH_EVERY, RunnerError, run_autonomous_loop
from auto_dataset.validation import (
    ValidationError,
    load_suite,
    render_agent_brief,
    render_suite_dashboard,
    summarize_suite,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-dataset")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a suite manifest and its cases.")
    validate_parser.add_argument("manifest", type=Path)

    summary_parser = subparsers.add_parser("summary", help="Summarize a suite manifest.")
    summary_parser.add_argument("manifest", type=Path)

    dashboard_parser = subparsers.add_parser("dashboard", help="Render a markdown status dashboard for a suite.")
    dashboard_parser.add_argument("manifest", type=Path)
    dashboard_parser.add_argument("--output", type=Path)

    brief_parser = subparsers.add_parser("brief", help="Render the autonomous operator brief for a suite.")
    brief_parser.add_argument("manifest", type=Path)
    brief_parser.add_argument("--mode")

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

    run_parser = subparsers.add_parser(
        "run",
        help="Run an autonomous loop around an external worker command.",
    )
    run_parser.add_argument("manifest", type=Path)
    run_parser.add_argument("--mode")
    run_parser.add_argument("--worker-cmd", required=True, help="Shell command for the worker; prompt is sent on stdin.")
    run_parser.add_argument("--max-runs", type=int)
    run_parser.add_argument("--publish-every", type=int, default=DEFAULT_PUBLISH_EVERY)
    run_parser.add_argument("--skip-publish", action="store_true")
    run_parser.add_argument("--output-root", type=Path, default=DEFAULT_STAGING_ROOT)
    run_parser.add_argument("--hf-token")
    run_parser.add_argument("--repo-id")
    run_parser.add_argument("--repo-name", default="auto-ij-dataset")
    run_parser.add_argument("--private", action="store_true")
    run_parser.add_argument("--worker-timeout-seconds", type=int)
    run_parser.add_argument("--sleep-seconds", type=float, default=0.0)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        manifest, cases = load_suite(args.manifest)
    except (PublishError, RunnerError, ValidationError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1

    if args.command == "validate":
        print(f"validation ok: {manifest['suite_id']} ({len(cases)} cases)")
        return 0

    if args.command == "summary":
        summary = summarize_suite(args.manifest, manifest, cases)
        print(json.dumps({"suite_id": manifest["suite_id"], **summary}, indent=2))
        return 0

    if args.command == "dashboard":
        dashboard = render_suite_dashboard(args.manifest, manifest, cases)
        if args.output:
            args.output.write_text(dashboard, encoding="utf-8")
        else:
            print(dashboard)
        return 0

    if args.command == "brief":
        print(render_agent_brief(manifest, cases, mode=args.mode))
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

    if args.command == "run":
        result = run_autonomous_loop(
            args.manifest,
            mode=args.mode,
            worker_command=args.worker_cmd,
            max_runs=args.max_runs,
            publish_every=args.publish_every,
            publish_enabled=not args.skip_publish,
            output_root=args.output_root,
            hf_token=args.hf_token,
            hf_repo_id=args.repo_id,
            hf_repo_name=args.repo_name,
            hf_public=not args.private,
            worker_timeout_seconds=args.worker_timeout_seconds,
            sleep_seconds=args.sleep_seconds,
        )
        print(json.dumps(result, indent=2))
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
