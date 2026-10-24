import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_r01 import I, K, S, app, normal, reference_graph, sources, word


class ReferenceTests(unittest.TestCase):
    def test_beta_identity_erasure_duplication(self):
        self.assertEqual(normal(app(I, 'x')), 'x')
        self.assertEqual(normal(app(app(K, 'x'), 'y')), 'x')
        self.assertEqual(normal(app(app(app(S, 'x'), 'y'), 'z')),
                         app(app('x', 'z'), app('y', 'z')))

    def test_beta_avoids_capture_and_reduces_under_lambda(self):
        self.assertEqual(normal(app(('L', ('L', 1)), 'x')), ('L', 'x'))
        self.assertEqual(normal(('L', app(('L', ('L', 1)), 0))), ('L', ('L', 1)))
        self.assertEqual(normal(('L', app(I, 0))), ('L', 0))

    def test_reference_graph_loop_and_parallel(self):
        budget = dict(rng_seed=0, max_events=1, max_nodes=10, max_edges=10)
        result = reference_graph({'nodes': 2, 'edges': [[0, 0], [0, 0]]},
                                 ((0, 2), (2, 1)), 'oldest', budget)
        self.assertEqual(result['edges'], [[1, 0, 0, None], [2, 0, 2, 0], [3, 2, 0, 0]])
        self.assertEqual(result['nodes'], 3)

    def test_rng_and_source_denominators(self):
        self.assertEqual(word(0)[1], 0xe220a8397b1dcdaf)
        self.assertEqual([len(sources(n)) for n in range(1, 6)], [1, 1, 2, 5, 14])


if __name__ == '__main__':
    unittest.main()
