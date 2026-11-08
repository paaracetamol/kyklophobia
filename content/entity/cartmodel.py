import math
import numpy as np

from entity.model import mident, rotx, roty, rotz, trans



# (u, v, x0 y0 z0, dx dy dz, pivot xyz, rot xyz)
_H = math.pi / 2
PARTS = (
    (0,  10, (-10, -8, -1), (20, 16, 2), (0,  4,   0), (_H,  0,      0)),
    (0,  0,  (-8, -9,  -1), (16, 8,  2), (-9, 4,   0), (0,   3 * _H, 0)),
    (0,  0,  (-8, -9,  -1), (16, 8,  2), (9,  4,   0), (0,  _H,      0)),
    (0,  0,  (-8, -9,  -1), (16, 8,  2), (0,  4,  -7), (0,   2 * _H, 0)),
    (0,  0,  (-8, -9,  -1), (16, 8,  2), (0,  4,   7), (0,   0,      0)),
    (44, 10, (-9, -7,  -1), (18, 14, 1), (0,  4.1, 0), (-_H, 0,      0)),
)


def _gl_y(a): return roty(-a)






# model box
def _box(u, v, o, d):
    x0, y0, z0 = o
    x1, y1, z1 = x0 + d[0], y0 + d[1], z0 + d[2]
    dx, dy, dz = d
    uv = lambda a, b: (a / 64.0, (32.0 - b) / 32.0)
    # face corners + uv rect (a, b, c, d)
    return [
        (((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)), (1, 0, 0),  (u    + dz       + dx, v + dz, u + dz + dx + dz, v + dz + dy)),
        (((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)), (-1, 0, 0), (u, v + dz, u    + dz, v + dz    + dy)), #8==3
        (((x1, y0, z1), (x0, y0, z1), (x0, y0, z0), (x1, y0, z0)), (0, -1, 0), (u    + dz, v, u + dz    + dx, v + dz)),
        (((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)), (0, 1, 0),  (u    + dz       + dx, v + dz, u + dz    + dx + dx, v)),
        (((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)), (0, 0, -1), (u    + dz, v    + dz, u + dz    + dx, v + dz + dy)),
        (((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)), (0, 0, 1),  (u    + dz       + dx    + dz, v + dz, u + dz + dx + dz + dx, v + dz + dy)),
    ]







def cartmesh():

    vs, us, ns = [], [], []
    for u, v, o, d, pv, rt in PARTS:

        m = trans(
            pv[0] / 16.0, 
            pv[1] / 16.0, 
            pv[2] / 16.0
        ) @ rotz(rt[2]) @ _gl_y(rt[1]) @ rotx(rt[0])


        r = m[:3, :3]
        for cs, n, (a, b, c, e) in _box(u, v, o, d):
            
            q = [
                m @ np.array((
                    p[0] / 16.0, 
                    p[1] / 16.0, 
                    p[2] / 16.0, 1.0
                )) for p in cs
            ]


            t = [(a, b), (c, b), (c, e), (a, e)]
            nn = r @ np.array(n, dtype='f4')

            for i in (0, 1, 2, 0, 2, 3):
                vs.append(q[i][:3])
                us.append((t[i][0] / 64.0, (32.0 - t[i][1]) / 32.0))
                ns.append(nn)


    return np.array(vs, dtype='f4'), np.array(us, dtype='f4'), np.array(ns, dtype='f4'), np.zeros(len(vs), dtype='f4')










def cartmats(e, ck):
    from entity.minecart import railpos, railoff
    # server owned -> manager.update
    # local carts here only


    if e.eid > 0:
        x, y, z = float(e.pos[0]), float(e.pos[1]), float(e.pos[2])
    else:
        a = e.alpha
        x = float(e.opos[0] + (e.pos[0] - e.opos[0]) * a)
        y = float(e.opos[1] + (e.pos[1] - e.opos[1]) * a)
        z = float(e.opos[2] + (e.pos[2] - e.opos[2]) * a)



    yaw = float(e.yaw)
    pit = 0.0
    px, py, pz = x, y, z
    v = railpos(ck, x, y, z)


    if v is not None:
        v1 = railoff(ck, x, y, z, 0.3) or v
        v2 = railoff(ck, x, y, z, -0.3) or v

        px, pz = v[0], v[2]
        py = (v1[1] + v2[1]) / 2.0
        d = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
        l = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])


        if l != 0.0:
            d = (d[0] / l, d[1] / l, d[2] / l)
            yaw = math.degrees(math.atan2(d[2], d[0]))
            pit = math.degrees(math.atan(d[1])) * (73.0 / 57.29578)




    s = np.diag((-1.0, -1.0, 1.0, 1.0)).astype('f4')
    m = mident()

    m[0] = trans(0.0, 0.375, 0.0) @ _gl_y(math.radians(180.0 - yaw)) @ rotz(math.radians(-pit)) @ s


    return np.array((px, py, pz), dtype='f4'), m




























