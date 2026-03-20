#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

try:
    from importlib.metadata import version as package_version
except ImportError:  # pragma: no cover
    from importlib_metadata import version as package_version  # type: ignore

from markitdown import MarkItDown


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a local document into Markdown with provenance metadata."
    )
    parser.add_argument("input", type=Path, help="Path to a local source document.")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--output", type=Path, help="Write Markdown to this exact file path.")
    output_group.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/markdownified"),
        help="Directory for derived .md output. Defaults to artifacts/markdownified.",
    )
    parser.add_argument(
        "--source-url",
        help="Original public URL for the document, if the local file was downloaded from the web.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing output file.",
    )
    return parser


def _default_output_path(input_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{input_path.stem}.md"


def _yaml_string(value: str) -> str:
    return json.dumps(value)


def _frontmatter_lines(input_path: Path, source_url: str | None) -> list[str]:
    converter_name = f"markitdown {package_version('markitdown')}"
    lines = [
        "---",
        f"source_file: {_yaml_string(str(input_path.resolve()))}",
        f"converted_at_utc: {_yaml_string(datetime.now(UTC).replace(microsecond=0).isoformat())}",
        f"converter: {_yaml_string(converter_name)}",
    ]
    if source_url:
        lines.append(f"source_url: {_yaml_string(source_url)}")
    lines.extend(["---", ""])
    return lines


def _render_markdown(input_path: Path, source_url: str | None) -> str:
    converter = MarkItDown()
    result = converter.convert(str(input_path))
    body = result.text_content.rstrip()
    if body:
        body += "\n"
    return "\n".join(_frontmatter_lines(input_path, source_url)) + body


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path = args.input.resolve()
    if not input_path.exists():
        parser.error(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        parser.error(f"input path must be a file: {input_path}")

    output_path = args.output.resolve() if args.output else _default_output_path(input_path, args.output_dir.resolve())
    if output_path.exists() and not args.force:
        parser.error(f"output file already exists: {output_path} (pass --force to overwrite)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_markdown(input_path, args.source_url), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
