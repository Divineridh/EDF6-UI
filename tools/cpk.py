import io
import os
import struct
import sys

TYPES = {
    0: ("B", 1), 1: ("b", 1), 2: ("H", 2), 3: ("h", 2),
    4: ("I", 4), 5: ("i", 4), 6: ("Q", 8), 7: ("q", 8),
    8: ("f", 4), 9: ("d", 8),
}


def unmask(data):
    if data[:4] == b"@UTF":
        return data
    n = len(data)
    ks = bytearray(n)
    m = 0x655F
    t = 0x4115
    for i in range(n):
        ks[i] = m & 0xFF
        m = (m * t) & 0xFFFFFFFF
    x = int.from_bytes(data, "big") ^ int.from_bytes(ks, "big")
    return x.to_bytes(n, "big")


class Utf:
    def __init__(self, blob):
        blob = unmask(blob)
        assert blob[:4] == b"@UTF", blob[:4]
        size = struct.unpack_from(">I", blob, 4)[0]
        body = blob[8:8 + size]
        (rows_off, strings_off, data_off, name_off,
         col_count, row_len, row_count) = struct.unpack_from(">IIIIHHI", body, 0)
        strings = body[strings_off:data_off]

        def s(off):
            end = strings.index(b"\x00", off)
            return strings[off:end].decode("utf-8", "replace")

        self.name = s(name_off)
        self.rows = []
        cols = []
        p = 24
        for _ in range(col_count):
            flags = body[p]; p += 1
            nameoff = struct.unpack_from(">I", body, p)[0]; p += 4
            cname = s(nameoff)
            const = None
            storage = flags & 0xF0
            typ = flags & 0x0F
            if storage == 0x30:
                const, p = self._read(body, p, typ, strings, data_off)
            cols.append((cname, typ, storage, const))

        for r in range(row_count):
            p = rows_off + r * row_len
            row = {}
            for cname, typ, storage, const in cols:
                if storage == 0x10:
                    row[cname] = None
                elif storage == 0x30:
                    row[cname] = const
                else:
                    row[cname], p = self._read(body, p, typ, strings, data_off)
            self.rows.append(row)

    @staticmethod
    def _read(body, p, typ, strings, data_off):
        if typ in TYPES:
            fmt, n = TYPES[typ]
            v = struct.unpack_from(">" + fmt, body, p)[0]
            return v, p + n
        if typ == 0x0A:
            off = struct.unpack_from(">I", body, p)[0]
            end = strings.index(b"\x00", off)
            return strings[off:end].decode("utf-8", "replace"), p + 4
        if typ == 0x0B:
            off, ln = struct.unpack_from(">II", body, p)
            return body[data_off + off:data_off + off + ln], p + 8
        raise ValueError("unknown type %x" % typ)


def crilayla(data):
    assert data[:8] == b"CRILAYLA"
    uncsize, header_off = struct.unpack_from("<II", data, 8)
    out = bytearray(uncsize + 0x100)
    out[0:0x100] = data[16 + header_off:16 + header_off + 0x100]

    pos = 16 + header_off - 1
    pool = 0
    left = 0

    def bits(n):
        nonlocal pos, pool, left
        v = 0
        got = 0
        while got < n:
            if left == 0:
                pool = data[pos]
                left = 8
                pos -= 1
            take = min(left, n - got)
            v = (v << take) | ((pool >> (left - take)) & ((1 << take) - 1))
            left -= take
            got += take
        return v

    end = 0x100 + uncsize - 1
    written = 0
    while written < uncsize:
        if bits(1):
            ref = end - written + bits(13) + 3
            ln = 3
            level = None
            for w in (2, 3, 5, 8):
                level = bits(w)
                ln += level
                if level != (1 << w) - 1:
                    break
            else:
                while level == 255:
                    level = bits(8)
                    ln += level
            for _ in range(ln):
                out[end - written] = out[ref]
                ref -= 1
                written += 1
        else:
            out[end - written] = bits(8)
            written += 1
    return bytes(out)


class Cpk:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        assert self.f.read(4) == b"CPK "
        magic, blob = self._section(0)
        head = Utf(blob).rows[0]
        self.head = head
        toc_off = head.get("TocOffset") or 0
        content_off = head.get("ContentOffset") or 0
        self.base = min(toc_off, content_off) if content_off else toc_off
        magic, blob = self._section(toc_off)
        assert magic == b"TOC ", magic
        self.toc = Utf(blob).rows

    def _section(self, off):
        self.f.seek(off)
        header = self.f.read(0x10)
        magic = header[:4]
        size = struct.unpack_from("<Q", header, 8)[0]
        self.f.seek(off + 0x10)
        return magic, self.f.read(size)

    def entries(self):
        for r in self.toc:
            d = r.get("DirName") or ""
            n = r.get("FileName") or ""
            yield {
                "dir": d,
                "name": n,
                "path": (d + "/" + n) if d else n,
                "size": r.get("FileSize") or 0,
                "extract": r.get("ExtractSize") or 0,
                "offset": (r.get("FileOffset") or 0) + self.base,
            }

    def read(self, e):
        self.f.seek(e["offset"])
        raw = self.f.read(e["size"])
        if e["extract"] > e["size"] and raw[:8] == b"CRILAYLA":
            return crilayla(raw)
        return raw


if __name__ == "__main__":
    cmd = sys.argv[1]
    cpk = Cpk(sys.argv[2])
    if cmd == "dirs":
        agg = {}
        for e in cpk.entries():
            a = agg.setdefault(e["dir"], [0, 0])
            a[0] += 1
            a[1] += e["extract"]
        for d in sorted(agg):
            print("%-60s %6d files %12d bytes" % (d, agg[d][0], agg[d][1]))
        print("TOTAL entries:", sum(a[0] for a in agg.values()))
    elif cmd == "list":
        pat = sys.argv[3].lower()
        for e in cpk.entries():
            if pat in e["path"].lower():
                print("%12d %12d  %s" % (e["size"], e["extract"], e["path"]))
    elif cmd == "extract":
        pats = [p for p in sys.argv[3].lower().split("&") if p]
        dest = sys.argv[4]
        n = 0
        for e in cpk.entries():
            if all(p in e["path"].lower() for p in pats):
                out = os.path.join(dest, e["path"].replace("/", os.sep))
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, "wb") as fh:
                    fh.write(cpk.read(e))
                n += 1
        print("extracted", n)
