import json
import math
import os
import random
import threading
from collections import deque

from config import CHUNK_SZ
from items import textures as _T
from items.registry import REGISTRY
from world import blocks as _B
from world.blocks import CHEST, TRAPPED_CHEST, DISPENSER, DROPPER, HOPPER, TNT, FURNACE, FURNACE_ON


SIZES   = {CHEST: 27, TRAPPED_CHEST: 27, DISPENSER: 9, DROPPER: 9, HOPPER: 5, FURNACE: 3, FURNACE_ON: 3}
FURNACES = (FURNACE, FURNACE_ON)
CHESTS  = (CHEST, TRAPPED_CHEST)
HOP_T   = 8


DIRS = ((0,-1,0), (0,1,0), (0,0,-1), (0,0,1), (-1,0,0), (1,0,0))
HOR  = (2, 5, 3, 4)


def maxstack(i):
    d = REGISTRY.get(i)
    return d.max_stack if d else 64


FUEL = (_T.COAL, _T.CHARCOAL)


FUELS = frozenset(
    getattr(_B, i + j)          for i in ('OAK', 'SPRUCE', 'BIRCH', 'JUNGLE', 'ACACIA', 'DARK_OAK') for j in ('_LOG', '_PLANKS', '_STAIRS', '_SLAB', '_FENCE', '_FENCE_GATE')) | frozenset(
    getattr(_B, 'WOOL_' + i)    for i in ('WHITE', 'ORANGE', 'MAGENTA', 'LIGHT_BLUE', 'YELLOW', 'LIME', 'PINK', 'GRAY', 'SILVER', 'CYAN', 'PURPLE', 'BLUE', 'BROWN', 'GREEN', 'RED', 'BLACK')) | frozenset(
    getattr(_B, 'CARPET_' + i)  for i in ('WHITE', 'ORANGE', 'MAGENTA', 'LIGHT_BLUE', 'YELLOW', 'LIME', 'PINK', 'GRAY', 'SILVER', 'CYAN', 'PURPLE', 'BLUE', 'BROWN', 'GREEN', 'RED', 'BLACK')) | frozenset(
    getattr(_B, 'SAPLING_' + i) for i in ('OAK', 'SPRUCE', 'BIRCH', 'JUNGLE', 'ACACIA', 'DARK_OAK')) | frozenset((
    _B.BOOKSHELF, _B.CRAFTING_TABLE, _B.NOTEBLOCK, _B.JUKEBOX, _B.CHEST, _B.TRAPPED_CHEST, _B.LADDER, _B.WOODEN_BUTTON,
    _B.WOODEN_PRESSURE_PLATE, _B.OAK_TRAPDOOR, _B.DAYLIGHT_DETECTOR, _B.BROWN_MUSHROOM_BLOCK, _B.RED_MUSHROOM_BLOCK, _B.COAL_BLOCK,
    _T.COAL, _T.CHARCOAL, _T.STICK, _T.BOW, _T.FISHING_ROD, _T.SIGN, _T.BOWL, _T.BLAZE_ROD, _T.LAVA_BUCKET, _T.BUCKET, _T.BOAT,
    _T.WOOD_AXE, _T.WOOD_HOE, _T.WOOD_PICKAXE, _T.WOOD_SHOVEL, _T.WOOD_SWORD,
    _T.DOOR_WOOD, _T.DOOR_SPRUCE, _T.DOOR_BIRCH, _T.DOOR_JUNGLE, _T.DOOR_ACACIA, _T.DOOR_DARK_OAK,
))
FURN_ONLY  = (None, FUELS, ())
FURN_FACES = {0: (2, 1), 1: (0,)}


def validslot(t, j, iid):
    o = t.only and t.only[j]
    return o is None or iid in o


class Tile:
    __slots__ = ('slots', 'cd', 'tick', 'views', 'only')

    def __init__(self, n, only=None):
        self.only  = only 
        self.slots = [None] * n
        self.cd    = -1 # hopper
        self.tick  = 0 # ticked
        self.views = 0



class Tiles:
    def __init__(self, rs):
        self.rs     = rs
        self.tiles  = {}
        self.lock   = threading.RLock()
        self.loaded = set()
        self.dirty  = set()
        self.chg    = deque()
        self.vq     = deque() 
        self.onchg  = None 
        self.carts   = {}
        self.cartpos = {}


    def reset(self):
        with self.lock:
            self.tiles.clear()
            self.loaded.clear()
            self.dirty.clear()
            self.chg.clear()
            self.vq.clear()
            self.carts.clear()
            self.cartpos.clear()



    


    # disk
    def path(self, cx, cz): 
        return os.path.join(self.rs.cm.world_dir, f"{cx}_{cz}.tile")


    def loadck(self, cx, cz):
        if (cx, cz) in self.loaded or not self.rs.cm.is_server: return

        with self.lock:

            self.loaded.add((cx, cz))

            fp = self.path(cx, cz)
            if not os.path.exists(fp): return
            
            with open(fp) as f: d = json.load(f)
            for k, j in d.items():
                t = Tile(len(j['s']))
                t.slots = [i and list(i) for i in j['s']]

                t.cd = j.get('cd', -1)
                self.tiles[tuple(int(i) for i in k.split(','))] = t




    def save(self):
        with self.lock:
            if not self.dirty or not self.rs.cm.is_server:
                self.dirty.clear()
                return


            for ck in self.dirty:
                d = {
                    f"{x},{y},{z}": {'s': t.slots, 'cd': t.cd}
                    for (x, y, z), t in self.tiles.items()
                    if (
                        (x // CHUNK_SZ, z // CHUNK_SZ) == ck and any(t.slots) or 
                        (x // CHUNK_SZ, z // CHUNK_SZ) == ck and  t.cd >= 0
                    )
                }

                fp = self.path(*ck)

                if d:
                    with open(fp, 'w') as f: json.dump(d, f)
                elif os.path.exists(fp): os.remove(fp)


            self.dirty.clear()







    def get(self, x, y, z):
        b = self.rs.raw(x, y, z) & 0x3FF
        if b not in SIZES: return None
        with self.lock:
            self.loadck(x // CHUNK_SZ, z // CHUNK_SZ)
            t = self.tiles.get((x, y, z))
            if t is None or len(t.slots) != SIZES[b]:
                t = Tile(SIZES[b])
                self.tiles[(x, y, z)] = t
            if b in FURNACES: t.only = FURN_ONLY
            return t




    def mark(self, x, y, z):
        self.dirty.add((x // CHUNK_SZ, z // CHUNK_SZ))
        self.chg.append((x, y, z))




    # block broken
    def remove(self, x, y, z):
        with self.lock:

            self.loadck(x // CHUNK_SZ, z // CHUNK_SZ)
            t = self.tiles.pop((x, y, z), None)
            if t is None: return

            self.dirty.add((x // CHUNK_SZ, z // CHUNK_SZ))

            for i in t.slots:
                if i and self.rs.spawn:

                    # same spread as broken container
                    px = x + random.random() * 0.8 + 0.1
                    py = y + random.random() * 0.8 + 0.1
                    pz = z + random.random() * 0.8 + 0.1
                    n  = i[1]

                    while n > 0:
                        c = min(n, random.randint(10, 30))
                        n -= c
                        v = (
                            random.gauss(0, 0.05) * 20.0,
                            (random.gauss(0, 0.05) + 0.2) * 20.0,
                            random.gauss(0, 0.05) * 20.0,
                        )
                        self.rs.spawn(i[0], c, (px, py, pz), v)






    # (tile,index) p slot
    def view(self, x, y, z, ignore=False):

        if y < 0:
            t = self.carts.get(x)
            return [(t, i) for i in range(len(t.slots))] if t else None


        rs = self.rs
        b  = rs.raw(x, y, z) & 0x3FF
        t  = self.get(x, y, z)
        if t is None: return None

        v  = [(t, i) for i in range(len(t.slots))]
        if b not in CHESTS: return v


        if not ignore and self.chestshut(x, y, z): 
            return None


        for d in HOR:
            o = DIRS[d]
            nx, nz = x + o[0], z + o[2]

            if rs.raw(nx, y, nz) & 0x3FF != b: continue
            if self.chestshut(nx, y, nz): return None

            n  = self.get(nx, y, nz)
            nv = [(n, i) for i in range(len(n.slots))]
            v  = nv + v if d in (4, 2) else v + nv

        return v




    def chestshut(self, x, y, z): return self.rs.cube(x, y + 1, z)



    def setslot(self, x, y, z, i, st):
        with self.lock:

            v = self.view(x, y, z, True)
            if v is None or not 0 <= i < len(v): return False

            t, j = v[i]
            if st and not validslot(t, j, st[0]): return False
            t.slots[j] = list(st) if st else None

            self.markview(v)
            return True



    def cartinv(self, eid, n, only=None):
        with self.lock:
            t = self.carts.get(eid)
            if t is None:
                t = Tile(n, only)
                self.carts[eid] = t


            return t


    # dropped inside entity lock
    def cartgone(self, eid, sp):
        with self.lock:
            self.cartpos.pop(eid, None)
            t = self.carts.pop(eid, None)

            if t is None: return
            for i in t.slots:
                if i: self.rs.spawnq.append(
                    (i[0], i[1], sp, (0.0, 2.0, 0.0))
                )




    def markview(self, v):

        for eid, t in self.carts.items():
            for u, _ in v:
                if u is t:
                    self.chg.append((eid, -1, 0))
                    break

        for k, t in self.tiles.items():
            for u, _ in v:
                if u is t:
                    self.mark(*k)
                    break




    def snapshot(self, x, y, z):
        with self.lock:

            v = self.view(x, y, z, True)
            if v is None: return None

            return [t.slots[j] and tuple(t.slots[j]) for t, j in v]




    def viewers(self, x, y, z, d):
        with self.lock:
            b = self.rs.raw(x, y, z) & 0x3FF
            if b not in CHESTS: return
            ps = [(x, z)]


            for i in HOR:
                o = DIRS[i]
                if self.rs.raw(x + o[0], y, z + o[2]) & 0x3FF == b: 
                    ps.append((x + o[0], z + o[2]))

            for px, pz in ps:
                t = self.get(px, y, pz)
                t.views = max(0, t.views + d)
                self.vq.append((px, y, pz, b))



    def chestviews(self, x, y, z):
        t = self.tiles.get((x, y, z))
        return min(t.views, 15) if t else 0




    

    def signal(self, x, y, z):
        with self.lock:

            v = self.view(x, y, z)
            if v is None: return 0
            i = 0
            f = 0.0

            for t, j in v:
                s = t.slots[j]
                if s:
                    f += s[1] / float(min(64, maxstack(s[0])))
                    i += 1

            f /= len(v)

            return math.floor(f * 14.0) + (1 if i > 0 else 0)





    # hopper tick
    def invat(self, x, y, z, face=None):
        b = self.rs.raw(x, y, z) & 0x3FF

        if b in SIZES:
            v = self.view(x, y, z, True)
            if b in FURNACES and face is not None: 
                return [v[i] for i in FURN_FACES.get(face, (1,))]

            return v


        
        
        l = [
            eid for eid, p in self.cartpos.items()
            if (
                self.rs.now - p[3] < 5 and 
                abs(p[0] - (x + 0.5)) < 0.99 and 
                abs(p[2] - (z + 0.5)) < 0.99 and 
                y - 0.7 < p[1] < y + 1
            )
        ]
        return self.view(random.choice(l), -1, 0) if l else None


    
    
    def insert(self, src, dst, st, srcpos=None):
        for t, j in dst:
            if not st: break
            st = self.insertone(src, t, j, st)

        return st





    def insertone(self, src, t, j, st):
        if not validslot(t, j, st[0]): return st
        cur = t.slots[j]
        was = not any(t.slots)
        moved = False

        if cur is None:
            t.slots[j] = st
            st = None
            moved = True


        elif cur[0] == st[0] and cur[1] <= maxstack(st[0]):
            n = min(st[1], maxstack(st[0]) - cur[1])

            st = [st[0], st[1] - n] if st[1] > n else None
            cur[1] += n
            moved = n > 0



        if moved:
            # mayTransfer = cd > 8
            if was and t.cd <= 8 and len(t.slots) == 5:
                k = 0

                if src is not None and len(src.slots) == 5 and t.tick >= src.tick: k = 1
                t.cd = HOP_T - k


            for p, u in self.tiles.items():
                if u is t: self.mark(*p)

        return st






    def hoptick(self):
        rs = self.rs
        with self.lock:
            for (x, y, z), t in list(self.tiles.items()):

                if len(t.slots) != 5 or not rs.loaded(x, y, z): continue
                if rs.raw(x, y, z) & 0x3FF != HOPPER: continue
                
                if t.cd < 0: t.cd = 0
                t.cd  -= 1
                t.tick = rs.now
                if t.cd > 0: continue

                t.cd = 0
                self.hoprun(x, y, z, t)


    def hoprun(self, x, y, z, t):
        st = (self.rs.raw(x, y, z) >> 10) & 0x1F
        if st & 8: return False


        flag = False
        if any(t.slots):
            flag = self.hopout(x, y, z, t, st & 7)

        if not all(i and i[1] == maxstack(i[0]) for i in t.slots):
            flag = self.hoppull(x, y, z, t) or flag

        if flag:
            t.cd = HOP_T
            self.mark(x, y, z)
        return flag




    def hopout(self, x, y, z, t, f):
        o   = DIRS[f]
        dst = self.invat(x + o[0], y + o[1], z + o[2], f ^ 1)

        if dst is None: return False
        if all(
            u.slots[j] and 
            u.slots[j][1] == maxstack(u.slots[j][0]) for u, j in dst
        ): return False


        for i in range(len(t.slots)):
            s = t.slots[i]
            if not s: continue

            rest = self.insert(t, dst, [s[0], 1])
            if rest is None:
                s[1] -= 1
                if s[1] <= 0: t.slots[i] = None
                self.markview(dst)
                
                return True


        return False




    def hoppull(self, x, y, z, t):
        src = self.invat(x, y + 1, z, 0)
        me  = [(t, i) for i in range(len(t.slots))]

        if src is not None:
            for u, j in src:
                s = u.slots[j]

                if not s or (u.only and u.only[j] and s[0] != _T.BUCKET): continue

                if self.insert(None, me, [s[0], 1]) is None:
                    s[1] -= 1
                    if s[1] <= 0: u.slots[j] = None

                    self.markview(src)
                    return True


            return False




        #box
        if not self.rs.itemsin: return False

        cx, cy, cz = x + 0.5, y + 0.5, z + 0.5

        for iid, cnt, setn in self.rs.itemsin(
            cx - 0.5, cy, 
            cz - 0.5, cx + 0.5, 
            cy + 1.5, cz + 0.5
        ):
            r = self.insert(None, me, [iid, cnt])

            if r is None:
                setn(0)
                return True

            setn(r[1])


        return False







    # dispenser
    def pick(self, t):
        i, j = -1, 1
        for k, s in enumerate(t.slots):
            if s:
                if random.randrange(j) == 0: i = k
                j += 1
        return i


    
    
    def dispense(self, x, y, z, b, f):
        with self.lock:

            t = self.get(x, y, z)
            if t is None: return

            i = self.pick(t)
            if i < 0: return

            s = t.slots[i]
            o = DIRS[f]
            

            if b == DROPPER:
                dst = self.invat(x + o[0], y + o[1], z + o[2], f ^ 1)

                if dst is not None:
                    if self.insert(t, dst, [s[0], 1]) is None:
                        self.take(t, i, x, y, z)
                        self.markview(dst)

                    return



            # BlockDispenser TNT behaviour
            elif s[0] == TNT:
                tx, ty, tz = x + o[0], y + o[1], z + o[2]
                if self.rs.ontnt: self.rs.ontnt(tx, ty, tz)
                self.take(t, i, x, y, z)
                return

            self.drop(x, y, z, f, s[0])
            self.take(t, i, x, y, z)




    def take(self, t, i, x, y, z):
        t.slots[i][1] -= 1
        if t.slots[i][1] <= 0: t.slots[i] = None
        self.mark(x, y, z)



    # doDispense, speed=6
    def drop(self, x, y, z, f, iid):
        o  = DIRS[f]
        px = x + 0.5 + 0.7 * o[0]
        py = y + 0.5 + 0.7 * o[1] - (0.125 if o[1] else 0.15625)
        pz = z + 0.5 + 0.7 * o[2]

        k  = random.random() * 0.1 + 0.2
        g  = 0.0075 * 6

        v  = (
            (o[0] * k + random.gauss(0, 1) * g) / 0.05,
            (0.2 + random.gauss(0, 1) * g) / 0.05,
            (o[2] * k + random.gauss(0, 1) * g) / 0.05,
        )

        if self.rs.spawn: self.rs.spawn(iid, 1, (px, py, pz), v)






























