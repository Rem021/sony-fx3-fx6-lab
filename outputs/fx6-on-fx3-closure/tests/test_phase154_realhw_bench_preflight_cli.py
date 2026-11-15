"""Phase 154 tests: Host-Side Read-Only Physical Bench Preflight CLI, Passive USB Classifier, SD Staging Verifier & Dual-Copy FX3RCPT1 Receipt Engine."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx3-firmware-lab",
    "outputs/fx3-vm",
    "outputs/fx6-on-fx3-closure",
):
    _p = str(REPO_ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as cli_main  # noqa: E402
from fx6_closure.donor_paths import is_forced_clean_room  # noqa: E402
from fx6_closure.patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR  # noqa: E402
from fx6_closure.realhw_bench_preflight_and_usb_classifier import (  # noqa: E402
    ALERT_MULTIPLE_SONY_DEVICES_AMBIGUOUS,
    ALERT_SERVICE_MODE_STRANDED,
    ALERT_UNSUPPORTED_MODEL_PID,
    BENCH_USB_STATES,
    BLOCKED_FORBIDDEN_OTA_TRIGGER,
    ERR_CAMERA_CID_SHA256_MISMATCH,
    ERR_DUAL_COPY_CRC32_MISMATCH,
    ERR_DUAL_COPY_RECEIPT_INVALID,
    ERR_DUAL_COPY_RECEIPT_MISSING,
    ERR_DUAL_COPY_SHA256_MISMATCH,
    ERR_SD_ESCAPE_HATCH_LAUNCHER_HASH_MISMATCH,
    ERR_SD_FREE_SPACE_UNDER_2GIB,
    ERR_SD_STAGE_B_13_PARITY_FAILED,
    ERR_SD_SYMLINK_REJECTED,
    EXPECTED_ESCAPE_HATCH_LAUNCHER_SHA256,
    GIB_BYTES,
    IOKIT_HANDLES_OPENED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MIN_SD_FREE_SPACE_BYTES,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_154_SCHEMA,
    PHASE_154_VERSION,
    PHYSICAL_DEVICE_WRITES,
    RAW_FIRMWARE_SLICES_EMITTED,
    SD_MANIFEST_RELPATH,
    SD_PHYSICAL_MEDIA_WRITTEN,
    SPI_NOR_WRITE_AUTHORIZED,
    USB_PACKETS_EMITTED,
    USB_STATE_MULTIPLE_SONY_DEVICES_AMBIGUOUS,
    USB_STATE_NO_SONY_CAMERA_ATTACHED,
    USB_STATE_READY_MSC_054C_0DA1,
    USB_STATE_STRANDED_SERVICE_054C_0336,
    USB_STATE_UNSUPPORTED_MODEL_PID,
    USB_STATE_WRONG_USB_MODE_MTP_REMOTE_OR_UVC,
    VERDICT_GO_READONLY_PREFLIGHT,
    VERDICT_NO_GO,
    audit_sd_staging_directory,
    build_synthetic_ioreg_snapshot,
    capture_passive_ioreg_snapshot,
    classify_passive_usb_snapshot,
    inspect_bench_donor_readiness,
    parse_ioreg_usb_snapshot,
    populate_dual_copy_receipt_fixtures,
    populate_sd_staging_fixture,
    render_phase154_markdown,
    run_realhw_bench_preflight,
    verify_dual_copy_tier0_receipts,
    verify_phase154_report,
)


def _donors_available_for_local_test() -> bool:
    if is_forced_clean_room():
        return False
    return (DEFAULT_FX6_DONOR_LIB_DIR / "appFw.so").is_file() and (
        DEFAULT_FX3_MODULES_DIR / "upm.ko"
    ).is_file()


class TestPhase154ExportsAndSafetyLocks(unittest.TestCase):
    def test_01_public_exports_present_in_fx6_closure_init(self) -> None:
        for name in (
            "PHASE_154_SCHEMA",
            "PHASE_154_VERSION",
            "BENCH_USB_STATES",
            "inspect_bench_donor_readiness",
            "parse_ioreg_usb_snapshot",
            "classify_passive_usb_snapshot",
            "capture_passive_ioreg_snapshot",
            "build_synthetic_ioreg_snapshot",
            "audit_sd_staging_directory",
            "verify_dual_copy_tier0_receipts",
            "populate_sd_staging_fixture",
            "populate_dual_copy_receipt_fixtures",
            "run_realhw_bench_preflight",
            "verify_phase154_report",
            "render_phase154_markdown",
        ):
            self.assertTrue(hasattr(fx6_closure, name), f"Missing fx6_closure.{name}")

    def test_02_hard_locked_safety_constants_immutable(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(SD_PHYSICAL_MEDIA_WRITTEN)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertEqual(USB_PACKETS_EMITTED, 0)
        self.assertEqual(IOKIT_HANDLES_OPENED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_SLICES_EMITTED, 0)
        self.assertEqual(len(BENCH_USB_STATES), 6)

    def test_03_donor_readiness_clean_room_and_optional_local_donor(self) -> None:
        res_cr = inspect_bench_donor_readiness(synthetic_clean_room=True)
        self.assertTrue(res_cr.passed)
        self.assertEqual(res_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_cr.stage_b_13_lock_count, 13)
        self.assertEqual(res_cr.raw_firmware_slices_emitted, 0)
        self.assertTrue(res_cr.read_only_o_rdonly_enforced)

        if _donors_available_for_local_test():
            res_local = inspect_bench_donor_readiness(synthetic_clean_room=False)
            self.assertTrue(res_local.passed)
            self.assertEqual(res_local.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res_local.stage_b_13_lock_count, 13)
            self.assertEqual(res_local.raw_firmware_slices_emitted, 0)

    def test_04_donor_readiness_missing_dir_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "nonexistent_lib"
            res = inspect_bench_donor_readiness(
                fx6_lib_dir=missing,
                fx3_modules_dir=missing,
                synthetic_clean_room=False,
            )
            self.assertFalse(res.passed)
            self.assertGreater(len(res.errors), 0)


class TestPhase154PassiveUsbClassifier(unittest.TestCase):
    def _assert_zero_packet_invariants(self, res) -> None:
        self.assertEqual(res.usb_packets_emitted, 0)
        self.assertEqual(res.iokit_handles_opened, 0)
        self.assertFalse(res.live_usb_iokit_transmit_enabled)

    def test_05_state_no_sony_camera_attached_empty_and_non_sony(self) -> None:
        res_empty = classify_passive_usb_snapshot("")
        self.assertEqual(res_empty.usb_state, USB_STATE_NO_SONY_CAMERA_ATTACHED)
        self.assertFalse(res_empty.ready_for_msc_session)
        self.assertFalse(res_empty.hard_abort)
        self._assert_zero_packet_invariants(res_empty)
        joined = "\n".join(res_empty.remediation_steps)
        self.assertIn("NP-FZ100 battery charge >= 80%", joined)
        self.assertIn("VMC-BNCM1", joined)
        self.assertIn("Mass Storage", joined)

        for fmt in ("xml_plist", "ioreg_text"):
            snap = build_synthetic_ioreg_snapshot(
                scenario="NO_SONY_CAMERA_ATTACHED", snapshot_format=fmt
            )
            res = classify_passive_usb_snapshot(snap)
            self.assertEqual(res.usb_state, USB_STATE_NO_SONY_CAMERA_ATTACHED)
            self.assertEqual(res.sony_device_count, 0)
            self.assertEqual(res.total_usb_devices_seen, 1)
            self._assert_zero_packet_invariants(res)

    def test_06_state_ready_msc_054c_0da1_plist_and_text(self) -> None:
        for fmt in ("xml_plist", "ioreg_text"):
            snap = build_synthetic_ioreg_snapshot(
                scenario="READY_MSC_054C_0DA1", snapshot_format=fmt
            )
            res = classify_passive_usb_snapshot(snap)
            self.assertEqual(res.usb_state, USB_STATE_READY_MSC_054C_0DA1)
            self.assertTrue(res.ready_for_msc_session)
            self.assertFalse(res.hard_abort)
            self.assertEqual(res.sony_device_count, 1)
            self.assertEqual(res.sony_devices[0].vid_pid, "054C:0DA1")
            self.assertTrue(res.sony_devices[0].mass_storage_driver_attached)
            self._assert_zero_packet_invariants(res)

    def test_07_real_macos_ioreg_pipe_format_ready_msc(self) -> None:
        real_like_ioreg = """\
+-o Root  <class IORegistryEntry, id 0x100000100, retain 20>
  +-o AppleUSBHostController@01000000  <class AppleT8112USBXHCI, id 0x100000500>
    | {
    |   "IOPowerManagement" = {"CurrentPowerState"=2}
    | }
    +-o ILME-FX3@01100000  <class IOUSBHostDevice, id 0x100000900, registered, matched, active>
      | {
      |   "idVendor" = 1356
      |   "idProduct" = 3489
      |   "USB Product Name" = "ILME-FX3"
      |   "USB Vendor Name" = "Sony"
      |   "locationID" = 17825792
      | }
      +-o IOUSBHostInterface@0  <class IOUSBHostInterface, id 0x100000901>
        | {
        |   "bInterfaceClass" = 8
        | }
        +-o IOUSBMassStorageDriver  <class IOUSBMassStorageDriver, id 0x100000902>
"""
        res = classify_passive_usb_snapshot(real_like_ioreg)
        self.assertEqual(res.snapshot_format, "ioreg_text")
        self.assertEqual(res.usb_state, USB_STATE_READY_MSC_054C_0DA1)
        self.assertTrue(res.ready_for_msc_session)
        self.assertEqual(res.sony_devices[0].location_id_hex, "0x01100000")
        self._assert_zero_packet_invariants(res)

    def test_08_state_stranded_service_054c_0336_and_teardown_runbook(self) -> None:
        for fmt in ("xml_plist", "ioreg_text"):
            snap = build_synthetic_ioreg_snapshot(
                scenario="STRANDED_SERVICE_054C_0336", snapshot_format=fmt
            )
            res = classify_passive_usb_snapshot(snap)
            self.assertEqual(res.usb_state, USB_STATE_STRANDED_SERVICE_054C_0336)
            self.assertEqual(res.alert_code, ALERT_SERVICE_MODE_STRANDED)
            self.assertFalse(res.ready_for_msc_session)
            self.assertTrue(res.hard_abort)
            joined = "\n".join(res.remediation_steps)
            self.assertIn("STOP (0336:7)", joined)
            self.assertIn("0da1:9", joined)
            self._assert_zero_packet_invariants(res)

    def test_09_state_wrong_usb_mode_mtp_remote_and_uvc(self) -> None:
        for scenario in (
            "WRONG_USB_MODE_MTP",
            "WRONG_USB_MODE_REMOTE",
            "WRONG_USB_MODE_UVC",
        ):
            for fmt in ("xml_plist", "ioreg_text"):
                snap = build_synthetic_ioreg_snapshot(scenario=scenario, snapshot_format=fmt)
                res = classify_passive_usb_snapshot(snap)
                self.assertEqual(res.usb_state, USB_STATE_WRONG_USB_MODE_MTP_REMOTE_OR_UVC)
                self.assertFalse(res.ready_for_msc_session)
                self.assertFalse(res.hard_abort)
                self.assertIn("Mass Storage", "\n".join(res.remediation_steps))
                self._assert_zero_packet_invariants(res)

    def test_10_state_wrong_usb_mode_rndis_and_interface_class_fallback(self) -> None:
        rndis_ioreg = """\
+-o IOUSBHostDevice@01100000  <class IOUSBHostDevice, id 0x100000a00>
  {
    "idVendor" = 0x054c
    "idProduct" = 0x0999
    "USB Product Name" = "ILME-FX3 RNDIS"
  }
  +-o AppleUSBEthernetHost  <class AppleUSBEthernetHost, id 0x100000a01>
    {
      "bInterfaceClass" = 224
    }
"""
        res = classify_passive_usb_snapshot(rndis_ioreg)
        self.assertEqual(res.usb_state, USB_STATE_WRONG_USB_MODE_MTP_REMOTE_OR_UVC)
        self.assertFalse(res.ready_for_msc_session)
        self._assert_zero_packet_invariants(res)

    def test_11_state_multiple_sony_devices_ambiguous_hard_abort(self) -> None:
        for fmt in ("xml_plist", "ioreg_text"):
            snap = build_synthetic_ioreg_snapshot(
                scenario="MULTIPLE_SONY_DEVICES_AMBIGUOUS", snapshot_format=fmt
            )
            res = classify_passive_usb_snapshot(snap)
            self.assertEqual(res.usb_state, USB_STATE_MULTIPLE_SONY_DEVICES_AMBIGUOUS)
            self.assertEqual(res.alert_code, ALERT_MULTIPLE_SONY_DEVICES_AMBIGUOUS)
            self.assertFalse(res.ready_for_msc_session)
            self.assertTrue(res.hard_abort)
            self.assertEqual(res.sony_device_count, 2)
            self._assert_zero_packet_invariants(res)

    def test_12_state_unsupported_model_pid_hard_abort(self) -> None:
        for fmt in ("xml_plist", "ioreg_text"):
            snap = build_synthetic_ioreg_snapshot(
                scenario="UNSUPPORTED_MODEL_PID", snapshot_format=fmt
            )
            res = classify_passive_usb_snapshot(snap)
            self.assertEqual(res.usb_state, USB_STATE_UNSUPPORTED_MODEL_PID)
            self.assertEqual(res.alert_code, ALERT_UNSUPPORTED_MODEL_PID)
            self.assertFalse(res.ready_for_msc_session)
            self.assertTrue(res.hard_abort)
            self._assert_zero_packet_invariants(res)

    def test_13_state_unsupported_model_name_even_with_0da1_or_unknown_pid(self) -> None:
        fx6_ioreg = """\
+-o ILME-FX6@01100000  <class IOUSBHostDevice, id 0x100000b00>
  {
    "idVendor" = 1356
    "idProduct" = 3489
    "USB Product Name" = "ILME-FX6"
  }
"""
        res = classify_passive_usb_snapshot(fx6_ioreg)
        self.assertEqual(res.usb_state, USB_STATE_UNSUPPORTED_MODEL_PID)
        self.assertTrue(res.hard_abort)
        self._assert_zero_packet_invariants(res)

    def test_14_malformed_xml_plist_fails_safe_without_crash(self) -> None:
        devs, fmt, errs = parse_ioreg_usb_snapshot("<?xml version='1.0'?><plist><broken>")
        self.assertEqual(fmt, "xml_plist")
        self.assertEqual(len(devs), 0)
        self.assertGreater(len(errs), 0)

        res = classify_passive_usb_snapshot("<?xml version='1.0'?><plist><broken>")
        self.assertEqual(res.usb_state, USB_STATE_NO_SONY_CAMERA_ATTACHED)
        self._assert_zero_packet_invariants(res)

    def test_15_capture_passive_ioreg_snapshot_mocked_zero_usb_packets(self) -> None:
        sample = build_synthetic_ioreg_snapshot(
            scenario="READY_MSC_054C_0DA1", snapshot_format="ioreg_text"
        )
        cp = mock.Mock(returncode=0, stdout=sample, stderr="")
        with mock.patch("sys.platform", "darwin"), mock.patch("subprocess.run", return_value=cp) as m_run:
            out, err = capture_passive_ioreg_snapshot()
        self.assertIsNone(err)
        self.assertIn("3489", out)
        called_cmd = m_run.call_args[0][0]
        self.assertEqual(called_cmd, ["ioreg", "-a", "-p", "IOUSB", "-l", "-w", "0"])

    def test_16_capture_passive_ioreg_snapshot_handles_nonzero_and_missing(self) -> None:
        cp_err = mock.Mock(returncode=2, stdout="", stderr="ioreg unavailable")
        with mock.patch("sys.platform", "darwin"), mock.patch("subprocess.run", return_value=cp_err):
            out, err = capture_passive_ioreg_snapshot()
        self.assertEqual(out, "")
        self.assertIn("exited with rc=2", err or "")


class TestPhase154SdStagingAndForbiddenFirewall(unittest.TestCase):
    def _build_valid_sd(self, td: Path) -> Path:
        sd_dir = td / "FX3_STAGEB_SD"
        populate_sd_staging_fixture(
            sd_dir,
            synthetic_clean_room=True,
            include_launcher_file=True,
        )
        return sd_dir

    def test_17_sd_staging_valid_passes_o_rdonly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            res = audit_sd_staging_directory(
                sd_dir,
                free_bytes_override=8 * GIB_BYTES,
                require_launcher_artifact=True,
            )
            self.assertTrue(res.passed, msg=str(res.errors))
            self.assertTrue(res.read_only_o_rdonly_enforced)
            self.assertTrue(res.forbidden_firewall_passed)
            self.assertTrue(res.manifest_present)
            self.assertTrue(res.manifest_signature_valid)
            self.assertEqual(res.stage_b_13_locks_verified, 13)
            self.assertTrue(res.stage_b_13_parity_ok)
            self.assertTrue(res.bk4_shadow_magic_valid)
            self.assertTrue(res.uninstall_manifest_valid)
            self.assertTrue(res.escape_hatch_launcher_hash_ok)
            self.assertEqual(res.escape_hatch_launcher_sha256, EXPECTED_ESCAPE_HATCH_LAUNCHER_SHA256)
            self.assertEqual(res.escape_hatch_max_latency_us, 50)
            self.assertTrue(res.free_space_quota_ok)

    def test_18_sd_staging_not_provided_fails_closed(self) -> None:
        res = audit_sd_staging_directory(None)
        self.assertFalse(res.passed)
        self.assertFalse(res.provided)

    def test_19_sd_staging_missing_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = audit_sd_staging_directory(Path(td) / "does_not_exist")
            self.assertFalse(res.passed)
            self.assertTrue(res.provided)

    def test_20_forbidden_bodydata_dat_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            (sd_dir / "BODYDATA.DAT").write_text("OTA", encoding="utf-8")
            res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
            self.assertFalse(res.passed)
            self.assertFalse(res.forbidden_firewall_passed)
            self.assertIn(BLOCKED_FORBIDDEN_OTA_TRIGGER, res.error_codes)
            self.assertIn("BODYDATA.DAT", res.forbidden_files_found)

    def test_21_forbidden_edisx_elf_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            (sd_dir / "FX6_STAGEB/edisx.elf").write_text("REPART", encoding="utf-8")
            res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
            self.assertFalse(res.passed)
            self.assertIn(BLOCKED_FORBIDDEN_OTA_TRIGGER, res.error_codes)

    def test_22_forbidden_nor_loader_writer_sh_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            (sd_dir / "nor_loader_writer.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
            self.assertFalse(res.passed)
            self.assertIn(BLOCKED_FORBIDDEN_OTA_TRIGGER, res.error_codes)

    def test_23_forbidden_us_spi_firmup_and_us_darwin_firm_rejected(self) -> None:
        for fname in ("us_spi_firmup.sh", "us_darwin_firm.sh"):
            with tempfile.TemporaryDirectory() as td:
                sd_dir = self._build_valid_sd(Path(td))
                (sd_dir / fname).write_text("#!/bin/sh\n", encoding="utf-8")
                res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
                self.assertFalse(res.passed, msg=fname)
                self.assertIn(BLOCKED_FORBIDDEN_OTA_TRIGGER, res.error_codes)

    def test_24_forbidden_setting_updater_mode_glob_rejected(self) -> None:
        for rel in ("setting/updater/mode", "setting/updater/mode_service", "updater/mode1"):
            with tempfile.TemporaryDirectory() as td:
                sd_dir = self._build_valid_sd(Path(td))
                p = sd_dir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("1", encoding="utf-8")
                res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
                self.assertFalse(res.passed, msg=rel)
                self.assertIn(BLOCKED_FORBIDDEN_OTA_TRIGGER, res.error_codes)

    def test_25_sd_symlink_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            target = Path(td) / "outside_secret.txt"
            target.write_text("outside", encoding="utf-8")
            os.symlink(target, sd_dir / "FX6_STAGEB" / "link_leak.txt")
            res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
            self.assertFalse(res.passed)
            self.assertGreater(res.symlink_rejected_count, 0)
            self.assertIn(ERR_SD_SYMLINK_REJECTED, res.error_codes)

    def test_26_sd_free_space_under_2gib_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            res = audit_sd_staging_directory(
                sd_dir, free_bytes_override=MIN_SD_FREE_SPACE_BYTES - 1
            )
            self.assertFalse(res.passed)
            self.assertFalse(res.free_space_quota_ok)
            self.assertIn(ERR_SD_FREE_SPACE_UNDER_2GIB, res.error_codes)

    def test_27_sd_stage_b_13_lock_parity_tamper_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            appfw_p = sd_dir / "FX6_STAGEB/usr_overlay/lib/appFw.so"
            data = bytearray(appfw_p.read_bytes())
            data[-1] ^= 0xFF
            appfw_p.write_bytes(bytes(data))
            res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
            self.assertFalse(res.passed)
            self.assertFalse(res.stage_b_13_parity_ok)
            self.assertLess(res.stage_b_13_locks_verified, 13)
            self.assertIn(ERR_SD_STAGE_B_13_PARITY_FAILED, res.error_codes)

    def test_28_sd_manifest_signature_tamper_and_write_flag_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            mp = sd_dir / SD_MANIFEST_RELPATH
            doc = json.loads(mp.read_text(encoding="utf-8"))
            doc["persistent_emmc_writes_authorized"] = True
            mp.write_text(json.dumps(doc), encoding="utf-8")
            res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
            self.assertFalse(res.passed)
            self.assertFalse(res.manifest_signature_valid)

    def test_29_sd_escape_hatch_launcher_hash_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            (sd_dir / "FX6_STAGEB/rescue/im_elf_escape_hatch.sh").write_text(
                "#!/bin/sh\necho TAMPERED\n", encoding="utf-8"
            )
            res = audit_sd_staging_directory(
                sd_dir, free_bytes_override=8 * GIB_BYTES, require_launcher_artifact=True
            )
            self.assertFalse(res.passed)
            self.assertFalse(res.escape_hatch_launcher_hash_ok)
            self.assertIn(ERR_SD_ESCAPE_HATCH_LAUNCHER_HASH_MISMATCH, res.error_codes)

    def test_30_sd_bk4_and_uninstall_manifest_tamper_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = self._build_valid_sd(Path(td))
            (sd_dir / "FX6_STAGEB/runtime/bk4_ram_shadow.seed").write_bytes(b"BAD!" * 8)
            (sd_dir / "FX6_STAGEB/rescue/uninstall_restore_stock.manifest").write_text(
                "{}", encoding="utf-8"
            )
            res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
            self.assertFalse(res.passed)
            self.assertFalse(res.bk4_shadow_magic_valid)
            self.assertFalse(res.uninstall_manifest_valid)


class TestPhase154DualCopyTier0Receipts(unittest.TestCase):
    def test_31_dual_copy_receipts_valid_passes_crc32_sha256_and_cid(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            info = populate_dual_copy_receipt_fixtures(
                Path(td) / "sd_bk", Path(td) / "vault_bk"
            )
            res = verify_dual_copy_tier0_receipts(
                sd_receipt_path=info["sd_receipt_path"],
                vault_receipt_path=info["vault_receipt_path"],
                expected_camera_cid_sha256=info["camera_cid_sha256"],
            )
            self.assertTrue(res.passed, msg=str(res.errors))
            self.assertTrue(res.crc32_parity_ok)
            self.assertTrue(res.sha256_parity_ok)
            self.assertTrue(res.surface_16_parity_ok)
            self.assertTrue(res.camera_cid_sha256_match)
            self.assertTrue(res.manifest_16_items_verified)
            self.assertEqual(res.sd_copy.byte_length, 528)
            self.assertEqual(res.vault_copy.byte_length, 528)

    def test_32_missing_vault_or_sd_receipt_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            info = populate_dual_copy_receipt_fixtures(
                Path(td) / "sd_bk", Path(td) / "vault_bk"
            )
            res1 = verify_dual_copy_tier0_receipts(
                sd_receipt_path=info["sd_receipt_path"], vault_receipt_path=None
            )
            self.assertFalse(res1.passed)
            self.assertIn(ERR_DUAL_COPY_RECEIPT_MISSING, res1.error_codes)

            res2 = verify_dual_copy_tier0_receipts(
                sd_receipt_path=None, vault_receipt_path=info["vault_receipt_path"]
            )
            self.assertFalse(res2.passed)
            self.assertIn(ERR_DUAL_COPY_RECEIPT_MISSING, res2.error_codes)

    def test_33_corrupt_magic_or_truncated_528b_receipt_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            info = populate_dual_copy_receipt_fixtures(
                Path(td) / "sd_bk", Path(td) / "vault_bk"
            )
            info["sd_receipt_path"].write_bytes(b"BADMAGIC" + b"\x00" * 100)
            res = verify_dual_copy_tier0_receipts(
                sd_receipt_path=info["sd_receipt_path"],
                vault_receipt_path=info["vault_receipt_path"],
            )
            self.assertFalse(res.passed)
            self.assertIn(ERR_DUAL_COPY_RECEIPT_INVALID, res.error_codes)

    def test_34_crc32_and_sha256_mismatch_between_sd_and_vault_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            info = populate_dual_copy_receipt_fixtures(
                Path(td) / "sd_bk", Path(td) / "vault_bk"
            )
            raw = bytearray(info["vault_receipt_path"].read_bytes())
            raw[20] ^= 0x01
            info["vault_receipt_path"].write_bytes(bytes(raw))
            res = verify_dual_copy_tier0_receipts(
                sd_receipt_path=info["sd_receipt_path"],
                vault_receipt_path=info["vault_receipt_path"],
            )
            self.assertFalse(res.passed)
            self.assertFalse(res.crc32_parity_ok)
            self.assertFalse(res.sha256_parity_ok)
            self.assertIn(ERR_DUAL_COPY_CRC32_MISMATCH, res.error_codes)
            self.assertIn(ERR_DUAL_COPY_SHA256_MISMATCH, res.error_codes)

    def test_35_camera_cid_sha256_mismatch_and_trivial_cid_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            info = populate_dual_copy_receipt_fixtures(
                Path(td) / "sd_bk", Path(td) / "vault_bk"
            )
            res_mismatch = verify_dual_copy_tier0_receipts(
                sd_receipt_path=info["sd_receipt_path"],
                vault_receipt_path=info["vault_receipt_path"],
                expected_camera_cid_sha256="a" * 64,
            )
            self.assertFalse(res_mismatch.passed)
            self.assertFalse(res_mismatch.camera_cid_sha256_match)
            self.assertIn(ERR_CAMERA_CID_SHA256_MISMATCH, res_mismatch.error_codes)

            res_trivial = verify_dual_copy_tier0_receipts(
                sd_receipt_bytes=info["sd_receipt_path"].read_bytes(),
                vault_receipt_bytes=info["vault_receipt_path"].read_bytes(),
                sd_camera_cid_sha256="0" * 64,
                vault_camera_cid_sha256="0" * 64,
            )
            self.assertFalse(res_trivial.passed)
            self.assertIn(ERR_CAMERA_CID_SHA256_MISMATCH, res_trivial.error_codes)

    def test_36_manifest_sha256_sidecar_tamper_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            info = populate_dual_copy_receipt_fixtures(
                Path(td) / "sd_bk", Path(td) / "vault_bk"
            )
            (Path(td) / "sd_bk" / "MANIFEST.SHA256").write_text(
                f"{'1' * 64}  sector0_512b.bin\n", encoding="utf-8"
            )
            res = verify_dual_copy_tier0_receipts(
                sd_receipt_path=info["sd_receipt_path"],
                vault_receipt_path=info["vault_receipt_path"],
            )
            self.assertFalse(res.passed)
            self.assertFalse(res.manifest_16_items_verified)


class TestPhase154GoNoGoEngineAndVerify(unittest.TestCase):
    def test_37_offline_default_no_go_truthful_and_verified(self) -> None:
        rep = run_realhw_bench_preflight(synthetic_clean_room=True)
        self.assertEqual(rep.schema, PHASE_154_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_154_VERSION)
        self.assertFalse(rep.bench_go)
        self.assertEqual(rep.verdict, VERDICT_NO_GO)
        self.assertEqual(rep.usb_packets_emitted, 0)
        self.assertEqual(rep.iokit_handles_opened, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.sd_physical_media_written)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_slices_emitted, 0)
        v = verify_phase154_report(rep.to_dict())
        self.assertTrue(v.valid, msg=str(v.errors))

    def test_38_simulate_ready_bench_clean_room_go_verified(self) -> None:
        rep = run_realhw_bench_preflight(simulate_ready_bench=True, synthetic_clean_room=True)
        self.assertTrue(rep.bench_go, msg=str(rep.errors))
        self.assertEqual(rep.verdict, VERDICT_GO_READONLY_PREFLIGHT)
        self.assertTrue(rep.simulated_bench_mode)
        self.assertEqual(rep.usb_classification.usb_state, USB_STATE_READY_MSC_054C_0DA1)
        self.assertTrue(rep.sd_staging_audit.passed)
        self.assertTrue(rep.dual_copy_receipt_audit.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_emitted, 0)
        v = verify_phase154_report(rep.to_dict())
        self.assertTrue(v.valid, msg=str(v.errors))

        md = render_phase154_markdown(rep)
        self.assertIn("GO_READONLY_BENCH_PREFLIGHT", md)
        self.assertIn("G5_HARD_LOCK_NO_PERSISTENT_WRITE", md)

    def test_39_simulate_ready_bench_local_donor_when_available(self) -> None:
        if not _donors_available_for_local_test():
            self.skipTest("Clean-room mode or local donors unavailable")
        rep = run_realhw_bench_preflight(simulate_ready_bench=True, synthetic_clean_room=False)
        self.assertTrue(rep.bench_go, msg=str(rep.errors))
        self.assertEqual(rep.verification_mode, "LOCAL_DONOR_O_RDONLY")
        v = verify_phase154_report(rep.to_dict())
        self.assertTrue(v.valid, msg=str(v.errors))

    def test_40_end_to_end_temp_fixtures_go_and_stranded_0336_no_go(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            sd_dir = td_p / "sd"
            sd_info = populate_sd_staging_fixture(sd_dir, synthetic_clean_room=True)
            rcpt_info = populate_dual_copy_receipt_fixtures(
                td_p / "sd_bk", td_p / "vault_bk"
            )
            snap_go = td_p / "ioreg_msc.txt"
            snap_go.write_text(
                build_synthetic_ioreg_snapshot(
                    scenario="READY_MSC_054C_0DA1", snapshot_format="ioreg_text"
                ),
                encoding="utf-8",
            )
            rep_go = run_realhw_bench_preflight(
                usb_snapshot_path=snap_go,
                sd_dir=sd_dir,
                sd_free_bytes_override=8 * GIB_BYTES,
                sd_receipt_path=rcpt_info["sd_receipt_path"],
                vault_receipt_path=rcpt_info["vault_receipt_path"],
                expected_camera_cid_sha256=sd_info["camera_cid_sha256"],
                synthetic_clean_room=True,
            )
            self.assertTrue(rep_go.bench_go, msg=str(rep_go.errors))
            self.assertTrue(verify_phase154_report(rep_go.to_dict()).valid)

            snap_0336 = td_p / "ioreg_0336.plist"
            snap_0336.write_text(
                build_synthetic_ioreg_snapshot(
                    scenario="STRANDED_SERVICE_054C_0336", snapshot_format="xml_plist"
                ),
                encoding="utf-8",
            )
            rep_0336 = run_realhw_bench_preflight(
                usb_snapshot_path=snap_0336,
                sd_dir=sd_dir,
                sd_free_bytes_override=8 * GIB_BYTES,
                sd_receipt_path=rcpt_info["sd_receipt_path"],
                vault_receipt_path=rcpt_info["vault_receipt_path"],
                expected_camera_cid_sha256=sd_info["camera_cid_sha256"],
                synthetic_clean_room=True,
            )
            self.assertFalse(rep_0336.bench_go)
            self.assertEqual(rep_0336.usb_classification.alert_code, ALERT_SERVICE_MODE_STRANDED)
            self.assertTrue(any("STOP (0336:7)" in r for r in rep_0336.remediation_actions))
            self.assertTrue(verify_phase154_report(rep_0336.to_dict()).valid)

    def test_41_verify_phase154_report_rejects_safety_and_sha256_tampering(self) -> None:
        base = run_realhw_bench_preflight(
            simulate_ready_bench=True, synthetic_clean_room=True
        ).to_dict()
        self.assertTrue(verify_phase154_report(base).valid)

        t1 = copy.deepcopy(base)
        t1["persistent_emmc_writes_authorized"] = True
        self.assertFalse(verify_phase154_report(t1).valid)

        t2 = copy.deepcopy(base)
        t2["usb_packets_emitted"] = 1
        self.assertFalse(verify_phase154_report(t2).valid)

        t3 = copy.deepcopy(base)
        t3["report_sha256"] = "0" * 64
        self.assertFalse(verify_phase154_report(t3).valid)

        t4 = copy.deepcopy(base)
        t4["errors"] = ["injected failure"]
        self.assertFalse(verify_phase154_report(t4).valid)

        t5 = copy.deepcopy(base)
        t5["remediation_actions"] = ["leaked raw bytes b'\\x7fELF'"]
        self.assertFalse(verify_phase154_report(t5).valid)


class TestPhase154CliEndToEnd(unittest.TestCase):
    def test_42_cli_default_no_go_returns_1(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = cli_main(["preflight-realhw-bench", "--clean-room"])
        self.assertEqual(rc, 1)
        out = buf.getvalue()
        self.assertIn("verdict=NO_GO_BENCH_BLOCKED", out)
        self.assertIn("usb_pkts=0", out)
        self.assertIn("emmc_writes_auth=False", out)

    def test_43_cli_simulate_ready_bench_json_output_and_markdown_returns_0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "bench_preflight.json"
            out_md = Path(td) / "bench_preflight.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-realhw-bench",
                        "--clean-room",
                        "--simulate-ready-bench",
                        "--json",
                        "--output",
                        str(out_json),
                        "--markdown-out",
                        str(out_md),
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["verdict"], VERDICT_GO_READONLY_PREFLIGHT)
            self.assertTrue(payload["bench_go"])
            self.assertFalse(payload["persistent_emmc_writes_authorized"])
            self.assertEqual(payload["usb_packets_emitted"], 0)
            self.assertTrue(verify_phase154_report(payload).valid)
            self.assertTrue(out_json.is_file())
            self.assertIn("GO_READONLY_BENCH_PREFLIGHT", out_md.read_text(encoding="utf-8"))

    def test_44_cli_real_temp_inputs_go_and_forbidden_trigger_no_go(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            sd_dir = td_p / "sd"
            sd_info = populate_sd_staging_fixture(sd_dir, synthetic_clean_room=True)
            rcpt_info = populate_dual_copy_receipt_fixtures(
                td_p / "sd_bk", td_p / "vault_bk"
            )
            snap_p = td_p / "ioreg.xml"
            snap_p.write_text(
                build_synthetic_ioreg_snapshot(
                    scenario="READY_MSC_054C_0DA1", snapshot_format="xml_plist"
                ),
                encoding="utf-8",
            )
            args = [
                "preflight-realhw-bench",
                "--clean-room",
                "--usb-snapshot",
                str(snap_p),
                "--sd-dir",
                str(sd_dir),
                "--sd-free-bytes",
                str(8 * GIB_BYTES),
                "--sd-receipt",
                str(rcpt_info["sd_receipt_path"]),
                "--vault-receipt",
                str(rcpt_info["vault_receipt_path"]),
                "--camera-cid-sha256",
                sd_info["camera_cid_sha256"],
                "--json",
            ]
            buf_go = io.StringIO()
            with mock.patch("sys.stdout", buf_go):
                rc_go = cli_main(args)
            self.assertEqual(rc_go, 0)
            self.assertTrue(json.loads(buf_go.getvalue())["bench_go"])

            # Inject forbidden edisx.elf and re-run CLI -> must fail closed with rc=1
            (sd_dir / "edisx.elf").write_text("FORBIDDEN", encoding="utf-8")
            buf_bad = io.StringIO()
            with mock.patch("sys.stdout", buf_bad):
                rc_bad = cli_main(args)
            self.assertEqual(rc_bad, 1)
            bad_doc = json.loads(buf_bad.getvalue())
            self.assertFalse(bad_doc["bench_go"])
            self.assertIn(BLOCKED_FORBIDDEN_OTA_TRIGGER, bad_doc["sd_staging_audit"]["error_codes"])

    def test_45_cli_probe_host_usb_mocked_zero_packets(self) -> None:
        sample = build_synthetic_ioreg_snapshot(
            scenario="NO_SONY_CAMERA_ATTACHED", snapshot_format="ioreg_text"
        )
        cp = mock.Mock(returncode=0, stdout=sample, stderr="")
        buf = io.StringIO()
        with mock.patch("subprocess.run", return_value=cp), mock.patch("sys.stdout", buf):
            rc = cli_main(["preflight-realhw-bench", "--probe-host-usb", "--json"])
        self.assertEqual(rc, 1)
        doc = json.loads(buf.getvalue())
        self.assertEqual(doc["usb_packets_emitted"], 0)
        self.assertEqual(doc["iokit_handles_opened"], 0)
        self.assertEqual(doc["usb_classification"]["usb_state"], USB_STATE_NO_SONY_CAMERA_ATTACHED)
        self.assertTrue(verify_phase154_report(doc).valid)

    def test_46_sd_exfat_invalid_chars_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sd_dir = Path(td) / "sd"
            populate_sd_staging_fixture(sd_dir, synthetic_clean_room=True)
            (sd_dir / "bad?name.txt").write_text("bad", encoding="utf-8")
            res = audit_sd_staging_directory(sd_dir, free_bytes_override=8 * GIB_BYTES)
            self.assertFalse(res.passed)
            self.assertFalse(res.exfat_paths_valid)


if __name__ == "__main__":
    unittest.main()
