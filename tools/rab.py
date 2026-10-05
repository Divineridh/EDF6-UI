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


SSA_VERSION = 0x110
ENTRY_SIZE = 0x20
INDEX_SIZE = 8
HEADER_SIZE = 0x28
TEXTURE = "TEXTURE"
NO_EXTRA = (0, 0, 0, 0)


def wide(text):
    return text.encode("utf-16le") + b"\0\0"


def read_wide(data, offset):
    end = offset
    while data[end:end + 2] != b"\0\0":
        end += 2
    return data[offset:end].decode("utf-16le")


def stored(data):
    count, table = struct.unpack_from("<II", data, 0x14)
    found = []
    for i in range(count):
        entry = table + i * ENTRY_SIZE
        name_rel, size, folder, extra0, extra1, extra2, offset, extra3 = struct.unpack_from("<8I", data, entry)
        found.append((read_wide(data, entry + name_rel), folder, data[offset:offset + size],
                      (extra0, extra1, extra2, extra3)))
    return found


def folders(data):
    count, table = struct.unpack_from("<II", data, 0x20)
    return [read_wide(data, table + 4 * i + struct.unpack_from("<I", data, table + 4 * i)[0]) for i in range(count)]


def write(archive, folder_names):
    count = len(archive)
    table = HEADER_SIZE
    index = table + count * ENTRY_SIZE
    folder_table = index + count * INDEX_SIZE
    strings = folder_table + 4 * len(folder_names)
    order = sorted(range(count), key=lambda i: archive[i][0])
    text = b""
    string_at = {}
    for string in sorted(set(folder_names) | {member[0] for member in archive}):
        string_at[string] = strings + len(text)
        text += wide(string)
    data_start = strings + len(text)
    out = bytearray(data_start)
    out[strings:data_start] = text
    for rank, i in enumerate(order):
        record = index + rank * INDEX_SIZE
        struct.pack_into("<II", out, record, string_at[archive[i][0]] - record, i)
    for slot, folder in enumerate(folder_names):
        record = folder_table + 4 * slot
        struct.pack_into("<I", out, record, string_at[folder] - record)
    biggest_block = biggest_payload = 0
    for i, (name, folder, block, extra) in enumerate(archive):
        entry = table + i * ENTRY_SIZE
        struct.pack_into("<8I", out, entry, string_at[name] - entry, len(block), folder, extra[0], extra[1], extra[2],
                         len(out), extra[3])
        out += block
        payload_size = struct.unpack_from(">I", block, 4)[0] if block[:4] == b"CMPL" else len(block)
        biggest_block = max(biggest_block, len(block))
        biggest_payload = max(biggest_payload, payload_size)
    struct.pack_into("<4s9I", out, 0, b"SSA\0", SSA_VERSION, data_start, biggest_block, biggest_payload, count,
                     table, index, len(folder_names), folder_table)
    return bytes(out)


def rebuild(data, replacements, additions=()):
    folder_names = folders(data)
    archive = []
    for name, folder, block, extra in stored(data):
        if name.lower() in replacements:
            block = cmpl_literal(replacements[name.lower()])
        archive.append((name, folder, block, extra))
    if additions:
        texture_folder = folder_names.index(TEXTURE)
        textures = [i for i, member in enumerate(archive) if member[1] == texture_folder]
        insert_at = textures[-1] + 1 if textures else 0
        added = [(name, texture_folder, cmpl_literal(payload), NO_EXTRA) for name, payload in additions]
        archive = archive[:insert_at] + added + archive[insert_at:]
    return write(archive, folder_names)


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
