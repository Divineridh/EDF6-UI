"""Weapon category names, from DEFAULTPACKAGE/CONFIG.SGO.

That file is SGO but **big-endian** (the signature reads '\\0OGS'), unlike the
UI layouts. Node 3 is the id -> key table.
"""

import json
import os
import re
import struct
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(RAIZ, "extract", "DEFAULTPACKAGE", "CONFIG.SGO")
SALIDA = os.path.join(RAIZ, "build", "categories.json")

CLASES = ("Ranger", "Pale", "Heavy", "Engineer")


class SgoBE:
    def __init__(self, data):
        assert data[:4] == b"\x00OGS", data[:4]
        self.d = data
        self.count = struct.unpack_from(">I", data, 8)[0]
        self.off = struct.unpack_from(">I", data, 0x0C)[0]

    def record(self, o):
        t, n, v = struct.unpack_from(">III", self.d, o)
        if t == 0:
            return [self.record(o + v + i * 12) for i in range(n)]
        if t == 1:
            return v if v < 0x80000000 else v - 0x100000000
        if t == 2:
            return round(struct.unpack_from(">f", self.d, o + 8)[0], 3)
        if t == 3:
            p = o + v
            e = p
            while e + 1 < len(self.d) and self.d[e:e + 2] != b"\x00\x00":
                e += 2
            return self.d[p:e].decode("utf-16be", "replace")
        return None

    def tree(self):
        return [self.record(self.off + i * 12) for i in range(self.count)]


def legible(clave):
    """Weapon_Engineer_Call_Gunship -> Call Gunship"""
    partes = clave.split("_")
    if partes and partes[0] == "Weapon":
        partes = partes[1:]
    if partes and partes[0] in CLASES:
        partes = partes[1:]
    palabras = []
    for p in partes:
        palabras += re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", p)
    return " ".join(w.capitalize() if w.islower() else w for w in palabras) or clave


def main():
    tabla = SgoBE(open(CONFIG, "rb").read()).tree()[3]
    cats = {int(par[0]): {"key": par[1], "name": legible(par[1])} for par in tabla}
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    json.dump(cats, open(SALIDA, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%d categories -> %s" % (len(cats), SALIDA))
    for k in sorted(cats)[:6]:
        print("  %3d  %s" % (k, cats[k]["name"]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
