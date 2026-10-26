"""Research-only category-pooling ablation. Never exports a production model.

Sweep category-prior precision independently for level and log slope. Zero uses
the raw category line; one reproduces the current fit; infinity uses the pooled
event posterior. Event-to-geometry regularization and course-noise estimates stay
fixed. Missing category lines retain their existing fallback. Select on validation
only, then evaluate the frozen shortlist on test and harder holdouts.
Private pairs and fitted objects are cached only under ignored target/.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np

import evaluate_and_train as e
from window_experiment import probe_pair

STRENGTHS = (0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0, math.inf)


def adjust(raw: tuple[float, float], post: e.Posterior, strength: float) -> e.Posterior:
    """Multiply the original category prior's precision, holding its mean fixed."""
    value, variance = raw
    share = post.own_share
    if strength == 1:
        return post
    if strength == 0:
        return e.Posterior(value, variance, 1.0)
    prior_value = (post.value - share * value) / (1 - share)
    prior_var = share * variance / (1 - share)
    if math.isinf(strength):
        return e.Posterior(prior_value, prior_var, 0.0)
    new_share = share / (share + strength * (1 - share))
    return e.Posterior(new_share * value + (1 - new_share) * prior_value,
                       new_share * variance, new_share)


def groups(train):
    out = defaultdict(list)
    canonical = {f'{a}->{b}' for a, b in e.COURSE_PAIRS}
    weights = e.swimmer_weights([p for p in train if p.direction in canonical])
    rows = [p for p in train if p.direction in canonical]
    for p, w in zip(rows, weights):
        out[(p.direction, p.event_key, p.category)].append(
            (math.log(p.source_time_cs / 100), math.log(p.target_time_cs / 100), w))
    return out


def variant(base, grouped, level, slope):
    model = copy.deepcopy(base)
    for key, line in base.lines.items():
        if key[2] == 'all':
            continue
        model.shift_post[key] = adjust((line.shift, line.shift_var), base.shift_post[key], level)
        model.slope_post[key] = adjust((line.log_slope, line.log_slope_var), base.slope_post[key], slope)
    for event, category in model.tables:
        model.linear[(event, category)] = model._reconcile(event, category)
        model.tables[(event, category)] = model._course_tables(event, category, grouped)
    return model


def shared_curve(base, grouped):
    """One common event curve, including common centers and support, for both categories.

    Unlike infinite category-prior precision alone, this also removes the raw
    category centers. Use event posteriors directly, preserving event regularization.
    """
    model = copy.deepcopy(base)
    pooled_groups = defaultdict(list)
    for (direction, event, _), rows in grouped.items():
        for category in e.CATEGORIES:
            pooled_groups[(direction, event, category)].extend(rows)
    for key in model.shift_post:
        direction, event, _ = key
        pooled_key = (direction, event, 'all')
        if pooled_key not in base.lines:
            continue
        model.lines[key] = base.lines[pooled_key]
        model.shift_post[key] = base.event_shift_post[pooled_key]
        available = next(k for k in base.slope_post
                         if k[:2] == key[:2] and k in base.lines)
        post = base.slope_post[available]
        raw = base.lines[available]
        prior = adjust((raw.log_slope, raw.log_slope_var), post, math.inf)
        model.slope_post[key] = e.Posterior(prior.value,
            max(1e-12, prior.var - base.tau2[direction]['category_log_slope']), 0.)
    for event, category in model.tables:
        model.linear[(event, category)] = model._reconcile(event, category)
        model.tables[(event, category)] = model._course_tables(event, category, pooled_groups)
    for event in e.CANONICAL_EVENT_ORDER:
        assert model.tables[(event, 'women')] == model.tables[(event, 'men')]
    return model


def predict(model, pairs):
    """Vectorized engine arithmetic; checked against scalar predictions before sweep."""
    indices = defaultdict(list)
    for i, p in enumerate(pairs):
        indices[(p.event_key, p.category, p.source_course, p.target_course)].append(i)
    out = np.empty(len(pairs), dtype=np.int64)
    for (event, category, src, dst), ix in indices.items():
        x = np.log(np.array([pairs[i].source_time_cs for i in ix]) / 100)
        tables = model.tables[(event, category)]
        latent = e.knot_map_np(tables[src], x, True)
        y = e.knot_map_np(tables[dst], latent, False)
        out[ix] = np.floor(np.exp(y) * 100 + 1e-8).astype(np.int64)
    return out


def metrics(pairs, pred):
    target = np.array([p.target_time_cs for p in pairs])
    err = (pred - target) / 100
    def one(ix):
        return {'rows': len(ix), 'mae': round(float(np.abs(err[ix]).mean()), 6),
                'bias_seconds': round(float(err[ix].mean()), 6),
                'bias_log_percent': round(float((100 * np.log(pred[ix] / target[ix])).mean()), 6)}
    out = {'overall': one(np.arange(len(pairs)))}
    for field in ('category', 'event_key', 'direction', 'age_band'):
        sub = defaultdict(list)
        for i, p in enumerate(pairs):
            sub[getattr(p, field)].append(i)
        out[field] = {k: one(v) for k, v in sorted(sub.items())}
    sub = defaultdict(list)
    for i, p in enumerate(pairs):
        sub[f'{p.event_key}|{p.category}'].append(i)
    out['event_category'] = {k: one(v) for k, v in sorted(sub.items())}
    return out


def name(level, slope):
    return f'level={level:g},slope={slope:g}'


def prepare(db, cache):
    receipt = json.loads((e.ROOT / 'research/conversion-model/evaluation-checkpoint-08.json').read_text())
    measured = e.measure_lakehouse_view(db)
    assert measured['iceberg_snapshot_id'] == receipt['input_provenance']['iceberg_snapshot_id']
    print('Loading pinned swims', flush=True)
    swims = e.load_swims_from_duckdb(db)
    digest = e.compute_swims_sha256(swims)
    assert digest == receipt['input_provenance']['loaded_swims_sha256']
    print('Verified input hash; reducing rounds', flush=True)
    dedup, _ = e.deduplicate_best_of_meet(swims)
    del swims
    print('Building pairs and repeats', flush=True)
    pairs = e.build_directional_pairs(dedup, max_days=30)
    repeats = e.build_repeat_swims(dedup, max_days=30)
    del dedup
    train = [p for p in pairs if p.partition == 'train' and not p.is_ratio_outlier]
    val = [p for p in pairs if p.partition == 'validation' and not p.is_ratio_outlier]
    test = [p for p in pairs if p.partition == 'test' and not p.is_ratio_outlier]
    datasets = {'main': (train, val, test, [r for r in repeats if r.partition == 'train'])}
    for label, splitter in [('temporal', e.temporal_holdout_splits), ('regions', e.leave_regions_out_splits)]:
        tr, te, rep = splitter(pairs, repeats)
        datasets[label] = ([p for p in tr if not p.is_ratio_outlier], [],
                           [p for p in te if not p.is_ratio_outlier], rep)
    fitted = {}
    for label, (tr, va, te, rep) in datasets.items():
        print(f'Fitting {label}: train={len(tr)}, validation={len(va)}, test={len(te)}', flush=True)
        base = e.EquivalenceModel()
        base.fit(tr, e.estimate_course_noise(rep))
        fitted[label] = (base, groups(tr), va, te)
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open('wb') as f:
        pickle.dump((digest, fitted), f)
    return digest, fitted


def run(args):
    cache = args.output / 'private-fit-cache.pkl'
    if cache.exists():
        with cache.open('rb') as f:
            digest, fitted = pickle.load(f)
    else:
        digest, fitted = prepare(args.duckdb, cache)
    pinned = json.loads((e.ROOT / 'research/conversion-model/evaluation-checkpoint-08.json').read_text())
    assert digest == pinned['input_provenance']['loaded_swims_sha256']
    base, grouped, val, test = fitted['main']
    assert base.export_snapshot_dict('', '')['cells'] == json.loads((e.ROOT / 'data/empirical.json').read_text())['cells']
    for pairs in (val, test):
        fast = predict(base, pairs)
        assert np.array_equal(fast, [base.predict(p) for p in pairs]), 'Vectorized/scalar mismatch'
    main_metrics = metrics(test, predict(base, test))
    assert abs(main_metrics['overall']['mae'] - 2.7711) < 0.00006, main_metrics
    sweep = {}
    configs = list(itertools.product(STRENGTHS, repeat=2))
    for level, slope in configs:
        model = variant(base, grouped, level, slope)
        score = metrics(val, predict(model, val))
        sweep[name(level, slope)] = score
        print(f'{name(level, slope)} validation MAE={score["overall"]["mae"]}', flush=True)
    # Freeze the shortlist before accessing candidate test results.
    ordered = sorted(configs, key=lambda c: sweep[name(*c)]['overall']['mae'])
    women = min(configs, key=lambda c: sweep[name(*c)]['category']['women']['mae'])
    men = min(configs, key=lambda c: sweep[name(*c)]['category']['men']['mae'])
    shortlist = list(dict.fromkeys([(1., 1.), (0., 0.), (math.inf, math.inf),
                                  (1., 0.), (0., 1.), *ordered[:3], women, men]))
    result = {'input_sha256': digest, 'configurations': len(configs),
              'selection': 'Validation MAE only; top 3 overall plus category winners and fixed controls.',
              'limitations': 'Exploratory; existing holdouts have been examined in prior research. No nested selection, refit bootstrap, or multiplicity adjustment. Noise estimates still pool categories; event priors unchanged; missing category lines retain fallback. Infinite precision replaces category parameters with event priors but retains category centers; shared_curve separately removes category centers and uses pooled support. No production artifacts modified.',
              'validation_sweep': sweep, 'frozen_shortlist': [name(*c) for c in shortlist],
              'evaluations': {}}
    (args.output / 'selection.json').write_text(json.dumps({k: v for k, v in result.items() if k != 'evaluations'}, indent=2))
    result['shared_curve_validation'] = metrics(val, predict(shared_curve(base, grouped), val))
    probes = [('100-FR', 7000, 100, 'freestyle'), ('100-BK', 7500, 100, 'backstroke'),
              ('200-BR', 13500, 200, 'breaststroke'), ('200-FL', 15000, 200, 'butterfly')]
    result['same_entered_time_probes'] = {}
    for setting in ((1., 1.), (0., 0.), ordered[0]):
        model = variant(base, grouped, *setting)
        result['same_entered_time_probes'][name(*setting)] = {
            event: {'invented_input_seconds': cs / 100, 'source_course': 'SCY', 'target_course': 'LCM',
                    **{cat: model.predict(probe_pair(cs, distance, stroke, cat, event)) / 100
                       for cat in e.CATEGORIES}}
            for event, cs, distance, stroke in probes}
    for label, (b, g, _, rows) in fitted.items():
        baseline_pred = predict(b, rows)
        target = np.array([p.target_time_cs for p in rows])
        out = {}
        candidates = [(name(level, slope), variant(b, g, level, slope)) for level, slope in shortlist]
        candidates.append(('shared_curve', shared_curve(b, g)))
        for label_model, model in candidates:
            pred = predict(model, rows)
            score = metrics(rows, pred)
            delta = (np.abs(pred - target) - np.abs(baseline_pred - target)) / 100
            bootstrap = {}
            for cat in ('all', 'women', 'men'):
                ix = [i for i, p in enumerate(rows) if cat == 'all' or p.category == cat]
                point, boot = e.clustered_bootstrap([rows[i].swimmer_key for i in ix],
                                                    {'delta': delta[ix]}, args.bootstrap, 20261026)
                bootstrap[cat] = e._delta_summary(point['delta'], boot['delta'])
            out[label_model] = {'metrics': score, 'delta_mae_bootstrap': bootstrap}
            print(f'{label} {label_model} test MAE={score["overall"]["mae"]}', flush=True)
        result['evaluations'][label] = out
    result['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.output / 'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    print(f'Aggregate receipt: {args.output / "receipt.json"}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duckdb', type=Path, default=e.ROOT / 'target/lakehouse-national-17/queries.duckdb')
    parser.add_argument('--output', type=Path, default=e.ROOT / 'target/sharing-experiment')
    parser.add_argument('--bootstrap', type=int, default=2000)
    run(parser.parse_args())
