import numpy as np

from world import blocks as B
from world.redstone import ATTDIR, ON_BIT, UP, DOWN, NORTH, SOUTH, WEST, EAST, TORCHES, BUTTONS, PLATES
from world.renderers.registry import (
    BLOCK_MODE_RENDER, BLOCK_ELEMS, NUM_ELEMENTS,
    STATE_ROW, STATE_ELEM_OFF, STATE_ELEM_NUM,
)


# selection boxes
# none = full cube

def _px(*a): return tuple(i / 16.0 for i in a)


# on wall opposite f, w = half width, y0-y1 height, d = depth
def wallbox(f, w, y0, y1, d):
    lo, hi = 0.5 - w, 0.5 + w
    if f == NORTH: return (lo, y0, 1.0 - d, hi, y1, 1.0)
    if f == SOUTH: return (lo, y0, 0.0, hi, y1, d)
    if f == WEST:  return (1.0 - d, y0, lo, 1.0, y1, hi)
    if f == EAST:  return (0.0, y0, lo, d, y1, hi)
    if f == UP:    return (lo, 0.0, 0.5 - 0.125, hi, d, 0.5 + 0.125)
    return (lo, 1.0 - d, 0.5 - 0.125, hi, 1.0, 0.5 + 0.125)



def _torch(s):
    f = ATTDIR[s & 7]
    if f == UP: return (0.4, 0.0, 0.4, 0.6, 0.6, 0.6)
    return wallbox(f, 0.15, 0.2, 0.8, 0.3)


def _lever(s):
    f = ATTDIR[s & 7]
    if f == UP:   return (0.25, 0.0, 0.1875, 0.75, 0.6, 0.8125)
    if f == DOWN: return (0.25, 0.4, 0.1875, 0.75, 1.0, 0.8125)
    return wallbox(f, 0.1875, 0.2, 0.8, 0.375)


def _button(s):
    f = ATTDIR[s & 7]
    d = 0.0625 if s & ON_BIT else 0.125
    if f in (UP, DOWN):
        y0 = 0.0 if f == UP else 1.0 - d
        return (0.3125, y0, 0.375, 0.6875, y0 + d, 0.625)
    return wallbox(f, 0.1875, 0.375, 0.625, d)



FLAT = {}
FLAT.update({i: _px(5, 0, 5, 11, 10, 11) for i in (
        B.DANDELION, B.POPPY, B.BLUE_ORCHID, B.ALLIUM, B.AZURE_BLUET,
        B.RED_TULIP, B.ORANGE_TULIP, B.WHITE_TULIP, B.PINK_TULIP, B.OXEYE_DAISY
    )
})
FLAT.update({i: (0.1, 0.0, 0.1, 0.9, 0.8, 0.9) for i in (
        B.SAPLING_OAK, B.SAPLING_SPRUCE, B.SAPLING_BIRCH, B.SAPLING_JUNGLE,
        B.SAPLING_ACACIA, B.SAPLING_DARK_OAK, B.TALLGRASS, B.FERN, B.DEAD_BUSH
    )
})
FLAT.update({i: (0.3, 0.0, 0.3, 0.7, 0.4, 0.7) for i in (B.BROWN_MUSHROOM, B.RED_MUSHROOM)})
FLAT.update({i: (0.0, 0.0, 0.0, 1.0, 0.125, 1.0) for i in (
        B.REPEATER, B.COMPARATOR, B.RAIL, B.POWERED_RAIL, B.POWERED_RAIL_ON,
        B.DETECTOR_RAIL, B.ACTIVATOR_RAIL
    )
})


FLAT.update({i: _px(1, 0, 1, 15, 1, 15) for i in PLATES})
FLAT.update({
    B.REDSTONE_WIRE: _px(0, 0, 0, 16, 1, 16),
    B.TRIPWIRE:      _px(0, 1, 0, 16, 2.5, 16),
    B.SUGAR_CANE:    _px(2, 0, 2, 14, 16, 14),
    B.LILY_PAD:      _px(1, 0, 1, 15, 1.5, 15),
    B.CAKE:          _px(1, 0, 1, 15, 8, 15),
    B.DAYLIGHT_DETECTOR:          _px(0, 0, 0, 16, 6, 16),
    B.DAYLIGHT_DETECTOR_INVERTED: _px(0, 0, 0, 16, 6, 16),
    B.ENDER_CHEST:   _px(1, 0, 1, 15, 14, 15),
})

FNS = {B.LEVER: _lever, B.TORCH: _torch}
FNS.update({i: _torch for i in TORCHES})
FNS.update({i: _button for i in BUTTONS})







MODEL = {
    B.SNOW, B.BED_HEAD, B.BED_FOOT, 
    B.ENCHANTING_TABLE, B.END_PORTAL_FRAME,
    B.OAK_TRAPDOOR, B.IRON_TRAPDOOR,
    B.OAK_DOOR_BOTTOM, B.OAK_DOOR_TOP, B.IRON_DOOR_BOTTOM, B.IRON_DOOR_TOP,
    B.SPRUCE_DOOR_BOTTOM, B.SPRUCE_DOOR_TOP, B.BIRCH_DOOR_BOTTOM, B.BIRCH_DOOR_TOP,
    B.JUNGLE_DOOR_BOTTOM, B.JUNGLE_DOOR_TOP, B.ACACIA_DOOR_BOTTOM, B.ACACIA_DOOR_TOP,
    B.DARK_OAK_DOOR_BOTTOM, B.DARK_OAK_DOOR_TOP,
    B.STONE_SLAB, B.SANDSTONE_SLAB, B.COBBLESTONE_SLAB, B.BRICK_SLAB,
    B.STONE_BRICK_SLAB, B.NETHER_BRICK_SLAB, B.QUARTZ_SLAB, B.OAK_SLAB,
    B.SPRUCE_SLAB, B.BIRCH_SLAB, B.JUNGLE_SLAB, B.ACACIA_SLAB,
    B.DARK_OAK_SLAB, B.RED_SANDSTONE_SLAB,
} | {getattr(B, i) for i in dir(B) if i.startswith("CARPET_")}



def modelbox(b, s):
    n = STATE_ELEM_NUM[b, s]
    r, o = STATE_ROW[b, s], STATE_ELEM_OFF[b, s]
    if n == 0: r, o, n = b, 0, NUM_ELEMENTS[b]

    e = BLOCK_ELEMS[r, o:o + n].reshape(-1, 3)
    lo, hi = np.clip(e.min(0), 0.0, 1.0), np.clip(e.max(0), 0.0, 1.0)

    return (*map(float, lo), *map(float, hi))







def selbox(v):

    b, s = v & 0x3FF, (v >> 10) & 0x1F
    if b in FLAT:  return FLAT[b]
    if b in FNS:   return FNS[b](s)
    if b in MODEL and b < len(BLOCK_MODE_RENDER): return modelbox(b, s)
    return None





# ray vs box
def rayhit(o, d, bx):
    t0, t1, ax = 0.0, 1e9, -1
    for i in range(3):
        if abs(d[i]) < 1e-9:
            if o[i] < bx[i] or o[i] > bx[i + 3]: return None
            continue

        a, b = (bx[i] - o[i]) / d[i], (bx[i + 3] - o[i]) / d[i]
        if a > b: a, b = b, a
        if a > t0: t0, ax = a, i
        t1 = min(t1, b)
        if t0 > t1: 
            return None

    return t0, ax













if __name__ == "__main__":
    assert rayhit((0.5, 2, 0.5), (0, -1, 0), (0, 0, 0, 1, 0.125, 1)) == (2 - 0.125, 1)
    assert rayhit((0.9, 2, 0.9), (0, -1, 0), (0.4, 0, 0.4, 0.6, 0.6, 0.6)) is None
    assert _torch(1)[2] == 0.7 and _lever(0)[4] == 0.6

    print("ok")



















