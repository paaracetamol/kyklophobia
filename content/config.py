root = None


CHUNK_SZ          = 16
CHUNK_H           = 128
SEA_LEVEL         = 64
WATER_OFF         = 4
WATER_TOP         = 0 #0.8       # TODO water top state
WATER_PLANE       = 1000.0

TERRAIN_SCL_X     = 0.010
TERRAIN_SCL_Z     = 0.010
TERRAIN_SCL_Y     = 0.015

WIN_W             = 1280         # f11 fullscreen
WIN_H             = 720

SUN_SZ            = 80.0
HLIGHT_SCL        = 1.002
LINE_W            = 3.0

RENDER_DIST       = 10
SEED              = 12345
BREAK_T           = 0.3
RAYCAST_DIST      = 5.0


HARDNESS          = 1.0
MINE_MULT         = 1.5          # sec p hardpoint
CRACK_SCL         = 1.008
HURT_T            = 0.5

# popoffs
POP_SCL           = 0.024        # scale 3.0 * 0.008
POP_YOFF          = 2.25         # bbox top + 0.5
POP_DRIFT         = 0.032        # motion x/z after 0.12 norm
POP_LIFE          = 0.6

POP_VY            = 2.4          # 0.12 p tick
POP_G             = -12.8        # 0.04 * particleGravity 0.8, p tick

POP_GROWR         = 4.6          # 1.08 p frame @60
POP_SHRINKR       = 2.45         # 0.96 p frame @60
POP_MAXMUL        = 3.0
CRIT_DIV          = 2.5


FOV               = 70.0
N_PLANE           = 0.1
F_PLANE           = 500.0
SENSIVITY         = 0.15
MOUS_SMOOTH       = 0.5






SV_PORT           = 25250
SV_HOST           = "0.0.0.0"
SV_RATE           = 30           # tick rate
SV_MAXONLINE      = 20
SV_MOTD           = "A Kyklophobia Server\nRunning v{VERSION}, {PLAYER_COUNT} online"
SV_TIMEOUT        = 10.0
SV_PVP            = True
CL_UPD_INT        = 0.033


P_W               = 0.6
P_H               = 1.8
P_EYE_H           = 1.62
P_EYE_F           = 0.0

# tick model
# p/20hz tick
TICK              = 0.05
TICK_CATCHUP      = 5

GRAV              = 0.08
DRAG_Y            = 0.98
FRIC_AIR          = 0.91
FRIC_TILE         = 0.6          # block slip *0.91 -> 0.546
FRIC_ICE          = 0.98
FRIC_SLIME        = 0.8
ACC_BASE          = 0.16277136
AIR_ACC           = 0.02
AIR_SPRINT        = 0.3          # air acc += air acc * AIR_SPRINT
WALK_SPD          = 0.1
SPRINT_MUL        = 1.3
SNEAK_MUL         = 0.3
JUMP_YD           = 0.42
SPRINT_JUMP       = 0.2
STEP_H            = 0.6
SNEAK_EYE         = 0.08         # eye dip, 1.62 -> 1.54

FLY_SPD           = 0.05
FLY_YD            = 0.15
FLY_SPRINT        = 2.0
FLY_DRAG_Y        = 0.6
FLY_FRIC          = 0.91

WATER_ACC         = 0.02
WATER_DRAG        = 0.8
WATER_GRAV        = 0.02
WATER_JUMP        = 0.04
LAVA_DRAG         = 0.5
LEDGE_YD          = 0.3

LADDER_CLAMP      = 0.15
LADDER_CLIMB      = 0.2

SPRINT_TRIG       = 7            # double tap window
FOOD_SPRINT       = 6
JUMP_TRIG         = 7            # double tap window
NOJUMP_DELAY      = 10
PUSHOUT           = 0.1


# old model
GRAVITY           = -32.0
TERM_V            = -78.4
JUMP_V            = 10.0
MAX_GSPEED        = 4.3          # ground
MAX_FSPEED        = 4.3          # fly
MP_SPRINT         = 1.75
FL_SPEED          = 12.0
FL_SPEED_MP       = 2.5


SURF_FRIC         = 0.50
AIR_RES           = 0.98
SURF_ACCEL        = 0.25
AIR_ACCEL         = 0.03
FL_ACCEL          = 0.6
FL_FRIC           = 0.85


SCL_HUD           = 3
SCL_FONT          = 2
FONTPATH          = None         # resolve at runtime
CHAT_MAX          = 10
CHAT_FADETIME     = 5.0
CHAT_LIFETIME     = 8.0





PART_MAXCOUNT     = 500
PART_PERBLOCK     = 20
PART_LF_MIN       = 0.5
PART_LF_MAX       = 1.0
PART_SZ_MIN       = 0.08
PART_SZ_MAX       = 0.15
PART_SPEED        = 3.0
PART_G            = -15.0



DROP_SZ           = 0.45
DROP_PICKUP_DELAY = 0.5
DROP_PICKUP_RANGE = 1.5
DROP_LIFETIME     = 300.0        # 5 mins
DROP_BOBSPEED     = 2.5 
DROP_BOBHEIGHT    = 0.1 
DROP_SPIN         = 1.5
DROP_G            = -20.0
DROP_F            = 0.8



# entities
ENT_GRAV          = -32.0
ENT_TERMVEL       = -78.4
ENT_IVELY         = 4.0
ENT_DRAG          = 0.98
ENT_FRIC          = 0.60
ENT_STEP          = 0.6
ENT_EPS           = 0.001
ENT_STILLV        = 0.02
ENT_EASE          = 10.0
ENT_REACH         = 4.0
KNOCK_H           = 6.0          # knockback
KNOCK_V           = 4.5
KNOCK_T           = 0.3






# performance tuning
# adjust values based on hardware.

# these settings were tested on:
# Lenovo IdeaPad L340 Gaming
# iCore i7 9gen, GeforceGTX 1050

CHUNK_WORKERS     = 8            # numba nogil workers
CHUNK_PARALLEL    = 32           # parallel gen cap
CHUNK_MESH_PTICK  = 16           # cap mesh build p/ thread iter


CHUNK_UPLD_BUDG_L = 0.016        # small Q, 16ms = 1 frame @60fps
CHUNK_UPLD_BUDG_H = 0.100        # large Q, 100ms -> fast
CHUNK_UPLD_CAP    = 16  
CHUNK_UPD_CACHE_D = 2.0          # min dist := refresh visible chunk cache

VERTEX_BUFF_POOL_SZ = 32         # prealloc buffs
VERTEX_BUFF_CAP_SZ  = 1_500_000  # float cap p vert buff

