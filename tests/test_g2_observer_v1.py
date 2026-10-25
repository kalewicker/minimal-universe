from fractions import Fraction
from unittest import TestCase, main
from unittest.mock import patch
from analysis import g2_observer_v1 as o


class ObserverTests(TestCase):
    def test_graph_identity_multiplicity_and_isolates(self):
        self.assertEqual(o.graph_digest(3, [(0, 1), (1, 0)]), o.graph_digest(3, [(1, 0), (0, 1)]))
        self.assertNotEqual(o.graph_digest(2, [(0, 1)]), o.graph_digest(3, [(0, 1)]))
        self.assertNotEqual(o.graph_digest(2, [(0, 1)]), o.graph_digest(2, [(0, 1)] * 2))

    def test_domain_and_occurrence_validation(self):
        for n, e in [(65, []), (True, []), (0, [(0, 0)]), (2, [(True, 0)]), (2, [(0, 1)] * 65)]:
            with self.assertRaises(ValueError):
                o.graph(n, e)
        with self.assertRaises(ValueError):
            o.exposure(2, [(0, 0, 1), (0, 1, 0)], [])

    def test_radius(self):
        self.assertEqual(o.radius(56), Fraction(2067, 100000))
        self.assertEqual(o.radius(1), Fraction(1, 64))
        for q in (False, 0, -1, 1.0):
            with self.assertRaises(ValueError):
                o.radius(q)

    def test_rejection_and_bound_one_consume_words(self):
        w = o.Words('a' * 64, 'test/vector', 'b' * 64, 3)
        w.start(0)
        with patch.object(w, 'word', side_effect=[0, 1, 2 ** 64 - 1]) as word:
            self.assertEqual(w.below(3), 1)  # zero is rejected
            self.assertEqual(w.below(1), 0)
            self.assertEqual(word.call_count, 3)

    def test_literal_sha_counter_vectors_and_draw_reset(self):
        w = o.Words('a' * 64, 'test/vector', 'b' * 64, 10)
        w.start(0)
        self.assertEqual([w.word() for _ in range(3)],
                         [1123277768083489074, 16135020977051064656, 3729921626085222993])
        w.start(0)
        self.assertEqual(w.word(), 1123277768083489074)
        self.assertEqual(w.total, 4)

    def test_force_sampling_cannot_silently_replace_exact_dispatch(self):
        with self.assertRaises(ValueError):
            o.degree_null(2, [], root='a' * 64, query='campaign', quota=56, calibration_force_sample=True)

    def test_constant_sample_is_unresolved_not_exact_degeneracy(self):
        with patch.object(o, 'SAMPLES', 4):
            result = o.degree_null(2, [(0, 1)] * 9, root='a' * 64, query='unit/constant', quota=56)
        self.assertEqual(result['status'], 'sampled_constant_unresolved')
        self.assertGreater(result['interval'][1], 0)
        self.assertFalse(result['scientific_acceptance'])

    def test_rng_budget_discards_partial_estimate(self):
        with patch.object(o.Words, 'word', side_effect=o.WordBudgetExceeded):
            r = o.degree_null(2, [(0, 1)] * 9, root='a' * 64, query='budget', quota=56)
        self.assertEqual(r['status'], 'rng_budget_exhausted')
        self.assertIsNone(r['mean'])
        self.assertIsNone(r['interval'])
        self.assertEqual(r['completed_draws'], 0)

    def test_budget_real_boundary(self):
        w = o.Words('a' * 64, 'test/vector', 'b' * 64, 1)
        w.start(0)
        w.below(1)
        with self.assertRaises(o.WordBudgetExceeded):
            w.below(1)
        self.assertEqual(w.total, 1)

    def test_exact_dispatch_and_undefined(self):
        r = o.degree_null(2, [(0, 1), (1, 0)], root='a' * 64, query='exact', quota=56)
        self.assertEqual(r['mode'], 'exact')
        self.assertEqual(r['mean'], Fraction(1, 2))
        self.assertEqual(r['status'], 'informative')
        self.assertEqual(o.exact_null(2, [])['status'], 'degenerate')
        self.assertEqual(o.degree_null(1, [], root='a' * 64, query='undefined', quota=56)['status'], 'undefined')

    def endpoint(self, **kwargs):
        args = dict(nodes=2, edges=[(0, 0, 1), (1, 1, 0)], parent_ids=[0, 1], targets=[0],
                    parent_event=10, event=60, horizon=50)
        args.update(kwargs)
        return o.observed_endpoint(**args)

    def test_occurrence_recreation_is_not_survival(self):
        self.assertTrue(self.endpoint()['observed_untouched'])
        r = self.endpoint(edges=[(2, 0, 1), (3, 1, 0)])
        self.assertFalse(r['observed_untouched'])
        self.assertEqual(r['local']['status'], 'target_already_consumed')
        self.assertIsNone(r['local']['probability_avoid'])

    def test_unavailable_does_not_fabricate_false(self):
        for status in ('terminal_before_horizon', 'resource_censored', 'domain_unsupported', 'undefined'):
            r = self.endpoint(nodes=None, edges=None, event=20, status=status)
            self.assertIsNone(r['observed_untouched'])
            self.assertIsNone(r['local'])
            self.assertEqual(r['status'], status)
        with self.assertRaises(ValueError):
            self.endpoint(event=20)
        with self.assertRaises(ValueError):
            self.endpoint(event=20, status='resource_censored')

    def test_no_eligible_and_deterministic_scheduler(self):
        r = self.endpoint(edges=[(0, 0, 1)])
        self.assertEqual(r['local']['status'], 'no_eligible_match')
        self.assertIsNone(r['local']['probability_avoid'])
        r = self.endpoint(scheduler='lex_first')
        self.assertEqual(r['local']['matches'], 2)
        self.assertIsNone(r['local']['probability_avoid'])

    def test_full_match_domain(self):
        r = o.exposure(1, [(i, 0, 0) for i in range(64)], [0])
        self.assertEqual(r['matches'], 4032)
        self.assertEqual(r['target_union_matches'], 126)
        self.assertEqual(r['probability_avoid'], Fraction(31, 32))


if __name__ == '__main__':
    main()
