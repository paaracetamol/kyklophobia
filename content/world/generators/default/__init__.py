import numpy as np
from config import CHUNK_SZ, SEA_LEVEL

CHUNK_H = 128   # this gen only fills the bottom half
from .noise import (
    PerlinNoise, fade, lerp, grad, noise3d, fractal3d,
    get_climate, get_biome, smooth_bonus,
    _badlands_band, locate_biome, BIOME_NAMES,
)
from .generate import _generate
from .trees import TreeManager, treetochunk, grasstochunk, cactitochunk
from .decor import RockManager, addchunkrocks

BIOMES = {
    "plains":   0,
    "desert":   1,
    "snowy":    2,
    "jungle":   3,
    "badlands": 4,
    "forest":   5,
}



def setup(w):
    w.trees = TreeManager()
    w.rocks = RockManager()
    reseed(w)



def tint(c): return None
def spawn(seed): return 0.0, 80.0, 0.0

def reseed(w): w.noise = PerlinNoise(seed=w.seed)


def biome(x, z, w):
    i = get_biome(x, z, w.noise.p)
    return BIOME_NAMES[i] if 0 <= i < len(BIOME_NAMES) else "Unknown"


def locate(px, pz, tid, w): return locate_biome(px, pz, tid, w.noise.p)


def gen(c):
    w = c.world
    biomes = np.zeros((CHUNK_SZ, CHUNK_SZ), dtype=np.int8)
    off_x = np.clip(float(c.offset_x), -1e6, 1e6)
    off_z = np.clip(float(c.offset_z), -1e6, 1e6)
    _generate(c.voxels, off_x, off_z, w.noise.p, biomes)

    if w.trees:
        treetochunk(
            c.voxels, c.offset_x, c.offset_z,
            w.trees, w.seed,
            w.noise.p, w.chunker,
            CHUNK_SZ, CHUNK_H, SEA_LEVEL,
            biomes
        )


    key = (c.x, c.z)
    if key in w.chunker.pending_decorations:
        for lx, ly, lz, bt in w.chunker.pending_decorations[key]:

            if 0 <= lx < CHUNK_SZ and 0 <= ly < CHUNK_H and 0 <= lz < CHUNK_SZ:
                if bt in [7, 8, 9] and c.voxels[lx, ly, lz] in [0, 1]:
                    c.voxels[lx, ly, lz] = bt


        del w.chunker.pending_decorations[key]

        

    if w.rocks:
        addchunkrocks(
            c.voxels, c.offset_x, c.offset_z,
            w.rocks, w.seed,
            w.noise.p, w.chunker,
            CHUNK_SZ, CHUNK_H, SEA_LEVEL
        )

    if w.trees:
        grasstochunk(
            c.voxels, c.offset_x, c.offset_z,
            w.seed, w.noise.p, biomes,
            CHUNK_SZ, CHUNK_H, SEA_LEVEL
        )

        cactitochunk(
            c.voxels, c.offset_x, c.offset_z,
            biomes, w.seed,
            CHUNK_SZ, CHUNK_H, SEA_LEVEL
        )




def warmup():
    p = np.arange(512, dtype=np.int32) % 256
    _ = fade(0.5)
    _ = lerp(0.5, 0.0, 1.0)
    _ = grad(1, 0.5, 0.5, 0.5)
    _ = noise3d(0.0, 0.0, 0.0, p)
    _ = fractal3d(0.0, 0.0, 0.0, p, 4, 0.5, 2.0, 0.01, 0.01, 0.01)
    _, _ = get_climate(0.0, 0.0, p)
    _ = get_biome(0.0, 0.0, p)
    _ = smooth_bonus(0.5, 0.5, 64.0)
    _ = _badlands_band(64)
    _, _ = locate_biome(0.0, 0.0, 0, p, 0, 32)   # max_radius=0 -> return

    dvox    = np.zeros((CHUNK_SZ, CHUNK_H, CHUNK_SZ), dtype=np.uint16)
    dbiomes = np.zeros((CHUNK_SZ, CHUNK_SZ), dtype=np.int8)
    _generate(dvox, 0.0, 0.0, p, dbiomes)


warmup()
