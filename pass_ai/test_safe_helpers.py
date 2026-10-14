import tempfile
import unittest
from pathlib import Path

import feature_extractor
import handle
import main
from feature_extractor import FEATURE_NAMES
from password_utils import calculate_entropy
from pattern_model import PatternFrequencyModel, extract_block_pattern
from pipeline.logger import PipelineLogger
from rules import RuleExecutor, RuleValidationError, get_available_rule_names


class SafeHelperTests(unittest.TestCase):
    def setUp(self):
        handle.read_config("rules.cfg")

    def test_mask_legacy_helper(self):
        self.assertEqual(main.get_mask('Ab1!'), '?u?l?d?s')

    def test_date_validation(self):
        self.assertTrue(main.is_valid_flexible_date('06/08/1980'))
        self.assertTrue(main.is_valid_flexible_date('06/08'))
        self.assertTrue(main.is_valid_flexible_date('08/1980'))
        self.assertFalse(main.is_valid_flexible_date('31/02/2020'))

    def test_core_flexible_date_variants(self):
        self.assertEqual(handle.generate_date_variants('0608'), {'0608', '0806'})
        self.assertTrue({'1980', '80', '081980'}.issubset(handle.generate_date_variants('081980')))
        self.assertTrue({'1980', '80', '0608', '0806'}.issubset(handle.generate_date_variants('06081980')))
        self.assertEqual(handle.generate_date_variants('3102'), set())

    def test_parse_params(self):
        self.assertEqual(main.parse_params('a=2, mode=test'), {'a': 2, 'mode': 'test'})

    def test_features_shape(self):
        self.assertEqual(len(feature_extractor.extract_features('Example1!')), len(FEATURE_NAMES))

    def test_shared_entropy(self):
        value = 'Example1!'
        self.assertEqual(feature_extractor.calculate_entropy(value), calculate_entropy(value))

    def test_registry_exposes_only_implemented_rules(self):
        names = get_available_rule_names()
        self.assertIn('LÕI_CƠ_HỌC', names)
        self.assertNotIn('TỰ_HỌC_KHUÔN_MẪU', names)
        self.assertNotIn('LEET', names)

    def test_executor_rejects_placeholder_rule(self):
        executor = RuleExecutor()
        with self.assertRaises(RuleValidationError):
            executor.validate_rule('LEET')
        with self.assertRaises(RuleValidationError):
            executor.validate_rule('TỰ_HỌC_KHUÔN_MẪU')

    def test_special_definition_includes_separators(self):
        self.assertTrue(handle.has_special('abc_def'))
        self.assertTrue(handle.has_special('abc-def'))
        self.assertFalse(handle.has_special('abcdef'))


    def test_pattern_extractor(self):
        self.assertEqual(extract_block_pattern('Abc_2020'), 'CAP3+SEP_UNDERSCORE+YEAR4')
        self.assertEqual(extract_block_pattern('hello123'), 'LOWER5+DIGIT3')

    def test_pattern_frequency_model(self):
        model = PatternFrequencyModel().fit(['Abc_2020', 'Def_2021', 'hello123'])
        top = model.top_patterns(limit=1)
        self.assertEqual(top[0].pattern, 'CAP3+SEP_UNDERSCORE+YEAR4')
        self.assertEqual(top[0].count, 2)
        self.assertAlmostEqual(model.coverage(limit=1), 2 / 3)

    def test_pattern_model_export_has_no_raw_examples(self):
        model = PatternFrequencyModel().fit(['Secret_2020', 'Other_2021'])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'summary.json'
            model.export_summary(path)
            content = path.read_text(encoding='utf-8')
            self.assertNotIn('Secret_2020', content)
            self.assertIn('CAP6+SEP_UNDERSCORE+YEAR4', content)

    def test_pipeline_logger_avoids_raw_secret_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'pipeline.jsonl'
            logger = PipelineLogger(path)
            logger.log('test_event', output_count=3)
            content = path.read_text(encoding='utf-8')
            self.assertIn('test_event', content)
            self.assertIn('output_count', content)

    def test_pattern_length_statistics_are_aggregate(self):
        model = PatternFrequencyModel().fit(['Abc_2020', 'hello123', 'XYZ!'])
        self.assertEqual(model.total_samples, 3)
        self.assertAlmostEqual(model.average_length, (8 + 8 + 4) / 3)
        self.assertEqual(model.min_length, 4)
        self.assertEqual(model.max_length, 8)
        lengths = {row.length: row.count for row in model.length_distribution()}
        self.assertEqual(lengths, {4: 1, 8: 2})

    def test_pattern_csv_export_has_only_aggregate_rows(self):
        model = PatternFrequencyModel().fit(['Secret_2020', 'Other_2021'])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'patterns.csv'
            model.export_patterns_csv(path)
            content = path.read_text(encoding='utf-8-sig')
            self.assertIn('pattern,count,probability', content)
            self.assertIn('CAP6+SEP_UNDERSCORE+YEAR4', content)
            self.assertNotIn('Secret_2020', content)
            self.assertNotIn('Other_2021', content)

    def test_pattern_preview_is_aggregate_only(self):
        model = PatternFrequencyModel().fit(['Abc_2020', 'Def_2021', 'hello123'])
        preview = main.build_pattern_preview(model, limit=2, min_count=1)
        self.assertIn('CAP3+SEP_UNDERSCORE+YEAR4', preview)
        self.assertNotIn('Abc_2020', preview)
        self.assertNotIn('Def_2021', preview)


if __name__ == '__main__':
    unittest.main()
