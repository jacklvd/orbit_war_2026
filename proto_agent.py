# =============================================================================
# Orbit Wars — Proto v2 (WorldModel architecture)
# =============================================================================
#
# STRATEGY
#   WorldModel-based agent with timeline simulation, efficiency scoring,
#   and proactive defense.
#
#   Key improvements over proto v1:
#   1. Timeline simulation: arrival ledger → forward-sim → fall_turn detection
#   2. Efficiency scoring: value / (ships + turns * 0.55 + 1) instead of linear
#   3. Proactive defense: per-planet reserve before spending on offense
#   4. Rescue missions: respond to planets about to fall
#   5. Global mission list: all src×target pairs ranked, executed top-down
#
# DECISION PIPELINE
#   build arrival ledger (current fleets → ETA per planet)
#   → simulate timelines (fall_turn, keep_needed per planet)
#   → compute indirect wealth and reaction times
#   → proactive defense reserve per planet
#   → Phase 1: rescue falling planets
#   → Phase 2: rank all src×target by efficiency score + ML penalty
#   → Phase 3: cooperative swarm for high-garrison targets
# =============================================================================

import math
from collections import defaultdict

# ── Constants ─────────────────────────────────────────────────────────────────
SUN_X = SUN_Y = 50.0
SUN_R = 10.0
SUN_SAFETY = 1.5
MAX_SPEED = 6.0
ORBIT_LIMIT = 50.0
TOTAL_STEPS = 500
SIM_HORIZON = 50
INTERCEPT_TOL = 1
NEIGHBOR_DIST = 25.0

ATTACK_COST_TURN_WEIGHT = 0.45
RESCUE_COST_TURN_WEIGHT = 0.40
INDIRECT_VALUE_SCALE    = 0.15
INDIRECT_FRIENDLY_WT    = 0.35
INDIRECT_NEUTRAL_WT     = 0.90
INDIRECT_ENEMY_WT       = 1.25

STATIC_NEUTRAL_MULT   = 1.40
STATIC_HOSTILE_MULT   = 1.55
HOSTILE_MULT          = 1.85
CONTESTED_MULT        = 1.00
SAFE_NEUTRAL_MULT     = 1.20
EARLY_NEUTRAL_MULT    = 1.20

PROACTIVE_HORIZON = 16
PROACTIVE_RATIO   = 0.18

RESCUE_LOOKAHEAD  = 28
SAFE_MARGIN       = 2     # my_t <= enemy_t - SAFE_MARGIN → safe neutral

LATE_REMAINING    = 60
LATE_SHIP_VAL     = 0.60
WEAK_ENEMY_THR    = 45
ELIMINATION_BONUS = 18.0

COOP_MIN_TARGET = 80
COOP_CAP        = 8

MAX_ATTACKS_PER_SRC  = 4    # max missions launched per planet per turn
MAX_TRANSIT_RATIO    = 0.40  # don't expand into neutrals beyond this fraction of total ships

# ── ML shot validator (decision tree) ────────────────────────────────────────
# Feature order: [tprod, tships, towner_neutral, turns, to_send, step,
#  remaining, profit_horizon, garrison_ratio, cost_fraction, nbr_prod,
#  nearby_enemy_prod, support_dist, is_ahead, is_behind, is_finishing]
_TREE_FEATURE   = [15, 13, 14, 11, 0, 10, -1, -1, 6, -1, -1, 12, 5, -1, -1, 11, -1, -1, 6, 3, -1, -1, 3, 6, -1, -1, 5, -1, -1, 3, 5, 5, 10, -1, -1, 11, -1, -1, 5, 12, -1, -1, 5, -1, -1, 9, 11, 7, -1, -1, 6, -1, -1, 7, 9, -1, -1, 6, -1, -1, 9, 3, 5, 3, 12, -1, -1, 10, -1, -1, 11, 4, -1, -1, 5, -1, -1, 9, 0, 5, -1, -1, 11, -1, -1, 7, 5, -1, -1, 3, -1, -1, 3, 11, 7, 5, -1, -1, 6, -1, -1, 3, 11, -1, -1, 0, -1, -1, 3, 0, 5, -1, -1, 9, -1, -1, 10, 11, -1, -1, 12, -1, -1]
_TREE_THRESHOLD = [0.030303, 0.030303, 0.030303, 11.030303, 1.121212, 7.636364, 0.000000, 0.000000, 390.787879, 0.000000, 0.000000, 48.008410, 355.272727, 0.000000, 0.000000, 22.181818, 0.000000, 0.000000, 146.363636, 15.606061, 0.000000, 0.000000, 8.393939, 433.151515, 0.000000, 0.000000, 26.000000, 0.000000, 0.000000, 36.545455, 141.545455, 63.848485, 18.574242, 0.000000, 0.000000, 0.787879, 0.000000, 0.000000, 291.818182, 37.891554, 0.000000, 0.000000, 316.090909, 0.000000, 0.000000, 0.009101, 2.545455, 160.337662, 0.000000, 0.000000, 364.636364, 0.000000, 0.000000, 110.757576, 0.016585, 0.000000, 0.000000, 426.757576, 0.000000, 0.000000, 0.010231, 31.969697, 149.121212, 20.454545, 9.823491, 0.000000, 0.000000, 8.295455, 0.000000, 0.000000, 3.454545, 32.393939, 0.000000, 0.000000, 189.636364, 0.000000, 0.000000, 0.005729, 3.060606, 113.030303, 0.000000, 0.000000, 3.151515, 0.000000, 0.000000, 54.393939, 274.181818, 0.000000, 0.000000, 42.000000, 0.000000, 0.000000, 28.151515, 0.696970, 9.610926, 301.393939, 0.000000, 0.000000, 344.666667, 0.000000, 0.000000, 16.545455, 14.333333, 0.000000, 0.000000, 2.090909, 0.000000, 0.000000, 41.000000, 2.090909, 147.787879, 0.000000, 0.000000, 0.034978, 0.000000, 0.000000, 6.477273, 1.000000, 0.000000, 0.000000, 12.616892, 0.000000, 0.000000]
_TREE_LEFT      = [1, 2, 3, 4, 5, 6, -1, -1, 9, -1, -1, 12, 13, -1, -1, 16, -1, -1, 19, 20, -1, -1, 23, 24, -1, -1, 27, -1, -1, 30, 31, 32, 33, -1, -1, 36, -1, -1, 39, 40, -1, -1, 43, -1, -1, 46, 47, 48, -1, -1, 51, -1, -1, 54, 55, -1, -1, 58, -1, -1, 61, 62, 63, 64, 65, -1, -1, 68, -1, -1, 71, 72, -1, -1, 75, -1, -1, 78, 79, 80, -1, -1, 83, -1, -1, 86, 87, -1, -1, 90, -1, -1, 93, 94, 95, 96, -1, -1, 99, -1, -1, 102, 103, -1, -1, 106, -1, -1, 109, 110, 111, -1, -1, 114, -1, -1, 117, 118, -1, -1, 121, -1, -1]
_TREE_RIGHT     = [60, 29, 18, 11, 8, 7, -1, -1, 10, -1, -1, 15, 14, -1, -1, 17, -1, -1, 22, 21, -1, -1, 26, 25, -1, -1, 28, -1, -1, 45, 38, 35, 34, -1, -1, 37, -1, -1, 42, 41, -1, -1, 44, -1, -1, 53, 50, 49, -1, -1, 52, -1, -1, 57, 56, -1, -1, 59, -1, -1, 92, 77, 70, 67, 66, -1, -1, 69, -1, -1, 74, 73, -1, -1, 76, -1, -1, 85, 82, 81, -1, -1, 84, -1, -1, 89, 88, -1, -1, 91, -1, -1, 108, 101, 98, 97, -1, -1, 100, -1, -1, 105, 104, -1, -1, 107, -1, -1, 116, 113, 112, -1, -1, 115, -1, -1, 120, 119, -1, -1, 122, -1, -1]
_TREE_VALUE     = [0.499130, 0.506475, 0.497699, 0.500707, 0.488305, 0.465583, 0.436957, 0.492634, 0.513986, 0.501095, 0.559679, 0.528535, 0.535433, 0.546907, 0.511692, 0.467829, 0.477178, 0.139860, 0.273306, 0.632768, 0.739583, 0.506173, 0.241840, 0.403571, 0.373757, 0.666667, 0.179891, 0.596154, 0.164539, 0.586439, 0.615866, 0.601834, 0.678874, 0.691113, 0.445055, 0.572937, 0.397816, 0.585253, 0.722632, 0.754557, 0.766118, 0.538462, 0.506608, 0.294118, 0.633803, 0.440822, 0.266003, 0.131507, 0.083682, 0.222222, 0.411243, 0.187919, 0.587302, 0.492809, 0.458805, 0.386040, 0.503030, 0.617357, 0.577938, 0.800000, 0.411806, 0.238567, 0.346167, 0.492944, 0.563830, 0.274510, 0.588138, 0.377778, 0.325806, 0.547368, 0.263962, 0.201916, 0.172060, 0.622222, 0.419593, 0.322344, 0.518657, 0.124373, 0.070777, 0.050181, 0.201923, 0.028354, 0.232227, 0.012500, 0.366412, 0.232432, 0.143552, 0.068966, 0.322314, 0.303502, 0.380645, 0.186275, 0.513823, 0.565038, 0.314931, 0.168712, 0.101562, 0.414286, 0.416136, 0.262673, 0.547244, 0.596958, 0.639966, 0.649853, 0.405594, 0.540929, 0.593985, 0.478783, 0.381424, 0.425643, 0.474132, 0.557441, 0.375194, 0.326055, 0.236607, 0.493724, 0.233227, 0.167742, 0.070707, 0.213270, 0.297468, 0.439560, 0.240000]
_TREE_BASELINE  = 0.258338

# ── ML training interface ─────────────────────────────────────────────────────
_logging_enabled: bool = False
_log_buffer: list = []

# =============================================================================
# PHYSICS
# =============================================================================

def fleet_speed(n):
    return 1.0 + (MAX_SPEED - 1.0) * (math.log(max(n, 1)) / math.log(1000)) ** 1.5


def _seg_sun_dist(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    sq = dx * dx + dy * dy
    if sq < 1e-12:
        return math.hypot(x1 - SUN_X, y1 - SUN_Y)
    t = max(0.0, min(1.0, ((SUN_X - x1) * dx + (SUN_Y - y1) * dy) / sq))
    return math.hypot(x1 + t * dx - SUN_X, y1 + t * dy - SUN_Y)


def hits_sun(x1, y1, x2, y2):
    return _seg_sun_dist(x1, y1, x2, y2) < SUN_R + SUN_SAFETY


def _travel_dist(sx, sy, sr, tx, ty, tr):
    return max(0.0, math.hypot(sx - tx, sy - ty) - sr - tr)


def _travel_turns(dist, ships):
    return max(1, math.ceil(dist / fleet_speed(max(1, ships))))


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


def _ray_hits_disc(fx, fy, fa, px, py, pr):
    dx, dy = math.cos(fa), math.sin(fa)
    ex, ey = px - fx, py - fy
    t = ex * dx + ey * dy
    if t < 0:
        return False
    cx = fx + t * dx - px
    cy = fy + t * dy - py
    return cx * cx + cy * cy <= pr * pr


# =============================================================================
# ARRIVAL LEDGER
# =============================================================================

def _fleet_to_planet(fleet, raw_p):
    """Ray-disc intersection: find which planet this fleet is heading to."""
    fx, fy = fleet[2], fleet[3]
    fa = fleet[4]
    speed = fleet_speed(max(1, fleet[6]))
    dx, dy = math.cos(fa), math.sin(fa)

    best_p, best_eta = None, 1e9
    for p in raw_p:
        px, py, pr = p[2], p[3], p[4]
        ex, ey = px - fx, py - fy
        proj = ex * dx + ey * dy
        if proj < 0:
            continue
        perp_sq = ex * ex + ey * ey - proj * proj
        if perp_sq >= pr * pr:
            continue
        hit_d = max(0.0, proj - math.sqrt(max(0.0, pr * pr - perp_sq)))
        eta = hit_d / speed
        if eta <= SIM_HORIZON + 5 and eta < best_eta:
            best_eta = eta
            best_p = p

    if best_p is None:
        return None, None
    return best_p, int(math.ceil(best_eta))


def build_arrival_ledger(raw_f, raw_p):
    """Build {planet_id: [(eta, owner, ships)]} from current fleets."""
    ledger = {p[0]: [] for p in raw_p}
    for f in raw_f:
        if f[6] <= 0:
            continue
        target_p, eta = _fleet_to_planet(f, raw_p)
        if target_p is None:
            continue
        ledger[target_p[0]].append((eta, f[1], int(f[6])))
    return ledger


# =============================================================================
# TIMELINE SIMULATION
# =============================================================================

def _resolve_arrival(owner, garrison, arrivals):
    """Battle resolution when multiple fleets arrive simultaneously."""
    by_owner = defaultdict(int)
    for (own, ships) in arrivals:
        by_owner[own] += ships

    if not by_owner:
        return owner, max(0.0, garrison)

    sorted_pl = sorted(by_owner.items(), key=lambda x: x[1], reverse=True)
    top_own, top_ships = sorted_pl[0]

    if len(sorted_pl) > 1:
        second = sorted_pl[1][1]
        if top_ships == second:
            surv_own, surv_ships = -1, 0
        else:
            surv_own, surv_ships = top_own, top_ships - second
    else:
        surv_own, surv_ships = top_own, top_ships

    if surv_ships <= 0:
        return owner, max(0.0, garrison)

    if owner == surv_own:
        return owner, garrison + surv_ships

    garrison -= surv_ships
    if garrison < 0:
        return surv_own, -garrison
    return owner, garrison


def simulate_timeline(p_raw, arrivals, player, horizon):
    """Forward-simulate planet. Returns {fall_turn, keep_needed, owner_at, ships_at}."""
    p_owner = p_raw[1]
    p_prod  = p_raw[6]
    p_ships = p_raw[5]

    by_turn = defaultdict(list)
    for (eta, own, ships) in arrivals:
        if ships > 0 and 1 <= int(eta) <= horizon:
            by_turn[int(eta)].append((own, int(ships)))

    owner    = p_owner
    garrison = float(p_ships)
    owner_at = {0: owner}
    ships_at = {0: max(0.0, garrison)}
    fall_turn = None

    for t in range(1, horizon + 1):
        if owner != -1:
            garrison += p_prod
        group = by_turn.get(t)
        if group:
            prev = owner
            owner, garrison = _resolve_arrival(owner, garrison, group)
            if prev == player and owner != player and fall_turn is None:
                fall_turn = t
        owner_at[t] = owner
        ships_at[t] = max(0.0, garrison)

    # Binary search for minimum garrison to keep planet through horizon
    keep_needed = 0
    if p_owner == player:
        def _survives(keep):
            s_own = p_owner
            s_gar = float(keep)
            for t in range(1, horizon + 1):
                if s_own != -1:
                    s_gar += p_prod
                group = by_turn.get(t)
                if group:
                    s_own, s_gar = _resolve_arrival(s_own, s_gar, group)
                    if s_own != player:
                        return False
            return s_own == player

        if not _survives(int(p_ships)):
            keep_needed = int(p_ships)
        else:
            lo, hi = 0, int(p_ships)
            while lo < hi:
                mid = (lo + hi) // 2
                if _survives(mid):
                    hi = mid
                else:
                    lo = mid + 1
            keep_needed = lo

    return {
        "fall_turn":   fall_turn,
        "keep_needed": keep_needed,
        "owner_at":    owner_at,
        "ships_at":    ships_at,
    }


# =============================================================================
# WORLD MODEL
# =============================================================================

class WorldModel:
    def __init__(self, player, step, raw_p, raw_f, av, init_by_id, raw_comets, comet_ids):
        self.player     = player
        self.step       = step
        self.raw_p      = raw_p
        self.raw_f      = raw_f
        self.av         = av
        self.init_by_id = init_by_id
        self.comet_ids  = comet_ids
        self.remaining  = max(1, TOTAL_STEPS - step)
        self.is_early   = step < 40
        self.is_late    = self.remaining < LATE_REMAINING

        self.my_p      = [p for p in raw_p if p[1] == player]
        self.enemy_p   = [p for p in raw_p if p[1] not in (-1, player)]
        self.neutral_p = [p for p in raw_p if p[1] == -1]
        self.others    = [p for p in raw_p if p[1] != player]
        self.planet_by_id = {p[0]: p for p in raw_p}

        # Strength accounting (planets + fleets in transit)
        self.my_on_planet  = sum(p[5] for p in self.my_p)
        enemy_on_planet    = sum(p[5] for p in self.enemy_p)
        my_transit    = sum(f[6] for f in raw_f if f[1] == player)
        enemy_transit = sum(f[6] for f in raw_f if f[1] >= 0 and f[1] != player)
        self.my_transit   = my_transit
        my_ships    = self.my_on_planet  + my_transit
        enemy_ships = enemy_on_planet + enemy_transit
        self.my_ships    = my_ships
        self.enemy_ships = enemy_ships
        self.my_prod     = sum(p[6] for p in self.my_p)
        self.enemy_prod  = sum(p[6] for p in self.enemy_p)

        dom = (my_ships - enemy_ships) / max(1, my_ships + enemy_ships)
        self.domination    = dom
        self.is_behind     = dom < -0.20
        self.is_ahead      = dom >  0.18
        self.is_finishing  = dom > 0.35 and self.my_prod > self.enemy_prod * 1.25 and step > 100

        # Comet remaining life
        self.comet_life = {}
        for group in raw_comets:
            pids  = group.get("planet_ids", [])
            paths = group.get("paths", [])
            pidx  = group.get("path_index", 0)
            for i, pid in enumerate(pids):
                if i < len(paths):
                    self.comet_life[pid] = max(0, len(paths[i]) - pidx)

        # Build arrival ledger and timeline per planet
        self.arrivals       = build_arrival_ledger(raw_f, raw_p)
        self.timelines      = {
            p[0]: simulate_timeline(p, self.arrivals[p[0]], player, SIM_HORIZON)
            for p in raw_p
        }
        self.fall_turn_map  = {pid: tl["fall_turn"]   for pid, tl in self.timelines.items()}
        self.keep_needed_map = {pid: tl["keep_needed"] for pid, tl in self.timelines.items()}

        # Indirect wealth per planet (neighbor production weighted by type and distance)
        self.indirect_wealth = {}
        for p in raw_p:
            w = 0.0
            for q in raw_p:
                if q[0] == p[0]:
                    continue
                d = math.hypot(p[2] - q[2], p[3] - q[3])
                factor = q[6] / (d + 12.0)
                if q[1] == player:
                    w += factor * INDIRECT_FRIENDLY_WT
                elif q[1] == -1:
                    w += factor * INDIRECT_NEUTRAL_WT
                else:
                    w += factor * INDIRECT_ENEMY_WT
            self.indirect_wealth[p[0]] = w

        # Reaction time map: for each non-owned target, compare our min ETA vs enemy min ETA
        # Include in-transit fleet ETAs so already-committed enemy fleets are counted
        self.reaction_times = {}
        for t in self.others:
            tid = t[0]
            my_eta  = min((_quick_eta(s, t) for s in self.my_p),    default=1e9)
            en_eta  = min((_quick_eta(e, t) for e in self.enemy_p), default=1e9)
            for eta, own, _ in self.arrivals.get(tid, []):
                if own == player:
                    my_eta = min(my_eta, eta)
                elif own >= 0:
                    en_eta = min(en_eta, eta)
            self.reaction_times[tid] = (my_eta, en_eta)

        # Proactive defense reserve + attack budget per planet
        self.reserve      = {}
        self.attack_budget = {}
        for mine in self.my_p:
            mid        = mine[0]
            exact_keep = self.keep_needed_map.get(mid, 0)
            proactive  = 0
            for enemy in self.enemy_p:
                d = max(0.0, math.hypot(mine[2] - enemy[2], mine[3] - enemy[3]) - mine[4] - enemy[4])
                eta = _travel_turns(d, max(1, enemy[5]))
                if eta <= PROACTIVE_HORIZON:
                    proactive = max(proactive, int(enemy[5] * PROACTIVE_RATIO))
            # Cap proactive at 35% of current ships so we always have attack budget
            proactive = min(proactive, int(mine[5] * 0.35))
            reserve = min(int(mine[5]), max(exact_keep, proactive))
            self.reserve[mid]       = reserve
            self.attack_budget[mid] = max(0, int(mine[5]) - reserve)

    def is_static(self, pid):
        init = self.init_by_id.get(pid)
        if init is None:
            return True
        return math.hypot(init[2] - SUN_X, init[3] - SUN_Y) + init[4] >= ORBIT_LIMIT

    def is_safe_neutral(self, tid):
        my_t, en_t = self.reaction_times.get(tid, (1e9, 1e9))
        return my_t <= en_t - SAFE_MARGIN

    def is_contested_neutral(self, tid):
        my_t, en_t = self.reaction_times.get(tid, (1e9, 1e9))
        return abs(my_t - en_t) <= SAFE_MARGIN

    def target_value(self, target, arrival_turns):
        """Compute capture value: production + indirect wealth, with type multipliers."""
        tid    = target[0]
        towner = target[1]
        tprod  = target[6]

        turns_profit = max(1, self.remaining - arrival_turns)

        if tid in self.comet_ids:
            life = self.comet_life.get(tid, 0)
            turns_profit = max(0, min(turns_profit, life - arrival_turns))
            if turns_profit <= 0:
                return -1.0

        value  = tprod * turns_profit
        value += self.indirect_wealth.get(tid, 0.0) * turns_profit * INDIRECT_VALUE_SCALE

        if self.is_static(tid):
            value *= STATIC_NEUTRAL_MULT if towner == -1 else STATIC_HOSTILE_MULT
        elif towner not in (-1, self.player):
            value *= HOSTILE_MULT

        if towner == -1:
            if self.is_safe_neutral(tid):
                value *= SAFE_NEUTRAL_MULT
            elif self.is_contested_neutral(tid):
                value *= CONTESTED_MULT
            if self.is_early:
                value *= EARLY_NEUTRAL_MULT

        if self.is_late:
            value += max(0, target[5]) * LATE_SHIP_VAL
            if towner not in (-1, self.player):
                en_total = sum(p[5] for p in self.enemy_p)
                if en_total <= WEAK_ENEMY_THR:
                    value += ELIMINATION_BONUS

        if self.is_finishing and towner not in (-1, self.player):
            value *= 1.15

        if self.is_behind and towner not in (-1, self.player):
            value *= 1.10

        return value

    def already_enroute(self, tid):
        """Our ships currently in transit toward this planet (from arrival ledger)."""
        return sum(ships for _, own, ships in self.arrivals.get(tid, []) if own == self.player)


def _quick_eta(src, target):
    d = max(0.0, math.hypot(src[2] - target[2], src[3] - target[3]) - src[4] - target[4])
    return _travel_turns(d, max(1, src[5]))


# =============================================================================
# ATTACK SOLVER
# =============================================================================

def _compute_attack(src, target, budget, committed_now, av, init_by_id, raw_f, player, opp_style="normal"):
    """3-pass iterative solver. Returns (angle, turns, to_send) or None."""
    tid, towner, tx, ty, tr, tships, tprod = target[:7]

    if towner == -1:
        margin = 2                              # neutrals don't produce; fixed buffer
    elif opp_style == "rusher":
        margin = min(5, 2 + int(tprod // 2))
    else:
        margin = min(8, 2 + int(tprod))

    ic = find_intercept(src, target, budget, av, init_by_id)
    if ic is None:
        return None
    angle, turns, _, _ = ic

    if turns > 18:
        margin = min(margin + 3, margin + int((turns - 18) / 6))

    for _ in range(3):
        # Neutrals don't produce ships; only enemy-owned planets accumulate
        garrison = tships + (tprod * turns if towner != -1 else 0)
        if towner != -1:
            for f in raw_f:
                if f[1] == player or f[1] < 0 or f[6] < 8:
                    continue
                if not _ray_hits_disc(f[2], f[3], f[4], tx, ty, tr + 4.0):
                    continue
                dist_rem = max(0.0, math.hypot(f[2] - tx, f[3] - ty) - tr)
                if _travel_turns(dist_rem, f[6]) <= turns:
                    garrison += f[6]

        if committed_now > 0 and committed_now >= garrison + margin:
            return None

        needed = max(0, int(garrison - committed_now)) + margin
        if budget < needed:
            return None

        to_send = min(int(needed * 1.06), budget)
        ic = find_intercept(src, target, to_send, av, init_by_id)
        if ic is None:
            return None
        angle, turns, _, _ = ic

    return angle, turns, to_send


# =============================================================================
# NEIGHBOR PRODUCTION (for ML features)
# =============================================================================

def _neighbor_prod(target, raw_p, player):
    tx, ty = target[2], target[3]
    total = 0.0
    for p in raw_p:
        if p[0] == target[0]:
            continue
        if math.hypot(p[2] - tx, p[3] - ty) < NEIGHBOR_DIST:
            if p[1] == player:
                total += p[6] * 0.35
            elif p[1] == -1:
                total += p[6] * 0.9
            else:
                total += p[6] * 1.25
    return total


# =============================================================================
# ML TREE PENALTY
# =============================================================================

def _ml_penalty(target, to_send, turns, step, world):
    """Decision tree penalty (negative only — suppresses bad shots)."""
    if len(_TREE_FEATURE) <= 1:
        return 0.0
    tprod, tships, towner = target[6], target[5], target[1]
    tx, ty       = target[2], target[3]
    remaining_v  = max(0, TOTAL_STEPS - step - turns)
    garrison_v   = tships + (tprod * turns if towner != -1 else 0)
    my_total     = max(1, sum(p[5] for p in world.raw_p if p[1] == world.player))
    near_ep      = sum(
        p[6] for p in world.raw_p
        if p[1] not in (-1, world.player) and math.hypot(p[2] - tx, p[3] - ty) < 30
    )
    sup_dist = min(
        (math.hypot(p[2] - tx, p[3] - ty) for p in world.my_p),
        default=100.0
    )
    nbr = _neighbor_prod(target, world.raw_p, world.player)
    feats = [
        tprod, tships, 1 if towner == -1 else 0, turns, to_send,
        step, remaining_v,
        tprod * remaining_v / max(1, to_send),
        to_send / max(1, garrison_v),
        to_send / my_total,
        nbr, near_ep, sup_dist,
        int(world.is_ahead), int(world.is_behind), int(world.is_finishing),
    ]
    node = 0
    while _TREE_FEATURE[node] != -1:
        node = (
            _TREE_LEFT[node]
            if feats[_TREE_FEATURE[node]] <= _TREE_THRESHOLD[node]
            else _TREE_RIGHT[node]
        )
    return min(0.0, (_TREE_VALUE[node] - _TREE_BASELINE) * 5.0)


# =============================================================================
# LOGGING (training data capture)
# =============================================================================

def _log_attack(mid, tid, target, to_send, turns, step, world):
    if not _logging_enabled:
        return
    tprod, tships = target[6], target[5]
    tx, ty = target[2], target[3]
    remaining    = max(0, TOTAL_STEPS - step - turns)
    garrison_at  = tships + (tprod * turns if target[1] != -1 else 0)
    my_total     = max(1, sum(p[5] for p in world.raw_p if p[1] == world.player))
    near_ep      = sum(
        p[6] for p in world.raw_p
        if p[1] not in (-1, world.player) and math.hypot(p[2] - tx, p[3] - ty) < 30
    )
    my_planets   = [p for p in world.raw_p if p[1] == world.player]
    sup_dist     = min(
        (math.hypot(p[2] - tx, p[3] - ty) for p in my_planets),
        default=100.0
    )
    nbr = _neighbor_prod(target, world.raw_p, world.player)
    _log_buffer.append({
        "mid": mid, "tid": tid,
        "tprod": tprod, "tships": tships,
        "towner_neutral": 1 if target[1] == -1 else 0,
        "turns": int(turns), "to_send": to_send,
        "step": step, "remaining": remaining,
        "profit_horizon": tprod * remaining / max(1, to_send),
        "garrison_ratio": to_send / max(1, garrison_at),
        "cost_fraction":  to_send / my_total,
        "nbr_prod":            nbr,
        "nearby_enemy_prod":   near_ep,
        "support_dist":        sup_dist,
        "is_ahead":    int(world.is_ahead),
        "is_behind":   int(world.is_behind),
        "is_finishing": int(world.is_finishing),
        "label_step":  min(step + int(turns) + 25, TOTAL_STEPS - 5),
    })


# =============================================================================
# MAIN AGENT
# =============================================================================

def agent(obs):
    try:
        return _agent(obs)
    except Exception:
        return []


def _agent(obs):
    # ── Parse observation ─────────────────────────────────────────────────────
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

    init_by_id = {p[0]: p for p in raw_init}

    # ── Build WorldModel ──────────────────────────────────────────────────────
    world = WorldModel(player, step, raw_p, raw_f, av, init_by_id, raw_comets, comet_ids)

    if not world.my_p or not world.others:
        return []

    # ── Opponent style ────────────────────────────────────────────────────────
    opp_style = "normal"
    if world.enemy_p:
        avg_gar = sum(p[5] for p in world.enemy_p) / len(world.enemy_p)
        if avg_gar < 15:
            opp_style = "rusher"
        elif avg_gar > 50:
            opp_style = "turtle"

    moves    = []
    pending  = []           # (tid, ships, eta) — flushed to global state at end
    this_turn = {}          # tid → ships committed this turn (same-turn coop)
    spent    = defaultdict(int)  # mid → ships spent this turn

    def attack_left(mid):
        return max(0, world.attack_budget.get(mid, 0) - spent[mid])

    # ── Phase 1: Rescue missions ──────────────────────────────────────────────
    # For each planet about to fall, find the best nearby source.
    rescue_targets = sorted(
        [
            (pid, ft)
            for pid, ft in world.fall_turn_map.items()
            if ft is not None
            and ft <= RESCUE_LOOKAHEAD
            and pid in {p[0] for p in world.my_p}
        ],
        key=lambda x: x[1],  # most urgent first
    )

    rescue_done = set()
    for pid, fall_t in rescue_targets:
        target = world.planet_by_id.get(pid)
        if target is None:
            continue

        best = None
        for src in sorted(world.my_p, key=lambda p: math.hypot(p[2] - target[2], p[3] - target[3])):
            if src[0] == pid:
                continue
            budget = attack_left(src[0])
            if budget < 2:
                continue
            ic = find_intercept(src, target, budget, av, init_by_id)
            if ic is None:
                continue
            angle, turns, _, _ = ic
            if turns >= fall_t:
                continue  # can't arrive in time

            need     = max(2, world.keep_needed_map.get(pid, 1) + target[6])
            to_send  = min(budget, need)
            if to_send < 2:
                continue

            value = target[6] * max(1, world.remaining - fall_t)
            score = value / (to_send + turns * RESCUE_COST_TURN_WEIGHT + 1.0)
            if best is None or score > best[0]:
                best = (score, src, angle, turns, to_send)

        if best:
            _, src, angle, turns, to_send = best
            moves.append([src[0], angle, to_send])
            spent[src[0]] += to_send
            this_turn[pid] = this_turn.get(pid, 0) + to_send
            pending.append((pid, to_send, turns))
            rescue_done.add(pid)

    # ── Phase 2: Build global attack mission list ─────────────────────────────
    all_missions = []

    for src in world.my_p:
        mid    = src[0]
        budget = attack_left(mid)
        if budget < 2:
            continue

        for target in world.others:
            tid    = target[0]
            towner = target[1]
            tprod  = target[6]

            # Comet filter
            if tid in comet_ids:
                life = world.comet_life.get(tid, 0)
                if life < 5:
                    continue
                if math.hypot(src[2] - target[2], src[3] - target[3]) > 30:
                    continue

            # Profit-horizon filter: skip unprofitable late neutrals
            if towner == -1 and tprod > 0 and step > 100:
                rough_d   = max(0.0, math.hypot(src[2] - target[2], src[3] - target[3]) - src[4] - target[4])
                rough_eta = _travel_turns(rough_d, budget)
                rough_rem = max(0, TOTAL_STEPS - step - rough_eta)
                if rough_rem > 0 and tprod * rough_rem < budget * 0.1:
                    continue

            committed_now = this_turn.get(tid, 0) + world.already_enroute(tid)
            result = _compute_attack(
                src, target, budget, committed_now,
                av, init_by_id, raw_f, player, opp_style
            )
            if result is None:
                continue
            angle, turns, to_send = result

            value = world.target_value(target, turns)
            if value <= 0:
                continue

            score  = value / (to_send + turns * ATTACK_COST_TURN_WEIGHT + 1.0)
            score += _ml_penalty(target, to_send, turns, step, world)

            all_missions.append((score, mid, tid, angle, turns, to_send))

    all_missions.sort(reverse=True)

    # ── Phase 2b: Execute missions in score order ─────────────────────────────
    src_attacks = defaultdict(int)
    transit_ratio = world.my_transit / max(1.0, world.my_ships)
    transit_capped = transit_ratio > MAX_TRANSIT_RATIO

    for score, mid, tid, _angle, _turns, _to_send in all_missions:
        budget = attack_left(mid)
        if budget < 2:
            continue
        if src_attacks[mid] >= MAX_ATTACKS_PER_SRC:
            continue
        # If over-committed in transit, skip neutral expansion; enemy attacks still allowed
        if transit_capped and world.planet_by_id.get(tid, [None, -1])[1] == -1:
            continue

        target = world.planet_by_id.get(tid)
        src    = world.planet_by_id.get(mid)
        if target is None or src is None:
            continue

        # Re-solve with current committed state
        committed_now = this_turn.get(tid, 0) + world.already_enroute(tid)
        result = _compute_attack(
            src, target, budget, committed_now,
            av, init_by_id, raw_f, player, opp_style
        )
        if result is None:
            continue
        angle, turns, to_send = result

        moves.append([mid, angle, to_send])
        _log_attack(mid, tid, target, to_send, turns, step, world)
        this_turn[tid] = this_turn.get(tid, 0) + to_send
        spent[mid] += to_send
        pending.append((tid, to_send, turns))
        src_attacks[mid] += 1

    # ── Phase 3: Cooperative swarm ────────────────────────────────────────────
    budgets_after = {p[0]: attack_left(p[0]) for p in world.my_p}

    coop_candidates = sorted(
        [t for t in world.others if t[5] >= COOP_MIN_TARGET and t[0] not in comet_ids],
        key=lambda t: -(t[6] * 20 - t[5] * 0.4),
    )
    coop_done = set()

    for t in coop_candidates:
        tid = t[0]
        if tid in coop_done:
            continue
        towner, tx, ty, tr, tships, tprod = t[1], t[2], t[3], t[4], t[5], t[6]

        # Already-committed: enroute from arrival ledger + same-turn
        already = world.already_enroute(tid) + this_turn.get(tid, 0)
        margin  = 2 if towner == -1 else 5

        contributors = []
        for mine in world.my_p:
            b = budgets_after.get(mine[0], 0)
            if b < 2:
                continue
            ic = find_intercept(mine, t, b, av, init_by_id)
            if ic is None:
                continue
            _, eta, _, _ = ic
            contributors.append((eta, mine, b))

        if not contributors:
            continue

        contributors.sort(key=lambda x: x[0])
        max_eta = contributors[-1][0]

        garrison_est = tships + (tprod * max_eta if towner != -1 else 0)
        if towner != -1:
            for f in raw_f:
                if f[1] == player or f[1] < 0 or f[6] < 8:
                    continue
                if not _ray_hits_disc(f[2], f[3], f[4], tx, ty, tr + 4.0):
                    continue
                dist_rem = max(0.0, math.hypot(f[2] - tx, f[3] - ty) - tr)
                if _travel_turns(dist_rem, f[6]) <= max_eta:
                    garrison_est += f[6]

        if already >= garrison_est + margin:
            continue

        needed     = max(0, int(garrison_est - already)) + margin
        total_avail = sum(b for _, _, b in contributors)
        if total_avail < needed:
            continue

        remaining_need = needed
        recruited = 0
        for eta, mine, _ in contributors[:COOP_CAP]:
            if remaining_need <= 0 or recruited >= COOP_CAP:
                break
            b_now = budgets_after.get(mine[0], 0)
            if b_now < 2:
                continue
            to_send = min(b_now, remaining_need + 2)
            if to_send < 2:
                continue
            ic = find_intercept(mine, t, to_send, av, init_by_id)
            if ic is None:
                continue
            angle, actual_eta, _, _ = ic
            moves.append([mine[0], angle, to_send])
            this_turn[tid] = this_turn.get(tid, 0) + to_send
            pending.append((tid, to_send, actual_eta))
            budgets_after[mine[0]] = b_now - to_send
            spent[mine[0]] += to_send
            remaining_need -= to_send
            recruited += 1

        if recruited > 0:
            coop_done.add(tid)

    return moves
