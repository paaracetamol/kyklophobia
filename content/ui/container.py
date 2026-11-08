from ui.inv import Inventory
from items.registry import REGISTRY, ItemStack
from world.container import FUEL, FURN_ONLY
from world.blocks import CHEST, TRAPPED_CHEST, DISPENSER, DROPPER, HOPPER, FURNACE, FURNACE_ON


# slot pos
def layout(b, n):
    if b in (DISPENSER, DROPPER):
        cs = [(62 + j * 18, 17 + i * 18) for i in range(3) for j in range(3)]
        return "dispenser", 176, 166, cs, 84, 142

    if b == HOPPER:
        cs = [(44 + j * 18, 20) for j in range(5)]
        return "hopper", 176, 133, cs, 51, 109

    if b in (FURNACE, FURNACE_ON):
        cs = [(56, 53)] if n == 1 else [(56, 17), (56, 53), (116, 35)]
        return "furnace", 176, 166, cs, 84, 142


    r  = n // 9
    o  = (r - 4) * 18
    cs = [(8 + k * 18, 18 + j * 18) for j in range(r) for k in range(9)]
    return "generic_54", 176, 114 + r * 18, cs, 103 + o, 161 + o



def tostack(s):
    if not s: return None
    d = REGISTRY.get(s[0])
    return ItemStack(d, s[1]) if d else None


def fromstack(s): return (s.item.itemId, s.count) if s else None



# current open
class ContScreen:
    def __init__(self, x, y, z, b, n, pinv, setslot):
        self.pos  = (x, y, z)
        self.b    = b
        self.n    = n
        self.rows = n // 9
        self.pinv = pinv
        self.setslot = setslot
        self.tex, self.w, self.h, cs, my, hy = layout(b, n)

        self.cv = Inventory(n)
        self.cv.spos = cs
        self.pv = Inventory(36)
        self.pv.spos  = [(8 + i * 18, hy) for i in range(9)]
        self.pv.spos += [(8 + k * 18, my + j * 18) for j in range(3) for k in range(9)]
        self.pv.slots = pinv.slots
        self.snap = [None] * n
        self.only = None

        if b in (FURNACE, FURNACE_ON): 
            self.only = (FUEL,) if n == 1 else FURN_ONLY





    def sync(self, snap):
        if snap is not None and len(snap) == self.n: self.snap = snap
        self.cv.slots = [tostack(i) for i in self.snap]
        self.pv.slots = self.pinv.slots


    def push(self, old):
        for i in range(self.n):
            j = fromstack(self.cv.slots[i])
            if j != old[i]:
                self.setslot(i, j)
                old[i] = j

        self.snap = old




    def hit(self, inv, lx, ly):
        for i, (sx, sy) in enumerate(inv.spos):
            if sx <= lx < sx + 18 and sy <= ly < sy + 18: return i

        return -1




    # false -> click outside
    def click(self, lx, ly, button, shift=False):

        if not (0 <= lx < self.w and 0 <= ly < self.h): return False
        old = [fromstack(i) for i in self.cv.slots]


        for v in (self.cv, self.pv):
            i = self.hit(v, lx, ly)
            if i < 0: continue
            # Slot.isItemValid

            h = self.pinv._held
            if (
                v is self.cv and self.only and h and not shift and 
                self.only[i] is not None and h.item.itemId not in self.only[i]
            ): break

            if shift and button == 1: self.quick(v, i)
            else:
                v._held = self.pinv._held
                v.slotclick(i, button)
                self.pinv._held = v._held

            break

        self.push(old)
        return True





    
    
    def quick(self, v, i):
        s = v.slots[i]
        if not s: return

        if v is self.cv: 
            dst = [(self.pv, j) for j in list(range(9, 36)) + list(range(9))][::-1]


        elif self.only:
            # TODO: Recipes
            k = len(self.only) // 2

            if s.item.itemId in self.only[k]: dst = [(self.cv, k)]

            elif i < 9: dst = [(self.pv, j) for j in range(9, 36)]
            else:       dst = [(self.pv, j) for j in range(9)]

        else:
            dst = [(self.cv, j) for j in range(self.n)]


        for u, j in dst:
            t = u.slots[j]

            if t and t.item.itemId == s.item.itemId and not t.isfull():
                s.count = t.add(s.count)
                if s.count <= 0: break


        if s.count > 0:
            for u, j in dst:
                if u.slots[j] is None:
                    u.slots[j] = s.copy()
                    s.count = 0
                    break


        if s.count <= 0: v.slots[i] = None











































