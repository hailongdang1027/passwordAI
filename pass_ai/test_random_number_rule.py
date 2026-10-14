"""Regression tests for opt-in rule behavior, using synthetic profiles only."""

import os
import random
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

import handle
import main
from rules import RuleExecutor, RuleValidationError, get_available_rule_names
from rules.random_number_rule import DEFAULT_PARAMS, RULE_NAME, RandomNumberRule, profile_words


class RandomNumberRuleTests(unittest.TestCase):
    def setUp(self):
        handle.read_config("rules.cfg")
        self.profile = {"fullname": "An", "hometown": "Huế", "company": "ABC"}
        self.executor = RuleExecutor()

    def make_rule(self, **params):
        return RandomNumberRule(rng=random.Random(42), **params)

    def test_registry_and_defaults(self):
        self.assertIn(RULE_NAME, get_available_rule_names())
        rule = self.executor.validate_rule(RULE_NAME)
        self.assertEqual(rule.params, DEFAULT_PARAMS)
        self.assertIsNot(rule.params, DEFAULT_PARAMS)

    def test_normalized_sources_and_missing_fields(self):
        words = profile_words({
            "fullname": "Đỗ Minh An", "relative_name": "Bình", "child_name": "Chi",
            "hometown": "  Hà\tNội ", "company": "Công ty ABC",
            "birthdate": "01012000", "unrelated": "ignored",
        })
        self.assertTrue({"an", "minhan", "dominhan", "binh", "chi", "hanoi", "congtyabc"} <= words)
        self.assertNotIn("01012000", words)
        self.assertNotIn("ignored", words)
        self.assertEqual(profile_words({"fullname": None, "company": "  "}), set())

    def test_each_field_receives_digits(self):
        result = self.make_rule(min_digits=3, max_digits=3, count=4, position="suffix").generate(self.profile, 1, 30)
        self.assertEqual(len(result), 12)
        for word in ("an", "hue", "abc"):
            matches = [pw for pw in result if pw.startswith(word)]
            self.assertEqual(len(matches), 4)
            self.assertTrue(all(pw[len(word):].isascii() and pw[len(word):].isdigit() for pw in matches))

    def test_positions(self):
        for position in ("prefix", "suffix", "both"):
            with self.subTest(position=position):
                result = self.make_rule(min_digits=2, max_digits=2, count=4, position=position).generate({"fullname": "An"}, 1, 20)
                self.assertEqual(len(result), 8 if position == "both" else 4)
                if position == "prefix":
                    self.assertTrue(all(pw.endswith("an") and pw[:2].isdigit() for pw in result))
                elif position == "suffix":
                    self.assertTrue(all(pw.startswith("an") and pw[-2:].isdigit() for pw in result))
                else:
                    self.assertEqual({pw[:2] for pw in result if pw.endswith("an")},
                                     {pw[-2:] for pw in result if pw.startswith("an")})

    def test_each_digit_width_and_total_length_filter(self):
        result = self.make_rule(count=3, position="suffix").generate({"fullname": "An"}, 1, 20)
        self.assertEqual({size: sum(len(pw) == size for pw in result) for size in (4, 5, 6)}, {4: 3, 5: 3, 6: 3})
        filtered = self.make_rule(count=3).generate(self.profile, 5, 5)
        self.assertTrue(filtered)
        self.assertTrue(all(len(pw) == 5 for pw in filtered))
        self.assertEqual(self.make_rule().generate(self.profile, 20, 30), set())
        self.assertEqual(self.make_rule().generate({}, 1, 30), set())

    def test_unique_sampling_caps_at_available_numbers(self):
        result = self.make_rule(min_digits=1, max_digits=1, count=100, position="suffix").generate({"fullname": "An"}, 1, 20)
        self.assertEqual(result, {f"an{number}" for number in range(10)})

    def test_leading_zeroes_are_preserved(self):
        result = self.make_rule(min_digits=2, max_digits=2, count=100, position="suffix").generate({"fullname": "An"}, 1, 20)
        self.assertEqual(len(result), 100)
        self.assertIn("an00", result)
        self.assertIn("an07", result)

    def test_invalid_parameters_rejected_before_core_runs(self):
        invalid = [
            {"min_digits": 0}, {"max_digits": 9}, {"min_digits": 5, "max_digits": 2},
            {"count": 0}, {"count": 101}, {"count": 1.5}, {"count": True},
            {"count": "abc"}, {"count": ""}, {"count": "-1"},
            {"position": "middle"}, {"unknown": 1},
        ]
        for params in invalid:
            with self.subTest(params=params), patch("handle.generate_basic_wordlist") as core:
                with self.assertRaises(RuleValidationError):
                    self.executor.generate([
                        {"rule": "LÕI_CƠ_HỌC"}, {"rule": RULE_NAME, "params": params},
                    ], self.profile, 1, 30)
                core.assert_not_called()

    def test_gui_string_parameters_are_normalized(self):
        rule = self.executor.validate_rule(RULE_NAME, {"min_digits": " 1 ", "max_digits": "3", "count": "5"})
        self.assertEqual(rule.params, {"min_digits": 1, "max_digits": 3, "count": 5, "position": "both"})

    def test_invalid_output_lengths(self):
        for low, high in ((0, 10), (-1, 10), (8, 3), (1.5, 10), (True, 10)):
            with self.subTest(bounds=(low, high)), self.assertRaises(RuleValidationError):
                self.executor.generate([], self.profile, low, high)

    def test_disabled_rule_does_not_change_legacy_results(self):
        expected = handle.generate_basic_wordlist(self.profile, 1, 30)
        with patch("rules.executor.RandomNumberRule") as random_rule:
            self.assertEqual(self.executor.generate([], self.profile, 1, 30), expected)
            self.assertEqual(self.executor.generate([{"rule": "LÕI_CƠ_HỌC"}], self.profile, 1, 30), expected)
            random_rule.assert_not_called()

    def test_enabled_rule_adds_to_core_and_removal_restores_core(self):
        rules = [{"rule": "LÕI_CƠ_HỌC"}, {"rule": RULE_NAME}]
        base = set(handle.generate_basic_wordlist(self.profile, 1, 30))
        result = self.executor.generate(rules, self.profile, 1, 30)
        self.assertLess(base, set(result))
        self.assertEqual(result, sorted(set(result)))
        rules.pop()
        self.assertEqual(set(self.executor.generate(rules, self.profile, 1, 30)), base)

    def test_random_rule_can_run_independently(self):
        with patch("handle.generate_basic_wordlist") as core:
            result = self.executor.generate([{"rule": RULE_NAME}], self.profile, 1, 30)
            self.assertTrue(result)
            self.assertTrue(all(any(c.isdigit() for c in pw) for pw in result))
            core.assert_not_called()

    def test_os_randomness_and_no_global_seed_change(self):
        state = random.getstate()
        rule = RandomNumberRule()
        self.assertIsInstance(rule.rng, random.SystemRandom)
        rule.generate(self.profile, 1, 30)
        self.assertEqual(random.getstate(), state)


class RuleGuiCallbackTests(unittest.TestCase):
    """Exercise real callbacks without requiring a graphical display."""

    def setup_gui(self, stack):
        stack.enter_context(patch.object(main, "active_rules", []))
        stack.enter_context(patch.object(main, "pipeline_logger"))
        stack.enter_context(patch.object(main, "messagebox"))
        values = {
            "combo_rule": RULE_NAME, "entry_random_min": "2", "entry_random_max": "3",
            "entry_random_count": "4", "combo_random_position": "Sau", "entry_params": "",
        }
        for name, value in values.items():
            stack.enter_context(patch.object(main, name, Mock(get=Mock(return_value=value)), create=True))
        for name in ("listbox_rules", "frame_random_params", "lbl_rule_description"):
            stack.enter_context(patch.object(main, name, Mock(), create=True))

    def test_selection_add_and_remove(self):
        with ExitStack() as stack:
            self.setup_gui(stack)
            main.on_rule_selected()
            self.assertEqual(main.active_rules, [])  # selecting alone is not opt-in
            main.frame_random_params.grid.assert_called_once()
            main.add_rule()
            self.assertEqual(main.active_rules, [{"rule": RULE_NAME, "params": {
                "min_digits": 2, "max_digits": 3, "count": 4, "position": "suffix",
            }}])
            main.listbox_rules.curselection.return_value = (0,)
            main.remove_rule()
            self.assertEqual(main.active_rules, [])
            main.combo_rule.get.return_value = "LÕI_CƠ_HỌC"
            main.on_rule_selected()
            main.frame_random_params.grid_remove.assert_called_once()

    def test_invalid_gui_values_do_not_add_rule(self):
        with ExitStack() as stack:
            self.setup_gui(stack)
            main.entry_random_min.get.return_value = "5"
            main.add_rule()
            self.assertEqual(main.active_rules, [])
            main.messagebox.showerror.assert_called_once()

    def test_generate_callback_exports_selected_rule(self):
        with ExitStack() as stack, tempfile.TemporaryDirectory() as tmp:
            self.setup_gui(stack)
            main.add_rule()
            values = {
                "entry_fullname": "An", "entry_hometown": "Huế", "entry_company": "ABC",
                "entry_birthdate": "", "entry_relative_name": "", "entry_relative_birth": "",
                "entry_child_name": "", "entry_child_birth": "", "entry_wcfrom": "4", "entry_wcto": "5",
            }
            for name, value in values.items():
                stack.enter_context(patch.object(main, name, Mock(get=Mock(return_value=value)), create=True))
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                main.generate_wordlist_via_pipeline()
                files = list(Path("output").glob("*.txt"))
                self.assertEqual(len(files), 1)
                lines = files[0].read_text(encoding="utf-8").splitlines()
                self.assertTrue(lines)
                self.assertEqual(lines, sorted(set(lines)))
                self.assertTrue(all(4 <= len(pw) <= 5 and pw[-1].isdigit() for pw in lines))
                main.messagebox.showerror.assert_not_called()
                main.messagebox.showinfo.assert_called_once()
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
