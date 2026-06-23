#!/usr/bin/env python3
"""Quick benchmark with mid-game diagnostic snapshots.

Runs N games between proto_agent and a chosen opponent, captures a
state snapshot at a configurable turn (default 50), and prints per-game
stats plus a win/loss breakdown so you can see *where* games diverge.

Usage:
    python3 benchmark.py                        # 40 games vs heuristic
    python3 benchmark.py --opponent main_agent  # vs main_agent
    python3 benchmark.py --games 80 --snap 100  # 80 games, snapshot at turn 100
    python3 benchmark.py --opponent 1103_opponent --games 60
"""

import argparse
import importlib.util
import sys
import math
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from kaggle_environments import make
import proto_agent

OPPONENT_PATHS = {
    "heuristic":    ROOT / "opponents" / "heuristic.py",
    "main_agent":   ROOT / "main.py",
    "alt_agent":    ROOT / "alt_agent.py",
    "1103_opponent": ROOT / "opponents" / "1103_opponent.py",
    "marco":        ROOT / "opponents" / "marco_dg_v3_3_top_score_1060_5.py",
    "another1000":  ROOT / "opponents" / "another1000_lb.py",
    "launch_safety_1039": ROOT / "opponents" / "launch_safety_1039.py",
    "heuristic_sim_1000": ROOT / "opponents" / "heuristic_sim_1000.py",
    "heuristic_sim_1050": ROOT / "opponents" / "heuristic_sim_1050.py",
}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _snap(obs, player):
    """Extract planet/ship/prod counts for both sides from one observation."""
    planets = obs.get("planets", [])
    fleets  = obs.get("fleets", [])

    my_p    = [p for p in planets if p[1] == player]
    en_p    = [p for p in planets if p[1] != player and p[1] != -1]
    neutral = [p for p in planets if p[1] == -1]

    my_transit = sum(f[6] for f in fleets if f[1] == player)
    en_transit = sum(f[6] for f in fleets if f[1] != player and f[1] != -1)

    return {
        "my_planets":  len(my_p),
        "en_planets":  len(en_p),
        "neutrals":    len(neutral),
        "my_ships":    sum(p[5] for p in my_p),
        "en_ships":    sum(p[5] for p in en_p),
        "my_transit":  my_transit,
        "en_transit":  en_transit,
        "my_prod":     sum(p[6] for p in my_p),
        "en_prod":     sum(p[6] for p in en_p),
    }


def run_game(proto_fn, opp_fn, proto_first, snap_turn, num_players=2, opp_fn2=None, opp_fn3=None):
    if num_players == 4:
        proto_pid = proto_first % 4  # rotate through all 4 positions
        if opp_fn3 is not None:
            # 1x each: proto + opp1 + opp2 + opp3
            slots = [opp_fn, opp_fn2, opp_fn3]
        else:
            # 2x opp1 + 1x opp2 (or 3x opp1 if no opp2)
            opp2 = opp_fn2 if opp_fn2 is not None else opp_fn
            slots = [opp_fn, opp_fn, opp2]
        agents = slots[:]
        agents.insert(proto_pid, proto_fn)  # insert proto at its position, shift rest
        agents = agents[:4]  # trim to 4
    elif proto_first:
        agents, proto_pid = [proto_fn, opp_fn], 0
    else:
        agents, proto_pid = [opp_fn, proto_fn], 1

    env = make("orbit_wars", debug=False)
    env.run(agents)

    snapshot = None
    final_obs = None

    for game_step, step_data in enumerate(env.steps):
        obs = step_data[proto_pid]["observation"]
        s   = obs.get("step") or game_step
        if snapshot is None and s >= snap_turn:
            snapshot = _snap(obs, proto_pid)
        final_obs = obs

    if final_obs is None:
        return None, None

    planets = final_obs.get("planets", [])
    my_ships   = sum(p[5] for p in planets if p[1] == proto_pid)
    my_planets = sum(1   for p in planets if p[1] == proto_pid)

    if num_players == 4:
        # Win = ranked 1st (most ships); or tied-first on ships by most planets
        all_ships = {}
        all_planets = {}
        for p in planets:
            pid = p[1]
            if pid == -1:
                continue
            all_ships[pid]   = all_ships.get(pid, 0) + p[5]
            all_planets[pid] = all_planets.get(pid, 0) + 1
        rank1_ships = max(all_ships.values(), default=0)
        won = (my_ships == rank1_ships and
               my_planets >= max((all_planets.get(pid, 0) for pid, s in all_ships.items() if s == rank1_ships), default=0))
    else:
        opp_pid = 1 - proto_pid
        en_ships   = sum(p[5] for p in planets if p[1] == opp_pid)
        en_planets = sum(1   for p in planets if p[1] == opp_pid)
        won = my_ships > en_ships or (my_ships == en_ships and my_planets >= en_planets)

    return won, snapshot


def fmt(v, width=6):
    return str(v).rjust(width)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--opponent", default="heuristic",
                        help="Opponent name: " + ", ".join(OPPONENT_PATHS))
    parser.add_argument("--games",    type=int, default=40)
    parser.add_argument("--snap",     type=int, default=50,
                        help="Turn to capture mid-game snapshot (default 50)")
    parser.add_argument("--players",   type=int, default=2, choices=[2, 4],
                        help="Number of players: 2 (default) or 4 (FFA)")
    parser.add_argument("--opponent2", default=None,
                        help="Second opponent for 4P mix. "
                             "4P layout (no --opponent3): proto + 2x opponent + 1x opponent2")
    parser.add_argument("--opponent3", default=None,
                        help="Third opponent for 4P mix. "
                             "4P layout (with --opponent3): proto + 1x each of opponent/opponent2/opponent3")
    args = parser.parse_args()

    opp_path = OPPONENT_PATHS.get(args.opponent)
    if opp_path is None:
        opp_path = Path(args.opponent)
    if not opp_path.exists():
        print(f"Opponent not found: {args.opponent}")
        print("Available:", ", ".join(OPPONENT_PATHS))
        sys.exit(1)

    opp_mod  = _load(str(opp_path), args.opponent)
    opp_fn   = opp_mod.agent
    proto_fn = proto_agent.agent

    opp_fn2 = None
    if args.opponent2:
        opp2_path = OPPONENT_PATHS.get(args.opponent2)
        if opp2_path is None:
            opp2_path = Path(args.opponent2)
        if not opp2_path.exists():
            print(f"Opponent2 not found: {args.opponent2}")
            sys.exit(1)
        opp2_mod = _load(str(opp2_path), args.opponent2 + "_2")
        opp_fn2  = opp2_mod.agent

    opp_fn3 = None
    if args.opponent3:
        opp3_path = OPPONENT_PATHS.get(args.opponent3)
        if opp3_path is None:
            opp3_path = Path(args.opponent3)
        if not opp3_path.exists():
            print(f"Opponent3 not found: {args.opponent3}")
            sys.exit(1)
        opp3_mod = _load(str(opp3_path), args.opponent3 + "_3")
        opp_fn3  = opp3_mod.agent

    mode = f"{args.players}P FFA" if args.players == 4 else "2P"
    if args.players == 4 and opp_fn3:
        mode = f"4P FFA (1x{args.opponent} + 1x{args.opponent2} + 1x{args.opponent3})"
    elif args.players == 4 and opp_fn2:
        mode = f"4P FFA (2x{args.opponent} + 1x{args.opponent2})"
    print(f"Benchmarking proto_agent vs {args.opponent}  "
          f"({args.games} games, {mode}, snapshot @ turn {args.snap})\n")

    proto_agent._logging_enabled = False

    wins = 0
    snaps_win  = []
    snaps_loss = []

    COL = ("game", "result", "T50 my_pl", "T50 en_pl", "neut",
           "my_ships", "en_ships", "my_prod", "en_prod",
           "pl_adv", "ship_adv", "prod_adv")
    header = (f"{'#':>4}  {'res':>4}  "
              f"{'my_pl':>5} {'en_pl':>5} {'neut':>4}  "
              f"{'my_sh':>6} {'en_sh':>6}  "
              f"{'my_tr':>6} {'en_tr':>6}  "
              f"{'my_tot':>6} {'en_tot':>6}  "
              f"{'my_pr':>5} {'en_pr':>5}")
    print(header)
    print("-" * len(header))

    for i in range(args.games):
        proto_first = i % (args.players if args.players == 4 else 2)
        won, snap = run_game(proto_fn, opp_fn, proto_first, args.snap,
                             num_players=args.players, opp_fn2=opp_fn2, opp_fn3=opp_fn3)
        if won is None:
            continue

        if won:
            wins += 1
        res = "WIN " if won else "LOSS"

        if snap:
            d_pl   = snap["my_planets"] - snap["en_planets"]
            d_sh   = snap["my_ships"]   - snap["en_ships"]
            d_pr   = snap["my_prod"]    - snap["en_prod"]

            my_tot = snap['my_ships'] + snap['my_transit']
            en_tot = snap['en_ships'] + snap['en_transit']
            print(f"{i+1:>4}  {res}  "
                  f"{snap['my_planets']:>5} {snap['en_planets']:>5} {snap['neutrals']:>4}  "
                  f"{snap['my_ships']:>6} {snap['en_ships']:>6}  "
                  f"{snap['my_transit']:>6} {snap['en_transit']:>6}  "
                  f"{my_tot:>6} {en_tot:>6}  "
                  f"{snap['my_prod']:>5} {snap['en_prod']:>5}")

            if won:
                snaps_win.append(snap)
            else:
                snaps_loss.append(snap)
        else:
            print(f"{i+1:>4}  {res}  (no snapshot — game ended before turn {args.snap})")

    total = wins + (args.games - wins)
    print("-" * len(header))
    print(f"\nResult: {wins}/{args.games} wins  ({wins/args.games:.0%})\n")

    def avg(snaps, key):
        if not snaps:
            return 0.0
        return sum(s[key] for s in snaps) / len(snaps)

    if snaps_win or snaps_loss:
        print(f"  {'':20s}  {'WINS':>8}  {'LOSSES':>8}  {'DIFF':>8}")
        for key in ("my_planets", "en_planets", "neutrals",
                    "my_ships", "en_ships", "my_transit", "en_transit",
                    "my_prod", "en_prod"):
            w = avg(snaps_win,  key)
            l = avg(snaps_loss, key)
            print(f"  {key:18s}  {w:8.1f}  {l:8.1f}  {w-l:+8.1f}")

        # Derived totals
        w_tot_my = avg(snaps_win, "my_ships") + avg(snaps_win, "my_transit")
        l_tot_my = avg(snaps_loss,"my_ships") + avg(snaps_loss,"my_transit")
        w_tot_en = avg(snaps_win, "en_ships") + avg(snaps_win, "en_transit")
        l_tot_en = avg(snaps_loss,"en_ships") + avg(snaps_loss,"en_transit")
        print(f"\n  {'my_total(pl+tr)':18s}  {w_tot_my:8.1f}  {l_tot_my:8.1f}  {w_tot_my-l_tot_my:+8.1f}")
        print(f"  {'en_total(pl+tr)':18s}  {w_tot_en:8.1f}  {l_tot_en:8.1f}  {w_tot_en-l_tot_en:+8.1f}")

        w_adv = avg(snaps_win,  "my_planets") - avg(snaps_win,  "en_planets")
        l_adv = avg(snaps_loss, "my_planets") - avg(snaps_loss, "en_planets")
        s_adv_w = w_tot_my - w_tot_en
        s_adv_l = l_tot_my - l_tot_en
        print(f"\n  Planet advantage @ T{args.snap}:  wins={w_adv:+.1f}  losses={l_adv:+.1f}")
        print(f"  Total ship adv   @ T{args.snap}:  wins={s_adv_w:+.1f}  losses={s_adv_l:+.1f}")


if __name__ == "__main__":
    main()
