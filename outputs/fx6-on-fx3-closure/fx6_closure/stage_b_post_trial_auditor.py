"""Phase 62 — Stage-B `H0`-vs-`H2` Post-Trial Zero-Persistence Forensic Auditor (`stage_b_post_trial_auditor.py`).

Upgrades Stage-A post-trial auditing (`stage_a_post_trial_auditor.py`) to full
**Stage-B (`P1..P12+Fan` + C2PA/Calibration + `exFAT` Media + `RP2040` Fixture + `BK4`/`WBI2`/`CP` Zero-Drift)**:

1. **Bit-for-Bit `H0` Pre-Trial vs `H2` Post-Reboot Zero-Persistence Forensic Differ**
   (`verify_stage_b_post_trial_zero_persistence`):
   - Validates BOTH `h0_bundle_dir` (pre-trial baseline) and `h2_bundle_dir` (post-power-cycle
     stock FX3 `v7.02` readback) via `verify_real_tier0_capture_bundle`, enforcing distinct
     non-symlink capture directories and 100% same-body hardware identity
     (`model_id == "0x91030080"`, matching `body_serial`, 128-bit `emmc_cid`, and `camera_body_tag`).
   - Streams and diffs (strictly via `os.open(..., os.O_RDONLY)`) all 11 mandatory Tier-0
     partition/calibration images + 2 mandatory redline header probes + Stage-B forensic probes
     (`p8_cp_image`, `c2pa_rq_lic`, `spacc_cnflasha` — 16 persistent surfaces total):
       * `sector0` (`'8246'` `'2.00'` `FX3_702`/`FX3_PARTINF_205`, `sector0_mutation_bytes == 0`)
       * `p2:/setting` `'BK4\\0'` persistent NVRAM (`bk4_mutated_bytes == 0`, `boot_img` byte `+8 == 0x00`,
         zero `/setting/updater/mode*` residue, and persistent Airplane-Mode keys `0x019e0012` /
         `0x0051000f` / `0x01a20002` + persistent `BK_LANG` `0x02cf019c` 100% unchanged vs `H0`,
         proving `/tmp/bk4_shadow` Airplane + CJK language override left `0` persistent NVRAM bytes altered)
       * `p5:/wbi` `'WBI2'` (`wbi_mutation_bytes == 0`, valid 88-byte `WBI2` hibernation header)
       * `p8:/cp` (`p8_tomco.txt` + `p8_cpapp_b.bin` Stock-CP `cp_mutation_bytes == 0`)
   - **C2PA (`RQ_LIC.DAT`) & `SPACC cnflasha` / Factory Sensor & IBIS Gyro Calibration Zero-Drift Proof**:
     `calibration_mutation_bytes == 0`, `c2pa_keystore_untouched == True`, `spacc_cnflasha_untouched == True`.
   - **`p1` VFAT One-Shot Boot-Counter & Rollback Capsule State + `exFAT` Lab Media Cleanliness**:
     Verifies `p1` VFAT (`FAT12`/`FAT16`) dual-FAT parity, `boot_attempts == 0` / `/tmp/mod_arm_once`
     unlinked, `p1` rollback capsule SHA-256 + `fsync` order, and `exFAT` BootChecksum +
     `VolumeDirty == 0` + `MediaFailure == 0` + zero `.RSV` unfinalized crash clips.
   - **`RP2040` Fixture + `serial_fault_detector_v2` + Thermal/Power Session Log Post-Mortem**:
     Verifies `RP2040-Zero` `-DOPEN_DRAIN` `1.8V` `48000` baud isolation, `serial_fault_detector_v2`
     `PASS` + `TIMER-IP` `<90s/220s` watchdog budget, peak session `SoC_C < 90.0°C`, zero
     `00342260` (`WF-12`) wireless hangs, zero `0x100D` (`13S`) panics, and
     `persistent_emmc_writes_authorized == False`.

2. **10-Scenario Anomaly & Drift Classifier** (`run_stage_b_post_trial_forensic_audit`):
   - Deterministic classification of 1 clean `H0==H2` Stage-B session (`S01`) + 9 injected
     post-trial anomalies (`S02..S10`), failing closed on every persistent drift.
   - Executes real `os.O_RDONLY` donor probes in Local Donor mode and deterministic synthetic
     equivalents in `FX3_FX6_FORCE_CLEAN_ROOM=1` mode, producing a self-authenticating
     `stage_b_post_trial_forensic_audit_v1` report (`verify_stage_b_post_trial_report`).

Hard-Locked Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `P8_CP_MUTATION_FORBIDDEN = True`, `CP_MUTATION_BYTES = 0`
- `WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True`, `WBI_MUTATION_BYTES = 0`
- `CALIBRATION_MUTATION_BYTES = 0`, `USB_OR_CAMERA_OPERATIONS = 0`
- All file reads strictly use `os.open(..., os.O_RDONLY)`.
- Never prints or embeds raw binary `bytes` reprs (`b'...'` / `b"..."`).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import tempfile
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from fx3_recovery.emmc_dump_forensic_verifier import (
    CPAPP_ARM_RESET_WORDS,
    build_synthetic_encrypted_cnflasha,
)
from fx3_recovery.unbrick_ladder_and_capsule_verifier import (
    REQUIRED_FSYNC_ORDER,
    audit_capsule_fsync_order,
)
from fx3_safety.boot_contracts import (
    BK4_HEADER_SIZE,
    BK4_MAGIC,
    BK4_SYNC_MARKER,
    FA0080_TOTAL_BYTES,
    parse_bk4_record,
    verify_sector0_partition_table,
)
from fx3_safety.exfat_media_integrity_guard import (
    EXFAT_FLAG_MEDIA_FAILURE,
    EXFAT_FLAG_VOLUME_DIRTY,
    build_synthetic_exfat_boot_region,
    inspect_sony_media_tree,
    parse_p1_fat12_fat16_vbr,
    verify_exfat_boot_region,
)
from fx3_safety.master_16gate_preflight import (
    verify_c2pa_and_factory_calibration_immutability,
)
from fx3_safety.multiport_bootrom_unbrick import (
    UART_BOOT_BAUD,
    validate_rp2040_multiport_harness,
)
from fx3_safety.preflight import TIER0_CANONICAL_SOURCES, TIER0_REQUIRED_BACKUPS
from fx3_safety.serial_fault_detector_v2 import (
    DISPOSITION_PASS,
    audit_serial_boot_telemetry,
)
from fx3_safety.thermal_pwm_and_power_guard import (
    FAIL_CLOSED_TEARDOWN_TEMP_C,
    H0_H1_REHEARSAL_MIN_SOC_PCT,
    USBPD_REQUIRED_POWER_MW,
)

from .backup_mount_tolerance_verifier import (
    BK4_ATTR_SHADOW_CRC16,
    BK4_SHADOW_MODEL_TAG,
    BK4_SHADOW_SUBSYSTEM_COUNT,
    BK4_VERSION_WORD0,
    KEY_BOOT_SCREEN_MODEL_A,
    KEY_BOOT_SCREEN_MODEL_B,
    KEY_DUAL_SLOT_MEDIA_SHADOW,
    KEY_FA0080_BOOT_DESC,
    KEY_FA0084_BOOT_SELECTOR,
    KEY_FIXED_AREA_SIZE,
    KEY_FIXED_AREA_TOP,
    KEY_MEDIACONFIG_SLOT0_BASE,
    KEY_MEDIACONFIG_SLOT1_BASE,
    KEY_MEDIACONFIG_SLOT2_BASE,
    _build_mediaconfig_64byte_slot_record,
    build_canonical_fa0080_normal_boot_table,
    build_dual_slot_807b002b_payload,
    compute_crc16_ccitt,
    read_bk4_property_bytes,
)
from .donor_paths import resolve_work_subpath
from .hardware_readiness_packet import (
    FX3_MODEL_ID_HEX,
    HEX64_RE,
    REQUIRED_REDLINE_HEADER_PROBES,
    SAFE_FILENAME_RE,
    RealTier0CaptureBundleAudit,
    _build_valid_fat16_p1_header_prefix,
    _build_valid_fx3_sector0_bytes,
    _build_valid_p5_wbi2_header_bytes,
    _build_valid_p8_tomco_bytes,
    _is_forced_clean_room,
    audit_p1_vfat_header,
    verify_real_tier0_capture_bundle,
)
from .patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR
from .stage_a_boot_orchestrator import parse_wbi2_header_bytes
from .stage_a_post_trial_auditor import (
    STICKY_UPDATER_RELPATH_RE,
    recompute_bk4_record0_checksum,
)
from .stage_b_ram_overlay_packager import (
    BK_KEY_LANG,
    STAGE_B_AIRPLANE_KEYS,
    STAGE_B_BK_LANG_SPECS,
)
from .wireless_fault_isolation_verifier import (
    BT_BKID_ENABLE_PRIMARY,
    BT_BKID_ENABLE_SECONDARY,
    BT_BKID_RSRC_MODE,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Constants & Schema Definitions
# ---------------------------------------------------------------------------

STAGE_B_POST_TRIAL_RECEIPT_SCHEMA: str = "stage_b_post_trial_receipt_v1"
STAGE_B_POST_TRIAL_AUDIT_SCHEMA: str = "stage_b_post_trial_forensic_audit_v1"
PHASE_62_VERSION: str = "62.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
P8_CP_MUTATION_FORBIDDEN: bool = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN: bool = True
CP_MUTATION_BYTES: int = 0
WBI_MUTATION_BYTES: int = 0
CALIBRATION_MUTATION_BYTES: int = 0
USB_OR_CAMERA_OPERATIONS: int = 0

READ_CHUNK_BYTES: int = 1024 * 1024  # 1 MiB O_RDONLY streaming chunks

STAGE_B_FORENSIC_PROBE_DEFAULTS: Dict[str, str] = {
    "p8_cp_image": "p8_cpapp_b.bin",
    "c2pa_rq_lic": "c2pa_rq_lic.dat",
    "spacc_cnflasha": "spacc_cnflasha_probe.bin",
}

STAGE_B_CALIBRATION_ITEM_IDS: Tuple[str, ...] = (
    "p2_backup_bin",
    "p2_psd_bin",
    "p2_defdet_bin",
    "p6_jiritsu",
    "p12_cert",
    "p18_lensfile",
    "spi_nor_ddrtraining",
    "c2pa_rq_lic",
    "spacc_cnflasha",
)

# Canonical Anomaly & Classification Codes
CLASS_CLEAN_ZERO_PERSISTENCE: str = "CLEAN_H0_EQ_H2_ZERO_PERSISTENCE"
ANOMALY_BK4_PERSISTENT_NVRAM_LEAK: str = "ANOMALY_BK4_PERSISTENT_NVRAM_LEAK"
ANOMALY_WBI2_HEADER_DRIFT: str = "ANOMALY_WBI2_HEADER_DRIFT"
ANOMALY_CP_BYTE_MUTATION: str = "ANOMALY_CP_BYTE_MUTATION"
ANOMALY_C2PA_OR_CALIBRATION_DRIFT: str = "ANOMALY_C2PA_OR_CALIBRATION_DRIFT"
ANOMALY_EXFAT_VOLUME_DIRTY: str = "ANOMALY_EXFAT_VOLUME_DIRTY"
ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP: str = "ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP"
ANOMALY_WF12_00342260_HANG: str = "ANOMALY_WF12_00342260_HANG"
ANOMALY_THERMAL_RUNAWAY_TEARDOWN: str = "ANOMALY_THERMAL_RUNAWAY_TEARDOWN"
ANOMALY_SECTOR0_TAMPER: str = "ANOMALY_SECTOR0_TAMPER"
ANOMALY_0x100D_13S_PANIC: str = "ANOMALY_0x100D_13S_PANIC"
ANOMALY_P1_CAPSULE_OR_COUNTER_DRIFT: str = "ANOMALY_P1_CAPSULE_OR_COUNTER_DRIFT"
ANOMALY_RP2040_FIXTURE_HAZARD: str = "ANOMALY_RP2040_FIXTURE_HAZARD"
ANOMALY_SERIAL_WATCHDOG_OR_PANIC: str = "ANOMALY_SERIAL_WATCHDOG_OR_PANIC"
ANOMALY_SAME_BODY_IDENTITY_MISMATCH: str = "ANOMALY_SAME_BODY_IDENTITY_MISMATCH"
ANOMALY_SYNTHETIC_OR_INVALID_BUNDLE: str = "ANOMALY_SYNTHETIC_OR_INVALID_BUNDLE"
ANOMALY_TIER0_PERSISTENT_DRIFT: str = "ANOMALY_TIER0_PERSISTENT_DRIFT"
ANOMALY_PERSISTENT_EMMC_WRITE_POLICY: str = "ANOMALY_PERSISTENT_EMMC_WRITE_POLICY"

STAGE_B_POST_TRIAL_SCENARIO_IDS: Tuple[str, ...] = (
    "S01_CLEAN_H0_EQ_H2_STAGE_B_SESSION",
    "S02_BK4_PERSISTENT_AIRPLANE_LEAK",
    "S03_WBI2_HEADER_DRIFT",
    "S04_CP_BYTE_MUTATION",
    "S05_C2PA_CALIBRATION_DIGEST_DRIFT",
    "S06_EXFAT_VOLUME_DIRTY_SET",
    "S07_EXFAT_RSV_CLIP_LEFT_BEHIND",
    "S08_WF12_00342260_LOG_SIGNATURE",
    "S09_THERMAL_90C_EMERGENCY_TEARDOWN",
    "S10_SECTOR0_TAMPER",
)

STAGE_B_ANOMALY_CLASSIFICATION_CODES: Tuple[str, ...] = (
    CLASS_CLEAN_ZERO_PERSISTENCE,
    ANOMALY_BK4_PERSISTENT_NVRAM_LEAK,
    ANOMALY_WBI2_HEADER_DRIFT,
    ANOMALY_CP_BYTE_MUTATION,
    ANOMALY_C2PA_OR_CALIBRATION_DRIFT,
    ANOMALY_EXFAT_VOLUME_DIRTY,
    ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP,
    ANOMALY_WF12_00342260_HANG,
    ANOMALY_THERMAL_RUNAWAY_TEARDOWN,
    ANOMALY_SECTOR0_TAMPER,
)

# Donor relative paths (probed strictly via os.O_RDONLY in Local Donor mode)
DONOR_P1_RELPATH: str = "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
DONOR_P5_WBI2_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha5.img"
DONOR_P8_CP_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha8.img"
DONOR_FX3_SEED_BK4_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_WF12_00342260_RE = re.compile(
    r"(?:00342260|\bWF-?12\b|WlanResourceMainThread.*(?:0x70d4|hang|usleep|loop|fatal)|"
    r"MODEL_WIFI_FATAL_ERROR_OCCURRED|Fatal error on Wi-Fi func|WLAN_RESOURCE_0x70D4_HANG)",
    re.IGNORECASE,
)
_PANIC_0x100D_13S_RE = re.compile(
    r"(?:\b0x100[dD]\b|\b13S\b|13\s+short\s+blinks|BAD_UART_BLINK)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageBPostTrialItemParity:
    item_id: str
    category: str
    file_name: str
    h0_bytes: int
    h2_bytes: int
    h0_sha256: str
    h2_sha256: str
    differing_bytes: int
    bit_exact_match: bool


@dataclass(frozen=True)
class StageBBk4NvramZeroDriftAudit:
    valid: bool
    h0_bk4_sha256: str
    h2_bk4_sha256: str
    bk4_bit_exact_match: bool
    bk4_mutated_bytes: int
    u5_boot_img_byte8_zero_ok: bool
    h2_bk4_byte8: Optional[int]
    u5_zero_updater_mode_residue_ok: bool
    sticky_updater_residue: Tuple[str, ...]
    persistent_airplane_keys_unchanged: bool
    persistent_bk_lang_unchanged: bool
    ram_shadow_bk4_only: bool
    ram_shadow_bk_lang: str
    ram_shadow_airplane_keys: Dict[str, str]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageBC2paSpaccCalibrationAudit:
    valid: bool
    calibration_mutation_bytes: int
    c2pa_keystore_untouched: bool
    spacc_cnflasha_untouched: bool
    c2pa_rq_lic_h0_sha256: str
    c2pa_rq_lic_h2_sha256: str
    spacc_cnflasha_h0_sha256: str
    spacc_cnflasha_h2_sha256: str
    audited_calibration_items: Tuple[str, ...]
    drifted_calibration_items: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageBP1CapsuleAndExfatAudit:
    valid: bool
    p1_vfat_valid: bool
    p1_vfat_type: str
    p1_oneshot_boot_counter_clean: bool
    p1_boot_attempts_observed: int
    p1_capsule_sha256: str
    p1_capsule_fsync_order_ok: bool
    exfat_vbr_valid: bool
    exfat_boot_checksum_ok: bool
    exfat_volume_dirty: bool
    exfat_media_failure: bool
    exfat_rsv_files: Tuple[str, ...]
    exfat_chk_files: Tuple[str, ...]
    exfat_media_clean: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageBRp2040AndSerialThermalPostMortem:
    valid: bool
    rp2040_fixture_safe: bool
    rp2040_board: str
    rp2040_open_drain_enforced: bool
    rp2040_io_voltage_v: float
    rp2040_baud_rate: int
    serial_detector_v2_passed: bool
    serial_detector_disposition: str
    watchdog_budget_passed: bool
    wf12_00342260_hang_detected: bool
    panic_0x100d_13s_detected: bool
    peak_soc_c: float
    thermal_under_90c_ok: bool
    thermal_emergency_teardown_triggered: bool
    npfz100_soc_pct: int
    usbpd_contract_mw: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageBPostTrialReceipt:
    schema: str
    phase_version: str
    verification_mode: str
    all_checks_passed: bool
    zero_persistence_verified: bool
    classification: str
    anomaly_codes: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    usb_or_camera_operations: int
    distinct_capture_dirs_ok: bool
    h0_bundle_valid: bool
    h2_bundle_valid: bool
    both_bundles_real_hardware_valid: bool
    same_body_identity_verified: bool
    model_id: str
    body_serial: str
    emmc_cid: str
    camera_body_tag: str
    audited_item_count: int
    matched_item_count: int
    persistent_bytes_mutated: int
    wbi_mutation_bytes: int
    cp_mutation_bytes: int
    calibration_mutation_bytes: int
    sector0_mutation_bytes: int
    c2pa_keystore_untouched: bool
    spacc_cnflasha_untouched: bool
    drifted_items: Tuple[str, ...]
    item_comparisons: Tuple[StageBPostTrialItemParity, ...]
    bk4_nvram_audit: StageBBk4NvramZeroDriftAudit
    c2pa_calibration_audit: StageBC2paSpaccCalibrationAudit
    p1_exfat_audit: StageBP1CapsuleAndExfatAudit
    serial_thermal_post_mortem: StageBRp2040AndSerialThermalPostMortem
    h0_bundle_audit: Dict[str, Any]
    h2_bundle_audit: Dict[str, Any]
    errors: Tuple[str, ...]
    receipt_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class StageBPostTrialScenarioResult:
    scenario_id: str
    description: str
    expected_pass: bool
    expected_anomaly_code: str
    observed_pass: bool
    observed_classification: str
    observed_anomaly_codes: Tuple[str, ...]
    passed: bool
    persistent_bytes_mutated: int
    wbi_mutation_bytes: int
    cp_mutation_bytes: int
    calibration_mutation_bytes: int
    sector0_mutation_bytes: int
    c2pa_keystore_untouched: bool
    exfat_media_clean: bool
    drifted_items: Tuple[str, ...]
    primary_error: str
    receipt_sha256: str


@dataclass(frozen=True)
class StageBPostTrialAuditReport:
    schema: str
    phase_version: str
    verification_mode: str
    all_checks_passed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    calibration_mutation_bytes: int
    usb_or_camera_operations: int
    temp_dir_cleaned: bool
    donor_o_rdonly_probes: Dict[str, Any]
    nominal_receipt: StageBPostTrialReceipt
    scenario_count: int
    passed_scenario_count: int
    all_10_scenarios_passed: bool
    scenarios: Tuple[StageBPostTrialScenarioResult, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class StageBPostTrialVerifyResult:
    valid: bool
    schema_ok: bool
    sha256_matched: bool
    expected_report_sha256: str
    observed_report_sha256: str
    safety_redlines_ok: bool
    nominal_receipt_ok: bool
    all_10_scenarios_ok: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Strict os.O_RDONLY File Helpers & Canonical Hashing
# ---------------------------------------------------------------------------


def _read_file_o_rdonly(path: Union[str, Path]) -> bytes:
    """Read an entire file strictly via `os.open(..., os.O_RDONLY)`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, READ_CHUNK_BYTES)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_slice_o_rdonly(path: Union[str, Path], offset: int, length: int) -> bytes:
    """Read a bounded slice strictly via `os.open(..., os.O_RDONLY)`."""
    if offset < 0 or length < 0:
        raise ValueError("offset and length must be non-negative")
    fd = os.open(str(path), os.O_RDONLY)
    try:
        if offset > 0:
            os.lseek(fd, offset, os.SEEK_SET)
        out = bytearray()
        while len(out) < length:
            chunk = os.read(fd, length - len(out))
            if not chunk:
                break
            out.extend(chunk)
        return bytes(out)
    finally:
        os.close(fd)


def _hash_single_file_o_rdonly(path: Path) -> Tuple[int, str]:
    """Stream-hash a file strictly via `os.open(..., os.O_RDONLY)`."""
    h = hashlib.sha256()
    sz = 0
    fd = os.open(str(path), os.O_RDONLY)
    try:
        while True:
            blk = os.read(fd, READ_CHUNK_BYTES)
            if not blk:
                break
            sz += len(blk)
            h.update(blk)
    finally:
        os.close(fd)
    return sz, h.hexdigest()


def _stream_compare_two_files_o_rdonly(
    h0_path: Optional[Path],
    h2_path: Optional[Path],
) -> Tuple[int, int, str, str, int]:
    """Stream-hash and byte-diff two files strictly via `os.O_RDONLY`."""
    if h0_path is None or not h0_path.is_file() or h0_path.is_symlink():
        if h2_path is None or not h2_path.is_file() or h2_path.is_symlink():
            return 0, 0, "", "", 0
        h2_sz, h2_sha = _hash_single_file_o_rdonly(h2_path)
        return 0, h2_sz, "", h2_sha, max(1, h2_sz)

    if h2_path is None or not h2_path.is_file() or h2_path.is_symlink():
        h0_sz, h0_sha = _hash_single_file_o_rdonly(h0_path)
        return h0_sz, 0, h0_sha, "", max(1, h0_sz)

    d0 = hashlib.sha256()
    d2: Optional[hashlib._Hash] = None
    sz0 = 0
    sz2 = 0
    diff_bytes = 0

    fd0 = os.open(str(h0_path), os.O_RDONLY)
    try:
        fd2 = os.open(str(h2_path), os.O_RDONLY)
        try:
            while True:
                b0 = os.read(fd0, READ_CHUNK_BYTES)
                b2 = os.read(fd2, READ_CHUNK_BYTES)
                if not b0 and not b2:
                    break
                if d2 is None and b0 == b2:
                    sz0 += len(b0)
                    sz2 += len(b2)
                    d0.update(b0)
                    continue
                if d2 is None:
                    d2 = d0.copy()
                if b0:
                    sz0 += len(b0)
                    d0.update(b0)
                if b2:
                    sz2 += len(b2)
                    d2.update(b2)
                common_len = min(len(b0), len(b2))
                if common_len > 0:
                    mv0 = memoryview(b0)[:common_len]
                    mv2 = memoryview(b2)[:common_len]
                    for x, y in zip(mv0, mv2):
                        if x != y:
                            diff_bytes += 1
                diff_bytes += abs(len(b0) - len(b2))
        finally:
            os.close(fd2)
    finally:
        os.close(fd0)

    sha0 = d0.hexdigest()
    sha2 = sha0 if d2 is None else d2.hexdigest()
    return sz0, sz2, sha0, sha2, diff_bytes


def _compute_canonical_sha256(payload: Mapping[str, Any], exclude_key: str) -> str:
    body = copy.deepcopy(dict(payload))
    body.pop(exclude_key, None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _compute_report_sha256(payload: Mapping[str, Any]) -> str:
    return _compute_canonical_sha256(payload, "report_sha256")


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _load_json_o_rdonly(path: Path) -> Dict[str, Any]:
    if not path.exists() or path.is_symlink() or not path.is_file():
        return {}
    try:
        raw = _read_file_o_rdonly(path).decode("utf-8")
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _resolve_item_filename(
    manifest: Mapping[str, object],
    section_key: str,
    item_key: str,
    default_fn: str,
) -> str:
    sec = manifest.get(section_key)
    if isinstance(sec, Mapping):
        ent = sec.get(item_key)
        if isinstance(ent, Mapping):
            cand = str(ent.get("file_name", default_fn))
            if SAFE_FILENAME_RE.fullmatch(cand) and cand not in (".", ".."):
                return cand
    return default_fn


# ---------------------------------------------------------------------------
# Stage-B Fixture & BK4 Persistent Baseline Builders
# ---------------------------------------------------------------------------


def build_persistent_stock_bk4_bytes(
    *,
    fa0080_table: Optional[bytes] = None,
    wireless_enabled: bool = True,
    bk_lang_byte: int = 0x00,
    active_byte8: int = 0x00,
) -> bytes:
    """Build a valid `BK4\\0` Record 0 representing stock FX3 persistent `Backup.bin`.

    By default (`wireless_enabled=True, bk_lang_byte=0x00`), persistent eMMC NVRAM
    has wireless ON (`0x019e0012=0x01`, `0x0051000f=0x01`, `0x01a20002=0x01`) and
    English `BK_LANG` (`0x00`), proving that Stage-B `/tmp/bk4_shadow` Airplane + CJK
    overrides do not leak into persistent eMMC NVRAM.
    """
    if fa0080_table is None:
        fa0080_table = build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None)
    if len(fa0080_table) != FA0080_TOTAL_BYTES:
        raise ValueError(f"Expected {FA0080_TOTAL_BYTES} B fa0080_table, got {len(fa0080_table)}")
    w_val = 0x01 if wireless_enabled else 0x00
    kv_map: Dict[int, bytes] = {
        KEY_FIXED_AREA_TOP: struct.pack("<Q", 0x90000000),
        KEY_FIXED_AREA_SIZE: struct.pack("<Q", 0x04000000),
        KEY_FA0080_BOOT_DESC: fa0080_table,
        KEY_FA0084_BOOT_SELECTOR: struct.pack("<Q", 0),
        KEY_DUAL_SLOT_MEDIA_SHADOW: build_dual_slot_807b002b_payload(),
        KEY_BOOT_SCREEN_MODEL_A: bytes([0]),
        KEY_BOOT_SCREEN_MODEL_B: bytes([1]),
        BT_BKID_ENABLE_PRIMARY: bytes([w_val]),
        BT_BKID_ENABLE_SECONDARY: bytes([w_val]),
        BT_BKID_RSRC_MODE: bytes([w_val]),
        BK_KEY_LANG: bytes([bk_lang_byte & 0xFF]),
    }
    slot0_rec = _build_mediaconfig_64byte_slot_record(0x1000, 0x01, 1)
    slot1_rec = _build_mediaconfig_64byte_slot_record(0x1010, 0x02, 2)
    slot2_rec = _build_mediaconfig_64byte_slot_record(0, 0, 0)
    for i in range(64):
        kv_map[KEY_MEDIACONFIG_SLOT0_BASE + i] = bytes([slot0_rec[i]])
        kv_map[KEY_MEDIACONFIG_SLOT1_BASE + i] = bytes([slot1_rec[i]])
        kv_map[KEY_MEDIACONFIG_SLOT2_BASE + i] = bytes([slot2_rec[i]])

    by_sub: Dict[int, Dict[int, Tuple[int, bytes]]] = {}
    for full_k, val in kv_map.items():
        s_idx = (full_k >> 16) & 0x7FFF
        u_idx = full_k & 0xFFFF
        by_sub.setdefault(s_idx, {})[u_idx] = (full_k, val)

    sub_entries: List[Tuple[int, int]] = []
    prop_units: List[Optional[Tuple[int, bytes]]] = []
    for s_idx in range(BK4_SHADOW_SUBSYSTEM_COUNT):
        units = by_sub.get(s_idx)
        if not units:
            sub_entries.append((0, 0))
            continue
        cnt = max(units.keys()) + 1
        first_prop = len(prop_units)
        sub_entries.append((cnt, first_prop))
        for u_idx in range(cnt):
            prop_units.append(units.get(u_idx))

    total_props = len(prop_units)
    raw_table_end = BK4_HEADER_SIZE + BK4_SHADOW_SUBSYSTEM_COUNT * 6 + total_props * 6
    data_offset = (raw_table_end + 15) & ~15

    data_blob = bytearray()
    prop_table_bytes = bytearray()
    for item in prop_units:
        if item is None:
            prop_table_bytes.extend(struct.pack("<HI", 0x0000, 0xFFFFFFFF))
            continue
        full_key, payload = item
        rel_off = data_offset + len(data_blob)
        crc16 = compute_crc16_ccitt(struct.pack("<I", full_key) + payload)
        if len(payload) == FA0080_TOTAL_BYTES:
            tag8 = 0xFF
            data_blob.extend(struct.pack("<H", len(payload)))
            data_blob.extend(payload)
            data_blob.extend(struct.pack("<H", crc16))
        elif 1 <= len(payload) <= 0xFE:
            tag8 = len(payload)
            data_blob.extend(payload)
            data_blob.extend(struct.pack("<H", crc16))
        else:
            tag8 = 0x00
            data_blob.extend(struct.pack("<HH", len(payload), len(payload)))
            data_blob.extend(payload)
            data_blob.extend(struct.pack("<H", crc16))
        word2 = ((tag8 & 0xFF) << 24) | (rel_off & 0xFFFFFF)
        prop_table_bytes.extend(struct.pack("<HI", BK4_ATTR_SHADOW_CRC16, word2))

    while len(data_blob) % 4 != 0:
        data_blob.append(0)
    data_size = len(data_blob)
    total_bytes = data_offset + data_size

    buf = bytearray(total_bytes)
    struct.pack_into("<II", buf, 0x00, BK4_VERSION_WORD0, BK4_SYNC_MARKER)
    buf[0x08] = active_byte8 & 0xFF
    buf[0x0C:0x10] = BK4_MAGIC
    struct.pack_into(
        "<IIIIII",
        buf,
        0x10,
        BK4_SHADOW_SUBSYSTEM_COUNT,
        total_props,
        data_offset,
        data_size,
        0,
        0x30,
    )
    struct.pack_into("<i", buf, 0x2C, 0)
    buf[0xC0 : 0xC0 + len(BK4_SHADOW_MODEL_TAG)] = BK4_SHADOW_MODEL_TAG
    for idx, (cnt, first_p) in enumerate(sub_entries):
        struct.pack_into("<HI", buf, BK4_HEADER_SIZE + idx * 6, cnt, first_p)
    prop_base = BK4_HEADER_SIZE + BK4_SHADOW_SUBSYSTEM_COUNT * 6
    buf[prop_base : prop_base + len(prop_table_bytes)] = prop_table_bytes
    buf[data_offset : data_offset + data_size] = data_blob
    return recompute_bk4_record0_checksum(bytes(buf))


def _build_synthetic_p8_cp_image_bytes(size_bytes: int = 8192) -> bytes:
    buf = bytearray(size_bytes)
    for idx, w in enumerate(CPAPP_ARM_RESET_WORDS):
        struct.pack_into("<I", buf, idx * 4, w)
    marker = b"[TOMCO]FX3_STOCK_CP_RTOS_V702_NO_MUTATION\x00"
    buf[0x40 : 0x40 + len(marker)] = marker
    seed = hashlib.sha256(b"fx3-p8-cpapp-b-stock-v702").digest()
    for off in range(0x100, size_bytes, len(seed)):
        take = min(len(seed), size_bytes - off)
        buf[off : off + take] = seed[:take]
    return bytes(buf)


def _build_synthetic_c2pa_rq_lic_bytes(size_bytes: int = 4096) -> bytes:
    buf = bytearray(size_bytes)
    hdr = b"C2PA_RQ_LIC_DAT_V1_SONY_TZ_SEALED\x00"
    buf[0 : len(hdr)] = hdr
    seed = hashlib.sha256(b"fx3-c2pa-rq-lic-dat-sealed").digest()
    for off in range(0x40, size_bytes, len(seed)):
        take = min(len(seed), size_bytes - off)
        buf[off : off + take] = seed[:take]
    return bytes(buf)


def _build_clean_stage_b_serial_log() -> str:
    return "\n".join(
        (
            "[    1.200000] FX6_STAGE_A_CLEAR_BEFORE_EXEC token_unlinked=1",
            "[    2.100000] WDT_SET_STOP source=stage_b_orchestrator wdt_budget_sec=90.0 timer_ip_sec=220.0",
            "[    2.700000] FX6_STAGE_A_VERIFY_RC=0 verified_digests=13",
            "[    6.400000] FX6_STAGE_B_BRIDGE stage=B p10_keymap=1 p11_uipc_shim=1 p12_wlan_guard=1 airplane_bk4=1 nop_count=0",
            "[    7.100000] P12_wlan_resource_handleFatalError_nonblocking status=OK",
            "[    7.800000] FX6_STAGE_B_P11_ACTIVE rtc_q=0x92d2091c handle_q=0x91db059b bb_q=0x92840747 xlr_h1_preserved=1",
            "[   14.200000] FX6_STAGE_B_LIFO_TEARDOWN_CLEAN lingering_mounts=0 emmc_writes=0 wbi_writes=0",
        )
    ) + "\n"


def _write_patterned_file(path: Path, total_bytes: int, header: bytes, seed: bytes) -> None:
    if len(header) > total_bytes:
        raise ValueError(f"Header {len(header)} > total_bytes {total_bytes}")
    block = (seed * ((65536 // len(seed)) + 1))[:65536]
    with path.open("wb") as fh:
        fh.write(header)
        rem = total_bytes - len(header)
        if rem > 0:
            lead = min(rem, max(0, 65536 - len(header)))
            if lead:
                fh.write(block[:lead])
                rem -= lead
            while rem >= 65536:
                fh.write(block)
                rem -= 65536
            if rem > 0:
                fh.write(block[:rem])


def populate_stage_b_capture_bundle_fixture(
    bundle_dir: Path | str,
    *,
    body_serial: str = "3018492",
    emmc_cid: str = "15010038474d453452019c4a7b8e5f91",
    fa0080_table: Optional[bytes] = None,
    bk4_bytes: Optional[bytes] = None,
    exfat_boot_bytes: Optional[bytes] = None,
    exfat_card_entries: Optional[Sequence[Dict[str, Any]]] = None,
    serial_log_text: Optional[str] = None,
    thermal_power_telemetry: Optional[Mapping[str, Any]] = None,
    rp2040_fixture_config: Optional[Mapping[str, Any]] = None,
    p1_capsule_info: Optional[Mapping[str, Any]] = None,
    ram_shadow_bk4_info: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a complete Stage-B H0 or H2 capture bundle passing `verify_real_tier0_capture_bundle`
    plus all Stage-B C2PA/SPACC/CP/exFAT/p1-capsule/RP2040/serial/thermal forensic probes.
    """
    bdir = Path(bundle_dir)
    bdir.mkdir(parents=True, exist_ok=True)

    tbl = fa0080_table if fa0080_table is not None else build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None)
    stock_bk4 = bk4_bytes if bk4_bytes is not None else build_persistent_stock_bk4_bytes(fa0080_table=tbl)

    sec0_bytes = _build_valid_fx3_sector0_bytes()
    p1_prefix = _build_valid_fat16_p1_header_prefix(25_100_288)
    size_and_headers: Dict[str, Tuple[int, bytes]] = {
        "sector0": (512, sec0_bytes),
        "boot0": (131_072, b"BOOT0_FX3_LDR\x00"),
        "boot1": (131_072, b"BOOT1_FX3_LDR\x00"),
        "p1_updater": (25_100_288, p1_prefix),
        "p2_backup_bin": (262_144, stock_bk4),
        "p2_psd_bin": (4_096, b"PSD_CAL_V1\x00"),
        "p2_defdet_bin": (4_096, b"DEFDET_CAL_V1\x00"),
        "p6_jiritsu": (26_214_400, b"JIRITSU_EXT2_RO\x00"),
        "p12_cert": (20_971_520, b"SONY_CERT_RO\x00"),
        "p18_lensfile": (4_096, b"LENSFILE_MOUNT_CAL\x00"),
        "spi_nor_ddrtraining": (8_192, b"DDRTRAINING_NOR\x00"),
    }

    items_manifest: Dict[str, Dict[str, Any]] = {}
    for key in TIER0_REQUIRED_BACKUPS:
        fn = str(TIER0_CANONICAL_SOURCES[key]["output_name"])
        total_sz, hdr = size_and_headers[key]
        fpath = bdir / fn
        _write_patterned_file(fpath, total_sz, hdr, f"FX3_STAGE_B_{key}_".encode("ascii"))
        sz, sha = _hash_single_file_o_rdonly(fpath)
        items_manifest[key] = {
            "file_name": fn,
            "source_path": str(TIER0_CANONICAL_SOURCES[key]["source_path"]),
            "bytes": sz,
            "pass1_sha256": sha,
            "pass2_sha256": sha,
        }

    redlines_manifest: Dict[str, Dict[str, Any]] = {}
    for probe_key, fn in REQUIRED_REDLINE_HEADER_PROBES.items():
        raw = _build_valid_p8_tomco_bytes() if probe_key == "p8_tomco_txt" else _build_valid_p5_wbi2_header_bytes()
        fpath = bdir / fn
        fpath.write_bytes(raw)
        sz, sha = _hash_single_file_o_rdonly(fpath)
        entry: Dict[str, Any] = {
            "file_name": fn,
            "source_path": "/cp/tomco.txt" if probe_key == "p8_tomco_txt" else "/dev/nflasha5",
            "bytes": sz,
            "pass1_sha256": sha,
            "pass2_sha256": sha,
        }
        if probe_key == "p5_wbi_header":
            entry["partition_image_bytes"] = 202_677_056
        redlines_manifest[probe_key] = entry

    # Stage-B forensic binary probes (`p8_cp_image`, `c2pa_rq_lic`, `spacc_cnflasha`)
    stage_b_probe_blobs: Dict[str, bytes] = {
        "p8_cp_image": _build_synthetic_p8_cp_image_bytes(8192),
        "c2pa_rq_lic": _build_synthetic_c2pa_rq_lic_bytes(4096),
        "spacc_cnflasha": build_synthetic_encrypted_cnflasha(size=32768),
    }
    stage_b_manifest: Dict[str, Dict[str, Any]] = {}
    for probe_key, fn in STAGE_B_FORENSIC_PROBE_DEFAULTS.items():
        raw = stage_b_probe_blobs[probe_key]
        fpath = bdir / fn
        fpath.write_bytes(raw)
        sz, sha = _hash_single_file_o_rdonly(fpath)
        stage_b_manifest[probe_key] = {
            "file_name": fn,
            "bytes": sz,
            "pass1_sha256": sha,
            "pass2_sha256": sha,
        }

    # exFAT lab media boot region + tree
    exfat_raw = exfat_boot_bytes if exfat_boot_bytes is not None else build_synthetic_exfat_boot_region()
    (bdir / "exfat_slot_a_vbr.bin").write_bytes(exfat_raw)
    tree_entries = list(exfat_card_entries) if exfat_card_entries is not None else []
    (bdir / "exfat_slot_a_tree.json").write_text(
        json.dumps({"slot_id": "SLOT_A", "dedicated_lab_card": True, "entries": tree_entries}, indent=2) + "\n",
        encoding="utf-8",
    )

    # p1 one-shot boot-counter & rollback capsule state
    cap_sha = hashlib.sha256(b"fx3-p1-fat12-rollback-capsule-v702").hexdigest()
    cap_info = dict(
        p1_capsule_info
        or {
            "boot_attempts": 0,
            "mod_arm_once_present": False,
            "capsule_sha256": cap_sha,
            "expected_capsule_sha256": cap_sha,
            "fsync_order": list(REQUIRED_FSYNC_ORDER),
            "allow_boot_partition_targeting": False,
            "emmc_write_bytes": 0,
        }
    )
    (bdir / "p1_rollback_capsule.json").write_text(json.dumps(cap_info, indent=2) + "\n", encoding="utf-8")

    # RP2040 fixture state
    rp_cfg = dict(
        rp2040_fixture_config
        or {
            "board": "waveshare_rp2040_zero",
            "open_drain": True,
            "gpio_drive_mode": "open_drain",
            "io_voltage_v": 1.8,
            "baud_rate": UART_BOOT_BAUD,
            "gnd_connected": True,
            "ltc_cable_connected": False,
        }
    )
    (bdir / "rp2040_fixture_state.json").write_text(json.dumps(rp_cfg, indent=2) + "\n", encoding="utf-8")

    # Session serial log & thermal/power telemetry
    s_log = serial_log_text if serial_log_text is not None else _build_clean_stage_b_serial_log()
    (bdir / "stage_b_session_serial.log").write_text(s_log, encoding="utf-8")

    tp_cfg = dict(
        thermal_power_telemetry
        or {
            "peak_soc_c": 58.4,
            "peak_cfexpress_c": 54.0,
            "thermal_emergency_teardown_triggered": False,
            "npfz100_soc_pct": 86,
            "usbpd_contract_mw": USBPD_REQUIRED_POWER_MW,
            "persistent_emmc_writes_authorized": False,
            "persistent_write_release": False,
        }
    )
    (bdir / "stage_b_thermal_power.json").write_text(json.dumps(tp_cfg, indent=2) + "\n", encoding="utf-8")

    ram_shadow_meta = dict(
        ram_shadow_bk4_info
        or {
            "ram_shadow_only": True,
            "target_path": "/tmp/bk4_shadow",
            "lang": "schinese",
            "bk_lang_hex": f"0x{STAGE_B_BK_LANG_SPECS['schinese'].bk_lang_value:02x}",
            "airplane_keys": {f"0x{k:08x}": f"{v:02x}" for k, v in STAGE_B_AIRPLANE_KEYS.items()},
        }
    )
    (bdir / "stage_b_ram_shadow_meta.json").write_text(
        json.dumps(ram_shadow_meta, indent=2) + "\n", encoding="utf-8"
    )

    tag = hashlib.sha256(f"FX3:{body_serial}:{emmc_cid}".encode("utf-8")).hexdigest()
    manifest: Dict[str, Any] = {
        "schema": "fx3-tier0-hardware-backup-manifest-v1",
        "capture_origin": "physical_fx3_hardware",
        "model_id": FX3_MODEL_ID_HEX,
        "camera_body_tag": tag,
        "body_serial": body_serial,
        "cid": emmc_cid,
        "items": items_manifest,
        "redline_headers": redlines_manifest,
        "stage_b_forensic_probes": stage_b_manifest,
    }
    (bdir / "backup-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Sub-Auditors (BK4 NVRAM, C2PA/SPACC/Calibration, p1+exFAT, RP2040+Serial+Thermal)
# ---------------------------------------------------------------------------


def _audit_stage_b_bk4_nvram_zero_drift(
    h0_dir: Path,
    h2_dir: Path,
    h0_manifest: Mapping[str, Any],
    h2_manifest: Mapping[str, Any],
    p2_parity: StageBPostTrialItemParity,
    ram_shadow_bk4_info: Optional[Mapping[str, Any]],
) -> StageBBk4NvramZeroDriftAudit:
    errors: List[str] = []
    p2_fn0 = _resolve_item_filename(
        h0_manifest, "items", "p2_backup_bin", str(TIER0_CANONICAL_SOURCES["p2_backup_bin"]["output_name"])
    )
    p2_fn2 = _resolve_item_filename(
        h2_manifest, "items", "p2_backup_bin", str(TIER0_CANONICAL_SOURCES["p2_backup_bin"]["output_name"])
    )
    p2_p0 = h0_dir / p2_fn0
    p2_p2 = h2_dir / p2_fn2

    h0_bk4_bytes = _read_file_o_rdonly(p2_p0) if p2_p0.is_file() and not p2_p0.is_symlink() else b""
    h2_bk4_bytes = _read_file_o_rdonly(p2_p2) if p2_p2.is_file() and not p2_p2.is_symlink() else b""

    byte8_val: Optional[int] = None
    byte8_ok = False
    if len(h2_bk4_bytes) >= BK4_HEADER_SIZE and h2_bk4_bytes[0x0C:0x10] == BK4_MAGIC:
        byte8_val = int(h2_bk4_bytes[0x08])
        rec0, rec0_errs = parse_bk4_record(h2_bk4_bytes, offset=0, record_index=0)
        if rec0 is None or rec0_errs:
            errors.append(f"U5 H2 p2_backup_bin Record 0 invalid: {rec0_errs}")
        elif rec0.active_byte8 != 0x00:
            errors.append(
                f"U5 sticky boot_img violation: H2 p2_backup_bin byte +8 == 0x{rec0.active_byte8:02x} (expected 0x00)"
            )
        else:
            rec1_bad = False
            next_off = rec0.total_bytes
            if next_off + BK4_HEADER_SIZE <= len(h2_bk4_bytes) and h2_bk4_bytes[next_off + 0x0C : next_off + 0x10] == BK4_MAGIC:
                rec1_b8 = int(h2_bk4_bytes[next_off + 0x08])
                if rec1_b8 != 0x00:
                    byte8_val = rec1_b8
                    rec1_bad = True
                    errors.append(
                        f"U5 sticky boot_img violation: H2 p2_backup_bin Record 1 byte +8 == 0x{rec1_b8:02x} (expected 0x00)"
                    )
            if not rec1_bad:
                byte8_ok = True
    else:
        errors.append("U5 H2 p2_backup_bin missing valid BK4 header at Record 0")

    # Sticky /setting/updater/mode* residue check
    residue: List[str] = []
    if h2_dir.exists() and not h2_dir.is_symlink() and h2_dir.is_dir():
        for root, _dirs, files in os.walk(h2_dir, followlinks=False):
            root_p = Path(root)
            for fname in sorted(files):
                rel = (root_p / fname).relative_to(h2_dir).as_posix()
                if STICKY_UPDATER_RELPATH_RE.search(rel):
                    residue.append(rel)
    for mkey in ("sticky_updater_mode_files", "setting_updater_mode_files"):
        mval = h2_manifest.get(mkey)
        if isinstance(mval, list):
            for item in mval:
                s = str(item).strip()
                if s and s not in residue:
                    residue.append(s)
    residue_sorted = tuple(sorted(residue))
    zero_residue_ok = len(residue_sorted) == 0
    if not zero_residue_ok:
        errors.append(f"U5 sticky updater mode residue detected in H2: {list(residue_sorted)!r}")

    # Persistent Airplane-Mode keys & BK_LANG key parity (H0 vs H2)
    airplane_unchanged = True
    for k_id in (BT_BKID_ENABLE_PRIMARY, BT_BKID_ENABLE_SECONDARY, BT_BKID_RSRC_MODE):
        v0 = read_bk4_property_bytes(h0_bk4_bytes, k_id, offset=0)
        v2 = read_bk4_property_bytes(h2_bk4_bytes, k_id, offset=0)
        if v0 != v2:
            airplane_unchanged = False
            v0_h = v0.hex() if v0 is not None else "missing"
            v2_h = v2.hex() if v2 is not None else "missing"
            errors.append(
                f"Persistent BK4 Airplane-Mode key 0x{k_id:08x} drifted between H0 ({v0_h}) and H2 ({v2_h})"
            )

    lang0 = read_bk4_property_bytes(h0_bk4_bytes, BK_KEY_LANG, offset=0)
    lang2 = read_bk4_property_bytes(h2_bk4_bytes, BK_KEY_LANG, offset=0)
    bk_lang_unchanged = lang0 == lang2
    if not bk_lang_unchanged:
        l0_h = lang0.hex() if lang0 is not None else "missing"
        l2_h = lang2.hex() if lang2 is not None else "missing"
        errors.append(
            f"Persistent BK4 BK_LANG (0x{BK_KEY_LANG:08x}) drifted between H0 ({l0_h}) and H2 ({l2_h})"
        )

    ram_meta = (
        dict(ram_shadow_bk4_info)
        if ram_shadow_bk4_info is not None
        else _load_json_o_rdonly(h2_dir / "stage_b_ram_shadow_meta.json")
    )
    ram_shadow_only = bool(ram_meta.get("ram_shadow_only", True)) and (ram_meta.get("target_path", "/tmp/bk4_shadow") == "/tmp/bk4_shadow")
    if not ram_shadow_only:
        errors.append("Stage-B BK4 shadow metadata indicates non-RAM target path")

    ram_lang = str(ram_meta.get("lang", "schinese"))
    raw_ap_keys = ram_meta.get("airplane_keys")
    if isinstance(raw_ap_keys, Mapping):
        ram_ap_keys = {str(k): str(v) for k, v in raw_ap_keys.items()}
    else:
        ram_ap_keys = {f"0x{k:08x}": f"{v:02x}" for k, v in STAGE_B_AIRPLANE_KEYS.items()}

    bk4_mut_bytes = p2_parity.differing_bytes if p2_parity.bit_exact_match is False else 0
    if not p2_parity.bit_exact_match and bk4_mut_bytes == 0:
        bk4_mut_bytes = 1

    valid = (
        p2_parity.bit_exact_match
        and bk4_mut_bytes == 0
        and byte8_ok
        and zero_residue_ok
        and airplane_unchanged
        and bk_lang_unchanged
        and ram_shadow_only
        and len(errors) == 0
    )
    return StageBBk4NvramZeroDriftAudit(
        valid=valid,
        h0_bk4_sha256=p2_parity.h0_sha256,
        h2_bk4_sha256=p2_parity.h2_sha256,
        bk4_bit_exact_match=p2_parity.bit_exact_match,
        bk4_mutated_bytes=bk4_mut_bytes,
        u5_boot_img_byte8_zero_ok=byte8_ok,
        h2_bk4_byte8=byte8_val,
        u5_zero_updater_mode_residue_ok=zero_residue_ok,
        sticky_updater_residue=residue_sorted,
        persistent_airplane_keys_unchanged=airplane_unchanged,
        persistent_bk_lang_unchanged=bk_lang_unchanged,
        ram_shadow_bk4_only=ram_shadow_only,
        ram_shadow_bk_lang=ram_lang,
        ram_shadow_airplane_keys=ram_ap_keys,
        errors=tuple(errors),
    )


def _audit_c2pa_spacc_and_calibration(
    parity_by_id: Mapping[str, StageBPostTrialItemParity],
    *,
    c2pa_keystore_writes_attempted: bool = False,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
) -> StageBC2paSpaccCalibrationAudit:
    errors: List[str] = []
    drifted: List[str] = []
    cal_mut_bytes = 0

    for item_id in STAGE_B_CALIBRATION_ITEM_IDS:
        rec = parity_by_id.get(item_id)
        if rec is None:
            drifted.append(item_id)
            cal_mut_bytes += 1
            errors.append(f"Missing C2PA/SPACC/calibration parity record for {item_id}")
            continue
        if not rec.bit_exact_match:
            drifted.append(item_id)
            cal_mut_bytes += rec.differing_bytes if rec.differing_bytes > 0 else 1
            errors.append(
                f"C2PA/SPACC/calibration drift on {item_id}: h0={rec.h0_sha256[:16]}... "
                f"vs h2={rec.h2_sha256[:16]}..., diff_bytes={rec.differing_bytes}"
            )

    c2pa_rec = parity_by_id.get("c2pa_rq_lic")
    p12_rec = parity_by_id.get("p12_cert")
    spacc_rec = parity_by_id.get("spacc_cnflasha")

    g15_res = verify_c2pa_and_factory_calibration_immutability(
        planned_mounts=planned_mounts,
        planned_writes=planned_writes,
        calibration_mutation_bytes=cal_mut_bytes,
        c2pa_keystore_writes_attempted=c2pa_keystore_writes_attempted,
    )
    if not g15_res.valid:
        errors.extend(g15_res.errors)

    c2pa_untouched = (
        c2pa_rec is not None
        and c2pa_rec.bit_exact_match
        and p12_rec is not None
        and p12_rec.bit_exact_match
        and not c2pa_keystore_writes_attempted
        and g15_res.trustzone_c2pa_keystore_protected
    )
    spacc_untouched = (
        spacc_rec is not None
        and spacc_rec.bit_exact_match
        and g15_res.cnflasha_protected
    )

    valid = (
        cal_mut_bytes == 0
        and len(drifted) == 0
        and c2pa_untouched
        and spacc_untouched
        and g15_res.valid
        and len(errors) == 0
    )
    return StageBC2paSpaccCalibrationAudit(
        valid=valid,
        calibration_mutation_bytes=cal_mut_bytes,
        c2pa_keystore_untouched=c2pa_untouched,
        spacc_cnflasha_untouched=spacc_untouched,
        c2pa_rq_lic_h0_sha256=c2pa_rec.h0_sha256 if c2pa_rec else "",
        c2pa_rq_lic_h2_sha256=c2pa_rec.h2_sha256 if c2pa_rec else "",
        spacc_cnflasha_h0_sha256=spacc_rec.h0_sha256 if spacc_rec else "",
        spacc_cnflasha_h2_sha256=spacc_rec.h2_sha256 if spacc_rec else "",
        audited_calibration_items=STAGE_B_CALIBRATION_ITEM_IDS,
        drifted_calibration_items=tuple(drifted),
        errors=tuple(errors),
    )


def _audit_p1_capsule_and_exfat_media(
    h2_dir: Path,
    h2_manifest: Mapping[str, Any],
    *,
    exfat_boot_bytes: Optional[bytes] = None,
    exfat_card_entries: Optional[Sequence[Union[str, Tuple[str, int], Mapping[str, Any]]]] = None,
    p1_capsule_info: Optional[Mapping[str, Any]] = None,
) -> StageBP1CapsuleAndExfatAudit:
    errors: List[str] = []

    # 1. p1 VFAT header + FAT12/FAT16 separation
    p1_fn = _resolve_item_filename(
        h2_manifest, "items", "p1_updater", str(TIER0_CANONICAL_SOURCES["p1_updater"]["output_name"])
    )
    p1_path = h2_dir / p1_fn
    p1_vfat_ok = False
    p1_vfat_type = "MISSING"
    if p1_path.is_file() and not p1_path.is_symlink():
        p1_audit = audit_p1_vfat_header(p1_path)
        p1_vbr_bytes = _read_slice_o_rdonly(p1_path, 0, 512)
        p1_sep_vbr = parse_p1_fat12_fat16_vbr(p1_vbr_bytes)
        p1_vfat_type = p1_audit.fat_type
        p1_vfat_ok = p1_audit.valid and p1_sep_vbr.valid and not p1_sep_vbr.is_exfat_spoofed
        if not p1_audit.valid:
            errors.extend(f"p1_vfat: {e}" for e in p1_audit.errors)
        if not p1_sep_vbr.valid:
            errors.extend(f"p1_vbr: {e}" for e in p1_sep_vbr.errors)
    else:
        errors.append(f"Missing H2 p1_updater image {p1_fn}")

    # 2. p1 one-shot boot-counter & rollback capsule state
    cap_data = (
        dict(p1_capsule_info)
        if p1_capsule_info is not None
        else _load_json_o_rdonly(h2_dir / "p1_rollback_capsule.json")
    )
    boot_attempts = int(cap_data.get("boot_attempts", -1)) if cap_data else -1
    mod_arm_present = bool(cap_data.get("mod_arm_once_present", True)) if cap_data else True
    cap_sha = str(cap_data.get("capsule_sha256", ""))
    exp_cap_sha = str(cap_data.get("expected_capsule_sha256", ""))
    fsync_raw = cap_data.get("fsync_order", ())
    fsync_ok, fsync_msg = audit_capsule_fsync_order(
        tuple(str(x) for x in fsync_raw) if isinstance(fsync_raw, (list, tuple)) else ()
    )
    if not fsync_ok:
        errors.append(f"p1 rollback capsule: {fsync_msg}")
    if bool(cap_data.get("allow_boot_partition_targeting", False)):
        errors.append("p1 rollback capsule allow_boot_partition_targeting must remain False")
    if int(cap_data.get("emmc_write_bytes", 0)) != 0:
        errors.append(f"p1 rollback capsule reported non-zero emmc_write_bytes={cap_data.get('emmc_write_bytes')}")

    cap_sha_ok = bool(HEX64_RE.fullmatch(cap_sha)) and cap_sha == exp_cap_sha
    if not cap_sha_ok:
        errors.append("p1 rollback capsule SHA-256 missing or mismatched")

    oneshot_clean = (
        boot_attempts == 0
        and (not mod_arm_present)
        and cap_sha_ok
        and not bool(cap_data.get("allow_boot_partition_targeting", False))
        and int(cap_data.get("emmc_write_bytes", 0)) == 0
    )
    if boot_attempts != 0 or mod_arm_present:
        errors.append(
            f"p1 one-shot boot counter not clean post-reboot: boot_attempts={boot_attempts}, mod_arm_once_present={mod_arm_present}"
        )

    # 3. exFAT Boot Region (VolumeDirty == 0, MediaFailure == 0, BootChecksum valid)
    vbr_path = h2_dir / "exfat_slot_a_vbr.bin"
    raw_exfat = exfat_boot_bytes
    if raw_exfat is None and vbr_path.is_file() and not vbr_path.is_symlink():
        raw_exfat = _read_file_o_rdonly(vbr_path)

    if raw_exfat is None:
        errors.append("Missing H2 exFAT lab media boot region (exfat_slot_a_vbr.bin)")
        exfat_vbr_valid = False
        exfat_chk_ok = False
        exfat_dirty = True
        exfat_fail = True
    else:
        ex_audit = verify_exfat_boot_region(raw_exfat, require_backup_region=True, allow_volume_dirty=False)
        exfat_vbr_valid = ex_audit.valid
        exfat_chk_ok = ex_audit.main_checksum_ok and (ex_audit.backup_checksum_ok is not False)
        exfat_dirty = ex_audit.volume_dirty
        exfat_fail = ex_audit.media_failure
        if not ex_audit.valid:
            errors.extend(f"exFAT VBR: {e}" for e in ex_audit.errors)

    # 4. exFAT Sony Media Tree (zero .RSV, zero .CHK, clean lab card)
    tree_path = h2_dir / "exfat_slot_a_tree.json"
    if exfat_card_entries is not None:
        tree_entries: Sequence[Union[str, Tuple[str, int], Mapping[str, Any]]] = exfat_card_entries
        tree_found = True
    elif tree_path.is_file() and not tree_path.is_symlink():
        tree_obj = _load_json_o_rdonly(tree_path)
        raw_entries = tree_obj.get("entries", [])
        tree_entries = raw_entries if isinstance(raw_entries, list) else []
        tree_found = isinstance(raw_entries, list)
    else:
        tree_entries = ()
        tree_found = False

    if not tree_found:
        errors.append("Missing H2 exFAT media tree manifest (exfat_slot_a_tree.json)")
        rsv_files: Tuple[str, ...] = ()
        chk_files: Tuple[str, ...] = ()
        tree_clean = False
    else:
        tree_audit = inspect_sony_media_tree(entries=tree_entries)
        rsv_files = tree_audit.unfinalized_rsv_files
        chk_files = tree_audit.chkdsk_chk_files
        tree_clean = tree_audit.valid and tree_audit.is_clean_lab_media and len(rsv_files) == 0 and len(chk_files) == 0
        if not tree_clean:
            errors.extend(f"exFAT media tree: {e}" for e in tree_audit.errors)

    exfat_clean = exfat_vbr_valid and exfat_chk_ok and (not exfat_dirty) and (not exfat_fail) and tree_clean
    valid = p1_vfat_ok and oneshot_clean and fsync_ok and exfat_clean and len(errors) == 0

    return StageBP1CapsuleAndExfatAudit(
        valid=valid,
        p1_vfat_valid=p1_vfat_ok,
        p1_vfat_type=p1_vfat_type,
        p1_oneshot_boot_counter_clean=oneshot_clean,
        p1_boot_attempts_observed=boot_attempts,
        p1_capsule_sha256=cap_sha,
        p1_capsule_fsync_order_ok=fsync_ok,
        exfat_vbr_valid=exfat_vbr_valid,
        exfat_boot_checksum_ok=exfat_chk_ok,
        exfat_volume_dirty=exfat_dirty,
        exfat_media_failure=exfat_fail,
        exfat_rsv_files=rsv_files,
        exfat_chk_files=chk_files,
        exfat_media_clean=exfat_clean,
        errors=tuple(errors),
    )


def _audit_rp2040_and_serial_thermal_post_mortem(
    h2_dir: Path,
    *,
    serial_log_text: Optional[str] = None,
    serial_log_path: Optional[Path | str] = None,
    thermal_power_telemetry: Optional[Mapping[str, Any]] = None,
    rp2040_fixture_config: Optional[Mapping[str, Any]] = None,
) -> StageBRp2040AndSerialThermalPostMortem:
    errors: List[str] = []

    # 1. RP2040 Multi-Port Fixture Post-Trial Safety State
    rp_cfg = (
        dict(rp2040_fixture_config)
        if rp2040_fixture_config is not None
        else _load_json_o_rdonly(h2_dir / "rp2040_fixture_state.json")
    )
    if not rp_cfg:
        errors.append("Missing RP2040 fixture state (rp2040_fixture_state.json)")
        rp_safe = False
        rp_board = "MISSING"
        rp_od = False
        rp_v = 0.0
        rp_baud = 0
    else:
        ltc_connected = bool(rp_cfg.get("ltc_cable_connected", False))
        harness_res = validate_rp2040_multiport_harness(
            board=str(rp_cfg.get("board", "waveshare_rp2040_zero")),
            open_drain=bool(rp_cfg.get("open_drain", False)),
            gpio_drive_mode=str(rp_cfg.get("gpio_drive_mode", "open_drain")),
            io_voltage_v=float(rp_cfg.get("io_voltage_v", 0.0)),
            baud_rate=int(rp_cfg.get("baud_rate", 0)),
            gnd_connected=bool(rp_cfg.get("gnd_connected", True)),
        )
        rp_safe = harness_res.valid and (not ltc_connected)
        rp_board = harness_res.board
        rp_od = harness_res.open_drain_enforced
        rp_v = harness_res.io_voltage_v
        rp_baud = harness_res.baud_rate
        if not harness_res.valid:
            errors.extend(f"RP2040 fixture: {e}" for e in harness_res.errors)
        if ltc_connected:
            errors.append("RP2040 fixture violation: VMC-BNCM1 LTC cable connected alongside Multi-Port UART")

    # 2. serial_fault_detector_v2 Post-Mortem
    raw_serial: Optional[str] = serial_log_text
    if raw_serial is None:
        s_path = Path(serial_log_path) if serial_log_path is not None else (h2_dir / "stage_b_session_serial.log")
        if s_path.is_file() and not s_path.is_symlink():
            raw_serial = _read_file_o_rdonly(s_path).decode("utf-8", errors="replace")

    if not raw_serial or not raw_serial.strip():
        errors.append("Missing Stage-B session serial telemetry log")
        s_passed = False
        s_disp = "MISSING"
        wdt_ok = False
        wf12_hang = False
        panic_13s = False
    else:
        s_rep = audit_serial_boot_telemetry(
            serial_text=raw_serial,
            native_faithful_mode=True,
            require_wdt_budget_proof=True,
            source_label="stage_b_post_trial",
        )
        s_passed = bool(s_rep.passed and s_rep.disposition == DISPOSITION_PASS)
        s_disp = s_rep.disposition
        wdt_ok = bool(s_rep.watchdog_budget.passed)
        if not s_passed:
            errors.extend(f"serial_fault_detector_v2: {e}" for e in (s_rep.errors or ("Serial fault detector did not return PASS",)))
            for f in s_rep.findings:
                errors.append(f"serial_fault[{f.code}]: {f.message}")
        if not wdt_ok:
            errors.extend(f"watchdog_budget: {e}" for e in s_rep.watchdog_budget.errors)

        # Explicit 00342260 (WF-12) wireless hang & 0x100D (13S) panic detectors
        wf12_hang = bool(_WF12_00342260_RE.search(raw_serial)) or any(
            f.code in ("WLAN_RESOURCE_0x70D4_HANG", "SYSTEM_ERROR_ABORT") for f in s_rep.findings
        ) or any(e.code == "WF12_DEGRADED_RADIO_OFF" for e in s_rep.degraded_events)
        if wf12_hang:
            errors.append("Post-trial serial log contains 00342260 (WF-12) wireless malfunction / hang signature")

        panic_13s = bool(_PANIC_0x100D_13S_RE.search(raw_serial)) or any(
            "0x100D" in str(f.code) or "0x100D" in str(f.brick_playbook_key or "") for f in s_rep.findings
        )
        if panic_13s:
            errors.append("Post-trial serial log contains 0x100D (13S) BootROM/UART panic signature")

    # 3. Thermal & Power Session Post-Mortem
    tp_data = (
        dict(thermal_power_telemetry)
        if thermal_power_telemetry is not None
        else _load_json_o_rdonly(h2_dir / "stage_b_thermal_power.json")
    )
    if not tp_data:
        errors.append("Missing Stage-B thermal/power session telemetry (stage_b_thermal_power.json)")
        peak_soc = 999.0
        thermal_under_90 = False
        emergency_teardown = True
        soc_pct = 0
        usbpd_mw = 0
    else:
        peak_soc = float(tp_data.get("peak_soc_c", 999.0))
        peak_cf = float(tp_data.get("peak_cfexpress_c", 0.0))
        emergency_teardown = bool(tp_data.get("thermal_emergency_teardown_triggered", False))
        soc_pct = int(tp_data.get("npfz100_soc_pct", 0))
        usbpd_mw = int(tp_data.get("usbpd_contract_mw", 0))
        thermal_under_90 = (
            peak_soc < FAIL_CLOSED_TEARDOWN_TEMP_C
            and peak_cf < FAIL_CLOSED_TEARDOWN_TEMP_C
            and (not emergency_teardown)
        )
        if not thermal_under_90:
            errors.append(
                f"Thermal runaway / >=90C emergency teardown in session log: "
                f"peak_soc_c={peak_soc:.1f}C, peak_cfexpress_c={peak_cf:.1f}C, "
                f"emergency_teardown={emergency_teardown}"
            )
        if soc_pct < H0_H1_REHEARSAL_MIN_SOC_PCT:
            errors.append(f"NP-FZ100 session SOC {soc_pct}% < {H0_H1_REHEARSAL_MIN_SOC_PCT}% minimum")
        if usbpd_mw < USBPD_REQUIRED_POWER_MW:
            errors.append(f"USB-PD contract {usbpd_mw} mW < {USBPD_REQUIRED_POWER_MW} mW (9V/3A)")
        if tp_data.get("persistent_emmc_writes_authorized") is True or tp_data.get("persistent_write_release") is True:
            errors.append("Session telemetry attempted to authorize persistent eMMC writes (hard-locked False)")

    valid = (
        rp_safe
        and s_passed
        and wdt_ok
        and (not wf12_hang)
        and (not panic_13s)
        and thermal_under_90
        and soc_pct >= H0_H1_REHEARSAL_MIN_SOC_PCT
        and usbpd_mw >= USBPD_REQUIRED_POWER_MW
        and len(errors) == 0
    )
    return StageBRp2040AndSerialThermalPostMortem(
        valid=valid,
        rp2040_fixture_safe=rp_safe,
        rp2040_board=rp_board,
        rp2040_open_drain_enforced=rp_od,
        rp2040_io_voltage_v=rp_v,
        rp2040_baud_rate=rp_baud,
        serial_detector_v2_passed=s_passed,
        serial_detector_disposition=s_disp,
        watchdog_budget_passed=wdt_ok,
        wf12_00342260_hang_detected=wf12_hang,
        panic_0x100d_13s_detected=panic_13s,
        peak_soc_c=peak_soc,
        thermal_under_90c_ok=thermal_under_90,
        thermal_emergency_teardown_triggered=emergency_teardown,
        npfz100_soc_pct=soc_pct,
        usbpd_contract_mw=usbpd_mw,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Primary Post-Trial Zero-Persistence Verifier (H0 vs H2)
# ---------------------------------------------------------------------------


def verify_stage_b_post_trial_zero_persistence(
    h0_bundle_dir: Path | str,
    h2_bundle_dir: Path | str,
    *,
    serial_log_text: Optional[str] = None,
    serial_log_path: Optional[Path | str] = None,
    thermal_power_telemetry: Optional[Mapping[str, Any]] = None,
    exfat_boot_bytes: Optional[bytes] = None,
    exfat_card_entries: Optional[Sequence[Union[str, Tuple[str, int], Mapping[str, Any]]]] = None,
    rp2040_fixture_config: Optional[Mapping[str, Any]] = None,
    p1_capsule_info: Optional[Mapping[str, Any]] = None,
    ram_shadow_bk4_info: Optional[Mapping[str, Any]] = None,
    c2pa_keystore_writes_attempted: bool = False,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    synthetic_clean_room: Optional[bool] = None,
    _preverified_h0_audit: Optional[RealTier0CaptureBundleAudit] = None,
    _preverified_h2_audit: Optional[RealTier0CaptureBundleAudit] = None,
) -> StageBPostTrialReceipt:
    """Verify full Stage-B post-power-cycle zero-persistence parity between Phase H0 and Phase H2."""
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR, fx3_modules_dir=DEFAULT_FX3_MODULES_DIR)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    h0_dir = Path(h0_bundle_dir)
    h2_dir = Path(h2_bundle_dir)
    errors: List[str] = []
    anomaly_codes: List[str] = []

    distinct_dirs_ok = True
    if h0_dir.exists() and h2_dir.exists():
        if h0_dir.resolve() == h2_dir.resolve():
            distinct_dirs_ok = False
            _add_code(anomaly_codes, ANOMALY_SYNTHETIC_OR_INVALID_BUNDLE)
            errors.append(
                "h0_bundle_dir and h2_bundle_dir resolve to the identical directory; "
                "Phase H2 must be an independent post-power-cycle readback capture"
            )

    # 1. Validate BOTH H0 and H2 bundles via `verify_real_tier0_capture_bundle`
    h0_audit = (
        _preverified_h0_audit
        if _preverified_h0_audit is not None
        else verify_real_tier0_capture_bundle(h0_dir)
    )
    h2_audit = (
        _preverified_h2_audit
        if _preverified_h2_audit is not None
        else verify_real_tier0_capture_bundle(h2_dir)
    )
    if not h0_audit.valid:
        errors.extend(f"h0-bundle: {e}" for e in h0_audit.errors)
    if not h2_audit.valid:
        errors.extend(f"h2-bundle: {e}" for e in h2_audit.errors)

    both_real_valid = (
        h0_audit.valid
        and h0_audit.is_non_synthetic_hardware
        and h2_audit.valid
        and h2_audit.is_non_synthetic_hardware
    )
    if not both_real_valid:
        _add_code(anomaly_codes, ANOMALY_SYNTHETIC_OR_INVALID_BUNDLE)

    # 2. Same-body hardware identity check
    same_body_ok = (
        h0_audit.is_non_synthetic_hardware
        and h2_audit.is_non_synthetic_hardware
        and h0_audit.model_id == FX3_MODEL_ID_HEX
        and h2_audit.model_id == FX3_MODEL_ID_HEX
        and bool(h0_audit.body_serial)
        and h0_audit.body_serial == h2_audit.body_serial
        and bool(h0_audit.emmc_cid)
        and h0_audit.emmc_cid.lower() == h2_audit.emmc_cid.lower()
        and bool(h0_audit.camera_body_tag)
        and h0_audit.camera_body_tag == h2_audit.camera_body_tag
    )
    if not same_body_ok:
        _add_code(anomaly_codes, ANOMALY_SAME_BODY_IDENTITY_MISMATCH)
        if h0_audit.body_serial != h2_audit.body_serial:
            errors.append(
                f"Same-body serial mismatch: H0={h0_audit.body_serial!r} vs H2={h2_audit.body_serial!r}"
            )
        if h0_audit.emmc_cid.lower() != h2_audit.emmc_cid.lower():
            errors.append(
                f"Same-body eMMC CID mismatch: H0={h0_audit.emmc_cid!r} vs H2={h2_audit.emmc_cid!r}"
            )

    # 3. Stream-compare all 11 Tier-0 + 2 redline + 3 Stage-B forensic probes (16 total) via O_RDONLY
    h0_manifest = _load_json_o_rdonly(h0_dir / "backup-manifest.json")
    h2_manifest = _load_json_o_rdonly(h2_dir / "backup-manifest.json")

    audited_specs: List[Tuple[str, str, str, str]] = [
        (key, "tier0_partition", "items", str(TIER0_CANONICAL_SOURCES[key]["output_name"]))
        for key in TIER0_REQUIRED_BACKUPS
    ] + [
        (probe_key, "redline_header_probe", "redline_headers", default_fn)
        for probe_key, default_fn in REQUIRED_REDLINE_HEADER_PROBES.items()
    ] + [
        (
            probe_key,
            "stage_b_cp_image" if probe_key == "p8_cp_image" else "c2pa_spacc_calibration",
            "stage_b_forensic_probes",
            default_fn,
        )
        for probe_key, default_fn in STAGE_B_FORENSIC_PROBE_DEFAULTS.items()
    ]

    comparisons: List[StageBPostTrialItemParity] = []
    parity_by_id: Dict[str, StageBPostTrialItemParity] = {}
    drifted: List[str] = []
    total_mutated_bytes = 0

    for item_id, category, sec_name, default_fn in audited_specs:
        fn0 = _resolve_item_filename(h0_manifest, sec_name, item_id, default_fn)
        fn2 = _resolve_item_filename(h2_manifest, sec_name, item_id, default_fn)
        p0 = (h0_dir / fn0) if h0_dir.is_dir() and not h0_dir.is_symlink() else None
        p2 = (h2_dir / fn2) if h2_dir.is_dir() and not h2_dir.is_symlink() else None

        sz0, sz2, sha0, sha2, diff_b = _stream_compare_two_files_o_rdonly(p0, p2)
        matched = sz0 > 0 and sz0 == sz2 and bool(sha0) and sha0 == sha2 and diff_b == 0
        if sec_name == "stage_b_forensic_probes":
            # Also require explicit manifest two-pass parity for Stage-B probes
            for m_label, m_obj in (("H0", h0_manifest), ("H2", h2_manifest)):
                sec_dict = m_obj.get(sec_name)
                ent = sec_dict.get(item_id) if isinstance(sec_dict, Mapping) else None
                if not isinstance(ent, Mapping):
                    matched = False
                    errors.append(f"{m_label} manifest missing stage_b_forensic_probes[{item_id!r}]")
                else:
                    s1 = str(ent.get("pass1_sha256", ""))
                    s2 = str(ent.get("pass2_sha256", ""))
                    exp_sha = sha0 if m_label == "H0" else sha2
                    if not HEX64_RE.fullmatch(s1) or s1 != s2 or s1 != exp_sha:
                        matched = False
                        errors.append(f"{m_label} stage_b_forensic_probes[{item_id!r}] two-pass SHA mismatch")

        if not matched:
            mutated_cnt = diff_b if diff_b > 0 else 1
            total_mutated_bytes += mutated_cnt
            drifted.append(item_id)
            errors.append(
                f"Post-trial drift on {item_id} ({fn2}): h0=({sz0} B, {sha0[:16]}...) "
                f"vs h2=({sz2} B, {sha2[:16]}...), diff_bytes={mutated_cnt}"
            )

        rec = StageBPostTrialItemParity(
            item_id=item_id,
            category=category,
            file_name=fn2,
            h0_bytes=sz0,
            h2_bytes=sz2,
            h0_sha256=sha0,
            h2_sha256=sha2,
            differing_bytes=diff_b,
            bit_exact_match=matched,
        )
        comparisons.append(rec)
        parity_by_id[item_id] = rec

    matched_count = sum(1 for c in comparisons if c.bit_exact_match)

    # Specific mutation byte counters
    sec0_rec = parity_by_id["sector0"]
    sector0_mut_bytes = 0 if sec0_rec.bit_exact_match else max(1, sec0_rec.differing_bytes)
    if not sec0_rec.bit_exact_match or not h2_audit.sector0_magic_ok:
        _add_code(anomaly_codes, ANOMALY_SECTOR0_TAMPER)

    wbi_rec = parity_by_id["p5_wbi_header"]
    wbi_mut_bytes = 0 if wbi_rec.bit_exact_match else max(1, wbi_rec.differing_bytes)
    if not wbi_rec.bit_exact_match or not h2_audit.p5_wbi2_header_ok:
        _add_code(anomaly_codes, ANOMALY_WBI2_HEADER_DRIFT)

    tomco_rec = parity_by_id["p8_tomco_txt"]
    cp_img_rec = parity_by_id["p8_cp_image"]
    cp_mut_bytes = (
        (0 if tomco_rec.bit_exact_match else max(1, tomco_rec.differing_bytes))
        + (0 if cp_img_rec.bit_exact_match else max(1, cp_img_rec.differing_bytes))
    )
    if cp_mut_bytes > 0 or not h2_audit.p8_tomco_header_ok:
        _add_code(anomaly_codes, ANOMALY_CP_BYTE_MUTATION)

    # 4. BK4 persistent NVRAM zero-drift check
    bk4_audit = _audit_stage_b_bk4_nvram_zero_drift(
        h0_dir, h2_dir, h0_manifest, h2_manifest, parity_by_id["p2_backup_bin"], ram_shadow_bk4_info
    )
    if not bk4_audit.valid:
        _add_code(anomaly_codes, ANOMALY_BK4_PERSISTENT_NVRAM_LEAK)
        errors.extend(bk4_audit.errors)

    # 5. C2PA RQ_LIC.DAT + SPACC cnflasha + Factory Sensor/IBIS Calibration check
    c2pa_cal_audit = _audit_c2pa_spacc_and_calibration(
        parity_by_id,
        c2pa_keystore_writes_attempted=c2pa_keystore_writes_attempted,
        planned_mounts=planned_mounts,
        planned_writes=planned_writes,
    )
    if not c2pa_cal_audit.valid:
        _add_code(anomaly_codes, ANOMALY_C2PA_OR_CALIBRATION_DRIFT)
        errors.extend(c2pa_cal_audit.errors)

    # 6. p1 VFAT one-shot boot-counter & rollback capsule + exFAT lab media cleanliness
    p1_exfat_audit = _audit_p1_capsule_and_exfat_media(
        h2_dir,
        h2_manifest,
        exfat_boot_bytes=exfat_boot_bytes,
        exfat_card_entries=exfat_card_entries,
        p1_capsule_info=p1_capsule_info,
    )
    if not p1_exfat_audit.valid:
        if p1_exfat_audit.exfat_volume_dirty or p1_exfat_audit.exfat_media_failure:
            _add_code(anomaly_codes, ANOMALY_EXFAT_VOLUME_DIRTY)
        if p1_exfat_audit.exfat_rsv_files or p1_exfat_audit.exfat_chk_files:
            _add_code(anomaly_codes, ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP)
        if (
            not p1_exfat_audit.p1_vfat_valid
            or not p1_exfat_audit.p1_oneshot_boot_counter_clean
            or not p1_exfat_audit.p1_capsule_fsync_order_ok
        ):
            _add_code(anomaly_codes, ANOMALY_P1_CAPSULE_OR_COUNTER_DRIFT)
        if not p1_exfat_audit.exfat_media_clean and (
            ANOMALY_EXFAT_VOLUME_DIRTY not in anomaly_codes
            and ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP not in anomaly_codes
        ):
            _add_code(anomaly_codes, ANOMALY_EXFAT_VOLUME_DIRTY)
        errors.extend(p1_exfat_audit.errors)

    # 7. RP2040 fixture + serial_fault_detector_v2 + thermal/power post-mortem
    serial_thermal = _audit_rp2040_and_serial_thermal_post_mortem(
        h2_dir,
        serial_log_text=serial_log_text,
        serial_log_path=serial_log_path,
        thermal_power_telemetry=thermal_power_telemetry,
        rp2040_fixture_config=rp2040_fixture_config,
    )
    if not serial_thermal.valid:
        if serial_thermal.wf12_00342260_hang_detected:
            _add_code(anomaly_codes, ANOMALY_WF12_00342260_HANG)
        if serial_thermal.panic_0x100d_13s_detected:
            _add_code(anomaly_codes, ANOMALY_0x100D_13S_PANIC)
        if not serial_thermal.thermal_under_90c_ok or serial_thermal.thermal_emergency_teardown_triggered:
            _add_code(anomaly_codes, ANOMALY_THERMAL_RUNAWAY_TEARDOWN)
        if not serial_thermal.rp2040_fixture_safe:
            _add_code(anomaly_codes, ANOMALY_RP2040_FIXTURE_HAZARD)
        if not serial_thermal.serial_detector_v2_passed:
            _add_code(anomaly_codes, ANOMALY_SERIAL_WATCHDOG_OR_PANIC)
        errors.extend(serial_thermal.errors)

    if total_mutated_bytes > 0 and not anomaly_codes:
        _add_code(anomaly_codes, ANOMALY_TIER0_PERSISTENT_DRIFT)

    # Priority-ordered primary classification
    priority = (
        ANOMALY_SECTOR0_TAMPER,
        ANOMALY_WBI2_HEADER_DRIFT,
        ANOMALY_CP_BYTE_MUTATION,
        ANOMALY_BK4_PERSISTENT_NVRAM_LEAK,
        ANOMALY_C2PA_OR_CALIBRATION_DRIFT,
        ANOMALY_EXFAT_VOLUME_DIRTY,
        ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP,
        ANOMALY_WF12_00342260_HANG,
        ANOMALY_THERMAL_RUNAWAY_TEARDOWN,
        ANOMALY_0x100D_13S_PANIC,
        ANOMALY_P1_CAPSULE_OR_COUNTER_DRIFT,
        ANOMALY_RP2040_FIXTURE_HAZARD,
        ANOMALY_SERIAL_WATCHDOG_OR_PANIC,
        ANOMALY_SAME_BODY_IDENTITY_MISMATCH,
        ANOMALY_SYNTHETIC_OR_INVALID_BUNDLE,
        ANOMALY_TIER0_PERSISTENT_DRIFT,
    )
    classification = CLASS_CLEAN_ZERO_PERSISTENCE
    for code in priority:
        if code in anomaly_codes:
            classification = code
            break

    zero_persistence_ok = (
        distinct_dirs_ok
        and both_real_valid
        and same_body_ok
        and total_mutated_bytes == 0
        and wbi_mut_bytes == 0
        and cp_mut_bytes == 0
        and c2pa_cal_audit.calibration_mutation_bytes == 0
        and sector0_mut_bytes == 0
        and c2pa_cal_audit.c2pa_keystore_untouched
        and c2pa_cal_audit.spacc_cnflasha_untouched
        and len(drifted) == 0
        and matched_count == len(audited_specs)
        and bk4_audit.valid
        and c2pa_cal_audit.valid
        and p1_exfat_audit.valid
        and serial_thermal.valid
    )
    all_passed = zero_persistence_ok and len(anomaly_codes) == 0 and len(errors) == 0

    draft = StageBPostTrialReceipt(
        schema=STAGE_B_POST_TRIAL_RECEIPT_SCHEMA,
        phase_version=PHASE_62_VERSION,
        verification_mode=verification_mode,
        all_checks_passed=all_passed,
        zero_persistence_verified=zero_persistence_ok,
        classification=classification,
        anomaly_codes=tuple(anomaly_codes),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        usb_or_camera_operations=USB_OR_CAMERA_OPERATIONS,
        distinct_capture_dirs_ok=distinct_dirs_ok,
        h0_bundle_valid=h0_audit.valid,
        h2_bundle_valid=h2_audit.valid,
        both_bundles_real_hardware_valid=both_real_valid,
        same_body_identity_verified=same_body_ok,
        model_id=h2_audit.model_id or h0_audit.model_id,
        body_serial=h0_audit.body_serial if same_body_ok else f"{h0_audit.body_serial}!={h2_audit.body_serial}",
        emmc_cid=h0_audit.emmc_cid if same_body_ok else f"{h0_audit.emmc_cid}!={h2_audit.emmc_cid}",
        camera_body_tag=h0_audit.camera_body_tag if same_body_ok else "",
        audited_item_count=len(audited_specs),
        matched_item_count=matched_count,
        persistent_bytes_mutated=total_mutated_bytes,
        wbi_mutation_bytes=wbi_mut_bytes,
        cp_mutation_bytes=cp_mut_bytes,
        calibration_mutation_bytes=c2pa_cal_audit.calibration_mutation_bytes,
        sector0_mutation_bytes=sector0_mut_bytes,
        c2pa_keystore_untouched=c2pa_cal_audit.c2pa_keystore_untouched,
        spacc_cnflasha_untouched=c2pa_cal_audit.spacc_cnflasha_untouched,
        drifted_items=tuple(drifted),
        item_comparisons=tuple(comparisons),
        bk4_nvram_audit=bk4_audit,
        c2pa_calibration_audit=c2pa_cal_audit,
        p1_exfat_audit=p1_exfat_audit,
        serial_thermal_post_mortem=serial_thermal,
        h0_bundle_audit=asdict(h0_audit),
        h2_bundle_audit=asdict(h2_audit),
        errors=tuple(errors),
        receipt_sha256="",
    )
    receipt_sha = _compute_canonical_sha256(draft.to_dict(), "receipt_sha256")
    return replace(draft, receipt_sha256=receipt_sha)


def _with_normalized_bundle_dirs(receipt: StageBPostTrialReceipt) -> StageBPostTrialReceipt:
    """Normalize ephemeral temp directory paths inside nominal receipt for reproducible report SHA-256."""
    d = receipt.to_dict()
    if isinstance(d.get("h0_bundle_audit"), dict):
        d["h0_bundle_audit"]["bundle_dir"] = "<STAGE_B_SANDBOX>/h0_capture"
    if isinstance(d.get("h2_bundle_audit"), dict):
        d["h2_bundle_audit"]["bundle_dir"] = "<STAGE_B_SANDBOX>/h2_capture"
    d["receipt_sha256"] = _compute_canonical_sha256(d, "receipt_sha256")
    return StageBPostTrialReceipt(
        schema=str(d["schema"]),
        phase_version=str(d["phase_version"]),
        verification_mode=str(d["verification_mode"]),
        all_checks_passed=bool(d["all_checks_passed"]),
        zero_persistence_verified=bool(d["zero_persistence_verified"]),
        classification=str(d["classification"]),
        anomaly_codes=tuple(d["anomaly_codes"]),
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        p8_cp_mutation_forbidden=True,
        wbi_p5_write_and_hibernation_forbidden=True,
        usb_or_camera_operations=0,
        distinct_capture_dirs_ok=bool(d["distinct_capture_dirs_ok"]),
        h0_bundle_valid=bool(d["h0_bundle_valid"]),
        h2_bundle_valid=bool(d["h2_bundle_valid"]),
        both_bundles_real_hardware_valid=bool(d["both_bundles_real_hardware_valid"]),
        same_body_identity_verified=bool(d["same_body_identity_verified"]),
        model_id=str(d["model_id"]),
        body_serial=str(d["body_serial"]),
        emmc_cid=str(d["emmc_cid"]),
        camera_body_tag=str(d["camera_body_tag"]),
        audited_item_count=int(d["audited_item_count"]),
        matched_item_count=int(d["matched_item_count"]),
        persistent_bytes_mutated=int(d["persistent_bytes_mutated"]),
        wbi_mutation_bytes=int(d["wbi_mutation_bytes"]),
        cp_mutation_bytes=int(d["cp_mutation_bytes"]),
        calibration_mutation_bytes=int(d["calibration_mutation_bytes"]),
        sector0_mutation_bytes=int(d["sector0_mutation_bytes"]),
        c2pa_keystore_untouched=bool(d["c2pa_keystore_untouched"]),
        spacc_cnflasha_untouched=bool(d["spacc_cnflasha_untouched"]),
        drifted_items=tuple(d["drifted_items"]),
        item_comparisons=receipt.item_comparisons,
        bk4_nvram_audit=receipt.bk4_nvram_audit,
        c2pa_calibration_audit=receipt.c2pa_calibration_audit,
        p1_exfat_audit=receipt.p1_exfat_audit,
        serial_thermal_post_mortem=receipt.serial_thermal_post_mortem,
        h0_bundle_audit=d["h0_bundle_audit"],
        h2_bundle_audit=d["h2_bundle_audit"],
        errors=tuple(d["errors"]),
        receipt_sha256=str(d["receipt_sha256"]),
    )


# ---------------------------------------------------------------------------
# O_RDONLY Donor Baseline Probes (Dual-Mode Local Donor vs Clean-Room)
# ---------------------------------------------------------------------------


def _probe_donor_surfaces_o_rdonly(*, use_clean_room: bool) -> Tuple[Dict[str, Any], bytes, List[str]]:
    errors: List[str] = []
    if use_clean_room:
        fa0080 = build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None)
        return (
            {
                "mode": "CLEAN_ROOM_SYNTHETIC",
                "p1_vbr_checked": True,
                "p5_wbi2_header_checked": True,
                "p8_cp_fat_checked": True,
                "bk4_seed_checked": True,
                "fa0080_sha256": hashlib.sha256(fa0080).hexdigest(),
            },
            fa0080,
            errors,
        )

    p1_path = resolve_work_subpath(DONOR_P1_RELPATH, require_file=True)
    p5_path = resolve_work_subpath(DONOR_P5_WBI2_RELPATH, require_file=True)
    p8_path = resolve_work_subpath(DONOR_P8_CP_RELPATH, require_file=True)
    bk4_path = resolve_work_subpath(DONOR_FX3_SEED_BK4_RELPATH, require_file=True)

    p1_vbr = _read_slice_o_rdonly(p1_path, 0, 512)
    p1_res = parse_p1_fat12_fat16_vbr(p1_vbr)
    if not p1_res.valid:
        errors.extend(f"donor p1: {e}" for e in p1_res.errors)

    p5_hdr = _read_slice_o_rdonly(p5_path, 0, 512)
    p5_size = p5_path.stat().st_size
    p5_sha = hashlib.sha256(p5_hdr).hexdigest()
    wbi_magic_ok = False
    wbi_sections = 0
    wbi_dver = 0
    if len(p5_hdr) < 88:
        errors.append(f"donor p5 WBI2 header truncated: {len(p5_hdr)} < 88")
    else:
        (
            wbi_fver,
            _wbi_pad,
            wbi_sections,
            _wbi_flag,
            wbi_resume_vec,
            wbi_dver,
            wbi_sector_sz,
            wbi_r_data_sz,
            _wbi_kstart,
            _wbi_ksz,
            _wbi_cksum,
            wbi_o_data_sz,
        ) = struct.unpack("<4sI10Q", p5_hdr[:88])
        wbi_magic_ok = wbi_fver == b"WBI2"
        if not wbi_magic_ok:
            errors.append(f"donor p5 WBI2 magic invalid: 0x{wbi_fver.hex()}")
        if wbi_sections <= 0 or wbi_resume_vec <= 0 or wbi_sector_sz <= 0 or wbi_r_data_sz <= 0 or wbi_o_data_sz <= 0:
            errors.append(
                f"donor p5 WBI2 geometry invalid: sections={wbi_sections} r_data={wbi_r_data_sz} o_data={wbi_o_data_sz}"
            )

    p8_hdr = _read_slice_o_rdonly(p8_path, 0, 4096)
    p8_boot_sig_ok = len(p8_hdr) >= 512 and p8_hdr[510:512] == b"\x55\xaa"
    if not p8_boot_sig_ok:
        errors.append("donor p8 nflasha8.img missing 0xAA55 VBR signature")

    bk4_raw = _read_file_o_rdonly(bk4_path)
    fa0080 = read_bk4_property_bytes(bk4_raw, KEY_FA0080_BOOT_DESC, offset=0) or b""
    if len(fa0080) != FA0080_TOTAL_BYTES:
        errors.append("donor FX3 BK4 seed missing 9216 B 0xfa0080 boot descriptor table")
        fa0080 = build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=None)

    return (
        {
            "mode": "LOCAL_DONOR_O_RDONLY",
            "p1_vbr_checked": p1_res.valid,
            "p1_fat_type": p1_res.fat_type,
            "p5_wbi2_header_checked": wbi_magic_ok and wbi_sections > 0 and p5_size >= 88,
            "p5_wbi2_sections": wbi_sections,
            "p5_wbi2_dversion_hex": f"0x{wbi_dver:08x}",
            "p5_wbi2_header_sha256": p5_sha,
            "p8_cp_fat_checked": p8_boot_sig_ok,
            "p8_cp_header_sha256": hashlib.sha256(p8_hdr).hexdigest(),
            "bk4_seed_checked": len(fa0080) == FA0080_TOTAL_BYTES,
            "fa0080_sha256": hashlib.sha256(fa0080).hexdigest(),
        },
        fa0080,
        errors,
    )


# ---------------------------------------------------------------------------
# 10-Scenario Anomaly & Drift Classifier Suite
# ---------------------------------------------------------------------------


def run_stage_b_post_trial_forensic_audit(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
) -> StageBPostTrialAuditReport:
    """Execute the Stage-B `H0`-vs-`H2` post-trial forensic audit + 10-scenario anomaly classifier."""
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"
    errors: List[str] = []

    donor_probes, fa0080_tbl, probe_errs = _probe_donor_surfaces_o_rdonly(use_clean_room=use_clean_room)
    errors.extend(probe_errs)

    stock_bk4 = build_persistent_stock_bk4_bytes(
        fa0080_table=fa0080_tbl, wireless_enabled=True, bk_lang_byte=0x00, active_byte8=0x00
    )

    scenarios: List[StageBPostTrialScenarioResult] = []
    tmp_ctx = tempfile.TemporaryDirectory(prefix="fx6_phase62_stage_b_post_trial_")
    tmp_path = Path(tmp_ctx.name)
    try:
        h0_dir = tmp_path / "h0_capture"
        h2_dir = tmp_path / "h2_capture"

        populate_stage_b_capture_bundle_fixture(
            h0_dir, fa0080_table=fa0080_tbl, bk4_bytes=stock_bk4
        )
        populate_stage_b_capture_bundle_fixture(
            h2_dir, fa0080_table=fa0080_tbl, bk4_bytes=stock_bk4
        )

        h0_pre = verify_real_tier0_capture_bundle(h0_dir)
        h2_pre = verify_real_tier0_capture_bundle(h2_dir)

        # S01: Nominal Clean H0 == H2 Stage-B Session
        nominal_raw = verify_stage_b_post_trial_zero_persistence(
            h0_dir,
            h2_dir,
            synthetic_clean_room=use_clean_room,
            _preverified_h0_audit=h0_pre,
            _preverified_h2_audit=h2_pre,
        )
        nominal_norm = _with_normalized_bundle_dirs(nominal_raw)
        if not nominal_raw.all_checks_passed:
            errors.extend(f"S01 nominal failed: {e}" for e in nominal_raw.errors)

        def _record_scenario(
            scenario_id: str,
            description: str,
            expected_pass: bool,
            expected_code: str,
            rec: StageBPostTrialReceipt,
            extra_predicate: bool = True,
        ) -> None:
            rec_norm = _with_normalized_bundle_dirs(rec)
            ok = (
                (rec_norm.all_checks_passed == expected_pass)
                and (rec_norm.classification == expected_code)
                and (expected_pass or expected_code in rec_norm.anomaly_codes)
                and extra_predicate
            )
            if not ok:
                errors.append(
                    f"Scenario {scenario_id} failed: expected=({expected_pass}, {expected_code}), "
                    f"observed=({rec_norm.all_checks_passed}, {rec_norm.classification}, codes={rec_norm.anomaly_codes})"
                )
            prim_err = rec_norm.errors[0] if rec_norm.errors else ""
            if prim_err:
                prim_err = prim_err.replace(str(tmp_path), "<STAGE_B_SANDBOX>")
            scenarios.append(
                StageBPostTrialScenarioResult(
                    scenario_id=scenario_id,
                    description=description,
                    expected_pass=expected_pass,
                    expected_anomaly_code=expected_code,
                    observed_pass=rec_norm.all_checks_passed,
                    observed_classification=rec_norm.classification,
                    observed_anomaly_codes=rec_norm.anomaly_codes,
                    passed=ok,
                    persistent_bytes_mutated=rec_norm.persistent_bytes_mutated,
                    wbi_mutation_bytes=rec_norm.wbi_mutation_bytes,
                    cp_mutation_bytes=rec_norm.cp_mutation_bytes,
                    calibration_mutation_bytes=rec_norm.calibration_mutation_bytes,
                    sector0_mutation_bytes=rec_norm.sector0_mutation_bytes,
                    c2pa_keystore_untouched=rec_norm.c2pa_keystore_untouched,
                    exfat_media_clean=rec_norm.p1_exfat_audit.exfat_media_clean,
                    drifted_items=rec_norm.drifted_items,
                    primary_error=prim_err,
                    receipt_sha256=rec_norm.receipt_sha256,
                )
            )

        _record_scenario(
            "S01_CLEAN_H0_EQ_H2_STAGE_B_SESSION",
            "Clean H0==H2 Stage-B session (BK4 Airplane/CJK RAM-only, WBI2/CP/C2PA/SPACC/exFAT/p1/RP2040/serial/thermal clean)",
            True,
            CLASS_CLEAN_ZERO_PERSISTENCE,
            nominal_norm,
        )

        h2_manifest_path = h2_dir / "backup-manifest.json"
        base_h2_manifest = json.loads(_read_file_o_rdonly(h2_manifest_path).decode("utf-8"))

        # S02: BK4 Persistent Airplane Leak (0x019e0012=0x00 + CJK BK_LANG=0x19 persisted in H2 p2_backup_bin.bin)
        p2_path = h2_dir / "p2_backup_bin.bin"
        orig_p2 = _read_file_o_rdonly(p2_path)
        try:
            leaked_bk4 = build_persistent_stock_bk4_bytes(
                fa0080_table=fa0080_tbl, wireless_enabled=False, bk_lang_byte=0x19, active_byte8=0x00
            )
            mut_p2 = bytearray(orig_p2)
            mut_p2[: len(leaked_bk4)] = leaked_bk4
            p2_path.write_bytes(bytes(mut_p2))
            m2 = copy.deepcopy(base_h2_manifest)
            s2 = hashlib.sha256(bytes(mut_p2)).hexdigest()
            m2["items"]["p2_backup_bin"]["pass1_sha256"] = s2
            m2["items"]["p2_backup_bin"]["pass2_sha256"] = s2
            h2_manifest_path.write_text(json.dumps(m2, indent=2) + "\n", encoding="utf-8")
            r_s02 = verify_stage_b_post_trial_zero_persistence(
                h0_dir, h2_dir, synthetic_clean_room=use_clean_room, _preverified_h0_audit=h0_pre
            )
            _record_scenario(
                "S02_BK4_PERSISTENT_AIRPLANE_LEAK",
                "Persistent BK4 Airplane-Mode (0x019e0012=00) + CJK BK_LANG leak in H2 p2_backup_bin.bin",
                False,
                ANOMALY_BK4_PERSISTENT_NVRAM_LEAK,
                r_s02,
                (not r_s02.bk4_nvram_audit.persistent_airplane_keys_unchanged)
                and (not r_s02.bk4_nvram_audit.persistent_bk_lang_unchanged)
                and r_s02.bk4_nvram_audit.bk4_mutated_bytes > 0,
            )
        finally:
            p2_path.write_bytes(orig_p2)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # S03: WBI2 Header Drift
        wbi_path = h2_dir / "p5_wbi_header.bin"
        orig_wbi = _read_file_o_rdonly(wbi_path)
        try:
            mut_wbi = bytearray(orig_wbi)
            mut_wbi[200] ^= 0x01
            wbi_path.write_bytes(bytes(mut_wbi))
            m3 = copy.deepcopy(base_h2_manifest)
            s3 = hashlib.sha256(bytes(mut_wbi)).hexdigest()
            m3["redline_headers"]["p5_wbi_header"]["pass1_sha256"] = s3
            m3["redline_headers"]["p5_wbi_header"]["pass2_sha256"] = s3
            h2_manifest_path.write_text(json.dumps(m3, indent=2) + "\n", encoding="utf-8")
            r_s03 = verify_stage_b_post_trial_zero_persistence(
                h0_dir, h2_dir, synthetic_clean_room=use_clean_room, _preverified_h0_audit=h0_pre
            )
            _record_scenario(
                "S03_WBI2_HEADER_DRIFT",
                "1-bit drift in H2 p5_wbi_header.bin (WBI2)",
                False,
                ANOMALY_WBI2_HEADER_DRIFT,
                r_s03,
                r_s03.wbi_mutation_bytes == 1 and "p5_wbi_header" in r_s03.drifted_items,
            )
        finally:
            wbi_path.write_bytes(orig_wbi)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # S04: CP Byte Mutation (`p8_cpapp_b.bin`)
        cp_path = h2_dir / "p8_cpapp_b.bin"
        orig_cp = _read_file_o_rdonly(cp_path)
        try:
            mut_cp = bytearray(orig_cp)
            mut_cp[0x120] ^= 0x01
            cp_path.write_bytes(bytes(mut_cp))
            m4 = copy.deepcopy(base_h2_manifest)
            s4 = hashlib.sha256(bytes(mut_cp)).hexdigest()
            m4["stage_b_forensic_probes"]["p8_cp_image"]["pass1_sha256"] = s4
            m4["stage_b_forensic_probes"]["p8_cp_image"]["pass2_sha256"] = s4
            h2_manifest_path.write_text(json.dumps(m4, indent=2) + "\n", encoding="utf-8")
            r_s04 = verify_stage_b_post_trial_zero_persistence(
                h0_dir, h2_dir, synthetic_clean_room=use_clean_room, _preverified_h0_audit=h0_pre
            )
            _record_scenario(
                "S04_CP_BYTE_MUTATION",
                "1-bit mutation in H2 p8:/cp (p8_cpapp_b.bin)",
                False,
                ANOMALY_CP_BYTE_MUTATION,
                r_s04,
                r_s04.cp_mutation_bytes == 1 and "p8_cp_image" in r_s04.drifted_items,
            )
        finally:
            cp_path.write_bytes(orig_cp)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # S05: C2PA / Calibration Digest Drift (`c2pa_rq_lic.dat`)
        c2pa_path = h2_dir / "c2pa_rq_lic.dat"
        orig_c2pa = _read_file_o_rdonly(c2pa_path)
        try:
            mut_c2pa = bytearray(orig_c2pa)
            mut_c2pa[0x50] ^= 0x01
            c2pa_path.write_bytes(bytes(mut_c2pa))
            m5 = copy.deepcopy(base_h2_manifest)
            s5 = hashlib.sha256(bytes(mut_c2pa)).hexdigest()
            m5["stage_b_forensic_probes"]["c2pa_rq_lic"]["pass1_sha256"] = s5
            m5["stage_b_forensic_probes"]["c2pa_rq_lic"]["pass2_sha256"] = s5
            h2_manifest_path.write_text(json.dumps(m5, indent=2) + "\n", encoding="utf-8")
            r_s05 = verify_stage_b_post_trial_zero_persistence(
                h0_dir, h2_dir, synthetic_clean_room=use_clean_room, _preverified_h0_audit=h0_pre
            )
            _record_scenario(
                "S05_C2PA_CALIBRATION_DIGEST_DRIFT",
                "1-bit digest drift in H2 C2PA RQ_LIC.DAT keystore probe",
                False,
                ANOMALY_C2PA_OR_CALIBRATION_DRIFT,
                r_s05,
                r_s05.calibration_mutation_bytes == 1 and (not r_s05.c2pa_keystore_untouched),
            )
        finally:
            c2pa_path.write_bytes(orig_c2pa)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # S06: exFAT VolumeDirty Set
        dirty_exfat = build_synthetic_exfat_boot_region(volume_flags=EXFAT_FLAG_VOLUME_DIRTY)
        r_s06 = verify_stage_b_post_trial_zero_persistence(
            h0_dir,
            h2_dir,
            exfat_boot_bytes=dirty_exfat,
            synthetic_clean_room=use_clean_room,
            _preverified_h0_audit=h0_pre,
            _preverified_h2_audit=h2_pre,
        )
        _record_scenario(
            "S06_EXFAT_VOLUME_DIRTY_SET",
            "exFAT VolumeDirty bit (VolumeFlags & 0x0002) set on lab media card",
            False,
            ANOMALY_EXFAT_VOLUME_DIRTY,
            r_s06,
            r_s06.p1_exfat_audit.exfat_volume_dirty and (not r_s06.p1_exfat_audit.exfat_media_clean),
        )

        # S07: exFAT .RSV Unfinalized Clip Left Behind
        r_s07 = verify_stage_b_post_trial_zero_persistence(
            h0_dir,
            h2_dir,
            exfat_card_entries=(("PRIVATE/M4ROOT/CLIP/C0001.RSV", 4_194_304),),
            synthetic_clean_room=use_clean_room,
            _preverified_h0_audit=h0_pre,
            _preverified_h2_audit=h2_pre,
        )
        _record_scenario(
            "S07_EXFAT_RSV_CLIP_LEFT_BEHIND",
            "Unfinalized .RSV crash recovery clip left behind on exFAT lab media card",
            False,
            ANOMALY_EXFAT_UNFINALIZED_RSV_CLIP,
            r_s07,
            ("PRIVATE/M4ROOT/CLIP/C0001.RSV" in r_s07.p1_exfat_audit.exfat_rsv_files)
            and (not r_s07.p1_exfat_audit.exfat_media_clean),
        )

        # S08: 00342260 WF-12 Wireless Hang Log Signature
        wf12_log = (
            _build_clean_stage_b_serial_log()
            + "[    8.500000] WlanResourceMainThread 0x70d4 usleep hang: NOTICE 00342260 WF-12 wireless malfunction\n"
        )
        r_s08 = verify_stage_b_post_trial_zero_persistence(
            h0_dir,
            h2_dir,
            serial_log_text=wf12_log,
            synthetic_clean_room=use_clean_room,
            _preverified_h0_audit=h0_pre,
            _preverified_h2_audit=h2_pre,
        )
        _record_scenario(
            "S08_WF12_00342260_LOG_SIGNATURE",
            "00342260 (WF-12) wireless hang / 0x70d4 bootloop log signature",
            False,
            ANOMALY_WF12_00342260_HANG,
            r_s08,
            r_s08.serial_thermal_post_mortem.wf12_00342260_hang_detected,
        )

        # S09: Thermal >=90C Emergency Teardown Receipt
        r_s09 = verify_stage_b_post_trial_zero_persistence(
            h0_dir,
            h2_dir,
            thermal_power_telemetry={
                "peak_soc_c": 91.5,
                "peak_cfexpress_c": 65.0,
                "thermal_emergency_teardown_triggered": True,
                "npfz100_soc_pct": 85,
                "usbpd_contract_mw": USBPD_REQUIRED_POWER_MW,
                "persistent_emmc_writes_authorized": False,
                "persistent_write_release": False,
            },
            synthetic_clean_room=use_clean_room,
            _preverified_h0_audit=h0_pre,
            _preverified_h2_audit=h2_pre,
        )
        _record_scenario(
            "S09_THERMAL_90C_EMERGENCY_TEARDOWN",
            "Peak SoC >= 90.0C thermal runaway emergency teardown receipt",
            False,
            ANOMALY_THERMAL_RUNAWAY_TEARDOWN,
            r_s09,
            r_s09.serial_thermal_post_mortem.peak_soc_c >= 90.0
            and (not r_s09.serial_thermal_post_mortem.thermal_under_90c_ok)
            and r_s09.serial_thermal_post_mortem.thermal_emergency_teardown_triggered,
        )

        # S10: Sector 0 Tamper
        sec0_path = h2_dir / "sector0.bin"
        orig_sec0 = _read_file_o_rdonly(sec0_path)
        try:
            mut_sec0 = bytearray(orig_sec0)
            mut_sec0[16] ^= 0x01
            sec0_path.write_bytes(bytes(mut_sec0))
            m10 = copy.deepcopy(base_h2_manifest)
            s10 = hashlib.sha256(bytes(mut_sec0)).hexdigest()
            m10["items"]["sector0"]["pass1_sha256"] = s10
            m10["items"]["sector0"]["pass2_sha256"] = s10
            h2_manifest_path.write_text(json.dumps(m10, indent=2) + "\n", encoding="utf-8")
            r_s10 = verify_stage_b_post_trial_zero_persistence(
                h0_dir, h2_dir, synthetic_clean_room=use_clean_room, _preverified_h0_audit=h0_pre
            )
            _record_scenario(
                "S10_SECTOR0_TAMPER",
                "1-bit tamper in H2 sector0.bin ('8246' partition table)",
                False,
                ANOMALY_SECTOR0_TAMPER,
                r_s10,
                r_s10.sector0_mutation_bytes == 1 and "sector0" in r_s10.drifted_items,
            )
        finally:
            sec0_path.write_bytes(orig_sec0)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")
    finally:
        tmp_ctx.cleanup()

    temp_cleaned = not tmp_path.exists()
    if not temp_cleaned:
        errors.append(f"Temporary audit directory not cleaned: {tmp_path}")

    passed_count = sum(1 for sc in scenarios if sc.passed)
    all_10_ok = len(scenarios) == 10 and passed_count == 10
    all_ok = (
        len(errors) == 0
        and all_10_ok
        and nominal_norm.all_checks_passed
        and nominal_norm.zero_persistence_verified
        and temp_cleaned
    )
    status = "VERIFIED_STAGE_B_POST_TRIAL_ZERO_PERSISTENCE" if all_ok else "FAILED"

    draft = StageBPostTrialAuditReport(
        schema=STAGE_B_POST_TRIAL_AUDIT_SCHEMA,
        phase_version=PHASE_62_VERSION,
        verification_mode=verification_mode,
        all_checks_passed=all_ok,
        status=status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        wbi_mutation_bytes=WBI_MUTATION_BYTES,
        calibration_mutation_bytes=CALIBRATION_MUTATION_BYTES,
        usb_or_camera_operations=USB_OR_CAMERA_OPERATIONS,
        temp_dir_cleaned=temp_cleaned,
        donor_o_rdonly_probes=donor_probes,
        nominal_receipt=nominal_norm,
        scenario_count=len(scenarios),
        passed_scenario_count=passed_count,
        all_10_scenarios_passed=all_10_ok,
        scenarios=tuple(scenarios),
        errors=tuple(errors),
        report_sha256="",
    )
    rep_sha = _compute_report_sha256(draft.to_dict())
    return replace(draft, report_sha256=rep_sha)


# ---------------------------------------------------------------------------
# Fail-Closed Tamper Verifier
# ---------------------------------------------------------------------------


def verify_stage_b_post_trial_report(payload: object) -> StageBPostTrialVerifyResult:
    """Fail-closed verifier for a `stage_b_post_trial_forensic_audit_v1` JSON/dict report."""
    errors: List[str] = []
    if isinstance(payload, StageBPostTrialAuditReport):
        payload = payload.to_dict()
    if not isinstance(payload, Mapping):
        return StageBPostTrialVerifyResult(
            valid=False,
            schema_ok=False,
            sha256_matched=False,
            expected_report_sha256="",
            observed_report_sha256="",
            safety_redlines_ok=False,
            nominal_receipt_ok=False,
            all_10_scenarios_ok=False,
            errors=("Stage-B post-trial report payload must be a mapping",),
        )

    serialized = json.dumps(payload, sort_keys=False)
    if _RAW_BYTES_REPR_RE.search(serialized):
        errors.append("Raw binary bytes repr detected in Stage-B post-trial report")

    schema_ok = (
        payload.get("schema") == STAGE_B_POST_TRIAL_AUDIT_SCHEMA
        and payload.get("phase_version") == PHASE_62_VERSION
        and payload.get("verification_mode") in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
    )
    if not schema_ok:
        errors.append(
            f"Invalid schema/version/mode: schema={payload.get('schema')!r}, "
            f"version={payload.get('phase_version')!r}, mode={payload.get('verification_mode')!r}"
        )

    obs_sha = str(payload.get("report_sha256", ""))
    exp_sha = _compute_report_sha256(payload)
    sha_matched = bool(HEX64_RE.fullmatch(obs_sha)) and obs_sha == exp_sha
    if not sha_matched:
        errors.append(f"report_sha256 mismatch: expected={exp_sha}, observed={obs_sha!r}")

    redlines_ok = (
        payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("p8_cp_mutation_forbidden") is True
        and payload.get("wbi_p5_write_and_hibernation_forbidden") is True
        and payload.get("cp_mutation_bytes") == 0
        and payload.get("wbi_mutation_bytes") == 0
        and payload.get("calibration_mutation_bytes") == 0
        and payload.get("usb_or_camera_operations") == 0
        and payload.get("temp_dir_cleaned") is True
    )
    if not redlines_ok:
        errors.append("Hard-locked safety redlines violated in Stage-B post-trial report")

    nom = payload.get("nominal_receipt")
    nominal_ok = False
    if isinstance(nom, Mapping):
        nom_obs_sha = str(nom.get("receipt_sha256", ""))
        nom_exp_sha = _compute_canonical_sha256(nom, "receipt_sha256")
        bk4_n = nom.get("bk4_nvram_audit")
        cal_n = nom.get("c2pa_calibration_audit")
        ex_n = nom.get("p1_exfat_audit")
        st_n = nom.get("serial_thermal_post_mortem")
        nominal_ok = (
            nom.get("schema") == STAGE_B_POST_TRIAL_RECEIPT_SCHEMA
            and bool(HEX64_RE.fullmatch(nom_obs_sha))
            and nom_obs_sha == nom_exp_sha
            and nom.get("all_checks_passed") is True
            and nom.get("zero_persistence_verified") is True
            and nom.get("classification") == CLASS_CLEAN_ZERO_PERSISTENCE
            and nom.get("persistent_bytes_mutated") == 0
            and nom.get("wbi_mutation_bytes") == 0
            and nom.get("cp_mutation_bytes") == 0
            and nom.get("calibration_mutation_bytes") == 0
            and nom.get("sector0_mutation_bytes") == 0
            and nom.get("c2pa_keystore_untouched") is True
            and nom.get("spacc_cnflasha_untouched") is True
            and isinstance(bk4_n, Mapping)
            and bk4_n.get("valid") is True
            and isinstance(cal_n, Mapping)
            and cal_n.get("valid") is True
            and isinstance(ex_n, Mapping)
            and ex_n.get("valid") is True
            and ex_n.get("exfat_media_clean") is True
            and isinstance(st_n, Mapping)
            and st_n.get("valid") is True
            and isinstance(st_n.get("peak_soc_c"), (int, float))
            and float(st_n["peak_soc_c"]) < FAIL_CLOSED_TEARDOWN_TEMP_C
        )
    if not nominal_ok:
        errors.append("Nominal Stage-B H0==H2 receipt check failed or tampered")

    scenarios_raw = payload.get("scenarios")
    all_10_ok = False
    if isinstance(scenarios_raw, (list, tuple)) and len(scenarios_raw) == 10:
        seen_ids = [str(s.get("scenario_id", "")) for s in scenarios_raw if isinstance(s, Mapping)]
        all_10_ok = (
            tuple(seen_ids) == STAGE_B_POST_TRIAL_SCENARIO_IDS
            and payload.get("scenario_count") == 10
            and payload.get("passed_scenario_count") == 10
            and payload.get("all_10_scenarios_passed") is True
            and all(isinstance(s, Mapping) and s.get("passed") is True for s in scenarios_raw)
        )
    if not all_10_ok:
        errors.append("10-Scenario Anomaly & Drift Classifier verification failed")

    if payload.get("all_checks_passed") is not True or payload.get("status") != "VERIFIED_STAGE_B_POST_TRIAL_ZERO_PERSISTENCE":
        errors.append("Report all_checks_passed/status not VERIFIED_STAGE_B_POST_TRIAL_ZERO_PERSISTENCE")
    if payload.get("errors"):
        errors.append(f"Report contains non-empty errors: {payload.get('errors')!r}")

    valid = (
        schema_ok
        and sha_matched
        and redlines_ok
        and nominal_ok
        and all_10_ok
        and len(errors) == 0
    )
    return StageBPostTrialVerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        sha256_matched=sha_matched,
        expected_report_sha256=exp_sha,
        observed_report_sha256=obs_sha,
        safety_redlines_ok=redlines_ok,
        nominal_receipt_ok=nominal_ok,
        all_10_scenarios_ok=all_10_ok,
        errors=tuple(errors),
    )
