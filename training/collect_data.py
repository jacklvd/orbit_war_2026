#!/usr/bin/env python3
"""Collect attack decision data for ML shot validator training.

Two auto-discovered opponent pools:

  league/       Proto-agent snapshots frozen with training/freeze_agent.py.
                Teaches the validator what works against our own past strategy.
                File pattern: proto_agent_v*.py

  opponents/    External competitor agents (any *.py).
                Drop any strong Kaggle competitor here to train against them.

Opponent mix (with L league agents, C competitor agents):
  self-play      25%   proto vs proto     — hardest, exposes own weaknesses
  league/*       30%   proto vs past      — prevents forgetting, split evenly
  opponents/*    25%   proto vs external  — learns real competition pressure
  alt_agent      12%   proto vs rusher    — keeps expansion discipline
  main_agent      8%   proto vs similar   — baseline sanity

Missing pools are redistributed proportionally to the ones present.

Output: training/attack_log.csv

Usage:
    python3 training/collect_data.py
    python3 training/collect_data.py --games 500
    python3 training/collect_data.py --games 50   # quick sanity check
"""
import csv
import sys
import argparse
import time
import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from kaggle_environments import make
import proto_agent
import alt_agent
import main as main_agent

OUT_FILE = HERE / "attack_log.csv"

FEATURE_COLS = [
    "tprod", "tships", "towner_neutral", "turns", "to_send",
    "step", "remaining", "profit_horizon", "garrison_ratio",
    "cost_fraction", "nbr_prod", "nearby_enemy_prod", "support_dist",
    "is_ahead", "is_behind", "is_finishing",
]

# Base allocation for each pool (will be renormalised if a pool is empty)
_POOL_WEIGHTS = {
    "self-play":  0.25,
    "league":     0.30,
    "opponents":  0.25,
    "alt_agent":  0.12,
    "main_agent": 0.08,
}


def _load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # must register before exec so @dataclass can resolve cls.__module__
    spec.loader.exec_module(mod)
    return mod


def _discover(directory, pattern="*.py"):
    """Load every *.py in directory that exposes an `agent` function."""
    agents = []
    for path in sorted(Path(directory).glob(pattern)):
        if path.name.startswith("__"):
            continue
        try:
            mod = _load_mod(str(path), path.stem)
            if hasattr(mod, "agent"):
                agents.append((mod.agent, path.stem))
        except Exception as exc:
            print(f"  Warning: could not load {path.name}: {exc}")
    return agents


def _build_opponents(league_agents, competitor_agents):
    """Build normalised opponent list from discovered pools."""
    # Decide which pools are live
    pools = {
        "self-play":  [(proto_agent.agent, "self-play")],
        "alt_agent":  [(alt_agent.agent,   "alt_agent")],
        "main_agent": [(main_agent.agent,  "main_agent")],
        "league":     league_agents,
        "opponents":  competitor_agents,
    }
    live   = {k: v for k, v in pools.items() if v}
    dead   = {k for k in _POOL_WEIGHTS if k not in live}

    # Redistribute dead pool weight proportionally among live pools
    dead_w = sum(_POOL_WEIGHTS[k] for k in dead)
    live_w = sum(_POOL_WEIGHTS[k] for k in live)
    scale  = (live_w + dead_w) / live_w if live_w > 0 else 1.0

    result = []
    for pool_name, agents in live.items():
        pool_frac = _POOL_WEIGHTS[pool_name] * scale
        per_agent = pool_frac / len(agents)
        for fn, label in agents:
            result.append((fn, label, per_agent))

    # Normalise to exactly 1.0 (floating-point safety)
    total = sum(f for _, _, f in result)
    result = [(fn, lbl, f / total) for fn, lbl, f in result]
    return result


def _pick_opponent(game_idx, n_games, opponents):
    cumulative = 0.0
    thresholds = []
    for fn, label, frac in opponents:
        cumulative += frac
        thresholds.append((cumulative, fn, label))
    slot = (game_idx % n_games) / n_games
    for threshold, fn, label in thresholds:
        if slot < threshold:
            return fn, label
    return opponents[-1][0], opponents[-1][1]


def run_game(game_idx, n_games, opponents):
    proto_agent._log_buffer.clear()
    opponent_fn, opp_label = _pick_opponent(game_idx, n_games, opponents)

    if game_idx % 2 == 0:
        agents, proto_pid = [proto_agent.agent, opponent_fn], 0
    else:
        agents, proto_pid = [opponent_fn, proto_agent.agent], 1

    env = make("orbit_wars", debug=False)
    env.run(agents)

    history = {}
    for step_data in env.steps:
        obs = step_data[proto_pid]["observation"]
        s   = obs.get("step", 0) or 0
        history[s] = {p[0]: p[1] for p in obs.get("planets", [])}

    records = []
    for rec in proto_agent._log_buffer:
        future = [s for s in history if s >= rec["label_step"]]
        if not future:
            label = 0
        else:
            owner = history[min(future)].get(rec["tid"], -2)
            label = 1 if owner == proto_pid else 0
        row = {col: rec[col] for col in FEATURE_COLS}
        row["label"]    = label
        row["game_id"]  = game_idx
        row["opponent"] = opp_label
        records.append(row)

    return records, opp_label


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games",     type=int, default=350)
    parser.add_argument("--league",    default=str(ROOT / "league"))
    parser.add_argument("--opponents", default=str(ROOT / "opponents"))
    parser.add_argument("--out",       default=str(OUT_FILE))
    args = parser.parse_args()

    print("Discovering league agents (proto snapshots)...")
    league_agents = _discover(args.league, "proto_agent_v*.py")
    for _, label in league_agents:
        print(f"  + {label}")
    if not league_agents:
        print("  (none — self-play absorbs league share)")

    print("Discovering competitor agents...")
    competitor_agents = _discover(args.opponents)
    for _, label in competitor_agents:
        print(f"  + {label}")
    if not competitor_agents:
        print("  (none — drop *.py files into opponents/ to add)")

    opponents   = _build_opponents(league_agents, competitor_agents)
    n_games     = args.games
    opp_summary = "  ".join(f"{lbl} {frac*100:.0f}%" for _, lbl, frac in opponents)
    print(f"\nRunning {n_games} games  [{opp_summary}]")
    print(f"Estimated time: {n_games * 2 / 60:.0f}–{n_games * 6 / 60:.0f} min\n")

    proto_agent._logging_enabled = True
    all_rows   = []
    opp_counts = {lbl: 0 for _, lbl, _ in opponents}
    t_start    = time.time()

    try:
        for i in range(n_games):
            rows, opp_label = run_game(i, n_games, opponents)
            all_rows.extend(rows)
            opp_counts[opp_label] += 1

            if (i + 1) % 25 == 0 or i == n_games - 1:
                elapsed = time.time() - t_start
                window  = all_rows[-2000:]
                cap_r   = sum(r["label"] for r in window) / max(1, len(window))
                eta_s   = elapsed / (i + 1) * (n_games - i - 1)
                print(f"  Game {i+1:4d}/{n_games} | "
                      f"records: {len(all_rows):7,d} | "
                      f"capture rate: {cap_r:.1%} | "
                      f"ETA: {eta_s / 60:.1f} min")
    finally:
        proto_agent._logging_enabled = False

    total_time   = time.time() - t_start
    capture_rate = sum(r["label"] for r in all_rows) / max(1, len(all_rows))
    print(f"\nDone in {total_time / 60:.1f} min")
    print(f"Total records  : {len(all_rows):,}")
    print(f"Overall capture: {capture_rate:.1%}")
    print("Games by opponent:")
    for _, lbl, _ in opponents:
        print(f"  {lbl:35s}: {opp_counts.get(lbl, 0)} games")

    fieldnames = FEATURE_COLS + ["label", "game_id", "opponent"]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved → {args.out}")
    print("Next step: python3 training/train_validator.py")


if __name__ == "__main__":
    main()
