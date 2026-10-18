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


# --- mesh groups: the geometry (E-075) -------------------------------------

GROUP_HEADER = 0x28


def group_record(name, size, flags=0x52, vertex_bytes=187_840, count=155,
                 payload=b""):
    """A MG_<hash>_0 record.

    Layout in the real file: 0x40 record, then a 0x28-byte descriptor, then the
    payload starting at ``descriptor + 0x28``. The record's ``size`` is a little
    longer than the payload, so 0x18 bytes of padding follow it.
    """
    rec = bytearray(RECORD_SIZE)
    struct.pack_into("<HHI", rec, 0, groups.ID_RESOURCE, flags, size)
    rec[8:8 + len(name)] = name.encode("latin-1")

    descriptor = bytearray(meshes.HEADER_SIZE)
    struct.pack_into("<HHIHHIII", descriptor, 0, 0x0D, 1, vertex_bytes, 4, count,
                     32, 0, 0x10000)
    struct.pack_into("<4I", descriptor, 0x18, 3140, 11664, 12912, 14344)
    body = payload or b"\x00" * max(0, size)
    return bytes(rec) + bytes(descriptor) + body + b"\x00" * 0x18


class TestMeshGroups(unittest.TestCase):
    def setUp(self):
        self.name = "MG_4196b97c_0"
        self.data = wad(group_record(self.name, 4096))

    def test_finds_the_group_with_geometry(self):
        found = meshes.find_mesh_groups(self.data)
        self.assertEqual([g.name for g in found], [self.name])
        self.assertEqual(found[0].size, 4096)

    def test_group_hash_and_index_are_parsed(self):
        g = meshes.find_mesh_groups(self.data)[0]
        self.assertEqual(g.hash, "4196b97c")
        self.assertEqual(g.index, 0)

    def test_descriptor_sits_in_the_second_header(self):
        g = meshes.find_mesh_groups(self.data)[0]
        self.assertEqual(g.descriptor, g.offset + RECORD_SIZE)

    def test_header_reads_the_documented_fields(self):
        g = meshes.find_mesh_groups(self.data)[0]
        h = g.header(self.data)
        self.assertEqual(h.ident, 0x0D)
        self.assertEqual(h.flags, 1)
        self.assertEqual(h.vertex_bytes, 187_840)
        self.assertEqual(h.first_count, 155)
        self.assertEqual(h.offsets, (3140, 11664, 12912, 14344))

    def test_vertex_count_is_bytes_over_stride(self):
        g = meshes.find_mesh_groups(self.data)[0]
        self.assertEqual(g.vertex_count(self.data), 187_840 // 20)
        self.assertEqual(g.vertex_count(self.data), 9392)

    def test_zero_size_occurrence_is_skipped(self):
        # A group name also appears with size 0 elsewhere; only the sized record
        # carries geometry.
        empty = bytearray(RECORD_SIZE)
        struct.pack_into("<HHI", empty, 0, groups.ID_RESOURCE, 0, 0)
        empty[8:8 + len(self.name)] = self.name.encode("latin-1")
        data = wad(bytes(empty), group_record(self.name, 4096))
        found = meshes.find_mesh_groups(data)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].size, 4096)

    def test_payload_returns_the_declared_bytes(self):
        g = meshes.find_mesh_groups(self.data)[0]
        self.assertEqual(len(g.payload(self.data)), 4096)

    def test_short_buffer_raises(self):
        with self.assertRaises(meshes.MeshError):
            meshes.parse_group_header(b"\x00" * 4, 0)

    def test_stride_and_sentinel_constants(self):
        self.assertEqual(meshes.VERTEX_STRIDE, 20)
        self.assertEqual(meshes.SKIN_SENTINEL, 0xFFFF)
        self.assertEqual(meshes.HEADER_SIZE, GROUP_HEADER)


class TestVertexBlocks(unittest.TestCase):
    def setUp(self):
        self.name = "MG_3c8ec52_0"
        # 3 vertices, then a separator record
        payload = b""
        for k in range(3):
            payload += struct.pack("<HH4f", 0xFFFF, 0, 1.0 + k, 2.0 + k,
                                   3.0 + k, 4.0 + k)
        payload += struct.pack("<HH4f", 0, 0, 0.0, 0.0, 2147483648.0, 0.0)
        self.data = wad(group_record(self.name, len(payload), vertex_bytes=60,
                                     count=3, payload=payload))

    def test_read_block_parses_records(self):
        g = meshes.find_mesh_groups(self.data)[0]
        verts = meshes.read_block(self.data, g.descriptor + meshes.HEADER_SIZE, 3)
        self.assertEqual(len(verts), 3)
        self.assertEqual(verts[0].skin_index, 0xFFFF)
        self.assertEqual(verts[0].floats, (1.0, 2.0, 3.0, 4.0))
        self.assertEqual(verts[2].position, (3.0, 4.0, 5.0))

    def test_position_is_the_first_three_floats(self):
        v = meshes.Vertex(0, 0, (7.0, 8.0, 9.0, 10.0))
        self.assertEqual(v.position, (7.0, 8.0, 9.0))

    def test_unskinned_sentinel(self):
        self.assertTrue(meshes.Vertex(0xFFFF, 0, (0,) * 4).is_unskinned)
        self.assertFalse(meshes.Vertex(0, 0, (0,) * 4).is_unskinned)

    def test_separator_is_recognised(self):
        self.assertTrue(meshes.Vertex(0, 0, (0.0, 0.0, 2147483648.0, 0.0)).is_separator)
        self.assertFalse(meshes.Vertex(0, 0, (1.0, 2.0, 3.0, 4.0)).is_separator)

    def test_block_is_clean(self):
        g = meshes.find_mesh_groups(self.data)[0]
        verts = meshes.read_block(self.data, g.descriptor + meshes.HEADER_SIZE, 4)
        self.assertTrue(meshes.block_is_clean(verts[:3]))
        self.assertFalse(meshes.block_is_clean(verts))

    def test_block_is_clean_rejects_absurd_values(self):
        self.assertFalse(meshes.block_is_clean(
            [meshes.Vertex(0, 0, (1e30, 0.0, 0.0, 0.0))]))

    def test_first_block_uses_the_declared_count(self):
        g = meshes.find_mesh_groups(self.data)[0]
        self.assertEqual(len(meshes.first_block(self.data, g)), 3)

    def test_bounding_box(self):
        verts = [meshes.Vertex(0, 0, (0.0, 1.0, 2.0, 3.0)),
                 meshes.Vertex(0, 0, (4.0, -1.0, 6.0, 7.0))]
        lo, hi = meshes.bounding_box(verts)
        self.assertEqual(lo, (0.0, -1.0, 2.0, 3.0))
        self.assertEqual(hi, (4.0, 1.0, 6.0, 7.0))

    def test_bounding_box_of_nothing_raises(self):
        with self.assertRaises(meshes.MeshError):
            meshes.bounding_box([])

    def test_read_block_overrun_raises(self):
        g = meshes.find_mesh_groups(self.data)[0]
        with self.assertRaises(meshes.MeshError):
            meshes.read_block(self.data, g.descriptor + meshes.HEADER_SIZE, 10_000)


if __name__ == "__main__":
    unittest.main()
