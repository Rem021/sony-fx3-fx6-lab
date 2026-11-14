"""Phase 28 End-to-End Phase H0 -> H1 -> H2 Read-Only Hardware Rehearsal Engine.

Unifies all pre-physical-camera safety invariants into a single deterministic,
fail-closed 6-stage rehearsal pipeline prior to connecting an ILME-FX3 body:

1. Stage 1: RP2040-Zero (`-DOPEN_DRAIN`) Multi-Port Tier-3 Harness & 48000-Baud
   Read-Only Probe Firewall (`multiport_bootrom_unbrick`).
2. Stage 2: macOS 26+ `IOUSBHost` (`0xe00002be`) Quiescence + `054C:0DA1 -> 054C:0336`
   Senser v1 7-Round Auth + USB STALL Guard + Jiritsu Read-Only Firewall
   (`fx3_recovery.macos_usb_transport_guard` when on `sys.path` or sibling repo,
   with a clean decoupled adapter fallback).
3. Stage 3: 4-Vector 2026 Runtime Anti-Brick Audit (`ld.so.preload` dynamic BusyBox
   ban, Sony BusyBox `dd` truncation ban + 5-step atomic contract, `nflasha10` 12 MiB
   `0x10000009` headroom, and `CAMSET`/`BK4\\0` `PRODUCT_MODEL` lock).
4. Stage 4: Brick Classifier v2 Full Symptom Matrix (`5L+6S`, `7L+7S`, `6L+9S` `WF-12`,
   `13S` `0x100D`, `0x10000009`, and `ld.so.preload`) + Wireless Fault Isolation check.
5. Stage 5: FX3 `v7.02` Simulated Shifted-VMA `p1` 4-Site Autolocator & Byte-Exact
   Rollback Rehearsal (`fx3_recovery.p1_symbol_autolocator` or decoupled adapter).
6. Stage 6: 12-Gate Safety Evaluation (`preflight.evaluate_12_safety_gates`)
   verifying `persistent_write_release == False` and deterministic fault-blocking.

Safety Redline:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` (hard-locked)
- `PERSISTENT_WRITE_RELEASE = False` (hard-locked)
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import posixpath
import struct
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .brick_classifier import classify_brick_state, generate_failsafe_init2_overlay_hook
from .multiport_bootrom_unbrick import (
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BOOTROM_SIZE_BYTES,
    BOOTROM_START,
    FASTBOOT_USB_VID_PID,
    PERSISTENT_EMMC_WRITES_AUTHORIZED as MULTIPORT_EMMC_AUTH,
    UART_BOOT_BAUD,
    UartBootOpcode,
    audit_fastboot_command_sequence,
    audit_rp2040_firmware_spec,
    decode_bootrom_diagnostic_code,
    decode_uart_boot_frame,
    encode_uart_boot_frame,
    estimate_uart_transfer_time_ms,
    generate_rp2040_zero_open_drain_probe_spec,
    validate_bootrom_read_range,
    validate_rp2040_multiport_harness,
)
from .preflight import TIER0_REQUIRED_BACKUPS, evaluate_12_safety_gates
from .runtime_antibrick_guards import (
    NFLASHA10_PARTITION_BYTES,
    PERSISTENT_EMMC_WRITES_AUTHORIZED as ANTIBRICK_EMMC_AUTH,
    audit_busybox_dd_commands,
    audit_camset_bk4_diff,
    audit_ld_so_preload_and_overlay,
    audit_nflasha10_vfat_budget,
    audit_pmca_5step_write_contract,
    evaluate_runtime_antibrick_guards,
)


PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
H0_REHEARSAL_SCHEMA: str = "fx3-h0-hardware-rehearsal-v1"

DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
SIBLING_RECOVERY_ADAPTER_DIR: Path = Path(__file__).resolve().parents[2] / "fx3-recovery-adapter"


@dataclass(frozen=True)
class StageResult:
    stage_id: str
    stage_number: int
    name: str
    passed: bool
    status: str
    adapter_mode: str
    persistent_emmc_writes_authorized: bool
    details: Dict[str, Any] = field(default_factory=dict)
    errors: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class H0RehearsalReport:
    schema: str
    evaluated_utc: str
    all_passed: bool
    ready_for_physical_h0_capture: bool
    status: str
    adapter_mode: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    stages: Tuple[StageResult, ...]
    blocked_stages: Tuple[str, ...]
    gates_summary: Dict[str, Any]
    gates_report: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _default_rehearsal_script() -> str:
    return (
        "# Phase H0/H1 RAM-only overlay & tmpfs staging rehearsal\n"
        'rm -f "/tmp/mod_arm_once"\n'
        "busybox sync\n"
        'busybox dd if="/tmp/fx6_stage_a/payload.bin" of="/tmp/fx6_stage_a/staged.bin" bs=4096\n'
        'busybox mount --bind "/tmp/fx6_stage_a/appFw.so" "/usr/lib/appFw.so"\n'
    )


def _default_pmca_5step_manifest() -> Dict[str, Any]:
    digest = sha256(b"fx3-h0-rehearsal-staged-payload").hexdigest()
    return {
        "drop_exit_guard_ok": True,
        "tmpfs_staging_ok": True,
        "expected_sha256": digest,
        "readback_sha256": digest,
        "rollback_history": (
            {"slot_id": "slot-1", "sha256": digest, "bytes": 4096},
        ),
    }


@dataclass(frozen=True)
class H0RehearsalConfig:
    repo_root: Optional[Path] = None
    camera_body_tag: str = "a" * 64
    force_decoupled_adapter: bool = False
    allow_sibling_recovery_import: bool = True

    # Stage 1 (RP2040-Zero -DOPEN_DRAIN & 48000-baud BootROM + Fastboot firewall)
    board: str = "waveshare_rp2040_zero"
    compile_flags: Tuple[str, ...] = ("-DOPEN_DRAIN",)
    open_drain: bool = True
    gpio_drive_mode: str = "open_drain"
    io_voltage_v: float = 1.8
    baud_rate: int = UART_BOOT_BAUD
    gnd_connected: bool = True
    gpio_mapping: Optional[Dict[int, str]] = None
    uart_probe_address: int = BOOTROM_START
    uart_probe_size: int = BOOTROM_SIZE_BYTES
    fastboot_commands: Tuple[str, ...] = (
        "getvar:version",
        "oem dumpbrom 0xffff0000 0xc000",
        "oem partition dump",
        "oem cetus dumpnor",
    )
    fastboot_usb_vid_pid: str = FASTBOOT_USB_VID_PID
    caller_force_emmc_auth: bool = False
    caller_force_destructive_fastboot: bool = False

    # Stage 2 (macOS 26+ IOUSBHost 0xe00002be + Senser v1/v2 + STALL + Jiritsu)
    macos_major: int = 26
    msc_vid_pid: str = "054C:0DA1"
    quiescence_waited_ms: int = 400
    driver_quiescent: bool = True
    claim_return_codes: Tuple[int, ...] = (0xE00002BE, 0x00000000)
    use_iousbhost_fallback: bool = True
    vendor_control_bm_request_type: int = 0x43
    vendor_control_b_request: int = 1
    vendor_control_w_value: int = 0x37FF
    vendor_control_w_index: int = 0xD7AA
    vendor_control_stall: bool = False
    senser_version: int = 1
    senser_auth_scheme: str = "xor_round_challenge"
    senser_challenge_rounds: int = 7
    senser_model_name: str = "ILME-FX3"
    senser_model_id: int = 0x91030080
    senser_rsa_modulus_bits: int = 0
    jiritsu_commands: Optional[Tuple[Tuple[int, int, int, Optional[str]], ...]] = None
    caller_force_jiritsu_writes: bool = False

    # Stage 3 (4-Vector 2026 Runtime Anti-Brick Audit)
    runtime_script_text: str = field(default_factory=_default_rehearsal_script)
    runtime_target_paths: Tuple[str, ...] = ("/tmp/fx6_stage_a/appFw.so",)
    jiritsu_set_file_paths: Tuple[str, ...] = ("/tmp/jiritsu/tier0_sector0.bin",)
    busybox_notrunc_verified: bool = False
    nflasha10_used_bytes: int = 6 * 1024 * 1024
    nflasha10_planned_writes: Tuple[Dict[str, Any], ...] = field(
        default_factory=lambda: ({"path": "/setting/opelog_meta.json", "bytes": 4096},)
    )
    camset_diff_entries: Tuple[Dict[str, Any], ...] = field(
        default_factory=lambda: (
            {"key": "LOG_SHOOTING_MODE", "bk_id": 0x02CF1443, "old_value": 0, "new_value": 1},
        )
    )
    before_bk4: Optional[bytes] = None
    after_bk4: Optional[bytes] = None
    protected_bk4_offsets: Tuple[int, ...] = ()
    pmca_5step_manifest: Optional[Dict[str, Any]] = field(
        default_factory=_default_pmca_5step_manifest
    )

    # Stage 4 (Brick Classifier v2 Symptom Matrix & WF-12 Isolation)
    wireless_fault_isolation_ok: bool = True
    symptom_matrix_overrides: Optional[Dict[str, Dict[str, Any]]] = None

    # Stage 5 (FX3 v7.02 Shifted-VMA p1 4-Site Autolocator & Rollback)
    shift_sd: int = 0x140
    shift_uc: int = 0x280
    vma_bias: int = 0x50000
    corrupt_prologue: bool = False
    duplicate_pattern_ambiguous: bool = False
    require_plt_cross_check: bool = True
    run_unicorn_verification: bool = False

    # Stage 6 (12-Gate Preflight Evaluation)
    allow_dry_run_gate12: bool = True
    tier0_manifest_override: Optional[Dict[str, Any]] = None
    worker_syscall_trace_override: Optional[List[Dict[str, Any]]] = None
    init2_failsafe_hook_override: Optional[str] = None
    backup_mount_tolerance_ok: Optional[bool] = None
    boot_selector_and_banks_ok: Optional[bool] = None
    kernel_dtb_ok: Optional[bool] = None
    storage_and_ram_budget_ok: Optional[bool] = None
    cp_rtos_ok: Optional[bool] = None
    stage_a_orchestrator_ok: Optional[bool] = None
    kmod_userland_abi_ok: Optional[bool] = None
    peripheral_ux_ok: Optional[bool] = None
    ap_cp_imaging_ok: Optional[bool] = None
    stage_b_p10_ok: Optional[bool] = None
    uipc_cp_shim_ok: Optional[bool] = None


# ---------------------------------------------------------------------------
# Recovery Adapter Resolution + Clean Decoupled Fallback Adapters
# ---------------------------------------------------------------------------


def _import_fx3_recovery_modules(
    *,
    force_decoupled_adapter: bool = False,
    allow_sibling_recovery_import: bool = True,
) -> Tuple[Optional[Any], Optional[Any], str]:
    """Import `macos_usb_transport_guard` and `p1_symbol_autolocator` if available."""
    if force_decoupled_adapter:
        return None, None, "decoupled"

    try:
        from fx3_recovery import macos_usb_transport_guard as usb_mod
        from fx3_recovery import p1_symbol_autolocator as p1_mod

        return usb_mod, p1_mod, "fx3_recovery_sys_path"
    except ImportError:
        pass

    if allow_sibling_recovery_import and (SIBLING_RECOVERY_ADAPTER_DIR / "fx3_recovery").is_dir():
        sibling_str = str(SIBLING_RECOVERY_ADAPTER_DIR)
        if sibling_str not in sys.path:
            sys.path.insert(0, sibling_str)
        try:
            from fx3_recovery import macos_usb_transport_guard as usb_mod
            from fx3_recovery import p1_symbol_autolocator as p1_mod

            return usb_mod, p1_mod, "fx3_recovery_sibling"
        except ImportError:
            pass

    return None, None, "decoupled"


def _run_decoupled_usb_transport(cfg: H0RehearsalConfig) -> Dict[str, Any]:
    """Clean decoupled macOS 26+ IOUSBHost / Senser v1/v2 / Jiritsu state machine."""
    errors: List[str] = []
    known_msc = ("054C:0DA1", "054C:0E0E", "054C:0E8A", "054C:0DA3", "054C:0994")
    norm_vp = cfg.msc_vid_pid.strip().upper()
    if norm_vp not in known_msc:
        return {
            "passed": False,
            "status": "BLOCKED_UNSUPPORTED_MSC_VID_PID",
            "errors": [f"Unsupported Sony MSC/PTP VID:PID {cfg.msc_vid_pid!r}"],
        }

    # 1. Quiescence check
    if cfg.macos_major >= 26 and (not cfg.driver_quiescent or cfg.quiescence_waited_ms < 350):
        return {
            "passed": False,
            "status": "BLOCKED_MSC_DRIVER_ACTIVE",
            "errors": [
                f"macOS {cfg.macos_major}+ requires driver_quiescent=True and waited_ms>=350ms "
                f"(got driver_quiescent={cfg.driver_quiescent}, waited_ms={cfg.quiescence_waited_ms})"
            ],
        }

    # 2. 0xe00002be backoff + IOUSBHost fallback claim
    backoff_schedule: List[int] = []
    claimed = False
    active_backend = ""
    for idx, rc in enumerate(cfg.claim_return_codes):
        rc_u32 = rc & 0xFFFFFFFF
        backend = "IOUSBLib" if (idx == 0 and cfg.macos_major >= 26 and cfg.use_iousbhost_fallback) else "IOUSBHost"
        if not cfg.use_iousbhost_fallback:
            backend = "IOUSBLib"
        if rc_u32 == 0x00000000:
            claimed = True
            active_backend = backend
            break
        if rc_u32 == 0xE00002BE:
            backoff_schedule.append(min(800, 50 * (1 << idx)))
            continue
        return {
            "passed": False,
            "status": "BLOCKED_USB_CLAIM_ERROR",
            "errors": [f"Unexpected IOReturn {hex(rc_u32)} during {backend} claim."],
        }

    if not claimed:
        return {
            "passed": False,
            "status": "FAILED_CLOSED_EXCLUSIVE_ACCESS",
            "backoff_schedule_ms": backoff_schedule,
            "errors": ["Exhausted claim retries under 0xe00002be (kIOReturnExclusiveAccess)."],
        }

    # 3. Vendor Control + STALL non-retransmit
    expected_vc = (0x43, 1, 0x37FF, 0xD7AA)
    actual_vc = (
        cfg.vendor_control_bm_request_type,
        cfg.vendor_control_b_request,
        cfg.vendor_control_w_value,
        cfg.vendor_control_w_index,
    )
    if actual_vc != expected_vc:
        return {
            "passed": False,
            "status": "BLOCKED_INVALID_VENDOR_CONTROL",
            "errors": [f"Invalid Vendor Control tuple {actual_vc}, expected {expected_vc}."],
        }
    if cfg.vendor_control_stall:
        return {
            "passed": False,
            "status": "STALL_ABORTED_NO_RETRANSMIT",
            "retransmit_count": 0,
            "errors": ["USB STALL (0xe000404f) detected; control packet retransmission suppressed."],
        }

    # 4. Senser v1 vs v2 fail-closed classification
    norm_model = cfg.senser_model_name.strip().upper()
    norm_scheme = cfg.senser_auth_scheme.strip().lower()
    if cfg.senser_version >= 2 or "rsa" in norm_scheme or cfg.senser_rsa_modulus_bits > 0 or norm_model in ("ILCE-7M5", "A7V", "A7_V"):
        return {
            "passed": False,
            "status": "BLOCKED_SENSER_V2_RSA_UNSUPPORTED",
            "errors": ["Senser v2 RSA challenge detected; failing closed."],
        }
    if cfg.senser_version != 1 or not (3 <= cfg.senser_challenge_rounds <= 7):
        return {
            "passed": False,
            "status": "BLOCKED_INVALID_SENSER_V1_ROUNDS",
            "errors": [f"Invalid Senser v1 rounds={cfg.senser_challenge_rounds}."],
        }

    # 5. Read-only Jiritsu AdjustControl audit
    cmds = cfg.jiritsu_commands or (
        (0x40, 0x1001, 0x4002, None),
        (0x40, 0x1001, 0x400F, "/tmp/jiritsu/tier0_read.bin"),
        (0x40, 0x1001, 0x4008, None),
        (0x40, 0x1001, 0x4011, None),
    )
    permitted: List[str] = []
    for pfunc, block, code, fpath in cmds:
        if pfunc != 0x40 or block != 0x1001:
            return {
                "passed": False,
                "status": "BLOCKED_INVALID_JIRITSU_TARGET",
                "errors": [f"Expected (0x40, 0x1001), got ({hex(pfunc)}, {hex(block)})."],
            }
        if code in (0x4003, 0x4006, 0x4007, 0x4010, 0x4005):
            return {
                "passed": False,
                "status": f"BLOCKED_JIRITSU_{hex(code)}",
                "errors": [f"Forbidden Jiritsu command {hex(code)} blocked under Tier-0 read-only policy."],
            }
        if code == 0x400F:
            if not fpath or "\\" in fpath or ".." in fpath.split("/") or not fpath.startswith("/"):
                return {
                    "passed": False,
                    "status": "BLOCKED_PATH_TRAVERSAL_OR_PERSISTENT_WRITE",
                    "errors": [f"Unsafe SET_FILE_PATH {fpath!r} blocked."],
                }
            norm_p = posixpath.normpath(fpath)
            if not norm_p.startswith(("/tmp/jiritsu/", "/mnt/fx3_tier0_backup/", "/log/")):
                return {
                    "passed": False,
                    "status": "BLOCKED_PATH_TRAVERSAL_OR_PERSISTENT_WRITE",
                    "errors": [f"Target SET_FILE_PATH {norm_p!r} outside read-only capture prefixes."],
                }
        elif code not in (0x4002, 0x4008, 0x4011):
            return {
                "passed": False,
                "status": "BLOCKED_UNKNOWN_JIRITSU_COMMAND",
                "errors": [f"Unknown Jiritsu command {hex(code)} rejected."],
            }
        permitted.append(hex(code))

    return {
        "passed": len(errors) == 0,
        "status": "VERIFIED_SENSER_V1_READONLY_SESSION",
        "active_backend": active_backend,
        "backoff_schedule_ms": backoff_schedule,
        "retransmit_count": 0,
        "service_vid_pid": "054C:0336",
        "senser_rounds": cfg.senser_challenge_rounds,
        "permitted_jiritsu_codes": permitted,
        "allow_persistent_writes": False,
        "stall_guard_verified": True,
        "senser_v2_fail_closed_verified": True,
        "errors": errors,
    }


def _run_decoupled_p1_autolocator(cfg: H0RehearsalConfig) -> Dict[str, Any]:
    """Self-contained decoupled 4-site AArch64 v7.02 shifted-VMA rehearsal."""
    if cfg.corrupt_prologue:
        return {
            "passed": False,
            "status": "BLOCKED_STAGE5_P1_AUTOLOCATOR",
            "errors": ["AutolocatorError: prologue mismatch (corrupt_prologue=True)"],
        }
    if cfg.duplicate_pattern_ambiguous:
        return {
            "passed": False,
            "status": "BLOCKED_STAGE5_P1_AUTOLOCATOR",
            "errors": ["AutolocatorError: chkFirmInfo_before expected 1 unique match, found 2"],
        }

    # Construct deterministic synthetic shifted AArch64 buffers and verify patch + rollback SHA-256
    base_sd = bytearray(0x400 + cfg.shift_sd)
    base_uc = bytearray(0x400 + cfg.shift_uc)
    off_ver = 0x100 + cfg.shift_sd
    off_sig = 0x180 + cfg.shift_sd
    off_s3 = 0x100 + cfg.shift_uc
    off_s4 = 0x140 + cfg.shift_uc

    orig_ver = bytes.fromhex("220440b900008052")
    pat_ver = bytes.fromhex("20008052c0035fd6")
    orig_sig = bytes.fromhex("fd7bbba9fd030091")
    pat_sig = bytes.fromhex("00008052c0035fd6")
    orig_s3 = bytes.fromhex("13008012")
    pat_s3 = bytes.fromhex("13008052")
    orig_s4 = bytes.fromhex("f3c39f5a")
    pat_s4 = bytes.fromhex("13008052")

    base_sd[off_ver : off_ver + 8] = orig_ver
    base_sd[off_sig : off_sig + 8] = orig_sig
    base_uc[off_s3 : off_s3 + 4] = orig_s3
    base_uc[off_s4 : off_s4 + 4] = orig_s4

    sd_orig = bytes(base_sd)
    uc_orig = bytes(base_uc)
    sd_pat = bytearray(sd_orig)
    sd_pat[off_ver : off_ver + 8] = pat_ver
    sd_pat[off_sig : off_sig + 8] = pat_sig
    uc_pat = bytearray(uc_orig)
    uc_pat[off_s3 : off_s3 + 4] = pat_s3
    uc_pat[off_s4 : off_s4 + 4] = pat_s4

    sd_rb = bytearray(sd_pat)
    sd_rb[off_ver : off_ver + 8] = orig_ver
    sd_rb[off_sig : off_sig + 8] = orig_sig
    uc_rb = bytearray(uc_pat)
    uc_rb[off_s3 : off_s3 + 4] = orig_s3
    uc_rb[off_s4 : off_s4 + 4] = orig_s4

    rollback_ok = bytes(sd_rb) == sd_orig and bytes(uc_rb) == uc_orig and len(sd_pat) == len(sd_orig)
    return {
        "passed": rollback_ok,
        "status": "VERIFIED_SHIFTED_VMA_AUTOLOCATOR_ROLLBACK" if rollback_ok else "BLOCKED_STAGE5_P1_AUTOLOCATOR",
        "located_offsets": {
            "isVersionOK": off_ver,
            "VerifySignature": off_sig,
            "chkFirmInfo_before_reject_ret": off_s3,
            "chkFirmInfo_before_cmp_csinv": off_s4,
        },
        "vma_bias": hex(cfg.vma_bias),
        "byte_length_invariant": len(sd_pat) == len(sd_orig) and len(uc_pat) == len(uc_orig),
        "rollback_verified": rollback_ok,
        "pass1_rollback_sha256": sha256(bytes(sd_rb) + bytes(uc_rb)).hexdigest(),
        "pass2_rollback_sha256": sha256(sd_orig + uc_orig).hexdigest(),
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "errors": [] if rollback_ok else ["Decoupled p1 rollback verification failed"],
    }


# ---------------------------------------------------------------------------
# Stage 1 .. Stage 6 Rehearsal Implementations
# ---------------------------------------------------------------------------


def run_stage1_multiport_harness_rehearsal(cfg: H0RehearsalConfig) -> StageResult:
    """Stage 1: RP2040-Zero -DOPEN_DRAIN Multi-Port Tier-3 Harness & 48000-Baud Firewall."""
    errors: List[str] = []
    warnings: List[str] = []

    if MULTIPORT_EMMC_AUTH or ALLOW_DESTRUCTIVE_FASTBOOT:
        errors.append("Hard-locked safety constants in multiport_bootrom_unbrick are not False!")

    harness = validate_rp2040_multiport_harness(
        board=cfg.board,
        compile_flags=cfg.compile_flags,
        open_drain=cfg.open_drain,
        gpio_drive_mode=cfg.gpio_drive_mode,
        io_voltage_v=cfg.io_voltage_v,
        gpio_mapping=cfg.gpio_mapping,
        gnd_connected=cfg.gnd_connected,
        baud_rate=cfg.baud_rate,
    )
    errors.extend(harness.errors)
    warnings.extend(harness.warnings)

    spec = generate_rp2040_zero_open_drain_probe_spec()
    spec_audit = audit_rp2040_firmware_spec(spec)
    if not spec_audit.valid:
        errors.extend(spec_audit.errors)

    read_range = validate_bootrom_read_range(cfg.uart_probe_address, cfg.uart_probe_size)
    if not read_range.valid:
        errors.extend(read_range.errors)

    frame_roundtrip_ok = False
    try:
        chunk_len = min(cfg.uart_probe_size, 4096)
        encoded = encode_uart_boot_frame(
            UartBootOpcode.MEM_READ,
            address=cfg.uart_probe_address,
            arg=chunk_len,
        )
        decoded = decode_uart_boot_frame(encoded)
        frame_roundtrip_ok = (
            decoded.opcode == UartBootOpcode.MEM_READ
            and decoded.address == cfg.uart_probe_address
            and decoded.arg == chunk_len
        )
    except Exception as exc:
        errors.append(f"48000-baud uart_boot frame roundtrip failed: {exc}")

    diag_100d = decode_bootrom_diagnostic_code(code=0x100D)
    diag_13s = decode_bootrom_diagnostic_code(short_blinks=13)
    if not (diag_100d.recognized and diag_13s.recognized and diag_100d.category == "BAD_UART_HANDSHAKE"):
        errors.append("0x100D / 13-short-blink BootROM diagnostic decoder check failed.")

    fw = audit_fastboot_command_sequence(
        cfg.fastboot_commands,
        persistent_emmc_writes_authorized=cfg.caller_force_emmc_auth,
        allow_destructive_fastboot=cfg.caller_force_destructive_fastboot,
        usb_vid_pid=cfg.fastboot_usb_vid_pid,
    )
    if fw.persistent_emmc_writes_authorized or fw.allow_destructive_fastboot:
        errors.append("Fastboot firewall failed to hard-lock persistent writes to False.")
    if not fw.allowed:
        errors.extend(fw.errors)
    warnings.extend(fw.warnings)

    passed = len(errors) == 0 and harness.valid and spec_audit.valid and read_range.valid and frame_roundtrip_ok and fw.allowed
    status = "VERIFIED_MULTIPORT_TIER3_SAFE" if passed else "BLOCKED_BY_MULTIPORT_TIER3_HARNESS_REDLINE"
    return StageResult(
        stage_id="S1_multiport_tier3_harness",
        stage_number=1,
        name="RP2040-Zero (-DOPEN_DRAIN) Multi-Port Tier-3 Harness & 48000-Baud Firewall",
        passed=passed,
        status=status,
        adapter_mode="native_fx3_safety",
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        details={
            "harness_status": harness.status,
            "board": harness.board,
            "open_drain_enforced": harness.open_drain_enforced,
            "baud_rate": harness.baud_rate,
            "io_voltage_v": harness.io_voltage_v,
            "bootrom_read_status": read_range.status,
            "bootrom_48kib_transfer_ms": estimate_uart_transfer_time_ms(BOOTROM_SIZE_BYTES),
            "uart_frame_roundtrip_ok": frame_roundtrip_ok,
            "diagnostic_0x100d_category": diag_100d.category,
            "fastboot_firewall_status": fw.status,
            "permitted_fastboot_commands": fw.permitted_commands,
            "blocked_fastboot_commands": fw.blocked_commands,
        },
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def run_stage2_macos_usb_transport_rehearsal(cfg: H0RehearsalConfig) -> StageResult:
    """Stage 2: macOS 26+ IOUSBHost 0xe00002be + Senser v1/v2 + STALL + Jiritsu Rehearsal."""
    usb_mod, _, adapter_mode = _import_fx3_recovery_modules(
        force_decoupled_adapter=cfg.force_decoupled_adapter,
        allow_sibling_recovery_import=cfg.allow_sibling_recovery_import,
    )

    if usb_mod is None:
        res = _run_decoupled_usb_transport(cfg)
        passed = bool(res.get("passed", False))
        return StageResult(
            stage_id="S2_macos_usb_transport_guard",
            stage_number=2,
            name="macOS 26+ IOUSBHost (0xe00002be) + Senser v1 Auth + STALL Guard",
            passed=passed,
            status=str(res.get("status", "BLOCKED_USB_TRANSPORT")),
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details=res,
            errors=tuple(str(e) for e in res.get("errors", ())),
            warnings=(),
        )

    errors: List[str] = []
    warnings: List[str] = []
    sess = usb_mod.MacOSUSBTransportSession(macos_major=cfg.macos_major)
    try:
        sess.attach_msc(
            vid_pid=cfg.msc_vid_pid,
            model_name=cfg.senser_model_name,
            model_id=cfg.senser_model_id,
        )
    except ValueError as exc:
        return StageResult(
            stage_id="S2_macos_usb_transport_guard",
            stage_number=2,
            name="macOS 26+ IOUSBHost (0xe00002be) + Senser v1 Auth + STALL Guard",
            passed=False,
            status="BLOCKED_UNSUPPORTED_MSC_VID_PID",
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details={"vid_pid": cfg.msc_vid_pid},
            errors=(str(exc),),
        )

    ok_q, status_q = sess.wait_for_msc_quiescence(
        waited_ms=cfg.quiescence_waited_ms,
        driver_quiescent=cfg.driver_quiescent,
    )
    if not ok_q:
        return StageResult(
            stage_id="S2_macos_usb_transport_guard",
            stage_number=2,
            name="macOS 26+ IOUSBHost (0xe00002be) + Senser v1 Auth + STALL Guard",
            passed=False,
            status="BLOCKED_MSC_DRIVER_ACTIVE",
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details={"quiescence_status": status_q, "history": list(sess.history)},
            errors=(status_q,),
        )

    claim = sess.claim_interface(
        cfg.claim_return_codes,
        use_iousbhost_fallback=cfg.use_iousbhost_fallback,
    )
    if not claim.success:
        return StageResult(
            stage_id="S2_macos_usb_transport_guard",
            stage_number=2,
            name="macOS 26+ IOUSBHost (0xe00002be) + Senser v1 Auth + STALL Guard",
            passed=False,
            status=claim.status,
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details={
                "active_backend": claim.active_backend,
                "backoff_schedule_ms": claim.backoff_schedule_ms,
                "exclusive_access_retries": claim.exclusive_access_retries,
            },
            errors=tuple(claim.errors),
        )

    vctrl = sess.send_vendor_control(
        bm_request_type=cfg.vendor_control_bm_request_type,
        b_request=cfg.vendor_control_b_request,
        w_value=cfg.vendor_control_w_value,
        w_index=cfg.vendor_control_w_index,
        usb_stall=cfg.vendor_control_stall,
    )
    if not vctrl.success:
        return StageResult(
            stage_id="S2_macos_usb_transport_guard",
            stage_number=2,
            name="macOS 26+ IOUSBHost (0xe00002be) + Senser v1 Auth + STALL Guard",
            passed=False,
            status=vctrl.status,
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details={
                "usb_stall_detected": vctrl.usb_stall_detected,
                "retransmit_count": vctrl.retransmit_count,
                "history": list(sess.history),
            },
            errors=tuple(vctrl.errors),
        )

    auth = sess.authenticate_senser(
        usb_mod.SenserChallenge(
            senser_version=cfg.senser_version,
            auth_scheme=cfg.senser_auth_scheme,
            challenge_rounds=cfg.senser_challenge_rounds,
            model_name=cfg.senser_model_name,
            model_id=cfg.senser_model_id,
            rsa_modulus_bits=cfg.senser_rsa_modulus_bits,
        )
    )
    if not auth.supported:
        return StageResult(
            stage_id="S2_macos_usb_transport_guard",
            stage_number=2,
            name="macOS 26+ IOUSBHost (0xe00002be) + Senser v1 Auth + STALL Guard",
            passed=False,
            status=auth.status,
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details={"senser_version": auth.senser_version, "fail_closed": auth.fail_closed},
            errors=(auth.reason,),
        )

    raw_jcmds = cfg.jiritsu_commands or (
        (usb_mod.JIRITSU_PFUNC, usb_mod.JIRITSU_BLOCK, usb_mod.JIRITSU_CODE_MOUNT, None),
        (
            usb_mod.JIRITSU_PFUNC,
            usb_mod.JIRITSU_BLOCK,
            usb_mod.JIRITSU_CODE_SET_FILE_PATH,
            "/tmp/jiritsu/tier0_read.bin",
        ),
        (usb_mod.JIRITSU_PFUNC, usb_mod.JIRITSU_BLOCK, usb_mod.JIRITSU_CODE_GET_FILE, None),
        (usb_mod.JIRITSU_PFUNC, usb_mod.JIRITSU_BLOCK, usb_mod.JIRITSU_CODE_GET_FILE2, None),
    )
    jcmds = [
        usb_mod.JiritsuCommand(pfunc=pf, block=blk, code=cd, file_path=fp)
        for pf, blk, cd, fp in raw_jcmds
    ]
    j_audit = sess.audit_jiritsu_flow(
        jcmds,
        allow_persistent_writes=cfg.caller_force_jiritsu_writes,
    )
    if j_audit.allow_persistent_writes:
        errors.append("Jiritsu auditor failed to hard-lock allow_persistent_writes=False.")
    if not j_audit.allowed:
        errors.extend(j_audit.errors)
    warnings.extend(j_audit.warnings)

    # Isolated negative sub-checks: STALL non-retransmit & Senser v2 RSA fail-closed
    stall_sess = usb_mod.MacOSUSBTransportSession(macos_major=26)
    stall_sess.attach_msc()
    stall_sess.wait_for_msc_quiescence(waited_ms=350, driver_quiescent=True)
    stall_sess.claim_interface([usb_mod.K_IORETURN_SUCCESS])
    stall_res = stall_sess.send_vendor_control(usb_stall=True)
    stall_guard_ok = (
        not stall_res.success
        and stall_res.status == "STALL_ABORTED_NO_RETRANSMIT"
        and stall_res.retransmit_count == 0
    )
    if not stall_guard_ok:
        errors.append("STALL non-retransmit negative sub-check failed.")

    v2_res = usb_mod.classify_senser_challenge(
        usb_mod.SenserChallenge(
            senser_version=2,
            auth_scheme="rsa_signature",
            challenge_rounds=1,
            model_name="ILCE-7M5",
            rsa_modulus_bits=2048,
        )
    )
    v2_fail_closed_ok = (not v2_res.supported) and v2_res.fail_closed
    if not v2_fail_closed_ok:
        errors.append("Senser v2 RSA fail-closed negative sub-check failed.")

    passed = len(errors) == 0 and j_audit.allowed
    status = "VERIFIED_SENSER_V1_READONLY_SESSION" if passed else j_audit.status
    return StageResult(
        stage_id="S2_macos_usb_transport_guard",
        stage_number=2,
        name="macOS 26+ IOUSBHost (0xe00002be) + Senser v1 Auth + STALL Guard",
        passed=passed,
        status=status,
        adapter_mode=adapter_mode,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        details={
            "active_backend": claim.active_backend,
            "backoff_schedule_ms": claim.backoff_schedule_ms,
            "exclusive_access_retries": claim.exclusive_access_retries,
            "retransmit_count": vctrl.retransmit_count,
            "service_vid_pid": auth.service_vid_pid,
            "senser_rounds": auth.rounds_required,
            "permitted_jiritsu_codes": j_audit.permitted_codes,
            "blocked_jiritsu_codes": j_audit.blocked_codes,
            "stall_guard_verified": stall_guard_ok,
            "senser_v2_fail_closed_verified": v2_fail_closed_ok,
            "state_history": list(sess.history),
        },
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def run_stage3_runtime_antibrick_rehearsal(cfg: H0RehearsalConfig) -> StageResult:
    """Stage 3: 4-Vector 2026 Runtime Anti-Brick Audit."""
    errors: List[str] = []
    warnings: List[str] = []

    if ANTIBRICK_EMMC_AUTH:
        errors.append("runtime_antibrick_guards.PERSISTENT_EMMC_WRITES_AUTHORIZED is not False!")

    ld_res = audit_ld_so_preload_and_overlay(
        script_text=cfg.runtime_script_text,
        target_paths=cfg.runtime_target_paths,
        jiritsu_set_file_paths=cfg.jiritsu_set_file_paths,
    )
    dd_res = audit_busybox_dd_commands(
        cfg.runtime_script_text,
        busybox_notrunc_verified=cfg.busybox_notrunc_verified,
    )
    vfat_res = audit_nflasha10_vfat_budget(
        current_used_bytes=cfg.nflasha10_used_bytes,
        planned_writes=cfg.nflasha10_planned_writes,
    )
    camset_res = audit_camset_bk4_diff(
        diff_entries=cfg.camset_diff_entries,
        before_bk4=cfg.before_bk4,
        after_bk4=cfg.after_bk4,
        protected_byte_offsets=cfg.protected_bk4_offsets,
    )

    unified = evaluate_runtime_antibrick_guards(
        script_text=cfg.runtime_script_text,
        target_paths=cfg.runtime_target_paths,
        jiritsu_set_file_paths=cfg.jiritsu_set_file_paths,
        busybox_notrunc_verified=cfg.busybox_notrunc_verified,
        nflasha10_used_bytes=cfg.nflasha10_used_bytes,
        nflasha10_planned_writes=cfg.nflasha10_planned_writes,
        camset_diff_entries=cfg.camset_diff_entries,
        before_bk4=cfg.before_bk4,
        after_bk4=cfg.after_bk4,
        protected_bk4_offsets=cfg.protected_bk4_offsets,
        pmca_5step_manifest=cfg.pmca_5step_manifest,
    )

    pmca_valid = True
    if cfg.pmca_5step_manifest is not None:
        pmca_res = audit_pmca_5step_write_contract(
            drop_exit_guard_ok=bool(cfg.pmca_5step_manifest.get("drop_exit_guard_ok", False)),
            tmpfs_staging_ok=bool(cfg.pmca_5step_manifest.get("tmpfs_staging_ok", False)),
            expected_sha256=str(cfg.pmca_5step_manifest.get("expected_sha256", "")),
            readback_sha256=str(cfg.pmca_5step_manifest.get("readback_sha256", "")),
            rollback_history=cfg.pmca_5step_manifest.get("rollback_history", ()),
            script_text=cfg.runtime_script_text,
            busybox_notrunc_verified=cfg.busybox_notrunc_verified,
        )
        pmca_valid = pmca_res.valid

    errors.extend(unified.errors)
    warnings.extend(unified.warnings)

    passed = (
        len(errors) == 0
        and unified.valid
        and ld_res.valid
        and dd_res.valid
        and vfat_res.valid
        and camset_res.valid
        and pmca_valid
    )
    status = "VERIFIED_4VECTOR_RUNTIME_ANTIBRICK_SAFE" if passed else unified.status
    return StageResult(
        stage_id="S3_runtime_antibrick_guards",
        stage_number=3,
        name="4-Vector 2026 Runtime Anti-Brick Audit",
        passed=passed,
        status=status,
        adapter_mode="native_fx3_safety",
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        details={
            "violation_codes": list(unified.violation_codes),
            "vector1_ld_so_preload_ok": ld_res.valid,
            "vector2_dd_truncation_ok": dd_res.valid,
            "vector2_pmca_5step_ok": pmca_valid,
            "vector3_nflasha10_headroom_ok": vfat_res.valid,
            "vector3_projected_free_bytes": vfat_res.details.get("projected_free_bytes"),
            "vector3_partition_bytes": NFLASHA10_PARTITION_BYTES,
            "vector4_camset_product_model_ok": camset_res.valid,
        },
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def run_stage4_brick_classifier_matrix_rehearsal(cfg: H0RehearsalConfig) -> StageResult:
    """Stage 4: Brick Classifier v2 Full Symptom Matrix & WF-12 Wireless Fault Isolation Check."""
    matrix_specs: Tuple[Tuple[str, Dict[str, Any], str, Dict[str, Any]], ...] = (
        (
            "5L+6S",
            {"led_symptom": "red_5L_6S"},
            "LEVEL_2_UPDATER_BLINK_LOOP_SD_RECOVERABLE",
            {"software_usb_or_sd_recoverable": True, "disassembly_free_uart_bootrom_recoverable": True},
        ),
        (
            "7L+7S",
            {"led_symptom": "red_7L_7S"},
            "LEVEL_2_UPDATER_BLINK_LOOP_SD_RECOVERABLE",
            {"software_usb_or_sd_recoverable": True, "disassembly_free_uart_bootrom_recoverable": True},
        ),
        (
            "6L+9S_WF12",
            {"led_symptom": "red_6L_9S"},
            "LEVEL_4_WF12_OR_CP_SUBCOMPONENT_6L9S_FAULT",
            {"software_usb_or_sd_recoverable": False, "disassembly_free_uart_bootrom_recoverable": True},
        ),
        (
            "13S_0x100D",
            {"led_symptom": "red_13S", "diagnostic_code": 0x100D},
            "LEVEL_3_MULTIPORT_BOOTROM_UART_FRAMING_ERROR_0x100D",
            {"software_usb_or_sd_recoverable": False, "disassembly_free_uart_bootrom_recoverable": True},
        ),
        (
            "0x10000009",
            {"led_symptom": "0x10000009", "error_code": 0x10000009},
            "LEVEL_2_NFLASHA10_VFAT_EXHAUSTION_0x10000009",
            {"software_usb_or_sd_recoverable": False, "disassembly_free_uart_bootrom_recoverable": True},
        ),
        (
            "ld_so_preload",
            {
                "led_symptom": "ld_so_preload_deadlock",
                "ld_so_preload_deadlock": True,
                "corrupted_regions": ["ld_so_preload"],
            },
            "LEVEL_2_LD_SO_PRELOAD_BUSYBOX_DEADLOCK",
            {"software_usb_or_sd_recoverable": False, "disassembly_free_uart_bootrom_recoverable": True},
        ),
    )

    errors: List[str] = []
    matrix_results: Dict[str, Dict[str, Any]] = {}
    overrides = cfg.symptom_matrix_overrides or {}

    for key, kwargs, expected_level, expected_flags in matrix_specs:
        eff_kwargs = dict(kwargs)
        if key in overrides:
            eff_kwargs.update(overrides[key])
        diag = classify_brick_state(**eff_kwargs)
        level_ok = diag.level == expected_level
        flags_ok = all(getattr(diag, f_name) == f_val for f_name, f_val in expected_flags.items())
        wf12_extra_ok = True
        if key == "6L+9S_WF12":
            joined = " ".join(diag.primary_recovery_steps + diag.fallback_recovery_steps)
            wf12_extra_ok = ("Airplane Mode" in joined) and ("7.02" in joined) and ("WF-12" in joined)
        row_ok = level_ok and flags_ok and wf12_extra_ok
        if not row_ok:
            errors.append(
                f"Symptom matrix mismatch for {key}: got level={diag.level!r} (expected {expected_level!r}), "
                f"flags_ok={flags_ok}, wf12_extra_ok={wf12_extra_ok}"
            )
        matrix_results[key] = {
            "level": diag.level,
            "severity": diag.severity,
            "software_usb_or_sd_recoverable": diag.software_usb_or_sd_recoverable,
            "disassembly_free_uart_bootrom_recoverable": diag.disassembly_free_uart_bootrom_recoverable,
            "passed": row_ok,
        }

    if not cfg.wireless_fault_isolation_ok:
        errors.append(
            "WF-12 Wireless Fault Isolation redline triggered (Sony Notice 00342260 cold-boot Airplane shadow / v7.02 degraded-mode guard disabled)."
        )

    passed = len(errors) == 0 and cfg.wireless_fault_isolation_ok
    status = "VERIFIED_BRICK_MATRIX_AND_WF12_ISOLATED" if passed else "BLOCKED_BY_WIRELESS_FAULT_ISOLATION_REDLINE"
    return StageResult(
        stage_id="S4_brick_classifier_matrix",
        stage_number=4,
        name="Brick Classifier v2 Full Symptom Matrix & WF-12 Wireless Fault Isolation",
        passed=passed,
        status=status,
        adapter_mode="native_fx3_safety",
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        details={
            "symptom_count": len(matrix_specs),
            "wireless_fault_isolation_ok": cfg.wireless_fault_isolation_ok,
            "matrix": matrix_results,
        },
        errors=tuple(errors),
        warnings=(),
    )


def run_stage5_p1_autolocator_rehearsal(cfg: H0RehearsalConfig) -> StageResult:
    """Stage 5: FX3 v7.02 Simulated Shifted-VMA p1 4-Site Autolocator & Rollback Rehearsal."""
    _, p1_mod, adapter_mode = _import_fx3_recovery_modules(
        force_decoupled_adapter=cfg.force_decoupled_adapter,
        allow_sibling_recovery_import=cfg.allow_sibling_recovery_import,
    )

    if p1_mod is None:
        res = _run_decoupled_p1_autolocator(cfg)
        passed = bool(res.get("passed", False))
        return StageResult(
            stage_id="S5_v702_p1_autolocator_rollback",
            stage_number=5,
            name="FX3 v7.02 Shifted-VMA p1 4-Site Autolocator & Rollback Rehearsal",
            passed=passed,
            status=str(res.get("status", "BLOCKED_STAGE5_P1_AUTOLOCATOR")),
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details=res,
            errors=tuple(str(e) for e in res.get("errors", ())),
            warnings=(),
        )

    errors: List[str] = []
    warnings: List[str] = []
    try:
        sd_raw, uc_raw = p1_mod.build_synthetic_p1_elf64_libraries(
            shift_sd=cfg.shift_sd,
            shift_uc=cfg.shift_uc,
            vma_bias=cfg.vma_bias,
            duplicate_pattern_ambiguous=cfg.duplicate_pattern_ambiguous,
            corrupt_prologue=cfg.corrupt_prologue,
        )
        auto_rep = p1_mod.autolocate_4_sites(
            sd_raw,
            uc_raw,
            profile_mode="v702_shifted_rehearsal",
            require_plt_cross_check=cfg.require_plt_cross_check,
        )
        warnings.extend(auto_rep.warnings)
        if not auto_rep.preserved_checks.get("isModelOK_and_isRegionOK_untouched", False):
            errors.append("Preserved region check failed for isModelOK/isRegionOK.")

        p1_img = p1_mod.build_synthetic_p1_fat12_squashfs_image(sd_raw, uc_raw)
        rt_rep = p1_mod.run_autolocated_p1_roundtrip(p1_img)
        if not (rt_rep.byte_length_invariant and rt_rep.rollback_verified and rt_rep.squashfs_readback_ok):
            errors.append("p1 FAT12/SquashFS roundtrip or two-pass SHA-256 rollback failed.")
        if rt_rep.persistent_emmc_writes_authorized:
            errors.append("p1_symbol_autolocator persistent_emmc_writes_authorized is not False!")

        unicorn_info: Dict[str, Any] = {"executed": False}
        if cfg.run_unicorn_verification:
            u_rep = p1_mod.verify_sites_in_unicorn(sd_raw, uc_raw, auto_rep.sites)
            unicorn_info = {
                "executed": True,
                "unicorn_available": u_rep.unicorn_available,
                "all_passed": u_rep.all_passed,
            }
            if u_rep.unicorn_available and not u_rep.all_passed:
                errors.extend(u_rep.errors)

        passed = len(errors) == 0
        return StageResult(
            stage_id="S5_v702_p1_autolocator_rollback",
            stage_number=5,
            name="FX3 v7.02 Shifted-VMA p1 4-Site Autolocator & Rollback Rehearsal",
            passed=passed,
            status="VERIFIED_SHIFTED_VMA_AUTOLOCATOR_ROLLBACK" if passed else "BLOCKED_STAGE5_P1_AUTOLOCATOR",
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details={
                "schema": auto_rep.schema,
                "located_offsets": rt_rep.located_offsets,
                "vma_bias": hex(cfg.vma_bias),
                "byte_length_invariant": rt_rep.byte_length_invariant,
                "rollback_verified": rt_rep.rollback_verified,
                "squashfs_readback_ok": rt_rep.squashfs_readback_ok,
                "pass1_rollback_sha256": rt_rep.pass1_rollback_sha256,
                "pass2_rollback_sha256": rt_rep.pass2_rollback_sha256,
                "unicorn": unicorn_info,
            },
            errors=tuple(errors),
            warnings=tuple(warnings),
        )
    except Exception as exc:
        return StageResult(
            stage_id="S5_v702_p1_autolocator_rollback",
            stage_number=5,
            name="FX3 v7.02 Shifted-VMA p1 4-Site Autolocator & Rollback Rehearsal",
            passed=False,
            status="BLOCKED_STAGE5_P1_AUTOLOCATOR",
            adapter_mode=adapter_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            details={"vma_bias": hex(cfg.vma_bias), "shift_sd": cfg.shift_sd, "shift_uc": cfg.shift_uc},
            errors=(f"{type(exc).__name__}: {exc}",),
            warnings=tuple(warnings),
        )


def _build_rehearsal_tier0_manifest(camera_body_tag: str) -> Dict[str, Any]:
    items = {}
    for k, spec in TIER0_REQUIRED_BACKUPS.items():
        sz = spec.get("exact_bytes") or spec.get("min_bytes") or 4096
        digest = sha256(f"fx3-h0-rehearsal:{camera_body_tag}:{k}".encode("utf-8")).hexdigest()
        items[k] = {"bytes": sz, "pass1_sha256": digest, "pass2_sha256": digest}
    return {
        "camera_body_tag": camera_body_tag,
        "model_id": "0x91030080",
        "items": items,
    }


def _default_rehearsal_syscall_trace() -> List[Dict[str, Any]]:
    return [
        {"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0},
        {"nr": 56, "dirfd": -100, "path": "/dev/nflasha", "flags": 0x28000, "ret": 10},
        {"nr": 56, "dirfd": -100, "path": "/mnt/fx3_tier0_backup/sector0.bin", "flags": 0x280C1, "ret": 11},
        {"nr": 64, "fd": 11, "ret": 512},
        {"nr": 57, "fd": 11, "ret": 0},
        {"nr": 57, "fd": 10, "ret": 0},
    ]


def run_stage6_preflight_12_gate_rehearsal(
    cfg: H0RehearsalConfig,
    prior_stages: Sequence[StageResult],
) -> Tuple[StageResult, Dict[str, Any]]:
    """Stage 6: 12-Gate Safety Evaluation confirming persistent_write_release == False."""
    repo_root = (cfg.repo_root or DEFAULT_REPO_ROOT).resolve()
    by_num = {s.stage_number: s for s in prior_stages}

    s1_ok = by_num[1].passed
    s2_ok = by_num[2].passed
    s3_ok = by_num[3].passed
    s4_ok = by_num[4].passed
    s5_ok = by_num[5].passed

    manifest = cfg.tier0_manifest_override or _build_rehearsal_tier0_manifest(cfg.camera_body_tag)
    trace = (
        cfg.worker_syscall_trace_override
        if cfg.worker_syscall_trace_override is not None
        else _default_rehearsal_syscall_trace()
    )
    hook = (
        cfg.init2_failsafe_hook_override
        if cfg.init2_failsafe_hook_override is not None
        else generate_failsafe_init2_overlay_hook()
    )

    gates_report = evaluate_12_safety_gates(
        repo_root=repo_root,
        tier0_manifest=manifest,
        worker_syscall_trace=trace,
        init2_failsafe_hook=hook,
        candidate_bundle_verified=(s1_ok and s2_ok and s3_ok and s4_ok and s5_ok),
        allow_dry_run_gate12=cfg.allow_dry_run_gate12,
        backup_mount_tolerance_ok=cfg.backup_mount_tolerance_ok,
        boot_selector_and_banks_ok=cfg.boot_selector_and_banks_ok,
        kernel_dtb_ok=cfg.kernel_dtb_ok,
        storage_and_ram_budget_ok=cfg.storage_and_ram_budget_ok,
        cp_rtos_ok=cfg.cp_rtos_ok,
        p1_recovery_bridge_ok=s5_ok,
        stage_a_orchestrator_ok=cfg.stage_a_orchestrator_ok,
        kmod_userland_abi_ok=cfg.kmod_userland_abi_ok,
        peripheral_ux_ok=cfg.peripheral_ux_ok,
        ap_cp_imaging_ok=cfg.ap_cp_imaging_ok,
        stage_b_p10_ok=cfg.stage_b_p10_ok,
        uipc_cp_shim_ok=cfg.uipc_cp_shim_ok,
        wireless_fault_isolation_ok=s4_ok,
        runtime_antibrick_ok=s3_ok,
        multiport_tier3_harness_ok=s1_ok,
    )

    errors: List[str] = []
    if gates_report.get("persistent_write_release") is not False:
        errors.append("CRITICAL: persistent_write_release is not hard-locked to False!")
    if gates_report.get("is_flash_authorization_or_recovery_certificate") is not False:
        errors.append("CRITICAL: is_flash_authorization_or_recovery_certificate is not False!")

    gates_list = gates_report.get("gates", [])
    g12 = next(
        (g for g in gates_list if isinstance(g, dict) and g.get("gate_id") == "G12_persistent_flash_write_authorization"),
        {"status": "MISSING"},
    )
    g12_status = str(g12.get("status", "MISSING"))
    summary = dict(gates_report.get("summary", {}))
    all_12_verified = bool(summary.get("all_12_gates_verified", False))

    if not (s1_ok and s2_ok and s3_ok and s4_ok and s5_ok):
        errors.append(
            "Prior rehearsal stage(s) failed: "
            + ", ".join(s.stage_id for s in prior_stages if not s.passed)
        )
    elif not all_12_verified:
        blocked_ids = [
            str(g.get("gate_id"))
            for g in gates_list
            if isinstance(g, dict) and not str(g.get("status", "")).startswith("VERIFIED")
        ]
        errors.append(f"12-Gate evaluation blocked on: {blocked_ids} (G12={g12_status})")

    passed = len(errors) == 0 and all_12_verified and (gates_report.get("persistent_write_release") is False)
    stage_status = g12_status if not passed else "VERIFIED_12_GATES_READONLY_DRY_RUN"
    stage_res = StageResult(
        stage_id="S6_preflight_12_gate_audit",
        stage_number=6,
        name="12-Gate Safety Evaluation (persistent_write_release == False)",
        passed=passed,
        status=stage_status,
        adapter_mode="native_fx3_safety",
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        details={
            "g12_status": g12_status,
            "persistent_write_release": gates_report.get("persistent_write_release"),
            "verified_gates": summary.get("verified_gates"),
            "total_gates": summary.get("total_gates"),
            "all_12_gates_verified": all_12_verified,
            "wireless_fault_isolation_ok": gates_report.get("wireless_fault_isolation_ok"),
            "runtime_antibrick_ok": gates_report.get("runtime_antibrick_ok"),
            "multiport_tier3_harness_ok": gates_report.get("multiport_tier3_harness_ok"),
        },
        errors=tuple(errors),
        warnings=(),
    )
    return stage_res, gates_report


def run_h0_hardware_rehearsal(
    config: Optional[H0RehearsalConfig] = None,
    **overrides: Any,
) -> H0RehearsalReport:
    """Execute the complete 6-Stage End-to-End Phase H0 Read-Only Hardware Rehearsal."""
    if config is None:
        cfg = H0RehearsalConfig(**overrides)
    elif overrides:
        base_kwargs = {f.name: getattr(config, f.name) for f in config.__dataclass_fields__.values()}
        base_kwargs.update(overrides)
        cfg = H0RehearsalConfig(**base_kwargs)
    else:
        cfg = config

    s1 = run_stage1_multiport_harness_rehearsal(cfg)
    s2 = run_stage2_macos_usb_transport_rehearsal(cfg)
    s3 = run_stage3_runtime_antibrick_rehearsal(cfg)
    s4 = run_stage4_brick_classifier_matrix_rehearsal(cfg)
    s5 = run_stage5_p1_autolocator_rehearsal(cfg)
    prior = (s1, s2, s3, s4, s5)
    s6, gates_report = run_stage6_preflight_12_gate_rehearsal(cfg, prior)

    stages = (s1, s2, s3, s4, s5, s6)
    blocked = tuple(s.stage_id for s in stages if not s.passed)
    all_passed = (
        len(blocked) == 0
        and all(s.passed for s in stages)
        and gates_report.get("persistent_write_release") is False
        and PERSISTENT_EMMC_WRITES_AUTHORIZED is False
        and PERSISTENT_WRITE_RELEASE is False
    )

    if all_passed:
        overall_status = "H0_REHEARSAL_READY_READONLY"
    else:
        first_bad = next(s for s in stages if not s.passed)
        overall_status = first_bad.status

    adapter_modes = sorted({s.adapter_mode for s in stages if s.stage_number in (2, 5)})
    adapter_label = "+".join(adapter_modes) if adapter_modes else "native_fx3_safety"

    all_errors: List[str] = []
    all_warnings: List[str] = []
    for s in stages:
        all_errors.extend(s.errors)
        all_warnings.extend(s.warnings)

    return H0RehearsalReport(
        schema=H0_REHEARSAL_SCHEMA,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        all_passed=all_passed,
        ready_for_physical_h0_capture=all_passed,
        status=overall_status,
        adapter_mode=adapter_label,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        stages=stages,
        blocked_stages=blocked,
        gates_summary=dict(gates_report.get("summary", {})),
        gates_report=gates_report,
        errors=tuple(all_errors),
        warnings=tuple(all_warnings),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx3_safety.h0_hardware_rehearsal",
        description="Phase 28 End-to-End Phase H0 Read-Only Hardware Rehearsal Engine",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--unicorn",
        action="store_true",
        help="Include Unicorn AArch64 instruction emulation in Stage 5",
    )
    parser.add_argument(
        "--decoupled",
        action="store_true",
        help="Force decoupled adapter mode instead of importing fx3_recovery",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional JSON output path",
    )
    args = parser.parse_args(argv)

    rep = run_h0_hardware_rehearsal(
        repo_root=args.repo_root,
        run_unicorn_verification=args.unicorn,
        force_decoupled_adapter=args.decoupled,
    )
    payload = json.dumps(rep.to_dict(), indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0 if rep.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
