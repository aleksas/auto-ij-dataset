from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml


VALID_SOURCE_TIERS = {"primary", "secondary", "tertiary", "manual_annotation"}
VALID_ANSWER_MODES = {"exact", "rubric", "mixed"}
REQUIRED_RUN_LOG_COLUMNS = (
    "run_id",
    "timestamp",
    "manifest",
    "cases_total",
    "validation_status",
    "change_kind",
    "source_family",
    "kept",
    "description",
)


class ValidationError(ValueError):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected a mapping at the top level")
    return data


def _require_keys(data: dict[str, Any], keys: list[str], path: Path, context: str | None = None) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        prefix = f"{context} " if context else ""
        raise ValidationError(f"{path}: {prefix}missing required keys: {', '.join(missing)}")


def _require_mapping(value: Any, name: str, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: {name} must be a mapping")
    return value


def _require_non_empty_list(value: Any, name: str, path: Path) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{path}: {name} must be a non-empty list")
    return value


def _require_string_list(value: Any, name: str, path: Path) -> list[str]:
    items = _require_non_empty_list(value, name, path)
    for index, item in enumerate(items, start=1):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{path}: {name}[{index}] must be a non-empty string")
    return items


def _require_positive_int(value: Any, name: str, path: Path) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{path}: {name} must be a positive integer")
    return value


def _validate_target_counts(value: Any, path: Path) -> None:
    target_counts = _require_mapping(value, "target_counts", path)
    for label, target in target_counts.items():
        if not isinstance(label, str) or not label.strip():
            raise ValidationError(f"{path}: target_counts keys must be non-empty strings")
        if not isinstance(target, (int, str)):
            raise ValidationError(f"{path}: target_counts[{label!r}] must be a string or integer")


def _validate_autonomous_loop(value: Any, path: Path) -> None:
    autonomous_loop = _require_mapping(value, "autonomous_loop", path)
    _require_keys(
        autonomous_loop,
        [
            "duration_days",
            "run_budget",
            "batch_size",
            "mutable_paths",
            "frozen_paths",
            "priorities",
            "daily_loop",
            "keep_if",
            "discard_if",
            "logging",
        ],
        path,
        "autonomous_loop",
    )

    _require_positive_int(autonomous_loop["duration_days"], "autonomous_loop.duration_days", path)

    run_budget = _require_mapping(autonomous_loop["run_budget"], "autonomous_loop.run_budget", path)
    _require_keys(
        run_budget,
        [
            "runs_per_day",
            "max_total_runs",
            "max_case_edits_per_run",
            "max_new_cases_per_run",
        ],
        path,
        "autonomous_loop.run_budget",
    )
    runs_per_day = _require_positive_int(run_budget["runs_per_day"], "autonomous_loop.run_budget.runs_per_day", path)
    max_total_runs = _require_positive_int(
        run_budget["max_total_runs"],
        "autonomous_loop.run_budget.max_total_runs",
        path,
    )
    if max_total_runs < runs_per_day:
        raise ValidationError(
            f"{path}: autonomous_loop.run_budget.max_total_runs must be at least runs_per_day"
        )
    _require_positive_int(
        run_budget["max_case_edits_per_run"],
        "autonomous_loop.run_budget.max_case_edits_per_run",
        path,
    )
    _require_positive_int(
        run_budget["max_new_cases_per_run"],
        "autonomous_loop.run_budget.max_new_cases_per_run",
        path,
    )

    batch_size = _require_mapping(autonomous_loop["batch_size"], "autonomous_loop.batch_size", path)
    _require_keys(batch_size, ["min_cases", "max_cases"], path, "autonomous_loop.batch_size")
    min_cases = _require_positive_int(batch_size["min_cases"], "autonomous_loop.batch_size.min_cases", path)
    max_cases = _require_positive_int(batch_size["max_cases"], "autonomous_loop.batch_size.max_cases", path)
    if min_cases > max_cases:
        raise ValidationError(f"{path}: autonomous_loop.batch_size.min_cases cannot exceed max_cases")

    _require_string_list(autonomous_loop["mutable_paths"], "autonomous_loop.mutable_paths", path)
    _require_string_list(autonomous_loop["frozen_paths"], "autonomous_loop.frozen_paths", path)
    _require_string_list(autonomous_loop["daily_loop"], "autonomous_loop.daily_loop", path)
    _require_string_list(autonomous_loop["keep_if"], "autonomous_loop.keep_if", path)
    _require_string_list(autonomous_loop["discard_if"], "autonomous_loop.discard_if", path)

    priorities = _require_non_empty_list(autonomous_loop["priorities"], "autonomous_loop.priorities", path)
    for index, item in enumerate(priorities, start=1):
        priority = _require_mapping(item, f"autonomous_loop.priorities[{index}]", path)
        _require_keys(
            priority,
            ["source_family", "goal"],
            path,
            f"autonomous_loop.priorities[{index}]",
        )
        if not isinstance(priority["source_family"], str) or not priority["source_family"].strip():
            raise ValidationError(f"{path}: autonomous_loop.priorities[{index}].source_family must be a string")
        if not isinstance(priority["goal"], str) or not priority["goal"].strip():
            raise ValidationError(f"{path}: autonomous_loop.priorities[{index}].goal must be a string")

    logging = _require_mapping(autonomous_loop["logging"], "autonomous_loop.logging", path)
    _require_keys(
        logging,
        ["results_path", "required_columns"],
        path,
        "autonomous_loop.logging",
    )
    if not isinstance(logging["results_path"], str) or not logging["results_path"].strip():
        raise ValidationError(f"{path}: autonomous_loop.logging.results_path must be a non-empty string")
    required_columns = _require_string_list(
        logging["required_columns"],
        "autonomous_loop.logging.required_columns",
        path,
    )
    if tuple(required_columns) != REQUIRED_RUN_LOG_COLUMNS:
        raise ValidationError(
            f"{path}: autonomous_loop.logging.required_columns must match {list(REQUIRED_RUN_LOG_COLUMNS)!r}"
        )


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = _load_yaml(manifest_path)
    _require_keys(
        manifest,
        ["suite_id", "version", "objective", "case_files"],
        manifest_path,
    )

    case_files = _require_non_empty_list(manifest["case_files"], "case_files", manifest_path)
    for index, item in enumerate(case_files, start=1):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{manifest_path}: case_files[{index}] must be a non-empty string")

    if "origin_notes" in manifest:
        _require_string_list(manifest["origin_notes"], "origin_notes", manifest_path)
    if "source_mix" in manifest:
        _require_string_list(manifest["source_mix"], "source_mix", manifest_path)
    if "target_counts" in manifest:
        _validate_target_counts(manifest["target_counts"], manifest_path)
    if "autonomous_loop" in manifest:
        _validate_autonomous_loop(manifest["autonomous_loop"], manifest_path)

    return manifest


def _validate_results_log(manifest: dict[str, Any], manifest_path: Path) -> None:
    autonomous_loop = manifest.get("autonomous_loop")
    if not autonomous_loop:
        return

    logging = autonomous_loop["logging"]
    results_path = (manifest_path.parent / logging["results_path"]).resolve()
    if not results_path.exists():
        raise ValidationError(f"{manifest_path}: missing results log {logging['results_path']}")

    with results_path.open("r", encoding="utf-8") as handle:
        first_line = handle.readline().strip()

    if not first_line:
        raise ValidationError(f"{results_path}: expected a TSV header row")

    observed_columns = first_line.split("\t")
    expected_columns = list(REQUIRED_RUN_LOG_COLUMNS)
    if observed_columns != expected_columns:
        raise ValidationError(
            f"{results_path}: expected header {expected_columns!r}, found {observed_columns!r}"
        )


def validate_case(path: Path) -> dict[str, Any]:
    case = _load_yaml(path)
    _require_keys(
        case,
        [
            "id",
            "title",
            "task_type",
            "answer_mode",
            "source_family",
            "source_tier",
            "sources",
            "evidence_bundle",
            "expected_output",
        ],
        path,
    )

    answer_mode = case["answer_mode"]
    if answer_mode not in VALID_ANSWER_MODES:
        raise ValidationError(f"{path}: invalid answer_mode '{answer_mode}'")

    source_tier = case["source_tier"]
    if source_tier not in VALID_SOURCE_TIERS:
        raise ValidationError(f"{path}: invalid source_tier '{source_tier}'")

    sources = case["sources"]
    if not isinstance(sources, list) or not sources:
        raise ValidationError(f"{path}: sources must be a non-empty list")

    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise ValidationError(f"{path}: source #{index} must be a mapping")
        _require_keys(source, ["label", "url", "checked_on", "provenance"], path)

    if answer_mode in {"exact", "mixed"} and "answer_key" not in case:
        raise ValidationError(f"{path}: answer_key is required for answer_mode '{answer_mode}'")

    if answer_mode in {"rubric", "mixed"} and "rubric" not in case:
        raise ValidationError(f"{path}: rubric is required for answer_mode '{answer_mode}'")

    return case


def load_suite(manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = validate_manifest(manifest_path)
    case_files = manifest["case_files"]

    base_dir = manifest_path.parent
    _validate_results_log(manifest, manifest_path)
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for relative_case_path in case_files:
        case_path = base_dir / relative_case_path
        if not case_path.exists():
            raise ValidationError(f"{manifest_path}: missing case file {relative_case_path}")

        case = validate_case(case_path)
        case_id = case["id"]
        if case_id in seen_ids:
            raise ValidationError(f"{manifest_path}: duplicate case id '{case_id}'")
        seen_ids.add(case_id)
        cases.append(case)

    return manifest, cases


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_task = Counter(case["task_type"] for case in cases)
    by_mode = Counter(case["answer_mode"] for case in cases)
    by_tier = Counter(case["source_tier"] for case in cases)
    by_family = Counter(case["source_family"] for case in cases)
    statuses = Counter(case.get("status", "unspecified") for case in cases)

    return {
        "cases_total": len(cases),
        "by_task_type": dict(sorted(by_task.items())),
        "by_answer_mode": dict(sorted(by_mode.items())),
        "by_source_tier": dict(sorted(by_tier.items())),
        "by_source_family": dict(sorted(by_family.items())),
        "by_status": dict(sorted(statuses.items())),
    }


def _format_counts(values: dict[str, int]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in values.items())


def render_agent_brief(manifest: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    autonomous_loop = manifest.get("autonomous_loop")
    if not autonomous_loop:
        raise ValidationError("manifest is missing autonomous_loop")

    run_budget = autonomous_loop["run_budget"]
    batch_size = autonomous_loop["batch_size"]
    logging = autonomous_loop["logging"]
    summary = summarize_cases(cases)
    objective = " ".join(str(manifest["objective"]).split())

    lines = [
        f"Suite: {manifest['suite_id']}",
        f"Mission: {objective}",
        "",
        "Timebox",
        f"- {autonomous_loop['duration_days']} days",
        f"- {run_budget['runs_per_day']} runs/day, {run_budget['max_total_runs']} max total",
        f"- {batch_size['min_cases']}-{batch_size['max_cases']} cases per run",
        (
            f"- {run_budget['max_case_edits_per_run']} case edits max and "
            f"{run_budget['max_new_cases_per_run']} new cases max per run"
        ),
        "",
        "Mutable Surface",
    ]
    lines.extend(f"- {path}" for path in autonomous_loop["mutable_paths"])
    lines.extend(["", "Frozen Surface"])
    lines.extend(f"- {path}" for path in autonomous_loop["frozen_paths"])
    lines.extend(["", "Priority Order"])
    lines.extend(
        f"{index}. {priority['source_family']}: {priority['goal']}"
        for index, priority in enumerate(autonomous_loop["priorities"], start=1)
    )

    target_counts = manifest.get("target_counts", {})
    if target_counts:
        lines.extend(["", "Coverage Targets"])
        lines.extend(f"- {label}: {target}" for label, target in target_counts.items())

    lines.extend(
        [
            "",
            "Current Baseline",
            f"- cases total: {summary['cases_total']}",
            f"- task types: {_format_counts(summary['by_task_type'])}",
            f"- answer modes: {_format_counts(summary['by_answer_mode'])}",
            f"- source families: {_format_counts(summary['by_source_family'])}",
            f"- statuses: {_format_counts(summary['by_status'])}",
            "",
            "Daily Loop",
        ]
    )
    lines.extend(f"{index}. {step}" for index, step in enumerate(autonomous_loop["daily_loop"], start=1))
    lines.extend(["", "Keep If"])
    lines.extend(f"- {rule}" for rule in autonomous_loop["keep_if"])
    lines.extend(["", "Discard If"])
    lines.extend(f"- {rule}" for rule in autonomous_loop["discard_if"])
    lines.extend(
        [
            "",
            "Run Log",
            f"- {logging['results_path']}",
            f"- columns: {', '.join(REQUIRED_RUN_LOG_COLUMNS)}",
        ]
    )
    return "\n".join(lines)
