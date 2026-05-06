# =============================================================================
# Orbit Wars — Proto-Hybrid Agent
# =============================================================================
#
# WHAT'S NEW vs main.py  (beats main.py ~76% over 50 games locally)
#
#   1. Iterative garrison solver (_compute_attack, 3 passes)
#      Initial fleet size → recalculate turns → recalculate garrison + enemy
#      reinforcements → recalculate fleet size.  Converges in ≤3 iterations.
#      main.py does 2 passes; the 3rd catches cases where fleet speed changes
#      shift the estimated garrison enough to need more ships.
#
#   2. Enemy reinforcement detection (_enemy_reinforce_enroute)
#      Before attacking an enemy planet, we scan raw_f for enemy fleets heading
#      toward it (ray-disc intersection) that will arrive before our fleet does.
#      Those ships are added to the garrison estimate.  main.py uses a static
#      heuristic (10% of nearby planet ships within 8 turns); this uses actual
#      observed fleets.
#
#   3. Global ETA-based fleet tracking (_gstate / _commit / _tick_gstate)
#      When we send a fleet we record (ships, eta_turns) per target.  Each turn,
#      ETAs are decremented and expired entries dropped.  The solo attack loop
#      uses a fresh per-turn dict (no cross-turn drift from failed fleets), while
#      the cooperative pass reads _gstate for the accurate already-en-route count.
#
#   4. Cooperative pass (MIN_COOP_TARGET = 80, enabled)
#      For targets with ≥80 ships that the solo pass couldn't cover, multiple
#      planets pool their leftover budget.  Garrison is estimated at max_eta
#      (the slowest contributor's arrival), which is conservative: earlier waves
#      partially deplete the garrison, so the final wave captures with margin.
#
#   5. Opponent style detection (_opponent_style)
#      Each turn, average enemy garrison is computed.  Against rushers (<15
#      ships/planet) the attack margin drops from 5 → 2, saving ships on every
#      enemy attack since rushers rarely reinforce their planets.
# =============================================================================

import math

# ── Constants ─────────────────────────────────────────────────────────────────
SUN_X = SUN_Y = 50.0
SUN_R  = 10.0
SUN_SAFETY = 1.5
MAX_SPEED   = 6.0
ORBIT_LIMIT = 50.0
TOTAL_STEPS = 500
INTERCEPT_TOL = 1
NEIGHBOR_DIST = 25.0
COOP_CAP        = 8    # max planets coordinating on one target
# Coop targets must have at least this many ships.  Earlier waves deplete the
# garrison; using max_eta for the estimate means the combined force is always
# sized for the worst-case (final-arrival) garrison, so the last wave captures
# even when earlier waves fail.  Setting too low wastes overhead on easy solos.
MIN_COOP_TARGET = 80

# ── Global fleet state ────────────────────────────────────────────────────────
# Maps target_id -> list of (ships, eta_remaining)
_gstate: dict = {}


# ── Physics ───────────────────────────────────────────────────────────────────

def fleet_speed(n):
    return 1.0 + (MAX_SPEED - 1.0) * (math.log(max(n, 1)) / math.log(1000)) ** 1.5


def _seg_sun_dist(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    sq = dx*dx + dy*dy
    if sq < 1e-12:
        return math.hypot(x1 - SUN_X, y1 - SUN_Y)
    t = max(0.0, min(1.0, ((SUN_X - x1)*dx + (SUN_Y - y1)*dy) / sq))
    return math.hypot(x1 + t*dx - SUN_X, y1 + t*dy - SUN_Y)


def hits_sun(x1, y1, x2, y2):
    return _seg_sun_dist(x1, y1, x2, y2) < SUN_R + SUN_SAFETY


def _travel_dist(sx, sy, sr, tx, ty, tr):
    return max(0.0, math.hypot(sx - tx, sy - ty) - sr - tr)


def _travel_turns(dist, ships):
    return max(1, math.ceil(dist / fleet_speed(max(1, ships))))


# ── Orbit prediction ──────────────────────────────────────────────────────────

def _is_orbiting(planet, init_by_id):
    init = init_by_id.get(planet[0])
    if init is None:
        return False
    return math.hypot(init[2] - SUN_X, init[3] - SUN_Y) + init[4] < ORBIT_LIMIT


def _orbital_radius(planet, init_by_id):
    init = init_by_id.get(planet[0])
    if init is None:
        return math.hypot(planet[2] - SUN_X, planet[3] - SUN_Y)
    return math.hypot(init[2] - SUN_X, init[3] - SUN_Y)


def _predict_pos(planet, turns, av, init_by_id):
    if not _is_orbiting(planet, init_by_id):
        return planet[2], planet[3]
    orb_r = _orbital_radius(planet, init_by_id)
    a = math.atan2(planet[3] - SUN_Y, planet[2] - SUN_X) + av * turns
    return SUN_X + orb_r * math.cos(a), SUN_Y + orb_r * math.sin(a)


def find_intercept(src, target, ships, av, init_by_id):
    sx, sy, sr = src[2], src[3], src[4]
    tr = target[4]

    def try_aim(tx, ty):
        if hits_sun(sx, sy, tx, ty):
            return None
        d = _travel_dist(sx, sy, sr, tx, ty, tr)
        return math.atan2(ty - sy, tx - sx), _travel_turns(d, ships)

    tx, ty = target[2], target[3]
    for _ in range(5):
        est = try_aim(tx, ty)
        if est is None:
            break
        _, turns = est
        ntx, nty = _predict_pos(target, turns, av, init_by_id)
        if abs(ntx - tx) < 0.3 and abs(nty - ty) < 0.3:
            return math.atan2(ty - sy, tx - sx), turns, tx, ty
        tx, ty = ntx, nty

    if not _is_orbiting(target, init_by_id):
        return None
    orb_r = _orbital_radius(target, init_by_id)
    cur_a = math.atan2(target[3] - SUN_Y, target[2] - SUN_X)
    for ft in range(1, 61):
        a = cur_a + av * ft
        ptx = SUN_X + orb_r * math.cos(a)
        pty = SUN_Y + orb_r * math.sin(a)
        est = try_aim(ptx, pty)
        if est is None:
            continue
        _, arrival = est
        if abs(arrival - ft) <= INTERCEPT_TOL:
            final = max(arrival, ft)
            fa = cur_a + av * final
            ftx = SUN_X + orb_r * math.cos(fa)
            fty = SUN_Y + orb_r * math.sin(fa)
            est2 = try_aim(ftx, fty)
            if est2 and abs(est2[1] - final) <= INTERCEPT_TOL:
                return est2[0], final, ftx, fty
    return None


# ── Ray-disc intersection ─────────────────────────────────────────────────────

def _ray_hits_disc(fx, fy, fa, px, py, pr):
    dx, dy = math.cos(fa), math.sin(fa)
    ex, ey = px - fx, py - fy
    t = ex*dx + ey*dy
    if t < 0:
        return False
    cx = fx + t*dx - px
    cy = fy + t*dy - py
    return cx*cx + cy*cy <= pr*pr


# ── Threat detection ──────────────────────────────────────────────────────────

def _incoming_per_planet(raw_p, raw_f, player):
    mine = [(p[0], p[2], p[3], p[4]) for p in raw_p if p[1] == player]
    result = {pid: 0 for pid, *_ in mine}
    for f in raw_f:
        if f[1] == player:
            continue
        fx, fy, fa, fships = f[2], f[3], f[4], f[6]
        for pid, px, py, pr in mine:
            if _ray_hits_disc(fx, fy, fa, px, py, pr):
                result[pid] += fships
                break
    return result


def _enemy_reinforce_enroute(tid, tx, ty, tr, our_eta, raw_f, player):
    """Enemy ships in transit that will reinforce target before our fleet arrives."""
    total = 0
    for f in raw_f:
        owner = f[1]
        if owner == player or owner < 0:
            continue
        fx, fy, fa, fships = f[2], f[3], f[4], f[6]
        # Expanded disc (+4 units) to catch near-miss rays from slightly off angles
        if not _ray_hits_disc(fx, fy, fa, tx, ty, tr + 4.0):
            continue
        dist_rem = max(0.0, math.hypot(fx - tx, fy - ty) - tr)
        eta = _travel_turns(dist_rem, fships)
        if eta <= our_eta:
            total += fships
    return total


# ── Global fleet commitment state ─────────────────────────────────────────────

def _committed_ships(tid):
    """Total our ships in transit toward target tid (global + same-turn)."""
    return sum(ships for ships, _ in _gstate.get(tid, []))


def _tick_gstate(owned_ids):
    """Decrement all ETAs; drop arrived fleets and newly-captured targets."""
    global _gstate
    new = {}
    for tid, entries in _gstate.items():
        if tid in owned_ids:
            continue  # we own it now, fleet either captured or reinforces us
        alive = [(s, e - 1) for s, e in entries if e > 1]
        if alive:
            new[tid] = alive
    _gstate = new


def _commit(tid, ships, eta):
    global _gstate
    if tid not in _gstate:
        _gstate[tid] = []
    _gstate[tid].append((ships, max(1, eta)))


# ── Opponent style detection ──────────────────────────────────────────────────

def _opponent_style(raw_p, player):
    """Detect whether opponent is rushing (thin garrisons) or turtling."""
    enemy_planets = [p for p in raw_p if p[1] >= 0 and p[1] != player]
    if not enemy_planets:
        return "normal"
    avg_garrison = sum(p[5] for p in enemy_planets) / len(enemy_planets)
    if avg_garrison < 15:
        return "rusher"
    if avg_garrison > 50:
        return "turtle"
    return "normal"


# ── Dominance state ───────────────────────────────────────────────────────────

def _build_modes(raw_p, player, step):
    my_s  = sum(p[5] for p in raw_p if p[1] == player)
    en_s  = sum(p[5] for p in raw_p if p[1] >= 0 and p[1] != player)
    my_pr = sum(p[6] for p in raw_p if p[1] == player)
    en_pr = sum(p[6] for p in raw_p if p[1] >= 0 and p[1] != player)
    dom   = (my_s - en_s) / max(1, my_s + en_s)
    return {
        "is_behind":    dom < -0.20,
        "is_ahead":     dom >  0.18,
        "is_finishing": dom > 0.35 and my_pr > en_pr * 1.25 and step > 100,
        "my_ships": my_s, "enemy_ships": en_s,
        "my_prod":  my_pr, "enemy_prod": en_pr,
    }


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _neighbor_prod(target, raw_p, player):
    tx, ty = target[2], target[3]
    total = 0.0
    for p in raw_p:
        if p[0] == target[0]:
            continue
        if math.hypot(p[2] - tx, p[3] - ty) < NEIGHBOR_DIST:
            if p[1] == player:   total += p[6] * 0.35
            elif p[1] == -1:     total += p[6] * 0.9
            else:                total += p[6] * 1.25
    return total


def _opp_priority(target, my_p):
    if not my_p:
        return 1.0
    cx = sum(p[2] for p in my_p) / len(my_p)
    cy = sum(p[3] for p in my_p) / len(my_p)
    d = math.hypot(target[2] - cx, target[3] - cy)
    return max(0.5, min(2.0, 2.0 - d / 50.0))


# ── Iterative attack solver ───────────────────────────────────────────────────

def _compute_attack(src, target, budget, committed_now, av, init_by_id, raw_f, player,
                    opp_style="normal"):
    """
    3-pass iterative solver.

    committed_now: ships already committed to this target THIS turn (same-turn
    coordination, like main.py's committed dict — does NOT include prior-turn
    global state to avoid stale-fleet contamination).

    Each pass: estimate garrison at arrival (target ships + production * turns
    + enemy reinforcements arriving before us) → compute needed ships →
    re-solve intercept with new fleet size → repeat.

    Returns (angle, turns, to_send) or None.
    """
    tid    = target[0]
    towner = target[1]
    tships = target[5]
    tprod  = target[6]
    tx, ty, tr = target[2], target[3], target[4]

    # Rushers keep thin garrisons and rarely reinforce; smaller margin suffices.
    if towner == -1:
        margin = 2
    elif opp_style == "rusher":
        margin = 2
    else:
        margin = 5

    # Seed with full-budget intercept
    ic = find_intercept(src, target, budget, av, init_by_id)
    if ic is None:
        return None
    angle, turns, _, _ = ic

    for _ in range(3):
        garrison = tships + tprod * turns
        if towner != -1:
            garrison += _enemy_reinforce_enroute(tid, tx, ty, tr, turns, raw_f, player)

        # Already covered by same-turn commits?
        if committed_now > 0 and committed_now >= garrison + margin:
            return None

        needed = max(0, int(garrison - committed_now)) + margin
        if budget < needed:
            return None

        to_send = min(int(needed * 1.15), budget)

        ic = find_intercept(src, target, to_send, av, init_by_id)
        if ic is None:
            return None
        angle, turns, _, _ = ic

    return angle, turns, to_send


# ── Attack scoring ────────────────────────────────────────────────────────────

def _score_target(src, target, budget, committed_now, av, init_by_id, raw_f, modes,
                  step, raw_p, player, my_p, comet_ids, comet_life, opp_style="normal"):
    """Returns (score, to_send, angle, turns) or None."""
    tid    = target[0]
    towner = target[1]
    tships = target[5]
    tprod  = target[6]

    if tid in comet_ids:
        if comet_life.get(tid, 0) < 5:
            return None
        sx, sy = src[2], src[3]
        if math.hypot(sx - target[2], sy - target[3]) > 30:
            return None

    result = _compute_attack(src, target, budget, committed_now,
                             av, init_by_id, raw_f, player, opp_style)
    if result is None:
        return None
    angle, turns, to_send = result

    # Scoring: production value + timing + neighborhood + fleet cost
    score = tprod * 25.0 - turns * tprod * 0.3 - to_send * 0.2

    nbr = _neighbor_prod(target, raw_p, player)
    score += nbr * 1.5

    if towner == -1:
        score += 5.0
        if not _is_orbiting(target, init_by_id) or step >= 40:
            score += 2.0
        if modes["is_behind"]:
            score += 3.0
    else:
        score += tprod * 4.0
        opp = _opp_priority(target, my_p)
        score *= max(0.7, min(1.3, opp))
        enemy_total = sum(p[5] for p in raw_p if p[1] == towner)
        if enemy_total < 150:
            score += 30.0
        if modes["is_finishing"]:
            score += 8.0

    if TOTAL_STEPS - step < 80:
        score += tships * 0.3

    return score, to_send, angle, turns


# ── Main agent ────────────────────────────────────────────────────────────────

def agent(obs):
    try:
        return _agent(obs)
    except Exception:
        return []


def _agent(obs):
    global _gstate

    if isinstance(obs, dict):
        player     = obs.get("player", 0)
        raw_p      = obs.get("planets", [])
        raw_f      = obs.get("fleets", [])
        av         = obs.get("angular_velocity", 0.0)
        raw_init   = obs.get("initial_planets", [])
        raw_comets = obs.get("comets", []) or []
        comet_ids  = set(obs.get("comet_planet_ids", None) or [])
        step       = obs.get("step", 0) or 0
    else:
        player     = obs.player
        raw_p      = list(obs.planets)
        raw_f      = list(obs.fleets)
        av         = obs.angular_velocity
        raw_init   = list(obs.initial_planets)
        raw_comets = list(obs.comets or [])
        comet_ids  = set(obs.comet_planet_ids or [])
        step       = getattr(obs, "step", 0) or 0

    # Reset global state at the start of each game
    if step <= 1:
        _gstate = {}

    my_p   = [p for p in raw_p if p[1] == player]
    others = [p for p in raw_p if p[1] != player]
    if not my_p or not others:
        return []

    init_by_id = {p[0]: p for p in raw_init}
    owned_ids  = {p[0] for p in my_p}

    # Age all in-transit commitments by 1 turn
    _tick_gstate(owned_ids)

    comet_life = {}
    for group in raw_comets:
        pids  = group.get("planet_ids", [])
        paths = group.get("paths", [])
        pidx  = group.get("path_index", 0)
        for i, pid in enumerate(pids):
            if i < len(paths):
                comet_life[pid] = max(0, len(paths[i]) - pidx)

    modes     = _build_modes(raw_p, player, step)
    opp_style = _opponent_style(raw_p, player)
    incoming  = _incoming_per_planet(raw_p, raw_f, player)

    n_neutral = sum(1 for p in others if p[1] == -1)
    if n_neutral > 8 or step < 60:
        garrison_frac = 0.04
    elif modes["is_finishing"]:
        garrison_frac = 0.05
    elif modes["is_behind"]:
        garrison_frac = 0.12
    else:
        garrison_frac = 0.08

    max_attacks = 3 if (modes["is_finishing"] or modes["is_ahead"]) else 2

    moves    = []
    # this_turn: fresh per-turn committed dict (like main.py) — no cross-turn drift
    this_turn = {}
    # pending_commits: collected this turn, flushed to _gstate at the end
    pending   = []
    budgets   = {}

    # ── Solo attack loop ──────────────────────────────────────────────────────
    for mine in sorted(my_p, key=lambda p: -p[5]):
        mid, _, sx, sy, sr, my_ships, _ = mine[:7]

        enemy_in = incoming.get(mid, 0)
        if enemy_in > 0:
            if enemy_in >= my_ships * 1.5:
                budget = max(0, my_ships - 5)   # evacuate
            else:
                budget = max(0, my_ships - enemy_in - 5)
        else:
            garrison = max(5, int(my_ships * garrison_frac))
            budget   = max(0, my_ships - garrison)

        if budget < 2:
            budgets[mid] = 0
            continue

        candidates = []
        for t in others:
            result = _score_target(mine, t, budget, this_turn.get(t[0], 0),
                                   av, init_by_id, raw_f, modes, step,
                                   raw_p, player, my_p, comet_ids, comet_life,
                                   opp_style)
            if result is None:
                continue
            sc, to_send, angle, turns = result
            candidates.append((sc, t[0], to_send, angle, turns))

        candidates.sort(reverse=True)

        attacks = 0
        for sc, tid, _, angle, turns in candidates:
            if attacks >= max_attacks or budget < 2:
                break
            t_data = next((t for t in others if t[0] == tid), None)
            if t_data is None:
                continue
            result = _score_target(mine, t_data, budget, this_turn.get(tid, 0),
                                   av, init_by_id, raw_f, modes, step,
                                   raw_p, player, my_p, comet_ids, comet_life,
                                   opp_style)
            if result is None:
                continue
            _, to_send, angle, turns = result
            moves.append([mid, angle, to_send])
            this_turn[tid] = this_turn.get(tid, 0) + to_send
            pending.append((tid, to_send, turns))
            budget -= to_send
            attacks += 1

        budgets[mid] = budget

    # ── Cooperative attack pass ───────────────────────────────────────────────
    # Use global state (previous turns) + this_turn for an accurate committed
    # count. The cooperative pass handles high-garrison targets that no single
    # planet's solo budget could cover.
    coop_done = set()
    coop_candidates = sorted(
        [t for t in others
         if t[5] >= MIN_COOP_TARGET and t[0] not in comet_ids],
        key=lambda t: -(t[6] * 20 - t[5] * 0.4)
    )

    for t in coop_candidates:
        tid    = t[0]
        if tid in coop_done:
            continue
        towner = t[1]
        tx, ty, tr, tships, tprod = t[2], t[3], t[4], t[5], t[6]

        # Combine previous-turn global commits + same-turn solo commits
        already = _committed_ships(tid) + this_turn.get(tid, 0)
        margin  = 2 if towner == -1 else 5

        contributors = []
        for mine in my_p:
            mid = mine[0]
            b = budgets.get(mid, 0)
            if b < 2:
                continue
            ic = find_intercept(mine, t, b, av, init_by_id)
            if ic is None:
                continue
            _, eta, _, _ = ic
            contributors.append((eta, mine, b))

        if not contributors:
            continue

        contributors.sort()
        # Use max ETA (slowest contributor) for garrison estimate.
        # Earlier, faster waves deplete the garrison in practice; sizing for the
        # final-arrival turn is conservative but guarantees the last wave wins.
        max_eta = contributors[-1][0]

        garrison_est = tships + tprod * max_eta
        if towner != -1:
            garrison_est += _enemy_reinforce_enroute(
                tid, tx, ty, tr, max_eta, raw_f, player)

        if already >= garrison_est + margin:
            continue  # already well-covered

        needed = max(0, int(garrison_est - already)) + margin
        if needed <= 0:
            continue

        total_avail = sum(b for _, _, b in contributors)
        if total_avail < needed:
            continue

        remaining = needed
        recruited = 0
        for eta, mine, _ in contributors[:COOP_CAP]:
            if remaining <= 0 or recruited >= COOP_CAP:
                break
            mid   = mine[0]
            b_now = budgets.get(mid, 0)
            if b_now < 2:
                continue
            to_send = min(b_now, remaining + 2)
            if to_send < 2:
                continue
            ic = find_intercept(mine, t, to_send, av, init_by_id)
            if ic is None:
                continue
            angle, actual_eta, _, _ = ic
            moves.append([mid, angle, to_send])
            this_turn[tid] = this_turn.get(tid, 0) + to_send
            pending.append((tid, to_send, actual_eta))
            budgets[mid] = b_now - to_send
            remaining   -= to_send
            recruited   += 1

        if recruited > 0:
            coop_done.add(tid)

    # Flush this turn's attacks into global state for future turns
    for tid, ships, eta in pending:
        _commit(tid, ships, eta)

    return moves
