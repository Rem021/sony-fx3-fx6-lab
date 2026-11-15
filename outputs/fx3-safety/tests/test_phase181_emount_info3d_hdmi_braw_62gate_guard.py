"""Fast dual-mode unit tests for Phase 181 — Real-Hardware Main Track Part 18:
Gate G61 (`MIRA_CETUS2` E-Mount `info7/info8/info3D` + `0x02cf0232` Breathing
Guard + Monitor & Control `Ver. 2.1.0+` Focus Map RO + `p18:/lens/LENSFILE.BIN`
`BLKROSET=1` & CineAlta manual `LENSFILE` slot write block),
Gate G62 (`Type-A HDMI 4264x2408` 16-bit Linear RAW `Blackmagic Video Assist
12G HDR` `.braw` & `Atomos Ninja` `ProRes RAW` vs `12G-SDI` MMIO Mask Guard),
and 62-Gate Master Preflight (`G01..G62` / `verify-62-gates`).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_dualmedia_bench_interlock_and_58gate_guard import (
    STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION,
    evaluate_58gate_preflight,
)
from fx3_safety.realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard import (
    STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
    STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR,
    evaluate_60gate_preflight,
)
from fx3_safety.realhw_emount_info3d_hdmi_braw_and_62gate_guard import (
    ALLOWED_INTERNAL_SIMULTANEOUS_CODECS,
    ATOMOS_ALLOWED_MODELS,
    ATOMOS_MIN_FW_VERSION,
    BKID_APP_MR_SETTING_LENS_COMP_BREATHING,
    BKID_APP_MR_SETTING_LENS_COMP_BREATHING_HEX,
    BRAW_ALLOWED_MODELS,
    BRAW_MIN_SDK_VERSION,
    BRAW_MIN_VIDEO_ASSIST_FW,
    BRAW_REJECTED_3G_MODELS,
    DEFAULT_SAFE_SONY_EMOUNT_LENS_ID,
    DEFAULT_SYNTHETIC_LENSFILE_SHA256,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMOUNT_SERIAL_PACKET_TYPES,
    FOCUS_MAP_ALLOWED_TRANSPORTS,
    FX3_HAS_PHYSICAL_12GSDI_BNC,
    FX3_HDMI_CONNECTOR_TYPE,
    FX3_HDMI_RAW_ASPECT_RATIO,
    FX3_HDMI_RAW_BIT_DEPTH,
    FX3_HDMI_RAW_COLOR_ENCODING,
    FX3_HDMI_RAW_HEIGHT,
    FX3_HDMI_RAW_MAX_FPS,
    FX3_HDMI_RAW_WIDTH,
    FX6_FORBIDDEN_SDI_RAW_MODES,
    G61,
    G61_GATE_CODE,
    G61_GATE_ID,
    G62,
    G62_GATE_CODE,
    G62_GATE_ID,
    GATE_G61_EMOUNT_INFO7_8_3D_LENSID_AND_BREATHING_02CF0232_GUARD,
    GATE_G62_HDMI_4264X2408_16BIT_RAW_BRAW_PRORES_VS_12GSDI_GUARD,
    INFO7_LENS_ID_BITS,
    MONITOR_CONTROL_MIN_VERSION,
    P18_DEVICE_NODE,
    P18_LENSFILE_EXPECTED_BYTES,
    P18_LENSFILE_PATH,
    P18_REQUIRED_MOUNT_FLAG,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE181_DONOR_SPECS,
    PLATFORM_MIRA_CETUS2,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_EMOUNT_INFO3D_HDMI_BRAW_62GATE_SCHEMA,
    REALHW_EMOUNT_INFO3D_HDMI_BRAW_62GATE_VERSION,
    RESOLVE_MIN_VERSION,
    SONY_FIRST_PARTY_LENS_PREFIX_BITS,
    SONY_LENS_ID_INVALID_LOW12,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G61_EMOUNT_SERIAL_INFO7_8_3D_CORRUPT,
    STATUS_BLOCKED_G61_FOCUS_MAP_TELEMETRY_WRITE_UNSAFE,
    STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED,
    STATUS_BLOCKED_G61_P18_LENSFILE_RO_OR_CINEALTA_SLOT_WRITE,
    STATUS_BLOCKED_G61_TELEMETRY_INVALID,
    STATUS_BLOCKED_G62_ATOMOS_NINJA_FW_OR_METADATA_INVALID,
    STATUS_BLOCKED_G62_BRAW_VIDEO_ASSIST_3G_OR_FW_UNSUPPORTED,
    STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED,
    STATUS_BLOCKED_G62_HDMI_4264X2408_16BIT_RAW_SPEC_INVALID,
    STATUS_BLOCKED_G62_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE181_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G61,
    STATUS_VERIFIED_G62,
    STATUS_VERIFIED_SAFE,
    SUPPORTED_HDMI_RAW_FPS,
    VALID_RECORDER_MODES,
    audit_phase181_donor_contracts,
    evaluate_62_master_safety_gates,
    evaluate_62gate_preflight,
    evaluate_g61_emount_breathing_guard,
    evaluate_g62_hdmi_raw_guard,
    is_sony_first_party_breathing_lens,
    main as module_cli_main,
    parse_semver_tuple,
    validate_atomos_ninja_prores_raw_compat,
    validate_braw_video_assist_12g_compat,
    validate_breathing_02cf0232_lens_filter,
    validate_emount_info7_8_3d_packets,
    validate_focus_map_readonly_telemetry,
    validate_fx6_12gsdi_mmio_mask,
    validate_hdmi_4264x2408_16bit_raw_spec,
    validate_p18_lensfile_ro_and_cinealta_block,
    verify_emount_info3d_and_breathing_02cf0232_guard,
    verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwEmountInfo3dHdmiBraw62GateTests(unittest.TestCase):
    # --- 1. Hard-Locked Redlines, Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertFalse(FX3_HAS_PHYSICAL_12GSDI_BNC)

        self.assertEqual(
            G61,
            GATE_G61_EMOUNT_INFO7_8_3D_LENSID_AND_BREATHING_02CF0232_GUARD,
        )
        self.assertEqual(
            G62,
            GATE_G62_HDMI_4264X2408_16BIT_RAW_BRAW_PRORES_VS_12GSDI_GUARD,
        )
        self.assertEqual(fx3_safety.G61, G61_GATE_CODE)
        self.assertEqual(fx3_safety.G62, G62_GATE_CODE)
        self.assertIs(fx3_safety.evaluate_62gate_preflight, evaluate_62gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_62_master_safety_gates, evaluate_62_master_safety_gates
        )
        self.assertEqual(STATUS_SAFE, "SAFE")
        self.assertEqual(STATUS_VERIFIED_SAFE, "VERIFIED_SAFE")
        self.assertEqual(
            REALHW_EMOUNT_INFO3D_HDMI_BRAW_62GATE_SCHEMA,
            "fx3-realhw-emount-info3d-hdmi-braw-62gate-preflight-v1",
        )
        self.assertEqual(REALHW_EMOUNT_INFO3D_HDMI_BRAW_62GATE_VERSION, "1.0.0")

    def test_02_pinned_specs_and_constants(self) -> None:
        self.assertEqual(PLATFORM_MIRA_CETUS2, "MIRA_CETUS2")
        self.assertEqual(BKID_APP_MR_SETTING_LENS_COMP_BREATHING, 0x02CF0232)
        self.assertEqual(BKID_APP_MR_SETTING_LENS_COMP_BREATHING_HEX, "0x02cf0232")
        self.assertEqual(EMOUNT_SERIAL_PACKET_TYPES, ("info7", "info8", "info3D"))
        self.assertEqual(INFO7_LENS_ID_BITS, 16)
        self.assertEqual(SONY_FIRST_PARTY_LENS_PREFIX_BITS, 3)
        self.assertEqual(SONY_LENS_ID_INVALID_LOW12, 0x0FFF)
        self.assertEqual(DEFAULT_SAFE_SONY_EMOUNT_LENS_ID, 0xC01A)
        self.assertEqual(MONITOR_CONTROL_MIN_VERSION, "2.1.0")
        self.assertEqual(P18_DEVICE_NODE, "/dev/nflasha18")
        self.assertEqual(P18_LENSFILE_PATH, "p18:/lens/LENSFILE.BIN")
        self.assertEqual(P18_LENSFILE_EXPECTED_BYTES, 262_592)
        self.assertEqual(P18_REQUIRED_MOUNT_FLAG, "MS_RDONLY")
        self.assertEqual(FX3_HDMI_CONNECTOR_TYPE, "TYPE_A_FULL_SIZE")
        self.assertEqual(FX3_HDMI_RAW_WIDTH, 4264)
        self.assertEqual(FX3_HDMI_RAW_HEIGHT, 2408)
        self.assertEqual(FX3_HDMI_RAW_ASPECT_RATIO, "16:9")
        self.assertEqual(FX3_HDMI_RAW_BIT_DEPTH, 16)
        self.assertEqual(FX3_HDMI_RAW_COLOR_ENCODING, "LINEAR_RAW")
        self.assertEqual(FX3_HDMI_RAW_MAX_FPS, 60.0)
        self.assertEqual(BRAW_MIN_VIDEO_ASSIST_FW, "3.22")
        self.assertEqual(BRAW_MIN_SDK_VERSION, "5.1")
        self.assertEqual(RESOLVE_MIN_VERSION, "20.2")
        self.assertEqual(ATOMOS_MIN_FW_VERSION, "10.64")
        self.assertEqual(len(PINNED_PHASE181_DONOR_SPECS), 3)

    def test_03_donor_audit_current_mode_and_clean_room_fallback(self) -> None:
        forced_clean = audit_phase181_donor_contracts(force_clean_room=True)
        self.assertTrue(forced_clean.valid)
        self.assertEqual(forced_clean.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(forced_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(forced_clean.access_mode, "O_RDONLY")
        self.assertEqual(forced_clean.files_inspected, 0)
        self.assertTrue(forced_clean.fx3_contracts_verified)
        self.assertTrue(forced_clean.p18_lensfile_verified)

        current = audit_phase181_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(current.valid)
        self.assertEqual(current.access_mode, "O_RDONLY")
        self.assertTrue(current.fx3_contracts_verified)
        self.assertTrue(current.p18_lensfile_verified)
        env_clean = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if env_clean:
            self.assertEqual(current.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_donor_audit_missing_directory_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = audit_phase181_donor_contracts(
                work_root=Path(td) / "nonexistent_work",
                force_clean_room=False,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)

    def test_05_donor_audit_corrupted_donor_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _key, (_body, rel, _sz, _sha, _toks, _lbl) in (
                PINNED_PHASE181_DONOR_SPECS.items()
            ):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"CORRUPTED_STUB_PAYLOAD")
            res = audit_phase181_donor_contracts(work_root=root, force_clean_room=False)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE181_DONOR_INTEGRITY)
            self.assertEqual(res.files_inspected, 3)

    def test_06_synthetic_donor_tree_exact_o_rdonly_match_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            custom_specs = {}
            for key, (body, rel, _sz, _sha, toks, lbl) in (
                PINNED_PHASE181_DONOR_SPECS.items()
            ):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                payload = b"".join(tok + b"\x00" for tok in toks)
                p.write_bytes(payload)
                custom_specs[key] = (
                    body,
                    rel,
                    len(payload),
                    hashlib.sha256(payload).hexdigest(),
                    toks,
                    lbl,
                )
            with patch(
                "fx3_safety.realhw_emount_info3d_hdmi_braw_and_62gate_guard.PINNED_PHASE181_DONOR_SPECS",
                custom_specs,
            ):
                res = audit_phase181_donor_contracts(
                    work_root=root, force_clean_room=False
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertEqual(res.files_inspected, 3)
                self.assertTrue(res.fx3_contracts_verified)
                self.assertTrue(res.p18_lensfile_verified)

    # --- 2. Gate G61 (MIRA_CETUS2 E-Mount info7/info8/info3D & 0x02cf0232 Breathing) ---

    def test_07_sony_first_party_lens_filter_math_boundaries(self) -> None:
        # ((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)
        self.assertTrue(is_sony_first_party_breathing_lens(0xC000))
        self.assertTrue(is_sony_first_party_breathing_lens(0xC01A))
        self.assertTrue(is_sony_first_party_breathing_lens("0xFFFE"))
        self.assertTrue(is_sony_first_party_breathing_lens(0xCFFE))
        # Boundary rejections:
        self.assertFalse(is_sony_first_party_breathing_lens(0xCFFF))  # low 12 bits == 0xFFF
        self.assertFalse(is_sony_first_party_breathing_lens(0xFFFF))  # low 12 bits == 0xFFF
        self.assertFalse(is_sony_first_party_breathing_lens(0x801A))  # top 2 bits == 2
        self.assertFalse(is_sony_first_party_breathing_lens(0x401A))  # top 2 bits == 1 (3rd party)
        self.assertFalse(is_sony_first_party_breathing_lens(0x0000))  # top 2 bits == 0
        self.assertFalse(is_sony_first_party_breathing_lens(-1))
        self.assertFalse(is_sony_first_party_breathing_lens(0x10000))
        self.assertFalse(is_sony_first_party_breathing_lens(True))

    def test_08_parse_semver_tuple_variants(self) -> None:
        self.assertEqual(parse_semver_tuple("2.1.0"), (2, 1, 0))
        self.assertEqual(parse_semver_tuple("v3.22"), (3, 22, 0))
        self.assertEqual(parse_semver_tuple("10.64"), (10, 64, 0))
        self.assertEqual(parse_semver_tuple("20.2.1"), (20, 2, 1))
        self.assertIsNone(parse_semver_tuple("invalid"))
        self.assertIsNone(parse_semver_tuple(None))

    def test_09_g61_default_guard_and_evaluator_pass(self) -> None:
        res = verify_emount_info3d_and_breathing_02cf0232_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G61)
        self.assertEqual(res.platform_name, PLATFORM_MIRA_CETUS2)
        self.assertTrue(res.emount_serial_packets_valid)
        self.assertTrue(res.is_sony_first_party_lens)
        self.assertTrue(res.breathing_guard_valid)
        self.assertTrue(res.focus_map_guard_valid)
        self.assertTrue(res.p18_lensfile_guard_valid)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

        verdict, g61 = evaluate_g61_emount_breathing_guard(force_clean_room=True)
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.gate_id, G61_GATE_ID)
        self.assertEqual(verdict.gate_code, G61_GATE_CODE)
        self.assertTrue(g61.valid)

    def test_10_g61_emount_info7_info8_info3d_corrupt_blocked(self) -> None:
        for kwargs in (
            {"info7_packet_valid": False},
            {"info8_packet_valid": False},
            {"info3d_packet_valid": False},
            {"info8_drive_params_valid": False},
            {"info3d_optical_profile_valid": False},
            {"emount_serial_crc_ok": False},
            {"emount_packet_channels_intact": False},
            {"platform_name": "UNKNOWN_PLATFORM"},
        ):
            res = verify_emount_info3d_and_breathing_02cf0232_guard(**kwargs)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G61_EMOUNT_SERIAL_INFO7_8_3D_CORRUPT)

    def test_11_g61_helper_info7_8_3d_direct_check(self) -> None:
        ok, code, errs = validate_emount_info7_8_3d_packets()
        self.assertTrue(ok)
        self.assertEqual(code, "")
        self.assertEqual(errs, [])

        ok_bad, code_bad, errs_bad = validate_emount_info7_8_3d_packets(
            emount_serial_crc_ok=False
        )
        self.assertFalse(ok_bad)
        self.assertEqual(code_bad, STATUS_BLOCKED_G61_EMOUNT_SERIAL_INFO7_8_3D_CORRUPT)
        self.assertTrue(errs_bad)

    def test_12_g61_breathing_filter_rejects_third_party_or_0fff_when_active(self) -> None:
        for bad_id in (0x401A, 0x8001, 0x0000, 0xCFFF, 0xFFFF):
            res = verify_emount_info3d_and_breathing_02cf0232_guard(
                lens_id=bad_id,
                breathing_compensation_enabled=True,
                catalyst_breathing_metadata_write=True,
            )
            self.assertFalse(res.valid, f"Expected 0x{bad_id:04x} to be blocked")
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED,
            )

    def test_13_g61_third_party_lens_allowed_when_breathing_disabled_and_filter_enforced(
        self,
    ) -> None:
        res = verify_emount_info3d_and_breathing_02cf0232_guard(
            lens_id=0x401A,
            breathing_compensation_enabled=False,
            catalyst_breathing_metadata_write=False,
            lens_id_whitelist_enforced=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.is_sony_first_party_lens)
        self.assertTrue(res.breathing_guard_valid)

    def test_14_g61_catalyst_breathing_metadata_write_with_third_party_blocked(self) -> None:
        res = verify_emount_info3d_and_breathing_02cf0232_guard(
            lens_id=0x401A,
            breathing_compensation_enabled=False,
            catalyst_breathing_metadata_write=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED
        )

    def test_15_g61_02cf0232_passthrough_loss_or_wrong_bkid_blocked(self) -> None:
        res1 = verify_emount_info3d_and_breathing_02cf0232_guard(
            bkid_02cf0232_passthrough_intact=False
        )
        res2 = verify_emount_info3d_and_breathing_02cf0232_guard(
            lens_id_whitelist_enforced=False
        )
        res3 = verify_emount_info3d_and_breathing_02cf0232_guard(bkid_hex="0x02cf0214")
        for r in (res1, res2, res3):
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status, STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED
            )

    def test_16_g61_focus_map_monitor_control_version_floor_2_1_0(self) -> None:
        for ok_ver in ("2.1.0", "2.1.5", "2.2.0", "3.0.0"):
            res = verify_emount_info3d_and_breathing_02cf0232_guard(
                monitor_control_version=ok_ver
            )
            self.assertTrue(res.valid, f"Expected M&C {ok_ver} to pass")

        for old_ver in ("1.0.0", "2.0.0", "2.0.9"):
            res = verify_emount_info3d_and_breathing_02cf0232_guard(
                monitor_control_version=old_ver,
                focus_map_enabled=True,
            )
            self.assertFalse(res.valid, f"Expected M&C {old_ver} to be blocked")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G61_FOCUS_MAP_TELEMETRY_WRITE_UNSAFE
            )

    def test_17_g61_focus_map_write_or_cp_mutation_blocked(self) -> None:
        for kwargs in (
            {"focus_map_readonly_telemetry": False},
            {"focus_map_emmc_writes": 1},
            {"focus_map_cp_mutation_bytes": 16},
            {"focus_map_transport": "UNKNOWN_BUS"},
        ):
            res = verify_emount_info3d_and_breathing_02cf0232_guard(**kwargs)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G61_FOCUS_MAP_TELEMETRY_WRITE_UNSAFE
            )

    def test_18_g61_p18_lensfile_blkroset_and_ms_rdonly_enforced(self) -> None:
        for kwargs in (
            {"p18_blkroset": 0},
            {"p18_mount_flags": "rw,relatime"},
            {"lens_partition_writes": 1},
            {"p18_device_node": "/dev/nflasha5"},
            {"p18_lensfile_path": "/setting/Backup.bin"},
            {"p18_lensfile_sha256": "0" * 64},
            {"cpapp_stock_preserved": False},
        ):
            res = verify_emount_info3d_and_breathing_02cf0232_guard(**kwargs)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G61_P18_LENSFILE_RO_OR_CINEALTA_SLOT_WRITE
            )

    def test_19_g61_cinealta_manual_lensfile_slot_write_blocked(self) -> None:
        res1 = verify_emount_info3d_and_breathing_02cf0232_guard(
            cinealta_manual_lensfile_slot_write_requested=True
        )
        res2 = verify_emount_info3d_and_breathing_02cf0232_guard(
            cinealta_manual_lensfile_slot_write_blocked=False
        )
        for r in (res1, res2):
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status, STATUS_BLOCKED_G61_P18_LENSFILE_RO_OR_CINEALTA_SLOT_WRITE
            )

    def test_20_g61_helper_focus_map_and_p18_direct_checks(self) -> None:
        ok_fm, c_fm, _ = validate_focus_map_readonly_telemetry(
            focus_map_transport="USB_LAN", monitor_control_version="2.2.1"
        )
        self.assertTrue(ok_fm)
        self.assertEqual(c_fm, "")
        ok_p18, c_p18, _ = validate_p18_lensfile_ro_and_cinealta_block()
        self.assertTrue(ok_p18)
        self.assertEqual(c_p18, "")
        ok_br, c_br, _ = validate_breathing_02cf0232_lens_filter()
        self.assertTrue(ok_br)
        self.assertEqual(c_br, "")

    def test_21_g61_invalid_telemetry_fails_closed(self) -> None:
        res1 = verify_emount_info3d_and_breathing_02cf0232_guard(lens_id=-5)
        res2 = verify_emount_info3d_and_breathing_02cf0232_guard(lens_id=0x1FFFF)
        res3 = verify_emount_info3d_and_breathing_02cf0232_guard(p18_blkroset=9)
        res4 = verify_emount_info3d_and_breathing_02cf0232_guard(lens_partition_writes=-1)
        res5 = verify_emount_info3d_and_breathing_02cf0232_guard(platform_name="   ")
        for r in (res1, res2, res3, res4, res5):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G61_TELEMETRY_INVALID)

    def test_22_g61_persistent_write_request_redline_blocked(self) -> None:
        verdict, res = evaluate_g61_emount_breathing_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_23_g61_propagates_corrupted_donor_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _key, (_body, rel, _sz, _sha, _toks, _lbl) in (
                PINNED_PHASE181_DONOR_SPECS.items()
            ):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"TAMPERED_DONOR")
            verdict, res = evaluate_g61_emount_breathing_guard(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(verdict.passed)
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_PHASE181_DONOR_INTEGRITY, res.violation_codes)

    # --- 3. Gate G62 (Type-A HDMI 4264x2408 16-bit RAW vs 12G-SDI Mask) ---

    def test_24_g62_default_guard_and_evaluator_pass(self) -> None:
        res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G62)
        self.assertTrue(res.hdmi_raw_spec_valid)
        self.assertTrue(res.braw_compat_valid)
        self.assertTrue(res.atomos_prores_compat_valid)
        self.assertTrue(res.sdi_mask_guard_valid)
        self.assertEqual(res.sdi_mmio_probes_emitted, 0)
        self.assertFalse(res.fx3_has_physical_12gsdi_bnc)
        self.assertFalse(res.persistent_emmc_writes_authorized)

        verdict, g62 = evaluate_g62_hdmi_raw_guard(force_clean_room=True)
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.gate_id, G62_GATE_ID)
        self.assertEqual(verdict.gate_code, G62_GATE_CODE)
        self.assertTrue(g62.valid)

    def test_25_g62_supported_hdmi_raw_fps_and_internal_codecs(self) -> None:
        for fps in SUPPORTED_HDMI_RAW_FPS:
            for codec in ALLOWED_INTERNAL_SIMULTANEOUS_CODECS:
                res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
                    hdmi_raw_fps=fps,
                    simultaneous_internal_codec=codec,
                )
                self.assertTrue(res.valid, f"Failed for fps={fps}, codec={codec}")

    def test_26_g62_rejects_bad_resolution_aspect_bitdepth_connector_or_over_60p(
        self,
    ) -> None:
        for kwargs in (
            {"hdmi_connector_type": "MICRO_HDMI_TYPE_D"},
            {"hdmi_raw_width": 4096, "hdmi_raw_height": 2160},
            {"hdmi_raw_aspect_ratio": "17:9"},
            {"hdmi_raw_bit_depth": 12},
            {"hdmi_raw_color_encoding": "LOG_10BIT"},
            {"hdmi_raw_fps": 119.88},
            {"hdmi_raw_fps": 120.0},
            {"simultaneous_internal_codec": "XAVC_RAW_INTERNAL"},
        ):
            res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(**kwargs)
            self.assertFalse(res.valid, f"Expected failure for {kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G62_HDMI_4264X2408_16BIT_RAW_SPEC_INVALID
            )

    def test_27_g62_braw_allowed_12g_models_and_rejected_3g_models(self) -> None:
        for model in BRAW_ALLOWED_MODELS:
            res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
                recorder_mode="BRAW_VIDEO_ASSIST_12G",
                braw_recorder_model=model,
            )
            self.assertTrue(res.valid, f"Expected {model} to pass")

        for bad_model in BRAW_REJECTED_3G_MODELS:
            res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
                recorder_mode="BRAW_VIDEO_ASSIST_12G",
                braw_recorder_model=bad_model,
            )
            self.assertFalse(res.valid, f"Expected 3G model {bad_model} to be rejected")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G62_BRAW_VIDEO_ASSIST_3G_OR_FW_UNSUPPORTED
            )

    def test_28_g62_braw_fw_sdk_resolve_iso_lock_and_private_profile_checks(self) -> None:
        for kwargs in (
            {"braw_video_assist_fw": "3.21"},
            {"braw_sdk_version": "5.0"},
            {"resolve_version": "20.1"},
            {"braw_iso_capture_state_locked": False},
            {"braw_private_sensor_profile_expected": True},
        ):
            res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
                recorder_mode="BRAW_VIDEO_ASSIST_12G",
                **kwargs,
            )
            self.assertFalse(res.valid, f"Expected rejection for {kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G62_BRAW_VIDEO_ASSIST_3G_OR_FW_UNSUPPORTED
            )

    def test_29_g62_atomos_ninja_models_and_fw_1064_plus_metadata(self) -> None:
        for model in ATOMOS_ALLOWED_MODELS:
            res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
                recorder_mode="PRORES_RAW_ATOMOS_NINJA",
                atomos_recorder_model=model,
                atomos_fw_version="10.64",
            )
            self.assertTrue(res.valid, f"Expected Atomos {model} to pass")

        for kwargs in (
            {"atomos_recorder_model": "UNKNOWN_RECORDER"},
            {"atomos_fw_version": "10.63"},
            {"resolve_version": "20.1"},
            {"prores_raw_wb_iso_offset_metadata_verified": False},
        ):
            res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
                recorder_mode="PRORES_RAW_ATOMOS_NINJA",
                **kwargs,
            )
            self.assertFalse(res.valid, f"Expected Atomos rejection for {kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G62_ATOMOS_NINJA_FW_OR_METADATA_INVALID
            )

    def test_30_g62_fx6_12gsdi_mmio_probes_hard_masked(self) -> None:
        for kwargs in (
            {"fx3_has_physical_12gsdi_bnc": True},
            {"sdi_mmio_probes_emitted": 1},
            {"sdi_driver_probes_masked": False},
            {"fx6_12gsdi_raw_enabled": True},
            {"hdmi_raw_pipeline_routed": False},
        ):
            res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(**kwargs)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED
            )

        for sdi_mode in FX6_FORBIDDEN_SDI_RAW_MODES:
            res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
                requested_sdi_mode=sdi_mode
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED
            )

    def test_31_g62_recorder_mode_none_internal_only_skips_ext_checks(self) -> None:
        res = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
            recorder_mode="NONE_INTERNAL_ONLY",
            braw_recorder_model="VIDEO_ASSIST_3G",
            atomos_fw_version="9.0",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G62)

    def test_32_g62_direct_helper_validators(self) -> None:
        ok_raw, c_raw, _ = validate_hdmi_4264x2408_16bit_raw_spec()
        self.assertTrue(ok_raw)
        self.assertEqual(c_raw, "")
        ok_braw, c_braw, _ = validate_braw_video_assist_12g_compat()
        self.assertTrue(ok_braw)
        self.assertEqual(c_braw, "")
        ok_atomos, c_atomos, _ = validate_atomos_ninja_prores_raw_compat()
        self.assertTrue(ok_atomos)
        self.assertEqual(c_atomos, "")
        ok_sdi, c_sdi, _ = validate_fx6_12gsdi_mmio_mask()
        self.assertTrue(ok_sdi)
        self.assertEqual(c_sdi, "")

    def test_33_g62_invalid_telemetry_fails_closed(self) -> None:
        res1 = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
            recorder_mode="INVALID_RECORDER_MODE"
        )
        res2 = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(sdi_mmio_probes_emitted=-1)
        res3 = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
            hdmi_raw_fps=float("nan")
        )
        res4 = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
            hdmi_raw_width=True  # type: ignore[arg-type]
        )
        for r in (res1, res2, res3, res4):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G62_TELEMETRY_INVALID)

    def test_34_g62_persistent_write_request_redline_blocked(self) -> None:
        verdict, res = evaluate_g62_hdmi_raw_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_35_g62_propagates_corrupted_donor_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _key, (_body, rel, _sz, _sha, _toks, _lbl) in (
                PINNED_PHASE181_DONOR_SPECS.items()
            ):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"TAMPERED_DONOR")
            verdict, res = evaluate_g62_hdmi_raw_guard(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(verdict.passed)
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_PHASE181_DONOR_INTEGRITY, res.violation_codes)

    # --- 4. 62-Gate Master Preflight & Backward Compatibility ---

    def test_36_evaluate_62gate_preflight_offline_59_of_62(self) -> None:
        report = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertEqual(report.summary["total_gates"], 62)
        self.assertEqual(report.summary["verified_gates"], 59)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(len(report.gates), 62)
        self.assertTrue(report.offline_59_gates_verified)
        self.assertFalse(report.all_62_gates_verified)
        self.assertTrue(report.g61_to_g62_all_passed)
        self.assertTrue(report.g13_to_g62_all_passed)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertFalse(report.physical_flash_auto_exec_authorized)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)
        self.assertEqual(report.status, "VERIFIED_59_OF_62_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertEqual(
                report.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_37_evaluate_62gate_preflight_dry_run_62_of_62(self) -> None:
        report = evaluate_62_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(report.summary["total_gates"], 62)
        self.assertEqual(report.summary["verified_gates"], 62)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(report.summary["g01_to_g12_verified"], 12)
        self.assertEqual(report.summary["g13_to_g60_verified"], 48)
        self.assertEqual(report.summary["g61_to_g62_verified"], 2)
        self.assertTrue(report.all_62_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertTrue(report.g61_to_g62_all_passed)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)
        self.assertEqual(report.status, "VERIFIED_ALL_62_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_38_evaluate_62gate_preflight_propagates_g61_faults(self) -> None:
        r_g61_id = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            emount_breathing_kwargs={"lens_id": 0x401A, "breathing_compensation_enabled": True},
        )
        self.assertFalse(r_g61_id.all_62_gates_verified)
        self.assertFalse(r_g61_id.g61_to_g62_all_passed)
        self.assertEqual(
            r_g61_id.status, STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED
        )

        r_g61_p18 = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            emount_breathing_kwargs={"cinealta_manual_lensfile_slot_write_requested": True},
        )
        self.assertFalse(r_g61_p18.all_62_gates_verified)
        self.assertEqual(
            r_g61_p18.status, STATUS_BLOCKED_G61_P18_LENSFILE_RO_OR_CINEALTA_SLOT_WRITE
        )

    def test_39_evaluate_62gate_preflight_propagates_g62_faults(self) -> None:
        r_g62_sdi = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            hdmi_raw_kwargs={"sdi_mmio_probes_emitted": 2},
        )
        self.assertFalse(r_g62_sdi.all_62_gates_verified)
        self.assertFalse(r_g62_sdi.g61_to_g62_all_passed)
        self.assertEqual(
            r_g62_sdi.status, STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED
        )

        r_g62_3g = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            hdmi_raw_kwargs={"braw_recorder_model": "VIDEO_ASSIST_7_3G"},
        )
        self.assertFalse(r_g62_3g.all_62_gates_verified)
        self.assertEqual(
            r_g62_3g.status, STATUS_BLOCKED_G62_BRAW_VIDEO_ASSIST_3G_OR_FW_UNSUPPORTED
        )

    def test_40_evaluate_62gate_preflight_propagates_upstream_g58_g59_g60_faults(
        self,
    ) -> None:
        r_g59 = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            ssboot_wbi2_kwargs={"blkroset_nflasha5": 0},
        )
        self.assertFalse(r_g59.all_62_gates_verified)
        self.assertEqual(
            r_g59.status,
            STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
        )

        r_g60 = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            slot1_ufu_c2pa_kwargs={"body_firmware_version": "2.02"},
        )
        self.assertFalse(r_g60.all_62_gates_verified)
        self.assertEqual(r_g60.status, STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR)

        r_g58 = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            bench_interlock_kwargs={"auto_flash_requested": True},
        )
        self.assertFalse(r_g58.all_62_gates_verified)
        self.assertEqual(r_g58.status, STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION)

    def test_41_evaluate_62gate_preflight_blocks_persistent_write_request(self) -> None:
        report = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(report.all_62_gates_verified)
        self.assertFalse(report.h0_h1_trial_entry_allowed)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertEqual(report.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_42_evaluate_58_and_60gate_preflight_backward_compatibility_intact(
        self,
    ) -> None:
        r58 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(r58.summary["total_gates"], 58)
        self.assertEqual(r58.summary["verified_gates"], 58)
        self.assertTrue(r58.all_58_gates_verified)

        r60 = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(r60.summary["total_gates"], 60)
        self.assertEqual(r60.summary["verified_gates"], 60)
        self.assertTrue(r60.all_60_gates_verified)

        for cmd, expected in (
            (["verify-58-gates", "--clean-room", "--dry-run-simulated-backup", "--json"], 58),
            (["verify-60-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 60),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(cmd)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["summary"]["verified_gates"], expected)

    def test_43_gate_order_g61_and_g62_ids_in_master_report(self) -> None:
        report = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(report.gates[60]["gate_id"], G61_GATE_ID)
        self.assertEqual(report.gates[60]["gate_code"], G61_GATE_CODE)
        self.assertEqual(report.gates[61]["gate_id"], G62_GATE_ID)
        self.assertEqual(report.gates[61]["gate_code"], G62_GATE_CODE)

    def test_44_dry_run_simulated_backup_alias_flag_supported(self) -> None:
        report = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertTrue(report.all_62_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(report.summary["verified_gates"], 62)

    # --- 5. CLI Entrypoints, Zero Raw Firmware Leakage & Performance ---

    def test_45_cli_verify_g61_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g61-emount-breathing-guard", "--force-clean-room", "--json"],
            ["verify-g61-emount-breathing-guard", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G61)
                self.assertFalse(data["persistent_emmc_writes_authorized"])

    def test_46_cli_verify_g62_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g62-hdmi-raw-guard", "--force-clean-room", "--json"],
            ["verify-g62-hdmi-raw-guard", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G62)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertEqual(
                    data["hdmi_raw_guard"]["sdi_mmio_probes_emitted"], 0
                )

    def test_47_cli_verify_62_gates_offline_and_dry_run_modes(self) -> None:
        for subcmd, expected_count in (
            (["verify-62-gates", "--force-clean-room", "--json"], 59),
            (["verify-62-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 62),
            (["verify-62-gates", "--force-clean-room"], None),
            (["verify-62-gates", "--force-clean-room", "--dry-run-simulated"], None),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, f"CLI failed for {subcmd}: {buf.getvalue()}")
            if expected_count is not None:
                payload = json.loads(buf.getvalue())
                self.assertEqual(payload["summary"]["verified_gates"], expected_count)
                self.assertFalse(payload["overall_ready_for_hardware_attach"])

    def test_48_module_cli_and_zero_raw_firmware_leakage_in_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated", "--json"])
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertNotIn("b'\\x7fELF", text)
        self.assertNotIn('b"\\x7fELF', text)
        payload = json.loads(text)
        self.assertEqual(payload["summary"]["verified_gates"], 62)
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["el3_payload_transmit_authorized"])
        self.assertFalse(payload["spi_nor_write_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_49_module_cli_text_output_smoke(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=62/62", out)
        self.assertIn("g61_to_g62_all_passed=True", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    def test_50_verify_62_gates_fast_runtime_under_6s(self) -> None:
        t0 = time.monotonic()
        report = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        elapsed = time.monotonic() - t0
        self.assertTrue(report.all_62_gates_verified)
        self.assertLess(elapsed, 6.0)


if __name__ == "__main__":
    unittest.main()
