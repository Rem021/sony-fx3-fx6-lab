"""Phase 276 (Task H315, 114/114 Safety Gates, Wave-47) Dual-Mode Unit Tests
(76 tests, < 5.0s runtime) for
`fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard`:

- Gate `G113` (`GATE_G113_USB_CONNECTION_MODE_NOUVC_PD_DATA_ISOLATION_AND_HDMI_INFO_DISPLAY_GUARD`):
  - Stock `ILME-FX3 Ver. 7.02` (`ilc/2210`) `[USB Connection Mode]` exposes ONLY 4 modes
    (`Sel. When Connect` `0x7738` factory default, `MassStorage(MSC)` `0x6c54` `054C:0DA1`,
    `MTP` `0xe24b`, `Remote Shoot (PC Remote)` `0x60aa`/`0x7c6f`) vs dormant `NOUVC` split
    (`appFw.so` + `_f.uxc` `0x7399` + `usb_f_uvc.ko` `78,840 B`).
  - Air-gapped Tier-0 bench rule: prohibit `MassStorage(MSC)`, `MTP`, `Remote Shoot`, and
    `USB-LAN` host enumeration; allow `[USB Power Supply] = On` (`0x721e`, Type-C only +
    `NP-FZ100` inserted; `[USB LUN Setting]` `Multi` `0xe631` / `Single` `0x776d`) ONLY
    when USB `D+/D-` & SuperSpeed data lines are physically isolated.
  - `[HDMI Info. Display]` (`0x6e7c`): `On` (factory default, blanks built-in LCD + disables
    LCD touch-focus) vs `Off` (clean feed); `1080` clamp for internal rec + `Log Shooting != Off`
    or `PPLUT1..4`; `4K` clean-feed forced-Off override for `Off(HDMI Only)` (`0x6573`) or
    `RAW Output = On` (`0x6e97`, disabled in `S&Q`); `(Setup)` reset survival vs
    `Framing Settings (HDMI)` exception across 256 matrix states.
- Gate `G114` (`GATE_G114_PROTECT_VS_FORMAT_SLOT1_WP_FIREWALL_AND_RESET_NETWORK_SET_ZERO_RF_GUARD`):
  - `[Protect]` (`0xe2c9`) 5 scopes (`Single`, `Multiple Img.`, `All in this Folder`,
    `All with this date`, `All Images in This Group`): blocks `[Delete]` / `[Delete pressing
    twice]`, strips protect on copy, yet `[Format]` (`0xe449`/`0xe414`) wipes protected files
    and `M1..M4`. Enforces dual-layer `Slot-1` defense: physical SD `WP` lock
    (`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`) + `slot1_format_hard_locked == True`.
  - `[Reset Network Set.]` (`FUNC_reset_network_settings`, `SETTING_RESET_NW`, `0x60d3`/`0x65d3`)
    clears `(Network)` credentials only, preserves `(Shooting)`/`(Setup)`/`(Playback)`/`CAMSET`,
    triggers mandatory automatic reboot (`BKID_APP_is_shutdown_factor_network_reset`), and resets
    `[Airplane Mode]` to `Off` — requiring auto-reboot completion + re-assertion of
    `[Airplane Mode] = [On]` for Zero-RF bench across 160 matrix states.
- Unified `114`-Gate Master Safety Preflight (`evaluate_114gate_preflight` / `verify-114-gates`):
  `111/114` offline (`VERIFIED_111_OF_114_AWAITING_PHYSICAL_TIER0`) and `114/114` in
  `--simulate-bench-dry-run` (`VERIFIED_ALL_114_GATES_DRY_RUN_SIMULATED_BACKUP`) with all
  hardware write/live-attach redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard import (
    AIRGAPPED_PROHIBITED_USB_DATA_MODES_G113,
    AIRPLANE_MODE_FACTORY_DEFAULT_G114,
    AIRPLANE_MODE_MENU_PATH_G114,
    AIRPLANE_MODE_OFF_G114,
    AIRPLANE_MODE_ON_G114,
    AIRPLANE_MODE_RESID16_G114,
    ALLOWED_AIRPLANE_MODES_G114,
    ALLOWED_FRAMING_HDMI_MODES_G113,
    ALLOWED_HDMI_INFO_DISPLAY_MODES_G113,
    ALLOWED_HDMI_OUTPUT_RESOLUTIONS_G113,
    ALLOWED_LOG_SHOOTING_MODES_G113,
    ALLOWED_MEDIA_OPS_G114,
    ALLOWED_PICTURE_PROFILES_G113,
    ALLOWED_PROTECT_SCOPES_G114,
    ALLOWED_RAW_OUTPUT_MODES_G113,
    ALLOWED_REC_MEDIA_DUR_HDMI_MODES_G113,
    ALLOWED_RESET_ACTIONS_PHASE276,
    ALLOWED_SHOOT_MODES_G113,
    ALLOWED_TARGET_SLOTS_G114,
    ALLOWED_USB_LUN_SETTINGS_G113,
    ALLOWED_USB_PORTS_G113,
    ALLOWED_USB_POWER_SUPPLY_MODES_G113,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE276,
    DONOR_CHECK_MAX_SECONDS_PHASE276,
    DORMANT_USB_F_UVC_KO_BYTES_G113,
    DORMANT_USB_STREAMING_RESID16_F_G113,
    DORMANT_USB_STREAMING_RESID16_G_G113,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE276,
    FORMAT_CONFIRM_RESID16_G114,
    FORMAT_FULL_RESID16_G114,
    FORMAT_MENU_PATH_G114,
    FORMAT_QUICK_RESID16_G114,
    FORMAT_RESID16_G114,
    FRAMING_HDMI_CROP_G113,
    FRAMING_HDMI_FACTORY_DEFAULT_G113,
    FRAMING_HDMI_FULL_G113,
    FRAMING_SETTINGS_HDMI_MENU_PATH_G113,
    FX3_DEFAULT_FW_VERSION_PHASE276,
    FX3_HELP_GUIDE_CODE_PHASE276,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_STOCK_4_USB_CONNECTION_MODES_G113,
    FX3_UI_EXPOSES_USB_STREAMING_G113,
    FX6_DEFAULT_FW_VERSION_PHASE276,
    FX6_MODEL_NAME,
    G113,
    G113_GATE_CODE,
    G113_GATE_ID,
    G114,
    G114_GATE_CODE,
    G114_GATE_ID,
    GATE_G113_USB_CONNECTION_MODE_NOUVC_PD_DATA_ISOLATION_AND_HDMI_INFO_DISPLAY_GUARD,
    GATE_G114_PROTECT_VS_FORMAT_SLOT1_WP_FIREWALL_AND_RESET_NETWORK_SET_ZERO_RF_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_4K_TOKEN_G113,
    HDMI_CLAMPED_1080_TOKEN_G113,
    HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113,
    HDMI_INFO_DISPLAY_MENU_PATH_G113,
    HDMI_INFO_DISPLAY_OFF_G113,
    HDMI_INFO_DISPLAY_ON_G113,
    HDMI_INFO_DISPLAY_RESID16_G113,
    HDMI_OUTPUT_SETTINGS_MENU_PATH_G113,
    HDMI_OUT_RES_1080I_G113,
    HDMI_OUT_RES_1080P_G113,
    HDMI_OUT_RES_2160P_G113,
    HDMI_OUT_RES_AUTO_G113,
    HDMI_OUT_RES_FACTORY_DEFAULT_G113,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LOG_SHOOTING_CINE_EI_G113,
    LOG_SHOOTING_CINE_EI_QUICK_G113,
    LOG_SHOOTING_FLEXIBLE_ISO_G113,
    LOG_SHOOTING_OFF_G113,
    MEDIA_OP_DELETE_PRESSING_TWICE_G114,
    MEDIA_OP_DELETE_SINGLE_G114,
    MEDIA_OP_FORMAT_FULL_G114,
    MEDIA_OP_FORMAT_QUICK_G114,
    MEDIA_OP_NONE_G114,
    NETWORK_RESET_CLEARED_CATEGORIES_G114,
    NETWORK_RESET_PRESERVED_DOMAINS_G114,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE276,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE276,
    PINNED_FX6_APPFW_SLICES_PHASE276,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE276,
    PINNED_PHASE276_DONOR_SPECS,
    PPLUT_PICTURE_PROFILES_G113,
    PROTECT_MENU_PATH_G114,
    PROTECT_RESID16_G114,
    PROTECT_SCOPE_ALL_IN_FOLDER_G114,
    PROTECT_SCOPE_ALL_IN_GROUP_G114,
    PROTECT_SCOPE_ALL_WITH_DATE_G114,
    PROTECT_SCOPE_MULTIPLE_IMG_G114,
    PROTECT_SCOPE_RESID16_MAP_G114,
    PROTECT_SCOPE_SINGLE_G114,
    RAW_FIRMWARE_BYTES_LEAKED,
    RAW_OUTPUT_FACTORY_DEFAULT_G113,
    RAW_OUTPUT_OFF_G113,
    RAW_OUTPUT_ON_G113,
    RAW_OUTPUT_RESID16_G113,
    REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_114GATE_SCHEMA,
    REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_114GATE_VERSION,
    REC_MEDIA_HDMI_FACTORY_DEFAULT_G113,
    REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113,
    REC_MEDIA_HDMI_OFF_RESID16_G113,
    REC_MEDIA_HDMI_ON_G113,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE276,
    RESET_NETWORK_PROMPT_RESID16_G114,
    RESET_NETWORK_SET_MENU_PATH_G114,
    RESET_NETWORK_SET_RESID16_G114,
    SHOOT_MODE_MOVIE_G113,
    SHOOT_MODE_SQ_G113,
    SHOOT_MODE_STILL_G113,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G113_AIRGAPPED_USB_DATA_ENUMERATION_HAZARD,
    STATUS_BLOCKED_G113_FX3_NOUVC_USB_STREAMING_SPOOF_VIOLATION,
    STATUS_BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION,
    STATUS_BLOCKED_G113_SETUP_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G113_TELEMETRY_INVALID,
    STATUS_BLOCKED_G113_USB_POWER_OR_LUN_CONTRACT_VIOLATION,
    STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD,
    STATUS_BLOCKED_G114_PROTECT_ONLY_WITHOUT_SLOT1_WP_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G114_PROTECT_SCOPE_OR_PLAYBACK_CONTRACT_VIOLATION,
    STATUS_BLOCKED_G114_RESET_BOUNDARY_OR_AUTO_REBOOT_VIOLATION,
    STATUS_BLOCKED_G114_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY,
    STATUS_VERIFIED_G113,
    STATUS_VERIFIED_G114,
    TARGET_SLOT_1_G114,
    TARGET_SLOT_2_G114,
    TARGET_SLOT_NONE_G114,
    USB_CONNECTION_MODE_FACTORY_DEFAULT_G113,
    USB_CONNECTION_MODE_MENU_PATH_G113,
    USB_CONNECTION_MODE_METADATA_G113,
    USB_CONNECTION_MODE_RESID16_G113,
    USB_CONN_MASS_STORAGE_MSC_G113,
    USB_CONN_MTP_G113,
    USB_CONN_REMOTE_SHOOT_G113,
    USB_CONN_SEL_WHEN_CONNECT_G113,
    USB_CONN_USB_LAN_G113,
    USB_CONN_USB_STREAMING_G113,
    USB_LUN_FACTORY_DEFAULT_G113,
    USB_LUN_MULTI_G113,
    USB_LUN_MULTI_RESID16_G113,
    USB_LUN_SETTING_MENU_PATH_G113,
    USB_LUN_SINGLE_G113,
    USB_LUN_SINGLE_RESID16_G113,
    USB_LUN_UXC_RESID16_G113,
    USB_MSC_APPFW_MARKER_G113,
    USB_MSC_VID_PID_G113,
    USB_PACKETS_TRANSMITTED,
    USB_PORT_MULTI_MICRO_G113,
    USB_PORT_NONE_G113,
    USB_PORT_TYPE_C_G113,
    USB_POWER_SUPPLY_FACTORY_DEFAULT_G113,
    USB_POWER_SUPPLY_MENU_PATH_G113,
    USB_POWER_SUPPLY_OFF_G113,
    USB_POWER_SUPPLY_ON_G113,
    USB_POWER_SUPPLY_RESID16_G113,
    _is_forced_clean_room,
    audit_phase276_donor_contracts,
    compute_protect_and_network_reset_matrix,
    compute_usb_mode_and_hdmi_info_matrix,
    evaluate_112gate_preflight,
    evaluate_114_master_safety_gates,
    evaluate_114gate_preflight,
    evaluate_g113_usb_mode_and_hdmi_info_guard,
    evaluate_g114_protect_and_network_reset_guard,
    main as module_main,
    resolve_fx3_protect_and_network_reset_state,
    resolve_fx3_usb_mode_and_hdmi_info_state,
    run_114_gate_preflight,
    verify_protect_and_network_reset_guard,
    verify_usb_mode_and_hdmi_info_guard,
)


def _clean_env_without_cleanroom() -> dict[str, str]:
    return {
        k: v
        for k, v in os.environ.items()
        if k not in (ENV_CLEAN_ROOM_TEST_PHASE276, "FX3_FX6_FORCE_CLEAN_ROOM")
    }


def _subprocess_timeout_seconds() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" else 10.0


class TestPhase276UsbModeHdmiInfoProtectNetworkReset114GateGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = audit_phase276_donor_contracts(force_clean_room=True)
        cls.clean_offline_112 = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        cls.clean_dryrun_112 = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )

    # ------------------------------------------------------------------
    # 1..4: Exports, schema, redlines & donor budget constants
    # ------------------------------------------------------------------

    def test_01_public_exports_and_schema_constants(self) -> None:
        self.assertEqual(
            REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_114GATE_SCHEMA,
            "realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard_v1",
        )
        self.assertEqual(
            REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_114GATE_VERSION,
            "1.0.0",
        )
        self.assertIn("evaluate_114gate_preflight", fx3_safety.__all__)
        self.assertIn(
            "evaluate_g113_usb_mode_and_hdmi_info_guard",
            fx3_safety.__all__,
        )
        self.assertIn(
            "evaluate_g114_protect_and_network_reset_guard",
            fx3_safety.__all__,
        )
        self.assertIn(
            "realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard",
            fx3_safety.__all__,
        )
        self.assertIs(
            fx3_safety.evaluate_114gate_preflight,
            evaluate_114gate_preflight,
        )
        self.assertIs(
            fx3_safety.run_114_gate_preflight,
            run_114_gate_preflight,
        )
        self.assertIs(
            fx3_safety.evaluate_114_master_safety_gates,
            evaluate_114_master_safety_gates,
        )

    def test_02_gate_ids_and_codes(self) -> None:
        self.assertEqual(G113, G113_GATE_ID)
        self.assertEqual(G114, G114_GATE_ID)
        self.assertEqual(
            G113_GATE_ID,
            "G113_usb_connection_mode_nouvc_pd_data_isolation_and_hdmi_info_display_guard",
        )
        self.assertEqual(
            G114_GATE_ID,
            "G114_protect_vs_format_slot1_wp_firewall_and_reset_network_set_zero_rf_guard",
        )
        self.assertEqual(
            G113_GATE_CODE,
            GATE_G113_USB_CONNECTION_MODE_NOUVC_PD_DATA_ISOLATION_AND_HDMI_INFO_DISPLAY_GUARD,
        )
        self.assertEqual(
            G114_GATE_CODE,
            GATE_G114_PROTECT_VS_FORMAT_SLOT1_WP_FIREWALL_AND_RESET_NETWORK_SET_ZERO_RF_GUARD,
        )

    def test_03_hard_safety_redlines_locked(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_04_donor_specs_and_budget_constants(self) -> None:
        self.assertEqual(DONOR_CHECK_MAX_SECONDS_PHASE276, 0.20)
        self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE276, 1.00)
        self.assertEqual(len(PINNED_PHASE276_DONOR_SPECS), 9)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE276), 19)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE276), 6)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE276), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE276), 64)
        self.assertEqual(DORMANT_USB_F_UVC_KO_BYTES_G113, 78_840)

    # ------------------------------------------------------------------
    # 5..14: O_RDONLY Local Donor Audit & Clean-Room Fallback
    # ------------------------------------------------------------------

    def test_05_donor_audit_clean_room_explicit(self) -> None:
        res = self.clean_audit
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.within_budget_200ms)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertEqual(res.dormant_usb_f_uvc_ko_bytes, 78_840)

    def test_06_donor_audit_dual_mode_env_flags(self) -> None:
        for key in (ENV_CLEAN_ROOM_TEST_PHASE276, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                res = audit_phase276_donor_contracts()
                self.assertTrue(res.valid)
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_07_donor_audit_missing_work_root_falls_back_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = audit_phase276_donor_contracts(work_root=Path(td))
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_08_donor_audit_local_o_rdonly_if_present(self) -> None:
        with mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True):
            res = audit_phase276_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertEqual(res.dormant_usb_f_uvc_ko_bytes, 78_840)
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(res.access_mode, "O_RDONLY")
            self.assertEqual(res.files_inspected, 9)
            budget = (
                DONOR_CHECK_CI_MAX_SECONDS_PHASE276
                if os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
                else DONOR_CHECK_MAX_SECONDS_PHASE276
            )
            self.assertLessEqual(res.elapsed_seconds, budget)

    def test_09_donor_audit_uses_os_o_rdonly_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            synthetic_blobs: dict[str, bytes] = {}
            for key, (_body, rel, exp_size, _sha, tokens, _label) in PINNED_PHASE276_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if key == "fx3_bk4_bin":
                    blob = b"BK4\x00" + b"\x00" * 12 + b"ILME-FX3" + b"\x00" * 64
                else:
                    blob = b"|".join(tokens)
                p.write_bytes(blob)
                synthetic_blobs[key] = blob

            patched_specs = {
                k: (
                    v[0],
                    v[1],
                    v[2] if k in ("fx3_appfw_so", "fx6_appfw_so") else len(synthetic_blobs[k]),
                    v[3]
                    if k in ("fx3_appfw_so", "fx6_appfw_so")
                    else hashlib.sha256(synthetic_blobs[k]).hexdigest(),
                    v[4],
                    v[5],
                )
                for k, v in PINNED_PHASE276_DONOR_SPECS.items()
            }

            opened_flags: list[int] = []
            real_open = os.open

            def _tracking_open(path, flags, *a, **kw):
                if str(work_root) in str(path):
                    opened_flags.append(flags)
                return real_open(path, flags, *a, **kw)

            def _fake_pread(fp: Path, slices_spec):
                if "nflasha15/lib/appFw.so" in str(fp):
                    return 79_015_712, PINNED_FX3_APPFW_SLICES_SHA256_PHASE276, True
                return 50_520_424, PINNED_FX6_APPFW_SLICES_SHA256_PHASE276, True

            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch.dict(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.PINNED_PHASE276_DONOR_SPECS",
                    patched_specs,
                    clear=True,
                ),
                mock.patch(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard._read_targeted_slices_o_rdonly",
                    side_effect=_fake_pread,
                ),
                mock.patch(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard._DONOR_BLOB_CACHE",
                    {},
                ),
                mock.patch("os.open", side_effect=_tracking_open),
            ):
                res = audit_phase276_donor_contracts(work_root=work_root)
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertGreaterEqual(len(opened_flags), 7)
            for flg in opened_flags:
                self.assertEqual(flg & os.O_ACCMODE, os.O_RDONLY)

    def test_10_donor_audit_detects_uxc_sha_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            for _key, (_body, rel, _sz, _sha, tokens, _label) in PINNED_PHASE276_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"|".join(tokens))

            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard._read_targeted_slices_o_rdonly",
                    return_value=(79_015_712, PINNED_FX3_APPFW_SLICES_SHA256_PHASE276, True),
                ),
                mock.patch(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard._DONOR_BLOB_CACHE",
                    {},
                ),
            ):
                res = audit_phase276_donor_contracts(work_root=work_root)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY)

    def test_11_donor_audit_detects_appfw_slice_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            synthetic_blobs: dict[str, bytes] = {}
            for key, (_body, rel, _sz, _sha, tokens, _label) in PINNED_PHASE276_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                blob = b"|".join(tokens)
                p.write_bytes(blob)
                synthetic_blobs[key] = blob

            patched_specs = {
                k: (
                    v[0],
                    v[1],
                    v[2] if k in ("fx3_appfw_so", "fx6_appfw_so") else len(synthetic_blobs[k]),
                    v[3]
                    if k in ("fx3_appfw_so", "fx6_appfw_so")
                    else hashlib.sha256(synthetic_blobs[k]).hexdigest(),
                    v[4],
                    v[5],
                )
                for k, v in PINNED_PHASE276_DONOR_SPECS.items()
            }

            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch.dict(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.PINNED_PHASE276_DONOR_SPECS",
                    patched_specs,
                    clear=True,
                ),
                mock.patch(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard._read_targeted_slices_o_rdonly",
                    return_value=(79_015_712, "0" * 64, False),
                ),
                mock.patch(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard._DONOR_BLOB_CACHE",
                    {},
                ),
            ):
                res = audit_phase276_donor_contracts(work_root=work_root)
            self.assertFalse(res.valid)
            self.assertFalse(res.fx3_contracts_verified)
            self.assertFalse(res.fx6_contracts_verified)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY)

    def test_12_donor_audit_detects_missing_fx3_or_fx6_markers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            synthetic_blobs: dict[str, bytes] = {}
            for key, (_body, rel, _sz, _sha, tokens, _label) in PINNED_PHASE276_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                blob = b"MISSING_TOKENS_ONLY" if key == "fx3_string_english_uxc" else b"|".join(tokens)
                p.write_bytes(blob)
                synthetic_blobs[key] = blob

            patched_specs = {
                k: (
                    v[0],
                    v[1],
                    v[2] if k in ("fx3_appfw_so", "fx6_appfw_so") else len(synthetic_blobs[k]),
                    v[3]
                    if k in ("fx3_appfw_so", "fx6_appfw_so")
                    else hashlib.sha256(synthetic_blobs[k]).hexdigest(),
                    v[4],
                    v[5],
                )
                for k, v in PINNED_PHASE276_DONOR_SPECS.items()
            }

            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch.dict(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.PINNED_PHASE276_DONOR_SPECS",
                    patched_specs,
                    clear=True,
                ),
                mock.patch(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard._read_targeted_slices_o_rdonly",
                    side_effect=lambda fp, _s: (
                        (79_015_712, PINNED_FX3_APPFW_SLICES_SHA256_PHASE276, True)
                        if "nflasha15/lib/appFw.so" in str(fp)
                        else (50_520_424, PINNED_FX6_APPFW_SLICES_SHA256_PHASE276, True)
                    ),
                ),
                mock.patch(
                    "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard._DONOR_BLOB_CACHE",
                    {},
                ),
            ):
                res = audit_phase276_donor_contracts(work_root=work_root)
            self.assertFalse(res.valid)
            self.assertFalse(res.fx3_contracts_verified)
            self.assertTrue(res.fx6_contracts_verified)

    def test_13_donor_audit_budget_timeout_fails_closed(self) -> None:
        res = audit_phase276_donor_contracts(force_clean_room=True, max_budget_seconds=0.0)
        self.assertFalse(res.valid)
        self.assertFalse(res.within_budget_200ms)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY)

    def test_14_donor_audit_to_dict_serializable(self) -> None:
        payload = json.dumps(self.clean_audit.to_dict(), ensure_ascii=False)
        decoded = json.loads(payload)
        self.assertEqual(decoded["dormant_usb_f_uvc_ko_bytes"], 78_840)
        self.assertEqual(decoded["raw_firmware_bytes_leaked"], 0)

    # ------------------------------------------------------------------
    # 15..36: Gate G113 ([USB Connection Mode], NOUVC, PD, [HDMI Info. Display])
    # ------------------------------------------------------------------

    def test_15_g113_defaults_pass(self) -> None:
        res = verify_usb_mode_and_hdmi_info_guard()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G113)
        self.assertEqual(len(res.fx3_stock_4_usb_modes), 4)
        self.assertFalse(res.fx3_ui_exposes_usb_streaming)
        self.assertEqual(res.usb_streaming_spoof_events, 0)
        self.assertEqual(res.effective_post_reset_usb_connection_mode, USB_CONN_SEL_WHEN_CONNECT_G113)
        self.assertEqual(res.effective_hdmi_info_display, HDMI_INFO_DISPLAY_OFF_G113)
        self.assertFalse(res.lcd_blanked)
        self.assertTrue(res.lcd_touch_focus_active)

    def test_16_g113_stock_4_usb_modes_and_resid16_metadata(self) -> None:
        self.assertEqual(
            FX3_STOCK_4_USB_CONNECTION_MODES_G113,
            (
                USB_CONN_SEL_WHEN_CONNECT_G113,
                USB_CONN_MASS_STORAGE_MSC_G113,
                USB_CONN_MTP_G113,
                USB_CONN_REMOTE_SHOOT_G113,
            ),
        )
        self.assertEqual(USB_CONNECTION_MODE_RESID16_G113, 0x69A2)
        self.assertEqual(USB_CONNECTION_MODE_FACTORY_DEFAULT_G113, "Sel. When Connect")
        self.assertEqual(USB_MSC_VID_PID_G113, "054C:0DA1")
        self.assertEqual(USB_MSC_APPFW_MARKER_G113, "USB_CONNECTION_METHOD_MASS_STRAGE")
        self.assertEqual(USB_CONNECTION_MODE_METADATA_G113[USB_CONN_SEL_WHEN_CONNECT_G113][0], 0x7738)
        self.assertEqual(USB_CONNECTION_MODE_METADATA_G113[USB_CONN_MASS_STORAGE_MSC_G113][0], 0x6C54)
        self.assertEqual(USB_CONNECTION_MODE_METADATA_G113[USB_CONN_MTP_G113][0], 0xE24B)
        self.assertEqual(USB_CONNECTION_MODE_METADATA_G113[USB_CONN_REMOTE_SHOOT_G113][0], 0x60AA)
        self.assertFalse(FX3_UI_EXPOSES_USB_STREAMING_G113)
        self.assertEqual(DORMANT_USB_STREAMING_RESID16_F_G113, 0x7399)
        self.assertEqual(DORMANT_USB_STREAMING_RESID16_G_G113, 0x63F7)

    def test_17_g113_blocks_fx3_nouvc_usb_streaming_spoof(self) -> None:
        cases = [
            dict(claimed_fx3_exposes_usb_streaming=True),
            dict(claimed_usb_streaming_uvc_active=True),
            dict(pre_reset_usb_connection_mode=USB_CONN_USB_STREAMING_G113),
            dict(claimed_usb_streaming_spoof_events=1),
        ]
        for kw in cases:
            res = verify_usb_mode_and_hdmi_info_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertIn(
                STATUS_BLOCKED_G113_FX3_NOUVC_USB_STREAMING_SPOOF_VIOLATION,
                res.violation_codes,
                msg=kw,
            )
            self.assertGreaterEqual(res.usb_streaming_spoof_events, 1)

    def test_18_g113_airgapped_tier0_blocks_all_prohibited_usb_data_modes(self) -> None:
        self.assertEqual(
            AIRGAPPED_PROHIBITED_USB_DATA_MODES_G113,
            (
                USB_CONN_MASS_STORAGE_MSC_G113,
                USB_CONN_MTP_G113,
                USB_CONN_REMOTE_SHOOT_G113,
                USB_CONN_USB_LAN_G113,
            ),
        )
        for mode in AIRGAPPED_PROHIBITED_USB_DATA_MODES_G113:
            res = verify_usb_mode_and_hdmi_info_guard(
                pre_reset_usb_connection_mode=mode,
                air_gapped_tier0_bench=True,
            )
            self.assertFalse(res.valid, msg=mode)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G113_AIRGAPPED_USB_DATA_ENUMERATION_HAZARD,
                msg=mode,
            )
            self.assertGreaterEqual(res.airgapped_usb_data_enumeration_hazards, 1)

    def test_19_g113_blocks_usb_pd_on_without_physical_data_isolation(self) -> None:
        res = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_usb_power_supply=USB_POWER_SUPPLY_ON_G113,
            usb_data_lines_physically_isolated=False,
            air_gapped_tier0_bench=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G113_AIRGAPPED_USB_DATA_ENUMERATION_HAZARD)

    def test_20_g113_blocks_usb_host_data_enumerated_even_in_sel_when_connect(self) -> None:
        res = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_usb_connection_mode=USB_CONN_SEL_WHEN_CONNECT_G113,
            usb_host_data_enumerated=True,
            air_gapped_tier0_bench=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G113_AIRGAPPED_USB_DATA_ENUMERATION_HAZARD)

    def test_21_g113_allows_usb_pd_off_without_data_isolation_when_sel_when_connect(self) -> None:
        res = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_usb_connection_mode=USB_CONN_SEL_WHEN_CONNECT_G113,
            pre_reset_usb_power_supply=USB_POWER_SUPPLY_OFF_G113,
            usb_data_lines_physically_isolated=False,
            air_gapped_tier0_bench=True,
        )
        self.assertTrue(res.valid, msg=res.errors)

    def test_22_g113_non_airgapped_allows_stock_msc_mtp_remote_shoot(self) -> None:
        for mode in (
            USB_CONN_MASS_STORAGE_MSC_G113,
            USB_CONN_MTP_G113,
            USB_CONN_REMOTE_SHOOT_G113,
        ):
            res = verify_usb_mode_and_hdmi_info_guard(
                pre_reset_usb_connection_mode=mode,
                air_gapped_tier0_bench=False,
                usb_data_lines_physically_isolated=False,
            )
            self.assertTrue(res.valid, msg=f"{mode}: {res.errors}")

    def test_23_g113_usb_pd_requires_type_c_and_np_fz100(self) -> None:
        r_micro = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_usb_power_supply=USB_POWER_SUPPLY_ON_G113,
            usb_port=USB_PORT_MULTI_MICRO_G113,
            np_fz100_battery_inserted=True,
        )
        self.assertFalse(r_micro.valid)
        self.assertEqual(r_micro.status, STATUS_BLOCKED_G113_USB_POWER_OR_LUN_CONTRACT_VIOLATION)

        r_nobatt = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_usb_power_supply=USB_POWER_SUPPLY_ON_G113,
            usb_port=USB_PORT_TYPE_C_G113,
            np_fz100_battery_inserted=False,
        )
        self.assertFalse(r_nobatt.valid)
        self.assertEqual(r_nobatt.status, STATUS_BLOCKED_G113_USB_POWER_OR_LUN_CONTRACT_VIOLATION)

    def test_24_g113_usb_lun_settings_and_resid16s(self) -> None:
        self.assertEqual(USB_LUN_UXC_RESID16_G113, 0x6B19)
        self.assertEqual(USB_LUN_MULTI_RESID16_G113, 0xE631)
        self.assertEqual(USB_LUN_SINGLE_RESID16_G113, 0x776D)
        self.assertEqual(USB_POWER_SUPPLY_RESID16_G113, 0x721E)
        for lun in ALLOWED_USB_LUN_SETTINGS_G113:
            res = verify_usb_mode_and_hdmi_info_guard(pre_reset_usb_lun_setting=lun)
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.effective_post_reset_usb_lun_setting, lun)

    def test_25_g113_hdmi_info_on_blanks_lcd_and_disables_touch_focus(self) -> None:
        self.assertEqual(HDMI_INFO_DISPLAY_RESID16_G113, 0x6E7C)
        self.assertEqual(HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113, HDMI_INFO_DISPLAY_ON_G113)
        res = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G113,
            pre_reset_rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G113,
            pre_reset_raw_output=RAW_OUTPUT_OFF_G113,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_hdmi_info_display, HDMI_INFO_DISPLAY_ON_G113)
        self.assertTrue(res.lcd_blanked)
        self.assertFalse(res.lcd_touch_focus_active)

        bad_lcd = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G113,
            claimed_lcd_blanked=False,
        )
        self.assertFalse(bad_lcd.valid)
        self.assertEqual(
            bad_lcd.status,
            STATUS_BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION,
        )

        bad_touch = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G113,
            claimed_lcd_touch_focus_active=True,
        )
        self.assertFalse(bad_touch.valid)
        self.assertEqual(
            bad_touch.status,
            STATUS_BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION,
        )

    def test_26_g113_hdmi_1080_clamp_for_internal_rec_plus_log_or_pplut1_4(self) -> None:
        for log_mode in (
            LOG_SHOOTING_FLEXIBLE_ISO_G113,
            LOG_SHOOTING_CINE_EI_G113,
            LOG_SHOOTING_CINE_EI_QUICK_G113,
        ):
            res = verify_usb_mode_and_hdmi_info_guard(
                pre_reset_rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G113,
                pre_reset_output_resolution=HDMI_OUT_RES_2160P_G113,
                log_shooting=log_mode,
            )
            self.assertTrue(res.valid, msg=log_mode)
            self.assertTrue(res.hdmi_1080_log_pplut_clamp_active)
            self.assertEqual(res.effective_hdmi_output_resolution, HDMI_CLAMPED_1080_TOKEN_G113)

        for pplut in PPLUT_PICTURE_PROFILES_G113:
            res = verify_usb_mode_and_hdmi_info_guard(
                pre_reset_rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G113,
                pre_reset_output_resolution=HDMI_OUT_RES_2160P_G113,
                picture_profile=pplut,
            )
            self.assertTrue(res.valid, msg=pplut)
            self.assertTrue(res.hdmi_1080_log_pplut_clamp_active)
            self.assertEqual(res.effective_hdmi_output_resolution, HDMI_CLAMPED_1080_TOKEN_G113)

        bad_claim = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G113,
            pre_reset_output_resolution=HDMI_OUT_RES_2160P_G113,
            log_shooting=LOG_SHOOTING_CINE_EI_G113,
            claimed_effective_hdmi_output_resolution="2160p",
        )
        self.assertFalse(bad_claim.valid)
        self.assertEqual(
            bad_claim.status,
            STATUS_BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION,
        )

    def test_27_g113_4k_clean_feed_forces_hdmi_info_off_and_unblanks_lcd(self) -> None:
        self.assertEqual(REC_MEDIA_HDMI_OFF_RESID16_G113, 0x6573)
        self.assertEqual(RAW_OUTPUT_RESID16_G113, 0x6E97)
        for trig in (
            dict(pre_reset_rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113),
            dict(pre_reset_raw_output=RAW_OUTPUT_ON_G113),
        ):
            res = verify_usb_mode_and_hdmi_info_guard(
                pre_reset_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G113,
                log_shooting=LOG_SHOOTING_CINE_EI_G113,
                **trig,
            )
            self.assertTrue(res.valid, msg=trig)
            self.assertTrue(res.hdmi_clean_feed_4k_forced_off_active)
            self.assertEqual(res.effective_hdmi_info_display, HDMI_INFO_DISPLAY_OFF_G113)
            self.assertEqual(res.effective_hdmi_output_resolution, HDMI_4K_TOKEN_G113)
            self.assertFalse(res.lcd_blanked)
            self.assertTrue(res.lcd_touch_focus_active)

            bad = verify_usb_mode_and_hdmi_info_guard(
                pre_reset_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G113,
                claimed_effective_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G113,
                **trig,
            )
            self.assertFalse(bad.valid, msg=trig)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION,
            )

    def test_28_g113_blocks_hdmi_only_or_raw_output_in_sq_mode(self) -> None:
        for kw in (
            dict(shoot_mode=SHOOT_MODE_SQ_G113, pre_reset_rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113),
            dict(shoot_mode=SHOOT_MODE_SQ_G113, pre_reset_raw_output=RAW_OUTPUT_ON_G113),
        ):
            res = verify_usb_mode_and_hdmi_info_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION,
            )

    def test_29_g113_setup_items_survive_camera_and_network_reset_except_framing(self) -> None:
        for r_act in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE276,
        ):
            res = verify_usb_mode_and_hdmi_info_guard(
                reset_action=r_act,
                pre_reset_usb_connection_mode=USB_CONN_SEL_WHEN_CONNECT_G113,
                pre_reset_usb_lun_setting=USB_LUN_SINGLE_G113,
                pre_reset_usb_power_supply=USB_POWER_SUPPLY_OFF_G113,
                pre_reset_hdmi_info_display=HDMI_INFO_DISPLAY_OFF_G113,
                pre_reset_rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113,
                pre_reset_raw_output=RAW_OUTPUT_ON_G113,
                pre_reset_output_resolution=HDMI_OUT_RES_1080P_G113,
                pre_reset_framing_settings_hdmi=FRAMING_HDMI_FULL_G113,
            )
            self.assertTrue(res.valid, msg=f"{r_act}: {res.errors}")
            self.assertEqual(res.effective_post_reset_usb_lun_setting, USB_LUN_SINGLE_G113)
            self.assertEqual(res.effective_post_reset_usb_power_supply, USB_POWER_SUPPLY_OFF_G113)
            self.assertEqual(res.effective_post_reset_hdmi_info_display, HDMI_INFO_DISPLAY_OFF_G113)
            self.assertEqual(
                res.effective_post_reset_rec_media_dur_hdmi_output,
                REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113,
            )
            self.assertEqual(res.effective_post_reset_raw_output, RAW_OUTPUT_ON_G113)
            self.assertEqual(res.effective_post_reset_output_resolution, HDMI_OUT_RES_1080P_G113)
            expected_framing = (
                FRAMING_HDMI_FACTORY_DEFAULT_G113
                if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET
                else FRAMING_HDMI_FULL_G113
            )
            self.assertEqual(res.effective_post_reset_framing_settings_hdmi, expected_framing)

    def test_30_g113_initialize_resets_all_setup_usb_and_hdmi_items_to_defaults(self) -> None:
        res = verify_usb_mode_and_hdmi_info_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_usb_connection_mode=USB_CONN_MASS_STORAGE_MSC_G113,
            pre_reset_usb_lun_setting=USB_LUN_SINGLE_G113,
            pre_reset_usb_power_supply=USB_POWER_SUPPLY_OFF_G113,
            pre_reset_hdmi_info_display=HDMI_INFO_DISPLAY_OFF_G113,
            pre_reset_rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113,
            pre_reset_raw_output=RAW_OUTPUT_ON_G113,
            pre_reset_output_resolution=HDMI_OUT_RES_1080I_G113,
            pre_reset_framing_settings_hdmi=FRAMING_HDMI_FULL_G113,
            air_gapped_tier0_bench=False,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_post_reset_usb_connection_mode, USB_CONNECTION_MODE_FACTORY_DEFAULT_G113)
        self.assertEqual(res.effective_post_reset_usb_lun_setting, USB_LUN_FACTORY_DEFAULT_G113)
        self.assertEqual(res.effective_post_reset_usb_power_supply, USB_POWER_SUPPLY_FACTORY_DEFAULT_G113)
        self.assertEqual(res.effective_post_reset_hdmi_info_display, HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113)
        self.assertEqual(res.effective_post_reset_rec_media_dur_hdmi_output, REC_MEDIA_HDMI_FACTORY_DEFAULT_G113)
        self.assertEqual(res.effective_post_reset_raw_output, RAW_OUTPUT_FACTORY_DEFAULT_G113)
        self.assertEqual(res.effective_post_reset_output_resolution, HDMI_OUT_RES_FACTORY_DEFAULT_G113)
        self.assertEqual(res.effective_post_reset_framing_settings_hdmi, FRAMING_HDMI_FACTORY_DEFAULT_G113)

    def test_31_g113_blocks_reported_reset_drift_violations(self) -> None:
        r1 = verify_usb_mode_and_hdmi_info_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_usb_lun_setting=USB_LUN_SINGLE_G113,
            claimed_post_reset_usb_lun_setting=USB_LUN_MULTI_G113,
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G113_SETUP_RESET_PERSISTENCE_VIOLATION)

        r2 = verify_usb_mode_and_hdmi_info_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_framing_settings_hdmi=FRAMING_HDMI_FULL_G113,
            claimed_post_reset_framing_settings_hdmi=FRAMING_HDMI_FULL_G113,
        )
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G113_SETUP_RESET_PERSISTENCE_VIOLATION)

    def test_32_g113_blocks_invalid_telemetry(self) -> None:
        bad_cases = [
            dict(body_model_name="ILME-FX6"),
            dict(body_model_id=0x12345678),
            dict(help_guide_code="ilc/9999"),
            dict(firmware_version=""),
            dict(reset_action="BAD_RESET"),
            dict(pre_reset_usb_connection_mode="FIREWIRE_DV"),
            dict(pre_reset_usb_lun_setting="TRIPLE"),
            dict(usb_port="HDMI_MICRO"),
            dict(shoot_mode="CINEMA"),
            dict(log_shooting="S-LOG2"),
            dict(picture_profile="PP99"),
            dict(pre_reset_output_resolution="8K"),
            dict(claimed_usb_streaming_spoof_events=-1),
        ]
        for kw in bad_cases:
            res = verify_usb_mode_and_hdmi_info_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G113_TELEMETRY_INVALID, msg=kw)

    def test_33_g113_256_state_matrix_verified(self) -> None:
        mat = compute_usb_mode_and_hdmi_info_matrix()
        self.assertEqual(mat["states_checked"], 256)
        self.assertEqual(mat["reset_corruptions"], 0)
        self.assertEqual(mat["clean_feed_override_violations"], 0)
        self.assertEqual(mat["log_1080_clamp_violations"], 0)
        self.assertTrue(mat["all_invariants_hold"])

    def test_34_g113_wrapper_and_donor_failure_propagation(self) -> None:
        verdict, gres = evaluate_g113_usb_mode_and_hdmi_info_guard(
            donor_audit=self.clean_audit,
        )
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.gate_id, G113_GATE_ID)
        self.assertTrue(gres.valid)
        self.assertEqual(gres.status, STATUS_VERIFIED_G113)
        self.assertFalse(gres.persistent_emmc_writes_authorized)
        self.assertEqual(gres.raw_firmware_bytes_leaked, 0)

        bad_donor = dataclasses.replace(
            self.clean_audit,
            valid=False,
            status=STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY,
            errors=("corrupt donor",),
        )
        v_bad, r_bad = evaluate_g113_usb_mode_and_hdmi_info_guard(donor_audit=bad_donor)
        self.assertFalse(v_bad.passed)
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.status, STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY)

    def test_35_g113_menu_paths_and_enums_exact(self) -> None:
        self.assertEqual(USB_CONNECTION_MODE_MENU_PATH_G113, "MENU -> Setup -> [USB] -> [USB Connection Mode]")
        self.assertEqual(USB_LUN_SETTING_MENU_PATH_G113, "MENU -> Setup -> [USB] -> [USB LUN Setting]")
        self.assertEqual(USB_POWER_SUPPLY_MENU_PATH_G113, "MENU -> Setup -> [USB] -> [USB Power Supply]")
        self.assertEqual(
            HDMI_INFO_DISPLAY_MENU_PATH_G113,
            "MENU -> Setup -> [External Output] -> [HDMI Info. Display]",
        )
        self.assertEqual(
            HDMI_OUTPUT_SETTINGS_MENU_PATH_G113,
            "MENU -> Setup -> [External Output] -> [HDMI Output Settings]",
        )
        self.assertEqual(
            FRAMING_SETTINGS_HDMI_MENU_PATH_G113,
            "MENU -> Setup -> [External Output] -> [Framing Settings]",
        )
        self.assertEqual(len(ALLOWED_USB_PORTS_G113), 3)
        self.assertEqual(len(ALLOWED_HDMI_OUTPUT_RESOLUTIONS_G113), 4)
        self.assertEqual(len(ALLOWED_SHOOT_MODES_G113), 3)
        self.assertEqual(len(ALLOWED_LOG_SHOOTING_MODES_G113), 4)
        self.assertEqual(len(ALLOWED_PICTURE_PROFILES_G113), 16)
        self.assertEqual(len(ALLOWED_FRAMING_HDMI_MODES_G113), 2)
        self.assertEqual(len(ALLOWED_HDMI_INFO_DISPLAY_MODES_G113), 2)
        self.assertEqual(len(ALLOWED_RAW_OUTPUT_MODES_G113), 2)
        self.assertEqual(len(ALLOWED_REC_MEDIA_DUR_HDMI_MODES_G113), 2)
        self.assertEqual(len(ALLOWED_USB_POWER_SUPPLY_MODES_G113), 2)

    def test_36_g113_resolve_helper_normalization(self) -> None:
        st = resolve_fx3_usb_mode_and_hdmi_info_state(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_usb_connection_mode="Sel. When Connect",
            pre_reset_rec_media_dur_hdmi_output="Off(HDMI Only)",
            pre_reset_hdmi_info_display="On",
            pre_reset_framing_settings_hdmi="Full",
        )
        self.assertEqual(st["effective_hdmi_info_display"], HDMI_INFO_DISPLAY_OFF_G113)
        self.assertEqual(st["effective_hdmi_output_resolution"], HDMI_4K_TOKEN_G113)
        self.assertEqual(st["effective_post_reset_framing_settings_hdmi"], FRAMING_HDMI_CROP_G113)

    # ------------------------------------------------------------------
    # 37..58: Gate G114 ([Protect] vs [Format] Slot-1 WP + [Reset Network Set.] Zero-RF)
    # ------------------------------------------------------------------

    def test_37_g114_defaults_pass(self) -> None:
        res = verify_protect_and_network_reset_guard()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G114)
        self.assertTrue(res.protect_blocks_delete)
        self.assertTrue(res.copy_strips_destination_protect)
        self.assertTrue(res.format_wipes_protected_files_and_m1_m4)
        self.assertTrue(res.slot1_sd_physical_wp_locked)
        self.assertTrue(res.slot1_format_hard_locked)
        self.assertTrue(res.slot1_vault_write_firewall_enforced)
        self.assertEqual(res.slot1_wp_firewall_violation_events, 0)
        self.assertEqual(res.post_reset_airplane_mode, AIRPLANE_MODE_ON_G114)
        self.assertEqual(res.post_network_reset_rf_hazard_events, 0)

    def test_38_g114_all_5_protect_scopes_and_resid16s(self) -> None:
        self.assertEqual(PROTECT_RESID16_G114, 0xE2C9)
        self.assertEqual(
            ALLOWED_PROTECT_SCOPES_G114,
            (
                PROTECT_SCOPE_SINGLE_G114,
                PROTECT_SCOPE_MULTIPLE_IMG_G114,
                PROTECT_SCOPE_ALL_IN_FOLDER_G114,
                PROTECT_SCOPE_ALL_WITH_DATE_G114,
                PROTECT_SCOPE_ALL_IN_GROUP_G114,
            ),
        )
        self.assertEqual(PROTECT_SCOPE_RESID16_MAP_G114[PROTECT_SCOPE_SINGLE_G114][0], 0xE2C9)
        self.assertEqual(PROTECT_SCOPE_RESID16_MAP_G114[PROTECT_SCOPE_MULTIPLE_IMG_G114][0], 0xE2CA)
        self.assertEqual(PROTECT_SCOPE_RESID16_MAP_G114[PROTECT_SCOPE_ALL_IN_FOLDER_G114][0], 0x6848)
        self.assertEqual(PROTECT_SCOPE_RESID16_MAP_G114[PROTECT_SCOPE_ALL_WITH_DATE_G114][0], 0x69F7)
        self.assertEqual(PROTECT_SCOPE_RESID16_MAP_G114[PROTECT_SCOPE_ALL_IN_GROUP_G114][0], 0xE826)
        for scope in ALLOWED_PROTECT_SCOPES_G114:
            res = verify_protect_and_network_reset_guard(protect_scope=scope)
            self.assertTrue(res.valid, msg=scope)
            self.assertEqual(res.protect_scope, scope)

    def test_39_g114_format_resid16s_and_protect_vs_format_semantics(self) -> None:
        self.assertEqual(FORMAT_RESID16_G114, 0xE449)
        self.assertEqual(FORMAT_CONFIRM_RESID16_G114, 0xE414)
        self.assertEqual(FORMAT_QUICK_RESID16_G114, 0xE792)
        self.assertEqual(FORMAT_FULL_RESID16_G114, 0xE8F5)

        for bad_kw in (
            dict(claimed_protect_blocks_delete=False),
            dict(claimed_copy_strips_destination_protect=False),
            dict(claimed_format_preserves_protected_files=True),
            dict(claimed_format_preserves_m1_m4=True),
        ):
            res = verify_protect_and_network_reset_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G114_PROTECT_SCOPE_OR_PLAYBACK_CONTRACT_VIOLATION,
                msg=bad_kw,
            )

    def test_40_g114_blocks_protect_only_without_slot1_wp_and_firewall(self) -> None:
        cases = [
            dict(protect_only_without_slot1_wp=True),
            dict(slot1_sd_physical_wp_locked=False),
            dict(slot1_format_hard_locked=False),
            dict(slot1_vault_write_firewall_enforced=False),
            dict(claimed_slot1_wp_firewall_violation_events=1),
        ]
        for kw in cases:
            res = verify_protect_and_network_reset_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G114_PROTECT_ONLY_WITHOUT_SLOT1_WP_FIREWALL_VIOLATION,
                msg=kw,
            )
            self.assertGreaterEqual(res.slot1_wp_firewall_violation_events, 1)

    def test_41_g114_blocks_all_delete_and_format_ops_on_slot1_vault(self) -> None:
        for op in (
            MEDIA_OP_DELETE_SINGLE_G114,
            MEDIA_OP_DELETE_PRESSING_TWICE_G114,
            MEDIA_OP_FORMAT_QUICK_G114,
            MEDIA_OP_FORMAT_FULL_G114,
        ):
            res = verify_protect_and_network_reset_guard(
                requested_media_op=op,
                target_slot=TARGET_SLOT_1_G114,
                slot1_holds_recovery_vault=True,
            )
            self.assertFalse(res.valid, msg=op)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G114_PROTECT_ONLY_WITHOUT_SLOT1_WP_FIREWALL_VIOLATION,
                msg=op,
            )

    def test_42_g114_allows_slot2_media_ops_when_slot1_dual_layer_locked(self) -> None:
        for op in (
            MEDIA_OP_DELETE_SINGLE_G114,
            MEDIA_OP_FORMAT_QUICK_G114,
            MEDIA_OP_FORMAT_FULL_G114,
        ):
            res = verify_protect_and_network_reset_guard(
                requested_media_op=op,
                target_slot=TARGET_SLOT_2_G114,
                slot1_holds_recovery_vault=True,
                slot1_sd_physical_wp_locked=True,
                slot1_format_hard_locked=True,
            )
            self.assertTrue(res.valid, msg=f"{op}: {res.errors}")

    def test_43_g114_reset_network_set_clears_only_network_and_reboots(self) -> None:
        self.assertEqual(RESET_NETWORK_SET_RESID16_G114, 0x60D3)
        self.assertEqual(RESET_NETWORK_PROMPT_RESID16_G114, 0x65D3)
        self.assertEqual(AIRPLANE_MODE_RESID16_G114, 0x6DF9)
        self.assertGreaterEqual(len(NETWORK_RESET_CLEARED_CATEGORIES_G114), 6)
        self.assertIn("CAMSET (M1..M4 on card)", NETWORK_RESET_PRESERVED_DOMAINS_G114)
        self.assertIn("(Setup)", NETWORK_RESET_PRESERVED_DOMAINS_G114)
        self.assertIn("(Playback)", NETWORK_RESET_PRESERVED_DOMAINS_G114)

        res = verify_protect_and_network_reset_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
            post_network_reset_reboot_completed=True,
            post_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertTrue(res.auto_reboot_triggered)
        self.assertEqual(res.effective_immediate_post_network_reset_airplane_mode, AIRPLANE_MODE_OFF_G114)
        self.assertEqual(res.post_reset_airplane_mode, AIRPLANE_MODE_ON_G114)
        self.assertTrue(res.playback_protect_survives_camera_and_network_reset)

    def test_44_g114_blocks_network_reset_without_post_reboot_airplane_on(self) -> None:
        r_omitted = verify_protect_and_network_reset_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
            post_network_reset_reboot_completed=True,
            post_reset_airplane_mode=None,
            air_gapped_zero_rf_bench=True,
        )
        self.assertFalse(r_omitted.valid)
        self.assertEqual(
            r_omitted.status,
            STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD,
        )

        r_off = verify_protect_and_network_reset_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
            post_network_reset_reboot_completed=True,
            post_reset_airplane_mode=AIRPLANE_MODE_OFF_G114,
            air_gapped_zero_rf_bench=True,
        )
        self.assertFalse(r_off.valid)
        self.assertEqual(
            r_off.status,
            STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD,
        )

        r_radio = verify_protect_and_network_reset_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
            post_network_reset_reboot_completed=True,
            post_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
            rf_radio_active_after_reset=True,
        )
        self.assertFalse(r_radio.valid)
        self.assertEqual(
            r_radio.status,
            STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD,
        )

    def test_45_g114_blocks_incomplete_auto_reboot_or_reset_boundary_violation(self) -> None:
        cases = [
            dict(
                reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
                post_network_reset_reboot_completed=False,
                post_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
            ),
            dict(
                reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
                claimed_auto_reboot_triggered=False,
                post_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
            ),
            dict(
                reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
                claimed_network_reset_clears_shooting_or_setup=True,
                post_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
            ),
            dict(
                reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
                claimed_network_reset_clears_camset=True,
                post_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
            ),
        ]
        for kw in cases:
            res = verify_protect_and_network_reset_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G114_RESET_BOUNDARY_OR_AUTO_REBOOT_VIOLATION,
                msg=kw,
            )

    def test_46_g114_playback_protect_survives_camera_and_network_reset_cleared_by_initialize(self) -> None:
        for r_act, expected_survive in (
            (RESET_ACTION_CAMERA_SETTINGS_RESET, True),
            (RESET_ACTION_RESET_NETWORK_SET_PHASE276, True),
            (RESET_ACTION_INITIALIZE, False),
        ):
            res = verify_protect_and_network_reset_guard(
                reset_action=r_act,
                post_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
                claimed_playback_protect_survives_network_reset=expected_survive,
            )
            self.assertTrue(res.valid, msg=f"{r_act}: {res.errors}")
            self.assertEqual(res.playback_protect_survives_camera_and_network_reset, expected_survive)

        bad = verify_protect_and_network_reset_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
            post_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
            claimed_playback_protect_survives_network_reset=False,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G114_PROTECT_SCOPE_OR_PLAYBACK_CONTRACT_VIOLATION)

    def test_47_g114_post_network_reset_performed_flag_without_action_triggers_rf_guard(self) -> None:
        res = verify_protect_and_network_reset_guard(
            reset_action=RESET_ACTION_NONE,
            post_network_reset_performed=True,
            post_reset_airplane_mode=None,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD)

    def test_48_g114_non_airgapped_allows_airplane_off_after_network_reset(self) -> None:
        res = verify_protect_and_network_reset_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
            post_network_reset_reboot_completed=True,
            post_reset_airplane_mode=AIRPLANE_MODE_OFF_G114,
            air_gapped_zero_rf_bench=False,
        )
        self.assertTrue(res.valid, msg=res.errors)

    def test_49_g114_blocks_invalid_telemetry(self) -> None:
        bad_cases = [
            dict(body_model_name="ILME-FX6"),
            dict(body_model_id=0x11111111),
            dict(help_guide_code="ilc/1111"),
            dict(firmware_version=""),
            dict(reset_action="BAD_RESET"),
            dict(protect_scope="All in Universe"),
            dict(requested_media_op="WIPE_ALL"),
            dict(target_slot="SLOT_99"),
            dict(pre_reset_airplane_mode="MAYBE"),
            dict(post_reset_airplane_mode="MAYBE"),
            dict(claimed_slot1_wp_firewall_violation_events=-1),
        ]
        for kw in bad_cases:
            res = verify_protect_and_network_reset_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G114_TELEMETRY_INVALID, msg=kw)

    def test_50_g114_160_state_matrix_verified(self) -> None:
        mat = compute_protect_and_network_reset_matrix()
        self.assertEqual(mat["states_checked"], 160)
        self.assertEqual(mat["playback_reset_corruptions"], 0)
        self.assertEqual(mat["unprotected_slot1_detected"], 120)
        self.assertEqual(mat["rf_hazards_detected"], 40)
        self.assertTrue(mat["all_invariants_hold"])

    def test_51_g114_wrapper_and_donor_failure_propagation(self) -> None:
        verdict, gres = evaluate_g114_protect_and_network_reset_guard(
            donor_audit=self.clean_audit,
        )
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.gate_id, G114_GATE_ID)
        self.assertTrue(gres.valid)
        self.assertEqual(gres.status, STATUS_VERIFIED_G114)
        self.assertFalse(gres.persistent_emmc_writes_authorized)
        self.assertEqual(gres.raw_firmware_bytes_leaked, 0)

        bad_donor = dataclasses.replace(
            self.clean_audit,
            valid=False,
            status=STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY,
            errors=("corrupt donor",),
        )
        v_bad, r_bad = evaluate_g114_protect_and_network_reset_guard(donor_audit=bad_donor)
        self.assertFalse(v_bad.passed)
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.status, STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY)

    def test_52_g114_menu_paths_and_constants(self) -> None:
        self.assertEqual(PROTECT_MENU_PATH_G114, "MENU -> Playback -> [Selection/Memo] -> [Protect]")
        self.assertEqual(FORMAT_MENU_PATH_G114, "MENU -> Shooting -> [Media] -> [Format]")
        self.assertEqual(
            RESET_NETWORK_SET_MENU_PATH_G114,
            "MENU -> Network -> [Network Option] -> [Reset Network Set.]",
        )
        self.assertEqual(
            AIRPLANE_MODE_MENU_PATH_G114,
            "MENU -> Network -> [Network Option] -> [Airplane Mode]",
        )
        self.assertEqual(AIRPLANE_MODE_FACTORY_DEFAULT_G114, "Off")
        self.assertEqual(len(ALLOWED_AIRPLANE_MODES_G114), 2)
        self.assertEqual(len(ALLOWED_MEDIA_OPS_G114), 5)
        self.assertEqual(len(ALLOWED_TARGET_SLOTS_G114), 3)

    def test_53_g114_resolve_helper_semantics(self) -> None:
        st_nw = resolve_fx3_protect_and_network_reset_state(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE276,
            pre_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
            post_reboot_reassert_airplane_mode=None,
        )
        self.assertTrue(st_nw["auto_reboot_triggered"])
        self.assertEqual(st_nw["effective_immediate_post_network_reset_airplane_mode"], "Off")
        self.assertEqual(st_nw["post_reset_airplane_mode"], "Off")
        self.assertTrue(st_nw["playback_protect_survives_reset"])

        st_init = resolve_fx3_protect_and_network_reset_state(
            reset_action=RESET_ACTION_INITIALIZE,
            post_reboot_reassert_airplane_mode=AIRPLANE_MODE_ON_G114,
        )
        self.assertFalse(st_init["auto_reboot_triggered"])
        self.assertFalse(st_init["playback_protect_survives_reset"])

    def test_54_g113_and_g114_persistent_write_escalation_blocked(self) -> None:
        v113, r113 = evaluate_g113_usb_mode_and_hdmi_info_guard(
            donor_audit=self.clean_audit,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v113.passed)
        self.assertFalse(r113.valid)
        self.assertFalse(r113.persistent_emmc_writes_authorized)

        v114, r114 = evaluate_g114_protect_and_network_reset_guard(
            donor_audit=self.clean_audit,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v114.passed)
        self.assertFalse(r114.valid)
        self.assertFalse(r114.persistent_emmc_writes_authorized)

    def test_55_g113_and_g114_to_dict_serializable(self) -> None:
        _, r113 = evaluate_g113_usb_mode_and_hdmi_info_guard(donor_audit=self.clean_audit)
        _, r114 = evaluate_g114_protect_and_network_reset_guard(donor_audit=self.clean_audit)
        j113 = json.loads(json.dumps(r113.to_dict(), ensure_ascii=False))
        j114 = json.loads(json.dumps(r114.to_dict(), ensure_ascii=False))
        self.assertEqual(j113["status"], STATUS_VERIFIED_G113)
        self.assertEqual(j114["status"], STATUS_VERIFIED_G114)

    def test_56_g113_hdmi_on_without_4k_override_still_allows_off_default_override(self) -> None:
        res = verify_usb_mode_and_hdmi_info_guard(
            pre_reset_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G113,
            pre_reset_output_resolution=HDMI_OUT_RES_AUTO_G113,
            claimed_effective_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G113,
            claimed_effective_hdmi_output_resolution="Auto",
        )
        self.assertTrue(res.valid, msg=res.errors)

    def test_57_g114_slot1_no_vault_allows_media_ops(self) -> None:
        res = verify_protect_and_network_reset_guard(
            slot1_holds_recovery_vault=False,
            slot1_sd_physical_wp_locked=False,
            slot1_format_hard_locked=False,
            requested_media_op=MEDIA_OP_FORMAT_QUICK_G114,
            target_slot=TARGET_SLOT_1_G114,
        )
        self.assertTrue(res.valid, msg=res.errors)

    def test_58_g113_case_insensitive_enum_normalization(self) -> None:
        res = verify_usb_mode_and_hdmi_info_guard(
            reset_action="[camera settings reset]",
            pre_reset_usb_connection_mode="select when connect",
            pre_reset_usb_lun_setting="[single]",
            pre_reset_usb_power_supply="[off]",
            usb_port="usb-c",
            shoot_mode="movie",
            log_shooting="cine ei",
            pre_reset_framing_settings_hdmi="full",
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_post_reset_usb_lun_setting, USB_LUN_SINGLE_G113)
        self.assertEqual(res.effective_post_reset_framing_settings_hdmi, FRAMING_HDMI_CROP_G113)

    # ------------------------------------------------------------------
    # 59..67: Unified 114-Gate Preflight Engine
    # ------------------------------------------------------------------

    def test_59_unified_114_gates_offline_111_of_114(self) -> None:
        rep = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_112_override=self.clean_offline_112,
        )
        self.assertEqual(rep.summary["total_gates"], 114)
        self.assertEqual(rep.summary["verified_gates"], 111)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_111_gates_verified)
        self.assertFalse(rep.all_114_gates_verified)
        self.assertTrue(rep.g113_to_g114_all_passed)
        self.assertEqual(rep.status, "VERIFIED_111_OF_114_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 114)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_60_unified_114_gates_dry_run_simulated_114_of_114(self) -> None:
        rep = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_112_override=self.clean_dryrun_112,
        )
        self.assertEqual(rep.summary["total_gates"], 114)
        self.assertEqual(rep.summary["verified_gates"], 114)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.offline_111_gates_verified)
        self.assertTrue(rep.all_114_gates_verified)
        self.assertTrue(rep.g113_to_g114_all_passed)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.status, "VERIFIED_ALL_114_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)

    def test_61_unified_114_gates_real_unmocked_delegation(self) -> None:
        rep = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertTrue(rep.all_114_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 114)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_62_unified_114_gates_g113_failure_blocks_report(self) -> None:
        rep = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_112_override=self.clean_dryrun_112,
            usb_mode_hdmi_info_kwargs={
                "claimed_fx3_exposes_usb_streaming": True,
            },
        )
        self.assertFalse(rep.g113_to_g114_all_passed)
        self.assertFalse(rep.all_114_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G113_FX3_NOUVC_USB_STREAMING_SPOOF_VIOLATION,
        )
        self.assertEqual(rep.summary["verified_gates"], 113)

    def test_63_unified_114_gates_g114_failure_blocks_report(self) -> None:
        rep = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_112_override=self.clean_dryrun_112,
            protect_and_network_reset_kwargs={
                "reset_action": RESET_ACTION_RESET_NETWORK_SET_PHASE276,
                "post_reset_airplane_mode": AIRPLANE_MODE_OFF_G114,
            },
        )
        self.assertFalse(rep.g113_to_g114_all_passed)
        self.assertFalse(rep.all_114_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD,
        )
        self.assertEqual(rep.summary["verified_gates"], 113)

    def test_64_unified_114_gates_blocks_persistent_write_escalation(self) -> None:
        rep = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
            master_112_override=self.clean_dryrun_112,
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.all_114_gates_verified)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_65_unified_114_gates_report_json_serializable(self) -> None:
        rep = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_112_override=self.clean_dryrun_112,
        )
        raw = json.dumps(rep.to_dict(), ensure_ascii=False)
        decoded = json.loads(raw)
        self.assertEqual(decoded["summary"]["verified_gates"], 114)
        self.assertEqual(decoded["g113_result"]["status"], STATUS_VERIFIED_G113)
        self.assertEqual(decoded["g114_result"]["status"], STATUS_VERIFIED_G114)

    def test_66_run_114_gate_preflight_and_evaluate_114_master_aliases(self) -> None:
        rep1 = run_114_gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_112_override=self.clean_offline_112,
        )
        rep2 = evaluate_114_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_112_override=self.clean_dryrun_112,
        )
        self.assertEqual(rep1.summary["verified_gates"], 111)
        self.assertEqual(rep2.summary["verified_gates"], 114)

    def test_67_reset_actions_tuple_exact(self) -> None:
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE276,
            (
                RESET_ACTION_NONE,
                RESET_ACTION_CAMERA_SETTINGS_RESET,
                RESET_ACTION_RESET_NETWORK_SET_PHASE276,
                RESET_ACTION_INITIALIZE,
            ),
        )
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE276, "7.02")
        self.assertEqual(FX6_DEFAULT_FW_VERSION_PHASE276, "6.01")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE276, "ilc/2210")
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX6_MODEL_NAME, "ILME-FX6")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)

    # ------------------------------------------------------------------
    # 68..76: CLI Entrypoints, Standalone Main, Subprocess Portability & Upstream
    # ------------------------------------------------------------------

    def test_68_cli_verify_usb_mode_hdmi_info_guard_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-usb-mode-hdmi-info-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G113_", buf.getvalue())
        self.assertIn("usb_modes=4", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g113-usb-mode-hdmi-info", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G113)

    def test_69_cli_verify_protect_and_network_reset_guard_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-protect-and-network-reset-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G114_", buf.getvalue())
        self.assertIn("slot1_wp=True", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g114-protect-network-reset", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G114)

    def test_70_cli_verify_114_gates_offline_text_and_json(self) -> None:
        offline_114 = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_112_override=self.clean_offline_112,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_114gate_preflight",
            return_value=offline_114,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-114-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=111/114", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(["verify-114-gates", "--force-clean-room", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 111)
            self.assertTrue(parsed["offline_111_gates_verified"])

    def test_71_cli_verify_114_gates_dry_run_text_and_json(self) -> None:
        dryrun_114 = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_112_override=self.clean_dryrun_112,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_114gate_preflight",
            return_value=dryrun_114,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-114-gates", "--force-clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=114/114", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-114-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_114_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 114)

    def test_72_standalone_module_main_offline_and_dry_run(self) -> None:
        offline_114 = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_112_override=self.clean_offline_112,
        )
        dryrun_114 = evaluate_114gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_112_override=self.clean_dryrun_112,
        )
        with mock.patch(
            "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.evaluate_114gate_preflight",
            return_value=offline_114,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=111/114", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.evaluate_114gate_preflight",
            return_value=dryrun_114,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = module_main(["--force-clean-room", "--simulate-bench-dry-run", "--json"])
            self.assertEqual(rc_j, 0)
            self.assertTrue(json.loads(jbuf.getvalue())["all_114_gates_verified"])

    def test_73_subprocess_cli_verify_g113_g114_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for cmd, expected_status in (
            ("verify-usb-mode-hdmi-info-guard", STATUS_VERIFIED_G113),
            ("verify-protect-and-network-reset-guard", STATUS_VERIFIED_G114),
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_safety", cmd, "--force-clean-room", "--json"],
                cwd=str(DEFAULT_REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=_subprocess_timeout_seconds(),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["status"], expected_status)

    def test_74_subprocess_cli_verify_114_gates_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-114-gates",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_114_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 114)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_75_fx3_clean_room_test_and_force_clean_room_env_in_master_114(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE276, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                rep = evaluate_114gate_preflight(
                    master_112_override=self.clean_offline_112,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)

    def test_76_argparse_help_and_upstream_verify_112_gates_parity(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for subcmd in (
            "verify-usb-mode-hdmi-info-guard",
            "verify-protect-and-network-reset-guard",
            "verify-114-gates",
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_safety", subcmd, "--help"],
                cwd=str(DEFAULT_REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=_subprocess_timeout_seconds(),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with mock.patch(
            "fx3_safety.__main__.evaluate_112gate_preflight",
            return_value=self.clean_offline_112,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-112-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=109/112", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
