import _bootstrap  # noqa: F401
import struct
import unittest

import fixtures_priorart as fx
from priorart import (
    FlverError,
    FlverSection,
    HEADER_SIZE,
    SECTION_SIZE,
    SECTION_TABLE_OFFSET,
    parse_flver_gx_block,
    parse_flver_gx_group,
    parse_flver_gx_groups,
    parse_flver_header,
    parse_flver_sections,
    parse_ascii,
    parse_smd,
)


class TestSmdParser(unittest.TestCase):
    def setUp(self):
        self.smd = parse_smd(fx.smd_text())

    def test_nodes(self):
        self.assertEqual([n.name for n in self.smd.nodes], ["Root", "Joint_A", "Joint_B"])
        self.assertEqual([n.parent for n in self.smd.nodes], [-1, 0, 0])

    def test_skeleton(self):
        self.assertEqual(len(self.smd.bones), 3)
        self.assertEqual(self.smd.bones[1].position, (0.0, -1.0, 0.0))

    def test_triangles(self):
        self.assertEqual(self.smd.triangle_count, 1)
        self.assertEqual(self.smd.vertex_count, 3)
        self.assertEqual(self.smd.groups[0][0], "m0_Test")

    def test_vertex_fields_and_links(self):
        vertex = self.smd.groups[0][1][1]
        self.assertEqual(vertex.position, (1.0, 0.0, 0.0))
        self.assertEqual(vertex.normal, (0.0, 0.0, 1.0))
        self.assertEqual(vertex.uv, (1.0, 0.0))
        self.assertEqual(vertex.links, ((1, 1.0),))

    def test_multiple_materials(self):
        smd = parse_smd(fx.smd_text({"m0_A": [(1, 1.0)], "m1_B": [(2, 0.5), (1, 0.5)]}))
        self.assertEqual([name for name, _ in smd.groups], ["m0_A", "m1_B"])
        self.assertEqual(smd.triangle_count, 2)
        self.assertEqual(smd.groups[1][1][0].links, ((2, 0.5), (1, 0.5)))

    def test_repeated_material_line_does_not_split_groups(self):
        # Exporters re-emit the material before every triangle; that must not
        # create thousands of groups.
        text = fx.smd_text({"m0_Test": [(1, 1.0)]})
        lines = text.splitlines()
        out = []
        for line in lines:
            out.append(line)
            if line.strip() == "m0_Test":
                # duplicate the material line right before the next triangle
                out.append("m0_Test")
        smd = parse_smd("\n".join(out) + "\n")
        self.assertEqual(len(smd.groups), 1)
        self.assertEqual(smd.triangle_count, 1)

    def test_material_name_reduction(self):
        from priorart.sourcesmd import material_name

        self.assertEqual(
            material_name("WP_A_1063\\N:\\SPRJ\\data\\tex\\WP_A_1063_a.tif"), "WP_A_1063"
        )
        self.assertEqual(material_name("plain"), "plain")

    def test_obj_export(self):
        obj = self.smd.to_obj(object_name="test")
        self.assertIn("o test", obj)
        self.assertIn("g m0_Test", obj)
        self.assertIn("usemtl m0_Test", obj)
        self.assertEqual(obj.count("\nv "), 3)
        self.assertEqual(obj.count("\nvt "), 3)
        self.assertEqual(obj.count("\nvn "), 3)
        self.assertEqual(obj.count("\nf "), 1)
        # triangles=1 appears in the generated header comment
        self.assertIn("triangles=1", obj)

    def test_bom_and_blank_lines_tolerated(self):
        smd = parse_smd("\ufeff\n" + fx.smd_text().replace("end", "\nend\n"))
        self.assertEqual(smd.triangle_count, 1)


class TestAsciiParser(unittest.TestCase):
    def setUp(self):
        self.mesh = parse_ascii(fx.ascii_text())

    def test_bones(self):
        self.assertEqual([b.name for b in self.mesh.bones], ["Root", "Blade_00"])
        self.assertEqual(self.mesh.bones[0].parent, -1)
        self.assertEqual(self.mesh.bones[1].position, (0.0, -0.5, 0.0))
        self.assertEqual(self.mesh.bones[1].rotation, (0.0, 0.0, 0.05, 0.999))

    def test_mesh_header(self):
        self.assertEqual(len(self.mesh.meshes), 1)
        mesh = self.mesh.meshes[0]
        self.assertEqual(mesh.name, "m0_Test")
        self.assertEqual(mesh.unknown, 2)

    def test_textures(self):
        textures = self.mesh.meshes[0].textures
        self.assertEqual(len(textures), 2)
        self.assertTrue(textures[0].path.endswith("Test_a.tif"))

    def test_vertices_and_faces(self):
        self.assertEqual(self.mesh.vertex_count, 3)
        self.assertEqual(self.mesh.triangle_count, 1)
        vertex = self.mesh.meshes[0].vertices[1]
        self.assertEqual(vertex.position, (1.0, 0.0, 0.0))
        self.assertEqual(vertex.normal, (0.0, 0.0, 1.0))
        self.assertEqual(vertex.color, (255.0, 255.0, 255.0, 255.0))
        self.assertEqual(vertex.uv, (1.0, 0.0))
        self.assertEqual(vertex.bones, (1, 0, 0, 0))
        self.assertEqual(vertex.weights, (1.0, 0.0, 0.0, 0.0))

    def test_line_budget_matches_expected_layout(self):
        # 1 + 2*3 + 1 + 1 + 1 + 1 + 2*2 + 1 + 3*7 + 1 + 1 == 39 non-empty lines
        text = fx.ascii_text()
        non_empty = [ln for ln in text.splitlines() if ln.strip()]
        self.assertEqual(len(non_empty), 39)

    def test_obj_export_shares_vertices(self):
        obj = self.mesh.to_obj(object_name="yamato")
        self.assertIn("o yamato", obj)
        self.assertIn("g m0_Test", obj)
        self.assertEqual(obj.count("\nv "), 3)
        self.assertEqual(obj.count("\nf "), 1)

    def test_truncated_input_raises(self):
        with self.assertRaises(Exception):
            parse_ascii("2\nRoot\n-1\n0 0 0 0 0 0 1\nBlade\n0\n0 -0.5 0 0 0 0.05 0.999\n5\n")


class TestFlverHeader(unittest.TestCase):
    def setUp(self):
        self.header = parse_flver_header(fx.flver_header())

    def test_magic_and_size(self):
        self.assertEqual(self.header.magic, b"FLVER\x00")

    def test_u16_fields_match_real_bytes(self):
        self.assertEqual(self.header.u16_06, 76)
        self.assertEqual(self.header.u16_08, 20)
        self.assertEqual(self.header.u16_0a, 2)

    def test_u32_fields_match_real_bytes(self):
        self.assertEqual(self.header.u32_0c, 61488)
        self.assertEqual(self.header.u32_10, 405520)
        self.assertEqual(self.header.u32_14, 0)
        self.assertEqual(self.header.u32_18, 6)
        self.assertEqual(self.header.u32_1c, 334)
        self.assertEqual(self.header.u32_20, 6)
        self.assertEqual(self.header.u32_24, 12)
        self.assertEqual(self.header.u32_40, 28062)
        self.assertEqual(self.header.u32_44, 28062)
        self.assertEqual(self.header.u32_48, 256)
        self.assertEqual(self.header.u32_4c, 0)
        self.assertEqual(self.header.u32_50, 36)
        self.assertEqual(self.header.u32_54, 10)
        self.assertEqual(self.header.u32_58, 42)

    def test_bbox_floats_match_real_bytes(self):
        self.assertAlmostEqual(self.header.bbox[0], -0.7157, places=4)
        self.assertAlmostEqual(self.header.bbox[1], 0.0, places=4)
        self.assertAlmostEqual(self.header.bbox[2], -0.1980, places=4)
        self.assertAlmostEqual(self.header.bbox[3], 0.7180, places=4)
        self.assertAlmostEqual(self.header.bbox[4], 1.7909, places=4)
        self.assertAlmostEqual(self.header.bbox[5], 0.2405, places=4)

    def test_truncated_input_raises(self):
        with self.assertRaises(FlverError):
            parse_flver_header(b"FLVER\x00")

    def test_bad_magic_raises(self):
        with self.assertRaises(FlverError):
            parse_flver_header(b"XXXX\x00" + b"\x00" * (HEADER_SIZE - 6))


class TestFlverSection(unittest.TestCase):
    def setUp(self):
        self.sections = parse_flver_sections(fx.flver_sections())

    def test_section_count_and_size(self):
        self.assertEqual(len(self.sections), 6)
        self.assertEqual(SECTION_SIZE, 0x20)

    def test_section_fields_match_real_observations(self):
        expected = [
            FlverSection(49600, 49616, 7, 0, 366, 48160, 0, 0),
            FlverSection(49966, 49976, 7, 7, 360, 48400, 1, 0),
            FlverSection(50326, 50338, 7, 14, 362, 48640, 2, 0),
            FlverSection(50688, 50700, 7, 21, 370, 48880, 3, 0),
            FlverSection(51058, 51082, 7, 28, 374, 49120, 4, 0),
            FlverSection(51432, 51442, 7, 35, 334, 49360, 5, 0),
        ]
        self.assertEqual(self.sections, expected)

    def test_section_offsets_start_at_table_offset(self):
        # Each entry is SECTION_SIZE bytes starting at SECTION_TABLE_OFFSET.
        data = fx.flver_sections()
        for index, section in enumerate(self.sections):
            fields = struct.unpack_from("<8I", data, SECTION_TABLE_OFFSET + index * SECTION_SIZE)
            self.assertEqual(FlverSection(*fields), section)

    def test_observed_constants(self):
        # u32_08 == 7, u32_0c == 7 * index, u32_1c == 0 in every entry.
        for index, section in enumerate(self.sections):
            self.assertEqual(section.u32_08, 7)
            self.assertEqual(section.u32_0c, 7 * index)
            self.assertEqual(section.u32_1c, 0)

    def test_truncated_table_raises(self):
        data = bytearray(fx.flver_sections())
        del data[SECTION_TABLE_OFFSET:]  # drop the whole table
        with self.assertRaises(FlverError):
            parse_flver_sections(bytes(data))


class TestFlverGxBlock(unittest.TestCase):
    def setUp(self):
        self.group, self.next_offset = parse_flver_gx_group(fx.flver_gx_group(), 0)

    def test_block_tags_match_real_observation(self):
        self.assertEqual(
            [b.tag for b in self.group.blocks],
            [
                b"GX00",
                b"GX04",
                b"GX20",
                b"GX22",
                b"GX24",
                b"GX26",
                b"GX30",
                struct.pack("<I", 0x7FFFFFFF),
            ],
        )

    def test_block_constant_is_100_everywhere(self):
        self.assertTrue(all(b.constant == 100 for b in self.group.blocks))

    def test_block_sizes_match_real_observation(self):
        self.assertEqual(
            [b.size for b in self.group.blocks], [44, 64, 24, 24, 24, 24, 24, 12]
        )
        self.assertEqual(sum(b.size for b in self.group.blocks), 240)

    def test_group_consumes_exactly_240_bytes(self):
        self.assertEqual(self.next_offset, 240)

    def test_payloads_match_real_bytes(self):
        blocks = self.group.blocks
        self.assertEqual(blocks[0].payload, b"\x00" * 32)   # GX00
        self.assertEqual(blocks[2].payload, b"\x00" * 12)   # GX20
        self.assertEqual(blocks[6].payload, b"\x00" * 12)   # GX30
        self.assertEqual(blocks[7].payload, b"")            # sentinel
        gx04 = (
            b"\x00" * 12
            + struct.pack("<8f", 5.0, 1.0, 0.5, 0.0, 5.0, 0.5, 1.0, 0.0)
            + b"\x00" * 8
        )
        self.assertEqual(blocks[1].payload, gx04)           # GX04

    def test_truncated_header_raises(self):
        with self.assertRaises(FlverError):
            parse_flver_gx_block(b"\x00" * 8, 0)

    def test_size_smaller_than_header_raises(self):
        bad = b"GX00" + struct.pack("<II", 100, 8)  # size 8 < 12-byte header
        with self.assertRaises(FlverError):
            parse_flver_gx_block(bad, 0)

    def test_block_overrun_raises(self):
        bad = b"GX00" + struct.pack("<II", 100, 100)  # claims 100 bytes, has 13
        with self.assertRaises(FlverError):
            parse_flver_gx_block(bad, 0)


class TestFlverGxGroup(unittest.TestCase):
    def test_group_next_offset_lands_on_next_group(self):
        document = fx.flver_gx_document()
        group, next_offset = parse_flver_gx_group(document, 0x200)
        self.assertEqual(next_offset, 0x2F0)
        group2, next_offset2 = parse_flver_gx_group(document, 0x2F0)
        self.assertEqual(group2, group)
        self.assertEqual(next_offset2, 0x3E0)

    def test_group_without_sentinel_raises(self):
        document = bytearray(fx.flver_gx_document())
        # wipe the sentinel tag of the first group
        struct.pack_into("<I", document, 0x200 + 228, 0)
        with self.assertRaises(FlverError):
            parse_flver_gx_group(bytes(document), 0x200)


class TestFlverGxGroups(unittest.TestCase):
    def test_all_sections_resolve_to_groups(self):
        document = fx.flver_gx_document()
        groups = parse_flver_gx_groups(document)
        self.assertEqual(len(groups), 6)
        self.assertTrue(all(g == groups[0] for g in groups))

    def test_section_u32_14_points_at_each_group(self):
        document = fx.flver_gx_document()
        expected_offsets = [0x200, 0x2F0, 0x3E0, 0x200, 0x2F0, 0x3E0]
        groups = parse_flver_gx_groups(document)
        for index, offset in enumerate(expected_offsets):
            group, _ = parse_flver_gx_group(document, offset)
            self.assertEqual(group, groups[index], f"section {index}")


if __name__ == "__main__":
    unittest.main()
