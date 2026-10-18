import _bootstrap  # noqa: F401
import unittest

from gow3 import vocab


def blob(*strings):
    """A synthetic executable body holding the given NUL-terminated strings."""
    return b"\x00".join(s.encode("latin-1") for s in strings) + b"\x00"


class TestStrings(unittest.TestCase):
    def test_reads_printable_runs_with_offsets(self):
        data = b"\x00\x01hello\x00\x00worldwide\x00"
        got = vocab.read_strings(data)
        self.assertEqual([s for _o, s in got], ["hello", "worldwide"])
        self.assertEqual(got[0][0], 2)

    def test_ignores_single_characters(self):
        self.assertEqual(vocab.read_strings(b"a\x00b\x00"), [])


class TestVocabulary(unittest.TestCase):
    def setUp(self):
        self.data = blob(
            "SCR_SetPhase", "SCR_PlayReplace", "SCR_MaterialAnim",
            "PS3_Pos", "PS3_Normal", "PS3_SkinWeights0", "Generic_UV0",
            "PS3_SomeUniformNotAVertex", "hfsmEnemy1", "hfsmReactive",
            "ms::tMove", "MeshProc::RenderMeshes", "FinalizePrims",
            "ANM_%s", "WAD_%s",
        )
        self.vocab = vocab.read_vocabulary(self.data)

    def test_extracts_script_commands(self):
        self.assertIn("SCR_SetPhase", self.vocab.script_commands)
        self.assertIn("SCR_PlayReplace", self.vocab.script_commands)
        self.assertEqual(len(self.vocab.script_commands), 3)

    def test_extracts_hfsm_types(self):
        self.assertEqual(self.vocab.hfsm_types, ["hfsmEnemy1", "hfsmReactive"])

    def test_extracts_engine_class_names(self):
        self.assertEqual(self.vocab.class_names, ["ms::tMove"])

    def test_extracts_mesh_pipeline_names(self):
        self.assertIn("MeshProc::RenderMeshes", self.vocab.mesh_names)
        self.assertIn("FinalizePrims", self.vocab.mesh_names)

    def test_extracts_format_strings(self):
        self.assertIn("ANM_%s", self.vocab.format_strings)
        self.assertIn("WAD_%s", self.vocab.format_strings)

    def test_deduplicates_and_preserves_first_seen_order(self):
        data = blob("SCR_B", "SCR_A", "SCR_B")
        v = vocab.read_vocabulary(data)
        self.assertEqual(v.script_commands, ["SCR_B", "SCR_A"])

    def test_vertex_attributes_keeps_only_real_attributes(self):
        attrs = vocab.vertex_attributes(self.vocab)
        self.assertIn("PS3_Pos", attrs)
        self.assertIn("PS3_SkinWeights0", attrs)
        self.assertIn("Generic_UV0", attrs)
        # a shader uniform starting PS3_ is not a vertex attribute
        self.assertNotIn("PS3_SomeUniformNotAVertex", attrs)

    def test_to_dict_round_trips_the_sections(self):
        as_dict = self.vocab.to_dict()
        self.assertEqual(set(as_dict), {
            "script_commands", "vertex_semantics", "mesh_names", "hfsm_types",
            "class_names", "format_strings"})
        self.assertEqual(as_dict["hfsm_types"], self.vocab.hfsm_types)

    def test_vertex_semantics_constant_covers_the_known_attributes(self):
        for name in ("PS3_Pos", "PS3_Normal", "PS3_Tangent", "PS3_BiTangent",
                     "PS3_SkinIndices0", "PS3_SkinIndices1",
                     "PS3_SkinningFlipFactor", "Generic_UV5"):
            self.assertIn(name, vocab.VERTEX_SEMANTICS)

    def test_mesh_types_constant(self):
        self.assertIn("Skinned", vocab.MESH_TYPES)

    def test_empty_input_is_safe(self):
        v = vocab.read_vocabulary(b"")
        self.assertEqual(v.script_commands, [])
        self.assertEqual(vocab.vertex_attributes(v), [])


if __name__ == "__main__":
    unittest.main()
