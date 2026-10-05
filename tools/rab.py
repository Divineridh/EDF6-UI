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


def members(data):
    count, table = struct.unpack_from("<II", data, 0x14)
    found = {}
    for i in range(count):
        entry = table + i * 0x20
        name_rel, size, _, _, _, _, offset, _ = struct.unpack_from("<8I", data, entry)
        e = entry + name_rel
        while data[e:e + 2] != b"\0\0":
            e += 2
        name = data[entry + name_rel:e].decode("utf-16le").lower()
        block = data[offset:offset + size]
        if block[:4] == b"CMPL":
            found[name], _ = cmpl(block[8:], struct.unpack_from(">I", block, 4)[0])
        else:
            found[name] = block
    return found


def cmpl_literal(payload):
    out = bytearray(b"CMPL" + struct.pack(">I", len(payload)))
    for i in range(0, len(payload), 8):
        out.append(0xFF)
        out += payload[i:i + 8]
    return bytes(out)


def rebuild(data, replacements):
    count, table = struct.unpack_from("<II", data, 0x14)
    entries = []
    for i in range(count):
        entry = table + i * 0x20
        name_rel, size, _, _, _, _, offset, _ = struct.unpack_from("<8I", data, entry)
        e = entry + name_rel
        while data[e:e + 2] != b"\0\0":
            e += 2
        name = data[entry + name_rel:e].decode("utf-16le").lower()
        entries.append((entry, name, data[offset:offset + size]))
    start = min(struct.unpack_from("<I", data, entry + 24)[0] for entry, _, _ in entries)
    out = bytearray(data[:start])
    biggest_block = biggest_payload = 0
    for entry, name, block in entries:
        if name in replacements:
            block = cmpl_literal(replacements[name])
        payload_size = struct.unpack_from(">I", block, 4)[0] if block[:4] == b"CMPL" else len(block)
        struct.pack_into("<I", out, entry + 4, len(block))
        struct.pack_into("<I", out, entry + 24, len(out))
        out += block
        biggest_block = max(biggest_block, len(block))
        biggest_payload = max(biggest_payload, payload_size)
    struct.pack_into("<II", out, 0x0C, biggest_block, biggest_payload)
    return bytes(out)


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
