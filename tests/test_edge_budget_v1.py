from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import unittest
from unittest.mock import patch
from analysis import edge_budget_v1 as b
from analysis import g2_observer_v1 as legacy


def pair(name='base'):
    parent = b.PARENT_PREFIX + name
    branch = dict(parent=parent, partition=b.partition(parent), scheduler='uniform_match', horizon=50,
                  status='reached', score_0=Fraction(), score_h=Fraction(1, 4), matches_0=2, matches_h=2)
    return dict(parent=parent, target=deepcopy(branch), sham=deepcopy(branch))


class BudgetObserverTests(unittest.TestCase):
    def test_budget_domain_distinguishes_empty_from_aliased_loops(self):
        self.assertIsNone(b.score(0, []))
        self.assertIsNone(b.score(2, []))
        self.assertEqual(b.score(1, [(0, 0)] * 2), 0)
        self.assertEqual(b.observe(1, [(0, 0)])['status'], 'defined')
        self.assertEqual(b.observe(2, [])['status'], 'undefined_empty_graph')

    def test_multiplicity_is_budget_not_reverse_supported_occurrence_fraction(self):
        self.assertEqual(b.score(64, [(0, 1), (1, 0)]), 1)
        self.assertEqual(b.score(2, [(0, 1)] * 3 + [(1, 0)]), Fraction(1, 2))
        self.assertEqual(b.score(2, [(0, 1), (1, 0)] + [(0, 0)] * 6), Fraction(1, 4))

    def test_exact_mean_and_informative_status(self):
        result = b.exact_null(2, [(0, 1)] * 3 + [(1, 0)])
        self.assertEqual(result['mean'], Fraction(1, 8))
        self.assertEqual(result['contrast_interval'], [Fraction(3, 8)] * 2)
        self.assertEqual(result['status'], 'informative')
        self.assertEqual(b.exact_null(1, [(0, 0)])['status'], 'degenerate')

    def test_dispatch_and_undefined_slot_keep_quota_without_words(self):
        for n, edges in [(0, []), (1, [(0, 0)]), (2, [(0, 1), (1, 0)])]:
            result = b.degree_null(n, edges, root='a' * 64, query='unit/exact', quota=892)
            self.assertEqual(result['mode'], 'exact')
            self.assertEqual(result['quota'], 892)
            self.assertEqual(result['words'], 0)
            self.assertEqual(result['metric'], b.METRIC)
        with self.assertRaises(ValueError):
            b.degree_null(2, [], root='bad', query='unit/exact', quota=892)

    def test_force_sampling_cannot_escape_calibration_namespace(self):
        with self.assertRaises(ValueError):
            b.degree_null(2, [(0, 1)], root='a' * 64, query='campaign', quota=892, calibration_force_sample=True)

    def test_rng_namespace_differs_from_historical_metric(self):
        new = b.Words('a' * 64, 'test/vector', 'b' * 64, 10)
        old = legacy.Words('a' * 64, 'test/vector', 'b' * 64, 10)
        new.start(0)
        old.start(0)
        header = dict(schema='mu-g2-budget-null-word-v1', root='a' * 64,
                      query='test/vector', graph='b' * 64, draw=0)
        expected = int.from_bytes(sha256(legacy.canonical(header) + b'\n0').digest()[:8], 'big')
        self.assertEqual(new.word(), expected)
        new.start(0)
        self.assertNotEqual(new.word(), old.word())

    def test_rejection_bound_one_and_budget_consumption(self):
        words = b.Words('a' * 64, 'unit/rng', 'b' * 64, 1)
        words.start(0)
        with patch.object(words, 'word', side_effect=[0, 1, 99]) as word:
            self.assertEqual(words.below(3), 1)
            self.assertEqual(words.below(1), 0)
            self.assertEqual(word.call_count, 3)
        words.word()
        with self.assertRaises(legacy.WordBudgetExceeded):
            words.word()

    def test_incomplete_query_preserves_one_draw_and_rejects_partial_mean(self):
        class LimitedWords(b.Words):
            def __init__(self, *args):
                super().__init__(*args)
                self.budget = 8
        with patch.object(b, 'Words', LimitedWords):
            result = b.degree_null(2, [(0, 1)] * 9, root='a' * 64, query='unit/budget', quota=892)
        self.assertEqual(result['status'], 'rng_budget_exhausted')
        self.assertEqual(result['completed_draws'], 1)
        self.assertEqual(sum(result['histogram'].values()), 1)
        self.assertIsNone(result['mean'])
        self.assertIsNone(result['interval'])
        self.assertIsNone(result['contrast_interval'])

    def test_sample_constant_is_unresolved(self):
        with patch.object(b, 'SAMPLES', 4):
            result = b.degree_null(2, [(0, 1)] * 9, root='a' * 64, query='unit/constant', quota=892)
        self.assertEqual(result['status'], 'sampled_constant_unresolved')
        self.assertGreater(result['interval'][1], 0)
        self.assertFalse(result['scientific_acceptance'])

    def test_invalid_domain_cannot_become_an_empty_graph(self):
        for n, e in [(True, []), (65, []), (2, [(0, True)]), (0, [(0, 0)]), (2, [(0, 1)] * 65)]:
            with self.assertRaises(ValueError):
                b.score(n, e)
        with self.assertRaises(ValueError):
            b.exact_null(2, [(0, 1)] * 9)

    def test_paired_offsets_and_differential_change(self):
        row = pair()
        row['target'].update(score_0=Fraction(1, 4), score_h=Fraction(1, 2))
        self.assertEqual(b.paired_bookkeeping([row])['mean_effect'], 0)
        row['target']['score_h'] = Fraction(3, 4)
        self.assertEqual(b.paired_bookkeeping([row])['mean_effect'], Fraction(1, 4))

    def test_missing_pair_prevents_aggregate_and_retains_match_changes(self):
        row = pair()
        row['target'].update(status='resource_censored', score_h=None, matches_h=None)
        result = b.paired_bookkeeping([pair('other'), row])
        self.assertEqual(result['total_pairs'], 2)
        self.assertEqual(result['complete_pairs'], 1)
        self.assertIsNone(result['mean_effect'])
        changed = pair('changed')
        changed['sham'].update(matches_0=1, matches_h=0)
        result = b.paired_bookkeeping([changed])
        self.assertTrue(result['pairs'][0]['initial_eligibility_changed'])
        self.assertTrue(result['pairs'][0]['endpoint_eligibility_changed'])
        self.assertEqual(result['sham_validity'], 'not_established')

    def test_namespace_split_and_invented_endpoints_are_rejected(self):
        rows = []
        duplicate = pair(); rows.append([duplicate, deepcopy(duplicate)])
        for key, value in [('parent', b.PARENT_PREFIX + 'child'), ('partition', 'invented'),
                           ('horizon', 49), ('scheduler', 'lex_last'), ('score_h', True),
                           ('status', 'resource_censored')]:
            row = pair(); row['target'][key] = value; rows.append([row])
        for sample in rows:
            with self.assertRaises(ValueError):
                b.paired_bookkeeping(sample)
        with self.assertRaises(ValueError):
            b.partition('production/parent-001')


if __name__ == '__main__':
    unittest.main()
