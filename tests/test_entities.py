import _bootstrap  # noqa: F401
import unittest

from dmc3 import entities


class TestEntityMap(unittest.TestCase):
    def test_primary_target_is_vergil(self):
        self.assertEqual(entities.DEFAULT_PLAYER_IDS, ["pl021"])
        self.assertTrue(entities.is_primary_target("pl021"))
        self.assertFalse(entities.is_primary_target("pl000"))

    def test_vergil_is_verified(self):
        entity = entities.lookup("pl021")
        self.assertIsNotNone(entity)
        self.assertEqual(entity.label, "Vergil (playable)")
        self.assertEqual(entity.confidence, "verified")

    def test_dante(self):
        self.assertEqual(entities.label_for("pl000"), "Dante")

    def test_unknown_id_falls_back_to_id(self):
        self.assertEqual(entities.label_for("pl999"), "pl999")

    def test_known_player_ids_are_zero_padded(self):
        for entity_id in entities.KNOWN_PLAYER_IDS:
            self.assertRegex(entity_id, r"^pl\d{3}$")


if __name__ == "__main__":
    unittest.main()
