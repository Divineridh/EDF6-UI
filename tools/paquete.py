import os
import shutil
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(RAIZ, "build")
FUENTE = os.path.join(RAIZ, "paquete")
DESTINO = os.path.join(BUILD, "paquete")
SALIDA = os.path.join(os.path.dirname(RAIZ), "builds")
ZIP = os.path.join(SALIDA, "EDF6UIMod.zip")

CONTENIDO = [
    (os.path.join(BUILD, "UI", "LYT_HUIHQWEAPONSELECT.SGO"),
     "Mods/UI/LYT_HUIHQWEAPONSELECT.SGO"),
    (os.path.join(BUILD, "UI", "LYT_MAINFRAME.SGO"),
     "Mods/UI/LYT_MAINFRAME.SGO"),
    (os.path.join(BUILD, "UI", "LYT_HUIHQCURRENTSTATUS.SGO"),
     "Mods/UI/LYT_HUIHQCURRENTSTATUS.SGO"),
    (os.path.join(BUILD, "WEAPON", "WEAPONTEXT.EN.SGO"),
     "Mods/WEAPON/WEAPONTEXT.EN.SGO"),
    (os.path.join(FUENTE, "LEEME.txt"), "LEEME.txt"),
]


def main():
    faltan = [o for o, _ in CONTENIDO if not os.path.exists(o)]
    if faltan:
        raise SystemExit("faltan archivos para armar el paquete:\n  " + "\n  ".join(faltan))

    if os.path.exists(DESTINO):
        shutil.rmtree(DESTINO)
    for origen, relativo in CONTENIDO:
        destino = os.path.join(DESTINO, relativo.replace("/", os.sep))
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy2(origen, destino)

    os.makedirs(SALIDA, exist_ok=True)
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for _, relativo in CONTENIDO:
            z.write(os.path.join(DESTINO, relativo.replace("/", os.sep)), relativo)

    print("%s" % ZIP)
    for _, relativo in CONTENIDO:
        ruta = os.path.join(DESTINO, relativo.replace("/", os.sep))
        print("  %-44s %8d bytes" % (relativo, os.path.getsize(ruta)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
