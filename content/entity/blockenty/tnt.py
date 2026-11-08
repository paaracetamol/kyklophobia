import math
import random
import numpy as np

from entity.blockenty.base import BlockEntity
from entity.blockenty.registry import regblockent, regitemblock
from config import TICK
from entity import motion, blast


FUSE_TIME       = 4.0
CHAIN_FUSE_MIN  = 0.5
CHAIN_FUSE_MAX  = 1.5
BLAST_RADIUS    = 4.0
BLAST_KNOCK_RAD = 8.0
MAX_KNOCK_FORCE = 18.0

_GRAVITY      = -32.0
_TERMINAL_VEL = -78.4
_INITIAL_VEL_Y =  4.0

_FLASH_SLOW = 0.5    # fuse > 1 s
_FLASH_FAST = 0.1    # fuse ≤ 1 s




def buildsphere(radius):
    r = int(radius)
    offsets = []
    for dx in range(-r - 1, r + 2):
        for dy in range(-r - 1, r + 2):
            for dz in range(-r - 1, r + 2):
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist <= radius:
                    offsets.append((dx, dy, dz, dist))
    offsets.sort(key=lambda t: t[3])  # sorted center-out
    return offsets

BLAST_OFF = buildsphere(BLAST_RADIUS)


# World.createExplosion on this side. destruction is the plain sphere, entities get vanilla's sums
def explodeat(wc, ex, ey, ez, power, rails=False, skip=None):
    chunker = wc.get('chunker')
    pmgr  = wc.get('particles')
    p     = wc.get('player')
    nc    = wc.get('netclient')
    bemgr = wc.get('blockentys')
    ents  = wc.get('entitys')
    items = wc.get('itementys')

    cx = int(math.floor(ex))
    cy = int(math.floor(ey))
    cz = int(math.floor(ez))
    from world.blocks import TNT as TNT_ID
    from world.redstone import pickitem
    from items.registry import REGISTRY
    online = nc and nc.isconn()

    if chunker:
        cpos, npos = [], []
        for dx, dy, dz, dist in blast.sphere(power):
            bx, by, bz = cx + dx, cy + dy, cz + dz
            bt = chunker.getblock(bx, by, bz)
            if not bt: continue
            if blast.spared(chunker, bx, by, bz, bt, rails): continue
            if bt == TNT_ID: cpos.append((bx, by, bz))
            else:            npos.append((bx, by, bz, dist))

        if online:
            # server does the block destruction, this is just the show
            if pmgr:
                for bx, by, bz, dist in npos:
                    if dist <= power * 0.6: pmgr.spawn(bx, by, bz, chunker.getblock(bx, by, bz))
        else:
            rm = chunker.batchbreak([(bx, by, bz) for bx, by, bz, _ in npos])
            for bx, by, bz, dist in npos:
                v = rm.get((bx, by, bz))
                if v is None: continue
                if pmgr and dist <= power * 0.6: pmgr.spawn(bx, by, bz, v)
                # Block.dropBlockAsItemWithChance, 1 / power
                iid = pickitem(v)
                if random.random() < 1.0 / power and REGISTRY.exists(iid) and chunker.rs.spawn:
                    chunker.rs.spawn(iid, 1, (bx + 0.5, by + 0.5, bz + 0.5), (0.0, 2.0, 0.0))

            # BlockTNT.onBlockDestroyedByExplosion: nextInt(20) + 10 ticks
            if bemgr is not None and not online:
                for bx, by, bz in cpos:
                    chunker.breakblock(bx, by, bz)
                    bemgr.activate(bx, by, bz, TNT_ID, fuse=(random.randrange(20) + 10) * TICK)

    bodies = []
    if p:
        hw, ph = p.physics.pw / 2, p.physics.ph
        px, py, pz = float(p.pos[0]), float(p.pos[1]), float(p.pos[2])

        def phit(dmg, dx, dy, dz):
            p.vel[0] += dx;  p.vel[1] += dy;  p.vel[2] += dz
            p.on_ground = False
            if not p.gmode: p.hurt(dmg)

        bodies.append((px, py, pz, p.physics.eye_h, (px - hw, py, pz - hw, px + hw, py + ph, pz + hw), phit))

    if not online and chunker:
        if ents: bodies += [blast.entbody(i) for i in list(ents.ents.values())]
        if bemgr is not None:
            for i in bemgr.entities:
                if i is skip or not i.alive or not isinstance(i, TNTEntity): continue
                bodies.append((float(i.pos[0]), float(i.pos[1]), float(i.pos[2]), 0.0, i.aabb(), tnthit(i)))
        if items:
            for i in list(items.items):
                if not i.active: continue
                bodies.append((float(i.pos[0]), float(i.pos[1]), float(i.pos[2]), 0.2125,
                    (i.pos[0] - 0.125, i.pos[1], i.pos[2] - 0.125, i.pos[0] + 0.125, i.pos[1] + 0.25, i.pos[2] + 0.125),
                    itemhit(i, items)))

    if chunker: blast.affect(chunker, ex, ey, ez, power, bodies)


def tnthit(i):
    def hit(dmg, dx, dy, dz):
        i.mx += dx;  i.my += dy;  i.mz += dz
    return hit


# EntityItem has 5 health
def itemhit(i, items):
    def hit(dmg, dx, dy, dz):
        i.vel[0] += dx * 20.0;  i.vel[1] += dy * 20.0;  i.vel[2] += dz * 20.0
        if dmg >= 5:
            i.active = False
            if i in items.items: items.items.remove(i)
    return hit




@regblockent(60)   # world.blocks.TNT = 60
class TNTEntity(BlockEntity):
    def __init__(self, x, y, z, fuse=None, _remote=False, eid=None):
        super().__init__(x, y, z)
        self.fuse    = fuse if fuse is not None else FUSE_TIME
        self._remote = _remote
        self.eid     = eid           # set -> server owns this one
        # pos[1] = bottom of the 1x1x1 cube
        self.pos = np.array([x + 0.5, float(y), z + 0.5], dtype='f4')
        self.vy  = _INITIAL_VEL_Y

        # EntityTNTPrimed: small random shove, up a bit. motion per tick
        a = random.random() * math.pi * 2.0
        self.mx = -math.sin(a) * 0.02
        self.my = 0.2
        self.mz = -math.cos(a) * 0.02
        self.opos = self.pos.copy()
        self.acc  = 0.0
        self.tpos = self.pos.copy()  # last pos the server sent

        self._on_ground   = False
        self._flash_timer = 0.0
        self._flash_on    = False
        self._uvs         = None


    # pos[1] = bot
    def aabb(self):
        return (
            self.pos[0] - 0.5, self.pos[1],       self.pos[2] - 0.5,
            self.pos[0] + 0.5, self.pos[1] + 1.0, self.pos[2] + 0.5,
        )


    def dbgtag(self):
        who = f"#{self.eid}" if self.eid is not None else "local"
        og  = "grnd" if self._on_ground else "air"
        d   = float(np.linalg.norm(self.tpos - self.pos)) if self.eid is not None else 0.0
        
        return (
            f"{who} tnt y{self.pos[1]:.1f} vy{self.vy:.1f} "
            f"f{max(self.fuse, 0.0):.1f} {og} d{d:.2f}"
        )


    def setnet(self, pos, vy):
        self.tpos = pos.copy()
        self.vy   = vy


    def update(self, dt, wc):
        # server owned -> ease onto the authoritative pos, it blows up when told
        if self.eid is not None:
            self.opos[:] = self.pos
            self.pos += (self.tpos - self.pos) * min(1.0, 10.0 * dt)
            self.fuse -= dt
            self.acc = 0.0
            return

        chunker = wc.get('chunker')
        self.acc += dt
        n = 0
        while self.acc >= TICK and n < 5 and self.alive:
            self.acc -= TICK
            n += 1
            self.step(chunker, wc)


    # EntityTNTPrimed.onUpdate
    def step(self, chunker, wc):
        self.opos[:] = self.pos
        self.my -= 0.04
        v = np.array((self.mx, self.my, self.mz), dtype='f4')
        fp, grnd, wall = motion.movebox(chunker, self.pos, v, 0.49, 0.98, 0.0, 1.0)
        self.pos = fp
        self.mx, self.my, self.mz = float(v[0]) * 0.98, float(v[1]) * 0.98, float(v[2]) * 0.98
        if grnd:
            self.mx *= 0.7;  self.mz *= 0.7;  self.my *= -0.5
        self.x = int(math.floor(self.pos[0]))
        self.y = int(math.floor(self.pos[1]))
        self.z = int(math.floor(self.pos[2]))

        self.fuse -= TICK
        if self.fuse <= 1e-6:
            self.explode(wc)
            return


    # RenderTNTPrimed: swells the last 10 ticks, white pulse every 5
    def render(self, mgr):
        a  = self.acc / TICK if self.eid is None else 1.0
        p  = self.opos + (self.pos - self.opos) * a
        ft = self.fuse / TICK - a + 1.0
        sc = 1.0
        if ft < 10.0:
            f  = max(0.0, min(1.0, 1.0 - ft / 10.0))
            sc = 1.0 + (f ** 4) * 0.3
        fl = (1.0 - ft / 100.0) * 0.8 if int(self.fuse / TICK) // 5 % 2 == 0 else 0.0
        mgr.draw_cube((p[0], p[1] + 0.5, p[2]), self.getuvs(), flash=max(0.0, fl), scale=sc)


    def applygrav(self, dt, chunker):
        bx = int(math.floor(self.pos[0]))
        bz = int(math.floor(self.pos[2]))



        if self._on_ground:

            sy = int(math.floor(self.pos[1])) - 1
            if not chunker.iscollide(bx, sy, bz):
                self._on_ground = False
                self.vy = 0.0


            return



        self.vy = max(self.vy + _GRAVITY * dt, _TERMINAL_VEL)
        ny      = self.pos[1] + self.vy * dt
        # print(self.vy, ny)
        # ny    = self.pos[1] + self.vy * dt + 0.5 * _GRAVITY * dt * dt


        if self.vy < 0:
            fb = int(math.floor(ny - 0.001))
            if chunker.iscollide(bx, fb, bz):
                self.pos[1]     = float(fb + 1)
                self.vy         = 0.0
                self._on_ground = True

            else:
                self.pos[1] = ny


        else:
            cb = int(math.floor(ny + 1.001))
            if chunker.iscollide(bx, cb, bz):
                self.pos[1] = float(cb) - 1.0
                self.vy = 0.0

            else:
                self.pos[1] = ny

        self.x = int(math.floor(self.pos[0]))
        self.y = int(math.floor(self.pos[1]))
        self.z = int(math.floor(self.pos[2]))




    def explode(self, wc):
        self.alive = False
        explodeat(wc, float(self.pos[0]), float(self.pos[1]) + 0.06125, float(self.pos[2]), 4.0, skip=self)


    """
    def applygrav(self, dt, chunker):
        self.vy = max(self.vy + _GRAVITY * dt, _TERMINAL_VEL)
        ny = self.pos[1] + self.vy * dt
        bx = int(math.floor(self.pos[0]))
        bz = int(math.floor(self.pos[2]))
        fb = int(math.floor(ny))
        if self.vy < 0 and chunker.issolid(bx, fb, bz):
            self.pos[1]     = float(fb + 1)
            self.vy         = 0.0
            self._on_ground = True
        else:
            self.pos[1]     = ny
            self._on_ground = False
    """

    """
    def knockback(self, p, ex, ey, ez):
        px, py, pz = p.getpos()
        dx, dy, dz = px - ex, py - ey, pz - ez
        dist = math.sqrt(dx*dx + dy*dy + dz*dz) + 0.001
        if dist > BLAST_KNOCK_RAD: return
        f = MAX_KNOCK_FORCE * (1.0 - dist / BLAST_KNOCK_RAD)
        p.vel += np.array([dx/dist * f, dy/dist * f + 4.0, dz/dist * f], dtype='f4')
    """

    def knockback(self, p, ex, ey, ez):
        px, py, pz = p.getpos()
        dx, dy, dz = px - ex, py - ey, pz - ez
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist >= BLAST_KNOCK_RAD or dist < 0.01: return

        strength = (1.0 - dist / BLAST_KNOCK_RAD) * MAX_KNOCK_FORCE
        nx, ny, nz = dx / dist, dy / dist, dz / dist
        # ny = (ny + 1.0) * 0.5
        p.knock((nx * strength, ny * strength + 6.0, nz * strength))







    def getuvs(self):
        if self._uvs is None:
            self._uvs = self.builduvs()
        return self._uvs






    @staticmethod
    def builduvs():
        from world.blocks import blockuvs, UV_W, UV_H, TNT

        buv = blockuvs(TNT)

        def face_quad(uv):
            u0, v0 = uv
            u1, v1 = u0 + UV_W, v0 + UV_H
            return [[u0,v0],[u1,v0],[u1,v1],[u0,v0],[u1,v1],[u0,v1]]


        fmap = [3, 2, 4, 5, 0, 1]
        auv = []
        for i in fmap:
            auv.extend(face_quad(buv[i]))

        return np.array(auv, dtype='f4')






def useflintonsteel(manager, x, y, z, item_stack, world_ref):
    from world.blocks import TNT
    if world_ref.chunker.getblock(x, y, z) != TNT:
        return

    world_ref.chunker.breakblock(x, y, z)

    nc = world_ref.netclient
    if nc and nc.isconn():
        nc.sendchange(x, y, z, 0x4000)  # tnt ignite signal, server spawns it
    else:
        manager.activate(x, y, z, TNT)






def reginteracts():
    from items.textures import FLINT_AND_STEEL
    from world.blocks import TNT
    regitemblock(FLINT_AND_STEEL, TNT, useflintonsteel)

reginteracts()










