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
        raise SystemExit("table and text don't match: %d vs %d" % (len(entries), len(names)))

    return [weapon(index, entry, name) for index, (entry, name) in enumerate(zip(entries, names))]


def weapon(index, entry, name):
    category = int(entry[2])
    return {
        "index": index,
        "id": entry[0],
        "asset": entry[1],
        "class": CLASSES.get(category // 100, "?"),
        "category": category,
        # entry[4] * 100 is 4x the "Lv" the game shows. It's rounded before
        # dividing because in float 2.6 * 25 gives 64.99 and we lost a level.
        "level": math.floor(round(entry[4] * 100) / 4),
        # entry[6] is each stat's upgrade cap: if the save matches them all, the
        # weapon is maxed and the game puts a star on its name.
        "upgrades": [int(v) for v in entry[6]],
        "name": name[0],
        "description": name[1],
        "stats": [stat(s) for s in name[2]],
    }


# The second double of each group is a stat type code, constant per label
# (Capacity=0, Damage=8, Accuracy=13, Range/ShotSpeed=16, Reload=21).
# 25 stores the interval in frames, not shots per second: the Lysander has 240,
# which as "240/sec" is absurd for a bolt-action and as 60/240 gives the real
# 0.25/sec. Only ROF and Beacon ROF use it.
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
        writer.writerow(["index", "class", "category", "level", "id", "name", "stats"])
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
    print("%d weapons -> %s.json / %s.csv" % (len(rows), out, out))
