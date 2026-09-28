import os

JUEGO_POR_DEFECTO = r"C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6"
RELATIVA_AL_JUEGO = os.path.join("Mods", "Compendium", "obtenidas.txt")


def candidatas(respaldo_local=None):
    rutas = []
    explicita = os.environ.get("EDF6_OBTENIDAS")
    if explicita:
        rutas.append(explicita)
    rutas.append(os.path.join(os.environ.get("EDF6_DIR", JUEGO_POR_DEFECTO), RELATIVA_AL_JUEGO))
    if respaldo_local:
        rutas.append(respaldo_local)
    return rutas


def cargar(respaldo_local=None):
    for ruta in candidatas(respaldo_local):
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as fh:
                nombres = {l.strip() for l in fh if l.strip()}
            if nombres:
                return ruta, nombres
    return None, None


def informe(ruta, nombres, respaldo_local=None):
    if nombres is None:
        lineas = ["  NO obtenidas.txt: the owned column is a placeholder by level.",
                  "  Looked in:"]
        lineas += ["    " + r for r in candidatas(respaldo_local)]
        return "\n".join(lineas)
    return "  owned: %d names from %s" % (len(nombres), ruta)
