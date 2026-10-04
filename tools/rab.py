import os
import struct
import sys


def cmpl(src, size):
    window = bytearray(4096)
    cursor = 0xFEE
    out = bytearray()
    i = 0
    flags = 0
    while len(out) < size and i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xFF00
            i += 1
        if flags & 1:
            byte = src[i]
            i += 1
            out.append(byte)
            window[cursor] = byte
            cursor = (cursor + 1) & 0xFFF
        else:
            high, low = src[i], src[i + 1]
            i += 2
            offset = (high << 4) | (low >> 4)
            length = (low & 0x0F) + 3
            for k in range(length):
                byte = window[(offset + k) & 0xFFF]
                out.append(byte)
                window[cursor] = byte
                cursor = (cursor + 1) & 0xFFF
    return bytes(out[:size]), i


def entries(data):
    found = []
    p = 0
    while True:
        p = data.find(b"CMPL", p)
        if p < 0:
            return found
        size = struct.unpack_from(">I", data, p + 4)[0]
        payload, used = cmpl(data[p + 8:], size)
        found.append(payload)
        p += 8 + used


def kind(payload):
    if payload[:4] == b"DDS ":
        return "dds"
    if payload[:4] == b"MDB0":
        return "mdb"
    return "bin"


if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    dest = sys.argv[2] if len(sys.argv) > 2 else None
    base = os.path.basename(sys.argv[1])
    for n, payload in enumerate(entries(data)):
        print("%2d %-4s %9d bytes" % (n, kind(payload), len(payload)))
        if dest:
            os.makedirs(dest, exist_ok=True)
            open(os.path.join(dest, "%s.%d.%s" % (base, n, kind(payload))), "wb").write(payload)
