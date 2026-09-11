import math

SWING_T   = 6
YAW_CLAMP = 75.0
MOVE_EPS  = 0.0025
TP_DIST   = 4.0

RAD2DEG = 180.0 / math.pi
DEG2RAD = math.pi / 180.0




def wrapdeg(a):
    a = math.fmod(a, 360.0)
    if a >= 180.0:  a -= 360.0
    if a < -180.0:  a += 360.0
    return a


def lerpang(a, b, t):
    return a + wrapdeg(b - a) * t




class Pose:
    __slots__ = (
        'r_arm', 'l_arm', 'r_leg', 'l_leg',
        'r_arm_y', 'l_arm_y', 'r_arm_z', 'l_arm_z',
        'body_y', 'byaw', 'headyaw'
    )







class Biped:
    def __init__(self, yaw=0.0):
        self.lswing  = 0.0    # acc swing phase
        self.lamt    = 0.0    # reach
        self.olamt   = 0.0

        self.byaw    = yaw
        self.obyaw   = yaw
        self.hyaw    = yaw
        self.ohyaw   = yaw

        self.swingi  = 0
        self.swinging = False
        self.swing   = 0.0
        self.oswing  = 0.0

        self.age     = 0




    def swingarm(self):
        if not self.swinging or self.swingi >= SWING_T // 2 or self.swingi < 0:
            self.swingi   = -1
            self.swinging = True





    def tick(self, x, z, ox, oz, yaw, on_ground=True):
        dx = x - ox #lastpos
        dz = z - oz

        
        if dx * dx + dz * dz > TP_DIST * TP_DIST: dx = dz = 0.0

        self.olamt = self.lamt
        d = math.sqrt(dx * dx + dz * dz) * 4.0
        if d > 1.0: d = 1.0
        self.lamt   += (d - self.lamt) * 0.4
        self.lswing += self.lamt

        self.obyaw = self.byaw
        self.ohyaw = self.hyaw
        self.hyaw  = yaw





        tgt = self.byaw
        if dx * dx + dz * dz > MOVE_EPS:
            tgt = math.atan2(dz, dx) * RAD2DEG

            # backward
            f = abs(wrapdeg(yaw) - tgt)
            if 95.0 < f < 265.0: tgt -= 180.0



        if self.swing > 0.0: tgt = yaw
        self.setbyaw(tgt, yaw)

        if self.swinging:
            self.swingi += 1
            if self.swingi >= SWING_T:
                self.swingi   = 0
                self.swinging = False
        else:
            self.swingi = 0





        self.oswing = self.swing
        self.swing  = self.swingi / float(SWING_T)
        self.age   += 1







    
    def setbyaw(self, tgt, yaw):
        self.byaw += wrapdeg(tgt - self.byaw) * 0.3

        f = wrapdeg(yaw - self.byaw)
        if f < -YAW_CLAMP: f = -YAW_CLAMP
        if f >=  YAW_CLAMP: f =  YAW_CLAMP

        self.byaw = yaw - f
        
        if f * f > 2500.0: self.byaw += f * 0.2 #catch





    
    def pose(self, a, pitch, sneak=False):
        amt = self.olamt + (self.lamt - self.olamt) * a
        if amt > 1.0: amt = 1.0
        ls  = self.lswing - self.lamt * (1.0 - a)
        age = self.age + a

        # tick swing ends @ 5/6 -> 0: carry ->1
        f = self.swing - self.oswing
        if f < 0.0: f += 1.0
        sw = self.oswing + f * a

        ph = ls * 0.6662

        
        ra_x = math.cos(ph + math.pi) * 2.0 * amt * 0.5
        la_x = math.cos(ph)           * 2.0 * amt * 0.5
        rl_x = math.cos(ph)           * 1.4 * amt

        ra_y = la_y = 0.0
        ra_z = la_z = 0.0
        body_y = 0.0

        # punch
        if sw > 0.0:
            body_y = math.sin(math.sqrt(sw) * math.pi * 2.0) * 0.2
            ra_y  += body_y
            la_y  += body_y
            la_x  += body_y

            f1 = 1.0 - sw
            f1 = f1 * f1
            f1 = f1 * f1
            f1 = 1.0 - f1

            f2 = math.sin(f1 * math.pi)
            f3 = math.sin(sw * math.pi) * -(-pitch * DEG2RAD - 0.7) * 0.75

            ra_x -= f2 * 1.2 + f3
            ra_y += body_y * 2.0
            ra_z += math.sin(sw * math.pi) * -0.4

        if sneak:
            ra_x += 0.4
            la_x += 0.4

        # idle sway
        ra_z += math.cos(age * 0.09)  * 0.05 + 0.05
        la_z -= math.cos(age * 0.09)  * 0.05 + 0.05
        ra_x += math.sin(age * 0.067) * 0.05
        la_x -= math.sin(age * 0.067) * 0.05

        p = Pose()
        # r_* = left arm, l_* = right
        p.r_arm   = la_x * RAD2DEG
        p.l_arm   = ra_x * RAD2DEG
        p.r_arm_y = la_y * RAD2DEG
        p.l_arm_y = ra_y * RAD2DEG
        p.r_arm_z = la_z * RAD2DEG
        p.l_arm_z = ra_z * RAD2DEG
        #lesg
        p.r_leg   = rl_x * RAD2DEG
        p.l_leg   = rl_x * RAD2DEG
        p.body_y  = body_y * RAD2DEG

        p.byaw    = lerpang(self.obyaw, self.byaw, a)
        p.headyaw = wrapdeg(lerpang(self.ohyaw, self.hyaw, a) - p.byaw)
        return p
