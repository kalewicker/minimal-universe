from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_r04 import audit, evaluate


class EligibilityAuditTests(unittest.TestCase):
    def setUp(self):
        self.inputs = [json.loads((ROOT / name).read_text()) for name in (
            'protocols/r02-measurement-contract.json', 'protocols/r03b-design.json',
            'protocols/r03b-launch.json', 'reports/r03b-run.json',
            'reports/r03b-analysis.json')]

    def test_missing_evidence_is_not_a_failed_effect(self):
        result = evaluate(*self.inputs)
        self.assertEqual(result['candidate_effect_status'], 'not_evaluated')
        self.assertEqual(result['intervention_status'], 'not_executed')
        self.assertEqual(result['eligible_candidates'], [])

    def test_changed_evidence_fails_closed(self):
        for index, key, value in ((4, 'audit_status', 'fail'),
                                  (4, 'candidate_promotions', 1),
                                  (4, 'candidate_promotions', False),
                                  (3, 'execution_status', 'partial'),
                                  (3, 'ledger_sha256', 'changed'),
                                  (2, 'holdout_authorized', True),
                                  (0, 'intervention_horizon', 2)):
            with self.subTest(key=key):
                inputs = deepcopy(self.inputs)
                inputs[index][key] = value
                with self.assertRaises(ValueError):
                    evaluate(*inputs)

    def test_accounting_mismatch_rejected(self):
        self.inputs[4]['counts']['reserved'] -= 1
        with self.assertRaises(ValueError):
            evaluate(*self.inputs)

    def test_input_tampering_rejected_before_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'protocols').mkdir()
            (root / 'protocols/r04a.json').write_bytes((ROOT / 'protocols/r04a.json').read_bytes())
            (root / 'protocols/r02-measurement-contract.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'input digest mismatch'):
                audit(root)


if __name__ == '__main__':
    unittest.main()
