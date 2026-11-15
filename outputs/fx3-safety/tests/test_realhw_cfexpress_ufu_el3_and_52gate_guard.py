"""Fast dual-mode unit tests for Phase 161 — Real-Hardware Main Track Part 13:
Gate G51 (Dual-Slot `CFexpress Type A / SDXC V90` Bitrate Gate, Card-Door GPIO
FIFO Flush, `PRIVATE/M4ROOT` & `XDROOT` Clip Preservation & Official
`BODYDATA.DAT` `\\x89UFU` Pre-Update Clean-Uninstall `H0 == H3` Guard),
Gate G52 (5-Tier Unbrickable Recovery Escalation Ladder, `ILME-FX3`
`0x91030080` `BODYDATA.DAT` Model-ID Lock & `CXD90057` EL3 `0xfe020000`
Read-Only Guard), and Unified 52-Gate Master Safety Preflight (`G01..G52` /
`verify-52-gates`).
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
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_cfexpress_ufu_el3_and_52gate_guard import (
    BODYDATA_SD_CANDIDATE_PATHS,
    BODYDATA_UFU_MAGIC_BYTES,
    BODYDATA_UFU_MAGIC_HEX_STR,
    CANONICAL_5_RECOVERY_TIERS,
    CXD90057_EL3_LOAD_ADDR_HEX,
    CXD90057_EL3_LOAD_ADDR_INT,
    CXD90057_SOC_NAME,
    DEFAULT_SYNTHETIC_H0_STOCK_SHA256,
    DEFAULT_SYNTHETIC_H3_POST_UNINSTALL_SHA256,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX3_MODEL_ID_HEX,
    FX3_MODEL_ID_INT,
    FX3_MODEL_NAME,
    G51_CFEXPRESS_SPEED_CLASSES,
    G51_GATE_CODE,
    G51_GATE_ID,
    G51_MEDIA_MIN_SUSTAINED_MB_S,
    G51_PROTECTED_CLIP_DIRS,
    G51_STAGE_A_BYPASS_MAX_US,
    G51_STAGE_A_BYPASS_NOMINAL_US,
    G51_VALID_MEDIA_TYPES,
    G51_VALID_SPEED_CLASSES,
    G51_XAVC_SI_4K120P_BITRATE_MBPS,
    G51_XAVC_SI_OVERHEAD_MARGIN,
    G52_GATE_CODE,
    G52_GATE_ID,
    MEDIA_TYPE_CFEXPRESS_A,
    MEDIA_TYPE_SDXC_UHS1,
    MEDIA_TYPE_SDXC_V30,
    MEDIA_TYPE_SDXC_V60,
    MEDIA_TYPE_SDXC_V90,
    P15_USR_ORIG_MARKER,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PINNED_BODYDATA_HEADER_MARKERS,
    PINNED_BODYDATA_HEADER_READ_BYTES,
    PINNED_BODYDATA_HEADER_RELPATH,
    PINNED_BODYDATA_HEADER_SHA256,
    PINNED_BODYDATA_TOTAL_BYTES,
    PINNED_PHASE161_DONOR_SPECS,
    REALHW_CFEXPRESS_UFU_EL3_52GATE_SCHEMA,
    REALHW_CFEXPRESS_UFU_EL3_52GATE_VERSION,
    RECOVERY_TIER_1_SD_47US,
    RECOVERY_TIER_2_P15_ORIG,
    RECOVERY_TIER_3_BODYDATA_UFU,
    RECOVERY_TIER_4_UART_EL3_RO,
    RECOVERY_TIER_5_CID_EMMC_ISP,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD,
    STATUS_BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO,
    STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT,
    STATUS_BLOCKED_G51_TELEMETRY_INVALID,
    STATUS_BLOCKED_G51_USER_CLIP_DIR_MUTATION,
    STATUS_BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH,
    STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED,
    STATUS_BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE,
    STATUS_BLOCKED_G52_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G51,
    STATUS_VERIFIED_G52,
    STATUS_VERIFIED_SAFE,
    XAVC_SI_4K120P_CODEC_PROFILE,
    audit_phase161_donor_contracts,
    compute_required_media_write_mb_s,
    evaluate_52_master_safety_gates,
    evaluate_52gate_preflight,
    evaluate_g51_cfexpress_ufu,
    evaluate_g52_5tier_el3_guard,
    main as module_cli_main,
    validate_5tier_recovery_ladder,
    validate_bodydata_ufu_and_clean_uninstall,
    validate_card_door_gpio_flush,
    validate_cxd90057_el3_readonly_guard,
    validate_dual_slot_media_bitrate,
    validate_fx3_model_id_bodydata_lock,
    validate_user_clip_dirs_untouched,
    verify_5tier_recovery_model_id_and_el3_ro_guard,
    verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard,
)
from fx3_safety.realhw_uart1v8_imx510_cal_and_50gate_guard import (
    REALHW_UART1V8_IMX510_50GATE_SCHEMA,
    SPI_NOR_WRITE_AUTHORIZED as PRIOR_SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE,
    STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE,
    evaluate_50gate_preflight,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwCfexpressUfuEl3And52GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PRIOR_SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            REALHW_CFEXPRESS_UFU_EL3_52GATE_SCHEMA,
            "fx3-realhw-cfexpress-ufu-el3-52gate-preflight-v1",
        )
        self.assertEqual(REALHW_CFEXPRESS_UFU_EL3_52GATE_VERSION, "1.0.0")
        self.assertEqual(FX3_MODEL_ID_INT, 0x91030080)
        self.assertEqual(FX3_MODEL_ID_HEX, "0x91030080")
        self.assertEqual(CXD90057_EL3_LOAD_ADDR_INT, 0xFE020000)
        self.assertEqual(CXD90057_EL3_LOAD_ADDR_HEX, "0xfe020000")
        self.assertEqual(BODYDATA_UFU_MAGIC_BYTES, b"\x89UFU\r\n\x1a\n")
        self.assertEqual(len(CANONICAL_5_RECOVERY_TIERS), 5)

        for sym in (
            "BODYDATA_SD_CANDIDATE_PATHS",
            "BODYDATA_UFU_MAGIC_BYTES",
            "BODYDATA_UFU_MAGIC_HEX_STR",
            "CANONICAL_5_RECOVERY_TIERS",
            "CXD90057_EL3_LOAD_ADDR_HEX",
            "CXD90057_EL3_LOAD_ADDR_INT",
            "CXD90057_SOC_NAME",
            "DEFAULT_SYNTHETIC_H0_STOCK_SHA256",
            "DEFAULT_SYNTHETIC_H3_POST_UNINSTALL_SHA256",
            "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
            "FX3_MODEL_ID_HEX",
            "FX3_MODEL_ID_INT",
            "FX3_MODEL_NAME",
            "G51_CFEXPRESS_SPEED_CLASSES",
            "G51_GATE_CODE",
            "G51_GATE_ID",
            "G51_MEDIA_MIN_SUSTAINED_MB_S",
            "G51_PROTECTED_CLIP_DIRS",
            "G51_STAGE_A_BYPASS_MAX_US",
            "G51_STAGE_A_BYPASS_NOMINAL_US",
            "G51_VALID_MEDIA_TYPES",
            "G51_VALID_SPEED_CLASSES",
            "G51_XAVC_SI_4K120P_BITRATE_MBPS",
            "G51_XAVC_SI_OVERHEAD_MARGIN",
            "G52_GATE_CODE",
            "G52_GATE_ID",
            "MEDIA_TYPE_SDXC_UHS1",
            "MEDIA_TYPE_SDXC_V30",
            "MEDIA_TYPE_SDXC_V60",
            "MEDIA_TYPE_SDXC_V90",
            "P15_USR_ORIG_MARKER",
            "PINNED_BODYDATA_HEADER_MARKERS",
            "PINNED_BODYDATA_HEADER_READ_BYTES",
            "PINNED_BODYDATA_HEADER_RELPATH",
            "PINNED_BODYDATA_HEADER_SHA256",
            "PINNED_BODYDATA_TOTAL_BYTES",
            "PINNED_PHASE161_DONOR_SPECS",
            "REALHW_CFEXPRESS_UFU_EL3_52GATE_SCHEMA",
            "REALHW_CFEXPRESS_UFU_EL3_52GATE_VERSION",
            "RECOVERY_TIER_1_SD_47US",
            "RECOVERY_TIER_2_P15_ORIG",
            "RECOVERY_TIER_3_BODYDATA_UFU",
            "RECOVERY_TIER_4_UART_EL3_RO",
            "RECOVERY_TIER_5_CID_EMMC_ISP",
            "STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD",
            "STATUS_BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO",
            "STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT",
            "STATUS_BLOCKED_G51_TELEMETRY_INVALID",
            "STATUS_BLOCKED_G51_USER_CLIP_DIR_MUTATION",
            "STATUS_BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH",
            "STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED",
            "STATUS_BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE",
            "STATUS_BLOCKED_G52_TELEMETRY_INVALID",
            "STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY",
            "STATUS_VERIFIED_G51",
            "STATUS_VERIFIED_G52",
            "XAVC_SI_4K120P_CODEC_PROFILE",
            "CfexpressUfuPreUpdateGuardResult",
            "FiveTierRecoveryEl3GuardResult",
            "G51CfexpressUfuResult",
            "G52FiveTierEl3GuardResult",
            "Master52GateReport",
            "Phase161DonorAuditResult",
            "audit_phase161_donor_contracts",
            "compute_required_media_write_mb_s",
            "evaluate_52_master_safety_gates",
            "evaluate_52gate_preflight",
            "evaluate_g51_cfexpress_ufu",
            "evaluate_g52_5tier_el3_guard",
            "realhw_cfexpress_ufu_el3_and_52gate_guard",
            "validate_5tier_recovery_ladder",
            "validate_bodydata_ufu_and_clean_uninstall",
            "validate_card_door_gpio_flush",
            "validate_cxd90057_el3_readonly_guard",
            "validate_dual_slot_media_bitrate",
            "validate_fx3_model_id_bodydata_lock",
            "validate_user_clip_dirs_untouched",
            "verify_5tier_recovery_model_id_and_el3_ro_guard",
            "verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing package export: {sym}")

        # Ensure prior colliding package-level constants remain untouched
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(fx3_safety.MEDIA_TYPE_CFEXPRESS_A, "CFEXPRESS_TYPE_A")

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        clean_res = audit_phase161_donor_contracts(force_clean_room=True)
        self.assertTrue(clean_res.valid)
        self.assertEqual(clean_res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(clean_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(clean_res.access_mode, "O_RDONLY")
        self.assertEqual(clean_res.files_inspected, 0)
        self.assertEqual(len(clean_res.checked_markers), len(PINNED_PHASE161_DONOR_SPECS))
        self.assertEqual(clean_res.missing_markers, ())
        self.assertTrue(clean_res.fx3_contracts_verified)
        self.assertFalse(clean_res.bodydata_header_checked)

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_res = audit_phase161_donor_contracts(
                work_root=Path(tmpdir), force_clean_room=False
            )
            self.assertTrue(missing_res.valid)
            self.assertEqual(missing_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        orig_open = os.open
        seen_flags: list[int] = []

        def spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            seen_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with patch(
            "fx3_safety.realhw_cfexpress_ufu_el3_and_52gate_guard.os.open",
            side_effect=spy_open,
        ):
            auto_res = audit_phase161_donor_contracts(repo_root=DEFAULT_REPO_ROOT)

        self.assertTrue(auto_res.valid)
        self.assertEqual(auto_res.access_mode, "O_RDONLY")
        if auto_res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertGreaterEqual(
                auto_res.files_inspected, len(PINNED_PHASE161_DONOR_SPECS)
            )
            self.assertGreaterEqual(len(seen_flags), len(PINNED_PHASE161_DONOR_SPECS))
            for fl in seen_flags:
                self.assertEqual(fl & 3, os.O_RDONLY)

        dumped = json.dumps(auto_res.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)
        self.assertNotIn("b'\\x89UFU", dumped)

    def test_03_donor_audit_fails_closed_on_tampered_sha_or_missing_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for _k, (_body, rel, size, _sha, toks, _lbl) in PINNED_PHASE161_DONOR_SPECS.items():
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                payload = b"".join(t + b"\x00" for t in toks)
                if len(payload) < size:
                    payload = payload + b"\x00" * min(128, size - len(payload))
                p.write_bytes(payload)

            tampered = audit_phase161_donor_contracts(work_root=work, force_clean_room=False)
            self.assertFalse(tampered.valid)
            self.assertEqual(tampered.status, STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY)
            self.assertEqual(tampered.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertFalse(tampered.fx3_contracts_verified)
            self.assertGreaterEqual(len(tampered.errors), len(PINNED_PHASE161_DONOR_SPECS))

            v51, r51 = evaluate_g51_cfexpress_ufu(donor_audit=tampered)
            self.assertFalse(v51.passed)
            self.assertFalse(r51.valid)
            self.assertIn(STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY, v51.violation_codes)

            v52, r52 = evaluate_g52_5tier_el3_guard(donor_audit=tampered)
            self.assertFalse(v52.passed)
            self.assertFalse(r52.valid)
            self.assertIn(STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY, v52.violation_codes)

    def test_04_donor_audit_fails_closed_on_tampered_bodydata_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for _k, (_body, rel, _sz, _sha, toks, _lbl) in PINNED_PHASE161_DONOR_SPECS.items():
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"".join(t + b"\x00" for t in toks))
            bd = work / PINNED_BODYDATA_HEADER_RELPATH
            bd.parent.mkdir(parents=True, exist_ok=True)
            bd.write_bytes(b"BAD_UFU_HEADER" + b"\x00" * 4082)

            tampered = audit_phase161_donor_contracts(work_root=work, force_clean_room=False)
            self.assertFalse(tampered.valid)
            self.assertTrue(tampered.bodydata_header_checked)
            self.assertEqual(tampered.status, STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY)

    # --- 2. Pure Helper Function Unit Tests ---

    def test_05_helper_compute_required_media_write_mb_s(self) -> None:
        self.assertEqual(compute_required_media_write_mb_s(600.0), 93.75)
        self.assertEqual(compute_required_media_write_mb_s(240.0), 37.5)
        self.assertEqual(compute_required_media_write_mb_s(0.0), 0.0)
        self.assertEqual(compute_required_media_write_mb_s(-10.0), 0.0)
        self.assertEqual(compute_required_media_write_mb_s(float("nan")), 0.0)
        self.assertEqual(compute_required_media_write_mb_s(600.0, 0.9), 0.0)

    def test_06_helper_validate_dual_slot_media_bitrate_positive(self) -> None:
        self.assertTrue(validate_dual_slot_media_bitrate())
        self.assertTrue(
            validate_dual_slot_media_bitrate(
                XAVC_SI_4K120P_CODEC_PROFILE,
                600.0,
                slot_a_media_type=MEDIA_TYPE_CFEXPRESS_A,
                slot_a_speed_class="VPG200",
                slot_a_sustained_write_mb_s=200.0,
            )
        )
        # Dual-slot simultaneous CFexpress Type A on both slots
        self.assertTrue(
            validate_dual_slot_media_bitrate(
                XAVC_SI_4K120P_CODEC_PROFILE,
                600.0,
                slot_a_active=True,
                slot_a_media_type=MEDIA_TYPE_CFEXPRESS_A,
                slot_a_speed_class="VPG400",
                slot_a_sustained_write_mb_s=400.0,
                slot_b_active=True,
                slot_b_media_type=MEDIA_TYPE_CFEXPRESS_A,
                slot_b_speed_class="VPG200",
                slot_b_sustained_write_mb_s=200.0,
            )
        )
        # SDXC V90 allowed for non-120p <= 500 Mbps XAVC S-I when sustained >= required
        self.assertTrue(
            validate_dual_slot_media_bitrate(
                "XAVC_SI_4K60P",
                500.0,
                slot_a_active=False,
                slot_b_active=True,
                slot_b_media_type=MEDIA_TYPE_SDXC_V90,
                slot_b_speed_class="V90",
                slot_b_sustained_write_mb_s=90.0,
            )
        )

    def test_07_helper_validate_dual_slot_media_bitrate_rejections(self) -> None:
        # XAVC S-I 4K 120p 600 Mbps MUST be rejected on SDXC V90 (non-CFexpress-A)
        self.assertFalse(
            validate_dual_slot_media_bitrate(
                XAVC_SI_4K120P_CODEC_PROFILE,
                600.0,
                slot_a_media_type=MEDIA_TYPE_SDXC_V90,
                slot_a_speed_class="V90",
                slot_a_sustained_write_mb_s=90.0,
            )
        )
        # Rejected on < V90 (V60 / V30 / UHS1)
        for mtype, sclass, rate in (
            (MEDIA_TYPE_SDXC_V60, "V60", 60.0),
            (MEDIA_TYPE_SDXC_V30, "V30", 30.0),
            (MEDIA_TYPE_SDXC_UHS1, "U1", 10.0),
        ):
            self.assertFalse(
                validate_dual_slot_media_bitrate(
                    XAVC_SI_4K120P_CODEC_PROFILE,
                    600.0,
                    slot_a_media_type=mtype,
                    slot_a_speed_class=sclass,
                    slot_a_sustained_write_mb_s=rate,
                )
            )
        # Dual-slot simultaneous recording where Slot B is SDXC V90
        self.assertFalse(
            validate_dual_slot_media_bitrate(
                XAVC_SI_4K120P_CODEC_PROFILE,
                600.0,
                slot_a_active=True,
                slot_b_active=True,
                slot_b_media_type=MEDIA_TYPE_SDXC_V90,
                slot_b_speed_class="V90",
                slot_b_sustained_write_mb_s=90.0,
            )
        )
        # Active slot not inserted or no active slot
        self.assertFalse(validate_dual_slot_media_bitrate(slot_a_inserted=False))
        self.assertFalse(validate_dual_slot_media_bitrate(slot_a_active=False, slot_b_active=False))
        # Degraded CFexpress card below VPG floor
        self.assertFalse(
            validate_dual_slot_media_bitrate(
                slot_a_speed_class="VPG200",
                slot_a_sustained_write_mb_s=150.0,
            )
        )

    def test_08_helper_validate_card_door_gpio_flush(self) -> None:
        self.assertTrue(validate_card_door_gpio_flush())
        self.assertTrue(
            validate_card_door_gpio_flush(
                card_door_gpio_irq_armed=True,
                card_door_open_event=True,
                fifo_flushed_before_umount=True,
                unflushed_fifo_bytes_on_door_open=0,
                umount_completed_before_power_cut=True,
            )
        )
        self.assertFalse(validate_card_door_gpio_flush(unflushed_fifo_bytes_on_door_open=1))
        self.assertFalse(validate_card_door_gpio_flush(fifo_flushed_before_umount=False))
        self.assertFalse(validate_card_door_gpio_flush(card_door_gpio_irq_armed=False))
        self.assertFalse(
            validate_card_door_gpio_flush(
                card_door_open_event=True, umount_completed_before_power_cut=False
            )
        )
        self.assertFalse(validate_card_door_gpio_flush(unflushed_fifo_bytes_on_door_open=-1))
        self.assertFalse(validate_card_door_gpio_flush(unflushed_fifo_bytes_on_door_open=True))  # type: ignore[arg-type]

    def test_09_helper_validate_user_clip_dirs_untouched(self) -> None:
        self.assertTrue(validate_user_clip_dirs_untouched())
        self.assertFalse(validate_user_clip_dirs_untouched(m4root_mutation_bytes=512))
        self.assertFalse(validate_user_clip_dirs_untouched(xdroot_mutation_bytes=1))
        self.assertFalse(
            validate_user_clip_dirs_untouched(dual_boot_switch_user_clip_untouched=False)
        )
        self.assertFalse(validate_user_clip_dirs_untouched(protected_clip_dirs=("PRIVATE/M4ROOT",)))
        self.assertFalse(validate_user_clip_dirs_untouched(m4root_mutation_bytes=-5))

    def test_10_helper_validate_bodydata_ufu_and_clean_uninstall(self) -> None:
        self.assertTrue(validate_bodydata_ufu_and_clean_uninstall())
        # Present on SD with 47us bypass passes
        self.assertTrue(
            validate_bodydata_ufu_and_clean_uninstall(
                bodydata_dat_present=True,
                bodydata_path="/mnt/sd/BODYDATA.DAT",
                bodydata_ufu_magic_hex=BODYDATA_UFU_MAGIC_HEX_STR,
                stage_a_stock_bypass_triggered=True,
                stage_a_bypass_latency_us=47.0,
            )
        )
        # Present with bypass not triggered or >= 100 us blocked
        self.assertFalse(
            validate_bodydata_ufu_and_clean_uninstall(
                bodydata_dat_present=True,
                stage_a_stock_bypass_triggered=False,
            )
        )
        self.assertFalse(
            validate_bodydata_ufu_and_clean_uninstall(
                bodydata_dat_present=True,
                stage_a_bypass_latency_us=100.0,
            )
        )
        self.assertFalse(
            validate_bodydata_ufu_and_clean_uninstall(
                bodydata_dat_present=True,
                bodydata_ufu_magic_hex="0011223344556677",
            )
        )
        # Official FW update launch requires p15 .orig clean uninstall AND H0 == H3
        self.assertTrue(
            validate_bodydata_ufu_and_clean_uninstall(
                bodydata_dat_present=True,
                official_fw_update_launch_requested=True,
                p15_usr_orig_clean_uninstall_verified=True,
                h0_stock_sha256="b" * 64,
                h3_post_uninstall_sha256="b" * 64,
            )
        )
        self.assertFalse(
            validate_bodydata_ufu_and_clean_uninstall(
                official_fw_update_launch_requested=True,
                p15_usr_orig_clean_uninstall_verified=False,
            )
        )
        self.assertFalse(
            validate_bodydata_ufu_and_clean_uninstall(
                official_fw_update_launch_requested=True,
                p15_usr_orig_clean_uninstall_verified=True,
                h0_stock_sha256="a" * 64,
                h3_post_uninstall_sha256="c" * 64,
            )
        )

    def test_11_helper_validate_5tier_recovery_ladder(self) -> None:
        self.assertTrue(validate_5tier_recovery_ladder())
        self.assertFalse(validate_5tier_recovery_ladder(CANONICAL_5_RECOVERY_TIERS[:4]))
        self.assertFalse(validate_5tier_recovery_ladder(tuple(reversed(CANONICAL_5_RECOVERY_TIERS))))
        self.assertFalse(validate_5tier_recovery_ladder(tier1_sd_47us_ready=False))
        self.assertFalse(validate_5tier_recovery_ladder(tier1_bypass_latency_us=100.0))
        self.assertFalse(validate_5tier_recovery_ladder(tier2_p15_orig_ready=False))
        self.assertFalse(validate_5tier_recovery_ladder(tier3_same_model_bodydata_ready=False))
        self.assertFalse(validate_5tier_recovery_ladder(tier4_uart_el3_ro_ready=False))
        self.assertFalse(validate_5tier_recovery_ladder(tier5_cid_emmc_isp_ready=False))
        self.assertFalse(validate_5tier_recovery_ladder(tier5_cid_matched=False))
        self.assertFalse(validate_5tier_recovery_ladder(destructive_tier_action_requested=True))

    def test_12_helper_validate_fx3_model_id_bodydata_lock(self) -> None:
        self.assertTrue(validate_fx3_model_id_bodydata_lock())
        self.assertTrue(validate_fx3_model_id_bodydata_lock("0x91030080", "ILME-FX3"))
        # Cross-model IDs blocked
        self.assertFalse(validate_fx3_model_id_bodydata_lock(0x91020080, "ILME-FX6"))
        self.assertFalse(validate_fx3_model_id_bodydata_lock("0x91010080", "ILCE-7M4"))
        self.assertFalse(validate_fx3_model_id_bodydata_lock(0x91050080, "ZV-E1"))
        self.assertFalse(validate_fx3_model_id_bodydata_lock(0x91030080, "ILME-FX6"))
        self.assertFalse(validate_fx3_model_id_bodydata_lock(cross_model_bodydata_attempted=True))
        self.assertFalse(validate_fx3_model_id_bodydata_lock(bodydata_ufu_magic_valid=False))
        self.assertFalse(validate_fx3_model_id_bodydata_lock(True))  # type: ignore[arg-type]

    def test_13_helper_validate_cxd90057_el3_readonly_guard(self) -> None:
        self.assertTrue(validate_cxd90057_el3_readonly_guard())
        self.assertTrue(
            validate_cxd90057_el3_readonly_guard(
                soc_name="CXD90057",
                el3_entry_addr="0xfe020000",
                el3_monitor_mode="READ_ONLY",
                el3_uart_tx_bytes=0,
            )
        )
        self.assertFalse(validate_cxd90057_el3_readonly_guard(soc_name="CXD90058"))
        self.assertFalse(validate_cxd90057_el3_readonly_guard(el3_entry_addr=0xFE040000))
        self.assertFalse(validate_cxd90057_el3_readonly_guard(el3_monitor_mode="READ_WRITE"))
        self.assertFalse(validate_cxd90057_el3_readonly_guard(el3_uart_tx_bytes=4))
        self.assertFalse(validate_cxd90057_el3_readonly_guard(el3_payload_transmit_requested=True))
        self.assertFalse(validate_cxd90057_el3_readonly_guard(spi_nor_write_requested=True))
        self.assertFalse(validate_cxd90057_el3_readonly_guard(persistent_emmc_write_requested=True))

    # --- 3. Gate G51 Guard & Evaluator Tests ---

    def test_14_g51_default_safe_pass(self) -> None:
        v, r = evaluate_g51_cfexpress_ufu(force_clean_room=True)
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(v.gate_id, G51_GATE_ID)
        self.assertEqual(v.gate_code, G51_GATE_CODE)
        self.assertEqual(r.status, STATUS_VERIFIED_G51)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertFalse(r.persistent_write_release)

    def test_15_g51_blocks_xavc_si_4k120p_600mbps_on_sdxc_v90_and_v60(self) -> None:
        for mtype, sclass, rate in (
            (MEDIA_TYPE_SDXC_V90, "V90", 90.0),
            (MEDIA_TYPE_SDXC_V60, "V60", 60.0),
            (MEDIA_TYPE_SDXC_V30, "V30", 30.0),
        ):
            res = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
                codec_profile=XAVC_SI_4K120P_CODEC_PROFILE,
                codec_bitrate_mbps=600.0,
                slot_a_media_type=mtype,
                slot_a_speed_class=sclass,
                slot_a_sustained_write_mb_s=rate,
            )
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT, res.violation_codes)
            self.assertFalse(res.dual_slot_bitrate_gate_safe)

    def test_16_g51_blocks_dual_slot_active_non_cfexpress_on_slot_b(self) -> None:
        res = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            slot_a_active=True,
            slot_b_active=True,
            slot_b_media_type=MEDIA_TYPE_SDXC_V90,
            slot_b_speed_class="V90",
            slot_b_sustained_write_mb_s=90.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT)

    def test_17_g51_blocks_unflushed_fifo_on_card_door_open(self) -> None:
        res = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            card_door_open_event=True,
            unflushed_fifo_bytes_on_door_open=65536,
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO, res.violation_codes)
        self.assertFalse(res.card_door_gpio_flush_safe)

    def test_18_g51_blocks_door_open_without_umount_or_irq_armed(self) -> None:
        res1 = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            card_door_open_event=True,
            umount_completed_before_power_cut=False,
        )
        self.assertFalse(res1.valid)
        self.assertIn(STATUS_BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO, res1.violation_codes)

        res2 = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            card_door_gpio_irq_armed=False,
        )
        self.assertFalse(res2.valid)
        self.assertIn(STATUS_BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO, res2.violation_codes)

    def test_19_g51_blocks_user_clip_dir_mutation(self) -> None:
        res_m4 = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            m4root_mutation_bytes=4096
        )
        self.assertFalse(res_m4.valid)
        self.assertIn(STATUS_BLOCKED_G51_USER_CLIP_DIR_MUTATION, res_m4.violation_codes)

        res_xd = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            xdroot_mutation_bytes=1024
        )
        self.assertFalse(res_xd.valid)
        self.assertIn(STATUS_BLOCKED_G51_USER_CLIP_DIR_MUTATION, res_xd.violation_codes)

        res_sw = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            dual_boot_switch_user_clip_untouched=False
        )
        self.assertFalse(res_sw.valid)
        self.assertIn(STATUS_BLOCKED_G51_USER_CLIP_DIR_MUTATION, res_sw.violation_codes)

    def test_20_g51_bodydata_ufu_stage_a_sub100us_bypass_and_slow_fail(self) -> None:
        ok = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            bodydata_dat_present=True,
            bodydata_slot="SLOT_A",
            bodydata_path="/mnt/sd/BODYDATA.DAT",
            bodydata_ufu_magic_hex=BODYDATA_UFU_MAGIC_HEX_STR,
            stage_a_stock_bypass_triggered=True,
            stage_a_bypass_latency_us=47.0,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.bodydata_ufu_preupdate_safe)

        slow = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            bodydata_dat_present=True,
            bodydata_slot="SLOT_B",
            bodydata_path="/mnt/slot_b/BODYDATA.DAT",
            stage_a_stock_bypass_triggered=True,
            stage_a_bypass_latency_us=100.0,
        )
        self.assertFalse(slow.valid)
        self.assertIn(
            STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD,
            slow.violation_codes,
        )

        no_bypass = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            bodydata_dat_present=True,
            stage_a_stock_bypass_triggered=False,
        )
        self.assertFalse(no_bypass.valid)
        self.assertIn(
            STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD,
            no_bypass.violation_codes,
        )

    def test_21_g51_blocks_official_fw_update_without_p15_orig_h0_eq_h3(self) -> None:
        blocked_orig = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            bodydata_dat_present=True,
            official_fw_update_launch_requested=True,
            p15_usr_orig_clean_uninstall_verified=False,
        )
        self.assertFalse(blocked_orig.valid)
        self.assertIn(
            STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD,
            blocked_orig.violation_codes,
        )

        blocked_h0_h3 = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            bodydata_dat_present=True,
            official_fw_update_launch_requested=True,
            p15_usr_orig_clean_uninstall_verified=True,
            h0_stock_sha256="a" * 64,
            h3_post_uninstall_sha256="d" * 64,
        )
        self.assertFalse(blocked_h0_h3.valid)
        self.assertFalse(blocked_h0_h3.h0_equals_h3_verified)
        self.assertIn(
            STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD,
            blocked_h0_h3.violation_codes,
        )

        allowed = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            bodydata_dat_present=True,
            official_fw_update_launch_requested=True,
            p15_usr_orig_clean_uninstall_verified=True,
            h0_stock_sha256="e" * 64,
            h3_post_uninstall_sha256="e" * 64,
        )
        self.assertTrue(allowed.valid)
        self.assertTrue(allowed.h0_equals_h3_verified)

    def test_22_g51_blocks_invalid_telemetry_and_persistent_emmc_request(self) -> None:
        bad = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            codec_bitrate_mbps=float("nan"),
        )
        self.assertFalse(bad.valid)
        self.assertIn(STATUS_BLOCKED_G51_TELEMETRY_INVALID, bad.violation_codes)

        bad_sha = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            h0_stock_sha256="not-a-sha",
        )
        self.assertFalse(bad_sha.valid)
        self.assertIn(STATUS_BLOCKED_G51_TELEMETRY_INVALID, bad_sha.violation_codes)

        v, r = evaluate_g51_cfexpress_ufu(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, v.violation_codes)
        self.assertFalse(r.persistent_emmc_writes_authorized)

    # --- 4. Gate G52 Guard & Evaluator Tests ---

    def test_23_g52_default_safe_pass_and_hard_locks(self) -> None:
        v, r = evaluate_g52_5tier_el3_guard(force_clean_room=True)
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(v.gate_id, G52_GATE_ID)
        self.assertEqual(v.gate_code, G52_GATE_CODE)
        self.assertEqual(r.status, STATUS_VERIFIED_G52)
        self.assertFalse(r.el3_payload_transmit_authorized)
        self.assertFalse(r.spi_nor_write_authorized)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertFalse(r.persistent_write_release)

    def test_24_g52_blocks_incomplete_or_reordered_5tier_ladder(self) -> None:
        res_short = verify_5tier_recovery_model_id_and_el3_ro_guard(
            recovery_ladder=CANONICAL_5_RECOVERY_TIERS[:4]
        )
        self.assertFalse(res_short.valid)
        self.assertIn(STATUS_BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE, res_short.violation_codes)

        res_tier4 = verify_5tier_recovery_model_id_and_el3_ro_guard(
            tier4_uart_el3_ro_ready=False
        )
        self.assertFalse(res_tier4.valid)
        self.assertIn(STATUS_BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE, res_tier4.violation_codes)

        res_cid = verify_5tier_recovery_model_id_and_el3_ro_guard(
            tier5_cid_matched=False
        )
        self.assertFalse(res_cid.valid)
        self.assertIn(STATUS_BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE, res_cid.violation_codes)

        res_destr = verify_5tier_recovery_model_id_and_el3_ro_guard(
            destructive_tier_action_requested=True
        )
        self.assertFalse(res_destr.valid)
        self.assertIn(STATUS_BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE, res_destr.violation_codes)

    def test_25_g52_blocks_cross_model_bodydata_id(self) -> None:
        for bad_id, bad_name in (
            (0x91020080, "ILME-FX6"),
            ("0x91010080", "ILCE-7M4"),
            (0x91050080, "ZV-E1"),
            (0x91030080, "ILME-FX30"),
        ):
            res = verify_5tier_recovery_model_id_and_el3_ro_guard(
                target_model_id=bad_id,
                target_model_name=bad_name,
            )
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH, res.violation_codes)
            self.assertFalse(res.model_id_lock_safe)

    def test_26_g52_blocks_el3_payload_tx_and_spi_nor_and_emmc_writes(self) -> None:
        r1 = verify_5tier_recovery_model_id_and_el3_ro_guard(
            el3_payload_transmit_requested=True
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r1.el3_payload_transmit_authorized)
        self.assertIn(STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED, r1.violation_codes)

        r2 = verify_5tier_recovery_model_id_and_el3_ro_guard(el3_uart_tx_bytes=16)
        self.assertFalse(r2.valid)
        self.assertIn(STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED, r2.violation_codes)

        r3 = verify_5tier_recovery_model_id_and_el3_ro_guard(spi_nor_write_requested=True)
        self.assertFalse(r3.valid)
        self.assertFalse(r3.spi_nor_write_authorized)
        self.assertIn(STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED, r3.violation_codes)

        r4 = verify_5tier_recovery_model_id_and_el3_ro_guard(
            persistent_emmc_write_requested=True
        )
        self.assertFalse(r4.valid)
        self.assertFalse(r4.persistent_emmc_writes_authorized)
        self.assertIn(STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED, r4.violation_codes)

        r5 = verify_5tier_recovery_model_id_and_el3_ro_guard(
            el3_entry_addr=0xFE040000
        )
        self.assertFalse(r5.valid)
        self.assertIn(STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED, r5.violation_codes)

    def test_27_g52_blocks_invalid_telemetry_and_persistent_emmc_request(self) -> None:
        bad = verify_5tier_recovery_model_id_and_el3_ro_guard(
            target_model_id="not_hex",
        )
        self.assertFalse(bad.valid)
        self.assertIn(STATUS_BLOCKED_G52_TELEMETRY_INVALID, bad.violation_codes)

        bad_lat = verify_5tier_recovery_model_id_and_el3_ro_guard(
            tier1_bypass_latency_us=float("inf"),
        )
        self.assertFalse(bad_lat.valid)
        self.assertIn(STATUS_BLOCKED_G52_TELEMETRY_INVALID, bad_lat.violation_codes)

        v, r = evaluate_g52_5tier_el3_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, v.violation_codes)
        self.assertFalse(r.el3_payload_transmit_authorized)
        self.assertFalse(r.spi_nor_write_authorized)
        self.assertFalse(r.persistent_emmc_writes_authorized)

    # --- 5. Unified 52-Gate Master Safety Preflight Tests ---

    def test_28_52gate_offline_default_reports_49_of_52_and_locks_writes(self) -> None:
        report = evaluate_52gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(report.schema, REALHW_CFEXPRESS_UFU_EL3_52GATE_SCHEMA)
        self.assertEqual(report.version, REALHW_CFEXPRESS_UFU_EL3_52GATE_VERSION)
        self.assertEqual(len(report.gates), 52)
        self.assertEqual(report.summary["total_gates"], 52)
        self.assertEqual(report.summary["verified_gates"], 49)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(report.summary["g01_to_g12_verified"], 9)
        self.assertEqual(report.summary["g13_to_g50_verified"], 38)
        self.assertEqual(report.summary["g51_to_g52_verified"], 2)
        self.assertTrue(report.offline_49_gates_verified)
        self.assertFalse(report.all_52_gates_verified)
        self.assertTrue(report.g13_to_g52_all_passed)
        self.assertTrue(report.g51_to_g52_all_passed)
        self.assertFalse(report.dry_run_rehearsal_only)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(report.status, "VERIFIED_49_OF_52_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(report.gates[idx]["passed"])
            self.assertEqual(report.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_29_52gate_dry_run_simulated_backup_52_of_52_keeps_redlines_locked(self) -> None:
        report = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertEqual(len(report.gates), 52)
        self.assertEqual(report.summary["verified_gates"], 52)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(report.all_52_gates_verified)
        self.assertTrue(report.offline_49_gates_verified)
        self.assertTrue(report.g13_to_g52_all_passed)
        self.assertTrue(report.g51_to_g52_all_passed)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(
            report.status, "VERIFIED_ALL_52_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        # Hard-locked even in dry-run green
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)

    def test_30_52gate_clean_room_and_alias_parity(self) -> None:
        r1 = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        r2 = evaluate_52_master_safety_gates(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r1.clean_room_forced)
        self.assertTrue(r1.all_52_gates_verified)
        self.assertEqual(r1.summary, r2.summary)
        self.assertEqual(r1.status, r2.status)
        self.assertEqual(
            r1.master_50_report["schema"], REALHW_UART1V8_IMX510_50GATE_SCHEMA
        )

    def test_31_52gate_propagates_g51_and_g52_failures_and_blocks_h0_h1(self) -> None:
        fail_g51 = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cfexpress_ufu_kwargs={
                "slot_a_media_type": MEDIA_TYPE_SDXC_V90,
                "slot_a_speed_class": "V90",
                "slot_a_sustained_write_mb_s": 90.0,
            },
        )
        self.assertFalse(fail_g51.all_52_gates_verified)
        self.assertFalse(fail_g51.offline_49_gates_verified)
        self.assertFalse(fail_g51.g51_to_g52_all_passed)
        self.assertFalse(fail_g51.h0_h1_trial_entry_allowed)
        self.assertEqual(
            fail_g51.status, STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT
        )

        fail_g52 = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            five_tier_el3_kwargs={
                "target_model_id": 0x91020080,
                "target_model_name": "ILME-FX6",
            },
        )
        self.assertFalse(fail_g52.all_52_gates_verified)
        self.assertFalse(fail_g52.offline_49_gates_verified)
        self.assertFalse(fail_g52.g51_to_g52_all_passed)
        self.assertFalse(fail_g52.h0_h1_trial_entry_allowed)
        self.assertEqual(
            fail_g52.status, STATUS_BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH
        )

    def test_32_52gate_propagates_g49_g50_failures_and_persistent_write_redline(self) -> None:
        fail_g49 = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            uart1v8_isp_kwargs={"uart_io_voltage_mv": 3300.0},
        )
        self.assertFalse(fail_g49.all_52_gates_verified)
        self.assertEqual(
            fail_g49.status, STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE
        )

        fail_g50 = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            imx510_sensor_cal_kwargs={
                "mlut_monitoring_enabled": True,
                "mlut_burn_in_to_xavc_master": True,
            },
        )
        self.assertFalse(fail_g50.all_52_gates_verified)
        self.assertEqual(
            fail_g50.status, STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE
        )

        fail_emmc = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(fail_emmc.all_52_gates_verified)
        self.assertEqual(fail_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(fail_emmc.persistent_emmc_writes_authorized)

    def test_33_52gate_unique_gate_ids_and_50gate_unchanged(self) -> None:
        m50 = evaluate_50gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        m52 = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(len(m50.gates), 50)
        self.assertEqual(len(m52.gates), 52)
        gate_ids = [g["gate_id"] for g in m52.gates]
        self.assertEqual(len(set(gate_ids)), 52)
        self.assertEqual(gate_ids[50], G51_GATE_ID)
        self.assertEqual(gate_ids[51], G52_GATE_ID)

    def test_34_json_serializable_without_raw_binary_leakage(self) -> None:
        report = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        dumped = json.dumps(report.to_dict(), ensure_ascii=False)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["summary"]["verified_gates"], 52)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn("b'\\x89UFU", dumped)

    # --- 6. CLI Tests (fx3_safety.__main__ & module main) ---

    def test_35_cli_verify_g51_cfexpress_ufu_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(
                ["verify-g51-cfexpress-ufu", "--clean-room", "--json"]
            )
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G51)
        self.assertFalse(data["persistent_emmc_writes_authorized"])

    def test_36_cli_verify_g52_5tier_el3_guard_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(
                ["verify-g52-5tier-el3-guard", "--clean-room", "--json"]
            )
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G52)
        self.assertFalse(data["el3_payload_transmit_authorized"])
        self.assertFalse(data["spi_nor_write_authorized"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])

    def test_37_cli_verify_52_gates_offline_and_dry_run(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-52-gates", "--clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=49/52", buf_off.getvalue())
        self.assertIn("overall_ready_for_hardware_attach=False", buf_off.getvalue())
        self.assertIn("el3_payload_transmit_authorized=False", buf_off.getvalue())

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-52-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        data = json.loads(buf_dry.getvalue())
        self.assertTrue(data["all_52_gates_verified"])
        self.assertEqual(data["summary"]["verified_gates"], 52)
        self.assertFalse(data["overall_ready_for_hardware_attach"])
        self.assertFalse(data["el3_payload_transmit_authorized"])
        self.assertFalse(data["spi_nor_write_authorized"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertFalse(data["persistent_write_release"])

    def test_38_module_cli_main_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup"]
            )
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=52/52", out)
        self.assertIn("el3_payload_transmit_authorized=False", out)
        self.assertIn("spi_nor_write_authorized=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    # --- 7. Additional Boundary & Edge-Case Coverage Tests (>= 46 Total) ---

    def test_39_g51_allows_cfexpress_vpg400_and_vpg200_for_4k120p_600mbps(self) -> None:
        for sclass, rate in (("VPG400", 400.0), ("VPG200", 200.0)):
            res = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
                codec_profile=XAVC_SI_4K120P_CODEC_PROFILE,
                codec_bitrate_mbps=600.0,
                slot_a_media_type=MEDIA_TYPE_CFEXPRESS_A,
                slot_a_speed_class=sclass,
                slot_a_sustained_write_mb_s=rate,
            )
            self.assertTrue(res.valid)

    def test_40_g51_blocks_cfexpress_with_non_vpg_speed_class(self) -> None:
        res = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            slot_a_media_type=MEDIA_TYPE_CFEXPRESS_A,
            slot_a_speed_class="V90",
            slot_a_sustained_write_mb_s=90.0,
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT, res.violation_codes)

    def test_41_g51_blocks_sdxc_v90_claimed_high_rate_on_4k120p_600mbps(self) -> None:
        # Even if claimed sustained MB/s is 150, non-CFexpress-A is blocked for 4K 120p 600 Mbps
        res = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            codec_profile=XAVC_SI_4K120P_CODEC_PROFILE,
            codec_bitrate_mbps=600.0,
            slot_a_media_type=MEDIA_TYPE_SDXC_V90,
            slot_a_speed_class="V90",
            slot_a_sustained_write_mb_s=150.0,
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT, res.violation_codes)

    def test_42_g51_blocks_bodydata_ufu_invalid_magic_on_slot_b(self) -> None:
        res = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            bodydata_dat_present=True,
            bodydata_slot="SLOT_B",
            bodydata_path="/mnt/slot_b/BODYDATA.DAT",
            bodydata_ufu_magic_hex="deadbeefdeadbeef",
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.bodydata_ufu_magic_valid)
        self.assertIn(
            STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD,
            res.violation_codes,
        )

    def test_43_g51_candidate_paths_and_protected_dirs_constants(self) -> None:
        self.assertIn("/mnt/sd/BODYDATA.DAT", BODYDATA_SD_CANDIDATE_PATHS)
        self.assertEqual(G51_PROTECTED_CLIP_DIRS, ("PRIVATE/M4ROOT", "XDROOT"))
        self.assertEqual(P15_USR_ORIG_MARKER, "p15:/usr/*.orig")

    def test_44_g52_tier_constants_and_hex_string_normalization(self) -> None:
        self.assertEqual(
            CANONICAL_5_RECOVERY_TIERS,
            (
                RECOVERY_TIER_1_SD_47US,
                RECOVERY_TIER_2_P15_ORIG,
                RECOVERY_TIER_3_BODYDATA_UFU,
                RECOVERY_TIER_4_UART_EL3_RO,
                RECOVERY_TIER_5_CID_EMMC_ISP,
            ),
        )
        res = verify_5tier_recovery_model_id_and_el3_ro_guard(
            target_model_id="0X91030080",
            target_model_name="ilme-fx3",
            el3_entry_addr="0XFE020000",
            el3_monitor_mode="read_only",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.target_model_id_hex, "0x91030080")
        self.assertEqual(res.el3_entry_addr_hex, "0xfe020000")

    def test_45_g52_blocks_bool_injection_in_model_id_and_tx_bytes(self) -> None:
        r1 = verify_5tier_recovery_model_id_and_el3_ro_guard(
            target_model_id=True,  # type: ignore[arg-type]
        )
        self.assertFalse(r1.valid)
        self.assertIn(STATUS_BLOCKED_G52_TELEMETRY_INVALID, r1.violation_codes)

        r2 = verify_5tier_recovery_model_id_and_el3_ro_guard(
            el3_uart_tx_bytes=False,  # type: ignore[arg-type]
        )
        # Note: in Python bool is subclass of int; _is_non_negative_int rejects bool!
        self.assertFalse(r2.valid)
        self.assertIn(STATUS_BLOCKED_G52_TELEMETRY_INVALID, r2.violation_codes)

    def test_46_g51_blocks_bool_injection_in_mutation_bytes_and_fifo(self) -> None:
        r1 = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            unflushed_fifo_bytes_on_door_open=False,  # type: ignore[arg-type]
        )
        self.assertFalse(r1.valid)
        self.assertIn(STATUS_BLOCKED_G51_TELEMETRY_INVALID, r1.violation_codes)

        r2 = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
            m4root_mutation_bytes=True,  # type: ignore[arg-type]
        )
        self.assertFalse(r2.valid)
        self.assertIn(STATUS_BLOCKED_G51_TELEMETRY_INVALID, r2.violation_codes)

    def test_47_clean_room_env_var_overrides_local_donors(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            report = evaluate_52gate_preflight(
                DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
            )
            self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(report.clean_room_forced)
            self.assertTrue(report.all_52_gates_verified)
            self.assertEqual(report.summary["verified_gates"], 52)
            self.assertFalse(report.el3_payload_transmit_authorized)
            self.assertFalse(report.spi_nor_write_authorized)
            self.assertFalse(report.persistent_emmc_writes_authorized)

    def test_48_text_cli_output_for_g51_and_g52(self) -> None:
        buf1 = io.StringIO()
        with contextlib.redirect_stdout(buf1):
            rc1 = package_cli_main(["verify-g51-cfexpress-ufu", "--clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn(G51_GATE_ID, buf1.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf1.getvalue())

        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = package_cli_main(["verify-g52-5tier-el3-guard", "--clean-room"])
        self.assertEqual(rc2, 0)
        self.assertIn(G52_GATE_ID, buf2.getvalue())
        self.assertIn("el3_payload_transmit_authorized=False", buf2.getvalue())
        self.assertIn("spi_nor_write_authorized=False", buf2.getvalue())


if __name__ == "__main__":
    unittest.main()
