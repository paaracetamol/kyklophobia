import shaders
import numpy as np
import moderngl
import math
from pyrr import Matrix44
from config import FOV, WIN_W, WIN_H
from entity.model import rotx, rotz, roty, trans





# gl style degrees, entity.model roty spins the other way
def _rx(d): return rotx(math.radians(d))
def _ry(d): return roty(math.radians(-d))
def _rz(d): return rotz(math.radians(d))

def _sf(d): return np.diag((d, d, d, 1.0)).astype('f4')

PI = math.pi

# model space right arm -> shoulder @ origin, hand towards +y
_ARMFIX  = trans(0.0, 1.5, 0.0) @ _rx(180.0)
PART_ARM = 3  # r_* = left arm, l_* = right

# mc model json firstperson_righthand
_BLOCKFP = _ry(45.0) @ _sf(0.4)
_ITEMFP  = trans(1.13/16.0, 3.2/16.0, 1.13/16.0) @ _ry(90.0) @ _rz(25.0) @ _sf(0.68)




class HeldItemRenderer:
    ARM_H   = 0.75
    B_SCALE = 0.3
    I_SCALE = 0.7

    def __init__(self, ctx, iem):
        self.ctx = ctx
        self.iem = iem

        self.prog = ctx.program(
            vertex_shader=shaders.load("held.vert"),
            fragment_shader=shaders.load("held.frag"),
        )

        # cube VAO -> own UV buffer, shared vert/norm buffers
        self.cuvbuf = ctx.buffer(reserve=self.iem.uv_buf.size)
        self.cvao   = ctx.vertex_array(self.prog, [
            (self.iem.vbo,      '3f', 'in_pos'),
            (self.cuvbuf,            '2f', 'in_uv'),
            (self.iem.norm_vbo, '3f', 'in_norm'),
        ])

        # sprite VAOs -> created on demand
        self.svaos = {}

        # never follows sprint fov, same as mc
        self.fpproj = np.array(Matrix44.perspective_projection(FOV, WIN_W / WIN_H, 0.05, 20.0), dtype='f4')
        # squeeze into the front 10% of depth so the world never overlaps the hand
        self.fpproj[:, 2] = self.fpproj[:, 2] * 0.1 - self.fpproj[:, 3] * 0.9
        
        
        

    def spritevao(self, itemId):
        if itemId in self.svaos:
            return self.svaos[itemId]

        sprite = self.iem.spritevao(itemId)
        if not sprite:
            self.svaos[itemId] = None
            return None

        vao = self.ctx.vertex_array(self.prog, [
            (sprite['vbo'],      '3f', 'in_pos'),
            (sprite['uv_vbo'],   '2f', 'in_uv'),
            (sprite['norm_vbo'], '3f', 'in_norm'),
        ])
        
        self.svaos[itemId] = vao
        return vao
        
        
        
        

    def render(self, mvp, p, sun_dir=None):
        slot = p._slot
        if slot < 0 or slot >= 9: return

        stack = p.inv.slots[slot]
        if stack is None: return

        idef   = stack.item
        itemId = idef.itemId

        # l_* = right arm 3
        ps = p.pose

        prog = self.prog
        prog['fp'].value   = 0
        prog['lite'].value = (1.0, 1.0, 1.0)
        prog['mvp'].write(mvp.astype('f4').tobytes())
        prog['player_pos'].write(p.getpos().astype('f4').tobytes())
        prog['byaw'].value = ps.byaw
        prog['arm_angle'].value   = ps.l_arm
        prog['arm_z_angle'].value = ps.l_arm_z
        prog['arm_y_angle'].value = ps.l_arm_y
        prog['body_y'].value      = ps.body_y
        prog['crouch'].value = p._smthcrouch

        if sun_dir is not None:
            prog['sun_dir'].write(sun_dir.astype('f4').tobytes())

        tint   = self.iem.TINT_MAP.get(itemId, (1.0, 1.0, 1.0))
        tmode  = self.iem.TINT_MODE_MAP.get(itemId, self.iem.TINT_MODE_ALL)
        prog['tint'].write(np.array(tint, dtype='f4').tobytes())
        prog['tint_mode'].value = tmode

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        
        

        if idef.is_block and not self.iem.flat(itemId):
            prog['scale'].value = self.B_SCALE
            prog['item_yaw'].value   = math.radians(-45.0)  # ~45° tilt
            prog['item_pitch'].value = 0.0
            prog['item_roll'].value  = 0.0
            prog['hand_offset'].write(np.array([0.0, -self.ARM_H + 0.05, 0.12], dtype='f4').tobytes())
            self.iem.texture.use(0)
            prog['texture0'].value = 0
            uvs = self.iem.blockuvs(itemId)
            self.cuvbuf.write(uvs.tobytes())
            self.cvao.render(moderngl.TRIANGLES)
            
        else:
            prog['scale'].value = self.I_SCALE
            prog['item_yaw'].value   = math.radians(90.0)   # edge forward
            prog['item_pitch'].value = 0.0
            prog['item_roll'].value  = math.radians(-45.0)
            prog['hand_offset'].write(np.array([0.0, -self.ARM_H + 0.1, 0.28], dtype='f4').tobytes())
            vao = self.spritevao(itemId)
            
            if vao:
                self.iem.spritetex(itemId).use(0)
                prog['texture0'].value = 0
                vao.render(moderngl.TRIANGLES)
                
                

        self.ctx.disable(moderngl.BLEND)
        
        
        
        
        
        

    def remoterender(self, mvp, pos, yaw, pitch, itemId, arm_angle, sun_dir=None, crouch=0.0,
                     arm_z=0.0, arm_y=0.0, body_y=0.0):
        from items.registry import REGISTRY
        if not REGISTRY.exists(itemId):
            return

        idef = REGISTRY.get(itemId)

        prog = self.prog
        prog['fp'].value   = 0
        prog['lite'].value = (1.0, 1.0, 1.0)
        prog['mvp'].write(mvp.astype('f4').tobytes())
        prog['player_pos'].write(pos.astype('f4').tobytes())
        prog['byaw'].value = yaw
        prog['arm_angle'].value   = arm_angle
        prog['arm_z_angle'].value = arm_z
        prog['arm_y_angle'].value = arm_y
        prog['body_y'].value      = body_y
        prog['crouch'].value = crouch

        if sun_dir is not None:
            prog['sun_dir'].write(sun_dir.astype('f4').tobytes())

        tint  = self.iem.TINT_MAP.get(itemId, (1.0, 1.0, 1.0))
        tmode = self.iem.TINT_MODE_MAP.get(itemId, self.iem.TINT_MODE_ALL)
        prog['tint'].write(np.array(tint, dtype='f4').tobytes())
        prog['tint_mode'].value = tmode
        

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        

        if idef.is_block and not self.iem.flat(itemId):
            prog['scale'].value      = self.B_SCALE
            prog['item_yaw'].value   = math.radians(-45.0)
            prog['item_pitch'].value = 0.0
            prog['item_roll'].value  = 0.0
            prog['hand_offset'].write(np.array([0.0, -self.ARM_H + 0.05, 0.12], dtype='f4').tobytes())
            self.iem.texture.use(0)
            prog['texture0'].value = 0
            uvs = self.iem.blockuvs(itemId)
            self.cuvbuf.write(uvs.tobytes())
            self.cvao.render(moderngl.TRIANGLES)
            
        else:
            prog['scale'].value      = self.I_SCALE
            prog['item_yaw'].value   = math.radians(90.0)
            prog['item_pitch'].value = 0.0
            prog['item_roll'].value  = math.radians(-45.0)
            prog['hand_offset'].write(np.array([0.0, -self.ARM_H + 0.1, 0.28], dtype='f4').tobytes())
            vao = self.spritevao(itemId)
            
            if vao:
                self.iem.spritetex(itemId).use(0)
                prog['texture0'].value = 0
                vao.render(moderngl.TRIANGLES)

        self.ctx.disable(moderngl.BLEND)
        
        

    # bob + delayed look sway, shared by arm & item
    def fproot(self, p):
        a = p.alpha
        t = p.bob_time
        f = p.bob_amp * 2.0
        ap = p.oarmp + (p.armp - p.oarmp) * a
        ay = p.oarmy + (p.army - p.oarmy) * a
        return (
            trans(math.sin(t) * f * 0.5, -abs(math.cos(t) * f), 0.0)
            @ _rz(math.sin(t) * f * 3.0)
            @ _rx(abs(math.cos(t - 0.2) * f) * 5.0)
            @ _rx((ap - p.cam.pitch) * 0.1)
            @ _ry((p.cam.yaw - ay) * 0.1)
        )



    def fparm(self, sw, eq):
        rs = math.sqrt(sw)
        return (
            trans(
                -0.3 * math.sin(rs * PI) + 0.64,
                0.4 * math.sin(rs * PI * 2.0) - 0.6 - eq * 0.6,
                -0.4 * math.sin(sw * PI) - 0.72
            )
            @ _ry(45.0)
            @ _ry(math.sin(rs * PI) * 70.0)
            @ _rz(math.sin(sw * sw * PI) * -20.0)
            @ trans(-1.0, 3.6, 3.5)
            @ _rz(120.0) @ _rx(200.0) @ _ry(-135.0)
            @ trans(5.6, 0.0, 0.0)
            @ _ARMFIX
        )



    def fpitem(self, sw, eq):
        rs = math.sin(math.sqrt(sw) * PI)
        return (
            trans(
                -0.4 * rs + 0.56,
                0.2 * math.sin(math.sqrt(sw) * PI * 2.0) - 0.52 - eq * 0.6,
                -0.2 * math.sin(sw * PI) - 0.72
            )
            @ _ry(45.0 + math.sin(sw * sw * PI) * -20.0)
            @ _rz(rs * -20.0)
            @ _rx(rs * -80.0)
            @ _ry(-45.0)
        )



    def renderfp(self, pm, p, sun_dir, lite):
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # normals live in view space here, sun has to follow
        fr = p.cam.front
        rt = np.cross(fr, (0.0, 1.0, 0.0))
        rt = rt / np.linalg.norm(rt)
        sv = np.array((np.dot(sun_dir, rt), np.dot(sun_dir, np.cross(rt, fr)), -np.dot(sun_dir, fr)), dtype='f4')

        sw   = p.pose.swing
        eq   = 1.0 - (p.oeq + (p.eq - p.oeq) * p.alpha)
        root = self.fproot(p)
        idef = p.eqit

        if idef is None:
            mats = np.zeros((12, 4, 4), dtype='f4')  # zeroed parts collapse, only the arm draws
            mats[PART_ARM] = root @ self.fparm(sw, eq)
            pm.model.render(self.fpproj, np.zeros(3), 90.0, mats, sun_pos=sv, lite=lite)
            self.ctx.disable(moderngl.BLEND)
            return

        itemId = idef.itemId
        prog   = self.prog
        tint   = self.iem.TINT_MAP.get(itemId, (1.0, 1.0, 1.0))
        tmode  = self.iem.TINT_MODE_MAP.get(itemId, self.iem.TINT_MODE_ALL)
        m      = root @ self.fpitem(sw, eq) @ (_BLOCKFP if idef.is_block and not self.iem.flat(itemId) else _ITEMFP)

        prog['fp'].value = 1
        prog['fpmat'].write(np.ascontiguousarray(m.T, dtype='f4').tobytes())
        prog['mvp'].write(self.fpproj.astype('f4').tobytes())
        prog['sun_dir'].write(sv.tobytes())
        prog['lite'].value = lite
        prog['tint'].write(np.array(tint, dtype='f4').tobytes())
        prog['tint_mode'].value = tmode
        prog['texture0'].value  = 0

        if idef.is_block and not self.iem.flat(itemId):
            self.iem.texture.use(0)
            self.cuvbuf.write(self.iem.blockuvs(itemId).tobytes())
            self.cvao.render(moderngl.TRIANGLES)
        else:
            vao = self.spritevao(itemId)
            if vao:
                self.iem.spritetex(itemId).use(0)
                vao.render(moderngl.TRIANGLES)

        self.ctx.disable(moderngl.BLEND)



    def release(self):
        for vao in self.svaos.values():
            if vao: vao.release()
        self.cvao.release()
        self.cuvbuf.release()
        self.prog.release()
        



















