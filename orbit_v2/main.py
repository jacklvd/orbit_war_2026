

from __future__ import annotations

import dataclasses
import os
import sys
from dataclasses import dataclass

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import torch
from torch import Tensor

from orbit_lite.geometry import fleet_speed
from orbit_lite.intercept_aim import intercept_angle
from orbit_lite.movement import MovementConfig, PlanetMovement
from orbit_lite.movement_step import (
    apply_private_planned_launches,
    concat_launch_entries,
    disambiguate_duplicate_launches,
    ensure_planet_movement,
    infer_planned_launches_from_entries,
)
from orbit_lite.obs import parse_obs
from orbit_lite.distance_cache import build_distance_cache
from orbit_lite.planner_core import (
    _candidate_indices,
    _empty_entries,
    _greedy_select,
    _plan_regroup,
    _plan_reinforce,
    build_target_shortlist,
    capture_floor,
    empty_action_row,
    entries_to_sparse_payload,
    largest_initial_player_count,
    make_launch_set,
    reachable_mask,
    reinforcement_timing_factor,
    safe_drain,
    score_candidates,
)
from orbit_lite.adapter import single_obs_to_tensor, sparse_action_row_to_moves


@dataclass(frozen=True)
class ProducerLiteConfig:
    horizon: int = 18
    max_sources_per_lane: int = 12
    max_offensive_targets: int = 12
    max_defensive_targets: int = 4          
    max_waves_per_turn: int = 6
    roi_threshold: float = 1.5
    # Terminal continuation value (deployable-tempo fix). Credits this many extra
    # production-turns to the owner of each planet at the projection horizon's end,
    # so competitive_score stops being horizon-myopic and the ROI gate stops
    # rejecting mid-game captures we can hold. Holdability-gated by construction (no
    # tail credit for planets we don't own at H), so it does not thin garrisons like
    # the FAILED expand_value_frac/surplus-valve levers. 0.0 = stock (champion
    # byte-identical). See docs/superpowers/specs/2026-06-22-terminal-value-tempo-design.md.
    terminal_value_lambda: float = 0.0
    min_ships_to_launch: float = 4.0
    enable_regroup: bool = True
    max_regroup_time: float = 7.0
    regroup_pressure_delta_min: float = 0.25
    max_regroup_sources_per_lane: int = 6
    max_regroup_targets_per_source: int = 7
    regroup_pressure_norm: str = "none"
    regroup_time_penalty_weight: float = 1e-3
    ffa_leader_attack_bonus: float = 0.0
    ffa_target_prod_bonus: float = 0.0
    # Reactive-reinforcement margin fed to capture_floor's `reinforcement` hook.
    # 0.0 = stock behaviour (no margin).
    reinforce_margin_frac: float = 0.0
    reinforce_eta_free: float = 2.0
    reinforce_eta_scale: float = 8.0
    # Cap each enemy planet's margin contribution at its own safe_drain.
    reinforce_cap_drain: bool = False
    # Extra shortlist slots ranked by projected clearing cost / prod
    # (snipe-friendly targets the proximity ranking misses). 0 = stock.
    max_cheap_targets: int = 0
    # Second candidate size per (source, target): floor-at-arrival + 1 instead
    # of full safe_drain, keeping reserve at the source. False = stock.
    enable_multi_size: bool = False
    # Margin counts only the largest single enemy player's reach instead of
    # summing all enemies (opponents don't jointly defend a target). Identical
    # to the sum in 2P; in FFA it de-escalates the 3-enemy inflation.
    margin_per_player_max: bool = False
    # Separate margin frac for NEUTRAL targets (-1 = same as
    # reinforce_margin_frac). Lower values unblock expansion while keeping
    # attack sizing vs enemy-owned planets honest.
    reinforce_margin_frac_neutral: float = -1.0
    # Multiply regroup pressure at planets we captured within the last
    # ``fresh_window`` turns, so leftover ships marshal there. 0 = stock.
    fresh_pressure_mult: float = 0.0
    fresh_window: int = 5
    # Hold window: margin counts enemy mass reaching the target up to this
    # many turns AFTER our arrival, so we only capture what survives the
    # immediate counterattack. 0 = stock (arrival-time reach only).
    margin_hold_turns: float = 0.0
    # Post-capture holdability reinforcement (R2). After offensive waves are
    # selected, route leftover ships to OWNED planets the do-nothing projection
    # will lose within ``reinforce_hold_H`` turns to reachable enemy mass —
    # sized to close the deficit, SKIPPING planets we cannot save (don't
    # reinforce the unholdable). False = stock (no reinforcement pass).
    enable_hold_reinforce: bool = False
    reinforce_hold_H: int = 8
    reinforce_unholdable_skip: bool = True
    reinforce_fresh_weight: float = 1.5
    # Precise defense (R3): when enable_hold_reinforce is on, base the deficit
    # on the do-nothing projection's ACTUAL flip (enemy post-combat garrison at
    # the flip turn) rather than hypothetical enemy reach-mass, and CAP each send
    # at that deficit so defense never cannibalises offense. Off = legacy reach.
    enable_precise_defense: bool = False
    reinforce_deficit_buffer: float = 1.0
    # Enemy-stock-aware holdability. Both price the largest SINGLE reachable
    # enemy player's stock within the hold window against ENEMY targets only
    # (neutral expansion untouched — paralysis-safe). Defaults off = stock.
    # (A) tighter floor: raise the capture floor so the sent fleet must survive
    #     the counter, margin = max(soft margin, stock_frac * reachable_stock).
    enable_stock_floor: bool = False
    stock_frac: float = 1.0
    # Reach window (turns from now) for the priced enemy stock: only count
    # enemy mass that can actually hit the planet within the hold window. Long
    # windows count ~the whole board (the enemy's entire army) and over-fire.
    stock_reach_turns: int = 8
    # (B) hard veto: drop a (source->target) enemy capture whose deliverable
    #     hold capacity (fleet + prod*veto_hold_H) can't match the reachable
    #     stack. Only removes candidates, so it cannot overcommit/waste-spiral.
    enable_hold_veto: bool = False
    veto_hold_H: int = 8
    # Deploy-or-lose surplus-expansion valve. competitive_score is horizon-myopic
    # (credits a capture only over the planning horizon, ignoring the 80-100+
    # turns it produces after), so the ROI gate rejects ~every mid-game neutral
    # capture; leftover ships then pile up and _plan_regroup only SHUFFLES them
    # between owned planets — the agent hoards 100s-900 idle ships and gets
    # out-expanded into collapse (LB fingerprint 2026-06-21, both B and phdef;
    # see analysis/FINGERPRINT_1062_phdef.md). When on, a SECOND greedy pass funds
    # the best remaining captures from each planet's SURPLUS leftover at a relaxed
    # ROI bar. Only planets with leftover >= surplus_min_idle release (genuine
    # hoarders), keeping surplus_reserve home; fleets stay capture_floor-sized so
    # garrisons don't thin out (unlike the FAILED expand_value_frac global-bar
    # lever, [[feedback_replay_passivity]]); wave-1 targets are excluded (no
    # pile-on). Runs before regroup so expansion beats shuffling. False = stock.
    enable_surplus_expand: bool = False
    surplus_min_idle: float = 60.0
    surplus_reserve: float = 30.0
    surplus_roi_threshold: float = -1e9


def _movement_config(config: ProducerLiteConfig, *, player_count: int) -> MovementConfig:
    return MovementConfig(
        movement_horizon=int(config.horizon),
        drift_epsilon=1e-3,
        track_fleets=True,
        player_count=int(player_count),
        max_tracked_fleets=128,
    )


def cheap_enemy_pressure(obs, cache, *, horizon: float, player_id: int) -> Tensor:
    P = int(obs.P)
    device = obs.device
    dtype = obs.ships.dtype
    if P == 0:
        return torch.zeros(P, dtype=dtype, device=device)
    d0 = cache.cross_dist[0].to(dtype)                                   
    ships = obs.ships.to(dtype)
    speeds = fleet_speed(ships.clamp(min=1e-6))                          
    reach_dist = (speeds.view(P, 1) * float(horizon)).clamp(min=1e-6)    
    enemy = obs.alive & (obs.owner_abs >= 0) & (obs.owner_abs != int(player_id))  
    eye = torch.eye(P, device=device, dtype=torch.bool)
    valid = enemy.view(P, 1) & obs.alive.view(1, P) & ~eye              
    decay = (1.0 - d0 / reach_dist).clamp(min=0.0)                       
    contrib = torch.where(valid, ships.view(P, 1) * decay, torch.zeros_like(decay))
    return contrib.sum(dim=0)                                            
    

def plan_lite_waves(
    *,
    movement: PlanetMovement,
    obs,
    obs_tensors: dict,
    cache,
    garrison_status,
    prod: Tensor,
    alive_by_step: Tensor,
    config: ProducerLiteConfig,
    player_count: int,
    fresh_mask: Tensor | None = None,
):
    P = obs.P
    device = obs.device
    dtype = obs.ships.dtype
    pid = int(obs.player_id)

    H_axis = int(garrison_status.ships.shape[-1])
    H = max(H_axis - 1, 0)
    K_eta = max(1, min(int(config.horizon), H))
    W = max(1, int(config.max_waves_per_turn))

    source_mask = obs.owned & obs.alive & (obs.ships >= float(config.min_ships_to_launch))
    if not bool(source_mask.any()):
        return _empty_entries(device, dtype)

    S_cap = max(1, min(int(config.max_sources_per_lane), P))
    source_idx, source_exists = _candidate_indices(obs.ships, source_mask, S_cap)
    target_idx, target_exists = build_target_shortlist(
        obs, obs_tensors, garrison_status, cache,
        config=config, K_eta=K_eta, H=H, prod=prod, source_mask=source_mask,
    )
    if not bool(target_exists.any()):
        return _empty_entries(device, dtype)
    S = int(source_idx.shape[0])
    T = int(target_idx.shape[0])
    target_is_mine = obs.owned[target_idx.clamp(0, P - 1)]                       
    
    source_ships = obs.ships[source_idx.clamp(0, P - 1)].to(dtype)                
    H_eff = torch.full((), float(H), dtype=dtype, device=device)
    drain = safe_drain(
        garrison_status, source_idx=source_idx, source_ships=source_ships,
        H_eff=H_eff, player_id=pid,
    )                                                                            
    
    eta_cap = torch.full((T,), float(K_eta), dtype=dtype, device=device)
    margin = None
    reachable_stock = None   # [T] largest single reachable enemy stock (hold window)
    tgt_enemy = None         # [T] bool: target currently enemy-owned
    if float(config.reinforce_margin_frac) > 0.0:
        # margin[t, k] = frac * ramp(k) * sum_e ships_e * [tau_et + 1 <= k]
        # e: alive enemy planets != t; tau_et = current distance / fleet speed.
        # Models defenders the enemy can reactively route to t before arrival.
        tgt = target_idx.clamp(0, P - 1)
        d0 = cache.cross_dist[0].to(dtype)                                   # [P, P]
        ships_all = obs.ships.to(dtype)
        enemy = obs.alive & (obs.owner_abs >= 0) & (obs.owner_abs != pid)    # [P]
        contrib_ships = ships_all
        if bool(config.reinforce_cap_drain):
            # Honest margin: an enemy planet can only shed its own safe_drain
            # without losing itself to the do-nothing projection.
            contrib_ships = torch.zeros_like(ships_all)
            for q in obs.owner_abs[enemy].unique().tolist():
                q_idx = (enemy & (obs.owner_abs == int(q))).nonzero(as_tuple=True)[0]
                contrib_ships[q_idx] = safe_drain(
                    garrison_status, source_idx=q_idx,
                    source_ships=ships_all[q_idx], H_eff=H_eff,
                    player_id=int(q),
                )
        speeds = fleet_speed(contrib_ships.clamp(min=1.0))                   # [P]
        tau = d0[:, tgt] / speeds.view(P, 1)                                 # [P, T]
        is_self = torch.arange(P, device=device).view(P, 1) == tgt.view(1, T)
        contributes = enemy.view(P, 1) & ~is_self                            # [P, T]
        k_grid = torch.arange(1, K_eta + 1, device=device, dtype=dtype)      # [K_eta]
        k_reach = k_grid + float(config.margin_hold_turns)
        arrives = (tau.unsqueeze(-1) + 1.0) <= k_reach.view(1, 1, K_eta)     # [P, T, K]
        arrives = arrives & contributes.unsqueeze(-1)
        weighted = contrib_ships.view(P, 1, 1) * arrives.to(dtype)          # [P, T, K]
        if bool(config.margin_per_player_max):
            owners = obs.owner_abs.to(torch.long)
            mass = torch.zeros(T, K_eta, dtype=dtype, device=device)
            for q in owners[enemy].unique().tolist():
                mass = torch.maximum(mass, weighted[owners == int(q)].sum(dim=0))
        else:
            mass = weighted.sum(dim=0)                                       # [T, K]
        ramp = reinforcement_timing_factor(
            k_grid,
            eta_free=float(config.reinforce_eta_free),
            eta_scale=float(config.reinforce_eta_scale),
        )                                                                    # [K_eta]
        frac_t = torch.full((T, 1), float(config.reinforce_margin_frac), dtype=dtype, device=device)
        if float(config.reinforce_margin_frac_neutral) >= 0.0:
            tgt_neutral = (obs.owner_abs[tgt] < 0).view(T, 1)
            frac_t = torch.where(
                tgt_neutral,
                torch.full_like(frac_t, float(config.reinforce_margin_frac_neutral)),
                frac_t,
            )
        margin = frac_t * mass * ramp.view(1, K_eta)
        # Enemy-stock-aware holdability (enemy targets only). reachable_stock[T]
        # = the largest SINGLE enemy player's mass that can hit the target
        # within stock_reach_turns (a BOUNDED retake window — using the long
        # margin grid would count ~the whole board). Priced by Mechanism A
        # (tighter floor, here) and Mechanism B (veto, below).
        if bool(config.enable_stock_floor) or bool(config.enable_hold_veto):
            tgt_enemy = (obs.owner_abs[tgt] >= 0) & (obs.owner_abs[tgt] != pid)   # [T]
            owners_l = obs.owner_abs.to(torch.long)
            within = contributes & (tau <= float(config.stock_reach_turns))       # [P, T]
            sw = contrib_ships.view(P, 1) * within.to(dtype)                       # [P, T]
            stock_full = torch.zeros(T, dtype=dtype, device=device)               # [T]
            for q in owners_l[enemy].unique().tolist():
                stock_full = torch.maximum(
                    stock_full, sw[owners_l == int(q)].sum(dim=0))
            reachable_stock = torch.where(
                tgt_enemy, stock_full, torch.zeros_like(stock_full))              # [T]
            if bool(config.enable_stock_floor):
                # margin = max(soft margin, stock_frac * reachable_stock); the
                # stock term carries NO ramp discount so the floor demands a
                # fleet that survives the counter, not just clears the garrison.
                stock_term = float(config.stock_frac) * reachable_stock          # [T]
                margin = torch.maximum(margin, stock_term.view(T, 1).expand(T, K_eta))
    floor = capture_floor(
        garrison_status, target_idx=target_idx, k_max=K_eta,
        capture_overhead=1.0, player_id=pid, reinforcement=margin,
    )
    K = int(floor.shape[-1])

    sizes = drain.view(S, 1).expand(S, T).floor()                                
    
    active = reachable_mask(
        movement, source_idx=source_idx, target_idx=target_idx,
        fleet_sizes=sizes.unsqueeze(-1), eta_cap=eta_cap,
    ).squeeze(-1)                                                                
    aim = intercept_angle(
        movement,
        source_idx.unsqueeze(1),                                                 
        target_idx.unsqueeze(0),                                                 
        sizes,                                                                    
        active=active,
    )
    angle = aim["angle"]                                                         
    eta = aim["eta"]
    viable = aim["viable"] & (eta <= eta_cap.view(1, T))

    if K > 0:
        k_arr = (eta.clamp(min=1.0, max=float(K)).ceil().long() - 1).clamp(0, K - 1)  
        floor_at_arr = floor.unsqueeze(0).expand(S, T, K).gather(-1, k_arr.unsqueeze(-1)).squeeze(-1)
    else:
        floor_at_arr = torch.ones(S, T, dtype=dtype, device=device)
    clears_floor = sizes >= floor_at_arr                                         
    
    src_neq_tgt = source_idx.view(S, 1) != target_idx.view(1, T)
    valid = (
        viable & clears_floor & (sizes >= 1.0) & src_neq_tgt
        & source_exists.view(S, 1) & target_exists.view(1, T)
    )

    # Mechanism B: hard holdability veto (enemy targets only). Drop a
    # (source->target) capture whose deliverable hold capacity (delivered fleet
    # + target prod over veto_hold_H) cannot match the largest reachable enemy
    # stack. Only removes candidates ⇒ cannot overcommit/waste-spiral. The bound
    # ignores ships spent clearing the garrison, so it under-vetoes (paralysis-
    # safe). Off, or no margin block ran (reachable_stock None) ⇒ valid unchanged.
    if bool(config.enable_hold_veto) and reachable_stock is not None:
        tgt_c = target_idx.clamp(0, P - 1)
        hold_capacity = sizes + (prod[tgt_c].to(dtype) * float(config.veto_hold_H)).view(1, T)
        unholdable = tgt_enemy.view(1, T) & (reachable_stock.view(1, T) > hold_capacity)
        valid = valid & ~unholdable

    variants = [(sizes, angle, eta, valid)]
    if bool(config.enable_multi_size) and K > 0:
        # Floor-sized variant: send just enough to clear the (margin-inflated)
        # floor, keeping the rest in reserve. Smaller fleets fly slower, so
        # re-aim and re-check the floor at the new arrival turn; candidates
        # that no longer clear simply drop out (the full-drain one remains).
        sizes2 = torch.minimum(sizes, floor_at_arr.ceil() + 1.0).floor()
        active2 = reachable_mask(
            movement, source_idx=source_idx, target_idx=target_idx,
            fleet_sizes=sizes2.unsqueeze(-1), eta_cap=eta_cap,
        ).squeeze(-1)
        aim2 = intercept_angle(
            movement, source_idx.unsqueeze(1), target_idx.unsqueeze(0),
            sizes2, active=active2,
        )
        angle2 = aim2["angle"]
        eta2 = aim2["eta"]
        viable2 = aim2["viable"] & (eta2 <= eta_cap.view(1, T))
        k_arr2 = (eta2.clamp(min=1.0, max=float(K)).ceil().long() - 1).clamp(0, K - 1)
        floor_at_arr2 = floor.unsqueeze(0).expand(S, T, K).gather(-1, k_arr2.unsqueeze(-1)).squeeze(-1)
        valid2 = (
            viable2 & (sizes2 >= floor_at_arr2) & (sizes2 >= 1.0) & src_neq_tgt
            & source_exists.view(S, 1) & target_exists.view(1, T)
            & (sizes2 < sizes - 0.5)
        )
        if bool(config.enable_hold_veto) and reachable_stock is not None:
            # Smaller floor-sized fleet ⇒ lower hold capacity ⇒ veto if the
            # reachable stack beats what this fleet + prod over the window holds.
            tgt_c = target_idx.clamp(0, P - 1)
            hold_capacity2 = sizes2 + (prod[tgt_c].to(dtype) * float(config.veto_hold_H)).view(1, T)
            valid2 = valid2 & ~(tgt_enemy.view(1, T) & (reachable_stock.view(1, T) > hold_capacity2))
        variants.append((sizes2, angle2, eta2, valid2))

    L = 1
    C = S * T * len(variants)
    cand_src = source_idx.view(S, 1).expand(S, T).reshape(-1, L).repeat(len(variants), 1)
    cand_tgt_slot = target_idx.view(1, T).expand(S, T).reshape(-1).repeat(len(variants))
    cand_tgt_short = (
        torch.arange(T, device=device).view(1, T).expand(S, T).reshape(-1).repeat(len(variants))
    )
    cand_send = torch.cat(
        [torch.where(v, sz, torch.zeros_like(sz)).reshape(-1, L) for sz, _, _, v in variants]
    )
    cand_angle = torch.cat([a.reshape(-1, L) for _, a, _, _ in variants])
    cand_eta = torch.cat(
        [torch.where(v, e, torch.ones_like(e)).reshape(-1, L) for _, _, e, v in variants]
    )
    cand_active = torch.cat([v.reshape(-1, L) for _, _, _, v in variants])
    cand_valid = cand_active.reshape(C)
    cand_is_def = target_is_mine[cand_tgt_short]

    launches = make_launch_set(
        source_slots=cand_src,
        target_slots=cand_tgt_slot.unsqueeze(-1).expand(C, L),
        ships=cand_send,
        eta=cand_eta,
        valid=cand_active & cand_valid.unsqueeze(-1),
        player_id=pid,
    )
    score = score_candidates(
        garrison_status, prod=prod, alive_by_step=alive_by_step,
        player_count=int(player_count), launches=launches, player_id=pid,
        terminal_lambda=float(config.terminal_value_lambda),
    )
    if int(player_count) >= 4 and (
        float(config.ffa_leader_attack_bonus) > 0.0
        or float(config.ffa_target_prod_bonus) > 0.0
    ):
        owner = obs.owner_abs.to(torch.long)
        owner_valid = (owner >= 0) & (owner < int(player_count)) & obs.alive
        owner_idx = owner.clamp(min=0, max=max(int(player_count) - 1, 0))
        prod_by_owner = torch.zeros(int(player_count), dtype=dtype, device=device)
        ships_by_owner = torch.zeros(int(player_count), dtype=dtype, device=device)
        prod_by_owner.scatter_add_(0, owner_idx, torch.where(owner_valid, prod.to(dtype), torch.zeros_like(prod.to(dtype))))
        ships_by_owner.scatter_add_(0, owner_idx, torch.where(owner_valid, obs.ships.to(dtype), torch.zeros_like(obs.ships.to(dtype))))
        strength = prod_by_owner + 0.025 * ships_by_owner
        my_strength = strength[pid].detach()

        target_owner = owner[target_idx.clamp(0, P - 1)].clamp(min=0, max=max(int(player_count) - 1, 0))
        target_owned_enemy = (
            target_exists
            & obs.is_enemy[target_idx.clamp(0, P - 1)]
            & (obs.owner_abs[target_idx.clamp(0, P - 1)] >= 0)
        )
        owner_strength = strength[target_owner]
        leader_delta = (owner_strength - my_strength).clamp(min=0.0)
        target_bonus_short = torch.where(
            target_owned_enemy,
            float(config.ffa_leader_attack_bonus) * leader_delta
            + float(config.ffa_target_prod_bonus) * prod[target_idx.clamp(0, P - 1)].to(dtype),
            torch.zeros_like(owner_strength),
        )
        score = score + target_bonus_short[cand_tgt_short]
    score = torch.where(cand_valid, score, torch.full_like(score, float("-inf")))

    wave_entries, leftover, wave_taken = _greedy_select(
        P=P, W=W, device=device, dtype=dtype, score=score,
        cand_src=cand_src, cand_send=cand_send, cand_angle=cand_angle, cand_eta=cand_eta,
        cand_active=cand_active, cand_tgt_slot=cand_tgt_slot, cand_tgt_short=cand_tgt_short,
        cand_is_def=cand_is_def, source_budget=obs.ships.to(dtype).clone(),
        target_exists=target_exists, roi_threshold=float(config.roi_threshold),
    )

    if (
        not bool(config.enable_regroup)
        and not bool(config.enable_hold_reinforce)
        and not bool(config.enable_surplus_expand)
    ):
        return wave_entries

    extra_entries = []
    if bool(config.enable_hold_reinforce):
        reinforce_entries = _plan_reinforce(
            movement=movement, obs=obs, obs_tensors=obs_tensors,
            garrison_status=garrison_status, cache=cache, leftover=leftover,
            original_ships=obs.ships.to(dtype), config=config, H=H,
            fresh_mask=fresh_mask,
        )
        extra_entries.append(reinforce_entries)
        # debit reinforcement sends from leftover so regroup can't double-spend
        if int(reinforce_entries.width) > 0:
            sent = torch.zeros(P, dtype=dtype, device=device)
            sent.scatter_add_(
                0,
                reinforce_entries.source_slots.clamp(0, P - 1),
                torch.where(
                    reinforce_entries.valid,
                    reinforce_entries.ships,
                    torch.zeros_like(reinforce_entries.ships),
                ),
            )
            leftover = (leftover - sent).clamp(min=0.0)

    if bool(config.enable_surplus_expand):
        # Deploy-or-lose: convert a stagnant idle stockpile into territory before
        # regroup merely shuffles it. Only planets hoarding >= surplus_min_idle
        # release (minus surplus_reserve kept home); the second greedy pass funds
        # the best remaining captures from that surplus at a relaxed ROI bar.
        # Fleet sizes are the same capture_floor candidates (no thin garrisons);
        # wave_taken excludes targets wave 1 already captured (no pile-on).
        surplus_budget = torch.where(
            leftover >= float(config.surplus_min_idle),
            (leftover - float(config.surplus_reserve)).clamp(min=0.0),
            torch.zeros_like(leftover),
        ).floor()
        if bool((surplus_budget >= float(config.min_ships_to_launch)).any()):
            expand_entries, _, _ = _greedy_select(
                P=P, W=W, device=device, dtype=dtype, score=score,
                cand_src=cand_src, cand_send=cand_send, cand_angle=cand_angle, cand_eta=cand_eta,
                cand_active=cand_active, cand_tgt_slot=cand_tgt_slot, cand_tgt_short=cand_tgt_short,
                cand_is_def=cand_is_def, source_budget=surplus_budget,
                target_exists=target_exists, roi_threshold=float(config.surplus_roi_threshold),
                taken_init=wave_taken,
            )
            extra_entries.append(expand_entries)
            if int(expand_entries.width) > 0:
                sent = torch.zeros(P, dtype=dtype, device=device)
                sent.scatter_add_(
                    0,
                    expand_entries.source_slots.clamp(0, P - 1),
                    torch.where(
                        expand_entries.valid,
                        expand_entries.ships,
                        torch.zeros_like(expand_entries.ships),
                    ),
                )
                leftover = (leftover - sent).clamp(min=0.0)

    if bool(config.enable_regroup):
        enemy_mass = cheap_enemy_pressure(obs, cache, horizon=float(K_eta), player_id=pid)
        if fresh_mask is not None and float(config.fresh_pressure_mult) > 0.0:
            # Only boost fresh captures that are actually outgunned by enemy
            # reach — safe captures should not pull the regroup flow around.
            threatened = fresh_mask & (enemy_mass > obs.ships.to(dtype))
            boosted = enemy_mass * (1.0 + float(config.fresh_pressure_mult))
            enemy_mass = torch.where(threatened, boosted, enemy_mass)
        regroup_entries = _plan_regroup(
            movement=movement, obs=obs, obs_tensors=obs_tensors, garrison_status=garrison_status,
            leftover=leftover, original_ships=obs.ships.to(dtype), pressure=enemy_mass,
            config=config, H=H,
        )
        extra_entries.append(regroup_entries)

    return concat_launch_entries([wave_entries, *extra_entries])


def run_turn(
    obs_tensors: dict, *, config: ProducerLiteConfig, player_count: int, memory,
    fresh_mask: Tensor | None = None,
) -> dict:
    device = obs_tensors["planets"].device
    obs = parse_obs(obs_tensors)
    P = obs.P
    if P == 0:
        return empty_action_row(device)

    movement = ensure_planet_movement(
        obs_tensors=obs_tensors,
        expected_cfg=_movement_config(config, player_count=int(player_count)),
        cached_movement=getattr(memory, "movement", None),
    )
    memory.movement = movement
    cache = build_distance_cache(movement, max_k=int(config.horizon))
    H = int(config.horizon)
    status = movement.garrison_status(max_horizon=H)
    alive_by_step = movement.alive_by_step[: H + 1]

    entries = plan_lite_waves(
        movement=movement, obs=obs, obs_tensors=obs_tensors, cache=cache,
        garrison_status=status, prod=movement.planet_prod,
        alive_by_step=alive_by_step, config=config, player_count=int(player_count),
        fresh_mask=fresh_mask,
    )
    entries = disambiguate_duplicate_launches(entries)
    launches = infer_planned_launches_from_entries(
        obs_tensors=obs_tensors, movement=movement, entries=entries, player_id=int(obs.player_id),
    )
    apply_private_planned_launches(
        movement=movement, launches=launches, owner_id=int(obs.player_id),
        obs_tensors=obs_tensors,
    )
    planet_ids = obs_tensors["planets"][..., 0].long()
    return entries_to_sparse_payload(entries, planet_ids=planet_ids)


# v2 experiment scaffold: stock values by default, overridable via env.
# ORBIT_V2_2P / ORBIT_V2_4P hold JSON dicts of ProducerLiteConfig field
# overrides (e.g. '{"horizon": 26, "max_waves_per_turn": 12}').
CONFIG_2P = dataclasses.replace(
    ProducerLiteConfig(),
    # Reactive-reinforcement margin: 65% vs stock over 120 fresh-seed 2P
    # mirrors (frac sweep peaked at 0.6; eta defaults beat perturbations).
    reinforce_margin_frac=0.6,
)

CONFIG_4P = dataclasses.replace(
    ProducerLiteConfig(),
    reinforce_margin_frac=0.6,
    horizon=13,
    max_sources_per_lane=6,
    max_offensive_targets=7,
    max_defensive_targets=2,
    roi_threshold=1.55,
    min_ships_to_launch=5.0,
    max_regroup_time=6.0,
    max_regroup_targets_per_source=8,
    ffa_leader_attack_bonus=0.035,
    ffa_target_prod_bonus=0.08,
)


def _apply_env_overrides() -> None:
    global CONFIG_2P, CONFIG_4P
    import json
    raw2 = os.environ.get("ORBIT_V2_2P")
    raw4 = os.environ.get("ORBIT_V2_4P")
    if raw2:
        CONFIG_2P = dataclasses.replace(CONFIG_2P, **json.loads(raw2))
    if raw4:
        CONFIG_4P = dataclasses.replace(CONFIG_4P, **json.loads(raw4))


_apply_env_overrides()


def _config_for(player_count: int) -> ProducerLiteConfig:
    return CONFIG_4P if int(player_count) >= 4 else CONFIG_2P


class ProducerLiteMemory:
    def __init__(self) -> None:
        self.movement = None
        self.cached_player_count: int | None = None
        self.last_sparse_action_row: dict | None = None
        self.prev_owner: dict[int, int] | None = None
        self.captured_at: dict[int, int] = {}

    def reset(self) -> None:
        self.movement = None
        self.cached_player_count = None
        self.last_sparse_action_row = None
        self.prev_owner = None
        self.captured_at = {}


def _update_fresh_mask(memory: ProducerLiteMemory, obs_tensors: dict, *, window: int) -> Tensor:
    """Track planets we captured within the last ``window`` turns. [P] bool."""
    planets = obs_tensors["planets"]
    ids = planets[..., 0].to(torch.long)
    owners = planets[..., 1].to(torch.long)
    me = int(obs_tensors["player"].flatten()[0].item())
    step = int(obs_tensors["step"].flatten()[0].item())
    cur = {int(i): int(o) for i, o in zip(ids.tolist(), owners.tolist()) if int(i) >= 0}
    prev = memory.prev_owner
    if prev is not None:
        for planet_id, owner in cur.items():
            if owner == me and prev.get(planet_id, me) != me:
                memory.captured_at[planet_id] = step
            elif owner != me:
                memory.captured_at.pop(planet_id, None)
    memory.prev_owner = cur
    fresh = torch.zeros(ids.shape, dtype=torch.bool, device=planets.device)
    for slot, planet_id in enumerate(ids.tolist()):
        cap = memory.captured_at.get(int(planet_id))
        if planet_id >= 0 and cap is not None and step - cap <= int(window):
            fresh[slot] = True
    return fresh


class ProducerLiteRuntime:
    def __init__(self, memory: ProducerLiteMemory | None = None) -> None:
        self.memory = memory if memory is not None else ProducerLiteMemory()

    def reset(self) -> None:
        self.memory.reset()

    def tensor_action(self, obs_tensors: dict):
        mem = self.memory
        if bool((obs_tensors["step"] == 0).all()):
            mem.cached_player_count = None
            mem.prev_owner = None
            mem.captured_at = {}
        if mem.cached_player_count is None:
            mem.cached_player_count = largest_initial_player_count(obs_tensors)
        config = _config_for(mem.cached_player_count)
        fresh_mask = None
        if float(config.fresh_pressure_mult) > 0.0:
            fresh_mask = _update_fresh_mask(
                mem, obs_tensors, window=int(config.fresh_window),
            )
        row = run_turn(
            obs_tensors, config=config,
            player_count=int(mem.cached_player_count), memory=mem,
            fresh_mask=fresh_mask,
        )
        mem.last_sparse_action_row = row
        return row


_RUNTIME = ProducerLiteRuntime()


def agent(obs):
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    player_id = int(player)
    obs_tensors = single_obs_to_tensor(obs, player_id=player_id)
    with torch.no_grad():
        sparse_row = _RUNTIME.tensor_action(obs_tensors)
    return sparse_action_row_to_moves(sparse_row, obs, player_id=player_id)
