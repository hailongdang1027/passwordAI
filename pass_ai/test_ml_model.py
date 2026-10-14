"""Supervised ML and data-leakage regression tests (no real passwords)."""
import csv
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import main
from feature_extractor import FEATURE_NAMES, extract_features
from ml_ranker import PasswordStrengthModel, read_labelled_csv, train_model

BASE = Path(__file__).resolve().parent
DATA = BASE / "examples" / "demo_labeled_synthetic.csv"


class PasswordModelTests(unittest.TestCase):
    def test_all_features_are_finite_and_empty_input_rejected(self):
        for password in ("a", "aaaaaaaa", "W0rds#4Test", "密码aĐ123!", "...."):
            row = extract_features(password)
            self.assertEqual(len(row), len(FEATURE_NAMES))
            self.assertTrue(all(math.isfinite(x) for x in row))
        with self.assertRaises(ValueError):
            extract_features("")

    def test_training_split_and_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            model_path = Path(folder) / "trained.json"
            metrics_path = Path(folder) / "evaluation.json"
            report = train_model(DATA, model_path, metrics_path, random_state=42)
            self.assertEqual(report["dataset"]["distinct_samples"], 144)
            self.assertEqual(report["dataset"]["group_leakage_check"],
                             "PASS: train/validation/test group_id disjoint")
            self.assertEqual(sum(report["split"][key] for key in ("train", "validation", "test")), 144)
            self.assertGreater(report["test"]["count"], 0)
            self.assertIn("roc_auc", report["test"])
            self.assertEqual(len(report["test"]["confusion_matrix_weak_strong"]), 2)
            self.assertEqual(report, json.loads(metrics_path.read_text(encoding="utf-8")))

            trained = PasswordStrengthModel.load(model_path)
            prediction = trained.explain("Independent!Demo#Example123")
            self.assertTrue(0 <= prediction["probability_strong"] <= 1)
            self.assertEqual(trained.probability_strong("Independent!Demo#Example123"),
                             trained.probability_strong("Independent!Demo#Example123"))
            self.assertNotIn("Independent!Demo#Example123", repr(prediction))
            model_content = model_path.read_text(encoding="utf-8")
            report_content = metrics_path.read_text(encoding="utf-8")
            self.assertNotIn("weak-welcome", model_content)
            self.assertNotIn("weak-welcome", report_content)
            self.assertNotIn('"password":', model_content)
            self.assertNotIn('"password":', report_content)
            self.assertEqual(trained.feature_names, FEATURE_NAMES)

    def test_contributions_reconstruct_log_odds(self):
        model = PasswordStrengthModel.load(BASE / "examples" / "demo_model.json")
        pwd = "Checking!Test12"
        result = model.explain(pwd, top_n=len(FEATURE_NAMES))
        log_odds = model.intercept + sum(item["contribution_log_odds"] for item in result["contributions"])
        recon = 1 / (1 + math.exp(-log_odds))
        self.assertAlmostEqual(recon, result["probability_strong"], places=4)

    def test_duplicate_labels_and_imbalanced_data_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            path.write_text("password,label\nfoo,0\nfoo,1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mâu thuẫn"):
                read_labelled_csv(path)
            path.write_text("password,label\nfoo,0\nbar,1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "60 mẫu"):
                read_labelled_csv(path)

    def test_unlabelled_corpus_not_accepted(self):
        with self.assertRaises(ValueError):
            read_labelled_csv(BASE / "gui" / "wifi_vietnam.txt")

    def test_invalid_schema_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"schema_version":"wrong"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                PasswordStrengthModel.load(path)

    def test_single_gui_prediction_clears_input_and_does_not_log_secret(self):
        model = PasswordStrengthModel.load(BASE / "examples" / "demo_model.json")
        entry = Mock()
        entry.get.return_value = "GuiTesting#991"
        text = Mock()
        with patch.object(main, "entry_strength_password", entry, create=True), \
             patch.object(main, "txt_strength_explanation", text, create=True), \
             patch.object(main, "strength_model", model), \
             patch.object(main, "pipeline_logger") as logger:
            main.assess_single_password()
            entry.delete.assert_called_once_with(0, main.tk.END)
            text.insert.assert_called_once()
            self.assertNotIn("GuiTesting#991", text.insert.call_args.args[1])
            logger.log.assert_not_called()

    def test_no_hand_scoring_and_no_guess_ranking_in_api(self):
        import ml_ranker
        import core_ai
        self.assertFalse(hasattr(ml_ranker, "heuristic_score"))
        self.assertFalse(hasattr(core_ai, "CoreAIRanker"))


if __name__ == "__main__":
    unittest.main()
