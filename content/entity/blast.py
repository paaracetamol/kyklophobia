import math

from world.blocks import (
    BEDROCK, OBSIDIAN, BARRIER, END_PORTAL_FRAME, COMMAND_BLOCK, ENDER_CHEST,
    ENCHANTING_TABLE, ANVIL, ANVIL_SLIGHTLY_DAMAGED, ANVIL_VERY_DAMAGED,
)
from world.redstone import ALLRAILS



BLASTPROOF = frozenset((
    BEDROCK, OBSIDIAN, BARRIER, END_PORTAL_FRAME, COMMAND_BLOCK, ENDER_CHEST,
    ENCHANTING_TABLE, ANVIL, ANVIL_SLIGHTLY_DAMAGED, ANVIL_VERY_DAMAGED,
))
_SPH = {}



def sphere(power):
    k = round(power, 1)
    if k not in _SPH:
        r = int(k) + 1
        o = []

        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    d = math.sqrt(dx * dx + dy * dy + dz * dz)
                    if d <= k: o.append((dx, dy, dz, d))


        o.sort(key=lambda t: t[3])
        _SPH[k] = o

    return _SPH[k]







def spared(ck, x, y, z, b, rails):
    if b in BLASTPROOF: return True
    return rails and (b in ALLRAILS or ck.getblock(x, y + 1, z) in ALLRAILS)




# get block density corners
def exposure(ck, ex, ey, ez, box, n=0):
    for i in range(8):
        px = box[0] + (box[3] - box[0]) * (0.05 + 0.9 * (i & 1))
        py = box[1] + (box[4] - box[1]) * (0.05 + 0.9 * ((i >> 1) & 1))
        pz = box[2] + (box[5] - box[2]) * (0.05 + 0.9 * ((i >> 2) & 1))


        dx, dy, dz = px - ex, py - ey, pz - ez
        ln = math.sqrt(dx * dx + dy * dy + dz * dz)
        hit = False

        for s in range(1, int(ln / 0.4) + 1):
            t = s * 0.4 / ln

            if ck.iscollide(math.floor(ex + dx * t), math.floor(ey + dy * t), math.floor(ez + dz * t)):
                hit = True
                break

        if not hit: n += 1

    return n / 8.0







# body = (x, y, z, eye, box, hit(dmg, dx, dy, dz))
def affect(ck, ex, ey, ez, power, bodies):

    f3 = power * 2.0
    for x, y, z, eye, box, hit in bodies:
        d12 = math.sqrt((x - ex) ** 2 + (y - ey) ** 2 + (z - ez) ** 2) / f3
        if d12 > 1.0: continue

        d5, d7, d9 = x - ex, y + eye - ey, z - ez
        d13 = math.sqrt(d5 * d5 + d7 * d7 + d9 * d9)
        if d13 == 0.0: continue

        d10 = (1.0 - d12) * exposure(ck, ex, ey, ez, box)
        
        hit(
            int((d10 * d10 + d10) / 2.0 * 7.0 * f3 + 1.0), 
            d5 / d13 * d10, d7 / d13 * d10, d9 / d13 * d10
        )






def enthit(e):
    def hit(dmg, dx, dy, dz):
        if hasattr(e, 'mx'):
            e.mx += dx;  e.my += dy;  e.mz += dz
            
        else:
            e.vel[0] += dx * 20.0
            e.vel[1] += dy * 20.0
            e.vel[2] += dz * 20.0

        if hasattr(e, 'blasted'): e.blasted()
        elif e.type.hp > 0:       e.hurt(dmg)

    return hit




def entbody(e):
    return (
        float(e.pos[0]), 
        float(e.pos[1]), 
        float(e.pos[2]), 
        e.type.eye, 
        e.aabb(), 
        enthit(e)
    )












