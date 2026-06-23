# orbit_v2 plan — path to top 10% (stable ≥1185, safe 1210)

## Status (2026-06-10 evening): READY TO SUBMIT

`orbit_v2/orbit_v2_submission.tar.gz` (main.py + orbit_lite/) is built,
verified from extraction, and passes every gate. The one change that matters:
**reactive-reinforcement margin, frac=0.6, baked into both configs.**

### Final validated results (candidate = baked main.py, no overrides)

| arm | result |
|---|---|
| 2P mirror vs stock, 120 fresh seeds (52000-) | 78/120 = 65.0% |
| 2P mirror vs stock, 60 fresh seeds (63000-) | 45/60 = 75.0% |
| **2P pooled fresh** | **123/180 = 68.3%** (null 50%) |
| 4P (1+3 stock), 60 fresh seeds (52000-) | 22/60 = 36.7% |
| 4P (1+3 stock), 60 fresh seeds (63000-) | 24/60 = 40.0% |
| **4P pooled fresh** | **46/120 = 38.3%** (null 25%) |
| vs sim_1050 (12 games) | 10/12 |
| vs sim_1000 (12 games) | 11/12 |
| turn time | mean 11ms, p99 18ms, max 144ms (budget 1000ms) |

68% mirror ≈ +130 Elo over the stock fork tier (1160-1250) ⇒ projected
~1290-1380 if the tier really is stock-ish forks. Even with slippage, ≥1185
looks reachable. **Next action: submit the tarball, watch LB for ~3-6h.**

## The winning change (implemented, baked in)

`reinforce_margin_frac=0.6` in both CONFIG_2P and CONFIG_4P
(`orbit_v2/main.py`). Margin computed in `plan_lite_waves` and passed to
`capture_floor`'s previously-unused `reinforcement=` hook:

    margin[t, k] = frac * ramp(k) * sum_e ships_e * [tau_et + 1 <= k]
    e: alive enemy planets != t;  tau_et = cross_dist[0][e,t] / fleet_speed(ships_e)
    ramp = reinforcement_timing_factor(k, eta_free=2, eta_scale=8)  (defaults)

Why it wins: stock sizes attacks against the do-nothing projection; reactive
defenders (flip-defense + regroup) kill its captures. The margin makes floors
honest about enemy reach. It also subsumes anti-snipe on neutrals (floors on
vulnerable neutrals get inflated, so we skip or oversize them).

### Sweep evidence (60 tuning seeds 41000-, 2P; baseline margin-off = 50%)

| frac | 0.3 | 0.45 | 0.6 | 0.8 | 1.0 |
|---|---|---|---|---|---|
| win | 60% | 67% | **75%** | 65% | 60% |

eta_free=0 / eta_scale=4 / eta_scale=12 at frac 0.6: all 65-67% — defaults win.

## Dead ends tried today (don't redo)

All measured at 60+ games, mostly *exactly* outcome-neutral or worse:

- **Cheapness-ranked shortlist slots** (`max_cheap_targets`, implemented &
  gated off in planner_core.build_target_shortlist): actions diverge in
  56-78 turns/game but outcomes identical at 2/4/6 slots, 2P and 4P, tuning
  and fresh seeds. The flow scorer never picks snipes that change outcomes —
  margin already covers the value.
- **Multi-size candidates** (`enable_multi_size`, implemented & gated off in
  main.py): floor+1-sized variant beside full safe_drain. Exactly neutral.
  Note smaller fleets are *slower* (speed grows with ships) — full drain is
  usually right and the exact scorer already knows it.
- **cap-drain margin** (`reinforce_cap_drain`, implemented & gated off):
  per-enemy contribution capped at its safe_drain, frac ∈ {0.6, 1.0, 1.5} →
  70/70/75% — no better than simple uncapped 0.6.
- **4P capacity scaling**: horizon 18 → 26.7%; src12/tgt12/def4 → 26.7%
  (vs 45% margin-only on same seeds). Stock's tiny 4P config is tuned; keep.
- (Previous session) 2P horizon/caps sweeps: stock 18 is a local optimum.

**Meta-lesson: candidate-level tweaks the exact flow scorer can already price
are neutral. Wins come from fixing what the scorer cannot see (opponent
reactions). Pick future edges by that test.**

## If LB lands short of 1185 (ideas not yet tried, in scorer-blind-spot order)

1. **Opponent-reaction modeling beyond floors**: margin only inflates capture
   floors. The *defense* side (flip-defense urgency, regroup pressure) still
   assumes do-nothing enemies. E.g. pre-position reserves toward enemy mass
   centroid before launches exist.
2. **Multi-turn commitment**: stock replans from scratch each turn; staged
   two-wave attacks (synchronized arrivals from multiple sources) are never
   found because each single launch must clear the full floor alone.
   `_greedy_select` already supports L>1 contributors per wave — explore
   building multi-source candidate waves with synchronized ETAs.
3. **Fingerprint-and-shadow** the fork tier: forks are deterministic torch;
   shadow instance predicts their exact moves (see [[opponent-fingerprinting]]).
4. Margin asymmetry 2P vs 4P (sweep frac in 4P only; 0.6 untested vs
   alternatives there beyond config-scaling arms).

## Tooling (unchanged, validated)

- `analysis/mirror_lite.py CAND_MAIN [n] [seed0] [--4p] [--ov2p JSON] [--ov4p JSON]`
  — seeded mirror vs stock buddy v5; env overrides map to ProducerLiteConfig
  fields. Sanity arm = exactly 50%. ~2 min per 60-game 2P arm.
- Seed batches used: 41000- (tuning), 52000- and 63000- (fresh confirms).
  **Use a NEW batch for any future confirm.**
- Run everything with `venv/bin/python` (torch 2.12.0 lives there).
- Mirror outcomes are strongly seed-determined: different arms often produce
  identical win totals — diff actions (not totals) to check a feature is live.

## Submission checklist

- [x] tarball `orbit_v2/orbit_v2_submission.tar.gz` (main.py + orbit_lite/, no __pycache__)
- [x] extracted-copy smoke test (7/8 vs stock)
- [x] all gates green (see table)
- [ ] upload to Kaggle ("late night snack")
- [ ] check LB after ~3h and ~17h; compare vs v1.5's 870-890 settle
