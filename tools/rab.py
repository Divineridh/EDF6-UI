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
FOLDER_NAMES = ("MODEL", "TEXTURE")
FOLDER_ORDER = ("TEXTURE", "MODEL")
TEXTURE_FOLDER = FOLDER_ORDER.index("TEXTURE")
HEADER_SIZE = 0x28


def wide(text):
    return text.encode("utf-16le") + b"\0\0"


def stored(data):
    count, table = struct.unpack_from("<II", data, 0x14)
    found = []
    for i in range(count):
        entry = table + i * ENTRY_SIZE
        name_rel, size, folder, _, _, _, offset, _ = struct.unpack_from("<8I", data, entry)
        e = entry + name_rel
        while data[e:e + 2] != b"\0\0":
            e += 2
        found.append((data[entry + name_rel:e].decode("utf-16le"), folder, data[offset:offset + size]))
    return found


def write(archive):
    count = len(archive)
    table = HEADER_SIZE
    index = table + count * ENTRY_SIZE
    folders = index + count * INDEX_SIZE
    strings = folders + 4 * len(FOLDER_ORDER)
    order = sorted(range(count), key=lambda i: archive[i][0])
    text = b""
    string_at = {}
    for string in sorted(set(FOLDER_NAMES) | {name for name, _, _ in archive}):
        string_at[string] = strings + len(text)
        text += wide(string)
    folder_at = {folder: string_at[folder] for folder in FOLDER_NAMES}
    name_at = {i: string_at[archive[i][0]] for i in range(count)}
    data_start = strings + len(text)
    out = bytearray(data_start)
    out[strings:data_start] = text
    for rank, i in enumerate(order):
        record = index + rank * INDEX_SIZE
        struct.pack_into("<II", out, record, name_at[i] - record, i)
    for slot, folder in enumerate(FOLDER_ORDER):
        record = folders + 4 * slot
        struct.pack_into("<I", out, record, folder_at[folder] - record)
    biggest_block = biggest_payload = 0
    for i, (name, folder, block) in enumerate(archive):
        entry = table + i * ENTRY_SIZE
        struct.pack_into("<8I", out, entry, name_at[i] - entry, len(block), folder, 0, 0, 0, len(out), 0)
        out += block
        payload_size = struct.unpack_from(">I", block, 4)[0] if block[:4] == b"CMPL" else len(block)
        biggest_block = max(biggest_block, len(block))
        biggest_payload = max(biggest_payload, payload_size)
    struct.pack_into("<4s9I", out, 0, b"SSA\0", SSA_VERSION, data_start, biggest_block, biggest_payload, count,
                     table, index, len(FOLDER_ORDER), folders)
    return bytes(out)


def rebuild(data, replacements, additions=()):
    archive = []
    for name, folder, block in stored(data):
        if name.lower() in replacements:
            block = cmpl_literal(replacements[name.lower()])
        archive.append((name, folder, block))
    textures = [i for i, (_, folder, _) in enumerate(archive) if folder == TEXTURE_FOLDER]
    insert_at = textures[-1] + 1 if textures else 0
    added = [(name, TEXTURE_FOLDER, cmpl_literal(payload)) for name, payload in additions]
    return write(archive[:insert_at] + added + archive[insert_at:])


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
