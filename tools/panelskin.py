import os
import struct
import sys
from collections import namedtuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cpk import Cpk
from mdb import Mdb
from patch import load
from rab import members, rebuild

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6"
SOURCE = os.path.join(ROOT, "extract", "UI")

Palette = namedtuple("Palette", "fill border accent name_row data_row")

GREEN = Palette((5, 14, 10), (47, 107, 74), (95, 163, 124), (25, 62, 42), (12, 32, 22))
BLUE = Palette((5, 10, 18), (47, 82, 122), (100, 140, 196), (24, 44, 74), (11, 22, 38))
PLUM_GREY = Palette((11, 10, 13), (78, 72, 86), (138, 130, 150), (40, 36, 46), (20, 18, 24))

BLUE_ERA = BLUE
B_ERAS = PLUM_GREY
C_ERAS = GREEN

FILL_ALPHA = 224
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


def panel(palette, dark, mid, light, fill_alpha):
    return pixels(ramp(((dark, palette.fill), (mid, palette.border), (light, palette.accent)), fill_alpha))


def per_variant(texture, paint):
    stem, extension = texture.rsplit(".", 1)
    return {
        "%s.%s" % (stem, extension): paint(BLUE_ERA),
        "%s_b.%s" % (stem, extension): paint(B_ERAS),
        "%s_c.%s" % (stem, extension): paint(C_ERAS),
    }


def class_window(palette):
    return pixels(flat(palette.fill, palette.border, {127: FILL_ALPHA}))


def class_frame(palette):
    return pixels(gradient(palette.border, palette.accent))


Split = namedtuple("Split", "materials files")

SPLITS = {
    "EDF6UI_ClassBox": Split(
        materials={2: 2, 3: 3},
        files={
            2: ("Window5_SoldierInfo_frame_dds", "window5_soldierinfo_frame.dds", class_frame(B_ERAS)),
            3: ("Window5_SoldierInfo_window_dds", "window5_soldierinfo_window.dds", class_window(B_ERAS)),
            4: ("Window5_SoldierInfo_frame", "window5_soldierinfo_frame.dds", class_frame(C_ERAS)),
            5: ("Window5_SoldierInfo_window", "window5_soldierinfo_window.dds", class_window(C_ERAS)),
        }),
}

CLONES = [
    ("WINDOW_TEST01", "EDF6UI_Panel", {
        "palette01.dds": panel(BLUE_ERA, 19.5, 171.7, 248.0, 171),
        "edf6_window01.b.dds": panel(B_ERAS, 0.0, 130.2, 192.0, 177),
        "edf6_window01.dds": panel(C_ERAS, 14.2, 104.1, 192.0, 177),
    }),
    ("WINDOW05_SOLDIERINFO", "EDF6UI_ClassBox", {
        "window5_soldierinfo_window.dds": class_window(BLUE_ERA),
        "window5_soldierinfo_frame.dds": class_frame(BLUE_ERA),
    }),
    ("SOLDIERINFO_NAME", "EDF6UI_ClassName", per_variant(
        "window5_soldierinfo_textbase1.dds", lambda p: pixels(flat(p.name_row, p.accent)))),
    ("SOLDIERINFO_DATA", "EDF6UI_ClassData", per_variant(
        "window5_soldierinfo_textbase2.dds", lambda p: pixels(flat(p.data_row, p.border)))),
    ("WEAPONSEL_INDEXBASE", "EDF6UI_Tab", per_variant(
        "weaponsel_indexbase01.dds", lambda p: framed(p.border, p.fill, TAB_ALPHA))),
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


def retarget(model, split):
    out = bytearray(model)
    parsed = Mdb(model)
    textures_off = struct.unpack_from("<I", model, 0x2C)[0]
    for material, texture in split.materials.items():
        record = parsed.material_off + material * 32
        refs = struct.unpack_from("<I", model, record + 20)[0]
        struct.pack_into("<I", out, record + refs, texture)
    for texture, (file, _, _) in split.files.items():
        encoded = b"\0\0" + file.encode("utf-16le") + b"\0\0"
        found = model.find(encoded)
        if found < 0 or found % 2 or model.find(encoded, found + 2) >= 0:
            raise SystemExit("no single string %r in the model" % file)
        entry = textures_off + texture * 16
        struct.pack_into("<I", out, entry + 8, found + 2 - entry)
    return bytes(out)


def clone(cpk, files, source, name, recipe, dest):
    skin = load(os.path.join(SOURCE, source + "_SKIN.SGO"))
    base = load(os.path.join(SOURCE, source + ".SGO"))
    archive_path = base.text_at("0.0.0.0")
    archive = cpk.read(files["UI/" + archive_path.split("/")[-1].upper()])
    originals = members(archive)
    textures = {}
    for member, data in originals.items():
        paint = recipe.get(member) or recipe.get("*")
        if member.endswith(".dds") and paint:
            textures[member] = paint(data)
    additions = []
    split = SPLITS.get(name)
    if split:
        additions = [(file, paint(originals[member])) for file, member, paint in split.files.values()]
        model = next(member for member in originals if member.endswith(".mdb"))
        textures[model] = retarget(originals[model], split)
    outputs = [(name.upper() + "_MERGE.RAB", rebuild(archive, textures, additions))]
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
