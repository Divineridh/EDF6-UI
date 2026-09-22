"""Sube a la primera linea de la descripcion datos que el juego entierra al final.

Dos notas, ambas sobre WEAPONTEXT:

  - Tipo de impulso de Fencer. El dato ya existe, pero en la ultima linea: hay
    que scrollear hasta el fondo para saber si el arma pide Side Thruster (dash)
    o Jump Booster (salto).
  - Cargador unico. Las armas con "Reload Time: ----" no recargan nunca: los
    tiros del cargador son todos los que tenes en la mision.

Por que la descripcion y no un stat nuevo: agregar una fila de stats implica
hacer crecer un array del DSGO, que es exactamente lo que crasheo el juego
cuando reescribimos el manual entero. La descripcion en cambio es un string
suelto, y re-apuntar strings al final del archivo esta probado.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dsgo import Dsgo
from dsgopatch import Patcher

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGO = os.path.join(RAIZ, "build", "catalog.json")
# Si hay un WEAPONTEXT modeado instalado, se parchea ESE y no el vanilla: pisarlo
# con el del cpk borraria los cambios del otro mod.
_MODEADO = os.path.join(RAIZ, "extract", "BRIAN", "WEAPONTEXT.EN.sgo")
_VANILLA = os.path.join(RAIZ, "extract", "WEAPON", "WEAPON", "WEAPONTEXT.EN.SGO")
TEXTO = _MODEADO if os.path.exists(_MODEADO) else _VANILLA
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
    print("  %d armas de Fencer con linea de impulso" % cuenta["impulso"])
    print("  %d armas con linea de cargador unico" % cuenta["cargador"])
    print("  %d bytes -> %d (solo se agrego al final)" % (len(origen), len(datos)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
