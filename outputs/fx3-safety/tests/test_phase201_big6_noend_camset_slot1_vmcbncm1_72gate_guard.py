"""Fast dual-mode unit tests for Phase 201 — Real-Hardware Main Track Part 23:
Gate G71 (`ILME-FX3` `Ver. 7.02` `BIG6` `[Mode Settings] = [Fixed/Variable]` &
`[Home (Lower Left)] = [Aperture / ND Filter]` Zero Physical e-ND Actuator Firewall
`e_nd_actuator_tx_count == 0` + Slot-1 `CAMSET01..10.DAT` Dual-Media Root Split,
`MR` Mode Lockout, Cross-Model `.DAT` Header Rejection, and Stage-B
`/tmp/fx6_camset_overlay` Sandboxing with `H0 == H3`),
Gate G72 (`VMC-BNCM1` `A-5051-506-A` Body-Only `Multi/Micro USB` `TC IN` `>= 10.0s`
`EXT-LK`, `XLR-H1` Handle Side Micro-USB Block, Reverse BNC `TC OUT` `EOPNOTSUPP`
Mask, and Digital Type-A HDMI-Only `TC OUT` Guard Auto-Disabled in `S&Q`),
and 72-Gate Master Preflight (`G01..G72` / `verify-72-gates` / `run_72_gate_preflight`).
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
from typing import Dict, List, Tuple
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
    evaluate_60gate_preflight,
)
from fx3_safety.realhw_emount_info3d_hdmi_braw_and_62gate_guard import (
    evaluate_62gate_preflight,
)
from fx3_safety.realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    evaluate_64gate_preflight,
)
from fx3_safety.realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard import (
    evaluate_66gate_preflight,
)
from fx3_safety.realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard import (
    evaluate_68gate_preflight,
)
from fx3_safety.realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard import (
    STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2,
    STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE,
    evaluate_70gate_preflight,
)
from fx3_safety.realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard import (
    ALLOWED_BIG6_HOME_LOWER_LEFT_ITEMS,
    ALLOWED_TC_OUT_TRANSPORT_G72,
    ALLOWED_VIRTUAL_ND_METADATA_LABELS,
    BIG6_EXACT_6_CELL_LAYOUT,
    BIG6_HOME_LOWER_LEFT_APERTURE,
    BIG6_HOME_LOWER_LEFT_MENU_PATH,
    BIG6_HOME_LOWER_LEFT_ND_FILTER,
    BIG6_REQUIRED_MODE_SETTING,
    BIG6_STATUS_BAR_REGION_INDEX,
    BODY_MULTI_MICRO_USB_PORT,
    CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
    CAMSET_MAX_FILES_PER_CARD,
    CAMSET_REQUIRED_SLOT_INDEX,
    CFEXPRESS_A_CAMSET_ROOT_DIR,
    DEFAULT_H0_CAMSET_SURFACE_SHA256,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EXT_LK_STATE_ACQUIRING,
    EXT_LK_STATE_LOCKED,
    EXT_LK_STATE_RELEASED,
    FORBIDDEN_STAGEB_CAMSET_WRITE_PATHS,
    FX3_BIG6_MIN_FW_VERSION,
    FX3_DEFAULT_FW_VERSION_G71,
    FX6_MODEL_NAME_G71,
    G71,
    G71_GATE_CODE,
    G71_GATE_ID,
    G72,
    G72_GATE_CODE,
    G72_GATE_ID,
    GATE_G71_FX3_BIG6_ZERO_END_ACTUATOR_AND_SLOT1_CAMSET_FIREWALL,
    GATE_G72_VMCBNCM1_BODY_TCIN_XLRH1_BLOCK_AND_HDMI_TCOUT_GUARD,
    HDMI_TC_OUT_MENU_PATH,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    INCOMPATIBLE_CAMSET_MODEL_HEADERS,
    MIN_VMC_BNCM1_EXT_LK_SECONDS,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE201_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_BIG6_NOEND_CAMSET_SLOT1_VMCBNCM1_72GATE_SCHEMA,
    REALHW_BIG6_NOEND_CAMSET_SLOT1_VMCBNCM1_72GATE_VERSION,
    REJECTED_TC_OUT_TRANSPORTS_G72,
    REJECTED_VMC_BNCM1_PORTS,
    REQUIRED_STAGEB_CAMSET_OVERLAY_DIR,
    SD_CAMSET_ROOT_DIR,
    SPI_NOR_WRITE_AUTHORIZED,
    STAGEB_BNC_TCOUT_MASK_ERRNO_NAME,
    STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN,
    STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID,
    STATUS_BLOCKED_G71_CAMSET_CROSS_MODEL_HEADER_REJECTED,
    STATUS_BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED,
    STATUS_BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH,
    STATUS_BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN,
    STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT,
    STATUS_BLOCKED_G71_TELEMETRY_INVALID,
    STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN,
    STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED,
    STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION,
    STATUS_BLOCKED_G72_TELEMETRY_INVALID,
    STATUS_BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE201_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G71,
    STATUS_VERIFIED_G72,
    STATUS_VERIFIED_SAFE,
    TC_DIRECTION_IN_ONLY,
    TC_MAKE_PRESET_REQUIRED,
    TC_RUN_FREE_RUN_REQUIRED,
    VALID_CAMSET_FILENAMES,
    VMC_BNCM1_ADAPTER_MODEL,
    VMC_BNCM1_CABLE_LENGTH_M,
    VMC_BNCM1_SONY_PART_NUMBER,
    XLR_H1_HANDLE_MICRO_USB_PORT,
    Master72GateReport,
    audit_phase201_donor_contracts,
    compute_vmcbncm1_ext_lk_state,
    evaluate_72_master_safety_gates,
    evaluate_72gate_preflight,
    evaluate_g71_big6_noend_camset_slot1_guard,
    evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard,
    main as module_cli_main,
    resolve_fx3_camset_slot1_directory,
    run_72_gate_preflight,
    validate_digital_hdmi_type_a_only_tcout,
    validate_fx3_big6_home_zero_end_actuator,
    validate_slot1_camset_dualmedia_and_crossmodel_firewall,
    validate_vmcbncm1_body_multi_usb_tcin_and_ext_lk,
    verify_fx3_big6_zero_end_and_slot1_camset_guard,
    verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard,
)


def _create_synthetic_donor_tree(
    base: Path,
    *,
    corrupt_saveload: bool = False,
) -> Tuple[Path, Dict[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]]:
    patched_specs: Dict[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]] = {}
    for key, (body, rel_path, _exp_size, _sha, markers, lbl) in PINNED_PHASE201_DONOR_SPECS.items():
        # Keep synthetic blobs small & fast (4096 B) when patching PINNED_PHASE201_DONOR_SPECS
        synth_size = 4096
        p = base / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = bytearray(synth_size)
        cursor = 0
        for tok in markers:
            if corrupt_saveload and key == "fx3_saveload_so" and tok == b"SaveLoadSettings":
                tok = b"CORRUPTED_MARKER"
            payload[cursor : cursor + len(tok)] = tok
            cursor += len(tok) + 16
        raw = bytes(payload)
        p.write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
        patched_specs[key] = (
            body,
            rel_path,
            synth_size if not corrupt_saveload else synth_size + 1,
            sha,
            markers,
            lbl,
        )
    return base, patched_specs


class Phase201Big6NoEndCamsetSlot1VmcBncm172GateGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_dry_70 = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        cls.clean_off_70 = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        t0 = time.monotonic()
        cls.default_dry_72 = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        cls.default_dry_elapsed = time.monotonic() - t0

    # --- 1. Hard-Locked Safety Redlines & Public Package Exports ---

    def test_01_hard_locked_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(
            G71, GATE_G71_FX3_BIG6_ZERO_END_ACTUATOR_AND_SLOT1_CAMSET_FIREWALL
        )
        self.assertEqual(
            G72, GATE_G72_VMCBNCM1_BODY_TCIN_XLRH1_BLOCK_AND_HDMI_TCOUT_GUARD
        )
        self.assertIs(run_72_gate_preflight, evaluate_72gate_preflight)
        self.assertIs(evaluate_72_master_safety_gates, evaluate_72gate_preflight)
        for name in (
            "G71",
            "G72",
            "Master72GateReport",
            "run_72_gate_preflight",
            "evaluate_72gate_preflight",
            "evaluate_72_master_safety_gates",
            "evaluate_g71_big6_noend_camset_slot1_guard",
            "evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard",
            "realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, name), f"missing fx3_safety.{name}")
            self.assertIn(name, fx3_safety.__all__)

    def test_02_schema_version_and_wave26_phase201_constants(self) -> None:
        self.assertEqual(
            REALHW_BIG6_NOEND_CAMSET_SLOT1_VMCBNCM1_72GATE_SCHEMA,
            "fx3-realhw-big6-noend-camset-slot1-vmcbncm1-72gate-preflight-v1",
        )
        self.assertEqual(
            REALHW_BIG6_NOEND_CAMSET_SLOT1_VMCBNCM1_72GATE_VERSION, "1.0.0"
        )
        self.assertEqual(FX3_BIG6_MIN_FW_VERSION, "7.00")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_G71, "7.02")
        self.assertEqual(BIG6_REQUIRED_MODE_SETTING, "FIXED_VARIABLE")
        self.assertEqual(len(BIG6_EXACT_6_CELL_LAYOUT), 6)
        self.assertEqual(BIG6_STATUS_BAR_REGION_INDEX, 7)
        self.assertEqual(
            ALLOWED_BIG6_HOME_LOWER_LEFT_ITEMS,
            (BIG6_HOME_LOWER_LEFT_APERTURE, BIG6_HOME_LOWER_LEFT_ND_FILTER),
        )
        self.assertEqual(CAMSET_REQUIRED_SLOT_INDEX, 1)
        self.assertEqual(CAMSET_MAX_FILES_PER_CARD, 10)
        self.assertEqual(len(VALID_CAMSET_FILENAMES), 10)
        self.assertEqual(VALID_CAMSET_FILENAMES[0], "CAMSET01.DAT")
        self.assertEqual(VALID_CAMSET_FILENAMES[-1], "CAMSET10.DAT")
        self.assertEqual(SD_CAMSET_ROOT_DIR, "/PRIVATE/SONY/SETTING/FX3/CAMSET/")
        self.assertEqual(CFEXPRESS_A_CAMSET_ROOT_DIR, "/SONY/SETTING/FX3/CAMSET/")
        self.assertEqual(REQUIRED_STAGEB_CAMSET_OVERLAY_DIR, "/tmp/fx6_camset_overlay")
        self.assertEqual(len(CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS), 5)
        self.assertEqual(
            INCOMPATIBLE_CAMSET_MODEL_HEADERS,
            (FX3_MODEL_NAME, FX3A_MODEL_NAME, FX6_MODEL_NAME_G71),
        )
        self.assertEqual(VMC_BNCM1_ADAPTER_MODEL, "VMC-BNCM1")
        self.assertEqual(VMC_BNCM1_SONY_PART_NUMBER, "A-5051-506-A")
        self.assertEqual(VMC_BNCM1_CABLE_LENGTH_M, 0.2)
        self.assertEqual(MIN_VMC_BNCM1_EXT_LK_SECONDS, 10.0)
        self.assertEqual(STAGEB_BNC_TCOUT_MASK_ERRNO_NAME, "EOPNOTSUPP")
        self.assertEqual(ALLOWED_TC_OUT_TRANSPORT_G72, "TYPE_A_HDMI")
        self.assertIn(XLR_H1_HANDLE_MICRO_USB_PORT, REJECTED_VMC_BNCM1_PORTS)
        self.assertIn("12G_SDI", REJECTED_TC_OUT_TRANSPORTS_G72)

    # --- 2. Strictly Read-Only (O_RDONLY) Donor Contract Audit ---

    def test_03_donor_audit_default_mode_respects_environment(self) -> None:
        audit = audit_phase201_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(audit.valid, audit.errors)
        self.assertEqual(audit.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 5)
        self.assertEqual(audit.missing_markers, ())
        env_clean = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if env_clean:
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.files_inspected, 0)
        else:
            self.assertIn(
                audit.verification_mode,
                ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
            )

    def test_04_donor_audit_forced_clean_room_and_missing_work_root_fallback(self) -> None:
        clean = audit_phase201_donor_contracts(force_clean_room=True)
        self.assertTrue(clean.valid)
        self.assertEqual(clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(clean.files_inspected, 0)
        self.assertEqual(len(clean.sha256_by_artifact), 5)

        with tempfile.TemporaryDirectory() as tmp:
            missing_work = audit_phase201_donor_contracts(
                work_root=Path(tmp),
                force_clean_room=False,
            )
            self.assertTrue(missing_work.valid)
            self.assertEqual(missing_work.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(missing_work.files_inspected, 0)

    def test_05_donor_audit_synthetic_tree_valid_and_o_rdonly_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work, specs = _create_synthetic_donor_tree(Path(tmp), corrupt_saveload=False)
            opened_flags: List[int] = []
            real_open = os.open

            def spy_open(path: str, flags: int, *args: object) -> int:
                opened_flags.append(flags)
                return real_open(path, flags, *args)

            with patch(
                "fx3_safety.realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard.PINNED_PHASE201_DONOR_SPECS",
                specs,
            ), patch(
                "fx3_safety.realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard.os.open",
                side_effect=spy_open,
            ):
                res = audit_phase201_donor_contracts(
                    work_root=work,
                    force_clean_room=False,
                )
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.files_inspected, 5)
            self.assertEqual(opened_flags, [os.O_RDONLY] * 5)

    def test_06_donor_audit_corrupted_marker_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work, specs = _create_synthetic_donor_tree(Path(tmp), corrupt_saveload=True)
            with patch(
                "fx3_safety.realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard.PINNED_PHASE201_DONOR_SPECS",
                specs,
            ):
                res = audit_phase201_donor_contracts(
                    work_root=work,
                    force_clean_room=False,
                )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE201_DONOR_INTEGRITY)
            self.assertFalse(res.fx3_contracts_verified)
            self.assertGreaterEqual(len(res.missing_markers), 1)

    # --- 3. Gate G71: BIG6 [Home (Lower Left)] Zero Physical e-ND Actuator Firewall ---

    def test_07_g71_default_big6_aperture_and_slot1_sd_camset_valid(self) -> None:
        res = verify_fx3_big6_zero_end_and_slot1_camset_guard()
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G71)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.canonical_mode_settings, BIG6_REQUIRED_MODE_SETTING)
        self.assertEqual(
            res.canonical_home_lower_left_item, BIG6_HOME_LOWER_LEFT_APERTURE
        )
        self.assertEqual(res.home_lower_left_menu_path, BIG6_HOME_LOWER_LEFT_MENU_PATH)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)
        self.assertFalse(res.fx3_has_physical_end_hardware)
        self.assertEqual(res.camset_slot_index, 1)
        self.assertEqual(res.camset_directory, SD_CAMSET_ROOT_DIR)
        self.assertTrue(res.stageb_camset_sandboxed_in_tmp)
        self.assertTrue(res.h0_equals_h3_camset_surface)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_08_g71_big6_virtual_nd_filter_metadata_only_all_labels_valid(self) -> None:
        for lbl in ALLOWED_VIRTUAL_ND_METADATA_LABELS:
            res = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                home_lower_left_item="ND Filter",
                nd_filter_virtual_metadata_only=True,
                virtual_nd_reference_label=lbl,
                e_nd_actuator_tx_count=0,
                fx6_variable_nd_motor_cmd_sent=False,
            )
            self.assertTrue(res.valid, f"failed for virtual ND label {lbl}: {res.errors}")
            self.assertEqual(
                res.canonical_home_lower_left_item, BIG6_HOME_LOWER_LEFT_ND_FILTER
            )

    def test_09_g71_blocks_nonzero_end_actuator_tx_count(self) -> None:
        for tx_cnt in (1, 4, 128):
            res = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                e_nd_actuator_tx_count=tx_cnt,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN)
            self.assertIn(
                STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN, res.violation_codes
            )

    def test_10_g71_blocks_fx6_variable_nd_motor_cmd_or_physical_end_claim(self) -> None:
        r_cmd = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            fx6_variable_nd_motor_cmd_sent=True,
        )
        self.assertFalse(r_cmd.valid)
        self.assertEqual(r_cmd.status, STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN)

        r_hw = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            fx3_has_physical_end_hardware=True,
        )
        self.assertFalse(r_hw.valid)
        self.assertEqual(r_hw.status, STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN)

        r_non_virt = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            home_lower_left_item="ND Filter",
            nd_filter_virtual_metadata_only=False,
        )
        self.assertFalse(r_non_virt.valid)
        self.assertEqual(
            r_non_virt.status, STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN
        )

    def test_11_g71_blocks_pre_700_firmware_or_non_fx3_body_model(self) -> None:
        for bad_fw in ("6.01", "5.00", "2.05", "Ver. 6.00"):
            r_fw = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                firmware_version=bad_fw,
            )
            self.assertFalse(r_fw.valid, f"expected fail for fw={bad_fw}")
            self.assertEqual(
                r_fw.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
            )

        r_body = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            body_model_name="ILME-FX6",
        )
        self.assertFalse(r_body.valid)
        self.assertEqual(
            r_body.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
        )

        r_id = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            body_model_id=0x91030099,
        )
        self.assertFalse(r_id.valid)
        self.assertEqual(
            r_id.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
        )

    def test_12_g71_blocks_invalid_big6_mode_settings_home_key_or_topology(self) -> None:
        r_mode = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            big6_home_active=True,
            mode_settings="Standard Movie",
        )
        self.assertFalse(r_mode.valid)
        self.assertEqual(
            r_mode.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
        )

        r_key = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            big6_home_active=True,
            custom_key_home_assigned=False,
        )
        self.assertFalse(r_key.valid)
        self.assertEqual(
            r_key.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
        )

        r_cells = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            big6_home_active=True,
            big6_cell_count=5,
        )
        self.assertFalse(r_cells.valid)
        self.assertEqual(
            r_cells.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
        )

        r_bar = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            big6_home_active=True,
            big6_status_bar_region_present=False,
        )
        self.assertFalse(r_bar.valid)
        self.assertEqual(
            r_bar.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
        )

    def test_13_g71_blocks_invalid_home_lower_left_or_virtual_nd_label(self) -> None:
        r_ll = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            home_lower_left_item="Audio Level",
        )
        self.assertFalse(r_ll.valid)
        self.assertEqual(
            r_ll.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
        )

        r_lbl = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            home_lower_left_item="ND Filter",
            virtual_nd_reference_label="1/256_MOTOR",
        )
        self.assertFalse(r_lbl.valid)
        self.assertEqual(
            r_lbl.status, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID
        )

    def test_14_g71_inactive_big6_allows_non_fixed_variable_mode_if_end_tx_zero(self) -> None:
        ok, code, errs = validate_fx3_big6_home_zero_end_actuator(
            big6_home_active=False,
            mode_settings="Standard",
            custom_key_home_assigned=False,
            e_nd_actuator_tx_count=0,
        )
        self.assertTrue(ok, errs)
        self.assertEqual(code, STATUS_SAFE)

    # --- 4. Gate G71: Slot-1 CAMSET01..10.DAT Dual-Media & Cross-Model Firewall ---

    def test_15_resolve_fx3_camset_slot1_directory_sd_vs_cfexpress_a(self) -> None:
        for sd_alias in ("SD", "SDHC", "SDXC", "sd_card", "SDXC_V90"):
            self.assertEqual(
                resolve_fx3_camset_slot1_directory(sd_alias), SD_CAMSET_ROOT_DIR
            )
        for cfe_alias in ("CFexpress-A", "CFexpress Type A", "CFE_A", "cfexpress_a"):
            self.assertEqual(
                resolve_fx3_camset_slot1_directory(cfe_alias),
                CFEXPRESS_A_CAMSET_ROOT_DIR,
            )
        self.assertEqual(
            resolve_fx3_camset_slot1_directory("XQD_CARD"), "INVALID_MEDIA_TYPE"
        )

    def test_16_g71_slot1_cfexpress_a_camset01_to_10_all_valid(self) -> None:
        for idx in range(1, 11):
            fname = f"CAMSET{idx:02d}.DAT"
            res = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                camset_slot="Slot 1",
                media_type="CFexpress-A",
                camset_directory=CFEXPRESS_A_CAMSET_ROOT_DIR,
                camset_filename=fname,
                camset_card_file_count=idx,
            )
            self.assertTrue(res.valid, f"failed for {fname}: {res.errors}")
            self.assertEqual(res.canonical_media_type, "CFEXPRESS_A")
            self.assertEqual(res.camset_directory, CFEXPRESS_A_CAMSET_ROOT_DIR)

    def test_17_g71_blocks_slot2_or_invalid_slot_camset(self) -> None:
        for bad_slot in (2, "Slot 2", "SLOT_2", "SLOT_B", 0, 3, "Slot_9"):
            res = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                camset_slot=bad_slot,
            )
            self.assertFalse(res.valid, f"expected fail for slot={bad_slot!r}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN
            )

    def test_18_g71_mr_recall_mode_lockout_vs_greyed_out_idle(self) -> None:
        r_attempt = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            mr_recall_mode_active=True,
            camset_operation_in_mr_attempted=True,
            camset_greyed_out_in_mr=True,
        )
        self.assertFalse(r_attempt.valid)
        self.assertEqual(
            r_attempt.status, STATUS_BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN
        )

        r_not_greyed = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            mr_recall_mode_active=True,
            camset_operation_in_mr_attempted=False,
            camset_greyed_out_in_mr=False,
        )
        self.assertFalse(r_not_greyed.valid)
        self.assertEqual(
            r_not_greyed.status, STATUS_BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN
        )

        r_idle_ok = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            mr_recall_mode_active=True,
            camset_operation_in_mr_attempted=False,
            camset_greyed_out_in_mr=True,
        )
        self.assertTrue(r_idle_ok.valid, r_idle_ok.errors)

    def test_19_g71_blocks_camset_filename_count_ceiling_or_unstripped_items(self) -> None:
        for bad_name in ("CAMSET00.DAT", "CAMSET11.DAT", "CAMSET1.DAT", "CAMSET01.BIN", "camset01.dat"):
            res = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                camset_filename=bad_name,
            )
            self.assertFalse(res.valid, f"expected fail for {bad_name!r}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED
            )

        for bad_cnt in (-1, 11, 99):
            res_cnt = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                camset_card_file_count=bad_cnt,
            )
            self.assertFalse(res_cnt.valid)
            self.assertEqual(
                res_cnt.status, STATUS_BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED
            )

        res_unstripped = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            excluded_machine_bound_items_stripped=False,
        )
        self.assertFalse(res_unstripped.valid)
        self.assertEqual(
            res_unstripped.status,
            STATUS_BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED,
        )

    def test_20_g71_blocks_swapped_sd_vs_cfexpress_a_camset_root_paths(self) -> None:
        # CFexpress-A path on SD card -> rejected
        r_sd_wrong = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            media_type="SDXC",
            camset_directory=CFEXPRESS_A_CAMSET_ROOT_DIR,
        )
        self.assertFalse(r_sd_wrong.valid)
        self.assertEqual(
            r_sd_wrong.status, STATUS_BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH
        )

        # SD /PRIVATE/... path on CFexpress Type A -> rejected
        r_cfe_wrong = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            media_type="CFexpress-A",
            camset_directory=SD_CAMSET_ROOT_DIR,
        )
        self.assertFalse(r_cfe_wrong.valid)
        self.assertEqual(
            r_cfe_wrong.status, STATUS_BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH
        )

        # FX6 directory on FX3 card -> rejected
        r_fx6_dir = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            media_type="SDXC",
            camset_directory="/PRIVATE/SONY/SETTING/FX6/CAMSET/",
        )
        self.assertFalse(r_fx6_dir.valid)
        self.assertEqual(
            r_fx6_dir.status, STATUS_BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH
        )

    def test_21_g71_blocks_cross_model_fx3a_and_fx6_camset_dat_headers(self) -> None:
        for cross_hdr in ("ILME-FX3A", "FX3A", "ILME-FX6", "FX6", "ILME-FX30"):
            res = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                camset_dat_header_model=cross_hdr,
            )
            self.assertFalse(res.valid, f"expected fail for header={cross_hdr!r}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G71_CAMSET_CROSS_MODEL_HEADER_REJECTED
            )
            self.assertTrue(res.cross_model_header_rejected)

    def test_22_g71_blocks_stageb_overlay_escape_slot1_overwrite_p2_write_and_h0_h3_drift(
        self,
    ) -> None:
        for bad_overlay in (
            "/PRIVATE/SONY/SETTING/FX3/CAMSET",
            "/SONY/SETTING/FX3/CAMSET",
            "p2:/setting/camset",
            "/setting/camset",
            "/dev/nflasha2",
            "/var/tmp/not_allowed",
        ):
            r_ov = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                stageb_camset_overlay_path=bad_overlay,
            )
            self.assertFalse(r_ov.valid, f"expected fail for overlay={bad_overlay!r}")
            self.assertEqual(
                r_ov.status, STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT
            )

        r_slot1_ow = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            stageb_slot1_fx3_camset_overwrite_attempted=True,
        )
        self.assertFalse(r_slot1_ow.valid)
        self.assertEqual(
            r_slot1_ow.status, STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT
        )

        r_p2_w = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            stageb_p2_setting_write_attempted=True,
        )
        self.assertFalse(r_p2_w.valid)
        self.assertEqual(
            r_p2_w.status, STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT
        )

        r_p2_bytes = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            p2_setting_mutation_bytes=64,
        )
        self.assertFalse(r_p2_bytes.valid)
        self.assertEqual(
            r_p2_bytes.status, STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT
        )

        r_drift = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            h0_camset_surface_sha256="a" * 64,
            h3_camset_surface_sha256="b" * 64,
        )
        self.assertFalse(r_drift.valid)
        self.assertFalse(r_drift.h0_equals_h3_camset_surface)
        self.assertEqual(
            r_drift.status, STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT
        )

    def test_23_g71_accepts_subpath_under_tmp_fx6_camset_overlay_and_hex_model_id(
        self,
    ) -> None:
        res = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            body_model_id="0x91030080",
            stageb_camset_overlay_path="/tmp/fx6_camset_overlay/CAMSET01.DAT",
        )
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.stageb_camset_sandboxed_in_tmp)
        self.assertEqual(res.body_model_id_hex, "0x91030080")

    def test_24_g71_rejects_malformed_telemetry_types(self) -> None:
        for bad_kwargs in (
            {"e_nd_actuator_tx_count": -1},
            {"e_nd_actuator_tx_count": True},  # type: ignore[dict-item]
            {"camset_slot": True},  # type: ignore[dict-item]
            {"firmware_version": ""},
            {"p2_setting_mutation_bytes": -4},
            {"big6_home_active": "yes"},  # type: ignore[dict-item]
        ):
            res = verify_fx3_big6_zero_end_and_slot1_camset_guard(**bad_kwargs)
            self.assertFalse(res.valid, f"expected invalid telemetry for {bad_kwargs}")
            self.assertEqual(res.status, STATUS_BLOCKED_G71_TELEMETRY_INVALID)

    def test_25_evaluate_g71_blocks_persistent_emmc_write_request(self) -> None:
        verdict, res = evaluate_g71_big6_noend_camset_slot1_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    # --- 5. Gate G72: VMC-BNCM1 Body-Only TC IN (EXT-LK), XLR-H1 Block & HDMI TC OUT ---

    def test_26_g72_default_vmcbncm1_body_tcin_and_hdmi_tcout_valid(self) -> None:
        res = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard()
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G72)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.adapter_model, VMC_BNCM1_ADAPTER_MODEL)
        self.assertEqual(res.adapter_part_number, VMC_BNCM1_SONY_PART_NUMBER)
        self.assertEqual(res.canonical_usb_port, BODY_MULTI_MICRO_USB_PORT)
        self.assertTrue(res.xlr_h1_handle_micro_usb_blocked)
        self.assertEqual(res.modeled_ext_lk_state, EXT_LK_STATE_LOCKED)
        self.assertTrue(res.ext_lk_locked)
        self.assertEqual(res.hdmi_tc_out_menu_path, HDMI_TC_OUT_MENU_PATH)
        self.assertEqual(res.canonical_tc_out_transport, ALLOWED_TC_OUT_TRANSPORT_G72)
        self.assertTrue(res.tc_out_enabled)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_27_compute_vmcbncm1_ext_lk_state_physics(self) -> None:
        # < 10.0s -> acquiring
        self.assertEqual(
            compute_vmcbncm1_ext_lk_state(continuous_ltc_lock_seconds=9.9),
            EXT_LK_STATE_ACQUIRING,
        )
        # >= 10.0s in Movie + Preset + Free Run -> EXT-LK
        self.assertEqual(
            compute_vmcbncm1_ext_lk_state(continuous_ltc_lock_seconds=10.0),
            EXT_LK_STATE_LOCKED,
        )
        # Switched to S&Q -> released immediately
        self.assertEqual(
            compute_vmcbncm1_ext_lk_state(
                shooting_mode="S&Q", continuous_ltc_lock_seconds=30.0
            ),
            EXT_LK_STATE_RELEASED,
        )
        self.assertEqual(
            compute_vmcbncm1_ext_lk_state(
                sq_mode_triggered=True, continuous_ltc_lock_seconds=30.0
            ),
            EXT_LK_STATE_RELEASED,
        )
        # Changed TC Make/Run/Preset -> released immediately
        self.assertEqual(
            compute_vmcbncm1_ext_lk_state(
                tc_make_run_preset_changed_after_lock=True,
                continuous_ltc_lock_seconds=30.0,
            ),
            EXT_LK_STATE_RELEASED,
        )
        self.assertEqual(
            compute_vmcbncm1_ext_lk_state(tc_make="Regenerate"),
            EXT_LK_STATE_RELEASED,
        )
        self.assertEqual(
            compute_vmcbncm1_ext_lk_state(tc_run="Rec Run"),
            EXT_LK_STATE_RELEASED,
        )

    def test_28_g72_blocks_xlrh1_handle_micro_usb_vmcbncm1_connection(self) -> None:
        r_flag = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            xlr_h1_handle_micro_usb_connected=True,
        )
        self.assertFalse(r_flag.valid)
        self.assertEqual(
            r_flag.status, STATUS_BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN
        )
        self.assertFalse(r_flag.xlr_h1_handle_micro_usb_blocked)

        for bad_port in (
            "XLR-H1 Handle Micro-USB",
            "XLR_H1_MICRO_USB",
            "HANDLE_MICRO_USB",
            "TOP_HANDLE_MICRO_USB",
            "MISHOE_HANDLE_USB",
            "USB Type-C",
            "UNKNOWN_PORT",
        ):
            r_port = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
                connected_usb_port=bad_port,
            )
            self.assertFalse(r_port.valid, f"expected fail for port={bad_port!r}")
            self.assertEqual(
                r_port.status,
                STATUS_BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN,
            )

    def test_29_g72_blocks_reverse_ltc_bnc_tcout_on_multi_micro_usb(self) -> None:
        for bad_dir in ("TC OUT", "BIDIRECTIONAL", "LTC_OUT", "TC_IN_OUT"):
            r_dir = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
                tc_signal_direction=bad_dir,
            )
            self.assertFalse(r_dir.valid, f"expected fail for dir={bad_dir!r}")
            self.assertEqual(
                r_dir.status, STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN
            )

        r_drive = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            multi_usb_ltc_bnc_tcout_drive_attempted=True,
        )
        self.assertFalse(r_drive.valid)
        self.assertEqual(
            r_drive.status, STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN
        )

        r_unmasked = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            stageb_fx6_bnc_tcout_masked_eopnotsupp=False,
        )
        self.assertFalse(r_unmasked.valid)
        self.assertEqual(
            r_unmasked.status, STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN
        )

    def test_30_g72_blocks_insufficient_lock_seconds_or_wrong_tc_make_run_mode(
        self,
    ) -> None:
        for short_s in (0.0, 4.5, 9.99):
            r_short = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
                continuous_ltc_lock_seconds=short_s,
            )
            self.assertFalse(r_short.valid)
            self.assertEqual(
                r_short.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
            )

        r_make = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(tc_make="Regenerate")
        self.assertFalse(r_make.valid)
        self.assertEqual(
            r_make.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

        r_run = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(tc_run="Rec Run")
        self.assertFalse(r_run.valid)
        self.assertEqual(
            r_run.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

        r_still = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(shooting_mode="Still")
        self.assertFalse(r_still.valid)
        self.assertEqual(
            r_still.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

    def test_31_g72_blocks_ext_lk_release_on_sq_or_tc_preset_change_when_lock_required(
        self,
    ) -> None:
        r_sq = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            sq_mode_triggered=True,
        )
        self.assertFalse(r_sq.valid)
        self.assertEqual(
            r_sq.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

        r_chg = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            tc_make_run_preset_changed_after_lock=True,
        )
        self.assertFalse(r_chg.valid)
        self.assertEqual(
            r_chg.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

    def test_32_g72_unlock_rehearsal_mode_verifies_auto_release_and_hdmi_tcout_off_in_sq(
        self,
    ) -> None:
        # In S&Q with ext_lk_required=False, EXT-LK auto-releases (ext_lk_locked=False)
        # and HDMI Time Code Output auto-disables ("Off") -> valid state transition!
        r_clean_sq = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            shooting_mode="S&Q",
            sq_mode_active=True,
            ext_lk_required=False,
            ext_lk_locked=False,
            hdmi_timecode_output="Off",
        )
        self.assertTrue(r_clean_sq.valid, r_clean_sq.errors)
        self.assertEqual(r_clean_sq.modeled_ext_lk_state, EXT_LK_STATE_RELEASED)
        self.assertFalse(r_clean_sq.tc_out_enabled)

        # Spoofing ext_lk_locked=True while in S&Q must fail-close!
        r_spoof_lk = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            shooting_mode="S&Q",
            sq_mode_active=True,
            ext_lk_required=False,
            ext_lk_locked=True,
            hdmi_timecode_output="Off",
        )
        self.assertFalse(r_spoof_lk.valid)
        self.assertEqual(
            r_spoof_lk.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

    def test_33_g72_blocks_hdmi_tcout_on_in_sq_and_non_hdmi_tcout_transports(self) -> None:
        # HDMI TC OUT = On in S&Q -> rejected
        r_sq_tcout = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            shooting_mode="S&Q",
            sq_mode_active=True,
            ext_lk_required=False,
            ext_lk_locked=False,
            hdmi_timecode_output="On",
            tc_out_transport="Type-A HDMI",
        )
        self.assertFalse(r_sq_tcout.valid)
        self.assertEqual(
            r_sq_tcout.status, STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION
        )

        # Non-HDMI TC OUT transports -> rejected
        for bad_tcout in ("12G-SDI", "SDI", "3.5mm Audio LTC", "XLR-H1 Micro-USB"):
            r_bad_trans = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
                hdmi_timecode_output="On",
                tc_out_transport=bad_tcout,
            )
            self.assertFalse(r_bad_trans.valid, f"expected fail for {bad_tcout!r}")
            self.assertEqual(
                r_bad_trans.status, STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION
            )

        # BNC TC OUT transport -> rejected with reverse BNC TC OUT code
        for bnc_trans in ("BNC_TC_OUT", "VMC_BNCM1_BNC", "MULTI_MICRO_USB_LTC"):
            ok, code, _ = validate_digital_hdmi_type_a_only_tcout(
                hdmi_timecode_output="On",
                tc_out_transport=bnc_trans,
            )
            self.assertFalse(ok)
            self.assertEqual(code, STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN)

    def test_34_g72_blocks_wrong_adapter_model_part_number_or_cable_length(self) -> None:
        r_mod = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            adapter_model="VMC-15MR2",
        )
        self.assertFalse(r_mod.valid)
        self.assertEqual(
            r_mod.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

        r_part = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            adapter_part_number="A-0000-000-X",
        )
        self.assertFalse(r_part.valid)
        self.assertEqual(
            r_part.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

        r_len = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
            cable_length_m=2.5,
        )
        self.assertFalse(r_len.valid)
        self.assertEqual(
            r_len.status, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED
        )

    def test_35_g72_rejects_malformed_telemetry_types(self) -> None:
        for bad_kwargs in (
            {"continuous_ltc_lock_seconds": -1.0},
            {"continuous_ltc_lock_seconds": True},  # type: ignore[dict-item]
            {"cable_length_m": 0.0},
            {"connected_usb_port": ""},
            {"hdmi_timecode_output": ""},
            {"xlr_h1_handle_micro_usb_connected": "no"},  # type: ignore[dict-item]
        ):
            res = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(**bad_kwargs)
            self.assertFalse(res.valid, f"expected invalid telemetry for {bad_kwargs}")
            self.assertEqual(res.status, STATUS_BLOCKED_G72_TELEMETRY_INVALID)

    def test_36_evaluate_g72_blocks_persistent_emmc_write_request(self) -> None:
        verdict, res = evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    # --- 6. Unified 72-Gate Master Preflight (evaluate_72gate_preflight) ---

    def test_37_master_72gate_offline_mode_verifies_69_of_72_with_tier0_locked(
        self,
    ) -> None:
        rep = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_70_override=self.clean_off_70,
        )
        self.assertIsInstance(rep, Master72GateReport)
        self.assertEqual(rep.status, "VERIFIED_69_OF_72_AWAITING_PHYSICAL_TIER0")
        self.assertTrue(rep.offline_69_gates_verified)
        self.assertFalse(rep.all_72_gates_verified)
        self.assertTrue(rep.g13_to_g72_all_passed)
        self.assertTrue(rep.g71_to_g72_all_passed)
        self.assertEqual(len(rep.gates), 72)
        self.assertEqual(rep.summary["total_gates"], 72)
        self.assertEqual(rep.summary["verified_gates"], 69)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(rep.agent_auto_flash_blocked)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_38_master_72gate_dry_run_simulated_verifies_72_of_72_while_redlines_locked(
        self,
    ) -> None:
        rep = self.default_dry_72
        self.assertEqual(
            rep.status, "VERIFIED_ALL_72_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertTrue(rep.all_72_gates_verified)
        self.assertTrue(rep.offline_69_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertTrue(rep.g71_to_g72_all_passed)
        self.assertEqual(rep.summary["verified_gates"], 72)
        self.assertEqual(rep.gates[-2]["gate_id"], G71_GATE_ID)
        self.assertEqual(rep.gates[-1]["gate_id"], G72_GATE_ID)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(rep.agent_auto_flash_blocked)
        self.assertFalse(rep.human_hardware_attach_token)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_39_master_72gate_propagates_g71_failure_fail_closed(self) -> None:
        rep = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_70_override=self.clean_dry_70,
            big6_camset_slot1_kwargs={"e_nd_actuator_tx_count": 3},
        )
        self.assertFalse(rep.all_72_gates_verified)
        self.assertFalse(rep.g71_to_g72_all_passed)
        self.assertEqual(rep.status, STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN)
        self.assertEqual(rep.summary["verified_gates"], 71)

    def test_40_master_72gate_propagates_g72_failure_fail_closed(self) -> None:
        rep = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_70_override=self.clean_dry_70,
            vmcbncm1_tcin_hdmi_tcout_kwargs={"xlr_h1_handle_micro_usb_connected": True},
        )
        self.assertFalse(rep.all_72_gates_verified)
        self.assertFalse(rep.g71_to_g72_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN
        )
        self.assertEqual(rep.summary["verified_gates"], 71)

    def test_41_master_72gate_propagates_upstream_g69_g70_g58_failures(self) -> None:
        rep_g69 = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            fan_pwm_thermal_kwargs={"fan_mode": "Auto1"},
        )
        self.assertFalse(rep_g69.all_72_gates_verified)
        self.assertEqual(rep_g69.status, STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2)

        rep_g70 = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            lut_split_shutter_angle_kwargs={
                "stageb_p2_setting_lut_write_attempted": True
            },
        )
        self.assertFalse(rep_g70.all_72_gates_verified)
        self.assertEqual(
            rep_g70.status, STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE
        )

        rep_g58 = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            bench_interlock_kwargs={"agent_auto_flash_blocked": False},
        )
        self.assertFalse(rep_g58.all_72_gates_verified)
        self.assertEqual(
            rep_g58.status, STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION
        )

    def test_42_master_72gate_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep.all_72_gates_verified)
        self.assertFalse(rep.offline_69_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_43_master_72gate_blocks_corrupted_phase201_donor_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work, specs = _create_synthetic_donor_tree(Path(tmp), corrupt_saveload=True)
            with patch(
                "fx3_safety.realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard.PINNED_PHASE201_DONOR_SPECS",
                specs,
            ):
                rep = evaluate_72gate_preflight(
                    DEFAULT_REPO_ROOT,
                    work_root=work,
                    force_clean_room=False,
                    dry_run_simulated=True,
                    master_70_override=self.clean_dry_70,
                )
            self.assertFalse(rep.all_72_gates_verified)
            self.assertFalse(rep.g71_to_g72_all_passed)
            self.assertEqual(rep.status, STATUS_BLOCKED_PHASE201_DONOR_INTEGRITY)

    # --- 7. Backward Compatibility Across 58/60/62/64/66/68/70 Gate Masters ---

    def test_44_backward_compatibility_58_to_70_gate_evaluators_intact(self) -> None:
        rep_58 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertTrue(rep_58.all_58_gates_verified)
        self.assertEqual(rep_58.summary["verified_gates"], 58)
        self.assertFalse(rep_58.overall_ready_for_hardware_attach)

        self.assertTrue(self.clean_dry_70.all_70_gates_verified)
        self.assertEqual(self.clean_dry_70.summary["verified_gates"], 70)
        self.assertFalse(self.clean_dry_70.overall_ready_for_hardware_attach)

        checks = (
            (evaluate_60gate_preflight, 60, "all_60_gates_verified"),
            (evaluate_62gate_preflight, 62, "all_62_gates_verified"),
            (evaluate_64gate_preflight, 64, "all_64_gates_verified"),
            (evaluate_66gate_preflight, 66, "all_66_gates_verified"),
            (evaluate_68gate_preflight, 68, "all_68_gates_verified"),
        )
        for fn, exp_total, attr in checks:
            rep = fn(DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True)
            self.assertTrue(getattr(rep, attr), f"{fn.__name__} failed {attr}")
            self.assertEqual(rep.summary["verified_gates"], exp_total)
            self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_45_backward_compatibility_cli_verify_58_to_70_gates_intact(self) -> None:
        for cmd, expected in (
            (["verify-58-gates", "--clean-room", "--dry-run-simulated-backup", "--json"], 58),
            (["verify-60-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 60),
            (["verify-62-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 62),
            (["verify-64-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 64),
            (["verify-66-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 66),
            (["verify-68-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 68),
            (["verify-70-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 70),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(cmd)
            self.assertEqual(rc, 0, f"{cmd[0]} failed: {buf.getvalue()}")
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["summary"]["verified_gates"], expected)
            self.assertFalse(payload["overall_ready_for_hardware_attach"])

    # --- 8. CLI Subcommands, Zero Raw Firmware Leakage & Runtime Budget ---

    def test_46_cli_verify_g71_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g71-big6-noend-camset-slot1", "--force-clean-room", "--json"],
            ["verify-g71-big6-noend-camset-slot1", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G71)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertEqual(
                    data["big6_noend_camset_slot1_guard"]["e_nd_actuator_tx_count"], 0
                )
                self.assertTrue(
                    data["big6_noend_camset_slot1_guard"]["big6_zero_end_firewall_valid"]
                )
                self.assertTrue(
                    data["big6_noend_camset_slot1_guard"]["slot1_camset_firewall_valid"]
                )
            else:
                self.assertIn(f"gate={G71_GATE_ID}", buf.getvalue())

    def test_47_cli_verify_g72_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g72-vmcbncm1-tcin-hdmi-tcout", "--force-clean-room", "--json"],
            ["verify-g72-vmcbncm1-tcin-hdmi-tcout", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G72)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertTrue(
                    data["vmcbncm1_tcin_hdmi_tcout_guard"]["vmcbncm1_body_tcin_valid"]
                )
                self.assertTrue(
                    data["vmcbncm1_tcin_hdmi_tcout_guard"]["hdmi_only_tcout_valid"]
                )
            else:
                self.assertIn(f"gate={G72_GATE_ID}", buf.getvalue())

    def test_48_cli_verify_72_gates_offline_and_dry_run_modes(self) -> None:
        for subcmd, expected_count in (
            (["verify-72-gates", "--force-clean-room", "--json"], 69),
            (["verify-72-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 72),
            (["verify-72-gates", "--force-clean-room"], None),
            (["verify-72-gates", "--force-clean-room", "--dry-run-simulated"], None),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, f"CLI failed for {subcmd}: {buf.getvalue()}")
            if expected_count is not None:
                payload = json.loads(buf.getvalue())
                self.assertEqual(payload["summary"]["verified_gates"], expected_count)
                self.assertFalse(payload["overall_ready_for_hardware_attach"])
                self.assertTrue(payload["agent_auto_flash_blocked"])

    def test_49_cli_supports_clean_room_and_dry_run_simulated_backup_aliases(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(
                ["verify-72-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(payload["all_72_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 72)

    def test_50_module_cli_and_zero_raw_firmware_leakage_in_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated", "--json"])
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertNotIn("b'\\x7fELF", text)
        self.assertNotIn('b"\\x7fELF', text)
        payload = json.loads(text)
        self.assertEqual(payload["summary"]["verified_gates"], 72)
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["human_hardware_attach_token"])
        self.assertFalse(payload["el3_payload_transmit_authorized"])
        self.assertFalse(payload["spi_nor_write_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_51_module_cli_text_output_offline_and_dry_run_smoke(self) -> None:
        for args, exp_tok in (
            (["--force-clean-room"], "verified=69/72"),
            (["--force-clean-room", "--dry-run-simulated"], "verified=72/72"),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_cli_main(args)
            self.assertEqual(rc, 0)
            self.assertIn(exp_tok, buf.getvalue())

    def test_52_to_dict_roundtrip_on_all_phase201_dataclasses(self) -> None:
        audit = audit_phase201_donor_contracts(force_clean_room=True)
        self.assertEqual(
            json.loads(json.dumps(audit.to_dict()))["status"], STATUS_VERIFIED_SAFE
        )

        g71_guard = verify_fx3_big6_zero_end_and_slot1_camset_guard()
        self.assertEqual(
            json.loads(json.dumps(g71_guard.to_dict()))["status"], STATUS_VERIFIED_G71
        )

        g72_guard = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard()
        self.assertEqual(
            json.loads(json.dumps(g72_guard.to_dict()))["status"], STATUS_VERIFIED_G72
        )

        _, r71 = evaluate_g71_big6_noend_camset_slot1_guard(force_clean_room=True)
        self.assertEqual(
            json.loads(json.dumps(r71.to_dict()))["status"], STATUS_VERIFIED_G71
        )

        _, r72 = evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard(force_clean_room=True)
        self.assertEqual(
            json.loads(json.dumps(r72.to_dict()))["status"], STATUS_VERIFIED_G72
        )

    def test_53_preflight_summary_counts_match_gate_list_breakdown(self) -> None:
        r_off = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            master_70_override=self.clean_off_70,
        )
        self.assertEqual(r_off.summary["total_gates"], 72)
        self.assertEqual(r_off.summary["g01_to_g12_verified"], 9)
        self.assertEqual(r_off.summary["g13_to_g70_verified"], 58)
        self.assertEqual(r_off.summary["g71_to_g72_verified"], 2)
        self.assertEqual(
            r_off.summary["g01_to_g12_verified"]
            + r_off.summary["g13_to_g70_verified"]
            + r_off.summary["g71_to_g72_verified"],
            69,
        )
        locked_ids = [g["gate_id"] for g in r_off.gates if not g["passed"]]
        self.assertEqual(len(locked_ids), 3)
        for gid in locked_ids:
            self.assertTrue(
                gid.startswith(("G10_", "G11_", "G12_")),
                f"unexpected offline failed gate: {gid}",
            )

    def test_54_g71_auto_resolves_camset_directory_when_none_provided(self) -> None:
        r_sd = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            media_type="SDXC",
            camset_directory=None,
        )
        self.assertTrue(r_sd.valid, r_sd.errors)
        self.assertEqual(r_sd.camset_directory, SD_CAMSET_ROOT_DIR)

        r_cfe = verify_fx3_big6_zero_end_and_slot1_camset_guard(
            media_type="CFexpress Type A",
            camset_directory=None,
        )
        self.assertTrue(r_cfe.valid, r_cfe.errors)
        self.assertEqual(r_cfe.camset_directory, CFEXPRESS_A_CAMSET_ROOT_DIR)

    def test_55_g72_supports_boolean_and_string_hdmi_tcout_toggles(self) -> None:
        for toggle_on in ("On", "ON", "enabled", True):
            r_on = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
                hdmi_timecode_output=toggle_on,
                tc_out_transport="HDMI",
            )
            self.assertTrue(r_on.valid, f"failed for toggle={toggle_on!r}")
            self.assertTrue(r_on.tc_out_enabled)

        for toggle_off in ("Off", "OFF", "disabled", False):
            r_off = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
                hdmi_timecode_output=toggle_off,
                tc_out_transport="DISABLED",
            )
            self.assertTrue(r_off.valid, f"failed for toggle={toggle_off!r}")
            self.assertFalse(r_off.tc_out_enabled)

    def test_56_g71_slot_and_path_trailing_slash_normalization(self) -> None:
        for slot_tok in (1, "1", "Slot 1", "SLOT_1", "SLOT_A"):
            res = verify_fx3_big6_zero_end_and_slot1_camset_guard(
                camset_slot=slot_tok,
                media_type="CFexpress-A",
                camset_directory="/SONY/SETTING/FX3/CAMSET",
            )
            self.assertTrue(res.valid, f"failed for slot={slot_tok!r}: {res.errors}")
            self.assertEqual(res.camset_slot_index, 1)

    def test_57_distinct_violation_codes_across_g71_and_g72(self) -> None:
        self.assertEqual(STATUS_SAFE, "SAFE")
        self.assertEqual(STATUS_VERIFIED_SAFE, "VERIFIED_SAFE")
        distinct = {
            STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN,
            STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID,
            STATUS_BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN,
            STATUS_BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED,
            STATUS_BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH,
            STATUS_BLOCKED_G71_CAMSET_CROSS_MODEL_HEADER_REJECTED,
            STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT,
            STATUS_BLOCKED_G71_TELEMETRY_INVALID,
            STATUS_BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN,
            STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN,
            STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED,
            STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION,
            STATUS_BLOCKED_G72_TELEMETRY_INVALID,
            STATUS_BLOCKED_PHASE201_DONOR_INTEGRITY,
        }
        self.assertEqual(len(distinct), 14)

    def test_58_wall_clock_ceiling_under_6_seconds(self) -> None:
        self.assertTrue(self.default_dry_72.all_72_gates_verified)
        self.assertLess(
            self.default_dry_elapsed,
            6.0,
            f"evaluate_72gate_preflight exceeded 6.0s wall-clock ceiling ({self.default_dry_elapsed:.2f}s)",
        )
        t0 = time.monotonic()
        rep_clean = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        clean_elapsed = time.monotonic() - t0
        self.assertTrue(rep_clean.all_72_gates_verified)
        self.assertLess(clean_elapsed, 6.0)


if __name__ == "__main__":
    unittest.main()
