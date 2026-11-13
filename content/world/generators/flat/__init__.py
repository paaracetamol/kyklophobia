from config import FLAT_LAYERS, FLAT_SPAWN

BIOMES = {}


def setup(w): pass
def tint(c): return None
def spawn(seed): return 0.0, FLAT_SPAWN, 0.0
def reseed(w): pass

def biome(x, z, w): return "Flat"
def locate(px, pz, tid, w): return -1.0, -1.0


def gen(c):
    y = 0
    for i, j in FLAT_LAYERS:
        c.voxels[:, y:y + i, :] = j
        y += i
