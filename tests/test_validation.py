from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from auto_dataset.cli import main as cli_main  # noqa: E402
from auto_dataset.publishing import build_intermediate_snapshot  # noqa: E402
from auto_dataset.runner import RunnerError, _build_worker_prompt, run_autonomous_loop  # noqa: E402
from auto_dataset.validation import (  # noqa: E402
    REQUIRED_RUN_LOG_COLUMNS,
    ValidationError,
    load_suite,
    render_suite_dashboard,
    summarize_cases,
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ValidationTests(unittest.TestCase):
    def test_bootstrap_manifest_loads(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        manifest, cases = load_suite(manifest_path)

        self.assertEqual(manifest["suite_id"], "public-validation-v1")
        self.assertEqual(len(cases), len(manifest["case_files"]))
        self.assertGreaterEqual(len(cases), 5)
        self.assertEqual(manifest["autonomous_loop"]["duration_days"], 21)
        self.assertEqual(manifest["autonomous_loop"]["default_mode"], "acquisition")
        self.assertIn("language_targets", manifest)
        self.assertIn("source_family_targets", manifest)
        self.assertIn("family_balance", manifest["autonomous_loop"])
        self.assertIn("family_acquisition_strategies", manifest["autonomous_loop"])
        self.assertEqual(
            tuple(manifest["autonomous_loop"]["logging"]["required_columns"]),
            REQUIRED_RUN_LOG_COLUMNS,
        )

    def test_summary_counts_answer_modes(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        _, cases = load_suite(manifest_path)
        summary = summarize_cases(cases)

        self.assertEqual(summary["cases_total"], len(cases))
        self.assertEqual(sum(summary["by_task_type"].values()), len(cases))
        self.assertEqual(sum(summary["by_answer_mode"].values()), len(cases))
        self.assertEqual(sum(summary["by_source_family"].values()), len(cases))
        self.assertIn("exact", summary["by_answer_mode"])
        self.assertIn("mixed", summary["by_answer_mode"])
        self.assertIn("rubric", summary["by_answer_mode"])
        self.assertIn("hardened", summary["by_pipeline_stage"])
        self.assertIn("template", summary["by_pipeline_stage"])
        self.assertIn("validated", summary["by_status"])
        self.assertIn("template", summary["by_status"])
        self.assertIn("en", summary["by_case_source_language"])
        self.assertIn("en", summary["by_answer_language"])
        self.assertGreaterEqual(summary["multilingual_cases_total"], 1)
        self.assertIn("journalist_style_case", summary["by_source_family"])
        self.assertIn("official_procurement", summary["by_source_family"])
        self.assertIn("public_documents_with_metadata", summary["by_source_family"])
        self.assertIn("public_entity_link_dataset", summary["by_source_family"])

    def test_summary_command_reports_gap_analysis_and_run_log_rollups(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        buffer = StringIO()

        with patch.object(sys, "argv", ["auto-dataset", "summary", str(manifest_path)]):
            with redirect_stdout(buffer):
                exit_code = cli_main()

        payload = yaml.safe_load(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["suite_id"], "public-validation-v1")
        self.assertIn("target_progress", payload)
        self.assertIn("language_target_progress", payload)
        self.assertIn("lifecycle", payload)
        self.assertIn("run_log", payload)
        self.assertIn("gap_analysis", payload)
        self.assertIn("accepted_by_source_family", payload["run_log"])
        self.assertIn("effort_proxy_counts", payload["run_log"])
        self.assertIn("recommended_next_actions", payload["gap_analysis"])
        self.assertIn("gold_candidate", [row["status"] for row in payload["lifecycle"]["status_rows"]])

    def test_brief_command_renders_autonomous_loop(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        buffer = StringIO()

        with patch.object(sys, "argv", ["auto-dataset", "brief", str(manifest_path)]):
            with redirect_stdout(buffer):
                exit_code = cli_main()

        brief = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Timebox", brief)
        self.assertIn("21 days", brief)
        self.assertIn("4-8 cases per run", brief)
        self.assertIn("results/runs.tsv", brief)
        self.assertIn("Loop Mode: acquisition", brief)
        self.assertIn("Language Targets", brief)
        self.assertIn("case source languages", brief)
        self.assertIn("Source Family Targets", brief)
        self.assertIn("Family Balance Policy", brief)
        self.assertIn("Family Acquisition Strategies", brief)

    def test_brief_command_accepts_explicit_mode(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        buffer = StringIO()

        with patch.object(sys, "argv", ["auto-dataset", "brief", str(manifest_path), "--mode", "hardening"]):
            with redirect_stdout(buffer):
                exit_code = cli_main()

        brief = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Loop Mode: hardening", brief)
        self.assertIn("Mode Goal: Promote harvested and draft cases into validated cases", brief)

    def test_dashboard_command_renders_markdown_status_surface(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        buffer = StringIO()

        with patch.object(sys, "argv", ["auto-dataset", "dashboard", str(manifest_path)]):
            with redirect_stdout(buffer):
                exit_code = cli_main()

        dashboard = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("# public-validation-v1 Status Dashboard", dashboard)
        self.assertIn("Target Progress", dashboard)
        self.assertIn("Run Log", dashboard)
        self.assertIn("phase_2_in_progress", dashboard)
        self.assertIn("default loop mode: `acquisition`", dashboard)
        self.assertIn("failure classes:", dashboard)
        self.assertIn("Language Coverage", dashboard)
        self.assertIn("Language Target Progress", dashboard)
        self.assertIn("Source Family Balance", dashboard)
        self.assertIn("Source Family Target Progress", dashboard)

    def test_render_suite_dashboard_flags_overrepresented_procurement_family(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        manifest, cases = load_suite(manifest_path)

        dashboard = render_suite_dashboard(manifest_path, manifest, cases)

        self.assertIn("overrepresented families: official_procurement=58", dashboard)
        self.assertIn("underrepresented families:", dashboard)

    def test_render_suite_dashboard_mentions_status_surface_rules(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        manifest, cases = load_suite(manifest_path)

        dashboard = render_suite_dashboard(manifest_path, manifest, cases)

        self.assertIn("Status Surface Rules", dashboard)
        self.assertIn("auto-dataset summary", dashboard)
        self.assertIn("docs/roadmap.md", dashboard)

    def test_runner_prompt_overrides_log_and_publish_steps(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        manifest, cases = load_suite(manifest_path)

        prompt = _build_worker_prompt(
            PROJECT_ROOT,
            manifest_path,
            manifest,
            cases,
            run_number=1,
            max_runs=1,
        )

        self.assertIn("Treat any brief steps about run-log appends or publishing as runner-owned", prompt)
        self.assertIn("Do not append to results/runs.tsv", prompt)
        self.assertIn("Do not run auto-dataset publish, git commit, git push, or Hugging Face publish", prompt)
        self.assertIn("Loop mode: acquisition", prompt)

    def test_export_builds_intermediate_snapshot(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        manifest, cases = load_suite(manifest_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_dir = build_intermediate_snapshot(manifest_path, manifest, cases, Path(tmpdir))

            self.assertTrue((snapshot_dir / "README.md").exists())
            self.assertTrue((snapshot_dir / "summary.json").exists())
            self.assertTrue((snapshot_dir / "readiness.json").exists())
            self.assertTrue((snapshot_dir / "brief.txt").exists())
            self.assertTrue((snapshot_dir / "source_documents" / "index.json").exists())
            self.assertTrue(
                (snapshot_dir / "datasets" / "cases" / "structured-public-record-template.yaml").exists()
            )
            self.assertTrue(
                (snapshot_dir / "datasets" / "cases" / "structured-public-record-espo-509-19-lot-3.yaml").exists()
            )
            self.assertTrue(
                (snapshot_dir / "source_documents" / "cases" / "structured-public-record-template.md").exists()
            )
            self.assertTrue(
                (
                    snapshot_dir
                    / "datasets"
                    / "public-validation-v1"
                    / "source_documents"
                    / "structured-public-record-template.md"
                ).exists()
            )
            self.assertTrue(
                (
                    snapshot_dir
                    / "datasets"
                    / "public-validation-v1"
                    / "source_artifacts"
                    / "structured-public-record-espo-509-19-lot-3"
                    / "source-01-ted-notice-xml-205756-2019.xml"
                ).exists()
            )
            self.assertTrue((snapshot_dir / "rubrics" / "citation-grounding.md").exists())
            readme = (snapshot_dir / "README.md").read_text(encoding="utf-8")
            self.assertTrue(readme.startswith("---\n"))
            self.assertIn("task_categories:", readme)
            self.assertIn("# public-validation-v1", readme)
            self.assertIn("source_documents/", readme)
            self.assertIn("source_artifacts/", readme)
            self.assertIn("readiness.json", readme)
            self.assertIn("default downstream-eval statuses", readme)
            readiness = yaml.safe_load((snapshot_dir / "readiness.json").read_text(encoding="utf-8"))
            self.assertEqual(readiness["publish_policy"]["default_consumption_statuses"], ["validated", "gold"])
            self.assertIn("gold_candidate", readiness["publish_policy"]["included_statuses"])
            self.assertEqual(readiness["lifecycle"]["evaluation_ready_cases_total"], 60)
            self.assertEqual(readiness["lifecycle"]["benchmark_queue_cases_total"], 0)
            summary_payload = yaml.safe_load((snapshot_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertIn("gap_analysis", summary_payload)
            self.assertIn("lifecycle", summary_payload)
            source_index = yaml.safe_load((snapshot_dir / "source_documents" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(source_index["structured-public-record-template"]["status"], "template")
            self.assertFalse(source_index["structured-public-record-template"]["evaluation_ready"])
            self.assertEqual(source_index["structured-public-record-espo-509-19-lot-3"]["status"], "validated")
            self.assertTrue(source_index["structured-public-record-espo-509-19-lot-3"]["evaluation_ready"])

    def test_load_suite_rejects_missing_declared_evidence_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "structured-public-record-template.yaml"
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["evidence_bundle"]["artifacts"] = [
                {
                    "id": "source_record_file",
                    "path": "artifacts/source-docs/missing.xml",
                    "role": "source_document",
                    "media_type": "application/xml",
                    "source_url": "https://example.org/missing.xml",
                    "collected_at": "2026-03-23",
                    "original_filename": "missing.xml",
                    "sha256": "0" * 64,
                    "acquisition_method": "Download the source file from the listed URL.",
                    "license": "Unknown; verify upstream terms before redistribution.",
                    "source_dataset": "test fixture",
                    "notes": "Validation fixture for a missing artifact path.",
                }
            ]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("evidence_bundle.artifacts[1].path does not exist", str(exc.exception))

    def test_load_suite_rejects_case_without_content_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "followup-gold-template.yaml"
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            del case_payload["evidence_bundle"]["content_markdown"]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("evidence_bundle missing required keys: content_markdown", str(exc.exception))

    def test_load_suite_rejects_case_without_source_languages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "followup-gold-template.yaml"
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            del case_payload["source_languages"]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("missing required keys: source_languages", str(exc.exception))

    def test_load_suite_rejects_source_without_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "followup-gold-template.yaml"
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            del case_payload["sources"][0]["language"]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("missing required keys: language", str(exc.exception))

    def test_load_suite_rejects_case_without_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "followup-gold-template.yaml"
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            del case_payload["evidence_bundle"]["artifacts"]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("evidence_bundle missing required keys: artifacts", str(exc.exception))

    def test_load_suite_rejects_non_template_case_without_original_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "structured-public-record-espo-509-19-lot-3.yaml"
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["evidence_bundle"]["artifacts"] = [
                artifact
                for artifact in case_payload["evidence_bundle"]["artifacts"]
                if artifact.get("role") == "source_document"
            ]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("validated cases must include an original_source_snapshot artifact", str(exc.exception))
            self.assertIn("downgrade the case to harvested/draft", str(exc.exception))

    def test_load_suite_allows_harvested_case_without_original_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = (
                project_copy
                / "datasets"
                / "public-validation-v1"
                / "cases"
                / "structured-public-record-espo-509-19-lot-3.yaml"
            )
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["status"] = "harvested"
            case_payload["evidence_bundle"]["artifacts"] = [
                artifact
                for artifact in case_payload["evidence_bundle"]["artifacts"]
                if artifact.get("role") == "source_document"
            ]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            manifest, cases = load_suite(manifest_path)

            self.assertEqual(manifest["suite_id"], "public-validation-v1")
            self.assertTrue(any(case["status"] == "harvested" for case in cases))

    def test_load_suite_allows_draft_case_without_original_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = (
                project_copy
                / "datasets"
                / "public-validation-v1"
                / "cases"
                / "structured-public-record-espo-509-19-lot-3.yaml"
            )
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["status"] = "draft"
            case_payload["evidence_bundle"]["artifacts"] = [
                artifact
                for artifact in case_payload["evidence_bundle"]["artifacts"]
                if artifact.get("role") == "source_document"
            ]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            manifest, cases = load_suite(manifest_path)

            self.assertEqual(manifest["suite_id"], "public-validation-v1")
            self.assertTrue(any(case["status"] == "draft" for case in cases))

    def test_load_suite_rejects_invalid_case_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = (
                project_copy / "datasets" / "public-validation-v1" / "cases" / "structured-public-record-template.yaml"
            )
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["status"] = "finished"
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("invalid status 'finished'", str(exc.exception))

    def test_load_suite_rejects_gold_case_without_review_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = (
                project_copy
                / "datasets"
                / "public-validation-v1"
                / "cases"
                / "structured-public-record-espo-509-19-lot-3.yaml"
            )
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["status"] = "gold"
            case_payload.pop("review", None)
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("gold cases must include review metadata", str(exc.exception))

    def test_load_suite_rejects_gold_candidate_without_review_candidate_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = (
                project_copy
                / "datasets"
                / "public-validation-v1"
                / "cases"
                / "structured-public-record-espo-509-19-lot-3.yaml"
            )
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["status"] = "gold_candidate"
            case_payload.pop("review_candidate", None)
            case_payload.pop("review", None)
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("gold_candidate cases must include review_candidate metadata", str(exc.exception))

    def test_load_suite_allows_gold_candidate_with_review_candidate_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = (
                project_copy
                / "datasets"
                / "public-validation-v1"
                / "cases"
                / "structured-public-record-espo-509-19-lot-3.yaml"
            )
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["status"] = "gold_candidate"
            case_payload["review_candidate"] = {
                "prepared_by": "dataset-agent",
                "prepared_on": "2026-03-23",
                "rationale": "Prepared for later human review when reviewer capacity becomes available.",
            }
            case_payload.pop("review", None)
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            manifest, cases = load_suite(manifest_path)

            self.assertEqual(manifest["suite_id"], "public-validation-v1")
            self.assertTrue(any(case["status"] == "gold_candidate" for case in cases))

    def test_load_suite_rejects_cross_country_case_with_one_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = (
                project_copy / "datasets" / "public-validation-v1" / "cases" / "leak-coverage-comparison-template.yaml"
            )
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["source_languages"] = ["en"]
            case_payload["evidence_languages"] = ["en"]
            for source in case_payload["sources"]:
                source["language"] = "en"
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("cross_country_leak_reporting cases must declare at least two source_languages", str(exc.exception))

    def test_load_suite_rejects_artifact_with_bad_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            source_artifact = project_copy / "artifacts" / "source-docs" / "sample-source.xml"
            source_artifact.parent.mkdir(parents=True, exist_ok=True)
            source_artifact.write_text("<root>sample</root>\n", encoding="utf-8")

            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "structured-public-record-template.yaml"
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["evidence_bundle"]["artifacts"] = [
                {
                    "id": "source_record_file",
                    "path": "artifacts/source-docs/sample-source.xml",
                    "role": "source_document",
                    "media_type": "application/xml",
                    "source_url": "https://example.org/sample-source.xml",
                    "collected_at": "2026-03-23",
                    "original_filename": "sample-source.xml",
                    "sha256": "f" * 64,
                    "acquisition_method": "Download the source file from the listed URL.",
                    "license": "Unknown; verify upstream terms before redistribution.",
                    "source_dataset": "test fixture",
                    "notes": "Validation fixture for a mismatched digest.",
                }
            ]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("sha256 does not match", str(exc.exception))

    def test_export_copies_declared_evidence_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            source_artifact = project_copy / "artifacts" / "source-docs" / "sample-source.xml"
            source_artifact.parent.mkdir(parents=True, exist_ok=True)
            source_artifact.write_text("<root>sample</root>\n", encoding="utf-8")

            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "structured-public-record-template.yaml"
            case_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))
            case_payload["evidence_bundle"]["artifacts"] = [
                {
                    "id": "source_record_file",
                    "path": "artifacts/source-docs/sample-source.xml",
                    "role": "source_document",
                    "media_type": "application/xml",
                    "source_url": "https://example.org/sample-source.xml",
                    "collected_at": "2026-03-23",
                    "original_filename": "sample-source.xml",
                    "sha256": _sha256_text("<root>sample</root>\n"),
                    "acquisition_method": "Download the source file from the listed URL.",
                    "license": "Unknown; verify upstream terms before redistribution.",
                    "source_dataset": "test fixture",
                    "notes": "Validation fixture for artifact copy behavior.",
                }
            ]
            case_path.write_text(yaml.safe_dump(case_payload, sort_keys=False), encoding="utf-8")

            manifest, cases = load_suite(manifest_path)
            snapshot_dir = build_intermediate_snapshot(
                manifest_path,
                manifest,
                cases,
                project_copy / "artifacts" / "hf-staging",
            )

            copied_artifact = snapshot_dir / "artifacts" / "source-docs" / "sample-source.xml"
            self.assertTrue(copied_artifact.exists())
            self.assertEqual(copied_artifact.read_text(encoding="utf-8"), "<root>sample</root>\n")
            source_index = yaml.safe_load((snapshot_dir / "source_documents" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(
                source_index["structured-public-record-template"]["artifacts"][0]["path"],
                "artifacts/source-docs/sample-source.xml",
            )
            self.assertEqual(
                source_index["structured-public-record-template"]["artifacts"][0]["sha256"],
                _sha256_text("<root>sample</root>\n"),
            )

    def test_brief_includes_source_documents_mutable_path(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        buffer = StringIO()

        with patch.object(sys, "argv", ["auto-dataset", "brief", str(manifest_path), "--mode", "hardening"]):
            with redirect_stdout(buffer):
                exit_code = cli_main()

        brief = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Loop Mode: hardening", brief)
        self.assertIn("datasets/public-validation-v1/source_documents", brief)
        self.assertIn("datasets/public-validation-v1/source_artifacts", brief)

    def test_load_suite_rejects_orphan_case_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            orphan_case_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "orphan.yaml"
            template_path = project_copy / "datasets" / "public-validation-v1" / "cases" / "structured-public-record-template.yaml"
            orphan_case_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

            with self.assertRaises(ValidationError) as exc:
                load_suite(manifest_path)

            self.assertIn("case_files is missing declared entries", str(exc.exception))
            self.assertIn("cases/orphan.yaml", str(exc.exception))

    def test_run_executes_worker_cycle_and_logs_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            worker_command = (
                f"{sys.executable} -c "
                "\"from pathlib import Path; "
                "path = Path('docs/roadmap.md'); "
                "path.write_text(path.read_text(encoding='utf-8') + '\\n# runner test\\n', encoding='utf-8')\""
            )

            result = run_autonomous_loop(
                manifest_path,
                worker_command=worker_command,
                max_runs=1,
                publish_enabled=False,
                output_root=project_copy / "artifacts" / "hf-staging",
            )

            self.assertEqual(result["accepted_runs"], 1)
            self.assertEqual(result["published_runs"], 0)
            initial_runs = (PROJECT_ROOT / "results" / "runs.tsv").read_text(encoding="utf-8").strip().splitlines()
            runs_lines = (project_copy / "results" / "runs.tsv").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(runs_lines), len(initial_runs) + 1)
            self.assertIn("accepted autonomous batch", runs_lines[-1])
            self.assertIn("\tacquisition\t", runs_lines[-1])

    def test_run_retries_retryable_worker_failure_and_then_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            worker_command = (
                f"{sys.executable} -c "
                "\"from pathlib import Path; "
                "flag = Path('artifacts/retry-flag.txt'); "
                "path = Path('docs/roadmap.md'); "
                "flag.parent.mkdir(parents=True, exist_ok=True); "
                "import sys; "
                "flag.exists() or (flag.write_text('seen', encoding='utf-8'), sys.stderr.write('temporary environment issue\\n'), sys.exit(1)); "
                "path.write_text(path.read_text(encoding='utf-8') + '\\n# retry success\\n', encoding='utf-8')\""
            )

            result = run_autonomous_loop(
                manifest_path,
                mode="acquisition",
                worker_command=worker_command,
                max_runs=2,
                publish_enabled=False,
                output_root=project_copy / "artifacts" / "hf-staging",
            )

            self.assertEqual(result["accepted_runs"], 1)
            runs_lines = (project_copy / "results" / "runs.tsv").read_text(encoding="utf-8").strip().splitlines()
            self.assertIn("\tworker_failed\t", runs_lines[-2])
            self.assertIn("\tacquisition\t", runs_lines[-2])
            self.assertIn("\tok\t", runs_lines[-1])

    def test_run_rejects_orphan_case_file_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project"
            shutil.copytree(
                PROJECT_ROOT,
                project_copy,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc", "artifacts"),
            )
            manifest_path = project_copy / "datasets" / "public-validation-v1" / "manifest.yaml"
            worker_command = (
                f"{sys.executable} -c "
                "\"from pathlib import Path; "
                "src = Path('datasets/public-validation-v1/cases/structured-public-record-template.yaml'); "
                "dst = Path('datasets/public-validation-v1/cases/orphan.yaml'); "
                "dst.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')\""
            )

            with self.assertRaises(RunnerError) as exc:
                run_autonomous_loop(
                    manifest_path,
                    worker_command=worker_command,
                    max_runs=1,
                    publish_enabled=False,
                    output_root=project_copy / "artifacts" / "hf-staging",
                )

            self.assertIn("case_files is missing declared entries", str(exc.exception))
            initial_runs = (PROJECT_ROOT / "results" / "runs.tsv").read_text(encoding="utf-8").strip().splitlines()
            runs_lines = (project_copy / "results" / "runs.tsv").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(runs_lines), len(initial_runs) + 1)
            self.assertIn("\tfailed\t", runs_lines[-1])


if __name__ == "__main__":
    unittest.main()
