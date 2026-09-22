import struct

RECORD_SIZE = 16
TYPE_STRING = 1


class Patcher:
    """Edita un DSGO sin reescribirlo.

    Los strings nuevos se agregan al final del archivo y se re-apunta el
    registro: la tabla de registros no cambia de tamano, asi que ningun offset
    existente se mueve. Misma tecnica que patch.py sobre los layouts SGO.
    """

    def __init__(self, data):
        assert data[:4] == b"DSGO", data[:4]
        self.buf = bytearray(data)
        self.count = struct.unpack_from("<I", self.buf, 8)[0]
        self.table = struct.unpack_from("<I", self.buf, 0x0C)[0]

    def record_offset(self, index):
        return self.table + index * RECORD_SIZE

    def kind(self, index):
        return struct.unpack_from("<I", self.buf, self.record_offset(index) + 8)[0]

    def set_string(self, index, text):
        o = self.record_offset(index)
        if self.kind(index) != TYPE_STRING:
            raise TypeError("el registro %d no es un string" % index)
        self.buf += b"\x00" * ((-len(self.buf)) % 8)
        target = len(self.buf)
        self.buf += text.encode("utf-16le") + b"\x00\x00"
        self.buf += b"\x00" * ((-len(self.buf)) % 8)
        struct.pack_into("<Q", self.buf, o, target - o)
        return target

    def data(self):
        return bytes(self.buf)
