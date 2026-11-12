"""Clean-room pure-stdlib synthetic tests for fx3_recovery wire, linker, and FS bounds."""
from hashlib import sha256
from pathlib import Path
import struct
import sys
import unittest
import zlib

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fx3_recovery import boot_worker as B
from fx3_recovery import capture as C
from fx3_recovery import elflink as L
from fx3_recovery import profiles as P
from fx3_recovery import worker as W
from fx3_recovery.fat import FatP1, MAX_P1
from fx3_recovery.squash import SquashFS, inflate_bounded


class CleanRoomSyntheticRecoveryTests(unittest.TestCase):
    def test_profiles_library_patch_invariants_and_fail_closed_tamper(self):
        self.assertEqual(P.PROFILE, "fx3-p1-reference-v1")
        self.assertEqual(len(P.LIBRARIES), 2)
        for lib_path, spec in P.LIBRARIES.items():
            self.assertTrue(lib_path.startswith("/usr/lib/"))
            self.assertEqual(len(spec["sha256"]), 64)
            for at, before, after, _name in spec["patches"]:
                self.assertEqual(len(bytes.fromhex(before)), len(bytes.fromhex(after)))
                self.assertGreaterEqual(at, 0)
            with self.assertRaises(ValueError):
                P.patched_library(b"\x7fELF\x02\x01" + b"\x00" * 128, spec)

    def test_p1_worker_window_shape_and_request_wire_crc(self):
        cid = "0123456789abcdef0123456789abcdef"
        spans = [C.shape(w) for w in (0, 1, 2)]
        self.assertEqual(spans[0][0], 0)
        self.assertEqual(spans[0][1] + spans[1][1] + spans[2][1], C.CHUNKS)
        self.assertEqual(C.CHUNKS * C.BLOCK, MAX_P1)
        for w in (0, 1, 2):
            req = W.request(cid, w)
            self.assertEqual(len(req), 64)
            self.assertEqual(req[:16], W.REQ)
            crc = struct.unpack_from("<I", req, 52)[0]
            self.assertEqual(crc, zlib.crc32(req[:52]))
        with self.assertRaises(ValueError):
            W.request("0" * 32, 0)
        with self.assertRaises(ValueError):
            W.request(cid, 3)

    def test_boot_worker_geometry_and_request_wire_contract(self):
        cid = "fedcba9876543210fedcba9876543210"
        self.assertEqual(B.geometry(B.UNIT), B.UNIT // B.BLOCK)
        self.assertEqual(B.geometry(4 * 1024 * 1024), (4 * 1024 * 1024) // B.BLOCK)
        with self.assertRaises(ValueError):
            B.geometry(0)
        with self.assertRaises(ValueError):
            B.geometry(B.UNIT + 512)

        req0 = B.request(cid, "boot0", 0, expected_total=0)
        self.assertEqual(len(req0), 128)
        self.assertEqual(req0[:16], B.REQ)
        self.assertEqual(req0[56:88], B.PROFILE)
        self.assertEqual(struct.unpack_from("<I", req0, 124)[0], zlib.crc32(req0[:124]))
        with self.assertRaises(ValueError):
            B.request(cid, "boot1", 1, expected_total=0)

    def test_elflink_aarch64_relocate_all_supported_opcodes_and_bounds(self):
        # 275: R_AARCH64_ADR_PREL_PG_HI21 (ADRP x0, ...)
        adrp = L.relocate(0x90000000, 275, 0x400100, 0x402340)
        self.assertEqual(adrp & 0x9F00001F, 0x90000000)
        with self.assertRaises(ValueError):
            L.relocate(0x90000000, 275, 0x400000, 0x400000 + (1 << 33))

        # 277: R_AARCH64_ADD_ABS_LO12_NC (ADD x0, x0, #lo12)
        add_w = L.relocate(0x91000000, 277, 0x400104, 0x402348)
        self.assertEqual((add_w >> 10) & 0xFFF, 0x348)

        # 286: R_AARCH64_LDST64_ABS_LO12_NC (LDR x0, [x0, #lo12])
        ldr64 = L.relocate(0xF9400000, 286, 0x400108, 0x402348)
        self.assertEqual(((ldr64 >> 10) & 0xFFF) * 8, 0x348)
        with self.assertRaises(ValueError):
            L.relocate(0xF9400000, 286, 0x400108, 0x402344)

        # 299: R_AARCH64_LDST128_ABS_LO12_NC
        ldr128 = L.relocate(0x3DC00000, 299, 0x40010C, 0x402340)
        self.assertEqual(((ldr128 >> 10) & 0xFFF) * 16, 0x340)

        # 283: R_AARCH64_CALL26 (BL target)
        bl_w = L.relocate(0x94000000, 283, 0x400110, 0x400210)
        self.assertEqual(bl_w, 0x94000040)
        with self.assertRaises(ValueError):
            L.relocate(0x94000000, 283, 0x400110, 0x400112)

    def test_fat12_and_squashfs_bounded_parsers_reject_malformed_inputs(self):
        # Valid minimal empty FX3 FAT12 image (boot + 2*FAT(32 sectors) + root(32 sectors) + 4 clusters)
        total_sectors = 1 + 2 * 32 + 32 + 4 * 32
        img = bytearray(total_sectors * 512)
        struct.pack_into("<H", img, 11, 512)
        img[13] = 32
        struct.pack_into("<H", img, 14, 1)
        img[16] = 2
        struct.pack_into("<H", img, 17, 512)
        struct.pack_into("<H", img, 19, total_sectors)
        struct.pack_into("<H", img, 22, 32)
        img[510:512] = b"\x55\xaa"
        fat_p1 = FatP1(bytes(img))
        self.assertEqual(fat_p1.files, {})
        self.assertEqual(fat_p1.clusters, 4)

        # Corrupt second FAT copy -> fail closed
        bad_fat = bytearray(img)
        bad_fat[512 + 32 * 512] ^= 0xFF
        with self.assertRaises(ValueError):
            FatP1(bytes(bad_fat))

        # Bounded zlib inflate enforces exact limit and EOF
        payload = b"clean-room-squashfs-block" * 8
        compressed = zlib.compress(payload)
        self.assertEqual(inflate_bounded(compressed, len(payload)), payload)
        with self.assertRaises(ValueError):
            inflate_bounded(compressed, len(payload) - 1)
        with self.assertRaises(ValueError):
            SquashFS(b"\x00" * 128)


if __name__ == "__main__":
    unittest.main()
