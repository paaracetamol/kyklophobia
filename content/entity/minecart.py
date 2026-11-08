import math
import random
import numpy as np

from config import TICK
from entity import motion
from entity.core import (
    Entity, regentity, 
    REND_CART, KIND_CART, KIND_CHESTCART, 
    KIND_FURNACECART, KIND_TNTCART, KIND_HOPPERCART,
)
from items import textures as _T
from items.textures import MINECART
from world.blocks import CHEST, FURNACE, TNT, HOPPER
from world.blocks import ACTIVATOR_RAIL, POWERED_RAIL_ON, POWERED_RAIL
from world.container import FUEL
from world.redstone import ALLRAILS, railshape, NS, EW, ASC_E, ASC_W, ASC_N, ASC_S, RAILPW




# cart entity matrx
MATRIX = (
    ((0,   0, -1), (0,  0, 1)), ((-1, 0,  0), (1,  0, 0)), 
    ((-1, -1,  0), (1,  0, 0)), ((-1, 0,  0), (1, -1, 0)),
    ((0,   0, -1), (0, -1, 1)), ((0, -1, -1), (0,  0, 1)), 
    ((0,   0,  1), (1,  0, 0)), ((0,  0,  1), (-1, 0, 0)),
    ((0,   0, -1), (-1, 0, 0)), ((0,  0, -1), (1,  0, 0)),
)
ASCENDING = (ASC_E, ASC_W, ASC_N, ASC_S)
MAXSPD    = 0.4
RIDEOFF   = -0.35 # player y offset
SWEEPEPS  = 1e-3
flr = math.floor






def sweep(ck, px, py, pz, hw, h, x, y, z):

    a = [
        px - hw, py, 
        pz - hw, px + hw, 
        py + h, pz + hw
    ]

    bs = list(
        ck.rs.colboxes(
            a[0] + min(x, 0.0), a[1] + min(y, 0.0), 
            a[2] + min(z, 0.0), a[3] + max(x, 0.0), 
            a[4] + max(y, 0.0), a[5] + max(z, 0.0)
    ))
    o = [y, x, z]

    for n, i, j, k in ((0, 1, 0, 2), (1, 0, 1, 2), (2, 2, 0, 1)):
        
        d = o[n]
        for b in bs:
            if b[j + 3] <= a[j] or b[j] >= a[j + 3] or b[k + 3] <= a[k] or b[k] >= a[k + 3]: continue
            if   d > 0.0 and b[i] >= a[i + 3] - SWEEPEPS: d = min(d, max(b[i] - a[i + 3], 0.0))
            elif d < 0.0 and b[i + 3] <= a[i] + SWEEPEPS: d = max(d, min(b[i + 3] - a[i], 0.0))


        o[n] = d
        a[i] += d
        a[i + 3] += d

    return o[1], o[0], o[2]






def israil(ck, x, y, z): return ck.getblock(x, y, z) in ALLRAILS


def railv(ck, x, y, z):
    c = ck.chunks.get((x // 16, z // 16))
    if not c or not c.gen_ready or y < 0 or y >= 128: return 0

    return int(c.voxels[x - c.offset_x, y, z - c.offset_z])






# get pos on rail under xyz
def railpos(ck, x, y, z):

    i, j, k = flr(x), flr(y), flr(z)
    if israil(ck, i, j - 1, k): j -= 1
    v = railv(ck, i, j, k)

    
    if v & 0x3FF not in ALLRAILS: return None
    a, b = MATRIX[railshape(v)]

    d0, d1, d2 = i + 0.5 + a[0] * 0.5, j + 0.0625 + a[1] * 0.5, k + 0.5 + a[2] * 0.5
    d3, d4, d5 = i + 0.5 + b[0] * 0.5, j + 0.0625 + b[1] * 0.5, k + 0.5 + b[2] * 0.5
    d6, d7, d8 = d3 - d0, (d4 - d1) * 2.0, d5 - d2


    if   d6 == 0.0: t = z - k
    elif d8 == 0.0: t = x - i
    else: 
        t = ((x - d0) * d6 + (z - d2) * d8) * 2.0


    rx, ry, rz = d0 + d6 * t, d1 + d7 * t, d2 + d8 * t
    if d7 < 0.0: ry += 1.0
    if d7 > 0.0: ry += 0.5

    return rx, ry, rz







# tilt
def railoff(ck, x, y, z, o):
    i, j, k = flr(x), flr(y), flr(z)

    if israil(ck, i, j - 1, k): j -= 1
    v = railv(ck, i, j, k)


    if v & 0x3FF not in ALLRAILS: return None
    d = railshape(v)
    
    y = float(j)
    if d in ASCENDING: y = float(j + 1)


    a, b = MATRIX[d]
    d0, d1 = float(b[0] - a[0]), float(b[2] - a[2])

    l = math.sqrt(d0 * d0 + d1 * d1)
    x += d0 / l * o
    z += d1 / l * o

    if   a[1] != 0 and flr(x) - i == a[0] and flr(z) - k == a[2]: y += a[1]
    elif b[1] != 0 and flr(x) - i == b[0] and flr(z) - k == b[2]: y += b[1]


    return railpos(ck, x, y, z)






@regentity(KIND_CART, "minecart", w=0.98, h=0.7, hp=5, grav=0.0, rend=REND_CART)
class MinecartEnt(Entity):
    ownmove  = True
    rideable = True
    maxspd   = MAXSPD
    showblk  = 0      # block in cart
    showoff  = 6      # tile offset
    extra    = None   # drop




    def __init__(self, **kw):
        super().__init__(**kw)
        self.mx = self.my = self.mz = 0.0
        self.opos    = self.pos.copy()
        self.acc     = 0.0
        self.alpha   = 0.0
        self.flip    = False
        self.oyaw    = self.yaw
        self.rider   = None
        self.ongnd   = False
        self.onrail  = False
        self.hwall   = False
        self.hspeed  = 0.0
        self.w       = None





    


    def knock(self, v): pass


    def kill(self):

        if self.alive and self.w is not None:
            ck = self.w.chunker
            sp = (
                float(self.pos[0]), 
                float(self.pos[1]) + 0.1, 
                float(self.pos[2])
            )

            ck.rs.spawnq.append((MINECART, 1, sp, (0.0, 2.0, 0.0)))
            if self.extra: 
                ck.rs.spawnq.append((self.extra, 1, sp, (0.0, 2.0, 0.0)))

            self.eject()
            self.ondie(ck, sp)

        self.alive = False





    def ondie(self, ck, sp): pass
    def track2(self, w): pass
    def tick2(self, w): pass


    def eject(self):
        r = self.rider
        self.rider = None

        if r is not None and self.w is not None: 
            self.w.cartkick(r, self)




    def think(self, dt, w):
        self.w = w
        self.acc += dt

        n = 0
        while self.acc >= TICK and n < 5:
            self.acc -= TICK
            n += 1
            self.step(w)


        if n >= 5: self.acc = 0.0
        self.alpha = self.acc / TICK




    # server update
    def step(self, w):
        ck = w.chunker
        if not motion.loaded(ck, self.pos[0], self.pos[2]):
            self.frozen = True
            return

        self.frozen = False



        self.opos[:] = self.pos
        self.oyaw    = self.yaw
        ox, oz = float(self.pos[0]), float(self.pos[2])

        self.my -= 0.04
        k, l, i1 = flr(self.pos[0]), flr(self.pos[1]), flr(self.pos[2])
        if israil(ck, k, l - 1, i1): l -= 1


        v = railv(ck, k, l, i1)
        self.onrail = v & 0x3FF in ALLRAILS

        if self.onrail:
            self.track(w, k, l, i1, v)
            self.track2(w)
            if v & 0x3FF == ACTIVATOR_RAIL: 
                self.activator(bool((v >> 10) & RAILPW))
            ck.rs.cartseen[(k, l, i1)] = ck.rs.now


        else:
            self.offrail(ck)





        # travel yaw -> flips 170<
        d0, d2 = ox - float(self.pos[0]), oz - float(self.pos[2])

        if d0 * d0 + d2 * d2 > 0.001:
            self.yaw = math.degrees(math.atan2(d2, d0))
            if self.flip: self.yaw += 180.0

        d3 = (self.yaw - self.oyaw + 180.0) % 360.0 - 180.0
        if d3 < -170.0 or d3 >= 170.0:
            self.yaw += 180.0
            self.flip = not self.flip

        self.bump(w)
        self.tick2(w)


        self.vel[:] = (self.mx / TICK, self.my / TICK, self.mz / TICK)
        sp = abs(self.mx) + abs(self.mz)
        self.still = sp < 0.001 and self.ongnd

        if self.pos[1] < -64: self.kill()





   
   
    
    def activator(self, on):
        if on and self.rider is not None: self.eject()


    
    def move(self, ck, x, y, z):
        px, py, pz = float(self.pos[0]), float(self.pos[1]), float(self.pos[2])
        dx, dy, dz = sweep(ck, px, py, pz, self.type.hw, self.type.h, x, y, z)

        self.hspeed = x * x + z * z
        self.hwall  = dx != x or dz != z
        self.ongnd  = dy != y and y < 0.0
        self.pos    = np.array((px + dx, py + dy, pz + dz), dtype='f4')

        if dx != x: self.mx = 0.0
        if dz != z: self.mz = 0.0
        if dy != y: self.my = 0.0




    # move derailed
    def offrail(self, ck):
        self.mx = max(-self.maxspd, min(self.maxspd, self.mx))
        self.mz = max(-self.maxspd, min(self.maxspd, self.mz))

        if self.ongnd:
            self.mx *= 0.5
            self.my *= 0.5
            self.mz *= 0.5
            
        self.move(ck, self.mx, self.my, self.mz)
        if not self.ongnd:
            self.mx *= 0.95
            self.my *= 0.95
            self.mz *= 0.95



    # move railed
    def track(self, w, bx, by, bz, v):
        ck = w.chunker
        px, py, pz = float(self.pos[0]), float(self.pos[1]), float(self.pos[2])
        v0 = railpos(ck, px, py, pz)
        py = float(by)


        b  = v & 0x3FF
        fl = b == POWERED_RAIL_ON
        fl1 = b == POWERED_RAIL
        d  = railshape(v)

        if   d == ASC_E: 
            self.mx -= 0.0078125
            py += 1.0
        elif d == ASC_W: 
            self.mx += 0.0078125
            py += 1.0
        elif d == ASC_N: 
            self.mz += 0.0078125
            py += 1.0
        elif d == ASC_S: 
            self.mz -= 0.0078125
            py += 1.0


        a0, a1 = MATRIX[d]
        d1, d2 = float(a1[0] - a0[0]), float(a1[2] - a0[2])
        d3 = math.sqrt(d1 * d1 + d2 * d2)

        if self.mx * d1 + self.mz * d2 < 0.0:
            d1, d2 = -d1, -d2

        d5 = min(math.sqrt(self.mx * self.mx + self.mz * self.mz), 2.0)
        self.mx = d5 * d1 / d3
        self.mz = d5 * d2 / d3



        # forward key
        r = self.rider
        if r is not None:
            fw, yw = w.cartinput(r)
            if fw > 0.0 and self.mx * self.mx + self.mz * self.mz < 0.01:
                self.mx += math.cos(math.radians(yw)) * 0.1
                self.mz += math.sin(math.radians(yw)) * 0.1
                fl1 = False

        if fl1:
            if math.sqrt(self.mx * self.mx + self.mz * self.mz) < 0.03:
                self.mx = self.my = self.mz = 0.0

            else:
                self.mx *= 0.5
                self.my  = 0.0
                self.mz *= 0.5


        d18, d19 = bx + 0.5 + a0[0] * 0.5, bz + 0.5 + a0[2] * 0.5
        d20, d21 = bx + 0.5 + a1[0] * 0.5, bz + 0.5 + a1[2] * 0.5
        d1, d2 = d20 - d18, d21 - d19

        if d1 == 0.0:
            px = bx + 0.5
            t  = pz - bz
        elif d2 == 0.0:
            pz = bz + 0.5
            t  = px - bx
        else:
            t = ((px - d18) * d1 + (pz - d19) * d2) * 2.0



        px, pz = d18 + d1 * t, d19 + d2 * t
        self.pos = np.array((px, py, pz), dtype='f4')

        dd = 0.75 if r is not None else 1.0
        d22 = max(-self.maxspd, min(self.maxspd, self.mx * dd))
        d23 = max(-self.maxspd, min(self.maxspd, self.mz * dd))
        self.move(ck, d22, 0.0, d23)




        px, py, pz = float(self.pos[0]), float(self.pos[1]), float(self.pos[2])
        if a0[1]   != 0 and flr(px) - bx == a0[0] and flr(pz) - bz == a0[2]: py += a0[1]
        elif a1[1] != 0 and flr(px) - bx == a1[0] and flr(pz) - bz == a1[2]: py += a1[1]

        self.applydrag(r)

        v1 = railpos(ck, px, py, pz)
        if v1 is not None and v0 is not None:
            d14 = (v0[1] - v1[1]) * 0.05
            d5  = math.sqrt(self.mx * self.mx + self.mz * self.mz)

            if d5 > 0.0:
                self.mx = self.mx / d5 * (d5 + d14)
                self.mz = self.mz / d5 * (d5 + d14)

            py = v1[1]


        self.pos = np.array((px, py, pz), dtype='f4')

        j, i = flr(px), flr(pz)
        if j != bx or i != bz:
            d5 = math.sqrt(self.mx * self.mx + self.mz * self.mz)
            self.mx = d5 * (j - bx)
            self.mz = d5 * (i - bz)




        if fl:
            d15 = math.sqrt(self.mx * self.mx + self.mz * self.mz)

            if d15 > 0.01:
                self.mx += self.mx / d15 * 0.06
                self.mz += self.mz / d15 * 0.06

            elif d == EW:
                if   ck.rs.cube(bx - 1, by, bz): self.mx = 0.02
                elif ck.rs.cube(bx + 1, by, bz): self.mx = -0.02

            elif d == NS:
                if   ck.rs.cube(bx, by, bz - 1): self.mz = 0.02
                elif ck.rs.cube(bx, by, bz + 1): self.mz = -0.02

        self.ongnd = True












    def applydrag(self, r):
        dg = 0.997 if r is not None else 0.96
        self.mx *= dg
        self.my = 0.0
        self.mz *= dg


    def box(self, g=0.0):
        hw = self.type.hw + g
        return (
            self.pos[0] - hw, self.pos[1], 
            self.pos[2] - hw, self.pos[0] + hw, 
            self.pos[1] + self.type.h, 
            self.pos[2] + hw
        )


    
    

    def bump(self, w):
        b = self.box(0.2)
        hit = lambda a: (
            a[0] < b[3] and a[3] > b[0] and 
            a[1] < b[4] and a[4] > b[1] and 
            a[2] < b[5] and a[5] > b[2]
        )


        mov = self.mx * self.mx + self.mz * self.mz > 0.01
        for e in w.cartbodies():
            if e is self or e is self.rider or getattr(e, 'riding', None) is not None: continue
            eb = e.cbox()

            if not hit(eb): continue
            if isinstance(e, MinecartEnt):
                self.collide(e)

            elif e.type.hp > 0 and mov and self.rider is None and self.rideable:
                self.rider = e
                e.riding   = self



        for p in w.aiplayers():
            if p is self.rider or getattr(p, 'ride', None) is not None: continue
            ph = w.cartplayerbox(p)
            if hit(ph): 
                self.pushed(
                    float(ph[0] + ph[3]) / 2.0, 
                    float(ph[2] + ph[5]) / 2.0
                )




    def pushed(self, x, z):
        d0, d1 = x - float(self.pos[0]), z - float(self.pos[2])
        d2 = d0 * d0 + d1 * d1
        if d2 < 1e-4: return


        d2 = math.sqrt(d2)
        d0, d1 = d0 / d2, d1 / d2
        d3 = min(1.0 / d2, 1.0)
        self.mx -= d0 * d3 * 0.05
        self.mz -= d1 * d3 * 0.05





    
    def collide(self, o):

        d0, d1 = float(o.pos[0] - self.pos[0]), float(o.pos[2] - self.pos[2])
        d2 = d0 * d0 + d1 * d1
        if d2 < 1e-4: return

        d2 = math.sqrt(d2)
        ax, az = d0 / d2, d1 / d2
        d3 = min(1.0 / d2, 1.0)
        d0, d1 = ax * d3 * 0.05, az * d3 * 0.05

        y = math.radians(self.yaw)
        if abs(ax * math.cos(y) + az * math.sin(y)) < 0.8: return


        d7, d8 = (o.mx + self.mx) / 2.0, (o.mz + self.mz) / 2.0
        self.mx = self.mx * 0.2 + d7 - d0
        self.mz = self.mz * 0.2 + d8 - d1
        o.mx    = o.mx * 0.2 + d7 + d0
        o.mz    = o.mz * 0.2 + d8 + d1



    def cbox(self): return self.box()




# cart container
# @ world.container, key (eid, -1, 0)
class ContCart(MinecartEnt):
    rideable = False
    slots    = 27
    only     = None

    def invt(self, ck): return ck.rs.tiles.cartinv(self.eid, self.slots, self.only)

    def tick2(self, w):
        ck = w.chunker
        self.invt(ck)

        ck.rs.tiles.cartpos[self.eid] = (
            float(self.pos[0]), float(self.pos[1]), 
            float(self.pos[2]), ck.rs.now
        )



    def ondie(self, ck, sp): ck.rs.tiles.cartgone(self.eid, sp)







@regentity(
    KIND_CHESTCART, "minecart_chest", 
    w=0.98, h=0.7, hp=5, grav=0.0, rend=REND_CART
)
class ChestCart(ContCart):
    showblk = CHEST
    showoff = 8
    extra   = CHEST


@regentity(
    KIND_HOPPERCART, "minecart_hopper", 
    w=0.98, h=0.7, hp=5, grav=0.0, rend=REND_CART
)
class HopperCart(ContCart):
    slots   = 5
    showblk = HOPPER
    showoff = 1
    extra   = _T.HOPPER if hasattr(_T, 'HOPPER') else 0

    def __init__(self, **kw):
        super().__init__(**kw)
        self.enabled = True
        self.cd      = 0
        self.last    = None



    
    def activator(self, on): self.enabled = not on


    def tick2(self, w):
        super().tick2(w)


        if not self.enabled: return
        tl = w.chunker.rs.tiles
        bp = (
            flr(self.pos[0]), 
            flr(self.pos[1]), 
            flr(self.pos[2])
        )


        if bp == self.last: self.cd -= 1
        else: self.cd = 0

        self.last = bp
        if self.cd > 0: return
        self.cd = 0

        t = self.invt(w.chunker)

        with tl.lock:
            if tl.hoppull(bp[0], flr(self.pos[1] + 0.5), bp[2], t):
                self.cd = 4
                tl.chg.append((self.eid, -1, 0))







@regentity(
    KIND_FURNACECART, "minecart_furnace", 
    w=0.98, h=0.7, hp=5, grav=0.0, rend=REND_CART
)
class FurnaceCart(ContCart):
    slots    = 1 #coal
    only     = (FUEL,)
    maxspd   = 0.2
    showblk  = FURNACE
    extra    = FURNACE

    def __init__(self, **kw):
        super().__init__(**kw)
        self.fuel = 0
        self.pushx = self.pushz = 0.0






    def tick2(self, w):
        super().tick2(w)

        if self.fuel > 0: self.fuel -= 1
        elif self.pushx or self.pushz:

            tl = w.chunker.rs.tiles
            with tl.lock:
                s = self.invt(w.chunker).slots[0]


                if s:
                    self.fuel = 3600
                    tl.setslot(
                        self.eid, -1, 0, 0, 
                        (s[0], s[1] - 1) if s[1] > 1 else None
                    )


        if self.fuel <= 0: self.pushx = self.pushz = 0.0





    
    def track2(self, w):
        d0 = self.pushx * self.pushx + self.pushz * self.pushz
        if d0 > 1e-4 and self.mx * self.mx + self.mz * self.mz > 0.001:
            d0 = math.sqrt(d0)

            self.pushx /= d0
            self.pushz /= d0


            if self.pushx * self.mx + self.pushz * self.mz < 0.0:
                self.pushx = self.pushz = 0.0

            else:
                d1 = d0 / self.maxspd
                self.pushx *= d1
                self.pushz *= d1





    def applydrag(self, r):
        d0 = self.pushx * self.pushx + self.pushz * self.pushz

        if d0 > 1e-4:
            d0 = math.sqrt(d0)
            self.pushx /= d0
            self.pushz /= d0
            self.mx *= 0.8
            self.my = 0.0
            self.mz *= 0.8
            self.mx += self.pushx
            self.mz += self.pushz

        else:
            self.mx *= 0.98
            self.my = 0.0
            self.mz *= 0.98

        super().applydrag(r)




    # use coal
    def use(self, px, pz, coal):
        if coal and self.fuel + 3600 <= 32000: self.fuel += 3600
        self.pushx = float(self.pos[0]) - px
        self.pushz = float(self.pos[2]) - pz



@regentity(
    KIND_TNTCART, "minecart_tnt", 
    w=0.98, h=0.7, hp=5, grav=0.0, rend=REND_CART
)
class TntCart(MinecartEnt):
    rideable = False
    showblk  = TNT
    extra    = TNT

    def __init__(self, **kw):
        super().__init__(**kw)
        self.fuse = -1
        self.dead = False
        self.fall = 0.0
        self.told = False




    def activator(self, on):
        if on and self.fuse < 0: self.fuse = 80


    def lightquick(self):
        if self.fuse < 0: 
            self.fuse = random.randrange(20) + random.randrange(20)


    

    def kill(self):
        if self.alive and not self.dead and self.mx * self.mx + self.mz * self.mz >= 0.01:
            self.lightquick()
            self.hp = 1
            return

        super().kill()




    
    def blasted(self): self.lightquick()


    
    def boom(self, w, v2):

        if self.dead: return
        self.dead = True

        d = min(math.sqrt(v2), 5.0)
        w.cartboom(
            float(self.pos[0]), float(self.pos[1]), float(self.pos[2]), 
            4.0 + random.random() * 1.5 * d, self.fuse > -1
        )
        self.alive = False


    
    
    def tick(self, dt, w):
        super().tick(dt, w)
        
        if not w.chunker.netmode or self.fuse <= 0: return


        self.acc += dt
        while self.acc >= TICK and self.fuse > 0:
            self.acc -= TICK
            self.fuse -= 1


        self.alpha = self.acc / TICK






    def tick2(self, w):
        v2 = self.mx * self.mx + self.mz * self.mz
        if self.fuse > -1 and not self.told:
            self.told = True
            w.cartlit(self)

        if self.fuse > 0:
            self.fuse -= 1

        elif self.fuse == 0:
            self.boom(w, v2)
            return

        if self.hwall and self.hspeed >= 0.01:
            self.boom(w, self.hspeed)
            return



        # fall()
        if self.my < 0.0 and not self.ongnd: 
            self.fall -= self.my


        if self.ongnd:
            if self.fall >= 3.0 and not self.onrail: 
                self.boom(w, (self.fall / 10.0) ** 2)
            self.fall = 0.0



















CARTITEMS = {
    _T.MINECART: KIND_CART, 
    _T.MINECART_CHEST: KIND_CHESTCART, 
    _T.MINECART_FURNACE: KIND_FURNACECART,
    _T.MINECART_TNT: KIND_TNTCART, 
    _T.MINECART_HOPPER: KIND_HOPPERCART,
}
CARTKINDS = frozenset(CARTITEMS.values())





























