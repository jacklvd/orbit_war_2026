# Orbit Wars

A competition agent for **Orbit Wars** — a real-time strategy game where 2 or 4
players conquer planets orbiting a sun in continuous 2D space. Whoever holds the
most ships (on planets + in fleets) after 500 turns wins.

This repo holds the agent (`orbit_v2/`), the analysis tooling used to develop it,
and the design records for the experiments. The [game rules](#game-rules-reference)
are documented at the bottom.

---

## Result

| | |
|---|---|
| **Best stable score** | ~**1239** Elo (peak **1352**) — the `orbit_v2` agent, 2026-06-12 |
| **Final submitted pair** | `holdwindow8` + `B_holdwindow` (the two most *consistent* configs) |
| **Goal** | Top 10% of the field |

The leaderboard uses a continuously-updated Elo: agents keep playing and the rating
drifts. Fresh submissions start at ~600 and take ~a day of games to converge to their
true level. The final pair was chosen for **consistency** (validated across both the
leaderboard and the local arena), not single-run peak.

---

## The agent (`orbit_v2/`)

The agent is a **flow-based greedy planner**, not a search or ML policy. Each turn it
projects the board forward and scores candidate fleet launches by their effect on a
competitive objective, then greedily commits the best non-conflicting waves.

**Pipeline (`orbit_v2/main.py` → `orbit_v2/orbit_lite/`):**

1. **Forward projection** (`orbit_lite/movement.py`, `garrison_launch.py`) — a
   bit-exact simulation of planet rotation, fleet flight, production, and combat over a
   short horizon (18 turns in 2P, 13 in 4P).
2. **Candidate generation** (`plan_lite_waves` in `main.py`) — for each (source, target)
   pair it computes a **capture floor** (`capture_floor`: min ships to take the planet,
   accounting for the defender's projected garrison) and a **safe drain** (`safe_drain`:
   max ships a source can shed while still holding itself).
3. **Scoring** (`score_candidates` → `sparse_launch_flow_delta` → `competitive_score`) —
   each launch is scored by the *delta* it causes in `Δnet_ships_me − Σ Δnet_ships_opp`,
   computed exactly via a sparse per-planet flow projector.
4. **Greedy selection** (`_greedy_select`) — picks the best wave each iteration (one per
   target, source-budget-aware) while its competitive score clears an ROI gate; leftover
   ships are reinforced/regrouped.

**The one winning lever:** a **reactive-reinforcement margin** (`reinforce_margin_frac=0.6`)
fed into `capture_floor`. Stock scoring sizes attacks against a *do-nothing* projection;
the margin makes the agent send enough to survive the defender's reactive counter — fixing
the scorer's main blind spot. This took the agent from the ~870-890 tier (`proto_agent`
v1.x) to ~1240.

Behavior is tuned by `ProducerLiteConfig`; `CONFIG_2P` / `CONFIG_4P` hold the shipped
values, overridable at runtime via the `ORBIT_V2_2P` / `ORBIT_V2_4P` env vars (JSON).

---

## What worked, and what didn't

The hard-won lesson of this project: **candidate-level tweaks that the flow scorer can
already price are outcome-neutral, and "expand more" levers are actively harmful.** Real
edges must fix what the scorer *cannot see* (opponent reactions).

**Worked**
- Reactive-reinforcement margin (`reinforce_margin_frac=0.6`) — the core win.
- Hold-window margin (`margin_hold_turns`) — only count enemy mass that reaches a target
  *after* our arrival, so we capture what survives the immediate counter (`B`/`holdwindow8`).

**Refuted (documented so they aren't retried)**
- **Expansion-volume levers** — `expand_value_frac` (thin-garrison trap), early quality
  multipliers, blanket fleet-fraction cuts, the **surplus-expansion valve** (shipped, LB
  1073 vs 1176), and the **terminal-value tempo knob** (implemented default-off, no robust
  local edge). Conclusion: expanding *more* just takes planets we can't hold under enemy
  reaction. The unbuilt direction is expansion *quality* / reaction-aware holdability.
- **Defensive reworks** — precise-defense / post-capture holdability (LB 1062).
- Candidate-level no-ops the scorer already prices: cheap-target shortlist slots,
  multi-size sends, cap-drain margin, 4P capacity scaling.

Full write-ups in `analysis/FINDINGS_2026-06-21_latest2.md` and
`docs/superpowers/specs/`.

---

## Repo layout

```
orbit_v2/                  Active agent
  main.py                  Planner + ProducerLiteConfig (CONFIG_2P / CONFIG_4P)
  orbit_lite/              Engine: movement, garrison/flow projection, scoring, aiming
  build_stock_submissions.py   Builds a submission tarball for a given config
  orbit_v2_submission*.tar.gz   The 3 tarballs active on the leaderboard
  PLAN.md                  Blind-spot / future-edge list
analysis/                  Development & analysis tooling (see below)
docs/superpowers/          Design specs & implementation plans for experiments
agent_log/                 Downloaded leaderboard replays (ours + top opponents)
opponents/                 Local sparring agents (buddy_v5, etc.)
archive/                   Older proto_agent work + the forward simulator
proto_agent.py             v1.x agent (pre-pivot, ~870-890 tier)
.env                       Kaggle API token (gitignored)
```

## Running it

Everything runs with the project venv (`venv/bin/python`) — the agent imports `torch`
but **not** the kaggle CLI, so it's unaffected by the slow-import caveat below.

```bash
# Run the agent vs a local opponent on a seed (kaggle_environments must be installed)
venv/bin/python -c "from kaggle_environments import make; ..."   # see analysis/ scripts

# Build a submission tarball for a config
venv/bin/python orbit_v2/build_stock_submissions.py

# Submit / check standings (needs the throwaway kaggle CLI — see Caveats)
set -a; source .env; set +a
/tmp/kgl/bin/kaggle competitions submit orbit-wars -f orbit_v2/<tarball> -m "..."
/tmp/kgl/bin/kaggle competitions submissions orbit-wars
```

## Tooling (`analysis/`)

| Script | Purpose |
|---|---|
| `pull_replays.py` | Download recent episode replays for a submission (stdlib-only) |
| `phdef_autopsy.py` | Per-replay autopsy: planet/ship trajectories, win/loss diagnosis |
| `arena_oracle.py` | Local regression gate vs a fixed opponent pool |
| `verify_terminal_value.py` | Subprocess-isolated config A/B + λ sweep harness |
| `test_terminal_value.py` | Unit tests for the terminal-value scoring term |

**Win/loss discriminator** (from replay analysis): track when our total-ship stockpile
peaks. Wins peak at the *end* of the game (snowball); losses peak *mid-game* (we hoard
idle ships and get out-expanded). `argmax(ships)/T` near 1.0 = healthy.

## Caveats (read before extending)

- **Local oracle ceiling** — local opponents cap at the ~1000-1100 tier; only `buddy_v5`
  and 4P self-play discriminate. Local win-rate is a regression gate, **not** proof of a
  leaderboard gain. Real validation is an A/B submission.
- **Win-rate varies hugely by seed batch** — never conclude from one batch; a single good
  batch repeatedly turned out to be noise.
- **Harness nondeterminism** — `kaggle_environments` + agent is deterministic *across*
  processes but **not within one** (global state leaks between sequential `env.run` calls).
  Run each (seed, config) cell in its own subprocess (`verify_terminal_value.py` does this).
- **Kaggle CLI** — the Google-Drive filesystem times out importing the kaggle package's
  protobuf, so the CLI lives in a throwaway venv at `/tmp/kgl`. Recreate with
  `python3 -m venv /tmp/kgl && /tmp/kgl/bin/pip install kaggle` (token is in `.env`).
  The agent itself does not need this.

---

## Game Rules Reference

Conquer planets rotating around a sun in continuous 2D space. A real-time strategy game
for 2 or 4 players.

### Overview

Players start with a single home planet and compete to control the map by sending fleets
to capture neutral and enemy planets. The board is a 100x100 continuous space with a sun
at the center. Planets orbit the sun, comets fly through on elliptical trajectories, and
fleets travel in straight lines. The game lasts 500 turns. The player with the most total
ships (on planets + in fleets) at the end wins.

### Board Layout

- **Board**: 100x100 continuous space, origin at top-left.
- **Sun**: Centered at (50, 50) with radius 10. Fleets that cross the sun are destroyed.
- **Symmetry**: All planets and comets are placed with 4-fold mirror symmetry around the
  center: (x, y), (100-x, y), (x, 100-y), (100-x, 100-y).

### Planets

Each planet is `[id, owner, x, y, radius, ships, production]`.

- **owner**: Player ID (0-3), or -1 for neutral.
- **radius**: `1 + ln(production)`.
- **production**: Integer 1-5; each turn an owned planet generates this many ships.
- **ships**: Current garrison. Starts between 5 and 99 (skewed low).
- **Orbiting** planets (`orbital_radius + planet_radius < 50`) rotate at 0.025-0.05
  rad/turn; **static** planets do not. Use `initial_planets` + `angular_velocity` to
  predict positions. Map has 20-40 planets (5-10 symmetric groups of 4).
- **Home planets**: one symmetric group; 2P start diagonally opposite (Q1/Q4), 4P one
  each. Home planets start with 10 ships.

### Fleets

Each fleet is `[id, owner, x, y, angle, from_planet_id, ships]`.

- **Speed** scales with size: `speed = 1.0 + (maxSpeed-1.0) * (log(ships)/log(1000))^1.5`
  (1 ship → 1.0, ~1000 ships → max 6.0).
- Fleets travel straight and are removed on out-of-bounds, sun crossing, or planet
  collision (continuous path-segment detection; collision triggers combat).
- **Launch**: each turn return `[from_planet_id, direction_angle, num_ships]` moves from
  planets you own; can't send more than the planet holds; multiple launches allowed.

### Comets

Temporary objects on elliptical orbits, spawning in groups of 4 (one per quadrant) at
steps 50/150/250/350/450. Radius 1.0, production 1/turn, low starting ships. They obey
all planet rules. Identified via `comet_planet_ids`; trajectories in `comets`. Removed
(with their garrison) when they leave the board, before fleet launches.

### Turn Order

1. Comet expiration → 2. Comet spawning → 3. Fleet launch → 4. Production →
5. Fleet movement (out-of-bounds / sun / planet collision) → 6. Planet rotation & comet
movement (sweeps caught fleets into combat) → 7. Combat resolution.

### Combat

When fleets collide with a planet:

1. Arriving fleets grouped by owner; same-owner ships summed.
2. Largest attacking force fights the second largest; the difference survives.
3. A surviving attacker either reinforces (same owner) or fights the garrison (different
   owner); if attackers exceed the garrison, the planet flips and the garrison becomes
   the surplus.
4. A tie destroys all attacking ships.

### Scoring and Termination

Game ends at 500 steps or when one/zero players remain. Final score = ships on owned
planets + ships in owned fleets. Highest wins.

### Observation Reference

| Field | Description |
|-------|-------------|
| `planets` | `[[id, owner, x, y, radius, ships, production], ...]` (incl. comets) |
| `fleets` | `[[id, owner, x, y, angle, from_planet_id, ships], ...]` |
| `player` | Your player ID (0-3) |
| `angular_velocity` | Planet rotation speed (rad/turn) |
| `initial_planets` | Planet positions at game start |
| `comets` | `[{planet_ids, paths, path_index}, ...]` |
| `comet_planet_ids` | Planet IDs that are comets |
| `remainingOverageTime` | Remaining overage time budget (seconds) |

### Action Format

Return `[[from_planet_id, direction_angle, num_ships], ...]` (angle in radians, 0 = right,
π/2 = down), or `[]` for no action.

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `episodeSteps` | 500 | Max turns |
| `actTimeout` | 1 | Seconds per turn |
| `shipSpeed` | 6.0 | Max fleet speed |
| `sunRadius` | 10.0 | Sun radius |
| `boardSize` | 100.0 | Board dimensions |
| `cometSpeed` | 4.0 | Comet speed (units/turn) |
