from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from g2_reference import Reference, sample, word
from verify_r05b import cases


class G2ReferenceTests(unittest.TestCase):
    def config(self):
        return dict(nodes=1, seed=[[0, 0], [0, 0]], rhs=[[0, 0]] * 3,
                    rng=104729, scheduler='lex_first',
                    limits=dict(events=6, nodes=16, edges=16, matches=256))

    def test_parent_deduplication_and_merge(self):
        ref = Reference(self.config())
        final = ref.run()
        self.assertEqual(final['events'][0]['parents'], [])
        self.assertEqual(final['events'][1]['parents'], [0])
        self.assertEqual(final['events'][2]['parents'], [0, 1])

    def test_cap_rejections_preserve_continuation(self):
        for key, value, rhs, status in (
                ('events', 0, [[0, 0]] * 3, 'event_cap'),
                ('edges', 2, [[0, 0]] * 3, 'edge_cap'),
                ('nodes', 1, [[0, 3], [3, 1]], 'node_cap'),
                ('matches', 1, [[0, 0]] * 3, 'match_cap')):
            config = self.config()
            config['rhs'], config['scheduler'] = rhs, 'uniform_match'
            config['limits'][key] = value
            ref = Reference(config)
            before = ref.snapshot('before')
            self.assertEqual(ref.advance(), status)
            self.assertEqual(ref.snapshot('before'), before)

    def test_single_uniform_match_still_draws(self):
        config = self.config()
        config.update(nodes=3, seed=[[0, 1], [1, 2]], scheduler='uniform_match')
        ref = Reference(config)
        ref.advance()
        self.assertEqual(ref.rng, word(config['rng'])[0])

    def test_rng_wrap_and_rejection(self):
        self.assertEqual(word(0)[1], 16294208416658607535)
        state, index = sample(3, (1 << 63) + 1)
        self.assertNotEqual(state, word(3)[0])  # The first word is rejected.
        self.assertTrue(0 <= index < (1 << 63) + 1)
        self.assertEqual(sample((1 << 64) - 1, 1)[1], 0)

    def test_fresh_alias_emission_retains_occurrences(self):
        config = self.config()
        config['rhs'] = [[0, 3], [1, 3], [2, 3]]
        ref = Reference(config)
        ref.advance()
        self.assertEqual(ref.nodes, 2)
        self.assertEqual([edge[1:3] for edge in ref.edges.values()], [[0, 1]] * 3)
        self.assertEqual(list(ref.edges), [2, 3, 4])

    def test_prefix_snapshot_is_not_mutated_by_continuation(self):
        ref = Reference(self.config())
        snapshot = ref.prefix(1)
        saved = deepcopy(snapshot)
        ref.run()
        self.assertEqual(snapshot, saved)

    def test_registered_matrix_has_all_cases(self):
        protocol = json.loads((ROOT / 'protocols/r05b.json').read_text())
        self.assertEqual(len(list(cases(protocol))), 15433)


if __name__ == '__main__':
    unittest.main()
