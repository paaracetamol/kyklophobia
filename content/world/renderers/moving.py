import math
import numpy as np
import moderngl
from world.chunk import Chunk
from world.blocks import PISTON_HEAD, STICKY_PISTON


MAXV = 65536
_PC  = (8, 64, 8)






class MovingRenderer:
    def __init__(self, ctx, prog, world):
        self.ctx   = ctx
        self.world = world
        self.cache = {}

        self.chunk = Chunk(99990, 99990, world)
        self.chunk.light[:]  = 15
        self.chunk.blight[:] = 15
        self.chunk.gen_ready = True

        self.vbo = ctx.buffer(reserve=MAXV * 32, dynamic=True)
        self.vao = ctx.vertex_array(
            prog, [(self.vbo, '3f 3f 2f', 'in_pos', 'in_lit', 'in_uv')]
        )





    def model(self, v):
        v = v & 0x7FFF
        if v in self.cache: return self.cache[v]

        c = self.chunk
        c.voxels[:] = 0
        c.voxels[_PC] = v

        a, t = c.build_mesh()


        m = np.concatenate((a, t)).reshape(-1, 8).copy()
        m[:, 0] -= c.offset_x + _PC[0]
        m[:, 1] -= _PC[1]
        m[:, 2] -= c.offset_z + _PC[2]

        self.cache[v] = m
        return m




    def place(self, out, v, x, y, z, l):
        m = self.model(v).copy()
        m[:, 0] += x
        m[:, 1] += y
        m[:, 2] += z
        m[:, 3] = l[0]
        m[:, 4] = l[1]
        
        out.append(m)





    def render(self, rs, alpha):
        if not rs.moving: return
        out = []

        cm  = self.world.chunker

        for m in list(rs.moving.values()):
            p = m.at(alpha)
            if p >= 1.0: continue

            s = m.shift(p)


            from world.redstone import DIRS
            o = DIRS[m.f]
            x, y, z = m.x + s * o[0], m.y + s * o[1], m.z + s * o[2]
            l = cm.getlight(m.x, m.y, m.z)



            if m.v & 0x3FF == PISTON_HEAD and p <= 0.25:
                self.place(out, m.v | (16 << 10), x, y, z, l)


            elif m.src and not m.ext:
                st = m.f | (8 if m.v & 0x3FF == STICKY_PISTON else 0)
                if p >= 0.5: st |= 16

                self.place(out, PISTON_HEAD | (st << 10), x, y, z, l)
                self.place(out, (m.v & 0x3FF) | ((m.f | 8) << 10), m.x, m.y, m.z, l)


            else:
                self.place(out, m.v, x, y, z, l)



        if not out: return
        d = np.concatenate(out)
        n = min(len(d), MAXV)

        self.vbo.write(d[:n].astype('f4').tobytes())
        self.vao.render(moderngl.TRIANGLES, vertices=n)








    
    def rendercarts(self, ents):
        from entity.cartmodel import cartmats, _gl_y
        from entity.model import trans


        out = []
        cm  = self.world.chunker

        for e in ents:
            if not getattr(e, 'showblk', 0): continue
            p, m = cartmats(e, cm)

            

            sw, fl = 1.0, 0.0
            fu = getattr(e, 'fuse', -1)

            if fu > -1:
                a = e.alpha
                ft = fu - a + 1.0

                if ft < 10.0:
                    f  = max(0.0, min(1.0, 1.0 - ft / 10.0))
                    sw = 1.0 + (f ** 4) * 0.3

                if fu // 5 % 2 == 0: fl = (1.0 - ft / 100.0) * 0.8



            s = np.diag((0.75 * sw, 0.75 * sw, 0.75 * sw, 1.0)).astype('f4')
            k = m[0] @ np.diag((-1.0, -1.0, 1.0, 1.0)).astype('f4') @ s @ trans(-0.5, (e.showoff - 8) / 16.0, 0.5) @ _gl_y(math.pi / 2)

            v = self.model(e.showblk).copy()
            h = np.c_[v[:, :3], np.ones(len(v))] @ k.T

            v[:, :3] = h[:, :3] + p
            l = cm.getlight(int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(p[2])))
            v[:, 3] = l[0];  v[:, 4] = l[1]


            if fl > 0.0: v[:, 5] = -fl
            out.append(v)


        if not out: return

        d = np.concatenate(out)
        n = min(len(d), MAXV)

        self.vbo.write(d[:n].astype('f4').tobytes())
        self.vao.render(moderngl.TRIANGLES, vertices=n)




    def release(self):
        self.vao.release()
        self.vbo.release()





































