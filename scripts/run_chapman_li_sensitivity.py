#!/usr/bin/env python3
"""Finite, resumable Chapman sensitivity campaign using the unchanged shared fitter.

Fixed-condition fits use the official cache. Carbonate-independent Fig2 controls
reuse a proven identical objective, with a fresh trajectory equivalence check;
they never forge cache entries for a fit that was not run. Adapter fits are stored
separately and keyed by adapter source, inputs, protocol and engine identity.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from nernstwork.data import joint_observation_set, load_dataset, observation_set, sha256_json
from nernstwork.evaluate import code_identity, fit_key, run_fit, translate_fit, validate_submission
from nernstwork.fit import Problem, fit, seed_from
from nernstwork.investigation import _batched_process_map
from nernstwork.model import compile_mechanism
from nernstwork.store import FitCache, atomic_write_json, now

OUT = REPO / 'data/derived/chapman_li_sensitivity'
PROTOCOL_PATH = REPO / 'configs/protocols/synthesis-mle-v1.json'
PROTOCOL = json.loads(PROTOCOL_PATH.read_text())
CODE = code_identity()['sha256']


def read(path):
    return json.loads(Path(path).read_text())


def inputs(scenario):
    paths = read(OUT / 'input_manifest.json')['inputs'][scenario]
    dev = joint_observation_set([load_dataset(REPO / p) for p in paths[:2]])
    ds, sha = load_dataset(REPO / paths[2])
    hold = observation_set(ds, sha)
    return dev, hold, paths


def common_sigma():
    p = REPO / 'investigations/runs/chapman750-propose_space-opus1/final/chapman2023_fig2_750C/predictions.json'
    return read(p)['common_sigma']


def no_carbonate_dependence(sub):
    for r in sub['mechanism']['reactions']:
        if any(t['species'] == 'Li2CO3' for t in r['reactants']):
            return False
        if 'Li2CO3' in r['rate_law'].get('orders', {}):
            return False
    return True


def predict(comp, val, result, obs, common):
    ode = PROTOCOL['ode']
    Y = comp.simulate(np.array(result['theta']), obs.t_union, obs.c0, conditions=obs.conditions,
                      rtol=ode['rtol'], atol=ode['atol'], method=ode['method'], max_rhs=ode['max_rhs_evals'])
    pos = {float(t): i for i, t in enumerate(obs.t_union)}
    channels, sse, n = {}, 0., 0
    score, nll = 0., 0.
    for ch in obs.channels:
        idx = [comp.species.index(s) for s in val['observation_map'][ch.name]]
        y = Y[idx][:, [pos[float(t)] for t in ch.t]].sum(axis=0)
        residual = y - ch.y
        ss = float(residual @ residual)
        sse += ss
        n += len(y)
        score += ss / common[ch.name] ** 2
        sig = result['sigma'][ch.name]
        nll += len(y) * .5 * math.log(2 * math.pi * sig * sig) + ss / (2 * sig * sig)
        channels[ch.name] = {'time_min': ch.t.tolist(), 'observed': ch.y.tolist(), 'predicted': y.tolist(),
                             'rmse': float(np.sqrt(np.mean(residual ** 2))), 'sse': ss}
    return {'heldout_score': score, 'rmse_all': math.sqrt(sse / n), 'predictive_nll': nll,
            'channels': channels, 'common_sigma': common, 'n_obs': n,
            'initial_carbonate_input': obs.c0['Li2CO3'],
            'initial_carbonate_used': float(Y[comp.species.index('Li2CO3'), pos[0.0]])}


def invariant_fit(record, sub, val, comp, obs, scenario):
    if not no_carbonate_dependence(sub):
        return None
    if scenario == 'fig2_lower' and record.get('old_data_cache_path'):
        body = read(REPO / record['old_data_cache_path'])
        old_scenario = 'fig2_nominal'
    elif scenario == 's1_lower':
        old_scenario = 's1_nominal'
        old, _, _ = inputs(old_scenario)
        source_key = fit_key(val['dynamics_hash'], old.sha256, PROTOCOL, CODE)
        body = FitCache(REPO / 'investigations').result(source_key)
        if body is None:
            return None
    else:
        return None
    result = translate_fit(body['result'], val, comp)
    if result.get('status') != 'fitted':
        return None
    old, _, _ = inputs(old_scenario)
    maxdiff = 0.
    for pold, pnew in zip(old.parts, obs.parts):
        assert pold.conditions == pnew.conditions
        assert all(np.array_equal(a.t, b.t) and np.array_equal(a.y, b.y) for a, b in zip(pold.channels, pnew.channels))
        for key in set(pold.c0) | set(pnew.c0):
            if key != 'Li2CO3':
                assert pold.c0.get(key, 0) == pnew.c0.get(key, 0)
        ys = [comp.simulate(np.array(result['theta']), p.t_union, p.c0, conditions=p.conditions) for p in (pold, pnew)]
        ids = {s for ss in val['observation_map'].values() for s in ss}
        for s in ids:
            maxdiff = max(maxdiff, float(np.max(np.abs(ys[0][comp.species.index(s)] - ys[1][comp.species.index(s)]))))
    if maxdiff > 1e-9:
        raise ValueError(f'carbonate independence check failed {maxdiff}')
    return result, {'kind': 'proven_invariant_objective', 'original_fit_key': body['fit_key'],
                    'source_scenario': old_scenario, 'source_data_sha256': old.sha256,
                    'max_observed_trajectory_difference': maxdiff,
                    'note': 'Original optimization reused; every observed trajectory re-simulated under both initial states. No new fixed-data fit cache record created.'}


def run_one(job):
    record, scenario, mode, force_refit = job
    sub = record['submission']
    obs, hold, paths = inputs(scenario)
    val = validate_submission(sub, obs, PROTOCOL)
    dh = val.get('dynamics_hash', record['dynamics_hash'])
    directory = OUT / 'results' / f'{scenario}__{mode}'
    outpath = directory / f'{dh}.json'
    signature = {'dynamics_hash': dh, 'data_sha256': obs.sha256, 'heldout_sha256': hold.sha256,
                 'protocol_sha256': sha256_json(PROTOCOL), 'engine_sha256': CODE, 'mode': mode,
                 'common_sigma': common_sigma(), 'force_refit': force_refit}
    if mode != 'fixed':
        from chapman_initial_amount_adapter import compile_with_initial_amount, fit_with_initial_amount
        signature['adapter_sha256'] = hashlib.sha256((REPO / 'scripts/chapman_initial_amount_adapter.py').read_bytes()).hexdigest()
    identity = sha256_json(signature)
    if outpath.exists():
        saved = read(outpath)
        if saved['identity'] != identity:
            raise ValueError(f'campaign output identity changed at {outpath}; use a fresh campaign directory')
        return {k: saved.get(k) for k in ('dynamics_hash', 'status', 'scenario', 'mode')} | {'reused_output': True}
    start = time.perf_counter()
    out = {'identity': identity, **signature, 'scenario': scenario, 'created_at': now(), 'paths': paths,
           'candidate_name': sub['name'], 'sources': record.get('sources', []), 'submission': sub,
           'validation': val, 'carbonate_independent': no_carbonate_dependence(sub)}
    try:
        if val['status'] != 'valid':
            raise ValueError(val)
        comp = compile_mechanism(sub['mechanism'], obs.conditions, PROTOCOL['bounds'])
        reused = None
        if scenario in ('fig2_lower', 's1_lower') and mode == 'fixed' and not force_refit:
            reused = invariant_fit(record, sub, val, comp, obs, scenario)
        if reused:
            result, out['fit_origin'] = reused
        elif mode == 'fixed':
            cache = FitCache(REPO / 'investigations')
            key = fit_key(dh, obs.sha256, PROTOCOL, CODE)
            body = cache.result(key)
            if body:
                result = translate_fit(body['result'], val, comp)
                out['fit_origin'] = {'kind': 'exact_cache', 'fit_key': key}
            else:
                live = cache.live_attempt(key)
                if live:
                    return {'status': 'busy', 'dynamics_hash': dh, 'attempt': live['attempt_id']}
                aid = cache.begin_attempt(key, {'campaign': 'chapman_li_sensitivity', 'scenario': scenario,
                                                'dynamics_hash': dh, 'code_sha256': CODE})
                try:
                    raw = run_fit(sub, val, obs, PROTOCOL)
                    body = cache.commit(key, aid, raw)['result']
                    result = translate_fit(body['result'], val, comp)
                except Exception as e:
                    cache.end_attempt(key, aid, 'failed', error=f'{type(e).__name__}: {e}')
                    raise
                out['fit_origin'] = {'kind': 'new_official_fit', 'fit_key': key}
        else:
            comp = compile_with_initial_amount(sub['mechanism'], obs.conditions, PROTOCOL['bounds'], mode=mode)
            seed = seed_from(f"{PROTOCOL['optimizer']['seed']}:{dh}:{obs.sha256}:{mode}")
            result = fit_with_initial_amount(sub, obs, PROTOCOL, mode=mode, seed=seed)
            out['fit_origin'] = {'kind': 'new_adapter_fit', 'adapter_identity': signature['adapter_sha256']}
        out['status'] = result['status']
        out['fit'] = result
        if result['status'] == 'fitted':
            out['prediction'] = predict(comp, val, result, hold, signature['common_sigma'])
    except Exception as e:
        out['status'] = 'execution_error'
        out['error'] = f'{type(e).__name__}: {e}'
        import traceback
        out['traceback'] = traceback.format_exc()
    out['campaign_wall_s'] = time.perf_counter() - start
    atomic_write_json(outpath, out)
    return {k: out.get(k) for k in ('dynamics_hash', 'status', 'scenario', 'mode', 'error', 'campaign_wall_s')}


def records(args):
    items = read(args.records)
    if args.ids:
        wanted = set(args.ids.split(','))
        items = [r for r in items if r['dynamics_hash'] in wanted]
    if args.dependent_only:
        items = [r for r in items if not no_carbonate_dependence(r['submission'])]
    # Preserve all members, but finish informative original best fits early.
    def priority(r):
        old = r.get('old_data_cache_path')
        if old and (REPO / old).exists():
            fr = read(REPO / old)['result']
            return (not no_carbonate_dependence(r['submission']), fr.get('aicc', math.inf))
        return (True, math.inf)
    items.sort(key=priority)
    return items[:args.limit] if args.limit else items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--records', type=Path, default=OUT / 'repaired_records.json')
    ap.add_argument('--scenario', required=True, choices=['fig2_nominal', 'fig2_lower', 's1_nominal', 's1_lower'])
    ap.add_argument('--mode', default='fixed', choices=['fixed', 'shared', 'per_temperature'])
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--ids')
    ap.add_argument('--dependent-only', action='store_true')
    ap.add_argument('--force-refit', action='store_true', help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.force_refit:
        ap.error('--force-refit cannot safely overwrite provenance-keyed campaign results; '
                 'use scripts/check_chapman_sensitivity_numerics.py for isolated numerical repeats')
    if args.workers < 1:
        ap.error('--workers must be positive')
    jobs = [(r, args.scenario, args.mode, args.force_refit) for r in records(args)]
    print(json.dumps({'started': now(), 'jobs': len(jobs), 'scenario': args.scenario, 'mode': args.mode,
                      'workers': args.workers, 'engine': CODE}), flush=True)
    counts = {}
    for n, result in enumerate(_batched_process_map(run_one, jobs, args.workers), 1):
        counts[result['status']] = counts.get(result['status'], 0) + 1
        print(json.dumps({'completed': n, **result}), flush=True)
    print(json.dumps({'finished': now(), 'counts': counts}), flush=True)


if __name__ == '__main__':
    main()
