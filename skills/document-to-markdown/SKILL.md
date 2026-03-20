---
name: document-to-markdown
description: Convert local documents such as PDF, DOCX, PPTX, XLSX, XLS, HTML, text files, and Outlook messages into Markdown reference files using MarkItDown. Use when Codex needs to preserve source documents as local Markdown for dataset building, reference capture, provenance review, or later analysis, especially when the output should include source metadata and a conversion timestamp.
---

# Document To Markdown

## Overview

Use this skill to turn source documents into project-local Markdown references with a small provenance header. Prefer it when collecting supporting material for dataset work, especially if the document should be reviewed later by humans or LLMs without reopening the original binary file.

## Quick Start

Convert one file into `artifacts/markdownified/`:

```bash
python skills/document-to-markdown/scripts/convert_document.py \
  path/to/source.pdf \
  --output-dir artifacts/markdownified
```

Include a source URL when the file came from the web:

```bash
python skills/document-to-markdown/scripts/convert_document.py \
  downloads/report.docx \
  --output-dir artifacts/markdownified \
  --source-url https://example.org/report.docx
```

## Workflow

1. Keep the original document in local storage such as `downloads/` or another non-source location.
2. Run `scripts/convert_document.py` on the local file.
3. Write the Markdown output under ignored storage such as `artifacts/markdownified/` unless the user wants a different location.
4. Pass `--source-url` whenever the local document was downloaded from a public source.
5. Use the generated Markdown as a reference copy; do not treat it as a substitute for the original file when provenance or formatting disputes matter.

## Output Contract

The converter prepends YAML frontmatter with:

- `source_file`
- `source_url` when provided
- `converted_at_utc`
- `converter`

Keep that header intact so later dataset work can recover provenance and conversion timing.

## Script

Use `scripts/convert_document.py` for deterministic conversion. It:

- accepts one local input file
- writes Markdown either to `--output` or a derived file path under `--output-dir`
- creates parent directories as needed
- refuses to overwrite existing files unless `--force` is set

If the document type is unsupported or conversion quality is poor, keep the original file and note the limitation rather than silently rewriting the Markdown by hand.

If conversion problems recur and a better structured-document pipeline is needed, consider evaluating Docling as a heavier fallback. It is not the default here because the dependency stack is much larger than the current MarkItDown-based path.
