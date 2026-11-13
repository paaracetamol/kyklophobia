import importlib

# world/generators/<type>/ by world.json type
# BIOMES, setup, reseed, gen, tint, spawn, biome, locate
TYPES = ("default", "flat")

def get(nm): return importlib.import_module(f"world.generators.{nm if nm in TYPES else TYPES[0]}")
