import heapq
import threading
import json
import math
import os
import numpy as np
from collections import deque

from config import CHUNK_SZ, CHUNK_H, TICK
from world.blocks import (
    REDSTONE_WIRE, REDSTONE_BLOCK, REDSTONE_LAMP, REDSTONE_LAMP_ON,
    REDSTONE_TORCH_ON, REDSTONE_TORCH_OFF, REPEATER, COMPARATOR,
    LEVER, STONE_BUTTON, WOODEN_BUTTON, TNT, GLOWSTONE,
    STONE_PRESSURE_PLATE, WOODEN_PRESSURE_PLATE,
    LIGHT_WEIGHTED_PRESSURE_PLATE, HEAVY_WEIGHTED_PRESSURE_PLATE,
    OAK_DOOR_BOTTOM, OAK_DOOR_TOP, IRON_DOOR_BOTTOM, IRON_DOOR_TOP,
    SPRUCE_DOOR_BOTTOM, SPRUCE_DOOR_TOP, BIRCH_DOOR_BOTTOM, BIRCH_DOOR_TOP,
    JUNGLE_DOOR_BOTTOM, JUNGLE_DOOR_TOP, ACACIA_DOOR_BOTTOM, ACACIA_DOOR_TOP,
    DARK_OAK_DOOR_BOTTOM, DARK_OAK_DOOR_TOP,
    OAK_TRAPDOOR, IRON_TRAPDOOR,
    OAK_FENCE_GATE, SPRUCE_FENCE_GATE, BIRCH_FENCE_GATE,
    JUNGLE_FENCE_GATE, ACACIA_FENCE_GATE, DARK_OAK_FENCE_GATE,
    PISTON, STICKY_PISTON, PISTON_HEAD, MOVING_PISTON, SLIME, POWERED_RAIL, POWERED_RAIL_ON,
    OBSIDIAN, BEDROCK, CHEST, TRAPPED_CHEST, ENDER_CHEST, FURNACE, FURNACE_ON,
    DISPENSER, DROPPER, HOPPER, WATER, WATER_FLOWING, LAVA, LAVA_FLOWING, FIRE,
    TALLGRASS, TORCH, RAIL, DETECTOR_RAIL, ACTIVATOR_RAIL, TRIPWIRE,
    OAK_LEAVES, BIRCH_LEAVES, SPRUCE_LEAVES, JUNGLE_LEAVES, ACACIA_LEAVES, DARK_OAK_LEAVES,
    SAPLING_OAK, SAPLING_SPRUCE, SAPLING_BIRCH, SAPLING_JUNGLE, SAPLING_ACACIA, SAPLING_DARK_OAK,
    DANDELION, POPPY, BLUE_ORCHID, ALLIUM, AZURE_BLUET, RED_TULIP, ORANGE_TULIP, WHITE_TULIP, PINK_TULIP, OXEYE_DAISY,
    BROWN_MUSHROOM, RED_MUSHROOM, DEAD_BUSH, FERN, SUNFLOWER, LILAC, DOUBLE_TALLGRASS, LARGE_FERN, ROSE_BUSH, PEONY,
    CACTUS, PUMPKIN, JACK_O_LANTERN, MELON, CAKE, COBWEB, LADDER, VINE, LILY_PAD, SUGAR_CANE, COCOA, DRAGON_EGG,
    WHEAT_STAGE_7, CARROTS_STAGE_3, POTATOES_STAGE_3, NETHER_WART_STAGE_2, TRIPWIRE_HOOK,
    BED_HEAD, BED_FOOT, BARRIER, COMMAND_BLOCK, END_PORTAL_FRAME, ANVIL, ANVIL_SLIGHTLY_DAMAGED, ANVIL_VERY_DAMAGED,
    NOTEBLOCK, JUKEBOX, MOB_SPAWNER, BEACON, ENCHANTING_TABLE, BREWING_STAND_BLOCK, SIGN_STANDING,
    DAYLIGHT_DETECTOR, DAYLIGHT_DETECTOR_INVERTED, OBSERVER,
)
from world.mesh import BLOCK_OPAC
from world.container import Tiles, SIZES
import items.textures as _IT
from items.registry import REGISTRY
from world.renderers.registry import BLOCK_MODE_RENDER




DOWN, UP, NORTH, SOUTH, WEST, EAST = 0, 1, 2, 3, 4, 5
DIRS = ((0,-1,0), (0,1,0), (0,0,-1), (0,0,1), (-1,0,0), (1,0,0))
OPP  = (UP, DOWN, SOUTH, NORTH, EAST, WEST)
NOTIFY = (WEST, EAST, DOWN, UP, NORTH, SOUTH)
HOR  = (NORTH, EAST, SOUTH, WEST)
CW   = {NORTH: EAST, EAST: SOUTH, SOUTH: WEST, WEST: NORTH}
CCW  = {NORTH: WEST, WEST: SOUTH, SOUTH: EAST, EAST: NORTH}

FACEDIR = (NORTH, SOUTH, EAST, WEST)



# state layouts 5b
#wire      pppp   power
#repeater  pddff  powered, delay1, facing
#torch     aaa    attach
#lever     paaa   powered, attach
ATT_FLOOR, ATT_CEIL = 0, 5
ATTDIR = (UP, NORTH, SOUTH, EAST, WEST, DOWN)
ON_BIT = 8

TORCHES  = (REDSTONE_TORCH_ON, REDSTONE_TORCH_OFF)
BUTTONS  = (STONE_BUTTON, WOODEN_BUTTON)
ATTACHED = (LEVER, STONE_BUTTON, WOODEN_BUTTON) + TORCHES
PLATES   = (STONE_PRESSURE_PLATE, WOODEN_PRESSURE_PLATE, LIGHT_WEIGHTED_PRESSURE_PLATE, HEAVY_WEIGHTED_PRESSURE_PLATE)
SOURCES  = frozenset(
    (
        REDSTONE_BLOCK, COMPARATOR, LEVER, STONE_BUTTON, 
        WOODEN_BUTTON,  TRAPPED_CHEST, OBSERVER, TRIPWIRE_HOOK, 
        DETECTOR_RAIL, DAYLIGHT_DETECTOR, DAYLIGHT_DETECTOR_INVERTED
    ) + TORCHES + PLATES
)

BTN_T    = {STONE_BUTTON: 20, WOODEN_BUTTON: 30}
TORCH_T  = 2
LAMP_T   = 4
BURN_T   = 60
BURN_MAX = 8
BURN_OFF = 160
CMP_T    = 2
TRIP_T   = 10
HOOK_MAX = 42
OBS_T    = 2
DISP_T   = 4
TRIG_BIT = 8
PLATE_T  = 20
WPLATE_T = 10
PUSH_MAX = 12
RAIL_MAX = 8
MAX_UPD  = 65536 #ptick
CATCHUP  = 5


# door/trapdoor/gate state
# ff, 4=open, 8=top 16=powered
OPEN_BIT = 4
PW_BIT   = 16

# comparator state
# ff, 4=subtract, 8=powered
SUB_BIT  = 4

# piston
# 8=extend
EXT_BIT  = 8

DOORS = {
    OAK_DOOR_BOTTOM: OAK_DOOR_TOP, IRON_DOOR_BOTTOM: IRON_DOOR_TOP,
    SPRUCE_DOOR_BOTTOM: SPRUCE_DOOR_TOP, BIRCH_DOOR_BOTTOM: BIRCH_DOOR_TOP,
    JUNGLE_DOOR_BOTTOM: JUNGLE_DOOR_TOP, ACACIA_DOOR_BOTTOM: ACACIA_DOOR_TOP,
    DARK_OAK_DOOR_BOTTOM: DARK_OAK_DOOR_TOP,
}
DOORTOPS = {j: i for i, j in DOORS.items()}
IRONDOOR = (IRON_DOOR_BOTTOM, IRON_DOOR_TOP, IRON_TRAPDOOR)
TRAPS    = (OAK_TRAPDOOR, IRON_TRAPDOOR)
GATES    = (OAK_FENCE_GATE, SPRUCE_FENCE_GATE, BIRCH_FENCE_GATE, JUNGLE_FENCE_GATE, ACACIA_FENCE_GATE, DARK_OAK_FENCE_GATE)
OPENABLE = frozenset(tuple(DOORS) + tuple(DOORTOPS) + TRAPS + GATES)
PISTONS  = (PISTON, STICKY_PISTON)
RAILS    = (POWERED_RAIL, POWERED_RAIL_ON)
WEIGHTED = {LIGHT_WEIGHTED_PRESSURE_PLATE: 1, HEAVY_WEIGHTED_PRESSURE_PLATE: 10}


NOCOLLIDE = frozenset((
    REDSTONE_WIRE, REPEATER, COMPARATOR, LEVER, STONE_BUTTON, WOODEN_BUTTON, TORCH, TRIPWIRE, TRIPWIRE_HOOK,
) + TORCHES + PLATES + RAILS + (RAIL, DETECTOR_RAIL, ACTIVATOR_RAIL))

# tables
PUSH_HARD = frozenset((BEDROCK, BARRIER, COMMAND_BLOCK, END_PORTAL_FRAME)) # hardness -1
PUSH_NEVER = frozenset((ANVIL, ANVIL_SLIGHTLY_DAMAGED, ANVIL_VERY_DAMAGED, PISTON_HEAD, MOVING_PISTON))
# material or override
PUSH_POP = frozenset((
    WATER, WATER_FLOWING, LAVA, LAVA_FLOWING, FIRE, TALLGRASS, TRIPWIRE,
    REDSTONE_WIRE, REPEATER, COMPARATOR, TORCH, LEVER, STONE_BUTTON, WOODEN_BUTTON, TRIPWIRE_HOOK,
    OAK_LEAVES, BIRCH_LEAVES, SPRUCE_LEAVES, JUNGLE_LEAVES, ACACIA_LEAVES, DARK_OAK_LEAVES,
    SAPLING_OAK, SAPLING_SPRUCE, SAPLING_BIRCH, SAPLING_JUNGLE, SAPLING_ACACIA, SAPLING_DARK_OAK,
    DANDELION, POPPY, BLUE_ORCHID, ALLIUM, AZURE_BLUET, RED_TULIP, ORANGE_TULIP, WHITE_TULIP, PINK_TULIP, OXEYE_DAISY,
    BROWN_MUSHROOM, RED_MUSHROOM, DEAD_BUSH, FERN, SUNFLOWER, LILAC, DOUBLE_TALLGRASS, LARGE_FERN, ROSE_BUSH, PEONY,
    CACTUS, PUMPKIN, JACK_O_LANTERN, MELON, CAKE, COBWEB, LADDER, VINE, LILY_PAD, SUGAR_CANE, COCOA, DRAGON_EGG,
    WHEAT_STAGE_7, CARROTS_STAGE_3, POTATOES_STAGE_3, NETHER_WART_STAGE_2, BED_HEAD, BED_FOOT,
) + TORCHES + PLATES + tuple(DOORS) + tuple(DOORTOPS))
# has tile entity
PUSH_TILE = frozenset((
    CHEST, TRAPPED_CHEST, ENDER_CHEST, FURNACE, FURNACE_ON, DISPENSER, DROPPER, HOPPER, NOTEBLOCK, JUKEBOX,
    MOB_SPAWNER, BEACON, ENCHANTING_TABLE, BREWING_STAND_BLOCK, SIGN_STANDING, DAYLIGHT_DETECTOR, DAYLIGHT_DETECTOR_INVERTED,
))








def extbox(f):
    a  = {DOWN: 1, UP: 1, NORTH: 2, SOUTH: 2, WEST: 0, EAST: 0}[f]
    lo, hi = [0.0, 0.0, 0.0], [1.0, 1.0, 1.0]
    if f in (UP, SOUTH, EAST): hi[a] = 0.75
    else: lo[a] = 0.25

    return (*lo, *hi)




def headboxes(f):
    a  = {DOWN: 1, UP: 1, NORTH: 2, SOUTH: 2, WEST: 0, EAST: 0}[f]
    pl = [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
    sh = [[0.375, 0.375, 0.375], [0.625, 0.625, 0.625]]

    if f in (UP, SOUTH, EAST):
        pl[0][a], sh[0][a], sh[1][a] = 0.75, -0.25, 0.75
    else:
        pl[1][a], sh[0][a], sh[1][a] = 0.25, 0.25, 1.25

    return [(*pl[0], *pl[1]), (*sh[0], *sh[1])]




POPITEM = {
    REDSTONE_WIRE: _IT.REDSTONE, REPEATER: _IT.REPEATER, COMPARATOR: _IT.COMPARATOR,
    REDSTONE_TORCH_OFF: REDSTONE_TORCH_ON, REDSTONE_LAMP_ON: REDSTONE_LAMP,
    POWERED_RAIL_ON: POWERED_RAIL,
}

DAYS = (DAYLIGHT_DETECTOR, DAYLIGHT_DETECTOR_INVERTED)



#midclick get
def pickitem(v):
    b = int(v) & 0x3FF
    if b in POPITEM: return POPITEM[b]
    if b == TRIPWIRE: return _IT.STRING
    if b == PISTON_HEAD: return STICKY_PISTON if (int(v) >> 10) & 8 else PISTON
    if b in DOORTOPS: b = DOORTOPS[b]
    # placed by an item, hopper, cauldron, doors, sign -> item, NOT (Block)
    for i in REGISTRY._items.values():
        if i.places_block == b and i.category != "variants": 
            return i.itemId
    return b



WATCH = np.array(sorted(set((
    REDSTONE_WIRE, REPEATER, COMPARATOR, OBSERVER, HOPPER, DISPENSER, DROPPER, ACTIVATOR_RAIL,
    REDSTONE_LAMP, REDSTONE_LAMP_ON, TNT, PISTON, STICKY_PISTON,
    POWERED_RAIL, POWERED_RAIL_ON, *TORCHES, *DAYS,
))), dtype=np.int32)



NS, EW, ASC_E, ASC_W, ASC_N, ASC_S, SE, SW, NW, NE = range(10)
ALLRAILS = frozenset((RAIL, POWERED_RAIL, POWERED_RAIL_ON, DETECTOR_RAIL, ACTIVATOR_RAIL))
RAILPW   = 16


def railshape(v):
    s = state(v) & 15
    if s > 9 or (s > 5 and bid(v) != RAIL): return NS
    return s






class Rail:
    def __init__(self, rs, x, y, z, v):
        self.rs  = rs
        self.p   = (x, y, z)
        self.v   = v
        self.bad = bid(v) != RAIL
        self.setconn(railshape(v))


    def setconn(self, d):
        x, y, z = self.p
        n, s_, w, e = (x, y, z - 1), (x, y, z + 1), (x - 1, y, z), (x + 1, y, z)
        up = lambda p: (p[0], p[1] + 1, p[2])

        self.c = {
            NS: [n, s_], EW: [w, e], 
            ASC_E: [w, up(e)],  ASC_W: [up(w), e],
            ASC_N: [up(n), s_], ASC_S: [n, up(s_)],
            SE: [e, s_], SW: [w, s_], NW: [w, n], NE: [e, n],
        }[d]


    def israil(self, p): return bid(self.rs.raw(*p)) in ALLRAILS


    def at(self, p):
        for q in (p, (p[0], p[1] + 1, p[2]), (p[0], p[1] - 1, p[2])):
            v = self.rs.raw(*q)
            if bid(v) in ALLRAILS: return Rail(self.rs, *q, v)

        return None




    def check(self):
        i = 0
        while i < len(self.c):
            r = self.at(self.c[i])
            if r is not None and r.has(self.p):
                self.c[i] = r.p
                i += 1
            else:
                del self.c[i]


    def has(self, p): return any(q[0] == p[0] and q[2] == p[2] for q in self.c)


    #count adjacent
    def count(self):
        x, y, z = self.p
        i = 0
        for q in (
            (x, y, z - 1), (x + 1, y, z), 
            (x, y, z + 1), (x - 1, y, z)
        ):
            if (
                self.israil(q) or 
                self.israil((q[0], q[1] + 1, q[2])) or 
                self.israil((q[0], q[1] - 1, q[2]))
            ): i += 1

        return i




    def canconn(self, o): return self.has(o.p) or len(self.c) != 2


    def write(self, d):
        self.v = (self.rs.raw(*self.p) & ~(15 << 10)) | (d << 10)
        self.rs.put(*self.p, self.v)
        self.rs.notify(*self.p)




    def slope(self, d):
        x, y, z = self.p
        if d == NS:
            if self.israil((x, y + 1, z - 1)): d = ASC_N
            if self.israil((x, y + 1, z + 1)): d = ASC_S

        elif d == EW:
            if self.israil((x + 1, y + 1, z)): d = ASC_E
            if self.israil((x - 1, y + 1, z)): d = ASC_W

        return d





    

    def connect(self, o):
        self.c.append(o.p)
        x, y, z = self.p
        f, f1, f2, f3 = self.has((x, y, z - 1)), self.has((x, y, z + 1)), self.has((x - 1, y, z)), self.has((x + 1, y, z))
        
        d = None
        if f or f1: d = NS
        if f2 or f3: d = EW

        if not self.bad:
            if f1 and f3 and not f and not f2: d = SE
            if f1 and f2 and not f and not f3: d = SW
            if f and f2 and not f1 and not f3: d = NW
            if f and f3 and not f1 and not f2: d = NE

        d = self.slope(d) if d is not None else NS
        self.write(d)




    def linked(self, p):
        r = self.at(p)
        if r is None: return False
        r.check()

        return r.canconn(self)





    

    def place(self, pw, first):
        x, y, z = self.p
        f, f1, f2, f3 = self.linked((x, y, z - 1)), self.linked((x, y, z + 1)), self.linked((x - 1, y, z)), self.linked((x + 1, y, z))
        
        d = None
        if (f or f1) and not f2 and not f3: d = NS
        if (f2 or f3) and not f and not f1: d = EW


        if not self.bad:
            if f1 and f3 and not f and not f2: d = SE
            if f1 and f2 and not f and not f3: d = SW
            if f and f2 and not f1 and not f3: d = NW
            if f and f3 and not f1 and not f2: d = NE


        if d is None:
            if f or f1: d = NS
            if f2 or f3: d = EW
            if not self.bad:
                if pw:
                    if f1 and f3: d = SE
                    if f2 and f1: d = SW
                    if f3 and f:  d = NE
                    if f and f2:  d = NW

                else:
                    if f and f2:  d = NW
                    if f3 and f:  d = NE
                    if f2 and f1: d = SW
                    if f1 and f3: d = SE


        d = self.slope(d) if d is not None else NS
        self.setconn(d)
        if first or railshape(self.rs.raw(*self.p)) != d:
            self.write(d)

            for q in self.c:
                r = self.at(q)
                if r is not None:
                    r.check()
                    if r.canconn(self): 
                        r.connect(self)





class Mov:
    __slots__ = ('x', 'y', 'z', 'v', 'f', 'ext', 'src', 'prog', 'last')

    def __init__(self, x, y, z, v, f, ext, src):
        self.x, self.y, self.z = x, y, z
        self.v, self.f, self.ext, self.src = v, f, ext, src
        self.prog = 0.0
        self.last = 0.0


    
    def shift(self, p): return p - 1.0 if self.ext else 1.0 - p
    def at(self, a):    return self.last + (self.prog - self.last) * min(a, 1.0)


# HashSet<BlockPos> iteration order
# 16 bucket, >= 7 here
def javaset(ps):
    b = {}

    for p in ps:

        h = ((p[1] + p[2] * 31) * 31 + p[0]) & 0xFFFFFFFF
        h = (h ^ (h >> 16)) & 15
        c = b.setdefault(h, [])
        if p not in c: c.append(p)

    return [p for i in sorted(b) for p in b[i]]


FULLBOX = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)



# x0, y0, z0, x1, y1, z1
def boxhit(a, b):
    return a[0] < b[3] and a[3] > b[0] and a[1] < b[4] and a[4] > b[1] and a[2] < b[5] and a[5] > b[2]


def boxunion(a, b):
    return (
        min(a[0], b[0]), min(a[1], b[1]), 
        min(a[2], b[2]), max(a[3], b[3]), 
        max(a[4], b[4]), max(a[5], b[5])
    )






def sweep(b, d, amt):
    i  = {DOWN: 1, UP: 1, NORTH: 2, SOUTH: 2, WEST: 0, EAST: 0}[d]
    r  = list(b)
    pos = DIRS[d][i] > 0

    d0 = amt if pos else -amt
    fc = b[i + 3] if pos else b[i]
    r[i], r[i + 3] = fc + min(d0, 0.0), fc + max(d0, 0.0)

    return tuple(r)




def pushdist(b, d, e):
    i = {DOWN: 1, UP: 1, NORTH: 2, SOUTH: 2, WEST: 0, EAST: 0}[d]
    return b[i + 3] - e[i] if DIRS[d][i] > 0 else e[i + 3] - b[i]


def bid(v):   return int(v) & 0x3FF
def state(v): return (int(v) >> 10) & 0x1F
def pack(i, s): return i | (s << 10) | 0x8000





class Redstone:
    def __init__(self, cm):
        self.cm      = cm
        self.accum   = 0.0
        self.now     = 0
        self.evs     = deque() # thread edits
        self.nq      = deque() # neigbour updates
        self.sched   = []
        self.pend    = set()
        self.seq     = 0
        self.dirty   = set()
        self.burn    = deque() # torch toggles
        self.wirepow = True

        self.onflush = None
        self.ontnt   = None
        self.ondrop  = None
        self.bodies  = None       # -> iter x, y, z, halfw, living
        self.cout    = {}         # comparator out
        self.plate   = {}         # plate pos -> [all, living] @ tick
        self.bev     = [[], []]
        self.bevi    = 0
        self.moving  = {}         # pos -> Mov
        self.anims   = deque()    # net thread -> client tick
        self.movers  = None       # -> iter box, move(dx, dy, dz), vel(axis, v)
        self.spawn   = None       # (iid, count, pos, vel/sec)
        self.itemsin = None       # box -> iter iid, count, setcount
        self.tiles   = Tiles(self)
        self.lock    = threading.RLock()
        self.notepw  = {}
        self.railpw  = {}
        self.spawnq  = deque()
        self.cartseen = {}
        self.onnote  = None
        self.sunangle = lambda: 90.0
        self.days    = set()
        self.loadq   = deque()
        self.schedok = False
        self.onmove  = None
        self.pushing = None







    def reset(self):
        self.evs.clear()
        self.nq.clear()
        self.sched.clear()
        self.pend.clear()
        self.dirty.clear()
        self.burn.clear()
        self.cout.clear()
        self.plate.clear()
        self.bev = [[], []]
        self.moving.clear()
        self.anims.clear()
        self.tiles.reset()
        self.days.clear()
        self.loadq.clear()
        self.schedok = False


    def live(self): return not self.cm.netmode



    # world
    def raw(self, x, y, z):
        if y < 0 or y >= CHUNK_H: return 0

        c = self.cm.chunks.get((x // CHUNK_SZ, z // CHUNK_SZ))
        if not c or not c.gen_ready: return 0

        return int(c.voxels[x - c.offset_x, y, z - c.offset_z])




    def loaded(self, x, y, z):
        c = self.cm.chunks.get((x // CHUNK_SZ, z // CHUNK_SZ))
        return c is not None and c.gen_ready


    def put(self, x, y, z, v):
        c = self.cm.chunks.get((x // CHUNK_SZ, z // CHUNK_SZ))
        if not c or not c.gen_ready or y < 0 or y >= CHUNK_H: return

        o = c.voxels[x - c.offset_x, y, z - c.offset_z]
        c.voxels[x - c.offset_x, y, z - c.offset_z] = v
        self.dirty.add((x, y, z))

        if int(o) & 0x7FFF != int(v) & 0x7FFF: self.observed(x, y, z)


    
    #observed neighbor
    def observed(self, x, y, z):
        for d in range(6):
            nx, ny, nz = self.off(x, y, z, d)
            n = self.raw(nx, ny, nz)

            if bid(n) == OBSERVER and state(n) & 7 == OPP[d] and not state(n) & 8:
                self.schedule(nx, ny, nz, OBSERVER, OBS_T)




    
    def blocked(self, x0, y0, z0, x1, y1, z1):
        for _ in self.colboxes(x0, y0, z0, x1, y1, z1): return True
        return False








    def colboxes(self, x0, y0, z0, x1, y1, z1):
        e = (x0, y0, z0, x1, y1, z1)

        for x in range(math.floor(x0), math.ceil(x1)):
            for y in range(math.floor(y0), math.ceil(y1)):
                for z in range(math.floor(z0), math.ceil(z1)):
                    
                    v = self.raw(x, y, z)
                    b = bid(v)
                    if b in PISTONS and state(v) & EXT_BIT: bx = (extbox(state(v) & 7),)
                    elif b == PISTON_HEAD:                  bx = headboxes(state(v) & 7)
                    elif self.cm.iscollide(x, y, z):        bx = (FULLBOX,)
                    else: continue


                    for i in bx:
                        o = (
                            x + i[0], y + i[1], 
                            z + i[2], x + i[3], 
                            y + i[4], z + i[5]
                        )
                        if boxhit(e, o): yield o



        if not self.moving: return


        for m in list(self.moving.values()):
            if m.src and not m.ext:
                i = extbox(m.f)
                o = (
                    m.x + i[0], m.y + i[1], 
                    m.z + i[2], m.x + i[3], 
                    m.y + i[4], m.z + i[5]
                )
                if boxhit(e, o): yield o


            #doesnt collide
            if m.prog < 1.0 and self.pushing == (m.f if m.ext else OPP[m.f]): continue

            s = m.shift(m.prog)
            o = DIRS[m.f]
            for i in self.movboxes(m):
                ox, oy, oz = m.x + s * o[0], m.y + s * o[1], m.z + s * o[2]
                u = (
                    ox + i[0], oy + i[1], 
                    oz + i[2], ox + i[3], 
                    oy + i[4], oz + i[5]
                )
                if boxhit(e, u): yield u




    def cube(self, x, y, z):
        v = self.raw(x, y, z)
        b = bid(v)
        if b in PISTONS: return not state(v) & EXT_BIT
        if b in (DISPENSER, DROPPER): return True
        return b != 0 and b not in SOURCES and BLOCK_MODE_RENDER[b] == 0 and BLOCK_OPAC[b] == 255




    # worker
    # find sensors && wakes redstone on border
    def chunkready(self, c):
        if self.cm.netmode: return

        mask = np.isin(c.voxels & 0x3FF, WATCH)
        if not mask.any(): return

        for lx, y, lz in zip(*np.nonzero(mask)):
            x, z = c.offset_x + int(lx), c.offset_z + int(lz)
            b = int(c.voxels[lx, y, lz]) & 0x3FF

            if b in DAYS: self.days.add((x, int(y), z))
            if lx in (0, CHUNK_SZ - 1) or lz in (0, CHUNK_SZ - 1): 
                self.loadq.append((x, int(y), z))





    
    def schedfile(self): return os.path.join(self.cm.world_dir, "redstone.ticks")


    def savesched(self):
        if not self.cm.is_server: return

        d = [[x, y, z, i, t - self.now, p] for t, p, _, x, y, z, i in self.sched]
        fp = self.schedfile()

        if d:
            with open(fp, 'w') as f: json.dump(d, f)
        elif os.path.exists(fp): os.remove(fp)




    def loadsched(self):
        self.schedok = True
        if not self.cm.is_server or not os.path.exists(self.schedfile()): return

        with open(self.schedfile()) as f: d = json.load(f)
        for x, y, z, i, t, p in d: self.schedule(x, y, z, i, max(t, 1), p)



    

    def daytick(self):
        for p in list(self.days):
            b = bid(self.raw(*p))

            if self.loaded(*p) and b not in DAYS:
                self.days.discard(p)
                continue


            if b in DAYS: self.dayupd(*p, b)


    
    

    def skyat(self, x, y, z):
        c = self.cm.chunks.get((x // CHUNK_SZ, z // CHUNK_SZ))
        if not c: return 0

        if not self.cm.headless: 
            return int(c.light[x - c.offset_x, y, z - c.offset_z])

        col = c.voxels[x - c.offset_x, y + 1:, z - c.offset_z] & 0x3FF

        return 15 if not np.any(BLOCK_OPAC[col] != 0) else 0







    
    def dayupd(self, x, y, z, b):
        ang = (self.sunangle() - 90.0) / 360.0 % 1.0
        br  = 1.0 - (math.cos(ang * math.pi * 2.0) * 2.0 + 0.5)
        sub = int(max(0.0, min(1.0, br)) * 11.0)

        i   = self.skyat(x, y, z) - sub
        f   = ang * math.pi * 2.0
        inv = b == DAYLIGHT_DETECTOR_INVERTED

        if inv: i = 15 - i
        if i > 0 and not inv:
            f1 = 0.0 if f < math.pi else math.pi * 2.0
            f  = f + (f1 - f) * 0.2
            i  = round(i * math.cos(f))


        i = max(0, min(15, i))
        v = self.raw(x, y, z)

        if state(v) != i:
            self.put(x, y, z, (v & ~(0x1F << 10)) | (i << 10))
            self.notify(x, y, z)




    
    

    def doorhinge(self, x, y, z, b, st, hx, hz):
        f  = FACEDIR[st & 3]
        o  = DIRS[f]

        rt = (o[0] < 0 and hz < 0.5) or (o[0] > 0 and hz > 0.5) or (o[2] < 0 and hx > 0.5) or (o[2] > 0 and hx < 0.5)
        cw, ccw = self.off(x, y, z, CW[f]), self.off(x, y, z, CCW[f])
        up = lambda p: (p[0], p[1] + 1, p[2])
        ty = DOORS[b]

        i  = int(self.cube(*ccw)) + int(self.cube(*up(ccw)))
        j  = int(self.cube(*cw))  + int(self.cube(*up(cw)))
        isd = lambda p: bid(self.raw(*p)) in (b, ty)

        fl  = isd(ccw) or isd(up(ccw))
        fl1 = isd(cw)  or isd(up(cw))


        if (not fl or fl1) and j <= i:
            if (fl1 and not fl) or j < i: rt = False
        else:
            rt = True

        return rt


    # edits
    def onset(self, x, y, z, old, new):
        if self.live() and (int(old) & 0x7FFF) != (int(new) & 0x7FFF):
            self.evs.append((x, y, z, int(old), int(new)))


    def update(self, dt):
        self.accum += dt
        n = 0

        while self.accum >= TICK and n < CATCHUP:
            self.accum -= TICK
            n += 1

            if self.live():
                with self.lock: self.tick()
            else:
                self.animtick()


        if n >= CATCHUP: self.accum = 0.0




    def tick(self):
        self.now += 1
        while self.spawnq:
            i = self.spawnq.popleft()
            if self.spawn: self.spawn(*i)

        self.detectscan()
        if not self.schedok: self.loadsched()

        while self.loadq: self.nq.append(self.loadq.popleft())

        if self.now % 20 == 0: self.daytick()
        self.platescan()
        self.drain()



        while self.sched and self.sched[0][0] <= self.now:
            _, _, _, x, y, z, i = heapq.heappop(self.sched)

            # wauit
            if not self.nearloaded(x, z):
                self.seq += 1
                heapq.heappush(self.sched, (self.now + 1, 0, self.seq, x, y, z, i))
                break

            self.pend.discard((x, y, z, i))
            b = bid(self.raw(x, y, z))
            if b == i or (b in TORCHES and i in TORCHES): self.ontick(x, y, z, b)
            self.drain()



        self.runevents()
        self.tileticks()
        self.tiles.hoptick()
        self.containerq()
        self.drain()
        self.flush()

        if self.now % 20 == 0:
            self.tiles.save()
            self.savesched()





    
    def containerq(self):
        tl = self.tiles

        while tl.chg:
            x, y, z = tl.chg.popleft()
            if tl.onchg: tl.onchg(x, y, z)


            for d in HOR:
                nx, ny, nz = self.off(x, y, z, d)
                if not self.loaded(nx, ny, nz): continue
                
                b = bid(self.raw(nx, ny, nz))
                if b == COMPARATOR: self.nq.append((nx, ny, nz))
                elif self.cube(nx, ny, nz):
                    q = self.off(nx, ny, nz, d)
                    if bid(self.raw(*q)) == COMPARATOR: 
                        self.nq.append(q)



        while tl.vq:
            x, y, z, b = tl.vq.popleft()
            self.notify(x, y, z)

            if b == TRAPPED_CHEST: self.notify(x, y - 1, z)




    def drain(self, n=0):
        while (self.evs or self.nq) and n < MAX_UPD:
            n += 1
            rest = self.nq
            self.nq = deque()

            if self.evs: 
                self.onedit(*self.evs.popleft())
            else:
                i = rest.popleft()
                self.neighbour(*i)


            new     = self.nq
            self.nq = rest
            self.nq.extendleft(reversed(new))




    def flush(self):
        if not self.dirty: return

        chgs = [(x, y, z, self.raw(x, y, z)) for x, y, z in self.dirty]
        self.dirty.clear()
        self.cm.setblocks(chgs, _rs=False)
        

        
        for x, y, z, b in chgs:
            m = self.moving.get((x, y, z))
            if m and bid(b) == MOVING_PISTON:
                cx, cz = x // CHUNK_SZ, z // CHUNK_SZ
                self.cm.recordmod(cx, cz, x - cx * CHUNK_SZ, y, z - cz * CHUNK_SZ, m.v)

        if self.onflush: self.onflush(chgs)




    # helpers
    def schedule(self, x, y, z, i, d, prio=0):
        k = (x, y, z, i)
        if k in self.pend: return
        self.pend.add(k)
        self.seq += 1
        heapq.heappush(self.sched, (self.now + d, prio, self.seq, x, y, z, i))


    def pending(self, x, y, z, i): return (x, y, z, i) in self.pend


    def off(self, x, y, z, d):
        o = DIRS[d]
        return x + o[0], y + o[1], z + o[2]


    def notify(self, x, y, z, skip=-1):
        for d in NOTIFY:
            if d != skip:
                o = DIRS[d]
                self.nq.append((x + o[0], y + o[1], z + o[2]))


    
    
    def notify2(self, x, y, z):
        self.notify(x, y, z)
        for d in range(6): self.notify(*self.off(x, y, z, d))


    def pop(self, x, y, z, v):
        self.put(x, y, z, 0)
        self.evs.append((x, y, z, v, 0))
        if self.ondrop: self.ondrop(x, y, z, bid(v))



    # queries, side = dir
    def weak(self, x, y, z, side):
        v = self.raw(x, y, z)
        b = bid(v)


        if b == REDSTONE_WIRE:     return self.wireweak(x, y, z, state(v), side)
        if b == REDSTONE_TORCH_ON: return 15 if ATTDIR[state(v) & 7] != side else 0
        if b == REDSTONE_BLOCK:    return 15
        if b == REPEATER:
            return 15 if state(v) & 16 and FACEDIR[state(v) & 3] == side else 0
        if b == LEVER or b in BUTTONS:
            return 15 if state(v) & ON_BIT else 0
        if b == COMPARATOR:
            return self.cmpout(x, y, z, v) if state(v) & ON_BIT and FACEDIR[state(v) & 3] == side else 0

        if b in PLATES:        return self.platelvl(v)
        if b == TRAPPED_CHEST: return self.tiles.chestviews(x, y, z)
        if b == OBSERVER:      return 15 if state(v) & 8 and state(v) & 7 == side else 0
        if b in DAYS:          return state(v) & 15
        if b == TRIPWIRE_HOOK: return 15 if state(v) & 8 else 0
        if b == DETECTOR_RAIL: return 15 if state(v) & RAILPW else 0

        return 0







    def strong(self, x, y, z, side):
        v = self.raw(x, y, z)
        b = bid(v)

        if b == REDSTONE_WIRE:     return self.weak(x, y, z, side) if self.wirepow else 0
        if b == REDSTONE_TORCH_ON: return self.weak(x, y, z, side) if side == DOWN else 0
        if b == REPEATER:          return self.weak(x, y, z, side)
        if b == LEVER or b in BUTTONS:
            return 15 if state(v) & ON_BIT and ATTDIR[state(v) & 7] == side else 0
        if b == COMPARATOR:    return self.weak(x, y, z, side)
        if b in PLATES:        return self.platelvl(v) if side == UP else 0
        if b == TRAPPED_CHEST: return self.weak(x, y, z, side) if side == UP else 0
        if b == OBSERVER:      return self.weak(x, y, z, side)
        if b == TRIPWIRE_HOOK: return 15 if state(v) & 8 and FACEDIR[state(v) & 3] == side else 0
        if b == DETECTOR_RAIL: return 15 if state(v) & RAILPW and side == UP else 0

        return 0


    def strongin(self, x, y, z):
        m = 0
        for d in range(6):
            nx, ny, nz = self.off(x, y, z, d)
            m = max(m, self.strong(nx, ny, nz, d))
            if m >= 15: break
        return m


    def side(self, x, y, z, d):
        if self.cube(x, y, z): return self.strongin(x, y, z)
        return self.weak(x, y, z, d)


    def powered(self, x, y, z):
        for d in range(6):
            nx, ny, nz = self.off(x, y, z, d)
            if self.side(nx, ny, nz, d) > 0: return True
        return False


    def indirect(self, x, y, z):
        m = 0
        for d in range(6):
            nx, ny, nz = self.off(x, y, z, d)
            m = max(m, self.side(nx, ny, nz, d))
            if m >= 15: return 15
        return m



    # wire
    def wirelink(self, v, d=None):
        b = bid(v)
        if b == REDSTONE_WIRE: return True

        if b == REPEATER:
            f = FACEDIR[state(v) & 3]
            return d is not None and (f == d or OPP[f] == d)

        if b == OBSERVER: return d == state(v) & 7
        return b in SOURCES and d is not None




    def wireconn(self, x, y, z, d):
        nx, ny, nz = self.off(x, y, z, d)
        v  = self.raw(nx, ny, nz)
        nc = self.cube(nx, ny, nz)

        if not self.cube(x, y + 1, z) and nc and self.wirelink(self.raw(nx, ny + 1, nz)): return True
        if self.wirelink(v, d): return True
        if bid(v) == REPEATER and state(v) & 16 and FACEDIR[state(v) & 3] == d: return True

        return not nc and self.wirelink(self.raw(nx, ny - 1, nz))


    def wireweak(self, x, y, z, pw, side):
        if not self.wirepow or pw == 0: return 0
        if side == UP: return pw

        conn = [d for d in HOR if self.wireconn(x, y, z, d)]
        if side != DOWN and not conn: return pw

        if side in conn and CCW[side] not in conn and CW[side] not in conn: 
            return pw


        return 0






    def wirelvl(self, x, y, z, m):
        v = self.raw(x, y, z)
        return max(m, state(v) & 15) if bid(v) == REDSTONE_WIRE else m


    def wireupd(self, x, y, z):
        v = self.raw(x, y, z)
        i = state(v) & 15
        j = i

        self.wirepow = False
        k = self.indirect(x, y, z)
        self.wirepow = True
        if k > 0 and k > j - 1: j = k


        l = 0
        upc = self.cube(x, y + 1, z)
        for d in HOR:
            nx, ny, nz = self.off(x, y, z, d)
            l = self.wirelvl(nx, ny, nz, l)
            nc = self.cube(nx, ny, nz)
            
            if nc and not upc: l = self.wirelvl(nx, ny + 1, nz, l)
            elif not nc:       l = self.wirelvl(nx, ny - 1, nz, l)

        if l > j:    j = l - 1
        elif j > 0:  j -= 1
        else:        j = 0

        if k > j - 1: j = k


        if i != j:
            self.put(x, y, z, (v & ~(0x1F << 10)) | (j << 10))
            for i in javaset([(x, y, z)] + [self.off(x, y, z, d) for d in range(6)]):
                self.notify(*i)




    def wirenear(self, x, y, z):
        if bid(self.raw(x, y, z)) == REDSTONE_WIRE: self.notify2(x, y, z)


    def wirearound(self, x, y, z):
        for d in HOR:
            self.wirenear(*self.off(x, y, z, d))

        for d in HOR:
            nx, ny, nz = self.off(x, y, z, d)
            if self.cube(nx, ny, nz): 
                self.wirenear(nx, ny + 1, nz)
            else: 
                self.wirenear(nx, ny - 1, nz)





    def topsolid(self, x, y, z):
        return self.cube(x, y, z) or bid(self.raw(x, y, z)) == REDSTONE_BLOCK


    def wirefloor(self, x, y, z):
        return self.topsolid(x, y - 1, z) or bid(self.raw(x, y - 1, z)) == GLOWSTONE



    # torch
    def torchin(self, x, y, z, v):
        d = OPP[ATTDIR[state(v) & 7]]
        nx, ny, nz = self.off(x, y, z, d)
        return self.side(nx, ny, nz, d) > 0



    def burnt(self, x, y, z, add):
        if add: self.burn.append(((x, y, z), self.now))
        n = 0

        for p, _ in self.burn:
            if p == (x, y, z):
                n += 1
                if n >= BURN_MAX: return True

        return False




    def torchflip(self, x, y, z, v, b):
        self.put(x, y, z, pack(b, state(v)) | (v & 0x8000))
        self.notify2(x, y, z)





    # repeater
    def diodein(self, x, y, z, v):
        d = FACEDIR[state(v) & 3]
        nx, ny, nz = self.off(x, y, z, d)

        i = self.side(nx, ny, nz, d)
        if i >= 15: return True
        
        n = self.raw(nx, ny, nz)
        if bid(n) == REDSTONE_WIRE: i = max(i, state(n) & 15)

        return i > 0




    def locked(self, x, y, z, v):
        f = FACEDIR[state(v) & 3]
        for d in (CW[f], CCW[f]):
            nx, ny, nz = self.off(x, y, z, d)
            n = self.raw(nx, ny, nz)

            if bid(n) in (REPEATER, COMPARATOR) and self.strong(nx, ny, nz, d) > 0: 
                return True

        return False




    def diodeout(self, x, y, z, v):
        f = FACEDIR[state(v) & 3]
        nx, ny, nz = self.off(x, y, z, OPP[f])
        self.nq.append((nx, ny, nz))
        self.notify(nx, ny, nz, skip=f)



    def delay(self, v): return (((state(v) >> 2) & 3) + 1) * 2


    def diodeupd(self, x, y, z, v):
        if self.locked(x, y, z, v): return

        on = bool(state(v) & 16)
        if on == self.diodein(x, y, z, v) or self.pending(x, y, z, REPEATER): 
            return



        f = FACEDIR[state(v) & 3]
        nx, ny, nz = self.off(x, y, z, OPP[f])
        n = self.raw(nx, ny, nz)

        fr = bid(n) in (REPEATER, COMPARATOR) and FACEDIR[state(n) & 3] != OPP[f]
        self.schedule(x, y, z, REPEATER, self.delay(v), -3 if fr else (-2 if on else -1))



    # p block reactions
    def supported(self, x, y, z, v):
        b = bid(v)

        if b == REDSTONE_WIRE: return self.wirefloor(x, y, z)
        if b == TRIPWIRE_HOOK:
            nx, ny, nz = self.off(x, y, z, OPP[FACEDIR[state(v) & 3]])
            return not self.loaded(nx, ny, nz) or self.cube(nx, ny, nz)

        if b == REPEATER or b == COMPARATOR or b in PLATES or b in ALLRAILS:
            return self.topsolid(x, y - 1, z)

        a = state(v) & 7
        if a > ATT_CEIL or (b in TORCHES and a == ATT_CEIL): 
            return False

        nx, ny, nz = self.off(x, y, z, OPP[ATTDIR[a]])
        if not self.loaded(nx, ny, nz): return True

        return self.cube(nx, ny, nz)




    # other half of supported()
    def canplace(self, x, y, z, b, st):
        if bid(self.raw(x, y, z)) == MOVING_PISTON: return False

        if b in (CHEST, TRAPPED_CHEST):
            n = [self.off(x, y, z, d) for d in HOR if bid(self.raw(*self.off(x, y, z, d))) == b]
            if len(n) > 1: return False

            for p in n:
                if any(bid(self.raw(*self.off(*p, d))) == b for d in HOR): 
                    return False


        if b in DOORS:
            return self.cube(x, y - 1, z) and bid(self.raw(x, y + 1, z)) in (0, WATER, WATER_FLOWING, LAVA, LAVA_FLOWING)

        if b in DOORTOPS: 
            return False

        if b == TORCH:
            if st >= ATT_CEIL: return False
            return self.cube(*self.off(x, y, z, OPP[ATTDIR[st]]))


        if b in ALLRAILS: return self.topsolid(x, y - 1, z)
        if b == TRIPWIRE_HOOK and st & 16: return False
        if (
            b == REDSTONE_WIRE or b == REPEATER or 
            b == COMPARATOR or b in ATTACHED or b in PLATES or 
            b in RAILS or b == ACTIVATOR_RAIL or b == TRIPWIRE_HOOK
        ):
            return self.supported(x, y, z, pack(b, st))

        return True





    def nearloaded(self, x, z):
        return (
            self.loaded(x, 0, z) and self.loaded(x + 1, 0, z) and self.loaded(x - 1, 0, z)
            and self.loaded(x, 0, z + 1) and self.loaded(x, 0, z - 1)
        )



    def neighbour(self, x, y, z):
        if not self.nearloaded(x, z): return
        v = self.raw(x, y, z)
        b = bid(v)
        if b == 0: return

        if b in OPENABLE:
            self.openupd(x, y, z, v, b)
            return

        if (
            b == REDSTONE_WIRE or b == REPEATER or 
            b == COMPARATOR or b in ATTACHED or b in PLATES or 
            b in ALLRAILS or b == TRIPWIRE_HOOK
        ):
            if not self.supported(x, y, z, v):
                self.pop(x, y, z, v)
                return

        if b == REDSTONE_WIRE:
            self.wireupd(x, y, z)

        elif b in TORCHES:
            if (b == REDSTONE_TORCH_ON) == self.torchin(x, y, z, v):
                self.schedule(x, y, z, b, TORCH_T)

        elif b == REPEATER: self.diodeupd(x, y, z, v)
        elif b == COMPARATOR: self.cmpupd(x, y, z, v)
        elif b in PISTONS: self.pistonupd(x, y, z, v)


        elif b == PISTON_HEAD:
            nx, ny, nz = self.off(x, y, z, OPP[state(v) & 7])
            n = self.raw(nx, ny, nz)
            if bid(n) not in PISTONS: self.gone(x, y, z)
            else: self.pistonupd(nx, ny, nz, n)
            

        elif b in ALLRAILS:
            self.railupd(x, y, z, v, b)



        elif b in (DISPENSER, DROPPER):
            pw = self.powered(x, y, z) or self.powered(x, y + 1, z)
            on = bool(state(v) & TRIG_BIT)

            if pw and not on:
                self.schedule(x, y, z, b, DISP_T)
                self.put(x, y, z, v | (TRIG_BIT << 10))

            elif not pw and on:
                self.put(x, y, z, v & ~(TRIG_BIT << 10))



        elif b == NOTEBLOCK:
            k  = (x, y, z)
            pw = self.powered(x, y, z)

            if pw != self.notepw.get(k, False):
                if pw and self.onnote: self.onnote(x, y, z, state(v) % 25)
                self.notepw[k] = pw


        elif b == HOPPER:
            en = not self.powered(x, y, z)
            if en == bool(state(v) & 8):
                self.put(x, y, z, v ^ (8 << 10))


        elif b == REDSTONE_LAMP:
            if self.powered(x, y, z): 
                self.put(x, y, z, pack(REDSTONE_LAMP_ON, 0))

        elif b == REDSTONE_LAMP_ON:
            if not self.powered(x, y, z): 
                self.schedule(x, y, z, b, LAMP_T)

        elif b == TNT:
            if self.powered(x, y, z): 
                self.ignite(x, y, z)














    def ontick(self, x, y, z, b):
        v = self.raw(x, y, z)

        if b in TORCHES:
            pw = self.torchin(x, y, z, v)
            while self.burn and self.now - self.burn[0][1] > BURN_T:
                self.burn.popleft()


            if b == REDSTONE_TORCH_ON:
                if pw:
                    self.torchflip(x, y, z, v, REDSTONE_TORCH_OFF)

                    if self.burnt(x, y, z, True):
                        self.schedule(x, y, z, REDSTONE_TORCH_OFF, BURN_OFF)


            elif not pw and not self.burnt(x, y, z, False):
                self.torchflip(x, y, z, v, REDSTONE_TORCH_ON)





        elif b == REPEATER:
            if self.locked(x, y, z, v): return
            pw = self.diodein(x, y, z, v)
            on = bool(state(v) & 16)

            if on and not pw:
                self.setdiode(x, y, z, v, False)
            elif not on:
                self.setdiode(x, y, z, v, True)
                if not pw: 
                    self.schedule(x, y, z, REPEATER, self.delay(v), -1)



        elif b == REDSTONE_LAMP_ON:
            if not self.powered(x, y, z): 
                self.put(x, y, z, pack(REDSTONE_LAMP, 0))

        elif b in BUTTONS:
            if state(v) & ON_BIT:
                nv = v & ~(ON_BIT << 10)
                self.put(x, y, z, nv)
                self.notifyatt(x, y, z, nv)


        elif b == COMPARATOR:
            self.cmptick(x, y, z, v)

        elif b in (DISPENSER, DROPPER):
            self.tiles.dispense(x, y, z, b, state(v) & 7)

        elif b == TRIPWIRE:
            if state(v) & 1: 
                self.tripcheck(x, y, z)

        elif b == TRIPWIRE_HOOK:
            self.hookcalc(x, y, z, v, False, True)

        elif b == DETECTOR_RAIL:
            if state(v) & RAILPW: 
                self.detectupd(x, y, z, v)

        elif b == OBSERVER:

            if state(v) & 8:
                nv = v & ~(8 << 10)
            else:
                nv = v | (8 << 10)
                self.schedule(x, y, z, OBSERVER, OBS_T)

            self.put(x, y, z, nv)
            self.obsout(x, y, z, nv)



        elif b in PLATES:
            self.platetick(x, y, z, v, b)












    # comparator
    def cmpback(self, x, y, z, v):
        d = FACEDIR[state(v) & 3]
        nx, ny, nz = self.off(x, y, z, d)
        i = self.side(nx, ny, nz, d)

        if i < 15:
            n = self.raw(nx, ny, nz)
            if bid(n) == REDSTONE_WIRE: 
                i = max(i, state(n) & 15)

        # trough solid
        if bid(self.raw(nx, ny, nz)) in SIZES:
            i = self.tiles.signal(nx, ny, nz)

        elif i < 15 and self.cube(nx, ny, nz):
            qx, qy, qz = self.off(nx, ny, nz, d)
            if bid(self.raw(qx, qy, qz)) in SIZES: 
                i = self.tiles.signal(qx, qy, qz)
                
        return i




    def cmpside(self, x, y, z, v):
        f = FACEDIR[state(v) & 3]
        m = 0

        for d in (CW[f], CCW[f]):
            nx, ny, nz = self.off(x, y, z, d)
            n = self.raw(nx, ny, nz)

            if bid(n) == REDSTONE_BLOCK:   m = max(m, 15)
            elif bid(n) == REDSTONE_WIRE:  m = max(m, state(n) & 15)
            elif bid(n) in SOURCES or bid(n) == REPEATER:
                m = max(m, self.strong(nx, ny, nz, d))

        return m




    def cmpcalc(self, x, y, z, v):
        i = self.cmpback(x, y, z, v)
        if state(v) & SUB_BIT: 
            return max(i - self.cmpside(x, y, z, v), 0)
        return i




    def cmpon(self, x, y, z, v):
        i = self.cmpback(x, y, z, v)
        if i >= 15: return True
        if i == 0:  return False

        j = self.cmpside(x, y, z, v)
        return j == 0 or i >= j




    # output not in voxel
    # 5bit overflow := missing -> recompute
    def cmpout(self, x, y, z, v):
        k = (x, y, z)
        if k not in self.cout:
            self.cout[k] = self.cmpcalc(x, y, z, v)

        return self.cout[k]




    def cmpupd(self, x, y, z, v):
        if self.pending(x, y, z, COMPARATOR): return
        if (
            self.cmpcalc(x, y, z, v) != self.cmpout(x, y, z, v) or 
            bool(state(v) & ON_BIT) != self.cmpon(x, y, z, v)
        ):
            f = FACEDIR[state(v) & 3]
            n = self.raw(*self.off(x, y, z, OPP[f]))

            fr = bid(n) in (REPEATER, COMPARATOR) and FACEDIR[state(n) & 3] != OPP[f]
            self.schedule(x, y, z, COMPARATOR, CMP_T, -1 if fr else 0)





    def cmptick(self, x, y, z, v):
        i  = self.cmpcalc(x, y, z, v)
        j  = self.cmpout(x, y, z, v)
        on = self.cmpon(x, y, z, v)

        self.cout[(x, y, z)] = i

        if j != i or not state(v) & SUB_BIT:
            was = bool(state(v) & ON_BIT)

            if was and not on:   v = v & ~(ON_BIT << 10)
            elif on and not was: v = v | (ON_BIT << 10)

            self.put(x, y, z, v)
            self.diodeout(x, y, z, v)





    # tripwire
    def tripscan(self):
        for x, y, z, hw, liv, *h in self.bodies():
            h = h[0] if h else 0.25

            for cx in range(math.floor(x - hw), math.floor(x + hw) + 1):
                for cz in range(math.floor(z - hw), math.floor(z + hw) + 1):
                    for cy in range(math.floor(y), math.floor(y + h) + 1):

                        v = self.raw(cx, cy, cz)
                        if bid(v) != TRIPWIRE or state(v) & 1: continue

                        if self.tripin(cx, cy, cz, v, (x, y, z, hw, h)): 
                            self.tripcheck(cx, cy, cz)





    def tripin(self, cx, cy, cz, v, b):
        x, y, z, hw, h = b
        y0, y1 = (cy + 0.0625, cy + 0.15625) if state(v) & 4 else (cy, cy + 0.5)
        return x + hw > cx and x - hw < cx + 1 and z + hw > cz and z - hw < cz + 1 and y + h > y0 and y < y1




    # upd state
    def tripcheck(self, x, y, z):
        v  = self.raw(x, y, z)
        on = bool(state(v) & 1)
        hit = False


        if self.bodies:
            for bx, by, bz, hw, liv, *h in self.bodies():
                if self.tripin(x, y, z, v, (bx, by, bz, hw, h[0] if h else 0.25)):
                    hit = True
                    break


        if hit != on:
            nv = v ^ (1 << 10)
            self.put(x, y, z, nv)
            self.notify(x, y, z)
            self.tripnotify(x, y, z, nv)
            
        if hit: 
            self.schedule(x, y, z, TRIPWIRE, TRIP_T)


    
    # notify hook
    def tripnotify(self, x, y, z, st):
        for d in (SOUTH, WEST):
            for i in range(1, HOOK_MAX):
                p = self.offn((x, y, z), d, i)
                n = self.raw(*p)

                if bid(n) == TRIPWIRE_HOOK:
                    if FACEDIR[state(n) & 3] == OPP[d]: 
                        self.hookcalc(*p, n, False, True, i, st)
                    break

                if bid(n) != TRIPWIRE: break





    
    def hookcalc(self, x, y, z, v, removed, notify, j=-1, jv=None):
        f    = FACEDIR[state(v) & 3]
        was  = bool(state(v) & 4)
        att  = not removed
        pw   = False
        i    = 0
        keep = [None] * HOOK_MAX

        for k in range(1, HOOK_MAX):
            p = self.offn((x, y, z), f, k)
            n = self.raw(*p)

            if bid(n) == TRIPWIRE_HOOK:
                if FACEDIR[state(n) & 3] == OPP[f]: i = k
                break

            if bid(n) != TRIPWIRE and k != j:
                keep[k] = None
                att = False

            else:
                if k == j and jv is not None: n = jv
                armed = not state(n) & 8
                pw |= armed and bool(state(n) & 1)
                keep[k] = n

                if k == j:
                    self.schedule(x, y, z, TRIPWIRE_HOOK, TRIP_T)
                    att &= armed



        att = att and i > 1
        pw  = pw and att
        bits = (4 if att else 0) | (8 if pw else 0)


        if i > 0:
            p  = self.offn((x, y, z), f, i)
            o  = OPP[f]
            self.put(*p, pack(TRIPWIRE_HOOK, FACEDIR.index(o) | bits))
            self.notify(*p)
            self.hooknotify(*p, o)

        if not removed:
            self.put(x, y, z, pack(TRIPWIRE_HOOK, (state(v) & 3) | bits))
            self.notify(x, y, z)
            if notify: self.hooknotify(x, y, z, f)

        if was != att:
            for k in range(1, i):
                p = self.offn((x, y, z), f, k)
                if keep[k] is not None and bid(self.raw(*p)) != 0:
                    n = keep[k]
                    self.put(*p, (n & ~(4 << 10)) | ((4 if att else 0) << 10))
                    self.notify(*p)




    def hooknotify(self, x, y, z, f):
        self.notify(x, y, z)
        self.notify(*self.off(x, y, z, OPP[f]))


    # plates
    def platelvl(self, v):
        return state(v) & 15


    def platescan(self):
        self.plate.clear()
        if not self.bodies: return

        self.tripscan()
        
        for x, y, z, hw, liv, *_ in self.bodies():
            cy = math.floor(y)
            if y - cy >= 0.25: continue

            for cx in range(math.floor(x - hw), math.floor(x + hw) + 1):
                for cz in range(math.floor(z - hw), math.floor(z + hw) + 1):

                    if bid(self.raw(cx, cy, cz)) not in PLATES: continue
                    if x + hw <= cx + 0.0625 or x - hw >= cx + 0.9375: continue
                    if z + hw <= cz + 0.0625 or z - hw >= cz + 0.9375: continue

                    c = self.plate.setdefault((cx, cy, cz), [0, 0])
                    c[0] += 1
                    if liv: c[1] += 1

        for k, c in self.plate.items():
            b = bid(self.raw(*k))
            if self.platewant(b, c) and not state(self.raw(*k)):
                self.platetick(k[0], k[1], k[2], self.raw(*k), b)




    def platewant(self, b, c):
        if b in WEIGHTED: return min(15, (c[0] + WEIGHTED[b] - 1) // WEIGHTED[b])
        n = c[1] if b == STONE_PRESSURE_PLATE else c[0]
        return 15 if n else 0



    def platetick(self, x, y, z, v, b):
        c  = self.plate.get((x, y, z), (0, 0))
        lv = self.platewant(b, c)

        if lv != state(v):
            nv = (v & ~(0x1F << 10)) | (lv << 10)
            self.put(x, y, z, nv)
            self.notify(x, y, z)
            self.notify(x, y - 1, z)

        if lv: 
            self.schedule(x, y, z, b, WPLATE_T if b in WEIGHTED else PLATE_T)





    # doors, trapdoors, gates
    def openupd(self, x, y, z, v, b):
        if b in DOORS:
            t = bid(self.raw(x, y + 1, z))
            if t != DOORS[b] or not self.cube(x, y - 1, z):
                self.pop(x, y, z, v)
                if t == DOORS[b]: self.gone(x, y + 1, z)
                return

            pw = self.powered(x, y, z) or self.powered(x, y + 1, z)

        elif b in DOORTOPS:
            if bid(self.raw(x, y - 1, z)) != DOORTOPS[b]:
                self.gone(x, y, z)
                return

            pw = self.powered(x, y, z) or self.powered(x, y - 1, z)

        else:
            pw = self.powered(x, y, z)

            

        if pw == bool(state(v) & PW_BIT): return

        st = (state(v) & ~PW_BIT) | (PW_BIT if pw else 0)
        st = (st | OPEN_BIT) if pw else (st & ~OPEN_BIT)
        self.setopen(x, y, z, st, b)




    def setopen(self, x, y, z, st, b):
        self.put(x, y, z, (self.raw(x, y, z) & ~(0x1F << 10)) | (st << 10))
        self.notify(x, y, z)

        o = y + 1 if b in DOORS else (y - 1 if b in DOORTOPS else None)
        if o is None: return

        self.put(x, o, z, (self.raw(x, o, z) & ~(0x1F << 10)) | (st << 10))
        self.notify(x, o, z)




    # pistons
    def pistonpow(self, x, y, z, f):
        for d in range(6):
            if d != f:
                nx, ny, nz = self.off(x, y, z, d)
                if self.side(nx, ny, nz, d) > 0: 
                    return True

        if self.side(x, y, z, DOWN) > 0: return True

        # quasi connectivity
        for d in range(6):
            if d != DOWN:
                nx, ny, nz = self.off(x, y + 1, z, d)
                if self.side(nx, ny, nz, d) > 0: 
                    return True

        return False






    
    def pistonupd(self, x, y, z, v):
        f   = state(v) & 7
        pw  = self.pistonpow(x, y, z, f)
        ext = bool(state(v) & EXT_BIT)

        if pw and not ext:
            if self.structure(x, y, z, f, True) is not None: 
                self.addevent(x, y, z, bid(v), 0)

        elif not pw and ext:
            self.addevent(x, y, z, bid(v), 1)



    

    def addevent(self, x, y, z, b, i):
        e = (x, y, z, b, i)
        if e not in self.bev[self.bevi]: 
            self.bev[self.bevi].append(e)


    def runevents(self):
        while self.bev[self.bevi]:
            i = self.bevi
            self.bevi ^= 1

            for x, y, z, b, j in self.bev[i]:
                if bid(self.raw(x, y, z)) == b: 
                    self.pistonevent(x, y, z, b, j)

                self.drain()
            self.bev[i] = []




    
    def pistonevent(self, x, y, z, b, i):
        v  = self.raw(x, y, z)
        f  = state(v) & 7
        pw = self.pistonpow(x, y, z, f)
        

        if pw and i == 1:
            self.put(x, y, z, v | (EXT_BIT << 10))
            return

        if not pw and i == 0: return

        if i == 0:
            if not self.pushmove(x, y, z, f, True): return
            self.put(x, y, z, v | (EXT_BIT << 10))
            self.notify(x, y, z)
            return


        hx, hy, hz = self.off(x, y, z, f)
        m = self.moving.get((hx, hy, hz))
        if m: self.finish(m)

        self.put(x, y, z, pack(MOVING_PISTON, 0))
        self.notify(x, y, z)
        self.addmov(x, y, z, (v & ~(0x1F << 10)) | (f << 10), f, False, True)

        if b == STICKY_PISTON:
            nx, ny, nz = self.off(hx, hy, hz, f)
            n = self.raw(nx, ny, nz)
            done = False

            if bid(n) == MOVING_PISTON:
                m2 = self.moving.get((nx, ny, nz))
                if m2 and m2.f == f and m2.ext:
                    self.finish(m2)
                    done = True

            if (
                not done and bid(n) != 0 and 
                self.canpush(nx, ny, nz, n, OPP[f], False, f) and 
                bid(n) not in PUSH_POP
            ):
                self.pushmove(x, y, z, f, False)

        else:
            self.edit(hx, hy, hz, 0)







    
    def canpush(self, x, y, z, v, d, destroy, only):
        b = bid(v)
        if b == OBSIDIAN or not self.loaded(x, y, z): return False
        if y < 0 or (d == DOWN and y == 0): return False
        if y > CHUNK_H - 1 or (d == UP and y == CHUNK_H - 1): return False

        if b in PISTONS:
            if state(v) & EXT_BIT: return False
        else:
            if b in PUSH_HARD or b in PUSH_NEVER: return False
            if b in PUSH_POP: return destroy

        return b not in PUSH_TILE




    
    
    def structure(self, x, y, z, f, ext):
        mv    = f if ext else OPP[f]
        start = self.off(x, y, z, f) if ext else self.off(*self.off(x, y, z, f), f)
        h = (mv, (x, y, z), [], [])

        v = self.raw(*start)
        if not self.canpush(*start, v, mv, False, mv):
            if bid(v) in PUSH_POP:
                h[3].append(start)
                return h[2], h[3], mv

            return None


        if not self.addline(h, start, mv): return None

        for i in h[2]:
            if bid(self.raw(*i)) == SLIME and not self.addsides(h, i): 
                return None
        return h[2], h[3], mv
        


    def offn(self, p, d, n):
        o = DIRS[d]
        return p[0] + o[0] * n, p[1] + o[1] * n, p[2] + o[2] * n


    def addline(self, h, p, only):
        mv, piston, move, kill = h
        v = self.raw(*p)
        b = bid(v)

        if b == 0: return True
        if not self.canpush(*p, v, mv, False, only): return True
        if p == piston or p in move: return True

        i = 1
        if i + len(move) > PUSH_MAX: return False


        while b == SLIME:
            q = self.offn(p, OPP[mv], i)
            v = self.raw(*q)
            b = bid(v)

            if (
                b == 0 or 
                not self.canpush(*q, v, mv, False, OPP[mv]) or 
                q == piston
            ): break

            i += 1
            if i + len(move) > PUSH_MAX: return False



        n = 0
        for j in range(i - 1, -1, -1):
            move.append(self.offn(p, OPP[mv], j))
            n += 1

        j = 1
        while True:
            q = self.offn(p, mv, j)
            if q in move:
                k = move.index(q)
                self.reorder(move, n, k)

                for l in range(k + n + 1):
                    if (
                        bid(self.raw(*move[l])) == SLIME and 
                        not self.addsides(h, move[l])
                    ): return False
                return True


            v = self.raw(*q)
            if bid(v) == 0: return True
            if not self.canpush(*q, v, mv, True, mv) or q == piston: return False

            if bid(v) in PUSH_POP:
                kill.append(q)
                return True

            if len(move) >= PUSH_MAX: return False
            move.append(q)
            n += 1
            j += 1










    def reorder(self, move, n, k):
        a = move[:k]
        b = move[len(move) - n:]
        c = move[k:len(move) - n]
        move[:] = a + b + c


    def addsides(self, h, p):
        for d in range(6):
            if d // 2 != h[0] // 2 and not self.addline(h, self.off(*p, d), d): 
                return False
        return True


    def addmov(self, x, y, z, v, f, ext, src):
        self.moving[(x, y, z)] = Mov(x, y, z, v, f, ext, src)
        if self.onmove: self.onmove(x, y, z, v, f, ext, src, False)


    
    
    def pushmove(self, x, y, z, f, ext):
        if not ext: self.edit(*self.off(x, y, z, f), 0)

        h = self.structure(x, y, z, f, ext)
        if h is None: return False
        move, kill, mv = h

        olds = [self.raw(*i) for i in move]

        for i in reversed(kill):
            k = self.raw(*i)
            self.put(*i, 0)
            if self.ondrop and bid(k) not in (
                WATER, WATER_FLOWING, LAVA, LAVA_FLOWING
            ): self.ondrop(*i, bid(k))




        for j in range(len(move) - 1, -1, -1):
            i = move[j]
            self.put(*i, 0)
            t = self.off(*i, mv)
            self.put(*t, pack(MOVING_PISTON, 0))
            self.addmov(*t, olds[j], f, ext, False)
            

        hp = self.off(x, y, z, f)
        if ext:
            b = bid(self.raw(x, y, z))
            self.put(*hp, pack(MOVING_PISTON, 0))
            self.addmov(
                *hp, pack(PISTON_HEAD, f | (EXT_BIT if b == STICKY_PISTON else 0)), 
                f, True, True
            )

        for i in reversed(kill): self.notify(*i)
        for i in reversed(move): self.notify(*i)
        if ext: self.notify(*hp)

        return True





    # clr piston tile entity + update tail
    def finish(self, m):
        self.moving.pop((m.x, m.y, m.z), None)
        if self.onmove: self.onmove(m.x, m.y, m.z, m.v, m.f, m.ext, m.src, True)
        if bid(self.raw(m.x, m.y, m.z)) == MOVING_PISTON:
            self.edit(m.x, m.y, m.z, m.v | 0x8000)



    
    def tileticks(self):
        for m in list(self.moving.values()):
            if bid(self.raw(m.x, m.y, m.z)) != MOVING_PISTON:
                self.moving.pop((m.x, m.y, m.z), None)
                continue

            m.last = m.prog
            if m.last >= 1.0:
                self.finish(m)
                continue

            np_ = m.prog + 0.5
            self.pushents(m, np_)
            m.prog = min(np_, 1.0)




    # client
    def animtick(self):
        while self.anims:
            x, y, z, v, f, ext, src, done = self.anims.popleft()

            if done: self.moving.pop((x, y, z), None)
            else:
                self.moving[(x, y, z)] = Mov(x, y, z, v, f, ext, src)


        for m in list(self.moving.values()):
            m.last = m.prog
            if m.last >= 1.0:
                self.moving.pop((m.x, m.y, m.z), None)
                continue

            np_ = m.prog + 0.5
            self.pushents(m, np_)
            m.prog = min(np_, 1.0)




    # moving collisions
    def movboxes(self, m):
        v = m.v
        if m.src and not m.ext: v = pack(PISTON_HEAD, m.f)
        b = bid(v)

        if b == PISTON_HEAD: return headboxes(state(v) & 7)
        if b in PISTONS and state(v) & EXT_BIT: return [extbox(state(v) & 7)]
        if b == 0 or b in NOCOLLIDE: return []
        return [(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)]




    
    def pushents(self, m, p):
        if not self.movers: return
        boxes = self.movboxes(m)
        if not boxes: return


        ed = m.f if m.ext else OPP[m.f]
        d0 = p - m.prog
        s  = m.shift(m.prog)
        o  = DIRS[m.f]
        ox, oy, oz = m.x + s * o[0], m.y + s * o[1], m.z + s * o[2]
        wb = [
            (
                b[0] + ox, b[1] + oy, 
                b[2] + oz, b[3] + ox, 
                b[4] + oy, b[5] + oz
            ) for b in boxes
        ]

        un = (
            min(0.0, *[b[0] for b in boxes]) + ox, min(0.0, *[b[1] for b in boxes]) + oy, min(0.0, *[b[2] for b in boxes]) + oz,
            max(1.0, *[b[3] for b in boxes]) + ox, max(1.0, *[b[4] for b in boxes]) + oy, max(1.0, *[b[5] for b in boxes]) + oz,
        )

        broad = boxunion(sweep(un, ed, d0), un)
        slime = bid(m.v) == SLIME
        a     = {DOWN: 1, UP: 1, NORTH: 2, SOUTH: 2, WEST: 0, EAST: 0}[ed]
        dv    = DIRS[ed]




        for ebox, move, vel in self.movers():
            if not boxhit(ebox, broad): continue
            if slime: vel(a, float(dv[a]))

            d1 = 0.0
            for b in wb:
                sb = sweep(b, ed, d0)
                if boxhit(sb, ebox):
                    d1 = max(d1, pushdist(sb, ed, ebox))
                    if d1 >= d0: break

            if d1 > 0.0:
                d1 = min(d1, d0) + 0.01
                self.pushing = ed
                move(d1 * dv[0], d1 * dv[1], d1 * dv[2])
                self.pushing = None
                if not m.ext and m.src: 
                    self.pushback(m, ed, d0, ebox, move, d1)




    
    def pushback(self, m, ed, d0, ebox, move, moved):
        o  = DIRS[ed]
        e2 = tuple(ebox[i] + moved * o[i % 3] for i in range(6))
        cb = (
            float(m.x), float(m.y), float(m.z), 
            m.x + 1.0, m.y + 1.0, m.z + 1.0
        )
        if not boxhit(e2, cb): return

        bk = OPP[ed]
        a  = pushdist(cb, bk, e2) + 0.01
        c  = pushdist(cb, bk, boxunion(e2, cb)) + 0.01

        if abs(a - c) < 0.01:
            a = min(a, d0) + 0.01
            v = DIRS[bk]
            self.pushing = ed
            move(a * v[0], a * v[1], a * v[2])
            self.pushing = None



    def edit(self, x, y, z, v):
        o = self.raw(x, y, z)
        self.put(x, y, z, v)
        self.evs.append((x, y, z, o, v))


    def gone(self, x, y, z):
        self.edit(x, y, z, 0)




    # power line
    def detectscan(self):
        for p, t in list(self.cartseen.items()):
            if self.now - t > 1:
                del self.cartseen[p]
                continue

            v = self.raw(*p)
            if bid(v) == DETECTOR_RAIL and not state(v) & RAILPW: 
                self.detectupd(*p, v)

                


    # 20ticks @cart
    def detectupd(self, x, y, z, v):
        on  = bool(state(v) & RAILPW)
        hit = (x, y, z) in self.cartseen

        if hit != on:
            nv = v ^ (RAILPW << 10)
            self.put(x, y, z, nv)
            self.notify(x, y, z)
            self.notify(x, y - 1, z)
            for i in Rail(self, x, y, z, nv).c: 
                self.nq.append(i)


        if hit: 
            self.schedule(x, y, z, DETECTOR_RAIL, 20)






    def railfam(self, b): return RAILS if b in RAILS else (b,)


    def railon(self, v):
        return bid(v) == POWERED_RAIL_ON or (
            bid(v) in (ACTIVATOR_RAIL, DETECTOR_RAIL) and 
            bool(state(v) & RAILPW)
        )



    
    def railsignal(self, x, y, z, v, fwd, n):
        if n >= RAIL_MAX: return False
        d = railshape(v)
        flag = True
        if   d == NS: z +=  1 if fwd else -1
        elif d == EW: x += -1 if fwd else 1
        elif d == ASC_E:
            if fwd: x -= 1
            else:
                x += 1
                y += 1
                flag = False
            d = EW

        elif d == ASC_W:
            if fwd: 
                x -= 1
                y += 1
                flag = False
            else: x += 1
            d = EW
            
        elif d == ASC_N:
            if fwd: z += 1
            else:   
                z -= 1
                y += 1
                flag = False
            d = NS

        elif d == ASC_S:
            if fwd: 
                z += 1
                y += 1
                flag = False
            else: z -= 1
            d = NS

        fam = self.railfam(bid(v))

        if self.railnext(x, y, z, fwd, n, d, fam): return True
        return flag and self.railnext(x, y - 1, z, fwd, n, d, fam)
        


    
    def railnext(self, x, y, z, fwd, n, d, fam):
        v = self.raw(x, y, z)
        if bid(v) not in fam: return False

        o = railshape(v)
        if d == EW and o in (NS, ASC_N, ASC_S): return False
        if d == NS and o in (EW, ASC_E, ASC_W): return False
        if not self.railon(v): return False

        return self.powered(x, y, z) or self.railsignal(x, y, z, v, fwd, n + 1)


    # neigbor tail + updateState per type
    def railupd(self, x, y, z, v, b):
        d = railshape(v)
        o = {
            ASC_E: (x + 1, y, z), ASC_W: (x - 1, y, z), 
            ASC_N: (x, y, z - 1), ASC_S: (x, y, z + 1)
        }.get(d)

        if o is not None and self.loaded(*o) and not self.topsolid(*o):
            self.pop(x, y, z, v)
            return

        if b == RAIL:
            # T junction re-picks when power flips
            k  = (x, y, z)
            pw = self.powered(x, y, z)
            
            if pw != self.railpw.get(k, False):
                self.railpw[k] = pw
                r = Rail(self, x, y, z, v)
                if r.count() == 3: r.place(pw, False)
            return

        if b == DETECTOR_RAIL: return

        pw = self.powered(x, y, z) or self.railsignal(x, y, z, v, True, 0) or self.railsignal(x, y, z, v, False, 0)
        if pw == self.railon(v): return
        if b in RAILS: 
            nv = pack(POWERED_RAIL_ON if pw else POWERED_RAIL, d)
        else:
            nv = v ^ (RAILPW << 10)

        self.put(x, y, z, nv)
        self.notify(x, y, z)
        self.notify(x, y - 1, z)

        if d in (ASC_E, ASC_W, ASC_N, ASC_S): 
            self.notify(x, y + 1, z)



    
    def obsout(self, x, y, z, v):
        f = state(v) & 7
        nx, ny, nz = self.off(x, y, z, OPP[f])
        self.nq.append((nx, ny, nz))
        self.notify(nx, ny, nz, skip=f)


    def setdiode(self, x, y, z, v, on):
        nv = (v | (16 << 10)) if on else (v & ~(16 << 10))
        self.put(x, y, z, nv)
        self.diodeout(x, y, z, nv)


    def notifyatt(self, x, y, z, v):
        self.nq.append((x, y, z))
        self.notify(x, y, z)
        nx, ny, nz = self.off(x, y, z, OPP[ATTDIR[state(v) & 7]])
        self.nq.append((nx, ny, nz))
        self.notify(nx, ny, nz)


    def ignite(self, x, y, z):
        self.put(x, y, z, 0)
        self.notify(x, y, z)
        if self.ontnt: self.ontnt(x, y, z)


    def onedit(self, x, y, z, old, new):
        ob, nb = bid(old), bid(new)

        self.observed(x, y, z)

        # invert swaps ids
        if nb in DAYS: self.notify(x, y, z)

        if ob == nb:
            if ob == LEVER:
                self.notifyatt(x, y, z, new)
            elif ob in BUTTONS:
                self.notifyatt(x, y, z, new)
                if state(new) & ON_BIT: self.schedule(x, y, z, ob, BTN_T[ob])
            elif ob == REPEATER:   self.diodeupd(x, y, z, new)
            elif ob == COMPARATOR: self.cmpupd(x, y, z, new)
            
            return



        # removed
        if ob in SIZES: self.tiles.remove(x, y, z)
        if ob == NOTEBLOCK: self.notepw.pop((x, y, z), None)

        if ob in ALLRAILS and nb not in ALLRAILS:
            self.railpw.pop((x, y, z), None)
            if railshape(old) in (ASC_E, ASC_W, ASC_N, ASC_S): 
                self.notify(x, y + 1, z)

            if ob != RAIL:
                self.notify(x, y, z)
                self.notify(x, y - 1, z)

        if ob == TRIPWIRE: 
            self.tripnotify(x, y, z, old | (1 << 10))

        if ob == TRIPWIRE_HOOK:
            if state(old) & 12: self.hookcalc(x, y, z, old, True, False)
            if state(old) & 8:  self.hooknotify(x, y, z, FACEDIR[state(old) & 3])

        if ob in DAYS and nb not in DAYS: self.days.discard((x, y, z))
        if ob == OBSERVER and state(old) & 8 and self.pending(x, y, z, OBSERVER):
            self.obsout(x, y, z, old & ~(8 << 10))

        if ob == REDSTONE_WIRE:
            self.notify2(x, y, z)
            self.wirearound(x, y, z)

        elif ob == REPEATER:
            self.notify(x, y, z)
            self.diodeout(x, y, z, old)

        elif ob in (LEVER, STONE_BUTTON, WOODEN_BUTTON):
            if state(old) & ON_BIT: self.notifyatt(x, y, z, old)

        elif ob == REDSTONE_TORCH_ON:
            for d in range(6): self.notify(*self.off(x, y, z, d))

        elif ob == COMPARATOR:
            self.cout.pop((x, y, z), None)
            self.diodeout(x, y, z, old)

        elif ob in PLATES:
            self.notify(x, y - 1, z)

        elif ob in PISTONS:
            if state(old) & EXT_BIT:
                hx, hy, hz = self.off(x, y, z, state(old) & 7)
                if bid(self.raw(hx, hy, hz)) == PISTON_HEAD: self.gone(hx, hy, hz)

        elif ob == PISTON_HEAD:
            nx, ny, nz = self.off(x, y, z, OPP[state(old) & 7])
            n = self.raw(nx, ny, nz)

            if bid(n) in PISTONS and state(n) & EXT_BIT:
                self.put(nx, ny, nz, 0)
                self.evs.append((nx, ny, nz, n, 0))
                if self.ondrop: self.ondrop(nx, ny, nz, bid(n))


        # added
        if nb == REDSTONE_WIRE:
            self.nq.append((x, y, z))
            self.notify(x, y - 1, z)
            self.notify(x, y + 1, z)
            self.wirearound(x, y, z)

        elif nb == REDSTONE_TORCH_ON:
            for d in range(6): self.notify(*self.off(x, y, z, d))
            self.nq.append((x, y, z))

        elif nb == REDSTONE_TORCH_OFF or nb in (LEVER, STONE_BUTTON, WOODEN_BUTTON):
            self.nq.append((x, y, z))

        elif nb == REPEATER:
            self.diodeout(x, y, z, new)
            self.nq.append((x, y, z))

        elif nb in DAYS:
            self.days.add((x, y, z))
            self.dayupd(x, y, z, nb)

        elif nb in ALLRAILS and ob not in ALLRAILS:
            Rail(self, x, y, z, new).place(self.powered(x, y, z), True)
            self.nq.append((x, y, z))

        elif nb == TRIPWIRE:
            self.tripnotify(x, y, z, new)

        elif nb == TRIPWIRE_HOOK:
            self.hookcalc(x, y, z, new, False, False)
            self.nq.append((x, y, z))

        elif nb == OBSERVER:
            if state(new) & 8: self.ontick(x, y, z, OBSERVER)
            elif not state(new) & 8: self.schedule(x, y, z, OBSERVER, OBS_T)

        elif nb in (DISPENSER, DROPPER, HOPPER, FURNACE, FURNACE_ON):
            self.tiles.get(x, y, z)
            self.nq.append((x, y, z))

        elif nb in (
            REDSTONE_LAMP, REDSTONE_LAMP_ON, TNT, COMPARATOR, ACTIVATOR_RAIL, NOTEBLOCK
        ) or nb in PISTONS or nb in OPENABLE or nb in RAILS or nb in PLATES:
            self.nq.append((x, y, z))

        self.notify(x, y, z)



























































