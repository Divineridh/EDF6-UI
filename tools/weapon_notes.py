"""Moves to the first line of the description data the game buries at the end.

Two notes, both on WEAPONTEXT:

  - Fencer boost type. The data is already there, but on the last line: you
    have to scroll to the bottom to learn whether the weapon wants Side Thruster
    (dash) or Jump Booster (jump).
  - Single magazine. Weapons with "Reload Time: ----" never reload: the shots
    in the magazine are all you get for the mission.

Why the description and not a new stat: adding a stat row means growing a
DSGO array, which is exactly what crashed the game when we rewrote the whole
manual. The description instead is a standalone string, and re-pointing strings
to the end of the file is proven.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dsgo import Dsgo
from dsgopatch import Patcher

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGO = os.path.join(RAIZ, "build", "catalog.json")
# If a modded WEAPONTEXT is installed, THAT one is patched and not the vanilla
# one: overwriting it with the cpk's would wipe the other mod's changes.
# --vanilla forces the game's own file, which is what a public release must use:
# shipping the modded one would redistribute someone else's mod.
_MODEADO = os.path.join(RAIZ, "extract", "BRIAN", "WEAPONTEXT.EN.sgo")
_VANILLA = os.path.join(RAIZ, "extract", "WEAPON", "WEAPON", "WEAPONTEXT.EN.SGO")
TEXTO = _MODEADO if os.path.exists(_MODEADO) and "--vanilla" not in sys.argv else _VANILLA
SALIDA = os.path.join(RAIZ, "build", "WEAPON", "WEAPONTEXT.EN.SGO")

LISTA_MAESTRA = 1

DASH = "Side Thruster"
JUMP = "Jump Booster"


def tipo_de_impulso(descripcion):
    dash = DASH in descripcion
    jump = JUMP in descripcion
    if dash and jump:
        return "Dash or Jump"
    if dash:
        return "Dash (Side Thruster)"
    if jump:
        return "Jump (Jump Booster)"
    return None


def stat(arma, etiqueta):
    for s in arma["stats"]:
        if s["label"] == etiqueta:
            return s["text"]
    return None


def sin_recarga(arma):
    texto = stat(arma, "Reload Time")
    if texto is None:
        return False
    limpio = texto.strip().replace("-", "").replace("─", "")
    return limpio == "" and "-" in texto


def notas(arma, descripcion):
    salida = []
    if arma["class"] == "Fencer":
        tipo = tipo_de_impulso(descripcion)
        if tipo:
            salida.append("Boost type: %s" % tipo)
    if sin_recarga(arma):
        salida.append("Single magazine: does not reload")
    return salida


def main():
    catalogo = {w["index"]: w for w in json.load(open(CATALOGO, encoding="utf-8"))}

    origen = open(TEXTO, "rb").read()
    doc = Dsgo(origen)
    entradas = doc.children(LISTA_MAESTRA)
    parche = Patcher(origen)

    cuenta = {"impulso": 0, "cargador": 0}
    for indice, arma in sorted(catalogo.items()):
        if indice >= len(entradas):
            continue
        campos = doc.children(entradas[indice])
        if len(campos) < 2:
            continue
        i_desc = campos[1]
        descripcion = doc.record(i_desc)
        if not isinstance(descripcion, str):
            continue

        lineas = notas(arma, descripcion)
        if not lineas:
            continue
        for l in lineas:
            cuenta["impulso" if l.startswith("Boost") else "cargador"] += 1
        parche.set_string(i_desc, "%s\n\n%s" % ("\n".join(lineas), descripcion))

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    datos = parche.data()
    open(SALIDA, "wb").write(datos)

    print("%s" % SALIDA)
    print("  %d Fencer weapons with a boost line" % cuenta["impulso"])
    print("  %d weapons with a single-magazine line" % cuenta["cargador"])
    print("  %d bytes -> %d (only appended at the end)" % (len(origen), len(datos)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
