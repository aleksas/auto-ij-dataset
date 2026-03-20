from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from auto_dataset.cli import main as cli_main  # noqa: E402
from auto_dataset.publishing import build_intermediate_snapshot  # noqa: E402
from auto_dataset.runner import RunnerError, _build_worker_prompt, run_autonomous_loop  # noqa: E402
from auto_dataset.validation import REQUIRED_RUN_LOG_COLUMNS, ValidationError, load_suite, summarize_cases  # noqa: E402


class ValidationTests(unittest.TestCase):
    def test_bootstrap_manifest_loads(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        manifest, cases = load_suite(manifest_path)

        self.assertEqual(manifest["suite_id"], "public-validation-v1")
        self.assertEqual(len(cases), len(manifest["case_files"]))
        self.assertGreaterEqual(len(cases), 5)
        self.assertEqual(manifest["autonomous_loop"]["duration_days"], 7)
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
        self.assertIn("journalist_style_case", summary["by_source_family"])
        self.assertIn("official_procurement", summary["by_source_family"])
        self.assertIn("public_documents_with_metadata", summary["by_source_family"])
        self.assertIn("public_entity_link_dataset", summary["by_source_family"])

    def test_brief_command_renders_autonomous_loop(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        buffer = StringIO()

        with patch.object(sys, "argv", ["auto-dataset", "brief", str(manifest_path)]):
            with redirect_stdout(buffer):
                exit_code = cli_main()

        brief = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Timebox", brief)
        self.assertIn("7 days", brief)
        self.assertIn("2-4 cases per run", brief)
        self.assertIn("results/runs.tsv", brief)

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

    def test_export_builds_intermediate_snapshot(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        manifest, cases = load_suite(manifest_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_dir = build_intermediate_snapshot(manifest_path, manifest, cases, Path(tmpdir))

            self.assertTrue((snapshot_dir / "README.md").exists())
            self.assertTrue((snapshot_dir / "summary.json").exists())
            self.assertTrue((snapshot_dir / "brief.txt").exists())
            self.assertTrue(
                (snapshot_dir / "datasets" / "cases" / "structured-public-record-template.yaml").exists()
            )
            self.assertTrue(
                (snapshot_dir / "datasets" / "cases" / "structured-public-record-espo-509-19-lot-3.yaml").exists()
            )
            self.assertTrue((snapshot_dir / "rubrics" / "citation-grounding.md").exists())
            readme = (snapshot_dir / "README.md").read_text(encoding="utf-8")
            self.assertTrue(readme.startswith("---\n"))
            self.assertIn("task_categories:", readme)
            self.assertIn("# public-validation-v1", readme)

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
