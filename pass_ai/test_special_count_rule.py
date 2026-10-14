"""Count constraints, pipeline integration and GUI callbacks; synthetic inputs."""
import json
import os
import random
import tempfile
import unittest
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

import handle
import main
from rules import RuleExecutor, RuleValidationError
from rules.special_count_rule import RULE_NAME, SpecialCountRule, count_specials, validate_params


class SpecialCountTests(unittest.TestCase):
    def setUp(self):
        handle.read_config("rules.cfg")
        self.executor = RuleExecutor()

    def test_one_symbol_can_appear_at_every_gap(self):
        base = "hailongdang"
        values = SpecialCountRule(counts=[1], characters="@", position="any", samples=100).apply([base], 1, 30)
        self.assertEqual(values, {base[:i] + "@" + base[i:] for i in range(len(base) + 1)})
        self.assertIn("hailong@dang", values)
        self.assertIn("hailongdang@", values)

    def test_two_symbols_include_internal_repeated_and_boundary_positions(self):
        values = SpecialCountRule(counts=[2], characters="@", position="any", samples=100).apply(["ab"], 1, 10)
        self.assertEqual(values, {"@@ab", "@a@b", "@ab@", "a@@b", "a@b@", "ab@@"})

    def test_multiple_counts_are_union_not_maximum(self):
        values = SpecialCountRule(counts=[3, 1, 2, 2], characters="@!").apply(["demo"], 1, 30)
        self.assertEqual({count_specials(p) for p in values}, {1, 2, 3})
        self.assertEqual(validate_params({"counts": [3, "1", 2, 2]})["counts"], [1, 2, 3])

    def test_existing_marks_are_replaced_not_added_and_case_is_retained(self):
        rule = SpecialCountRule(counts=[2], characters="@", position="edges", samples=100)
        values = rule.apply(["Demo_20!", "Demo20", "D.e.m.o20", "@@@"], 1, 30)
        self.assertEqual(values, {"@@Demo20", "@Demo20@", "Demo20@@"})
        self.assertTrue(all(count_specials(p) == 2 for p in values))

    def test_zero_optional_count_and_length_bounds(self):
        rule = SpecialCountRule(counts=[0, 1, 2, 4], characters="@", position="edges")
        self.assertEqual(rule.apply(["ab"], 2, 2), {"ab"})
        self.assertEqual({len(p) for p in rule.apply(["ab"], 4, 4)}, {4})
        self.assertEqual(rule.apply(["ab"], 10, 12), set())
        self.assertEqual(rule.apply([], 1, 20), set())

    def test_default_priority_has_majority_at_edges_when_space_allows(self):
        values = SpecialCountRule(counts=[2], characters="@!#", samples=24).apply(["demo"], 1, 30)
        self.assertEqual(len(values), 24)
        self.assertEqual(sum("demo" in p for p in values), 17)

    def test_exact_bounded_reproducible_results_without_global_rng_changes(self):
        state = random.getstate()
        rule = SpecialCountRule(counts=[1, 3], samples=10)
        first = rule.apply(["demo"], 1, 30)
        self.assertEqual(first, rule.apply(["demo"], 1, 30))
        self.assertEqual(Counter(map(count_specials, first)), {1: 10, 3: 10})
        self.assertEqual(state, random.getstate())

    def test_large_count_does_not_overflow_sampling_range(self):
        values = SpecialCountRule(counts=[64], samples=1, position="edges").apply(["ab"], 1, 100)
        self.assertEqual(len(values), 1)
        self.assertEqual({count_specials(p) for p in values}, {64})

    def test_invalid_values_fail_before_generation(self):
        invalid = [
            {"counts": []}, {"counts": "1,2"}, {"counts": [True]}, {"counts": [-1]},
            {"counts": [65]}, {"counts": [1.5]}, {"characters": ""}, {"characters": "@a"},
            {"characters": "@ "}, {"samples": 0}, {"samples": 101}, {"samples": True},
            {"position": "wrong"}, {"bad": 1},
        ]
        for params in invalid:
            with self.subTest(params=params), patch("handle.generate_basic_wordlist") as core:
                with self.assertRaises(RuleValidationError):
                    self.executor.generate([{"rule": RULE_NAME, "params": params}], {"fullname": "An"}, 1, 30)
                core.assert_not_called()

    def test_short_bases_reach_min_length_after_insertion(self):
        values = self.executor.generate([{"rule": RULE_NAME, "params": {"counts": [2], "characters": "@"}}],
                                        {"fullname": "An"}, 4, 4)
        self.assertTrue(values)
        self.assertTrue(all(len(p) == 4 and count_specials(p) == 2 for p in values))
        self.assertIn("an@@", values)

    def test_count_rule_is_final_regardless_of_list_position(self):
        special = {"rule": RULE_NAME, "params": {"counts": [1, 3], "characters": "@"}}
        core = {"rule": "LÕI_CƠ_HỌC"}
        a = self.executor.generate([special, core], {"fullname": "Demo"}, 1, 20)
        b = self.executor.generate([core, special], {"fullname": "Demo"}, 1, 20)
        self.assertEqual(a, b)
        self.assertEqual({count_specials(p) for p in a}, {1, 3})

    def test_other_rules_cannot_bypass_final_constraint(self):
        values = self.executor.generate([
            {"rule": "LÕI_CƠ_HỌC"},
            {"rule": "GHÉP_SỐ_NGẪU_NHIÊN", "params": {"count": 2}},
            {"rule": RULE_NAME, "params": {"counts": [4], "samples": 2}},
        ], {"fullname": "An"}, 6, 12)
        self.assertTrue(values)
        self.assertTrue(all(count_specials(p) == 4 and 6 <= len(p) <= 12 for p in values))
        self.assertEqual(values, sorted(set(values)))

    def test_removing_rule_restores_legacy_and_duplicates_rejected(self):
        profile = {"fullname": "An"}
        self.assertEqual(self.executor.generate([], profile, 1, 20), handle.generate_basic_wordlist(profile, 1, 20))
        with self.assertRaisesRegex(RuleValidationError, "Chỉ dùng một"):
            self.executor.generate([{"rule": RULE_NAME}, {"rule": RULE_NAME}], profile, 1, 20)


class SpecialGuiTests(unittest.TestCase):
    def setup_ui(self, stack):
        stack.enter_context(patch.object(main, "active_rules", []))
        stack.enter_context(patch.object(main, "pipeline_logger"))
        stack.enter_context(patch.object(main, "messagebox"))
        stack.enter_context(patch.object(main, "special_count_rows", [(Mock(), Mock(get=Mock(return_value="2"))),
                                                                     (Mock(), Mock(get=Mock(return_value="1")))]))
        for name in ("frame_special_params", "frame_random_params", "lbl_rule_description", "listbox_rules"):
            stack.enter_context(patch.object(main, name, Mock(), create=True))
        for name, value in {
            "combo_rule": RULE_NAME, "entry_special_characters": "@!", "combo_special_position": "Bất kỳ vị trí",
            "entry_special_samples": "24", "entry_params": "",
        }.items():
            stack.enter_context(patch.object(main, name, Mock(get=Mock(return_value=value)), create=True))

    def test_selection_add_update_and_remove(self):
        with ExitStack() as stack:
            self.setup_ui(stack)
            main.on_rule_selected()
            main.frame_special_params.grid.assert_called_once()
            self.assertEqual(main.active_rules, [])
            main.add_rule()
            self.assertEqual(main.active_rules[0]["params"]["counts"], [1, 2])
            main.special_count_rows.append((Mock(), Mock(get=Mock(return_value="3"))))
            main.add_rule()
            self.assertEqual(len(main.active_rules), 1)
            self.assertEqual(main.active_rules[0]["params"]["counts"], [1, 2, 3])
            main.listbox_rules.curselection.return_value = (0,)
            main.remove_rule()
            self.assertEqual(main.active_rules, [])

    def test_plus_chooses_next_unused_count_and_minus_keeps_one_row(self):
        def entry_factory(*args, **kwargs):
            obj = Mock()
            value = {"text": ""}
            obj.insert.side_effect = lambda _, text: value.update(text=text)
            obj.get.side_effect = lambda: value["text"]
            return obj
        with ExitStack() as stack:
            stack.enter_context(patch.object(main, "special_count_rows", []))
            stack.enter_context(patch.object(main, "frame_special_counts", Mock(), create=True))
            for name in ("Frame", "Label", "Button"):
                stack.enter_context(patch.object(main.tk, name))
            stack.enter_context(patch.object(main.tk, "Spinbox", side_effect=entry_factory))
            main.add_special_count_row(2)
            main.add_special_count_row()
            main.add_special_count_row()
            self.assertEqual([entry.get() for _, entry in main.special_count_rows], ["2", "1", "3"])
            main.remove_special_count_row(*main.special_count_rows[-1])
            main.remove_special_count_row(*main.special_count_rows[-1])
            main.remove_special_count_row(*main.special_count_rows[-1])
            self.assertEqual(len(main.special_count_rows), 1)

    def test_export_counts_match_summary_and_selected_groups(self):
        with ExitStack() as stack, tempfile.TemporaryDirectory() as temp:
            self.setup_ui(stack)
            main.add_rule()
            for name, value in {
                "entry_fullname": "Demo", "entry_birthdate": "", "entry_relative_name": "",
                "entry_relative_birth": "", "entry_child_name": "", "entry_child_birth": "",
                "entry_company": "", "entry_hometown": "", "entry_wcfrom": "5", "entry_wcto": "6",
            }.items():
                stack.enter_context(patch.object(main, name, Mock(get=Mock(return_value=value)), create=True))
            previous = os.getcwd()
            try:
                os.chdir(temp)
                main.generate_wordlist_via_pipeline()
                main.messagebox.showerror.assert_not_called()
                files = list(Path("output").glob("*.txt"))
                self.assertEqual(len(files), 1)
                lines = files[0].read_text(encoding="utf-8").splitlines()
                stats = json.loads(files[0].with_suffix(".summary.json").read_text(encoding="utf-8"))
                self.assertTrue(lines)
                self.assertEqual({count_specials(p) for p in lines}, {1, 2})
                self.assertEqual(stats["total"], len(lines))
                self.assertEqual(stats["special_character_counts"],
                                 {str(k): v for k, v in Counter(map(count_specials, lines)).items()})
                self.assertTrue(all(5 <= len(p) <= 6 for p in lines))
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
