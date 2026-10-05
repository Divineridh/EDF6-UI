import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cpk import Cpk
from patch import load
from rab import members, rebuild

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6"
SOURCE = os.path.join(ROOT, "extract", "UI")

FILL = (5, 14, 10)
FILL_ALPHA = 224
BORDER = (47, 107, 74)
ACCENT = (95, 163, 124)
NAME_ROW = (25, 62, 42)
DATA_ROW = (12, 32, 22)
TAB_ALPHA = 204
ACCENT_SELECTION = (255, 138, 31, 235)


def luminance(r, g, b):
    return 0.3 * r + 0.59 * g + 0.11 * b


def lerp(c0, c1, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c0, c1))


def ramp(anchors, fill_alpha):
    def paint(r, g, b, a, lums):
        lum = luminance(r, g, b)
        color = anchors[-1][1]
        if lum <= anchors[0][0]:
            color = anchors[0][1]
        else:
            for (l0, c0), (l1, c1) in zip(anchors, anchors[1:]):
                if lum <= l1:
                    color = lerp(c0, c1, (lum - l0) / (l1 - l0))
                    break
        return color, FILL_ALPHA if a == fill_alpha else a
    return paint


def gradient(dark, light):
    def paint(r, g, b, a, lums):
        lo, hi = lums
        t = (luminance(r, g, b) - lo) / (hi - lo) if hi > lo else 0
        return lerp(dark, light, t), a
    return paint


def flat(body, line, body_alpha=None):
    def paint(r, g, b, a, lums):
        if a >= 200 and luminance(r, g, b) >= 150:
            return line, a
        return body, body_alpha.get(a, a) if body_alpha else a
    return paint


def framed(border, fill, fill_alpha):
    def paint(dds):
        h, w = struct.unpack_from("<II", dds, 12)
        levels = max(1, struct.unpack_from("<I", dds, 28)[0])
        out = bytearray(dds)
        offset = 128
        for _ in range(levels):
            for y in range(h):
                for x in range(w):
                    edge = x in (0, w - 1) or y in (0, h - 1)
                    r, g, b = border if edge else fill
                    out[offset:offset + 4] = bytes((b, g, r, 255 if edge else fill_alpha))
                    offset += 4
            w, h = max(1, w // 2), max(1, h // 2)
        return bytes(out)
    return paint


def pixels(paint):
    return lambda dds: recolor(dds, paint)


CLONES = [
    ("WINDOW_TEST01", "EDF6UI_Panel", {
        "palette01.dds": pixels(ramp(((19.5, FILL), (171.7, BORDER), (248.0, ACCENT)), 171)),
        "edf6_window01.dds": pixels(ramp(((14.2, FILL), (104.1, BORDER), (192.0, ACCENT)), 177)),
        "edf6_window01.b.dds": pixels(ramp(((0.0, FILL), (130.2, BORDER), (192.0, ACCENT)), 177)),
    }),
    ("WINDOW05_SOLDIERINFO", "EDF6UI_ClassBox", {
        "window5_soldierinfo_window.dds": pixels(flat(FILL, BORDER, {127: FILL_ALPHA})),
        "window5_soldierinfo_frame.dds": pixels(gradient(BORDER, ACCENT)),
    }),
    ("SOLDIERINFO_NAME", "EDF6UI_ClassName", {"*": pixels(flat(NAME_ROW, ACCENT))}),
    ("SOLDIERINFO_DATA", "EDF6UI_ClassData", {"*": pixels(flat(DATA_ROW, BORDER))}),
    ("WEAPONSEL_INDEXBASE", "EDF6UI_Tab", {"*": framed(BORDER, FILL, TAB_ALPHA)}),
]

SOLIDS = [
    ("SCROLLBAR_GUIDE", "EDF6UI_Accent", ACCENT_SELECTION),
]


def output_names():
    return ([name.upper() + suffix for _, name, _ in CLONES for suffix in ("_MERGE.RAB", ".SGO", "_SKIN.SGO")] +
            [name.upper() + "_SKIN.SGO" for _, name, _ in SOLIDS])


def recolor(dds, paint):
    h, w = struct.unpack_from("<II", dds, 12)
    out = bytearray(dds)
    pixels = range(128, 128 + w * h * 4, 4)
    lums = [luminance(out[p + 2], out[p + 1], out[p]) for p in pixels if out[p + 3]]
    bounds = (min(lums), max(lums)) if lums else (0, 0)
    for p in pixels:
        b, g, r, a = out[p:p + 4]
        if a == 0:
            continue
        (r2, g2, b2), a2 = paint(r, g, b, a, bounds)
        out[p:p + 4] = bytes((b2, g2, r2, a2))
    return bytes(out)


def clone(cpk, files, source, name, recipe, dest):
    skin = load(os.path.join(SOURCE, source + "_SKIN.SGO"))
    base = load(os.path.join(SOURCE, source + ".SGO"))
    archive_path = base.text_at("0.0.0.0")
    archive = cpk.read(files["UI/" + archive_path.split("/")[-1].upper()])
    textures = {}
    for member, data in members(archive).items():
        paint = recipe.get(member) or recipe.get("*")
        if member.endswith(".dds") and paint:
            textures[member] = paint(data)
    outputs = [(name.upper() + "_MERGE.RAB", rebuild(archive, textures))]
    base.repoint("0.0.0.0", "app:/UI/%s_merge.rab" % name, add=True)
    outputs.append((name.upper() + ".SGO", bytes(base.buf)))
    skin.repoint("0", "app:/UI/%s.sgo" % name, add=True)
    outputs.append((name.upper() + "_SKIN.SGO", bytes(skin.buf)))
    for filename, data in outputs:
        open(os.path.join(dest, filename), "wb").write(data)
    return [filename for filename, _ in outputs]


def solid(source, name, rgba, dest):
    skin = load(os.path.join(SOURCE, source + "_SKIN.SGO"))
    for channel, value in enumerate(rgba):
        skin.set("0.%d" % channel, value)
    filename = name.upper() + "_SKIN.SGO"
    open(os.path.join(dest, filename), "wb").write(bytes(skin.buf))
    return filename


def build(dest):
    cpk = Cpk(os.path.join(GAME, "Root.cpk"))
    files = {e["path"].upper(): e for e in cpk.entries()}
    written = []
    for source, name, recipe in CLONES:
        written += clone(cpk, files, source, name, recipe, dest)
    for source, name, rgba in SOLIDS:
        written.append(solid(source, name, rgba, dest))
    return written


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "UI")
    os.makedirs(dest, exist_ok=True)
    for f in build(dest):
        print(f, os.path.getsize(os.path.join(dest, f)))
