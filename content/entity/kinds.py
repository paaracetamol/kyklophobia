import math
import random
import numpy as np

from config import DROP_F, DROP_LIFETIME, DROP_PICKUP_DELAY, ENT_STEP, TICK
from entity import motion
from entity.core import (
    Entity, regentity,
    KIND_TNT, KIND_ITEM, KIND_DUMMY, KIND_ZOMBIE,
    REND_CUBE, REND_SPRITE, REND_MODEL,
)
from entity.ai import Controller, Melee, Wander, LookAt


TNT_FUSE = 4.0




@regentity(KIND_TNT, "tnt", w=0.98, h=0.98, rend=REND_CUBE, pin=True)
class TNTEnt(Entity):
    ownmove = True

    def __init__(self, eid=0, pos=None, fuse=TNT_FUSE, **kw):
        super().__init__(eid=eid, pos=pos, **kw)
        self.fuse = fuse
        
        
        a = random.random() * math.pi * 2.0
        self.mx = -math.sin(a) * 0.02
        self.my = 0.2
        self.mz = -math.cos(a) * 0.02
        self.acc = 0.0


    

    def think(self, dt, w):
        self.acc += dt
        n = 0
        while self.acc >= TICK and n < 5:
            self.acc -= TICK
            n += 1
            self.my -= 0.04
            v = np.array((self.mx, self.my, self.mz), dtype='f4')
            fp, grnd, wall = motion.movebox(w.chunker, self.pos, v, 0.49, 0.98, 0.0, 1.0)
            self.pos = fp
            self.mx, self.my, self.mz = float(v[0]) * 0.98, float(v[1]) * 0.98, float(v[2]) * 0.98
            if grnd:
                self.mx *= 0.7;  self.mz *= 0.7;  self.my *= -0.5
        self.vel[:] = (self.mx / TICK, self.my / TICK, self.mz / TICK)


    def tick(self, dt, w):
        super().tick(dt, w)
        self.fuse -= dt
        if self.fuse <= 0.0: self.kill()


    def dbgtag(self):
        return f"{super().dbgtag()} f{max(self.fuse, 0.0):.1f}"


    def save(self):
        d = super().save()
        d['fuse'] = float(self.fuse)
        return d

    def load(self, d):
        super().load(d)
        self.fuse = d.get('fuse', self.fuse)




@regentity(KIND_ITEM, "item", w=0.25, h=0.25, fric=DROP_F, yoff=0.1, rend=REND_SPRITE)
class ItemDrop(Entity):
    def __init__(self, eid=0, pos=None, iid=0, cnt=1, **kw):
        super().__init__(eid=eid, pos=pos, **kw)
        self.iid   = iid
        self.cnt   = cnt
        self.delay = DROP_PICKUP_DELAY


    def tick(self, dt, w):
        super().tick(dt, w)
        if self.delay > 0.0: self.delay -= dt
        
        if self.age > DROP_LIFETIME or self.pos[1] < 0.0: self.kill()


    def dbgtag(self):
        return f"{super().dbgtag()} i{self.iid}x{self.cnt}"


    def save(self):
        d = super().save()
        d['iid'] = int(self.iid)
        d['cnt'] = int(self.cnt)
        return d

    def load(self, d):
        super().load(d)
        self.iid = d.get('iid', self.iid)
        self.cnt = d.get('cnt', self.cnt)




@regentity(
    KIND_DUMMY, "dummy",
    w=0.6, h=1.8, hp=20, step=ENT_STEP,
    rend=REND_MODEL, persist=True,
)
class DummyEnt(Entity):
    pass




@regentity(
    KIND_ZOMBIE, "zombie",
    w=0.6, h=1.8, hp=20, spd=2.6, step=ENT_STEP,
    rend=REND_MODEL, persist=True, armsup=True,
)
class ZombieEnt(Entity):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.ai = Controller([Melee(), Wander(), LookAt()])



import entity.minecart  # noqa: F401, registers itself
