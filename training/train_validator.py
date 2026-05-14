#!/usr/bin/env python3
"""Train a CART decision tree shot validator from training/attack_log.csv.

Pure numpy — no sklearn required.

Outputs Python constants to paste into proto_agent.py:
    _TREE_FEATURE / _TREE_THRESHOLD / _TREE_LEFT / _TREE_RIGHT
    _TREE_VALUE / _TREE_BASELINE

Usage:
    python3 training/train_validator.py
    python3 training/train_validator.py --depth 8 --samples 300000
"""
import csv
import argparse
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent

FEATURE_COLS = [
    "tprod", "tships", "towner_neutral", "turns", "to_send",
    "step", "remaining", "profit_horizon", "garrison_ratio",
    "cost_fraction", "nbr_prod", "nearby_enemy_prod", "support_dist",
    "is_ahead", "is_behind", "is_finishing",
]


# ── CART decision tree ────────────────────────────────────────────────────────

def _gini(y):
    n = len(y)
    if n == 0:
        return 0.0
    p = y.sum() / n
    return 2.0 * p * (1.0 - p)


def _best_split(X, y, min_leaf=50, n_thresholds=32):
    best_gain, best_feat, best_thr = -1.0, -1, 0.0
    n        = len(y)
    g_parent = _gini(y)
    for f in range(X.shape[1]):
        col  = X[:, f]
        lo, hi = col.min(), col.max()
        if lo == hi:
            continue
        for thr in np.linspace(lo, hi, n_thresholds + 2)[1:-1]:
            left  = y[col <= thr]
            right = y[col >  thr]
            if len(left) < min_leaf or len(right) < min_leaf:
                continue
            gain = g_parent - (
                len(left) * _gini(left) + len(right) * _gini(right)
            ) / n
            if gain > best_gain:
                best_gain, best_feat, best_thr = gain, f, float(thr)
    return best_feat, best_thr, best_gain


def _build_tree(X, y, max_depth, min_leaf=50, n_thresholds=32):
    nodes = []

    def _recurse(X_sub, y_sub, depth):
        node_id = len(nodes)
        nodes.append(None)
        val = float(y_sub.mean()) if len(y_sub) > 0 else 0.0
        n   = len(y_sub)

        if depth >= max_depth or n < 2 * min_leaf:
            nodes[node_id] = {"feature": -1, "threshold": 0.0,
                              "left": -1, "right": -1, "value": val, "n": n}
            return node_id

        feat, thr, gain = _best_split(X_sub, y_sub, min_leaf, n_thresholds)
        if feat == -1 or gain < 1e-8:
            nodes[node_id] = {"feature": -1, "threshold": 0.0,
                              "left": -1, "right": -1, "value": val, "n": n}
            return node_id

        mask     = X_sub[:, feat] <= thr
        left_id  = _recurse(X_sub[mask],  y_sub[mask],  depth + 1)
        right_id = _recurse(X_sub[~mask], y_sub[~mask], depth + 1)
        nodes[node_id] = {"feature": feat, "threshold": thr,
                          "left": left_id, "right": right_id,
                          "value": val, "n": n}
        return node_id

    _recurse(X, y, 0)
    return nodes


def _predict_proba(nodes, X):
    probs = np.empty(len(X))
    for i, row in enumerate(X):
        node = 0
        while nodes[node]["feature"] != -1:
            f, thr = nodes[node]["feature"], nodes[node]["threshold"]
            node   = nodes[node]["left"] if row[f] <= thr else nodes[node]["right"]
        probs[i] = nodes[node]["value"]
    return probs


def evaluate(nodes, X, y, threshold=0.5):
    p    = _predict_proba(nodes, X)
    pred = (p >= threshold).astype(int)
    acc  = (pred == y).mean()
    tp   = ((pred == 1) & (y == 1)).sum()
    fp   = ((pred == 1) & (y == 0)).sum()
    fn   = ((pred == 0) & (y == 1)).sum()
    prec = tp / max(1, tp + fp)
    rec  = tp / max(1, tp + fn)
    f1   = 2 * prec * rec / max(1e-9, prec + rec)
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


# ── Data loading ─────────────────────────────────────────────────────────────

def load_csv(path):
    X_rows, y_rows = [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            X_rows.append([float(row[c]) for c in FEATURE_COLS])
            y_rows.append(int(row["label"]))
    return (np.array(X_rows, dtype=np.float64),
            np.array(y_rows, dtype=np.float64))


def stratified_split(X, y, test_frac=0.2, seed=42):
    rng    = np.random.default_rng(seed)
    pos_i  = np.where(y == 1)[0]
    neg_i  = np.where(y == 0)[0]
    tp     = rng.choice(pos_i, int(len(pos_i) * test_frac), replace=False)
    tn     = rng.choice(neg_i, int(len(neg_i) * test_frac), replace=False)
    test_i = np.concatenate([tp, tn])
    mask   = np.ones(len(y), dtype=bool)
    mask[test_i] = False
    return X[mask], X[~mask], y[mask], y[~mask]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv",        default=str(HERE / "attack_log.csv"))
    parser.add_argument("--depth",      type=int, default=6)
    parser.add_argument("--samples",    type=int, default=200_000)
    parser.add_argument("--min-leaf",   type=int, default=50)
    parser.add_argument("--thresholds", type=int, default=32)
    args = parser.parse_args()

    print(f"Loading {args.csv}...")
    X, y = load_csv(args.csv)
    print(f"Samples: {len(y):,}  |  capture rate: {y.mean():.1%}")
    baseline = float(y.mean())

    # Class balancing
    pos_i = np.where(y == 1)[0]
    neg_i = np.where(y == 0)[0]
    if len(pos_i) < len(neg_i):
        extra = np.random.choice(pos_i, len(neg_i) - len(pos_i), replace=True)
    else:
        extra = np.random.choice(neg_i, len(pos_i) - len(neg_i), replace=True)
    X = np.concatenate([X, X[extra]])
    y = np.concatenate([y, y[extra]])

    X_tr, X_te, y_tr, y_te = stratified_split(X, y)
    print(f"Train: {len(y_tr):,}  |  Test: {len(y_te):,}")

    if args.samples > 0 and len(y_tr) > args.samples:
        idx = np.random.default_rng(42).choice(
            len(y_tr), args.samples, replace=False)
        X_tr_fit, y_tr_fit = X_tr[idx], y_tr[idx]
        print(f"Subsampled train → {len(y_tr_fit):,}")
    else:
        X_tr_fit, y_tr_fit = X_tr, y_tr

    print(f"\nBuilding CART tree  (depth={args.depth}, "
          f"min_leaf={args.min_leaf}, thresholds={args.thresholds})...")
    np.random.seed(42)
    nodes    = _build_tree(X_tr_fit, y_tr_fit,
                           max_depth=args.depth,
                           min_leaf=args.min_leaf,
                           n_thresholds=args.thresholds)
    n_leaves = sum(1 for nd in nodes if nd["feature"] == -1)
    print(f"Tree built: {len(nodes)} nodes, {n_leaves} leaves")

    tr_met = evaluate(nodes, X_tr, y_tr)
    te_met = evaluate(nodes, X_te, y_te)
    print(f"\nTrain  acc={tr_met['accuracy']:.3f}  "
          f"prec={tr_met['precision']:.3f}  "
          f"rec={tr_met['recall']:.3f}  f1={tr_met['f1']:.3f}")
    print(f"Test   acc={te_met['accuracy']:.3f}  "
          f"prec={te_met['precision']:.3f}  "
          f"rec={te_met['recall']:.3f}  f1={te_met['f1']:.3f}")

    counts  = [0] * len(FEATURE_COLS)
    for nd in nodes:
        if nd["feature"] != -1:
            counts[nd["feature"]] += 1
    max_c = max(counts) if max(counts) > 0 else 1
    print("\nFeature use counts (split frequency):")
    for name, c in sorted(zip(FEATURE_COLS, counts),
                           key=lambda x: x[1], reverse=True):
        bar = "█" * int(c * 20 / max_c) if c > 0 else ""
        print(f"  {name:20s}  {c:3d}  {bar}")

    def _fmt(lst, fmt=".6f"):
        return "[" + ", ".join(format(v, fmt) for v in lst) + "]"

    print("\n" + "=" * 70)
    print("Paste these lines into proto_agent.py")
    print("(replacing the existing _TREE_* constants)")
    print("=" * 70)
    print(f"_TREE_FEATURE   = {_fmt([nd['feature']   for nd in nodes], 'd')}")
    print(f"_TREE_THRESHOLD = {_fmt([nd['threshold'] for nd in nodes])}")
    print(f"_TREE_LEFT      = {_fmt([nd['left']      for nd in nodes], 'd')}")
    print(f"_TREE_RIGHT     = {_fmt([nd['right']     for nd in nodes], 'd')}")
    print(f"_TREE_VALUE     = {_fmt([nd['value']     for nd in nodes])}")
    print(f"_TREE_BASELINE  = {baseline:.6f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
