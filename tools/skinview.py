import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cpk import Cpk
from mdb import Mdb
from rab import members
from sgo import Sgo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6"
CORNER_TARGET = {"LT": (0, 0), "RT": (1, 0), "LB": (0, 1), "RB": (1, 1)}
SIDE_TARGET = {"left": 0, "right": 1}
ERAS = ("base", "B", "C")


def texture_of(mdb, material):
    record = mdb.material_off + material * 32
    ref_off, ref_count = struct.unpack_from("<II", mdb.d, record + 20)
    index = struct.unpack_from("<I", mdb.d, record + ref_off)[0]
    entry = mdb.textures_off + index * 16
    file_rel = struct.unpack_from("<I", mdb.d, entry + 8)[0]
    return mdb.wide(entry + file_rel)


def read_dds(data):
    h, w = struct.unpack_from("<II", data, 12)
    return w, h, data[128:128 + w * h * 4]


class Skin:
    def __init__(self, name, cpk=None):
        self.cpk = cpk or Cpk(os.path.join(GAME, "Root.cpk"))
        files = {e["path"].upper(): e for e in self.cpk.entries()}
        tree = Sgo(open(os.path.join(ROOT, "extract", "UI", name.upper() + "_SKIN.SGO"), "rb").read()).tree()
        base = Sgo(self.cpk.read(files["UI/" + tree[0].split("/")[-1].upper()])).tree()
        archive = base[0][0][0][0]
        self.files = members(self.cpk.read(files["UI/" + archive.split("/")[-1].upper()]))
        mdb_bytes = next(v for k, v in self.files.items() if k.endswith(".mdb"))
        self.mdb = Mdb(mdb_bytes)
        self.mdb.textures_off = struct.unpack_from("<I", mdb_bytes, 0x2C)[0]
        self.design = next(((b["x"], b["y"]) for b in self.mdb.bones if b["name"] == "RB"), None)
        self.textures = {}

    def objects(self, era):
        for obj in self.mdb.objects:
            suffix = obj["name"].rsplit(".", 1)[1].upper() if "." in obj["name"] else "base"
            if suffix == era:
                yield obj

    def texture(self, name):
        key = name.lower()
        if key not in self.textures:
            data = self.files.get(key) or next(v for k, v in self.files.items() if k.startswith(key.split(".")[0]))
            self.textures[key] = read_dds(data)
        return self.textures[key]

    def triangles(self, era, width, height):
        for obj in self.objects(era):
            for mesh in obj["meshes"]:
                tex = self.texture(texture_of(self.mdb, mesh["material"]))
                verts = []
                for v in mesh["vertices"]:
                    x, y = v["position"][0] * 100, v["position"][1] * 100
                    weights = v.get("blendweight", (1.0,))
                    indices = v.get("blendindices", (0,))
                    nx = ny = total = 0.0
                    for i, w in zip(indices, weights):
                        if w <= 0:
                            continue
                        b = self.mdb.bones[i]
                        tx, ty = b["x"], b["y"]
                        if b["name"] in CORNER_TARGET:
                            fx, fy = CORNER_TARGET[b["name"]]
                            tx, ty = fx * width, fy * height
                        elif b["name"].lower() in SIDE_TARGET:
                            tx = SIDE_TARGET[b["name"].lower()] * width
                        nx += w * (x - b["x"] + tx)
                        ny += w * (y - b["y"] + ty)
                        total += w
                    if total:
                        nx, ny = nx / total, ny / total
                    verts.append((nx, ny, v["texcoord"]))
                idx = mesh["indices"]
                for k in range(0, len(idx) - 2, 3):
                    yield tex, verts[idx[k]], verts[idx[k + 1]], verts[idx[k + 2]]


class Canvas:
    def __init__(self, width, height, background):
        self.w, self.h = width, height
        self.px = bytearray(bytes(background) * (width * height))

    def triangle(self, tex, a, b, c, ox, oy, scale):
        tw, th, data = tex
        (x0, y0, t0), (x1, y1, t1), (x2, y2, t2) = [((v[0] + ox) * scale, (v[1] + oy) * scale, v[2]) for v in (a, b, c)]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            return
        minx, maxx = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, self.w)
        miny, maxy = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, self.h)
        px = self.px
        for y in range(miny, maxy):
            cy = y + 0.5
            for x in range(minx, maxx):
                cx = x + 0.5
                w0 = ((x1 - cx) * (y2 - cy) - (x2 - cx) * (y1 - cy)) / area
                w1 = ((x2 - cx) * (y0 - cy) - (x0 - cx) * (y2 - cy)) / area
                w2 = 1 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
                u = w0 * t0[0] + w1 * t1[0] + w2 * t2[0]
                v = w0 * t0[1] + w1 * t1[1] + w2 * t2[1]
                sx = min(max(int(u * tw), 0), tw - 1)
                sy = min(max(int(v * th), 0), th - 1)
                s = (sy * tw + sx) * 4
                alpha = data[s + 3] / 255.0
                if alpha <= 0:
                    continue
                d = (y * self.w + x) * 3
                px[d] = int(data[s + 2] * alpha + px[d] * (1 - alpha))
                px[d + 1] = int(data[s + 1] * alpha + px[d + 1] * (1 - alpha))
                px[d + 2] = int(data[s] * alpha + px[d + 2] * (1 - alpha))

    def outline(self, x, y, w, h, color, scale):
        for i in range(int(x * scale), int((x + w) * scale)):
            for j in (int(y * scale), int((y + h) * scale) - 1):
                if 0 <= i < self.w and 0 <= j < self.h:
                    self.px[(j * self.w + i) * 3:(j * self.w + i) * 3 + 3] = bytes(color)
        for j in range(int(y * scale), int((y + h) * scale)):
            for i in (int(x * scale), int((x + w) * scale) - 1):
                if 0 <= i < self.w and 0 <= j < self.h:
                    self.px[(j * self.w + i) * 3:(j * self.w + i) * 3 + 3] = bytes(color)

    def save(self, path):
        raw = b"".join(b"\x00" + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3]) for y in range(self.h))

        def chunk(t, body):
            return struct.pack(">I", len(body)) + t + body + struct.pack(">I", zlib.crc32(t + body) & 0xFFFFFFFF)

        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
        open(path, "wb").write(png)


def render(skin, era, width, height, path, scale=0.5, margin=60, background=(30, 70, 50)):
    canvas = Canvas(int((width + 2 * margin) * scale), int((height + 2 * margin) * scale), background)
    for tex, a, b, c in skin.triangles(era, width, height):
        canvas.triangle(tex, a, b, c, margin, margin, scale)
    canvas.outline(margin, margin, width, height, (255, 0, 255), scale)
    canvas.save(path)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    name, width, height, dest = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    skin = Skin(name)
    os.makedirs(dest, exist_ok=True)
    for era in ERAS:
        out = os.path.join(dest, "%s_%dx%d_%s.png" % (name, width, height, era))
        render(skin, era, width, height, out)
        print(out)
