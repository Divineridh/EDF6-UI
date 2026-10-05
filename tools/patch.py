import struct
import sys

from sgo import Sgo

TYPE_ARRAY = 0
TYPE_INT = 1
TYPE_FLOAT = 2
TYPE_STRING = 3


class Editable(Sgo):
    def slots(self):
        found = []
        for i in range(self.root_count):
            self._walk(self.root_off + i * 12, str(i), found)
        return found

    def _walk(self, o, path, found):
        t, n, v = struct.unpack_from("<III", self.d, o)
        if t == TYPE_ARRAY:
            for i in range(n):
                self._walk(o + v + i * 12, "%s.%d" % (path, i), found)
        elif t == TYPE_FLOAT:
            found.append((path, o + 8, struct.unpack_from("<f", self.d, o + 8)[0], "float"))
        elif t == TYPE_INT:
            found.append((path, o + 8, v, "int"))
        elif t == TYPE_STRING:
            found.append((path, o + v, self.string_at(o + v), "str"))

    def str_slots(self):
        found = []
        for i in range(self.root_count):
            self._walk_str(self.root_off + i * 12, str(i), found)
        return found

    def _walk_str(self, o, path, found):
        t, n, v = struct.unpack_from("<III", self.d, o)
        if t == TYPE_ARRAY:
            for i in range(n):
                self._walk_str(o + v + i * 12, "%s.%d" % (path, i), found)
        elif t == TYPE_STRING:
            found.append((path, o, self.string_at(o + v)))

    def table(self):
        out = {}
        p = self.str_base
        while p < len(self.d) - 2:
            e = p
            while e + 1 < len(self.d) and self.d[e:e + 2] != b"\x00\x00":
                e += 2
            out[self.d[p:e].decode("utf-16le", "replace")] = p
            p = e + 2
        return out

    def text_at(self, path):
        for p, rec, old in self.str_slots():
            if p == path:
                return old
        raise KeyError(path)

    def append(self, text):
        target = len(self.buf)
        self.buf += text.encode("utf-16le") + b"\x00\x00"
        self.d = bytes(self.buf)
        return target

    def repoint(self, path, text, add=False):
        target = self.table().get(text)
        if target is None and add:
            target = self.append(text)
        if target is None:
            raise KeyError("that string isn't in the file's table: " + text)
        for p, rec, old in self.str_slots():
            if p == path:
                struct.pack_into("<II", self.buf, rec + 4, len(text), target - rec)
                return old
        raise KeyError(path)

    def set(self, path, value):
        for p, off, old, kind in self.slots():
            if p == path:
                if kind == "float":
                    struct.pack_into("<f", self.buf, off, float(value))
                elif kind == "int":
                    struct.pack_into("<I", self.buf, off, int(value))
                else:
                    raise ValueError("can't rewrite a string in place: " + path)
                return old
        raise KeyError(path)


def load(path):
    data = bytearray(open(path, "rb").read())
    e = Editable(bytes(data))
    e.buf = data
    return e


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    src = sys.argv[1]
    cmd = sys.argv[2]
    e = load(src)
    if cmd == "slots":
        needle = sys.argv[3] if len(sys.argv) > 3 else ""
        for p, off, val, kind in e.slots():
            if needle in p:
                print("%-16s @%-8s %-6s %s" % (p, hex(off), kind, val))
    elif cmd == "strings":
        for text in sorted(e.table()):
            print(text)
    elif cmd == "set":
        dest = sys.argv[-1]
        for assign in sys.argv[3:-1]:
            path, value = assign.split("=", 1)
            if value.startswith("@"):
                old = e.repoint(path, value[1:])
            else:
                old = e.set(path, value)
            print("%-14s %s -> %s" % (path, old, value))
        open(dest, "wb").write(bytes(e.buf))
        print("wrote", dest, len(e.buf), "bytes")
