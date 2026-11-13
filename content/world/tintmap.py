import moderngl
from config import TINT_RING




class TintMap:
    def __init__(s, ctx, prog, u=5):
        s.tex = ctx.texture((TINT_RING, TINT_RING), 4, bytes(TINT_RING * TINT_RING * 16), dtype="f4")
        s.tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        s.tex.use(u)
        prog['tintmap'].value = u

    def put(s, c):
        s.tex.write(c.tint.tobytes(), viewport=((c.x * 16) % TINT_RING, (c.z * 16) % TINT_RING, 16, 16))
