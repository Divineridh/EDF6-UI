import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cpk import Cpk
from mdb import Mdb
from rab import entries
from sgo import Sgo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6"
CORNERS = ("LT", "LB", "RT", "RB")
SIDES = ("left", "right")
SKIN_CLASSES = ("Window", "Button", "Model", "Solid", "Texture")


def loaded_groups():
    groups = {}
    for path in glob.glob(os.path.join(ROOT, "extract", "UI", "UIRESOURCEGROUP_*.SGO")):
        group = os.path.basename(path)[len("UIRESOURCEGROUP_"):-4]
        text = repr(Sgo(open(path, "rb").read()).tree()).upper()
        groups[group] = text
    return groups


def reach(mdb, obj):
    r = dict.fromkeys(("left", "right", "top", "bottom", "out_left", "out_right", "out_top", "out_bottom"), 0.0)
    loose = set()
    for x, y, uv, bones in mdb.bound_vertices(obj):
        for b in bones:
            name = b["name"].lower()
            if b["name"] not in CORNERS and name not in SIDES:
                loose.add(b["name"])
                continue
            dx, dy = x - b["x"], y - b["y"]
            if name.startswith("l"):
                r["left"] = max(r["left"], dx)
                r["out_left"] = max(r["out_left"], -dx)
            else:
                r["right"] = max(r["right"], -dx)
                r["out_right"] = max(r["out_right"], dx)
            if name in SIDES:
                continue
            if b["name"][1] == "T":
                r["top"] = max(r["top"], dy)
                r["out_top"] = max(r["out_top"], -dy)
            else:
                r["bottom"] = max(r["bottom"], -dy)
                r["out_bottom"] = max(r["out_bottom"], dy)
    return r, sorted(loose)


def main(filters):
    cpk = Cpk(os.path.join(GAME, "Root.cpk"))
    files = {e["path"].upper(): e for e in cpk.entries()}
    groups = loaded_groups()
    print("%-24s %-7s %-6s %-5s %9s %9s  %-26s %s" % ("skin", "class", "era", "hq", "min w", "min h", "outside frame (l t r b)", "design"))
    for path in sorted(glob.glob(os.path.join(ROOT, "extract", "UI", "*_SKIN.SGO"))):
        name = os.path.basename(path)[:-len("_SKIN.SGO")]
        if filters and not any(f.upper() in name for f in filters):
            continue
        tree = Sgo(open(path, "rb").read()).tree()
        cls = next((x for x in tree if x in SKIN_CLASSES), "?")
        in_hq = any(("UI/%s_SKIN.SGO" % name) in groups.get(g, "") for g in ("HQ", "GLOBAL"))
        if cls == "Solid":
            print("%-24s %-7s %-6s %-5s %9s %9s  %-26s rgba=%s" % (name, cls, "all", "yes" if in_hq else "no", 0, 0, "-", tree[0]))
            continue
        if cls not in ("Window", "Button") or not isinstance(tree[0], str):
            continue
        base = files.get("UI/" + tree[0].split("/")[-1].upper())
        if not base:
            continue
        model = Sgo(cpk.read(base)).tree()[0][0][0][0]
        archive = files.get("UI/" + model.split("/")[-1].upper())
        if not archive:
            continue
        mdbs = [p for p in entries(cpk.read(archive)) if p[:4] == b"MDB0"]
        mdb = Mdb(mdbs[0])
        design = next(("%dx%d" % (b["x"], b["y"]) for b in mdb.bones if b["name"] == "RB"), "-")
        for obj in mdb.objects:
            era = obj["name"].rsplit(".", 1)[1].upper() if "." in obj["name"] else "base"
            r, loose = reach(mdb, obj)
            outside = "%d %d %d %d" % (r["out_left"], r["out_top"], r["out_right"], r["out_bottom"])
            print("%-24s %-7s %-6s %-5s %9d %9d  %-26s %s %s" % (
                name, cls, era, "yes" if in_hq else "no", r["left"] + r["right"], r["top"] + r["bottom"],
                outside, design, ("bones=" + ",".join(loose)) if loose else ""))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
