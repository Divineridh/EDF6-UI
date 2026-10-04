import struct
import sys

FORMAT_HALF4 = 7
FORMAT_FLOAT2 = 0xC
FORMAT_FLOAT4 = 1
FORMAT_UBYTE4 = 0x15
BONE_SIZE = 192
MESH_SIZE = 0x28


def half(bits):
    return struct.unpack("<e", struct.pack("<H", bits))[0]


class Mdb:
    def __init__(self, data):
        assert data[:4] == b"MDB0", data[:4]
        self.d = data
        (self.version, name_count, name_off, bone_count, bone_off, object_count, object_off,
         self.material_count, self.material_off, texture_count, texture_off) = struct.unpack_from("<11I", data, 4)
        self.names = [self.wide(name_off + 4 * i + self.u32(name_off + 4 * i)) for i in range(name_count)]
        self.bones = [self.bone(bone_off + i * BONE_SIZE) for i in range(bone_count)]
        self.textures = [self.wide(texture_off + i * 16 + self.u32(texture_off + i * 16 + 4)) for i in range(texture_count)]
        self.objects = [self.object(object_off + i * 16) for i in range(object_count)]

    def u32(self, o):
        return struct.unpack_from("<I", self.d, o)[0]

    def wide(self, o):
        e = o
        while self.d[e:e + 2] != b"\0\0":
            e += 2
        return self.d[o:e].decode("utf-16le", "replace")

    def ascii(self, o):
        return self.d[o:self.d.index(b"\0", o)].decode()

    def bone(self, o):
        index, parent, sibling, child, name = struct.unpack_from("<5i", self.d, o)
        local = struct.unpack_from("<16f", self.d, o + 32)
        return {"index": index, "parent": parent, "name": self.names[name] if 0 <= name < len(self.names) else "",
                "x": local[12] * 100, "y": local[13] * 100}

    def object(self, o):
        name, bone, mesh_count, mesh_off = struct.unpack_from("<4I", self.d, o)
        return {"name": self.names[name] if name < len(self.names) else "", "bone": bone,
                "meshes": [self.mesh(o + mesh_off + k * MESH_SIZE) for k in range(mesh_count)]}

    def mesh(self, m):
        (flags, kind, material, _, attr_off, stride, attr_count, vertex_count, _, vertex_off,
         index_count, index_off) = struct.unpack_from("<HHIIIHHIIIII", self.d, m)
        attrs = []
        for k in range(attr_count):
            a = m + attr_off + k * 16
            fmt, offset, channel, name_off = struct.unpack_from("<4I", self.d, a)
            attrs.append((self.ascii(a + name_off).lower(), fmt, offset))
        vertices = [self.vertex(m + vertex_off + v * stride, attrs) for v in range(vertex_count)]
        indices = list(struct.unpack_from("<%dH" % index_count, self.d, m + index_off))
        return {"material": material, "vertices": vertices, "indices": indices}

    def vertex(self, base, attrs):
        out = {}
        for name, fmt, offset in attrs:
            p = base + offset
            if fmt == FORMAT_HALF4:
                out[name] = tuple(half(x) for x in struct.unpack_from("<4H", self.d, p))
            elif fmt == FORMAT_FLOAT2:
                out[name] = struct.unpack_from("<2f", self.d, p)
            elif fmt == FORMAT_FLOAT4:
                out[name] = struct.unpack_from("<4f", self.d, p)
            elif fmt == FORMAT_UBYTE4:
                out[name] = tuple(self.d[p:p + 4])
        return out

    def bound_vertices(self, obj):
        for mesh in obj["meshes"]:
            for v in mesh["vertices"]:
                weights = v.get("blendweight", (1.0,))
                indices = v.get("blendindices", (0,))
                bones = [self.bones[i] for i, w in zip(indices, weights) if w > 0]
                yield v["position"][0] * 100, v["position"][1] * 100, v["texcoord"], bones


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    mdb = Mdb(open(sys.argv[1], "rb").read())
    print("textures:", mdb.textures)
    for b in mdb.bones:
        print("bone %-28s at (%7.1f, %7.1f)" % (b["name"], b["x"], b["y"]))
    for obj in mdb.objects:
        print("object", obj["name"])
        for x, y, uv, bones in mdb.bound_vertices(obj):
            print("    (%8.1f, %8.1f) uv=(%.3f, %.3f) %s" % (x, y, uv[0], uv[1], "+".join(b["name"] for b in bones)))
