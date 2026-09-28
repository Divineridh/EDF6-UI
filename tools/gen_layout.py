"""Reconstruye los layouts modificados a partir de los del juego.

Las ediciones son en sitio: patch.py reescribe floats y re-apunta strings a la
tabla que el archivo ya tiene, asi que el tamaño no cambia y ningun offset se
mueve. Reserializar un SGO/DSGO entero crashea el juego.

Cada entrada es (ruta del nodo, valor). Un valor con "@" adelante es un string
que se re-apunta a una entrada existente de la tabla.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patch import load

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.join(RAIZ, "extract", "UI")
SALIDA = os.path.join(RAIZ, "build", "UI")

CAMBIOS = {
# pantalla de equipamiento
"LYT_HUIHQWEAPONSELECT.SGO": [
    ("2.2.0", "-600"),
    ("6.1.0.1.0", "1330"),
    ("6.1.0.1.1", "67"),
    ("6.1.1.1.3", "560"),
    ("10.1", "@app:/UI/Transparent_skin.sgo"),
    ("11.1.0.1.0", "1345"),
    ("11.1.0.1.1", "647"),
    ("11.1.1.1.3", "298"),
    ("17.2.0", "1255"),
    ("17.2.1", "830"),
    ("18.2.0", "1255"),
    ("18.2.1", "660"),
    ("19.1.0.1.0", "20"),
    ("19.1.0.1.1", "632"),
    ("19.1.1.1.3", "1320"),
    ("21.3.2", "440"),
    ("21.3.3", "560"),
    ("22.2.0", "16"),
    ("22.2.1", "32"),
    ("22.3.2", "1229"),
    ("22.3.3", "160"),
    ("23.1", "@app:/UI/Window07_WeaponSel2_skin.sgo"),
    ("23.2.0", "0"),
    ("23.2.1", "647"),
    ("23.3.2", "1360"),
    ("23.3.3", "205"),
    ("24.2.0", "1420"),
    ("24.2.1", "60"),
    ("24.3.2", "465"),
    ("24.3.3", "460"),
    ("25.2.0", "20"),
    ("25.2.1", "80"),
    ("25.3.1", "40"),
    ("25.3.2", "425"),
    ("26.2.0", "20"),
    ("26.3.2", "1320"),
    ("27.1", "@app:/UI/Window07_WeaponSel2_skin.sgo"),
    ("27.2.0", "1400"),
    ("27.2.1", "-65"),
    ("27.3.2", "465"),
    ("27.3.3", "540"),
    ("27.7.1.1.0", "0"),
    ("27.7.1.1.1", "0"),
    ("28.2.0", "354"),
    ("29.2.0", "354"),
    ("30.2.0", "16"),
    ("30.2.1", "608"),
    ("32.2.0", "397"),
    ("33.2.0", "397"),
    ("34.3.2", "440"),
    ("35.3.2", "440"),
    ("36.2.0", "20"),
    ("36.3.2", "1320"),
    ("36.3.3", "560"),
    ("36.7.0.1.0", "0"),
    ("36.7.0.1.2", "0"),
    ("39.1", "@app:/UI/Transparent_skin.sgo"),
    ("39.2.0", "40"),
    ("39.2.1", "130"),
    ("39.3.2", "1830"),
    ("39.3.3", "870"),
    ("40.1", "@app:/UI/Window07_WeaponSel2_skin.sgo"),
    ("40.2.0", "40"),
    ("40.2.1", "110"),
    ("40.3.2", "1360"),
    ("40.3.3", "647"),
],
# marco decorativo del cuartel
"LYT_MAINFRAME.SGO": [
    ("10.1", "@app:/UI/Transparent_skin.sgo"),
],
# cuadro de clase y equipo
"LYT_HUIHQCURRENTSTATUS.SGO": [
    ("9.2.0", "1710"),
    ("9.2.1", "593"),
    ("11.3.2", "433"),
    ("12.3.2", "433"),
    ("13.3.2", "433"),
    ("14.3.2", "433"),
    ("19.2.0", "1440"),
    ("19.2.1", "633"),
    ("19.3.2", "465"),
],
}


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, pares in CAMBIOS.items():
        e = load(os.path.join(ORIGEN, nombre))
        for ruta, valor in pares:
            if valor.startswith("@"):
                e.repoint(ruta, valor[1:])
            else:
                e.set(ruta, valor)
        destino = os.path.join(SALIDA, nombre)
        open(destino, "wb").write(bytes(e.buf))
        print("%s: %d valores, %d bytes" % (nombre, len(pares), len(e.buf)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
