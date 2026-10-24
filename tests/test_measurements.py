import math
from pathlib import Path
import sys
import unittest
from fractions import Fraction

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
import measurements as m


class MeasurementTests(unittest.TestCase):
    def test_parallel_loops_isolates_and_coverage(self):
        result = m.motifs(2, [(0,0), (0,0)])
        self.assertEqual(result['counts'], {'1:0':1, '1:2':1})
        self.assertEqual(result['denominators'], {1:2, 2:1})
        excluded = m.motifs(2, [(0,1)]*3)
        self.assertEqual(excluded['excluded_subsets'], 1)
        self.assertFalse(excluded['coverage_complete'])
        self.assertEqual(excluded['counts'], {'1:0':2})

    def test_reciprocal_and_exact_null(self):
        self.assertIsNone(m.reciprocal_density(1, [(0,0)]))
        self.assertEqual(m.reciprocal_density(3, [(0,1),(1,0)]), Fraction(1,3))
        null = m.degree_null(2, [(0,1),(1,0)])
        self.assertEqual(null['distribution'], {Fraction(0):Fraction(1,2), Fraction(1):Fraction(1,2)})
        self.assertEqual(m.degree_null(2, [(0,1)])['status'], 'degenerate')
        with self.assertRaises(ValueError):
            m.degree_null(2, [(0,1)]*9)

    def test_survival_not_regeneration(self):
        self.assertEqual(m.survival_probability(3,1,3,2), Fraction(8,15))
        self.assertIsNone(m.survival_probability(1,1,0,2))
        self.assertFalse(m.untouched([1,2], [3,4]))
        self.assertTrue(m.untouched([1,2], [1,2,3]))
        with self.assertRaises(ValueError):
            m.untouched([1,1], [1])

    def test_partition_and_holm(self):
        from hashlib import sha256
        labels = ['discovery']*4 + ['detector-development']*2 + ['validation']*2 + ['final-test']*2
        for parent in ['parent-1', 'parent-2', 'parent-3']:
            bucket = int(sha256(parent.encode()).hexdigest()[:16],16)%10
            self.assertEqual(m.partition(parent), labels[bucket])
        self.assertEqual(m.holm([.01,.04,.03]), [.03,.06,.06])
        with self.assertRaises(ValueError):
            m.holm([math.nan])

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            m.motifs(2, [(2,0)])
        with self.assertRaises(ValueError):
            m.survival_probability(1,2,1,1)
        with self.assertRaises(ValueError):
            m.partition('')
        self.assertFalse(m.promotion({}))


if __name__ == '__main__':
    unittest.main()
