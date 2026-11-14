#!/usr/bin/env python3
"""Phase 29 Test Suite — Software GPE Compositor & `virtual-rom-v1` Bluetooth HCI H4 Emulator.

Exercises 25 unit & integration tests across BOTH Local Donor (`O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic modes, strictly offline and hardware-free.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import os
import struct
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import soft_gpe_and_bt_rom_emulator as emu  # noqa: E402


class TestSoftGpeRasterAndSpriteEngine(unittest.TestCase):
    """Part A: Software GPE, pixel formats, `fx6_px` parity, 9-patch, LDEC/UXC, and `HOSDAP02` `ramfb`."""

    def test_01_fx6_px_rb_channel_parity(self) -> None:
        # Pure Red: r=0xFF, g=0x00, b=0x00, a=0xFF -> 0xFFFF0000 ([00, 00, FF, FF] LE)
        red = emu.fx6_px(0xFF, 0x00, 0x00, 0xFF)
        self.assertEqual(red, 0xFFFF0000)
        self.assertEqual(struct.pack("<I", red), b"\x00\x00\xFF\xFF")
        # Pure Blue: r=0x00, g=0x00, b=0xFF, a=0xFF -> 0xFF0000FF ([FF, 00, 00, FF] LE)
        blue = emu.fx6_px(0x00, 0x00, 0xFF, 0xFF)
        self.assertEqual(blue, 0xFF0000FF)
        self.assertEqual(struct.pack("<I", blue), b"\xFF\x00\x00\xFF")
        # Cinema Line Amber: r=0xF0, g=0x80, b=0x18, a=0xFF -> 0xFFF08018
        amber = emu.fx6_px(0xF0, 0x80, 0x18, 0xFF)
        self.assertEqual(amber, 0xFFF08018)
        self.assertEqual(emu.unpack_argb8888(amber), (0xF0, 0x80, 0x18, 0xFF))

    def test_02_rgba4444_and_argb4444_nibble_expansion_parity(self) -> None:
        vectors_rgba4444 = (
            (0x0000, 0x00000000),
            (0xFFFF, 0xFFFFFFFF),
            (0xF00F, 0xFFFF0000),
            (0x0F0F, 0xFF00FF00),
            (0x00FF, 0xFF0000FF),
            (0xA538, 0x88AA5533),
        )
        for pv, expected in vectors_rgba4444:
            got = emu.rgba4444_to_argb8888(pv)
            self.assertEqual(got, expected)
            self.assertEqual(emu.argb8888_to_rgba4444(got), pv)

        vectors_argb4444 = (
            (0x0000, 0x00000000),
            (0xFFFF, 0xFFFFFFFF),
            (0xFF00, 0xFFFF0000),
            (0xF0F0, 0xFF00FF00),
            (0xF00F, 0xFF0000FF),
            (0x8A53, 0x88AA5533),
        )
        for pv, expected in vectors_argb4444:
            got = emu.argb4444_to_argb8888(pv)
            self.assertEqual(got, expected)
            self.assertEqual(emu.argb8888_to_argb4444(got), pv)

    def test_03_porter_duff_src_over_and_src_copy_arithmetic(self) -> None:
        # sa=0 preserves destination
        self.assertEqual(emu.porter_duff_src_over(255, 0, 0, 0, 10, 20, 30, 255), (10, 20, 30, 255))
        # sa=255 replaces destination
        self.assertEqual(emu.porter_duff_src_over(200, 100, 50, 255, 10, 20, 30, 128), (200, 100, 50, 255))
        # Translucent blend matching libgrm-fbinit25-542.c integer formula
        r, g, b, a = emu.porter_duff_src_over(255, 0, 0, 128, 0, 0, 255, 255)
        self.assertEqual((r, g, b, a), ((255 * 128) // 255, 0, (255 * 127) // 255, 128 + 127))

    def test_04_grm_fillrect_clipping_and_const_alpha_blending(self) -> None:
        eng = emu.SoftGpeEngine(32, 16)
        # Opaque background fill with clipping beyond right/bottom
        written = eng.grm_fillrect(-4, -2, 40, 20, 0x10, 0x20, 0x30, 0xFF)
        self.assertEqual(written, 32 * 16)
        self.assertEqual(eng.gpe0.read_argb32(0, 0), 0xFF102030)
        self.assertEqual(eng.gpe0.read_argb32(31, 15), 0xFF102030)

        # Translucent fill via BLEND_SRC_OVER_CONST_ALPHA (blend_mode=2)
        eng.grm_fillrect(4, 4, 8, 8, 0xF0, 0x80, 0x18, 0xFF, blend_mode=emu.BLEND_SRC_OVER_CONST_ALPHA, const_alpha=0x80)
        blended = eng.gpe0.read_argb32(6, 6)
        exp_r, exp_g, exp_b, exp_a = emu.porter_duff_src_over(0xF0, 0x80, 0x18, 0x80, 0x10, 0x20, 0x30, 0xFF)
        self.assertEqual(blended, emu.fx6_px(exp_r, exp_g, exp_b, exp_a))
        # Outside fill rect remains background
        self.assertEqual(eng.gpe0.read_argb32(3, 4), 0xFF102030)

    def test_05_grm_rectblit_across_all_four_pixel_formats(self) -> None:
        eng = emu.SoftGpeEngine(32, 16)
        eng.grm_fillrect(0, 0, 32, 16, 0x10, 0x20, 0x30, 0xFF)

        # 1. RGBA4444 (0xF00F = Red, 0x0F0F = Green)
        s_rgba4444 = emu.GpeSurface(2, 1, emu.PIXEL_FMT_RGBA4444, raw_bytes=struct.pack("<2H", 0xF00F, 0x0F0F))
        eng.grm_rectblit(s_rgba4444, (0, 0, 2, 1), (0, 0, 2, 1))
        self.assertEqual(eng.gpe0.read_argb32(0, 0), 0xFFFF0000)
        self.assertEqual(eng.gpe0.read_argb32(1, 0), 0xFF00FF00)

        # 2. ARGB4444 (0xF00F = Blue, 0xFF80 = Red+half-green)
        s_argb4444 = emu.GpeSurface(2, 1, emu.PIXEL_FMT_ARGB4444, raw_bytes=struct.pack("<2H", 0xF00F, 0xFF80))
        eng.grm_rectblit(s_argb4444, (0, 0, 2, 1), (4, 0, 2, 1))
        self.assertEqual(eng.gpe0.read_argb32(4, 0), 0xFF0000FF)
        self.assertEqual(eng.gpe0.read_argb32(5, 0), 0xFFFF8800)

        # 3. RGBA8888 ([R, G, B, A])
        s_rgba8888 = emu.GpeSurface(1, 1, emu.PIXEL_FMT_RGBA8888, raw_bytes=bytes((0xAA, 0xBB, 0xCC, 0xFF)))
        eng.grm_rectblit(s_rgba8888, (0, 0, 1, 1), (8, 0, 1, 1))
        self.assertEqual(eng.gpe0.read_argb32(8, 0), 0xFFAABBCC)

        # 4. A8 glyph mask with COLOR_MOD_TINT (0x0E) + dual const_alpha
        s_a8 = emu.GpeSurface(2, 1, emu.PIXEL_FMT_A8, raw_bytes=bytes((0xFF, 0x00)))
        eng.grm_rectblit(
            s_a8,
            (0, 0, 2, 1),
            (12, 0, 2, 1),
            color_mod=emu.COLOR_MOD_TINT,
            tint_rgb=(0xEE, 0xEE, 0xEE),
        )
        self.assertEqual(eng.gpe0.read_argb32(12, 0), 0xFFEEEEEE)
        self.assertEqual(eng.gpe0.read_argb32(13, 0), 0xFF102030)

        # 5. SRC_COPY (blend_mode=1) overwrites even with sa=0
        eng.grm_rectblit(s_a8, (1, 0, 1, 1), (14, 0, 1, 1), blend_mode=emu.BLEND_SRC_COPY, tint_rgb=(0x11, 0x22, 0x33))
        self.assertEqual(eng.gpe0.read_argb32(14, 0), 0x00112233)

    def test_06_grm_rectblit_stretch_scaling_and_scissor_clip(self) -> None:
        eng = emu.SoftGpeEngine(32, 32)
        src = emu.GpeSurface(2, 2, emu.PIXEL_FMT_RGBA8888, raw_bytes=bytes((
            0xFF, 0x00, 0x00, 0xFF,  0x00, 0xFF, 0x00, 0xFF,
            0x00, 0x00, 0xFF, 0xFF,  0xFF, 0xFF, 0x00, 0xFF,
        )))
        # Stretch 2x2 -> 8x8 at (4, 4), clipped to (6, 4, 4, 8)
        eng.grm_rectblit(src, (0, 0, 2, 2), (4, 4, 8, 8), clip_rect=(6, 4, 4, 8))
        # Outside clip_rect left side stays 0
        self.assertEqual(eng.gpe0.read_argb32(5, 5), 0)
        # Inside top-left quadrant (clipped x=6..7) is Red
        self.assertEqual(eng.gpe0.read_argb32(6, 5), 0xFFFF0000)
        # Inside top-right quadrant (x=8..9) is Green
        self.assertEqual(eng.gpe0.read_argb32(8, 5), 0xFF00FF00)
        # Inside bottom-right quadrant (x=8..9, y=8..11) is Yellow
        self.assertEqual(eng.gpe0.read_argb32(8, 9), 0xFFFFFF00)
        # Outside clip_rect right side stays 0
        self.assertEqual(eng.gpe0.read_argb32(10, 9), 0)

    def test_07_grm_nine_patch_blit_preserves_corners_and_stretches_center(self) -> None:
        eng = emu.SoftGpeEngine(64, 64)
        # Build a 6x6 RGBA8888 9-patch (insets 2,2,2,2): white border, blue center
        src = emu.GpeSurface(6, 6, emu.PIXEL_FMT_RGBA8888)
        for y in range(6):
            for x in range(6):
                if x < 2 or x >= 4 or y < 2 or y >= 4:
                    src.write_rgba(x, y, 0xFF, 0xFF, 0xFF, 0xFF)
                else:
                    src.write_rgba(x, y, 0x20, 0x60, 0xE0, 0xFF)
        eng.grm_nine_patch_blit(src, (10, 10, 30, 20), emu.NinePatchInsets(2, 2, 2, 2))
        # Corners and borders remain exact 2px border
        self.assertEqual(eng.gpe0.read_argb32(10, 10), 0xFFFFFFFF)
        self.assertEqual(eng.gpe0.read_argb32(11, 11), 0xFFFFFFFF)
        self.assertEqual(eng.gpe0.read_argb32(39, 29), 0xFFFFFFFF)
        self.assertEqual(eng.gpe0.read_argb32(38, 28), 0xFFFFFFFF)
        # Center stretched across (12..37, 12..27)
        self.assertEqual(eng.gpe0.read_argb32(12, 12), 0xFF2060E0)
        self.assertEqual(eng.gpe0.read_argb32(37, 27), 0xFF2060E0)

        # Horizontal-only 3-slice bar (top=0, bottom=0, left=2, right=2)
        bar = emu.GpeSurface(6, 2, emu.PIXEL_FMT_RGBA8888)
        for y in range(2):
            for x in range(6):
                if x < 2 or x >= 4:
                    bar.write_rgba(x, y, 0xF0, 0x80, 0x18, 0xFF)
                else:
                    bar.write_rgba(x, y, 0x40, 0x40, 0x40, 0xFF)
        eng.grm_nine_patch_blit(bar, (4, 40, 20, 2), emu.NinePatchInsets(2, 0, 2, 0))
        self.assertEqual(eng.gpe0.read_argb32(4, 40), 0xFFF08018)
        self.assertEqual(eng.gpe0.read_argb32(10, 40), 0xFF404040)
        self.assertEqual(eng.gpe0.read_argb32(23, 41), 0xFFF08018)

    def test_08_ldec_lz77_roundtrip_0x0f_raw_and_0xf0_backref(self) -> None:
        pattern = (b"\x11\x22\x33\x44" * 16) + b"\xAA\xBB\xCC" + (b"\x55" * 48)
        enc_lz = emu.encode_ldec_lz77(pattern, prefer_lz77=True)
        self.assertEqual(enc_lz[0], 0xF0)
        self.assertLess(len(enc_lz), len(pattern))
        self.assertEqual(emu.decode_ldec_lz77(enc_lz, expected_output_len=len(pattern)), pattern)

        enc_raw = emu.encode_ldec_lz77(pattern, prefer_lz77=False)
        self.assertEqual(enc_raw[0], 0x0F)
        self.assertEqual(emu.decode_ldec_lz77(enc_raw, expected_output_len=len(pattern)), pattern)

        # Malformed streams must fail cleanly with SoftGpeError
        with self.assertRaises(emu.SoftGpeError):
            emu.decode_ldec_lz77(b"")
        with self.assertRaises(emu.SoftGpeError):
            emu.decode_ldec_lz77(b"\x99\x00\x00")
        with self.assertRaises(emu.SoftGpeError):
            emu.decode_ldec_lz77(enc_lz, expected_output_len=len(pattern) - 1)

    def test_09_clean_room_uxd_fixture_parses_all_formats_and_9patch(self) -> None:
        uxd = emu.build_clean_room_uxd_fixture()
        slots, sprites = emu.parse_uxd_sprites(uxd)
        self.assertEqual(slots, 5)
        self.assertEqual(len(sprites), 5)
        self.assertEqual(
            [s.pixel_format for s in sprites],
            [emu.PIXEL_FMT_RGBA4444, emu.PIXEL_FMT_RGBA4444, emu.PIXEL_FMT_RGBA8888, emu.PIXEL_FMT_ARGB4444, emu.PIXEL_FMT_A8],
        )
        self.assertTrue(sprites[1].is_nine_patch)
        self.assertEqual(sprites[1].insets, emu.NinePatchInsets(4, 4, 4, 4))
        for sp in sprites:
            self.assertEqual(sp.aligned_width, (sp.width + 15) & ~15)
            surf = emu.decode_uxd_sprite_to_surface(uxd, sp)
            self.assertEqual(surf.width, sp.width)
            self.assertEqual(surf.height, sp.height)

    def test_10_hosdap02_ramfb_aperture_bounds_and_xrgb8888_scanout(self) -> None:
        eng = emu.SoftGpeEngine()
        # Fill full backdrop + semi-transparent overlay
        eng.grm_fillrect(0, 0, 1024, 540, 0x00, 0x00, 0x00, 0x00)
        eng.grm_fillrect(100, 100, 20, 20, 0xFF, 0x00, 0x00, 0x80)
        gpe0_sha = eng.flush_to_offscreen_parity()
        self.assertEqual(gpe0_sha, eng.gpe1.sha256())

        hdr, scanout, stats = eng.hosdap02_ramfb_scanout(backdrop_xrgb=0x000000FF)
        self.assertEqual(hdr[:8], emu.HOSDAP02_MAGIC)
        self.assertEqual(len(scanout), emu.GPE0_BYTES)
        self.assertEqual(stats["gpe0_phys"], "0x41e001000")
        self.assertEqual(stats["ramfb_phys"], "0x41e100000")
        # Pixel (0,0) has alpha=0 so ramfb shows backdrop 0x000000FF
        bg_px = struct.unpack_from("<I", scanout, 0)[0]
        self.assertEqual(bg_px, 0x000000FF)
        # Pixel (105,105) has red@0x80 over blue backdrop -> R~0x80, B~0x7F
        fg_px = struct.unpack_from("<I", scanout, (105 * 1024 + 105) * 4)[0]
        self.assertEqual((fg_px >> 16) & 0xFF, (255 * 128) // 255)
        self.assertEqual(fg_px & 0xFF, (255 * 127) // 255)

        # Out-of-bounds ramfb aperture must raise SoftGpeError
        with self.assertRaises(emu.SoftGpeError):
            eng.hosdap02_ramfb_scanout(ramfb_phys=emu.RAMFB_WINDOW_START - 0x1000)
        with self.assertRaises(emu.SoftGpeError):
            eng.hosdap02_ramfb_scanout(ramfb_phys=emu.RAMFB_WINDOW_END - 0x1000)

    def test_11_local_donor_image_00_169_uxc_decode_and_composite_or_clean_room(self) -> None:
        rep = emu.run_phase29_soft_gpe_and_bt_audit(env=os.environ)
        self.assertTrue(rep["all_checks_passed"])
        gpe = rep["part_a_soft_gpe"]
        self.assertTrue(gpe["fx6_px_rb_parity_ok"])
        self.assertEqual(gpe["amber_accent_px_hex"], "0xfff08018")
        if emu.is_forced_clean_room():
            self.assertEqual(gpe["source_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(gpe["total_sprites"], 5)
            return
        uxc_path = emu.resolve_phase29_donor_paths()["fx6_image_uxc"]
        if not uxc_path.is_file():
            self.skipTest("Optional local FX6 image_00_169.uxc absent on this host")
        self.assertEqual(gpe["source_mode"], "LOCAL_DONOR_RDONLY")
        self.assertEqual(gpe["total_sprites"], 1610)
        self.assertEqual(gpe["nine_patch_sprites"], 22)


class TestVirtualRomV1BluetoothHciUart(unittest.TestCase):
    """Part B: `virtual-rom-v1` `/dev/ttyAMA3` H4 UART responder & 4 operating modes."""

    def test_12_bt_donor_inspection_clean_room_and_local_rdonly(self) -> None:
        cr = emu.inspect_bt_donor_libraries(force_clean_room=True)
        self.assertEqual(cr.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(cr.all_markers_satisfied)
        self.assertIn("/dev/ttyAMA3", cr.vendor_markers_present)
        self.assertIn("/dev/ttyAMA3", cr.core_markers_present)

        if not emu.is_forced_clean_room():
            paths = emu.resolve_phase29_donor_paths()
            if paths["fx6_libbt_vendor"].is_file() and paths["fx6_libbt_core"].is_file():
                loc = emu.inspect_bt_donor_libraries(force_clean_room=False)
                self.assertEqual(loc.source_mode, "LOCAL_DONOR_RDONLY")
                self.assertTrue(loc.all_markers_satisfied)
                self.assertEqual(loc.libbt_vendor_bytes, 47968)
                self.assertEqual(loc.libbt_core_bytes, 267576)

    def test_13_h4_stream_fragmentation_and_coalescing(self) -> None:
        pkt1 = emu.build_h4_hci_command(emu.HCI_OP_RESET)
        pkt2 = emu.build_h4_hci_command(emu.HCI_OP_READ_LOCAL_VERSION_INFO)
        pkt3 = emu.build_h4_hci_command(emu.HCI_OP_READ_BD_ADDR)

        # Feed 1 byte at a time
        c_frag = emu.VirtualRomV1BtController(mode=emu.BT_MODE_HEALTHY)
        c_frag.open_uart()
        ev_frag = []
        for b in pkt1 + pkt2 + pkt3:
            ev_frag.extend(c_frag.feed_uart_bytes(bytes([b])))

        # Feed all coalesced in one write
        c_coal = emu.VirtualRomV1BtController(mode=emu.BT_MODE_HEALTHY)
        c_coal.open_uart()
        ev_coal = c_coal.feed_uart_bytes(pkt1 + pkt2 + pkt3)

        self.assertEqual([e.raw_h4 for e in ev_frag], [e.raw_h4 for e in ev_coal])
        self.assertEqual(len(ev_coal), 3)

    def test_14_hci_reset_0x0c03_resets_baudrate_before_launch(self) -> None:
        ctrl = emu.VirtualRomV1BtController(mode=emu.BT_MODE_HEALTHY)
        ctrl.open_uart()
        ctrl.feed_uart_bytes(
            emu.build_h4_hci_command(emu.HCI_OP_BCM_UPDATE_BAUDRATE, emu.build_bcm_baudrate_params(3000000))
        )
        self.assertEqual(ctrl.baudrate, 3000000)
        evts = ctrl.feed_uart_bytes(emu.build_h4_hci_command(emu.HCI_OP_RESET))
        self.assertEqual(len(evts), 1)
        self.assertEqual(evts[0].raw_h4, b"\x04\x0e\x04\x01\x03\x0c\x00")
        self.assertEqual(ctrl.baudrate, 115200)

    def test_15_hci_read_local_version_0x1001_and_bd_addr_0x1009(self) -> None:
        ctrl = emu.VirtualRomV1BtController(mode=emu.BT_MODE_HEALTHY)
        ctrl.open_uart()
        e_ver = ctrl.feed_uart_bytes(emu.build_h4_hci_command(emu.HCI_OP_READ_LOCAL_VERSION_INFO))[0]
        self.assertEqual(e_ver.status, 0)
        hci_ver, hci_rev, lmp_ver, mfg, lmp_sub = struct.unpack("<BHBHH", e_ver.payload)
        self.assertEqual(hci_ver, emu.VIRTUAL_ROM_V1_HCI_VER)
        self.assertEqual(lmp_ver, emu.VIRTUAL_ROM_V1_LMP_VER)
        self.assertEqual(mfg, emu.VIRTUAL_ROM_V1_MANUFACTURER)
        self.assertEqual((hci_rev, lmp_sub), (emu.VIRTUAL_ROM_V1_HCI_REV, emu.VIRTUAL_ROM_V1_LMP_SUBVER))

        e_bd = ctrl.feed_uart_bytes(emu.build_h4_hci_command(emu.HCI_OP_READ_BD_ADDR))[0]
        self.assertEqual(e_bd.status, 0)
        self.assertEqual(len(e_bd.payload), 6)
        self.assertEqual(e_bd.payload[::-1], bytes(emu.VIRTUAL_ROM_V1_BD_ADDR))
        self.assertEqual(ctrl.bd_addr_str, "58:36:57:00:29:01")

    def test_16_bcm_baudrate_switch_0xfc18_and_invalid_param_rejection(self) -> None:
        ctrl = emu.VirtualRomV1BtController(mode=emu.BT_MODE_HEALTHY)
        ctrl.open_uart()
        bad_short = ctrl.feed_uart_bytes(emu.build_h4_hci_command(emu.HCI_OP_BCM_UPDATE_BAUDRATE, b"\x00\x00"))[0]
        self.assertEqual(bad_short.status, emu.HCI_STATUS_INVALID_PARAMS)
        bad_zero = ctrl.feed_uart_bytes(
            emu.build_h4_hci_command(emu.HCI_OP_BCM_UPDATE_BAUDRATE, emu.build_bcm_baudrate_params(0))
        )[0]
        self.assertEqual(bad_zero.status, emu.HCI_STATUS_INVALID_PARAMS)

        ok = ctrl.feed_uart_bytes(
            emu.build_h4_hci_command(emu.HCI_OP_BCM_UPDATE_BAUDRATE, emu.build_bcm_baudrate_params(3000000))
        )[0]
        self.assertEqual(ok.status, 0)
        self.assertEqual(ctrl.baudrate, 3000000)

    def test_17_bcm_patchram_state_machine_0xfc2e_0xfc4c_0xfc4e(self) -> None:
        ctrl = emu.VirtualRomV1BtController(mode=emu.BT_MODE_HEALTHY)
        ctrl.open_uart()
        # Write_RAM before Download_Minidriver is disallowed
        early_w = ctrl.feed_uart_bytes(
            emu.build_h4_hci_command(emu.HCI_OP_BCM_WRITE_RAM, emu.build_bcm_write_ram_params(0x200000, b"\xAA" * 8))
        )[0]
        self.assertEqual(early_w.status, emu.HCI_STATUS_COMMAND_DISALLOWED)

        self.assertEqual(ctrl.feed_uart_bytes(emu.build_h4_hci_command(emu.HCI_OP_BCM_DOWNLOAD_MINIDRIVER))[0].status, 0)
        self.assertEqual(ctrl.patchram_state, "MINIDRIVER_READY")
        self.assertEqual(
            ctrl.feed_uart_bytes(
                emu.build_h4_hci_command(emu.HCI_OP_BCM_WRITE_RAM, emu.build_bcm_write_ram_params(0x200000, b"\xBB" * 16))
            )[0].status,
            0,
        )
        self.assertEqual(ctrl.patchram_state, "DOWNLOADING")
        self.assertEqual(ctrl.patchram_chunks_acked, 1)
        self.assertEqual(ctrl.patchram_bytes_acked, 16)
        self.assertEqual(
            ctrl.feed_uart_bytes(emu.build_h4_hci_command(emu.HCI_OP_BCM_LAUNCH_RAM, struct.pack("<I", 0x200000)))[0].status,
            0,
        )
        self.assertEqual(ctrl.patchram_state, "LAUNCHED")

    def test_18_mode1_healthy_virtual_rom_v1_full_bsa_bringup(self) -> None:
        res = emu.run_bsa_bringup_scenario(emu.BT_MODE_HEALTHY)
        self.assertTrue(res.passed)
        self.assertTrue(res.uart_opened)
        self.assertTrue(res.bsa_ready)
        self.assertEqual(res.hal_error_code, 0)
        self.assertEqual(res.final_baudrate, 3000000)
        self.assertEqual(res.patchram_chunks_acked, 3)
        self.assertEqual(res.patchram_bytes_acked, 160)
        self.assertEqual(res.bd_addr, "58:36:57:00:29:01")
        self.assertEqual(res.degraded_state, "BSA_HEALTHY_READY")
        self.assertFalse(res.system_error_abort)
        self.assertEqual(res.wdt_resets, 0)
        self.assertEqual(res.nvram_writes, 0)

    def test_19_mode2_uart_disconnected_timeout_p12_0xbb9_fallback(self) -> None:
        res = emu.run_bsa_bringup_scenario(emu.BT_MODE_UART_TIMEOUT)
        self.assertTrue(res.passed)
        self.assertFalse(res.uart_opened)
        self.assertFalse(res.bsa_ready)
        self.assertEqual(res.rx_events, 0)
        self.assertEqual(res.hal_error_code, 0x0BB9)
        self.assertEqual(res.degraded_state, "BT_DEGRADED_DISABLED")
        self.assertFalse(res.system_error_abort)
        self.assertEqual(res.wdt_resets, 0)
        self.assertTrue(res.shooting_unaffected)
        self.assertTrue(res.recording_unaffected)
        self.assertEqual(res.nvram_writes, 0)

    def test_20_mode3_patchram_corrupt_nack_00342260_airplane_latch(self) -> None:
        res = emu.run_bsa_bringup_scenario(emu.BT_MODE_PATCHRAM_NACK)
        self.assertTrue(res.passed)
        self.assertTrue(res.uart_opened)
        self.assertFalse(res.bsa_ready)
        self.assertEqual(res.patchram_chunks_acked, 1)
        self.assertEqual(res.notice_id, "00342260")
        self.assertEqual(res.degraded_state, "NOTICE_00342260_AIRPLANE_LATCHED")
        self.assertTrue(res.airplane_latched)
        self.assertFalse(res.system_error_abort)
        self.assertEqual(res.wdt_resets, 0)
        self.assertTrue(res.shooting_unaffected)
        self.assertTrue(res.recording_unaffected)
        self.assertEqual(res.nvram_writes, 0)

    def test_21_mode4_airplane_shadow_gated_zero_hci_packets(self) -> None:
        res = emu.run_bsa_bringup_scenario(emu.BT_MODE_AIRPLANE_GATED, bkid_0x019e0012=0x00, bkid_0x01a20002=0x00)
        self.assertTrue(res.passed)
        self.assertFalse(res.uart_opened)
        self.assertEqual(res.tx_packets, 0)
        self.assertEqual(res.tx_bytes, 0)
        self.assertEqual(res.rx_events, 0)
        self.assertEqual(res.degraded_state, "AIRPLANE_SHADOW_GATED_IDLE")
        self.assertTrue(res.airplane_latched)
        self.assertFalse(res.system_error_abort)
        self.assertEqual(res.nvram_writes, 0)

        ctrl = emu.VirtualRomV1BtController(mode=emu.BT_MODE_AIRPLANE_GATED)
        self.assertFalse(ctrl.open_uart())
        with self.assertRaises(emu.BtRomEmulatorError):
            ctrl.feed_uart_bytes(emu.build_h4_hci_command(emu.HCI_OP_RESET))

    def test_22_invalid_h4_packet_type_and_unknown_opcode_handling(self) -> None:
        ctrl = emu.VirtualRomV1BtController(mode=emu.BT_MODE_HEALTHY)
        ctrl.open_uart()
        unk = ctrl.feed_uart_bytes(emu.build_h4_hci_command(0xFC99))[0]
        self.assertEqual(unk.status, emu.HCI_STATUS_UNKNOWN_COMMAND)
        with self.assertRaises(emu.BtRomEmulatorError):
            ctrl.feed_uart_bytes(b"\x02\x00\x00\x00")
        with self.assertRaises(emu.BtRomEmulatorError):
            emu.VirtualRomV1BtController(mode="UNKNOWN_MODE")

    def test_23_end_to_end_phase29_audit_clean_room_and_determinism(self) -> None:
        r1 = emu.run_phase29_soft_gpe_and_bt_audit(force_clean_room=True)
        r2 = emu.run_phase29_soft_gpe_and_bt_audit(force_clean_room=True)
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(
            r1["part_a_soft_gpe"]["ramfb_scanout"]["ramfb_xrgb8888_sha256"],
            r2["part_a_soft_gpe"]["ramfb_scanout"]["ramfb_xrgb8888_sha256"],
        )
        self.assertEqual(
            r1["part_a_soft_gpe"]["ramfb_scanout"]["gpe0_sha256"],
            r2["part_a_soft_gpe"]["ramfb_scanout"]["gpe0_sha256"],
        )

    def test_24_clean_room_env_disables_donor_paths(self) -> None:
        paths = emu.resolve_phase29_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        for k, p in paths.items():
            self.assertIn(emu.CLEAN_ROOM_SENTINEL_DIRNAME, str(p), msg=f"Clean-room bypass failed for {k}")
            self.assertFalse(p.exists())

    def test_25_source_hygiene_o_rdonly_and_zero_forbidden_writes(self) -> None:
        src = (FX3_VM_DIR / "soft_gpe_and_bt_rom_emulator.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("8768", src)
        self.assertIn("WBI_MUTATION_BYTES = 0", src)
        self.assertIn("CP_MUTATION_BYTES = 0", src)
        self.assertIn("NVRAM_PERSISTENT_WRITES = 0", src)


if __name__ == "__main__":
    unittest.main()
