import _bootstrap  # noqa: F401
import struct
import unittest

from gow3 import groups, meshes
from gow3.meshes import find_mesh_definitions, materials


HEADER = 0x50
RECORD_SIZE = 0x40
ALIGN = 0x10


def sized(name, payload, flags):
    buf = bytearray(RECORD_SIZE)
    struct.pack_into("<HHI", buf, 0, groups.ID_RESOURCE, flags, len(payload))
    buf[8:8 + len(name)] = name.encode("latin-1")
    extra = b"\x00" * RECORD_SIZE if flags else b""
    pad = b"\x00" * ((-len(payload)) % ALIGN)
    return bytes(buf) + extra + payload + pad


def plain(name, ident):
    buf = bytearray(RECORD_SIZE)
    struct.pack_into("<HH", buf, 0, ident, 0)
    buf[8:8 + len(name)] = name.encode("latin-1")
    return bytes(buf)


def wad(*parts):
    return b"\x00" * HEADER + b"".join(parts)


class TestMeshDefinitions(unittest.TestCase):
    def setUp(self):
        self.data = wad(
            plain("GroupStart", groups.GROUP_START),
            sized("MDL_4196b97c", b"M" * 128, 0x52),
            plain("MG_4196b97c_0", groups.ID_RESOURCE),
            sized("MDL_c13cd430", b"M" * 128, 0x52),
            plain("MG_c13cd430_0", groups.ID_RESOURCE),
            plain("GroupEnd", groups.GROUP_END),
        )

    def test_finds_definitions_in_file_order(self):
        defs = find_mesh_definitions(self.data)
        self.assertEqual([d.name for d in defs],
                         ["MDL_4196b97c", "MDL_c13cd430"])

    def test_reads_the_size_and_flags(self):
        first = find_mesh_definitions(self.data)[0]
        self.assertEqual(first.size, 128)
        self.assertEqual(first.flags, 0x52)
        self.assertEqual(first.hash, "4196b97c")

    def test_payload_is_the_declared_128_bytes(self):
        first = find_mesh_definitions(self.data)[0]
        self.assertEqual(len(first.payload(self.data)), 128)

    def test_finds_the_following_mesh_groups(self):
        first = find_mesh_definitions(self.data)[0]
        self.assertEqual(first.groups, ("MG_4196b97c_0",))

    def test_a_name_without_a_record_is_not_a_definition(self):
        data = b"\x00" * HEADER + b"junk MDL_4196b97c junk"
        self.assertEqual(find_mesh_definitions(data), [])

    def test_deduplicates_the_same_name(self):
        data = wad(
            sized("MDL_4196b97c", b"M" * 128, 0x52),
            b"later MDL_4196b97c appears again".ljust(0x80, b"\x00"),
        )
        self.assertEqual(len(find_mesh_definitions(data)), 1)

    def test_no_definitions_is_empty(self):
        self.assertEqual(find_mesh_definitions(b"\x00" * HEADER), [])

    def test_constants_match_what_was_observed(self):
        self.assertEqual(meshes.MESH_FLAGS, 0x52)
        self.assertEqual(meshes.MESH_DEFINITION_SIZE, 128)


class TestMaterials(unittest.TestCase):
    def test_finds_material_names_in_order_and_dedupes(self):
        data = b"MAT_ubershader1\x00MAT_lambert1\x00MAT_ubershader1\x00"
        self.assertEqual(materials(data), ["MAT_ubershader1", "MAT_lambert1"])

    def test_material_name_with_colons(self):
        data = b"MAT_normalmapblood1:lambert2\x00"
        self.assertEqual(materials(data),
                         ["MAT_normalmapblood1:lambert2"])

    def test_no_materials(self):
        self.assertEqual(materials(b"nothing here"), [])


if __name__ == "__main__":
    unittest.main()
