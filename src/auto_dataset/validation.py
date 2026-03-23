from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
from typing import Any

import yaml


VALID_SOURCE_TIERS = {"primary", "secondary", "tertiary", "manual_annotation"}
VALID_ANSWER_MODES = {"exact", "rubric", "mixed"}
VALID_CASE_STATUSES = {"template", "harvested", "draft", "validated", "gold_candidate", "gold"}
DEFAULT_PUBLISH_INCLUDED_STATUSES = ("template", "harvested", "draft", "validated", "gold_candidate", "gold")
DEFAULT_EVALUATION_READY_STATUSES = ("validated", "gold")
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


def _require_non_empty_string(value: Any, name: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{path}: {name} must be a non-empty string")
    return value


def _validate_language_code(value: Any, name: str, path: Path) -> str:
    text = _require_non_empty_string(value, name, path).strip().lower()
    parts = text.split("-")
    if not parts or any(not part.isalnum() for part in parts):
        raise ValidationError(f"{path}: {name} must be a lowercase BCP47-style language tag")
    first = parts[0]
    if len(first) not in {2, 3}:
        raise ValidationError(f"{path}: {name} must start with a 2-3 letter language code")
    if not first.isalpha():
        raise ValidationError(f"{path}: {name} must start with alphabetic language code characters")
    return text


def _validate_language_list(value: Any, name: str, path: Path) -> list[str]:
    items = _require_non_empty_list(value, name, path)
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        code = _validate_language_code(item, f"{name}[{index}]", path)
        if code in seen:
            raise ValidationError(f"{path}: {name} contains duplicate language code '{code}'")
        seen.add(code)
        normalized.append(code)
    return normalized


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
        if (candidate / "datasets").exists():
            return candidate
    return None


def _validate_evidence_artifacts(value: Any, case_path: Path) -> list[Any]:
    artifacts = _require_non_empty_list(value, "evidence_bundle.artifacts", case_path)
    repo_root = _find_project_root(case_path.parent)
    if repo_root is None:
        raise ValidationError(f"{case_path}: unable to determine project root for evidence_bundle.artifacts")

    seen_ids: set[str] = set()
    for index, item in enumerate(artifacts, start=1):
        artifact = _require_mapping(item, f"evidence_bundle.artifacts[{index}]", case_path)
        _require_keys(
            artifact,
            [
                "id",
                "path",
                "role",
                "media_type",
                "source_url",
                "collected_at",
                "original_filename",
                "sha256",
                "acquisition_method",
                "license",
                "source_dataset",
                "notes",
            ],
            case_path,
            f"evidence_bundle.artifacts[{index}]",
        )

        artifact_id = _require_non_empty_string(
            artifact["id"],
            f"evidence_bundle.artifacts[{index}].id",
            case_path,
        )
        if artifact_id in seen_ids:
            raise ValidationError(f"{case_path}: duplicate evidence_bundle artifact id '{artifact_id}'")
        seen_ids.add(artifact_id)

        artifact_path_text = _require_non_empty_string(
            artifact["path"],
            f"evidence_bundle.artifacts[{index}].path",
            case_path,
        )
        artifact_path = Path(artifact_path_text)
        if artifact_path.is_absolute():
            raise ValidationError(
                f"{case_path}: evidence_bundle.artifacts[{index}].path must be repo-relative, not absolute"
            )

        resolved_path = (repo_root / artifact_path).resolve()
        try:
            resolved_path.relative_to(repo_root)
        except ValueError as exc:
            raise ValidationError(
                f"{case_path}: evidence_bundle.artifacts[{index}].path must stay within the repo"
            ) from exc
        if not resolved_path.exists() or not resolved_path.is_file():
            raise ValidationError(
                f"{case_path}: evidence_bundle.artifacts[{index}].path does not exist: {artifact_path_text}"
            )

        for required_key in (
            "role",
            "media_type",
            "source_url",
            "collected_at",
            "original_filename",
            "sha256",
            "acquisition_method",
            "license",
            "source_dataset",
            "notes",
        ):
            _require_non_empty_string(
                artifact[required_key],
                f"evidence_bundle.artifacts[{index}].{required_key}",
                case_path,
            )

        sha256 = artifact["sha256"].lower()
        if len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
            raise ValidationError(
                f"{case_path}: evidence_bundle.artifacts[{index}].sha256 must be a 64-character hex digest"
            )
        actual_sha256 = _sha256_file(resolved_path)
        if sha256 != actual_sha256:
            raise ValidationError(
                f"{case_path}: evidence_bundle.artifacts[{index}].sha256 does not match {artifact_path_text}"
            )
    return artifacts


def _has_artifact_role(artifacts: list[Any], role: str) -> bool:
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("role") == role:
            return True
    return False


def _pipeline_stage_for_status(status: str) -> str:
    if status == "template":
        return "template"
    if status in {"harvested", "draft"}:
        return "acquisition"
    if status == "validated":
        return "hardened"
    if status == "gold_candidate":
        return "benchmark_queue"
    if status == "gold":
        return "benchmark"
    return "unspecified"


def resolve_loop_mode(manifest: dict[str, Any], mode: str | None = None) -> tuple[str, dict[str, Any]]:
    autonomous_loop = manifest.get("autonomous_loop")
    if not isinstance(autonomous_loop, dict):
        raise ValidationError("manifest is missing autonomous_loop")
    modes = autonomous_loop.get("modes")
    if not isinstance(modes, dict) or not modes:
        raise ValidationError("manifest autonomous_loop is missing modes")

    selected_mode = mode or autonomous_loop.get("default_mode")
    if not isinstance(selected_mode, str) or not selected_mode.strip():
        raise ValidationError("manifest autonomous_loop is missing default_mode")
    mode_config = modes.get(selected_mode)
    if not isinstance(mode_config, dict):
        raise ValidationError(f"unknown autonomous loop mode '{selected_mode}'")
    return selected_mode, mode_config


def classify_failure(validation_status: str, description: str) -> str:
    text = description.lower()
    if validation_status == "worker_timeout":
        return "timeout"
    if validation_status == "disallowed_changes":
        return "policy"
    if validation_status == "no_changes":
        return "no_effect"
    if validation_status == "failed":
        return "validation"
    if validation_status == "worker_failed":
        if any(
            token in text
            for token in (
                "usage limit",
                "read-only file system",
                "failed to install system skills",
                "unexpected argument",
                "permission denied",
                "command not found",
                "no such file or directory",
            )
        ):
            return "environment"
        if any(
            token in text
            for token in (
                "429",
                "503",
                "connection",
                "timed out",
                "download",
                "fetch",
                "dns",
                "temporarily unavailable",
                "http error",
            )
        ):
            return "source_fetch"
        return "worker"
    if validation_status == "ok":
        return "ok"
    return "unknown"


def _validate_target_counts(value: Any, path: Path) -> None:
    target_counts = _require_mapping(value, "target_counts", path)
    for label, target in target_counts.items():
        if not isinstance(label, str) or not label.strip():
            raise ValidationError(f"{path}: target_counts keys must be non-empty strings")
        if not isinstance(target, (int, str)):
            raise ValidationError(f"{path}: target_counts[{label!r}] must be a string or integer")


def _validate_source_family_targets(value: Any, path: Path) -> None:
    source_family_targets = _require_mapping(value, "source_family_targets", path)
    for label, target in source_family_targets.items():
        if not isinstance(label, str) or not label.strip():
            raise ValidationError(f"{path}: source_family_targets keys must be non-empty strings")
        if not isinstance(target, (int, str)):
            raise ValidationError(f"{path}: source_family_targets[{label!r}] must be a string or integer")


def _validate_language_targets(value: Any, path: Path) -> None:
    language_targets = _require_mapping(value, "language_targets", path)
    for label, target in language_targets.items():
        if not isinstance(label, str) or not label.strip():
            raise ValidationError(f"{path}: language_targets keys must be non-empty strings")
        if label != "multilingual_cases":
            _validate_language_code(label, f"language_targets[{label!r}]", path)
        if not isinstance(target, (int, str)):
            raise ValidationError(f"{path}: language_targets[{label!r}] must be a string or integer")


def _validate_status_list(value: Any, name: str, path: Path) -> list[str]:
    statuses = _require_string_list(value, name, path)
    for status in statuses:
        if status not in VALID_CASE_STATUSES:
            raise ValidationError(f"{path}: {name} contains invalid status '{status}'")
    if len(set(statuses)) != len(statuses):
        raise ValidationError(f"{path}: {name} must not contain duplicate statuses")
    return statuses


def _validate_publishing(value: Any, path: Path) -> None:
    publishing = _require_mapping(value, "publishing", path)
    _require_keys(
        publishing,
        ["included_statuses", "evaluation_ready_statuses", "default_consumption_statuses", "notes"],
        path,
        "publishing",
    )
    included_statuses = _validate_status_list(publishing["included_statuses"], "publishing.included_statuses", path)
    evaluation_ready_statuses = _validate_status_list(
        publishing["evaluation_ready_statuses"],
        "publishing.evaluation_ready_statuses",
        path,
    )
    default_consumption_statuses = _validate_status_list(
        publishing["default_consumption_statuses"],
        "publishing.default_consumption_statuses",
        path,
    )
    for status in evaluation_ready_statuses:
        if status not in included_statuses:
            raise ValidationError(
                f"{path}: publishing.evaluation_ready_statuses must be a subset of publishing.included_statuses"
            )
    for status in default_consumption_statuses:
        if status not in included_statuses:
            raise ValidationError(
                f"{path}: publishing.default_consumption_statuses must be a subset of publishing.included_statuses"
            )
    _require_non_empty_string(publishing["notes"], "publishing.notes", path)


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
            "default_mode",
            "modes",
            "failure_policy",
            "family_balance",
            "family_acquisition_strategies",
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

    default_mode = _require_non_empty_string(autonomous_loop["default_mode"], "autonomous_loop.default_mode", path)
    modes = _require_mapping(autonomous_loop["modes"], "autonomous_loop.modes", path)
    if default_mode not in modes:
        raise ValidationError(f"{path}: autonomous_loop.default_mode must reference a key in autonomous_loop.modes")
    for mode_name, mode_value in modes.items():
        if not isinstance(mode_name, str) or not mode_name.strip():
            raise ValidationError(f"{path}: autonomous_loop.modes keys must be non-empty strings")
        mode = _require_mapping(mode_value, f"autonomous_loop.modes.{mode_name}", path)
        _require_keys(
            mode,
            ["description", "goal"],
            path,
            f"autonomous_loop.modes.{mode_name}",
        )
        _require_non_empty_string(mode["description"], f"autonomous_loop.modes.{mode_name}.description", path)
        _require_non_empty_string(mode["goal"], f"autonomous_loop.modes.{mode_name}.goal", path)
        if "mutable_paths" in mode:
            _require_string_list(mode["mutable_paths"], f"autonomous_loop.modes.{mode_name}.mutable_paths", path)
        if "frozen_paths" in mode:
            _require_string_list(mode["frozen_paths"], f"autonomous_loop.modes.{mode_name}.frozen_paths", path)
        if "daily_loop" in mode:
            _require_string_list(mode["daily_loop"], f"autonomous_loop.modes.{mode_name}.daily_loop", path)
        if "keep_if" in mode:
            _require_string_list(mode["keep_if"], f"autonomous_loop.modes.{mode_name}.keep_if", path)
        if "discard_if" in mode:
            _require_string_list(mode["discard_if"], f"autonomous_loop.modes.{mode_name}.discard_if", path)
        if "prompt_rules" in mode:
            _require_string_list(mode["prompt_rules"], f"autonomous_loop.modes.{mode_name}.prompt_rules", path)

    failure_policy = _require_mapping(autonomous_loop["failure_policy"], "autonomous_loop.failure_policy", path)
    _require_keys(
        failure_policy,
        ["retryable_statuses", "max_consecutive_retryable_failures", "stop_on_nonretryable_failure"],
        path,
        "autonomous_loop.failure_policy",
    )
    _require_string_list(
        failure_policy["retryable_statuses"],
        "autonomous_loop.failure_policy.retryable_statuses",
        path,
    )
    _require_positive_int(
        failure_policy["max_consecutive_retryable_failures"],
        "autonomous_loop.failure_policy.max_consecutive_retryable_failures",
        path,
    )
    if not isinstance(failure_policy["stop_on_nonretryable_failure"], bool):
        raise ValidationError(
            f"{path}: autonomous_loop.failure_policy.stop_on_nonretryable_failure must be a boolean"
        )

    family_balance = _require_mapping(autonomous_loop["family_balance"], "autonomous_loop.family_balance", path)
    _require_keys(
        family_balance,
        ["max_share_by_source_family", "underrepresented_families", "reject_acquisition_if_family_above_max_share"],
        path,
        "autonomous_loop.family_balance",
    )
    max_share_by_source_family = _require_mapping(
        family_balance["max_share_by_source_family"],
        "autonomous_loop.family_balance.max_share_by_source_family",
        path,
    )
    for family, value in max_share_by_source_family.items():
        if not isinstance(family, str) or not family.strip():
            raise ValidationError(
                f"{path}: autonomous_loop.family_balance.max_share_by_source_family keys must be non-empty strings"
            )
        if not isinstance(value, (int, float)) or value <= 0 or value > 1:
            raise ValidationError(
                f"{path}: autonomous_loop.family_balance.max_share_by_source_family[{family!r}] must be between 0 and 1"
            )
    _require_string_list(
        family_balance["underrepresented_families"],
        "autonomous_loop.family_balance.underrepresented_families",
        path,
    )
    if not isinstance(family_balance["reject_acquisition_if_family_above_max_share"], bool):
        raise ValidationError(
            f"{path}: autonomous_loop.family_balance.reject_acquisition_if_family_above_max_share must be a boolean"
        )

    family_acquisition_strategies = _require_mapping(
        autonomous_loop["family_acquisition_strategies"],
        "autonomous_loop.family_acquisition_strategies",
        path,
    )
    for family_name, strategy_value in family_acquisition_strategies.items():
        if not isinstance(family_name, str) or not family_name.strip():
            raise ValidationError(
                f"{path}: autonomous_loop.family_acquisition_strategies keys must be non-empty strings"
            )
        strategy = _require_mapping(
            strategy_value,
            f"autonomous_loop.family_acquisition_strategies.{family_name}",
            path,
        )
        _require_keys(
            strategy,
            ["acquisition_method", "search_rule", "preservation_rule"],
            path,
            f"autonomous_loop.family_acquisition_strategies.{family_name}",
        )
        for key in ("acquisition_method", "search_rule", "preservation_rule"):
            _require_non_empty_string(
                strategy[key],
                f"autonomous_loop.family_acquisition_strategies.{family_name}.{key}",
                path,
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
    if "source_family_targets" in manifest:
        _validate_source_family_targets(manifest["source_family_targets"], manifest_path)
    if "language_targets" in manifest:
        _validate_language_targets(manifest["language_targets"], manifest_path)
    if "publishing" in manifest:
        _validate_publishing(manifest["publishing"], manifest_path)
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
            "status",
            "task_type",
            "answer_mode",
            "source_family",
            "source_tier",
            "source_languages",
            "evidence_languages",
            "answer_language",
            "sources",
            "evidence_bundle",
            "expected_output",
        ],
        path,
    )

    evidence_bundle = _require_mapping(case["evidence_bundle"], "evidence_bundle", path)
    _require_keys(evidence_bundle, ["kind"], path, "evidence_bundle")

    # Every case must carry materialized source content so exports always include a source document.
    _require_keys(evidence_bundle, ["content_markdown"], path, "evidence_bundle")
    _require_keys(evidence_bundle, ["artifacts"], path, "evidence_bundle")
    if "required_artifacts" in evidence_bundle:
        _require_string_list(evidence_bundle["required_artifacts"], "evidence_bundle.required_artifacts", path)
    artifacts = _validate_evidence_artifacts(evidence_bundle["artifacts"], path)

    status = _require_non_empty_string(case["status"], "status", path)
    if status not in VALID_CASE_STATUSES:
        raise ValidationError(f"{path}: invalid status '{status}'")

    if not _has_artifact_role(artifacts, "source_document"):
        raise ValidationError(f"{path}: evidence_bundle.artifacts must include a source_document artifact")
    if status in {"validated", "gold_candidate", "gold"} and not _has_artifact_role(artifacts, "original_source_snapshot"):
        raise ValidationError(
            f"{path}: {status} cases must include an original_source_snapshot artifact; "
            "downgrade the case to harvested/draft until provenance hardening is complete"
        )

    if "related_cases" in case:
        _require_string_list(case["related_cases"], "related_cases", path)

    answer_mode = case["answer_mode"]
    if answer_mode not in VALID_ANSWER_MODES:
        raise ValidationError(f"{path}: invalid answer_mode '{answer_mode}'")

    source_tier = case["source_tier"]
    if source_tier not in VALID_SOURCE_TIERS:
        raise ValidationError(f"{path}: invalid source_tier '{source_tier}'")

    source_languages = _validate_language_list(case["source_languages"], "source_languages", path)
    evidence_languages = _validate_language_list(case["evidence_languages"], "evidence_languages", path)
    answer_language = _validate_language_code(case["answer_language"], "answer_language", path)

    sources = case["sources"]
    if not isinstance(sources, list) or not sources:
        raise ValidationError(f"{path}: sources must be a non-empty list")

    source_item_languages: list[str] = []
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise ValidationError(f"{path}: source #{index} must be a mapping")
        _require_keys(source, ["label", "url", "language", "checked_on", "provenance"], path)
        language = _validate_language_code(source["language"], f"sources[{index}].language", path)
        source_item_languages.append(language)
        if language not in source_languages:
            raise ValidationError(f"{path}: sources[{index}].language '{language}' must appear in source_languages")

    if answer_language == "und":
        raise ValidationError(f"{path}: answer_language cannot be 'und'")
    if case["source_family"] == "cross_country_leak_reporting" and len(set(source_languages)) < 2:
        raise ValidationError(f"{path}: cross_country_leak_reporting cases must declare at least two source_languages")
    if case["source_family"] == "cross_country_leak_reporting" and len(set(source_item_languages)) < 2:
        raise ValidationError(f"{path}: cross_country_leak_reporting cases must include at least two source languages")

    if answer_mode in {"exact", "mixed"} and "answer_key" not in case:
        raise ValidationError(f"{path}: answer_key is required for answer_mode '{answer_mode}'")

    if answer_mode in {"rubric", "mixed"} and "rubric" not in case:
        raise ValidationError(f"{path}: rubric is required for answer_mode '{answer_mode}'")

    if status == "gold_candidate":
        review_candidate_value = case.get("review_candidate")
        if not isinstance(review_candidate_value, dict):
            raise ValidationError(
                f"{path}: gold_candidate cases must include review_candidate metadata with prepared_by, prepared_on, and rationale"
            )
        review_candidate = _require_mapping(review_candidate_value, "review_candidate", path)
        _require_keys(
            review_candidate,
            ["prepared_by", "prepared_on", "rationale"],
            path,
            "review_candidate",
        )
        for required_key in ("prepared_by", "prepared_on", "rationale"):
            _require_non_empty_string(
                review_candidate[required_key],
                f"review_candidate.{required_key}",
                path,
            )

    if status == "gold":
        review_value = case.get("review")
        if not isinstance(review_value, dict):
            raise ValidationError(
                f"{path}: gold cases must include review metadata with reviewed_by, reviewed_on, and notes"
            )
        review = _require_mapping(review_value, "review", path)
        _require_keys(review, ["reviewed_by", "reviewed_on", "notes"], path, "review")
        for required_key in ("reviewed_by", "reviewed_on", "notes"):
            _require_non_empty_string(review[required_key], f"review.{required_key}", path)

    return case


def load_suite(manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = validate_manifest(manifest_path)
    case_files = manifest["case_files"]

    base_dir = manifest_path.parent
    _validate_results_log(manifest, manifest_path)
    declared_case_paths = {str((base_dir / relative_case_path).resolve()) for relative_case_path in case_files}
    cases_dir = base_dir / "cases"
    if cases_dir.exists():
        orphan_case_paths = sorted(
            str(path.relative_to(base_dir))
            for path in cases_dir.rglob("*.yaml")
            if str(path.resolve()) not in declared_case_paths
        )
        if orphan_case_paths:
            raise ValidationError(
                f"{manifest_path}: case_files is missing declared entries for {', '.join(orphan_case_paths)}"
            )
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
    pipeline = Counter(_pipeline_stage_for_status(case.get("status", "unspecified")) for case in cases)
    case_source_languages = Counter()
    source_record_languages = Counter()
    evidence_languages = Counter()
    answer_languages = Counter()
    multilingual_cases_total = 0

    for case in cases:
        source_languages = case.get("source_languages", [])
        if isinstance(source_languages, list):
            unique_source_languages = []
            seen: set[str] = set()
            for code in source_languages:
                if isinstance(code, str) and code not in seen:
                    seen.add(code)
                    unique_source_languages.append(code)
            for code in unique_source_languages:
                case_source_languages[code] += 1
            if len(unique_source_languages) >= 2:
                multilingual_cases_total += 1

        case_evidence_languages = case.get("evidence_languages", [])
        if isinstance(case_evidence_languages, list):
            for code in case_evidence_languages:
                if isinstance(code, str):
                    evidence_languages[code] += 1

        answer_language = case.get("answer_language")
        if isinstance(answer_language, str):
            answer_languages[answer_language] += 1

        for source in case.get("sources", []) or []:
            if isinstance(source, dict) and isinstance(source.get("language"), str):
                source_record_languages[source["language"]] += 1

    return {
        "cases_total": len(cases),
        "by_task_type": dict(sorted(by_task.items())),
        "by_answer_mode": dict(sorted(by_mode.items())),
        "by_source_tier": dict(sorted(by_tier.items())),
        "by_source_family": dict(sorted(by_family.items())),
        "by_status": dict(sorted(statuses.items())),
        "by_pipeline_stage": dict(sorted(pipeline.items())),
        "by_case_source_language": dict(sorted(case_source_languages.items())),
        "by_source_record_language": dict(sorted(source_record_languages.items())),
        "by_evidence_language": dict(sorted(evidence_languages.items())),
        "by_answer_language": dict(sorted(answer_languages.items())),
        "multilingual_cases_total": multilingual_cases_total,
    }


def resolve_publish_policy(manifest: dict[str, Any]) -> dict[str, Any]:
    publishing = manifest.get("publishing")
    if not isinstance(publishing, dict):
        return {
            "included_statuses": list(DEFAULT_PUBLISH_INCLUDED_STATUSES),
            "evaluation_ready_statuses": list(DEFAULT_EVALUATION_READY_STATUSES),
            "default_consumption_statuses": list(DEFAULT_EVALUATION_READY_STATUSES),
            "notes": (
                "HF snapshots include all lifecycle states. Downstream evaluation should default "
                "to validated and gold cases, while gold_candidate remains a review-ready queue."
            ),
        }
    return {
        "included_statuses": list(publishing["included_statuses"]),
        "evaluation_ready_statuses": list(publishing["evaluation_ready_statuses"]),
        "default_consumption_statuses": list(publishing["default_consumption_statuses"]),
        "notes": str(publishing["notes"]).strip(),
    }


def _parse_target_lower_bound(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None
    if "-" in text:
        lower_bound = text.split("-", 1)[0].strip()
        return int(lower_bound) if lower_bound.isdigit() else None
    return int(text) if text.isdigit() else None


def _parse_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    return int(text) if text.isdigit() else None


def _truncate_text(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def summarize_target_progress(manifest: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_cases(cases)
    target_counts = manifest.get("target_counts", {})
    target_proxies = {
        "documents": (
            summary["by_source_family"].get("public_documents_with_metadata", 0),
            "proxy: source_family=public_documents_with_metadata",
        ),
        "entity_link_cases": (
            summary["by_task_type"].get("entity_linking", 0),
            "proxy: task_type=entity_linking",
        ),
        "structured_records": (
            summary["by_task_type"].get("field_extraction", 0),
            "proxy: task_type=field_extraction",
        ),
        "manual_gold_cases": (
            summary["by_status"].get("gold", 0),
            "proxy: status=gold",
        ),
    }

    progress_rows: list[dict[str, Any]] = []
    under_target_labels: list[str] = []
    for label, target in target_counts.items():
        current_value, basis = target_proxies.get(label, (0, "no proxy configured"))
        lower_bound = _parse_target_lower_bound(target)
        gap_to_lower_bound = None if lower_bound is None else max(lower_bound - current_value, 0)
        if gap_to_lower_bound:
            under_target_labels.append(label)
        progress_rows.append(
            {
                "target": label,
                "target_range": target,
                "current": current_value,
                "gap_to_lower_bound": gap_to_lower_bound,
                "basis": basis,
            }
        )

    return {
        "progress_rows": progress_rows,
        "under_target_labels": under_target_labels,
    }


def summarize_language_target_progress(manifest: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_cases(cases)
    language_targets = manifest.get("language_targets", {})
    progress_rows: list[dict[str, Any]] = []
    underrepresented_languages: list[str] = []

    for label, target in language_targets.items():
        if label == "multilingual_cases":
            current_value = summary["multilingual_cases_total"]
            basis = "proxy: cases with 2+ source_languages"
        else:
            current_value = summary["by_case_source_language"].get(label, 0)
            basis = "proxy: case source_languages"
        lower_bound = _parse_target_lower_bound(target)
        gap_to_lower_bound = None if lower_bound is None else max(lower_bound - current_value, 0)
        if gap_to_lower_bound:
            underrepresented_languages.append(label)
        progress_rows.append(
            {
                "language": label,
                "target_range": target,
                "current": current_value,
                "gap_to_lower_bound": gap_to_lower_bound,
                "basis": basis,
            }
        )

    return {
        "progress_rows": progress_rows,
        "underrepresented_languages": underrepresented_languages,
    }


def summarize_source_family_balance(manifest: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_cases(cases)
    source_family_targets = manifest.get("source_family_targets", {})
    autonomous_loop = manifest.get("autonomous_loop", {})
    family_balance = autonomous_loop.get("family_balance", {}) if isinstance(autonomous_loop, dict) else {}
    max_share_by_source_family = (
        family_balance.get("max_share_by_source_family", {}) if isinstance(family_balance, dict) else {}
    )
    underrepresented_families = (
        family_balance.get("underrepresented_families", []) if isinstance(family_balance, dict) else []
    )

    families = set(summary["by_source_family"])
    families.update(key for key in source_family_targets if isinstance(key, str))
    families.update(key for key in max_share_by_source_family if isinstance(key, str))
    families.update(item for item in underrepresented_families if isinstance(item, str))

    total_cases = summary["cases_total"] or 0
    progress_rows: list[dict[str, Any]] = []
    overrepresented: list[str] = []
    underrepresented: list[str] = []

    for family in sorted(families):
        current = summary["by_source_family"].get(family, 0)
        share = 0.0 if total_cases == 0 else current / total_cases
        target = source_family_targets.get(family)
        lower_bound = _parse_target_lower_bound(target)
        gap_to_lower_bound = None if lower_bound is None else max(lower_bound - current, 0)
        max_share = max_share_by_source_family.get(family)
        if isinstance(max_share, (int, float)) and share > max_share:
            overrepresented.append(family)
        if family in underrepresented_families and lower_bound is not None and current < lower_bound:
            underrepresented.append(family)
        progress_rows.append(
            {
                "source_family": family,
                "current": current,
                "share": share,
                "target": target,
                "gap_to_lower_bound": gap_to_lower_bound,
                "max_share": max_share,
            }
        )

    return {
        "progress_rows": progress_rows,
        "overrepresented_families": overrepresented,
        "underrepresented_families": underrepresented,
    }


def summarize_lifecycle_readiness(manifest: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_cases(cases)
    publish_policy = resolve_publish_policy(manifest)
    status_rows: list[dict[str, Any]] = []
    for status in DEFAULT_PUBLISH_INCLUDED_STATUSES:
        count = summary["by_status"].get(status, 0)
        status_rows.append(
            {
                "status": status,
                "count": count,
                "pipeline_stage": _pipeline_stage_for_status(status),
                "included_in_publish": status in publish_policy["included_statuses"],
                "evaluation_ready": status in publish_policy["evaluation_ready_statuses"],
                "default_consumption": status in publish_policy["default_consumption_statuses"],
            }
        )

    included_cases_total = sum(
        summary["by_status"].get(status, 0) for status in publish_policy["included_statuses"]
    )
    evaluation_ready_cases_total = sum(
        summary["by_status"].get(status, 0) for status in publish_policy["evaluation_ready_statuses"]
    )
    default_consumption_cases_total = sum(
        summary["by_status"].get(status, 0) for status in publish_policy["default_consumption_statuses"]
    )
    benchmark_queue_cases_total = summary["by_status"].get("gold_candidate", 0)
    benchmark_ready_cases_total = summary["by_status"].get("gold", 0)
    under_construction_cases_total = max(included_cases_total - evaluation_ready_cases_total, 0)

    return {
        "publish_policy": publish_policy,
        "status_rows": status_rows,
        "included_cases_total": included_cases_total,
        "evaluation_ready_cases_total": evaluation_ready_cases_total,
        "default_consumption_cases_total": default_consumption_cases_total,
        "benchmark_queue_cases_total": benchmark_queue_cases_total,
        "benchmark_ready_cases_total": benchmark_ready_cases_total,
        "under_construction_cases_total": under_construction_cases_total,
    }


def _classify_effort_proxy(row: dict[str, str], case_delta: int | None) -> str:
    description = row.get("description", "").lower()
    if case_delta is not None and case_delta > 0:
        return "net_new"
    if row.get("validation_status") != "ok":
        return "failed"
    if case_delta is None and row.get("kept") == "true":
        return "baseline_unknown"
    if any(
        token in description
        for token in ("hardening", "backfill", "provenance", "snapshot", "artifact", "digest", "review", "gold")
    ):
        return "hardening"
    if row.get("kept") == "true":
        return "zero_growth_kept"
    return "rejected"


def summarize_results_log(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    autonomous_loop = manifest.get("autonomous_loop")
    if not isinstance(autonomous_loop, dict):
        return {
            "rows_total": 0,
            "accepted_runs": 0,
            "rejected_runs": 0,
            "non_ok_runs": 0,
            "last_cases_total": None,
            "by_failure_status": {},
            "by_failure_class": {},
            "by_change_kind": {},
            "accepted_by_source_family": {},
            "rejected_by_source_family": {},
            "effort_proxy_counts": {},
            "net_new_runs": 0,
            "zero_growth_kept_runs": 0,
            "hardening_proxy_runs": 0,
            "total_case_growth": 0,
            "acceptance_rate": 0.0,
            "failure_rate": 0.0,
            "case_growth_events": [],
            "recent_window": {},
            "recent_runs": [],
        }

    logging = autonomous_loop.get("logging")
    if not isinstance(logging, dict):
        return {
            "rows_total": 0,
            "accepted_runs": 0,
            "rejected_runs": 0,
            "non_ok_runs": 0,
            "last_cases_total": None,
            "by_failure_status": {},
            "by_failure_class": {},
            "by_change_kind": {},
            "accepted_by_source_family": {},
            "rejected_by_source_family": {},
            "effort_proxy_counts": {},
            "net_new_runs": 0,
            "zero_growth_kept_runs": 0,
            "hardening_proxy_runs": 0,
            "total_case_growth": 0,
            "acceptance_rate": 0.0,
            "failure_rate": 0.0,
            "case_growth_events": [],
            "recent_window": {},
            "recent_runs": [],
        }

    results_path_value = logging.get("results_path")
    if not isinstance(results_path_value, str) or not results_path_value.strip():
        return {
            "rows_total": 0,
            "accepted_runs": 0,
            "rejected_runs": 0,
            "non_ok_runs": 0,
            "last_cases_total": None,
            "by_failure_status": {},
            "by_failure_class": {},
            "by_change_kind": {},
            "accepted_by_source_family": {},
            "rejected_by_source_family": {},
            "effort_proxy_counts": {},
            "net_new_runs": 0,
            "zero_growth_kept_runs": 0,
            "hardening_proxy_runs": 0,
            "total_case_growth": 0,
            "acceptance_rate": 0.0,
            "failure_rate": 0.0,
            "case_growth_events": [],
            "recent_window": {},
            "recent_runs": [],
        }

    results_path = (manifest_path.parent / results_path_value).resolve()
    if not results_path.exists():
        return {
            "rows_total": 0,
            "accepted_runs": 0,
            "rejected_runs": 0,
            "non_ok_runs": 0,
            "last_cases_total": None,
            "by_failure_status": {},
            "by_failure_class": {},
            "by_change_kind": {},
            "accepted_by_source_family": {},
            "rejected_by_source_family": {},
            "effort_proxy_counts": {},
            "net_new_runs": 0,
            "zero_growth_kept_runs": 0,
            "hardening_proxy_runs": 0,
            "total_case_growth": 0,
            "acceptance_rate": 0.0,
            "failure_rate": 0.0,
            "case_growth_events": [],
            "recent_window": {},
            "recent_runs": [],
        }

    rows = results_path.read_text(encoding="utf-8").splitlines()
    if not rows:
        return {
            "rows_total": 0,
            "accepted_runs": 0,
            "rejected_runs": 0,
            "non_ok_runs": 0,
            "last_cases_total": None,
            "by_failure_status": {},
            "by_failure_class": {},
            "recent_runs": [],
        }

    data_rows: list[dict[str, str]] = []
    for raw_row in rows[1:]:
        if not raw_row.strip():
            continue
        parts = raw_row.split("\t", maxsplit=len(REQUIRED_RUN_LOG_COLUMNS) - 1)
        if len(parts) < len(REQUIRED_RUN_LOG_COLUMNS):
            parts.extend([""] * (len(REQUIRED_RUN_LOG_COLUMNS) - len(parts)))
        data_rows.append(dict(zip(REQUIRED_RUN_LOG_COLUMNS, parts, strict=False)))

    accepted_runs = sum(1 for row in data_rows if row["kept"] == "true")
    rejected_runs = sum(1 for row in data_rows if row["kept"] == "false")
    non_ok_runs = sum(1 for row in data_rows if row["validation_status"] != "ok")
    by_failure_status = Counter(row["validation_status"] for row in data_rows if row["validation_status"] != "ok")
    by_failure_class = Counter(
        classify_failure(row["validation_status"], row["description"])
        for row in data_rows
        if row["validation_status"] != "ok"
    )
    by_change_kind = Counter(row["change_kind"] for row in data_rows if row["change_kind"])
    accepted_by_source_family = Counter(
        row["source_family"] for row in data_rows if row["kept"] == "true" and row["source_family"]
    )
    rejected_by_source_family = Counter(
        row["source_family"] for row in data_rows if row["kept"] == "false" and row["source_family"]
    )
    effort_proxy_counts = Counter()
    case_growth_events: list[dict[str, Any]] = []
    previous_cases_total: int | None = None
    total_case_growth = 0
    net_new_runs = 0
    zero_growth_kept_runs = 0
    hardening_proxy_runs = 0
    recent_window_rows: list[dict[str, Any]] = []
    for row in data_rows:
        current_cases_total = _parse_int(row["cases_total"])
        case_delta = None
        if current_cases_total is not None and previous_cases_total is not None:
            case_delta = current_cases_total - previous_cases_total
        effort_proxy = _classify_effort_proxy(row, case_delta)
        effort_proxy_counts[effort_proxy] += 1
        if row["kept"] == "true" and case_delta is not None and case_delta > 0:
            net_new_runs += 1
            total_case_growth += case_delta
            case_growth_events.append(
                {
                    "run_id": row["run_id"],
                    "timestamp": row["timestamp"],
                    "source_family": row["source_family"],
                    "change_kind": row["change_kind"],
                    "cases_total": current_cases_total,
                    "case_delta": case_delta,
                }
            )
        elif row["kept"] == "true" and row["validation_status"] == "ok" and case_delta == 0:
            zero_growth_kept_runs += 1
            if effort_proxy in {"hardening", "zero_growth_kept"}:
                hardening_proxy_runs += 1
        recent_window_rows.append(
            {
                **row,
                "case_delta": case_delta,
                "effort_proxy": effort_proxy,
            }
        )
        if current_cases_total is not None:
            previous_cases_total = current_cases_total

    recent_runs = data_rows[-5:]
    last_cases_total = recent_runs[-1]["cases_total"] if recent_runs else None
    recent_window_slice = recent_window_rows[-10:]
    recent_window_failure_rate = 0.0
    recent_window_case_growth = sum(
        max(int(row["case_delta"]), 0) for row in recent_window_slice if isinstance(row["case_delta"], int)
    )
    if recent_window_slice:
        recent_window_failure_rate = sum(1 for row in recent_window_slice if row["validation_status"] != "ok") / len(
            recent_window_slice
        )

    return {
        "rows_total": len(data_rows),
        "accepted_runs": accepted_runs,
        "rejected_runs": rejected_runs,
        "non_ok_runs": non_ok_runs,
        "last_cases_total": last_cases_total,
        "by_failure_status": dict(sorted(by_failure_status.items())),
        "by_failure_class": dict(sorted(by_failure_class.items())),
        "by_change_kind": dict(sorted(by_change_kind.items())),
        "accepted_by_source_family": dict(sorted(accepted_by_source_family.items())),
        "rejected_by_source_family": dict(sorted(rejected_by_source_family.items())),
        "effort_proxy_counts": dict(sorted(effort_proxy_counts.items())),
        "net_new_runs": net_new_runs,
        "zero_growth_kept_runs": zero_growth_kept_runs,
        "hardening_proxy_runs": hardening_proxy_runs,
        "total_case_growth": total_case_growth,
        "acceptance_rate": 0.0 if not data_rows else accepted_runs / len(data_rows),
        "failure_rate": 0.0 if not data_rows else non_ok_runs / len(data_rows),
        "case_growth_events": case_growth_events[-10:],
        "recent_window": {
            "rows_total": len(recent_window_slice),
            "accepted_runs": sum(1 for row in recent_window_slice if row["kept"] == "true"),
            "non_ok_runs": sum(1 for row in recent_window_slice if row["validation_status"] != "ok"),
            "failure_rate": recent_window_failure_rate,
            "case_growth_total": recent_window_case_growth,
        },
        "recent_runs": recent_runs,
    }


def summarize_gap_analysis(manifest: dict[str, Any], cases: list[dict[str, Any]], manifest_path: Path) -> dict[str, Any]:
    target_progress = summarize_target_progress(manifest, cases)
    language_progress = summarize_language_target_progress(manifest, cases)
    source_family_balance = summarize_source_family_balance(manifest, cases)
    lifecycle = summarize_lifecycle_readiness(manifest, cases)
    run_log = summarize_results_log(manifest, manifest_path)

    recommended_actions: list[dict[str, str]] = []
    for label in target_progress["under_target_labels"]:
        recommended_actions.append(
            {
                "kind": "target_count",
                "label": label,
                "reason": "suite-level target is still below its configured lower bound",
            }
        )
    for family in source_family_balance["underrepresented_families"]:
        recommended_actions.append(
            {
                "kind": "source_family",
                "label": family,
                "reason": "source family is explicitly underrepresented relative to its target range",
            }
        )
    for language in language_progress["underrepresented_languages"]:
        recommended_actions.append(
            {
                "kind": "language",
                "label": language,
                "reason": "language coverage is below its configured lower bound",
            }
        )
    if lifecycle["benchmark_ready_cases_total"] == 0:
        if lifecycle["benchmark_queue_cases_total"] == 0:
            recommended_actions.append(
                {
                    "kind": "lifecycle",
                    "label": "gold_candidate",
                    "reason": "no review-ready gold_candidate cases exist yet; prepare candidates and defer final gold promotion until reviewer capacity exists",
                }
            )
        else:
            recommended_actions.append(
                {
                    "kind": "lifecycle",
                    "label": "gold_review",
                    "reason": "gold_candidate cases exist but no benchmark-ready gold cases have been signed off yet",
                }
            )
    if run_log["hardening_proxy_runs"] > run_log["net_new_runs"]:
        recommended_actions.append(
            {
                "kind": "operations",
                "label": "acquisition_vs_hardening",
                "reason": "recent logged effort is spending more kept runs on zero-growth hardening/maintenance proxies than net-new acquisition",
            }
        )

    return {
        "missing_target_counts": target_progress["under_target_labels"],
        "underrepresented_source_families": source_family_balance["underrepresented_families"],
        "overrepresented_source_families": source_family_balance["overrepresented_families"],
        "underrepresented_languages": language_progress["underrepresented_languages"],
        "benchmark_queue_cases_total": lifecycle["benchmark_queue_cases_total"],
        "benchmark_ready_cases_total": lifecycle["benchmark_ready_cases_total"],
        "recommended_next_actions": recommended_actions,
    }


def summarize_suite(manifest_path: Path, manifest: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_cases(cases)
    target_progress = summarize_target_progress(manifest, cases)
    language_target_progress = summarize_language_target_progress(manifest, cases)
    source_family_balance = summarize_source_family_balance(manifest, cases)
    lifecycle = summarize_lifecycle_readiness(manifest, cases)
    run_log = summarize_results_log(manifest, manifest_path)
    gap_analysis = summarize_gap_analysis(manifest, cases, manifest_path)
    return {
        **summary,
        "target_progress": target_progress,
        "language_target_progress": language_target_progress,
        "source_family_balance": source_family_balance,
        "lifecycle": lifecycle,
        "run_log": run_log,
        "gap_analysis": gap_analysis,
    }


def render_suite_dashboard(manifest_path: Path, manifest: dict[str, Any], cases: list[dict[str, Any]]) -> str:
    suite_summary = summarize_suite(manifest_path, manifest, cases)
    summary = {key: value for key, value in suite_summary.items() if key in summarize_cases(cases)}
    run_log = suite_summary["run_log"]
    target_progress = suite_summary["target_progress"]
    source_family_targets = manifest.get("source_family_targets", {})
    language_targets = manifest.get("language_targets", {})
    status_text = str(manifest.get("status", "unspecified")).strip() or "unspecified"
    objective = " ".join(str(manifest["objective"]).split())
    mode_name, mode_config = resolve_loop_mode(manifest)
    source_family_balance = suite_summary["source_family_balance"]
    language_target_progress = suite_summary["language_target_progress"]
    lifecycle = suite_summary["lifecycle"]
    gap_analysis = suite_summary["gap_analysis"]

    lines = [
        f"# {manifest['suite_id']} Status Dashboard",
        "",
        "> Source of truth for live suite state: regenerate this file with",
        f"> `PYTHONPATH=src python3 -m auto_dataset.cli dashboard {manifest_path.as_posix()} --output docs/{manifest['suite_id']}-status.md`",
        "",
        "> Warning: prose counts in narrative docs can drift. Use this dashboard or",
        f"> `auto-dataset summary {manifest_path.as_posix()}` for live counts.",
        "",
        "## Suite State",
        "",
        f"- suite status: `{status_text}`",
        "- roadmap phase: `Phase 2: First real public suite`",
        f"- default loop mode: `{mode_name}`",
        f"- loop mode goal: {mode_config['goal']}",
        f"- objective: {objective}",
        f"- cases total: `{summary['cases_total']}`",
        "",
        "## Current Coverage",
        "",
        f"- by status: {_format_counts(summary['by_status'])}",
        f"- by task type: {_format_counts(summary['by_task_type'])}",
        f"- by answer mode: {_format_counts(summary['by_answer_mode'])}",
        f"- by source family: {_format_counts(summary['by_source_family'])}",
        f"- by source tier: {_format_counts(summary['by_source_tier'])}",
        f"- by pipeline stage: {_format_counts(summary['by_pipeline_stage'])}",
        "",
        "## Source Family Balance",
        "",
        f"- overrepresented families: {_format_counts({family: summary['by_source_family'].get(family, 0) for family in source_family_balance['overrepresented_families']})}",
        f"- underrepresented families: {_format_counts({family: summary['by_source_family'].get(family, 0) for family in source_family_balance['underrepresented_families']})}",
        "",
        "## Language Coverage",
        "",
        f"- by case source language: {_format_counts(summary['by_case_source_language'])}",
        f"- by source record language: {_format_counts(summary['by_source_record_language'])}",
        f"- by evidence language: {_format_counts(summary['by_evidence_language'])}",
        f"- by answer language: {_format_counts(summary['by_answer_language'])}",
        f"- multilingual cases total: `{summary['multilingual_cases_total']}`",
        "",
        "## Target Progress",
        "",
        "| target | target range | current | gap to lower bound | basis |",
        "| --- | --- | ---: | ---: | --- |",
    ]

    for row in target_progress["progress_rows"]:
        gap_text = "n/a" if row["gap_to_lower_bound"] is None else str(row["gap_to_lower_bound"])
        lines.append(f"| {row['target']} | {row['target_range']} | {row['current']} | {gap_text} | {row['basis']} |")

    if source_family_targets:
        lines.extend(
            [
                "",
                "## Source Family Target Progress",
                "",
                "| source family | target range | current | current share | gap to lower bound | max share |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in source_family_balance["progress_rows"]:
            if row["source_family"] not in source_family_targets:
                continue
            target = row["target"]
            gap_text = "n/a" if row["gap_to_lower_bound"] is None else str(row["gap_to_lower_bound"])
            max_share = row["max_share"]
            max_share_text = "n/a" if max_share is None else f"{max_share:.0%}"
            lines.append(
                f"| {row['source_family']} | {target} | {row['current']} | {row['share']:.0%} | {gap_text} | {max_share_text} |"
            )

    if language_targets:
        lines.extend(
            [
                "",
                "## Language Target Progress",
                "",
                "| language target | target range | current | gap to lower bound | basis |",
                "| --- | --- | ---: | ---: | --- |",
            ]
        )
        for row in language_target_progress["progress_rows"]:
            gap_text = "n/a" if row["gap_to_lower_bound"] is None else str(row["gap_to_lower_bound"])
            lines.append(
                f"| {row['language']} | {row['target_range']} | {row['current']} | {gap_text} | {row['basis']} |"
            )

    lines.extend(
        [
            "",
            "## Lifecycle Readiness",
            "",
            f"- publish includes statuses: `{', '.join(lifecycle['publish_policy']['included_statuses'])}`",
            f"- evaluation-ready statuses: `{', '.join(lifecycle['publish_policy']['evaluation_ready_statuses'])}`",
            f"- default downstream-consumption statuses: `{', '.join(lifecycle['publish_policy']['default_consumption_statuses'])}`",
            f"- included cases total: `{lifecycle['included_cases_total']}`",
            f"- evaluation-ready cases total: `{lifecycle['evaluation_ready_cases_total']}`",
            f"- benchmark-queue cases total: `{lifecycle['benchmark_queue_cases_total']}`",
            f"- benchmark-ready cases total: `{lifecycle['benchmark_ready_cases_total']}`",
            f"- under-construction cases total: `{lifecycle['under_construction_cases_total']}`",
            f"- policy note: {lifecycle['publish_policy']['notes']}",
            "",
            "| status | count | pipeline stage | published | evaluation-ready | default downstream use |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in lifecycle["status_rows"]:
        lines.append(
            f"| {row['status']} | {row['count']} | {row['pipeline_stage']} | "
            f"{'yes' if row['included_in_publish'] else 'no'} | "
            f"{'yes' if row['evaluation_ready'] else 'no'} | "
            f"{'yes' if row['default_consumption'] else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Gap Analysis",
            "",
            f"- missing suite-level targets: {', '.join(gap_analysis['missing_target_counts']) or 'none'}",
            f"- underrepresented source families: {', '.join(gap_analysis['underrepresented_source_families']) or 'none'}",
            f"- overrepresented source families: {', '.join(gap_analysis['overrepresented_source_families']) or 'none'}",
            f"- underrepresented languages: {', '.join(gap_analysis['underrepresented_languages']) or 'none'}",
            f"- benchmark-queue cases total: `{gap_analysis['benchmark_queue_cases_total']}`",
            f"- benchmark-ready cases total: `{gap_analysis['benchmark_ready_cases_total']}`",
            "",
            "| next focus | label | reason |",
            "| --- | --- | --- |",
        ]
    )
    for item in gap_analysis["recommended_next_actions"]:
        lines.append(f"| {item['kind']} | {item['label']} | {item['reason']} |")
    if not gap_analysis["recommended_next_actions"]:
        lines.append("| none | n/a | no immediate target gaps are flagged |")

    lines.extend(
        [
            "",
            "## Run Log",
            "",
            f"- logged runs: `{run_log['rows_total']}`",
            f"- accepted runs: `{run_log['accepted_runs']}`",
            f"- rejected runs: `{run_log['rejected_runs']}`",
            f"- non-ok runs: `{run_log['non_ok_runs']}`",
            f"- acceptance rate: `{run_log['acceptance_rate']:.0%}`",
            f"- failure rate: `{run_log['failure_rate']:.0%}`",
            f"- change kinds: {_format_counts(run_log['by_change_kind'])}",
            f"- failure statuses: {_format_counts(run_log['by_failure_status'])}",
            f"- failure classes: {_format_counts(run_log['by_failure_class'])}",
            f"- accepted by source family: {_format_counts(run_log['accepted_by_source_family'])}",
            f"- rejected by source family: {_format_counts(run_log['rejected_by_source_family'])}",
            f"- effort proxies: {_format_counts(run_log['effort_proxy_counts'])}",
            f"- net-new runs: `{run_log['net_new_runs']}`",
            f"- zero-growth kept runs: `{run_log['zero_growth_kept_runs']}`",
            f"- hardening proxy runs: `{run_log['hardening_proxy_runs']}`",
            f"- total recorded case growth: `{run_log['total_case_growth']}`",
            f"- last recorded cases total: `{run_log['last_cases_total'] or 'n/a'}`",
            f"- recent-window case growth: `{run_log['recent_window'].get('case_growth_total', 0)}` over `{run_log['recent_window'].get('rows_total', 0)}` runs",
            f"- recent-window failure rate: `{run_log['recent_window'].get('failure_rate', 0.0):.0%}`",
            "",
            "## Lifecycle Notes",
            "",
            "- `template`: scaffold only; not counted as a live acquisition case.",
            "- `harvested` and `draft`: acquisition-stage cases. They must carry a checked-in source document, but raw upstream snapshots can still be deferred.",
            "- `validated`: provenance-hardened case. It must carry both the checked-in source document and at least one raw upstream snapshot artifact.",
            "- `gold_candidate`: review-ready benchmark candidate. It must satisfy validated provenance requirements and carry candidate-preparation metadata, but it is not benchmark-final yet.",
            "- `gold`: benchmark-stage case. It must satisfy validated provenance requirements and include review metadata.",
            "",
            "### Recent Outcomes",
            "",
            "| run_id | timestamp | cases_total | validation_status | source_family | kept | description |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )

    for row in run_log["recent_runs"]:
        lines.append(
            "| {run_id} | {timestamp} | {cases_total} | {validation_status} | {source_family} | {kept} | {description} |".format(
                run_id=row["run_id"],
                timestamp=row["timestamp"],
                cases_total=row["cases_total"],
                validation_status=row["validation_status"],
                source_family=row["source_family"],
                kept=row["kept"],
                description=_truncate_text(row["description"], 160).replace("|", "\\|"),
            )
        )

    lines.extend(
        [
            "",
            "### Case Growth",
            "",
            "| run_id | timestamp | cases_total | case_delta | source_family | change_kind |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in run_log["case_growth_events"]:
        lines.append(
            f"| {row['run_id']} | {row['timestamp']} | {row['cases_total']} | {row['case_delta']} | {row['source_family']} | {row['change_kind']} |"
        )
    if not run_log["case_growth_events"]:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a |")

    lines.extend(
        [
            "",
            "## Status Surface Rules",
            "",
            "- `auto-dataset summary` is the machine-readable live count source.",
            "- This dashboard is the human-readable live status source.",
            "- `datasets/public-validation-v1/manifest.yaml` is the source of truth for operating contract and targets.",
            "- `docs/roadmap.md` is the source of truth for phase narrative, not live telemetry.",
            "- Case-level language coverage is measured from `source_languages`; source-level language coverage is measured from `sources[].language`.",
            "",
        ]
    )

    return "\n".join(lines)


def _format_counts(values: dict[str, int]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in values.items())


def render_agent_brief(manifest: dict[str, Any], cases: list[dict[str, Any]], mode: str | None = None) -> str:
    autonomous_loop = manifest.get("autonomous_loop")
    if not autonomous_loop:
        raise ValidationError("manifest is missing autonomous_loop")

    selected_mode, mode_config = resolve_loop_mode(manifest, mode)
    run_budget = autonomous_loop["run_budget"]
    batch_size = autonomous_loop["batch_size"]
    logging = autonomous_loop["logging"]
    failure_policy = autonomous_loop["failure_policy"]
    family_balance = autonomous_loop["family_balance"]
    family_acquisition_strategies = autonomous_loop["family_acquisition_strategies"]
    summary = summarize_cases(cases)
    objective = " ".join(str(manifest["objective"]).split())
    mutable_paths = list(mode_config.get("mutable_paths", autonomous_loop["mutable_paths"]))
    frozen_paths = list(mode_config.get("frozen_paths", autonomous_loop["frozen_paths"]))
    daily_loop = list(mode_config.get("daily_loop", autonomous_loop["daily_loop"]))
    keep_if = [*autonomous_loop["keep_if"], *mode_config.get("keep_if", [])]
    discard_if = [*autonomous_loop["discard_if"], *mode_config.get("discard_if", [])]
    source_family_targets = manifest.get("source_family_targets", {})
    source_family_balance = summarize_source_family_balance(manifest, cases)

    lines = [
        f"Suite: {manifest['suite_id']}",
        f"Mission: {objective}",
        f"Loop Mode: {selected_mode}",
        f"Mode Goal: {mode_config['goal']}",
        f"Mode Description: {mode_config['description']}",
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
    lines.extend(f"- {path}" for path in mutable_paths)
    lines.extend(["", "Frozen Surface"])
    lines.extend(f"- {path}" for path in frozen_paths)
    prompt_rules = mode_config.get("prompt_rules", [])
    if prompt_rules:
        lines.extend(["", "Mode Rules"])
        lines.extend(f"- {rule}" for rule in prompt_rules)
    lines.extend(["", "Priority Order"])
    lines.extend(
        f"{index}. {priority['source_family']}: {priority['goal']}"
        for index, priority in enumerate(autonomous_loop["priorities"], start=1)
    )

    target_counts = manifest.get("target_counts", {})
    language_targets = manifest.get("language_targets", {})
    if target_counts:
        lines.extend(["", "Coverage Targets"])
        lines.extend(f"- {label}: {target}" for label, target in target_counts.items())
    if language_targets:
        lines.extend(["", "Language Targets"])
        lines.extend(f"- {label}: {target}" for label, target in language_targets.items())
    if source_family_targets:
        lines.extend(["", "Source Family Targets"])
        lines.extend(f"- {label}: {target}" for label, target in source_family_targets.items())

    lines.extend(
        [
            "",
            "Current Baseline",
            f"- cases total: {summary['cases_total']}",
            f"- task types: {_format_counts(summary['by_task_type'])}",
            f"- answer modes: {_format_counts(summary['by_answer_mode'])}",
            f"- source families: {_format_counts(summary['by_source_family'])}",
            f"- statuses: {_format_counts(summary['by_status'])}",
            f"- pipeline stages: {_format_counts(summary['by_pipeline_stage'])}",
            f"- case source languages: {_format_counts(summary['by_case_source_language'])}",
            f"- source record languages: {_format_counts(summary['by_source_record_language'])}",
            f"- multilingual cases: {summary['multilingual_cases_total']}",
            f"- overrepresented families: {_format_counts({family: summary['by_source_family'].get(family, 0) for family in source_family_balance['overrepresented_families']})}",
            f"- underrepresented families: {_format_counts({family: summary['by_source_family'].get(family, 0) for family in source_family_balance['underrepresented_families']})}",
            "",
            "Family Balance Policy",
        ]
    )
    lines.extend(
        f"- {family}: max {value:.0%} share"
        for family, value in family_balance["max_share_by_source_family"].items()
    )
    lines.extend(
        [
            f"- underrepresented families to prioritize: {', '.join(family_balance['underrepresented_families'])}",
            (
                "- reject acquisition if capped family share is exceeded: "
                f"{family_balance['reject_acquisition_if_family_above_max_share']}"
            ),
            "",
            "Family Acquisition Strategies",
        ]
    )
    for family_name, strategy in family_acquisition_strategies.items():
        lines.extend(
            [
                f"- {family_name}: {strategy['acquisition_method']}",
                f"  search rule: {strategy['search_rule']}",
                f"  preservation rule: {strategy['preservation_rule']}",
            ]
        )
    lines.extend(
        [
            "",
            "Daily Loop",
        ]
    )
    lines.extend(f"{index}. {step}" for index, step in enumerate(daily_loop, start=1))
    lines.extend(["", "Keep If"])
    lines.extend(f"- {rule}" for rule in keep_if)
    lines.extend(["", "Discard If"])
    lines.extend(f"- {rule}" for rule in discard_if)
    lines.extend(
        [
            "",
            "Failure Policy",
            f"- retryable statuses: {', '.join(failure_policy['retryable_statuses'])}",
            (
                "- max consecutive retryable failures: "
                f"{failure_policy['max_consecutive_retryable_failures']}"
            ),
            f"- stop on nonretryable failure: {failure_policy['stop_on_nonretryable_failure']}",
        ]
    )
    lines.extend(
        [
            "",
            "Run Log",
            f"- {logging['results_path']}",
            f"- columns: {', '.join(REQUIRED_RUN_LOG_COLUMNS)}",
        ]
    )
    return "\n".join(lines)
