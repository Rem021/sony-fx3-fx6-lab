"""Unit tests for fx3_firmware_lab (UFU/FDAT/UDTRFIRM, HAITA/BK4, and .uxc/CPU LDEC).

Designed to pass in BOTH Local Donor mode (`O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1`
mode in under 3 seconds, with zero proprietary Sony secret keys embedded.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import unittest
from pathlib import Path

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import (
    CANONICAL_BK4_CONTRACTS,
    FX3_EXPECTED_ACTIVE_PRODUCT_MODELS,
    PRODUCT_MODEL_CONTRACTS,
    _extract_ident_tokens_containing,
    analyze_haita_and_bk4_features,
    audit_bk4_record_bytes,
    build_clean_room_bk4_record,
    is_forced_clean_room,
)
from fx3_firmware_lab.ufu_container_auditor import (
    FDAT_CHUNK_SIZE,
    FDAT_RSA2048_SIG_BYTES,
    FDAT_TRAILER_BYTES,
    MODEL_ID_FX3,
    MODEL_ID_FX3A,
    MODEL_ID_FX6,
    PUBLIC_EMPTY_SHA256_PREFIX16,
    UFU_MAGIC,
    audit_sdm2_partition_table,
    audit_ufu_container,
    audit_ufu_suite,
    build_fdat_chunk_stream,
    build_sdm2_partition_table,
    build_synthetic_ufu_container,
    build_udtrfirm_container,
    default_fx3_sdm2_entries,
    parse_udtrfirm_container,
    verify_fdat_chunk_stream,
)
from fx3_firmware_lab.uxc_ldec_inspector import (
    PIXEL_FMT_A8,
    PIXEL_FMT_ARGB4444,
    PIXEL_FMT_RGBA4444,
    PIXEL_FMT_RGBA8888,
    LdecDecodeError,
    build_synthetic_uxc_string_pack,
    build_synthetic_uxd_sprite_pack,
    convert_pixel_buffer_to_argb8888,
    decode_ldec_lz77,
    encode_ldec_lz77_raw_or_match,
    inspect_uxc_and_ldec,
    inspect_uxc_bytes,
    parse_uxc_sprites,
    rgba4444_to_argb8888,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestUfuContainerAuditor(unittest.TestCase):
    def test_synthetic_fx3_ufu_passes_keyless_audit(self) -> None:
        blob = build_synthetic_ufu_container(model_id=MODEL_ID_FX3)
        self.assertTrue(blob.startswith(UFU_MAGIC))
        rep = audit_ufu_container(blob, expected_model_id=MODEL_ID_FX3)
        self.assertTrue(rep.valid, msg=f"Unexpected errors: {rep.errors}")
        self.assertTrue(rep.ufu_magic_ok)
        self.assertTrue(rep.fdat_found)
        self.assertEqual(rep.fdat_trailer_bytes, FDAT_TRAILER_BYTES)
        self.assertEqual(rep.fdat_rsa2048_sig_bytes, FDAT_RSA2048_SIG_BYTES)
        self.assertEqual(rep.fdat_iv_hex, PUBLIC_EMPTY_SHA256_PREFIX16.hex())
        self.assertIsNotNone(rep.udtrfirm_manifest)
        self.assertTrue(rep.udtrfirm_manifest.valid)

    def test_fx3a_model_id_mismatch_triggers_5l_6s_brick_guard(self) -> None:
        fx3a_blob = build_synthetic_ufu_container(model_id=MODEL_ID_FX3A)
        rep = audit_ufu_container(fx3a_blob, expected_model_id=MODEL_ID_FX3)
        self.assertFalse(rep.valid)
        self.assertFalse(rep.model_id_match)
        self.assertEqual(rep.brick_guard_code, "5L+6S_MODEL_ID_MISMATCH_BRICK_GUARD")
        self.assertTrue(any("5L+6S" in e for e in rep.errors))

    def test_degenerate_iv_or_signature_rejected(self) -> None:
        bad_iv = build_synthetic_ufu_container(iv=bytes(16))
        rep_iv = audit_ufu_container(bad_iv, expected_model_id=MODEL_ID_FX3)
        self.assertFalse(rep_iv.valid)
        self.assertFalse(rep_iv.fdat_trailer_non_degenerate)

        bad_sig = build_synthetic_ufu_container(signature=bytes([0xAA]) * 256)
        rep_sig = audit_ufu_container(bad_sig, expected_model_id=MODEL_ID_FX3)
        self.assertFalse(rep_sig.valid)
        self.assertFalse(rep_sig.fdat_trailer_non_degenerate)

    def test_truncated_and_corrupt_magic_ufu_rejected(self) -> None:
        rep_short = audit_ufu_container(b"\x89UFU")
        self.assertFalse(rep_short.valid)
        self.assertEqual(rep_short.brick_guard_code, "TRUNCATED_UFU_ENVELOPE")

        bad_magic = b"BADMAGIC" + build_synthetic_ufu_container()[8:]
        rep_magic = audit_ufu_container(bad_magic)
        self.assertFalse(rep_magic.valid)
        self.assertFalse(rep_magic.ufu_magic_ok)

    def test_fdat_1024_chunk_framing_multi_chunk_roundtrip(self) -> None:
        payload = bytes((i * 17) & 0xFF for i in range(2500))
        framed = build_fdat_chunk_stream(payload)
        self.assertEqual(len(framed), 3 * FDAT_CHUNK_SIZE)
        audit, recovered = verify_fdat_chunk_stream(framed, return_payload=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.chunk_count, 3)
        self.assertTrue(audit.terminal_flag_seen)
        self.assertEqual(recovered, payload)

    def test_fdat_chunk_checksum_and_terminal_flag_errors(self) -> None:
        framed = bytearray(build_fdat_chunk_stream(b"SONY_FDAT_PAYLOAD_CHECK" * 60))
        # Flip one payload byte in chunk 0 without updating u16 checksum
        framed[10] ^= 0xFF
        audit_bad_chk, _ = verify_fdat_chunk_stream(bytes(framed))
        self.assertFalse(audit_bad_chk.valid)
        self.assertGreater(len(audit_bad_chk.checksum_errors), 0)

        # Strip terminal 0x8000 flag from final chunk
        clean = bytearray(build_fdat_chunk_stream(b"HELLO_FDAT"))
        chk, len_w = struct.unpack_from("<HH", clean, 0)
        struct.pack_into("<HH", clean, 0, chk, len_w & 0x7FFF)
        audit_no_term, _ = verify_fdat_chunk_stream(bytes(clean))
        self.assertFalse(audit_no_term.valid)
        self.assertFalse(audit_no_term.terminal_flag_seen)

    def test_udtrfirm_manifest_parse_and_tamper_detection(self) -> None:
        raw = bytearray(
            build_udtrfirm_container(
                (
                    ("/dev/nflasha3", 3, b"KERNEL_A35"),
                    ("/dev/nflasha15", 15, b"USR_APPFW"),
                ),
                model_id=MODEL_ID_FX3,
            )
        )
        ok_m = parse_udtrfirm_container(bytes(raw))
        self.assertTrue(ok_m.valid)
        self.assertEqual(ok_m.entry_count, 2)
        self.assertEqual([e.partition_index for e in ok_m.entries], [3, 15])

        # Corrupt payload byte -> SHA-256 mismatch
        raw[-1] ^= 0x01
        bad_m = parse_udtrfirm_container(bytes(raw))
        self.assertFalse(bad_m.valid)
        self.assertTrue(any("SHA-256 mismatch" in e for e in bad_m.errors))

    def test_byof_callback_invocation_without_embedded_keys(self) -> None:
        raw_ufu = build_synthetic_ufu_container(model_id=MODEL_ID_FX3)
        # XOR-mask the FDAT chunk stream to simulate an external caller-decrypted payload
        fdat_off = raw_ufu.find(b"FDAT")
        payload_start = fdat_off + 16
        payload_end = len(raw_ufu) - FDAT_TRAILER_BYTES
        masked = (
            raw_ufu[:payload_start]
            + bytes(b ^ 0x5A for b in raw_ufu[payload_start:payload_end])
            + raw_ufu[payload_end:]
        )
        seen_iv = []

        def caller_byof_decrypt(cipher: bytes, iv: bytes) -> bytes:
            seen_iv.append(iv)
            return bytes(b ^ 0x5A for b in cipher)

        rep = audit_ufu_container(masked, expected_model_id=MODEL_ID_FX3, byof_decrypt_callback=caller_byof_decrypt)
        self.assertTrue(rep.valid)
        self.assertTrue(rep.byof_callback_invoked)
        self.assertEqual(seen_iv[0], PUBLIC_EMPTY_SHA256_PREFIX16)

    def test_sdm2_partition_table_fx3_xts_and_overlap_guard(self) -> None:
        sdm2 = build_sdm2_partition_table(default_fx3_sdm2_entries())
        res = audit_sdm2_partition_table(sdm2)
        self.assertTrue(res.valid, msg=f"SDM2 errors: {res.errors}")
        self.assertEqual(res.layout_profile, "FX3_702")
        self.assertIn(3, res.xts_encrypted_partitions)
        self.assertIn(15, res.xts_encrypted_partitions)
        self.assertIn(1, res.plaintext_partitions)
        self.assertFalse(res.emmc_static_boot_sig_required)

        # Introduce overlap between p15 and p18
        bad_entries = default_fx3_sdm2_entries()
        bad_entries[14] = (0x0022A000, 0x000FA000, 5, 1)
        res_bad = audit_sdm2_partition_table(build_sdm2_partition_table(bad_entries))
        self.assertFalse(res_bad.valid)
        self.assertTrue(res_bad.has_overlaps)

    def test_audit_ufu_suite_passes(self) -> None:
        suite = audit_ufu_suite()
        self.assertTrue(suite["all_checks_passed"])
        self.assertTrue(suite["keyless_clean_room_mode"])
        self.assertEqual(
            suite["public_header_vector_sha256_empty_16b"],
            "e3b0c44298fc1c149afbf4c8996fb924",
        )


class TestHaitaBk4FeatureAnalyzer(unittest.TestCase):
    def test_analyze_active_mode_passes(self) -> None:
        rep = analyze_haita_and_bk4_features()
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertTrue(rep.fx3_9_active_models_verified)
        self.assertTrue(rep.fx6_chaplin_present)
        self.assertTrue(rep.open_gate_asymmetry_verified)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.fx3_profile.product_models, FX3_EXPECTED_ACTIVE_PRODUCT_MODELS)
            self.assertGreater(rep.fx3_profile.haita_symbol_count, 5000)
            self.assertGreater(rep.fx6_profile.bkid_count, 4000)

    def test_forced_clean_room_uses_synthetic_fixtures(self) -> None:
        rep = analyze_haita_and_bk4_features(clean_room=True)
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(rep.fx3_profile.source_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(rep.fx6_profile.source_mode, "SYNTHETIC_CLEAN_ROOM")

    def test_env_force_clean_room_respected(self) -> None:
        rep = analyze_haita_and_bk4_features(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_product_model_alcin_uud_contract_values(self) -> None:
        alcin = PRODUCT_MODEL_CONTRACTS["PRODUCT_MODEL_ALCIN_UUD"]
        self.assertEqual(alcin["enum_id"], 4)
        self.assertEqual(alcin["feature_index"], 24)
        self.assertEqual(alcin["sensor"], "IMX510")
        self.assertEqual(alcin["category"], "CINEMA_LINE")

    def test_canonical_bk4_nvram_ids_complete(self) -> None:
        ids = {c.prop_id for c in CANONICAL_BK4_CONTRACTS}
        for required in (
            0x02CF1702,  # Shutter Angle Mode
            0x02CF1704,  # Shutter Angle Value
            0x02CF1443,  # Log Shooting / Cine EI
            0x02CF1453,  # Select LUT
            0x02CF1BF2,  # Anamorphic De-Squeeze
            0x02CF00D7,  # Open-Gate Movie Rec Aspect
            0x02CF0004,  # NTSC/PAL popup
        ):
            self.assertIn(required, ids)

    def test_bk4_record_build_audit_and_tamper_detection(self) -> None:
        rec = bytearray(build_clean_room_bk4_record())
        ok_res = audit_bk4_record_bytes(bytes(rec))
        self.assertTrue(ok_res.valid, msg=f"BK4 errors: {ok_res.errors}")
        self.assertIn("0x2cf1702", ok_res.found_nvram_ids)
        self.assertIn("0x2cf1443", ok_res.found_nvram_ids)
        self.assertIn("0x2cf1453", ok_res.found_nvram_ids)
        self.assertIn("0x2cf1bf2", ok_res.found_nvram_ids)

        # Flip one payload byte -> checksum mismatch
        rec[-1] ^= 0x01
        bad_res = audit_bk4_record_bytes(bytes(rec))
        self.assertFalse(bad_res.valid)
        self.assertFalse(bad_res.checksum_ok)

    def test_product_model_nvram_hazard_proof(self) -> None:
        rep = analyze_haita_and_bk4_features(clean_room=True)
        proof = rep.hazard_proof
        self.assertEqual(proof.verdict, "BLOCKED_PRODUCT_MODEL_NVRAM_HAZARD")
        self.assertFalse(proof.stock_nvram_mutation_allowed)
        self.assertTrue(proof.stage_a_ram_shadow_allowed)
        self.assertEqual(proof.flash_mutation_bytes, 0)
        self.assertFalse(proof.open_gate_nvram_only_feasible)
        self.assertGreaterEqual(len(proof.coupled_hardware_subsystems), 4)

    def test_fast_ident_token_extractor(self) -> None:
        sample = b"\x00PRM_HAITA_CINEMA_LINE\x00FOO_HAITA_BAR\x00PRM_FEATURE_MANAGER_menu_item\x00"
        haitas = _extract_ident_tokens_containing(sample, b"HAITA")
        self.assertEqual(haitas, {b"PRM_HAITA_CINEMA_LINE", b"FOO_HAITA_BAR"})
        fms = _extract_ident_tokens_containing(sample, b"FEATURE_MANAGER")
        self.assertEqual(fms, {b"PRM_FEATURE_MANAGER_menu_item"})

    def test_clean_room_no_secret_keys_in_package_source(self) -> None:
        # Ensure proprietary Sony key constants or private key headers never appear in source
        forbidden_markers = ("CXD90057_k8", "BEGIN RSA PRIVATE KEY", "BEGIN PRIVATE KEY")
        for py_file in (PKG_ROOT / "fx3_firmware_lab").glob("*.py"):
            txt = py_file.read_text(encoding="utf-8")
            for marker in forbidden_markers:
                if marker == "CXD90057_k8":
                    # Only permitted in docstrings explaining prohibition, never assigned as hex/bytes
                    self.assertNotRegex(txt, r'CXD90057_k8\s*=')
                else:
                    self.assertNotIn(marker, txt)


class TestUxcLdecInspectorAndCli(unittest.TestCase):
    def test_inspect_active_mode_hardware_free(self) -> None:
        rep = inspect_uxc_and_ldec()
        self.assertTrue(rep.all_checks_passed, msg=f"UXC errors: {rep.errors}")
        self.assertFalse(rep.hardware_ldec_required)
        self.assertTrue(rep.rgba4444_to_argb8888_parity_ok)
        self.assertGreater(rep.sprites_decoded_and_verified, 0)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreaterEqual(len(rep.sibling_uxc_packs), 60)
            by_name = {c.filename: c for c in rep.container_summaries}
            self.assertEqual(by_name["image_00_169.uxc"].sprite_count, 1610)
            self.assertEqual(by_name["string_english_2.uxc"].string_count, 5915)

    def test_clean_room_synthetic_all_pixel_formats(self) -> None:
        rep = inspect_uxc_and_ldec(clean_room=True)
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        fmts = {v.pixel_format for v in rep.sprite_verifications}
        self.assertEqual(
            fmts,
            {PIXEL_FMT_RGBA4444, PIXEL_FMT_RGBA8888, PIXEL_FMT_ARGB4444, PIXEL_FMT_A8},
        )
        self.assertTrue(any(v.is_nine_patch for v in rep.sprite_verifications))

    def test_ldec_lz77_and_raw_block_roundtrip(self) -> None:
        raw_rle = (b"\x12\x34" * 40) + (b"\xAB\xCD\xEF\x01" * 10)
        comp_lz = encode_ldec_lz77_raw_or_match(raw_rle, prefer_lz77=True)
        dec_lz, stats_lz = decode_ldec_lz77(comp_lz, expected_output_len=len(raw_rle))
        self.assertEqual(dec_lz, raw_rle)
        self.assertGreater(stats_lz.matches, 0)
        self.assertEqual(stats_lz.lz77_block_count, 1)

        comp_raw = encode_ldec_lz77_raw_or_match(raw_rle, prefer_lz77=False)
        dec_raw, stats_raw = decode_ldec_lz77(comp_raw, expected_output_len=len(raw_rle))
        self.assertEqual(dec_raw, raw_rle)
        self.assertEqual(stats_raw.raw_block_count, 1)

    def test_ldec_decode_bounds_errors(self) -> None:
        with self.assertRaises(LdecDecodeError):
            decode_ldec_lz77(b"")
        with self.assertRaises(LdecDecodeError):
            decode_ldec_lz77(b"\xAA\x00\x00", expected_output_len=4)
        # Distance > current block history
        with self.assertRaises(LdecDecodeError):
            decode_ldec_lz77(b"\xF0\x01\x00\x05", expected_output_len=3)
        # Truncated raw 0x0F block
        with self.assertRaises(LdecDecodeError):
            decode_ldec_lz77(b"\x0F\x00\x10\x00\xAA", expected_output_len=16)

    def test_rgba4444_and_pixel_conversion_parity(self) -> None:
        self.assertEqual(rgba4444_to_argb8888(0xF00F), 0xFFFF0000)
        self.assertEqual(rgba4444_to_argb8888(0x0F0F), 0xFF00FF00)
        self.assertEqual(rgba4444_to_argb8888(0x00FF), 0xFF0000FF)
        self.assertEqual(rgba4444_to_argb8888(0xA538), 0x88AA5533)

        # 2x1 RGBA4444 inside 16-pixel aligned row stride (32 bytes/row)
        row = bytearray(32)
        struct.pack_into("<HH", row, 0, 0xF00F, 0x0F0F)
        px = convert_pixel_buffer_to_argb8888(bytes(row), PIXEL_FMT_RGBA4444, 2, 1, aligned_width=16)
        self.assertEqual(px, [0xFFFF0000, 0xFF00FF00])

        # A8 tint conversion
        a8_row = bytes([0x80, 0xFF]) + bytes(14)
        px_a8 = convert_pixel_buffer_to_argb8888(a8_row, PIXEL_FMT_A8, 2, 1, aligned_width=16, tint_rgb=0x112233)
        self.assertEqual(px_a8, [0x80112233, 0xFF112233])

    def test_synthetic_uxc_string_and_sprite_containers(self) -> None:
        str_pack = build_synthetic_uxc_string_pack(("Cine EI", "Shutter Angle"), namespace_id=2)
        summ = inspect_uxc_bytes(str_pack, filename="string_test.uxc", source_mode="SYNTHETIC_CLEAN_ROOM")
        self.assertTrue(summ.valid)
        self.assertEqual(summ.namespace_id, 2)
        self.assertEqual(summ.string_count, 2)
        self.assertEqual(summ.sample_strings.get("0x4000"), "Cine EI")

        sprite_raw = struct.pack("<H", 0xFFFF) * (16 * 2)
        uxd_pack = build_synthetic_uxd_sprite_pack(((4, 2, PIXEL_FMT_RGBA4444, sprite_raw, False, True),))
        sprites = parse_uxc_sprites(uxd_pack)
        self.assertEqual(len(sprites), 1)
        self.assertEqual(sprites[0].width, 4)
        self.assertEqual(sprites[0].aligned_width, 16)

    def test_run_audit_all_in_process(self) -> None:
        res_clean = run_audit_all(clean_room=True)
        self.assertTrue(res_clean["all_checks_passed"])
        self.assertTrue(res_clean["keyless_byof_compliant"])
        self.assertFalse(res_clean["hardware_ldec_required"])

    def test_cli_audit_all_clean_room_deterministic_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-all", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        proc2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-all", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertEqual(proc1.stdout, proc2.stdout)
        parsed = json.loads(proc1.stdout)
        self.assertTrue(parsed["all_checks_passed"])

    def test_cli_in_process_subcommands(self) -> None:
        # Exercise cli_main directly without polluting stdout
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-ufu"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
