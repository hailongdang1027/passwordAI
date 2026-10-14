"""Tests for static generator analysis only (no password guess ranking)."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import handle
import main
from core_ai import analyze_core_source, format_core_analysis


class CoreAIAnalysisTests(unittest.TestCase):
    def setUp(self):
        handle.read_config("rules.cfg")
        self.source = Path(__file__).with_name("handle.py")

    def test_reads_real_core_strategies(self):
        analysis = analyze_core_source(self.source)
        keys = {strategy.key for strategy in analysis.strategies}
        self.assertGreaterEqual(len(analysis.functions), 15)
        self.assertTrue({"NORMALIZE_CASE", "NAME_VARIANTS", "DATE_VARIANTS", "OUTPUT_FILTER"} <= keys)
        self.assertEqual(len(analysis.source_sha256), 64)
        self.assertEqual(analysis.source_sha256, hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_analysis_is_based_on_ast_and_does_not_store_raw_source(self):
        analysis = analyze_core_source(self.source)
        self.assertFalse(hasattr(analysis, "source"))
        rendered = format_core_analysis(analysis)
        self.assertIn("handle.py", rendered)
        self.assertIn("Biến thể tên", rendered)
        self.assertNotIn("Nguyen Van An", rendered)

    def test_missing_signatures_are_not_reported_as_real_strategies(self):
        source = "def generate_basic_wordlist():\n    return []\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handle.py"
            path.write_text(source, encoding="utf-8")
            analysis = analyze_core_source(path)
        self.assertEqual(analysis.functions, ("generate_basic_wordlist",))
        self.assertEqual(analysis.strategies, ())

    def test_gui_analysis_callback_renders_report(self):
        with patch.object(main, "txt_core_analysis", Mock(), create=True), \
                patch.object(main, "lbl_core_ai_status", Mock(), create=True), \
                patch.object(main, "pipeline_logger"):
            main.show_core_ai_analysis()
            main.txt_core_analysis.config.assert_any_call(state=main.tk.NORMAL)
            main.txt_core_analysis.insert.assert_called_once()
            main.txt_core_analysis.config.assert_any_call(state=main.tk.DISABLED)
            main.lbl_core_ai_status.config.assert_called_once()


if __name__ == "__main__":
    unittest.main()
