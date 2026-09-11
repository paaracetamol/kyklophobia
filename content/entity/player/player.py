import numpy as np
import pygame
from pygame.locals import *
import math

from engine.camera import Camera
from engine.physics import PhysicsEngine
from entity.biped import Biped
from config import (
    BREAK_T, RAYCAST_DIST, HURT_T, KNOCK_T,
    TICK, TICK_CATCHUP,
    WALK_SPD, SPRINT_MUL, SNEAK_MUL, JUMP_YD, SPRINT_JUMP,
    SNEAK_EYE, LADDER_CLIMB,
    FLY_YD, FLY_SPD, FLY_SPRINT, FLY_FRIC, FLY_DRAG_Y,
    WATER_JUMP, LEDGE_YD,
    SPRINT_TRIG, FOOD_SPRINT, JUMP_TRIG, NOJUMP_DELAY
)
RUN_TRESH = 0.8      # forward stick past this counts as a run


class Player:
    def __init__(self, world, pos=None):
        self.world   = world
        self.physics = PhysicsEngine(world)

        if pos is None:
            pos = np.array([0.0, 80.0, 0.0], dtype='f4')
        else:
            pos = np.array(pos, dtype='f4')

        self.pos = pos.copy()
        self.vel = np.array([0.0, 0.0, 0.0], dtype='f4')   # per tick, blocks
        self.knockt = 0.0

        # tick pos -> render pos
        self.opos  = self.pos.copy()
        self.rpos  = self.pos.copy()
        self.accum = 0.0
        self.alpha = 0.0

        self.on_ground = False
        self.gmode  = 1
        self.fly    = True
        self.sprint = False
        self.crouching = False
        self._smthcrouch  = 0.0
        self.world_ready  = False

        # input
        self.xa       = 0.0
        self.ya       = 0.0
        self.jumping  = False
        self.sneaking = False
        self.sinkkey  = False
        self.shift    = False

        self.hcoll    = False
        self.yslide   = 0.0
        self.sprtrig  = 0
        self.jumptrig = 0
        self.nojumpd  = 0
        self.wasjump  = False
        self.oya      = 0.0
        self.inwtr    = 0

        self.fov  = 1.0
        self.ofov = 1.0

        self.cmode = 0

        ep    = self.pos.copy()
        ep[1] += self.physics.eye_h
        self.cam = Camera(pos=ep)
        self.eye = ep.copy()

        self.freecam = False
        self.fcmove  = True
        self.fcstick = False
        self.fcam    = None

        self.on_jump    = False
        self.on_toggleflight = False
        self.bob_time   = 0.0
        self.bob_amp    = 0.0
        self.limb_swing = 0.0

        self.ui       = None
        self.last_pos = self.pos.copy()

        self.mtgt = None
        self.mprog = 0.0
        self.swseq = 0
        self.falld = 0.0
        self.hurtt = 0.0

        self.anim_time    = 0.0
        self.is_breaking  = False
        self.is_placing   = False
        self.break_time   = 0.0
        self.break_duration = BREAK_T

        bids     = [1, 2, 3, 12, 6, 7, 8, 14, 11]
        self.inv = [{'id': bid, 'count': 64} for bid in bids]
        self._slot = 0

        self.health     = 20
        self.max_health = 20
        self.hunger     = 20
        self.max_hunger = 20
        self.armor      = 20
        self.max_armor  = 20
        self.air        = 300
        self.max_air    = 300
        self._underwater = True

        self.anim       = Biped(self.cam.yaw)
        self.pose       = self.anim.pose(0.0, 0.0)
        self.byaw       = self.cam.yaw
        self.headyawoff = 0.0

        self._smooth_r_arm = 0.0
        self._smooth_l_arm = 0.0
        self._smooth_r_leg = 0.0
        self._smooth_l_leg = 0.0
        self._last_dt      = 0.0

        self.orbital_distance = 6.0
        self.orb_yaw      = 0.0
        self.orb_pitch    = 30.0

    def inwater(self):
        return self.inwtr == 1

    # ceil(dist - 3)
    def onfall(self):
        if self.fly or self.gmode or self.inwtr:
            self.falld = 0.0
            return

        
        dy = float(self.opos[1] - self.pos[1])
        if dy > 0: self.falld += dy

        if self.on_ground and self.falld > 0:
            dmg = math.ceil(self.falld - 3.0)
            if dmg > 0: self.hurt(dmg)
            self.falld = 0.0

    def sethealth(self, hp):
        self.health = max(0, min(self.max_health, int(hp)))
        return True

    def sethunger(self, hg):
        self.hunger = max(0, min(self.max_hunger, int(hg)))
        return True

    
    def knock(self, v):
        self.vel[0] += v[0] * TICK
        self.vel[1]  = max(float(self.vel[1]), v[1] * TICK)
        self.vel[2] += v[2] * TICK
        self.knockt  = KNOCK_T
        self.on_ground = False


    def hurt(self, dmg):
        if dmg <= 0: return
        self.health = max(0, self.health - dmg)
        self.hurtt  = HURT_T
        self.world.onhurt(dmg)

    def swing(self, placing=False):
        if placing: self.is_placing  = True
        else:       self.is_breaking = True
        self.break_time = 0.0
        self.swseq      = (self.swseq + 1) & 3
        self.anim.swingarm()

    def setgmode(self, m):
        self.gmode = m
        if m == 0:
            self.fly    = False
            self.vel[1] = 0
            self.mtgt   = None
            self.mprog  = 0.0

    def togglegmode(self):
        self.setgmode(0 if self.gmode else 1)
        return self.gmode

    def toggleflight(self):
        if not self.gmode: return

        self.fly = not self.fly
        if self.fly:
            self.vel[1] = 0
            self.ui.chatmsg("Flight: ON", color=(200, 255, 200))
        else:
            self.ui.chatmsg("Flight: OFF", color=(200, 255, 200))

    def togglecam(self):
        self.cmode = (self.cmode + 1) % 4
        if self.cmode == 3:
            self.orb_yaw   = self.cam.yaw
            self.orb_pitch = 30.0

    def togglefreecam(self):
        self.freecam = not self.freecam
        if self.freecam:
            self.fcam = Camera(pos=self.cam.pos.copy())
            self.fcam.yaw = self.fcam.target_yaw = self.cam.yaw
            self.fcam.pitch = self.fcam.target_pitch = self.cam.pitch
            self.fcam.updatevecs()
            self.fcmove = True
            self.fcstick = False

    def togglefcctrl(self):
        self.fcmove = not self.fcmove

    def togglefcstick(self):
        self.fcstick = not self.fcstick

    def rcam(self):
        return self.fcam if self.freecam else self.cam

    
    def clearinput(self):
        self.xa      = 0.0
        self.ya      = 0.0
        self.jumping = False
        self.shift   = False
        self.sinkkey = False


    
    def oninput(self, dt):
        if self.freecam and self.fcmove:
            self.fcam.oninput(dt)
            return

        keys = pygame.key.get_pressed()

        if keys[K_f]:
            if not self.on_toggleflight:
                self.toggleflight()
                self.on_toggleflight = True
        else:
            self.on_toggleflight = False

        
        self.sneaking  = keys[K_LCTRL] and not self.fly
        self.crouching = self.sneaking
        self.sinkkey   = keys[K_LCTRL]
        self.shift     = keys[K_LSHIFT]

        xa = 0.0
        ya = 0.0
        if keys[K_w]: ya += 1.0
        if keys[K_s]: ya -= 1.0
        if keys[K_d]: xa += 1.0
        if keys[K_a]: xa -= 1.0

        if self.sneaking:
            xa *= SNEAK_MUL
            ya *= SNEAK_MUL

        self.xa      = xa
        self.ya      = ya
        self.jumping = keys[K_SPACE]
        # print(xa, ya, self.jumping)



    
    def fovmod(self):
        t = 1.0
        if self.fly: t *= 1.1
        return t * ((SPRINT_MUL if self.sprint else 1.0) + 1.0) / 2.0


    def canfly(self):
        return bool(self.gmode)

    def cansprint(self):
        if self.canfly(): return True
        return self.hunger > FOOD_SPRINT







    
    def tick(self):
        ph = self.physics
        self.opos = self.pos.copy()

        if self.sprtrig > 0: self.sprtrig -= 1
        if self.nojumpd > 0: self.nojumpd -= 1

        xa = self.xa
        ya = self.ya

        wasjump = self.wasjump
        wasrun  = self.oya >= RUN_TRESH
        self.wasjump = self.jumping
        self.oya     = ya

        
        if (
            self.on_ground and not self.sneaking and not wasrun
            and ya >= RUN_TRESH and not self.sprint and self.cansprint()
        ):
            if self.sprtrig <= 0 and not self.shift: self.sprtrig = SPRINT_TRIG
            else: self.setsprint(True)



        if not self.sprint and ya >= RUN_TRESH and self.cansprint() and self.shift:
            self.setsprint(True)

        if self.sprint and (ya < RUN_TRESH or self.hcoll or not self.cansprint()):
            self.setsprint(False)



        
        if self.canfly():
            if not wasjump and self.jumping:
                if self.jumptrig == 0:
                    self.jumptrig = JUMP_TRIG
                else:
                    self.fly      = not self.fly
                    self.jumptrig = 0
        elif self.fly:
            self.fly = False


        if self.jumptrig > 0: self.jumptrig -= 1

        self.inwtr = ph.fluidat(self.pos)
        fric       = ph.fricat(self.pos)
        wasgrnd    = self.on_ground

        if self.knockt > 0.0: xa = ya = 0.0





        if self.fly:
            
            if self.sinkkey:
                if self.sneaking:
                    xa /= SNEAK_MUL
                    ya /= SNEAK_MUL
                self.vel[1] -= FLY_YD
            if self.jumping: self.vel[1] += FLY_YD

            d0  = float(self.vel[1])
            spd = FLY_SPD * (FLY_SPRINT if self.sprint else 1.0)

            self.vel = ph.moverel(self.vel, xa, ya, self.cam.yaw, spd)
            self.noclip()

            self.vel[0] *= FLY_FRIC
            self.vel[2] *= FLY_FRIC
            self.vel[1]  = d0 * FLY_DRAG_Y

            self.falld     = 0.0
            self.on_ground = False

        elif self.inwtr:
            if self.jumping: self.vel[1] += WATER_JUMP

            self.vel = ph.swimaccel(self.vel, xa, ya, self.cam.yaw)
            self.domove()
            self.vel = ph.swimdrag(self.vel, self.inwtr == 2)

            
            if self.hcoll and ph.freeat(
                self.pos[0] + self.vel[0], 
                self.pos[1] + LEDGE_YD, 
                self.pos[2] + self.vel[2]
            ):
                self.vel[1] = LEDGE_YD

        else:
            if self.jumping and self.on_ground and self.nojumpd == 0:
                self.jump()

            spd      = WALK_SPD * (SPRINT_MUL if self.sprint else 1.0)
            self.vel = ph.accel(
                self.vel, xa, ya, 
                self.cam.yaw, spd, 
                self.on_ground, fric, 
                self.sprint
            )


            ladder = ph.onladder(self.pos)
            if ladder:
                self.vel   = ph.ladderclamp(self.vel, self.sneaking)
                self.falld = 0.0

            self.domove()

            #ladder
            if ladder and self.hcoll: self.vel[1] = LADDER_CLIMB

            self.vel = ph.drag(self.vel, wasgrnd, fric)

        
        if not self.fly: self.vel = ph.pushout(self.pos, self.vel)

        
        self.yslide = SNEAK_EYE if self.sneaking else 0.0

        self.anim.tick(
            self.pos[0], self.pos[2],
            self.opos[0], self.opos[2],
            self.cam.yaw, self.on_ground
        )

        self.onfall()

        


        self.ofov = self.fov
        self.fov += (self.fovmod() - self.fov) * 0.5






    def jump(self):
        self.vel[1] = JUMP_YD
        if self.sprint:
            yr = math.radians(self.cam.yaw)
            self.vel[0] += math.cos(yr) * SPRINT_JUMP
            self.vel[2] += math.sin(yr) * SPRINT_JUMP
        self.nojumpd = NOJUMP_DELAY
        


    def setsprint(self, on):
        self.sprint = on


    
    def noclip(self):
        self.pos       = self.pos + self.vel
        self.hcoll     = False
        self.on_ground = False


    def domove(self):
        ph = self.physics
        fp, hc, grnd, ceil_, sl = ph.movebox(
            self.pos, self.vel, self.on_ground, self.sneaking
        )
        self.pos   = fp
        self.hcoll = hc
        # print(fp, hc, grnd, sl)

        # if sl > 0.0: self.yslide += sl   # lce ySlideOffset, smooths the step pop

        if hc:
            if not ph.freeat(self.pos[0] + self.vel[0], self.pos[1], self.pos[2]): self.vel[0] = 0.0
            if not ph.freeat(self.pos[0], self.pos[1], self.pos[2] + self.vel[2]): self.vel[2] = 0.0

        if ceil_ and self.vel[1] > 0: self.vel[1] = 0.0

        self.on_ground = grnd or ph.grounded(self.pos)
        if self.on_ground and self.vel[1] < 0: self.vel[1] = 0.0


    # h speed
    def gspeed(self):
        return math.sqrt(self.vel[0]**2 + self.vel[2]**2) / TICK


    def update(self, dt):
        self._last_dt  = dt
        _grnd_prev     = self.on_ground
        # t0 = time.perf_counter()

        if not self.world_ready:
            if len(self.world.chunker.chunks) > 0:
                self.world_ready = True

        if not self.world_ready:
            ep    = self.pos.copy()
            ep[1] += self.physics.eye_h
            yr    = math.radians(self.cam.yaw)
            ep[0] += math.cos(yr) * self.physics.eye_f
            ep[2] += math.sin(yr) * self.physics.eye_f
            self.cam.pos = ep
            self.eye = ep.copy()
            return
            
            

        self.last_pos = self.pos.copy()

        self.accum += dt
        n = 0
        while self.accum >= TICK and n < TICK_CATCHUP:
            self.accum -= TICK
            n          += 1
            self.tick()

        if n >= TICK_CATCHUP: self.accum = 0.0

        self.alpha = self.accum / TICK
        self.rpos  = self.opos + (self.pos - self.opos) * self.alpha

        self.cam.fovmul = self.ofov + (self.fov - self.ofov) * self.alpha

        ep    = self.rpos.copy()
        ep[1] += self.physics.eye_h - self.yslide
        yr    = math.radians(self.cam.yaw)
        ep[0] += math.cos(yr) * self.physics.eye_f
        ep[2] += math.sin(yr) * self.physics.eye_f
        self.eye = ep.copy()

        speed = self.gspeed()
        ta    = 0.05 if self.on_ground and speed > 0.1 and self.cmode == 0 else 0.0

        if self.on_ground and speed > 0.1 and self.cmode == 0:
            self.bob_time += speed * dt * 1.5

        self.pose       = self.anim.pose(self.alpha, self.cam.pitch, self.crouching)
        self.byaw       = self.pose.byaw
        self.headyawoff = self.pose.headyaw

        self.bob_amp += (ta - self.bob_amp) * 10.0 * dt
        
        
        

        if self.cmode == 0 and self.bob_amp > 0.001:
            bob_x = math.sin(self.bob_time) * self.bob_amp
            bob_y = math.sin(self.bob_time * 2.0) * self.bob_amp
            ceil_y = self.rpos[1] + self.physics.ph + 0.1
            if self.physics.isblocksolid(self.rpos[0], ceil_y, self.rpos[2]):
                if bob_y > 0: bob_y *= 0.2
            ep[0] += math.cos(yr) * bob_x
            ep[2] += math.sin(yr) * bob_x
            ep[1] += bob_y

        if self.cmode == 0:
            self.cam.pos = ep
            
            
        elif self.cmode in (1, 2):
            # pull back from wall
            td  = 4.0
            dir = -self.cam.front if self.cmode == 1 else self.cam.front
            ad  = td
            for d in np.arange(0, td, 0.1):
                chk = ep + dir * d
                if self.physics.isblocksolid(int(chk[0]), int(chk[1]), int(chk[2])):
                    ad = max(0.2, d - 0.2);  break
                    
            self.cam.pos = ep + dir * ad
            
            
            
            
            
        elif self.cmode == 3:
            oyr = math.radians(self.orb_yaw)
            opr = math.radians(self.orb_pitch)
            cp  = math.cos(opr)
            corb = np.array([
                -math.cos(oyr) * cp * self.orbital_distance,
                 math.sin(opr) * self.orbital_distance,
                -math.sin(oyr) * cp * self.orbital_distance
            ], dtype='f4')
            
            
            ad   = self.orbital_distance
            cdir = corb / np.linalg.norm(corb)
            
            for d in np.arange(0, self.orbital_distance, 0.1):
                chk = ep + cdir * d
                if self.physics.isblocksolid(int(chk[0]), int(chk[1]), int(chk[2])):
                    ad = max(1.0, d - 0.5);  break
                    
                    
                    
            self.cam.pos = ep + cdir * ad
            ld   = ep - self.cam.pos
            ldst = np.linalg.norm(ld)
            
            if ldst > 0.001:
                ld /= ldst
                self.cam.front = ld
                self.cam.pitch = math.degrees(math.asin(np.clip(ld[1], -1, 1)))
                self.cam.yaw   = math.degrees(math.atan2(ld[2], ld[0]))
                
                

        # drag freecam
        if self.freecam and self.fcstick:
            self.fcam.pos += self.pos - self.last_pos

        self.anim_time += dt
        if self.hurtt  > 0: self.hurtt  -= dt
        if self.knockt > 0: self.knockt -= dt

        self._smthcrouch = 1.0 if self.crouching else 0.0

        if self.is_breaking or self.is_placing:
            self.break_time += dt
            if self.break_time >= self.break_duration:
                self.is_breaking = False
                self.is_placing  = False
                self.break_time  = 0.0

    
    def animangles(self):
        p = self.pose
        return (p.r_arm, p.l_arm, p.r_leg, p.l_leg, p.r_arm_z, p.l_arm_z)

        """
        def animangles(self):
            speed = self.gspeed()
            lsa   = min(speed / 4.3, 1.0) if speed > 0.1 else 0.0
            phase = self.limb_swing * 0.6662
            RAD2DEG = 180.0 / math.pi
            r_arm = math.cos(phase + math.pi) * 2.0 * lsa * 0.5 * RAD2DEG
            l_arm = math.cos(phase)            * 2.0 * lsa * 0.5 * RAD2DEG
            r_leg = math.cos(phase)            * 1.4 * lsa         * RAD2DEG
            return (r_arm, l_arm, r_leg, r_leg, 0.0, 0.0)
        """




    def onmouse(self):
        if self.freecam and self.fcmove:
            self.fcam.onmouse()
            return
        if self.cmode == 3:
            from config import SENSIVITY
            dx, dy = pygame.mouse.get_rel()
            self.orb_yaw   += dx * SENSIVITY
            self.orb_pitch += dy * SENSIVITY
            self.orb_pitch = max(-89.0, min(89.0, self.orb_pitch))
        else:
            self.cam.onmouse()
            
            
            

    def onscroll(self, y):
        if self.cmode == 3:
            self.orbital_distance = max(2.0, min(20.0, self.orbital_distance - y * 0.5))

    def getpos(self): return self.rpos.copy()

    def eyepos(self): return self.eye.copy()
    def getvel(self): return self.vel.copy() / TICK
    
    
    
    def chunkpos(self, chunk_size):
        return self.cam.chunkpos(chunk_size)
        

    def teleport(self, pos):
        self.pos = np.array(pos, dtype='f4')
        self.vel = np.array([0.0, 0.0, 0.0], dtype='f4')
        self.falld = 0.0
        self.opos   = self.pos.copy()
        self.rpos   = self.pos.copy()
        self.accum  = 0.0
        self.yslide = 0.0
        ep    = self.pos.copy()
        ep[1] += self.physics.eye_h
        yr    = math.radians(self.cam.yaw)
        ep[0] += math.cos(yr) * self.physics.eye_f
        ep[2] += math.sin(yr) * self.physics.eye_f
        self.cam.pos = ep
        
        

    def setflying(self, fly):
        if fly != self.fly:
            self.toggleflight()
            

    def getsel(self):
        if 0 <= self._slot < 9:
            stack = self.inv.slots[self._slot]
            if stack:
                if stack.item.is_block:
                    return stack.item.itemId
                if stack.item.places_block is not None:
                    return stack.item.places_block
                return None

        """
        elif isinstance(self.inv, list):
            from items.registry import REGISTRY
            if 0 <= self._slot < len(self.inv):
                item = self.inv[self._slot]
                iid  = item.get('id', 1) if isinstance(item, dict) else item
                idef = REGISTRY.get(iid)
                if idef:
                    if idef.is_block: return iid
                    if idef.places_block is not None: return idef.places_block
            return None
        """

        return None

    def targetblock(self, max_dist=RAYCAST_DIST):
        start = self.eye.copy()

        direction = self.cam.front
        step = 0.05
        dist = 0.0
        lb   = None

        while dist < max_dist:
            p     = start + direction * dist
            block = (int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(p[2])))

            if self.physics.isblocksolid(block[0], block[1], block[2]):
                face = None

                if lb is not None and lb != block:
                    dx = lb[0] - block[0]
                    dy = lb[1] - block[1]
                    dz = lb[2] - block[2]

                    if abs(dx) + abs(dy) + abs(dz) == 1:
                        face = (dx, dy, dz)

                if face is None:
                    ad = (abs(direction[0]), abs(direction[1]), abs(direction[2]))
                    mi = 0
                    if ad[1] > ad[mi]: mi = 1
                    if ad[2] > ad[mi]: mi = 2

                    face = [0, 0, 0]
                    face[mi] = -1 if direction[mi] > 0 else 1
                    face = tuple(face)

                # print(block, face)
                return block, face

            lb   = block
            dist += step

        return None, None

    def placepos(self, block_pos, face):
        if block_pos is None or face is None:
            return None

        px = block_pos[0] + face[0]
        py = block_pos[1] + face[1]
        pz = block_pos[2] + face[2]

        ep = self.eye.copy()

        fy = self.rpos[1]
        hy = fy + self.physics.ph

        if (abs(px - ep[0]) < 0.6 and
            abs(pz - ep[2]) < 0.6 and
            py >= fy - 0.2 and py <= hy + 0.2):
            return None

        return (px, py, pz)


"""
def get_lookat(self, max_dist=8.0, step=0.05):
    pos = self.cam.pos.copy()
    d   = self.cam.front
    n   = int(max_dist / step)
    for i in range(n):
        pos += d * step
        bx, by, bz = int(pos[0]), int(pos[1]), int(pos[2])
        if self.physics.isblocksolid(bx, by, bz):
            return (bx, by, bz)
    return None
"""




# shims
Player.position  = property(lambda self: self.pos,       lambda self, v: setattr(self, 'pos', v))
Player.velocity  = property(lambda self: self.vel,       lambda self, v: setattr(self, 'vel', v))
Player.is_flying = property(lambda self: self.fly,       lambda self, v: setattr(self, 'fly', v))
Player.is_sprint = property(lambda self: self.sprint,    lambda self, v: setattr(self, 'sprint', v))
