#!/usr/bin/env python3
"""Bake the two enemy-stock holdability submissions from the live orbit_v2.

Each stage = a copy of orbit_v2/{main.py, orbit_lite} with the config flags
baked into BOTH CONFIG_2P and CONFIG_4P (inserted right after
``ProducerLiteConfig(),`` in each ``dataclasses.replace`` call — the baked
fields are all NEW fields, so there is no kwarg collision with the existing
``reinforce_margin_frac=0.6`` etc.).
"""
import shutil
from pathlib import Path

HERE = Path(__file__).parent
ANCHOR = "    ProducerLiteConfig(),\n"

# name -> baked field lines (applied to both 2P and 4P configs)
SUBMISSIONS = {
    "s1_veto": [
        "margin_hold_turns=8.0",
        "enable_hold_veto=True",
        "veto_hold_H=8",
        "stock_reach_turns=8",
    ],
    "s2_veto_floor": [
        "margin_hold_turns=8.0",
        "enable_hold_veto=True",
        "veto_hold_H=8",
        "stock_reach_turns=8",
        "enable_stock_floor=True",
        "stock_frac=1.0",
    ],
}


def build_asym(name, fields, frac4p):
    """S2-base in 2P (conservative), but override CONFIG_4P's
    reinforce_margin_frac to ``frac4p`` (combat-tempo finding 2026-06-17:
    4P margin sweep peaks at 0.0 — full enemy-attack tempo wins +5pp vs the
    external pool; 2P stays conservative). Bakes ``fields`` into BOTH configs
    then rewrites ONLY the 4P frac."""
    stage = HERE / f"stage_{name}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    shutil.copytree(HERE / "orbit_lite", stage / "orbit_lite",
                    ignore=shutil.ignore_patterns("__pycache__"))
    src = (HERE / "main.py").read_text()
    assert src.count(ANCHOR) == 2, f"expected 2 anchors, found {src.count(ANCHOR)}"
    insert = "".join(f"    {f},\n" for f in fields)
    baked = src.replace(ANCHOR, ANCHOR + insert)
    marker = "\nCONFIG_4P ="
    i = baked.index(marker)
    head, tail = baked[:i], baked[i:]          # tail = the CONFIG_4P block onward
    old = "reinforce_margin_frac=0.6,"
    assert tail.count(old) == 1, f"4P frac lines in tail: {tail.count(old)}"
    tail = tail.replace(old, f"reinforce_margin_frac={frac4p},")
    (stage / "main.py").write_text(head + tail)
    print(f"built stage_{name}: 2P=conservative(frac0.6), 4P frac={frac4p}")
    return stage


def build(name, fields):
    stage = HERE / f"stage_{name}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    shutil.copytree(HERE / "orbit_lite", stage / "orbit_lite",
                    ignore=shutil.ignore_patterns("__pycache__"))
    src = (HERE / "main.py").read_text()
    insert = "".join(f"    {f},\n" for f in fields)
    baked = src.replace(ANCHOR, ANCHOR + insert)
    n = src.count(ANCHOR)
    assert n == 2, f"expected 2 ProducerLiteConfig() anchors, found {n}"
    (stage / "main.py").write_text(baked)
    print(f"built stage_{name}: baked {len(fields)} fields into {n} configs")
    return stage


if __name__ == "__main__":
    for name, fields in SUBMISSIONS.items():
        build(name, fields)
    # Combat-tempo candidate: S2 conservative 2P + aggressive (margin=0) 4P.
    build_asym("s2_4paggro", SUBMISSIONS["s2_veto_floor"], frac4p=0.0)
