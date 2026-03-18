from __future__ import annotations

import sys
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
from auto_dataset.validation import REQUIRED_RUN_LOG_COLUMNS, load_suite, summarize_cases  # noqa: E402


class ValidationTests(unittest.TestCase):
    def test_bootstrap_manifest_loads(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        manifest, cases = load_suite(manifest_path)

        self.assertEqual(manifest["suite_id"], "public-validation-v1")
        self.assertEqual(len(cases), 4)
        self.assertEqual(manifest["autonomous_loop"]["duration_days"], 7)
        self.assertEqual(
            tuple(manifest["autonomous_loop"]["logging"]["required_columns"]),
            REQUIRED_RUN_LOG_COLUMNS,
        )

    def test_summary_counts_answer_modes(self) -> None:
        manifest_path = PROJECT_ROOT / "datasets" / "public-validation-v1" / "manifest.yaml"
        _, cases = load_suite(manifest_path)
        summary = summarize_cases(cases)

        self.assertEqual(summary["cases_total"], 4)
        self.assertEqual(summary["by_answer_mode"]["exact"], 2)
        self.assertEqual(summary["by_answer_mode"]["mixed"], 1)
        self.assertEqual(summary["by_answer_mode"]["rubric"], 1)
        self.assertEqual(summary["by_source_family"]["journalist_style_case"], 1)

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


if __name__ == "__main__":
    unittest.main()
