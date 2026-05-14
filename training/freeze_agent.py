#!/usr/bin/env python3
"""Snapshot proto_agent.py into league/ for league self-play training.

Each frozen snapshot becomes a permanent training opponent.  Run this
whenever the agent reaches a new performance milestone worth preserving.

Usage:
    python3 training/freeze_agent.py
    python3 training/freeze_agent.py --name proto_agent_v2.0
"""
import shutil
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _next_version(league_dir):
    existing = sorted(league_dir.glob("proto_agent_v*.py"))
    nums = []
    for f in existing:
        m = re.search(r"v(\d+(?:\.\d+)?)", f.stem)
        if m:
            nums.append(float(m.group(1)))
    return round(max(nums) + 0.1, 1) if nums else 0.2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default=None,
                        help="Override snapshot filename (without .py)")
    args = parser.parse_args()

    src       = ROOT / "proto_agent.py"
    league    = ROOT / "league"
    league.mkdir(exist_ok=True)

    if args.name:
        stem = args.name if args.name.endswith(".py") else args.name + ".py"
        dst  = league / stem
    else:
        ver = _next_version(league)
        dst = league / f"proto_agent_v{ver:.1f}.py"

    shutil.copy(src, dst)
    snapshots = sorted(league.glob("*.py"))
    print(f"Frozen  : proto_agent.py → league/{dst.name}")
    print(f"League  : {len(snapshots)} agent(s) total")
    for s in snapshots:
        print(f"  {s.name}")
    print("\nNext: python3 training/collect_data.py")


if __name__ == "__main__":
    main()
