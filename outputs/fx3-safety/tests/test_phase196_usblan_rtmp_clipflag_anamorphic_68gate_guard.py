"""Fast dual-mode unit tests for Phase 196 — Real-Hardware Main Track Part 21:
Gate G67 (`ILME-FX3` `Ver. 7.00 / 7.02` Power-On `USB-LAN` `RNDIS/CDC-NCM`
Auto-Connect, Stock `/setting` Protection, `RTMP/RTMPS/SRT <= 38 Mbps`
`3840x2160 59.94p` Cap & `RTMPS` TLS `EROFS` Verification),
Gate G68 (`Creators' Cloud` `Creators' App >= 3.1.0` / `M&C >= 2.4.0` Non-Destructive
MXF/XML Sidecar `OK/NG/KEEP` Clip-Flag Hygiene, `1.3x/1.5x/1.6x/2.0x` Anamorphic
De-Squeeze Monitoring Lock with HDMI `4264x2408` Linear RAW Auto-Disable &
`CXD90057` Bright-Monitoring + Focus-Magnifier Coexistence Guard),
and 68-Gate Master Preflight (`G01..G68` / `verify-68-gates` / `run_68_gate_preflight`).
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
    STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED,
    STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED,
    evaluate_62gate_preflight,
)
from fx3_safety.realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE,
    STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE,
    evaluate_64gate_preflight,
)
from fx3_safety.realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard import (
    STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN,
    STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE,
    evaluate_66gate_preflight,
)
from fx3_safety.realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard import (
    ACTIVE_STREAMING_PROTOCOLS,
    ALLOWED_ANAMORPHIC_DESQUEEZE_RATIOS,
    ALLOWED_CLIP_FLAG_SIDECAR_FORMATS,
    ALLOWED_FOCUS_MAGNIFIER_FACTORS,
    ALLOWED_G67_BODY_MODELS,
    ALLOWED_STREAMING_CODECS,
    ALLOWED_STREAMING_PROTOCOLS,
    ALLOWED_USBLAN_ADAPTER_CHIPSETS,
    ALLOWED_USBLAN_PORTS,
    ALLOWED_USBLAN_POWER_MODES,
    ALLOWED_USBLAN_PROTOCOLS,
    CANONICAL_STREAMING_FPS,
    CREATORS_APP_MIN_VERSION,
    CXD90057_SOC_NAME,
    DEFAULT_SYNTHETIC_ESSENCE_SHA256,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FILTERABLE_CLIP_FLAGS,
    FORBIDDEN_STOCK_SETTING_PREFIXES,
    FX3_TARGET_FW_VERSION,
    G67,
    G67_GATE_CODE,
    G67_GATE_ID,
    G68,
    G68_GATE_CODE,
    G68_GATE_ID,
    GATE_G67_FX3_USBLAN_AUTOCONNECT_AND_RTMP_SRT_STREAMING_GUARD,
    GATE_G68_CREATORS_CLOUD_CLIPFLAG_ANAMORPHIC_AND_BRIGHT_MAGNIFIER_GUARD,
    HDMI_RAW_UNSCALED_HEIGHT,
    HDMI_RAW_UNSCALED_WIDTH,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    MAX_STREAMING_BITRATE_MBPS,
    MAX_STREAMING_FPS,
    MAX_STREAMING_HEIGHT,
    MAX_STREAMING_WIDTH,
    MIN_USBLAN_AUTOCONNECT_FW_VERSION,
    MONITOR_CONTROL_MIN_VERSION_G68,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE196_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_SCHEMA,
    REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_VERSION,
    REJECTED_USBLAN_ADAPTER_CHIPSETS,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED,
    STATUS_BLOCKED_G67_STAGEB_SETTING_PROFILE_OVERWRITE,
    STATUS_BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION,
    STATUS_BLOCKED_G67_TELEMETRY_INVALID,
    STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE,
    STATUS_BLOCKED_G68_ANAMORPHIC_DESQUEEZE_OR_HDMI_RAW_SCALE,
    STATUS_BLOCKED_G68_BRIGHT_MONITORING_MAGNIFIER_FAULT,
    STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR,
    STATUS_BLOCKED_G68_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE196_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G67,
    STATUS_VERIFIED_G68,
    STATUS_VERIFIED_SAFE,
    TLS_CERT_DEFAULT_PATH,
    TLS_CERT_EROFS_ERRNO,
    TLS_CERT_REQUIRED_MOUNT_FLAG,
    USBLAN_DC_C1_MIN_CABLE_AMPS,
    USBLAN_DC_C1_MIN_WATTS,
    USBLAN_MAX_AUTORECONNECT_LATENCY_MS,
    USBLAN_MIN_NPFZ100_PCT,
    VALID_CLIP_FLAGS,
    audit_phase196_donor_contracts,
    evaluate_68_master_safety_gates,
    evaluate_68gate_preflight,
    evaluate_g67_usblan_rtmp_guard,
    evaluate_g68_clipflag_anamorphic_guard,
    main as module_cli_main,
    run_68_gate_preflight,
    validate_anamorphic_desqueeze_and_hdmi_raw_lock,
    validate_bright_monitoring_and_focus_magnifier_cxd90057,
    validate_creators_cloud_clip_flag_hygiene,
    validate_network_streaming_rtmp_srt_and_tls,
    validate_usblan_poweron_autoconnect,
    verify_clipflag_anamorphic_and_bright_magnifier_guard,
    verify_usblan_autoconnect_and_rtmp_srt_guard,
)


def _create_synthetic_donor_tree(base: Path, *, corrupt_net: bool = False) -> Path:
    for key, (_body, rel_path, exp_size, _sha, markers, _lbl) in PINNED_PHASE196_DONOR_SPECS.items():
        p = base / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = bytearray(exp_size)
        cursor = 0
        for tok in markers:
            if corrupt_net and key == "fx3_libnetserviceether_so" and b"NetService" in tok:
                tok = b"CORRUPTED_NET_MARKER"
            payload[cursor : cursor + len(tok)] = tok
            cursor += len(tok) + 16
        p.write_bytes(bytes(payload))
    return base


class Phase196UsbLanRtmpClipFlagAnamorphic68GateGuardTests(unittest.TestCase):
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
            G67, GATE_G67_FX3_USBLAN_AUTOCONNECT_AND_RTMP_SRT_STREAMING_GUARD
        )
        self.assertEqual(
            G68, GATE_G68_CREATORS_CLOUD_CLIPFLAG_ANAMORPHIC_AND_BRIGHT_MAGNIFIER_GUARD
        )
        self.assertIs(run_68_gate_preflight, evaluate_68gate_preflight)
        self.assertIs(evaluate_68_master_safety_gates, evaluate_68gate_preflight)
        for name in (
            "G67",
            "G68",
            "run_68_gate_preflight",
            "evaluate_68gate_preflight",
            "evaluate_68_master_safety_gates",
            "evaluate_g67_usblan_rtmp_guard",
            "evaluate_g68_clipflag_anamorphic_guard",
            "realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, name), f"missing fx3_safety.{name}")
            self.assertIn(name, fx3_safety.__all__)

    def test_02_schema_version_and_wave24_phase196_constants(self) -> None:
        self.assertEqual(
            REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_SCHEMA,
            "fx3-realhw-usblan-rtmp-clipflag-anamorphic-68gate-preflight-v1",
        )
        self.assertEqual(REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_VERSION, "1.0.0")
        self.assertEqual(MIN_USBLAN_AUTOCONNECT_FW_VERSION, "7.00")
        self.assertEqual(FX3_TARGET_FW_VERSION, "7.02")
        self.assertEqual(MAX_STREAMING_BITRATE_MBPS, 38.0)
        self.assertEqual(MAX_STREAMING_WIDTH, 3840)
        self.assertEqual(MAX_STREAMING_HEIGHT, 2160)
        self.assertEqual(CANONICAL_STREAMING_FPS, 59.94)
        self.assertEqual(MAX_STREAMING_FPS, 60.0)
        self.assertEqual(TLS_CERT_EROFS_ERRNO, "EROFS")
        self.assertEqual(TLS_CERT_REQUIRED_MOUNT_FLAG, "MS_RDONLY")
        self.assertEqual(CREATORS_APP_MIN_VERSION, "3.1.0")
        self.assertEqual(MONITOR_CONTROL_MIN_VERSION_G68, "2.4.0")
        self.assertEqual(FILTERABLE_CLIP_FLAGS, ("OK", "NG", "KEEP"))
        self.assertEqual(ALLOWED_ANAMORPHIC_DESQUEEZE_RATIOS, (1.0, 1.3, 1.5, 1.6, 2.0))
        self.assertEqual(HDMI_RAW_UNSCALED_WIDTH, 4264)
        self.assertEqual(HDMI_RAW_UNSCALED_HEIGHT, 2408)
        self.assertEqual(CXD90057_SOC_NAME, "CXD90057")
        self.assertEqual(USBLAN_MIN_NPFZ100_PCT, 51)
        self.assertEqual(USBLAN_DC_C1_MIN_WATTS, 65.0)
        self.assertEqual(USBLAN_DC_C1_MIN_CABLE_AMPS, 5.0)
        self.assertEqual(USBLAN_MAX_AUTORECONNECT_LATENCY_MS, 5000.0)

    # --- 2. Strictly O_RDONLY Donor Audit & Clean-Room Dual Mode ---

    def test_03_donor_audit_matches_environment_mode_and_has_no_missing_markers(self) -> None:
        res = audit_phase196_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.network_contracts_verified)
        self.assertEqual(res.missing_markers, ())

    def test_04_donor_audit_clean_room_forced_skips_file_reads(self) -> None:
        res = audit_phase196_donor_contracts(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(len(res.checked_markers), 3)

    def test_05_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase196_donor_contracts(
                work_root=Path(tmp) / "nonexistent",
                force_clean_room=False,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)

    def test_06_donor_audit_synthetic_tree_detects_corrupted_sha_and_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _create_synthetic_donor_tree(Path(tmp), corrupt_net=True)
            res = audit_phase196_donor_contracts(
                work_root=work,
                force_clean_room=False,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE196_DONOR_INTEGRITY)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.files_inspected, 3)
            self.assertFalse(res.network_contracts_verified)

    def test_07_donor_audit_passes_with_patched_sha_matching_synthetic_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _create_synthetic_donor_tree(Path(tmp), corrupt_net=False)
            patched = {}
            for key, (body, rel_path, exp_size, _sha, markers, lbl) in PINNED_PHASE196_DONOR_SPECS.items():
                real_sha = hashlib.sha256((work / rel_path).read_bytes()).hexdigest()
                patched[key] = (body, rel_path, exp_size, real_sha, markers, lbl)
            with patch.dict(
                "fx3_safety.realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard.PINNED_PHASE196_DONOR_SPECS",
                patched,
                clear=True,
            ):
                res = audit_phase196_donor_contracts(work_root=work, force_clean_room=False)
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.files_inspected, 3)

    # --- 3. Gate G67: Power-On USB-LAN Auto-Connect & Network Streaming (RTMP/RTMPS/SRT) ---

    def test_08_g67_defaults_and_allowed_usblan_chipsets_protocols_pass(self) -> None:
        for proto, chipset, pwr in (
            ("CDC-NCM", "RTL8153", "NP-FZ100"),
            ("CDC-NCM", "ASIX", "DC-C1"),
            ("CDC-NCM", "AX88179", "NP-FZ100"),
            ("RNDIS", "RNDIS", "DC-C1_COUPLER"),
            ("CDC_NCM", "CDC_NCM", "USB_PD_BODY"),
        ):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(
                usblan_protocol=proto,
                adapter_chipset=chipset,
                power_mode=pwr,
            )
            self.assertTrue(res.valid, f"failed for {(proto, chipset, pwr)}: {res.errors}")
            self.assertEqual(res.status, STATUS_VERIFIED_G67)
            self.assertTrue(res.usblan_autoconnect_valid)
            self.assertTrue(res.stock_setting_protected)
            self.assertTrue(res.streaming_cap_valid)
            self.assertTrue(res.tls_erofs_valid)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.persistent_write_release)

    def test_09_g67_accepts_v700_and_v702_but_rejects_v600_for_autoconnect(self) -> None:
        for fw in ("7.00", "7.02"):
            ok, code, errs = validate_usblan_poweron_autoconnect(firmware_version=fw)
            self.assertTrue(ok, errs)
            self.assertEqual(code, "")

        res_old = verify_usblan_autoconnect_and_rtmp_srt_guard(firmware_version="6.00")
        self.assertFalse(res_old.valid)
        self.assertEqual(res_old.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

    def test_10_g67_rejects_disabled_autoconnect_wrong_port_and_unsupported_chipsets(self) -> None:
        for kwargs in (
            {"usblan_autoconnect_enabled": False},
            {"usb_port": "MULTI_PORT_MICRO_USB"},
            {"usblan_protocol": "CDC-ECM"},
            {"adapter_chipset": "AX88179A"},
            {"adapter_chipset": "AX88179B"},
            {"adapter_chipset": "RTL8156"},
            {"adapter_chipset": "AQUANTIA_10G"},
            {"auto_reconnect_latency_ms": 6500.0},
        ):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(**kwargs)
            self.assertFalse(res.valid, f"expected fail for {kwargs}")
            self.assertEqual(res.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

    def test_11_g67_power_supply_npfz100_and_dcc1_interlocks(self) -> None:
        r_no_batt = verify_usblan_autoconnect_and_rtmp_srt_guard(
            power_mode="NP-FZ100",
            np_fz100_present=False,
        )
        self.assertFalse(r_no_batt.valid)
        self.assertEqual(r_no_batt.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

        r_low_batt = verify_usblan_autoconnect_and_rtmp_srt_guard(
            power_mode="NP-FZ100",
            np_fz100_present=True,
            battery_pct=45,
        )
        self.assertFalse(r_low_batt.valid)
        self.assertEqual(r_low_batt.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

        r_dcc1_low_w = verify_usblan_autoconnect_and_rtmp_srt_guard(
            power_mode="DC-C1",
            dc_c1_pd_watts=45.0,
            emarked_5a_cable=True,
        )
        self.assertFalse(r_dcc1_low_w.valid)
        self.assertEqual(r_dcc1_low_w.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

        r_dcc1_3a = verify_usblan_autoconnect_and_rtmp_srt_guard(
            power_mode="DC-C1",
            dc_c1_pd_watts=65.0,
            emarked_5a_cable=False,
        )
        self.assertFalse(r_dcc1_3a.valid)
        self.assertEqual(r_dcc1_3a.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

    def test_12_g67_blocks_stageb_stock_setting_network_profile_overwrite(self) -> None:
        for bad_kwargs in (
            {"stageb_setting_network_overwrite_attempted": True},
            {"setting_network_writes": 1},
            {"setting_mount_ro_protected": False},
            {"target_profile_path": "/setting/network/usblan.cfg"},
            {"target_profile_path": "p2:/setting/net.bin"},
            {"target_profile_path": "/dev/nflasha2"},
            {"target_profile_path": "/dev/cnflasha2"},
        ):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(**bad_kwargs)
            self.assertFalse(res.valid, f"expected /setting block for {bad_kwargs}")
            self.assertEqual(res.status, STATUS_BLOCKED_G67_STAGEB_SETTING_PROFILE_OVERWRITE)
            self.assertFalse(res.stock_setting_protected)

    def test_13_g67_rtmp_rtmps_srt_streaming_caps_and_codecs(self) -> None:
        for proto, codec, mbps, fps in (
            ("RTMP", "H.264/AVC", 38.0, 59.94),
            ("RTMPS", "H.265/HEVC", 38.0, 59.94),
            ("SRT", "HEVC", 25.0, 50.0),
            ("NONE", "HEVC", 0.0, 59.94),
        ):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(
                streaming_protocol=proto,
                streaming_codec=codec,
                streaming_bitrate_mbps=mbps,
                stream_fps=fps,
            )
            self.assertTrue(res.valid, f"failed for {(proto, codec, mbps, fps)}: {res.errors}")

        for bad_kwargs in (
            {"streaming_protocol": "WEBRTC_RAW"},
            {"streaming_protocol": "RTMPS", "streaming_bitrate_mbps": 38.1},
            {"streaming_protocol": "SRT", "streaming_bitrate_mbps": 0.0},
            {"streaming_protocol": "RTMP", "streaming_codec": "PRORES_RAW"},
            {"streaming_protocol": "RTMPS", "stream_width": 4096},
            {"streaming_protocol": "RTMPS", "stream_height": 2408},
            {"streaming_protocol": "SRT", "stream_fps": 119.88},
        ):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(**bad_kwargs)
            self.assertFalse(res.valid, f"expected cap block for {bad_kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION
            )

    def test_14_g67_enforces_rtmps_tls_cert_erofs_readonly(self) -> None:
        for bad_tls in (
            {"streaming_protocol": "RTMPS", "tls_cert_verified": False},
            {"streaming_protocol": "RTMPS", "tls_cert_mount_ro": False},
            {"streaming_protocol": "RTMPS", "tls_cert_write_errno": "EACCES"},
            {"streaming_protocol": "RTMPS", "tls_cert_mutation_bytes": 16},
            {"streaming_protocol": "RTMPS", "tls_cert_write_attempted": True},
        ):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(**bad_tls)
            self.assertFalse(res.valid, f"expected TLS EROFS fail for {bad_tls}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED
            )
            self.assertFalse(res.tls_erofs_valid)

    def test_15_g67_rejects_malformed_telemetry_and_wrong_body_model(self) -> None:
        res_bad_id = verify_usblan_autoconnect_and_rtmp_srt_guard(
            body_model_name="ILME-FX3",
            body_model_id=0x91030084,
        )
        self.assertFalse(res_bad_id.valid)
        self.assertEqual(res_bad_id.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

        for bad_tel in (
            {"battery_pct": 105},
            {"streaming_bitrate_mbps": -2.0},
            {"usblan_autoconnect_enabled": "yes"},
            {"body_model_name": ""},
        ):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(**bad_tel)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G67_TELEMETRY_INVALID)

    def test_16_evaluate_g67_blocks_persistent_emmc_write_request(self) -> None:
        verdict, res = evaluate_g67_usblan_rtmp_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    # --- 4. Gate G68: Creators' Cloud Clip-Flag, Anamorphic & Bright-Monitoring Magnifier ---

    def test_17_g68_defaults_and_clip_flag_sidecar_hygiene_pass(self) -> None:
        for flag in ("OK", "NG", "KEEP", "NONE"):
            for fmt in ALLOWED_CLIP_FLAG_SIDECAR_FORMATS:
                res = verify_clipflag_anamorphic_and_bright_magnifier_guard(
                    clip_flag=flag,
                    sidecar_format=fmt,
                )
                self.assertTrue(res.valid, f"failed for {(flag, fmt)}: {res.errors}")
                self.assertEqual(res.status, STATUS_VERIFIED_G68)
                self.assertTrue(res.clip_flag_hygiene_valid)
                self.assertTrue(res.anamorphic_hdmi_raw_valid)
                self.assertTrue(res.bright_magnifier_valid)
                self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_18_g68_enforces_creators_app_and_mc_version_floors(self) -> None:
        for bad_ver in (
            {"creators_app_version": "3.0.9"},
            {"creators_app_version": "2.9.0"},
            {"monitor_control_version": "2.3.5"},
            {"monitor_control_version": "2.1.0"},
        ):
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(**bad_ver)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR
            )

        res_ok = verify_clipflag_anamorphic_and_bright_magnifier_guard(
            creators_app_version="3.2.0",
            monitor_control_version="2.5.1",
        )
        self.assertTrue(res_ok.valid, res_ok.errors)

    def test_19_g68_blocks_video_essence_mutation_and_invalid_clip_flags(self) -> None:
        for bad_clip in (
            {"clip_flag": "DELETE_PERMANENT"},
            {"filter_flags": ("OK", "INVALID_FLAG")},
            {"sidecar_format": "IN_PLACE_MP4_REWRITE"},
            {"sidecar_metadata_only": False},
            {"video_essence_modified": True},
            {"video_essence_mutation_bytes": 64},
            {"mxf_mp4_essence_sha256_after": "b" * 64},
            {"stage_b_persistent_clip_rewrite": True},
        ):
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(**bad_clip)  # type: ignore[arg-type]
            self.assertFalse(res.valid, f"expected fail for {bad_clip}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR
            )

    def test_20_g68_anamorphic_desqueeze_ratios_and_hdmi_raw_auto_disable(self) -> None:
        for ratio in ALLOWED_ANAMORPHIC_DESQUEEZE_RATIOS:
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(
                anamorphic_desqueeze_ratio=ratio,
                hdmi_raw_output_active=False,
            )
            self.assertTrue(res.valid, f"failed for ratio={ratio}: {res.errors}")

        # During HDMI RAW (4264x2408), 1.5x/1.6x desqueeze auto-disables so linear RAW stays unscaled
        res_raw_safe = verify_clipflag_anamorphic_and_bright_magnifier_guard(
            anamorphic_desqueeze_ratio=1.6,
            hdmi_raw_output_active=True,
            anamorphic_desqueeze_active_on_hdmi_raw=False,
            anamorphic_auto_disabled_for_hdmi_raw=True,
            hdmi_raw_width=4264,
            hdmi_raw_height=2408,
            hdmi_raw_linear_unscaled=True,
        )
        self.assertTrue(res_raw_safe.valid, res_raw_safe.errors)
        self.assertTrue(any("4264x2408" in w for w in res_raw_safe.warnings))

        for bad_ana in (
            {"anamorphic_desqueeze_ratio": 1.8},
            {"desqueeze_monitoring_only": False},
            {"recorded_essence_anamorphic_baked": True},
            {"hdmi_raw_output_active": True, "anamorphic_desqueeze_active_on_hdmi_raw": True},
            {"hdmi_raw_output_active": True, "anamorphic_auto_disabled_for_hdmi_raw": False},
            {"hdmi_raw_output_active": True, "hdmi_raw_width": 3840},
            {"hdmi_raw_output_active": True, "hdmi_raw_height": 2160},
            {"hdmi_raw_output_active": True, "hdmi_raw_linear_unscaled": False},
        ):
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(**bad_ana)
            self.assertFalse(res.valid, f"expected fail for {bad_ana}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G68_ANAMORPHIC_DESQUEEZE_OR_HDMI_RAW_SCALE
            )

    def test_21_g68_bright_monitoring_and_focus_magnifier_cxd90057_coexistence(self) -> None:
        for factor in ALLOWED_FOCUS_MAGNIFIER_FACTORS:
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(
                soc_name="CXD90057",
                bright_monitoring_active=True,
                focus_magnifier_active=True,
                focus_magnifier_factor=factor,
            )
            self.assertTrue(res.valid, f"failed for magnifier={factor}: {res.errors}")

        for bad_bright in (
            {"soc_name": "CXD90058"},
            {"focus_magnifier_factor": 16.0},
            {"coexistence_supported": False},
            {"magnifier_overlay_non_destructive": False},
            {"recorded_essence_bright_or_zoom_baked": True},
            {"exposure_metering_corrupted": True},
            {"cxd90057_isp_pipeline_fault": True},
        ):
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(**bad_bright)
            self.assertFalse(res.valid, f"expected fail for {bad_bright}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G68_BRIGHT_MONITORING_MAGNIFIER_FAULT
            )

    def test_22_g68_rejects_malformed_telemetry_and_persistent_writes(self) -> None:
        for bad_tel in (
            {"anamorphic_desqueeze_ratio": -1.5},
            {"focus_magnifier_factor": 0.0},
            {"video_essence_mutation_bytes": -1},
            {"filter_flags": "OK"},
            {"bright_monitoring_active": 1},
        ):
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(**bad_tel)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G68_TELEMETRY_INVALID)

        verdict, r_pw = evaluate_g68_clipflag_anamorphic_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(r_pw.valid)
        self.assertEqual(r_pw.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 5. Pure Validator Unit Checks ---

    def test_23_pure_validators_direct_invocations(self) -> None:
        ok1, code1, _ = validate_usblan_poweron_autoconnect(
            power_mode="DC-C1",
            dc_c1_pd_watts=65.0,
            emarked_5a_cable=True,
        )
        self.assertTrue(ok1)
        self.assertEqual(code1, "")

        ok2, code2, _ = validate_network_streaming_rtmp_srt_and_tls(
            streaming_protocol="SRT",
            streaming_codec="H.265/HEVC",
            streaming_bitrate_mbps=38.0,
        )
        self.assertTrue(ok2)
        self.assertEqual(code2, "")

        ok3, code3, _ = validate_creators_cloud_clip_flag_hygiene(
            clip_flag="OK",
            sidecar_format="XML_SIDECAR",
        )
        self.assertTrue(ok3)
        self.assertEqual(code3, "")

        ok4, code4, _ = validate_anamorphic_desqueeze_and_hdmi_raw_lock(
            anamorphic_desqueeze_ratio=1.3,
            hdmi_raw_output_active=False,
        )
        self.assertTrue(ok4)
        self.assertEqual(code4, "")

        ok5, code5, _ = validate_bright_monitoring_and_focus_magnifier_cxd90057(
            focus_magnifier_factor=8.0,
        )
        self.assertTrue(ok5)
        self.assertEqual(code5, "")

    def test_24_g67_and_g68_evaluators_propagate_corrupted_donor_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _create_synthetic_donor_tree(Path(tmp), corrupt_net=True)
            v67, r67 = evaluate_g67_usblan_rtmp_guard(
                work_root=work,
                force_clean_room=False,
            )
            self.assertFalse(v67.passed)
            self.assertFalse(r67.valid)
            self.assertIn(STATUS_BLOCKED_PHASE196_DONOR_INTEGRITY, r67.violation_codes)

            v68, r68 = evaluate_g68_clipflag_anamorphic_guard(
                work_root=work,
                force_clean_room=False,
            )
            self.assertFalse(v68.passed)
            self.assertFalse(r68.valid)
            self.assertIn(STATUS_BLOCKED_PHASE196_DONOR_INTEGRITY, r68.violation_codes)

    # --- 6. Unified 68-Gate Master Safety Preflight (`evaluate_68gate_preflight`) ---

    def test_25_preflight_default_offline_verifies_65_of_68_and_hard_locks_redlines(self) -> None:
        report = evaluate_68gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(report.schema, REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_SCHEMA)
        self.assertEqual(report.version, REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_VERSION)
        self.assertEqual(len(report.gates), 68)
        self.assertTrue(report.offline_65_gates_verified, report.errors)
        self.assertFalse(report.all_68_gates_verified)
        self.assertTrue(report.g13_to_g68_all_passed)
        self.assertTrue(report.g67_to_g68_all_passed)
        self.assertEqual(report.summary["verified_gates"], 65)
        self.assertEqual(report.summary["technical_gates_passed"], 65)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(report.summary["g67_to_g68_verified"], 2)
        self.assertEqual(report.status, "VERIFIED_65_OF_68_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.human_hardware_attach_token)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertFalse(report.physical_flash_auto_exec_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)

    def test_26_preflight_dry_run_simulated_verifies_68_of_68_still_locks_attach(self) -> None:
        report = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        self.assertEqual(len(report.gates), 68)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertTrue(report.all_68_gates_verified)
        self.assertEqual(report.summary["verified_gates"], 68)
        self.assertEqual(report.summary["technical_gates_passed"], 68)
        self.assertEqual(report.status, "VERIFIED_ALL_68_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.human_hardware_attach_token)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertFalse(report.physical_flash_auto_exec_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)

    def test_27_preflight_clean_room_mode_verifies_65_offline_and_68_dry_run(self) -> None:
        r_off = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertEqual(r_off.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r_off.offline_65_gates_verified)
        self.assertEqual(r_off.summary["verified_gates"], 65)

        r_dry = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(r_dry.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r_dry.all_68_gates_verified)
        self.assertEqual(r_dry.summary["verified_gates"], 68)

    def test_28_preflight_gate_order_places_g67_and_g68_at_indices_66_and_67(self) -> None:
        report = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(report.gates[66]["gate_id"], G67_GATE_ID)
        self.assertEqual(report.gates[66]["gate_code"], G67_GATE_CODE)
        self.assertEqual(report.gates[67]["gate_id"], G68_GATE_ID)
        self.assertEqual(report.gates[67]["gate_code"], G68_GATE_CODE)

    def test_29_preflight_propagates_g67_usblan_setting_and_rtmp_tls_faults(self) -> None:
        r_chip = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            usblan_rtmp_kwargs={"adapter_chipset": "AX88179A"},
        )
        self.assertFalse(r_chip.all_68_gates_verified)
        self.assertFalse(r_chip.g67_to_g68_all_passed)
        self.assertEqual(r_chip.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)
        self.assertEqual(r_chip.summary["verified_gates"], 67)

        r_set = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            usblan_rtmp_kwargs={"stageb_setting_network_overwrite_attempted": True},
        )
        self.assertFalse(r_set.all_68_gates_verified)
        self.assertEqual(r_set.status, STATUS_BLOCKED_G67_STAGEB_SETTING_PROFILE_OVERWRITE)

        r_bw = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            usblan_rtmp_kwargs={"streaming_bitrate_mbps": 45.0},
        )
        self.assertFalse(r_bw.all_68_gates_verified)
        self.assertEqual(r_bw.status, STATUS_BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION)

        r_tls = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            usblan_rtmp_kwargs={"tls_cert_mount_ro": False},
        )
        self.assertFalse(r_tls.all_68_gates_verified)
        self.assertEqual(r_tls.status, STATUS_BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED)

    def test_30_preflight_propagates_g68_clipflag_anamorphic_and_bright_faults(self) -> None:
        r_clip = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            clipflag_anamorphic_kwargs={"video_essence_modified": True},
        )
        self.assertFalse(r_clip.all_68_gates_verified)
        self.assertFalse(r_clip.g67_to_g68_all_passed)
        self.assertEqual(
            r_clip.status, STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR
        )
        self.assertEqual(r_clip.summary["verified_gates"], 67)

        r_ana = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            clipflag_anamorphic_kwargs={
                "hdmi_raw_output_active": True,
                "anamorphic_desqueeze_active_on_hdmi_raw": True,
            },
        )
        self.assertFalse(r_ana.all_68_gates_verified)
        self.assertEqual(
            r_ana.status, STATUS_BLOCKED_G68_ANAMORPHIC_DESQUEEZE_OR_HDMI_RAW_SCALE
        )

        r_bright = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            clipflag_anamorphic_kwargs={"cxd90057_isp_pipeline_fault": True},
        )
        self.assertFalse(r_bright.all_68_gates_verified)
        self.assertEqual(
            r_bright.status, STATUS_BLOCKED_G68_BRIGHT_MONITORING_MAGNIFIER_FAULT
        )

    def test_31_preflight_propagates_g58_to_g66_faults_and_persistent_write_block(self) -> None:
        for kwargs, expected_status in (
            (
                {"bench_interlock_kwargs": {"auto_flash_requested": True}},
                STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION,
            ),
            (
                {"ssboot_wbi2_kwargs": {"blkroset_nflasha5": 0}},
                STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
            ),
            (
                {"slot1_ufu_c2pa_kwargs": {"body_firmware_version": "2.02"}},
                STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR,
            ),
            (
                {"emount_breathing_kwargs": {"lens_id": 0x0001}},
                STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED,
            ),
            (
                {"hdmi_raw_kwargs": {"sdi_mmio_probes_emitted": 1}},
                STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED,
            ),
            (
                {"fx3a_firewall_kwargs": {"body_model_name": FX3A_MODEL_NAME}},
                STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE,
            ),
            (
                {"xlrh1_mishoe_kwargs": {"body_35mm_mic_plugged": True}},
                STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE,
            ),
            (
                {"nouvc_dcc1_pd_kwargs": {"uvc_uac_gadget_requested": True}},
                STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN,
            ),
            (
                {
                    "lut_path_cineei_bt_kwargs": {
                        "media_type": "CFEXPRESS_TYPE_A",
                        "lut_directory": "/Private/Sony/PRO/LUT/",
                    }
                },
                STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE,
            ),
        ):
            r = evaluate_68gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated=True,
                **kwargs,
            )
            self.assertFalse(r.all_68_gates_verified)
            self.assertEqual(r.status, expected_status)

        r_pw = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r_pw.all_68_gates_verified)
        self.assertEqual(r_pw.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_32_dry_run_simulated_backup_alias_flag_works(self) -> None:
        report = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertTrue(report.all_68_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(report.summary["verified_gates"], 68)

    # --- 7. Backward Compatibility: 58/60/62/64/66-Gate Preflights & CLIs Intact ---

    def test_33_backward_compatibility_58_60_62_64_66_preflights_intact(self) -> None:
        r58 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(r58.summary["verified_gates"], 58)
        self.assertTrue(r58.all_58_gates_verified)

        r60 = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r60.summary["verified_gates"], 60)
        self.assertTrue(r60.all_60_gates_verified)

        r62 = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r62.summary["verified_gates"], 62)
        self.assertTrue(r62.all_62_gates_verified)

        r64 = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r64.summary["verified_gates"], 64)
        self.assertTrue(r64.all_64_gates_verified)

        r66 = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r66.summary["verified_gates"], 66)
        self.assertTrue(r66.all_66_gates_verified)

        for cmd, expected in (
            (["verify-58-gates", "--clean-room", "--dry-run-simulated-backup", "--json"], 58),
            (["verify-60-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 60),
            (["verify-62-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 62),
            (["verify-64-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 64),
            (["verify-66-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 66),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(cmd)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["summary"]["verified_gates"], expected)

    # --- 8. Edge-Case Coverage Matrix for G67 & G68 ---

    def test_34_g67_port_and_power_mode_normalization_aliases(self) -> None:
        for port in ("USB_TYPE_C", "TYPE_C", "USBC", "USB-C"):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(usb_port=port)
            self.assertTrue(res.valid, f"failed for port={port}: {res.errors}")

        for pwr, extra in (
            ("NP-FZ100", {"np_fz100_present": True, "battery_pct": 51}),
            ("USB_PD_BODY", {"np_fz100_present": True, "battery_pct": 75}),
            ("DC-C1", {"dc_c1_pd_watts": 65.0, "emarked_5a_cable": True}),
            ("DC_C1_COUPLER", {"dc_c1_pd_watts": 100.0, "emarked_5a_cable": True}),
        ):
            res = verify_usblan_autoconnect_and_rtmp_srt_guard(power_mode=pwr, **extra)
            self.assertTrue(res.valid, f"failed for power_mode={pwr}: {res.errors}")

    def test_35_g67_body_model_id_hex_string_and_fx3a_supported(self) -> None:
        r_fx3 = verify_usblan_autoconnect_and_rtmp_srt_guard(
            body_model_name=FX3_MODEL_NAME,
            body_model_id="0x91030080",
        )
        self.assertTrue(r_fx3.valid, r_fx3.errors)
        self.assertEqual(r_fx3.body_model_id, FX3_MODEL_ID)
        self.assertEqual(r_fx3.body_model_id_hex, "0x91030080")

        r_fx3a = verify_usblan_autoconnect_and_rtmp_srt_guard(
            body_model_name=FX3A_MODEL_NAME,
            body_model_id=FX3_MODEL_ID,
        )
        self.assertTrue(r_fx3a.valid, r_fx3a.errors)

    def test_36_g67_boundary_latency_5000ms_and_38mbps_cap(self) -> None:
        r_edge = verify_usblan_autoconnect_and_rtmp_srt_guard(
            auto_reconnect_latency_ms=5000.0,
            streaming_protocol="RTMP",
            streaming_codec="H.264/AVC",
            streaming_bitrate_mbps=38.0,
            stream_width=3840,
            stream_height=2160,
            stream_fps=60.0,
        )
        self.assertTrue(r_edge.valid, r_edge.errors)

        r_over_lat = verify_usblan_autoconnect_and_rtmp_srt_guard(
            auto_reconnect_latency_ms=5000.1,
        )
        self.assertFalse(r_over_lat.valid)
        self.assertEqual(r_over_lat.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

    def test_37_g67_non_rtmps_still_enforces_tls_cert_ro_erofs_store(self) -> None:
        r_rtmp_rw = verify_usblan_autoconnect_and_rtmp_srt_guard(
            streaming_protocol="RTMP",
            tls_cert_mount_ro=False,
        )
        self.assertFalse(r_rtmp_rw.valid)
        self.assertEqual(
            r_rtmp_rw.status, STATUS_BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED
        )

    def test_38_g67_blocks_unknown_power_mode_and_empty_tls_path_for_rtmps(self) -> None:
        r_pwr = verify_usblan_autoconnect_and_rtmp_srt_guard(power_mode="MICRO_USB_5V")
        self.assertFalse(r_pwr.valid)
        self.assertEqual(r_pwr.status, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE)

        r_cert = verify_usblan_autoconnect_and_rtmp_srt_guard(
            streaming_protocol="RTMPS",
            tls_cert_path="",
        )
        self.assertFalse(r_cert.valid)
        self.assertEqual(r_cert.status, STATUS_BLOCKED_G67_TELEMETRY_INVALID)

    def test_39_g68_supports_single_and_multi_clip_flag_filters(self) -> None:
        for subset in (("OK",), ("NG",), ("KEEP",), ("OK", "KEEP"), ("OK", "NG", "KEEP")):
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(
                filter_flags=subset,
            )
            self.assertTrue(res.valid, f"failed for subset={subset}: {res.errors}")

        res_empty = verify_clipflag_anamorphic_and_bright_magnifier_guard(filter_flags=())
        self.assertFalse(res_empty.valid)
        self.assertEqual(
            res_empty.status, STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR
        )

    def test_40_g68_blocks_blank_or_mismatched_essence_sha256(self) -> None:
        r_blank = verify_clipflag_anamorphic_and_bright_magnifier_guard(
            mxf_mp4_essence_sha256_before="",
        )
        self.assertFalse(r_blank.valid)
        self.assertEqual(r_blank.status, STATUS_BLOCKED_G68_TELEMETRY_INVALID)

        r_diff = verify_clipflag_anamorphic_and_bright_magnifier_guard(
            mxf_mp4_essence_sha256_before="a" * 64,
            mxf_mp4_essence_sha256_after="c" * 64,
        )
        self.assertFalse(r_diff.valid)
        self.assertEqual(
            r_diff.status, STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR
        )

    def test_41_g68_hdmi_raw_1_0x_produces_no_warning_and_rejects_bad_desqueeze_when_inactive(
        self,
    ) -> None:
        r_1x = verify_clipflag_anamorphic_and_bright_magnifier_guard(
            anamorphic_desqueeze_ratio=1.0,
            hdmi_raw_output_active=True,
        )
        self.assertTrue(r_1x.valid, r_1x.errors)
        self.assertEqual(r_1x.warnings, ())

        r_bad_flag = verify_clipflag_anamorphic_and_bright_magnifier_guard(
            hdmi_raw_output_active=False,
            anamorphic_desqueeze_active_on_hdmi_raw=True,
        )
        self.assertFalse(r_bad_flag.valid)
        self.assertEqual(
            r_bad_flag.status, STATUS_BLOCKED_G68_ANAMORPHIC_DESQUEEZE_OR_HDMI_RAW_SCALE
        )

    def test_42_g68_bright_monitoring_off_with_magnifier_on_or_off_still_valid(self) -> None:
        for bm, fm in ((False, True), (True, False), (False, False)):
            res = verify_clipflag_anamorphic_and_bright_magnifier_guard(
                bright_monitoring_active=bm,
                focus_magnifier_active=fm,
                focus_magnifier_factor=1.0 if not fm else 2.0,
            )
            self.assertTrue(res.valid, f"failed for bm={bm}, fm={fm}: {res.errors}")

    def test_43_g68_version_parser_handles_v_prefix_and_4part_versions(self) -> None:
        r_ok = verify_clipflag_anamorphic_and_bright_magnifier_guard(
            creators_app_version="v3.1.0.1",
            monitor_control_version="Ver. 2.4.0",
        )
        self.assertTrue(r_ok.valid, r_ok.errors)

        r_bad = verify_clipflag_anamorphic_and_bright_magnifier_guard(
            creators_app_version="bad_version",
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(
            r_bad.status, STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR
        )

    # --- 9. CLI Subcommands, Zero Raw Firmware Leakage & Runtime Budget ---

    def test_44_cli_verify_g67_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g67-usblan-rtmp", "--force-clean-room", "--json"],
            ["verify-g67-usblan-rtmp", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G67)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertTrue(data["usblan_rtmp_guard"]["usblan_autoconnect_valid"])
                self.assertTrue(data["usblan_rtmp_guard"]["stock_setting_protected"])
                self.assertTrue(data["usblan_rtmp_guard"]["tls_erofs_valid"])
            else:
                self.assertIn(f"gate={G67_GATE_ID}", buf.getvalue())

    def test_45_cli_verify_g68_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g68-clipflag-anamorphic", "--force-clean-room", "--json"],
            ["verify-g68-clipflag-anamorphic", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G68)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertTrue(data["clipflag_anamorphic_guard"]["clip_flag_hygiene_valid"])
                self.assertTrue(data["clipflag_anamorphic_guard"]["anamorphic_hdmi_raw_valid"])
                self.assertTrue(data["clipflag_anamorphic_guard"]["bright_magnifier_valid"])
            else:
                self.assertIn(f"gate={G68_GATE_ID}", buf.getvalue())

    def test_46_cli_verify_68_gates_offline_and_dry_run_modes(self) -> None:
        for subcmd, expected_count in (
            (["verify-68-gates", "--force-clean-room", "--json"], 65),
            (["verify-68-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 68),
            (["verify-68-gates", "--force-clean-room"], None),
            (["verify-68-gates", "--force-clean-room", "--dry-run-simulated"], None),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, f"CLI failed for {subcmd}: {buf.getvalue()}")
            if expected_count is not None:
                payload = json.loads(buf.getvalue())
                self.assertEqual(payload["summary"]["verified_gates"], expected_count)
                self.assertFalse(payload["overall_ready_for_hardware_attach"])

    def test_47_cli_supports_clean_room_and_dry_run_simulated_backup_aliases(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(
                ["verify-68-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(payload["all_68_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 68)

    def test_48_module_cli_and_zero_raw_firmware_leakage_in_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated", "--json"])
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertNotIn("b'\\x7fELF", text)
        self.assertNotIn('b"\\x7fELF', text)
        payload = json.loads(text)
        self.assertEqual(payload["summary"]["verified_gates"], 68)
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["human_hardware_attach_token"])
        self.assertFalse(payload["el3_payload_transmit_authorized"])
        self.assertFalse(payload["spi_nor_write_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_49_module_cli_text_output_smoke(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=68/68", out)
        self.assertIn("g67_to_g68_all_passed=True", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    def test_50_verify_68_gates_fast_runtime_under_6s(self) -> None:
        t0 = time.monotonic()
        report = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        elapsed = time.monotonic() - t0
        self.assertTrue(report.all_68_gates_verified)
        self.assertLess(elapsed, 6.0)

    def test_51_status_constants_and_allowed_collections_consistency(self) -> None:
        self.assertEqual(STATUS_SAFE, "SAFE")
        self.assertEqual(STATUS_VERIFIED_SAFE, "VERIFIED_SAFE")
        self.assertIn("ILME-FX3", ALLOWED_G67_BODY_MODELS)
        self.assertIn("ILME-FX3A", ALLOWED_G67_BODY_MODELS)
        self.assertEqual(ALLOWED_USBLAN_PROTOCOLS, ("CDC_NCM", "RNDIS"))
        self.assertIn("RTL8153", ALLOWED_USBLAN_ADAPTER_CHIPSETS)
        self.assertIn("AX88179", ALLOWED_USBLAN_ADAPTER_CHIPSETS)
        self.assertIn("AX88179A", REJECTED_USBLAN_ADAPTER_CHIPSETS)
        self.assertIn("USB_TYPE_C", ALLOWED_USBLAN_PORTS)
        self.assertIn("NP_FZ100", ALLOWED_USBLAN_POWER_MODES)
        self.assertIn("DC_C1", ALLOWED_USBLAN_POWER_MODES)
        self.assertIn("/setting", FORBIDDEN_STOCK_SETTING_PREFIXES)
        self.assertEqual(ALLOWED_STREAMING_PROTOCOLS, ("RTMP", "RTMPS", "SRT", "NONE"))
        self.assertEqual(ACTIVE_STREAMING_PROTOCOLS, ("RTMP", "RTMPS", "SRT"))
        self.assertIn("HEVC", ALLOWED_STREAMING_CODECS)
        self.assertIn("AVC", ALLOWED_STREAMING_CODECS)
        self.assertEqual(TLS_CERT_DEFAULT_PATH, "/cert/rtmps_ca_bundle.pem")
        self.assertEqual(VALID_CLIP_FLAGS, ("OK", "NG", "KEEP", "NONE"))
        self.assertEqual(len(DEFAULT_SYNTHETIC_ESSENCE_SHA256), 64)

    def test_52_report_serialization_roundtrip_is_pure_json(self) -> None:
        report = run_68_gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        serialized = json.dumps(report.to_dict(), ensure_ascii=False)
        parsed = json.loads(serialized)
        self.assertEqual(
            parsed["schema"], REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_SCHEMA
        )
        self.assertEqual(len(parsed["gates"]), 68)
        self.assertEqual(parsed["summary"]["technical_gates_passed"], 68)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])
        self.assertFalse(parsed["spi_nor_write_authorized"])
        self.assertFalse(parsed["el3_payload_transmit_authorized"])
        self.assertEqual(parsed["physical_usb_packets_emitted"], 0)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)


if __name__ == "__main__":
    unittest.main()
