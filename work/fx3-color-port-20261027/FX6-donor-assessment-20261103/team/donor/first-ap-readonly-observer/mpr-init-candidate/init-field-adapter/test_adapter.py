"""Host 反例；不执行原 ELF/VM。"""
import struct
import unittest

from init_adapter import Rejected, convert_for_guest, project
from replay import genuine


class TestProjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = genuine()

    def mutated(self, offset, fmt, value):
        b = bytearray(self.raw)
        struct.pack_into(fmt, b, offset, value)
        return bytes(b)

    def test_genuine_count_and_four_slots(self):
        p = project(self.raw)
        self.assertEqual(p.count, 2)
        self.assertEqual(p.slots, (0x1000, 0x1010, 0, 0))
        self.assertEqual(p.msidconv_values, (0x1000, 0x1010, 0xffff, 0xffff))
        self.assertEqual(p.status_active, (True, True, True, True))
        self.assertEqual(p.movie_values, (0x1000, 0x1010))
        self.assertEqual(p.scalar_fields["source_u16"], 1440)
        self.assertIsNone(p.preview_0x1f8)
        self.assertIn("writer_mode_unobserved;u16_1440_to_780_not_authorized", p.rejected)

    def test_callback_nonnull_not_zeroed(self):
        p = project(self.raw)
        self.assertEqual(sum(not r["source_null"] for r in p.callback_rows), 46)
        self.assertEqual(len(p.fx6_extra_nonnull), 10)
        self.assertTrue(any("callback_requires_guest_binding" in r for r in p.rejected))

    def test_count_five_rejected(self):
        p = project(self.mutated(0x268, "<I", 5))
        self.assertIn("count_outside_verified_1_to_4:5", p.rejected)

    def test_active_sentinel_rejected(self):
        p = project(self.mutated(0x26c, "<I", 0xffff))
        self.assertIn("active_slot_is_ffff_sentinel", p.rejected)

    def test_duplicate_id_rejected(self):
        p = project(self.mutated(0x270, "<I", 0x1000))
        self.assertIn("duplicate_active_slot_id", p.rejected)

    def test_invalid_input_rejected(self):
        for b in (self.raw[:-1], bytearray(self.raw)):
            with self.assertRaises(Rejected):
                project(b)

    def test_mxf_not_portable(self):
        p = project(self.raw, writer_mode="fx6_mxf", mode_source="symbolic_fixture")
        self.assertIsNone(p.preview_0x1f8)
        self.assertTrue(any(s.startswith("writer_mode_not_portable") for s in p.rejected))

    def test_xavcs_fixture_still_guest_rejected(self):
        p = project(self.raw, writer_mode="fx6_xavcs", mode_source="symbolic_fixture")
        self.assertEqual(len(p.preview_0x1f8), 0x1f8)
        self.assertEqual(struct.unpack_from("<I", p.preview_0x1f8, 0x1d0)[0], 2)
        self.assertEqual(struct.unpack_from("<4I", p.preview_0x1f8, 0x1d4), (0x1000, 0x1010, 0, 0))
        self.assertEqual(struct.unpack_from("<H", p.preview_0x1f8, 0x1f2)[0], 780)
        with self.assertRaisesRegex(Rejected, "writer_mode_is_fixture_not_natural"):
            convert_for_guest(self.raw, writer_mode="fx6_xavcs", mode_source="symbolic_fixture")

    def test_unsupported_callback_still_rejected_with_mode(self):
        with self.assertRaisesRegex(Rejected, "callback_requires_guest_binding"):
            convert_for_guest(self.raw, writer_mode="fx6_xavcs", mode_source="verified_movie_mode_observation")


if __name__ == "__main__":
    unittest.main(verbosity=2)
