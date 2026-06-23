# This notebook is an extension & tuned version of following notebook:
#https://www.kaggle.com/code/vickimar/orbit-wars-heuristic-1000

import math
import os
import time
from collections import defaultdict, namedtuple

# COUNCIL:

# ============================================================
# COUNCIL IMPROVEMENTS APPLIED (see comments marked [COUNCIL])
# 1. _detect_mode 2P bug fixed: no longer hardcoded "pressure"
# 2. fleet_target_planet caching added (_fleet_target_cache)
# 3. melis_evaluate uses weighted snapshot averaging (1/t)
# 4. NEUTRAL_SATURATION_STOP_EXPAND_ENABLED = True (was False)
# 5. MULTIPRONG_ENABLED = True (was False)
# 6. SEARCH_DEPTH2_ENABLED = True (was False) + budget gate
# 7. _commitment_viable: enemy-to-enemy trades no longer pruned
# 8. melis_evaluate depth-2 budget-gated inside search loop
# ============================================================

F14_4A_2P_FOCUS_ENABLED = True
F14_4A_2P_FOCUS_DIST_BONUS = 18.0   
F14_4A_2P_FOCUS_HAMMER_BONUS = 20.0
F14_4A_2P_FOCUS_MEGA_BONUS = 100

BOARD = 100.0
CENTER_X = 50.0
CENTER_Y = 50.0
SUN_R = 10.0
SUN_SAFETY = 1.5
ROTATION_LIMIT = 50.0
LAUNCH_CLEARANCE = 0.1
MAX_SPEED = 6.0
TOTAL_STEPS = 500
SIM_HORIZON = 110
FWD_SIM_FILTER_ENABLED = True   
FWD_SIM_HORIZON = 7             
FWD_SIM_DEFENSE_CHECK = True    
FWD_SIM_RANK_BONUS_4P = 0.0
                                
SEARCH_EXPAND_4P_ENABLED = True 
SEARCH_EXPAND_2P_ENABLED = True 
SEARCH_MAX_PER_SOURCE = 3       
SEARCH_MAX_ACTIONS_TO_PICK = 5    
SEARCH_MAX_ACTIONS_TO_PICK_2P = 7 
SEARCH_DISABLES_CHEAP_PICKUP = True
# [COUNCIL] Enabled depth-2 search — it was fully implemented but disabled.
# A per-action budget check inside search_step_action prevents timeout blowout.
SEARCH_DEPTH2_ENABLED = True    # was False


NEUTRAL_CAP_USES_EFFECTIVE_GARRISON = True
NEUTRAL_CAP_LOOKAHEAD = 10       

N6_USE_EFFECTIVE_PRE_GARRISON = True

TERMINAL_PHASE_ENABLED = True
TERMINAL_PHASE_TURNS = 30

FLEET_INTENT_ENABLED = True
FLEET_INTENT_MIN_DROP = 8       
FLEET_INTENT_HAMMER_BONUS = 5.0 

F1B_EXPAND_BONUS_ENABLED = True
F1B_EXPAND_BONUS = 3.0   

R1_RECAPTURE_PRIORITY_ENABLED = True
R1_RECAPTURE_HAMMER_BONUS = 8.0

E2_USE_GARRISON_THRESHOLD = True

SO1_STATIC_PREFERENCE_ENABLED = True
SO1_STATIC_BONUS = 2.179862   
SO1_STATIC_BONUS_2P = 2.179862    
SO1_STATIC_BONUS_4P = 2.95474    

SP1_SPEED_AWARE_ENABLED = True
SP1_LONG_DIST_THRESHOLD = 27.637375  
SP1_LONG_DIST_SHIPS = 22         

TI1_TIE_FOR_WIN_ENABLED = True
TI1_HORIZON_TURNS = 25           
TI1_REQUIRED_EXTRA_MARGIN = 5    
TI1_TRAILING_GAP_MIN = 10        

AS1_ANTI_SECOND_ENABLED = True

FAILTOLERANT_ENABLED = True

MELIS_SANITY_ENABLED = True
MELIS_SANITY_THETA = 3.0

F16_DIVERSITY_ENABLED = True
F16_CLOSEST_PICKS = 2
F16_PROD_PICKS = 1

CHAIN_DENSITY_ENABLED = True          # bonus for neutrals surrounded by other neutrals
CHAIN_DENSITY_RADIUS = 14.0           # radius to count nearby neutrals
CHAIN_DENSITY_BONUS = 0.8             # effective-distance reduction per nearby neutral

FWD_SCORE_AGG_ENABLED = True
FWD_SCORE_AGG_TURNS = (4, 8, 14, 20)

PSM_OPENING_TURN = 14
PSM_OPENING_TURN_2P = 14    
PSM_OPENING_TURN_4P = 10

ABSORB_MIN_THREAT = 3            
ABSORB_PROJECTION_MARGIN = 0     

DEFENSE_OVERSEND = 1             
DEFENSE_OVERSEND_2P = 1    
DEFENSE_OVERSEND_4P = 0    
DEFENSE_COALITION_MAX = 2        

MIN_DISPATCH_SHIPS = 8           

F3_THREE_BUCKET_ENABLED = True
F3_SAFE_FLOOR = 5
F3_SAFE_DIST = 12.0
F3_HARD_FLOOR = 14
F3_HARD_GARRISON = 14

EXPAND_K_OPENING = 2             
EXPAND_K_MID = 1                 
EXPAND_MAX_TRAVEL_OPENING = 20
EXPAND_MAX_TRAVEL_MID = 14
EXPAND_MIN_MARGIN = 0            
EXPAND_MIN_MARGIN_4P = 3  

X8B_2P_EXTRA = 3
EXPAND_MIN_SHIPS = MIN_DISPATCH_SHIPS

EXPAND_MIN_PROD_2P = 2

TIEBREAK_ENABLED = True
TIEBREAK_EPS_FRAC = 0.005   
TIEBREAK_EPS_MIN = 1.439234      

ROT_AWARE_RANK_ENABLED = os.environ.get("V124_ROT_AWARE", "1") != "0"

VALUE_WEIGHT_2P = 4.86118
VALUE_WEIGHT_4P = float(os.environ.get("V126_VALUE_WEIGHT_4P", "2.0"))

ANTI_SNIPE_ENABLED = os.environ.get("V124_ANTI_SNIPE", "1") != "0"
ANTI_SNIPE_HORIZON = 25          
ANTI_SNIPE_2P_ONLY = False       

REACTIVE_SNIPE_PROJECTION_ENABLED = True
REACTIVE_EMIT_FRAC = 0.49629        
REACTIVE_MIN_ENEMY_SHIPS = 5     
REACTIVE_MIN_PROJECTED = 3       

SUN_SHADOW_REACTIVE_FILTER = True

COUNTER_SNIPE_ENABLED = os.environ.get("V124_COUNTER_SNIPE", "1") != "0"
COUNTER_SNIPE_2P_ONLY = False    
COUNTER_SNIPE_MAX_COST = 30
COUNTER_SNIPE_MIN_DELAY = 1
COUNTER_SNIPE_MAX_DELAY = 12

CHEAP_PICKUP_ENABLED = os.environ.get("V124_CHEAP_PICKUP", "1") != "0"
CHEAP_PICKUP_4P_ONLY = True
CHEAP_PICKUP_MAX_GARRISON = 25

CHEAP_PICKUP_MIN_PROD = int(os.environ.get("F32_CP_MIN_PROD", "2"))

ENDGAME_ROI_ENABLED = os.environ.get("V128_ENDGAME_ROI", "1") != "0"
ENDGAME_ROI_TURNS = 30

NEUTRAL_TEMPO_FILTER_ENABLED = os.environ.get("V128_TEMPO_FILTER", "1") != "0"
NEUTRAL_TEMPO_THRESHOLD = 10     

LAUNCH_BLACKOUT_ENABLED = os.environ.get("V128_LAUNCH_BLACKOUT", "1") != "0"
LAUNCH_BLACKOUT_TURNS = 10

NEUTRAL_HARD_CAP_ENABLED = os.environ.get("V128_NEUTRAL_CAP", "1") != "0"
NEUTRAL_HARD_CAP_4P = 40          
NEUTRAL_HARD_CAP_2P = 61          
NEUTRAL_WATCHLIST_MIN_DROP = 5  

LOW_PROD_NEUTRAL_SKIP_ENABLED = True
LOW_PROD_NEUTRAL_SKIP_PROD = 1       
LOW_PROD_NEUTRAL_SKIP_GARRISON = 14  

WEAKEST_TARGET_ENABLED = os.environ.get("V128_WEAKEST_TARGET", "1") != "0"
WEAKEST_TARGET_BONUS = 2.0
WEAKEST_TARGET_MIN_STEP = 60    
WEAKEST_DONT_FINISH_SHARE = 0.05
WEAKEST_DONT_FINISH_PENALTY = 12.0  

LEADER_BASH_ENABLED = os.environ.get("V128_LEADER_BASH", "1") != "0"
LEADER_BASH_RATIO = 1.3
LEADER_BASH_BONUS = 4.0
LEADER_BASH_MIN_STEP = 60   

COALITION_ENABLED = True
COALITION_MAX_PARTICIPANTS = 3   
COALITION_NEUTRALS_ONLY = False  
COALITION_MAX_TRAVEL_BONUS = 2   
COALITION_MIN_PER_CONTRIBUTOR = 15   
COALITION_MIN_PER_CONTRIBUTOR_2P = 15    
COALITION_MIN_PER_CONTRIBUTOR_4P = 5    
COALITION_MIN_TARGET_SHIPS = 20      

HAMMER_ENABLED = True
HAMMER_STOCKPILE_MIN = 50
HAMMER_TARGET_PROD_MIN = 2
HAMMER_PROD_SHARE_TRIGGER = 0.40
HAMMER_OVERKILL_RATIO = 1.30
HAMMER_SURROUNDED_PROMOTE_TURNS = 10
HAMMER_MAX_TRAVEL = 24
HAMMER_ABORT_OVERRUN_RATIO = 1.329521
HAMMER_PLAN_REVALIDATE_INTERVAL = 1
HAMMER_MIN_PER_CONTRIBUTOR = 9
HAMMER_MELIS_VERIFY = True
HAMMER_PROD_WEIGHT = 3.0              # bonus per production unit in target scoring
HAMMER_4P_WEAK_BONUS = 0.0           # HARMFUL: -10pp 4P balanced test; dying player's planets already attractive via low required
HAMMER_4P_VULTURE_BONUS = 0.0        # 4P only: bonus when another enemy is attacking the target (HARMFUL: -16pp 4P, reverted)
HAMMER_EMIT_ENABLED = False          # HARMFUL: -10pp 4P; predict_defender_at_arrival already sees lower garrison; bonus double-counts
HAMMER_EMIT_BONUS = 8.0
HAMMER_EMIT_THRESH = 0.40
HAMMER_EMIT_LOOKBACK = 5

BATTLE_BONUS_ENABLED = False         # HARMFUL -7pp: fires when attackers pursue dying player → sends hammer to wrong targets
BATTLE_BONUS_SCORE = 5.0
BATTLE_BONUS_MIN_SHIPS = 50

# Arrival snipe: when an enemy fleet is about to capture a planet (neutral or
# another enemy's), arrive 1-3 turns after the capture and take it while the
# garrison is the landing's survivors. Launched fleets cannot redirect, so the
# capture event is deterministic; only post-capture reinforcement is uncertain,
# which the small arrival window and margin cover. Runs after expand so the
# melis path keeps first claim on ships.
SNIPE_ENABLED = True
SNIPE_2P_ENABLED = True
SNIPE_MIN_STEP = 10            # never during the opening expansion race
SNIPE_MAX_PER_TURN = 1
SNIPE_MAX_PENDING = 2          # max snipe fleets in flight
SNIPE_ARRIVAL_WINDOW = 3       # arrive within N turns after the capture
SNIPE_CAP_HORIZON = 14         # only react to captures landing within N turns
SNIPE_MAX_COST = 45            # max ships in a snipe fleet
SNIPE_MARGIN = 2               # ships above effective needed
SNIPE_MIN_SURVIVORS = 1
SNIPE_MAX_SURVIVORS = 35       # don't chase big landings
SNIPE_MIN_PROD = 1
# Holdability: the sims retake fresh captures cheaply (R1_RECAPTURE), so only
# snipe planets we are positioned to hold — our nearest planet must be at
# least as close as the nearest enemy planet (plus slack).
SNIPE_PROXIMITY_RATIO = 1.0
SNIPE_PROXIMITY_SLACK = 2.0

# Producer-style regroup: move idle surplus from rear planets to frontline planets.
REGROUP_ENABLED = False              # HARMFUL -6pp: depletes rear garrison, competes with hammer stockpile

MEGA_HAMMER_ENABLED = True
MEGA_HAMMER_4P_ONLY = True
MEGA_HAMMER_SHIPS_MIN = 300           
MEGA_HAMMER_TARGET_GARRISON_MAX = 80  
MEGA_HAMMER_MAX_TRAVEL = 40           

PROD_RESERVE_ENABLED = False          

MEGA_HAMMER_THRESHOLD_BY_PROD = {5: 200, 4: 250, 3: 300, 2: 350, 1: 400}

FRESH_CAPTURE_INHERITANCE_ENABLED = True
FRESH_CAPTURE_MAX_AGE = 5                  
MEGA_HAMMER_SHIPS_MIN_FRESH = 200          

MEGA_HAMMER_CONCENTRATE_ENABLED = True
MEGA_HAMMER_MAX_PER_TURN = 1

MEGA_HAMMER_MELIS_VERIFY = True

MEGA_HAMMER_VERIFY_OPP_EMIT = 0.30

HAMMER_NO_THREAT_OVERSEND_ENABLED = True
HAMMER_NO_THREAT_OVERSEND_2P_ONLY = True

HAMMER_ALWAYS_OVERSEND_2P = False

HAMMER_SAFE_SURPLUS_OVERSEND_ENABLED = True
HAMMER_SAFE_SURPLUS_RATIO = 2.0  
HAMMER_OVERSEND_MAX_THREAT_RATIO = 0.3  

ACCUMULATOR_ENABLED = True
ACCUMULATOR_4P_ONLY = True                  
ACCUMULATOR_TURN_MIN = 15                   
ACCUMULATOR_LEAD_MIN_SHIPS = 100            
ACCUMULATOR_LEAD_THREAT_RATIO = 0.5         
ACCUMULATOR_FEEDER_MIN_SURPLUS = 30         
ACCUMULATOR_FEEDER_KEEP_RESERVE = 30        
ACCUMULATOR_FEEDER_MAX_TRAVEL = 30          
ACCUMULATOR_MAX_FEEDS_PER_TURN = 3          

BRAIN_LEAD_RESERVE_ENABLED = True
BRAIN_LEAD_RESERVE_4P_ONLY = True            
BRAIN_LEAD_RESERVE_MIN_SHIPS = 200
BRAIN_LEAD_RESERVE_REQUIRE_TARGET = False
BRAIN_LEAD_PREFER_FRONTIER = False
BRAIN_LEAD_FRONTIER_WEIGHT = 2.0

MEGA_HAMMER_TARGET_GARRISON_MAX_ITER_H = 100  

# [COUNCIL] Enabled multiprong — fully implemented, just never turned on.
# Forces opponent to split defense: defend the hammer target and lose the
# secondary, or defend the secondary and the hammer lands clean.
MULTIPRONG_ENABLED = True       # was False
MULTIPRONG_2P_ONLY = True

MULTIPRONG_REINFORCER_MIN_RATIO = 1.0
MULTIPRONG_E_OVERKILL = 1.05
MULTIPRONG_CREDIBILITY_FACTOR = 0.6
MULTIPRONG_MAX_TRAVEL = 40
MULTIPRONG_MIN_PER_CONTRIBUTOR = 8
MULTIPRONG_MAX_PARTICIPANTS = 3

LATE_FLUSH_REMAINING_TURNS = 25  
LATE_FLUSH_OVERKILL_RATIO = 1.05      

SOFT_DEADLINE_FRACTION = 0.82

RACE_ENABLED = True
RACE_HORIZON_TURNS = 18          
RACE_MAX_NEUTRAL_DIST = 20     
RACE_TIE_GOES_TO_LARGER = True   

PERSONALITY_ENABLED = True
PERSONALITY_AGG_HIGH = 0.30
PERSONALITY_AGG_LOW = 0.10
PERSONALITY_MIN_SAMPLE = 50      

MODE_PARAMS = {
    "patient": {
        "expand_k_opening": 2,            
        "expand_max_travel_opening": 22,  
        "expand_k_mid": 1,
        "expand_max_travel_mid": 14,
        "hammer_prod_share": 0.2,
        "hammer_overkill": 1.30,
        "hammer_stockpile_min": 50,       
    },
    "opportunistic": {
        "expand_k_opening": 3,            
        "expand_max_travel_opening": 22,  
        "expand_k_mid": 2,                
        "expand_max_travel_mid": 18,      
        "hammer_prod_share": 0.35,        
        "hammer_overkill": 1.30,
        "hammer_stockpile_min": 50,
    },
    "pressure": {
        "expand_k_opening": 3,
        "expand_max_travel_opening": 22,
        "expand_k_mid": 0,
        "expand_max_travel_mid": 9,
        "hammer_prod_share": 0.30,
        "hammer_overkill": 1.20,
        "hammer_stockpile_min": 50,
    },
}

MODE_PARAMS_2P = {
    "patient": {
        "expand_k_opening": 5,            
        "expand_max_travel_opening": 35,  
        "expand_k_mid": 4,                
        "expand_max_travel_mid": 28,      
        "hammer_prod_share": 0.30,        
        "hammer_overkill": 1.15,          
        "hammer_stockpile_min": 25,       
    },
    "opportunistic": {
        "expand_k_opening": 5,
        "expand_max_travel_opening": 35,
        "expand_k_mid": 6,
        "expand_max_travel_mid": 30,
        "hammer_prod_share": 0.28,
        "hammer_overkill": 1.15,
        "hammer_stockpile_min": 25,
    },
    "pressure": {
        "expand_k_opening": 5,
        "expand_max_travel_opening": 35,
        "expand_k_mid": 2,
        "expand_max_travel_mid": 52,      
        "hammer_prod_share": 0.25,        
        "hammer_overkill": 1.177645,
        "hammer_stockpile_min": 25,
    },
}

TWO_P_PATIENT_NUDGE_TURNS = 10
TWO_P_PATIENT_ESCALATE_TURNS = 20
TWO_P_PROD_SHARE_HISTORY = 10
TWO_P_PROD_SHARE_PROGRESS_EPS = 0.005   

STOP_EXPAND_2P_ENABLED = True
STOP_EXPAND_PROD_SHARE_2P = 0.65    
STOP_EXPAND_TURN_MIN_2P = 30        

COMBAT_STOP_EXPAND_ENABLED = False      
COMBAT_STOP_EXPAND_4P_ONLY = True
COMBAT_STOP_EXPAND_TURN_MIN = 25
COMBAT_CONTACT_MIN_SHIPS = 15
COMBAT_CHEAP_GARRISON = 10              
COMBAT_CHEAP_DIST = 12.0

PROD_LAG_STOP_EXPAND_ENABLED = True
PROD_LAG_STOP_EXPAND_TURN_MIN = 25
PROD_LAG_STOP_EXPAND_THRESH_2P = 0.40   
PROD_LAG_STOP_EXPAND_THRESH_4P = 0.22   

ENEMY_TEMPO_STOP_EXPAND_ENABLED = True
ENEMY_TEMPO_STOP_EXPAND_TURN_MIN = 20
ENEMY_TEMPO_STOP_EXPAND_MIN_LAUNCHES = 2

EASY_ENEMY_STOP_EXPAND_ENABLED = False
EASY_ENEMY_STOP_EXPAND_TURN_MIN = 15
EASY_ENEMY_MAX_GARRISON = 20
EASY_ENEMY_MAX_DIST = 25.0
EASY_ENEMY_MIN_COUNT = 1

TURN_CUTOFF_STOP_EXPAND_ENABLED = True
TURN_CUTOFF_STOP_EXPAND_TURN = 80   

PROD_LEAD_STOP_EXPAND_4P_ENABLED = True
PROD_LEAD_STOP_EXPAND_4P_TURN_MIN = 25
PROD_LEAD_STOP_EXPAND_4P_THRESH = 0.35   

STOCKPILE_STOP_EXPAND_ENABLED = True
STOCKPILE_STOP_EXPAND_TURN_MIN = 20
STOCKPILE_STOP_EXPAND_MAX_GARRISON = 250

SURVIVAL_MODE_4P_ENABLED = False     # HARMFUL: blocks normal expansion at T30 (2 planets is normal in 4P mid-game)
SURVIVAL_MODE_4P_PLANET_MAX = 2
SURVIVAL_MODE_4P_TURN_MIN = 30  

# [COUNCIL] Enabled — this feature was fully written (gated to 2P only) but
# never activated. Once cheap neutrals are exhausted in 2P, stop wasting
# compute on expansion and redirect ships toward the enemy.
NEUTRAL_SATURATION_STOP_EXPAND_ENABLED = True   # was False
NEUTRAL_SATURATION_2P_ONLY = True
NEUTRAL_SATURATION_TURN_MIN = 20
NEUTRAL_SATURATION_CHEAP_GARRISON = 10
NEUTRAL_SATURATION_REACH_DIST = 30.0


Planet = namedtuple("Planet", ["id", "owner", "x", "y", "radius", "ships", "production"])
Fleet = namedtuple("Fleet", ["id", "owner", "x", "y", "angle", "from_planet_id", "ships"])

# ── GBC value function v2 ─────────────────────────────────────────────────
GBC_V2_ENABLED = False  # 2P-only model, net-negative in 4P Kaggle games
GBC_V2_WEIGHT  = 75   # delta_win_prob * weight added to hammer target score

GBC_4P_ENABLED = False  # HARMFUL (-10pp 4P): ship_ratio dominance anti-biases all expensive hammers
GBC_4P_WEIGHT  = 75   # delta_win_prob * weight added to hammer target score

GBC_4P_GATE_ENABLED    = False  # neutral (-1pp 4P): gate fires too rarely at threshold 0.10
GBC_4P_DANGER_THRESH   = 0.10  # P(win) below this → danger mode (we're badly losing)
GBC_4P_DANGER_MAX_TRAVEL = 18  # max hammer travel turns allowed in danger mode

GBC_V2_INIT = 0.0
GBC_V2_LR   = 0.05
GBC_V2_N    = 150
GBC_V2_COLS = ['step', 'remaining', 'my_planets', 'en_planets', 'neutrals', 'my_ships_planet', 'en_ships_planet', 'my_ships_transit', 'en_ships_transit', 'my_prod', 'en_prod', 'my_total', 'en_total', 'planet_diff', 'ship_diff', 'prod_diff', 'my_centrality', 'en_centrality', 'my_fleets', 'en_fleets', 'prod_ratio', 'ship_ratio', 'planet_ratio']
GBC_V2_TREES = [
  {'feature': [21, 14, 19, -2, -2, 22, -2, -2, 21, 20, -2, -2, 20, -2, -2], 'threshold': [0.514308, -71.5, 29.5, -2.0, -2.0, 0.532292, -2.0, -2.0, 0.540184, 0.483602, -2.0, -2.0, 0.489964, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001182, -0.141918, -0.52254, -2.261376, -0.57377, -0.053926, -0.307818, 0.989392, 0.373352, 0.234927, -0.070187, 1.21532, 0.399677, 1.170635, 1.674257]},
  {'feature': [21, 14, 20, -2, -2, 22, -2, -2, 21, 20, -2, -2, 20, -2, -2], 'threshold': [0.509613, -51.5, 0.522305, -2.0, -2.0, 0.537088, -2.0, -2.0, 0.540733, 0.483602, -2.0, -2.0, 0.489579, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000545, -0.135255, -0.474206, -2.049315, 0.332709, -0.045364, -0.252135, 0.998354, 0.34369, 0.2019, 0.024339, 1.061111, 0.377966, 0.984648, 1.619236]},
  {'feature': [21, 14, 20, -2, -2, 22, -2, -2, 21, 20, -2, -2, 20, -2, -2], 'threshold': [0.509613, -47.5, 0.522305, -2.0, -2.0, 0.532292, -2.0, -2.0, 0.540733, 0.483694, -2.0, -2.0, 0.489579, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001937, -0.125067, -0.445022, -1.90085, 0.264372, -0.037943, -0.223342, 0.980061, 0.326872, 0.190527, 0.012352, 1.027678, 0.359266, 0.971924, 1.567556]},
  {'feature': [21, 14, 19, -2, -2, 22, -2, -2, 22, 21, -2, -2, 21, -2, -2], 'threshold': [0.50952, -71.5, 29.5, -2.0, -2.0, 0.530331, -2.0, -2.0, 0.522774, 0.536154, -2.0, -2.0, 0.522, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001371, -0.12047, -0.443357, -1.881159, -0.220186, -0.043475, -0.244769, 0.909533, 0.310381, 0.168954, 0.317043, 1.124266, 0.34238, 0.966244, 1.521789]},
  {'feature': [21, 14, 19, -2, -2, 22, -2, -2, 20, 21, -2, -2, 21, -2, -2], 'threshold': [0.512656, -94.5, 28.5, -2.0, -2.0, 0.58114, -2.0, -2.0, 0.519356, 0.532241, -2.0, -2.0, 0.571263, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000934, -0.117352, -0.436395, -1.836272, -0.534353, -0.048049, -0.239475, 1.327513, 0.302691, 0.186749, 0.386139, 1.130343, 0.32648, 1.285495, 1.505619]},
  {'feature': [21, 13, 21, -2, -2, 22, -2, -2, 21, 20, -2, -2, 22, -2, -2], 'threshold': [0.50952, -1.5, 0.414441, -2.0, -2.0, 0.550862, -2.0, -2.0, 0.555176, 0.483694, -2.0, -2.0, 0.482676, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001243, -0.110279, -0.40789, -1.854946, -1.234275, -0.040036, -0.212266, 0.940877, 0.281848, 0.184902, 0.098848, 0.997869, 0.315994, 1.043628, 1.463377]},
  {'feature': [21, 14, 20, -2, -2, 20, -2, -2, 21, 20, -2, -2, 21, -2, -2], 'threshold': [0.514346, -49.5, 0.522305, -2.0, -2.0, 0.525212, -2.0, -2.0, 0.552924, 0.481812, -2.0, -2.0, 0.571298, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000152, -0.102992, -0.369864, -1.586839, 0.373528, -0.033493, -0.196732, 0.834267, 0.275092, 0.187301, 0.077691, 1.006191, 0.300491, 1.232754, 1.435795]},
  {'feature': [21, 15, 6, -2, -2, 20, -2, -2, 21, 20, -2, -2, 20, -2, -2], 'threshold': [0.504871, -2.5, 166.5, -2.0, -2.0, 0.542705, -2.0, -2.0, 0.539442, 0.53379, -2.0, -2.0, 0.489579, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001081, -0.101059, -0.364071, -0.130001, -1.570614, -0.033752, -0.183923, 0.899298, 0.246562, 0.128375, 0.273163, 1.143084, 0.280122, 0.75371, 1.387653]},
  {'feature': [21, 14, 19, -2, -2, 22, -2, -2, 22, 19, -2, -2, 21, -2, -2], 'threshold': [0.514308, -71.5, 29.5, -2.0, -2.0, 0.530331, -2.0, -2.0, 0.522774, 14.5, -2.0, -2.0, 0.517098, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001541, -0.091885, -0.353409, -1.545938, -0.084679, -0.030882, -0.182537, 0.724662, 0.249972, 0.157049, 0.574024, 1.3248, 0.268966, 0.401275, 1.350983]},
  {'feature': [21, 14, 6, -2, -2, 3, -2, -2, 22, 21, -2, -2, 21, -2, -2], 'threshold': [0.514308, -46.5, 134.0, -2.0, -2.0, 3.5, -2.0, -2.0, 0.522774, 0.552947, -2.0, -2.0, 0.517098, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002917, -0.083892, -0.316827, 0.602728, -1.404467, -0.022936, 0.311407, -0.210631, 0.23516, 0.141166, 0.403272, 1.146713, 0.254881, 0.364013, 1.319366]},
  {'feature': [21, 14, 6, -2, -2, 22, -2, -2, 21, 20, -2, -2, 20, -2, -2], 'threshold': [0.512673, -49.5, 144.5, -2.0, -2.0, 0.58114, -2.0, -2.0, 0.538752, 0.533712, -2.0, -2.0, 0.489579, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000506, -0.083212, -0.30798, 0.34763, -1.378753, -0.024539, -0.131818, 1.186966, 0.220879, 0.121784, 0.235798, 1.095559, 0.240289, 0.693239, 1.304333]},
  {'feature': [20, 14, 6, -2, -2, 4, -2, -2, 21, 3, -2, -2, 6, -2, -2], 'threshold': [0.514929, -35.5, 134.0, -2.0, -2.0, 20.5, -2.0, -2.0, 0.517137, 4.5, -2.0, -2.0, 367.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.003819, -0.078147, -0.307238, 0.395774, -1.365118, -0.019318, -0.17092, 0.267903, 0.213358, 0.132346, 1.188097, 0.348235, 0.231502, 1.278774, 0.914677]},
  {'feature': [21, 13, 19, -2, -2, 4, -2, -2, 21, 6, -2, -2, 21, -2, -2], 'threshold': [0.509613, -1.5, 28.5, -2.0, -2.0, 20.5, -2.0, -2.0, 0.55518, 363.0, -2.0, -2.0, 0.579747, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001785, -0.075999, -0.295683, -1.357502, -0.134126, -0.024627, -0.204525, 0.278592, 0.199843, 0.133629, 0.761772, -0.150314, 0.223262, 1.063656, 1.29453]},
  {'feature': [20, 14, 6, -2, -2, 21, -2, -2, 21, 19, -2, -2, 13, -2, -2], 'threshold': [0.514496, -35.5, 144.5, -2.0, -2.0, 0.514458, -2.0, -2.0, 0.516897, 24.5, -2.0, -2.0, 0.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001791, -0.074481, -0.274637, 0.141341, -1.273764, -0.020668, -0.137477, 0.667946, 0.194767, 0.125014, 0.463989, 1.52722, 0.21022, 0.805482, 1.239482]},
  {'feature': [20, 14, 19, -2, -2, 21, -2, -2, 14, 19, -2, -2, 22, -2, -2], 'threshold': [0.514929, -35.5, 29.5, -2.0, -2.0, 0.530501, -2.0, -2.0, -23.5, 24.0, -2.0, -2.0, 0.550862, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002285, -0.073581, -0.265726, -1.261705, -0.066438, -0.022359, -0.127851, 0.80566, 0.184938, 0.045009, -0.081567, 1.462947, 0.193202, 0.736673, 1.209849]},
  {'feature': [20, 14, 6, -2, -2, 21, -2, -2, 20, 21, -2, -2, 14, -2, -2], 'threshold': [0.52587, -31.5, 144.5, -2.0, -2.0, 0.537459, -2.0, -2.0, 0.590263, 0.504504, -2.0, -2.0, -5.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00244, -0.068305, -0.2459, 0.304436, -1.188909, -0.019584, -0.116504, 0.904969, 0.179868, 0.141275, 0.312759, 0.973907, 0.197016, 1.241366, 1.227534]},
  {'feature': [21, 13, 19, -2, -2, 4, -2, -2, 22, 6, -2, -2, 21, -2, -2], 'threshold': [0.517144, -1.5, 26.5, -2.0, -2.0, 20.5, -2.0, -2.0, 0.455844, 269.0, -2.0, -2.0, 0.539428, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002166, -0.059563, -0.241146, -1.220611, -0.161629, -0.017393, -0.16434, 0.266882, 0.16921, -0.01172, 0.373166, -1.239092, 0.17512, 0.56813, 1.195208]},
  {'feature': [21, 13, 19, -2, -2, 4, -2, -2, 6, 14, -2, -2, 14, -2, -2], 'threshold': [0.504684, -1.5, 28.5, -2.0, -2.0, 20.5, -2.0, -2.0, 359.5, 71.5, -2.0, -2.0, 136.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001786, -0.066485, -0.236289, -1.219272, 0.003422, -0.026569, -0.209296, 0.251971, 0.151147, 0.161426, 0.570272, 1.183777, 0.007775, -0.465869, 0.954744]},
  {'feature': [20, 14, 19, -2, -2, 10, -2, -2, 14, 19, -2, -2, 22, -2, -2], 'threshold': [0.511766, -51.5, 29.5, -2.0, -2.0, 57.5, -2.0, -2.0, -23.5, 24.5, -2.0, -2.0, 0.579796, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000611, -0.059252, -0.221328, -1.16798, 0.160132, -0.019451, -0.067656, -2.182416, 0.153342, 0.026764, -0.098311, 1.420005, 0.161716, 0.797083, 1.185441]},
  {'feature': [20, 14, 21, -2, -2, 2, -2, -2, 14, 19, -2, -2, 20, -2, -2], 'threshold': [0.511766, -51.5, 0.39989, -2.0, -2.0, 1.5, -2.0, -2.0, -31.5, 24.5, -2.0, -2.0, 0.541918, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00178, -0.059255, -0.222162, -1.329263, -0.828564, -0.019477, 0.3965, -0.133775, 0.144274, 0.016168, -0.25541, 1.403575, 0.151124, 0.584582, 1.101905]},
  {'feature': [20, 14, 6, -2, -2, 10, -2, -2, 21, 1, -2, -2, 13, -2, -2], 'threshold': [0.511766, -28.5, 161.5, -2.0, -2.0, 56.5, -2.0, -2.0, 0.517137, 232.5, -2.0, -2.0, 0.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002189, -0.049943, -0.194811, 0.125339, -1.066761, -0.010263, -0.031196, -2.060167, 0.134615, 0.074852, -1.19125, 0.429332, 0.14862, 0.550008, 1.12819]},
  {'feature': [20, 14, 6, -2, -2, 0, -2, -2, 22, 19, -2, -2, 14, -2, -2], 'threshold': [0.514496, -28.5, 107.5, -2.0, -2.0, 212.5, -2.0, -2.0, 0.565942, 24.5, -2.0, -2.0, -45.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001315, -0.050645, -0.19342, 0.73188, -1.036535, -0.011325, 0.007039, -0.467451, 0.13473, 0.09705, 0.461672, 1.261626, 0.147285, -0.070135, 1.132375]},
  {'feature': [21, 15, 6, -2, -2, 3, -2, -2, 21, 15, -2, -2, 22, -2, -2], 'threshold': [0.50448, -5.5, 278.5, -2.0, -2.0, 3.5, -2.0, -2.0, 0.539428, -9.5, -2.0, -2.0, 0.447222, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000489, -0.051679, -0.194373, -0.446331, -1.189366, -0.021891, 0.195651, -0.168739, 0.119399, 0.058941, -1.271874, 0.36464, 0.137248, 0.233189, 1.105968]},
  {'feature': [22, 14, 19, -2, -2, 10, -2, -2, 14, 19, -2, -2, 6, -2, -2], 'threshold': [0.5139, -38.5, 29.5, -2.0, -2.0, 57.5, -2.0, -2.0, -40.5, 24.5, -2.0, -2.0, 359.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001553, -0.048995, -0.172215, -1.041215, 0.325705, -0.01656, -0.057655, -1.947167, 0.116504, -0.054015, -0.501694, 1.040604, 0.124844, 0.972083, 0.248062]},
  {'feature': [21, 15, 6, -2, -2, 19, -2, -2, 15, -2, 21, -2, -2], 'threshold': [0.514298, -5.5, 132.5, -2.0, -2.0, 28.5, -2.0, -2.0, -7.5, -2.0, 0.555074, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [0.001551, -0.042121, -0.179519, 0.736965, -1.057225, -0.013417, -0.074576, 1.26541, 0.119442, -0.593149, 0.12216, 0.567705, 1.125631]},
  {'feature': [20, 14, 19, -2, -2, 10, -2, -2, 20, 18, -2, -2, 15, -2, -2], 'threshold': [0.514496, -28.5, 27.5, -2.0, -2.0, 58.0, -2.0, -2.0, 0.569098, 2.5, -2.0, -2.0, 1.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002204, -0.03897, -0.155354, -0.968029, 0.154804, -0.006528, -0.017088, -1.845942, 0.110415, 0.07799, 1.305088, 0.407154, 0.121773, -0.396611, 1.071176]},
  {'feature': [21, 14, 14, -2, -2, 19, -2, -2, 20, 8, -2, -2, 6, -2, -2], 'threshold': [0.514308, -188.5, -324.5, -2.0, -2.0, 24.5, -2.0, -2.0, 0.424457, 21.0, -2.0, -2.0, 363.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001944, -0.038029, -0.181019, -1.240729, -0.850277, -0.015906, -0.089964, 1.037657, 0.107208, -0.059801, 0.715687, -1.051803, 0.110091, 0.965794, 0.285003]},
  {'feature': [21, 13, 19, -2, -2, 3, -2, -2, 6, 14, -2, -2, 14, -2, -2], 'threshold': [0.50468, -1.5, 27.5, -2.0, -2.0, 3.5, -2.0, -2.0, 358.5, 66.5, -2.0, -2.0, 136.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000338, -0.040676, -0.153204, -1.01641, -0.005243, -0.014433, 0.217499, -0.138237, 0.096309, 0.103908, 0.39362, 1.078221, -0.009045, -0.578404, 0.9208]},
  {'feature': [21, 14, 6, -2, -2, 0, -2, -2, 10, 20, -2, -2, -2], 'threshold': [0.504947, -88.5, 145.0, -2.0, -2.0, 42.5, -2.0, -2.0, 50.5, 0.467914, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001087, -0.040914, -0.148781, 0.681875, -1.002031, -0.016666, 0.040113, -0.26223, 0.092911, 0.094882, 0.057046, 0.857226, -1.254355]},
  {'feature': [14, 19, 6, -2, -2, 14, -2, -2, 13, 0, -2, -2, 22, -2, -2], 'threshold': [-28.5, 29.5, 107.5, -2.0, -2.0, -327.5, -2.0, -2.0, 0.5, 227.5, -2.0, -2.0, 0.579796, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002458, -0.121051, -0.134787, 0.498221, -0.887037, 0.087735, -1.260471, 1.492265, 0.027679, -0.005041, 0.026044, -0.430894, 0.096111, 0.497966, 1.075566]},
  {'feature': [21, 14, 21, -2, -2, 19, -2, -2, 20, 21, -2, -2, 21, -2, -2], 'threshold': [0.516897, -189.5, 0.400136, -2.0, -2.0, 24.5, -2.0, -2.0, 0.489579, 0.563749, -2.0, -2.0, 0.539442, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002605, -0.036086, -0.152212, -1.178187, -0.637245, -0.018154, -0.097435, 0.954575, 0.088852, 0.011476, -0.201086, 0.887061, 0.094866, 0.419823, 1.065425]},
  {'feature': [20, 14, 19, -2, -2, 1, -2, -2, 22, 16, -2, -2, 21, -2, -2], 'threshold': [0.514929, -47.5, 27.5, -2.0, -2.0, 307.5, -2.0, -2.0, 0.591751, 38.065378, -2.0, -2.0, 0.511968, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000973, -0.033953, -0.125534, -0.956314, 0.237995, -0.011352, -0.421136, 0.008076, 0.086124, 0.064934, -0.558108, 0.505269, 0.097043, 0.93619, 1.087071]},
  {'feature': [22, 15, 6, -2, -2, 19, -2, -2, 14, 15, -2, -2, 16, -2, -2], 'threshold': [0.5139, -7.5, 249.5, -2.0, -2.0, 27.5, -2.0, -2.0, -88.5, 5.5, -2.0, -2.0, 32.428087, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002079, -0.034976, -0.13081, -0.142044, -1.02596, -0.016335, -0.082499, 1.140933, 0.080269, -0.084198, -0.84464, 0.41125, 0.083921, -0.874516, 0.793317]},
  {'feature': [21, 14, 21, -2, -2, 1, -2, -2, 6, 9, -2, -2, 14, -2, -2], 'threshold': [0.501919, -189.5, 0.389976, -2.0, -2.0, 457.5, -2.0, -2.0, 365.5, 8.5, -2.0, -2.0, 142.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000347, -0.031908, -0.133394, -1.150119, -0.605359, -0.015311, -0.255027, 0.043836, 0.073227, 0.080685, 0.006575, 0.774359, -0.032971, -0.600965, 0.897179]},
  {'feature': [20, 14, 19, -2, -2, 10, -2, -2, 2, 17, -2, -2, 21, -2, -2], 'threshold': [0.535048, -28.5, 28.5, -2.0, -2.0, 52.5, -2.0, -2.0, 6.5, 32.00591, -2.0, -2.0, 0.45352, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000751, -0.026115, -0.104633, -0.792025, 0.342872, -0.004651, -0.005552, -1.423872, 0.081409, 0.121301, -0.186764, 0.982684, 0.077515, -0.456109, 0.897197]},
  {'feature': [21, 0, 9, -2, -2, 16, -2, -2, 15, -2, 21, -2, -2], 'threshold': [0.514308, 82.5, 37.5, -2.0, -2.0, 46.48753, -2.0, -2.0, -8.5, -2.0, 0.538755, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.001122, -0.029695, -0.005709, -0.102367, 0.418607, -0.089593, -0.229614, -1.390729, 0.074365, -0.707937, 0.076031, 0.286883, 0.989051]},
  {'feature': [20, 14, 19, -2, -2, 10, -2, -2, 2, 17, -2, -2, 20, -2, -2], 'threshold': [0.525126, -94.5, 29.5, -2.0, -2.0, 57.5, -2.0, -2.0, 6.5, 31.784547, -2.0, -2.0, 0.566915, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000327, -0.026456, -0.109409, -0.965765, 0.167149, -0.009532, -0.030138, -1.716713, 0.072025, 0.121937, -0.449797, 0.991365, 0.066915, 0.238481, 0.994425]},
  {'feature': [14, 19, 7, -2, -2, 14, -2, -2, 22, 16, -2, -2, 16, -2, -2], 'threshold': [-94.5, 29.5, 243.5, -2.0, -2.0, -325.0, -2.0, -2.0, 0.5139, 37.844177, -2.0, -2.0, 39.852554, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000126, -0.10397, -0.115412, -1.09332, -0.747274, 0.058369, -1.281956, 1.570782, 0.015798, -0.007921, -0.383337, 0.012906, 0.066589, 0.196614, 0.789647]},
  {'feature': [15, 6, 20, -2, -2, 11, -2, -2, 21, 4, -2, -2, 6, -2, -2], 'threshold': [-5.5, 132.5, 0.405828, -2.0, -2.0, 823.0, -2.0, -2.0, 0.50468, 20.5, -2.0, -2.0, 513.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001412, -0.100342, 0.096346, -0.329712, 1.386496, -0.105674, -0.782402, -1.359476, 0.016774, -0.006897, -0.094402, 0.215217, 0.064707, 0.704879, -1.087294]},
  {'feature': [14, 19, 7, -2, -2, 14, -2, -2, 21, 4, -2, -2, 22, -2, -2], 'threshold': [-94.5, 26.5, 305.5, -2.0, -2.0, -346.5, -2.0, -2.0, 0.532594, 2.5, -2.0, -2.0, 0.447222, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001993, -0.092847, -0.105992, -1.047108, -0.60415, 0.039967, -1.190125, 1.552278, 0.016009, -0.003141, -0.365766, 0.029923, 0.066978, -0.191444, 0.948512]},
  {'feature': [21, 10, 19, -2, -2, 2, -2, -2, 22, 11, -2, -2, 3, -2, -2], 'threshold': [0.517167, 43.5, 24.5, -2.0, -2.0, 16.5, -2.0, -2.0, 0.455844, 75.5, -2.0, -2.0, 15.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000969, -0.023356, -0.009749, -0.063018, 1.078201, -0.114846, -0.657041, -1.359479, 0.060562, -0.028163, 1.314518, -0.428347, 0.063724, 0.814064, 1.206434]},
  {'feature': [14, 19, 6, -2, -2, 12, -2, -2, 20, 4, -2, -2, 21, -2, -2], 'threshold': [-88.5, 26.5, 144.5, -2.0, -2.0, 903.5, -2.0, -2.0, 0.535299, 20.5, -2.0, -2.0, 0.492079, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001871, -0.089739, -0.100949, 0.300337, -0.963298, 0.030462, 1.988927, -0.939516, 0.015478, -0.002871, -0.069399, 0.21478, 0.061504, 0.635742, 0.835697]},
  {'feature': [21, 10, 19, -2, -2, 2, -2, -2, 22, 21, -2, -2, 3, -2, -2], 'threshold': [0.516872, 43.5, 26.5, -2.0, -2.0, 16.5, -2.0, -2.0, 0.450806, 0.549435, -2.0, -2.0, 15.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00041, -0.020397, -0.008574, -0.056164, 1.199626, -0.099898, -0.610527, -1.174189, 0.054728, -0.033166, -0.640878, 0.577062, 0.057556, 0.762615, 1.210562]},
  {'feature': [14, 6, 16, -2, -2, 19, -2, -2, 22, 4, -2, -2, 21, -2, -2], 'threshold': [-28.5, 105.0, 46.61689, -2.0, -2.0, 28.5, -2.0, -2.0, 0.550862, 21.5, -2.0, -2.0, 0.499545, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000869, -0.075954, 0.128265, 1.127155, -1.00208, -0.084663, -0.750387, 0.287665, 0.016745, 0.001229, -0.057847, 0.255822, 0.059832, 0.889373, 0.897296]},
  {'feature': [20, 14, 19, -2, -2, 16, -2, -2, 4, 21, -2, -2, -2], 'threshold': [0.546061, -28.5, 27.5, -2.0, -2.0, 39.045898, -2.0, -2.0, 31.5, 0.492079, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001041, -0.01795, -0.072276, -0.660989, 0.276082, -0.002824, -0.30862, 0.046416, 0.055017, 0.056291, 0.615466, 0.873629, -1.201881]},
  {'feature': [14, 19, 9, -2, -2, 14, -2, -2, 21, 4, -2, -2, 6, -2, -2], 'threshold': [-170.5, 32.5, 39.5, -2.0, -2.0, -390.0, -2.0, -2.0, 0.530465, 3.5, -2.0, -2.0, 363.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000891, -0.087438, -0.093192, -1.015379, -1.242229, 0.041765, -1.308624, 1.808948, 0.011129, -0.003702, -0.371629, 0.031168, 0.05193, 0.877056, -0.119741]},
  {'feature': [14, 3, 21, -2, -2, 9, -2, -2, 21, 20, -2, -2, 6, -2, -2], 'threshold': [61.5, 3.5, 0.499211, -2.0, -2.0, 25.5, -2.0, -2.0, 0.525802, 0.513095, -2.0, -2.0, 359.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.0009, -0.016917, 0.044607, 0.869216, 0.133199, -0.030641, -0.431373, 0.004402, 0.052055, 0.153562, 1.179171, 0.845702, 0.049899, 0.939361, -0.108509]},
  {'feature': [14, 17, -2, 9, -2, -2, 16, 10, -2, -2, 10, -2, -2], 'threshold': [-189.5, 37.325304, -2.0, 46.5, -2.0, -2.0, 37.822254, 15.5, -2.0, -2.0, 57.5, -2.0, -2.0], 'left': [1, 2, -1, 4, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 3, -1, 5, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.001148, -0.085262, 0.107455, -0.087481, -0.986065, -1.21377, 0.010399, -0.065336, -0.026376, -1.027106, 0.017698, 0.106724, -1.577005]},
  {'feature': [21, 14, 8, -2, -2, 19, -2, -2, 3, 6, -2, -2, 21, -2, -2], 'threshold': [0.514308, -189.5, 943.0, -2.0, -2.0, 24.5, -2.0, -2.0, 14.5, 359.5, -2.0, -2.0, 0.526678, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [4.3e-05, -0.016854, -0.082258, -0.940262, -1.213942, -0.006639, -0.045298, 0.87915, 0.045768, 0.043308, 0.706104, -0.42296, 0.110879, 1.177565, 0.837822]},
  {'feature': [15, 6, 5, -2, -2, 19, -2, -2, 16, 16, -2, -2, 10, -2, -2], 'threshold': [-5.5, 153.0, 141.0, -2.0, -2.0, 24.5, -2.0, -2.0, 38.97657, 38.95878, -2.0, -2.0, 53.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001129, -0.06683, 0.097197, -0.067315, 1.317143, -0.073098, -0.797732, -0.038052, 0.011201, -0.04958, -0.152112, -1.94451, 0.020483, 0.121703, -1.339219]},
  {'feature': [20, 1, 3, -2, -2, 9, -2, -2, 6, 21, -2, -2, 18, -2, -2], 'threshold': [0.527373, 397.5, 6.5, -2.0, -2.0, 26.5, -2.0, -2.0, 327.5, 0.493257, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001755, -0.013576, -0.058902, -1.640615, -0.166894, 0.002125, -0.151954, 0.229197, 0.045078, 0.049546, 0.530132, 0.816159, -0.009651, -0.891829, 0.49698]},
  {'feature': [14, 19, 20, -2, -2, 14, -2, -2, 0, 9, -2, -2, 2, -2, -2], 'threshold': [-94.5, 26.5, 0.470143, -2.0, -2.0, -301.0, -2.0, -2.0, 232.5, 26.5, -2.0, -2.0, 6.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00133, -0.06708, -0.076907, -0.888298, -0.836277, 0.03024, -1.0875, 1.509241, 0.01123, 0.018125, -0.051286, 0.253557, -0.061708, -1.810025, -0.095844]},
  {'feature': [10, 1, 16, -2, -2, 16, -2, -2, 9, 16, -2, -2, 10, -2, -2], 'threshold': [15.5, 497.5, 55.845798, -2.0, -2.0, 60.415009, -2.0, -2.0, 25.5, 38.994032, -2.0, -2.0, 45.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000515, 0.040478, 0.068601, 0.374827, 1.561656, 0.015337, 0.115024, -1.116454, -0.016659, -0.077554, -1.003096, -0.314121, 0.006657, 0.090561, -0.568166]},
  {'feature': [21, 0, 9, -2, -2, 17, -2, -2, 22, 7, -2, -2, 20, -2, -2], 'threshold': [0.539428, 92.5, 37.5, -2.0, -2.0, 46.499214, -2.0, -2.0, 0.442222, 54.0, -2.0, -2.0, 0.530931, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002075, -0.016041, -0.001823, -0.079525, 0.365471, -0.054831, -0.111674, -1.351809, 0.044923, -0.041041, 0.853432, -1.100958, 0.046149, 0.769859, 0.941544]},
  {'feature': [22, 3, 0, -2, -2, 9, -2, -2, 16, -2, 20, -2, -2], 'threshold': [0.542262, 1.5, 2.5, -2.0, -2.0, 25.5, -2.0, -2.0, 32.443998, -2.0, 0.51676, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.000215, -0.013703, 0.066451, 0.113451, 0.615488, -0.020513, -0.26652, 0.013994, 0.042717, -1.29624, 0.04405, 1.105857, 0.710738]},
  {'feature': [12, 19, 22, -2, -2, 22, -2, -2, 9, 6, -2, -2, -2], 'threshold': [949.5, 22.5, 0.4861, -2.0, -2.0, 0.472136, -2.0, -2.0, 65.5, 301.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [0.001216, 0.007838, 0.003451, -0.378826, 0.064108, 0.110684, 1.496114, 0.649863, -0.078275, -0.070855, 0.994287, -0.758721, -1.537883]},
  {'feature': [21, 3, 21, -2, -2, 16, -2, -2, 14, -2, 22, -2, -2], 'threshold': [0.516897, 3.5, 0.498634, -2.0, -2.0, 37.977203, -2.0, -2.0, 7.5, -2.0, 0.450806, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.003653, -0.019035, 0.033705, 0.973286, 0.050542, -0.030367, -0.667913, -0.106131, 0.03809, 1.302487, 0.037031, -0.263032, 0.686152]},
  {'feature': [21, 6, 21, -2, -2, 9, -2, -2, 10, 3, -2, -2, 20, -2, -2], 'threshold': [0.53856, 84.5, 0.491881, -2.0, -2.0, 25.5, -2.0, -2.0, 28.5, 12.5, -2.0, -2.0, 0.505556, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000199, -0.012558, 0.02873, 0.655274, 0.064563, -0.024401, -0.416352, 0.000673, 0.041127, 0.036141, 0.874717, -1.530543, 0.063136, 1.056864, 0.967587]},
  {'feature': [10, 2, 1, -2, -2, 21, -2, -2, 5, 6, -2, -2, 7, -2, -2], 'threshold': [45.5, 11.5, 362.5, -2.0, -2.0, 0.490656, -2.0, -2.0, 475.0, 305.0, -2.0, -2.0, 557.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00259, 0.009457, -0.006384, -0.473908, 0.045513, 0.035496, -0.351663, 0.354617, -0.075074, -0.060737, 0.393954, -0.655088, -0.2486, -0.924996, -1.64406]},
  {'feature': [13, 19, 11, -2, -2, 14, -2, -2, 16, 16, -2, -2, 10, -2, -2], 'threshold': [-1.5, 24.5, 959.0, -2.0, -2.0, -327.5, -2.0, -2.0, 37.822254, 37.798199, -2.0, -2.0, 61.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002574, -0.050822, -0.063779, -0.595635, -1.456565, 0.047878, -0.973229, 1.570237, 0.011631, -0.051219, -0.14494, -1.90506, 0.01831, 0.109984, -1.500796]},
  {'feature': [22, 4, 16, -2, -2, 17, -2, -2, 5, 6, -2, -2, 20, -2, -2], 'threshold': [0.550862, 21.5, 48.06464, -2.0, -2.0, 34.004124, -2.0, -2.0, 106.5, 12.5, -2.0, -2.0, 0.527525, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001636, -0.013748, -0.024138, -0.062863, -0.648952, 0.041403, -0.212721, 0.247696, 0.038571, 0.08273, -0.025189, 0.990496, 0.033806, -0.43824, 0.794342]},
  {'feature': [21, 3, 16, -2, -2, 9, -2, -2, 20, 8, -2, -2, 21, -2, -2], 'threshold': [0.555176, 3.5, 32.343418, -2.0, -2.0, 25.5, -2.0, -2.0, 0.530931, 26.0, -2.0, -2.0, 0.569783, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002173, -0.012988, 0.037231, -0.324674, 0.235732, -0.02309, -0.350113, 0.000673, 0.03887, 0.074108, 1.165718, 0.638877, 0.035205, 0.224965, 1.038771]},
  {'feature': [14, 6, 16, -2, -2, 19, -2, -2, 10, 16, -2, -2, 6, -2, -2], 'threshold': [-23.5, 166.0, 46.64143, -2.0, -2.0, 27.5, -2.0, -2.0, 57.5, 36.389969, -2.0, -2.0, 532.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000662, -0.043712, 0.082651, 0.828526, -1.192886, -0.057809, -0.656086, 0.447557, 0.008616, 0.009829, -0.285936, 0.081336, -0.292425, -1.473857, -1.38972]},
  {'feature': [6, 19, 14, -2, -2, 22, -2, -2, 1, 9, -2, -2, 10, -2, -2], 'threshold': [351.5, 22.5, -31.5, -2.0, -2.0, 0.471405, -2.0, -2.0, 182.5, 38.5, -2.0, -2.0, 43.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000539, 0.009145, 0.004518, -0.427447, 0.058286, 0.095421, 1.328563, 0.587037, -0.042694, -0.179107, -0.531274, -1.986646, -0.034, -0.015622, -0.653128]},
  {'feature': [12, 19, 13, -2, -2, 22, -2, -2, 11, 2, -2, -2, 6, -2, -2], 'threshold': [1004.5, 24.5, -1.5, -2.0, -2.0, 0.47913, -2.0, -2.0, 1105.5, 17.5, -2.0, -2.0, 522.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000115, 0.005413, 0.002059, -0.482294, 0.044411, 0.099969, 1.332591, 0.651582, -0.076935, -0.066613, -0.842297, -0.973845, -0.258411, -1.018423, -1.496269]},
  {'feature': [12, 19, 13, -2, -2, 22, -2, -2, 7, 14, -2, -2, 5, -2, -2], 'threshold': [1023.5, 24.5, -1.5, -2.0, -2.0, 0.47913, -2.0, -2.0, 563.0, -44.5, -2.0, -2.0, 418.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001896, 0.006808, 0.003329, -0.475544, 0.053375, 0.106058, 1.28052, 0.744535, -0.07721, -0.059119, -1.023063, 0.15622, -0.225375, -0.56638, -1.353072]},
  {'feature': [21, 0, 4, -2, -2, 3, -2, -2, 20, 0, -2, -2, 21, -2, -2], 'threshold': [0.555176, 212.5, 6.5, -2.0, -2.0, 6.5, -2.0, -2.0, 0.530931, 2.5, -2.0, -2.0, 0.571263, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001495, -0.011339, -0.004492, -0.201117, 0.052692, -0.06579, -1.69206, -0.178676, 0.03541, 0.071602, 0.467746, 1.05223, 0.031736, -0.155389, 1.036124]},
  {'feature': [14, 19, 19, -2, -2, 14, -2, -2, 16, 16, -2, -2, 16, -2, -2], 'threshold': [-93.5, 27.5, 10.5, -2.0, -2.0, -352.5, -2.0, -2.0, 37.842468, 37.798199, -2.0, -2.0, 48.883631, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000666, -0.047201, -0.053927, -0.32521, -0.894138, 0.033502, -1.181412, 1.10085, 0.00774, -0.050053, -0.145596, -1.764006, 0.013697, 0.117202, -0.187925]},
  {'feature': [20, 1, 16, -2, -2, 9, -2, -2, 12, 14, -2, -2, -2], 'threshold': [0.56022, 272.5, 41.321785, -2.0, -2.0, 26.5, -2.0, -2.0, 930.0, -64.0, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [0.000655, -0.008728, -0.062253, 0.396985, -0.719175, -0.002507, -0.120384, 0.110035, 0.033985, 0.032605, -0.57655, 0.806358, 1.507156]},
  {'feature': [10, 1, 16, -2, -2, 16, -2, -2, 9, 16, -2, -2, 16, -2, -2], 'threshold': [15.5, 497.5, 55.697895, -2.0, -2.0, 55.655748, -2.0, -2.0, 25.5, 38.029879, -2.0, -2.0, 47.273689, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [6.3e-05, 0.02981, 0.056702, 0.322343, 1.347169, 0.005286, 0.075628, -0.587908, -0.012108, -0.061372, -0.992915, -0.290089, 0.006924, 0.076144, -0.685707]},
  {'feature': [10, 0, 16, -2, -2, 16, -2, -2, 9, 17, -2, -2, 16, -2, -2], 'threshold': [15.5, 2.5, 56.046654, -2.0, -2.0, 55.657885, -2.0, -2.0, 25.5, 38.961275, -2.0, -2.0, 46.72073, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00059, 0.029015, 0.005114, 0.082338, -0.857112, 0.054901, 0.307811, 1.340611, -0.011529, -0.055501, -0.793273, -0.227781, 0.005426, 0.078326, -0.552862]},
  {'feature': [21, 4, 17, -2, -2, 16, -2, -2, 20, 10, -2, -2, 21, -2, -2], 'threshold': [0.552681, 3.5, 49.95122, -2.0, -2.0, 38.97657, -2.0, -2.0, 0.530931, 24.5, -2.0, -2.0, 0.569921, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000785, -0.00982, -0.058365, -0.309975, -1.53036, -0.001416, -0.211667, 0.037497, 0.032891, 0.068017, 0.367697, 1.136953, 0.029082, 0.00777, 1.032877]},
  {'feature': [3, 1, 16, -2, -2, 9, -2, -2, 22, 21, -2, -2, 1, -2, -2], 'threshold': [17.5, 272.5, 46.57062, -2.0, -2.0, 26.5, -2.0, -2.0, 0.471405, 0.482709, -2.0, -2.0, 422.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001853, 0.006283, -0.04902, -0.07621, -1.563833, 0.011838, -0.039224, 0.187857, -0.070236, -0.051683, -1.033132, 0.497688, -0.21637, -1.337467, -0.269728]},
  {'feature': [10, 0, 4, -2, -2, 16, -2, -2, 16, 17, -2, -2, 0, -2, -2], 'threshold': [15.5, 2.5, 22.5, -2.0, -2.0, 55.657885, -2.0, -2.0, 48.134655, 35.150343, -2.0, -2.0, 10.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002174, 0.029162, 0.004372, -0.152044, 0.204155, 0.056318, 0.320804, 1.304146, -0.009336, -0.001867, -1.330579, 0.006342, -0.108281, 0.222929, -1.285847]},
  {'feature': [22, 2, 16, -2, -2, -2, 20, 21, -2, -2, 14, -2, -2], 'threshold': [0.522774, 18.5, 48.88658, -2.0, -2.0, -2.0, 0.50658, 0.491481, -2.0, -2.0, -23.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.00187, -0.012209, -0.011328, -0.022474, -0.298888, -1.666784, 0.025489, 0.116882, 1.181057, 0.3662, 0.023037, -0.179414, 0.548861]},
  {'feature': [21, 3, 17, -2, -2, 16, -2, -2, 10, 21, -2, -2, 20, -2, -2], 'threshold': [0.540184, 1.5, 32.688206, -2.0, -2.0, 47.729536, -2.0, -2.0, 36.5, 0.573687, -2.0, -2.0, 0.505912, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00118, -0.010324, 0.05728, -0.235149, 0.320039, -0.015992, -0.037524, -0.432837, 0.029476, 0.02673, 0.049576, 1.002333, 0.072809, 1.19924, 1.061019]},
  {'feature': [14, 4, 17, -2, -2, 16, -2, -2, 6, 20, -2, -2, -2], 'threshold': [61.5, 6.5, 49.486174, -2.0, -2.0, 39.008698, -2.0, -2.0, 508.5, 0.514087, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001074, -0.009678, -0.035136, -0.146216, -1.325915, 0.003075, -0.235821, 0.08178, 0.027827, 0.028836, 0.624229, 0.799535, -0.888718]},
  {'feature': [6, 19, 14, -2, -2, 0, -2, -2, 1, 9, -2, -2, 9, -2, -2], 'threshold': [365.5, 24.5, -69.5, -2.0, -2.0, 137.5, -2.0, -2.0, 182.5, 39.5, -2.0, -2.0, 66.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00049, 0.008082, 0.005053, -0.597273, 0.052898, 0.081014, 0.945259, -1.66475, -0.038203, -0.165495, -0.692745, -1.892614, -0.029881, -0.189814, -1.373115]},
  {'feature': [21, 19, 6, -2, -2, -2, 19, 10, -2, -2, 22, -2, -2], 'threshold': [0.397138, 35.5, 44.0, -2.0, -2.0, -2.0, 24.5, 15.5, -2.0, -2.0, 0.455844, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.002071, -0.050979, -0.047826, 0.364804, -0.969516, -1.228115, 0.007104, 0.004134, 0.167328, -0.034881, 0.086692, 1.598579, 0.523676]},
  {'feature': [6, 21, 1, -2, -2, 2, -2, -2, 9, 1, -2, -2, 0, -2, -2], 'threshold': [123.5, 0.494949, 452.5, -2.0, -2.0, 1.5, -2.0, -2.0, 26.5, 462.5, -2.0, -2.0, 42.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.003008, 0.028229, 0.104175, -0.903956, 0.672444, 0.019815, 0.23645, 0.075952, -0.008581, -0.046245, 0.140809, -0.749955, 0.00925, 0.299035, -0.202214]},
  {'feature': [10, 16, 16, -2, -2, 10, -2, -2, 5, 1, -2, -2, 0, -2, -2], 'threshold': [45.5, 36.17256, 34.969166, -2.0, -2.0, 18.5, -2.0, -2.0, 469.5, 337.5, -2.0, -2.0, 62.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000734, 0.005809, -0.061691, -0.029681, -0.832003, 0.009718, 0.224439, -0.012489, -0.058312, -0.045914, -1.332435, -0.307329, -0.194534, -1.443954, -0.500259]},
  {'feature': [2, 0, 9, -2, -2, 17, -2, -2, 12, 20, -2, -2, 7, -2, -2], 'threshold': [11.5, 117.5, 27.5, -2.0, -2.0, 46.499214, -2.0, -2.0, 1024.0, 0.4671, -2.0, -2.0, 560.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000804, -0.012738, 5.2e-05, -0.091687, 0.267379, -0.067804, -0.144369, -1.460546, 0.018275, 0.023184, -0.502269, 0.224719, -0.10227, -0.590693, -0.966333]},
  {'feature': [6, 16, 10, -2, -2, 16, -2, -2, 0, 9, -2, -2, 11, -2, -2], 'threshold': [383.5, 38.587713, 15.5, -2.0, -2.0, 38.59993, -2.0, -2.0, 297.5, 66.0, -2.0, -2.0, 746.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000257, 0.006149, -0.032388, 0.019486, -0.522088, 0.011546, 1.937609, 0.058028, -0.038515, -0.030463, -0.210039, -1.335533, -0.151994, -0.586029, -1.679795]},
  {'feature': [3, 10, 0, -2, -2, 1, -2, -2, 2, 17, -2, -2, 17, -2, -2], 'threshold': [8.5, 31.5, 227.5, -2.0, -2.0, 452.5, -2.0, -2.0, 11.5, 49.964342, -2.0, -2.0, 38.614027, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000761, 0.016479, 0.010659, 0.110649, -0.610446, 0.386837, 1.87222, 1.078073, -0.015952, -0.036308, -0.199259, -1.227713, 0.004281, 1.060408, -0.008077]},
  {'feature': [14, 9, 20, -2, -2, 0, -2, -2, 10, 16, -2, -2, 12, -2, -2], 'threshold': [-189.5, 42.5, 0.461032, -2.0, -2.0, 70.0, -2.0, -2.0, 57.5, 37.822254, -2.0, -2.0, 1083.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001016, -0.043438, -0.041052, -0.948836, 0.179075, -0.101444, -0.660616, -1.227187, 0.005836, 0.006797, -0.177959, 0.064763, -0.212984, -1.359109, -1.264383]},
  {'feature': [21, 4, 17, -2, -2, 1, -2, -2, 20, 20, -2, -2, 22, -2, -2], 'threshold': [0.571263, 20.5, 48.95435, -2.0, -2.0, 422.5, -2.0, -2.0, 0.532971, 0.441518, -2.0, -2.0, 0.57634, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002998, -0.010096, -0.016285, -0.055945, -0.518277, 0.020332, 1.588078, 0.068381, 0.027526, 0.061247, -0.263022, 1.09663, 0.025038, 1.038578, 1.024939]},
  {'feature': [21, 7, 4, -2, -2, 1, -2, -2, 20, 16, -2, -2, 22, -2, -2], 'threshold': [0.537911, 512.5, 20.5, -2.0, -2.0, 407.5, -2.0, -2.0, 0.52587, 48.24954, -2.0, -2.0, 0.52087, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002162, -0.010798, -0.00774, -0.073088, 0.095746, -0.084758, -0.881537, -0.11348, 0.026834, 0.058786, 0.691956, -0.244943, 0.022707, -0.300963, 0.947844]},
  {'feature': [14, 19, 6, -2, -2, 14, -2, -2, 10, 21, -2, -2, 16, -2, -2], 'threshold': [-23.5, 27.5, 89.5, -2.0, -2.0, -352.5, -2.0, -2.0, 52.5, 0.478324, -2.0, -2.0, 43.923309, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000259, -0.029689, -0.037298, 0.492689, -0.456468, 0.067885, -1.136463, 1.035991, 0.0067, 0.007889, 0.781529, 0.035055, -0.17623, -0.338305, -1.342239]},
  {'feature': [16, 3, 16, -2, -2, 2, -2, -2, 17, 2, -2, -2, 0, -2, -2], 'threshold': [48.88658, 17.5, 39.006523, -2.0, -2.0, 18.5, -2.0, -2.0, 52.202881, 10.5, -2.0, -2.0, 2.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000127, 0.004881, 0.008328, -0.139979, 0.09106, -0.060141, -0.737611, -1.291159, -0.042887, -0.073045, -0.519836, 0.460052, 0.044542, -0.090555, 0.590088]},
  {'feature': [15, 6, -2, 18, -2, -2, 16, 16, -2, -2, 16, -2, -2], 'threshold': [-5.5, 113.0, -2.0, 14.5, -2.0, -2.0, 37.822254, 37.798199, -2.0, -2.0, 48.958323, -2.0, -2.0], 'left': [1, 2, -1, 4, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 3, -1, 5, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.000895, -0.033904, 0.782839, -0.03777, -0.401901, -0.842197, 0.006037, -0.04236, -0.115577, -1.624879, 0.010906, 0.094508, -0.15641]},
  {'feature': [1, 10, 16, -2, -2, 14, -2, -2, 9, 0, -2, -2, 2, -2, -2], 'threshold': [272.5, 39.5, 46.57062, -2.0, -2.0, -35.0, -2.0, -2.0, 26.5, 2.5, -2.0, -2.0, 8.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00163, -0.039043, -0.001209, 0.230453, -1.439499, -0.156447, -0.595407, -1.446362, 0.005957, -0.012342, -0.26776, 0.174302, 0.021231, 0.591519, 0.091844]},
  {'feature': [14, 21, 19, -2, -2, 19, -2, -2, 6, 16, -2, -2, 18, -2, -2], 'threshold': [-189.5, 0.389976, 35.5, -2.0, -2.0, 26.5, -2.0, -2.0, 542.5, 48.88658, -2.0, -2.0, 15.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001312, -0.037438, -0.042449, -0.993105, -1.182703, -0.012856, -0.662949, 1.029669, 0.00543, 0.006607, 0.065554, -0.181176, -0.164981, -1.375411, -0.594018]},
  {'feature': [10, 16, 0, -2, -2, 3, -2, -2, 9, 22, -2, -2, 16, -2, -2], 'threshold': [18.5, 36.17256, 77.5, -2.0, -2.0, 10.5, -2.0, -2.0, 25.5, 0.474937, -2.0, -2.0, 47.273689, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000987, 0.020173, -0.050151, -0.073892, -1.446424, 0.030825, 0.205887, 1.724459, -0.009157, -0.049658, -0.286808, -0.390851, 0.004158, 0.054488, -0.569299]},
  {'feature': [14, 19, 3, -2, -2, 14, -2, -2, 16, 21, -2, -2, 1, -2, -2], 'threshold': [-94.5, 26.5, 12.5, -2.0, -2.0, -351.5, -2.0, -2.0, 48.221828, 0.455842, -2.0, -2.0, 417.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [1.9e-05, -0.032619, -0.039707, -0.754847, -0.640313, 0.03575, -1.123695, 1.008554, 0.004835, 0.009665, 0.951598, 0.041679, -0.031203, -1.161822, 0.012616]},
  {'feature': [14, 19, 10, -2, -2, 14, -2, -2, 21, 10, -2, -2, 16, -2, -2], 'threshold': [-94.5, 26.5, 31.5, -2.0, -2.0, -327.5, -2.0, -2.0, 0.4389, 16.5, -2.0, -2.0, 39.964458, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002358, -0.029584, -0.035714, -0.86767, -0.54457, 0.031122, -0.881649, 1.041835, 0.007055, 0.128799, 0.526716, 2.054206, 0.005541, -0.112416, 0.067709]},
  {'feature': [1, 10, 10, -2, -2, 17, -2, -2, 9, 4, -2, -2, 2, -2, -2], 'threshold': [307.5, 27.5, 25.5, -2.0, -2.0, 40.690659, -2.0, -2.0, 26.5, 10.5, -2.0, -2.0, 8.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000777, -0.033967, 0.048189, -0.364705, 1.555602, -0.086429, 0.998223, -0.906791, 0.00575, -0.010576, -0.519634, 0.080706, 0.019639, 0.677256, 0.066932]},
  {'feature': [10, 0, 2, -2, -2, 16, -2, -2, 17, 16, -2, -2, 16, -2, -2], 'threshold': [15.5, 37.5, 1.5, -2.0, -2.0, 38.619675, -2.0, -2.0, 36.887527, 38.549753, -2.0, -2.0, 49.577013, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000892, 0.020808, 0.008131, 0.233428, -0.060305, 0.059535, 1.407153, 0.506178, -0.007579, -0.151093, -1.098216, 0.581387, -0.00438, -0.003419, -1.018158]},
  {'feature': [14, 4, 17, -2, -2, 17, -2, -2, 6, 15, -2, -2, 18, -2, -2], 'threshold': [64.5, 16.5, 48.953798, -2.0, -2.0, 25.537415, -2.0, -2.0, 359.5, 3.5, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002707, -0.010157, -0.018721, -0.064535, -0.736098, 0.014639, -0.797998, 0.081585, 0.022594, 0.025564, 0.777541, 0.884036, -0.027551, -2.48307, 0.206237]},
  {'feature': [6, 20, 16, -2, -2, 4, -2, -2, 9, 16, -2, -2, 1, -2, -2], 'threshold': [152.5, 0.5, 33.471771, -2.0, -2.0, 31.5, -2.0, -2.0, 25.5, 39.039103, -2.0, -2.0, 462.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000685, 0.019563, 0.083764, -0.377448, 0.493179, 0.010444, 0.108003, -0.37724, -0.010387, -0.047449, -0.885327, -0.248871, 0.001883, -0.116018, 0.143083]},
  {'feature': [2, 0, 9, -2, -2, 17, -2, -2, 4, 16, -2, -2, 10, -2, -2], 'threshold': [11.5, 97.5, 27.5, -2.0, -2.0, 46.499214, -2.0, -2.0, 10.5, 38.645885, -2.0, -2.0, 37.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001938, -0.0079, 0.004056, -0.072395, 0.303511, -0.050358, -0.09314, -1.212963, 0.017747, 0.02577, 1.332107, 0.176279, -0.03331, 0.000417, -0.75664]},
  {'feature': [16, 16, 9, -2, -2, 1, -2, -2, 10, 3, -2, -2, 9, -2, -2], 'threshold': [35.013941, 34.978691, 7.5, -2.0, -2.0, 287.5, -2.0, -2.0, 17.5, 9.5, -2.0, -2.0, 25.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000514, -0.061898, -0.024424, -0.283108, 0.351757, -0.316265, -1.378378, -1.545098, 0.002136, 0.023069, 0.143916, 1.779198, -0.00727, -0.328096, 0.033701]},
  {'feature': [21, 2, 1, -2, -2, 16, -2, -2, 20, 20, -2, -2, 22, -2, -2], 'threshold': [0.555176, 1.5, 497.5, -2.0, -2.0, 48.879593, -2.0, -2.0, 0.536811, 0.381048, -2.0, -2.0, 0.534524, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000347, -0.00671, 0.033454, 0.548784, -0.003119, -0.010454, -0.028504, -0.361908, 0.023789, 0.05186, -0.626885, 0.842473, 0.020564, 0.077277, 1.022469]},
  {'feature': [17, 16, 3, -2, -2, 16, -2, -2, 22, 1, -2, -2, 4, -2, -2], 'threshold': [52.202881, 49.370871, 17.5, -2.0, -2.0, 49.386204, -2.0, -2.0, 0.5, 492.5, -2.0, -2.0, 31.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001676, -0.000666, 0.003364, 0.036691, -0.73571, -0.068013, -1.644401, -0.387607, 0.062281, 0.122869, 1.350707, 0.353951, 0.023958, 0.413634, -0.535605]},
  {'feature': [14, 6, 16, -2, -2, 19, -2, -2, 2, 18, -2, -2, 6, -2, -2], 'threshold': [-35.5, 92.5, 44.570145, -2.0, -2.0, 27.5, -2.0, -2.0, 11.5, 17.5, -2.0, -2.0, 503.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001307, -0.029003, 0.138278, 1.457416, -0.453936, -0.034233, -0.543397, 0.394804, 0.004153, -0.00733, -0.024234, -0.724201, 0.020536, 0.209579, -0.5852]},
  {'feature': [3, 10, 0, -2, -2, 1, -2, -2, 10, 21, -2, -2, 19, -2, -2], 'threshold': [8.5, 31.5, 212.5, -2.0, -2.0, 447.5, -2.0, -2.0, 17.5, 0.513889, -2.0, -2.0, 24.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000259, 0.012945, 0.007262, 0.092143, -0.614852, 0.361794, 1.838237, 1.048918, -0.011834, 0.140654, 1.295931, 1.076336, -0.014221, -0.114917, 0.500524]},
  {'feature': [6, 16, 1, -2, -2, 16, -2, -2, 9, 1, -2, -2, -2], 'threshold': [351.5, 36.17256, 422.5, -2.0, -2.0, 47.507231, -2.0, -2.0, 66.0, 182.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-3.6e-05, 0.00552, -0.047447, -1.342493, -0.081802, 0.008935, 0.094064, -0.11311, -0.023659, -0.021009, -0.847665, -0.116208, -1.280164]},
  {'feature': [6, 21, 16, -2, -2, 2, -2, -2, 2, 16, -2, -2, 17, -2, -2], 'threshold': [150.5, 0.484519, 46.634735, -2.0, -2.0, 1.5, -2.0, -2.0, 11.5, 39.043215, -2.0, -2.0, 38.597567, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002131, 0.018236, 0.091394, 0.758122, -0.122656, 0.011732, 0.204488, 0.028892, -0.006887, -0.021961, -0.694477, -0.07365, 0.011466, 0.937515, 0.046133]},
  {'feature': [21, 11, 17, -2, -2, 18, -2, -2, 22, 0, -2, -2, 20, -2, -2], 'threshold': [0.532581, 1039.5, 43.192284, -2.0, -2.0, 22.5, -2.0, -2.0, 0.447222, 42.5, -2.0, -2.0, 0.530931, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001939, -0.008703, -0.007402, -0.109324, 0.029931, -0.138239, -1.076936, -0.029964, 0.01964, -0.03919, -0.839562, 1.019384, 0.021063, 0.622368, 0.757818]},
  {'feature': [3, 19, 2, -2, -2, 22, -2, -2, 22, 21, -2, -2, 17, -2, -2], 'threshold': [17.5, 24.5, 13.5, -2.0, -2.0, 0.48436, -2.0, -2.0, 0.472953, 0.482709, -2.0, -2.0, 43.569206, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000637, 0.003215, 0.000903, -0.031871, 0.228533, 0.067212, 1.217446, 0.396998, -0.043192, -0.028484, -0.975956, 0.47229, -0.179954, -1.41433, -0.391069]},
  {'feature': [10, 19, 14, -2, -2, 22, -2, -2, 11, 7, -2, -2, 8, -2, -2], 'threshold': [45.5, 22.5, -28.5, -2.0, -2.0, 0.453079, -2.0, -2.0, 811.5, 442.5, -2.0, -2.0, 482.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002892, 0.000609, -0.002288, -0.321996, 0.010815, 0.064276, 1.262051, 0.429496, -0.042918, -0.021916, -0.584247, 0.855109, -0.102925, -1.056549, -0.289772]},
  {'feature': [14, 4, 17, -2, -2, 6, -2, -2, 20, 17, -2, -2, 21, -2, -2], 'threshold': [75.5, 16.5, 48.953798, -2.0, -2.0, 275.5, -2.0, -2.0, 0.530151, 42.050667, -2.0, -2.0, 0.53145, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-5e-05, -0.006064, -0.013077, -0.043455, -0.598765, 0.014054, 0.085571, -0.850681, 0.021036, 0.056953, 0.061305, 0.898001, 0.016583, 1.091917, 0.796974]},
  {'feature': [21, 17, 17, -2, -2, 16, -2, -2, 20, 20, -2, -2, 20, -2, -2], 'threshold': [0.552924, 52.202881, 48.88658, -2.0, -2.0, 54.580076, -2.0, -2.0, 0.537407, 0.41523, -2.0, -2.0, 0.543584, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00028, -0.005773, -0.008145, -0.017502, -0.34909, 0.063373, 0.751678, 0.053619, 0.019956, 0.043881, -0.426747, 0.823648, 0.016949, -1.216226, 0.996296]},
  {'feature': [17, 16, 17, -2, -2, 16, -2, -2, 1, 16, -2, -2, 16, -2, -2], 'threshold': [52.266979, 49.370871, 46.155243, -2.0, -2.0, 49.394989, -2.0, -2.0, 497.5, 55.657885, -2.0, -2.0, 55.655748, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000561, -0.002845, 0.000284, -0.029693, 0.161237, -0.056379, -1.688778, -0.302419, 0.060061, 0.116317, 0.458534, 1.306301, 0.004549, 0.723217, -0.561679]},
  {'feature': [14, 19, 20, -2, -2, 14, -2, -2, 6, 16, -2, -2, 16, -2, -2], 'threshold': [-94.5, 26.5, 0.470143, -2.0, -2.0, -301.0, -2.0, -2.0, 512.5, 37.822254, -2.0, -2.0, 42.227697, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001096, -0.026807, -0.033614, -0.718652, -0.602885, 0.035163, -0.735071, 1.029273, 0.005151, 0.006501, -0.159566, 0.062853, -0.125365, 0.07145, -0.822179]},
  {'feature': [4, 10, 0, -2, -2, 17, -2, -2, -2], 'threshold': [35.5, 15.5, 37.5, -2.0, -2.0, 35.157961, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, -1], 'value': [0.000339, 0.000881, 0.018404, 0.024221, 0.855135, -0.006492, -0.931465, -0.030265, -1.183376]},
  {'feature': [6, 3, 10, -2, -2, 11, -2, -2, 1, 9, -2, -2, 9, -2, -2], 'threshold': [383.5, 12.5, 33.5, -2.0, -2.0, 599.5, -2.0, -2.0, 202.5, 38.5, -2.0, -2.0, 43.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00119, 0.005697, 0.001126, 0.034263, -0.187276, 0.032553, -0.148794, 0.327129, -0.025605, -0.100534, -0.238476, -1.622333, -0.019778, -0.082852, -0.442047]},
  {'feature': [21, 4, 10, -2, -2, 17, -2, -2, 20, 10, -2, -2, 21, -2, -2], 'threshold': [0.552681, 3.5, 29.5, -2.0, -2.0, 43.23653, -2.0, -2.0, 0.530931, 24.5, -2.0, -2.0, 0.569912, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001017, -0.006184, -0.033368, 0.109489, -0.376763, -0.001398, -0.071603, 0.066471, 0.018059, 0.039558, 0.098498, 1.122994, 0.015707, -0.132669, 1.01871]},
  {'feature': [22, 2, 2, -2, -2, -2, 20, 21, -2, -2, 20, -2, -2], 'threshold': [0.522774, 18.5, 13.5, -2.0, -2.0, -2.0, 0.508336, 0.49168, -2.0, -2.0, 0.510421, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.000878, -0.006966, -0.006343, -0.054575, 0.119552, -1.226512, 0.015208, 0.088738, 1.015109, 0.277689, 0.012849, -0.878295, 0.32068]},
  {'feature': [3, 21, 13, -2, -2, 4, -2, -2, 9, 9, -2, -2, 17, -2, -2], 'threshold': [3.5, 0.493987, 0.5, -2.0, -2.0, 35.5, -2.0, -2.0, 25.5, 23.5, -2.0, -2.0, 40.677435, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001591, 0.023978, 0.109015, 1.150939, 0.375417, 0.016782, 0.123664, -0.986852, -0.004086, -0.0263, -0.09007, -0.475512, 0.006989, 0.2731, -0.003576]},
  {'feature': [21, 19, 7, -2, -2, 12, -2, -2, 20, 7, -2, -2, 20, -2, -2], 'threshold': [0.539428, 24.5, 542.5, -2.0, -2.0, 900.5, -2.0, -2.0, 0.552435, 72.0, -2.0, -2.0, 0.559423, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000453, -0.004746, -0.007178, -0.026275, -0.405843, 0.056687, 0.848104, -0.24631, 0.017617, 0.033676, -0.324287, 0.699591, 0.014138, -1.740337, 0.965246]},
  {'feature': [17, 5, 17, -2, -2, 2, -2, -2, 17, 6, -2, -2, 4, -2, -2], 'threshold': [43.2209, 6.5, 37.59968, -2.0, -2.0, 13.5, -2.0, -2.0, 43.237932, 327.0, -2.0, -2.0, 4.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001562, -0.009191, 0.107653, 0.926134, -0.236624, -0.011126, -0.109999, 0.244391, 0.011661, 0.365282, 1.753411, 1.314752, 0.006109, -0.111915, 0.118609]},
  {'feature': [21, 4, 17, -2, -2, 19, -2, -2, 20, 6, -2, -2, 22, -2, -2], 'threshold': [0.573673, 3.5, 46.370121, -2.0, -2.0, 24.5, -2.0, -2.0, 0.515388, 86.5, -2.0, -2.0, 0.57634, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00232, -0.007094, -0.033643, -0.34888, 0.132818, -0.002328, -0.022008, 0.670605, 0.017754, 0.063822, 1.120424, 0.678235, 0.015357, 1.03034, 1.014726]},
  {'feature': [16, 16, 16, -2, -2, 16, -2, -2, 10, 3, -2, -2, 9, -2, -2], 'threshold': [36.17256, 34.978691, 32.705603, -2.0, -2.0, 35.071678, -2.0, -2.0, 17.5, 10.5, -2.0, -2.0, 25.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000622, -0.063327, -0.027266, -0.437045, 0.284059, -0.139105, -1.435196, -0.353486, 0.00297, 0.024515, 0.170166, 1.710102, -0.006452, -0.237288, 0.012089]},
  {'feature': [11, 1, 9, -2, -2, 4, -2, -2, 1, 10, -2, -2, 16, -2, -2], 'threshold': [598.5, 497.5, 27.5, -2.0, -2.0, 7.5, -2.0, -2.0, 480.0, 36.5, -2.0, -2.0, 41.310343, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-7.8e-05, -0.008745, 0.006751, 0.149396, -0.283875, -0.023883, -0.682873, -0.002638, 0.012236, -0.007446, 0.418091, -0.581879, 0.032749, -0.834821, 0.502171]},
  {'feature': [4, 9, 1, -2, -2, 16, -2, -2, 0, 17, -2, -2, -2], 'threshold': [22.5, 25.5, 497.5, -2.0, -2.0, 46.72073, -2.0, -2.0, 62.5, 32.701172, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [0.001604, -0.001803, -0.022332, 0.009628, -0.291476, 0.008589, 0.091923, -0.330236, 0.028718, 0.021247, -0.359477, 0.165844, 1.6098]},
  {'feature': [14, 9, 20, -2, -2, 15, -2, -2, 10, 3, -2, -2, 6, -2, -2], 'threshold': [-188.5, 36.5, 0.461032, -2.0, -2.0, -7.0, -2.0, -2.0, 57.5, 13.5, -2.0, -2.0, 510.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001121, -0.027352, -0.023267, -0.919025, 0.732043, -0.067251, -1.056804, -1.047083, 0.004153, 0.004877, 0.002146, 0.192607, -0.161058, -1.238816, -1.190385]},
  {'feature': [16, 16, 16, -2, -2, 1, -2, -2, 16, 10, -2, -2, 1, -2, -2], 'threshold': [48.88658, 48.576111, 48.572851, -2.0, -2.0, 492.5, -2.0, -2.0, 48.961807, 6.0, -2.0, -2.0, 397.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000969, 0.002161, 0.00044, 0.00795, -1.619019, 0.132024, -0.168778, 1.443954, -0.028832, -0.23029, -0.269422, -1.660495, -0.019239, -1.182171, -0.023042]},
  {'feature': [16, 17, 17, -2, -2, 17, -2, -2, 16, 10, -2, -2, 4, -2, -2], 'threshold': [49.370871, 43.23653, 40.679914, -2.0, -2.0, 43.237932, -2.0, -2.0, 50.096201, 3.5, -2.0, -2.0, 31.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001395, 0.001514, -0.009774, 0.04375, -0.182141, 0.013632, 1.702597, 0.048003, -0.034981, -0.128112, 0.898788, -1.016114, -0.004187, 0.076897, -0.64504]},
  {'feature': [16, 16, 3, -2, -2, 4, -2, -2, 1, 9, -2, -2, 16, -2, -2], 'threshold': [46.736553, 46.717155, 8.5, -2.0, -2.0, 2.0, -2.0, -2.0, 362.5, 22.5, -2.0, -2.0, 46.775076, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000356, 0.003628, 0.001684, 0.098845, -0.049082, 0.409774, 1.818501, 1.595062, -0.019556, -0.123744, -0.119684, -1.35109, -0.003626, -1.62203, -0.001796]},
  {'feature': [7, 1, 2, -2, -2, 3, -2, -2, 1, 10, -2, -2, 16, -2, -2], 'threshold': [299.5, 432.5, 6.5, -2.0, -2.0, 6.5, -2.0, -2.0, 447.5, 36.5, -2.0, -2.0, 41.357901, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001363, -0.009843, 0.015211, -0.798823, 0.30923, -0.018544, 0.02049, -0.279567, 0.009968, -0.011852, 0.269647, -0.605811, 0.031707, -0.685061, 0.420742]},
  {'feature': [19, 8, 1, -2, -2, 1, -2, -2, 14, 12, -2, -2, 22, -2, -2], 'threshold': [24.5, 326.5, 482.5, -2.0, -2.0, 447.5, -2.0, -2.0, -346.5, 1129.0, -2.0, -2.0, 0.472953, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000823, -0.001094, 0.005306, 0.135935, -0.041822, -0.015029, -0.289003, 0.086158, 0.043981, -0.045925, -1.136722, -0.850009, 0.069574, 1.256677, 0.441964]},
  {'feature': [14, 19, 14, -2, -2, 14, -2, -2, 22, 19, -2, -2, 10, -2, -2], 'threshold': [-94.5, 24.5, -148.0, -2.0, -2.0, -351.5, -2.0, -2.0, 0.392081, 10.5, -2.0, -2.0, 57.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001047, -0.02574, -0.031509, -0.724888, -0.672049, 0.012604, -0.947993, 0.721455, 0.005002, 0.145713, 0.26707, 1.911251, 0.003968, 0.027446, -1.2342]},
  {'feature': [10, 3, 12, -2, -2, 1, -2, -2, 2, 1, -2, -2, 4, -2, -2], 'threshold': [43.5, 12.5, 695.5, -2.0, -2.0, 222.5, -2.0, -2.0, 16.5, 337.5, -2.0, -2.0, 1.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000718, 0.003595, -0.001019, 0.015051, -0.243491, 0.026917, -0.754095, 0.253101, -0.023935, -0.013638, -1.328393, 0.007724, -0.117252, 0.161812, -1.011802]},
  {'feature': [5, 6, 16, -2, -2, 17, -2, -2, 10, 3, -2, -2, 17, -2, -2], 'threshold': [318.5, 238.5, 36.294394, -2.0, -2.0, 49.486174, -2.0, -2.0, 45.5, 12.5, -2.0, -2.0, 44.297834, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001554, -0.008059, 0.001559, -0.17036, 0.03359, -0.024219, -0.142395, -1.193426, 0.012466, 0.017439, 0.085922, 0.268463, -0.03755, -0.491217, 0.317162]},
  {'feature': [17, 17, 1, -2, -2, 1, -2, -2, 17, 17, -2, -2, 14, -2, -2], 'threshold': [43.229509, 40.974117, 382.5, -2.0, -2.0, 267.5, -2.0, -2.0, 43.237932, 43.237518, -2.0, -2.0, -31.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00147, -0.007415, 0.00886, 0.419349, -0.040722, -0.030902, -0.999936, -0.107073, 0.009757, 0.358587, 1.557865, 1.743066, 0.004635, -0.316476, 0.059644]},
  {'feature': [16, 16, 16, -2, -2, 16, -2, -2, 10, 3, -2, -2, 9, -2, -2], 'threshold': [36.152514, 34.978691, 32.705603, -2.0, -2.0, 35.013941, -2.0, -2.0, 16.5, 9.5, -2.0, -2.0, 26.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000528, -0.039244, -0.001379, -0.208626, 0.303261, -0.121552, -1.437937, -0.248995, 0.002817, 0.018994, 0.125802, 1.74861, -0.003819, -0.175041, 0.039511]},
  {'feature': [16, 21, 4, -2, -2, 17, -2, -2, 16, 16, -2, -2, 16, -2, -2], 'threshold': [29.522548, 0.478778, 7.5, -2.0, -2.0, 26.519533, -2.0, -2.0, 32.343418, 31.974328, -2.0, -2.0, 33.230515, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00215, 0.089351, -0.045045, -1.016135, -1.917771, 0.153749, 0.105712, 1.017683, -0.003208, -0.161201, -0.507397, -1.737819, -0.001557, 0.826866, -0.01459]},
  {'feature': [21, 17, 6, -2, -2, 17, -2, -2, 20, 5, -2, -2, 22, -2, -2], 'threshold': [0.573673, 34.969, 37.5, -2.0, -2.0, 35.051546, -2.0, -2.0, 0.51564, 65.5, -2.0, -2.0, 0.573593, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00237, -0.006828, 0.041785, -0.034696, 0.821171, -0.00892, -1.293739, -0.03915, 0.016609, 0.062913, 1.119235, 0.769922, 0.014, 1.028339, 1.013487]},
  {'feature': [10, 16, 3, -2, -2, 0, -2, -2, 0, 16, -2, -2, 21, -2, -2], 'threshold': [43.5, 44.484043, 13.5, -2.0, -2.0, 357.5, -2.0, -2.0, 162.5, 43.368196, -2.0, -2.0, 0.476094, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001499, 0.004224, 0.011481, 0.031866, 0.326688, -0.008853, -0.073607, 0.758215, -0.022294, -0.008423, -0.420637, 0.163431, -0.072784, -1.067329, -1.370471]},
  {'feature': [11, 3, 10, -2, -2, 10, -2, -2, 1, 10, -2, -2, 10, -2, -2], 'threshold': [595.5, 8.5, 30.5, -2.0, -2.0, 17.5, -2.0, -2.0, 457.5, 36.5, -2.0, -2.0, 36.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001185, -0.008842, 0.001598, -0.014954, 1.423213, -0.022401, 1.122181, -0.184507, 0.009524, -0.011032, 0.35487, -0.564377, 0.030335, -0.136168, 0.577989]},
  {'feature': [9, 9, 21, -2, -2, 22, -2, -2, 17, 17, -2, -2, 1, -2, -2], 'threshold': [25.5, 23.5, 0.500639, -2.0, -2.0, 0.474937, -2.0, -2.0, 40.5476, 40.536459, -2.0, -2.0, 452.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002046, -0.013392, -0.004034, -0.066403, 0.370558, -0.082996, 0.7153, -0.668481, 0.005829, 0.039439, 0.238465, 1.666715, -0.002344, -0.204442, 0.149232]},
  {'feature': [16, 16, 16, -2, -2, 0, -2, -2, 16, 3, -2, -2, 17, -2, -2], 'threshold': [48.88658, 48.576111, 48.572851, -2.0, -2.0, 7.5, -2.0, -2.0, 48.961807, 2.5, -2.0, -2.0, 51.952978, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001519, 0.004448, 0.002978, 0.023769, -1.533304, 0.117042, 1.266159, -0.120133, -0.024726, -0.22001, -0.285276, -1.496007, -0.014509, -0.218958, 0.17068]},
  {'feature': [16, 17, 12, -2, -2, 17, -2, -2, 16, -2, 16, -2, -2], 'threshold': [36.37739, 29.715061, 36.0, -2.0, -2.0, 30.974954, -2.0, -2.0, 36.522854, -2.0, 47.507231, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.001713, -0.044912, 0.062567, -0.002493, 1.592765, -0.064895, -1.176222, -0.29496, 0.000898, 1.084041, 0.000376, 0.027689, -0.121493]},
  {'feature': [22, 19, 4, -2, -2, 11, -2, -2, 11, -2, 21, -2, -2], 'threshold': [0.591751, 27.5, 5.5, -2.0, -2.0, 523.5, -2.0, -2.0, 31.5, -2.0, 0.511963, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.001673, -0.005709, -0.007412, -0.160791, -0.001564, 0.058954, -0.612595, 0.851281, 0.016186, -1.179825, 0.01825, 0.88054, 0.919335]},
  {'feature': [9, 9, 0, -2, -2, 16, -2, -2, 17, 17, -2, -2, 1, -2, -2], 'threshold': [25.5, 23.5, 37.5, -2.0, -2.0, 39.897856, -2.0, -2.0, 40.549723, 40.521784, -2.0, -2.0, 442.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00027, -0.010997, -0.003846, -0.094282, 0.257582, -0.06599, -1.013729, -0.086803, 0.007101, 0.034134, 0.182458, 1.618576, 0.000442, -0.180055, 0.142575]},
  {'feature': [1, 16, 16, -2, -2, 10, -2, -2, 16, 1, -2, -2, 4, -2, -2], 'threshold': [272.5, 40.545343, 40.396441, -2.0, -2.0, 27.5, -2.0, -2.0, 41.355526, 497.5, -2.0, -2.0, 6.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002952, -0.02386, 0.071603, -0.122646, 1.720911, -0.057751, 0.7099, -0.756495, 0.005786, -0.013073, 0.216403, -0.327016, 0.013375, -0.06157, 0.185693]},
  {'feature': [22, 17, 4, -2, -2, 17, -2, -2, 11, 6, -2, -2, 21, -2, -2], 'threshold': [0.579796, 26.590008, 28.0, -2.0, -2.0, 29.043256, -2.0, -2.0, 282.5, 5.5, -2.0, -2.0, 0.491655, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000153, -0.003552, -0.157753, 0.016375, -1.306806, -0.002902, 1.254928, -0.022054, 0.015533, 0.051394, -1.102329, 0.847314, 0.011105, -0.585443, 0.863128]},
  {'feature': [16, 16, 16, -2, -2, 0, -2, -2, 16, -2, 4, -2, -2], 'threshold': [49.370871, 49.151499, 49.088112, -2.0, -2.0, 27.5, -2.0, -2.0, 49.386204, -2.0, 31.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.002282, 0.000438, -0.000658, 0.00155, -1.287733, 0.154189, 1.191895, -0.515446, -0.034035, -1.627232, -0.026319, -0.080482, -0.678651]},
  {'feature': [6, 19, 4, -2, -2, 22, -2, -2, 17, 17, -2, -2, 17, -2, -2], 'threshold': [247.5, 15.5, 35.5, -2.0, -2.0, 0.452273, -2.0, -2.0, 49.363094, 46.160089, -2.0, -2.0, 49.59845, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001579, 0.005724, 0.001691, 0.015316, -0.915639, 0.037273, 1.278324, 0.244889, -0.01195, -0.009544, -0.101173, 0.22547, -0.112437, -1.588216, -0.406461]},
  {'feature': [17, 17, 1, -2, -2, -2, 17, 17, -2, -2, 0, -2, -2], 'threshold': [43.195929, 43.185223, 437.5, -2.0, -2.0, -2.0, 43.259701, 43.236618, -2.0, -2.0, 92.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.000411, -0.0101, -0.008752, 0.095898, -0.130239, -2.020687, 0.010005, 0.168442, 0.014625, 1.486447, 0.005617, 0.082876, -0.109227]},
]

def _gbc_v2_predict(feat_vec):
    """feat_vec: list of floats in GBC_V2_COLS order. Returns P(win)."""
    score = GBC_V2_INIT
    for tree in GBC_V2_TREES:
        node = 0
        feat  = tree['feature']
        thr   = tree['threshold']
        left  = tree['left']
        right = tree['right']
        val   = tree['value']
        while feat[node] != -2:  # -2 == leaf sentinel
            if feat_vec[feat[node]] <= thr[node]:
                node = left[node]
            else:
                node = right[node]
        score += GBC_V2_LR * val[node]
    return 1.0 / (1.0 + math.exp(-score))

_GBC_CENTER = 50.0

# ── GBC value function 4P ─────────────────────────────────────────────────
GBC_4P_INIT = 0.0
GBC_4P_LR   = 0.05
GBC_4P_N    = 150
GBC_4P_COLS = ['step', 'remaining', 'my_planets', 'en_planets', 'neutrals', 'my_ships_planet', 'en_ships_planet', 'my_ships_transit', 'en_ships_transit', 'my_prod', 'en_prod', 'my_total', 'en_total', 'planet_diff', 'ship_diff', 'prod_diff', 'my_centrality', 'en_centrality', 'my_fleets', 'en_fleets', 'prod_ratio', 'ship_ratio', 'planet_ratio']
GBC_4P_TREES = [
  {'feature': [21, 21, 3, -2, -2, 15, -2, -2, 14, 12, -2, -2, 3, -2, -2], 'threshold': [0.350151, 0.222813, 10.5, -2.0, -2.0, -36.5, -2.0, -2.0, -79.5, 1001.0, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.005412, -0.12443, -0.221371, -0.059132, -1.290007, -0.010988, -0.847696, 0.048352, 0.542412, 0.280647, 1.974112, -0.966, 0.717448, 4.193429, 2.567346]},
  {'feature': [21, 21, 3, -2, -2, 0, -2, -2, 3, 14, -2, -2, 9, -2, -2], 'threshold': [0.46062, 0.229946, 10.5, -2.0, -2.0, 107.5, -2.0, -2.0, 12.5, -8.5, -2.0, -2.0, 31.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000215, -0.08926, -0.207417, 0.000201, -1.270994, 0.039983, 0.128576, 3.217319, 0.680644, 0.722851, 3.648986, 3.605111, 0.538068, 1.498534, 3.721686]},
  {'feature': [21, 21, 13, -2, -2, 12, -2, -2, 14, 0, -2, -2, 3, -2, -2], 'threshold': [0.365535, 0.229946, -7.5, -2.0, -2.0, 1138.0, -2.0, -2.0, -66.5, 62.5, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.003195, -0.109368, -0.195381, -1.256692, -0.013811, 0.00134, 0.107401, -0.946247, 0.511277, 0.261482, 1.006954, 3.582659, 0.650458, 3.181491, 1.804263]},
  {'feature': [21, 21, 13, -2, -2, 17, -2, -2, 14, 1, -2, -2, 3, -2, -2], 'threshold': [0.366053, 0.229946, -7.5, -2.0, -2.0, 46.514002, -2.0, -2.0, -66.5, 435.0, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000684, -0.100912, -0.189567, -1.248497, -0.265099, 0.014594, -0.118093, 0.649526, 0.481687, 0.245446, 3.143486, 0.91978, 0.619787, 2.860857, 1.815418]},
  {'feature': [21, 21, 6, -2, -2, 21, -2, -2, 3, 14, -2, -2, 9, -2, -2], 'threshold': [0.455848, 0.229961, 196.5, -2.0, -2.0, 0.335968, -2.0, -2.0, 13.5, -22.5, -2.0, -2.0, 29.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.004459, -0.081182, -0.177717, -0.001694, -1.201375, 0.022947, -0.089888, 0.94486, 0.587775, 0.612295, 2.412427, 2.609902, 0.437712, 0.878337, 3.014493]},
  {'feature': [21, 21, 15, -2, -2, 0, -2, -2, 14, 12, -2, -2, 3, -2, -2], 'threshold': [0.350151, 0.229883, -8.5, -2.0, -2.0, 97.5, -2.0, -2.0, -65.5, 1000.5, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002397, -0.091702, -0.168308, -1.139825, 0.838684, 0.006693, -0.008502, 1.777935, 0.424347, 0.20217, 1.300303, -1.002932, 0.567728, 2.422357, 1.861809]},
  {'feature': [21, 14, 13, -2, -2, 17, -2, -2, 14, 17, -2, -2, 21, -2, -2], 'threshold': [0.365535, -510.5, -12.5, -2.0, -2.0, 42.748489, -2.0, -2.0, -116.5, 44.980825, -2.0, -2.0, 0.542011, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.004277, -0.085447, -0.154773, -1.20821, -0.552263, 0.012655, -0.362448, 0.448398, 0.426508, 0.209684, 0.519437, 2.375082, 0.528474, 1.872872, 2.271191]},
  {'feature': [21, 22, 12, -2, -2, 17, -2, -2, 14, 12, -2, -2, 3, -2, -2], 'threshold': [0.350151, 0.220486, 100.5, -2.0, -2.0, 46.562786, -2.0, -2.0, -55.0, 1001.0, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.003388, -0.086892, -0.165936, 0.328878, -1.179411, -0.016159, -0.28851, 0.499297, 0.37349, 0.184311, 1.138067, -0.995319, 0.504155, 2.12185, 1.336325]},
  {'feature': [21, 13, 21, -2, -2, 17, -2, -2, 14, 17, -2, -2, 21, -2, -2], 'threshold': [0.335968, -10.5, 0.262442, -2.0, -2.0, 46.613808, -2.0, -2.0, -116.5, 47.528074, -2.0, -2.0, 0.54185, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00043, -0.084427, -0.148003, -1.145056, -0.236648, -0.002919, -0.197783, 0.384354, 0.341598, 0.168358, 0.586186, 2.977843, 0.464511, 1.504844, 2.025451]},
  {'feature': [21, 21, 12, -2, -2, 1, -2, -2, 14, 17, -2, -2, 3, -2, -2], 'threshold': [0.334067, 0.214231, 149.5, -2.0, -2.0, 397.5, -2.0, -2.0, -66.5, 46.702068, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00157, -0.088098, -0.146932, 0.675065, -1.1519, -0.019993, 1.436402, -0.14641, 0.323207, 0.167577, 0.519859, 2.385234, 0.453849, 1.917299, 1.069991]},
  {'feature': [21, 21, 13, -2, -2, 17, -2, -2, 14, 12, -2, -2, 3, -2, -2], 'threshold': [0.335968, 0.197667, -8.5, -2.0, -2.0, 46.797478, -2.0, -2.0, -66.5, 1001.0, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000601, -0.077875, -0.141645, -1.172555, -0.292289, -0.015221, -0.231522, 0.325363, 0.314049, 0.150819, 1.030964, -0.995775, 0.436237, 1.844252, 1.1068]},
  {'feature': [21, 21, 13, -2, -2, 0, -2, -2, 14, 0, -2, -2, 3, -2, -2], 'threshold': [0.342218, 0.23897, -8.5, -2.0, -2.0, 97.5, -2.0, -2.0, -66.5, 85.0, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.003352, -0.075367, -0.124912, -1.127926, -0.211864, 0.003508, -0.02359, 1.855162, 0.308716, 0.166925, 0.524219, 2.465228, 0.412527, 1.75675, 1.078802]},
  {'feature': [21, 13, 18, -2, -2, 17, -2, -2, 14, 12, -2, -2, 3, -2, -2], 'threshold': [0.335968, -10.5, 4.5, -2.0, -2.0, 46.613808, -2.0, -2.0, -66.5, 1001.0, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001229, -0.068159, -0.122738, -1.062757, -0.099036, 0.002977, -0.191827, 0.509657, 0.278666, 0.142015, 0.93408, -0.811718, 0.390873, 1.71057, 0.843246]},
  {'feature': [21, 13, 18, -2, -2, 17, -2, -2, 14, 11, -2, -2, 6, -2, -2], 'threshold': [0.334067, -10.5, 4.5, -2.0, -2.0, 46.613808, -2.0, -2.0, -118.0, 663.5, -2.0, -2.0, 557.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001641, -0.066108, -0.11898, -1.063758, -0.091724, 0.002941, -0.180635, 0.458429, 0.266635, 0.129395, 0.866627, -0.788464, 0.363185, 1.575616, 0.617102]},
  {'feature': [21, 14, 22, -2, -2, 17, -2, -2, 21, 1, -2, -2, 3, -2, -2], 'threshold': [0.365535, -511.5, 0.262014, -2.0, -2.0, 42.814159, -2.0, -2.0, 0.531974, 437.5, -2.0, -2.0, 12.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001887, -0.059288, -0.110674, -1.051985, -0.320636, 0.012027, -0.308246, 0.381412, 0.284674, 0.184732, 1.978057, 0.574061, 0.375765, 1.585098, 1.738087]},
  {'feature': [21, 13, 18, -2, -2, 4, -2, -2, 14, 17, -2, -2, 3, -2, -2], 'threshold': [0.334845, -10.5, 4.5, -2.0, -2.0, 12.5, -2.0, -2.0, -66.5, 46.147991, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.004686, -0.065729, -0.109278, -1.046957, -0.191656, -0.008877, 0.221361, -0.242419, 0.239388, 0.12657, 0.312847, 1.713078, 0.333237, 1.547743, 0.670421]},
  {'feature': [21, 21, 14, -2, -2, 1, -2, -2, 3, 13, -2, -2, 10, -2, -2], 'threshold': [0.457998, 0.229946, -66.0, -2.0, -2.0, 392.5, -2.0, -2.0, 13.5, -1.5, -2.0, -2.0, 34.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.003949, -0.044836, -0.102665, -0.999626, 0.84267, 0.017415, 2.07548, 0.039756, 0.306722, 0.333485, 1.716756, 1.471007, 0.127921, -0.81656, 1.594717]},
  {'feature': [21, 21, 13, -2, -2, 20, -2, -2, 12, 14, -2, -2, 8, -2, -2], 'threshold': [0.320374, 0.229898, -8.5, -2.0, -2.0, 0.299123, -2.0, -2.0, 1055.5, -67.0, -2.0, -2.0, 536.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001059, -0.057046, -0.099431, -1.107946, -0.217226, 0.005492, -0.066254, 0.580395, 0.207022, 0.234375, 0.665892, 1.375241, -0.190216, -1.311507, -0.756626]},
  {'feature': [21, 22, 12, -2, -2, 12, -2, -2, 12, 16, -2, -2, 12, -2, -2], 'threshold': [0.324272, 0.246212, 270.5, -2.0, -2.0, 1221.0, -2.0, -2.0, 832.5, 38.415493, -2.0, -2.0, 1067.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002088, -0.054116, -0.095549, 0.132662, -0.994008, 0.003704, 0.091615, -1.032178, 0.198615, 0.252281, 0.241611, 1.239201, 0.033855, 0.437052, -0.864452]},
  {'feature': [21, 21, 13, -2, -2, 15, -2, -2, 12, 21, -2, -2, 9, -2, -2], 'threshold': [0.344016, 0.229946, -6.5, -2.0, -2.0, -36.5, -2.0, -2.0, 1002.5, 0.54185, -2.0, -2.0, 33.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-3.9e-05, -0.050625, -0.090183, -1.053743, 0.004636, 0.003512, -0.726101, 0.107993, 0.215057, 0.240902, 0.769758, 1.425851, -0.114323, -1.054353, -0.179066]},
  {'feature': [21, 13, 15, -2, -2, 17, -2, -2, 12, 21, -2, -2, -2], 'threshold': [0.334067, -10.5, -22.0, -2.0, -2.0, 46.797478, -2.0, -2.0, 1064.5, 0.54185, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001501, -0.050749, -0.088442, -0.966477, 0.663439, -0.001486, -0.176547, 0.370104, 0.194229, 0.215769, 0.695448, 1.395983, -0.810361]},
  {'feature': [21, 22, 17, -2, -2, 8, -2, -2, 12, 4, -2, -2, 3, -2, -2], 'threshold': [0.350151, 0.220486, 47.549627, -2.0, -2.0, 565.0, -2.0, -2.0, 876.5, 8.5, -2.0, -2.0, 12.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00163, -0.044757, -0.08963, -1.062188, 0.536382, -0.004773, 0.045139, -1.014425, 0.190095, 0.225018, 1.256932, 0.626829, 0.01325, 1.050521, -0.223626]},
  {'feature': [21, 20, 17, -2, -2, 12, -2, -2, 12, 0, -2, -2, 9, -2, -2], 'threshold': [0.335968, 0.220464, 47.36944, -2.0, -2.0, 1223.5, -2.0, -2.0, 1002.5, 65.0, -2.0, -2.0, 34.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000524, -0.04407, -0.08405, -1.032452, 0.625291, -0.004472, 0.044195, -1.041825, 0.176792, 0.204068, 0.849561, 1.606019, -0.116948, -1.098835, -0.032268]},
  {'feature': [21, 14, 21, -2, -2, 0, -2, -2, 6, 10, -2, -2, -2], 'threshold': [0.457998, -518.5, 0.285236, -2.0, -2.0, 87.5, -2.0, -2.0, 557.5, 33.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.000594, -0.030083, -0.073742, -0.905862, 0.097513, 0.020822, 0.051493, 1.485376, 0.230702, 0.241907, 1.193895, 1.427469, 0.384458]},
  {'feature': [21, 22, 18, -2, -2, 8, -2, -2, 12, 16, -2, -2, 17, -2, -2], 'threshold': [0.335583, 0.220486, 4.5, -2.0, -2.0, 565.0, -2.0, -2.0, 695.0, 38.945755, -2.0, -2.0, 46.55286, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000654, -0.039833, -0.078491, -1.043728, 0.378272, -0.003075, 0.047424, -0.958572, 0.161848, 0.216088, 0.358464, 1.186992, 0.062535, 0.126314, 1.481433]},
  {'feature': [21, 13, 20, -2, -2, 17, -2, -2, 17, 0, -2, -2, 14, -2, -2], 'threshold': [0.301007, -9.5, 0.298936, -2.0, -2.0, 53.653385, -2.0, -2.0, 46.662474, 62.5, -2.0, -2.0, -125.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000382, -0.043459, -0.067944, -0.868533, 1.008633, 0.00105, 0.082544, -0.815327, 0.137022, 0.100966, 0.32258, 1.668304, 0.292415, 1.843925, 1.259136]},
  {'feature': [21, 21, 12, -2, -2, 0, -2, -2, 9, 3, -2, -2, 10, -2, -2], 'threshold': [0.457998, 0.228265, 99.5, -2.0, -2.0, 107.5, -2.0, -2.0, 29.5, 12.5, -2.0, -2.0, 33.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002269, -0.028608, -0.068259, 0.676327, -0.946432, 0.014375, 0.027608, 1.743704, 0.204311, 0.13878, 1.304325, -0.575682, 0.232663, 1.249835, 1.4076]},
  {'feature': [21, 21, 6, -2, -2, 0, -2, -2, 14, 17, -2, -2, 3, -2, -2], 'threshold': [0.301007, 0.226621, 191.0, -2.0, -2.0, 2.5, -2.0, -2.0, -48.5, 47.528074, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000171, -0.04057, -0.063884, 0.245325, -0.992516, -0.006436, 0.145351, -0.636001, 0.122711, 0.061545, 0.137017, 1.895511, 0.198101, 1.282499, 0.318538]},
  {'feature': [21, 20, 17, -2, -2, 1, -2, -2, 12, 1, -2, -2, 8, -2, -2], 'threshold': [0.301007, 0.220294, 47.866915, -2.0, -2.0, 497.5, -2.0, -2.0, 1104.5, 432.5, -2.0, -2.0, 561.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002626, -0.035177, -0.066718, -1.034828, 0.870455, -0.001547, -0.557617, 0.154093, 0.118611, 0.136299, 1.619586, 0.572453, -0.163607, -1.255064, -0.713333]},
  {'feature': [21, 14, 21, -2, -2, 0, -2, -2, 9, 12, -2, -2, 21, -2, -2], 'threshold': [0.451929, -511.5, 0.314317, -2.0, -2.0, 87.5, -2.0, -2.0, 32.5, 651.0, -2.0, -2.0, 0.528988, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000516, -0.023158, -0.056753, -0.714849, -1.244559, 0.017962, 0.027684, 1.490961, 0.169929, 0.099553, 1.110107, -1.1534, 0.210448, 1.495835, 1.251466]},
  {'feature': [21, 20, 14, -2, -2, 11, -2, -2, 6, 10, -2, -2, -2], 'threshold': [0.455848, 0.24218, -281.5, -2.0, -2.0, 680.5, -2.0, -2.0, 526.0, 34.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [0.001072, -0.020964, -0.056008, -0.973484, 0.218371, 0.015906, 0.135337, -1.405206, 0.17559, 0.18573, 1.14732, 1.226078, 0.313727]},
  {'feature': [21, 17, 22, -2, -2, 21, -2, -2, 9, 3, -2, -2, 21, -2, -2], 'threshold': [0.461554, 46.781157, 0.440972, -2.0, -2.0, 0.29288, -2.0, -2.0, 29.5, 12.5, -2.0, -2.0, 0.531726, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.003786, -0.023955, -0.037637, -0.299547, -1.079301, 0.056771, 0.050159, 1.608121, 0.161817, 0.095909, 1.226491, -0.821182, 0.188455, 1.370634, 1.192248]},
  {'feature': [21, 21, 17, -2, -2, 1, -2, -2, 3, 21, -2, -2, -2], 'threshold': [0.483876, 0.241881, 46.817076, -2.0, -2.0, 412.5, -2.0, -2.0, 13.5, 0.535659, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.003584, -0.022802, -0.051422, -0.825502, 0.179614, 0.015357, 1.250423, 0.017451, 0.156877, 0.169182, 1.26478, 1.196944, 0.214482]},
  {'feature': [21, 14, 11, -2, -2, 4, -2, -2, 12, 5, -2, -2, 11, -2, -2], 'threshold': [0.300928, -716.0, 453.0, -2.0, -2.0, 13.5, -2.0, -2.0, 1090.0, 133.5, -2.0, -2.0, 695.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002221, -0.028402, -0.057659, -0.964969, -1.197517, -0.00029, 0.233071, -0.199664, 0.098848, 0.115584, -0.486119, 0.770179, -0.156194, -1.225994, -0.873543]},
  {'feature': [21, 21, 10, -2, -2, 0, -2, -2, 20, -2, 10, -2, -2], 'threshold': [0.460753, 0.222859, 15.5, -2.0, -2.0, 107.5, -2.0, -2.0, 0.449138, -2.0, 31.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.000656, -0.018911, -0.051423, 0.777327, -0.94224, 0.012667, 0.029132, 1.35565, 0.140259, 0.130955, 0.153361, 1.049045, 1.270104]},
  {'feature': [21, 21, 12, -2, -2, 4, -2, -2, 17, 14, -2, -2, 14, -2, -2], 'threshold': [0.350151, 0.229961, 98.0, -2.0, -2.0, 3.5, -2.0, -2.0, 43.925795, -114.0, -2.0, -2.0, -167.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000979, -0.021367, -0.047266, 0.682015, -0.851493, 0.012686, -0.941074, 0.131579, 0.102493, 0.050875, -0.414316, 0.916434, 0.161626, 1.271591, 0.811523]},
  {'feature': [21, 22, 21, -2, -2, 4, -2, -2, 12, 10, -2, -2, 10, -2, -2], 'threshold': [0.401391, 0.220486, 0.283485, -2.0, -2.0, 3.5, -2.0, -2.0, 815.0, 40.5, -2.0, -2.0, 36.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000416, -0.019079, -0.05203, -0.949416, -1.312513, 0.008558, -0.90451, 0.122514, 0.113785, 0.137672, 0.877501, 1.300148, -0.03306, -1.227494, 0.828422]},
  {'feature': [21, 20, 14, -2, -2, 13, -2, -2, 17, 1, -2, -2, 14, -2, -2], 'threshold': [0.301007, 0.299123, -366.5, -2.0, -2.0, -4.5, -2.0, -2.0, 47.529268, 437.5, -2.0, -2.0, -72.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001261, -0.024045, -0.030939, -0.70799, 0.039044, 0.068591, 0.806766, -0.643357, 0.080548, 0.058234, 1.366546, 0.175553, 0.217834, 1.709736, 1.042538]},
  {'feature': [21, 21, 16, -2, -2, 21, -2, -2, 9, 12, -2, -2, 3, -2, -2], 'threshold': [0.451929, 0.24443, 55.389942, -2.0, -2.0, 0.247731, -2.0, -2.0, 31.5, 651.0, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002312, -0.013444, -0.038337, -0.607922, 1.110105, 0.022689, 1.414218, 0.069721, 0.117674, 0.06378, 0.948103, -0.873726, 0.147192, 1.154565, 1.311995]},
  {'feature': [20, 17, 4, -2, -2, 9, -2, -2, 17, 14, -2, -2, 3, -2, -2], 'threshold': [0.272233, 36.046062, 24.5, -2.0, -2.0, 15.5, -2.0, -2.0, 47.552628, -66.5, -2.0, -2.0, 10.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001796, -0.028942, 0.081612, 1.072745, -0.474734, -0.033377, -0.483338, 0.181804, 0.059567, 0.036039, -0.026171, 0.879615, 0.191589, 0.64644, 1.980289]},
  {'feature': [14, 17, 14, -2, -2, -2, 4, 9, -2, -2, 16, -2, -2], 'threshold': [-383.5, 47.999815, -405.5, -2.0, -2.0, -2.0, 8.5, 7.5, -2.0, -2.0, 41.241432, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.001144, -0.03352, -0.036466, -0.467576, -0.985469, 0.962597, 0.047078, 0.115084, 2.069548, 0.628443, 0.009884, -0.341162, 0.302625]},
  {'feature': [21, 17, 17, -2, -2, 21, -2, -2, 3, 1, -2, -2, -2], 'threshold': [0.54185, 46.781157, 37.285473, -2.0, -2.0, 0.29288, -2.0, -2.0, 12.5, 422.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001986, -0.014188, -0.025185, 0.524643, -0.323978, 0.051794, 0.074885, 1.16795, 0.123042, 0.118643, 1.113849, 1.138372, 1.210341]},
  {'feature': [21, 17, 20, -2, -2, 20, -2, -2, 1, 9, -2, -2, 14, -2, -2], 'threshold': [0.229946, 38.573072, 0.23235, -2.0, -2.0, 0.262829, -2.0, -2.0, 402.5, 18.5, -2.0, -2.0, 91.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001885, -0.038401, 0.012475, -0.872451, 2.153137, -0.042329, -0.848954, -0.761302, 0.035989, 0.183028, 1.430693, 0.967529, 0.02649, 0.057769, 1.145516]},
  {'feature': [21, 11, 21, -2, -2, 16, -2, -2, 3, 21, -2, -2, 10, -2, -2], 'threshold': [0.45565, 663.5, 0.197667, -2.0, -2.0, 44.959333, -2.0, -2.0, 13.5, 0.535659, -2.0, -2.0, 35.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001934, -0.014954, -0.011825, -0.934847, 0.06984, -0.190821, -1.486099, -0.480569, 0.097936, 0.114511, 1.044726, 1.120122, 0.002554, -0.997542, 1.155564]},
  {'feature': [20, 17, 14, -2, -2, 6, -2, -2, 17, 12, -2, -2, 3, -2, -2], 'threshold': [0.299123, 53.653385, -281.5, -2.0, -2.0, 31.5, -2.0, -2.0, 46.701698, 659.5, -2.0, -2.0, 10.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001753, -0.022306, -0.01898, -0.447995, 0.120897, -0.161905, -1.079481, -0.394292, 0.059169, 0.031095, 0.591039, -0.173722, 0.170222, 0.811541, 1.732283]},
  {'feature': [5, 17, 6, -2, -2, 6, -2, -2, 12, 17, -2, -2, 11, -2, -2], 'threshold': [171.5, 46.81559, 33.5, -2.0, -2.0, 31.5, -2.0, -2.0, 1089.5, 42.0902, -2.0, -2.0, 453.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002544, -0.02587, -0.035315, -1.043076, -0.37465, 0.028592, -0.39153, 0.424221, 0.045114, 0.078068, 0.029053, 0.73476, -0.058019, -0.257866, -0.996914]},
  {'feature': [21, 4, 7, -2, -2, 9, -2, -2, 3, 1, -2, -2, -2], 'threshold': [0.54185, 3.5, 100.5, -2.0, -2.0, 15.5, -2.0, -2.0, 12.5, 422.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.000855, -0.010523, -0.0707, -0.608797, -0.952583, -0.001414, -0.196077, 0.322557, 0.101871, 0.096596, 1.091523, 1.110103, 1.18468]},
  {'feature': [14, 21, 21, -2, -2, -2, 4, 16, -2, -2, 16, -2, -2], 'threshold': [-511.5, 0.314317, 0.285236, -2.0, -2.0, -2.0, 8.5, 39.430515, -2.0, -2.0, 41.241432, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.000237, -0.033443, -0.030115, -0.76045, 1.526857, -1.206744, 0.03097, 0.083349, 2.245333, 0.339029, 0.00033, -0.456405, 0.276359]},
  {'feature': [21, 17, 17, -2, -2, 2, -2, -2, 3, 17, -2, -2, -2], 'threshold': [0.54185, 46.781157, 37.285473, -2.0, -2.0, 6.5, -2.0, -2.0, 12.5, 46.973078, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001777, -0.010734, -0.021558, 0.437383, -0.2888, 0.055292, 0.148066, 1.558651, 0.094586, 0.090524, 1.104703, 1.091832, 1.17084]},
  {'feature': [21, 4, 15, -2, -2, 16, -2, -2, 5, 17, -2, -2, 22, -2, -2], 'threshold': [0.285236, 27.5, -3.5, -2.0, -2.0, 52.889271, -2.0, -2.0, 136.5, 37.96451, -2.0, -2.0, 0.367003, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000388, -0.019954, -0.01595, -0.217771, 1.07557, -0.103804, -0.968013, 0.494819, 0.052958, -0.087755, 0.806663, -0.728779, 0.074074, 0.793901, 0.270987]},
  {'feature': [14, 21, 21, -2, -2, 11, -2, -2, 4, 16, -2, -2, 16, -2, -2], 'threshold': [-510.5, 0.314317, 0.286711, -2.0, -2.0, 620.5, -2.0, -2.0, 9.5, 39.430515, -2.0, -2.0, 41.241432, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001174, -0.030488, -0.027163, -0.65073, 0.821829, -0.146434, -1.213452, -1.143431, 0.029695, 0.074552, 2.087229, 0.325657, -0.001515, -0.433811, 0.255381]},
  {'feature': [20, 17, 5, -2, -2, 17, -2, -2, 17, 4, -2, -2, 4, -2, -2], 'threshold': [0.25695, 36.046062, 23.5, -2.0, -2.0, 53.653385, -2.0, -2.0, 42.123535, 6.5, -2.0, -2.0, 3.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000943, -0.02319, 0.073798, -0.097245, 1.764099, -0.027395, -0.327484, -0.657539, 0.036596, -0.020038, 1.183908, -0.376778, 0.066716, -0.506307, 0.687453]},
  {'feature': [14, 17, 17, -2, -2, 15, -2, -2, 10, 3, -2, -2, 14, -2, -2], 'threshold': [71.5, 46.781157, 37.301102, -2.0, -2.0, -27.5, -2.0, -2.0, 31.5, 11.5, -2.0, -2.0, 203.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00097, -0.009735, -0.019051, 0.369067, -0.263454, 0.048214, -1.004122, 0.424561, 0.084729, 0.07592, 1.090444, 0.14417, 0.119662, 1.219639, 1.134553]},
  {'feature': [21, 17, 17, -2, -2, 6, -2, -2, 0, 17, -2, -2, 22, -2, -2], 'threshold': [0.301007, 53.653385, 52.511068, -2.0, -2.0, 32.5, -2.0, -2.0, 62.5, 46.663427, -2.0, -2.0, 0.317895, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000501, -0.01568, -0.012036, -0.163168, 1.212953, -0.164642, -1.218621, -0.246939, 0.046397, 0.026898, -0.001399, 1.055217, 0.167844, 2.032421, 0.761125]},
  {'feature': [20, 17, 17, -2, -2, 17, -2, -2, 5, 21, -2, -2, 4, -2, -2], 'threshold': [0.253249, 36.046062, 34.176931, -2.0, -2.0, 46.817076, -2.0, -2.0, 64.5, 0.218734, -2.0, -2.0, 3.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000333, -0.02096, 0.078805, -0.196423, 1.894537, -0.02548, -0.563821, 0.131375, 0.032889, -0.071656, 0.561198, -0.615331, 0.04291, -0.290406, 0.410956]},
  {'feature': [20, 17, 17, -2, -2, 16, -2, -2, 22, 15, -2, -2, 14, -2, -2], 'threshold': [0.298936, 53.653385, 52.402849, -2.0, -2.0, 57.191286, -2.0, -2.0, 0.320714, -27.0, -2.0, -2.0, -66.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001581, -0.016422, -0.012151, -0.170859, 1.244697, -0.169698, -1.357153, -0.047915, 0.042637, 0.165412, 2.710907, 0.583582, 0.020534, -0.190865, 0.825633]},
  {'feature': [17, 4, 3, -2, -2, -2, 20, 17, -2, -2, 10, -2, -2], 'threshold': [37.285473, 25.5, 11.5, -2.0, -2.0, -2.0, 0.509288, 46.817076, -2.0, -2.0, 35.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.000153, 0.098262, 0.149717, 1.365117, -0.977241, -0.750221, -0.006532, -0.014108, -0.253014, 0.241274, 0.077253, 0.858804, 1.361681]},
  {'feature': [22, 17, 3, -2, -2, -2, 4, 17, -2, -2, 10, -2, -2], 'threshold': [0.229021, 47.343048, 13.5, -2.0, -2.0, -2.0, 17.5, 37.758041, -2.0, -2.0, 12.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.00482, -0.030438, -0.033859, -0.688253, -0.860279, 1.015915, 0.030396, 0.045421, 1.706547, 0.255524, -0.035265, 0.102753, -0.496115]},
  {'feature': [21, 4, 4, -2, -2, -2, 4, 17, -2, -2, 15, -2, -2], 'threshold': [0.228362, 23.5, 18.5, -2.0, -2.0, -2.0, 17.5, 37.285473, -2.0, -2.0, -5.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.001353, -0.027529, -0.029997, -0.717674, -1.230134, 0.662047, 0.020378, 0.03533, 1.625044, 0.189465, -0.040144, -0.495991, 0.311625]},
  {'feature': [20, 6, 5, -2, -2, 21, -2, -2, 4, 9, -2, -2, 4, -2, -2], 'threshold': [0.220464, 116.5, 21.5, -2.0, -2.0, 0.229955, -2.0, -2.0, 3.5, 31.5, -2.0, -2.0, 12.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001663, -0.029205, 0.092938, -0.327595, 1.359399, -0.033618, -1.001861, -0.99127, 0.022006, -0.051837, -1.044741, 0.578335, 0.032561, 0.440315, -0.056453]},
  {'feature': [21, 17, 18, -2, -2, 17, -2, -2, 3, 17, -2, -2, -2], 'threshold': [0.54185, 46.781157, 8.5, -2.0, -2.0, 53.387497, -2.0, -2.0, 12.5, 46.66028, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.003811, -0.011214, -0.019314, -0.167987, -0.702228, 0.037048, 0.405746, -0.65822, 0.071141, 0.066845, 1.076902, 1.065864, 1.132508]},
  {'feature': [21, 6, 16, -2, -2, 10, -2, -2, 3, 17, -2, -2, -2], 'threshold': [0.54185, 31.5, 53.786921, -2.0, -2.0, 5.5, -2.0, -2.0, 12.5, 46.66028, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.004248, -0.010925, -0.07995, -0.272021, -0.900206, -0.007185, 1.187792, -0.093529, 0.067878, 0.063302, 1.072522, 1.061925, 1.131237]},
  {'feature': [9, 16, 15, -2, -2, 5, -2, -2, 16, 20, -2, -2, 3, -2, -2], 'threshold': [14.5, 43.372314, -3.5, -2.0, -2.0, 177.5, -2.0, -2.0, 42.829996, 0.323737, -2.0, -2.0, 13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001114, -0.018934, -0.037956, -0.679444, 0.941446, 0.015652, -0.018436, 1.553352, 0.029122, 0.071035, 1.023733, 0.074755, -0.01073, 0.55924, -0.482635]},
  {'feature': [14, 17, 13, -2, -2, -2, 4, 17, -2, -2, 1, -2, -2], 'threshold': [-712.0, 47.607264, -9.5, -2.0, -2.0, -2.0, 17.5, 46.613688, -2.0, -2.0, 497.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.000666, -0.027802, -0.025864, -0.932437, 0.584291, -1.19913, 0.015885, 0.028869, 0.103478, 0.685749, -0.032185, -0.92115, -0.021346]},
  {'feature': [12, 19, 5, -2, -2, 10, -2, -2, 3, -2, 10, -2, -2], 'threshold': [692.5, 9.5, 184.5, -2.0, -2.0, 25.5, -2.0, -2.0, 9.5, -2.0, 35.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.00129, 0.023429, 0.010371, -0.072371, 0.749314, 0.121246, 2.523774, 0.485611, -0.019897, 1.200882, -0.022488, -1.089128, -0.223038]},
  {'feature': [5, 5, 12, -2, -2, 3, -2, -2, 12, 1, -2, -2, 17, -2, -2], 'threshold': [156.5, 151.5, 59.5, -2.0, -2.0, 16.5, -2.0, -2.0, 1196.5, 407.5, -2.0, -2.0, 43.836779, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001876, -0.014557, -0.011463, -0.53028, -0.077403, -0.15919, -1.463974, -0.644042, 0.031857, 0.051436, 1.298806, 0.286779, -0.058347, -0.502342, -1.150299]},
  {'feature': [20, 14, 21, -2, -2, -2, 4, 9, -2, -2, 4, -2, -2], 'threshold': [0.220464, -65.0, 0.260456, -2.0, -2.0, -2.0, 3.5, 31.5, -2.0, -2.0, 6.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.001472, -0.025671, -0.028265, -0.81928, -1.218408, 0.838174, 0.01997, -0.044651, -1.036095, 0.662932, 0.028804, 0.67533, 0.091949]},
  {'feature': [21, 17, 4, -2, -2, 17, -2, -2, 3, 17, -2, -2, -2], 'threshold': [0.531974, 37.285473, 18.5, -2.0, -2.0, 42.093769, -2.0, -2.0, 12.5, 46.626698, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.003322, -0.00908, 0.061764, 1.496906, -0.018453, -0.013979, -0.457931, -0.001188, 0.059926, 0.0552, 1.064755, 1.052199, 1.134039]},
  {'feature': [13, 20, 20, -2, -2, -2, 12, 14, -2, -2, 17, -2, -2], 'threshold': [-12.5, 0.2595, 0.251214, -2.0, -2.0, -2.0, 59.5, -20.5, -2.0, -2.0, 46.781157, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.002127, -0.026047, -0.023127, -0.929638, 0.824892, -1.238235, 0.018526, -0.06473, -1.160403, -0.11038, 0.025022, 0.096057, 0.465029]},
  {'feature': [15, 5, 18, -2, -2, 21, -2, -2, 19, 17, -2, -2, 21, -2, -2], 'threshold': [-36.5, 235.5, 4.5, -2.0, -2.0, 0.228799, -2.0, -2.0, 15.5, 42.043728, -2.0, -2.0, 0.282498, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001393, -0.025051, -0.020359, -0.93021, 0.529072, -0.073773, -1.034013, -1.150927, 0.017194, 0.013309, -0.160055, 0.226655, 0.188849, 0.613911, 1.807576]},
  {'feature': [17, 4, 3, -2, -2, -2, 17, 10, -2, -2, 15, -2, -2], 'threshold': [37.285473, 25.5, 10.5, -2.0, -2.0, -2.0, 41.386911, 42.5, -2.0, -2.0, -36.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.00245, 0.079578, 0.122046, 1.270221, -0.799373, -0.676954, -0.002777, -0.037392, -0.763515, 0.159079, 0.008661, -0.763334, 0.211375]},
  {'feature': [14, 21, 21, -2, -2, -2, 3, 0, -2, -2, 13, -2, -2], 'threshold': [-511.5, 0.314317, 0.282366, -2.0, -2.0, -2.0, 19.5, 72.5, -2.0, -2.0, -13.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.002021, -0.02168, -0.01843, -0.625988, 0.721151, -1.196183, 0.015942, 0.01067, 0.010842, 1.064067, 0.188805, 0.004155, 1.694713]},
  {'feature': [10, 16, 15, -2, -2, 13, -2, -2, 16, 9, -2, -2, 20, -2, -2], 'threshold': [28.5, 42.793627, -3.5, -2.0, -2.0, -7.5, -2.0, -2.0, 43.099833, 15.5, -2.0, -2.0, 0.511364, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001476, 0.027484, -0.036423, -0.56502, 0.590434, 0.074446, 1.913874, 0.302168, -0.012063, 0.004569, -0.635374, 0.52333, -0.041367, -0.479858, 1.367042]},
  {'feature': [14, 22, 21, -2, -2, 16, -2, -2, 10, 19, -2, -2, 14, -2, -2], 'threshold': [71.5, 0.377155, 0.396473, -2.0, -2.0, 47.032438, -2.0, -2.0, 31.5, 6.5, -2.0, -2.0, 207.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001065, -0.006573, -0.001191, -0.035273, 0.981508, -0.062666, -0.504382, 1.387377, 0.053845, 0.046239, 1.053764, 0.456122, 0.081528, 1.181269, 1.085836]},
  {'feature': [21, 6, -2, 17, -2, -2, 17, 16, -2, -2, 16, -2, -2], 'threshold': [0.214231, 129.5, -2.0, 38.567114, -2.0, -2.0, 53.653385, 52.402849, -2.0, -2.0, 58.534693, -2.0, -2.0], 'left': [1, 2, -1, 4, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 3, -1, 5, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.001722, -0.019129, 0.589406, -0.022197, 0.865307, -1.011071, 0.017313, 0.022455, 0.12567, 1.085147, -0.127257, -1.256265, 0.194344]},
  {'feature': [14, 11, 9, -2, -2, -2, 19, 10, -2, -2, 10, -2, -2], 'threshold': [-726.5, 453.0, 23.5, -2.0, -2.0, -2.0, 8.5, 51.5, -2.0, -2.0, 25.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-4.7e-05, -0.021073, -0.01845, -0.959238, 1.009184, -1.136445, 0.012448, -0.002916, -0.075823, 1.015223, 0.044492, 1.4905, 0.207301]},
  {'feature': [17, 17, 4, -2, -2, -2, 16, 9, -2, -2, -2], 'threshold': [53.653385, 52.686335, 27.5, -2.0, -2.0, -2.0, 57.191286, 4.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, -1], 'value': [0.000713, 0.003556, 0.001347, 0.050172, -0.643705, 1.595629, -0.1243, -0.187511, -1.310814, -0.824565, 0.103954]},
  {'feature': [22, 12, -2, 13, -2, -2, 17, 10, -2, -2, 16, -2, -2], 'threshold': [0.220486, 100.5, -2.0, -9.5, -2.0, -2.0, 37.285473, 22.5, -2.0, -2.0, 38.530226, -2.0, -2.0], 'left': [1, 2, -1, 4, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 3, -1, 5, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.000635, -0.021065, 0.643476, -0.02327, -0.890719, -1.027666, 0.014897, 0.095285, 0.120879, 1.602518, 0.008151, -0.658767, 0.124151]},
  {'feature': [13, 20, 20, -2, -2, -2, 4, 9, -2, -2, 4, -2, -2], 'threshold': [-12.5, 0.25782, 0.248762, -2.0, -2.0, -2.0, 3.5, 31.5, -2.0, -2.0, 6.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.000126, -0.020467, -0.017258, -0.933846, 0.766661, -1.297641, 0.01233, -0.055601, -1.108998, 0.562113, 0.021195, 0.826542, 0.015468]},
  {'feature': [5, 22, 17, -2, -2, 20, -2, -2, 12, 19, -2, -2, 11, -2, -2], 'threshold': [171.5, 0.314145, 37.301102, -2.0, -2.0, 0.322142, -2.0, -2.0, 1067.5, 15.5, -2.0, -2.0, 516.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00142, -0.013204, -0.008314, 0.41609, -0.187124, -0.10561, -1.520473, -0.219734, 0.022832, 0.047622, 0.30834, 1.631051, -0.049527, -0.368747, -1.142681]},
  {'feature': [17, 14, 22, -2, -2, 10, -2, -2, 1, 0, -2, -2, 10, -2, -2], 'threshold': [46.169661, 71.5, 0.327957, -2.0, -2.0, 31.5, -2.0, -2.0, 497.5, 62.5, -2.0, -2.0, 47.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.0007, -0.007148, -0.011873, -0.018704, -0.410036, 0.05419, 0.902787, 1.119278, 0.033385, -0.077258, -0.871523, -0.065542, 0.06303, 0.57078, -0.696586]},
  {'feature': [5, 16, 16, -2, -2, 21, -2, -2, 17, 7, -2, -2, 17, -2, -2], 'threshold': [29.5, 49.263842, 48.270311, -2.0, -2.0, 0.219583, -2.0, -2.0, 37.70223, 10.5, -2.0, -2.0, 43.952579, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002926, -0.025249, -0.014088, -0.540992, 1.435344, -0.084459, 0.725731, -0.630842, 0.015751, 0.126759, 1.961169, 0.620274, 0.009367, -0.123692, 0.338515]},
  {'feature': [17, 17, 4, -2, -2, -2, 6, 19, -2, -2, -2], 'threshold': [53.653385, 52.679098, 27.5, -2.0, -2.0, -2.0, 32.5, 2.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, -1], 'value': [-0.004654, -0.002145, -0.003947, -0.004862, -0.680949, 1.260762, -0.127747, -0.195641, -0.996884, -1.293568, 0.027116]},
  {'feature': [12, 17, 16, -2, -2, 16, -2, -2, 10, 17, -2, -2, 14, -2, -2], 'threshold': [664.0, 53.653385, 52.402849, -2.0, -2.0, 57.191286, -2.0, -2.0, 41.5, 46.405439, -2.0, -2.0, -283.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.003125, 0.02398, 0.031417, 0.177713, 1.080303, -0.111678, -1.082652, -0.003357, -0.011316, -0.058042, -0.805915, 1.052763, -0.000797, -0.107093, 1.048808]},
  {'feature': [17, 17, 10, -2, -2, -2, 14, 5, -2, -2, -2], 'threshold': [53.653385, 52.670395, 28.5, -2.0, -2.0, -2.0, -22.0, 14.0, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, -1], 'value': [-0.000844, 0.002481, 0.000427, 0.230285, -0.132781, 1.502758, -0.147129, -0.20476, -1.015095, -1.321584, -0.271614]},
  {'feature': [12, 16, 17, -2, -2, 17, -2, -2, 14, 17, -2, -2, 7, -2, -2], 'threshold': [59.5, 49.582821, 48.26194, -2.0, -2.0, 52.686335, -2.0, -2.0, -66.5, 50.368979, -2.0, -2.0, 10.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001757, -0.083792, -0.02943, -0.569816, 0.457105, -0.162864, -1.187585, -0.612731, 0.001973, -0.006323, -0.027602, -0.834389, 0.053459, 0.889009, 0.471392]},
  {'feature': [17, 21, 22, -2, -2, 9, -2, -2, 0, 15, -2, -2, 15, -2, -2], 'threshold': [46.781157, 0.457998, 0.440972, -2.0, -2.0, 29.5, -2.0, -2.0, 2.5, -27.5, -2.0, -2.0, -11.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001327, -0.008154, -0.013489, -0.111594, -1.117901, 0.041003, -0.136139, 0.993886, 0.03703, 0.060479, -0.813337, 0.514718, -0.084226, -1.369223, 0.159004]},
  {'feature': [17, 5, 9, -2, -2, 17, -2, -2, 2, 21, -2, -2, 9, -2, -2], 'threshold': [37.285473, 31.5, 1.5, -2.0, -2.0, 37.094589, -2.0, -2.0, 3.5, 0.281398, -2.0, -2.0, 7.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001001, 0.056628, -0.020898, 1.183979, -0.619026, 0.130277, 0.580279, 2.234251, -0.004864, -0.02356, -0.309998, -1.017658, 0.009481, 1.900771, 0.019551]},
  {'feature': [9, 4, 2, -2, -2, 9, -2, -2, 3, 21, -2, -2, -2], 'threshold': [34.5, 3.5, 9.5, -2.0, -2.0, 15.5, -2.0, -2.0, 14.5, 0.465199, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.003152, -0.00747, -0.052846, -0.552148, -1.204595, -0.001073, -0.14377, 0.199006, 0.046798, 0.03189, -0.723519, 1.066051, 1.246283]},
  {'feature': [4, 17, 3, -2, -2, 17, -2, -2, 16, 17, -2, -2, -2], 'threshold': [27.5, 37.285473, 11.5, -2.0, -2.0, 46.628881, -2.0, -2.0, 52.494715, 49.04487, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001247, 0.001671, 0.089735, 0.881441, -1.09241, -0.003532, -0.137998, 0.283134, -0.080654, -0.143266, -0.590193, -1.381014, 0.694046]},
  {'feature': [17, 9, 18, -2, -2, 3, -2, -2, 15, 20, -2, -2, 6, -2, -2], 'threshold': [46.781157, 34.5, 9.5, -2.0, -2.0, 14.5, -2.0, -2.0, -27.5, 0.229874, -2.0, -2.0, 464.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001771, -0.005837, -0.010029, -0.081997, -1.084408, 0.050035, 0.526228, 1.252868, 0.043153, -0.072892, -0.5426, -1.172878, 0.069071, 0.302141, 1.814395]},
  {'feature': [17, 17, 17, -2, -2, 15, -2, -2, 19, 4, -2, -2, -2], 'threshold': [50.503325, 46.781157, 37.285473, -2.0, -2.0, -27.5, -2.0, -2.0, 5.5, 16.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.002001, 0.001998, -0.006078, 0.365483, -0.132101, 0.065085, -0.863444, 0.689079, -0.084791, -0.042128, 0.419744, -0.473698, -1.486118]},
  {'feature': [13, 20, 20, -2, -2, -2, 5, 11, -2, -2, 17, -2, -2], 'threshold': [-12.5, 0.25782, 0.246265, -2.0, -2.0, -2.0, 29.5, 32.5, -2.0, -2.0, 37.285473, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.002828, -0.01809, -0.015095, -0.962464, 0.801926, -1.277185, 0.014969, -0.032988, -0.010705, -0.609033, 0.02469, 1.045338, 0.134985]},
  {'feature': [17, 17, 4, -2, -2, -2, 19, -2, -2], 'threshold': [54.214201, 52.679098, 31.5, -2.0, -2.0, -2.0, 2.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 8, -1, -1], 'value': [-0.000629, 0.001493, -0.000345, 0.017155, -1.28539, 0.948448, -0.125152, -0.236406, -1.266303]},
  {'feature': [9, 16, 15, -2, -2, 16, -2, -2, 16, 15, -2, -2, 17, -2, -2], 'threshold': [15.5, 43.372314, -3.5, -2.0, -2.0, 44.37184, -2.0, -2.0, 43.158106, -22.5, -2.0, -2.0, 44.358679, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001035, -0.009829, -0.026143, -0.574802, 1.046708, 0.01907, 1.361981, 0.027243, 0.021776, 0.070923, 1.146954, -0.015298, -0.028962, -0.719812, 0.212801]},
  {'feature': [5, 20, 17, -2, -2, 8, -2, -2, 12, 0, -2, -2, 10, -2, -2], 'threshold': [64.5, 0.256112, 35.956049, -2.0, -2.0, 117.0, -2.0, -2.0, 665.5, 57.5, -2.0, -2.0, 39.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001619, -0.017018, -0.011408, 0.411988, -0.286167, -0.087198, -0.190818, -1.329015, 0.014996, 0.047304, 0.285631, 1.244762, -0.008669, -0.631828, 0.10462]},
  {'feature': [17, 19, 21, -2, -2, 10, -2, -2, 15, 22, -2, -2, 6, -2, -2], 'threshold': [46.187262, 8.5, 0.422259, -2.0, -2.0, 25.5, -2.0, -2.0, -27.5, 0.245, -2.0, -2.0, 462.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002092, -0.01078, -0.027695, -0.395458, 0.498641, 0.003898, 1.624287, -0.040646, 0.033944, -0.040217, -0.131335, -1.061891, 0.058283, 0.244382, 1.545741]},
  {'feature': [21, 14, 3, -2, -2, 11, -2, -2, 0, 1, -2, -2, 10, -2, -2], 'threshold': [0.193528, -561.0, 12.5, -2.0, -2.0, 45.5, -2.0, -2.0, 77.5, 497.5, -2.0, -2.0, 51.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00371, -0.015637, -0.013408, 1.081615, -1.019273, -0.038027, 0.31316, -1.095567, 0.015608, 0.009855, -0.372615, 0.154052, 0.08828, 1.219073, -1.233052]},
  {'feature': [15, 3, 21, -2, -2, 10, -2, -2, 3, 17, -2, -2, 21, -2, -2], 'threshold': [-5.5, 8.5, 0.287166, -2.0, -2.0, 24.5, -2.0, -2.0, 11.5, 54.45747, -2.0, -2.0, 0.54185, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002152, -0.008112, -0.064847, -0.272683, -1.387424, -0.000808, 0.738981, -0.091154, 0.028887, 0.042112, 0.549804, -0.478244, -0.03853, -0.878741, 1.068101]},
  {'feature': [14, 17, 18, -2, -2, 20, -2, -2, 12, 16, -2, -2, 7, -2, -2], 'threshold': [-66.5, 50.368979, 8.5, -2.0, -2.0, 0.254032, -2.0, -2.0, 59.5, 48.974051, -2.0, -2.0, 10.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [5.4e-05, -0.006632, -0.003675, -0.006675, -0.733495, -0.151849, -0.306969, -1.475078, 0.031241, -0.03316, 0.141979, -0.543267, 0.0525, 0.887565, 0.462319]},
  {'feature': [21, 20, 21, -2, -2, 3, -2, -2, 4, 17, -2, -2, 1, -2, -2], 'threshold': [0.197667, 0.255229, 0.172812, -2.0, -2.0, 15.5, -2.0, -2.0, 16.5, 37.885118, -2.0, -2.0, 497.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001882, -0.017058, -0.015036, -0.822871, -0.879146, -0.063293, -1.139379, -1.052046, 0.014499, 0.027742, 1.161851, 0.162116, -0.030445, -0.840668, -0.0345]},
  {'feature': [5, 21, 15, -2, -2, 22, -2, -2, 10, 16, -2, -2, 16, -2, -2], 'threshold': [32.5, 0.219926, -12.5, -2.0, -2.0, 0.261364, -2.0, -2.0, 28.5, 43.372314, -2.0, -2.0, 42.829996, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [5.2e-05, -0.018197, -0.006628, -0.939931, 0.974476, -0.048055, -0.187773, -1.360055, 0.008945, 0.043548, -0.149942, 0.728064, -0.00248, 0.213986, -0.288495]},
  {'feature': [14, 17, 22, -2, -2, 5, -2, -2, 5, 8, -2, -2, 9, -2, -2], 'threshold': [-66.5, 50.368979, 0.372685, -2.0, -2.0, 34.0, -2.0, -2.0, 11.5, 33.5, -2.0, -2.0, 1.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001829, -0.008535, -0.005421, 0.01118, -0.416626, -0.149564, -0.454371, -1.090347, 0.028767, -0.031104, -0.422942, 0.359727, 0.04552, 1.333092, 0.446746]},
  {'feature': [6, 0, 0, -2, -2, 5, -2, -2, 10, 14, -2, -2, 10, -2, -2], 'threshold': [361.5, 52.5, 2.5, -2.0, -2.0, 108.0, -2.0, -2.0, 26.5, -156.0, -2.0, -2.0, 35.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000168, 0.017605, 0.007705, 0.137185, -0.360559, 0.108225, -1.134601, 1.772281, -0.011189, 0.115932, 1.219476, 0.202017, -0.014316, -0.876142, -0.109658]},
  {'feature': [17, 17, 19, -2, -2, 16, -2, -2, 8, -2, -2], 'threshold': [53.387497, 46.781157, 6.5, -2.0, -2.0, 52.402849, -2.0, -2.0, 21.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, -1], 'value': [0.00245, 0.004652, -0.002302, -0.234072, 0.088678, 0.045745, 0.225448, 1.005902, -0.102151, -0.125408, -1.113009]},
  {'feature': [17, 4, 16, -2, -2, 15, -2, -2, 9, 11, -2, -2, 5, -2, -2], 'threshold': [37.285473, 15.5, 37.784348, -2.0, -2.0, -3.5, -2.0, -2.0, 31.5, 540.5, -2.0, -2.0, 324.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001585, 0.052624, 0.176448, 2.343466, 0.491413, 0.009163, -0.337004, 1.425727, -0.005399, -0.009707, -0.062875, -0.54855, 0.034915, 1.099984, 0.339389]},
  {'feature': [17, 4, 3, -2, -2, -2, 9, 11, -2, -2, 13, -2, -2], 'threshold': [37.285473, 25.5, 11.5, -2.0, -2.0, -2.0, 31.5, 749.5, -2.0, -2.0, -5.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.001155, 0.054126, 0.081909, 0.810306, -1.111173, -0.58272, -0.005024, -0.009925, -0.08519, -1.306727, 0.039272, 1.404502, 0.3607]},
  {'feature': [9, 16, 15, -2, -2, 16, -2, -2, 16, 15, -2, -2, 17, -2, -2], 'threshold': [14.5, 43.370768, -3.5, -2.0, -2.0, 48.960245, -2.0, -2.0, 43.150784, -22.5, -2.0, -2.0, 46.160707, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000926, -0.010526, -0.024364, -0.584154, 0.850987, 0.0147, 0.452547, -0.205545, 0.020603, 0.05479, 0.839252, -0.018466, -0.015304, -0.379758, 0.570716]},
  {'feature': [17, 4, 17, -2, -2, 16, -2, -2, 15, 20, -2, -2, 4, -2, -2], 'threshold': [42.469976, 8.5, 39.257895, -2.0, -2.0, 41.229475, -2.0, -2.0, -36.5, 0.228054, -2.0, -2.0, 3.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000834, -0.017677, 0.030917, 2.216095, 0.119363, -0.043532, -0.673289, 0.089819, 0.013998, -0.021817, -0.738075, -1.152807, 0.034142, -0.467199, 0.336254]},
  {'feature': [17, 17, 4, -2, -2, 15, -2, -2, 8, 12, -2, -2, 9, -2, -2], 'threshold': [50.503325, 46.817076, 30.0, -2.0, -2.0, -24.5, -2.0, -2.0, 44.5, 62.0, -2.0, -2.0, 8.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.002146, 0.00142, -0.005991, -0.059336, -1.181913, 0.061117, -0.561266, 0.626565, -0.071391, -0.012535, -0.68431, 0.909914, -0.169483, -1.260201, -0.530109]},
  {'feature': [4, 17, 3, -2, -2, 17, -2, -2, 9, 14, -2, -2, -2], 'threshold': [17.5, 37.758041, 12.5, -2.0, -2.0, 47.695784, -2.0, -2.0, 11.5, -37.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.002449, 0.002695, 0.106511, 1.255955, -0.940013, -0.001031, -0.065309, 0.367405, -0.035326, -0.022016, 0.003305, -0.522522, -1.169419]},
  {'feature': [14, 22, 20, -2, -2, 16, -2, -2, 3, 17, -2, -2, -2], 'threshold': [91.5, 0.377155, 0.375735, -2.0, -2.0, 47.883072, -2.0, -2.0, 12.5, 46.66028, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001348, -0.004764, 0.000426, -0.017861, 0.888765, -0.058042, -0.506283, 1.296338, 0.035249, 0.032768, 1.041965, 1.028118, 1.072664]},
  {'feature': [9, 22, 21, -2, -2, 10, -2, -2, 22, -2, 14, -2, -2], 'threshold': [31.5, 0.327957, 0.385997, -2.0, -2.0, 26.5, -2.0, -2.0, 0.403125, -2.0, -113.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [-0.002119, -0.006445, 1.8e-05, -0.019814, 1.017207, -0.04762, 0.330443, -0.556611, 0.037871, 1.044937, 0.025046, -0.555341, 1.090747]},
  {'feature': [17, 16, -2, 13, -2, -2, 21, 22, -2, -2, 10, -2, -2], 'threshold': [37.285473, 29.612673, -2.0, -7.5, -2.0, -2.0, 0.457998, 0.327957, -2.0, -2.0, 37.5, -2.0, -2.0], 'left': [1, 2, -1, 4, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 3, -1, 5, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.000421, 0.065141, -0.890366, 0.095077, -1.140421, 0.861051, -0.004913, -0.009543, -0.021485, -0.364043, 0.032359, 0.483122, 0.860392]},
  {'feature': [17, 10, 15, -2, -2, 15, -2, -2, 19, 21, -2, -2, 8, -2, -2], 'threshold': [37.133722, 22.5, -3.5, -2.0, -2.0, -20.5, -2.0, -2.0, 6.5, 0.529692, -2.0, -2.0, 125.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001333, 0.057145, 0.010201, -0.392079, 1.194725, 0.140081, -0.192711, 1.438446, -0.00182, -0.021433, -0.270148, 1.044548, 0.008895, 1.357775, 0.04518]},
  {'feature': [4, 10, 16, -2, -2, 12, -2, -2, 16, 16, -2, -2, -2], 'threshold': [27.5, 28.5, 42.990904, -2.0, -2.0, 341.0, -2.0, -2.0, 52.494715, 48.974051, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-1.9e-05, 0.002662, 0.03335, -0.126408, 0.490557, -0.007672, 0.888537, -0.147565, -0.072308, -0.114194, -0.508941, -1.132121, 0.277998]},
  {'feature': [17, 4, 10, -2, -2, -2, 15, 3, -2, -2, 17, -2, -2], 'threshold': [46.781157, 30.0, 4.5, -2.0, -2.0, -2.0, -24.5, 13.5, -2.0, -2.0, 48.825905, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.001169, -0.005477, -0.004226, 1.25435, -0.078619, -1.182793, 0.037954, -0.058918, -1.271689, -0.020629, 0.067495, 1.128784, 0.019921]},
  {'feature': [14, 17, 22, -2, -2, 17, -2, -2, 14, 7, -2, -2, 16, -2, -2], 'threshold': [-66.5, 50.368979, 0.367003, -2.0, -2.0, 52.75918, -2.0, -2.0, -42.5, 10.5, -2.0, -2.0, 53.786921, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.00158, -0.004654, -0.001256, 0.058301, -0.347727, -0.167397, -1.263042, -0.449323, 0.029776, 0.121011, 1.07798, 0.204371, 0.014412, 0.317381, -0.820386]},
  {'feature': [13, 20, 9, -2, -2, -2, 4, 9, -2, -2, 4, -2, -2], 'threshold': [-12.5, 0.25782, 19.5, -2.0, -2.0, -2.0, 3.5, 31.5, -2.0, -2.0, 6.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.00045, -0.015775, -0.01293, -0.690409, -1.139281, -1.262414, 0.009933, -0.042404, -0.943215, 0.422559, 0.017102, 0.6437, 0.025591]},
  {'feature': [21, 16, 22, -2, -2, -2, 0, 1, -2, -2, 10, -2, -2], 'threshold': [0.211443, 54.847172, 0.28869, -2.0, -2.0, -2.0, 62.5, 497.5, -2.0, -2.0, 50.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [0.000468, -0.012673, -0.014271, -0.732338, -0.872173, 0.829352, 0.009825, 0.002616, -0.494266, 0.096814, 0.077297, 1.115184, -1.170959]},
  {'feature': [9, 16, 16, -2, -2, 16, -2, -2, 16, 2, -2, -2, 17, -2, -2], 'threshold': [15.5, 43.372314, 36.052517, -2.0, -2.0, 44.37184, -2.0, -2.0, 43.256191, 4.5, -2.0, -2.0, 44.980825, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000201, -0.008547, -0.024713, -0.107994, -0.666202, 0.020441, 1.264953, 0.052936, 0.016619, 0.062618, 3.214555, 0.395712, -0.031207, -0.657604, 0.245359]},
  {'feature': [17, 4, 16, -2, -2, 15, -2, -2, 4, 17, -2, -2, -2], 'threshold': [37.285473, 16.5, 37.339014, -2.0, -2.0, -3.5, -2.0, -2.0, 28.5, 50.503325, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.005623, 0.052651, 0.133706, 1.577126, 0.481125, 0.013011, -0.285445, 1.155872, -0.009723, -0.011133, -0.089055, -0.584559, 0.645288]},
  {'feature': [8, 19, 16, -2, -2, 13, -2, -2, 12, 14, -2, -2, 10, -2, -2], 'threshold': [157.5, 6.5, 52.402849, -2.0, -2.0, -4.5, -2.0, -2.0, 459.5, -130.5, -2.0, -2.0, 26.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000302, 0.019585, 0.004645, -0.034026, 0.428639, 0.118689, 1.097553, -0.072088, -0.007771, -0.0838, -0.911879, 1.177751, -0.003515, 0.68781, -0.107868]},
  {'feature': [17, 4, 10, -2, -2, -2, 17, 4, -2, -2, 4, -2, -2], 'threshold': [37.626225, 28.5, 4.5, -2.0, -2.0, -2.0, 41.386593, 8.5, -2.0, -2.0, 3.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.00083, 0.046187, 0.066213, 1.931074, 0.335037, -1.184489, -0.004346, -0.02529, 0.450934, -0.651682, 0.002354, -0.546887, 0.097176]},
  {'feature': [5, 22, 20, -2, -2, 15, -2, -2, 12, 20, -2, -2, 15, -2, -2], 'threshold': [201.5, 0.322005, 0.298936, -2.0, -2.0, -9.5, -2.0, -2.0, 1185.5, 0.323876, -2.0, -2.0, -37.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001784, -0.009318, -0.003956, -0.122879, 0.625179, -0.098628, -1.028144, 0.0968, 0.01839, 0.03271, 0.601622, 0.104363, -0.046287, -0.680189, -0.94073]},
  {'feature': [6, 6, 7, -2, -2, 6, -2, -2, 16, 10, -2, -2, -2], 'threshold': [32.5, 22.5, 24.0, -2.0, -2.0, 28.5, -2.0, -2.0, 56.36281, 4.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.006134, -0.060329, 0.015585, -0.380437, 1.45832, -0.098635, -1.280103, -0.475438, -0.003111, -0.004563, 1.024841, -0.069201, 1.311337]},
  {'feature': [20, 21, 10, -2, -2, 19, -2, -2, 4, 9, -2, -2, 10, -2, -2], 'threshold': [0.221281, 0.250875, 25.5, -2.0, -2.0, 2.5, -2.0, -2.0, 3.5, 31.5, -2.0, -2.0, 41.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001369, -0.013756, -0.010876, 0.509923, -1.026178, -0.057488, 0.132456, -0.788735, 0.011296, -0.043247, -1.018471, 0.487203, 0.019308, 0.030171, 0.376865]},
  {'feature': [17, 16, 12, -2, -2, 10, -2, -2, 4, 17, -2, -2, -2], 'threshold': [37.626225, 29.612673, 754.0, -2.0, -2.0, 4.5, -2.0, -2.0, 28.5, 53.387497, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [7.3e-05, 0.042608, -0.074995, -1.254652, -1.00982, 0.069036, 1.623038, 0.342765, -0.00314, -0.004315, -0.020609, -0.819143, 0.564531]},
  {'feature': [14, 13, 15, -2, -2, 17, -2, -2, 16, 16, -2, -2, 16, -2, -2], 'threshold': [-66.5, -5.5, -13.5, -2.0, -2.0, 37.638395, -2.0, -2.0, 36.098639, 33.067675, -2.0, -2.0, 38.123205, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [6.3e-05, -0.005228, 0.003738, -0.010237, 0.868515, -0.05566, 0.486039, -0.452052, 0.024098, 0.109953, -0.091179, 1.518808, 0.016414, -1.023222, 0.274455]},
  {'feature': [5, 11, 14, -2, -2, 20, -2, -2, 6, 11, -2, -2, 20, -2, -2], 'threshold': [30.5, 49.5, -39.0, -2.0, -2.0, 0.246212, -2.0, -2.0, 114.5, 45.5, -2.0, -2.0, 0.220464, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002578, -0.016749, -0.011202, -0.074033, -0.422499, -0.106656, 0.072949, -1.463858, 0.011509, 0.086174, 1.536786, 0.689815, 0.006478, -0.825644, 0.125074]},
  {'feature': [9, 16, 21, -2, -2, 16, -2, -2, 16, 2, -2, -2, 17, -2, -2], 'threshold': [15.5, 43.372314, 0.257455, -2.0, -2.0, 44.37184, -2.0, -2.0, 43.089855, 4.5, -2.0, -2.0, 44.354639, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.001484, -0.007281, -0.023587, -0.329211, -0.689146, 0.021101, 0.968574, 0.081734, 0.018004, 0.05517, 2.548335, 0.337541, -0.01958, -0.677839, 0.265032]},
  {'feature': [14, 22, 20, -2, -2, 16, -2, -2, 14, 7, -2, -2, 5, -2, -2], 'threshold': [-66.5, 0.327957, 0.299123, -2.0, -2.0, 47.561396, -2.0, -2.0, -37.5, 10.5, -2.0, -2.0, 14.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001862, -0.00703, 3.8e-05, -0.083123, 0.663146, -0.052464, -0.429958, 0.960145, 0.022193, 0.077872, 0.705389, 0.045777, 0.008082, -0.342083, 0.506264]},
  {'feature': [17, 17, 17, -2, -2, 6, -2, -2, 1, 16, -2, -2, 10, -2, -2], 'threshold': [46.613808, 45.268324, 43.952579, -2.0, -2.0, 257.5, -2.0, -2.0, 497.5, 53.123116, -2.0, -2.0, 44.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.001847, -0.007618, -0.003043, -0.128622, 0.307933, -0.044839, -1.231, -0.304441, 0.025191, -0.058735, -0.355221, -1.300658, 0.045647, 0.436034, -0.716525]},
  {'feature': [12, 8, 16, -2, -2, 21, -2, -2, 3, -2, 10, -2, -2], 'threshold': [665.5, 234.5, 48.987814, -2.0, -2.0, 0.218176, -2.0, -2.0, 9.5, -2.0, 35.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [0.001812, 0.014622, 0.003461, 0.119868, -0.204189, 0.078516, -1.06527, 0.768096, -0.00707, 1.11528, -0.009057, -1.038626, -0.045206]},
  {'feature': [15, 20, 18, -2, -2, 14, -2, -2, 10, 0, -2, -2, 4, -2, -2], 'threshold': [-35.5, 0.247185, 4.5, -2.0, -2.0, -745.5, -2.0, -2.0, 51.5, 72.5, -2.0, -2.0, 8.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.002765, -0.013358, -0.007675, -0.83369, 1.294248, -0.059518, -0.349284, -0.935429, 0.012982, 0.007999, 0.005406, 0.943157, 0.122074, -0.090302, 1.674827]},
  {'feature': [16, 4, 10, -2, -2, 16, -2, -2, -2], 'threshold': [56.852638, 25.5, 15.5, -2.0, -2.0, 51.803852, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, -1], 'value': [-0.002996, -0.00413, -0.001714, 0.380839, -0.084004, -0.069718, -0.672645, 0.297951, 0.644806]},
  {'feature': [13, 15, 19, -2, -2, -2, 14, 0, -2, -2, 4, -2, -2], 'threshold': [-6.5, -13.5, 8.5, -2.0, -2.0, -2.0, -66.5, 47.5, -2.0, -2.0, 24.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [-0.006277, 0.002166, -0.001349, -0.329337, 0.227869, 1.542641, -0.0219, -0.054, -0.370615, 0.785269, 0.009907, 0.286259, -0.355741]},
  {'feature': [4, 10, 12, -2, -2, 22, -2, -2, 20, 15, -2, -2, 19, -2, -2], 'threshold': [3.5, 27.5, 479.0, -2.0, -2.0, 0.239048, -2.0, -2.0, 0.220464, -8.5, -2.0, -2.0, 8.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000824, -0.022802, 0.063031, 0.308982, 1.391917, -0.035002, -0.715007, -0.725812, 0.00483, -0.011932, -0.721287, 0.541876, 0.01516, -0.010132, 0.334968]},
  {'feature': [16, 17, 16, -2, -2, 9, -2, -2, -2], 'threshold': [59.120594, 53.653385, 52.404345, -2.0, -2.0, 3.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, -1], 'value': [6.8e-05, -0.000798, 0.001298, -0.013055, 0.789157, -0.130514, -1.23705, -0.558765, 0.861062]},
  {'feature': [17, 22, 11, -2, -2, 14, -2, -2, 15, 16, -2, -2, 13, -2, -2], 'threshold': [42.049885, 0.327957, 427.5, -2.0, -2.0, -81.5, -2.0, -2.0, -24.5, 43.084869, -2.0, -2.0, -5.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [0.000447, -0.013392, -0.001276, -0.084217, 1.026038, -0.076848, -1.099468, 1.020531, 0.008357, -0.010895, 0.333499, -0.638963, 0.029728, 0.524402, 0.016488]},
  {'feature': [6, 16, 19, -2, -2, -2, 10, -2, 17, -2, -2], 'threshold': [33.5, 53.786921, 3.5, -2.0, -2.0, -2.0, 3.5, -2.0, 48.881138, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, -1, 9, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 8, -1, 10, -1, -1], 'value': [-0.001393, -0.048608, -0.020122, -0.324535, 0.519414, -1.047107, 0.001376, 1.496923, -0.000228, 0.03048, -0.303137]},
  {'feature': [4, 17, 16, -2, -2, 17, -2, -2, 16, 17, -2, -2, -2], 'threshold': [17.5, 37.285473, 36.96069, -2.0, -2.0, 46.562786, -2.0, -2.0, 56.852638, 50.506166, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, -1], 'value': [-0.001457, 0.0024, 0.102371, 1.253466, 0.276286, -0.000488, -0.076425, 0.279342, -0.025313, -0.036506, -0.145796, -0.705163, 0.660846]},
  {'feature': [17, 17, 15, -2, -2, -2, 11, 22, -2, -2, 4, -2, -2], 'threshold': [37.285473, 37.094589, -3.5, -2.0, -2.0, -2.0, 330.5, 0.310096, -2.0, -2.0, 3.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, 8, -1, -1, 11, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 10, 9, -1, -1, 12, -1, -1], 'value': [8.7e-05, 0.043493, 0.020959, -0.063287, 1.10222, 1.608504, -0.00295, -0.010726, -0.059754, -0.640464, 0.01747, -0.438428, 0.30878]},
  {'feature': [16, 16, 4, -2, -2, 4, -2, -2, -2], 'threshold': [56.852638, 50.506166, 30.0, -2.0, -2.0, 19.5, -2.0, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, -1], 'value': [-0.000158, -0.001416, 0.001526, 0.039549, -1.059895, -0.048562, 0.053908, -0.810561, 0.690224]},
  {'feature': [17, 4, 17, -2, -2, 3, -2, -2, 15, 9, -2, -2, 17, -2, -2], 'threshold': [42.920439, 7.5, 39.693588, -2.0, -2.0, 15.5, -2.0, -2.0, -36.5, 20.5, -2.0, -2.0, 43.26656, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.000377, -0.014812, 0.017304, 2.476864, -0.095555, -0.027401, -0.396953, 0.045382, 0.012376, -0.016728, -0.720016, -1.128517, 0.027847, 1.330924, 0.146101]},
  {'feature': [9, 18, 4, -2, -2, 17, -2, -2, 22, -2, 14, -2, -2], 'threshold': [31.5, 8.5, 3.5, -2.0, -2.0, 44.899466, -2.0, -2.0, 0.403125, -2.0, -417.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, -1, 11, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 10, -1, 12, -1, -1], 'value': [0.001495, -0.002204, 0.000656, -0.890055, 0.053122, -0.103385, -1.059647, 0.116291, 0.035808, 1.291757, 0.021312, -1.143904, 0.632109]},
  {'feature': [17, 17, 4, -2, -2, -2, 8, -2, -2], 'threshold': [53.387497, 52.402849, 30.0, -2.0, -2.0, -2.0, 22.5, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, -1, 7, -1, -1], 'right': [6, 5, 4, -1, -1, -1, 8, -1, -1], 'value': [0.001327, 0.003477, 0.001896, 0.042022, -0.893379, 0.940182, -0.096115, -0.225218, -1.079911]},
  {'feature': [17, -2, 17, -2, 21, -2, -2], 'threshold': [30.975628, -2.0, 32.933214, -2.0, 0.211599, -2.0, -2.0], 'left': [1, -1, 3, -1, 5, -1, -1], 'right': [2, -1, 4, -1, 6, -1, -1], 'value': [0.002673, -0.96134, 0.003918, 0.988283, 0.002755, -0.643293, 0.096652]},
  {'feature': [6, 14, -2, 16, -2, -2, 16, 17, -2, -2, -2], 'threshold': [31.5, -49.5, -2.0, 48.974051, -2.0, -2.0, 56.826591, 48.883087, -2.0, -2.0, -2.0], 'left': [1, 2, -1, 4, -1, -1, 7, 8, -1, -1, -1], 'right': [6, 3, -1, 5, -1, -1, 10, 9, -1, -1, -1], 'value': [-0.001435, -0.062644, -1.28917, -0.037661, -0.01669, -0.498168, 0.001782, 0.000576, 0.042245, -0.329453, 1.072328]},
  {'feature': [17, 4, 17, -2, -2, 9, -2, -2, 15, 13, -2, -2, 21, -2, -2], 'threshold': [42.4713, 8.5, 38.589582, -2.0, -2.0, 25.0, -2.0, -2.0, -24.5, -8.5, -2.0, -2.0, 0.248517, -2.0, -2.0], 'left': [1, 2, 3, -1, -1, 6, -1, -1, 9, 10, -1, -1, 13, -1, -1], 'right': [8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1], 'value': [-0.00267, -0.01435, 0.01312, 2.639183, -0.041112, -0.029894, -0.250924, -0.944272, 0.005972, -0.011922, -0.105282, -1.021099, 0.025112, 0.566659, 0.061611]},
]

def _gbc_4p_predict(feat_vec):
    """feat_vec: list of floats in GBC_4P_COLS order. Returns P(win)."""
    score = GBC_4P_INIT
    for tree in GBC_4P_TREES:
        node = 0
        feat  = tree['feature']
        thr   = tree['threshold']
        left  = tree['left']
        right = tree['right']
        val   = tree['value']
        while feat[node] != -2:
            if feat_vec[feat[node]] <= thr[node]:
                node = left[node]
            else:
                node = right[node]
        score += GBC_4P_LR * val[node]
    import math
    return 1.0 / (1.0 + math.exp(-score))



def _gbc_feat_vec(world):
    """23-feature vector matching FEATURE_COLS in generate_training_data_v2."""
    my_p  = world.my_planets
    en_p  = world.enemy_planets
    neu_p = world.neutral_planets
    my_fl = [f for f in world.fleets if f.owner == world.player]
    en_fl = [f for f in world.fleets if f.owner not in (-1, world.player)]
    my_sp = sum(int(p.ships) for p in my_p)
    en_sp = sum(int(p.ships) for p in en_p)
    my_st = sum(int(f.ships) for f in my_fl)
    en_st = sum(int(f.ships) for f in en_fl)
    my_pr = sum(int(p.production) for p in my_p)
    en_pr = sum(int(p.production) for p in en_p)
    my_tot = my_sp + my_st
    en_tot = en_sp + en_st
    nmp = len(my_p); nep = len(en_p)
    def _c(ps):
        if not ps: return 0.0
        return sum(math.hypot(p.x - _GBC_CENTER, p.y - _GBC_CENTER) for p in ps) / len(ps)
    return [
        world.step, max(0, 500 - world.step),
        nmp, nep, len(neu_p),
        my_sp, en_sp, my_st, en_st,
        my_pr, en_pr, my_tot, en_tot,
        nmp - nep, my_tot - en_tot, my_pr - en_pr,
        _c(my_p), _c(en_p), len(my_fl), len(en_fl),
        my_pr  / (my_pr  + en_pr  + 1e-6),
        my_tot / (my_tot + en_tot + 1e-6),
        nmp    / (nmp    + nep    + 1e-6),
    ]


def _gbc_delta(base, tgt, required, world):
    """Win-prob improvement from hammer-capturing tgt. base = _gbc_feat_vec(world)."""
    is_enemy = tgt.owner not in (-1, world.player)
    prod = int(tgt.production); tships = int(tgt.ships)
    f = base[:]
    # idx: 2=my_pl,3=en_pl,4=neu,5=my_sp,6=en_sp,7=my_st,9=my_pr,10=en_pr,
    #      11=my_tot,12=en_tot,13=pl_diff,14=sh_diff,15=pr_diff,
    #      20=prod_ratio,21=ship_ratio,22=planet_ratio
    f[2] += 1
    if is_enemy: f[3] = max(0, f[3] - 1)
    else:        f[4] = max(0, f[4] - 1)
    f[9] += prod
    if is_enemy: f[10] = max(0, f[10] - prod)
    f[7] = max(0, f[7] - required)
    f[5] += 1
    if is_enemy:
        f[6]  = max(0, f[6]  - tships)
        f[12] = max(0, f[12] - tships)
    f[11] = f[5] + f[7]
    f[13] = f[2] - f[3]
    f[14] = f[11] - f[12]
    f[15] = f[9]  - f[10]
    f[20] = f[9]  / (f[9]  + f[10] + 1e-6)
    f[21] = f[11] / (f[11] + f[12] + 1e-6)
    f[22] = f[2]  / (f[2]  + f[3]  + 1e-6)
    return _gbc_v2_predict(f) - _gbc_v2_predict(base)
# ────────────────────────────────────────────────────────────────────────────

def _gbc_4p_delta(base, tgt, required, world):
    """Win-prob improvement from hammer-capturing tgt. Uses 4P-trained model."""
    is_enemy = tgt.owner not in (-1, world.player)
    prod = int(tgt.production); tships = int(tgt.ships)
    f = base[:]
    f[2] += 1
    if is_enemy: f[3] = max(0, f[3] - 1)
    else:        f[4] = max(0, f[4] - 1)
    f[9] += prod
    if is_enemy: f[10] = max(0, f[10] - prod)
    f[7] = max(0, f[7] - required)
    f[5] += 1
    if is_enemy:
        f[6]  = max(0, f[6]  - tships)
        f[12] = max(0, f[12] - tships)
    f[11] = f[5] + f[7]
    f[13] = f[2] - f[3]
    f[14] = f[11] - f[12]
    f[15] = f[9]  - f[10]
    f[20] = f[9]  / (f[9]  + f[10] + 1e-6)
    f[21] = f[11] / (f[11] + f[12] + 1e-6)
    f[22] = f[2]  / (f[2]  + f[3]  + 1e-6)
    return _gbc_4p_predict(f) - _gbc_4p_predict(base)



def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def fleet_speed(ships):
    if ships <= 1:
        return 1.0
    ratio = math.log(ships) / math.log(1000.0)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 + (MAX_SPEED - 1.0) * (ratio ** 1.5)


def orbital_radius(p):
    return dist(p.x, p.y, CENTER_X, CENTER_Y)


def is_static_planet(p):
    return orbital_radius(p) + p.radius >= ROTATION_LIMIT


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    seg_sq = dx * dx + dy * dy
    if seg_sq <= 1e-9:
        return dist(px, py, x1, y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_sq))
    return dist(px, py, x1 + t * dx, y1 + t * dy)


def segment_hits_sun(x1, y1, x2, y2):
    return point_to_segment_distance(CENTER_X, CENTER_Y, x1, y1, x2, y2) < SUN_R + SUN_SAFETY


def launch_point(sx, sy, sr, angle):
    c = sr + LAUNCH_CLEARANCE
    return sx + math.cos(angle) * c, sy + math.sin(angle) * c


def safe_geometry(sx, sy, sr, tx, ty, tr):
    angle = math.atan2(ty - sy, tx - sx)
    lx, ly = launch_point(sx, sy, sr, angle)
    hit_d = max(0.0, dist(sx, sy, tx, ty) - (sr + LAUNCH_CLEARANCE) - tr)
    ex = lx + math.cos(angle) * hit_d
    ey = ly + math.sin(angle) * hit_d
    if segment_hits_sun(lx, ly, ex, ey):
        return None
    return angle, hit_d


def estimate_arrival(sx, sy, sr, tx, ty, tr, ships):
    safe = safe_geometry(sx, sy, sr, tx, ty, tr)
    if safe is None:
        return None
    angle, total_d = safe
    turns = max(1, int(math.ceil(total_d / fleet_speed(max(1, ships)))))
    return angle, turns


def predict_planet_position(planet, initial_by_id, ang_vel, turns):
    init = initial_by_id.get(planet.id)
    if init is None:
        return planet.x, planet.y
    r = dist(init.x, init.y, CENTER_X, CENTER_Y)
    if r + init.radius >= ROTATION_LIMIT:
        return planet.x, planet.y
    cur = math.atan2(planet.y - CENTER_Y, planet.x - CENTER_X)
    new = cur + ang_vel * turns
    return CENTER_X + r * math.cos(new), CENTER_Y + r * math.sin(new)


R4_BEHIND_SUN_WAIT_ENABLED = True
R4_FUTURE_HORIZON = 10   


def predict_comet_position(planet_id, comets, turns):
    for group in comets:
        pids = group.get("planet_ids", []) if isinstance(group, dict) else []
        if planet_id not in pids:
            continue
        idx = pids.index(planet_id)
        paths = group.get("paths", []) if isinstance(group, dict) else []
        path_index = group.get("path_index", 0) if isinstance(group, dict) else 0
        if idx >= len(paths):
            return None
        path = paths[idx]
        future_idx = int(path_index) + int(turns)
        if 0 <= future_idx < len(path):
            return float(path[future_idx][0]), float(path[future_idx][1])
        return None
    return None


def predict_target_position(target, world, turns):
    if target.id in world.comet_ids:
        pos = predict_comet_position(target.id, world.comets, turns)
        if pos is not None:
            return pos
    return predict_planet_position(target, world.initial_by_id, world.ang_vel, turns)


AIM_MAX_ITERS = 6          
AIM_CONVERGE_TURNS = 2
AIM_CONVERGE_DIST = 0.6


def aim_at_target(src, target, ships, initial_by_id, ang_vel, world=None):
    est = estimate_arrival(src.x, src.y, src.radius, target.x, target.y, target.radius, ships)
    if est is None and R4_BEHIND_SUN_WAIT_ENABLED and world is not None:
        for future_t in range(2, R4_FUTURE_HORIZON, 2):
            if target.id in world.comet_ids:
                pos = predict_comet_position(target.id, world.comets, future_t)
            else:
                init = initial_by_id.get(target.id)
                if init is None:
                    pos = None
                elif dist(init.x, init.y, CENTER_X, CENTER_Y) + init.radius >= ROTATION_LIMIT:
                    pos = None  
                else:
                    pos = predict_planet_position(target, initial_by_id, ang_vel, future_t)
            if pos is None:
                continue
            est = estimate_arrival(src.x, src.y, src.radius, pos[0], pos[1], target.radius, ships)
            if est is not None:
                break
    if est is None:
        return None
    
    is_comet = world is not None and target.id in world.comet_ids
    if not is_comet:
        init = initial_by_id.get(target.id)
        if init is None:
            return est
        if dist(init.x, init.y, CENTER_X, CENTER_Y) + init.radius >= ROTATION_LIMIT:
            return est

    angle, turns = est
    tx, ty = target.x, target.y
    for _ in range(AIM_MAX_ITERS):
        if is_comet:
            pos = predict_comet_position(target.id, world.comets, turns)
            if pos is None:
                return None
            ntx, nty = pos
        else:
            ntx, nty = predict_planet_position(target, initial_by_id, ang_vel, turns)
        nest = estimate_arrival(src.x, src.y, src.radius, ntx, nty, target.radius, ships)
        if nest is None:
            return None
        nangle, nturns = nest
        if (abs(ntx - tx) < AIM_CONVERGE_DIST
                and abs(nty - ty) < AIM_CONVERGE_DIST
                and abs(nturns - turns) <= AIM_CONVERGE_TURNS):
            return nangle, nturns
        angle, turns = nangle, nturns
        tx, ty = ntx, nty
    return None


# [COUNCIL] fleet_target_planet caching.
# This function is O(T×P) per fleet and was called from World.__init__,
# forward_project, and _build_multiprong_attack without any memoization.
# Cache by (fleet_id, step, planet_count) — invalidated each turn automatically
# since step advances. On boards with 80 fleets × 20 orbital planets this
# reduces ~176,000 operations to a dict lookup for repeated calls.
_fleet_target_cache = {}   # (fleet_id, step) -> (planet_id_or_None, eta_or_None)
_fleet_target_cache_step = -1


def fleet_target_planet(fleet, planets, initial_by_id=None, ang_vel=0.0,
                        _cache_step=None):
    global _fleet_target_cache, _fleet_target_cache_step
    # Invalidate cache when step advances
    if _cache_step is not None and _cache_step != _fleet_target_cache_step:
        _fleet_target_cache.clear()
        _fleet_target_cache_step = _cache_step

    cache_key = (int(fleet.id), _cache_step)
    if cache_key in _fleet_target_cache and _cache_step is not None:
        pid, eta = _fleet_target_cache[cache_key]
        if pid is None:
            return None, None
        for p in planets:
            if p.id == pid:
                return p, eta
        return None, None

    result_planet, result_eta = _fleet_target_planet_impl(
        fleet, planets, initial_by_id, ang_vel
    )

    if _cache_step is not None:
        _fleet_target_cache[cache_key] = (
            result_planet.id if result_planet else None,
            result_eta,
        )

    return result_planet, result_eta


def _fleet_target_planet_impl(fleet, planets, initial_by_id=None, ang_vel=0.0):
    """Core fleet_target_planet logic (uncached implementation)."""
    dx_dir = math.cos(fleet.angle)
    dy_dir = math.sin(fleet.angle)
    speed = fleet_speed(fleet.ships)

    def _is_orbital(p):
        if initial_by_id is None:
            return False
        init = initial_by_id.get(p.id)
        if init is None:
            return False
        return dist(init.x, init.y, CENTER_X, CENTER_Y) + init.radius < ROTATION_LIMIT

    best_p, best_t = None, float(SIM_HORIZON) + 1.0

    for p in planets:
        if _is_orbital(p):
            continue
        dx = p.x - fleet.x
        dy = p.y - fleet.y
        proj = dx * dx_dir + dy * dy_dir
        if proj < 0:
            continue
        perp_sq = dx * dx + dy * dy - proj * proj
        rr = p.radius * p.radius
        if perp_sq >= rr:
            continue
        hit_d = max(0.0, proj - math.sqrt(max(0.0, rr - perp_sq)))
        t = hit_d / speed
        if t <= SIM_HORIZON and t < best_t:
            best_t, best_p = t, p

    if initial_by_id is not None:
        best_dsq = None
        max_t = int(math.ceil(min(best_t, float(SIM_HORIZON))))
        for t in range(1, max_t + 1):
            fx = fleet.x + dx_dir * speed * t
            fy = fleet.y + dy_dir * speed * t
            for p in planets:
                if not _is_orbital(p):
                    continue
                px, py = predict_planet_position(p, initial_by_id, ang_vel, t)
                rr = p.radius * p.radius
                dsq = (fx - px) ** 2 + (fy - py) ** 2
                if dsq < rr:
                    if t < best_t or (t == best_t and (best_dsq is None or dsq < best_dsq)):
                        best_t, best_p, best_dsq = float(t), p, dsq
            if best_p is not None and best_t <= t:
                break

    if best_p is None:
        return None, None
    return best_p, max(1, int(math.ceil(best_t)))


def garrison_at_arrival(target, travel_turns):
    if target.owner == -1:
        return int(target.ships)  
    return int(target.ships) + int(target.production) * int(travel_turns)


def needed_to_capture(target, travel_turns):
    return garrison_at_arrival(target, travel_turns) + 1


EFFECTIVE_GARRISON_ENABLED = True

def effective_garrison_at_arrival(target, travel_turns, world):
    if not EFFECTIVE_GARRISON_ENABLED:
        return target.owner, garrison_at_arrival(target, travel_turns)
    arrivals = world.arrivals_by_planet.get(target.id, [])
    if world.is_2p:
        relevant = sorted(
            ((eta, owner, ships) for eta, owner, ships in arrivals
             if 1 <= eta <= travel_turns and ships > 0 and owner != -1),
            key=lambda x: x[0],
        )
    else:
        relevant = sorted(
            ((eta, owner, ships) for eta, owner, ships in arrivals
             if 1 <= eta <= travel_turns and owner != world.player and ships > 0
             and owner != -1),
            key=lambda x: x[0],
        )
    if not relevant:
        return target.owner, garrison_at_arrival(target, travel_turns)
    owner = int(target.owner)
    ships = int(target.ships)
    prod = max(0, int(target.production))
    last_t = 0
    for eta, fleet_owner, fleet_ships in relevant:
        if owner != -1:
            ships += prod * (eta - last_t)
        if fleet_owner == owner:
            ships += fleet_ships  
        else:
            if fleet_ships > ships:
                owner = int(fleet_owner)
                ships = fleet_ships - ships
            elif fleet_ships < ships:
                ships -= fleet_ships
            else:
                ships = 0  
        last_t = eta
    if owner != -1:
        ships += prod * (travel_turns - last_t)
    return owner, ships


def effective_needed_to_capture(target, travel_turns, world):
    _, defender_ships = effective_garrison_at_arrival(target, travel_turns, world)
    return defender_ships + 1


def collect_arrivals(planet_id, fleets, planets, initial_by_id=None, ang_vel=0.0):
    out = []
    for f in fleets:
        if int(f.ships) <= 0:
            continue
        target, eta = fleet_target_planet(f, planets, initial_by_id, ang_vel)
        if target is None or target.id != planet_id:
            continue
        out.append((eta, int(f.owner), int(f.ships)))
    return out


def compute_planet_reserve(planet, arrivals, player):
    if planet.owner != player:
        return 0, True, 0, None

    prod = max(0, int(planet.production))
    ships_now = max(0, int(planet.ships))
    if prod > 0:
        absorb_window = max(1, ships_now // prod)
    else:
        absorb_window = SIM_HORIZON

    hostile_in_window = 0
    for eta, owner, ships in arrivals:
        if ships <= 0 or owner == player or owner == -1:
            continue
        if int(eta) <= absorb_window:
            hostile_in_window += int(ships)
    
    absorb_min_threat = max(1, min(ABSORB_MIN_THREAT, ships_now // 3))
    skip_in_window_hostiles = hostile_in_window < absorb_min_threat

    friendly_events = defaultdict(int)
    hostile_by_owner = defaultdict(lambda: defaultdict(int))
    for eta, owner, ships in arrivals:
        if ships <= 0:
            continue
        if owner == player:
            friendly_events[eta] += ships
        elif owner == -1:
            continue
        else:
            if skip_in_window_hostiles and int(eta) <= absorb_window:
                continue
            hostile_by_owner[eta][owner] += int(ships)

    events = defaultdict(int)
    for eta, ships in friendly_events.items():
        events[eta] += ships
    for eta, owner_totals in hostile_by_owner.items():
        sorted_h = sorted(owner_totals.values(), reverse=True)
        if len(sorted_h) == 1:
            survivor = sorted_h[0]
        elif sorted_h[0] == sorted_h[1]:
            survivor = 0
        else:
            survivor = sorted_h[0] - sorted_h[1]
        events[eta] -= survivor

    if not events:
        return 0, True, 0, None

    growth = int(planet.production)
    bal = int(planet.ships)
    last_t = 0
    min_bal = bal
    deadline = None

    for turn in sorted(events):
        bal += growth * (turn - last_t)
        bal += events[turn]
        if bal < min_bal:
            min_bal = bal
        if bal < ABSORB_PROJECTION_MARGIN and deadline is None:
            deadline = turn
        last_t = turn

    if min_bal >= ABSORB_PROJECTION_MARGIN:
        excess = min_bal - ABSORB_PROJECTION_MARGIN
        reserve = max(0, int(planet.ships) - excess)
        return reserve, True, 0, None

    deficit = ABSORB_PROJECTION_MARGIN - min_bal
    return int(planet.ships), False, int(deficit), deadline


def forward_project(world, our_capture_target=None, our_capture_turn=None,
                    our_capture_ships=None, horizon=20,
                    project_opponent_moves=False,
                    opponent_emit_fraction=0.4,
                    snapshot_turns=None):
    by_pid = defaultdict(list)
    for pid, arrs in world.arrivals_by_planet.items():
        for eta, owner, ships in arrs:
            if 0 < eta <= horizon:
                by_pid[pid].append((int(eta), int(owner), int(ships)))

    if our_capture_target is not None and our_capture_turn is not None:
        by_pid[our_capture_target].append(
            (int(our_capture_turn), int(world.player), int(our_capture_ships))
        )

    state = {}
    for p in world.planets:
        state[p.id] = [int(p.owner), int(p.ships), int(p.production)]

    planet_pos_map = {p.id: (float(p.x), float(p.y)) for p in world.planets}

    prod_by_pid = {p.id: max(0, int(p.production)) for p in world.planets}

    snapshots = {} if snapshot_turns else None
    snapshot_set = set(snapshot_turns) if snapshot_turns else None
    for t in range(1, horizon + 1):
        for pid, st in state.items():
            if st[0] != -1:
                st[1] += st[2]
        
        if project_opponent_moves and t % 4 == 0:
            for pid, st in state.items():
                if st[0] == -1 or st[1] < 10:
                    continue
                src_x, src_y = planet_pos_map[pid]
                src_owner = st[0]
                best_d = float("inf")
                best_op = None
                for opid, ost in state.items():
                    if opid == pid or ost[0] == src_owner:
                        continue
                    ox, oy = planet_pos_map[opid]
                    d = ((src_x - ox) ** 2 + (src_y - oy) ** 2) ** 0.5
                    if d < best_d:
                        best_d, best_op = d, opid
                if best_op is None:
                    continue
                if src_owner == world.player:
                    frac = opponent_emit_fraction * 0.5
                else:
                    frac = opponent_emit_fraction
                emit = int(st[1] * frac)
                if emit < 5:
                    continue
                ratio = math.log(max(2, emit)) / math.log(1000.0)
                speed = 1.0 + (MAX_SPEED - 1.0) * (ratio ** 1.5)
                eta_arrive = max(1, int(math.ceil(best_d / speed)))
                arrival_t = t + eta_arrive
                if arrival_t > horizon:
                    continue
                by_pid[best_op].append((arrival_t, src_owner, emit))
                st[1] -= emit
        
        for pid, arrs in by_pid.items():
            this_turn = [(o, s) for et, o, s in arrs if et == t]
            if not this_turn:
                continue
            st = state[pid]
            defender_owner, garrison = st[0], st[1]
            from_owner = defaultdict(int)
            for o, s in this_turn:
                from_owner[o] += s
            sorted_owners = sorted(from_owner.items(), key=lambda x: -x[1])
            top_owner, top_ships = sorted_owners[0]
            if len(sorted_owners) >= 2:
                second_ships = sorted_owners[1][1]
                if top_ships == second_ships:
                    survivor_ships = 0
                    survivor_owner = -1
                else:
                    survivor_ships = top_ships - second_ships
                    survivor_owner = top_owner
            else:
                survivor_ships = top_ships
                survivor_owner = top_owner
            if survivor_ships > 0:
                if defender_owner == survivor_owner:
                    st[1] = garrison + survivor_ships
                else:
                    new_garrison = garrison - survivor_ships
                    if new_garrison < 0:
                        st[0] = survivor_owner
                        st[1] = -new_garrison
                    else:
                        st[1] = new_garrison
        if snapshot_set is not None and t in snapshot_set:
            snapshots[t] = {pid: (st[0], st[1]) for pid, st in state.items()}

    final = {pid: (st[0], st[1]) for pid, st in state.items()}
    if snapshot_turns is not None:
        return final, snapshots
    return final


def _depth2_penalty(world, our_action, top_opp_actions=2):
    target_id = our_action["target_id"]
    tgt = world.planet_by_id.get(target_id)
    if tgt is None:
        return 0.0
    worst_delta = 0.0
    candidates_evaluated = 0
    for ep in world.planets:
        if ep.owner == world.player or ep.owner == -1:
            continue
        if int(ep.ships) < 9:
            continue
        d = ((tgt.x - ep.x) ** 2 + (tgt.y - ep.y) ** 2) ** 0.5
        if d > 30.0:
            continue
        opp_ships = max(8, int(ep.ships) - 5)
        ratio = math.log(max(2, opp_ships)) / math.log(1000.0)
        speed = 1.0 + (MAX_SPEED - 1.0) * (ratio ** 1.5)
        opp_eta = max(1, int(math.ceil(d / speed)))
        if opp_eta > FWD_SIM_HORIZON + 4:
            continue
        proj = forward_project(
            world,
            our_capture_target=our_action["target_id"],
            our_capture_turn=our_action["arrival_turn"],
            our_capture_ships=our_action["ships"],
            horizon=FWD_SIM_HORIZON + 6,
            project_opponent_moves=True,
            opponent_emit_fraction=0.30,
        )
        end_owner, end_ships = proj.get(target_id, (-1, 0))
        if end_owner != world.player and opp_ships > end_ships:
            worst_delta = min(worst_delta, -opp_ships)
        candidates_evaluated += 1
        if candidates_evaluated >= top_opp_actions:
            break
    return worst_delta


def search_step_action(world, max_per_source=3, max_actions_to_eval=10,
                       use_depth2=False, deadline=None):
    """Depth-1 (optionally depth-2) alpha-beta over step actions.

    [COUNCIL] Added `deadline` parameter: depth-2 penalty computation is
    expensive (calls forward_project per action). We skip it for remaining
    candidates once we're past 70% of the per-call budget to avoid burning
    the main plan_moves deadline.
    """
    actions = generate_step_actions(world, max_per_source=max_per_source)
    if not actions:
        return []
    baseline_score = melis_evaluate(world, our_step_action=None)
    
    apply_decay = world.is_2p
    scored = []
    for act in actions[:max_actions_to_eval]:
        act_score = melis_evaluate(world, our_step_action=act)
        gain = act_score - baseline_score
        if apply_decay and gain > 0:
            gain *= 0.97 ** int(act["arrival_turn"])
        act["score"] = gain
        scored.append(act)
    scored.sort(key=lambda a: (-a["score"], a.get("raw_dist", 0.0)))

    if use_depth2:
        # [COUNCIL] Budget-gated depth-2: only evaluate while we have budget.
        # If deadline is not provided, evaluate top-3 unconditionally (original behaviour).
        for act in scored[:3]:
            if deadline is not None and time.perf_counter() >= deadline * 0.70:
                break
            act["score"] += _depth2_penalty(world, act)
        scored.sort(key=lambda a: (-a["score"], a.get("raw_dist", 0.0)))
    
    if MELIS_SANITY_ENABLED and world.is_2p and scored and scored[0]["score"] < MELIS_SANITY_THETA:
        return []
    return scored


def generate_step_actions(world, max_per_source=3):
    actions = []
    if not world.my_planets:
        return actions
    
    is_opening = world.is_opening
    if is_opening:
        max_travel = world.mode_params.get(
            "expand_max_travel_opening", EXPAND_MAX_TRAVEL_OPENING)
    else:
        max_travel = world.mode_params["expand_max_travel_mid"]

    for src in world.my_planets:
        avail = max(0, int(src.ships))
        if avail < MIN_DISPATCH_SHIPS:
            continue
        targets = []
        for t in world.planets:
            if t.owner == world.player:
                continue
            if not is_targetable(world, t):
                continue
            if _neutral_blocked_by_cap(world, t):
                continue
            raw = dist(src.x, src.y, t.x, t.y)
            if raw / MAX_SPEED > max_travel + 4:
                continue
            targets.append((raw, t))
        targets.sort(key=lambda x: x[0])
        
        if F16_DIVERSITY_ENABLED:
            n_close = min(F16_CLOSEST_PICKS, max_per_source)
            picks = list(targets[:n_close])
            picked_ids = {p[1].id for p in picks}
            extras = [(raw, t) for raw, t in targets if t.id not in picked_ids]
            extras.sort(key=lambda x: (-int(x[1].production), x[0]))
            picks.extend(extras[:F16_PROD_PICKS])
        else:
            picks = targets[:max_per_source]
        for raw, t in picks:
            plan = plan_solo_capture(world, src, t, avail, max_travel)
            if plan is None:
                continue
            angle, turns, ships = plan
            actions.append({
                "target_id": int(t.id),
                "source_id": int(src.id),
                "angle": float(angle),
                "arrival_turn": int(turns),
                "ships": int(ships),
                "raw_dist": float(raw),
            })
    return actions


def melis_evaluate(world, our_step_action=None, horizon=12, future_horizon=8,
                   opp_emit=0.20):
    """Melis full-attack-future evaluator.

    [COUNCIL] Snapshot averaging is now weighted by 1/t (earlier snapshots
    are more reliable; 20-turn projections carry ~5x more cascaded error
    than 4-turn ones). Previously all snapshots had equal weight, allowing
    the noisiest late projection to dominate action ranking.
    """
    target = arrival = ships = None
    if our_step_action is not None:
        target = our_step_action.get("target_id")
        arrival = our_step_action.get("arrival_turn")
        ships = our_step_action.get("ships")
    H = horizon + future_horizon
    n = 2 if world.is_2p else 4
    if FWD_SCORE_AGG_ENABLED:
        snap_turns = tuple(t for t in FWD_SCORE_AGG_TURNS if t <= H)
        if not snap_turns:
            snap_turns = (H,)
        final, snaps = forward_project(
            world,
            our_capture_target=target,
            our_capture_turn=arrival,
            our_capture_ships=ships,
            horizon=H,
            project_opponent_moves=True,
            opponent_emit_fraction=opp_emit,
            snapshot_turns=snap_turns,
        )
        # [COUNCIL] Weighted average: weight = 1/t so turn-4 counts 5x more
        # than turn-20 (1/4 vs 1/20). Prevents late noisy horizons from
        # swamping reliable near-term projections in action selection.
        total = 0.0
        weight_sum = 0.0
        for t in snap_turns:
            snap = snaps.get(t)
            if snap is None:
                continue
            w = 1.0 / t
            total += forward_score(snap, world.player, n, world) * w
            weight_sum += w
        if H not in snap_turns:
            w = 1.0 / H
            total += forward_score(final, world.player, n, world) * w
            weight_sum += w
        return total / max(1e-9, weight_sum)
    state = forward_project(
        world,
        our_capture_target=target,
        our_capture_turn=arrival,
        our_capture_ships=ships,
        horizon=H,
        project_opponent_moves=True,
        opponent_emit_fraction=opp_emit,
    )
    return forward_score(state, world.player, n, world)


def forward_score(state, player, n_seats, world=None):
    n_planets = [0] * n_seats
    n_prod = [0] * n_seats
    n_ships = [0] * n_seats
    for pid, (o, s) in state.items():
        if 0 <= o < n_seats:
            n_ships[o] += s
            n_planets[o] += 1
            if world is not None:
                p = world.planet_by_id.get(pid)
                if p is not None:
                    n_prod[o] += int(p.production)
    if n_seats <= 1:
        return n_ships[player]
    others = [i for i in range(n_seats) if i != player]
    leader_ships = max(n_ships[i] for i in others)
    leader_planets = max(n_planets[i] for i in others)
    leader_prod = max(n_prod[i] for i in others)
    return ((n_ships[player] - leader_ships)
            + 5 * (n_planets[player] - leader_planets)
            + 8 * (n_prod[player] - leader_prod))


class World:
    def __init__(self, obs, inferred_step=None):
        global COALITION_MIN_PER_CONTRIBUTOR, DEFENSE_OVERSEND, PSM_OPENING_TURN, SO1_STATIC_BONUS
        global _fleet_target_cache_step
        self.player = _read(obs, "player", 0)
        obs_step = _read(obs, "step", 0) or 0
        self.step = max(obs_step, inferred_step or 0)
        raw_planets = _read(obs, "planets", []) or []
        raw_fleets = _read(obs, "fleets", []) or []
        raw_init = _read(obs, "initial_planets", []) or []
        self.ang_vel = _read(obs, "angular_velocity", 0.0) or 0.0

        self.planets = [Planet(*p) for p in raw_planets]
        self.fleets = [Fleet(*f) for f in raw_fleets]
        self.initial_by_id = {Planet(*p).id: Planet(*p) for p in raw_init}

        raw_comet_ids = _read(obs, "comet_planet_ids", []) or []
        self.comet_ids = set(int(x) for x in raw_comet_ids)

        self.comet_remaining = {}
        raw_comet_groups = _read(obs, "comets", []) or []
        self.comets = raw_comet_groups
        for grp in raw_comet_groups:
            try:
                idx = int(grp.get("path_index", 0))
                pids = grp.get("planet_ids", []) or []
                paths = grp.get("paths", []) or []
                for i, pid in enumerate(pids):
                    if i < len(paths):
                        rem = max(0, len(paths[i]) - idx)
                        self.comet_remaining[int(pid)] = rem
            except (AttributeError, TypeError, IndexError):
                continue

        self.planet_by_id = {p.id: p for p in self.planets}
        self.my_planets = [p for p in self.planets if p.owner == self.player]
        self.enemy_planets = [p for p in self.planets if p.owner not in (-1, self.player)]
        self.neutral_planets = [p for p in self.planets if p.owner == -1]

        self.remaining_steps = max(1, TOTAL_STEPS - self.step)
        self.is_opening = self.step < PSM_OPENING_TURN
        self.is_late = self.remaining_steps < LATE_FLUSH_REMAINING_TURNS

        self.owner_strength = defaultdict(int)
        self.owner_production = defaultdict(int)
        for p in self.planets:
            if p.owner != -1:
                self.owner_strength[p.owner] += int(p.ships)
                self.owner_production[p.owner] += int(p.production)
        for f in self.fleets:
            self.owner_strength[f.owner] += int(f.ships)

        self.my_prod = self.owner_production.get(self.player, 0)
        self.total_prod = sum(self.owner_production.values())
        self.my_prod_share = (self.my_prod / self.total_prod) if self.total_prod else 0.0
        
        if self.remaining_steps < 80 and self.my_prod_share > 0.55:
            self.is_late = True

        self.leader_id = None
        self.contest_leader = False

        self.owner_planet_count = defaultdict(int)
        for p in self.planets:
            if p.owner not in (-1,):
                self.owner_planet_count[p.owner] += 1
        self.weakest_enemy = None
        self.weakest_enemy_prod_share = 0.0
        if self.total_prod > 0:
            best_score = None
            for owner in self.owner_production.keys():
                if owner in (-1, self.player):
                    continue
                score = (
                    self.owner_production.get(owner, 0) * 0.5
                    + self.owner_strength.get(owner, 0) * 0.3
                    + self.owner_planet_count.get(owner, 0) * 0.2
                )
                if best_score is None or score < best_score:
                    best_score = score
                    self.weakest_enemy = owner
            if self.weakest_enemy is not None:
                their_prod = self.owner_production.get(self.weakest_enemy, 0)
                self.weakest_enemy_prod_share = (
                    their_prod / self.total_prod if self.total_prod else 0.0
                )

        # [COUNCIL] Pass self.step to fleet_target_planet as cache_step so the
        # cache is automatically invalidated each new turn without any explicit
        # clear call. The World constructor populates arrivals_by_planet with
        # cached fleet-target lookups, giving O(1) repeated calls this turn.
        _fleet_target_cache_step  # trigger import
        self.arrivals_by_planet = defaultdict(list)
        for f in self.fleets:
            target, eta = fleet_target_planet(
                f, self.planets, self.initial_by_id, self.ang_vel,
                _cache_step=self.step
            )
            if target is None:
                continue
            self.arrivals_by_planet[target.id].append((eta, int(f.owner), int(f.ships)))

        self.enemy_race_eta = _compute_enemy_race_eta(self) if RACE_ENABLED else {}

        global _game_num_players
        if _game_num_players is None and self.planets:
            _game_num_players = self.num_players
        self.is_2p = (_game_num_players == 2)

        if self.is_2p:
            COALITION_MIN_PER_CONTRIBUTOR = COALITION_MIN_PER_CONTRIBUTOR_2P
            DEFENSE_OVERSEND = DEFENSE_OVERSEND_2P
            PSM_OPENING_TURN = PSM_OPENING_TURN_2P
            SO1_STATIC_BONUS = SO1_STATIC_BONUS_2P
        else:
            COALITION_MIN_PER_CONTRIBUTOR = COALITION_MIN_PER_CONTRIBUTOR_4P
            DEFENSE_OVERSEND = DEFENSE_OVERSEND_4P
            PSM_OPENING_TURN = PSM_OPENING_TURN_4P
            SO1_STATIC_BONUS = SO1_STATIC_BONUS_4P
        
        if LEADER_BASH_ENABLED and not self.is_2p:
            lead_scores = {}
            for owner in self.owner_production.keys():
                if owner == -1:
                    continue
                lead_scores[owner] = (
                    self.owner_strength.get(owner, 0) * 0.5
                    + self.owner_production.get(owner, 0) * 0.5
                )
            if lead_scores:
                top_owner = max(lead_scores, key=lambda k: lead_scores[k])
                self.leader_id = top_owner
                my_score = lead_scores.get(self.player, 0)
                top_score = lead_scores.get(top_owner, 0)
                if (
                    top_owner != self.player
                    and my_score > 0
                    and (top_score / my_score) >= LEADER_BASH_RATIO
                ):
                    self.contest_leader = True

        self.mode = _detect_mode(self) if PERSONALITY_ENABLED else "patient"
        
        if TERMINAL_PHASE_ENABLED and self.remaining_steps < TERMINAL_PHASE_TURNS:
            self.mode = "pressure"
        params_table = MODE_PARAMS_2P if self.is_2p else MODE_PARAMS
        self.mode_params = params_table[self.mode]

        self.stop_expanding_2p = (
            STOP_EXPAND_2P_ENABLED
            and self.is_2p
            and self.step >= STOP_EXPAND_TURN_MIN_2P
            and self.my_prod_share >= STOP_EXPAND_PROD_SHARE_2P
        )

        self.in_combat_contact = False
        if COMBAT_STOP_EXPAND_ENABLED:
            my_ids = {p.id for p in self.my_planets}
            enemy_ids = {p.id for p in self.enemy_planets}
            for pid, arrs in self.arrivals_by_planet.items():
                if pid in my_ids:
                    for _eta, owner, ships in arrs:
                        if owner != self.player and owner != -1 and ships >= COMBAT_CONTACT_MIN_SHIPS:
                            self.in_combat_contact = True
                            break
                elif pid in enemy_ids:
                    for _eta, owner, ships in arrs:
                        if owner == self.player and ships >= COMBAT_CONTACT_MIN_SHIPS:
                            self.in_combat_contact = True
                            break
                if self.in_combat_contact:
                    break
        self.combat_stop_expand = (
            COMBAT_STOP_EXPAND_ENABLED
            and self.in_combat_contact
            and self.step >= COMBAT_STOP_EXPAND_TURN_MIN
            and (not COMBAT_STOP_EXPAND_4P_ONLY or not self.is_2p)
        )

        prod_lag_thresh = (
            PROD_LAG_STOP_EXPAND_THRESH_2P if self.is_2p
            else PROD_LAG_STOP_EXPAND_THRESH_4P
        )
        self.prod_lag_stop_expand = (
            PROD_LAG_STOP_EXPAND_ENABLED
            and self.step >= PROD_LAG_STOP_EXPAND_TURN_MIN
            and self.my_prod_share < prod_lag_thresh
        )

        self.enemy_tempo_stop_expand = (
            ENEMY_TEMPO_STOP_EXPAND_ENABLED
            and self.step >= ENEMY_TEMPO_STOP_EXPAND_TURN_MIN
            and FLEET_INTENT_ENABLED
            and len(_enemy_recently_launched) >= ENEMY_TEMPO_STOP_EXPAND_MIN_LAUNCHES
        )

        self.easy_enemy_stop_expand = False
        if EASY_ENEMY_STOP_EXPAND_ENABLED and self.step >= EASY_ENEMY_STOP_EXPAND_TURN_MIN:
            easy_count = 0
            for ep in self.enemy_planets:
                if int(ep.ships) > EASY_ENEMY_MAX_GARRISON:
                    continue
                for mp in self.my_planets:
                    if dist(mp.x, mp.y, ep.x, ep.y) <= EASY_ENEMY_MAX_DIST:
                        easy_count += 1
                        break
                if easy_count >= EASY_ENEMY_MIN_COUNT:
                    break
            self.easy_enemy_stop_expand = (easy_count >= EASY_ENEMY_MIN_COUNT)

        self.stockpile_stop_expand = False
        if STOCKPILE_STOP_EXPAND_ENABLED and self.step >= STOCKPILE_STOP_EXPAND_TURN_MIN:
            for mp in self.my_planets:
                if int(mp.ships) >= STOCKPILE_STOP_EXPAND_MAX_GARRISON:
                    self.stockpile_stop_expand = True
                    break

        self.prod_lead_stop_expand_4p = (
            PROD_LEAD_STOP_EXPAND_4P_ENABLED
            and not self.is_2p
            and self.step >= PROD_LEAD_STOP_EXPAND_4P_TURN_MIN
            and self.my_prod_share >= PROD_LEAD_STOP_EXPAND_4P_THRESH
        )

        self.turn_cutoff_stop_expand = (
            TURN_CUTOFF_STOP_EXPAND_ENABLED
            and self.step >= TURN_CUTOFF_STOP_EXPAND_TURN
        )

        self.neutral_saturation_stop_expand = False
        if (
            NEUTRAL_SATURATION_STOP_EXPAND_ENABLED
            and self.step >= NEUTRAL_SATURATION_TURN_MIN
            and (not NEUTRAL_SATURATION_2P_ONLY or self.is_2p)
        ):
            any_cheap = False
            for n in self.planets:
                if n.owner != -1 or n.id in self.comet_ids:
                    continue
                if int(n.ships) > NEUTRAL_SATURATION_CHEAP_GARRISON:
                    continue
                for mp in self.my_planets:
                    if dist(mp.x, mp.y, n.x, n.y) <= NEUTRAL_SATURATION_REACH_DIST:
                        any_cheap = True
                        break
                if any_cheap:
                    break
            self.neutral_saturation_stop_expand = not any_cheap

        self.stop_expand_lax = (
            self.combat_stop_expand
            or self.prod_lag_stop_expand
            or self.enemy_tempo_stop_expand
            or self.easy_enemy_stop_expand
            or self.neutral_saturation_stop_expand
            or self.stockpile_stop_expand
        )

        self.survival_mode_4p = (
            SURVIVAL_MODE_4P_ENABLED
            and not self.is_2p
            and len(self.my_planets) <= SURVIVAL_MODE_4P_PLANET_MAX
            and self.step >= SURVIVAL_MODE_4P_TURN_MIN
        )

        self.focus_enemy_2p = None
        if F14_4A_2P_FOCUS_ENABLED and self.is_2p:
            for o in self.owner_production.keys():
                if o not in (-1, self.player):
                    self.focus_enemy_2p = o
                    break

    @property
    def num_players(self):
        owners = set()
        for p in self.planets:
            if p.owner != -1:
                owners.add(p.owner)
        for f in self.fleets:
            owners.add(f.owner)
        return max(2, len(owners))


def _read(obs, key, default=None):
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def _compute_enemy_race_eta(world):
    out = {}
    if not world.neutral_planets:
        return out

    for n in world.neutral_planets:
        needed = int(n.ships) + 1
        earliest = None

        for eta, owner, ships in world.arrivals_by_planet.get(n.id, []):
            if owner == world.player or owner == -1:
                continue
            if ships < needed:
                continue
            if earliest is None or eta < earliest:
                earliest = int(eta)

        for ep in world.enemy_planets:
            if int(ep.ships) < needed:
                continue
            d = dist(ep.x, ep.y, n.x, n.y)
            if d > RACE_MAX_NEUTRAL_DIST:
                continue
            if safe_geometry(ep.x, ep.y, ep.radius, n.x, n.y, n.radius) is None:
                continue
            min_turns = max(1, int(math.ceil(d / fleet_speed(int(ep.ships)))))
            if min_turns > RACE_HORIZON_TURNS:
                continue
            if earliest is None or min_turns < earliest:
                earliest = min_turns

        if earliest is not None:
            out[n.id] = earliest
    return out


def _detect_mode(world):
    """Pick a personality mode from the current snapshot.

    [COUNCIL] Bug fix: the original code always returned "pressure" for 2P,
    making the entire patience/escalation system dead code. Now the computed
    `intended` mode flows through the streak-based escalation:
    - streak < TWO_P_PATIENT_NUDGE_TURNS  → use intended mode
    - streak >= TWO_P_PATIENT_NUDGE_TURNS  → escalate to opportunistic
    - streak >= TWO_P_PATIENT_ESCALATE_TURNS → escalate to pressure
    This unlocks the TWO_P_PATIENT_NUDGE_TURNS / TWO_P_PATIENT_ESCALATE_TURNS
    logic that was designed but never ran.
    """
    if world.is_opening:
        if world.is_2p:
            _record_2p_progress(world.my_prod_share, intended_patient=True, reset=True)
        return "patient"

    enemy_planet_ships = 0
    for p in world.planets:
        if p.owner not in (-1, world.player):
            enemy_planet_ships += int(p.ships)
    enemy_fleet_ships = 0
    for f in world.fleets:
        if f.owner != world.player and f.owner != -1:
            enemy_fleet_ships += int(f.ships)

    enemy_total = enemy_planet_ships + enemy_fleet_ships
    if enemy_total < PERSONALITY_MIN_SAMPLE:
        intended = "patient"
    else:
        aggression = enemy_fleet_ships / float(enemy_total)
        if aggression >= PERSONALITY_AGG_HIGH:
            intended = "pressure"
        elif aggression <= PERSONALITY_AGG_LOW:
            intended = "opportunistic"
        else:
            intended = "patient"

    if not world.is_2p:
        return intended

    # [COUNCIL] 2P escalation: record progress and escalate based on streak.
    # Previously this was: _record_2p_progress(...); return "pressure"  <-- bug
    _record_2p_progress(world.my_prod_share, intended_patient=(intended == "patient"))
    streak = _2p_patient_streak
    if streak >= TWO_P_PATIENT_ESCALATE_TURNS:
        return "pressure"
    elif streak >= TWO_P_PATIENT_NUDGE_TURNS:
        return "opportunistic"
    return intended


def _record_2p_progress(my_prod_share, intended_patient, reset=False):
    global _2p_patient_streak, _2p_prod_share_history
    if reset:
        _2p_patient_streak = 0
        _2p_prod_share_history = []
        return 0
    _2p_prod_share_history.append(float(my_prod_share))
    if len(_2p_prod_share_history) > TWO_P_PROD_SHARE_HISTORY:
        _2p_prod_share_history.pop(0)
    if not intended_patient:
        _2p_patient_streak = 0
        return 0
    if len(_2p_prod_share_history) >= TWO_P_PROD_SHARE_HISTORY:
        delta = _2p_prod_share_history[-1] - _2p_prod_share_history[0]
        if delta > TWO_P_PROD_SHARE_PROGRESS_EPS:
            _2p_patient_streak = 0
            return 0
    _2p_patient_streak += 1
    return _2p_patient_streak


_agent_step = 0
_hammer_plan = None
_planet_idle_counts = {}
_promoted_stockpiles = set()
_game_num_players = None
_2p_patient_streak = 0          
_2p_prod_share_history = []     

_neutral_prev_ships = {}
_neutral_wounded = set()

_enemy_prev_ships = {}
_enemy_recently_launched = set()

_planet_prev_owner = {}        
_freshly_lost_planets = set()  

_freshly_captured_planets = set()  
_planet_capture_age = {}       

_pending_commitments = []

_snipe_commitments = []
_snipe_total = 0   # diagnostics: snipes fired across the process lifetime
_snipe_log = []    # diagnostics: per-snipe records for offline analysis

OPP_PROFILE_WINDOW = 20
_opp_profile = {}


def _update_opp_profile_4p(world):
    global _opp_profile
    if world.step == 0:
        _opp_profile = {}

    plan_ships = defaultdict(int)
    plan_max = defaultdict(int)
    plan_count = defaultdict(int)
    for p in world.planets:
        if p.owner == world.player or p.owner == -1:
            continue
        s = int(p.ships)
        plan_ships[p.owner] += s
        plan_count[p.owner] += 1
        if s > plan_max[p.owner]:
            plan_max[p.owner] = s
    fleet_ships = defaultdict(int)
    for f in world.fleets:
        if f.owner == world.player or f.owner == -1:
            continue
        fleet_ships[f.owner] += int(f.ships)

    enemies = set(plan_count.keys()) | set(fleet_ships.keys())
    for owner in enemies:
        ps = plan_ships.get(owner, 0)
        fs = fleet_ships.get(owner, 0)
        total = ps + fs
        emit = (fs / total) if total else 0.0
        prof = _opp_profile.setdefault(owner, {"emit": [], "stock": [], "plan": []})
        prof["emit"].append(emit)
        prof["stock"].append(plan_max.get(owner, 0))
        prof["plan"].append(plan_count.get(owner, 0))
        if len(prof["emit"]) > OPP_PROFILE_WINDOW:
            prof["emit"] = prof["emit"][-OPP_PROFILE_WINDOW:]
            prof["stock"] = prof["stock"][-OPP_PROFILE_WINDOW:]
            prof["plan"] = prof["plan"][-OPP_PROFILE_WINDOW:]

    world.opp_profile = _opp_profile


def predict_defender_at_arrival(world, target, arrival_turn):
    arrivals = world.arrivals_by_planet.get(target.id, [])
    by_turn = defaultdict(list)
    for eta, owner, ships in arrivals:
        if ships <= 0:
            continue
        by_turn[eta].append((owner, ships))

    owner = target.owner
    garrison = float(target.ships)
    horizon = max(1, int(math.ceil(arrival_turn)))

    for t in range(1, horizon + 1):
        if owner != -1:
            garrison += int(target.production)
        group = by_turn.get(t)
        if group:
            owner, garrison = _resolve_combat(owner, garrison, group)
    return owner, max(0.0, garrison)


def _resolve_combat(owner, garrison, arrivals):
    by_owner = defaultdict(int)
    for o, s in arrivals:
        by_owner[o] += s
    if not by_owner:
        return owner, max(0.0, garrison)
    sorted_o = sorted(by_owner.items(), key=lambda kv: kv[1], reverse=True)
    top_o, top_s = sorted_o[0]
    if len(sorted_o) > 1 and top_s == sorted_o[1][1]:
        survivor_o, survivor_s = -1, 0
    elif len(sorted_o) > 1:
        survivor_o, survivor_s = top_o, top_s - sorted_o[1][1]
    else:
        survivor_o, survivor_s = top_o, top_s

    if survivor_s <= 0:
        return owner, max(0.0, garrison)
    if owner == survivor_o:
        return owner, garrison + survivor_s
    garrison -= survivor_s
    if garrison < 0:
        return survivor_o, -garrison
    return owner, garrison


FWD_SIM_ENABLED = os.environ.get("V128_FWD_SIM", "1") != "0"
FWD_LOOKAHEAD_HORIZON = 25
FWD_LOOKAHEAD_TOP_K = 6          
FWD_MAX_FLEETS = 80


def _fwd_clone(world):
    planet_ids = []
    planet_owner = {}
    planet_ships = {}
    planet_xy = {}
    planet_radius = {}
    planet_prod = {}
    orbital = {}
    for p in world.planets:
        if p.id in world.comet_ids:
            continue
        planet_ids.append(p.id)
        planet_owner[p.id] = int(p.owner)
        planet_ships[p.id] = float(p.ships)
        planet_xy[p.id] = (float(p.x), float(p.y))
        planet_radius[p.id] = float(p.radius)
        planet_prod[p.id] = int(p.production)
        init = world.initial_by_id.get(p.id)
        if init is not None:
            dx = float(init.x) - CENTER_X
            dy = float(init.y) - CENTER_Y
            r = math.sqrt(dx * dx + dy * dy)
            if r + p.radius < ROTATION_LIMIT:
                orbital[p.id] = (r, math.atan2(dy, dx))
    fleets = []
    next_id = 0
    for f in world.fleets:
        fleets.append([int(f.id), int(f.owner), float(f.x), float(f.y),
                       float(f.angle), int(f.ships)])
        next_id = max(next_id, int(f.id))
    return {
        "planet_ids": planet_ids,
        "planet_owner": planet_owner,
        "planet_ships": planet_ships,
        "planet_xy": planet_xy,
        "planet_radius": planet_radius,
        "planet_prod": planet_prod,
        "orbital": orbital,
        "fleets": fleets,
        "step": int(world.step),
        "ang_vel": float(world.ang_vel),
        "next_fleet_id": next_id + 1,
    }


def _fwd_inject_launch(state, src_id, angle, ships):
    if src_id not in state["planet_xy"]:
        return False
    if state["planet_ships"][src_id] < ships:
        return False
    state["planet_ships"][src_id] -= ships
    radius = state["planet_radius"][src_id]
    sx, sy = state["planet_xy"][src_id]
    fx = sx + math.cos(angle) * (radius + 0.1)
    fy = sy + math.sin(angle) * (radius + 0.1)
    owner = state["planet_owner"][src_id]
    state["fleets"].append([state["next_fleet_id"], int(owner), fx, fy,
                            float(angle), int(ships)])
    state["next_fleet_id"] += 1
    return True


def _fwd_step(state):
    for pid in state["planet_ids"]:
        if state["planet_owner"][pid] != -1:
            state["planet_ships"][pid] += state["planet_prod"][pid]
    combat = {pid: [] for pid in state["planet_ids"]}
    surviving = []
    radii = state["planet_radius"]
    xy = state["planet_xy"]
    pids = state["planet_ids"]
    for fl in state["fleets"]:
        ships = fl[5]
        if ships <= 0:
            continue
        speed = fleet_speed(ships)
        old_x, old_y = fl[2], fl[3]
        new_x = old_x + math.cos(fl[4]) * speed
        new_y = old_y + math.sin(fl[4]) * speed
        fl[2] = new_x
        fl[3] = new_y
        if not (0.0 <= new_x <= BOARD and 0.0 <= new_y <= BOARD):
            continue
        if point_to_segment_distance(CENTER_X, CENTER_Y, old_x, old_y, new_x, new_y) < SUN_R:
            continue
        hit_pid = -1
        for pid in pids:
            px, py = xy[pid]
            if point_to_segment_distance(px, py, old_x, old_y, new_x, new_y) < radii[pid]:
                hit_pid = pid
                break
        if hit_pid >= 0:
            combat[hit_pid].append(fl)
        else:
            surviving.append(fl)
    state["step"] += 1
    new_xy = dict(xy)
    for pid, (r, a0) in state["orbital"].items():
        a = a0 + state["ang_vel"] * state["step"]
        new_xy[pid] = (CENTER_X + r * math.cos(a), CENTER_Y + r * math.sin(a))
    still = []
    for fl in surviving:
        hit_pid = -1
        for pid in pids:
            if pid not in state["orbital"]:
                continue
            old_px, old_py = xy[pid]
            new_px, new_py = new_xy[pid]
            if point_to_segment_distance(fl[2], fl[3], old_px, old_py, new_px, new_py) < radii[pid]:
                hit_pid = pid
                break
        if hit_pid >= 0:
            combat[hit_pid].append(fl)
        else:
            still.append(fl)
    state["planet_xy"] = new_xy
    state["fleets"] = still
    for pid, arrivals in combat.items():
        if not arrivals:
            continue
        per_owner = defaultdict(int)
        for fl in arrivals:
            per_owner[fl[1]] += fl[5]
        sorted_o = sorted(per_owner.items(), key=lambda kv: kv[1], reverse=True)
        top_o, top_s = sorted_o[0]
        if len(sorted_o) > 1:
            second_s = sorted_o[1][1]
            if top_s == second_s:
                surv_s, surv_o = 0, -1
            else:
                surv_s, surv_o = top_s - second_s, top_o
        else:
            surv_o, surv_s = top_o, top_s
        if surv_s > 0:
            cur = state["planet_owner"][pid]
            if cur == surv_o:
                state["planet_ships"][pid] += surv_s
            else:
                state["planet_ships"][pid] -= surv_s
                if state["planet_ships"][pid] < 0:
                    state["planet_owner"][pid] = surv_o
                    state["planet_ships"][pid] = -state["planet_ships"][pid]


def _fwd_simulate(state, horizon):
    for _ in range(horizon):
        if len(state["fleets"]) > FWD_MAX_FLEETS:
            break
        _fwd_step(state)
    return state


def _fwd_my_score(state, player):
    total = 0.0
    for pid in state["planet_ids"]:
        if state["planet_owner"][pid] == player:
            total += state["planet_ships"][pid]
    for fl in state["fleets"]:
        if fl[1] == player:
            total += fl[5]
    return total


def _fwd_marginal(world, src_id, angle, ships, player, horizon):
    state_no = _fwd_clone(world)
    _fwd_simulate(state_no, horizon)
    base = _fwd_my_score(state_no, player)
    state_yes = _fwd_clone(world)
    if not _fwd_inject_launch(state_yes, src_id, angle, int(ships)):
        return 0.0
    _fwd_simulate(state_yes, horizon)
    return _fwd_my_score(state_yes, player) - base


def _fwd_capture_holds_2p(world, src, target, angle, turns, ships, my_player):
    state = _fwd_clone(world)
    if not _fwd_inject_launch(state, src.id, angle, int(ships)):
        return True  
    horizon = int(turns) + 15  
    _fwd_simulate(state, horizon)
    return state["planet_owner"].get(target.id) == my_player


def is_targetable(world, target):
    if target.id in world.comet_ids:
        return False
    if target.owner == -1:
        my_arrivals = sorted(
            ((eta, ships) for eta, owner, ships
             in world.arrivals_by_planet.get(target.id, [])
             if owner == world.player),
            key=lambda x: x[0],
        )
        if my_arrivals:
            total_ships = sum(s for _, s in my_arrivals)
            last_eta = my_arrivals[-1][0]
            if total_ships > garrison_at_arrival(target, last_eta):
                return False
        if _neutral_blocked_by_cap(world, target):
            return False
        if (LOW_PROD_NEUTRAL_SKIP_ENABLED
                and int(target.production) <= LOW_PROD_NEUTRAL_SKIP_PROD
                and int(target.ships) >= LOW_PROD_NEUTRAL_SKIP_GARRISON):
            return False
    return True


def _update_neutral_watchlist(world):
    _neutral_wounded.clear()
    if NEUTRAL_HARD_CAP_ENABLED:
        for p in world.neutral_planets:
            prev = _neutral_prev_ships.get(p.id)
            cur = int(p.ships)
            if prev is not None and (prev - cur) >= NEUTRAL_WATCHLIST_MIN_DROP:
                _neutral_wounded.add(p.id)
    _neutral_prev_ships.clear()
    for p in world.neutral_planets:
        _neutral_prev_ships[p.id] = int(p.ships)
    
    if FLEET_INTENT_ENABLED:
        _enemy_recently_launched.clear()
        for p in world.enemy_planets:
            prev = _enemy_prev_ships.get(p.id)
            cur = int(p.ships)
            if prev is not None:
                expected = prev + int(p.production)
                if expected - cur >= FLEET_INTENT_MIN_DROP:
                    _enemy_recently_launched.add(p.id)
        _enemy_prev_ships.clear()
        for p in world.enemy_planets:
            _enemy_prev_ships[p.id] = int(p.ships)
    
    if R1_RECAPTURE_PRIORITY_ENABLED:
        _freshly_lost_planets.clear()
        _freshly_captured_planets.clear()
        for p in world.planets:
            prev_owner = _planet_prev_owner.get(p.id)
            if prev_owner == world.player and p.owner != -1 and p.owner != world.player:
                _freshly_lost_planets.add(p.id)
            if (
                FRESH_CAPTURE_INHERITANCE_ENABLED
                and prev_owner is not None
                and prev_owner != world.player
                and p.owner == world.player
            ):
                _freshly_captured_planets.add(p.id)
                _planet_capture_age[p.id] = 0
        
        if FRESH_CAPTURE_INHERITANCE_ENABLED:
            for pid in list(_planet_capture_age.keys()):
                if pid in _freshly_captured_planets:
                    continue
                pp = world.planet_by_id.get(pid)
                if pp is None or pp.owner != world.player:
                    del _planet_capture_age[pid]
                else:
                    _planet_capture_age[pid] += 1
                    if _planet_capture_age[pid] > FRESH_CAPTURE_MAX_AGE:
                        del _planet_capture_age[pid]
        _planet_prev_owner.clear()
        for p in world.planets:
            _planet_prev_owner[p.id] = int(p.owner)


def _neutral_blocked_by_cap(world, target):
    if not NEUTRAL_HARD_CAP_ENABLED:
        return False
    if target.owner != -1:
        return False
    
    if NEUTRAL_CAP_USES_EFFECTIVE_GARRISON:
        eff_owner, eff_ships = effective_garrison_at_arrival(target, NEUTRAL_CAP_LOOKAHEAD, world)
        if eff_owner != -1:
            return False
        if world.is_2p:
            return eff_ships >= NEUTRAL_HARD_CAP_2P
        if eff_ships <= NEUTRAL_HARD_CAP_4P:
            return False
        return target.id not in _neutral_wounded
    
    if world.is_2p:
        return int(target.ships) >= NEUTRAL_HARD_CAP_2P
    if int(target.ships) <= NEUTRAL_HARD_CAP_4P:
        return False
    return target.id not in _neutral_wounded


def _neutral_tempo_ok(world, target, ships, turns):
    if not NEUTRAL_TEMPO_FILTER_ENABLED:
        return True
    if world.is_2p:
        return True
    if target.owner != -1:
        return True
    remaining_after = max(0, int(world.remaining_steps) - int(turns))
    net = float(target.production) * remaining_after - float(ships)
    return net >= NEUTRAL_TEMPO_THRESHOLD


def _ti1_extra_margin(world):
    if not TI1_TIE_FOR_WIN_ENABLED:
        return 0
    if world.remaining_steps > TI1_HORIZON_TURNS:
        return 0
    my_sum = world.owner_strength.get(world.player, 0)
    leader_sum = my_sum
    for owner, ships in world.owner_strength.items():
        if owner == world.player or owner == -1:
            continue
        if ships > leader_sum:
            leader_sum = ships
    if leader_sum - my_sum < TI1_TRAILING_GAP_MIN:
        return 0  
    return TI1_REQUIRED_EXTRA_MARGIN


def _endgame_roi_ok(world, target, ships, turns):
    if not ENDGAME_ROI_ENABLED:
        return True
    if world.is_2p:
        return True
    if target.owner != -1:
        return True
    if world.step < TOTAL_STEPS - ENDGAME_ROI_TURNS:
        return True
    remaining_after = max(0, int(world.remaining_steps) - int(turns))
    expected_growth = float(target.production) * remaining_after
    threshold = float(target.ships) if E2_USE_GARRISON_THRESHOLD else float(ships)
    return expected_growth > threshold


def friendly_already_committed(world, target_id):
    target = world.planet_by_id.get(target_id)
    if target is None:
        return False
    pending = [c for c in _pending_commitments if c["target_id"] == target_id]
    if not pending:
        return False
    if target.owner == -1 or target.owner == world.player:
        return sum(c["ships"] for c in pending) > 0
    for c in pending:
        eta = int(c["arrival_abs"]) - int(world.step)
        if eta <= 0:
            continue
        if int(c["ships"]) >= needed_to_capture(target, eta):
            return True
    return False


def _commit_fleet(world, moves, spent, target_locked,
                  src_id, target_id, angle, turns, ships):
    moves.append([src_id, float(angle), int(ships)])
    spent[src_id] += int(ships)
    target_locked.add(target_id)
    target_obj = world.planet_by_id.get(int(target_id))
    owner_at_commit = int(target_obj.owner) if target_obj is not None else -2
    _pending_commitments.append({
        "target_id": int(target_id),
        "ships": int(ships),
        "arrival_abs": int(world.step) + int(turns),
        "owner_at_commit": owner_at_commit,
    })
    if os.environ.get("ORBIT_TRACE"):
        try:
            with open(os.environ["ORBIT_TRACE"], "a") as fh:
                fh.write(
                    f"t={world.step} src={src_id} tgt={target_id} ships={ships} eta={turns}\n"
                )
        except Exception:
            pass


def _find_capture_event(world, tgt, horizon):
    """Walk tgt's deterministic arrival sequence; return the first flip to an
    enemy owner within `horizon` as (eta, new_owner, survivors), else None.

    Mirrors effective_garrison_at_arrival's combat walk (same ordering and
    tie rules) but reports the flip instead of the final garrison."""
    arrivals = sorted(
        ((eta, owner, ships) for eta, owner, ships
         in world.arrivals_by_planet.get(tgt.id, [])
         if 1 <= eta <= horizon and ships > 0 and owner != -1),
        key=lambda x: x[0],
    )
    if not arrivals:
        return None
    owner = int(tgt.owner)
    ships = int(tgt.ships)
    prod = max(0, int(tgt.production))
    last_t = 0
    for eta, f_owner, f_ships in arrivals:
        if owner != -1:
            ships += prod * (eta - last_t)
        last_t = eta
        if f_owner == owner:
            ships += f_ships
        elif f_ships > ships:
            owner = int(f_owner)
            ships = f_ships - ships
            if owner == world.player:
                return None  # flips to us first — not a snipe target
            return (int(eta), owner, int(ships))
        elif f_ships < ships:
            ships -= f_ships
        else:
            ships = 0
    return None


def handle_snipe(world, available, spent, target_locked, moves, mode_log):
    global _snipe_total
    if not SNIPE_ENABLED:
        return
    if world.is_2p and not SNIPE_2P_ENABLED:
        return
    if world.step < SNIPE_MIN_STEP:
        return
    if LAUNCH_BLACKOUT_ENABLED and world.step >= TOTAL_STEPS - LAUNCH_BLACKOUT_TURNS:
        return
    _snipe_commitments[:] = [c for c in _snipe_commitments
                             if c["arrival_abs"] > world.step]
    if len(_snipe_commitments) >= SNIPE_MAX_PENDING:
        return

    events = []
    for tgt in world.planets:
        if tgt.owner == world.player or tgt.id in target_locked:
            continue
        if tgt.id in world.comet_ids:
            continue
        if int(tgt.production) < SNIPE_MIN_PROD:
            continue
        if friendly_already_committed(world, tgt.id):
            continue
        ev = _find_capture_event(world, tgt, SNIPE_CAP_HORIZON)
        if ev is None:
            continue
        t_cap, _cap_owner, survivors = ev
        if not (SNIPE_MIN_SURVIVORS <= survivors <= SNIPE_MAX_SURVIVORS):
            continue
        d_my = min(dist(p.x, p.y, tgt.x, tgt.y) for p in world.my_planets)
        enemy_planets = [p for p in world.planets
                         if p.owner not in (-1, world.player) and p.id != tgt.id]
        if enemy_planets:
            d_en = min(dist(p.x, p.y, tgt.x, tgt.y) for p in enemy_planets)
            if d_my > d_en * SNIPE_PROXIMITY_RATIO + SNIPE_PROXIMITY_SLACK:
                continue
        events.append((survivors - int(tgt.production) * 3, t_cap, tgt))
    if not events:
        return
    events.sort(key=lambda e: (e[0], e[1]))

    fired = 0
    for _, t_cap, tgt in events:
        if fired >= SNIPE_MAX_PER_TURN or len(_snipe_commitments) >= SNIPE_MAX_PENDING:
            return
        for src in sorted(world.my_planets,
                          key=lambda s: dist(s.x, s.y, tgt.x, tgt.y)):
            if mode_log.get(src.id):
                continue
            avail = available[src.id] - spent[src.id]
            if avail < MIN_DISPATCH_SHIPS:
                continue
            budget = min(avail, SNIPE_MAX_COST)
            ships = effective_needed_to_capture(tgt, t_cap + 1, world) + SNIPE_MARGIN
            if ships > budget:
                continue
            plan = None
            for _ in range(3):
                aim = aim_at_target(src, tgt, ships, world.initial_by_id,
                                    world.ang_vel, world=world)
                if aim is None:
                    break
                angle, turns = aim
                if not (t_cap + 1 <= turns <= t_cap + SNIPE_ARRIVAL_WINDOW):
                    break
                need = effective_needed_to_capture(tgt, turns, world) + SNIPE_MARGIN
                if need > budget:
                    break
                if need <= ships:
                    # aim was computed for `ships`, so the plan is consistent
                    plan = (angle, turns, ships)
                    break
                ships = need
            if plan is None:
                continue
            angle, turns, ships = plan
            _commit_fleet(world, moves, spent, target_locked,
                          src.id, tgt.id, angle, turns, ships)
            mode_log[src.id] = "snipe"
            _snipe_commitments.append(
                {"target_id": tgt.id, "arrival_abs": int(world.step) + int(turns)})
            _snipe_total += 1
            _snipe_log.append({"step": int(world.step), "tgt": int(tgt.id),
                               "src": int(src.id), "ships": int(ships),
                               "eta": int(turns), "t_cap": int(t_cap)})
            fired += 1
            break


def plan_solo_capture(world, src, tgt, max_avail, max_travel):
    raw_dist = dist(src.x, src.y, tgt.x, tgt.y)
    if F3_THREE_BUCKET_ENABLED:
        if tgt.owner == -1 and raw_dist < F3_SAFE_DIST:
            min_floor = F3_SAFE_FLOOR
        elif (tgt.owner != -1 and tgt.owner != world.player
              and int(tgt.ships) >= F3_HARD_GARRISON):
            min_floor = F3_HARD_FLOOR
        else:
            min_floor = MIN_DISPATCH_SHIPS
    else:
        min_floor = 5 if (world.is_2p and raw_dist < 12.0) else MIN_DISPATCH_SHIPS
    if max_avail < min_floor:
        return None
    aim = aim_at_target(src, tgt, max_avail, world.initial_by_id, world.ang_vel, world=world)
    if aim is None:
        return None
    angle, turns = aim
    if turns > max_travel:
        return None
    need = effective_needed_to_capture(tgt, turns, world)  
    margin = EXPAND_MIN_MARGIN_4P if not world.is_2p else EXPAND_MIN_MARGIN
    extra = X8B_2P_EXTRA if world.is_2p else 0
    extra += _ti1_extra_margin(world)
    preferred = max(min_floor, need + margin + extra)
    
    if SP1_SPEED_AWARE_ENABLED:
        raw_dist = dist(src.x, src.y, tgt.x, tgt.y)
        if raw_dist >= SP1_LONG_DIST_THRESHOLD:
            preferred = max(preferred, min(SP1_LONG_DIST_SHIPS, max_avail))
    if preferred <= max_avail:
        ships = preferred
    else:
        ships = max(min_floor, need + margin)
        if ships > max_avail:
            ships = max(min_floor, need)  
    if ships < min_floor or ships > max_avail:
        return None
    aim2 = aim_at_target(src, tgt, ships, world.initial_by_id, world.ang_vel, world=world)
    if aim2 is None:
        return None
    angle, turns = aim2
    if turns > max_travel:
        return None
    need2 = effective_needed_to_capture(tgt, turns, world)  
    if ships < need2 + margin:
        ships = need2 + margin
        if ships > max_avail:
            return None
        aim3 = aim_at_target(src, tgt, ships, world.initial_by_id, world.ang_vel, world=world)
        if aim3 is None:
            return None
        angle, turns = aim3
        if turns > max_travel:
            return None
    
    if AS1_ANTI_SECOND_ENABLED and not world.is_2p:
        for eta, owner, e_ships in world.arrivals_by_planet.get(tgt.id, []):
            if int(eta) != int(turns):
                continue
            if owner == world.player or owner == -1:
                continue
            if int(e_ships) >= int(ships):
                return None  
    
    if FWD_SIM_FILTER_ENABLED and not world.is_2p and tgt.owner == -1:
        proj = forward_project(
            world,
            our_capture_target=tgt.id,
            our_capture_turn=int(turns),
            our_capture_ships=int(ships),
            horizon=FWD_SIM_HORIZON,
            project_opponent_moves=True,
            opponent_emit_fraction=0.30,
        )
        end_owner, end_ships = proj.get(tgt.id, (-1, 0))
        if end_owner != world.player and end_owner != -1 and end_ships > 5:
            return None
    return angle, turns, int(ships)


def handle_defense(world, rescue_needs, available, spent, target_locked,
                   moves, mode_log):
    if not rescue_needs:
        return

    for victim_id, (deficit, deadline, victim) in rescue_needs.items():
        if victim_id in target_locked:
            continue
        need = deficit + DEFENSE_OVERSEND

        if PREEMPTIVE_DOOM_EVAC_ENABLED and (not PREEMPTIVE_DOOM_EVAC_2P_ONLY or world.is_2p):
            enemy_arrivals = [
                (eta, owner, int(ships)) for eta, owner, ships
                in world.arrivals_by_planet.get(victim_id, [])
                if owner != world.player and owner != -1
            ]
            if world.is_2p or not PREEMPTIVE_EVAC_USE_LARGEST_SINGLE_ENEMY_4P:
                threat_metric = sum(ships for _eta, _owner, ships in enemy_arrivals)
            else:
                by_owner = defaultdict(int)
                for _eta, owner, ships in enemy_arrivals:
                    by_owner[owner] += ships
                threat_metric = max(by_owner.values()) if by_owner else 0
            window = deadline if deadline is not None else PREEMPTIVE_EVAC_DEFAULT_WINDOW
            garrison_at_deadline = int(victim.ships) + int(victim.production) * int(window)
            if threat_metric > garrison_at_deadline * PREEMPTIVE_EVAC_DOOM_RATIO:
                if _try_doom_evac(world, victim, available, spent, target_locked, moves, mode_log):
                    continue

        solo = []
        for src in world.my_planets:
            if src.id == victim_id:
                continue
            avail = available[src.id] - spent[src.id]
            if avail < need:
                continue
            aim = aim_at_target(src, victim, avail, world.initial_by_id, world.ang_vel, world=world)
            if aim is None:
                continue
            angle, turns = aim
            if deadline is not None and turns > deadline:
                continue
            solo.append((turns, src.id, src, angle, avail))

        if solo:
            solo.sort()  
            fired_solo = False
            last_fail = None
            for _t, src_id, src, _angle_est, avail in solo:
                send = min(avail, need)
                send = max(send, deficit + 1)
                if send < MIN_DISPATCH_SHIPS:
                    send = MIN_DISPATCH_SHIPS if avail >= MIN_DISPATCH_SHIPS else 0
                if send <= 0:
                    last_fail = "doomed-too-poor"
                    continue
                aim_final = aim_at_target(src, victim, send, world.initial_by_id, world.ang_vel, world=world)
                if aim_final is None:
                    last_fail = "doomed-aim-blocked"
                    continue
                angle, turns = aim_final
                if deadline is not None and turns > deadline:
                    last_fail = "doomed-too-slow"
                    continue
                if FWD_SIM_DEFENSE_CHECK and not world.is_2p:
                    proj = forward_project(
                        world,
                        our_capture_target=victim_id,
                        our_capture_turn=int(turns),
                        our_capture_ships=int(send),
                        horizon=FWD_SIM_HORIZON,
                        project_opponent_moves=True,
                        opponent_emit_fraction=0.30,
                    )
                    end_owner, _ = proj.get(victim_id, (-1, 0))
                    if end_owner != world.player:
                        last_fail = "fwd-sim-victim-still-lost"
                        continue
                _commit_fleet(world, moves, spent, target_locked,
                              src_id, victim_id, angle, turns, int(send))
                mode_log[victim_id] = "defended-by-solo"
                mode_log[src_id] = "defense"
                fired_solo = True
                break
            if fired_solo:
                continue
            if last_fail is not None:
                mode_log[victim_id] = last_fail

        if not COALITION_ENABLED:
            if _try_doom_evac(world, victim, available, spent, target_locked, moves, mode_log):
                continue
            mode_log[victim_id] = "doomed"
            continue
        coalition = _find_defense_coalition(
            world, victim, deadline, need, available, spent
        )
        if coalition is None:
            if _try_doom_evac(world, victim, available, spent, target_locked, moves, mode_log):
                continue
            mode_log[victim_id] = "doomed"
            continue
        for src_id, src, angle, ships, turns in coalition:
            _commit_fleet(world, moves, spent, target_locked,
                          src_id, victim_id, angle, turns, int(ships))
            mode_log[src_id] = "defense-coalition"
        mode_log[victim_id] = "defended-by-coalition"


def _try_doom_evac(world, victim, available, spent, target_locked, moves, mode_log):
    if not DOOM_EVAC_ENABLED:
        return False
    garrison = available[victim.id] - spent[victim.id]
    if garrison < DOOM_EVAC_MIN_SHIPS:
        return False

    friendly_candidates = []
    for dst in world.my_planets:
        if dst.id == victim.id:
            continue
        aim = aim_at_target(victim, dst, garrison, world.initial_by_id,
                            world.ang_vel, world=world)
        if aim is None:
            continue
        angle, turns = aim
        if turns > DOOM_EVAC_MAX_TRAVEL:
            continue
        score = int(dst.ships) + int(dst.production) * 5
        friendly_candidates.append((-score, int(turns), dst, angle))
    if friendly_candidates:
        friendly_candidates.sort()
        _score, turns, dst, angle = friendly_candidates[0]
        _commit_fleet(world, moves, spent, target_locked,
                      victim.id, dst.id, angle, turns, int(garrison))
        mode_log[victim.id] = "doom-evac-launched"
        mode_log[dst.id] = "doom-evac-recipient"
        return True

    if not DOOM_EVAC_ATTACK_FALLBACK_ENABLED:
        return False
    if DOOM_EVAC_ATTACK_FALLBACK_4P_ONLY and world.is_2p:
        return False
    attack_candidates = []
    for dst in world.planets:
        if dst.id == victim.id or dst.owner == world.player:
            continue
        if dst.id in target_locked:
            continue
        if not is_targetable(world, dst):
            continue
        aim = aim_at_target(victim, dst, garrison, world.initial_by_id,
                            world.ang_vel, world=world)
        if aim is None:
            continue
        angle, turns = aim
        if turns > DOOM_EVAC_MAX_TRAVEL:
            continue
        is_enemy = dst.owner != -1
        prod = int(dst.production) if is_enemy else 0
        arrival_garrison = int(dst.ships) + prod * int(turns)
        required = arrival_garrison + DOOM_EVAC_ATTACK_OVERKILL
        if int(garrison) < required:
            continue
        recently_launched_bonus = (
            -DOOM_EVAC_ATTACK_PREFER_LAUNCHED_BONUS
            if (is_enemy and dst.id in _enemy_recently_launched) else 0
        )
        rank = (
            recently_launched_bonus,
            -int(dst.production),
            int(turns),
            int(required),
        )
        attack_candidates.append((rank, dst, angle, turns))
    if not attack_candidates:
        return False
    attack_candidates.sort(key=lambda x: x[0])
    _rank, dst, angle, turns = attack_candidates[0]
    _commit_fleet(world, moves, spent, target_locked,
                  victim.id, dst.id, angle, turns, int(garrison))
    mode_log[victim.id] = "doom-evac-attack"
    mode_log[dst.id] = "doom-evac-attack-target"
    return True


def _find_defense_coalition(world, victim, deadline, need, available, spent):
    options = []
    for src in world.my_planets:
        if src.id == victim.id:
            continue
        avail = available[src.id] - spent[src.id]
        if avail < COALITION_MIN_PER_CONTRIBUTOR:
            continue
        aim = aim_at_target(src, victim, avail, world.initial_by_id, world.ang_vel, world=world)
        if aim is None:
            continue
        _angle_est, turns = aim
        if deadline is not None and turns > deadline:
            continue
        options.append((turns, src.id, src, avail))

    if len(options) < 2:
        return None
    options.sort()

    for i in range(len(options)):
        for j in range(i + 1, len(options)):
            t_i, sid_i, s_i, a_i = options[i]
            t_j, sid_j, s_j, a_j = options[j]
            if a_i + a_j < need:
                continue
            ratio = a_i / float(a_i + a_j)
            ship_i = max(COALITION_MIN_PER_CONTRIBUTOR,
                         min(a_i, int(round(need * ratio))))
            ship_j = max(COALITION_MIN_PER_CONTRIBUTOR,
                         min(a_j, need - ship_i))
            while ship_i + ship_j < need:
                if ship_i < a_i:
                    ship_i += 1
                elif ship_j < a_j:
                    ship_j += 1
                else:
                    break
            if (ship_i + ship_j < need
                    or ship_i < COALITION_MIN_PER_CONTRIBUTOR
                    or ship_j < COALITION_MIN_PER_CONTRIBUTOR):
                continue
            aim_i = aim_at_target(s_i, victim, ship_i, world.initial_by_id, world.ang_vel, world=world)
            aim_j = aim_at_target(s_j, victim, ship_j, world.initial_by_id, world.ang_vel, world=world)
            if aim_i is None or aim_j is None:
                continue
            ang_i, turns_i = aim_i
            ang_j, turns_j = aim_j
            if (deadline is not None
                    and (turns_i > deadline or turns_j > deadline)):
                continue
            return [
                (sid_i, s_i, ang_i, ship_i, turns_i),
                (sid_j, s_j, ang_j, ship_j, turns_j),
            ]
    return None


COMET_EVAC_REMAINING_TURNS = 3   
COMET_EVAC_MIN_SHIPS = 5          

DOOM_EVAC_ENABLED = True
DOOM_EVAC_MIN_SHIPS = 5           
DOOM_EVAC_MAX_TRAVEL = 40         

DOOM_EVAC_ATTACK_FALLBACK_ENABLED = True
DOOM_EVAC_ATTACK_FALLBACK_4P_ONLY = True  
DOOM_EVAC_ATTACK_OVERKILL = 2     
DOOM_EVAC_ATTACK_PREFER_LAUNCHED_BONUS = 3  

PREEMPTIVE_DOOM_EVAC_ENABLED = True
PREEMPTIVE_DOOM_EVAC_2P_ONLY = False  

PREEMPTIVE_EVAC_DOOM_RATIO = 1.20  
PREEMPTIVE_EVAC_DEFAULT_WINDOW = 15  

PREEMPTIVE_EVAC_USE_LARGEST_SINGLE_ENEMY_4P = True


def handle_comet_evac(world, available, spent, target_locked, moves, mode_log):
    if not world.comet_remaining:
        return
    
    own_non_comet = [p for p in world.my_planets if p.id not in world.comet_ids]
    if not own_non_comet:
        own_non_comet = [p for p in world.planets
                         if p.owner == -1 and p.id not in world.comet_ids]
        if not own_non_comet:
            return
    for src in world.my_planets:
        rem = world.comet_remaining.get(src.id)
        if rem is None or rem > COMET_EVAC_REMAINING_TURNS:
            continue
        if src.id in mode_log:
            continue
        avail = max(0, available[src.id] - spent.get(src.id, 0))
        if avail < COMET_EVAC_MIN_SHIPS:
            continue
        best = None
        best_d = float("inf")
        for dst in own_non_comet:
            if dst.id == src.id:
                continue
            d_now = dist(src.x, src.y, dst.x, dst.y)
            est_turns = max(1, int(math.ceil(d_now / fleet_speed(max(1, int(avail))))))
            dst_px, dst_py = predict_target_position(dst, world, est_turns)
            d = dist(src.x, src.y, dst_px, dst_py)
            if d < best_d:
                best_d = d
                best = dst
        if best is None:
            continue
        aim = aim_at_target(src, best, avail, world.initial_by_id, world.ang_vel, world=world)
        if aim is None:
            continue
        angle, turns = aim
        _commit_fleet(world, moves, spent, target_locked,
                      src.id, best.id, angle, turns, int(avail))
        mode_log[src.id] = "comet-evac"


def handle_cheap_pickup(world, available, spent, target_locked, moves, mode_log):
    if not CHEAP_PICKUP_ENABLED:
        return
    if CHEAP_PICKUP_4P_ONLY and world.is_2p:
        return
    
    if LAUNCH_BLACKOUT_ENABLED and world.step >= TOTAL_STEPS - LAUNCH_BLACKOUT_TURNS:
        return
    if world.is_opening:
        max_travel = world.mode_params.get("expand_max_travel_opening", EXPAND_MAX_TRAVEL_OPENING)
    else:
        max_travel = world.mode_params["expand_max_travel_mid"]

    cheap_neutrals = [
        p for p in world.neutral_planets
        if int(p.ships) <= CHEAP_PICKUP_MAX_GARRISON
        and p.id not in target_locked
        and is_targetable(world, p)
    ]
    if not cheap_neutrals:
        return
    
    if CHEAP_PICKUP_MIN_PROD >= 2 and any(int(p.production) >= CHEAP_PICKUP_MIN_PROD for p in cheap_neutrals):
        cheap_neutrals = [p for p in cheap_neutrals if int(p.production) >= CHEAP_PICKUP_MIN_PROD]

    sources = sorted(world.my_planets,
                     key=lambda s: -(available[s.id] - spent[s.id]))
    for src in sources:
        avail = available[src.id] - spent[src.id]
        if avail < MIN_DISPATCH_SHIPS:
            continue
        if mode_log.get(src.id):
            continue
        candidates = []
        for n in cheap_neutrals:
            if n.id in target_locked:
                continue
            if friendly_already_committed(world, n.id):
                continue
            cost = int(n.ships) + 1
            if cost > avail:
                continue
            raw = dist(src.x, src.y, n.x, n.y)
            if raw / MAX_SPEED > max_travel + 4:
                continue
            eff = _effective_target_dist(src, n, world)
            candidates.append((cost, eff, n))
        if not candidates:
            continue
        candidates.sort(key=lambda kv: (kv[0], kv[1]))
        for _cost, _eff, n in candidates:
            plan = plan_solo_capture(world, src, n, avail, max_travel)
            if plan is None:
                continue
            angle, turns, ships = plan
            if RACE_ENABLED:
                enemy_eta = world.enemy_race_eta.get(n.id)
                if enemy_eta is not None and turns > enemy_eta:
                    continue
            if not _capture_holds_against_snipe(world, n, turns, int(ships)):
                continue
            if not _endgame_roi_ok(world, n, int(ships), turns):
                continue
            if not _neutral_tempo_ok(world, n, int(ships), turns):
                continue
            _commit_fleet(world, moves, spent, target_locked,
                          src.id, n.id, angle, turns, int(ships))
            mode_log[src.id] = "cheap-pickup"
            break


def _is_cheap_neutral_pick(world, target):
    if target.owner != -1:
        return True  
    if int(target.ships) > COMBAT_CHEAP_GARRISON:
        return False
    for mp in world.my_planets:
        if dist(mp.x, mp.y, target.x, target.y) <= COMBAT_CHEAP_DIST:
            return True
    return False


def _handle_search_expand_4p(world, available, spent, target_locked, moves, mode_log,
                              deadline=None):
    """[COUNCIL] deadline passed through so search_step_action can budget-gate
    depth-2 penalty computation on a per-action basis."""
    actions = search_step_action(
        world, max_per_source=SEARCH_MAX_PER_SOURCE,
        max_actions_to_eval=12,
        use_depth2=SEARCH_DEPTH2_ENABLED,
        deadline=deadline,
    )
    committed_sources = set()
    committed_targets = set()
    for act in actions[:SEARCH_MAX_ACTIONS_TO_PICK * 2]:
        if act["score"] <= 0:
            continue
        src_id = act["source_id"]
        tgt_id = act["target_id"]
        if src_id in committed_sources or tgt_id in committed_targets:
            continue
        if tgt_id in target_locked:
            continue
        src_status = mode_log.get(src_id)
        if src_status == "brain-reserved-lead":
            continue
        avail = available[src_id] - spent[src_id]
        if avail < act["ships"]:
            continue
        tgt = world.planet_by_id.get(tgt_id)
        
        if (world.stop_expanding_2p or world.prod_lead_stop_expand_4p or world.turn_cutoff_stop_expand) and tgt is not None and tgt.owner == -1:
            continue
        
        if world.stop_expand_lax and tgt is not None and tgt.owner == -1:
            if not _is_cheap_neutral_pick(world, tgt):
                continue
        if tgt is not None and tgt.owner == -1:
            turns_act = int(act["arrival_turn"])
            ships_act = int(act["ships"])
            if not _capture_holds_against_snipe(world, tgt, turns_act, ships_act):
                continue
            if not _endgame_roi_ok(world, tgt, ships_act, turns_act):
                continue
            if not _neutral_tempo_ok(world, tgt, ships_act, turns_act):
                continue
        _commit_fleet(world, moves, spent, target_locked,
                      src_id, tgt_id, act["angle"], act["arrival_turn"], act["ships"])
        mode_log[src_id] = "search-expand"
        committed_sources.add(src_id)
        committed_targets.add(tgt_id)
        if len(committed_sources) >= SEARCH_MAX_ACTIONS_TO_PICK:
            break
    return committed_sources


def handle_expand(world, available, spent, target_locked, moves, mode_log,
                  deadline=None):
    if LAUNCH_BLACKOUT_ENABLED and world.step >= TOTAL_STEPS - LAUNCH_BLACKOUT_TURNS:
        return
    
    if (SEARCH_EXPAND_4P_ENABLED and not world.is_2p) or \
       (SEARCH_EXPAND_2P_ENABLED and world.is_2p):
        _handle_search_expand_4p(world, available, spent, target_locked, moves, mode_log,
                                 deadline=deadline)
        
    if world.is_opening:
        K = world.mode_params.get("expand_k_opening", EXPAND_K_OPENING)
        max_travel = world.mode_params.get("expand_max_travel_opening", EXPAND_MAX_TRAVEL_OPENING)
    else:
        K = world.mode_params["expand_k_mid"]
        max_travel = world.mode_params["expand_max_travel_mid"]

    nonfriendly = [
        p for p in world.planets
        if p.owner != world.player and is_targetable(world, p)
    ]
    
    if world.stop_expanding_2p or world.prod_lead_stop_expand_4p or world.turn_cutoff_stop_expand:
        nonfriendly = [p for p in nonfriendly if p.owner != -1]
    
    elif world.stop_expand_lax:
        nonfriendly = [
            p for p in nonfriendly
            if p.owner != -1 or _is_cheap_neutral_pick(world, p)
        ]
    if not nonfriendly:
        return

    def frontier_key(src):
        return min(dist(src.x, src.y, t.x, t.y) for t in nonfriendly)

    sources = sorted(world.my_planets, key=frontier_key)

    for src in sources:
        avail = _routine_avail(world, src, available[src.id] - spent[src.id])
        if avail < MIN_DISPATCH_SHIPS:
            continue
        status = mode_log.get(src.id)
        if status and status != "cheap-pickup":
            continue  

        candidates = _nearest_targets(src, world, K, max_travel, target_locked)
        fired_solo = False
        for tgt, _approx_dist in candidates:
            if friendly_already_committed(world, tgt.id):
                continue
            plan = plan_solo_capture(world, src, tgt, avail, max_travel)
            if plan is None:
                continue
            angle, turns, ships = plan
            if RACE_ENABLED and tgt.owner == -1:
                enemy_eta = world.enemy_race_eta.get(tgt.id)
                if enemy_eta is not None and turns > enemy_eta:
                    snipe = _plan_counter_snipe(world, src, tgt, avail, max_travel)
                    if snipe is None:
                        continue
                    angle, turns, ships = snipe
            if tgt.owner == -1 and not _capture_holds_against_snipe(world, tgt, turns, int(ships)):
                continue
            if not _endgame_roi_ok(world, tgt, int(ships), turns):
                continue
            if not _neutral_tempo_ok(world, tgt, int(ships), turns):
                continue
            if (
                FWD_SIM_ENABLED
                and world.is_2p
                and tgt.owner != world.player
                and not _fwd_capture_holds_2p(world, src, tgt, angle, turns, int(ships), world.player)
            ):
                continue
            _commit_fleet(world, moves, spent, target_locked,
                          src.id, tgt.id, angle, turns, int(ships))
            mode_log[src.id] = "expand-solo"
            fired_solo = True
            break

        if fired_solo:
            continue
        if not COALITION_ENABLED:
            continue

        coalition_max_travel = max_travel + COALITION_MAX_TRAVEL_BONUS
        for tgt, _ in candidates:
            if tgt.id in target_locked:
                continue
            if COALITION_NEUTRALS_ONLY and tgt.owner != -1:
                continue
            if friendly_already_committed(world, tgt.id):
                continue
            ok = _try_coalition_expand(
                world, src, tgt, coalition_max_travel, available, spent,
                target_locked, moves, mode_log,
            )
            if ok:
                break


def _effective_target_dist(src, tgt, world):
    raw = dist(src.x, src.y, tgt.x, tgt.y)
    if not ROT_AWARE_RANK_ENABLED:
        return raw
    init = world.initial_by_id.get(tgt.id)
    if init is None:
        return raw
    if dist(init.x, init.y, CENTER_X, CENTER_Y) + init.radius >= ROTATION_LIMIT:
        return raw
    speed = fleet_speed(50)
    travel = max(1, int(math.ceil(raw / speed)))
    if travel > 60:
        return raw
    px, py = predict_planet_position(tgt, world.initial_by_id, world.ang_vel, travel)
    return dist(src.x, src.y, px, py)


def _counter_snipe_candidates(world, src, max_travel, target_locked):
    if not COUNTER_SNIPE_ENABLED:
        return []
    if COUNTER_SNIPE_2P_ONLY and not world.is_2p:
        return []
    out = []
    for n in world.neutral_planets:
        if n.id in target_locked:
            continue
        if not is_targetable(world, n):
            continue
        enemy_eta = None
        enemy_remaining = None
        needed = int(n.ships) + 1
        for eta, owner, ships in world.arrivals_by_planet.get(n.id, []):
            if owner == world.player or owner == -1:
                continue
            if ships < needed:
                continue
            if enemy_eta is None or eta < enemy_eta:
                enemy_eta = int(eta)
                enemy_remaining = ships - int(n.ships)
        if enemy_eta is None:
            continue
        d = dist(src.x, src.y, n.x, n.y)
        speed = fleet_speed(50)
        my_eta_est = max(1, int(math.ceil(d / speed)))
        if my_eta_est > max_travel + 4:
            continue
        delay = my_eta_est - enemy_eta
        if delay < COUNTER_SNIPE_MIN_DELAY or delay > COUNTER_SNIPE_MAX_DELAY:
            continue
        prod = max(0, int(n.production))
        defender_at_my_arrival = max(0, int(enemy_remaining)) + prod * delay
        flip_cost = defender_at_my_arrival + 1
        if flip_cost > COUNTER_SNIPE_MAX_COST:
            continue
        out.append((flip_cost, n, d))
    out.sort(key=lambda kv: kv[0])
    return [(n, d) for _cost, n, d in out]


def _plan_counter_snipe(world, src, tgt, max_avail, max_travel):
    if not COUNTER_SNIPE_ENABLED or tgt.owner != -1:
        return None
    if COUNTER_SNIPE_2P_ONLY and not world.is_2p:
        return None
    if max_avail < MIN_DISPATCH_SHIPS:
        return None
    enemy_eta = None
    enemy_remaining = None
    needed_to_take = int(tgt.ships) + 1
    for eta, owner, ships in world.arrivals_by_planet.get(tgt.id, []):
        if owner == world.player or owner == -1:
            continue
        if ships < needed_to_take:
            continue
        if enemy_eta is None or eta < enemy_eta:
            enemy_eta = int(eta)
            enemy_remaining = ships - int(tgt.ships)
    if enemy_eta is None:
        return None

    aim = aim_at_target(src, tgt, max_avail, world.initial_by_id, world.ang_vel, world=world)
    if aim is None:
        return None
    angle, turns = aim
    if turns > max_travel:
        return None
    delay = turns - enemy_eta
    if delay < COUNTER_SNIPE_MIN_DELAY or delay > COUNTER_SNIPE_MAX_DELAY:
        return None
    prod = max(0, int(tgt.production))
    defender = max(0, int(enemy_remaining)) + prod * delay
    ships = max(MIN_DISPATCH_SHIPS, defender + 1)
    if ships > max_avail or ships > COUNTER_SNIPE_MAX_COST:
        return None
    aim2 = aim_at_target(src, tgt, ships, world.initial_by_id, world.ang_vel, world=world)
    if aim2 is None:
        return None
    angle, turns = aim2
    if turns > max_travel:
        return None
    delay2 = turns - enemy_eta
    if delay2 < COUNTER_SNIPE_MIN_DELAY or delay2 > COUNTER_SNIPE_MAX_DELAY:
        return None
    defender2 = max(0, int(enemy_remaining)) + prod * delay2
    if ships < defender2 + 1:
        ships = defender2 + 1
        if ships > max_avail or ships > COUNTER_SNIPE_MAX_COST:
            return None
        aim3 = aim_at_target(src, tgt, ships, world.initial_by_id, world.ang_vel, world=world)
        if aim3 is None:
            return None
        angle, turns = aim3
        if turns > max_travel:
            return None
    return angle, turns, int(ships)


def _capture_holds_against_snipe(world, target, arrival_turn, ships_sent):
    if not ANTI_SNIPE_ENABLED:
        return True
    if ANTI_SNIPE_2P_ONLY and not world.is_2p:
        return True
    if target.owner != -1:
        return True
    arrivals = world.arrivals_by_planet.get(target.id, [])
    enemy_after = []
    friendly_after = []
    for eta, owner, ships in arrivals:
        if ships <= 0:
            continue
        if eta <= arrival_turn:
            continue
        if eta - arrival_turn > ANTI_SNIPE_HORIZON:
            continue
        if owner == world.player:
            friendly_after.append((eta, ships))
        elif owner != -1:
            enemy_after.append((eta, ships))

    if REACTIVE_SNIPE_PROJECTION_ENABLED:
        for enemy_p in world.enemy_planets:
            e_ships = int(enemy_p.ships)
            if e_ships < REACTIVE_MIN_ENEMY_SHIPS:
                continue
            if SUN_SHADOW_REACTIVE_FILTER and not world.is_2p and segment_hits_sun(
                enemy_p.x, enemy_p.y, target.x, target.y
            ):
                continue
            d = dist(enemy_p.x, enemy_p.y, target.x, target.y)
            projected_force = max(REACTIVE_MIN_PROJECTED, int(e_ships * REACTIVE_EMIT_FRAC))
            speed = fleet_speed(projected_force)
            travel = max(1, int(math.ceil(d / speed)))
            snipe_eta = travel
            if snipe_eta <= arrival_turn:
                continue  
            if snipe_eta - arrival_turn > ANTI_SNIPE_HORIZON:
                continue
            enemy_after.append((snipe_eta, projected_force))

    if not enemy_after:
        return True

    if N6_USE_EFFECTIVE_PRE_GARRISON:
        _, pre_garrison = effective_garrison_at_arrival(target, arrival_turn, world)
    else:
        pre_garrison = garrison_at_arrival(target, arrival_turn)
    if ships_sent <= pre_garrison:
        return True
    surplus = ships_sent - pre_garrison
    prod = max(0, int(target.production))
    by_turn = defaultdict(int)
    for eta, ships in enemy_after:
        by_turn[eta] -= ships
    for eta, ships in friendly_after:
        by_turn[eta] += ships

    bal = surplus
    last_t = arrival_turn
    for eta in sorted(by_turn):
        bal += prod * (eta - last_t)
        bal += by_turn[eta]
        if bal <= 0:
            return False
        last_t = eta
    return True


def _tiebreak_hash(world, src_id, target_id):
    h = (int(world.player) * 2654435761) & 0xFFFFFFFF
    h ^= (int(world.step) * 1664525) & 0xFFFFFFFF
    h ^= (int(src_id) * 16777619) & 0xFFFFFFFF
    h ^= (int(target_id) * 2246822519) & 0xFFFFFFFF
    return h & 0xFFFF


def _nearest_targets(src, world, K, max_travel, target_locked):
    _f31_has_better = (
        world.is_2p
        and EXPAND_MIN_PROD_2P >= 2
        and any(int(n.production) >= EXPAND_MIN_PROD_2P for n in world.neutral_planets
                if n.id not in target_locked)
    )
    candidates = []
    for t in world.planets:
        if t.owner == world.player:
            continue
        if t.id in target_locked:
            continue
        if not is_targetable(world, t):
            continue
        if _neutral_blocked_by_cap(world, t):
            continue
        if _f31_has_better and t.owner == -1 and int(t.production) < EXPAND_MIN_PROD_2P:
            continue
        raw = dist(src.x, src.y, t.x, t.y)
        if raw / MAX_SPEED > max_travel + 4:
            continue
        eff = _effective_target_dist(src, t, world)
        weight = VALUE_WEIGHT_2P if world.is_2p else VALUE_WEIGHT_4P
        weighted = eff - max(0, int(t.production)) * weight
        
        if F1B_EXPAND_BONUS_ENABLED and t.owner != world.player and t.owner != -1:
            if t.id in _enemy_recently_launched:
                weighted -= F1B_EXPAND_BONUS
        
        if SO1_STATIC_PREFERENCE_ENABLED:
            init_t = world.initial_by_id.get(t.id)
            if init_t is not None:
                r_t = dist(init_t.x, init_t.y, CENTER_X, CENTER_Y)
                if r_t + init_t.radius >= ROTATION_LIMIT:
                    weighted -= SO1_STATIC_BONUS
        
        if (
            LEADER_BASH_ENABLED
            and not world.is_2p
            and world.contest_leader
            and world.step >= LEADER_BASH_MIN_STEP
            and world.leader_id is not None
            and t.owner == world.leader_id
        ):
            weighted -= LEADER_BASH_BONUS
        
        if (
            not world.is_2p
            and t.owner != -1
            and t.owner != world.player
            and world.opp_profile
            and t.owner in world.opp_profile
        ):
            prof = world.opp_profile[t.owner]
            if len(prof["emit"]) >= 5:
                avg_emit = sum(prof["emit"]) / len(prof["emit"])
                if avg_emit > 0.35:
                    weighted -= 5.0  
        
        if (
            WEAKEST_TARGET_ENABLED
            and not world.is_2p
            and world.step >= WEAKEST_TARGET_MIN_STEP
            and world.mode == "pressure"
            and world.weakest_enemy is not None
            and t.owner == world.weakest_enemy
        ):
            if world.weakest_enemy_prod_share < WEAKEST_DONT_FINISH_SHARE:
                weighted += WEAKEST_DONT_FINISH_PENALTY
            else:
                weighted -= WEAKEST_TARGET_BONUS
        
        if (
            F14_4A_2P_FOCUS_ENABLED
            and world.is_2p
            and world.focus_enemy_2p is not None
            and t.owner == world.focus_enemy_2p
        ):
            weighted -= F14_4A_2P_FOCUS_DIST_BONUS

        if CHAIN_DENSITY_ENABLED and t.owner == -1:
            nearby = sum(
                1 for n in world.neutral_planets
                if n.id != t.id
                and n.id not in target_locked
                and dist(t.x, t.y, n.x, n.y) <= CHAIN_DENSITY_RADIUS
            )
            weighted -= nearby * CHAIN_DENSITY_BONUS

        candidates.append((t, weighted, raw))
    if not candidates:
        return []
    candidates.sort(key=lambda kv: kv[1])
    
    if (FWD_SIM_RANK_BONUS_4P > 0 and not world.is_2p and len(candidates) > 1):
        baseline_proj = forward_project(
            world, horizon=FWD_SIM_HORIZON,
            project_opponent_moves=True, opponent_emit_fraction=0.30
        )
        baseline_score = forward_score(baseline_proj, world.player, 4, world)
        rerank = []
        topN = min(K + 2, len(candidates))
        for idx, (t, w, raw) in enumerate(candidates[:topN]):
            est_eta = max(1, int(math.ceil(raw / MAX_SPEED)))
            est_ships = needed_to_capture(t, est_eta) + 1
            proj = forward_project(
                world, our_capture_target=t.id, our_capture_turn=est_eta,
                our_capture_ships=est_ships, horizon=FWD_SIM_HORIZON,
                project_opponent_moves=True, opponent_emit_fraction=0.30
            )
            score_gain = forward_score(proj, world.player, 4, world) - baseline_score
            adjusted = w - FWD_SIM_RANK_BONUS_4P * score_gain
            rerank.append((t, adjusted, raw))
        candidates = rerank + candidates[topN:]
        candidates.sort(key=lambda kv: kv[1])
    if world.is_2p and TIEBREAK_ENABLED and len(candidates) > 1:
        best_d = candidates[0][1]
        eps = max(TIEBREAK_EPS_MIN, TIEBREAK_EPS_FRAC * best_d)
        def _k(kv):
            tgt, weighted_d, _raw = kv
            bucket = int(weighted_d / eps) if eps > 0 else 0
            return (bucket, _tiebreak_hash(world, src.id, tgt.id), weighted_d)
        candidates.sort(key=_k)

    counter_snipe = _counter_snipe_candidates(world, src, max_travel, target_locked)

    if not RACE_ENABLED or not world.enemy_race_eta:
        head = counter_snipe + [(t, raw) for t, _eff, raw in candidates[:K]]
        return _dedupe_targets(head)

    race_priority = []
    normal = []
    for t, _eff, raw in candidates:
        enemy_eta = world.enemy_race_eta.get(t.id)
        if enemy_eta is None or t.owner != -1:
            normal.append((t, raw))
            continue
        my_min = max(1, int(math.ceil(raw / fleet_speed(max(1, int(src.ships))))))
        if my_min <= enemy_eta:
            race_priority.append((t, raw))
        else:
            normal.append((t, raw))

    return _dedupe_targets(counter_snipe + race_priority + normal[:K])


def _dedupe_targets(seq):
    seen = set()
    out = []
    for tgt, d in seq:
        if tgt.id in seen:
            continue
        seen.add(tgt.id)
        out.append((tgt, d))
    return out


def _aim_partner(world, partner, tgt, ships, max_travel):
    if ships < COALITION_MIN_PER_CONTRIBUTOR:
        return None
    aim = aim_at_target(partner, tgt, ships, world.initial_by_id, world.ang_vel, world=world)
    if aim is None:
        return None
    angle, turns = aim
    if turns > max_travel:
        return None
    return angle, turns


def _try_coalition_expand(world, src, tgt, max_travel, available, spent,
                          target_locked, moves, mode_log):
    src_avail = available[src.id] - spent[src.id]
    if src_avail < COALITION_MIN_PER_CONTRIBUTOR:
        return False
    if int(tgt.ships) < COALITION_MIN_TARGET_SHIPS:
        return False

    partners = []
    for p in world.my_planets:
        if p.id == src.id:
            continue
        avail = available[p.id] - spent[p.id]
        if avail < COALITION_MIN_PER_CONTRIBUTOR:
            continue
        est = aim_at_target(p, tgt, avail, world.initial_by_id, world.ang_vel, world=world)
        if est is None:
            continue
        _, est_turns = est
        if est_turns > max_travel:
            continue
        partners.append((est_turns, p, avail))
    if not partners:
        return False
    partners.sort(key=lambda kv: kv[0])

    for est_turns, p, p_avail in partners:
        combined = src_avail + p_avail
        est_src = aim_at_target(src, tgt, src_avail, world.initial_by_id, world.ang_vel, world=world)
        if est_src is None:
            continue
        worst = max(est_src[1], est_turns)
        total_needed = needed_to_capture(tgt, worst)
        if combined < total_needed:
            continue

        ratio = src_avail / float(combined)
        s_src = max(COALITION_MIN_PER_CONTRIBUTOR,
                    min(src_avail, int(round(total_needed * ratio))))
        s_p = max(COALITION_MIN_PER_CONTRIBUTOR,
                  min(p_avail, total_needed - s_src))
        
        while s_src + s_p < total_needed:
            if s_src < src_avail:
                s_src += 1
            elif s_p < p_avail:
                s_p += 1
            else:
                break
        if s_src + s_p < total_needed:
            continue
        if s_src < COALITION_MIN_PER_CONTRIBUTOR or s_p < COALITION_MIN_PER_CONTRIBUTOR:
            continue
        if s_src > src_avail or s_p > p_avail:
            continue

        aim_src = aim_at_target(src, tgt, s_src, world.initial_by_id, world.ang_vel, world=world)
        aim_p = aim_at_target(p, tgt, s_p, world.initial_by_id, world.ang_vel, world=world)
        if aim_src is None or aim_p is None:
            continue
        a_src, t_src = aim_src
        a_p, t_p = aim_p
        if t_src > max_travel or t_p > max_travel:
            continue

        if world.is_2p and abs(t_src - t_p) > 1:
            continue

        post_eta = max(t_src, t_p)
        post_needed = needed_to_capture(tgt, post_eta)
        if s_src + s_p < post_needed:
            continue

        _commit_fleet(world, moves, spent, target_locked,
                      src.id, tgt.id, a_src, t_src, int(s_src))
        _commit_fleet(world, moves, spent, target_locked,
                      p.id, tgt.id, a_p, t_p, int(s_p))
        mode_log[src.id] = "expand-coalition"
        mode_log[p.id] = "expand-coalition"
        return True

    return False


def _routine_avail(world, planet, base_avail):
    if not PROD_RESERVE_ENABLED:
        return base_avail
    if PROD_RESERVE_4P_ONLY and world.is_2p:
        return base_avail
    if world.step < PROD_RESERVE_TURN_MIN:
        return base_avail
    if int(planet.production) < PROD_RESERVE_MIN_PROD:
        return base_avail
    reserve = int(int(planet.ships) * PROD_RESERVE_FRAC)
    return max(0, base_avail - reserve)


def _brain_pick_lead(world, available, spent, mode_log, min_ships=None):
    if min_ships is None:
        min_ships = ACCUMULATOR_LEAD_MIN_SHIPS
    enemies = world.enemy_planets
    candidates = []
    for p in world.my_planets:
        status = mode_log.get(p.id)
        if status and status != "brain-reserved-lead":
            continue
        avail = available[p.id] - spent[p.id]
        if avail < min_ships:
            continue
        threat = sum(int(ships) for eta, owner, ships
                     in world.arrivals_by_planet.get(p.id, [])
                     if owner != world.player and owner != -1)
        if threat >= avail * ACCUMULATOR_LEAD_THREAT_RATIO:
            continue
        if BRAIN_LEAD_PREFER_FRONTIER and enemies:
            frontier_dist = min(dist(p.x, p.y, e.x, e.y) for e in enemies)
            score = float(avail) - frontier_dist * BRAIN_LEAD_FRONTIER_WEIGHT
        else:
            score = float(avail)
        candidates.append((score, p))
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def _brain_reserve_lead(world, available, spent, mode_log):
    if not BRAIN_LEAD_RESERVE_ENABLED:
        return
    if not ACCUMULATOR_ENABLED:
        return
    if BRAIN_LEAD_RESERVE_4P_ONLY and world.is_2p:
        return
    if ACCUMULATOR_4P_ONLY and world.is_2p:
        return
    if world.step < ACCUMULATOR_TURN_MIN:
        return
    lead = _brain_pick_lead(world, available, spent, mode_log,
                            min_ships=BRAIN_LEAD_RESERVE_MIN_SHIPS)
    if lead is None:
        return
    
    if BRAIN_LEAD_RESERVE_REQUIRE_TARGET:
        has_target = False
        for tgt in world.enemy_planets:
            if int(tgt.ships) > MEGA_HAMMER_TARGET_GARRISON_MAX_ITER_H:
                continue
            aim = aim_at_target(lead, tgt, available[lead.id] - spent[lead.id],
                                world.initial_by_id, world.ang_vel, world=world)
            if aim is None:
                continue
            _, turns = aim
            if turns > MEGA_HAMMER_MAX_TRAVEL:
                continue
            has_target = True
            break
        if not has_target:
            return
    mode_log[lead.id] = "brain-reserved-lead"


def handle_accumulator(world, available, spent, target_locked, moves, mode_log):
    if not ACCUMULATOR_ENABLED:
        return
    if ACCUMULATOR_4P_ONLY and world.is_2p:
        return
    if world.step < ACCUMULATOR_TURN_MIN:
        return

    lead_candidates = []
    for p in world.my_planets:
        status = mode_log.get(p.id)
        if status and status != "brain-reserved-lead":
            continue
        avail = available[p.id] - spent[p.id]
        if avail < ACCUMULATOR_LEAD_MIN_SHIPS:
            continue
        threat = sum(int(ships) for eta, owner, ships
                     in world.arrivals_by_planet.get(p.id, [])
                     if owner != world.player and owner != -1)
        if threat >= avail * ACCUMULATOR_LEAD_THREAT_RATIO:
            continue
        lead_candidates.append((avail, p))
    if not lead_candidates:
        return
    lead_candidates.sort(key=lambda x: -x[0])
    lead_avail, lead = lead_candidates[0]

    feeders = []
    for p in world.my_planets:
        if p.id == lead.id or p.id in mode_log:
            continue
        threat = sum(int(ships) for eta, owner, ships
                     in world.arrivals_by_planet.get(p.id, [])
                     if owner != world.player and owner != -1)
        if threat > 0:
            continue
        avail = available[p.id] - spent[p.id]
        surplus = avail - ACCUMULATOR_FEEDER_KEEP_RESERVE
        if surplus < ACCUMULATOR_FEEDER_MIN_SURPLUS:
            continue
        aim = aim_at_target(p, lead, surplus, world.initial_by_id,
                            world.ang_vel, world=world)
        if aim is None:
            continue
        angle, turns = aim
        if turns > ACCUMULATOR_FEEDER_MAX_TRAVEL:
            continue
        feeders.append((turns, surplus, p, angle))

    if not feeders:
        return
    
    feeders.sort(key=lambda x: (x[0], -x[1]))
    fed_count = 0
    for turns, surplus, src, angle in feeders:
        if fed_count >= ACCUMULATOR_MAX_FEEDS_PER_TURN:
            break
        _commit_fleet(world, moves, spent, target_locked,
                      src.id, lead.id, angle, turns, int(surplus))
        mode_log[src.id] = "accumulator-feeder"
        fed_count += 1
    if fed_count > 0:
        if lead.id not in mode_log:
            mode_log[lead.id] = "accumulator-lead"


def handle_regroup(world, available, spent, target_locked, moves, mode_log):
    """Producer-style: move idle surplus from rear planets to frontline planets.

    Only fires from planets that were unclaimed by melis/hammer/accumulator and
    have surplus above the hammer stockpile minimum, so it never disrupts those paths.
    """
    if not REGROUP_ENABLED or world.is_2p:
        return
    if not world.enemy_planets or len(world.my_planets) < 2:
        return
    stockpile_min = world.mode_params.get("hammer_stockpile_min", 50)
    for src in world.my_planets:
        src_mode = mode_log.get(src.id)
        if src_mode and src_mode not in ("absorb",):
            continue  # already dispatched or reserved
        raw_surplus = available[src.id] - spent[src.id]
        above = raw_surplus - stockpile_min
        if above < REGROUP_MIN_ABOVE_STOCKPILE:
            continue
        # Only regroup from genuinely rear planets
        src_min_en = min(dist(src.x, src.y, ep.x, ep.y) for ep in world.enemy_planets)
        if src_min_en <= REGROUP_REAR_DIST_MIN:
            continue  # already frontline, don't regroup away
        # Find closest own planet that is closer to enemies than src
        best_tgt = None
        best_travel = float('inf')
        for tgt in world.my_planets:
            if tgt.id == src.id:
                continue
            tgt_min_en = min(dist(tgt.x, tgt.y, ep.x, ep.y) for ep in world.enemy_planets)
            if tgt_min_en >= src_min_en:
                continue  # not closer to frontline
            travel = dist(src.x, src.y, tgt.x, tgt.y)
            if travel < best_travel:
                best_travel = travel
                best_tgt = tgt
        if best_tgt is None:
            continue
        send = max(1, int(above * REGROUP_SEND_FRACTION))
        aim = aim_at_target(src, best_tgt, send, world.initial_by_id, world.ang_vel, world=world)
        if aim is None:
            continue
        angle, turns = aim
        if turns > REGROUP_MAX_TRAVEL:
            continue
        _commit_fleet(world, moves, spent, target_locked, src.id, best_tgt.id, angle, turns, send)
        mode_log[src.id] = "regroup"


def handle_mega_hammer(world, available, spent, target_locked, moves, mode_log):
    if not MEGA_HAMMER_ENABLED:
        return
    if MEGA_HAMMER_4P_ONLY and world.is_2p:
        return
    
    sources = sorted(world.my_planets,
                     key=lambda p: -(available[p.id] - spent[p.id]))
    fired_targets = set()
    fired_count = 0
    for src in sources:
        if MEGA_HAMMER_CONCENTRATE_ENABLED and fired_count >= MEGA_HAMMER_MAX_PER_TURN:
            break
        avail = available[src.id] - spent[src.id]
        prod = int(src.production)
        if FRESH_CAPTURE_INHERITANCE_ENABLED and src.id in _planet_capture_age:
            threshold = MEGA_HAMMER_SHIPS_MIN_FRESH
        else:
            threshold = MEGA_HAMMER_THRESHOLD_BY_PROD.get(prod, MEGA_HAMMER_SHIPS_MIN)
        if avail < threshold:
            continue  
        status = mode_log.get(src.id)
        if status and status not in ("cheap-pickup", "brain-reserved-lead"):
            continue
        
        best = None
        for tgt in world.enemy_planets:
            if tgt.id in target_locked or tgt.id in fired_targets:
                continue
            if int(tgt.ships) > MEGA_HAMMER_TARGET_GARRISON_MAX_ITER_H:
                continue
            aim = aim_at_target(src, tgt, avail, world.initial_by_id,
                                world.ang_vel, world=world)
            if aim is None:
                continue
            angle, turns = aim
            if turns > MEGA_HAMMER_MAX_TRAVEL:
                continue
            focus_bonus = 0
            if (F14_4A_2P_FOCUS_ENABLED and world.is_2p
                    and getattr(world, "focus_enemy_2p", None) is not None
                    and tgt.owner == world.focus_enemy_2p):
                focus_bonus = F14_4A_2P_FOCUS_MEGA_BONUS
            score = (int(tgt.production) + focus_bonus, -int(turns))
            if best is None or score > best[0]:
                best = (score, tgt, angle, turns)
        if best is None:
            continue
        _, tgt, angle, turns = best
        
        if MEGA_HAMMER_MELIS_VERIFY and turns > 0:
            proj = forward_project(
                world,
                our_capture_target=tgt.id,
                our_capture_turn=int(turns),
                our_capture_ships=int(avail),
                horizon=FWD_SIM_HORIZON + int(turns),
                project_opponent_moves=True,
                opponent_emit_fraction=MEGA_HAMMER_VERIFY_OPP_EMIT,
            )
            end_owner, _ = proj.get(tgt.id, (-1, 0))
            if end_owner != world.player:
                continue
        _commit_fleet(world, moves, spent, target_locked,
                      src.id, tgt.id, angle, turns, int(avail))
        mode_log[src.id] = "mega-hammer-launched"
        mode_log[tgt.id] = "mega-hammer-target"
        fired_targets.add(tgt.id)
        fired_count += 1


def handle_hammer(world, available, spent, target_locked, moves, mode_log):
    global _hammer_plan
    if not HAMMER_ENABLED:
        return
    if not world.enemy_planets:
        _hammer_plan = None
        return

    if _hammer_plan is not None:
        target = world.planet_by_id.get(_hammer_plan["target_id"])
        if target is None or target.owner == world.player:
            _hammer_plan = None
        else:
            arrival_rel = _hammer_plan["target_arrival_abs"] - world.step
            if arrival_rel <= 0:
                _hammer_plan = None
            else:
                d_owner, d_ships = predict_defender_at_arrival(world, target, arrival_rel)
                if d_ships > _hammer_plan["committed_strength"] / HAMMER_ABORT_OVERRUN_RATIO:
                    _hammer_plan = None

    if _hammer_plan is None:
        if not _hammer_should_fire(world):
            return
        plan = _build_hammer_plan(world, available, spent)
        if plan is None:
            return
        
        if HAMMER_MELIS_VERIFY:
            target = world.planet_by_id.get(plan["target_id"])
            if target is not None:
                arrival_rel = plan["target_arrival_abs"] - world.step
                if arrival_rel > 0:
                    proj = forward_project(
                        world,
                        our_capture_target=plan["target_id"],
                        our_capture_turn=int(arrival_rel),
                        our_capture_ships=int(plan["committed_strength"]),
                        horizon=FWD_SIM_HORIZON + arrival_rel,
                        project_opponent_moves=True,
                        opponent_emit_fraction=0.30,
                    )
                    end_owner, _ = proj.get(plan["target_id"], (-1, 0))
                    if end_owner != world.player:
                        return  
        _hammer_plan = plan

    plan = _hammer_plan
    completed_launches = []
    for src_id, launch in list(plan["launches"].items()):
        if launch.get("fired"):
            continue
        if launch["fire_turn_abs"] > world.step:
            continue  
        src = world.planet_by_id.get(src_id)
        if src is None or src.owner != world.player:
            completed_launches.append(src_id)
            continue
        ships = launch["ships"]
        if ships < HAMMER_MIN_PER_CONTRIBUTOR:
            completed_launches.append(src_id)
            continue
        avail = available[src_id] - spent[src_id]
        if avail < ships:
            completed_launches.append(src_id)
            continue
        target = world.planet_by_id[plan["target_id"]]
        aim = aim_at_target(src, target, ships, world.initial_by_id, world.ang_vel, world=world)
        if aim is None:
            completed_launches.append(src_id)
            continue
        angle, turns = aim
        _commit_fleet(world, moves, spent, target_locked,
                      src_id, plan["target_id"], angle, turns, int(ships))
        mode_log[src_id] = "hammer"
        launch["fired"] = True

    for sid in completed_launches:
        plan["launches"].pop(sid, None)
    if not plan["launches"] or all(l.get("fired") for l in plan["launches"].values()):
        _hammer_plan = None


def _hammer_should_fire(world):
    if world.is_late:
        return True
    threshold = world.mode_params["hammer_prod_share"]
    if world.my_prod_share < threshold:
        return False
    return True


def _build_hammer_plan(world, available, spent):
    stockpile_min = world.mode_params.get("hammer_stockpile_min", HAMMER_STOCKPILE_MIN)
    stockpiles = []
    for p in world.my_planets:
        avail = _routine_avail(world, p, available[p.id] - spent[p.id])
        if avail < HAMMER_MIN_PER_CONTRIBUTOR:
            continue
        promoted = p.id in _promoted_stockpiles
        if avail < stockpile_min and not promoted:
            continue
        stockpiles.append((p, avail))
    if not stockpiles:
        return None

    overkill = LATE_FLUSH_OVERKILL_RATIO if world.is_late else world.mode_params["hammer_overkill"]

    _gbc_base = _gbc_feat_vec(world) if (GBC_V2_ENABLED or (GBC_4P_ENABLED and not world.is_2p)) else None

    _gbc_4p_pwin = None
    if GBC_4P_GATE_ENABLED and not world.is_2p:
        _gbc_4p_feat = _gbc_feat_vec(world)
        _gbc_4p_pwin = _gbc_4p_predict(_gbc_4p_feat)

    # Map: enemy_owner -> ships they have in transit toward OTHER enemies (not neutrals, not us).
    # An enemy attacking another enemy has depleted their own garrison — their planets are more
    # vulnerable than predict_defender shows (which only sees fleets heading to our target).
    _battle_bonus_map = {}
    if not world.is_2p and BATTLE_BONUS_ENABLED:
        for planet_id, arrivals in world.arrivals_by_planet.items():
            planet = world.planet_by_id.get(planet_id)
            if planet is None or planet.owner == world.player or planet.owner == -1:
                continue
            for _, owner, ships in arrivals:
                if owner == world.player or owner == -1 or owner == planet.owner:
                    continue
                # enemy 'owner' is attacking enemy 'planet.owner' → owner is overextended
                _battle_bonus_map[owner] = _battle_bonus_map.get(owner, 0) + ships

    targets = [
        p for p in world.enemy_planets
        if is_targetable(world, p) and p.production >= HAMMER_TARGET_PROD_MIN
    ]
    if not targets:
        if world.is_late:
            targets = [p for p in world.enemy_planets if is_targetable(world, p)]
        if not targets:
            return None

    best = None
    for tgt in targets:
        per_src = []
        for src, avail in stockpiles:
            aim = aim_at_target(src, tgt, max(1, avail), world.initial_by_id, world.ang_vel, world=world)
            if aim is None:
                continue
            angle, turns = aim
            if turns > HAMMER_MAX_TRAVEL:
                continue
            per_src.append((turns, src, avail, angle))
        if not per_src:
            continue
        per_src.sort()
        target_arrival = per_src[-1][0]
        if (_gbc_4p_pwin is not None
                and _gbc_4p_pwin < GBC_4P_DANGER_THRESH
                and target_arrival > GBC_4P_DANGER_MAX_TRAVEL):
            continue
        d_owner, d_ships = predict_defender_at_arrival(world, tgt, target_arrival)
        if d_owner == world.player:
            continue
        required = int(math.ceil(d_ships * overkill)) + 1

        accum = 0
        chosen = []
        for turns, src, avail, angle in per_src:
            chosen.append((turns, src, avail, angle))
            accum += avail
            if accum >= required:
                break
        if accum < required:
            continue

        slack = accum - required
        if slack > 0 and chosen:
            last_turn, last_src, last_avail, last_angle = chosen[-1]
            oversend_active = (
                HAMMER_NO_THREAT_OVERSEND_ENABLED
                and (not HAMMER_NO_THREAT_OVERSEND_2P_ONLY or world.is_2p)
            )
            last_src_threat = sum(
                int(ships) for eta, owner, ships
                in world.arrivals_by_planet.get(last_src.id, [])
                if owner != world.player and owner != -1
            )
            safe_surplus_ok = (
                HAMMER_SAFE_SURPLUS_OVERSEND_ENABLED
                and last_avail >= required * HAMMER_SAFE_SURPLUS_RATIO
                and last_src_threat <= last_avail * HAMMER_OVERSEND_MAX_THREAT_RATIO
            )
            if safe_surplus_ok:
                pass
            elif oversend_active and HAMMER_ALWAYS_OVERSEND_2P and world.is_2p:
                pass
            elif oversend_active and last_src_threat == 0:
                pass
            else:
                trimmed = last_avail - slack
                if trimmed < HAMMER_MIN_PER_CONTRIBUTOR:
                    chosen.pop()
                    if not chosen or sum(c[2] for c in chosen) < required - last_avail:
                        chosen.append((last_turn, last_src, last_avail, last_angle))
                else:
                    chosen[-1] = (last_turn, last_src, trimmed, last_angle)

        score = required - target_arrival * 0.5 + int(tgt.production) * HAMMER_PROD_WEIGHT
        if GBC_V2_ENABLED and _gbc_base is not None:
            score += _gbc_delta(_gbc_base, tgt, required, world) * GBC_V2_WEIGHT
        if GBC_4P_ENABLED and not world.is_2p and _gbc_base is not None:
            score += _gbc_4p_delta(_gbc_base, tgt, required, world) * GBC_4P_WEIGHT

        if (F14_4A_2P_FOCUS_ENABLED and world.is_2p
                and getattr(world, "focus_enemy_2p", None) is not None
                and tgt.owner == world.focus_enemy_2p):
            score += F14_4A_2P_FOCUS_HAMMER_BONUS
        
        if FLEET_INTENT_ENABLED and tgt.id in _enemy_recently_launched:
            score += FLEET_INTENT_HAMMER_BONUS

        if R1_RECAPTURE_PRIORITY_ENABLED and tgt.id in _freshly_lost_planets:
            score += R1_RECAPTURE_HAMMER_BONUS

        if HAMMER_EMIT_ENABLED and not world.is_2p:
            opp_prof = getattr(world, 'opp_profile', {}).get(tgt.owner, {})
            emit_hist = opp_prof.get('emit', [])
            if len(emit_hist) >= 3:
                lb = min(HAMMER_EMIT_LOOKBACK, len(emit_hist))
                avg_emit = sum(emit_hist[-lb:]) / lb
                if avg_emit > HAMMER_EMIT_THRESH:
                    score += HAMMER_EMIT_BONUS

        if not world.is_2p and BATTLE_BONUS_ENABLED:
            if _battle_bonus_map.get(tgt.owner, 0) >= BATTLE_BONUS_MIN_SHIPS:
                score += BATTLE_BONUS_SCORE

        if not world.is_2p:
            my_strength = world.owner_strength.get(world.player, 0)
            enemy_strengths = [
                (world.owner_strength[o], o)
                for o in world.owner_strength
                if o not in (-1, world.player) and world.owner_strength[o] > 0
            ]
            if enemy_strengths:
                max_enemy_strength, max_enemy_owner = max(enemy_strengths)
                if max_enemy_strength > my_strength and tgt.owner == max_enemy_owner:
                    score = score - abs(score) * 0.3
            # Bonus for targeting a nearly-eliminated enemy (≤3 planets).
            if HAMMER_4P_WEAK_BONUS > 0:
                tgt_pl = world.owner_planet_count.get(tgt.owner, 99)
                if tgt_pl <= 3:
                    score += HAMMER_4P_WEAK_BONUS
            if HAMMER_4P_VULTURE_BONUS > 0:
                for v_eta, v_owner, v_ships in world.arrivals_by_planet.get(tgt.id, []):
                    if (v_owner not in (-1, world.player, tgt.owner)
                            and v_ships >= 10
                            and v_eta < target_arrival):
                        score += HAMMER_4P_VULTURE_BONUS
                        break
        cand = {
            "target_id": tgt.id,
            "target_arrival_abs": world.step + target_arrival,
            "committed_strength": sum(c[2] for c in chosen),
            "score": score,
            "launches": {},
        }
        for turns, src, ships, angle in chosen:
            fire_turn_rel = target_arrival - turns
            cand["launches"][src.id] = {
                "fire_turn_abs": world.step + fire_turn_rel,
                "ships": int(ships),
                "angle": float(angle),
                "fired": False,
            }
        if best is None or cand["score"] > best["score"]:
            best = cand
    return best


def handle_multiprong(world, available, spent, target_locked, moves, mode_log):
    """[COUNCIL] Enabled: MULTIPRONG_ENABLED is now True. This forces opponents
    to split defense: defend the hammer target and lose the secondary, or
    defend the secondary and the hammer lands clean.

    [COUNCIL] Note: _hammer_plan is set by handle_hammer which runs BEFORE
    multiprong in the pipeline, so this will correctly see the active plan.
    """
    if not MULTIPRONG_ENABLED:
        return
    if MULTIPRONG_2P_ONLY and not world.is_2p:
        return
    if _hammer_plan is None:
        return

    target_id = _hammer_plan.get("target_id")
    target = world.planet_by_id.get(target_id)
    if target is None or target.owner == world.player or target.owner == -1:
        return
    arrival_rel = _hammer_plan.get("target_arrival_abs", world.step) - world.step
    if arrival_rel <= 0:
        return
    committed = int(_hammer_plan.get("committed_strength", 0))
    if committed <= 0:
        return

    reinforcer_ships = defaultdict(int)
    for f in world.fleets:
        if int(f.ships) <= 0:
            continue
        if f.owner == world.player or f.owner == -1:
            continue
        ftarget, _eta = fleet_target_planet(
            f, world.planets, world.initial_by_id, world.ang_vel,
            _cache_step=world.step
        )
        if ftarget is None or ftarget.id != target_id:
            continue
        reinforcer_ships[int(f.from_planet_id)] += int(f.ships)
    if not reinforcer_ships:
        return

    _, defender_at_arrival = predict_defender_at_arrival(world, target, arrival_rel)
    needed_t = int(math.ceil(defender_at_arrival)) + 1
    deficit = max(0, needed_t - committed)
    min_reinforce = max(1, int(math.ceil(deficit * MULTIPRONG_REINFORCER_MIN_RATIO)))

    candidates = []
    for src_id, ship_count in reinforcer_ships.items():
        src = world.planet_by_id.get(src_id)
        if src is None:
            continue
        if src.owner == world.player or src.owner == -1:
            continue
        if ship_count < min_reinforce:
            continue
        candidates.append((src, ship_count))
    if not candidates:
        return
    
    candidates.sort(key=lambda kv: kv[1], reverse=True)

    for reinforcer, in_flight in candidates:
        if reinforcer.id in target_locked:
            continue
        if not is_targetable(world, reinforcer):
            continue
        prong = _build_multiprong_attack(
            world, reinforcer, available, spent, target_locked
        )
        if prong is None:
            continue
        prong_strength, prong_arrival, prong_landings, e_at_arrival = prong

        if prong_strength <= e_at_arrival * MULTIPRONG_E_OVERKILL:
            continue
        needed_e = int(math.ceil(e_at_arrival)) + 1
        if committed + prong_strength < needed_t + int(round(needed_e * MULTIPRONG_CREDIBILITY_FACTOR)):
            continue

        for src_id, src, angle, ships, turns in prong_landings:
            _commit_fleet(
                world, moves, spent, target_locked,
                src_id, reinforcer.id, angle, turns, int(ships),
            )
            mode_log[src_id] = "multiprong"
        mode_log[reinforcer.id] = "multiprong-target"
        return  


def _build_multiprong_attack(world, target, available, spent, target_locked):
    sources = []
    for src in world.my_planets:
        avail = available[src.id] - spent[src.id]
        if avail < MULTIPRONG_MIN_PER_CONTRIBUTOR:
            continue
        aim = aim_at_target(src, target, max(MULTIPRONG_MIN_PER_CONTRIBUTOR, avail), world.initial_by_id, world.ang_vel, world=world)
        if aim is None:
            continue
        _angle, est_turns = aim
        if est_turns > MULTIPRONG_MAX_TRAVEL:
            continue
        sources.append((est_turns, src, avail))
    if not sources:
        return None
    sources.sort(key=lambda kv: kv[0])

    chosen = []
    for est_turns, src, avail in sources[:MULTIPRONG_MAX_PARTICIPANTS]:
        chosen.append((est_turns, src, avail))
        common_arrival = max(t for t, _, _ in chosen)
        _, e_at_arrival = predict_defender_at_arrival(world, target, common_arrival)
        total_avail = sum(a for _, _, a in chosen)
        required = int(math.ceil(e_at_arrival * MULTIPRONG_E_OVERKILL)) + 1
        if total_avail >= required:
            break
    common_arrival = max(t for t, _, _ in chosen)
    _, e_at_arrival = predict_defender_at_arrival(world, target, common_arrival)
    required = int(math.ceil(e_at_arrival * MULTIPRONG_E_OVERKILL)) + 1
    total_avail = sum(a for _, _, a in chosen)
    if total_avail < required:
        return None

    slack = total_avail - required
    if slack > 0 and chosen:
        last_turn, last_src, last_avail = chosen[-1]
        trimmed = last_avail - slack
        if trimmed >= MULTIPRONG_MIN_PER_CONTRIBUTOR:
            chosen[-1] = (last_turn, last_src, trimmed)

    landings = []
    final_strength = 0
    for est_turns, src, ships in chosen:
        if ships < MULTIPRONG_MIN_PER_CONTRIBUTOR:
            return None
        aim = aim_at_target(src, target, ships, world.initial_by_id, world.ang_vel, world=world)
        if aim is None:
            return None
        angle, turns = aim
        if turns > MULTIPRONG_MAX_TRAVEL:
            return None
        landings.append((src.id, src, angle, int(ships), int(turns)))
        final_strength += int(ships)

    final_arrival = max(turns for _, _, _, _, turns in landings)
    _, final_defender = predict_defender_at_arrival(world, target, final_arrival)
    final_required = int(math.ceil(final_defender * MULTIPRONG_E_OVERKILL)) + 1
    if final_strength < final_required:
        return None

    return final_strength, final_arrival, landings, final_defender


def plan_moves(world, deadline=None):
    global _planet_idle_counts, _promoted_stockpiles, _pending_commitments

    def _commitment_viable(c):
        if c["arrival_abs"] <= world.step:
            return False
        target = world.planet_by_id.get(c["target_id"])
        if target is None:
            return False
        if target.owner == world.player:
            return False
        if FAILTOLERANT_ENABLED:
            owner_at_commit = c.get("owner_at_commit")
            if owner_at_commit is not None:
                current_owner = int(target.owner)
                # [COUNCIL] Bug fix: enemy-to-enemy ownership trades should NOT
                # prune a valid attack commitment. Only prune if:
                # (a) the planet flipped to neutral (-1), or
                # (b) the planet is now ours (world.player).
                # Previously: any owner change triggered prune, abandoning valid
                # attacks when opponents traded planets between themselves.
                if current_owner == -1:
                    return False   # neutral — commitment type changed
                if current_owner == world.player:
                    return False   # we already own it — no need to attack
                # Enemy → different enemy: commitment still valid
        return True

    _pending_commitments[:] = [c for c in _pending_commitments if _commitment_viable(c)]

    _update_neutral_watchlist(world)

    moves = []
    spent = defaultdict(int)
    target_locked = set()
    mode_log = {}

    rescue_needs = {}
    available = {}
    for p in world.my_planets:
        arrivals = world.arrivals_by_planet.get(p.id, [])
        reserve, holds, deficit, dline = compute_planet_reserve(
            p, arrivals, world.player
        )
        available[p.id] = max(0, int(p.ships) - reserve)
        if not holds:
            rescue_needs[p.id] = (deficit, dline, p)
            mode_log[p.id] = "absorb-need-rescue"
        elif arrivals:
            mode_log[p.id] = "absorb"

    def _over_budget():
        return deadline is not None and time.perf_counter() >= deadline

    handle_comet_evac(world, available, spent, target_locked, moves, mode_log)

    handle_defense(world, rescue_needs, available, spent, target_locked,
                   moves, mode_log)

    _brain_reserve_lead(world, available, spent, mode_log)

    if not _over_budget():
        if not (SEARCH_EXPAND_4P_ENABLED and not world.is_2p
                and SEARCH_DISABLES_CHEAP_PICKUP):
            handle_cheap_pickup(world, available, spent, target_locked, moves, mode_log)

    if not _over_budget() and not world.survival_mode_4p:
        handle_expand(world, available, spent, target_locked, moves, mode_log,
                      deadline=deadline)

    if not _over_budget():
        handle_snipe(world, available, spent, target_locked, moves, mode_log)

    if not _over_budget():
        handle_accumulator(world, available, spent, target_locked, moves, mode_log)

    if not _over_budget():
        handle_mega_hammer(world, available, spent, target_locked, moves, mode_log)

    if not _over_budget():
        handle_hammer(world, available, spent, target_locked, moves, mode_log)

    if not _over_budget():
        handle_multiprong(world, available, spent, target_locked, moves, mode_log)

    if not _over_budget():
        handle_regroup(world, available, spent, target_locked, moves, mode_log)

    for p in world.my_planets:
        if mode_log.get(p.id) and "absorb" not in mode_log[p.id]:
            _planet_idle_counts[p.id] = 0
        else:
            _planet_idle_counts[p.id] = _planet_idle_counts.get(p.id, 0) + 1
            if _planet_idle_counts[p.id] >= HAMMER_SURROUNDED_PROMOTE_TURNS:
                _promoted_stockpiles.add(p.id)

    return moves


def agent(obs, config=None):
    global _agent_step, _hammer_plan, _planet_idle_counts, _promoted_stockpiles, _pending_commitments
    global _game_num_players, _2p_patient_streak, _2p_prod_share_history
    global _opp_profile
    global _fleet_target_cache, _fleet_target_cache_step

    obs_step = _read(obs, "step", 0) or 0
    if obs_step == 0:
        _agent_step = 0
        _hammer_plan = None
        _planet_idle_counts = {}
        _promoted_stockpiles = set()
        _pending_commitments = []
        _snipe_commitments.clear()
        _snipe_log.clear()
        _game_num_players = None
        _2p_patient_streak = 0
        _2p_prod_share_history = []
        _neutral_prev_ships.clear()
        _neutral_wounded.clear()
        _enemy_prev_ships.clear()
        _enemy_recently_launched.clear()
        _planet_prev_owner.clear()
        _freshly_lost_planets.clear()
        _opp_profile = {}
        # [COUNCIL] Clear fleet target cache on game reset
        _fleet_target_cache.clear()
        _fleet_target_cache_step = -1
    _agent_step += 1

    start = time.perf_counter()
    world = World(obs, inferred_step=_agent_step - 1)
    if not world.my_planets:
        return []

    if not world.is_2p:
        _update_opp_profile_4p(world)

    act_timeout = _read(config, "actTimeout", 1.0) if config is not None else 1.0
    soft_budget = max(0.5, act_timeout * SOFT_DEADLINE_FRACTION)
    deadline = start + soft_budget

    return plan_moves(world, deadline=deadline)


__all__ = ["agent", "Planet", "Fleet"]