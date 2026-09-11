import numpy as np
import math
from config import (
    P_W, P_H, P_EYE_H, P_EYE_F,
    GRAV, DRAG_Y, FRIC_AIR, FRIC_TILE, FRIC_ICE, FRIC_SLIME,
    ACC_BASE, AIR_ACC, AIR_SPRINT, STEP_H, PUSHOUT,
    WATER_ACC, WATER_DRAG, WATER_GRAV, LAVA_DRAG,
    LADDER_CLAMP,
    GRAVITY, TERM_V, JUMP_V,
    MAX_GSPEED, MAX_FSPEED, MP_SPRINT,
    FL_SPEED, FL_SPEED_MP,
    SURF_FRIC, AIR_RES, SURF_ACCEL, AIR_ACCEL,
    FL_ACCEL, FL_FRIC
)
from world.blocks import (
    ICE, ICE_PACKED, SLIME, WATER, WATER_FLOWING, LAVA, LAVA_FLOWING, LADDER, VINE
)

flr, cl = math.floor, math.ceil

FRIC = {ICE: FRIC_ICE, ICE_PACKED: FRIC_ICE, SLIME: FRIC_SLIME}

WATERY = (WATER, WATER_FLOWING)
LAVAY  = (LAVA, LAVA_FLOWING)


class AABB:
    def __init__(self, mn, mx):
        self.min = np.array(mn, dtype='f4')
        self.max = np.array(mx, dtype='f4')

    def intersects(self, other):
        return (
            self.min[0] <= other.max[0] and self.max[0] >= other.min[0] and
            self.min[1] <= other.max[1] and self.max[1] >= other.min[1] and
            self.min[2] <= other.max[2] and self.max[2] >= other.min[2]
        )

    def expand(self, amt):
        off = np.array([amt, amt, amt], dtype='f4')
        return AABB(self.min - off, self.max + off)





class PhysicsEngine:
    def __init__(self, world):
        self.world = world
        self.eye_h = P_EYE_H
        self.eye_f = P_EYE_F
        self.pw    = P_W
        self.ph    = P_H

    def playeraabb(self, pos):
        hw = self.pw / 2
        return AABB(
            [pos[0] - hw, pos[1], pos[2] - hw],
            [pos[0] + hw, pos[1] + self.ph, pos[2] + hw]
        )





    def isblocksolid(self, x, y, z):
        return self.world.issolid(int(flr(x)), int(flr(y)), int(flr(z)))



    def collidingblocks(self, aabb, result=[]):
        result = []
        x0 = int(flr(aabb.min[0])); x1 = int(cl(aabb.max[0]))
        y0 = int(flr(aabb.min[1])); y1 = int(cl(aabb.max[1]))
        z0 = int(flr(aabb.min[2])); z1 = int(cl(aabb.max[2]))
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    if self.isblocksolid(x, y, z):
                        ba = AABB([x, y, z], [x+1, y+1, z+1])
                        if aabb.intersects(ba):
                            result.append((x, y, z, ba))

        return result






    # -- box tests

    def freeat(self, px, py, pz):
        hw       = self.pw / 2
        mnx, mxx = px - hw, px + hw
        mny, mxy = py,      py + self.ph
        mnz, mxz = pz - hw, pz + hw



        is_solid = self.world.issolid  # cache
        m  = 0.001
        sx = int(flr(mnx - m)); ex = int(cl(mxx + m))
        sy = int(flr(mny - m)); ey = int(cl(mxy + m))
        sz = int(flr(mnz - m)); ez = int(cl(mxz + m))
        #print(sx, ex, sy, ey, sz, ez)

        for x in range(sx, ex):
            for y in range(sy, ey):
                for z in range(sz, ez):
                    if is_solid(x, y, z):
                        if (mnx < x+1 and mxx > x and
                            mny < y+1 and mxy > y and
                            mnz < z+1 and mxz > z):
                            return False
                        
        return True
    




    def is_validpos(self, pos):
        return self.freeat(pos[0], pos[1], pos[2])

    def grounded(self, pos):
        tp = pos.copy(); tp[1] -= 0.02
        if not self.is_validpos(tp): return True
        tp[1] = pos[1] - 0.001
        return not self.is_validpos(tp)




    
    def fricat(self, pos):
        b = self.world.chunker.getblock(
            int(flr(pos[0])), int(flr(pos[1] - 0.02)), int(flr(pos[2]))
        )
        return FRIC.get(b, FRIC_TILE)

    

    def onladder(self, pos):
        x = int(flr(pos[0])); z = int(flr(pos[2]))
        gb = self.world.chunker.getblock
        for y in (int(flr(pos[1])), int(flr(pos[1] + 1.0))):
            if gb(x, y, z) in (LADDER, VINE): return True
        return False

    

    
    def ladderclamp(self, vel, sneak):
        vel[0] = max(-LADDER_CLAMP, min(LADDER_CLAMP, vel[0]))
        vel[2] = max(-LADDER_CLAMP, min(LADDER_CLAMP, vel[2]))
        if vel[1] < -LADDER_CLAMP: vel[1] = -LADDER_CLAMP
        if sneak and vel[1] < 0.0:    vel[1] = 0.0
        return vel



    def fluidat(self, pos, off=0.4):
        b = self.world.chunker.getblock(
            int(flr(pos[0])), int(flr(pos[1] + off)), int(flr(pos[2]))
        )
        if b in WATERY: return 1
        if b in LAVAY:  return 2
        return 0




    

    # stick vect -> world vel : norm past unitl
    def moverel(self, vel, xa, ya, yaw, acc):
        d = xa * xa + ya * ya
        if d < 1e-4: return vel

        d = math.sqrt(d)
        if d < 1.0: d = 1.0
        d = acc / d
        xa *= d
        ya *= d

        s = math.sin(math.radians(yaw))
        c = math.cos(math.radians(yaw))
        vel[0] += ya * c - xa * s
        vel[2] += ya * s + xa * c
        return vel
    


    def accel(self, vel, xa, ya, yaw, spd, on_ground, fric, sprint=False):
        if on_ground:
            ff = fric * FRIC_AIR
            a  = spd * (ACC_BASE / (ff * ff * ff))
        else:
            a  = AIR_ACC * (1.0 + AIR_SPRINT) if sprint else AIR_ACC

        return self.moverel(vel, xa, ya, yaw, a)

    


    # gravity + drag
    def drag(self, vel, on_ground, fric):
        vel[1] -= GRAV
        vel[1] *= DRAG_Y

        ff = fric * FRIC_AIR if on_ground else FRIC_AIR
        vel[0] *= ff
        vel[2] *= ff
        return vel

    


    def swimaccel(self, vel, xa, ya, yaw):
        return self.moverel(vel, xa, ya, yaw, WATER_ACC)

    def swimdrag(self, vel, lava):
        d = LAVA_DRAG if lava else WATER_DRAG
        vel[0] *= d
        vel[1] *= d
        vel[2] *= d
        vel[1] -= WATER_GRAV
        return vel




    def movey(self, fp, my):
        if my == 0.0: return False, False

        ty = fp[1] + my
        if self.freeat(fp[0], ty, fp[2]):
            fp[1] = ty
            return False, False

        precise = abs(my) > 0.6
        grnd    = my < 0
        ceil_   = my > 0



        if precise:
            lo, hi = (ty, fp[1]) if grnd else (fp[1], ty)
            for _ in range(6):
                mid = 0.5 * (lo + hi)
                if self.freeat(fp[0], mid, fp[2]):
                    if grnd: hi = mid
                    else:    lo = mid
                else:
                    if grnd: lo = mid
                    else:    hi = mid

            fp[1] = hi if grnd else lo


        elif grnd:
            sy    = float(flr(ty))
            found = False
            for _ in range(10):
                if self.freeat(fp[0], sy, fp[2]):
                    fp[1] = sy
                    found = True
                    break
                sy += 0.05
            if not found:
                fp[1] = float(cl(ty)) + 0.001

        else:
            fp[1] = float(flr(ty + self.ph)) - self.ph - 0.01




        
        if grnd:
            sy = float(flr(fp[1]))
            if sy != fp[1] and self.freeat(fp[0], sy, fp[2]): fp[1] = sy

        return grnd, ceil_


    def movex(self, fp, mx):
        if mx == 0.0: return False
        tx = fp[0] + mx
        if self.freeat(tx, fp[1], fp[2]):
            fp[0] = tx
            return False
        return True

    

    def movez(self, fp, mz):
        if mz == 0.0: return False
        tz = fp[2] + mz
        if self.freeat(fp[0], fp[1], tz):
            fp[2] = tz
            return False
        return True

    


    # y first
    # slabs stairs
    def movebox(self, pos, d, on_ground, sneak=False):
        fp = pos.copy()
        dx, dy, dz = float(d[0]), float(d[1]), float(d[2])

        #sneak edge guard
        if sneak and on_ground and dy <= 0.0:
            s = 0.05
            while dx != 0.0 and self.freeat(fp[0] + dx, fp[1] - 1.0, fp[2]):
                dx = 0.0 if abs(dx) < s else (dx - s if dx > 0 else dx + s)

            while dz != 0.0 and self.freeat(fp[0], fp[1] - 1.0, fp[2] + dz):
                dz = 0.0 if abs(dz) < s else (dz - s if dz > 0 else dz + s)

            while dx != 0.0 and dz != 0.0 and self.freeat(fp[0] + dx, fp[1] - 1.0, fp[2] + dz):
                dx = 0.0 if abs(dx) < s else (dx - s if dx > 0 else dx + s)
                dz = 0.0 if abs(dz) < s else (dz - s if dz > 0 else dz + s)




        grnd, ceil_ = self.movey(fp, dy)

        ox, oy, oz = fp[0], fp[1], fp[2]
        bx = self.movex(fp, dx)
        bz = self.movez(fp, dz)
        hc = bx or bz
        sl = 0.0

        if hc and (on_ground or grnd):
            ry = oy + STEP_H
            if self.freeat(ox, ry, oz):
                tp = np.array([ox, ry, oz], dtype='f4')
                b2x = self.movex(tp, dx)
                b2z = self.movez(tp, dz)

                got = (tp[0]-ox)**2 + (tp[2]-oz)**2
                had = (fp[0]-ox)**2 + (fp[2]-oz)**2
                if got > had:
                    self.movey(tp, -STEP_H)
                    sl = float(tp[1] - oy)
                    if sl < 0.0: sl = 0.0
                    fp = tp
                    hc = b2x or b2z
                    grnd = True

        return fp, hc, grnd, ceil_, sl





    
    def pushout(self, pos, vel):
        hw = self.pw * 0.35
        for cx, cz in ((-hw, hw), (-hw, -hw), (hw, -hw), (hw, hw)):
            x  = pos[0] + cx
            y  = pos[1] + 0.5
            z  = pos[2] + cz
            xt = int(flr(x)); yt = int(flr(y)); zt = int(flr(z))
            xd = x - xt
            zd = z - zt

            if not (self.isblocksolid(xt, yt, zt) or self.isblocksolid(xt, yt + 1, zt)):
                continue

            west  = not self.isblocksolid(xt-1, yt, zt) and not self.isblocksolid(xt-1, yt+1, zt)
            east  = not self.isblocksolid(xt+1, yt, zt) and not self.isblocksolid(xt+1, yt+1, zt)
            north = not self.isblocksolid(xt, yt, zt-1) and not self.isblocksolid(xt, yt+1, zt-1)
            south = not self.isblocksolid(xt, yt, zt+1) and not self.isblocksolid(xt, yt+1, zt+1)



            dir     = -1
            closest = 9999.0
            if west and xd < closest:
                closest = xd;      dir = 0
            if east and 1 - xd < closest:
                closest = 1 - xd;  dir = 1
            if north and zd < closest:
                closest = zd;      dir = 4
            if south and 1 - zd < closest:
                closest = 1 - zd;  dir = 5


            if dir == 0: vel[0] = -PUSHOUT
            if dir == 1: vel[0] = +PUSHOUT
            if dir == 4: vel[2] = -PUSHOUT
            if dir == 5: vel[2] = +PUSHOUT

        return vel


"""
def check_coll(self, pos, mv):
    #solve y -> solve x, z (axis separated)
    fp       = pos.copy()
    am       = np.array([0.0, 0.0, 0.0], dtype='f4')
    on_gnd   = False
    hit_ceil = False

    if mv[1] != 0:
        tp = fp.copy(); tp[1] += mv[1]
        if self.is_validpos(tp):
            fp[1] = tp[1]
            am[1] = mv[1]


        else:
            precise = abs(mv[1]) > 0.6
            if mv[1] < 0:
                on_gnd = True
                if precise:
                    lo, hi = tp[1], fp[1]
                    for _ in range(6):
                        mid = 0.5 * (lo + hi)
                        probe = fp.copy(); probe[1] = mid
                        if self.is_validpos(probe): hi = mid
                        else: lo = mid
                    fp[1] = hi
                else:
                
                    ty    = math.floor(fp[1])
                    found = False
                    for _ in range(10):
                        probe = fp.copy(); probe[1] = ty
                        if self.is_validpos(probe):
                            found = True; fp[1] = ty; break
                        ty += 0.05
                    if not found:
                        fp[1] = math.ceil(tp[1]) + 0.001
            else:
            
                hit_ceil = True
                if precise:
                    lo, hi = fp[1], tp[1]
                    for _ in range(6):
                        mid = 0.5 * (lo + hi)
                        probe = fp.copy(); probe[1] = mid
                        if self.is_validpos(probe): lo = mid
                        else: hi = mid
                    fp[1] = lo
                else:
                    fp[1] = math.floor(tp[1] + self.ph) - self.ph - 0.01



    if mv[0] != 0:
        tp = fp.copy(); tp[0] += mv[0]
        if self.is_validpos(tp): fp[0] = tp[0]; am[0] = mv[0]

    if mv[2] != 0:
        tp = fp.copy(); tp[2] += mv[2]
        if self.is_validpos(tp): fp[2] = tp[2]; am[2] = mv[2]

    return fp, am, on_gnd, hit_ceil


def apply_physics(self, pos, vel, on_ground, fly, dt):
    if fly: on_ground = False
    else:
        on_ground = self.grounded(pos)
        if on_ground:
            if vel[1] < 0: vel[1] = 0
        else:
            vel[1] += GRAVITY * dt
            if vel[1] < TERM_V: vel[1] = TERM_V
    return vel, on_ground


def apply_movinput(self, vel, move_dir, on_ground, fly, sprint, dt):
    if fly:
        tspd = FL_SPEED * (FL_SPEED_MP if sprint else 1.0)
        n    = np.linalg.norm(move_dir)
        if n > 0:
            d   = move_dir / n
            lf  = 10.0 * dt
            vel = vel * (1 - lf) + d * tspd * lf
        else:
            vel *= 0.8
    else:
        wspd = MAX_GSPEED * (MP_SPRINT if sprint else 1.0)
        n    = np.linalg.norm(move_dir)
        if n > 0:
            d      = move_dir / n
            vel[0] = d[0] * wspd
            vel[2] = d[2] * wspd
        else:
            vel[0] = 0
            vel[2] = 0
            if not on_ground:
                vel[0] *= 0.95
                vel[2] *= 0.95
    return vel


def apply_jump(self, vel, on_ground):
    if on_ground: vel[1] = JUMP_V
    return vel

"""





























