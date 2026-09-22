import json
import struct
import sys

TYPE_DOUBLE = 0
TYPE_STRING = 1
TYPE_INT = 2
TYPE_ARRAY = 3

RECORD_SIZE = 16
ARRAY_DATA_OFFSET = 16


class Dsgo:
    def __init__(self, data):
        assert data[:4] == b"DSGO", data[:4]
        self.d = data
        self.root_count = struct.unpack_from("<I", data, 8)[0]
        self.root_off = struct.unpack_from("<I", data, 0x0C)[0]

    def string_at(self, o):
        e = o
        while e + 1 < len(self.d) and self.d[e:e + 2] != b"\x00\x00":
            e += 2
        return self.d[o:e].decode("utf-16le", "replace")

    def record_offset(self, index):
        return self.root_off + index * RECORD_SIZE

    def kind(self, index):
        return struct.unpack_from("<I", self.d, self.record_offset(index) + 8)[0]

    def children(self, index):
        o = self.record_offset(index)
        value = struct.unpack_from("<Q", self.d, o)[0]
        table = o + value
        count = struct.unpack_from("<I", self.d, table + 12)[0]
        return struct.unpack_from("<%dI" % count, self.d, table + ARRAY_DATA_OFFSET)

    def record(self, index, seen=()):
        o = self.record_offset(index)
        value, kind, _ = struct.unpack_from("<QII", self.d, o)

        if kind == TYPE_DOUBLE:
            return struct.unpack_from("<d", self.d, o)[0]
        if kind == TYPE_STRING:
            return self.string_at(o + value)
        if kind == TYPE_INT:
            return value if value < 0x8000000000000000 else value - 0x10000000000000000
        if kind == TYPE_ARRAY:
            if index in seen:
                return {"ciclo": index}
            return [self.record(child, seen + (index,)) for child in self.children(index)]
        return {"tipo_desconocido": kind, "valor": value}

    def tree(self):
        return [self.record(i) for i in range(self.root_count)]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    doc = Dsgo(open(sys.argv[1], "rb").read())
    target = sys.argv[2] if len(sys.argv) > 2 else "json"
    node = doc.tree() if target == "json" else doc.record(int(target))
    json.dump(node, sys.stdout, indent=1, ensure_ascii=False)
