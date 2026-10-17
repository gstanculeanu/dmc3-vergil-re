import _bootstrap  # noqa: F401
import unittest

import fixtures_priorart as fx
from priorart import parse_ascii, parse_smd


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


if __name__ == "__main__":
    unittest.main()
