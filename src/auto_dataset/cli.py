from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        manifest, cases = load_suite(args.manifest)
    except ValidationError as exc:
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

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
