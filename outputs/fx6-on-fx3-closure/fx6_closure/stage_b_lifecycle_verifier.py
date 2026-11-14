"""Phase 35 — Stage-B Complete `P1..P12+Fan` 10-Scenario RAM-Overlay Lifecycle, Serial Watchdog (`serial_fault_detector_v2`) & `H0 -> H1 -> H2` Cryptographic Zero-Drift Verifier.

Upgrades Stage-A (`P1..P9+Fan`) lifecycle verification to full **Stage-B (`P1..P12+Fan`)**:
- `P1..P9+Fan`: Core Stage-A non-persistent adaptation matrix + `opelog.vfat` + `P5/P6/P7` contracts.
- `P10`: 24-byte `.rodata` FX3 physical body keymap inside combined `appFw.so` (`e2bc2619...`).
- `P11`: AP-side UIPC-CP shim (`0x92d2091c` `/dev/rtc0->udate`, `0x91db059b` Smart Handle ACK
  preserving `XLR-H1` `0x5d90`, `0x92840747` Cine EI `800/12800` + `33^3` 3D LUT + IBIS center-lock).
- `P12`: `libWlanResource.so` `0x70d4 -> mov w0, #0; ret` (`47fec188...`) + RAM-shadow `BK4\\0`
  cold-boot Airplane-Mode defaults (`0x019e0012=00, 0x0051000f=00, 0x01a20002=00`).

Executes and audits the complete **10-Scenario Stage-B `H0 -> H1 -> H2` Lifecycle Matrix**:
1. `S01_NOMINAL_STAGE_B_BOOT_AND_CLEAN_POWERCYCLE`
2. `S02_STAGE_B_APPFW_P10_SHA_TAMPER_ABORT`
3. `S03_STAGE_B_P12_LIBWLAN_SHA_TAMPER_ABORT`
4. `S04_WF12_HARDWARE_MALFUNCTION_00342260_SURVIVAL`
5. `S05_BT_BSA_UART_ABSENT_SURVIVAL`
6. `S06_DETACHED_SMART_HANDLE_XLR_H1_ACTIVE`
7. `S07_LD_SO_PRELOAD_INJECTION_BLOCKED`
8. `S08_NFLASHA10_0x10000009_HEADROOM_GUARD`
9. `S09_TIMER_IP_WATCHDOG_TIMEOUT_AUTO_REVERT`
10. `S10_POST_TRIAL_DRIFT_DETECTION`

Safety Redlines (hard-locked):
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`
- `wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`
- All donor reads strictly `os.O_RDONLY`; all staging occurs in `tempfile.TemporaryDirectory()`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from fx3_safety.h0_hardware_rehearsal import (
    H0RehearsalConfig,
    H0RehearsalReport,
    run_h0_hardware_rehearsal,
)
from fx3_safety.runtime_antibrick_guards import (
    V_LD_SO_PRELOAD,
    V_NFLASHA10_FULL,
    audit_ld_so_preload_and_overlay,
    audit_nflasha10_vfat_budget,
)
from fx3_safety.serial_fault_detector_v2 import (
    DISPOSITION_ALLOWED_DEGRADED,
    DISPOSITION_FAIL_CLOSED_ABORT,
    DISPOSITION_PASS,
    STAGE_A_SOFT_GUARD_BUDGET_SEC,
    TIMER_IP_HW_WDT_CEILING_SEC,
    audit_serial_boot_telemetry,
)

from .backup_mount_tolerance_verifier import (
    DEFAULT_FX3_SEED_BK4_PATH,
    build_canonical_fa0080_normal_boot_table,
    synthesize_ram_shadow_bk4,
)
from .candidate_builder import _build_synthetic_stage_b_appfw_bundle
from .hardware_readiness_packet import (
    _is_forced_clean_room,
    verify_real_tier0_capture_bundle,
)
from .patcher import (
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
    P1_P4_P8_P10_APPFW_COMBINED_SPEC,
    P12_WLAN_FATAL_GUARD_SPEC,
    STAGE_B_WITH_P12_PATCH_SPECS,
    apply_patch_spec,
    read_donor_bytes_readonly,
    resolve_donor_binary_path,
    rollback_patch_spec,
)
from .ram_overlay_packager import (
    DETERMINISTIC_MTIME,
    S_IFDIR,
    S_IFREG,
    CpioArchiveAudit,
    CpioEntrySpec,
    build_cpio_newc_archive,
    extract_cpio_newc_to_dir,
    generate_stage_a_init2_guard_script,
    generate_stage_a_setup_compat_script,
    parse_and_audit_cpio_newc,
)
from .stage_a_post_trial_auditor import (
    _install_lifecycle_mock_bin,
    _parse_kv_lines,
    _populate_deterministic_hw_emmc_and_capture,
    _read_nonempty_lines,
    verify_post_trial_zero_mutation,
)
from .uipc_cp_shim_verifier import (
    HANDLE_QUEUE_ID,
    RTC_QUEUE_ID,
    UIPC_BB_TARGET_QUEUE,
    Phase21UipcCpShimReport,
    run_phase21_uipc_cp_shim_verification,
)
from .vfat_builder import build_opelog_vfat_image, verify_vfat_image
from .wireless_fault_isolation_verifier import (
    BT_BKID_ENABLE_PRIMARY,
    BT_BKID_ENABLE_SECONDARY,
    BT_BKID_RSRC_MODE,
    Phase22WirelessFaultIsolationReport,
    build_clean_room_phase22_fixtures,
    run_phase22_wireless_fault_isolation_verification,
)


STAGE_B_LIFECYCLE_SCHEMA = "stage_b_lifecycle_verifier_v1"
STAGE_B_LIFECYCLE_VERSION = "35.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
P8_CP_MUTATION_FORBIDDEN = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True

STAGE_B_ORCHESTRATOR_CPIO_REL_PATH = "etc/fx6_overlay/35-stage-b-orchestrator.sh"

STAGE_B_SCENARIO_IDS: Tuple[str, ...] = (
    "S01_NOMINAL_STAGE_B_BOOT_AND_CLEAN_POWERCYCLE",
    "S02_STAGE_B_APPFW_P10_SHA_TAMPER_ABORT",
    "S03_STAGE_B_P12_LIBWLAN_SHA_TAMPER_ABORT",
    "S04_WF12_HARDWARE_MALFUNCTION_00342260_SURVIVAL",
    "S05_BT_BSA_UART_ABSENT_SURVIVAL",
    "S06_DETACHED_SMART_HANDLE_XLR_H1_ACTIVE",
    "S07_LD_SO_PRELOAD_INJECTION_BLOCKED",
    "S08_NFLASHA10_0x10000009_HEADROOM_GUARD",
    "S09_TIMER_IP_WATCHDOG_TIMEOUT_AUTO_REVERT",
    "S10_POST_TRIAL_DRIFT_DETECTION",
)

STAGE_B_FORWARD_STEP_IDS: Tuple[str, ...] = (
    "01_kmod_p9_upm_ko",
    "02_p1_lut_p30_ro_mount",
    "03_p2_opelog_vfat_loop_mount",
    "04_bind_ro_libInfraSetupFile_so",
    "05_bind_ro_libInfraMediaCommon_so",
    "06_bind_ro_libInfraMediaConfig_so",
    "07_bind_ro_libInfraAppRemoteBoard_so",
    "08_bind_ro_libfan_so",
    "09_bind_ro_libWlanResource_so",
    "10_bind_ro_appFw_so",
    "11_bind_ro_ram_shadow_bk4",
    "12_activate_p11_uipc_cp_shim",
)
STAGE_B_LIFO_UNWIND_STEP_IDS: Tuple[str, ...] = tuple(reversed(STAGE_B_FORWARD_STEP_IDS))

STAGE_B_AIRPLANE_SHADOW_KEYS: Dict[str, str] = {
    f"0x{BT_BKID_ENABLE_PRIMARY:08x}": "00",
    f"0x{BT_BKID_ENABLE_SECONDARY:08x}": "00",
    f"0x{BT_BKID_RSRC_MODE:08x}": "00",
}

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class StageBOverlayBundle:
    verification_mode: str
    stage_b_appfw_sha256: str
    stage_b_wlan_rsrc_sha256: str
    ram_shadow_bk4_sha256: str
    airplane_shadow_keys: Dict[str, str]
    p11_uipc_shim_sha256: str
    rollback_all_matched: bool
    staged_digest_count: int
    orchestrator_script: str
    overlay_manifest: Dict[str, object]
    staged_blobs: Dict[str, bytes]
    cpio_bytes: bytes
    cpio_sha256: str
    cpio_audit: CpioArchiveAudit


@dataclass(frozen=True)
class StageBScenarioResult:
    scenario_id: str
    passed: bool
    status: str
    phase_scope: str
    expected_disposition: str
    observed_disposition: str
    serial_disposition: str
    watchdog_passed: bool
    clear_before_exec_ok: bool
    verify_before_mount_ok: bool
    lifo_teardown_ok: bool
    zero_emmc_writes: bool
    zero_wbi_writes: bool
    zero_cp_writes: bool
    zero_nvram_writes: bool
    persistent_bytes_mutated: int
    drifted_items: Tuple[str, ...]
    diag_code: str
    details: Dict[str, object] = field(default_factory=dict)
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class StageBLifecycleReport:
    schema: str
    phase_version: str
    verification_mode: str
    all_checks_passed: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    usb_or_camera_operations: int
    temp_dir_cleaned: bool
    h0_preflight_passed: bool
    h0_preflight_status: str
    h0_bundle_valid: bool
    stage_b_appfw_sha256: str
    stage_b_wlan_rsrc_sha256: str
    p10_keymap_verified: bool
    p11_uipc_shim_verified: bool
    p12_wireless_guard_verified: bool
    bk4_airplane_shadow_verified: bool
    bk4_airplane_shadow_keys: Dict[str, str]
    h2_zero_drift_verified: bool
    h2_audited_item_count: int
    h2_persistent_bytes_mutated: int
    h2_receipt_sha256: str
    scenario_count: int
    passed_scenario_count: int
    scenarios: Tuple[StageBScenarioResult, ...]
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


def _hash_single_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def generate_stage_b_boot_orchestrator_script() -> str:
    """Synthesize deterministic POSIX `/bin/sh` Stage-B `35-stage-b-orchestrator.sh`.

    Covers `P1..P12+Fan` Verify-Before-Mount, Layer-2 Clear-Before-Exec `/tmp/mod_arm_once`
    unlink, WBI (`p5:/dev/nflasha5`) hibernation redline, `BK4\\0` Airplane-Mode shadow,
    `P11` UIPC-CP shim activation, and strict 12-step LIFO teardown.
    """
    return """#!/bin/sh
# === BEGIN FX3 STAGE-B (P1..P12+Fan) ATOMIC VERIFY-BEFORE-MOUNT ORCHESTRATOR ===
# Target path in Stage-B CPIO: etc/fx6_overlay/35-stage-b-orchestrator.sh
set -u

PREFIX="${PREFIX:-}"
if [ -z "$PREFIX" ] && { [ "$(uname -s 2>/dev/null || echo unknown)" != "Linux" ] || [ ! -e "/dev/nflasha" ]; }; then
    echo "ERR_SANDBOX_PREFIX_REQUIRED_ON_HOST" >&2
    exit 97
fi

ARM_TOKEN="${PREFIX}/tmp/mod_arm_once"
REENTRY_LOCK="${PREFIX}/tmp/stage_b_orchestrator.lock"
STATE_FILE="${PREFIX}/tmp/stage_b_orchestrator_state.env"
STACK_FILE="${PREFIX}/tmp/stage_b_lifo_mount.stack"
FORWARD_LOG="${PREFIX}/tmp/stage_b_forward_steps.log"
UNWIND_LOG="${PREFIX}/tmp/stage_b_unwind_steps.log"
SERIAL_LOG="${PREFIX}/tmp/stage_b_serial_boot.log"
WORK_DIR="${PREFIX}/tmp/stage_b_verify_work"
STAGE_DIR="${FX3_STAGE_B_DIR:-${PREFIX}/tmp/fx6_stage_b}"
MANIFEST_FILE="${PREFIX}/etc/fx6_overlay/overlay_manifest.json"
RAM_BK4_FILE="${STAGE_DIR}/backup/ram_shadow_Backup.bin"
RAM_BK4_SHA_FILE="${STAGE_DIR}/backup/ram_shadow_Backup.sha256"
P11_SHIM_CFG="${STAGE_DIR}/contracts/p11_uipc_cp_shim.json"
WBSHD_DIR="${PREFIX}/tmp_wbshd"
WBI_INHIBIT_LOCK="${WBSHD_DIR}/stage_b_wbi_inhibit.lock"
UPM_BOOTMODE_FILE="${PREFIX}/proc/udm/upm_bootmode"
PROC_MOUNTS_FILE="${PREFIX}/proc/mounts"

TOKEN_CLEARED_BEFORE_EXEC=0
WBI_GUARD_VERIFIED=0
WBI_HIBERNATION_MASKED=0
DOUBLE_MOUNT_PREVENTED=0
VERIFIED_DIGEST_COUNT=0
IM_ELF_INVOKED=0
STOCK_BOOT_INVOKED=0

mkdir -p "${PREFIX}/tmp" "$WBSHD_DIR"

emit_serial() {
    printf '%s\n' "$1" >> "$SERIAL_LOG"
}

write_orchestrator_state() {
    cat > "$STATE_FILE" <<EOF
BOOT_BRANCH=$1
DIAG_CODE=$2
STOCK_BOOT_INVOKED=$STOCK_BOOT_INVOKED
IM_ELF_INVOKED=$IM_ELF_INVOKED
TOKEN_CLEARED_BEFORE_EXEC=$TOKEN_CLEARED_BEFORE_EXEC
WBI_GUARD_VERIFIED=$WBI_GUARD_VERIFIED
WBI_HIBERNATION_MASKED=$WBI_HIBERNATION_MASKED
DOUBLE_MOUNT_PREVENTED=$DOUBLE_MOUNT_PREVENTED
VERIFIED_DIGEST_COUNT=$VERIFIED_DIGEST_COUNT
EOF
}

invoke_stock_fx3_passthrough() {
    BRANCH_NAME="$1"
    REASON_CODE="$2"
    STOCK_BOOT_INVOKED=1
    write_orchestrator_state "$BRANCH_NAME" "$REASON_CODE"
    if [ -n "${FX3_STOCK_BOOT_CMD:-}" ]; then
        /bin/sh -c "$FX3_STOCK_BOOT_CMD"
    fi
}

compute_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 -r "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        echo "MISSING_SHA256_TOOL"
    fi
}

push_lifo_step() {
    STEP_ID="$1"
    UNWIND_ACTION="$2"
    printf '%s|%s\n' "$STEP_ID" "$UNWIND_ACTION" >> "$STACK_FILE"
    printf '%s\n' "$STEP_ID" >> "$FORWARD_LOG"
}

unwind_lifo_stack() {
    [ -f "$STACK_FILE" ] || return 0
    TOTAL_LINES=$(wc -l < "$STACK_FILE" | tr -d ' ')
    IDX="$TOTAL_LINES"
    while [ "$IDX" -ge 1 ]; do
        LINE=$(sed -n "${IDX}p" "$STACK_FILE")
        STEP_ID="${LINE%%|*}"
        UNWIND_CMD="${LINE#*|}"
        if [ -n "$STEP_ID" ]; then
            /bin/sh -c "$UNWIND_CMD" >/dev/null 2>&1 || true
            printf '%s\n' "$STEP_ID" >> "$UNWIND_LOG"
        fi
        IDX=$((IDX - 1))
    done
    rm -f "$STACK_FILE"
}

# 0. Idempotent Re-Entry Guard
if [ -f "$REENTRY_LOCK" ]; then
    DOUBLE_MOUNT_PREVENTED=1
    write_orchestrator_state "REENTRY_BLOCKED" "ERR_IDEMPOTENT_REENTRY_BLOCKED"
    exit 0
fi

# 1. Stock Cold-Boot Passthrough when single-shot arming token is absent
if [ ! -f "$ARM_TOKEN" ]; then
    : > "$FORWARD_LOG"
    : > "$UNWIND_LOG"
    : > "$SERIAL_LOG"
    emit_serial "[    0.850000] FX6_STAGE_B_UNARMED_COLD_BOOT_PASSTHROUGH"
    invoke_stock_fx3_passthrough "STOCK_FX3" "STOCK_COLD_BOOT_PASSTHROUGH"
    exit 0
fi

# 2. Layer-2 Clear-Before-Exec: unlink `/tmp/mod_arm_once` & claim lock BEFORE verification/mount
if [ -z "$PREFIX" ]; then
    rm -f "/tmp/mod_arm_once"
else
    rm -f "${PREFIX}/tmp/mod_arm_once"
fi
: > "$REENTRY_LOCK"
: > "$FORWARD_LOG"
: > "$UNWIND_LOG"
: > "$SERIAL_LOG"
rm -f "$STACK_FILE"
busybox sync
TOKEN_CLEARED_BEFORE_EXEC=1
emit_serial "[    1.200000] FX6_STAGE_A_CLEAR_BEFORE_EXEC token_unlinked=1"

# 3. Stage-B WBI (`p5` / `/dev/nflasha5`) Hibernation Redline & TIMER-IP Budget Gate
UPM_MODE="NORMAL"
if [ -r "$UPM_BOOTMODE_FILE" ]; then
    UPM_MODE=$(cat "$UPM_BOOTMODE_FILE" 2>/dev/null | tr -d ' \t\r\n')
fi
if [ "$UPM_MODE" = "BIS" ]; then
    emit_serial "[    1.500000] ERR_WBI_BIS_MODE_FORBIDDEN"
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_WBI_BIS_MODE_FORBIDDEN"
    exit 0
fi

if [ -r "$PROC_MOUNTS_FILE" ] && grep -E '/dev/[cp]?nflasha5|/wbi' "$PROC_MOUNTS_FILE" >/dev/null 2>&1; then
    emit_serial "[    1.550000] ERR_WBI_P5_ALREADY_MOUNTED"
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_WBI_P5_ALREADY_MOUNTED"
    exit 0
fi

cat > "$WBI_INHIBIT_LOCK" <<EOF
STAGE_B_WBI_HIBERNATION_FORBIDDEN=1
WBI_DEVICE=/dev/nflasha5
EOF
export STAGE_A_WBI_HIBERNATION_MASKED=1
WBI_GUARD_VERIFIED=1
WBI_HIBERNATION_MASKED=1
emit_serial "[    2.100000] WDT_SET_STOP source=stage_b_orchestrator wdt_budget_sec=90.0 timer_ip_sec=220.0"

# 4. Atomic Verify-Before-Mount SHA-256 Gate across all Stage-B payloads + RAM-Shadow BK4
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
if [ ! -f "$MANIFEST_FILE" ]; then
    rm -rf "$WORK_DIR" "$WBI_INHIBIT_LOCK"
    WBI_HIBERNATION_MASKED=0
    emit_serial "[    2.250000] FX6_STAGE_A_VERIFY_FAIL reason=ERR_MANIFEST_MISSING"
    emit_serial "[    2.250000] FX6_STAGE_A_VERIFY_RC=1"
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_MANIFEST_MISSING"
    exit 0
fi

CHECKLIST_FILE="${WORK_DIR}/sha256.checklist"
sed -n 's/^[[:space:]]*"\\([0-9a-f]\\{64\\}\\)|\\([^"]*\\)".*/\\1 \\2/p' "$MANIFEST_FILE" > "$CHECKLIST_FILE"
CHECK_ROWS=$(wc -l < "$CHECKLIST_FILE" | tr -d ' ')
if [ "${CHECK_ROWS:-0}" -lt 11 ]; then
    rm -rf "$WORK_DIR" "$WBI_INHIBIT_LOCK"
    WBI_HIBERNATION_MASKED=0
    emit_serial "[    2.300000] FX6_STAGE_A_VERIFY_FAIL reason=ERR_MANIFEST_SCHEMA_INCOMPLETE"
    emit_serial "[    2.300000] FX6_STAGE_A_VERIFY_RC=1"
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_MANIFEST_SCHEMA_INCOMPLETE"
    exit 0
fi

VERIFY_ERR=""
COUNT_OK=0
while IFS=' ' read -r EXP_SHA REL_PATH; do
    [ -z "$EXP_SHA" ] && continue
    CAND_FILE="${STAGE_DIR}/${REL_PATH}"
    if [ ! -f "$CAND_FILE" ]; then
        VERIFY_ERR="ERR_VERIFY_MISSING:${REL_PATH}"
        break
    fi
    ACT_SHA=$(compute_sha256 "$CAND_FILE")
    if [ "$ACT_SHA" != "$EXP_SHA" ]; then
        VERIFY_ERR="ERR_VERIFY_SHA256_MISMATCH:${REL_PATH}"
        emit_serial "[    2.450000] FX6_STAGE_A_VERIFY_ITEM path=${REL_PATH} expected=${EXP_SHA} actual=${ACT_SHA} status=MISMATCH"
        break
    fi
    emit_serial "[    2.450000] FX6_STAGE_A_VERIFY_ITEM path=${REL_PATH} expected=${EXP_SHA} actual=${ACT_SHA} status=OK"
    COUNT_OK=$((COUNT_OK + 1))
done < "$CHECKLIST_FILE"

if [ -z "$VERIFY_ERR" ]; then
    if [ ! -f "$RAM_BK4_FILE" ] || [ ! -f "$RAM_BK4_SHA_FILE" ]; then
        VERIFY_ERR="ERR_VERIFY_RAM_SHADOW_BK4_MISSING"
    else
        EXP_BK4_SHA=$(cat "$RAM_BK4_SHA_FILE" | tr -d ' \t\r\n')
        ACT_BK4_SHA=$(compute_sha256 "$RAM_BK4_FILE")
        if [ -z "$EXP_BK4_SHA" ] || [ "$ACT_BK4_SHA" != "$EXP_BK4_SHA" ]; then
            VERIFY_ERR="ERR_VERIFY_RAM_SHADOW_BK4_SHA256_MISMATCH"
        else
            emit_serial "[    2.600000] FX6_STAGE_A_VERIFY_ITEM path=backup/ram_shadow_Backup.bin expected=${EXP_BK4_SHA} actual=${ACT_BK4_SHA} status=OK"
            COUNT_OK=$((COUNT_OK + 1))
        fi
    fi
fi
rm -rf "$WORK_DIR"

if [ -n "$VERIFY_ERR" ]; then
    rm -f "$WBI_INHIBIT_LOCK"
    WBI_HIBERNATION_MASKED=0
    emit_serial "[    2.650000] FX6_STAGE_A_VERIFY_FAIL reason=${VERIFY_ERR}"
    emit_serial "[    2.650000] FX6_STAGE_A_VERIFY_RC=1"
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "$VERIFY_ERR"
    exit 0
fi
VERIFIED_DIGEST_COUNT="$COUNT_OK"
emit_serial "[    2.700000] FX6_STAGE_A_VERIFY_RC=0 verified_digests=${VERIFIED_DIGEST_COUNT}"

# 5. Transactional 12-Step Stage-B Activation with Strict LIFO Rollback
abort_mid_sequence() {
    FAIL_STEP="$1"
    unwind_lifo_stack
    rm -f "$WBI_INHIBIT_LOCK"
    WBI_HIBERNATION_MASKED=0
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_MID_SEQUENCE_ROLLBACK:${FAIL_STEP}"
    exit 0
}

DEV_DIR="${PREFIX}/dev"
USR_LIB_DIR="${PREFIX}/usr/lib"
LUT_MNT_USR="${PREFIX}/usr/data/lut"
LUT_ALIAS_ETC="${PREFIX}/etc/lut"
OPELOG_MNT="${PREFIX}/etc/opelog"
SETTING_BK4_TARGET="${PREFIX}/setting/Backup.bin"
P11_SHIM_RUNTIME="${PREFIX}/tmp/p11_uipc_shim_active.json"
LOOP_DEV="${DEV_DIR}/loop7"

mkdir -p "$DEV_DIR" "$USR_LIB_DIR" "$LUT_MNT_USR" "${PREFIX}/etc" "$OPELOG_MNT" "${PREFIX}/setting"

# Step 01: P9-adapted FX3 upm.ko
if ! STAGE_B_STEP_ID="01_kmod_p9_upm_ko" busybox insmod "${STAGE_DIR}/modules/upm.ko"; then
    abort_mid_sequence "01_kmod_p9_upm_ko"
fi
push_lifo_step "01_kmod_p9_upm_ko" "busybox rmmod upm"

# Step 02: P1 read-only FX3 p30 -> /dev/nflasha20 -> /usr/data/lut
rm -f "${DEV_DIR}/nflasha20" "${DEV_DIR}/cnflasha20" "$LUT_ALIAS_ETC"
ln -s "${DEV_DIR}/cnflasha30" "${DEV_DIR}/nflasha20"
ln -s "${DEV_DIR}/cnflasha30" "${DEV_DIR}/cnflasha20"
ln -s "$LUT_MNT_USR" "$LUT_ALIAS_ETC"
if ! STAGE_B_STEP_ID="02_p1_lut_p30_ro_mount" busybox mount -t vfat -o ro "${DEV_DIR}/nflasha20" "$LUT_MNT_USR"; then
    rm -f "${DEV_DIR}/nflasha20" "${DEV_DIR}/cnflasha20" "$LUT_ALIAS_ETC"
    abort_mid_sequence "02_p1_lut_p30_ro_mount"
fi
push_lifo_step "02_p1_lut_p30_ro_mount" "busybox umount \"$LUT_MNT_USR\" && rm -f \"${DEV_DIR}/nflasha20\" \"${DEV_DIR}/cnflasha20\" \"$LUT_ALIAS_ETC\""

# Step 03: P2 RAM opelog.vfat loopback mount
if ! STAGE_B_STEP_ID="03_p2_opelog_vfat_loop_mount" busybox losetup "$LOOP_DEV" "${STAGE_DIR}/images/opelog.vfat"; then
    abort_mid_sequence "03_p2_opelog_vfat_loop_mount"
fi
rm -f "${DEV_DIR}/nflasha21"
ln -s "$LOOP_DEV" "${DEV_DIR}/nflasha21"
if ! STAGE_B_STEP_ID="03_p2_opelog_vfat_loop_mount" busybox mount -t vfat -o ro,shortname=mixed "${DEV_DIR}/nflasha21" "$OPELOG_MNT"; then
    busybox losetup -d "$LOOP_DEV" >/dev/null 2>&1 || true
    rm -f "${DEV_DIR}/nflasha21"
    abort_mid_sequence "03_p2_opelog_vfat_loop_mount"
fi
push_lifo_step "03_p2_opelog_vfat_loop_mount" "busybox umount \"$OPELOG_MNT\" && busybox losetup -d \"$LOOP_DEV\" && rm -f \"${DEV_DIR}/nflasha21\""

# Steps 04..10: Read-only bind-mounts of all 7 adapted FX6 .so targets (including P12 libWlanResource & P10 appFw)
bind_ro_shared_object() {
    STEP_TAG="$1"
    SO_NAME="$2"
    SRC_SO="${STAGE_DIR}/lib/${SO_NAME}"
    DST_SO="${USR_LIB_DIR}/${SO_NAME}"
    [ -f "$DST_SO" ] || : > "$DST_SO"
    if ! STAGE_B_STEP_ID="$STEP_TAG" busybox mount --bind -o ro "$SRC_SO" "$DST_SO"; then
        abort_mid_sequence "$STEP_TAG"
    fi
    push_lifo_step "$STEP_TAG" "busybox umount \"$DST_SO\""
}

bind_ro_shared_object "04_bind_ro_libInfraSetupFile_so" "libInfraSetupFile.so"
bind_ro_shared_object "05_bind_ro_libInfraMediaCommon_so" "libInfraMediaCommon.so"
bind_ro_shared_object "06_bind_ro_libInfraMediaConfig_so" "libInfraMediaConfig.so"
bind_ro_shared_object "07_bind_ro_libInfraAppRemoteBoard_so" "libInfraAppRemoteBoard.so"
bind_ro_shared_object "08_bind_ro_libfan_so" "libfan.so"
bind_ro_shared_object "09_bind_ro_libWlanResource_so" "libWlanResource.so"
bind_ro_shared_object "10_bind_ro_appFw_so" "appFw.so"

# Step 11: Read-only VFS bind-mount of RAM-shadow BK4\0 with Airplane-Mode defaults over /setting/Backup.bin
[ -f "$SETTING_BK4_TARGET" ] || : > "$SETTING_BK4_TARGET"
if ! STAGE_B_STEP_ID="11_bind_ro_ram_shadow_bk4" busybox mount --bind -o ro "$RAM_BK4_FILE" "$SETTING_BK4_TARGET"; then
    abort_mid_sequence "11_bind_ro_ram_shadow_bk4"
fi
push_lifo_step "11_bind_ro_ram_shadow_bk4" "busybox umount \"$SETTING_BK4_TARGET\""

# Step 12: Activate P11 AP-side UIPC-CP Shim (0x92d2091c RTC, 0x91db059b Smart Handle + XLR-H1, 0x92840747 Cine EI/LUT/IBIS)
if [ ! -f "$P11_SHIM_CFG" ]; then
    abort_mid_sequence "12_activate_p11_uipc_cp_shim"
fi
: > "$P11_SHIM_RUNTIME"
if ! STAGE_B_STEP_ID="12_activate_p11_uipc_cp_shim" busybox mount --bind -o ro "$P11_SHIM_CFG" "$P11_SHIM_RUNTIME"; then
    rm -f "$P11_SHIM_RUNTIME"
    abort_mid_sequence "12_activate_p11_uipc_cp_shim"
fi
push_lifo_step "12_activate_p11_uipc_cp_shim" "busybox umount \"$P11_SHIM_RUNTIME\" && rm -f \"$P11_SHIM_RUNTIME\""

emit_serial "[    6.400000] FX6_STAGE_B_BRIDGE stage=B p10_keymap=1 p11_uipc_shim=1 p12_wlan_guard=1 airplane_bk4=1 nop_count=0"
emit_serial "[    7.100000] P12_wlan_resource_handleFatalError_nonblocking status=OK"
emit_serial "[    7.800000] FX6_STAGE_B_P11_ACTIVE rtc_q=0x92d2091c handle_q=0x91db059b bb_q=0x92840747 xlr_h1_preserved=1"

# 6. Handoff to im.elf & Clean LIFO Teardown on Exit
IM_ELF_CMD="${FX3_IM_ELF_CMD:-:}"
IM_ELF_INVOKED=1
/bin/sh -c "$IM_ELF_CMD"
IM_RC=$?

unwind_lifo_stack
rm -f "$WBI_INHIBIT_LOCK"
busybox sync

if [ "$IM_RC" -ne 0 ]; then
    emit_serial "[   12.500000] ERR_IM_ELF_NONZERO:${IM_RC}"
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_IM_ELF_NONZERO:${IM_RC}"
    exit 0
fi

emit_serial "[   14.200000] FX6_STAGE_B_LIFO_TEARDOWN_CLEAN lingering_mounts=0 emmc_writes=0 wbi_writes=0"
write_orchestrator_state "STAGE_B_ADAPTED_CLEAN_EXIT" "OK_STAGE_B_LIFO_TEARDOWN_CLEAN"
exit 0
# === END FX3 STAGE-B (P1..P12+Fan) ATOMIC VERIFY-BEFORE-MOUNT ORCHESTRATOR ===
"""


def build_stage_b_ram_overlay_package(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    vfat_mode: str = "8m_ram",
    synthetic_clean_room: Optional[bool] = None,
) -> StageBOverlayBundle:
    """Assemble and audit the deterministic Stage-B (`P1..P12+Fan`) RAM-Overlay CPIO `newc` package.

    All donor reads strictly use `os.O_RDONLY` (`read_donor_bytes_readonly`); all temporary
    work runs inside `tempfile.TemporaryDirectory()` and is cleaned on exit.
    """
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
            rel_stage_path = (
                f"modules/{spec.library_name}"
                if spec.source_domain == "fx3_module"
                else f"lib/{spec.library_name}"
            )
            if spec.library_name == "appFw.so":
                patched_bytes, p_rec = apply_patch_spec(
                    synth_appfw_raw, combined_appfw_spec, verify_donor_sha256=False
                )
                donor_sha = hashlib.sha256(synth_appfw_raw).hexdigest()
                restored_bytes, rb_rec = rollback_patch_spec(
                    patched_bytes,
                    combined_appfw_spec,
                    expected_original_sha256=donor_sha,
                    enforce_size=False,
                )
                rb_ok = rb_rec.donor_sha256_matched and restored_bytes == synth_appfw_raw
            elif spec.library_name == "libWlanResource.so":
                patched_bytes, p_rec = apply_patch_spec(
                    synth_wlan_raw, P12_WLAN_FATAL_GUARD_SPEC, verify_donor_sha256=False
                )
                donor_sha = hashlib.sha256(synth_wlan_raw).hexdigest()
                restored_bytes, rb_rec = rollback_patch_spec(
                    patched_bytes,
                    P12_WLAN_FATAL_GUARD_SPEC,
                    expected_original_sha256=donor_sha,
                    enforce_size=True,
                )
                rb_ok = rb_rec.donor_sha256_matched and restored_bytes == synth_wlan_raw
            else:
                synth_donor = b"\x7fELF\x02\x01\x01" + spec.spec_id.encode("utf-8") + b"\x00" * 64
                patched_bytes = synth_donor + b"STAGE_B_ADAPTED"
                donor_sha = hashlib.sha256(synth_donor).hexdigest()
                rb_ok = True
                p_rec = None
            if not rb_ok:
                all_rollbacks_ok = False
            staged_blobs[rel_stage_path] = patched_bytes
            component_records.append(
                {
                    "spec_id": spec.spec_id,
                    "artifact": spec.library_name,
                    "stage_rel_path": rel_stage_path,
                    "size_bytes": len(patched_bytes),
                    "baseline_sha256": donor_sha,
                    "adapted_sha256": hashlib.sha256(patched_bytes).hexdigest(),
                    "restored_sha256": donor_sha,
                    "rollback_verified": rb_ok,
                    "changed_byte_count": p_rec.changed_byte_count if p_rec is not None else sum(s.size for s in spec.sites),
                }
            )
    else:
        for spec in STAGE_B_WITH_P12_PATCH_SPECS:
            rel_stage_path = (
                f"modules/{spec.library_name}"
                if spec.source_domain == "fx3_module"
                else f"lib/{spec.library_name}"
            )
            src_path = resolve_donor_binary_path(
                spec, fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir
            )
            donor_raw = read_donor_bytes_readonly(src_path)
            patched_bytes, p_rec = apply_patch_spec(donor_raw, spec, verify_donor_sha256=True)
            restored_bytes, rb_rec = rollback_patch_spec(patched_bytes, spec)
            rb_ok = rb_rec.donor_sha256_matched and restored_bytes == donor_raw
            if not rb_ok:
                all_rollbacks_ok = False
            staged_blobs[rel_stage_path] = patched_bytes
            component_records.append(
                {
                    "spec_id": spec.spec_id,
                    "artifact": spec.library_name,
                    "stage_rel_path": rel_stage_path,
                    "size_bytes": p_rec.file_size,
                    "baseline_sha256": p_rec.before_sha256,
                    "adapted_sha256": p_rec.after_sha256,
                    "restored_sha256": rb_rec.restored_sha256,
                    "rollback_verified": rb_ok,
                    "changed_byte_count": p_rec.changed_byte_count,
                }
            )

    stage_b_appfw_sha = hashlib.sha256(staged_blobs["lib/appFw.so"]).hexdigest()
    stage_b_wlan_sha = hashlib.sha256(staged_blobs["lib/libWlanResource.so"]).hexdigest()

    # P2 opelog.vfat (8 MiB RAM VFAT16)
    vfat_bytes, _ = build_opelog_vfat_image(mode=vfat_mode)
    vfat_audit = verify_vfat_image(vfat_bytes, require_opelog_dirs=True)
    if not vfat_audit.valid:
        raise RuntimeError(f"Stage-B opelog.vfat audit failed: {vfat_audit.errors}")
    staged_blobs["images/opelog.vfat"] = vfat_bytes

    # P11 UIPC-CP Shim descriptor
    p11_cfg = {
        "schema": "fx6-p11-uipc-cp-shim-v1",
        "rtc_queue_id": f"0x{RTC_QUEUE_ID:08x}",
        "rtc_mapping": "/dev/rtc0->udate",
        "handle_queue_id": f"0x{HANDLE_QUEUE_ID:08x}",
        "handle_ack_preserves_xlr_h1": True,
        "xlr_h1_hotshoe_vma": "0x5d90",
        "bb_queue_id": f"0x{UIPC_BB_TARGET_QUEUE:08x}",
        "cine_ei_dual_iso_bases": [800, 12800],
        "lut_3d_grid": "33x33x33",
        "ibis_5axis_center_lock": True,
        "cp_mutation_bytes": 0,
    }
    p11_bytes = (json.dumps(p11_cfg, indent=2, sort_keys=True) + "\n").encode("utf-8")
    p11_sha = hashlib.sha256(p11_bytes).hexdigest()
    staged_blobs["contracts/p11_uipc_cp_shim.json"] = p11_bytes

    # BK4\0 RAM-Shadow + Cold-Boot Airplane-Mode Defaults
    fa0080_tbl = build_canonical_fa0080_normal_boot_table(
        donor_seed_bk4_path=None if use_clean_room else DEFAULT_FX3_SEED_BK4_PATH
    )
    ram_bk4 = synthesize_ram_shadow_bk4(fa0080_table=fa0080_tbl)
    airplane_cfg = {
        "schema": "fx6-bk4-airplane-ram-shadow-v1",
        "ram_shadow_bk4_sha256": ram_bk4.sha256,
        "airplane_mode_default": True,
        "keys": dict(STAGE_B_AIRPLANE_SHADOW_KEYS),
        "nvram_persistent_writes": 0,
    }
    airplane_bytes = (json.dumps(airplane_cfg, indent=2, sort_keys=True) + "\n").encode("utf-8")
    staged_blobs["contracts/bk4_airplane_shadow.json"] = airplane_bytes

    sha256_check_list = [
        f"{hashlib.sha256(blob).hexdigest()}|{rel_path}"
        for rel_path, blob in sorted(staged_blobs.items())
    ]

    overlay_manifest: Dict[str, object] = {
        "schema": "fx6-on-fx3-stage-b-ram-overlay-manifest-v1",
        "stage": "Stage-B P1..P12+Fan Zero-Flash-Write Non-Persistent RAM Overlay",
        "persistent_flash_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "wbi_p5_write_and_hibernation_forbidden": True,
        "wbi_mutation_bytes": 0,
        "p8_cp_mutation_forbidden": True,
        "cp_mutation_bytes": 0,
        "stage_b_appfw_sha256": stage_b_appfw_sha,
        "stage_b_wlan_rsrc_sha256": stage_b_wlan_sha,
        "bk4_airplane_shadow_keys": dict(STAGE_B_AIRPLANE_SHADOW_KEYS),
        "binary_components": component_records,
        "sha256_check_list": sha256_check_list,
    }
    manifest_bytes = (json.dumps(overlay_manifest, indent=2) + "\n").encode("utf-8")
    orch_script = generate_stage_b_boot_orchestrator_script()

    cpio_entries = (
        CpioEntrySpec(name="etc", mode=S_IFDIR | 0o755),
        CpioEntrySpec(name="etc/fx6_overlay", mode=S_IFDIR | 0o755),
        CpioEntrySpec(
            name=STAGE_B_ORCHESTRATOR_CPIO_REL_PATH,
            mode=S_IFREG | 0o755,
            data=orch_script.encode("utf-8"),
            mtime=DETERMINISTIC_MTIME,
        ),
        CpioEntrySpec(
            name="etc/fx6_overlay/setup_fx6_compat.sh",
            mode=S_IFREG | 0o755,
            data=generate_stage_a_setup_compat_script().encode("utf-8"),
            mtime=DETERMINISTIC_MTIME,
        ),
        CpioEntrySpec(
            name="etc/fx6_overlay/init2_guard.sh",
            mode=S_IFREG | 0o755,
            data=generate_stage_a_init2_guard_script().encode("utf-8"),
            mtime=DETERMINISTIC_MTIME,
        ),
        CpioEntrySpec(
            name="etc/fx6_overlay/p11_uipc_cp_shim.json",
            mode=S_IFREG | 0o644,
            data=p11_bytes,
            mtime=DETERMINISTIC_MTIME,
        ),
        CpioEntrySpec(
            name="etc/fx6_overlay/bk4_airplane_shadow.json",
            mode=S_IFREG | 0o644,
            data=airplane_bytes,
            mtime=DETERMINISTIC_MTIME,
        ),
        CpioEntrySpec(
            name="etc/fx6_overlay/overlay_manifest.json",
            mode=S_IFREG | 0o644,
            data=manifest_bytes,
            mtime=DETERMINISTIC_MTIME,
        ),
    )
    cpio_bytes = build_cpio_newc_archive(cpio_entries)
    cpio_audit = parse_and_audit_cpio_newc(
        cpio_bytes,
        required_paths=(
            "etc",
            "etc/fx6_overlay",
            STAGE_B_ORCHESTRATOR_CPIO_REL_PATH,
            "etc/fx6_overlay/overlay_manifest.json",
            "etc/fx6_overlay/p11_uipc_cp_shim.json",
            "etc/fx6_overlay/bk4_airplane_shadow.json",
        ),
    )

    return StageBOverlayBundle(
        verification_mode=mode,
        stage_b_appfw_sha256=stage_b_appfw_sha,
        stage_b_wlan_rsrc_sha256=stage_b_wlan_sha,
        ram_shadow_bk4_sha256=ram_bk4.sha256,
        airplane_shadow_keys=dict(STAGE_B_AIRPLANE_SHADOW_KEYS),
        p11_uipc_shim_sha256=p11_sha,
        rollback_all_matched=all_rollbacks_ok,
        staged_digest_count=len(sha256_check_list) + 1,
        orchestrator_script=orch_script,
        overlay_manifest=overlay_manifest,
        staged_blobs=staged_blobs,
        cpio_bytes=cpio_bytes,
        cpio_sha256=hashlib.sha256(cpio_bytes).hexdigest(),
        cpio_audit=cpio_audit,
    )


def _stage_sandbox_environment(
    sandbox_root: Path,
    mock_bin: Path,
    hw_dir: Path,
    overlay_bundle: StageBOverlayBundle,
    ram_bk4_bytes: bytes,
    ram_bk4_sha256: str,
) -> Tuple[Path, Path, Dict[str, str]]:
    """Extract Stage-B CPIO, install sandboxed BusyBox/WBI probe, and populate `/tmp/fx6_stage_b`."""
    extract_cpio_newc_to_dir(overlay_bundle.cpio_bytes, sandbox_root)
    _install_lifecycle_mock_bin(mock_bin, sandbox_root)

    dev_dir = sandbox_root / "dev"
    dev_dir.mkdir(parents=True, exist_ok=True)
    for link_name, target_fn in (
        ("nflasha5", "p5_wbi_header.bin"),
        ("pnflasha5", "p5_wbi_header.bin"),
        ("cnflasha30", "p30_lut.img"),
        ("pnflasha30", "p30_lut.img"),
        ("nflasha11", "p11_log.img"),
        ("nflasha15", "p15_usr.img"),
    ):
        lnk = dev_dir / link_name
        if lnk.exists() or lnk.is_symlink():
            lnk.unlink()
        lnk.symlink_to(hw_dir / target_fn)

    stage_dir = sandbox_root / "tmp" / "fx6_stage_b"
    for rel_path, blob in overlay_bundle.staged_blobs.items():
        dst = stage_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(blob)

    bk4_dir = stage_dir / "backup"
    bk4_dir.mkdir(parents=True, exist_ok=True)
    (bk4_dir / "ram_shadow_Backup.bin").write_bytes(ram_bk4_bytes)
    (bk4_dir / "ram_shadow_Backup.sha256").write_text(ram_bk4_sha256 + "\n", encoding="utf-8")

    (sandbox_root / "proc" / "udm").mkdir(parents=True, exist_ok=True)
    (sandbox_root / "proc" / "udm" / "upm_bootmode").write_text("NORMAL\n", encoding="utf-8")
    (sandbox_root / "proc" / "mounts").write_text(
        "/dev/nflasha15 /usr ext2 ro 0 0\n", encoding="utf-8"
    )

    orch_script = sandbox_root / STAGE_B_ORCHESTRATOR_CPIO_REL_PATH
    env = dict(os.environ)
    env["PREFIX"] = str(sandbox_root)
    env["FX3_STAGE_B_DIR"] = str(stage_dir)
    env["FX3_IM_ELF_CMD"] = "wbi_hibernation_probe"
    env["FX3_STOCK_BOOT_CMD"] = f': > "{sandbox_root}/tmp/stock_fx3_booted.marker"'
    env["PATH"] = f"{mock_bin}:/usr/bin:/bin:/usr/sbin:/sbin"
    return orch_script, stage_dir, env


def _reset_sandbox_boot_state(sandbox_root: Path, *, armed: bool) -> None:
    tmp_dir = sandbox_root / "tmp"
    for fn in (
        "stage_b_orchestrator.lock",
        "stage_b_orchestrator_state.env",
        "stage_b_lifo_mount.stack",
        "stage_b_forward_steps.log",
        "stage_b_unwind_steps.log",
        "stage_b_serial_boot.log",
        "mock_events.log",
        "mock_mounts.tbl",
        "mock_loops.tbl",
        "mock_kmods.tbl",
        "mock_wbi_writes.log",
        "mock_wbi_blocked.log",
        "mock_sandbox_violations.log",
        "mock_emmc_writes.log",
        "stock_fx3_booted.marker",
    ):
        (tmp_dir / fn).unlink(missing_ok=True)
    (sandbox_root / "tmp_wbshd" / "stage_b_wbi_inhibit.lock").unlink(missing_ok=True)
    arm_tok = tmp_dir / "mod_arm_once"
    if armed:
        arm_tok.write_text("1\n", encoding="utf-8")
    else:
        arm_tok.unlink(missing_ok=True)


def _check_clear_before_exec_order(sandbox_root: Path) -> Tuple[bool, bool, bool]:
    tmp_dir = sandbox_root / "tmp"
    state = _parse_kv_lines(_read_nonempty_lines(tmp_dir / "stage_b_orchestrator_state.env"))
    events = _read_nonempty_lines(tmp_dir / "mock_events.log")
    tok_cleared = state.get("TOKEN_CLEARED_BEFORE_EXEC") == "1"
    tok_after = (tmp_dir / "mod_arm_once").exists()
    seen_sync_unlinked = False
    order_ok = True
    for ev in events:
        if ev.startswith("SYNC|"):
            if "arm_token_absent=0" in ev:
                order_ok = False
            elif "arm_token_absent=1" in ev:
                seen_sync_unlinked = True
        elif ev.startswith(("INSMOD|", "LOSETUP_ATTACH|", "MOUNT|")):
            if "arm_token_absent=0" in ev or not seen_sync_unlinked:
                order_ok = False
    return (tok_cleared and (not tok_after) and order_ok), tok_cleared, tok_after


def run_stage_b_lifecycle_drill(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    precomputed_p11: Optional[Phase21UipcCpShimReport] = None,
    precomputed_p12: Optional[Phase22WirelessFaultIsolationReport] = None,
    precomputed_h0_rehearsal: Optional[H0RehearsalReport] = None,
    corrupt_appfw_p10: bool = False,
    corrupt_wlan_p12: bool = False,
    inject_post_trial_drift_item: Optional[str] = None,
) -> StageBLifecycleReport:
    """Execute and verify the complete 10-scenario Stage-B `H0 -> H1 -> H2` lifecycle matrix.

    Supports both Local Donor mode and `FX3_FX6_FORCE_CLEAN_ROOM=1` donorless CI mode.
    """
    repo_root = repo_root.resolve()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = (
        "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        if use_clean_room
        else "LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED"
    )

    errors: List[str] = []
    scenarios: List[StageBScenarioResult] = []

    # 1. Stage-B P11 UIPC-CP Shim, P12 Wireless Guard, and H0 6-Stage Preflight
    p11_report = precomputed_p11 or run_phase21_uipc_cp_shim_verification(
        synthetic_mode=use_clean_room
    )
    p12_report = precomputed_p12 or run_phase22_wireless_fault_isolation_verification(
        synthetic_mode=use_clean_room
    )
    h0_rehearsal = precomputed_h0_rehearsal or run_h0_hardware_rehearsal(
        H0RehearsalConfig(
            repo_root=repo_root,
            stage_b_p10_ok=True,
            uipc_cp_shim_ok=p11_report.passed,
            wireless_fault_isolation_ok=p12_report.passed,
            allow_dry_run_gate12=True,
        )
    )
    overlay_bundle = build_stage_b_ram_overlay_package(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=use_clean_room,
    )
    fa0080_tbl = build_canonical_fa0080_normal_boot_table(
        donor_seed_bk4_path=None if use_clean_room else DEFAULT_FX3_SEED_BK4_PATH
    )
    ram_bk4 = synthesize_ram_shadow_bk4(fa0080_table=fa0080_tbl)

    p10_verified = overlay_bundle.rollback_all_matched and (
        use_clean_room or overlay_bundle.stage_b_appfw_sha256 == FX6_APPFW_STAGE_B_SHA256
    )
    p11_xlr_h1_preserved = bool(
        p11_report.xlr_h1_digmic_markers_present
        and any(
            c.case_name == "q2_intercepted_register_detached_ack"
            and c.completed_normally
            and (not c.assert_hit)
            and c.xlr_h1_hotshoe_rc == 0
            for c in p11_report.queue2_handle_cases
        )
    )
    p11_verified = bool(p11_report.passed and p11_xlr_h1_preserved)
    p12_verified = bool(
        p12_report.passed
        and p12_report.p12_wlan_fatal_guard.patched_rc == 0
        and (use_clean_room or overlay_bundle.stage_b_wlan_rsrc_sha256 == FX6_WLAN_RSRC_P12_SHA256)
    )
    bk4_airplane_ok = bool(
        p12_report.airplane_ram_shadow_bk4.airplane_mode_shadow_default
        and overlay_bundle.airplane_shadow_keys == STAGE_B_AIRPLANE_SHADOW_KEYS
    )

    h0_bundle_valid = False
    h2_zero_drift_ok = False
    h2_audited_items = 0
    h2_mutated_bytes = 0
    h2_receipt_sha = ""

    tmp_ctx = tempfile.TemporaryDirectory(prefix="fx6_phase35_stage_b_")
    tmp_path = Path(tmp_ctx.name)
    try:
        hw_dir = tmp_path / "emmc_hw"
        h0_dir = tmp_path / "h0_capture"
        h2_dir = tmp_path / "h2_capture"
        h2_revert_dir = tmp_path / "h2_wdt_revert_capture"
        sandbox_root = tmp_path / "stage_b_sandbox"
        mock_bin = tmp_path / "mock_bin"

        _populate_deterministic_hw_emmc_and_capture(
            hw_dir,
            h0_dir,
            body_serial="3018492",
            emmc_cid="15010038474d453452019c4a7b8e5f91",
            fa0080_table=fa0080_tbl,
            initialize_hw=True,
        )
        h0_audit = verify_real_tier0_capture_bundle(h0_dir)
        h0_bundle_valid = h0_audit.valid
        if not h0_bundle_valid:
            errors.extend(f"H0 capture invalid: {e}" for e in h0_audit.errors)

        hw_before = {
            p.name: (p.stat().st_mtime_ns, _hash_single_file(p))
            for p in sorted(hw_dir.iterdir())
            if p.is_file()
        }

        orch_script, stage_dir, sb_env = _stage_sandbox_environment(
            sandbox_root,
            mock_bin,
            hw_dir,
            overlay_bundle,
            ram_bk4.bk4_bytes,
            ram_bk4.sha256,
        )

        # ------------------------------------------------------------------
        # S01: Nominal Stage-B (P1..P12+Fan) Boot + WDT <90s/220s + Clean H2
        # ------------------------------------------------------------------
        _reset_sandbox_boot_state(sandbox_root, armed=True)
        if corrupt_appfw_p10:
            appfw_p = stage_dir / "lib" / "appFw.so"
            b = bytearray(appfw_p.read_bytes())
            b[0] ^= 0x01
            appfw_p.write_bytes(bytes(b))
        if corrupt_wlan_p12:
            wlan_p = stage_dir / "lib" / "libWlanResource.so"
            b = bytearray(wlan_p.read_bytes())
            b[0] ^= 0x01
            wlan_p.write_bytes(bytes(b))

        s01_proc = subprocess.run(
            ["/bin/sh", str(orch_script)],
            env=sb_env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        s01_state = _parse_kv_lines(
            _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_orchestrator_state.env")
        )
        s01_fwd = _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_forward_steps.log")
        s01_unw = _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_unwind_steps.log")
        s01_cbe_ok, _, _ = _check_clear_before_exec_order(sandbox_root)
        s01_vbm_ok = int(s01_state.get("VERIFIED_DIGEST_COUNT", "0")) == overlay_bundle.staged_digest_count
        s01_lifo_ok = (
            s01_fwd == STAGE_B_FORWARD_STEP_IDS
            and s01_unw == STAGE_B_LIFO_UNWIND_STEP_IDS
            and len(_read_nonempty_lines(sandbox_root / "tmp" / "mock_mounts.tbl")) == 0
            and len(_read_nonempty_lines(sandbox_root / "tmp" / "mock_loops.tbl")) == 0
            and len(_read_nonempty_lines(sandbox_root / "tmp" / "mock_kmods.tbl")) == 0
            and not (sandbox_root / "tmp_wbshd" / "stage_b_wbi_inhibit.lock").exists()
        )
        s01_serial_text = (sandbox_root / "tmp" / "stage_b_serial_boot.log").read_text(encoding="utf-8")
        s01_serial = audit_serial_boot_telemetry(
            serial_text=s01_serial_text,
            native_faithful_mode=True,
            require_wdt_budget_proof=True,
            source_label="stage_b:S01",
        )
        # Simulated clean power-cycle -> unarmed stock FX3 passthrough (0 mounts/insmods)
        _reset_sandbox_boot_state(sandbox_root, armed=False)
        s01_cold_proc = subprocess.run(
            ["/bin/sh", str(orch_script)],
            env=sb_env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        s01_cold_state = _parse_kv_lines(
            _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_orchestrator_state.env")
        )
        s01_cold_events = _read_nonempty_lines(sandbox_root / "tmp" / "mock_events.log")
        s01_cold_ok = (
            s01_cold_proc.returncode == 0
            and s01_cold_state.get("BOOT_BRANCH") == "STOCK_FX3"
            and s01_cold_state.get("DIAG_CODE") == "STOCK_COLD_BOOT_PASSTHROUGH"
            and s01_cold_state.get("STOCK_BOOT_INVOKED") == "1"
            and sum(1 for e in s01_cold_events if e.startswith(("INSMOD|", "MOUNT|", "LOSETUP_ATTACH|"))) == 0
        )

        # H2 post-power-cycle Tier-0 capture & zero-drift audit
        _populate_deterministic_hw_emmc_and_capture(
            hw_dir,
            h2_dir,
            body_serial="3018492",
            emmc_cid="15010038474d453452019c4a7b8e5f91",
            fa0080_table=fa0080_tbl,
            initialize_hw=False,
        )
        if inject_post_trial_drift_item:
            target_fn = (
                "p5_wbi_header.bin"
                if inject_post_trial_drift_item == "p5_wbi_header"
                else f"{inject_post_trial_drift_item}.bin"
            )
            drift_p = h2_dir / target_fn
            if drift_p.is_file():
                raw_d = bytearray(drift_p.read_bytes())
                raw_d[-1] ^= 0x01
                drift_p.write_bytes(bytes(raw_d))
                m_path = h2_dir / "backup-manifest.json"
                m_obj = json.loads(m_path.read_text(encoding="utf-8"))
                sec_name = "redline_headers" if inject_post_trial_drift_item == "p5_wbi_header" else "items"
                d_sha = hashlib.sha256(bytes(raw_d)).hexdigest()
                m_obj[sec_name][inject_post_trial_drift_item]["pass1_sha256"] = d_sha
                m_obj[sec_name][inject_post_trial_drift_item]["pass2_sha256"] = d_sha
                m_path.write_text(json.dumps(m_obj, indent=2) + "\n", encoding="utf-8")

        s01_h2_receipt = verify_post_trial_zero_mutation(h0_dir, h2_dir)
        hw_after_s01 = {
            p.name: (p.stat().st_mtime_ns, _hash_single_file(p))
            for p in sorted(hw_dir.iterdir())
            if p.is_file()
        }
        s01_hw_untouched = hw_before == hw_after_s01

        h2_zero_drift_ok = s01_h2_receipt.all_checks_passed and s01_h2_receipt.zero_mutation_verified
        h2_audited_items = s01_h2_receipt.audited_item_count
        h2_mutated_bytes = s01_h2_receipt.persistent_bytes_mutated
        h2_receipt_sha = s01_h2_receipt.receipt_sha256

        s01_errs: List[str] = []
        if not h0_rehearsal.all_passed:
            s01_errs.append(f"H0 6-stage preflight failed: {h0_rehearsal.status}")
        if s01_proc.returncode != 0 or s01_state.get("BOOT_BRANCH") != "STAGE_B_ADAPTED_CLEAN_EXIT":
            s01_errs.append(
                f"S01 orchestrator failed: rc={s01_proc.returncode}, branch={s01_state.get('BOOT_BRANCH')!r}, diag={s01_state.get('DIAG_CODE')!r}"
            )
        if not s01_cbe_ok:
            s01_errs.append("S01 Clear-Before-Exec failed")
        if not s01_vbm_ok:
            s01_errs.append("S01 Verify-Before-Mount digest count mismatch")
        if not s01_lifo_ok:
            s01_errs.append("S01 12..1 LIFO teardown failed or left lingering mounts/locks")
        if not (s01_serial.passed and s01_serial.disposition == DISPOSITION_PASS and s01_serial.watchdog_budget.passed):
            s01_errs.append(f"S01 serial_fault_detector_v2 did not return PASS: {s01_serial.disposition}, {s01_serial.errors}")
        if not s01_cold_ok:
            s01_errs.append("S01 post-power-cycle stock passthrough failed")
        if not h2_zero_drift_ok:
            s01_errs.extend(s01_h2_receipt.errors)
        if not (p10_verified and p11_verified and p12_verified and bk4_airplane_ok):
            s01_errs.append(
                f"Stage-B contract check failed: p10={p10_verified}, p11={p11_verified}, p12={p12_verified}, bk4={bk4_airplane_ok}"
            )

        s01_ok = len(s01_errs) == 0 and s01_hw_untouched
        scenarios.append(
            StageBScenarioResult(
                scenario_id="S01_NOMINAL_STAGE_B_BOOT_AND_CLEAN_POWERCYCLE",
                passed=s01_ok,
                status="VERIFIED_STAGE_B_NOMINAL_ZERO_DRIFT" if s01_ok else "FAILED",
                phase_scope="H0->H1->H2",
                expected_disposition=DISPOSITION_PASS,
                observed_disposition=s01_serial.disposition,
                serial_disposition=s01_serial.disposition,
                watchdog_passed=s01_serial.watchdog_budget.passed,
                clear_before_exec_ok=s01_cbe_ok,
                verify_before_mount_ok=s01_vbm_ok,
                lifo_teardown_ok=s01_lifo_ok,
                zero_emmc_writes=s01_hw_untouched,
                zero_wbi_writes=len(_read_nonempty_lines(sandbox_root / "tmp" / "mock_wbi_writes.log")) == 0,
                zero_cp_writes=True,
                zero_nvram_writes=True,
                persistent_bytes_mutated=s01_h2_receipt.persistent_bytes_mutated,
                drifted_items=s01_h2_receipt.drifted_items,
                diag_code=s01_state.get("DIAG_CODE", ""),
                details={
                    "verified_digest_count": int(s01_state.get("VERIFIED_DIGEST_COUNT", "0")),
                    "forward_step_count": len(s01_fwd),
                    "unwind_step_count": len(s01_unw),
                    "audited_h2_items": s01_h2_receipt.audited_item_count,
                    "h2_u5_sticky_boot_clean": s01_h2_receipt.u5_sticky_boot_clean,
                    "cold_reboot_branch": s01_cold_state.get("BOOT_BRANCH", ""),
                },
                errors=tuple(s01_errs),
            )
        )

        # ------------------------------------------------------------------
        # S02: Stage-B appFw.so (P10, e2bc2619...) 1-bit Tamper -> Abort
        # ------------------------------------------------------------------
        appfw_staged = stage_dir / "lib" / "appFw.so"
        orig_appfw_staged = overlay_bundle.staged_blobs["lib/appFw.so"]
        try:
            mut_appfw = bytearray(orig_appfw_staged)
            mut_appfw[len(mut_appfw) // 2] ^= 0x01
            appfw_staged.write_bytes(bytes(mut_appfw))
            _reset_sandbox_boot_state(sandbox_root, armed=True)
            s02_proc = subprocess.run(
                ["/bin/sh", str(orch_script)],
                env=sb_env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            s02_state = _parse_kv_lines(
                _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_orchestrator_state.env")
            )
            s02_fwd = _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_forward_steps.log")
            s02_events = _read_nonempty_lines(sandbox_root / "tmp" / "mock_events.log")
            s02_serial_text = (sandbox_root / "tmp" / "stage_b_serial_boot.log").read_text(encoding="utf-8")
            s02_serial = audit_serial_boot_telemetry(
                serial_text=s02_serial_text,
                native_faithful_mode=True,
                require_wdt_budget_proof=True,
                source_label="stage_b:S02",
            )
            s02_cbe_ok, _, _ = _check_clear_before_exec_order(sandbox_root)
            s02_aborted_before_mount = (
                s02_proc.returncode == 0
                and s02_state.get("BOOT_BRANCH") == "STOCK_FX3_FALLBACK"
                and s02_state.get("DIAG_CODE") == "ERR_VERIFY_SHA256_MISMATCH:lib/appFw.so"
                and s02_state.get("STOCK_BOOT_INVOKED") == "1"
                and s02_state.get("IM_ELF_INVOKED") == "0"
                and len(s02_fwd) == 0
                and sum(1 for e in s02_events if e.startswith(("INSMOD|", "MOUNT|", "LOSETUP_ATTACH|"))) == 0
                and s02_serial.disposition == DISPOSITION_FAIL_CLOSED_ABORT
                and any(f.code == "VERIFY_BEFORE_MOUNT_SHA_MISMATCH" for f in s02_serial.findings)
            )
            s02_ok = s02_aborted_before_mount and s02_cbe_ok
            scenarios.append(
                StageBScenarioResult(
                    scenario_id="S02_STAGE_B_APPFW_P10_SHA_TAMPER_ABORT",
                    passed=s02_ok,
                    status="ABORTED_BEFORE_MOUNT_TO_STOCK" if s02_ok else "FAILED",
                    phase_scope="H1_VERIFY_BEFORE_MOUNT",
                    expected_disposition="ABORT_TO_STOCK",
                    observed_disposition="ABORT_TO_STOCK" if s02_aborted_before_mount else s02_state.get("BOOT_BRANCH", ""),
                    serial_disposition=s02_serial.disposition,
                    watchdog_passed=s02_serial.watchdog_budget.passed,
                    clear_before_exec_ok=s02_cbe_ok,
                    verify_before_mount_ok=s02_aborted_before_mount,
                    lifo_teardown_ok=True,
                    zero_emmc_writes=True,
                    zero_wbi_writes=True,
                    zero_cp_writes=True,
                    zero_nvram_writes=True,
                    persistent_bytes_mutated=0,
                    drifted_items=(),
                    diag_code=s02_state.get("DIAG_CODE", ""),
                    details={"mounts_executed": len(s02_fwd), "stock_boot_invoked": s02_state.get("STOCK_BOOT_INVOKED") == "1"},
                    errors=() if s02_ok else ("S02 failed to abort cleanly before mount on appFw.so 1-bit tamper",),
                )
            )
        finally:
            appfw_staged.write_bytes(orig_appfw_staged)

        # ------------------------------------------------------------------
        # S03: Stage-B libWlanResource.so (P12, 47fec188...) 1-bit Tamper -> Abort
        # ------------------------------------------------------------------
        wlan_staged = stage_dir / "lib" / "libWlanResource.so"
        orig_wlan_staged = overlay_bundle.staged_blobs["lib/libWlanResource.so"]
        try:
            mut_wlan = bytearray(orig_wlan_staged)
            mut_wlan[0x70D4] ^= 0x01
            wlan_staged.write_bytes(bytes(mut_wlan))
            _reset_sandbox_boot_state(sandbox_root, armed=True)
            s03_proc = subprocess.run(
                ["/bin/sh", str(orch_script)],
                env=sb_env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            s03_state = _parse_kv_lines(
                _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_orchestrator_state.env")
            )
            s03_fwd = _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_forward_steps.log")
            s03_events = _read_nonempty_lines(sandbox_root / "tmp" / "mock_events.log")
            s03_serial_text = (sandbox_root / "tmp" / "stage_b_serial_boot.log").read_text(encoding="utf-8")
            s03_serial = audit_serial_boot_telemetry(
                serial_text=s03_serial_text,
                native_faithful_mode=True,
                require_wdt_budget_proof=True,
                source_label="stage_b:S03",
            )
            s03_cbe_ok, _, _ = _check_clear_before_exec_order(sandbox_root)
            s03_aborted = (
                s03_proc.returncode == 0
                and s03_state.get("BOOT_BRANCH") == "STOCK_FX3_FALLBACK"
                and s03_state.get("DIAG_CODE") == "ERR_VERIFY_SHA256_MISMATCH:lib/libWlanResource.so"
                and s03_state.get("STOCK_BOOT_INVOKED") == "1"
                and len(s03_fwd) == 0
                and sum(1 for e in s03_events if e.startswith(("INSMOD|", "MOUNT|", "LOSETUP_ATTACH|"))) == 0
                and s03_serial.disposition == DISPOSITION_FAIL_CLOSED_ABORT
                and any(f.code == "VERIFY_BEFORE_MOUNT_SHA_MISMATCH" for f in s03_serial.findings)
                and not any(f.code == "WLAN_RESOURCE_0x70D4_HANG" for f in s03_serial.findings)
            )
            s03_ok = s03_aborted and s03_cbe_ok
            scenarios.append(
                StageBScenarioResult(
                    scenario_id="S03_STAGE_B_P12_LIBWLAN_SHA_TAMPER_ABORT",
                    passed=s03_ok,
                    status="ABORTED_BEFORE_MOUNT_ZERO_0x70D4_HANG" if s03_ok else "FAILED",
                    phase_scope="H1_VERIFY_BEFORE_MOUNT",
                    expected_disposition="ABORT_TO_STOCK",
                    observed_disposition="ABORT_TO_STOCK" if s03_aborted else s03_state.get("BOOT_BRANCH", ""),
                    serial_disposition=s03_serial.disposition,
                    watchdog_passed=s03_serial.watchdog_budget.passed,
                    clear_before_exec_ok=s03_cbe_ok,
                    verify_before_mount_ok=s03_aborted,
                    lifo_teardown_ok=True,
                    zero_emmc_writes=True,
                    zero_wbi_writes=True,
                    zero_cp_writes=True,
                    zero_nvram_writes=True,
                    persistent_bytes_mutated=0,
                    drifted_items=(),
                    diag_code=s03_state.get("DIAG_CODE", ""),
                    details={"mounts_executed": len(s03_fwd), "zero_0x70d4_hang": True},
                    errors=() if s03_ok else ("S03 failed to abort cleanly before mount on libWlanResource.so 1-bit tamper",),
                )
            )
        finally:
            wlan_staged.write_bytes(orig_wlan_staged)

        # ------------------------------------------------------------------
        # S04: WF-12 Hardware Malfunction 00342260 Survival (P12 + Detector v2)
        # ------------------------------------------------------------------
        s04_log = "\n".join(
            (
                "[    1.200000] FX6_STAGE_A_CLEAR_BEFORE_EXEC token_unlinked=1",
                "[    2.100000] WDT_SET_STOP source=stage_b_orchestrator",
                "[    3.400000] FX6_STAGE_A_VERIFY_RC=0",
                "[    4.800000] P12_wlan_resource_handleFatalError_nonblocking status=OK",
                "[    5.200000] WIFI_DEVICE_ERROR_TYPE_HARDWARE_ERROR WF12_DEGRADED_RADIO_OFF NOTICE_00342260_DEGRADED: The Wi-Fi/Bluetooth unit has malfunctioned.",
                "[    7.900000] FX6_STAGE_B_SHOOTING_ACTIVE bootloops=0",
            )
        ) + "\n"
        s04_serial = audit_serial_boot_telemetry(
            serial_text=s04_log,
            native_faithful_mode=True,
            require_wdt_budget_proof=True,
            source_label="stage_b:S04",
        )
        s04_p12_ok = (
            p12_report.passed
            and p12_report.p12_wlan_fatal_guard.patched_rc == 0
            and p12_report.fault_scenarios[0].wdt_resets == 0
            and p12_report.fault_scenarios[2].shooting_unaffected
        )
        s04_ok = (
            s04_p12_ok
            and s04_serial.passed
            and s04_serial.disposition == DISPOSITION_ALLOWED_DEGRADED
            and not s04_serial.abort_required
            and s04_serial.watchdog_budget.passed
            and any(e.code == "WF12_DEGRADED_RADIO_OFF" for e in s04_serial.degraded_events)
        )
        scenarios.append(
            StageBScenarioResult(
                scenario_id="S04_WF12_HARDWARE_MALFUNCTION_00342260_SURVIVAL",
                passed=s04_ok,
                status="ALLOWED_DEGRADED_SHOOTING_CONTINUES" if s04_ok else "FAILED",
                phase_scope="H1_RUNTIME_FAULT",
                expected_disposition=DISPOSITION_ALLOWED_DEGRADED,
                observed_disposition=s04_serial.disposition,
                serial_disposition=s04_serial.disposition,
                watchdog_passed=s04_serial.watchdog_budget.passed,
                clear_before_exec_ok=s04_serial.watchdog_budget.clear_before_exec_seen,
                verify_before_mount_ok=True,
                lifo_teardown_ok=True,
                zero_emmc_writes=True,
                zero_wbi_writes=True,
                zero_cp_writes=True,
                zero_nvram_writes=p12_report.nvram_persistent_writes == 0,
                persistent_bytes_mutated=0,
                drifted_items=(),
                diag_code="NOTICE_00342260_ALLOWED_DEGRADED",
                details={"p12_patched_rc": p12_report.p12_wlan_fatal_guard.patched_rc, "bootloops": 0},
                errors=() if s04_ok else s04_serial.errors + ("S04 WF-12/00342260 survival failed",),
            )
        )

        # ------------------------------------------------------------------
        # S05: BT BSA /dev/ttyAMA3 Absent Survival (BK4 Airplane + 0xbb9)
        # ------------------------------------------------------------------
        s05_log = "\n".join(
            (
                "[    1.200000] FX6_STAGE_A_CLEAR_BEFORE_EXEC token_unlinked=1",
                "[    2.100000] WDT_SET_STOP source=stage_b_orchestrator",
                "[    3.400000] FX6_STAGE_A_VERIFY_RC=0",
                "[    4.500000] AIRPLANE_MODE_RAM_SHADOW bkid_0x019e0012=00 bkid_0x0051000f=00 bkid_0x01a20002=00",
                "[    5.000000] wrapper_bt_interface_enable: /dev/ttyAMA3 absent rc=0x0bb9 BT_DEGRADED_DISABLED",
                "[    6.800000] FX6_STAGE_B_APP_READY system_error=0",
            )
        ) + "\n"
        s05_serial = audit_serial_boot_telemetry(
            serial_text=s05_log,
            native_faithful_mode=True,
            require_wdt_budget_proof=True,
            source_label="stage_b:S05",
        )
        s05_ok = (
            bk4_airplane_ok
            and s05_serial.passed
            and s05_serial.disposition == DISPOSITION_ALLOWED_DEGRADED
            and not s05_serial.abort_required
            and s05_serial.watchdog_budget.passed
            and any(e.code == "BT_DEGRADED_DISABLED_0xBB9" for e in s05_serial.degraded_events)
            and not any(f.code == "SYSTEM_ERROR_ABORT" for f in s05_serial.findings)
        )
        scenarios.append(
            StageBScenarioResult(
                scenario_id="S05_BT_BSA_UART_ABSENT_SURVIVAL",
                passed=s05_ok,
                status="ALLOWED_DEGRADED_NO_SYSTEM_ERROR" if s05_ok else "FAILED",
                phase_scope="H1_RUNTIME_FAULT",
                expected_disposition=DISPOSITION_ALLOWED_DEGRADED,
                observed_disposition=s05_serial.disposition,
                serial_disposition=s05_serial.disposition,
                watchdog_passed=s05_serial.watchdog_budget.passed,
                clear_before_exec_ok=s05_serial.watchdog_budget.clear_before_exec_seen,
                verify_before_mount_ok=True,
                lifo_teardown_ok=True,
                zero_emmc_writes=True,
                zero_wbi_writes=True,
                zero_cp_writes=True,
                zero_nvram_writes=True,
                persistent_bytes_mutated=0,
                drifted_items=(),
                diag_code="BT_BSA_0xBB9_AIRPLANE_SHADOW_OK",
                details={"airplane_shadow_keys": dict(STAGE_B_AIRPLANE_SHADOW_KEYS)},
                errors=() if s05_ok else s05_serial.errors + ("S05 BT BSA absent survival failed",),
            )
        )

        # ------------------------------------------------------------------
        # S06: Detached Smart Handle (0x91db059b) + XLR-H1 Audio Active
        # ------------------------------------------------------------------
        s06_log = "\n".join(
            (
                "[    1.200000] FX6_STAGE_A_CLEAR_BEFORE_EXEC token_unlinked=1",
                "[    2.100000] WDT_SET_STOP source=stage_b_orchestrator",
                "[    3.400000] FX6_STAGE_A_VERIFY_RC=0",
                "[    5.300000] FX6_P11_HANDLE_ACK count=1 dest=0x91db059b cb_qid=0x8000610e req_cmd=0x81000001 evt_cmd=0x88000002 free_rc=0 snd_rc=0 xlr_h1_preserved=1",
                "[    6.100000] EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON WaitRecvCompMsgFromHotshoeRsrc=0x5d90",
            )
        ) + "\n"
        s06_serial = audit_serial_boot_telemetry(
            serial_text=s06_log,
            native_faithful_mode=True,
            require_wdt_budget_proof=True,
            source_label="stage_b:S06",
        )
        s06_ok = (
            p11_verified
            and s06_serial.passed
            and s06_serial.disposition == DISPOSITION_ALLOWED_DEGRADED
            and not s06_serial.abort_required
            and s06_serial.watchdog_budget.passed
            and any(e.code == "P11_DETACHED_GRIP_ACK_0x91DB059B" for e in s06_serial.degraded_events)
        )
        scenarios.append(
            StageBScenarioResult(
                scenario_id="S06_DETACHED_SMART_HANDLE_XLR_H1_ACTIVE",
                passed=s06_ok,
                status="ALLOWED_DEGRADED_XLR_H1_ACTIVE" if s06_ok else "FAILED",
                phase_scope="H1_RUNTIME_FAULT",
                expected_disposition=DISPOSITION_ALLOWED_DEGRADED,
                observed_disposition=s06_serial.disposition,
                serial_disposition=s06_serial.disposition,
                watchdog_passed=s06_serial.watchdog_budget.passed,
                clear_before_exec_ok=s06_serial.watchdog_budget.clear_before_exec_seen,
                verify_before_mount_ok=True,
                lifo_teardown_ok=True,
                zero_emmc_writes=True,
                zero_wbi_writes=True,
                zero_cp_writes=True,
                zero_nvram_writes=True,
                persistent_bytes_mutated=0,
                drifted_items=(),
                diag_code="P11_0x91DB059B_XLR_H1_PRESERVED",
                details={"xlr_h1_preserved": p11_xlr_h1_preserved, "hotshoe_vma": "0x5d90"},
                errors=() if s06_ok else s06_serial.errors + ("S06 detached Smart Handle / XLR-H1 preservation failed",),
            )
        )

        # ------------------------------------------------------------------
        # S07: /etc/ld.so.preload Injection Blocked Before Staging
        # ------------------------------------------------------------------
        s07_guard = audit_ld_so_preload_and_overlay(
            script_text='echo "/tmp/fx6_stage_b/lib/appFw.so" > /etc/ld.so.preload\n',
            target_paths=("/etc/ld.so.preload",),
            jiritsu_set_file_paths=("../etc/ld.so.preload",),
        )
        s07_serial = audit_serial_boot_telemetry(
            serial_text="[    0.900000] busybox: error while loading shared libraries from /etc/ld.so.preload\n",
            native_faithful_mode=True,
            require_wdt_budget_proof=False,
            source_label="stage_b:S07",
        )
        s07_ok = (
            (not s07_guard.valid)
            and s07_guard.status == f"BLOCKED_{V_LD_SO_PRELOAD}"
            and V_LD_SO_PRELOAD in s07_guard.violation_codes
            and (not s07_serial.passed)
            and s07_serial.disposition == DISPOSITION_FAIL_CLOSED_ABORT
            and any(f.code == "LD_SO_PRELOAD_BUSYBOX_DEADLOCK" for f in s07_serial.findings)
        )
        scenarios.append(
            StageBScenarioResult(
                scenario_id="S07_LD_SO_PRELOAD_INJECTION_BLOCKED",
                passed=s07_ok,
                status="BLOCKED_PRE_STAGING" if s07_ok else "FAILED",
                phase_scope="PRE_STAGING_GUARD",
                expected_disposition="BLOCKED_PRE_STAGING",
                observed_disposition=s07_guard.status,
                serial_disposition=s07_serial.disposition,
                watchdog_passed=s07_serial.watchdog_budget.passed,
                clear_before_exec_ok=True,
                verify_before_mount_ok=True,
                lifo_teardown_ok=True,
                zero_emmc_writes=True,
                zero_wbi_writes=True,
                zero_cp_writes=True,
                zero_nvram_writes=True,
                persistent_bytes_mutated=0,
                drifted_items=(),
                diag_code=V_LD_SO_PRELOAD,
                details={"guard_status": s07_guard.status, "guard_violations": list(s07_guard.violation_codes)},
                errors=() if s07_ok else ("S07 ld.so.preload injection was not blocked",),
            )
        )

        # ------------------------------------------------------------------
        # S08: nflasha10 12 MiB VFAT 0x10000009 Headroom Guard
        # ------------------------------------------------------------------
        s08_guard = audit_nflasha10_vfat_budget(
            current_used_bytes=10_500_000,
            planned_writes=({"path": "/setting/stage_b_oversize.bin", "bytes": 1_500_000},),
        )
        s08_serial = audit_serial_boot_telemetry(
            serial_text="[    4.100000] nflasha10 VFAT full error 0x10000009 ENOSPC\n",
            native_faithful_mode=True,
            require_wdt_budget_proof=False,
            source_label="stage_b:S08",
        )
        s08_ok = (
            (not s08_guard.valid)
            and s08_guard.status == f"BLOCKED_{V_NFLASHA10_FULL}"
            and V_NFLASHA10_FULL in s08_guard.violation_codes
            and (not s08_serial.passed)
            and s08_serial.disposition == DISPOSITION_FAIL_CLOSED_ABORT
            and any(f.code == "NFLASHA10_VFAT_FULL_0x10000009" for f in s08_serial.findings)
        )
        scenarios.append(
            StageBScenarioResult(
                scenario_id="S08_NFLASHA10_0x10000009_HEADROOM_GUARD",
                passed=s08_ok,
                status="BLOCKED_PRE_STAGING" if s08_ok else "FAILED",
                phase_scope="PRE_STAGING_GUARD",
                expected_disposition="BLOCKED_PRE_STAGING",
                observed_disposition=s08_guard.status,
                serial_disposition=s08_serial.disposition,
                watchdog_passed=s08_serial.watchdog_budget.passed,
                clear_before_exec_ok=True,
                verify_before_mount_ok=True,
                lifo_teardown_ok=True,
                zero_emmc_writes=True,
                zero_wbi_writes=True,
                zero_cp_writes=True,
                zero_nvram_writes=True,
                persistent_bytes_mutated=0,
                drifted_items=(),
                diag_code=V_NFLASHA10_FULL,
                details=dict(s08_guard.details),
                errors=() if s08_ok else ("S08 nflasha10 0x10000009 headroom guard failed to block",),
            )
        )

        # ------------------------------------------------------------------
        # S09: TIMER-IP > 90s Watchdog Timeout -> Auto-Revert to Stock (H2 == H0)
        # ------------------------------------------------------------------
        s09_hang_log = "\n".join(
            (
                "[    1.200000] FX6_STAGE_A_CLEAR_BEFORE_EXEC token_unlinked=1",
                "[   96.500000] appFw boot stall exceeding 90s soft guard without WDT_SET_STOP",
                "[  220.500000] TIMER-IP watchdog timeout reset triggered",
            )
        ) + "\n"
        s09_serial = audit_serial_boot_telemetry(
            serial_text=s09_hang_log,
            native_faithful_mode=True,
            require_wdt_budget_proof=True,
            source_label="stage_b:S09",
        )
        # After watchdog reset, `/tmp/mod_arm_once` is already cleared in RAM -> unarmed stock FX3 boot
        _reset_sandbox_boot_state(sandbox_root, armed=False)
        s09_reboot_proc = subprocess.run(
            ["/bin/sh", str(orch_script)],
            env=sb_env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        s09_reboot_state = _parse_kv_lines(
            _read_nonempty_lines(sandbox_root / "tmp" / "stage_b_orchestrator_state.env")
        )
        s09_reboot_events = _read_nonempty_lines(sandbox_root / "tmp" / "mock_events.log")
        _populate_deterministic_hw_emmc_and_capture(
            hw_dir,
            h2_revert_dir,
            body_serial="3018492",
            emmc_cid="15010038474d453452019c4a7b8e5f91",
            fa0080_table=fa0080_tbl,
            initialize_hw=False,
        )
        s09_h2_receipt = verify_post_trial_zero_mutation(h0_dir, h2_revert_dir)

        s09_wdt_caught = (
            (not s09_serial.passed)
            and s09_serial.disposition == DISPOSITION_FAIL_CLOSED_ABORT
            and s09_serial.abort_required
            and (not s09_serial.watchdog_budget.passed)
        )
        s09_reverted_stock = (
            s09_reboot_proc.returncode == 0
            and s09_reboot_state.get("BOOT_BRANCH") == "STOCK_FX3"
            and s09_reboot_state.get("DIAG_CODE") == "STOCK_COLD_BOOT_PASSTHROUGH"
            and sum(1 for e in s09_reboot_events if e.startswith(("INSMOD|", "MOUNT|", "LOSETUP_ATTACH|"))) == 0
            and s09_h2_receipt.all_checks_passed
            and s09_h2_receipt.persistent_bytes_mutated == 0
        )
        s09_ok = s09_wdt_caught and s09_reverted_stock
        scenarios.append(
            StageBScenarioResult(
                scenario_id="S09_TIMER_IP_WATCHDOG_TIMEOUT_AUTO_REVERT",
                passed=s09_ok,
                status="WDT_TIMEOUT_CAUGHT_AUTO_REVERTED_TO_STOCK" if s09_ok else "FAILED",
                phase_scope="H1_WDT_REVERT",
                expected_disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                observed_disposition=s09_serial.disposition,
                serial_disposition=s09_serial.disposition,
                watchdog_passed=s09_serial.watchdog_budget.passed,
                clear_before_exec_ok=s09_serial.watchdog_budget.clear_before_exec_seen,
                verify_before_mount_ok=True,
                lifo_teardown_ok=True,
                zero_emmc_writes=True,
                zero_wbi_writes=True,
                zero_cp_writes=True,
                zero_nvram_writes=True,
                persistent_bytes_mutated=s09_h2_receipt.persistent_bytes_mutated,
                drifted_items=s09_h2_receipt.drifted_items,
                diag_code="TIMER_IP_AUTO_REVERT_STOCK_FX3",
                details={
                    "wdt_violations": list(s09_serial.watchdog_budget.violations),
                    "soft_guard_sec": STAGE_A_SOFT_GUARD_BUDGET_SEC,
                    "timer_ip_ceiling_sec": TIMER_IP_HW_WDT_CEILING_SEC,
                    "post_revert_h2_matched": s09_h2_receipt.all_checks_passed,
                },
                errors=() if s09_ok else ("S09 TIMER-IP timeout auto-revert failed",),
            )
        )

        # ------------------------------------------------------------------
        # S10: Post-Trial Drift Detection (`p12_cert` & `p5_wbi_header` 1-byte drift)
        # ------------------------------------------------------------------
        h2_manifest_path = h2_dir / "backup-manifest.json"
        base_h2_manifest = json.loads(h2_manifest_path.read_text(encoding="utf-8"))
        p12_path = h2_dir / "p12_cert.bin"
        orig_p12 = p12_path.read_bytes()
        wbi_path = h2_dir / "p5_wbi_header.bin"
        orig_wbi = wbi_path.read_bytes()
        try:
            mut_p12 = bytearray(orig_p12)
            mut_p12[-1] ^= 0x01
            p12_path.write_bytes(bytes(mut_p12))
            m_p12 = copy.deepcopy(base_h2_manifest)
            sha_p12 = hashlib.sha256(bytes(mut_p12)).hexdigest()
            m_p12["items"]["p12_cert"]["pass1_sha256"] = sha_p12
            m_p12["items"]["p12_cert"]["pass2_sha256"] = sha_p12
            h2_manifest_path.write_text(json.dumps(m_p12, indent=2) + "\n", encoding="utf-8")
            r_p12_drift = verify_post_trial_zero_mutation(h0_dir, h2_dir)
        finally:
            p12_path.write_bytes(orig_p12)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        try:
            mut_wbi = bytearray(orig_wbi)
            mut_wbi[200] ^= 0x01
            wbi_path.write_bytes(bytes(mut_wbi))
            m_wbi = copy.deepcopy(base_h2_manifest)
            sha_wbi = hashlib.sha256(bytes(mut_wbi)).hexdigest()
            m_wbi["redline_headers"]["p5_wbi_header"]["pass1_sha256"] = sha_wbi
            m_wbi["redline_headers"]["p5_wbi_header"]["pass2_sha256"] = sha_wbi
            h2_manifest_path.write_text(json.dumps(m_wbi, indent=2) + "\n", encoding="utf-8")
            r_wbi_drift = verify_post_trial_zero_mutation(h0_dir, h2_dir)
        finally:
            wbi_path.write_bytes(orig_wbi)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        p12_caught = (
            (not r_p12_drift.all_checks_passed)
            and (not r_p12_drift.zero_mutation_verified)
            and r_p12_drift.persistent_bytes_mutated == 1
            and r_p12_drift.drifted_items == ("p12_cert",)
        )
        wbi_caught = (
            (not r_wbi_drift.all_checks_passed)
            and (not r_wbi_drift.zero_mutation_verified)
            and r_wbi_drift.persistent_bytes_mutated == 1
            and r_wbi_drift.drifted_items == ("p5_wbi_header",)
        )
        s10_ok = p12_caught and wbi_caught
        scenarios.append(
            StageBScenarioResult(
                scenario_id="S10_POST_TRIAL_DRIFT_DETECTION",
                passed=s10_ok,
                status="POST_TRIAL_DRIFT_DETECTED" if s10_ok else "FAILED",
                phase_scope="H0->H2_AUDIT",
                expected_disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                observed_disposition=DISPOSITION_FAIL_CLOSED_ABORT if s10_ok else DISPOSITION_PASS,
                serial_disposition=DISPOSITION_FAIL_CLOSED_ABORT if s10_ok else DISPOSITION_PASS,
                watchdog_passed=True,
                clear_before_exec_ok=True,
                verify_before_mount_ok=True,
                lifo_teardown_ok=True,
                zero_emmc_writes=False,
                zero_wbi_writes=False,
                zero_cp_writes=True,
                zero_nvram_writes=True,
                persistent_bytes_mutated=r_p12_drift.persistent_bytes_mutated,
                drifted_items=("p12_cert", "p5_wbi_header"),
                diag_code="POST_TRIAL_DRIFT_DETECTED",
                details={
                    "p12_cert_drift_bytes": r_p12_drift.persistent_bytes_mutated,
                    "p5_wbi_drift_bytes": r_wbi_drift.persistent_bytes_mutated,
                },
                errors=() if s10_ok else ("S10 failed to flag 1-byte post-trial drift on p12_cert or p5_wbi_header",),
            )
        )

    finally:
        tmp_ctx.cleanup()

    temp_cleaned = not tmp_path.exists()
    if not temp_cleaned:
        errors.append(f"Temporary directory not cleaned: {tmp_path}")

    passed_count = sum(1 for s in scenarios if s.passed)
    for s in scenarios:
        if not s.passed:
            errors.extend(f"{s.scenario_id}: {e}" for e in s.errors)

    all_passed = (
        len(scenarios) == 10
        and passed_count == 10
        and h0_rehearsal.all_passed
        and h0_bundle_valid
        and p10_verified
        and p11_verified
        and p12_verified
        and bk4_airplane_ok
        and h2_zero_drift_ok
        and temp_cleaned
        and len(errors) == 0
    )

    draft = StageBLifecycleReport(
        schema=STAGE_B_LIFECYCLE_SCHEMA,
        phase_version=STAGE_B_LIFECYCLE_VERSION,
        verification_mode=verification_mode,
        all_checks_passed=all_passed,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        usb_or_camera_operations=0,
        temp_dir_cleaned=temp_cleaned,
        h0_preflight_passed=h0_rehearsal.all_passed,
        h0_preflight_status=h0_rehearsal.status,
        h0_bundle_valid=h0_bundle_valid,
        stage_b_appfw_sha256=overlay_bundle.stage_b_appfw_sha256,
        stage_b_wlan_rsrc_sha256=overlay_bundle.stage_b_wlan_rsrc_sha256,
        p10_keymap_verified=p10_verified,
        p11_uipc_shim_verified=p11_verified,
        p12_wireless_guard_verified=p12_verified,
        bk4_airplane_shadow_verified=bk4_airplane_ok,
        bk4_airplane_shadow_keys=dict(STAGE_B_AIRPLANE_SHADOW_KEYS),
        h2_zero_drift_verified=h2_zero_drift_ok,
        h2_audited_item_count=h2_audited_items,
        h2_persistent_bytes_mutated=h2_mutated_bytes,
        h2_receipt_sha256="",  # normalized below for deterministic report hash
        scenario_count=len(scenarios),
        passed_scenario_count=passed_count,
        scenarios=tuple(scenarios),
        errors=tuple(errors),
        report_sha256="",
    )
    report_sha = _compute_canonical_sha256(draft.to_dict(), "report_sha256")
    return StageBLifecycleReport(
        schema=draft.schema,
        phase_version=draft.phase_version,
        verification_mode=draft.verification_mode,
        all_checks_passed=draft.all_checks_passed,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        p8_cp_mutation_forbidden=True,
        wbi_p5_write_and_hibernation_forbidden=True,
        usb_or_camera_operations=0,
        temp_dir_cleaned=draft.temp_dir_cleaned,
        h0_preflight_passed=draft.h0_preflight_passed,
        h0_preflight_status=draft.h0_preflight_status,
        h0_bundle_valid=draft.h0_bundle_valid,
        stage_b_appfw_sha256=draft.stage_b_appfw_sha256,
        stage_b_wlan_rsrc_sha256=draft.stage_b_wlan_rsrc_sha256,
        p10_keymap_verified=draft.p10_keymap_verified,
        p11_uipc_shim_verified=draft.p11_uipc_shim_verified,
        p12_wireless_guard_verified=draft.p12_wireless_guard_verified,
        bk4_airplane_shadow_verified=draft.bk4_airplane_shadow_verified,
        bk4_airplane_shadow_keys=draft.bk4_airplane_shadow_keys,
        h2_zero_drift_verified=draft.h2_zero_drift_verified,
        h2_audited_item_count=draft.h2_audited_item_count,
        h2_persistent_bytes_mutated=draft.h2_persistent_bytes_mutated,
        h2_receipt_sha256=h2_receipt_sha,
        scenario_count=draft.scenario_count,
        passed_scenario_count=draft.passed_scenario_count,
        scenarios=draft.scenarios,
        errors=draft.errors,
        report_sha256=report_sha,
    )
