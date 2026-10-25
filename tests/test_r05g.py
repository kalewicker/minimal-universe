from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from review_r05g import ceiling_status, check_pins, public_file, validate_calibration


class ReadinessReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads((ROOT / 'reports/r05f.json').read_text())
        cls.design = json.loads((ROOT / 'protocols/r05e-observer-design.json').read_text())

    def test_equality_does_not_imply_threshold_failure_or_candidate(self):
        bound, status = ceiling_status(16, 12, Fraction(1, 20))
        self.assertEqual(bound, Fraction(1, 20))
        self.assertEqual(status, 'not_excluded_by_ceiling')
        self.assertEqual(ceiling_status(16, 11, Fraction(1, 20))[1], 'below_frozen_threshold_upper_bound')

    def test_undefined_is_distinct_from_zero_density(self):
        self.assertEqual(ceiling_status(1, 64, Fraction(1, 20)), (None, 'undefined_density'))
        self.assertEqual(ceiling_status(2, 1, Fraction(1, 20)), (0, 'below_frozen_threshold_upper_bound'))

    def test_reciprocal_budget_and_retained_isolates(self):
        self.assertEqual(ceiling_status(3, 100, Fraction(1, 20))[0], 1)
        self.assertEqual(ceiling_status(56, 54, Fraction(1, 20))[0], Fraction(27, 1540))
        self.assertLess(ceiling_status(56, 54, Fraction(1, 20))[0],
                        ceiling_status(3, 54, Fraction(1, 20))[0])
        for n, e in [(True, 2), (2, -1), (-1, 2)]:
            with self.assertRaises(ValueError):
                ceiling_status(n, e, Fraction(1, 20))

    def test_saved_calibration_is_not_campaign_precision(self):
        result = validate_calibration(self.receipt, self.design)
        self.assertEqual(result['known_mean_covered'], 32)
        self.assertIsNone(result['campaign_quota'])
        self.assertIsNone(result['campaign_radius'])
        self.assertEqual(result['sample_statuses']['sampled_constant_unresolved'], 24)

    def test_saved_constant_sample_cannot_be_relabelled_degenerate(self):
        receipt = deepcopy(self.receipt)
        receipt['queries'][0]['result']['status'] = 'degenerate'
        with self.assertRaisesRegex(ValueError, 'degeneracy'):
            validate_calibration(receipt, self.design)

    def test_duplicate_query_cannot_replace_unfavorable_missing_slot(self):
        receipt = deepcopy(self.receipt)
        receipt['queries'][-1] = deepcopy(receipt['queries'][0])
        with self.assertRaisesRegex(ValueError, 'identity'):
            validate_calibration(receipt, self.design)

    def test_large_invariants_do_not_establish_coverage(self):
        receipt = deepcopy(self.receipt)
        receipt['queries'][-1]['coverage'] = True
        with self.assertRaisesRegex(ValueError, 'large-mean coverage'):
            validate_calibration(receipt, self.design)

    def test_changed_saved_mean_is_detected(self):
        receipt = deepcopy(self.receipt)
        receipt['queries'][0]['result']['mean'] = [1, 2]
        with self.assertRaisesRegex(ValueError, 'interval arithmetic'):
            validate_calibration(receipt, self.design)

    def test_custody_validation_does_not_open_bulk_or_private_inputs(self):
        for path in ('results/r05f-001/draws.jsonl', '.git/config', '../secret', '/tmp/secret', 'build-g2/mu-g2'):
            with self.assertRaises(ValueError):
                public_file(ROOT, path)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'digest'):
                check_pins(root, {'source.txt': '0' * 64})


if __name__ == '__main__':
    unittest.main()
