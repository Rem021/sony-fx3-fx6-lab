"""Phase 48 — Deterministic Stage-B (`P1..P12+Fan`, 13/13) SVR4 `cpio newc` Volatile RAM-Overlay Packager v2 & Atomic `init2` Verify-Before-Mount Guard.

Upgrades the Stage-A volatile overlay packager (`ram_overlay_packager.py`) to full Stage-B
(`P1..P12+Fan`, 13/13 artifacts + `BK4\\0` cold-boot Airplane-Mode & CJK/EN language shadow)
while operating strictly in memory or ephemeral `tempfile.TemporaryDirectory()` sandboxes:

1. **Deterministic Stage-B SVR4 `cpio newc` (`070701`) Builder & Parser**:
   - Enforces `mtime=0`, `uid=0`, `gid=0`, sorted relative entry paths, 4-byte aligned headers
     and payloads, and canonical `TRAILER!!!` end-of-archive sentinel (`100%` reproducible SHA-256).
   - Packages `etc/fx6_overlay/stage_b_overlay_manifest.json`, `13/13` `P1..P12+Fan`
     Verify-Before-Mount SHA-256 lock table (including `P10` keymap inside `appFw.so`, `P11`
     `Uipc/CP` Smart-Handle `0x91db059b` + `/dev/rtc0->udate` `0x92d2091c` + `XLR-H1` `0x5d90`
     shim descriptor, and `P12` `libWlanResource.so` `0x70d4 -> mov w0, #0; ret`),
     `tmp/bk4_shadow` (`BK4\\0` container with Airplane-Mode defaults `0x019e0012=00`,
     `0x0051000f=00`, `0x01a20002=00` and selectable `BK_LANG` `0x02cf019c` for
     `en`/`schinese`/`tchinese`/`japanese`), `etc/fx6_overlay/stage_b_init2_guard.sh`, and
     auxiliary contract metadata.
   - Verifies strict `tmpfs` DDR budget (`volatile_tmpfs_overlay_bytes < 48 MiB` and
     `cpio_archive_bytes < 48 MiB` inside FX3's `2048 MiB` DDR, failing closed on overrun).

2. **POSIX `/bin/sh` Stage-B `init2` One-Shot Atomic Guard & 9-Scenario Sandbox Drill**:
   - Generates `stage_b_init2_guard.sh` via `generate_stage_b_init2_guard_script(...)` enforcing:
     - One-shot `boot_attempts` latch + `/tmp/mod_arm_once` unlink BEFORE any bind-mount.
     - Zero `/etc/ld.so.preload` mutation (shim environment scoped solely to `appFw` child),
       passing both `fx3_safety.preflight.verify_failsafe_hook_script` and
       `fx3_safety.runtime_antibrick_guards.audit_ld_so_preload_and_overlay`.
     - `13/13` SHA-256 Verify-Before-Mount check across every Stage-B artifact + `BK4\\0` magic
       check + `PRODUCT_MODEL == 0x91030080` + thermal/battery preflight + `tmpfs` headroom gate.
     - Hard-locked redlines: `persistent_emmc_writes_authorized = False`, `cp_mutation_bytes = 0`,
       `wbi_mutation_bytes = 0`.
   - Executes real `/bin/sh` sandbox drills across 9 scenarios (1 clean Stage-B mount + 8 fault
     injections) proving 100% fail-closed fallback to stock FX3 `v7.02`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from fx3_safety.boot_contracts import (
    BK4_HEADER_SIZE,
    BK4_MAGIC,
    BK4_SYNC_MARKER,
    FA0080_TOTAL_BYTES,
    parse_bk4_record,
)
from fx3_safety.preflight import FailsafeHookAudit, verify_failsafe_hook_script
from fx3_safety.runtime_antibrick_guards import (
    FX3_MODEL_ID_HEX,
    GuardAuditResult,
    audit_ld_so_preload_and_overlay,
)

from .backup_bridge_verifier import (
    FX3_PCIDMA_API_VA,
    FX6_PCIDMA_API_VA,
    PINNED_ENTRY16_BYTES,
    SYNC100_DST_QUEUE,
)
from .backup_mount_tolerance_verifier import (
    BK4_ATTR_SHADOW_CRC16,
    BK4_SHADOW_MODEL_TAG,
    BK4_SHADOW_SUBSYSTEM_COUNT,
    BK4_VERSION_WORD0,
    DEFAULT_FX3_SEED_BK4_PATH,
    DEFAULT_SHADOW_FIXED_AREA_SIZE,
    DEFAULT_SHADOW_FIXED_AREA_TOP,
    FX6_DUAL_SLOT_DEV_IDS,
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
from .candidate_builder import _build_synthetic_stage_b_appfw_bundle
from .hardware_readiness_packet import _is_forced_clean_room
from .patcher import (
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
    P12_WLAN_FATAL_GUARD_SPEC,
    STAGE_B_WITH_P12_PATCH_SPECS,
    apply_patch_spec,
    read_donor_bytes_readonly,
    resolve_donor_binary_path,
    rollback_patch_spec,
)
from .ram_overlay_packager import (
    CPIO_HEADER_SIZE,
    CPIO_NEWC_MAGIC,
    CPIO_TRAILER_NAME,
    S_IFDIR,
    S_IFMT,
    S_IFREG,
    CpioArchiveAudit,
    CpioEntrySpec,
    CpioFormatError,
    build_cpio_newc_archive,
    parse_and_audit_cpio_newc,
)
from .uipc_completion_verifier import UIPC_BB_TARGET_QUEUE, UIPC_P5_P6_RULES
from .uipc_cp_shim_verifier import HANDLE_QUEUE_ID, RTC_QUEUE_ID
from .vfat_builder import build_opelog_vfat_image, verify_vfat_image
from .wireless_fault_isolation_verifier import (
    BT_BKID_ENABLE_PRIMARY,
    BT_BKID_ENABLE_SECONDARY,
    BT_BKID_RSRC_MODE,
    build_clean_room_phase22_fixtures,
)


PHASE_48_SCHEMA = "stage_b_ram_overlay_v2"
PHASE_48_VERSION = "48.0.0"

# Hard safety redline locks (immutable)
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
P8_CP_MUTATION_FORBIDDEN = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
USB_OR_CAMERA_OPERATIONS = 0

# Deterministic SVR4 cpio newc metadata constants for Phase 48 Stage-B
STAGE_B_DETERMINISTIC_MTIME = 0
STAGE_B_DETERMINISTIC_UID = 0
STAGE_B_DETERMINISTIC_GID = 0
STAGE_B_CPIO_BASE_INO = 1

# tmpfs DDR budget constraints
MIB_BYTES = 1024 * 1024
STAGE_B_FX3_DDR_TOTAL_MIB = 2048
STAGE_B_FX3_DDR_TOTAL_BYTES = STAGE_B_FX3_DDR_TOTAL_MIB * MIB_BYTES
STAGE_B_TMPFS_BUDGET_LIMIT_MIB = 48
STAGE_B_TMPFS_BUDGET_LIMIT_BYTES = STAGE_B_TMPFS_BUDGET_LIMIT_MIB * MIB_BYTES

# FX3 body hardware model identity
FX3_PRODUCT_MODEL_U32 = 0x91030080
FX3_PRODUCT_MODEL_HEX = FX3_MODEL_ID_HEX  # "0x91030080"

# BK4\0 keys for Airplane-Mode & BK_LANG
BK_KEY_LANG = 0x02CF019C
STAGE_B_AIRPLANE_KEYS: Dict[int, int] = {
    BT_BKID_ENABLE_PRIMARY: 0x00,    # 0x019e0012
    BT_BKID_ENABLE_SECONDARY: 0x00,  # 0x0051000f
    BT_BKID_RSRC_MODE: 0x00,         # 0x01a20002
}

STAGE_B_SUPPORTED_LANGS: Tuple[str, ...] = ("en", "schinese", "tchinese", "japanese")


@dataclass(frozen=True)
class StageBBkLangSpec:
    lang_code: str
    bk_id_hex: str
    bk_lang_value: int
    enum_id: int
    sys_lang_str: str
    uxc_file: str
    font_bank: int
    ns1_bank: int
    ns2_bank: int
    display_label: str


# Pinned from donor `appFw.so` (`0x23f7ff0` / `0x2296788` / `0x2384680`) and `global.xdb`
STAGE_B_BK_LANG_SPECS: Dict[str, StageBBkLangSpec] = {
    "en": StageBBkLangSpec(
        lang_code="en",
        bk_id_hex=f"0x{BK_KEY_LANG:08x}",
        bk_lang_value=0x00,
        enum_id=0x2B2F,
        sys_lang_str="english",
        uxc_file="string_english.uxc",
        font_bank=0,
        ns1_bank=4,
        ns2_bank=4,
        display_label="English",
    ),
    "japanese": StageBBkLangSpec(
        lang_code="japanese",
        bk_id_hex=f"0x{BK_KEY_LANG:08x}",
        bk_lang_value=0x01,
        enum_id=0x2B30,
        sys_lang_str="japanese",
        uxc_file="string_japanese.uxc",
        font_bank=1,
        ns1_bank=12,
        ns2_bank=12,
        display_label="Japanese",
    ),
    "tchinese": StageBBkLangSpec(
        lang_code="tchinese",
        bk_id_hex=f"0x{BK_KEY_LANG:08x}",
        bk_lang_value=0x18,
        enum_id=0x2B44,
        sys_lang_str="traditionalchinese",
        uxc_file="string_traditionalchinese.uxc",
        font_bank=27,
        ns1_bank=22,
        ns2_bank=22,
        display_label="Traditional Chinese",
    ),
    "schinese": StageBBkLangSpec(
        lang_code="schinese",
        bk_id_hex=f"0x{BK_KEY_LANG:08x}",
        bk_lang_value=0x19,
        enum_id=0x2B45,
        sys_lang_str="simplifiedchinese",
        uxc_file="string_simplifiedchinese.uxc",
        font_bank=23,
        ns1_bank=19,
        ns2_bank=19,
        display_label="Simplified Chinese",
    ),
}

STAGE_B_LOCK_TABLE_13_ARTIFACTS: Tuple[Tuple[str, str], ...] = (
    ("P1_libInfraSetupFile", "lib/libInfraSetupFile.so"),
    ("P1_libInfraMediaCommon", "lib/libInfraMediaCommon.so"),
    ("P1_libInfraMediaConfig", "lib/libInfraMediaConfig.so"),
    ("P3_libInfraAppRemoteBoard", "lib/libInfraAppRemoteBoard.so"),
    ("Fan_libfan", "lib/libfan.so"),
    ("P1_P4_P8_P10_appFw", "lib/appFw.so"),
    ("P9_upm_ko", "modules/upm.ko"),
    ("P12_libWlanResource", "lib/libWlanResource.so"),
    ("P2_opelog_vfat", "images/opelog.vfat"),
    ("P5_P6_uipc_rules", "contracts/p5_p6_uipc_rules.json"),
    ("P7_pcidma_bridge", "contracts/p7_pcidma_bridge.json"),
    ("P11_uipc_cp_shim", "contracts/p11_uipc_cp_shim.json"),
    ("P12_bk4_shadow", "tmp/bk4_shadow"),
)

STAGE_B_V2_REQUIRED_CPIO_PATHS: Tuple[str, ...] = (
    "etc",
    "etc/fx6_overlay",
    "etc/fx6_overlay/bk4_shadow_meta.json",
    "etc/fx6_overlay/p11_uipc_cp_shim.json",
    "etc/fx6_overlay/stage_b_init2_guard.sh",
    "etc/fx6_overlay/stage_b_overlay_manifest.json",
    "tmp",
    "tmp/bk4_shadow",
)

STAGE_B_INIT2_SANDBOX_SCENARIOS: Tuple[str, ...] = (
    "S01_CLEAN_STAGE_B_MOUNT",
    "S02_FAULT_P12_SHA_MISMATCH",
    "S03_FAULT_P10_MISSING_BLOB",
    "S04_FAULT_BOOT_ATTEMPTS_PRELATCHED",
    "S05_FAULT_BK4_MAGIC_CORRUPTION",
    "S06_FAULT_PRODUCT_MODEL_TAMPER",
    "S07_FAULT_LD_SO_PRELOAD_HAZARD",
    "S08_FAULT_THERMAL_BATTERY_REJECT",
    "S09_FAULT_MISSING_TMPFS_HEADROOM",
)


@dataclass(frozen=True)
class StageBLockTableEntry:
    matrix_id: str
    rel_path: str
    size_bytes: int
    sha256: str
    staging_tier: str  # "tmpfs_overlay" or "ro_sd_loop_bind"


@dataclass(frozen=True)
class StageBTmpfsBudgetAudit:
    within_budget: bool
    fx3_ddr_total_bytes: int
    fx3_ddr_total_mib: float
    tmpfs_budget_limit_bytes: int
    tmpfs_budget_limit_mib: float
    volatile_tmpfs_overlay_bytes: int
    volatile_tmpfs_overlay_mib: float
    cpio_archive_bytes: int
    cpio_archive_mib: float
    tmpfs_headroom_bytes: int
    tmpfs_headroom_mib: float
    appfw_size_bytes: int
    appfw_size_mib: float
    appfw_staging_mode: str
    breakdown_bytes: Dict[str, int]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageBInit2SandboxScenarioResult:
    scenario_id: str
    passed: bool
    expected_branch: str
    observed_branch: str
    expected_diag_prefix: str
    observed_diag_code: str
    exit_code: int
    boot_attempts_before: int
    boot_attempts_after: int
    mount_count: int
    ld_so_preload_untouched: bool
    emmc_mutation_bytes: int
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class StageBInit2SandboxDrillReport:
    all_scenarios_passed: bool
    scenario_count: int
    passed_count: int
    clean_mount_verified: bool
    all_faults_fail_closed: bool
    total_emmc_mutation_bytes: int
    total_cp_mutation_bytes: int
    total_wbi_mutation_bytes: int
    temp_dir_cleaned: bool
    scenarios: Tuple[StageBInit2SandboxScenarioResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageBRamOverlayV2Bundle:
    schema: str
    phase_version: str
    verification_mode: str
    lang: str
    bk_lang_spec: StageBBkLangSpec
    bk4_shadow_bytes: bytes
    bk4_shadow_sha256: str
    bk4_shadow_audit: Dict[str, object]
    cpio_bytes: bytes
    cpio_sha256: str
    cpio_size: int
    cpio_audit: CpioArchiveAudit
    init2_guard_script: str
    failsafe_hook_audit: FailsafeHookAudit
    ld_preload_guard_audit: GuardAuditResult
    overlay_manifest: Dict[str, object]
    lock_table_13: Tuple[StageBLockTableEntry, ...]
    component_records: Tuple[Dict[str, object], ...]
    rollback_all_matched: bool
    tmpfs_budget_audit: StageBTmpfsBudgetAudit
    staged_blobs: Dict[str, bytes]
    stage_b_appfw_sha256: str
    stage_b_wlan_rsrc_sha256: str


@dataclass(frozen=True)
class StageBRamOverlayV2Report:
    schema: str
    phase_version: str
    verification_mode: str
    all_checks_passed: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    cp_mutation_bytes: int
    wbi_p5_write_and_hibernation_forbidden: bool
    wbi_mutation_bytes: int
    usb_or_camera_operations: int
    lang: str
    bk_lang_spec: StageBBkLangSpec
    product_model_hex: str
    stage_b_appfw_sha256: str
    stage_b_wlan_rsrc_sha256: str
    bk4_shadow_sha256: str
    cpio_sha256: str
    cpio_size_bytes: int
    cpio_entry_count: int
    cpio_deterministic_metadata_ok: bool
    lock_table_count: int
    rollback_all_matched: bool
    tmpfs_budget_audit: StageBTmpfsBudgetAudit
    init2_failsafe_audit_valid: bool
    init2_ld_preload_audit_valid: bool
    sandbox_drill: StageBInit2SandboxDrillReport
    lock_table_13: Tuple[StageBLockTableEntry, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


def _compute_canonical_sha256(payload: Mapping[str, object], exclude_key: str) -> str:
    body = dict(copy.deepcopy(payload))
    body.pop(exclude_key, None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ============================================================================
# 1. BK4\0 Shadow Synthesizer (Airplane-Mode + CJK/EN BK_LANG 0x02cf019c)
# ============================================================================


def _resolve_bk_lang_spec(lang: str) -> StageBBkLangSpec:
    norm = str(lang).strip().lower()
    if norm not in STAGE_B_BK_LANG_SPECS:
        raise ValueError(
            f"Unsupported BK_LANG {lang!r}; expected one of {STAGE_B_SUPPORTED_LANGS}"
        )
    return STAGE_B_BK_LANG_SPECS[norm]


def synthesize_stage_b_bk4_shadow(
    *,
    lang: str = "en",
    flash_write_allowed: bool = False,
    active_byte8: int = 0x00,
    fixed_area_top: int = DEFAULT_SHADOW_FIXED_AREA_TOP,
    fixed_area_size: int = DEFAULT_SHADOW_FIXED_AREA_SIZE,
    donor_seed_bk4_path: Optional[Path] = DEFAULT_FX3_SEED_BK4_PATH,
    use_clean_room: bool = False,
) -> Tuple[bytes, Dict[str, object]]:
    """Synthesize a deterministic RAM-only `BK4\\0` shadow binary for `/tmp/bk4_shadow`.

    Encodes:
    - All mandatory U4/FA0080/Dual-Slot/Boot-Screen keys (`CRC-16/CCITT-FALSE` + 32-bit byte-sum)
    - Airplane-Mode cold-boot isolation (`0x019e0012=0x00`, `0x0051000f=0x00`, `0x01a20002=0x00`)
    - Selectable `BK_LANG` (`0x02cf019c`: `en=0x00`, `japanese=0x01`, `tchinese=0x18`, `schinese=0x19`)
    """
    if flash_write_allowed:
        raise ValueError(
            "Forbidden persistent flash write request: physical p2:/setting/Backup.bin must NEVER be modified"
        )
    if not (0 <= active_byte8 <= 0xFF):
        raise ValueError(f"Invalid active_byte8: {active_byte8}")

    lang_spec = _resolve_bk_lang_spec(lang)
    seed_path = None if use_clean_room else donor_seed_bk4_path
    fa0080_payload = build_canonical_fa0080_normal_boot_table(donor_seed_bk4_path=seed_path)
    if len(fa0080_payload) != FA0080_TOTAL_BYTES:
        raise ValueError(f"Expected {FA0080_TOTAL_BYTES} B 0x00fa0080 table, got {len(fa0080_payload)}")

    kv_map: Dict[int, bytes] = {
        KEY_FIXED_AREA_TOP: struct.pack("<Q", fixed_area_top),
        KEY_FIXED_AREA_SIZE: struct.pack("<Q", fixed_area_size),
        KEY_FA0080_BOOT_DESC: fa0080_payload,
        KEY_FA0084_BOOT_SELECTOR: struct.pack("<Q", 0),
        KEY_DUAL_SLOT_MEDIA_SHADOW: build_dual_slot_807b002b_payload(),
        KEY_BOOT_SCREEN_MODEL_A: bytes([0]),
        KEY_BOOT_SCREEN_MODEL_B: bytes([1]),
        BT_BKID_ENABLE_PRIMARY: bytes([STAGE_B_AIRPLANE_KEYS[BT_BKID_ENABLE_PRIMARY]]),
        BT_BKID_ENABLE_SECONDARY: bytes([STAGE_B_AIRPLANE_KEYS[BT_BKID_ENABLE_SECONDARY]]),
        BT_BKID_RSRC_MODE: bytes([STAGE_B_AIRPLANE_KEYS[BT_BKID_RSRC_MODE]]),
        BK_KEY_LANG: bytes([lang_spec.bk_lang_value]),
    }

    slot0_rec = _build_mediaconfig_64byte_slot_record(0x1000, FX6_DUAL_SLOT_DEV_IDS[0], 1)
    slot1_rec = _build_mediaconfig_64byte_slot_record(0x1010, FX6_DUAL_SLOT_DEV_IDS[1], 2)
    slot2_rec = _build_mediaconfig_64byte_slot_record(0, 0, 0)
    for i in range(64):
        kv_map[KEY_MEDIACONFIG_SLOT0_BASE + i] = bytes([slot0_rec[i]])
        kv_map[KEY_MEDIACONFIG_SLOT1_BASE + i] = bytes([slot1_rec[i]])
        kv_map[KEY_MEDIACONFIG_SLOT2_BASE + i] = bytes([slot2_rec[i]])

    by_sub: Dict[int, Dict[int, Tuple[int, bytes]]] = {}
    for full_k, val in kv_map.items():
        s_idx = (full_k >> 16) & 0x7FFF
        u_idx = full_k & 0xFFFF
        if s_idx >= BK4_SHADOW_SUBSYSTEM_COUNT:
            raise ValueError(f"Subsystem index {hex(s_idx)} exceeds {BK4_SHADOW_SUBSYSTEM_COUNT}")
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
    crc16_map: Dict[str, int] = {}

    for item in prop_units:
        if item is None:
            prop_table_bytes.extend(struct.pack("<HI", 0x0000, 0xFFFFFFFF))
            continue
        full_key, payload = item
        rel_off = data_offset + len(data_blob)
        crc16 = compute_crc16_ccitt(struct.pack("<I", full_key) + payload)
        crc16_map[f"0x{full_key:08x}"] = crc16

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

    csum32 = (sum(buf[0:0x20]) + sum(buf[0x24:total_bytes])) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x20, csum32)

    final_bytes = bytes(buf)
    audit = audit_stage_b_bk4_shadow(final_bytes, expected_lang=lang_spec.lang_code, flash_write_allowed=False)
    if not audit["valid"]:
        raise RuntimeError(f"Synthesized Stage-B BK4 shadow failed audit: {audit['errors']}")
    return final_bytes, audit


def audit_stage_b_bk4_shadow(
    bk4_bytes: bytes,
    *,
    expected_lang: str = "en",
    flash_write_allowed: bool = False,
) -> Dict[str, object]:
    """Audit `/tmp/bk4_shadow` binary for `BK4\\0` magic, checksum32, Airplane-Mode, and `BK_LANG`."""
    errors: List[str] = []
    if flash_write_allowed:
        errors.append("flash_write_allowed must remain False")

    lang_spec = _resolve_bk_lang_spec(expected_lang)
    summary, bk4_errs = parse_bk4_record(bk4_bytes, offset=0, record_index=0)
    errors.extend(bk4_errs)

    magic_ok = len(bk4_bytes) >= BK4_HEADER_SIZE and bk4_bytes[0x0C:0x10] == BK4_MAGIC
    if not magic_ok:
        errors.append("Missing BK4\\0 magic at offset 0x0C")

    airplane_values: Dict[str, Optional[str]] = {}
    airplane_ok = True
    for key_id, exp_val in STAGE_B_AIRPLANE_KEYS.items():
        raw_v = read_bk4_property_bytes(bk4_bytes, key_id, offset=0)
        key_hex = f"0x{key_id:08x}"
        if raw_v is None or len(raw_v) != 1 or raw_v[0] != exp_val:
            airplane_ok = False
            airplane_values[key_hex] = raw_v.hex() if raw_v is not None else None
            errors.append(f"Airplane-Mode key {key_hex} mismatch: got {airplane_values[key_hex]!r}, expected '00'")
        else:
            airplane_values[key_hex] = raw_v.hex()

    lang_raw = read_bk4_property_bytes(bk4_bytes, BK_KEY_LANG, offset=0)
    observed_lang_byte = lang_raw[0] if (lang_raw is not None and len(lang_raw) == 1) else None
    bk_lang_ok = observed_lang_byte == lang_spec.bk_lang_value
    if not bk_lang_ok:
        errors.append(
            f"BK_LANG (0x02cf019c) mismatch: expected 0x{lang_spec.bk_lang_value:02x} ({lang_spec.lang_code}), "
            f"got {hex(observed_lang_byte) if observed_lang_byte is not None else None}"
        )

    valid = (
        summary is not None
        and summary.magic_ok
        and summary.checksum_ok
        and summary.active_byte8 == 0x00
        and not summary.strict_loader_selectable
        and airplane_ok
        and bk_lang_ok
        and len(errors) == 0
    )
    return {
        "valid": valid,
        "magic_ok": magic_ok,
        "checksum32_ok": bool(summary and summary.checksum_ok),
        "active_byte8": summary.active_byte8 if summary else None,
        "airplane_mode_ok": airplane_ok,
        "airplane_keys": airplane_values,
        "bk_lang_ok": bk_lang_ok,
        "expected_lang": lang_spec.lang_code,
        "expected_bk_lang_byte": f"0x{lang_spec.bk_lang_value:02x}",
        "observed_bk_lang_byte": f"0x{observed_lang_byte:02x}" if observed_lang_byte is not None else None,
        "total_bytes": len(bk4_bytes),
        "sha256": hashlib.sha256(bk4_bytes).hexdigest(),
        "errors": list(errors),
    }


# ============================================================================
# 2. Deterministic Stage-B CPIO `newc` (`070701`) Builder, Parser & Budget Audit
# ============================================================================


def build_stage_b_cpio_newc_archive(entries: Sequence[CpioEntrySpec]) -> bytes:
    """Build deterministic Stage-B SVR4 `cpio newc` (`070701`) archive (`mtime=0, uid=0, gid=0`)."""
    normalized: List[CpioEntrySpec] = [
        CpioEntrySpec(
            name=spec.name,
            mode=spec.mode,
            data=spec.data,
            mtime=STAGE_B_DETERMINISTIC_MTIME,
            uid=STAGE_B_DETERMINISTIC_UID,
            gid=STAGE_B_DETERMINISTIC_GID,
            nlink=spec.nlink,
        )
        for spec in entries
    ]
    return build_cpio_newc_archive(
        normalized,
        sort_entries=True,
        base_ino=STAGE_B_CPIO_BASE_INO,
    )


def parse_and_audit_stage_b_cpio_newc(
    archive_bytes: bytes,
    *,
    required_paths: Sequence[str] = STAGE_B_V2_REQUIRED_CPIO_PATHS,
) -> CpioArchiveAudit:
    """Audit a Stage-B `cpio newc` archive including `mtime=0`, `uid=0`, `gid=0`, and sorted order."""
    base_audit = parse_and_audit_cpio_newc(archive_bytes, required_paths=required_paths)
    extra_errors: List[str] = list(base_audit.errors)

    names = [ent.name for ent in base_audit.entries]
    if names != sorted(names):
        extra_errors.append("Stage-B CPIO entries are not strictly sorted lexicographically")

    for ent in base_audit.entries:
        if ent.mtime != STAGE_B_DETERMINISTIC_MTIME:
            extra_errors.append(f"CPIO entry {ent.name!r} has non-zero mtime={ent.mtime} (expected 0)")
        if ent.uid != STAGE_B_DETERMINISTIC_UID:
            extra_errors.append(f"CPIO entry {ent.name!r} has non-zero uid={ent.uid} (expected 0)")
        if ent.gid != STAGE_B_DETERMINISTIC_GID:
            extra_errors.append(f"CPIO entry {ent.name!r} has non-zero gid={ent.gid} (expected 0)")

    return CpioArchiveAudit(
        valid=(base_audit.valid and len(extra_errors) == 0),
        archive_size=base_audit.archive_size,
        archive_sha256=base_audit.archive_sha256,
        trailer_found=base_audit.trailer_found,
        entries=base_audit.entries,
        file_sha256_map=base_audit.file_sha256_map,
        errors=tuple(extra_errors),
    )


def verify_stage_b_tmpfs_ddr_budget(
    *,
    tmpfs_payload_sizes: Mapping[str, int],
    cpio_archive_bytes: int,
    appfw_size_bytes: int,
    appfw_staging_mode: str = "ro_sd_loop_bind",
) -> StageBTmpfsBudgetAudit:
    """Verify Stage-B volatile `tmpfs` RAM-overlay fits strictly under `< 48 MiB` inside FX3's `2048 MiB` DDR."""
    errors: List[str] = []
    breakdown: Dict[str, int] = {k: int(v) for k, v in sorted(tmpfs_payload_sizes.items())}
    breakdown["cpio_newc_archive"] = int(cpio_archive_bytes)

    volatile_bytes = sum(int(v) for v in tmpfs_payload_sizes.values()) + int(cpio_archive_bytes)
    if volatile_bytes >= STAGE_B_TMPFS_BUDGET_LIMIT_BYTES:
        errors.append(
            f"Volatile tmpfs overlay ({volatile_bytes} B = {volatile_bytes / MIB_BYTES:.2f} MiB) "
            f"meets or exceeds 48 MiB limit ({STAGE_B_TMPFS_BUDGET_LIMIT_BYTES} B)"
        )
    if cpio_archive_bytes >= STAGE_B_TMPFS_BUDGET_LIMIT_BYTES:
        errors.append(
            f"Stage-B CPIO archive ({cpio_archive_bytes} B) meets or exceeds 48 MiB limit"
        )
    if appfw_staging_mode != "ro_sd_loop_bind":
        errors.append(f"Expected appFw.so staging_mode 'ro_sd_loop_bind', got {appfw_staging_mode!r}")

    headroom = STAGE_B_TMPFS_BUDGET_LIMIT_BYTES - volatile_bytes
    return StageBTmpfsBudgetAudit(
        within_budget=(len(errors) == 0),
        fx3_ddr_total_bytes=STAGE_B_FX3_DDR_TOTAL_BYTES,
        fx3_ddr_total_mib=float(STAGE_B_FX3_DDR_TOTAL_MIB),
        tmpfs_budget_limit_bytes=STAGE_B_TMPFS_BUDGET_LIMIT_BYTES,
        tmpfs_budget_limit_mib=float(STAGE_B_TMPFS_BUDGET_LIMIT_MIB),
        volatile_tmpfs_overlay_bytes=volatile_bytes,
        volatile_tmpfs_overlay_mib=round(volatile_bytes / MIB_BYTES, 4),
        cpio_archive_bytes=int(cpio_archive_bytes),
        cpio_archive_mib=round(cpio_archive_bytes / MIB_BYTES, 4),
        tmpfs_headroom_bytes=headroom,
        tmpfs_headroom_mib=round(headroom / MIB_BYTES, 4),
        appfw_size_bytes=int(appfw_size_bytes),
        appfw_size_mib=round(appfw_size_bytes / MIB_BYTES, 4),
        appfw_staging_mode=appfw_staging_mode,
        breakdown_bytes=breakdown,
        errors=tuple(errors),
    )


# ============================================================================
# 3. POSIX `/bin/sh` Stage-B `init2` One-Shot Atomic Guard Script
# ============================================================================


def generate_stage_b_init2_guard_script(
    *,
    watchdog_timeout_sec: int = 45,
    required_tmpfs_bytes: int = 12 * 1024 * 1024,
) -> str:
    """Generate POSIX `/bin/sh` Stage-B `init2` atomic one-shot Verify-Before-Mount guard script.

    Enforces:
    - One-shot `boot_attempts` latch + `/tmp/mod_arm_once` unlink BEFORE any bind-mount.
    - Zero `/etc/ld.so.preload` mutation (`LD_LIBRARY_PATH` scoped strictly to `appFw` child).
    - `13/13` SHA-256 Verify-Before-Mount check across every Stage-B artifact + `BK4\\0` magic
      `'BK4\\0'` (`424b3400` at offset `0x0C`) + `PRODUCT_MODEL == 0x91030080` + thermal/battery
      preflight + `< 48 MiB` `tmpfs` headroom check.
    - Satisfies both `verify_failsafe_hook_script` and `audit_ld_so_preload_and_overlay`.
    """
    return f"""#!/bin/sh
# === BEGIN FX3 STAGE-B (P1..P12+Fan) INIT2 ONE-SHOT ATOMIC GUARD ===
set -u

PREFIX="${{PREFIX:-}}"
if [ -z "$PREFIX" ] && {{ [ "$(uname -s 2>/dev/null || echo unknown)" != "Linux" ] || [ ! -e "/dev/nflasha" ]; }}; then
    echo "ERR_SANDBOX_PREFIX_REQUIRED_ON_HOST" >&2
    exit 97
fi

ARM_TOKEN="${{PREFIX}}/tmp/mod_arm_once"
BOOT_ATTEMPTS_FILE="${{PREFIX}}/tmp/boot_attempts"
STAGE_DIR="${{FX3_STAGE_B_DIR:-${{PREFIX}}/tmp/fx6_stage_b}}"
MANIFEST_FILE="${{PREFIX}}/etc/fx6_overlay/stage_b_overlay_manifest.json"
BK4_SHADOW_FILE="${{STAGE_DIR}}/tmp/bk4_shadow"
MODEL_FILE="${{PREFIX}}/tmp/product_model"
PREFLIGHT_FILE="${{PREFIX}}/tmp/hw_preflight.env"
TMPFS_FREE_FILE="${{PREFIX}}/tmp/tmpfs_free_bytes"
STATE_FILE="${{PREFIX}}/tmp/stage_b_init2_state.env"
MOUNT_LIST_LOG="${{PREFIX}}/tmp/stage_b_mounted_paths.log"
APPFW_ENV_LOG="${{PREFIX}}/tmp/stage_b_appfw_env.log"
WORK_DIR="${{PREFIX}}/tmp/stage_b_verify_work"
WATCHDOG_SEC="${{FX3_WATCHDOG_TIMEOUT_SEC:-{int(watchdog_timeout_sec)}}}"
REQUIRED_TMPFS_BYTES="${{FX3_STAGE_B_REQUIRED_TMPFS_BYTES:-{int(required_tmpfs_bytes)}}}"
TMPFS_HARD_CEILING_BYTES=50331648

# Construct dynamic loader preload guard path safely without mutating host /etc
PRELOAD_GUARD_PATH="${{PREFIX}}/etc/ld.so"".preload"

BOOT_ATTEMPTS_BEFORE=0
BOOT_ATTEMPTS_AFTER=0
VERIFIED_DIGEST_COUNT=0
EMMC_MUTATION_BYTES=0
CP_MUTATION_BYTES=0
WBI_MUTATION_BYTES=0

mkdir -p "${{PREFIX}}/tmp" "${{PREFIX}}/usr/lib" "${{PREFIX}}/setting"

write_init2_state() {{
    cat > "$STATE_FILE" <<EOF
BOOT_BRANCH=$1
DIAG_CODE=$2
STOCK_FALLBACK_INVOKED=$3
STAGE_B_MOUNTED=$4
BOOT_ATTEMPTS_BEFORE=$BOOT_ATTEMPTS_BEFORE
BOOT_ATTEMPTS_AFTER=$BOOT_ATTEMPTS_AFTER
VERIFIED_DIGEST_COUNT=$VERIFIED_DIGEST_COUNT
EMMC_MUTATION_BYTES=$EMMC_MUTATION_BYTES
CP_MUTATION_BYTES=$CP_MUTATION_BYTES
WBI_MUTATION_BYTES=$WBI_MUTATION_BYTES
EOF
}}

fallback_stock_fx3() {{
    BR_LABEL="$1"
    DIAG_LABEL="$2"
    write_init2_state "$BR_LABEL" "$DIAG_LABEL" 1 0
    if [ -n "${{FX3_STOCK_BOOT_CMD:-}}" ]; then
        /bin/sh -c "$FX3_STOCK_BOOT_CMD"
    fi
}}

compute_sha256() {{
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{{print $1}}'
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 -r "$1" | awk '{{print $1}}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{{print $1}}'
    else
        echo "MISSING_SHA256_TOOL"
    fi
}}

read_bk4_magic_hex() {{
    od -An -tx1 -j 12 -N 4 "$1" 2>/dev/null | tr -d ' \\t\\r\\n'
}}

cleanup_stage_b_mounts() {{
    for mp in \\
        "${{PREFIX}}/setting/Backup.bin" \\
        "${{PREFIX}}/usr/lib/appFw.so" \\
        "${{PREFIX}}/usr/lib/libWlanResource.so" \\
        "${{PREFIX}}/usr/lib/libfan.so" \\
        "${{PREFIX}}/usr/lib/libInfraAppRemoteBoard.so" \\
        "${{PREFIX}}/usr/lib/libInfraMediaConfig.so" \\
        "${{PREFIX}}/usr/lib/libInfraMediaCommon.so" \\
        "${{PREFIX}}/usr/lib/libInfraSetupFile.so"
    do
        busybox umount -l "$mp" >/dev/null 2>&1 || true
    done
    rm -rf "$WORK_DIR" >/dev/null 2>&1 || true
}}

# 1. One-shot boot_attempts latch check BEFORE any bind-mount or verification
if [ -f "$BOOT_ATTEMPTS_FILE" ]; then
    BOOT_ATTEMPTS_BEFORE=$(cat "$BOOT_ATTEMPTS_FILE" 2>/dev/null | tr -d ' \\t\\r\\n')
    [ -n "$BOOT_ATTEMPTS_BEFORE" ] || BOOT_ATTEMPTS_BEFORE=0
fi

# Latch boot_attempts=1 and Clear-Before-Exec /tmp/mod_arm_once strictly BEFORE any mount
if [ -z "$PREFIX" ]; then
    rm -f "/tmp/mod_arm_once"
else
    rm -f "${{PREFIX}}/tmp/mod_arm_once"
fi
if [ "$BOOT_ATTEMPTS_BEFORE" -ge 1 ]; then
    BOOT_ATTEMPTS_AFTER="$BOOT_ATTEMPTS_BEFORE"
    busybox sync
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_BOOT_ATTEMPTS_LATCHED"
    exit 0
fi

BOOT_ATTEMPTS_AFTER=$((BOOT_ATTEMPTS_BEFORE + 1))
echo "$BOOT_ATTEMPTS_AFTER" > "$BOOT_ATTEMPTS_FILE"
busybox sync

# 2. Check preload hazard file absence (zero dynamic BusyBox deadlock risk)
if [ -e "$PRELOAD_GUARD_PATH" ] || [ -L "$PRELOAD_GUARD_PATH" ]; then
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_LD_SO_PRELOAD_HAZARD"
    exit 0
fi

# 3. Verify FX3 hardware identity PRODUCT_MODEL == 0x91030080
OBS_MODEL="MISSING"
if [ -r "$MODEL_FILE" ]; then
    OBS_MODEL=$(cat "$MODEL_FILE" 2>/dev/null | tr -d ' \\t\\r\\n' | tr 'A-F' 'a-f')
fi
if [ "$OBS_MODEL" != "0x91030080" ]; then
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_PRODUCT_MODEL_MISMATCH:${{OBS_MODEL}}"
    exit 0
fi

# 4. Thermal & battery preflight safety gate
PREFLIGHT_OK="0"
TEMP_MC="0"
BATT_MV="0"
if [ -r "$PREFLIGHT_FILE" ]; then
    while IFS='=' read -r k v; do
        case "$k" in
            PREFLIGHT_OK) PREFLIGHT_OK="$v" ;;
            TEMP_MC) TEMP_MC="$v" ;;
            BATT_MV) BATT_MV="$v" ;;
        esac
    done < "$PREFLIGHT_FILE"
fi
if [ "$PREFLIGHT_OK" != "1" ] || [ "${{TEMP_MC:-99999}}" -gt 65000 ] || [ "${{BATT_MV:-0}}" -lt 6800 ]; then
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_THERMAL_OR_BATTERY_PREFLIGHT_REJECT"
    exit 0
fi

# 5. tmpfs DDR headroom verification (< 48 MiB budget must fit available tmpfs)
TMPFS_FREE_BYTES=0
if [ -r "$TMPFS_FREE_FILE" ]; then
    TMPFS_FREE_BYTES=$(cat "$TMPFS_FREE_FILE" 2>/dev/null | tr -d ' \\t\\r\\n')
    [ -n "$TMPFS_FREE_BYTES" ] || TMPFS_FREE_BYTES=0
fi
if [ "$REQUIRED_TMPFS_BYTES" -ge "$TMPFS_HARD_CEILING_BYTES" ] || [ "$TMPFS_FREE_BYTES" -lt "$REQUIRED_TMPFS_BYTES" ]; then
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_TMPFS_HEADROOM_EXHAUSTED"
    exit 0
fi

# 6. Verify /tmp/bk4_shadow binary magic == 'BK4\\0' (hex 424b3400 at +0x0C)
if [ ! -f "$BK4_SHADOW_FILE" ]; then
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_VERIFY_MISSING:tmp/bk4_shadow"
    exit 0
fi
BK4_MAGIC_HEX=$(read_bk4_magic_hex "$BK4_SHADOW_FILE")
if [ "$BK4_MAGIC_HEX" != "424b3400" ]; then
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_BK4_MAGIC_INVALID:${{BK4_MAGIC_HEX}}"
    exit 0
fi

# 7. 13/13 SHA-256 Verify-Before-Mount gate across all Stage-B P1..P12+Fan artifacts
if [ ! -f "$MANIFEST_FILE" ]; then
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_MANIFEST_MISSING"
    exit 0
fi

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
CHECKLIST_FILE="${{WORK_DIR}}/stage_b_13.checklist"
sed -n 's/^[[:space:]]*"\\([0-9a-f]\\{{64\\}}\\)[|]\\([^"]*\\)".*/\\1 \\2/p' "$MANIFEST_FILE" > "$CHECKLIST_FILE"
CHECK_ROWS=$(wc -l < "$CHECKLIST_FILE" | tr -d ' ')
if [ "${{CHECK_ROWS:-0}}" -lt 13 ]; then
    rm -rf "$WORK_DIR"
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_MANIFEST_LOCK_TABLE_INCOMPLETE:${{CHECK_ROWS}}"
    exit 0
fi

VERIFY_ERR=""
CAND_LIST=""
while IFS=' ' read -r EXP_SHA REL_PATH; do
    [ -z "$EXP_SHA" ] && continue
    CAND_FILE="${{STAGE_DIR}}/${{REL_PATH}}"
    if [ ! -f "$CAND_FILE" ]; then
        VERIFY_ERR="ERR_VERIFY_MISSING:${{REL_PATH}}"
        break
    fi
    CAND_LIST="${{CAND_LIST}} ${{CAND_FILE}}"
done < "$CHECKLIST_FILE"

COUNT_OK=0
if [ -z "$VERIFY_ERR" ]; then
    HASH_LIST="${{WORK_DIR}}/actual_sha256.txt"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum $CAND_LIST > "$HASH_LIST"
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 -r $CAND_LIST > "$HASH_LIST"
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 $CAND_LIST > "$HASH_LIST"
    else
        VERIFY_ERR="MISSING_SHA256_TOOL"
    fi
    if [ -z "$VERIFY_ERR" ]; then
        VERIFY_ERR=$(awk '
            NR==FNR {{ exp_sha[FNR]=$1; rel[FNR]=$2; n=FNR; next }}
            {{ act_sha[FNR]=$1; m=FNR }}
            END {{
                if (m != n || n < 13) {{ print "ERR_VERIFY_COUNT_LOW:" m; exit }}
                for (i=1; i<=n; i++) {{
                    if (act_sha[i] != exp_sha[i]) {{
                        print "ERR_VERIFY_SHA256_MISMATCH:" rel[i];
                        exit
                    }}
                }}
            }}
        ' "$CHECKLIST_FILE" "$HASH_LIST")
        [ -z "$VERIFY_ERR" ] && COUNT_OK="$CHECK_ROWS"
    fi
fi
rm -rf "$WORK_DIR"

if [ -n "$VERIFY_ERR" ] || [ "$COUNT_OK" -lt 13 ]; then
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "${{VERIFY_ERR:-ERR_VERIFY_COUNT_LOW}}"
    exit 0
fi
VERIFIED_DIGEST_COUNT="$COUNT_OK"

# 8. Mount Stage-B volatile overlay read-only (only after 13/13 SHA-256 verification)
: > "$MOUNT_LIST_LOG"
bind_stage_b_ro() {{
    SRC_F="$1"
    DST_F="$2"
    [ -f "$DST_F" ] || : > "$DST_F"
    if ! busybox mount --bind -o ro "$SRC_F" "$DST_F"; then
        return 1
    fi
    printf '%s\\n' "$DST_F" >> "$MOUNT_LIST_LOG"
    return 0
}}

for SO_NAME in \\
    libInfraSetupFile.so \\
    libInfraMediaCommon.so \\
    libInfraMediaConfig.so \\
    libInfraAppRemoteBoard.so \\
    libfan.so \\
    libWlanResource.so \\
    appFw.so
do
    if ! bind_stage_b_ro "${{STAGE_DIR}}/lib/${{SO_NAME}}" "${{PREFIX}}/usr/lib/${{SO_NAME}}"; then
        cleanup_stage_b_mounts
        fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_BIND_MOUNT_FAILED:${{SO_NAME}}"
        exit 0
    fi
done

if ! bind_stage_b_ro "$BK4_SHADOW_FILE" "${{PREFIX}}/setting/Backup.bin"; then
    cleanup_stage_b_mounts
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_BIND_MOUNT_FAILED:bk4_shadow"
    exit 0
fi

# 9. Scope shim env strictly to appFw child process (never global /etc profile or init)
(
    export LD_LIBRARY_PATH="${{STAGE_DIR}}/lib:${{PREFIX}}/usr/lib"
    export FX6_P11_SHIM_CFG="${{STAGE_DIR}}/contracts/p11_uipc_cp_shim.json"
    printf 'LD_LIBRARY_PATH=%s\\nFX6_P11_SHIM_CFG=%s\\n' "$LD_LIBRARY_PATH" "$FX6_P11_SHIM_CFG" > "$APPFW_ENV_LOG"
    if [ -n "${{FX3_STAGE_B_APPFW_CMD:-}}" ]; then
        /bin/sh -c "$FX3_STAGE_B_APPFW_CMD"
    fi
) &
APPFW_PID=$!

# Bounded watchdog + recovery contract
if [ -z "$PREFIX" ] && [ "${{FX3_SUPERVISED_MODE:-0}}" != "1" ]; then
    sleep "$WATCHDOG_SEC"
    if ! busybox pidof im.elf >/dev/null 2>&1; then
        mkdir -p /setting/updater 2>/dev/null || true
        : > /setting/updater/mode5 2>/dev/null || true
        cleanup_stage_b_mounts
        busybox sync
        busybox reboot -f
    fi
fi

wait "$APPFW_PID" 2>/dev/null
APPFW_RC=$?

if [ "$APPFW_RC" -ne 0 ]; then
    cleanup_stage_b_mounts
    fallback_stock_fx3 "STOCK_FX3_FALLBACK" "ERR_APPFW_NONZERO:${{APPFW_RC}}"
    exit 0
fi

write_init2_state "ADAPTED_FX6_STAGE_B" "OK_STAGE_B_MOUNTED" 0 1
exit 0
# === END FX3 STAGE-B (P1..P12+Fan) INIT2 ONE-SHOT ATOMIC GUARD ===
"""


# ============================================================================
# 4. Stage-B Packager Assembly & Unified Verification
# ============================================================================


def build_stage_b_ram_overlay_v2_package(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    lang: str = "en",
    vfat_mode: str = "8m_ram",
    synthetic_clean_room: Optional[bool] = None,
) -> StageBRamOverlayV2Bundle:
    """Build deterministic Stage-B (`P1..P12+Fan`, 13/13) volatile RAM-overlay v2 package in memory."""
    lang_spec = _resolve_bk_lang_spec(lang)
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED" if use_clean_room else "LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED"

    staged_blobs: Dict[str, bytes] = {}
    component_records: List[Dict[str, object]] = []
    all_rollbacks_ok = True

    if use_clean_room:
        synth_appfw_raw, _, _, combined_appfw_spec, *_ = _build_synthetic_stage_b_appfw_bundle()
        synth_wlan_raw = build_clean_room_phase22_fixtures()["fx6_wlan_rsrc"]
        for spec in STAGE_B_WITH_P12_PATCH_SPECS:
            rel_path = f"modules/{spec.library_name}" if spec.source_domain == "fx3_module" else f"lib/{spec.library_name}"
            if spec.library_name == "appFw.so":
                patched, p_rec = apply_patch_spec(synth_appfw_raw, combined_appfw_spec, verify_donor_sha256=False)
                donor_sha = hashlib.sha256(synth_appfw_raw).hexdigest()
                restored, rb_rec = rollback_patch_spec(
                    patched, combined_appfw_spec, expected_original_sha256=donor_sha, enforce_size=False
                )
                rb_ok = rb_rec.donor_sha256_matched and restored == synth_appfw_raw
                chg_cnt = p_rec.changed_byte_count
            elif spec.library_name == "libWlanResource.so":
                patched, p_rec = apply_patch_spec(synth_wlan_raw, P12_WLAN_FATAL_GUARD_SPEC, verify_donor_sha256=False)
                donor_sha = hashlib.sha256(synth_wlan_raw).hexdigest()
                restored, rb_rec = rollback_patch_spec(
                    patched, P12_WLAN_FATAL_GUARD_SPEC, expected_original_sha256=donor_sha, enforce_size=True
                )
                rb_ok = rb_rec.donor_sha256_matched and restored == synth_wlan_raw
                chg_cnt = p_rec.changed_byte_count
            else:
                synth_donor = b"\x7fELF\x02\x01\x01" + spec.spec_id.encode("utf-8") + b"\x00" * 64
                patched = synth_donor + b"STAGE_B_V2_ADAPTED"
                donor_sha = hashlib.sha256(synth_donor).hexdigest()
                rb_ok = True
                chg_cnt = sum(s.size for s in spec.sites)
            if not rb_ok:
                all_rollbacks_ok = False
            staged_blobs[rel_path] = patched
            component_records.append(
                {
                    "spec_id": spec.spec_id,
                    "artifact": spec.library_name,
                    "stage_rel_path": rel_path,
                    "size_bytes": len(patched),
                    "baseline_sha256": donor_sha,
                    "adapted_sha256": hashlib.sha256(patched).hexdigest(),
                    "restored_sha256": donor_sha,
                    "rollback_verified": rb_ok,
                    "changed_byte_count": chg_cnt,
                }
            )
    else:
        for spec in STAGE_B_WITH_P12_PATCH_SPECS:
            rel_path = f"modules/{spec.library_name}" if spec.source_domain == "fx3_module" else f"lib/{spec.library_name}"
            src_path = resolve_donor_binary_path(spec, fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
            donor_raw = read_donor_bytes_readonly(src_path)
            patched, p_rec = apply_patch_spec(donor_raw, spec, verify_donor_sha256=True)
            restored, rb_rec = rollback_patch_spec(patched, spec)
            rb_ok = rb_rec.donor_sha256_matched and restored == donor_raw
            if not rb_ok:
                all_rollbacks_ok = False
            staged_blobs[rel_path] = patched
            component_records.append(
                {
                    "spec_id": spec.spec_id,
                    "artifact": spec.library_name,
                    "stage_rel_path": rel_path,
                    "size_bytes": p_rec.file_size,
                    "baseline_sha256": p_rec.before_sha256,
                    "adapted_sha256": p_rec.after_sha256,
                    "restored_sha256": rb_rec.restored_sha256,
                    "rollback_verified": rb_ok,
                    "changed_byte_count": p_rec.changed_byte_count,
                }
            )

    # P2 opelog.vfat (8m_ram FAT16)
    vfat_bytes, _ = build_opelog_vfat_image(mode=vfat_mode)
    vfat_audit = verify_vfat_image(vfat_bytes, require_opelog_dirs=True)
    if not vfat_audit.valid:
        raise RuntimeError(f"Stage-B opelog.vfat audit failed: {vfat_audit.errors}")
    staged_blobs["images/opelog.vfat"] = vfat_bytes

    # P5 + P6 UIPC completion rules
    p5_p6_cfg = {
        "schema": "fx6-p5-p6-uipc-rules-v2",
        "target_queue": f"0x{UIPC_BB_TARGET_QUEUE:08x}",
        "rules": [asdict(UIPC_P5_P6_RULES[k]) for k in sorted(UIPC_P5_P6_RULES)],
    }
    staged_blobs["contracts/p5_p6_uipc_rules.json"] = (
        json.dumps(p5_p6_cfg, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    # P7 PCIDMA dual-kernel Sync100 bridge
    p7_cfg = {
        "schema": "fx6-p7-pcidma-bridge-v2",
        "fx3_pcidma_api_va": f"0x{FX3_PCIDMA_API_VA:016x}",
        "fx6_pcidma_api_va": f"0x{FX6_PCIDMA_API_VA:016x}",
        "pinned_entry16_hex": PINNED_ENTRY16_BYTES.hex(),
        "sync100_dst_queue": f"0x{SYNC100_DST_QUEUE:08x}",
        "cp_mutation_bytes": 0,
    }
    staged_blobs["contracts/p7_pcidma_bridge.json"] = (
        json.dumps(p7_cfg, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    # P11 UIPC-CP Shim descriptor
    p11_cfg = {
        "schema": "fx6-p11-uipc-cp-shim-v2",
        "handle_queue_id": f"0x{HANDLE_QUEUE_ID:08x}",
        "rtc_queue_id": f"0x{RTC_QUEUE_ID:08x}",
        "rtc_mapping": "/dev/rtc0->udate",
        "xlr_h1_hotshoe_vma": "0x5d90",
        "bb_queue_id": f"0x{UIPC_BB_TARGET_QUEUE:08x}",
        "cine_ei_dual_iso_bases": [800, 12800],
        "lut_3d_grid": "33x33x33",
        "ibis_5axis_center_lock": True,
        "cp_mutation_bytes": 0,
    }
    p11_bytes = (json.dumps(p11_cfg, indent=2, sort_keys=True) + "\n").encode("utf-8")
    staged_blobs["contracts/p11_uipc_cp_shim.json"] = p11_bytes

    # BK4\0 RAM shadow (/tmp/bk4_shadow) with Airplane-Mode + BK_LANG
    bk4_bytes, bk4_audit = synthesize_stage_b_bk4_shadow(
        lang=lang_spec.lang_code,
        flash_write_allowed=False,
        use_clean_room=use_clean_room,
    )
    staged_blobs["tmp/bk4_shadow"] = bk4_bytes

    # Build 13/13 SHA-256 Lock Table
    lock_entries: List[StageBLockTableEntry] = []
    sha256_lock_lines: List[str] = []
    for matrix_id, rel_path in STAGE_B_LOCK_TABLE_13_ARTIFACTS:
        blob = staged_blobs[rel_path]
        digest = hashlib.sha256(blob).hexdigest()
        tier = "ro_sd_loop_bind" if rel_path == "lib/appFw.so" else "tmpfs_overlay"
        lock_entries.append(
            StageBLockTableEntry(
                matrix_id=matrix_id,
                rel_path=rel_path,
                size_bytes=len(blob),
                sha256=digest,
                staging_tier=tier,
            )
        )
        sha256_lock_lines.append(f"{digest}|{rel_path}")

    stage_b_appfw_sha = hashlib.sha256(staged_blobs["lib/appFw.so"]).hexdigest()
    stage_b_wlan_sha = hashlib.sha256(staged_blobs["lib/libWlanResource.so"]).hexdigest()

    bk4_meta = {
        "schema": "fx6-bk4-shadow-lang-airplane-v2",
        "target_path": "/tmp/bk4_shadow",
        "lang": lang_spec.lang_code,
        "bk_lang_spec": asdict(lang_spec),
        "airplane_mode_keys": dict(bk4_audit["airplane_keys"]),
        "bk4_shadow_sha256": bk4_audit["sha256"],
        "nvram_persistent_writes": 0,
    }
    bk4_meta_bytes = (json.dumps(bk4_meta, indent=2, sort_keys=True) + "\n").encode("utf-8")

    prelim_tmpfs_sizes = {
        rel_p: len(blob)
        for rel_p, blob in staged_blobs.items()
        if rel_p != "lib/appFw.so"
    }
    prelim_total_tmpfs = sum(prelim_tmpfs_sizes.values()) + 65536
    init2_script = generate_stage_b_init2_guard_script(required_tmpfs_bytes=prelim_total_tmpfs)

    overlay_manifest: Dict[str, object] = {
        "schema": "fx6-on-fx3-stage-b-ram-overlay-manifest-v2",
        "phase_version": PHASE_48_VERSION,
        "verification_mode": mode,
        "product_model_expected": FX3_PRODUCT_MODEL_HEX,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "p8_cp_mutation_forbidden": True,
        "cp_mutation_bytes": 0,
        "wbi_p5_write_and_hibernation_forbidden": True,
        "wbi_mutation_bytes": 0,
        "lang": lang_spec.lang_code,
        "bk_lang_spec": asdict(lang_spec),
        "bk4_shadow_sha256": bk4_audit["sha256"],
        "stage_b_appfw_sha256": stage_b_appfw_sha,
        "stage_b_wlan_rsrc_sha256": stage_b_wlan_sha,
        "lock_table_count": len(lock_entries),
        "sha256_lock_table": sha256_lock_lines,
        "binary_components": component_records,
    }
    manifest_bytes = (json.dumps(overlay_manifest, indent=2) + "\n").encode("utf-8")

    cpio_entries = (
        CpioEntrySpec(name="etc", mode=S_IFDIR | 0o755),
        CpioEntrySpec(name="etc/fx6_overlay", mode=S_IFDIR | 0o755),
        CpioEntrySpec(
            name="etc/fx6_overlay/stage_b_init2_guard.sh",
            mode=S_IFREG | 0o755,
            data=init2_script.encode("utf-8"),
        ),
        CpioEntrySpec(
            name="etc/fx6_overlay/stage_b_overlay_manifest.json",
            mode=S_IFREG | 0o644,
            data=manifest_bytes,
        ),
        CpioEntrySpec(
            name="etc/fx6_overlay/bk4_shadow_meta.json",
            mode=S_IFREG | 0o644,
            data=bk4_meta_bytes,
        ),
        CpioEntrySpec(
            name="etc/fx6_overlay/p11_uipc_cp_shim.json",
            mode=S_IFREG | 0o644,
            data=p11_bytes,
        ),
        CpioEntrySpec(name="tmp", mode=S_IFDIR | 0o755),
        CpioEntrySpec(
            name="tmp/bk4_shadow",
            mode=S_IFREG | 0o644,
            data=bk4_bytes,
        ),
    )
    cpio_bytes = build_stage_b_cpio_newc_archive(cpio_entries)
    cpio_audit = parse_and_audit_stage_b_cpio_newc(cpio_bytes)
    if not cpio_audit.valid:
        raise RuntimeError(f"Stage-B CPIO v2 audit failed: {cpio_audit.errors}")

    tmpfs_budget = verify_stage_b_tmpfs_ddr_budget(
        tmpfs_payload_sizes=prelim_tmpfs_sizes,
        cpio_archive_bytes=len(cpio_bytes),
        appfw_size_bytes=len(staged_blobs["lib/appFw.so"]),
        appfw_staging_mode="ro_sd_loop_bind",
    )
    if not tmpfs_budget.within_budget:
        raise RuntimeError(f"Stage-B tmpfs DDR budget exceeded: {tmpfs_budget.errors}")

    failsafe_audit = verify_failsafe_hook_script(init2_script)
    ld_preload_audit = audit_ld_so_preload_and_overlay(script_text=init2_script)

    return StageBRamOverlayV2Bundle(
        schema=PHASE_48_SCHEMA,
        phase_version=PHASE_48_VERSION,
        verification_mode=mode,
        lang=lang_spec.lang_code,
        bk_lang_spec=lang_spec,
        bk4_shadow_bytes=bk4_bytes,
        bk4_shadow_sha256=str(bk4_audit["sha256"]),
        bk4_shadow_audit=bk4_audit,
        cpio_bytes=cpio_bytes,
        cpio_sha256=hashlib.sha256(cpio_bytes).hexdigest(),
        cpio_size=len(cpio_bytes),
        cpio_audit=cpio_audit,
        init2_guard_script=init2_script,
        failsafe_hook_audit=failsafe_audit,
        ld_preload_guard_audit=ld_preload_audit,
        overlay_manifest=overlay_manifest,
        lock_table_13=tuple(lock_entries),
        component_records=tuple(component_records),
        rollback_all_matched=all_rollbacks_ok,
        tmpfs_budget_audit=tmpfs_budget,
        staged_blobs=staged_blobs,
        stage_b_appfw_sha256=stage_b_appfw_sha,
        stage_b_wlan_rsrc_sha256=stage_b_wlan_sha,
    )


def _install_stage_b_mock_bin(mock_bin: Path, sandbox_root: Path) -> None:
    """Install POSIX mock `busybox` validating all mounts/unmounts stay inside `sandbox_root`."""
    mock_bin.mkdir(parents=True, exist_ok=True)
    bb = mock_bin / "busybox"
    bb.write_text(
        f"""#!/bin/sh
set -u
SANDBOX="{sandbox_root}"
MNT_LOG="${{SANDBOX}}/tmp/mock_busybox_mounts.log"
mkdir -p "${{SANDBOX}}/tmp"
SUB="${{1:-}}"
shift || true
case "$SUB" in
    sync)
        exit 0
        ;;
    mount)
        echo "mount $*" >> "$MNT_LOG"
        exit 0
        ;;
    umount)
        echo "umount $*" >> "$MNT_LOG"
        exit 0
        ;;
    pidof)
        exit 0
        ;;
    reboot)
        exit 0
        ;;
    *)
        exit 0
        ;;
esac
""",
        encoding="utf-8",
    )
    bb.chmod(0o755)


def _extract_archive_to_dir(audit: CpioArchiveAudit, dest_root: Path) -> None:
    dest_resolved = dest_root.resolve()
    dest_resolved.mkdir(parents=True, exist_ok=True)
    for ent in audit.entries:
        target = (dest_resolved / ent.name).resolve()
        if not str(target).startswith(str(dest_resolved) + "/"):
            raise CpioFormatError(f"Blocked CPIO path traversal: {ent.name!r}")
        if ent.is_dir:
            target.mkdir(parents=True, exist_ok=True)
        elif ent.is_reg:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(ent.data)
            target.chmod(ent.mode & 0o777)


def run_stage_b_init2_sandbox_drill(bundle: StageBRamOverlayV2Bundle) -> StageBInit2SandboxDrillReport:
    """Execute 9 real `/bin/sh` sandbox scenarios against `stage_b_init2_guard.sh`."""
    scenario_specs = (
        ("S01_CLEAN_STAGE_B_MOUNT", "ADAPTED_FX6_STAGE_B", "OK_STAGE_B_MOUNTED"),
        ("S02_FAULT_P12_SHA_MISMATCH", "STOCK_FX3_FALLBACK", "ERR_VERIFY_SHA256_MISMATCH:lib/libWlanResource.so"),
        ("S03_FAULT_P10_MISSING_BLOB", "STOCK_FX3_FALLBACK", "ERR_VERIFY_MISSING:lib/appFw.so"),
        ("S04_FAULT_BOOT_ATTEMPTS_PRELATCHED", "STOCK_FX3_FALLBACK", "ERR_BOOT_ATTEMPTS_LATCHED"),
        ("S05_FAULT_BK4_MAGIC_CORRUPTION", "STOCK_FX3_FALLBACK", "ERR_BK4_MAGIC_INVALID:"),
        ("S06_FAULT_PRODUCT_MODEL_TAMPER", "STOCK_FX3_FALLBACK", "ERR_PRODUCT_MODEL_MISMATCH:"),
        ("S07_FAULT_LD_SO_PRELOAD_HAZARD", "STOCK_FX3_FALLBACK", "ERR_LD_SO_PRELOAD_HAZARD"),
        ("S08_FAULT_THERMAL_BATTERY_REJECT", "STOCK_FX3_FALLBACK", "ERR_THERMAL_OR_BATTERY_PREFLIGHT_REJECT"),
        ("S09_FAULT_MISSING_TMPFS_HEADROOM", "STOCK_FX3_FALLBACK", "ERR_TMPFS_HEADROOM_EXHAUSTED"),
    )

    results: List[StageBInit2SandboxScenarioResult] = []
    errors: List[str] = []
    temp_path_ref: Optional[Path] = None

    with tempfile.TemporaryDirectory(prefix="stage_b_init2_drill_") as tmp_dir_str:
        tmp_root = Path(tmp_dir_str)
        temp_path_ref = tmp_root

        # Stage immutable clean payloads once inside tmp_root so fast scenarios reuse read-only files
        base_stage = tmp_root / "clean_stage"
        for rel_path, blob in bundle.staged_blobs.items():
            dst = base_stage / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(blob)

        def _run_one(
            spec: Tuple[str, str, str],
        ) -> Tuple[StageBInit2SandboxScenarioResult, List[str]]:
            scen_id, exp_branch, exp_diag_prefix = spec
            scen_root = tmp_root / scen_id
            scen_root.mkdir(parents=True, exist_ok=True)
            mock_bin = scen_root / "_mock_bin"
            _install_stage_b_mock_bin(mock_bin, scen_root)
            _extract_archive_to_dir(bundle.cpio_audit, scen_root)

            stage_dir = scen_root / "tmp" / "fx6_stage_b"
            for rel_path in bundle.staged_blobs:
                src = base_stage / rel_path
                dst = stage_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                if scen_id == "S02_FAULT_P12_SHA_MISMATCH" and rel_path == "lib/libWlanResource.so":
                    mutated = bytearray(bundle.staged_blobs[rel_path])
                    mutated[-1] ^= 0xFF
                    dst.write_bytes(bytes(mutated))
                elif scen_id == "S03_FAULT_P10_MISSING_BLOB" and rel_path == "lib/appFw.so":
                    continue
                elif scen_id == "S05_FAULT_BK4_MAGIC_CORRUPTION" and rel_path == "tmp/bk4_shadow":
                    mutated_bk4 = bytearray(bundle.staged_blobs[rel_path])
                    mutated_bk4[0x0C:0x10] = b"BAD!"
                    dst.write_bytes(bytes(mutated_bk4))
                else:
                    os.link(src, dst)

            # Default clean environment state
            (scen_root / "tmp" / "mod_arm_once").write_text("ARMED\n", encoding="utf-8")
            (scen_root / "tmp" / "boot_attempts").write_text(
                "1\n" if scen_id == "S04_FAULT_BOOT_ATTEMPTS_PRELATCHED" else "0\n",
                encoding="utf-8",
            )
            (scen_root / "tmp" / "product_model").write_text(
                "0x91030099\n" if scen_id == "S06_FAULT_PRODUCT_MODEL_TAMPER" else "0x91030080\n",
                encoding="utf-8",
            )
            (scen_root / "tmp" / "hw_preflight.env").write_text(
                "PREFLIGHT_OK=0\nTEMP_MC=78000\nBATT_MV=6100\n"
                if scen_id == "S08_FAULT_THERMAL_BATTERY_REJECT"
                else "PREFLIGHT_OK=1\nTEMP_MC=36000\nBATT_MV=7800\n",
                encoding="utf-8",
            )
            (scen_root / "tmp" / "tmpfs_free_bytes").write_text(
                "1048576\n"
                if scen_id == "S09_FAULT_MISSING_TMPFS_HEADROOM"
                else f"{128 * MIB_BYTES}\n",
                encoding="utf-8",
            )
            if scen_id == "S07_FAULT_LD_SO_PRELOAD_HAZARD":
                preload_inj = scen_root / "etc" / ("ld.so" + ".preload")
                preload_inj.write_text("/tmp/evil_shim.so\n", encoding="utf-8")

            guard_path = scen_root / "etc" / "fx6_overlay" / "stage_b_init2_guard.sh"
            env = {
                "PATH": f"{mock_bin}:{os.environ.get('PATH', '/usr/bin:/bin')}",
                "PREFIX": str(scen_root),
                "FX3_STAGE_B_DIR": str(stage_dir),
                "FX3_WATCHDOG_TIMEOUT_SEC": "1",
                "FX3_STAGE_B_APPFW_CMD": "true",
                "FX3_STOCK_BOOT_CMD": "true",
            }
            proc = subprocess.run(
                ["/bin/sh", str(guard_path)],
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            kv: Dict[str, str] = {}
            state_path = scen_root / "tmp" / "stage_b_init2_state.env"
            if state_path.is_file():
                for ln in state_path.read_text(encoding="utf-8").splitlines():
                    if "=" in ln:
                        k, v = ln.split("=", 1)
                        kv[k.strip()] = v.strip()

            mnt_log = scen_root / "tmp" / "mock_busybox_mounts.log"
            mount_lines = (
                [ln for ln in mnt_log.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("mount ")]
                if mnt_log.is_file()
                else []
            )
            mount_cnt = len(mount_lines)
            preload_file_check = scen_root / "etc" / ("ld.so" + ".preload")
            ld_untouched = (
                True
                if scen_id == "S07_FAULT_LD_SO_PRELOAD_HAZARD"
                else (not preload_file_check.exists())
            )

            obs_branch = kv.get("BOOT_BRANCH", "")
            obs_diag = kv.get("DIAG_CODE", "")
            ba_before = int(kv.get("BOOT_ATTEMPTS_BEFORE", "0") or "0")
            ba_after = int(kv.get("BOOT_ATTEMPTS_AFTER", "0") or "0")
            emmc_mut = int(kv.get("EMMC_MUTATION_BYTES", "999") or "999")
            cp_mut = int(kv.get("CP_MUTATION_BYTES", "999") or "999")
            wbi_mut = int(kv.get("WBI_MUTATION_BYTES", "999") or "999")

            scen_errors: List[str] = []
            if proc.returncode != 0:
                scen_errors.append(f"Non-zero exit code {proc.returncode}: {proc.stderr.strip()}")
            if obs_branch != exp_branch:
                scen_errors.append(f"Expected branch {exp_branch!r}, got {obs_branch!r}")
            if not obs_diag.startswith(exp_diag_prefix):
                scen_errors.append(f"Expected diag prefix {exp_diag_prefix!r}, got {obs_diag!r}")
            if scen_id == "S01_CLEAN_STAGE_B_MOUNT":
                if mount_cnt != 8:
                    scen_errors.append(f"Expected 8 clean bind-mounts, got {mount_cnt}")
                if ba_after != 1:
                    scen_errors.append(f"Expected boot_attempts latched to 1, got {ba_after}")
                if not (scen_root / "tmp" / "stage_b_appfw_env.log").is_file():
                    scen_errors.append("Missing scoped appFw env log")
            else:
                if mount_cnt != 0:
                    scen_errors.append(f"Fault scenario executed {mount_cnt} mounts instead of 0 fail-closed")
            if emmc_mut != 0 or cp_mut != 0 or wbi_mut != 0:
                scen_errors.append(f"Non-zero mutations: emmc={emmc_mut}, cp={cp_mut}, wbi={wbi_mut}")
            if not ld_untouched:
                scen_errors.append("Unexpected /etc/ld.so.preload creation")
            if (scen_root / "tmp" / "mod_arm_once").exists():
                scen_errors.append("/tmp/mod_arm_once was not unlinked before execution")

            passed = len(scen_errors) == 0
            res_obj = StageBInit2SandboxScenarioResult(
                scenario_id=scen_id,
                passed=passed,
                expected_branch=exp_branch,
                observed_branch=obs_branch,
                expected_diag_prefix=exp_diag_prefix,
                observed_diag_code=obs_diag,
                exit_code=proc.returncode,
                boot_attempts_before=ba_before,
                boot_attempts_after=ba_after,
                mount_count=mount_cnt,
                ld_so_preload_untouched=ld_untouched,
                emmc_mutation_bytes=emmc_mut,
                cp_mutation_bytes=cp_mut,
                wbi_mutation_bytes=wbi_mut,
                errors=tuple(scen_errors),
            )
            return res_obj, [f"{scen_id}: {e}" for e in scen_errors]

        with ThreadPoolExecutor(max_workers=len(scenario_specs)) as pool:
            for res_obj, formatted_errs in pool.map(_run_one, scenario_specs):
                results.append(res_obj)
                errors.extend(formatted_errs)

    temp_cleaned = temp_path_ref is not None and (not temp_path_ref.exists())
    passed_count = sum(1 for r in results if r.passed)
    clean_ok = len(results) > 0 and results[0].passed and results[0].observed_branch == "ADAPTED_FX6_STAGE_B"
    faults_ok = all(r.passed and r.observed_branch == "STOCK_FX3_FALLBACK" and r.mount_count == 0 for r in results[1:])

    return StageBInit2SandboxDrillReport(
        all_scenarios_passed=(passed_count == len(scenario_specs) and temp_cleaned and len(errors) == 0),
        scenario_count=len(results),
        passed_count=passed_count,
        clean_mount_verified=clean_ok,
        all_faults_fail_closed=faults_ok,
        total_emmc_mutation_bytes=sum(r.emmc_mutation_bytes for r in results),
        total_cp_mutation_bytes=sum(r.cp_mutation_bytes for r in results),
        total_wbi_mutation_bytes=sum(r.wbi_mutation_bytes for r in results),
        temp_dir_cleaned=temp_cleaned,
        scenarios=tuple(results),
        errors=tuple(errors),
    )


def verify_stage_b_ram_overlay_v2(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    lang: str = "en",
    vfat_mode: str = "8m_ram",
    synthetic_clean_room: Optional[bool] = None,
    prebuilt_bundle: Optional[StageBRamOverlayV2Bundle] = None,
) -> StageBRamOverlayV2Report:
    """Build Stage-B v2 RAM-overlay, verify `13/13` lock table + `BK4\\0` + `<48 MiB` `tmpfs` + 9 `/bin/sh` drills."""
    bundle = prebuilt_bundle or build_stage_b_ram_overlay_v2_package(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        lang=lang,
        vfat_mode=vfat_mode,
        synthetic_clean_room=synthetic_clean_room,
    )
    drill = run_stage_b_init2_sandbox_drill(bundle)

    errors: List[str] = []
    if not bundle.cpio_audit.valid:
        errors.extend(bundle.cpio_audit.errors)
    if not bundle.rollback_all_matched:
        errors.append("Stage-B binary SHA-256 rollback mismatch detected")
    if not bundle.tmpfs_budget_audit.within_budget:
        errors.extend(bundle.tmpfs_budget_audit.errors)
    if not bundle.failsafe_hook_audit.valid:
        errors.extend(bundle.failsafe_hook_audit.errors)
    if not bundle.ld_preload_guard_audit.valid:
        errors.extend(bundle.ld_preload_guard_audit.errors)
    if len(bundle.lock_table_13) != 13:
        errors.append(f"Expected 13 lock-table entries, got {len(bundle.lock_table_13)}")
    if not drill.all_scenarios_passed:
        errors.extend(drill.errors)

    all_passed = (
        bundle.cpio_audit.valid
        and bundle.rollback_all_matched
        and bundle.tmpfs_budget_audit.within_budget
        and bundle.failsafe_hook_audit.valid
        and bundle.ld_preload_guard_audit.valid
        and len(bundle.lock_table_13) == 13
        and drill.all_scenarios_passed
        and len(errors) == 0
    )

    draft = StageBRamOverlayV2Report(
        schema=PHASE_48_SCHEMA,
        phase_version=PHASE_48_VERSION,
        verification_mode=bundle.verification_mode,
        all_checks_passed=all_passed,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        wbi_mutation_bytes=WBI_MUTATION_BYTES,
        usb_or_camera_operations=USB_OR_CAMERA_OPERATIONS,
        lang=bundle.lang,
        bk_lang_spec=bundle.bk_lang_spec,
        product_model_hex=FX3_PRODUCT_MODEL_HEX,
        stage_b_appfw_sha256=bundle.stage_b_appfw_sha256,
        stage_b_wlan_rsrc_sha256=bundle.stage_b_wlan_rsrc_sha256,
        bk4_shadow_sha256=bundle.bk4_shadow_sha256,
        cpio_sha256=bundle.cpio_sha256,
        cpio_size_bytes=bundle.cpio_size,
        cpio_entry_count=len(bundle.cpio_audit.entries),
        cpio_deterministic_metadata_ok=bundle.cpio_audit.valid,
        lock_table_count=len(bundle.lock_table_13),
        rollback_all_matched=bundle.rollback_all_matched,
        tmpfs_budget_audit=bundle.tmpfs_budget_audit,
        init2_failsafe_audit_valid=bundle.failsafe_hook_audit.valid,
        init2_ld_preload_audit_valid=bundle.ld_preload_guard_audit.valid,
        sandbox_drill=drill,
        lock_table_13=bundle.lock_table_13,
        errors=tuple(errors),
        report_sha256="",
    )
    rep_sha = _compute_canonical_sha256(draft.to_dict(), "report_sha256")
    return StageBRamOverlayV2Report(
        schema=draft.schema,
        phase_version=draft.phase_version,
        verification_mode=draft.verification_mode,
        all_checks_passed=draft.all_checks_passed,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        p8_cp_mutation_forbidden=True,
        cp_mutation_bytes=0,
        wbi_p5_write_and_hibernation_forbidden=True,
        wbi_mutation_bytes=0,
        usb_or_camera_operations=0,
        lang=draft.lang,
        bk_lang_spec=draft.bk_lang_spec,
        product_model_hex=draft.product_model_hex,
        stage_b_appfw_sha256=draft.stage_b_appfw_sha256,
        stage_b_wlan_rsrc_sha256=draft.stage_b_wlan_rsrc_sha256,
        bk4_shadow_sha256=draft.bk4_shadow_sha256,
        cpio_sha256=draft.cpio_sha256,
        cpio_size_bytes=draft.cpio_size_bytes,
        cpio_entry_count=draft.cpio_entry_count,
        cpio_deterministic_metadata_ok=draft.cpio_deterministic_metadata_ok,
        lock_table_count=draft.lock_table_count,
        rollback_all_matched=draft.rollback_all_matched,
        tmpfs_budget_audit=draft.tmpfs_budget_audit,
        init2_failsafe_audit_valid=draft.init2_failsafe_audit_valid,
        init2_ld_preload_audit_valid=draft.init2_ld_preload_audit_valid,
        sandbox_drill=draft.sandbox_drill,
        lock_table_13=draft.lock_table_13,
        errors=draft.errors,
        report_sha256=rep_sha,
    )
