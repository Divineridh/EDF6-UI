import json
import struct
import sys

TYPE_ARRAY = 0
TYPE_INT = 1
TYPE_FLOAT = 2
TYPE_STRING = 3


class Sgo:
    def __init__(self, data):
        assert data[:4] == b"SGO\x00", data[:4]
        self.d = data
        self.version = self.u(4)
        self.root_count = self.u(8)
        self.root_off = self.u(0x0C)
        self.name_count = self.u(0x10)
        self.name_off = self.u(0x14)
        self.str_base = self.u(0x1C)

    def u(self, o):
        return struct.unpack_from("<I", self.d, o)[0]

    def string_at(self, abs_off):
        e = abs_off
        while e + 1 < len(self.d) and self.d[e:e + 2] != b"\x00\x00":
            e += 2
        return self.d[abs_off:e].decode("utf-16le", "replace")

    def record(self, o):
        t, n, v = struct.unpack_from("<III", self.d, o)
        if t == TYPE_ARRAY:
            return [self.record(o + v + i * 12) for i in range(n)]
        if t == TYPE_INT:
            return v if v < 0x80000000 else v - 0x100000000
        if t == TYPE_FLOAT:
            return round(struct.unpack_from("<f", self.d, o + 8)[0], 4)
        if t == TYPE_STRING:
            return self.string_at(o + v)
        return {"tipo_desconocido": t, "n": n, "v": v}

    def tree(self):
        return [self.record(self.root_off + i * 12) for i in range(self.root_count)]

    def names(self):
        out = {}
        for i in range(self.name_count):
            entry = self.name_off + i * 8
            rel, index = struct.unpack_from("<II", self.d, entry)
            out[index] = self.string_at(entry + rel)
        return out


def dump(node, indent=0, out=sys.stdout, path=""):
    pad = "  " * indent
    if isinstance(node, list):
        head = node[0] if node and isinstance(node[0], str) else ""
        name = node[1] if len(node) > 1 and isinstance(node[1], str) else ""
        scalars = [x for x in node if not isinstance(x, list)]
        kids = [x for x in node if isinstance(x, list)]
        out.write("%s[%s] %s %s\n" % (pad, head, name, scalars[2:] if len(scalars) > 2 else ""))
        for k in kids:
            dump(k, indent + 1, out)
    else:
        out.write("%s%r\n" % (pad, node))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    data = open(sys.argv[1], "rb").read()
    s = Sgo(data)
    tree = s.tree()
    if len(sys.argv) > 2 and sys.argv[2] == "json":
        json.dump(tree, sys.stdout, indent=1, ensure_ascii=False)
    else:
        for n in tree:
            dump(n)
