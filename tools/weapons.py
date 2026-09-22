import csv
import math
import json
import os
import sys

from dsgo import Dsgo

WEAPON_LIST_RECORD = 1

CLASSES = {0: "Ranger", 1: "Wing Diver", 2: "Fencer", 3: "Air Raider"}


def catalog(table_path, text_path):
    table = Dsgo(open(table_path, "rb").read())
    text = Dsgo(open(text_path, "rb").read())

    entries = [table.record(i) for i in table.children(WEAPON_LIST_RECORD)]
    names = [text.record(i) for i in text.children(WEAPON_LIST_RECORD)]
    if len(entries) != len(names):
        raise SystemExit("tabla y texto no coinciden: %d vs %d" % (len(entries), len(names)))

    return [weapon(index, entry, name) for index, (entry, name) in enumerate(zip(entries, names))]


def weapon(index, entry, name):
    category = int(entry[2])
    return {
        "index": index,
        "id": entry[0],
        "asset": entry[1],
        "class": CLASSES.get(category // 100, "?"),
        "category": category,
        # entry[4] * 100 da 4x el "Lv" que muestra el juego. Se redondea antes de
        # dividir porque en float 2.6 * 25 da 64.99 y perdiamos un nivel.
        "level": math.floor(round(entry[4] * 100) / 4),
        # entry[6] es el tope de mejora de cada stat: si el save iguala todos,
        # el arma esta al maximo y el juego le pone estrella al nombre.
        "upgrades": [int(v) for v in entry[6]],
        "name": name[0],
        "description": name[1],
        "stats": [stat(s) for s in name[2]],
    }


# El segundo double de cada grupo es un codigo de tipo de stat, constante por
# etiqueta (Capacity=0, Damage=8, Accuracy=13, Range/ShotSpeed=16, Reload=21).
# El 25 guarda el intervalo en frames, no disparos por segundo: el Lysander trae
# 240, que como "240/sec" es absurdo para un bolt-action y como 60/240 da los
# 0.25/sec reales. Solo ROF y Beacon ROF lo usan.
CODIGO_INTERVALO_EN_FRAMES = 25
FRAMES_POR_SEGUNDO = 60.0


def stat(raw):
    label, template = raw[0], raw[1]
    values = []
    for group in raw[2:]:
        valor = group[0]
        if len(group) > 1 and group[1] == CODIGO_INTERVALO_EN_FRAMES and valor:
            valor = round(FRAMES_POR_SEGUNDO / valor, 2)
        values.append(valor)
    return {"label": label, "text": render(template, values), "values": values}


def render(template, values):
    text = template
    for position, value in enumerate(values):
        text = text.replace("$%d" % position, number(value))
    return text


def number(value):
    v = float(value)
    if v.is_integer():
        return str(int(v))
    text = "%.2f" % v if abs(v) >= 1 else "%.4g" % v
    return text.rstrip("0").rstrip(".")


def write_csv(rows, path):
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["index", "clase", "categoria", "nivel", "id", "nombre", "stats"])
        for row in rows:
            stats = " | ".join("%s: %s" % (s["label"], s["text"]) for s in row["stats"])
            writer.writerow([row["index"], row["class"], row["category"], row["level"], row["id"], row["name"], stats])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    source = sys.argv[1] if len(sys.argv) > 1 else "extract/WEAPON/WEAPON"
    rows = catalog(os.path.join(source, "WEAPONTABLE.SGO"), os.path.join(source, "WEAPONTEXT.EN.SGO"))

    out = sys.argv[2] if len(sys.argv) > 2 else "build/catalog"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump(rows, open(out + ".json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    write_csv(rows, out + ".csv")
    print("%d armas -> %s.json / %s.csv" % (len(rows), out, out))
