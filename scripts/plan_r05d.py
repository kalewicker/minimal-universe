"""Closed-form static G2 size feasibility. No graph transition or trajectory input."""
from collections import Counter
from hashlib import sha256
from itertools import combinations_with_replacement, product
from math import comb, factorial
import json


def rules():
    arcs = tuple(product(range(4), repeat=2))
    for length in range(4):
        yield from combinations_with_replacement(arcs, length)


def rule_id(rhs):
    text = json.dumps(dict(schema='mu-g2-path-rule-v1', rhs=rhs), sort_keys=True, separators=(',', ':'))
    return sha256(text.encode('ascii')).hexdigest()


def seed_facts(seed):
    edges = seed['edges']
    incoming, outgoing = Counter(), Counter()
    for a, b in edges:
        outgoing[a] += 1
        incoming[b] += 1
    matches = sum(incoming[v] * outgoing[v] for v in range(seed['nodes'])) - sum(a == b for a, b in edges)
    return dict(nodes=seed['nodes'], edges=len(edges), matches=matches,
                density_defined=seed['nodes'] >= 2,
                motif_coverage_complete=max(Counter(map(tuple, edges)).values(), default=0) <= 2)


def project(rhs, seed, horizon, protocol):
    initial = seed_facts(seed)
    n, e, k = initial['nodes'], initial['edges'], len(rhs)
    fresh = any(3 in arc for arc in rhs)
    maximum = 0 if not initial['matches'] else (e - 2) // (2 - k) + 1 if k < 2 else None
    if horizon and not initial['matches']:
        availability = 'provably_unavailable_no_initial_match'
    elif horizon and maximum is not None and horizon > maximum:
        availability = 'provably_unavailable_edge_budget'
    else:
        availability = 'initial_state' if horizon == 0 else 'not_established_by_static_sizes'
    result = dict(availability=availability, successful_event_upper_bound=maximum,
                  initial=initial, projection=None)
    if availability.startswith('provably_unavailable'):
        return result
    end_n, end_e = n + fresh * horizon, e + (k - 2) * horizon
    peak_n, peak_e = end_n, max(e, end_e)
    kernel, observer, measurement = (protocol[key] for key in ('kernel_domain', 'observer_domain', 'g2_measurement_domain'))
    count_fits = horizon <= kernel['events'] and peak_n <= kernel['nodes'] and peak_e <= kernel['edges']
    match_upper = peak_e * max(0, peak_e - 1)
    local_fits = peak_n <= measurement['nodes'] and peak_e <= measurement['edges'] and match_upper <= measurement['matches']
    exact_size_fits = local_fits and horizon <= measurement['exact_horizon']
    # A sufficient bound on every intermediate frontier, not a measured state count.
    history_bound = 1
    if exact_size_fits:
        for t in range(horizon):
            pre_edges = e + (k - 2) * t
            bound = initial['matches'] if t == 0 else pre_edges * (pre_edges - 1)
            history_bound *= bound
        exact = ('guaranteed_by_count_bound' if history_bound <= measurement['frontier_states']
                 else 'frontier_not_guaranteed')
    else:
        history_bound = None
        exact = 'outside_size_or_horizon_domain'
    initial_complete = initial['motif_coverage_complete']
    motif = ('known_incomplete_at_initial_state' if not initial_complete else
             'guaranteed_complete' if horizon == 0 or peak_e <= 2 else 'not_guaranteed_by_sizes')
    null_fits = peak_e <= observer['null_edges']
    observer_fits = peak_n <= observer['nodes']
    result['projection'] = dict(endpoint_nodes=end_n, endpoint_edges=end_e,
        peak_nodes=peak_n, peak_edges=peak_e, match_count_upper_bound=match_upper,
        kernel_count_caps_fit=count_fits,
        kernel_match_cap_guaranteed=match_upper <= kernel['matches'],
        observer_node_domain=observer_fits, degree_null_edge_domain=null_fits,
        local_exposure_domain=local_fits, exact_survival_domain=exact,
        frontier_history_upper_bound=history_bound,
        initial_density_defined=initial['density_defined'], endpoint_density_defined=end_n >= 2,
        motif_coverage=motif, null_informativeness='not_established',
        motif_subset_work_upper_bound=sum(comb(peak_n, s) for s in range(1, min(3, peak_n) + 1)),
        raw_null_permutation_work_upper_bound=(horizon + 1) * factorial(peak_e)
        if null_fits and observer_fits else None)
    return result
