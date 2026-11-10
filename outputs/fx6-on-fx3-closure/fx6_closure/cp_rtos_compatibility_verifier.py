"""Phase 10 Blueprint `U2` Closure: CP RTOS (`cpapp-b.bin`) & `nflasha8` (`tomco.txt`) Compatibility Verifier.

Closes Blueprint Unknown `U2` ("FX6 `cpapp-b.bin` CP RTOS peripheral compatibility on FX3 hardware")
using strictly read-only clean donor artifacts:
1. Parses and cross-compares FX3 runtime `tomco.txt` (`dmm-backup-20261029/tomco.txt`), FX3 updater
   `tomco.txt` (`package-20261028/updaterfs/cp/tomco.txt`), and FX6 `nflasha8/tomco.txt`, proving
   100% identity across all 4 uncached shared-memory `memcfg=` pools (`1,724.00 MiB` total, 0 overlap)
   and all 20 CP<->MP IPC interrupt / exception / telemetry keys while pinpointing exact board GPIO
   reset (`xreset_req_port_ch=0:22`), `exception_reboot=Y`, and watchdog (`wdt_on`) differences.
2. Audits all 9 FX6 `nflasha8` (`/cp`) partition artifacts (`cpapp-b.bin`, `tomco.txt`, `DmmCfg.bin`,
   `MIS.bin`, `DGU.bin`, `pcie_phy_fw.bin`, `SysSound.bin`, `OldAmtCL.bin`, `loader_spi.bin`),
   FX3 reference metadata (`cp-av-analysis/mapping.json` & `DmmCfg.bin`), and the ARM32 flat-binary
   startup header at file offset `0x00` (`ldr r1, [pc, #4]; add r1, r1, #4; mov pc, r1` with literal
   `0x0010800c` -> self-referential load base `0x00108000`, matching `0xfa0080` Bank 1 `0x0800108000`
   and Octal-SPI NOR Sector `4096`).
3. Scans FX6 `cpapp-b.bin` read-only for pinned hardware peripheral driver markers (`Darwin` /
   `VariableNd` electronic variable ND controller, `Mew` SDI/Genlock FPGA chip-ID verifier, `FAN_R` /
   `SetFanEqId` thermal control, `vgrip` / `panel_sio`, `TOPPERS-FMP 1.4.0`, and `osal_uipc` /
   `DmmWrapper` / `Backup` bridges).
4. Proves and enforces the **Stage-A Stock-CP Redline (`p8_cp_mutation_forbidden = True`,
   `cp_mutation_bytes = 0`)**: proves why flashing FX6 `cpapp-b.bin` onto FX3 hardware is both
   unsafe (FX6-only `Darwin` ND + `Mew` FPGA self-checks + `+0xE0000`/`+0x14000` Bank 1 calibration
   shifts) and unnecessary (100% shared `memcfg=`/IPC transport + AP-side `P1..P9 + Fan` compatibility
   closure), and rejects any candidate manifest or overlay script attempting to mutate `p8` / `/cp`.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .backup_mount_tolerance_verifier import (
    DEFAULT_FX6_TEMPLATE_BK4_PATH,
    read_bk4_property_bytes,
)
from .boot_selector_and_bank_verifier import (
    DEFAULT_FX3_BANK1_FA0080_PATH,
    _extract_two_bk4_records,
    parse_and_audit_fa0080_bank,
)


DEFAULT_FX6_NFLASHA8_DIR = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8"
)
DEFAULT_FX6_CP_AV_ANALYSIS_DIR = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "FX6-donor-assessment-20261103/team/donor/cp-av-analysis"
)
DEFAULT_FX3_RUNTIME_TOMCO_PATH = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "dmm-backup-20261029/tomco.txt"
)
DEFAULT_FX3_UPDATER_CP_DIR = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "package-20261028/updaterfs/cp"
)
DEFAULT_FX3_DMMCFG_PATH = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "dmm-config-20261029/original-files/DmmCfg.bin"
)
DEFAULT_FX3_PFORMAT_CONFIG_PATH = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
    "config-producer-20261029/original-files/pformat_config.txt"
)

# Canonical pinned sizes & SHA-256 digests for FX6 nflasha8 (/cp) artifacts
EXPECTED_FX6_NFLASHA8_ARTIFACTS: Dict[str, Tuple[int, str]] = {
    "cpapp-b.bin": (
        17_952_816,
        "60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668",
    ),
    "tomco.txt": (
        810,
        "36566d47fe61e9560f4ce7f1b579bc2404b330bb7940b54e462abcff9c360140",
    ),
    "DmmCfg.bin": (
        41_552,
        "1e71bb9dcf7bcafe8df52b07b4ecc03ef8001c79b8b25ea92a870f4c2f839bf8",
    ),
    "MIS.bin": (
        119_296,
        "4cd3e9bc3a0a4aec4793bff77e7ca4dccdba8637212cd632cdc5ecbe550daf98",
    ),
    "DGU.bin": (
        24_336,
        "39eeb6d572a060149194463507800ed66b866a20dceb8ed49b01a04eb6fb2ba7",
    ),
    "pcie_phy_fw.bin": (
        16_384,
        "963669fdc92d57141fa41095ecd7c5a1b972162d2e699a702ebfc8b6c1ef64dc",
    ),
    "SysSound.bin": (
        64_128,
        "a4386c47456df69df8b48157d489758c0ffedd29b266bf615c28bc621c32a356",
    ),
    "OldAmtCL.bin": (
        161_766,
        "40d17dbba34f0a31d281db4b487ece12b9d518838faa26afca5f7fdb83d3062e",
    ),
    "loader_spi.bin": (
        39_184,
        "314d372d0d2b9883c3b9dc04b40389edb3100e6d5ef529633cc427c3d0cab72e",
    ),
}

EXPECTED_FX3_CP_REF_BYTES = 15_980_568
EXPECTED_FX3_CP_REF_SHA256 = "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba"
EXPECTED_CP_IDENTICAL_PREFIX_BYTES = 0x20000  # 131,072 B

EXPECTED_FX3_RUNTIME_TOMCO_BYTES = 710
EXPECTED_FX3_RUNTIME_TOMCO_SHA256 = (
    "42f1785422bce152dbb21c4e82f42dd4b053a1729c7694e54b7cc9f118592722"
)
EXPECTED_FX3_UPDATER_TOMCO_BYTES = 618
EXPECTED_FX3_UPDATER_TOMCO_SHA256 = (
    "d9401e6a7d0cdd85803e2a6823fd9dac0ff186910d82a5671f32fc0a37fc21f1"
)
EXPECTED_FX3_UDTRCP_BYTES = 880_944
EXPECTED_FX3_UDTRCP_SHA256 = (
    "f512ee9abf1b94c40a655a1dc0cebff7ff181858016e2e298ef5c74adcf7e283"
)
EXPECTED_FX3_DMMCFG_BYTES = 43_320
EXPECTED_FX3_DMMCFG_SHA256 = (
    "820dc02b6a001636b93fff51d90baaced1ba75cf9bbaa90600dfc7fd7a705166"
)

CP_LOCAL_LOAD_BASE = 0x00108000
CP_FIRST_BRANCH_TARGET = 0x00108010
CP_BANK1_BUS_LOAD_ADDR = 0x0800108000
TOMCO_BANK1_BUS_LOAD_ADDR = 0x0800100000
TOMCO_BANK1_SPAN_BYTES = 0x00008000

# ARM32 little-endian startup sequence at file offset 0x00..0x18 of cpapp-b.bin:
#   0x00: e59f1004  ldr r1, [pc, #4]      ; loads 0x0010800c from offset 0x0c
#   0x04: e2811004  add r1, r1, #4        ; r1 = 0x00108010
#   0x08: e1a0f001  mov pc, r1            ; jump to 0x00108010
#   0x0c: 0010800c  .word 0x0010800c      ; self-referential literal proving base = 0x00108000
#   0x10: e3a000d3  mov r0, #0xd3         ; Supervisor mode, IRQ+FIQ masked
#   0x14: e12ff000  msr cpsr_fsxc, r0
EXPECTED_CP_ARM32_ENTRY_WORDS: Tuple[int, ...] = (
    0xE59F1004,
    0xE2811004,
    0xE1A0F001,
    0x0010800C,
    0xE3A000D3,
    0xE12FF000,
)

EXPECTED_RUNTIME_MEMCFG_SPEC: Tuple[Tuple[int, int, str], ...] = (
    (0x04C00000, 0x00400000, "uc"),
    (0x09000000, 0x07000000, "uc"),
    (0x1B800000, 0x24800000, "uc"),
    (0x80000000, 0x40000000, "uc"),
)

REQUIRED_IDENTICAL_IPC_AND_TELEMETRY_KEYS: Tuple[str, ...] = (
    "usrrtn_cfggrp",
    "cpmp_exception_port_ch",
    "cpmp_exception_port_bit",
    "mpcp_exception_int_no",
    "mpcp_exception_int_cfg",
    "xpoweroff_port_ch",
    "xpoweroff_port_bit",
    "reset_req_int_no",
    "tmon_cpu",
    "tmon_addr",
    "tmon_size",
    "boottime_addr",
    "boottime_size",
    "klog_addr",
    "klog_size",
    "atm_target_pri",
    "atm_mngtsk_cyc",
    "atm_load_rst_num",
    "console_enable",
    "uart_baudrate",
)

# Exact pinned hardware peripheral & IPC driver strings inside FX6 cpapp-b.bin
PINNED_FX6_CP_PERIPHERAL_MARKERS: Tuple[Tuple[str, int, str, bool, str], ...] = (
    # (category, file_offset, exact_ascii, fx6_hardware_exclusive, ap_mitigation_id)
    (
        "darwin_electronic_nd",
        0xE7F83A,
        "Darwin ACV Port changed",
        True,
        "P4 (appFw.so ND Clear lock + stock FX3 CP)",
    ),
    (
        "darwin_electronic_nd",
        0x1C8B24,
        "[EC] (S_PB and ND_CTRL_CMR_LINEAR) is unexpected.",
        True,
        "P4 (appFw.so ND Clear lock + stock FX3 CP)",
    ),
    (
        "darwin_electronic_nd",
        0x1F5708,
        "EC: notifyVariableNdFilter:ND=[%lu/%lu],Result=[%d]",
        True,
        "P4 (appFw.so ND Clear lock + stock FX3 CP)",
    ),
    (
        "darwin_electronic_nd",
        0x1FB76C,
        "CheckSetVariableNdRotaryEncoder",
        True,
        "P4 (appFw.so ND Clear lock + stock FX3 CP)",
    ),
    (
        "mew_sdi_genlock_fpga",
        0x118B04,
        "Mew [MONI_ERR] %s() FPGA Chip ID Error  = %x %x %x %x",
        True,
        "Stock FX3 CP + P5/P6 UIPC display/audio completion synthesis",
    ),
    (
        "mew_sdi_genlock_fpga",
        0x1188CC,
        "MoniFpga_StartStopSDI",
        True,
        "Stock FX3 CP (no SDI/Genlock Mew FPGA on FX3 mainboard)",
    ),
    (
        "mew_sdi_genlock_fpga",
        0x8F14C,
        "[GENLOCK]:stage_Genlock_Idle_Off_SendComp %x",
        True,
        "Stock FX3 CP (no Genlock BNC hardware on FX3 mainboard)",
    ),
    (
        "mew_sdi_genlock_fpga",
        0x3AAFF8,
        "kbd: select vgrip",
        True,
        "P3 (libInfraAppRemoteBoard.so prune + stock FX3 CP)",
    ),
    (
        "fan_thermal_control",
        0x5EBBC,
        "[ADF]PROC_MSG_SET_FAN_EQ_ID:%x %x",
        False,
        "Fan (libfan.so fan_i_bkup_is_valid -> 1 + stock FX3 CP thermal loop)",
    ),
    (
        "fan_thermal_control",
        0xE86C2A,
        "FAN_R",
        False,
        "Fan (libfan.so fan_i_bkup_is_valid -> 1 + stock FX3 CP thermal loop)",
    ),
    (
        "toppers_fmp_rtos",
        0x44BD2C,
        "TOPPERS>",
        False,
        "Shared TOPPERS-FMP 1.4.0 SMP RTOS kernel @ 0x00108000",
    ),
    (
        "uipc_dmm_backup_ipc",
        0xB6144,
        "[DmmWrapper]AllocNew: ERR_OSAL_UIPC! %d, 0x%x, 0x%x, %d",
        False,
        "Shared 4x memcfg= DMM/UIPC transport + P5/P6/P7 AP bridges",
    ),
    (
        "uipc_dmm_backup_ipc",
        0x203B04,
        "cam_im_senser_copy_bk2shadow",
        False,
        "Stock FX3 CP + FX3 Bank 1 IMX410 sensor calibration + P9 upm.ko guard",
    ),
)

FORBIDDEN_CP_MUTATION_TOKENS: Tuple[str, ...] = (
    "/dev/nflasha8",
    "/dev/cnflasha8",
    "/dev/pnflasha8",
    "cpapp-b.bin",
    "udtrcp.bin",
    "/cp/tomco.txt",
    "/cp/DmmCfg.bin",
    "/cp/OldAmtCL.bin",
    "0x00200000",  # Octal-SPI NOR cpapp-b.bin flash offset
)

_MEMCFG_RE = re.compile(r"^(0x[0-9a-fA-F]+)@(0x[0-9a-fA-F]+)(?::([A-Za-z0-9_]+))?$")


class TomcoFormatError(ValueError):
    """Raised when a `[TOMCO]` CP RTOS configuration file is malformed or contains overlapping pools."""


@dataclass(frozen=True)
class TomcoMemcfgRegion:
    index: int
    base_addr: int
    size_bytes: int
    end_excl: int
    cache_attr: str
    raw_spec: str


@dataclass(frozen=True)
class ParsedTomcoConfig:
    source_label: str
    byte_length: int
    sha256: str
    scalar_params: Dict[str, str]
    duplicate_consistent_keys: Tuple[str, ...]
    memcfg_regions: Tuple[TomcoMemcfgRegion, ...]
    total_memcfg_bytes: int
    memcfg_pairwise_non_overlapping: bool


@dataclass(frozen=True)
class TomcoCrossModelAudit:
    valid: bool
    fx3_runtime: ParsedTomcoConfig
    fx6_runtime: ParsedTomcoConfig
    fx3_updater: ParsedTomcoConfig
    runtime_memcfg_identical: bool
    shared_ipc_telemetry_keys_identical: bool
    identical_key_count: int
    differing_scalar_keys: Dict[str, Dict[str, Optional[str]]]
    fx3_only_keys: Tuple[str, ...]
    fx6_only_keys: Tuple[str, ...]
    updater_memcfg_delta_documented: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CpArtifactDigestRecord:
    name: str
    byte_size: int
    sha256: str
    expected_bytes: int
    expected_sha256: str
    matched: bool


@dataclass(frozen=True)
class CpArm32StartupAudit:
    valid: bool
    fx6_cp_bytes: int
    fx6_cp_sha256: str
    fx3_cp_ref_bytes: int
    fx3_cp_ref_sha256: str
    cp_size_delta_bytes: int
    identical_prefix_bytes: int
    entry_words_hex: Tuple[str, ...]
    self_ref_literal: str
    derived_load_base: str
    first_branch_target: str
    embedded_vector_pointers_in_range: bool
    bank1_tomco_addr_matched: bool
    bank1_cpapp_addr_matched: bool
    spi_nor_cpapp_offset_matched: bool
    fx3_dmmcfg_bytes: int
    fx6_dmmcfg_bytes: int
    dmmcfg_size_delta_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CpPeripheralMarkerHit:
    category: str
    file_offset_hex: str
    exact_ascii: str
    verified_at_pinned_offset: bool
    fx6_hardware_exclusive: bool
    ap_mitigation: str


@dataclass(frozen=True)
class CpPeripheralMarkerAudit:
    valid: bool
    total_pinned_markers: int
    verified_marker_count: int
    fx6_exclusive_hazard_count: int
    category_counts: Dict[str, int]
    markers: Tuple[CpPeripheralMarkerHit, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CandidateCpRedlineAudit:
    valid: bool
    p8_cp_mutation_forbidden: bool
    cp_mutation_bytes: int
    audited_overlay_paths: int
    audited_script_count: int
    violations: Tuple[str, ...]


@dataclass(frozen=True)
class Phase10CpRtosCompatibilityReport:
    all_checks_passed: bool
    u2_closed: bool
    p8_cp_mutation_forbidden: bool
    cp_mutation_bytes: int
    nflasha8_artifacts: Tuple[CpArtifactDigestRecord, ...]
    fx3_udtrcp_verified: bool
    tomco_audit: TomcoCrossModelAudit
    arm32_startup_audit: CpArm32StartupAudit
    peripheral_marker_audit: CpPeripheralMarkerAudit
    candidate_redline_audit: CandidateCpRedlineAudit


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_tomco_txt(raw_bytes: bytes, source_label: str = "tomco.txt") -> ParsedTomcoConfig:
    """Parse and validate a Sony `[TOMCO]` CP RTOS configuration blob."""
    try:
        text = raw_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise TomcoFormatError(f"{source_label}: non-ASCII bytes in tomco.txt") from exc

    non_empty = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(non_empty) < 3 or non_empty[0] != "[TOMCO]" or non_empty[-1] != "[TOMCO]":
        raise TomcoFormatError(
            f"{source_label}: must start and end with '[TOMCO]' sentinel lines"
        )

    scalars: Dict[str, str] = {}
    duplicates: List[str] = []
    regions: List[TomcoMemcfgRegion] = []

    for line_idx, line in enumerate(non_empty[1:-1], start=2):
        if line.startswith("#"):
            continue
        if "=" not in line:
            raise TomcoFormatError(f"{source_label}:{line_idx}: missing '=' in {line!r}")
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if not key or not val:
            raise TomcoFormatError(f"{source_label}:{line_idx}: empty key or value in {line!r}")

        if key == "memcfg":
            m = _MEMCFG_RE.match(val)
            if not m:
                raise TomcoFormatError(
                    f"{source_label}:{line_idx}: invalid memcfg syntax {val!r}"
                )
            size_bytes = int(m.group(1), 16)
            base_addr = int(m.group(2), 16)
            cache_attr = m.group(3) or "cached"
            if size_bytes <= 0 or (size_bytes & 0xFFF) != 0 or (base_addr & 0xFFF) != 0:
                raise TomcoFormatError(
                    f"{source_label}:{line_idx}: memcfg must be positive and 4 KiB-aligned: {val!r}"
                )
            regions.append(
                TomcoMemcfgRegion(
                    index=len(regions),
                    base_addr=base_addr,
                    size_bytes=size_bytes,
                    end_excl=base_addr + size_bytes,
                    cache_attr=cache_attr,
                    raw_spec=val,
                )
            )
        else:
            if key in scalars:
                if scalars[key] != val:
                    raise TomcoFormatError(
                        f"{source_label}:{line_idx}: conflicting duplicate key {key!r}: "
                        f"{scalars[key]!r} vs {val!r}"
                    )
                if key not in duplicates:
                    duplicates.append(key)
            else:
                scalars[key] = val

    if not regions:
        raise TomcoFormatError(f"{source_label}: zero memcfg= regions defined")

    sorted_regs = sorted(regions, key=lambda r: r.base_addr)
    for i in range(len(sorted_regs) - 1):
        cur = sorted_regs[i]
        nxt = sorted_regs[i + 1]
        if cur.end_excl > nxt.base_addr:
            raise TomcoFormatError(
                f"{source_label}: overlapping memcfg regions "
                f"[0x{cur.base_addr:x}, 0x{cur.end_excl:x}) and [0x{nxt.base_addr:x}, 0x{nxt.end_excl:x})"
            )

    return ParsedTomcoConfig(
        source_label=source_label,
        byte_length=len(raw_bytes),
        sha256=_sha256_bytes(raw_bytes),
        scalar_params=scalars,
        duplicate_consistent_keys=tuple(duplicates),
        memcfg_regions=tuple(regions),
        total_memcfg_bytes=sum(r.size_bytes for r in regions),
        memcfg_pairwise_non_overlapping=True,
    )


def compare_tomco_configs(
    fx3_runtime_bytes: bytes,
    fx6_runtime_bytes: bytes,
    fx3_updater_bytes: bytes,
) -> TomcoCrossModelAudit:
    """Compare FX3 runtime, FX6 runtime, and FX3 updater `tomco.txt` files."""
    errors: List[str] = []
    fx3_rt = parse_tomco_txt(fx3_runtime_bytes, source_label="fx3_runtime_tomco.txt")
    fx6_rt = parse_tomco_txt(fx6_runtime_bytes, source_label="fx6_nflasha8_tomco.txt")
    fx3_up = parse_tomco_txt(fx3_updater_bytes, source_label="fx3_updater_cp_tomco.txt")

    if fx3_rt.byte_length != EXPECTED_FX3_RUNTIME_TOMCO_BYTES or fx3_rt.sha256 != EXPECTED_FX3_RUNTIME_TOMCO_SHA256:
        errors.append(
            f"FX3 runtime tomco.txt digest/size mismatch: got {fx3_rt.byte_length} B / {fx3_rt.sha256}"
        )
    exp_fx6_tomco_len, exp_fx6_tomco_sha = EXPECTED_FX6_NFLASHA8_ARTIFACTS["tomco.txt"]
    if fx6_rt.byte_length != exp_fx6_tomco_len or fx6_rt.sha256 != exp_fx6_tomco_sha:
        errors.append(
            f"FX6 nflasha8/tomco.txt digest/size mismatch: got {fx6_rt.byte_length} B / {fx6_rt.sha256}"
        )
    if fx3_up.byte_length != EXPECTED_FX3_UPDATER_TOMCO_BYTES or fx3_up.sha256 != EXPECTED_FX3_UPDATER_TOMCO_SHA256:
        errors.append(
            f"FX3 updater tomco.txt digest/size mismatch: got {fx3_up.byte_length} B / {fx3_up.sha256}"
        )

    fx3_tuples = tuple((r.base_addr, r.size_bytes, r.cache_attr) for r in fx3_rt.memcfg_regions)
    fx6_tuples = tuple((r.base_addr, r.size_bytes, r.cache_attr) for r in fx6_rt.memcfg_regions)
    memcfg_identical = fx3_tuples == fx6_tuples == EXPECTED_RUNTIME_MEMCFG_SPEC
    if not memcfg_identical:
        errors.append(
            f"Runtime memcfg= mismatch between FX3 {fx3_tuples} and FX6 {fx6_tuples}"
        )

    ipc_keys_ok = True
    for key in REQUIRED_IDENTICAL_IPC_AND_TELEMETRY_KEYS:
        v3 = fx3_rt.scalar_params.get(key)
        v6 = fx6_rt.scalar_params.get(key)
        if v3 is None or v3 != v6:
            ipc_keys_ok = False
            errors.append(f"Required shared IPC/telemetry key {key!r} diverged: FX3={v3!r} vs FX6={v6!r}")

    all_keys = sorted(set(fx3_rt.scalar_params.keys()) | set(fx6_rt.scalar_params.keys()))
    identical_cnt = 0
    differing: Dict[str, Dict[str, Optional[str]]] = {}
    fx3_only: List[str] = []
    fx6_only: List[str] = []
    for k in all_keys:
        v3 = fx3_rt.scalar_params.get(k)
        v6 = fx6_rt.scalar_params.get(k)
        if v3 == v6:
            identical_cnt += 1
        else:
            differing[k] = {"fx3_runtime": v3, "fx6_runtime": v6}
            if v6 is None:
                fx3_only.append(k)
            elif v3 is None:
                fx6_only.append(k)

    # Confirm FX6-specific hardware reset & reboot flags
    if fx6_rt.scalar_params.get("exception_reboot") != "Y":
        errors.append("Expected FX6 tomco.txt exception_reboot=Y")
    if fx6_rt.scalar_params.get("xreset_req_port_ch") != "0" or fx6_rt.scalar_params.get("xreset_req_port_bit") != "22":
        errors.append("Expected FX6 tomco.txt xreset_req_port_ch=0 / xreset_req_port_bit=22")
    if fx3_rt.scalar_params.get("wdt_on") != "1" or fx6_rt.scalar_params.get("wdt_on") != "0":
        errors.append("Unexpected wdt_on polarity between FX3 runtime and FX6 runtime")

    updater_delta_ok = (
        len(fx3_up.memcfg_regions) == 3
        and fx3_up.scalar_params.get("tmon_addr") == "0x03300000"
        and fx3_up.scalar_params.get("exception_reboot") == "N"
    )
    if not updater_delta_ok:
        errors.append("FX3 updater tomco.txt profile did not match expected 3-region recovery layout")

    valid = memcfg_identical and ipc_keys_ok and updater_delta_ok and len(errors) == 0
    return TomcoCrossModelAudit(
        valid=valid,
        fx3_runtime=fx3_rt,
        fx6_runtime=fx6_rt,
        fx3_updater=fx3_up,
        runtime_memcfg_identical=memcfg_identical,
        shared_ipc_telemetry_keys_identical=ipc_keys_ok,
        identical_key_count=identical_cnt,
        differing_scalar_keys=differing,
        fx3_only_keys=tuple(fx3_only),
        fx6_only_keys=tuple(fx6_only),
        updater_memcfg_delta_documented=updater_delta_ok,
        errors=tuple(errors),
    )


def audit_cpapp_arm32_startup(
    fx6_cp_bytes: bytes,
    cp_av_mapping_json: Mapping[str, object],
    fx3_dmmcfg_bytes: bytes,
    fx6_dmmcfg_bytes: bytes,
    fx3_bank1_bytes: bytes,
    fx6_backup_seed_bytes: bytes,
    pformat_config_text: str,
) -> CpArm32StartupAudit:
    """Verify `cpapp-b.bin` ARM32 startup header, `@ 0x00108000` load base, and Bank 1 / SPI NOR contracts."""
    errors: List[str] = []
    fx6_sha = _sha256_bytes(fx6_cp_bytes)
    exp_len, exp_sha = EXPECTED_FX6_NFLASHA8_ARTIFACTS["cpapp-b.bin"]
    if len(fx6_cp_bytes) != exp_len or fx6_sha != exp_sha:
        errors.append(f"FX6 cpapp-b.bin mismatch: {len(fx6_cp_bytes)} B / {fx6_sha}")

    if fx6_cp_bytes[:4] == b"\x7fELF":
        errors.append("cpapp-b.bin unexpectedly carries an ELF header instead of flat ARM32 binary")

    if len(fx6_cp_bytes) < 0x400:
        errors.append("cpapp-b.bin too truncated to inspect ARM32 startup vectors")
        entry_words = (0,) * 6
        extra_ptrs = (0,) * 5
    else:
        entry_words = struct.unpack_from("<6I", fx6_cp_bytes, 0)
        extra_ptrs = struct.unpack_from("<5I", fx6_cp_bytes, 0x380)

    if entry_words != EXPECTED_CP_ARM32_ENTRY_WORDS:
        errors.append(
            f"ARM32 startup words mismatch: {[hex(w) for w in entry_words]} "
            f"!= {[hex(w) for w in EXPECTED_CP_ARM32_ENTRY_WORDS]}"
        )

    self_ref_lit = entry_words[3]
    derived_base = self_ref_lit - 0x0C
    first_jump = self_ref_lit + 0x04
    if derived_base != CP_LOCAL_LOAD_BASE or first_jump != CP_FIRST_BRANCH_TARGET:
        errors.append(
            f"Derived CP load base 0x{derived_base:08x} / jump 0x{first_jump:08x} "
            f"!= 0x{CP_LOCAL_LOAD_BASE:08x} / 0x{CP_FIRST_BRANCH_TARGET:08x}"
        )

    upper_bound = CP_LOCAL_LOAD_BASE + len(fx6_cp_bytes)
    ptrs_in_range = all(CP_LOCAL_LOAD_BASE <= p < upper_bound for p in extra_ptrs)
    if not ptrs_in_range:
        errors.append(f"0x380 embedded vector pointers out of range: {[hex(p) for p in extra_ptrs]}")

    # Cross-check FX3 CP reference metadata from cp-av-analysis/mapping.json
    fx3_ref = cp_av_mapping_json.get("fx3_cp_reference")
    if not isinstance(fx3_ref, Mapping):
        errors.append("mapping.json missing fx3_cp_reference object")
        fx3_bytes_cnt = 0
        fx3_sha = ""
        prefix_bytes = 0
    else:
        fx3_bytes_cnt = int(fx3_ref.get("bytes", 0))
        fx3_sha = str(fx3_ref.get("sha256", ""))
        prefix_bytes = int(fx3_ref.get("identical_prefix_bytes", 0))
        if (
            fx3_bytes_cnt != EXPECTED_FX3_CP_REF_BYTES
            or fx3_sha != EXPECTED_FX3_CP_REF_SHA256
            or prefix_bytes != EXPECTED_CP_IDENTICAL_PREFIX_BYTES
        ):
            errors.append(
                f"FX3 CP reference mismatch in mapping.json: bytes={fx3_bytes_cnt} sha={fx3_sha} prefix={prefix_bytes}"
            )

    # Cross-check 0xfa0080 Bank 1 load descriptors on both FX3 and FX6
    fx3_b1 = parse_and_audit_fa0080_bank(
        fx3_bank1_bytes, label="FX3_702_BANK1", bank_index=1
    )
    _, (fx6_r1_b8, fx6_r1_bytes) = _extract_two_bk4_records(fx6_backup_seed_bytes)
    fx6_b1_raw = read_bk4_property_bytes(fx6_r1_bytes, 0x00FA0080)
    if fx6_b1_raw is None:
        errors.append("Missing 0x00fa0080 Bank 1 property in FX6 backup seed")
        fx6_b1 = fx3_b1
    else:
        fx6_b1 = parse_and_audit_fa0080_bank(
            fx6_b1_raw, label="FX6_601_BANK1", bank_index=1, active_byte8=fx6_r1_b8
        )

    def _find_slot(audit_obj: object, path_name: str) -> Optional[Tuple[int, int, int]]:
        slots = getattr(audit_obj, "intervals", ())
        for sl in slots:
            if getattr(sl, "path", "") == path_name:
                return (
                    int(getattr(sl, "partition", 0)),
                    int(getattr(sl, "raw_start_addr", 0)),
                    int(getattr(sl, "effective_span_bytes", 0)),
                )
        return None

    fx3_tomco_slot = _find_slot(fx3_b1, "\\tomco.txt")
    fx6_tomco_slot = _find_slot(fx6_b1, "\\tomco.txt")
    bank1_tomco_ok = (
        fx3_tomco_slot == (8, TOMCO_BANK1_BUS_LOAD_ADDR, TOMCO_BANK1_SPAN_BYTES)
        and fx6_tomco_slot == (8, TOMCO_BANK1_BUS_LOAD_ADDR, TOMCO_BANK1_SPAN_BYTES)
    )
    if not bank1_tomco_ok:
        errors.append(f"Bank 1 \\tomco.txt slot mismatch: FX3={fx3_tomco_slot} FX6={fx6_tomco_slot}")

    fx3_cp_slot = _find_slot(fx3_b1, "\\cpapp-b.bin")
    fx6_cp_slot = _find_slot(fx6_b1, "\\cpapp-b.bin")
    bank1_cpapp_ok = (
        fx3_cp_slot is not None
        and fx6_cp_slot is not None
        and fx3_cp_slot[0] == 8
        and fx6_cp_slot[0] == 8
        and fx3_cp_slot[1] == CP_BANK1_BUS_LOAD_ADDR
        and fx6_cp_slot[1] == CP_BANK1_BUS_LOAD_ADDR
        and (CP_BANK1_BUS_LOAD_ADDR & 0xFFFFFFFF) == CP_LOCAL_LOAD_BASE
    )
    if not bank1_cpapp_ok:
        errors.append(f"Bank 1 \\cpapp-b.bin slot mismatch: FX3={fx3_cp_slot} FX6={fx6_cp_slot}")

    cpapp_block_match = re.search(
        r'file_param\s*\{[^}]*path\s*=\s*"cpapp-b\.bin"[^}]*\}',
        pformat_config_text,
        re.DOTALL,
    )
    spi_nor_ok = bool(
        cpapp_block_match
        and re.search(r"load\s*=\s*0x00108000\b", cpapp_block_match.group(0))
        and re.search(r"start\s*=\s*4096\b", cpapp_block_match.group(0))
        and re.search(r"ldrinfo\s*=\s*3\b", cpapp_block_match.group(0))
    )
    if not spi_nor_ok:
        errors.append(
            "pformat_config.txt missing TOPPERS cpapp-b.bin (load=0x00108000, start=4096, ldrinfo=3) entry"
        )

    fx3_dmm_sha = _sha256_bytes(fx3_dmmcfg_bytes)
    if len(fx3_dmmcfg_bytes) != EXPECTED_FX3_DMMCFG_BYTES or fx3_dmm_sha != EXPECTED_FX3_DMMCFG_SHA256:
        errors.append(f"FX3 DmmCfg.bin mismatch: {len(fx3_dmmcfg_bytes)} B / {fx3_dmm_sha}")

    valid = len(errors) == 0
    return CpArm32StartupAudit(
        valid=valid,
        fx6_cp_bytes=len(fx6_cp_bytes),
        fx6_cp_sha256=fx6_sha,
        fx3_cp_ref_bytes=fx3_bytes_cnt,
        fx3_cp_ref_sha256=fx3_sha,
        cp_size_delta_bytes=len(fx6_cp_bytes) - fx3_bytes_cnt,
        identical_prefix_bytes=prefix_bytes,
        entry_words_hex=tuple(f"0x{w:08x}" for w in entry_words),
        self_ref_literal=f"0x{self_ref_lit:08x}",
        derived_load_base=f"0x{derived_base:08x}",
        first_branch_target=f"0x{first_jump:08x}",
        embedded_vector_pointers_in_range=ptrs_in_range,
        bank1_tomco_addr_matched=bank1_tomco_ok,
        bank1_cpapp_addr_matched=bank1_cpapp_ok,
        spi_nor_cpapp_offset_matched=spi_nor_ok,
        fx3_dmmcfg_bytes=len(fx3_dmmcfg_bytes),
        fx6_dmmcfg_bytes=len(fx6_dmmcfg_bytes),
        dmmcfg_size_delta_bytes=len(fx6_dmmcfg_bytes) - len(fx3_dmmcfg_bytes),
        errors=tuple(errors),
    )


def scan_fx6_cp_peripheral_markers(fx6_cp_bytes: bytes) -> CpPeripheralMarkerAudit:
    """Verify exact pinned peripheral driver & IPC strings in FX6 `cpapp-b.bin`."""
    errors: List[str] = []
    hits: List[CpPeripheralMarkerHit] = []
    cat_counts: Dict[str, int] = {}
    verified_cnt = 0
    exclusive_cnt = 0

    for category, offset, expected_ascii, exclusive, mitigation in PINNED_FX6_CP_PERIPHERAL_MARKERS:
        needle = expected_ascii.encode("ascii")
        end_off = offset + len(needle)
        matched = end_off <= len(fx6_cp_bytes) and fx6_cp_bytes[offset:end_off] == needle
        if matched:
            verified_cnt += 1
            cat_counts[category] = cat_counts.get(category, 0) + 1
            if exclusive:
                exclusive_cnt += 1
        else:
            errors.append(
                f"Missing pinned CP peripheral marker at 0x{offset:x} ({category}): {expected_ascii!r}"
            )
        hits.append(
            CpPeripheralMarkerHit(
                category=category,
                file_offset_hex=f"0x{offset:06x}",
                exact_ascii=expected_ascii,
                verified_at_pinned_offset=matched,
                fx6_hardware_exclusive=exclusive,
                ap_mitigation=mitigation,
            )
        )

    required_cats = {
        "darwin_electronic_nd",
        "mew_sdi_genlock_fpga",
        "fan_thermal_control",
        "toppers_fmp_rtos",
        "uipc_dmm_backup_ipc",
    }
    missing_cats = sorted(required_cats - set(cat_counts.keys()))
    if missing_cats:
        errors.append(f"Missing required CP peripheral marker categories: {missing_cats}")

    valid = verified_cnt == len(PINNED_FX6_CP_PERIPHERAL_MARKERS) and len(errors) == 0
    return CpPeripheralMarkerAudit(
        valid=valid,
        total_pinned_markers=len(PINNED_FX6_CP_PERIPHERAL_MARKERS),
        verified_marker_count=verified_cnt,
        fx6_exclusive_hazard_count=exclusive_cnt,
        category_counts=cat_counts,
        markers=tuple(hits),
        errors=tuple(errors),
    )


def validate_candidate_cp_redline(
    overlay_manifest: Optional[Mapping[str, object]] = None,
    overlay_entry_paths: Sequence[str] = (),
    scripts_to_audit: Sequence[Tuple[str, str]] = (),
    p8_cp_mutation_forbidden: bool = True,
    cp_mutation_bytes: int = 0,
) -> CandidateCpRedlineAudit:
    """Enforce the Stage-A Stock-CP Redline (`p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`).

    Rejects any candidate manifest, CPIO entry path, or shell script that attempts to overwrite
    or bind-mount over FX3 stock `p8` (`/dev/nflasha8`), `/cp`, `cpapp-b.bin`, `tomco.txt`,
    `DmmCfg.bin`, `udtrcp.bin`, or Octal-SPI NOR `0x00200000`.
    """
    violations: List[str] = []

    if not p8_cp_mutation_forbidden:
        violations.append("p8_cp_mutation_forbidden must remain strictly True")
    if cp_mutation_bytes != 0:
        violations.append(f"cp_mutation_bytes must be 0, got {cp_mutation_bytes}")

    if overlay_manifest is not None:
        if overlay_manifest.get("p8_cp_mutation_forbidden") is False:
            violations.append("overlay_manifest explicitly disabled p8_cp_mutation_forbidden")
        mut_b = overlay_manifest.get("cp_mutation_bytes", 0)
        if isinstance(mut_b, int) and mut_b != 0:
            violations.append(f"overlay_manifest declared non-zero cp_mutation_bytes={mut_b}")
        target_parts = overlay_manifest.get("target_flash_partitions", [])
        if isinstance(target_parts, Sequence) and not isinstance(target_parts, (str, bytes)):
            for part in target_parts:
                p_str = str(part).lower()
                if p_str in ("p8", "nflasha8", "/dev/nflasha8", "/cp", "spi_nor_cp"):
                    violations.append(f"overlay_manifest targets forbidden CP partition: {part!r}")

    for path_str in overlay_entry_paths:
        norm = "/" + path_str.lstrip("/")
        lower_norm = norm.lower()
        if (
            lower_norm.startswith("/cp/")
            or lower_norm == "/cp"
            or lower_norm.endswith("/cpapp-b.bin")
            or lower_norm.endswith("/udtrcp.bin")
            or lower_norm.endswith("/tomco.txt")
            or lower_norm.endswith("/dmmcfg.bin")
        ):
            violations.append(f"Forbidden CP RTOS payload staged in overlay archive: {path_str!r}")

    for script_name, script_text in scripts_to_audit:
        for line_no, raw_ln in enumerate(script_text.splitlines(), start=1):
            stripped = raw_ln.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for tok in FORBIDDEN_CP_MUTATION_TOKENS:
                if tok in stripped:
                    violations.append(
                        f"{script_name}:{line_no}: forbidden CP/p8 token {tok!r} in active command"
                    )

    return CandidateCpRedlineAudit(
        valid=len(violations) == 0,
        p8_cp_mutation_forbidden=p8_cp_mutation_forbidden and len(violations) == 0,
        cp_mutation_bytes=cp_mutation_bytes,
        audited_overlay_paths=len(overlay_entry_paths),
        audited_script_count=len(scripts_to_audit),
        violations=tuple(violations),
    )


def run_cp_rtos_compatibility_verification(
    fx6_nflasha8_dir: Path = DEFAULT_FX6_NFLASHA8_DIR,
    fx6_cp_av_analysis_dir: Path = DEFAULT_FX6_CP_AV_ANALYSIS_DIR,
    fx3_runtime_tomco_path: Path = DEFAULT_FX3_RUNTIME_TOMCO_PATH,
    fx3_updater_cp_dir: Path = DEFAULT_FX3_UPDATER_CP_DIR,
    fx3_dmmcfg_path: Path = DEFAULT_FX3_DMMCFG_PATH,
    fx3_bank1_path: Path = DEFAULT_FX3_BANK1_FA0080_PATH,
    fx6_backup_seed_path: Path = DEFAULT_FX6_TEMPLATE_BK4_PATH,
    pformat_config_path: Path = DEFAULT_FX3_PFORMAT_CONFIG_PATH,
    overlay_manifest: Optional[Mapping[str, object]] = None,
    overlay_entry_paths: Sequence[str] = (),
    scripts_to_audit: Sequence[Tuple[str, str]] = (),
) -> Phase10CpRtosCompatibilityReport:
    """Execute full Phase 10 Blueprint `U2` CP RTOS & `tomco.txt` compatibility verification."""
    artifact_records: List[CpArtifactDigestRecord] = []
    all_n8_matched = True

    cached_blobs: Dict[str, bytes] = {}
    for fname, (exp_bytes, exp_sha) in EXPECTED_FX6_NFLASHA8_ARTIFACTS.items():
        fpath = fx6_nflasha8_dir / fname
        raw = fpath.read_bytes()
        cached_blobs[fname] = raw
        sha = _sha256_bytes(raw)
        matched = len(raw) == exp_bytes and sha == exp_sha
        if not matched:
            all_n8_matched = False
        artifact_records.append(
            CpArtifactDigestRecord(
                name=fname,
                byte_size=len(raw),
                sha256=sha,
                expected_bytes=exp_bytes,
                expected_sha256=exp_sha,
                matched=matched,
            )
        )

    udtrcp_raw = (fx3_updater_cp_dir / "udtrcp.bin").read_bytes()
    udtrcp_ok = (
        len(udtrcp_raw) == EXPECTED_FX3_UDTRCP_BYTES
        and _sha256_bytes(udtrcp_raw) == EXPECTED_FX3_UDTRCP_SHA256
    )

    tomco_audit = compare_tomco_configs(
        fx3_runtime_bytes=fx3_runtime_tomco_path.read_bytes(),
        fx6_runtime_bytes=cached_blobs["tomco.txt"],
        fx3_updater_bytes=(fx3_updater_cp_dir / "tomco.txt").read_bytes(),
    )

    mapping_json = json.loads((fx6_cp_av_analysis_dir / "mapping.json").read_text(encoding="utf-8"))
    arm32_audit = audit_cpapp_arm32_startup(
        fx6_cp_bytes=cached_blobs["cpapp-b.bin"],
        cp_av_mapping_json=mapping_json,
        fx3_dmmcfg_bytes=fx3_dmmcfg_path.read_bytes(),
        fx6_dmmcfg_bytes=cached_blobs["DmmCfg.bin"],
        fx3_bank1_bytes=fx3_bank1_path.read_bytes(),
        fx6_backup_seed_bytes=fx6_backup_seed_path.read_bytes(),
        pformat_config_text=pformat_config_path.read_text(encoding="utf-8", errors="replace"),
    )

    marker_audit = scan_fx6_cp_peripheral_markers(cached_blobs["cpapp-b.bin"])

    redline_audit = validate_candidate_cp_redline(
        overlay_manifest=overlay_manifest,
        overlay_entry_paths=overlay_entry_paths,
        scripts_to_audit=scripts_to_audit,
        p8_cp_mutation_forbidden=True,
        cp_mutation_bytes=0,
    )

    u2_closed = (
        all_n8_matched
        and udtrcp_ok
        and tomco_audit.valid
        and arm32_audit.valid
        and marker_audit.valid
        and redline_audit.valid
    )
    return Phase10CpRtosCompatibilityReport(
        all_checks_passed=u2_closed,
        u2_closed=u2_closed,
        p8_cp_mutation_forbidden=redline_audit.p8_cp_mutation_forbidden,
        cp_mutation_bytes=redline_audit.cp_mutation_bytes,
        nflasha8_artifacts=tuple(artifact_records),
        fx3_udtrcp_verified=udtrcp_ok,
        tomco_audit=tomco_audit,
        arm32_startup_audit=arm32_audit,
        peripheral_marker_audit=marker_audit,
        candidate_redline_audit=redline_audit,
    )
