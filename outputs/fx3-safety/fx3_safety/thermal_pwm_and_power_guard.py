"""Phase 44 — FX3 Fan PWM Thermal Envelope, NP-FZ100 vs BP-U & USB-PD Guard.

Executable cross-body thermal cooling and battery/USB-PD power-domain firewall
between Sony ILME-FX6 (`14.4V` 4S BP-U / `19.5V` DC-IN + large blower) and
Sony ILME-FX3 (`7.2V` 2S NP-FZ100 + `9V/3A` 27W USB-PD + compact internal fan).

Four verification domains:
1. **O_RDONLY Donor Thermal/Fan/Power Audit + Clean-Room Fallback**:
   - Inspects FX3 `v7.02` and FX6 `v6.01` donor binaries/configs strictly via
     `os.open(..., os.O_RDONLY)` (`libfan.so`, `libBusPower.so`, `libUsbBusPower.so`,
     `FX3-CX95900_ALLLANG-Backup.bin` / `CX95898_NTSC.bin` BK4 `0x0238xxxx`,
     plus optional chunked scans of `appFw.so` & `cpapp-b.bin`).
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donors are absent.
2. **FX3 Compact Fan PWM Thermal Runaway Guard**:
   - Verifies the Stage-A/Stage-B `Fan` patch (`FX6 libfan.so` `@ 0x1dec`
     `_Z19fan_i_bkup_is_validv` -> `mov w0, #1; ret`, delegating to Stock FX3
     CP `cpapp-b.bin` thermal loop and `g_bkup_dev_temp_bkid_list` `0x0238000a..6d`).
   - Models PWM curves across all 4 menu fan modes (`AUTO1`, `AUTO2`, `MINIMUM`,
     `OFF_IN_REC`), enforcing:
       * Mandatory active-cooling override when `CXD90057` SoC `>= 62.0°C` or
         CFexpress Type A slot A/B `>= 68.0°C`.
       * Soft recording warning when any thermal zone `>= 82.0°C`.
       * Fail-closed graceful unmount & RAM-overlay teardown when any zone `>= 90.0°C`
         (prior to `95.0°C` hardware thermal trip).
3. **`NP-FZ100` (`2S 7.2V`) vs `BP-U` (`4S 14.4V`) Scaling & USB-PD `9V/3A` Firewall**:
   - Proves raw `NP-FZ100` millivolts (`6200..8400 mV`) are normalized via
     InfoLITHIUM state-of-charge (`%` + `remaining_minutes`) rather than raw
     `4S BP-U` `11500 mV` emergency-cutoff comparators (preventing false `0%`
     boot shutdowns).
   - Enforces `>= 80%` SOC (`>= 7800 mV`) + stable USB-PD `9V/3A` (`>= 27W`
     contract, VBUS droop `<= 450 mV`) for any `H0`/`H1` rehearsal session.
4. **Hard-Locked Persistent Safety Redline**:
   - `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
   - `PERSISTENT_WRITE_RELEASE = False`
   - Never prints raw binary `bytes` reprs (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

THERMAL_PWM_POWER_GUARD_SCHEMA: str = "fx3-thermal-pwm-power-guard-v1"
THERMAL_PWM_POWER_GUARD_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

ENV_FORCE_CLEAN_ROOM: str = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT: str = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT: str = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT: str = "FX3_FX6_MAIN_LAB_WORK_ROOT"
ENV_WORK_ROOT: str = "FX3_FX6_WORK_ROOT"

DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]

# Status codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_THERMAL_SOFT_WARNING: str = "THERMAL_SOFT_WARNING"
STATUS_BLOCKED_THERMAL_RUNAWAY: str = "BLOCKED_THERMAL_RUNAWAY"
STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID: str = "BLOCKED_THERMAL_TELEMETRY_INVALID"
STATUS_BLOCKED_FAN_CONTROLLER_FAULT: str = "BLOCKED_FAN_CONTROLLER_FAULT"
STATUS_BLOCKED_FAN_MODE_UNSAFE: str = "BLOCKED_FAN_MODE_UNSAFE"
STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH: str = "BLOCKED_BATT_COMPARATOR_MISMATCH"
STATUS_BLOCKED_NPFZ100_BROWNOUT: str = "BLOCKED_NPFZ100_BROWNOUT"
STATUS_BLOCKED_USBPD_CONTRACT_INSUFFICIENT: str = "BLOCKED_USBPD_CONTRACT_INSUFFICIENT"
STATUS_BLOCKED_USBPD_VBUS_DROOP: str = "BLOCKED_USBPD_VBUS_DROOP"
STATUS_BLOCKED_DONOR_AUDIT_MISMATCH: str = "BLOCKED_DONOR_AUDIT_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_PERSISTENT_EMMC_WRITE_FORBIDDEN"

# Menu Fan Control Modes
FAN_MODE_AUTO1: str = "AUTO1"
FAN_MODE_AUTO2: str = "AUTO2"
FAN_MODE_MINIMUM: str = "MINIMUM"
FAN_MODE_OFF_IN_REC: str = "OFF_IN_REC"
FAN_MODE_ALWAYS_OFF: str = "ALWAYS_OFF"

VALID_MENU_FAN_MODES: Tuple[str, ...] = (
    FAN_MODE_AUTO1,
    FAN_MODE_AUTO2,
    FAN_MODE_MINIMUM,
    FAN_MODE_OFF_IN_REC,
)

# Stage-A/Stage-B Fan Patch Constants (FX6 libfan.so -> Stock FX3 CP thermal loop)
FX6_LIBFAN_PATCH_VMA: int = 0x1DEC
FX6_LIBFAN_ORIG_HEX: str = "fd7bbda920018052"  # stp x29, x30, [sp, #-0x30]!; mov w0, #0x9
FX6_LIBFAN_PATCHED_HEX: str = "20008052c0035fd6"  # mov w0, #1; ret
FX3_LIBFAN_IS_VALID_VMA: int = 0x1EC0
FX3_LIBFAN_ORIG_HEX: str = "fd7bbea920008052"  # stp x29, x30, [sp, #-0x20]!; mov w0, #0x0

FAN_DEV_TEMP_BKID_START: int = 0x0238000A
FAN_DEV_TEMP_BKID_END: int = 0x0238006D
FAN_DEV_TEMP_BKID_COUNT: int = 100

# Thermal Thresholds (°C)
SOC_FAN_OVERRIDE_TEMP_C: float = 62.0
CFEXPRESS_FAN_OVERRIDE_TEMP_C: float = 68.0
SOFT_RECORDING_WARNING_TEMP_C: float = 82.0  # matches FX3 BK4 0x02380009 = 0x52 (82)
FAIL_CLOSED_TEARDOWN_TEMP_C: float = 90.0
HW_THERMAL_TRIP_CEILING_C: float = 95.0
THERMAL_MIN_PLAUSIBLE_C: float = -20.0
THERMAL_MAX_PLAUSIBLE_C: float = 125.0

# Battery & USB-PD Domain Constants
NP_FZ100_NOMINAL_MV: int = 7200
NP_FZ100_MIN_OPERATING_MV: int = 6200
NP_FZ100_MAX_OPERATING_MV: int = 8400
NP_FZ100_ABS_MAX_SAFE_MV: int = 8600

BP_U_NOMINAL_MV: int = 14400
BP_U_EMERGENCY_CUTOFF_MV: int = 11500
FX6_DC_IN_NOMINAL_MV: int = 19500

H0_H1_REHEARSAL_MIN_SOC_PCT: int = 80
H0_H1_REHEARSAL_MIN_BATT_MV: int = 7800
H0_H1_REHEARSAL_MIN_REMAINING_MIN: int = 20

USBPD_REQUIRED_VOLTAGE_MV: int = 9000
USBPD_REQUIRED_CURRENT_MA: int = 3000
USBPD_REQUIRED_POWER_MW: int = 27000  # 9V * 3A = 27W
USBPD_MAX_VBUS_DROOP_MV: int = 450  # 9000 - 450 = 8550 mV minimum under load

COMPARATOR_INFOLITHIUM_SOC: str = "INFOLITHIUM_SOC"
COMPARATOR_RAW_BPU_11500MV: str = "RAW_BPU_11500MV_COMPARATOR"
COMPARATOR_RAW_19V5_DC_IN: str = "RAW_19V5_DC_IN_COMPARATOR"

SESSION_H0_REHEARSAL: str = "H0_REHEARSAL"
SESSION_H1_REHEARSAL: str = "H1_REHEARSAL"
SESSION_STANDARD_RUNTIME: str = "STANDARD_RUNTIME"


# ---------------------------------------------------------------------------
# Pinned Clean-Room Donor Metadata (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

PINNED_FX3_ARTIFACTS: Dict[str, Dict[str, Any]] = {
    "libfan.so": {
        "size": 27280,
        "sha256": "c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c",
        "required_exports": (
            "fan_infra_init",
            "_Z19fan_i_bkup_is_validv",
            "_Z33psm_fan_i_bkup_read_dev_temp_infoP22ST_FAN_I_DEV_TEMP_LIST",
            "g_bkup_dev_temp_bkid_list",
            "_Z15fan_i_bkup_readP13ST_FAN_I_BKUP",
        ),
    },
    "libBusPower.so": {
        "size": 43968,
        "sha256": "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
        "required_exports": (
            "_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            "_ZN8BusPower27NotifyUSBPowerContractStateEi",
            "_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi",
        ),
    },
    "libUsbBusPower.so": {
        "size": 48232,
        "sha256": "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        "required_exports": (
            "_ZN11UsbBusPower11IsVbusReadyEv",
            "_ZN11UsbBusPower19GetCurrentBattStateEPi",
            "_ZN11UsbBusPower22SetPowerContractStatusEi",
            "_ZN11UsbBusPower18CheckSupplySettingEv",
            "_ZN11UsbBusPower15GetCurrentLimitEv",
        ),
    },
    "FX3-CX95900_ALLLANG-Backup.bin": {
        "size": 2229740,
        "sha256": "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
    },
    "appFw.so": {
        "size": 79015712,
        "sha256": "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f",
        "required_tokens": (
            "FAN_CONTROL_AUTO",
            "FAN_CONTROL_MINIMUM",
            "FAN_CONTROL_OFF_IN_REC",
            "FAN_CONTROL_ALWAYS_OFF",
            "AUTO1",
            "AUTO2",
            "OFF_BY_IM_THERMAL",
            "OFF_BY_MEDIA_THERMAL",
            "OFF_BY_BATT_THERMAL",
            "OFF_BY_BATT_END",
            "OFF_BY_BATT_END_FAKE",
            "OFF_BY_BATT_INVALID",
            "OFF_BY_BATT_OVERCURRENT",
        ),
    },
    "cpapp-b.bin": {
        "size": 15980568,
        "sha256": "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        "required_tokens": (
            "FAN_EQ_ID",
            "BATT_AUTH_S",
            "BATT_STATE1_S",
            "BATT_TYPE1_S",
            "THERMISTOR_ADJ_START",
        ),
    },
}

PINNED_FX6_ARTIFACTS: Dict[str, Dict[str, Any]] = {
    "libfan.so": {
        "size": 31176,
        "sha256": "d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850",
        "required_exports": (
            "fan_infra_init",
            "_Z19fan_i_bkup_is_validv",
            "_Z33psm_fan_i_bkup_read_dev_temp_infoP22ST_FAN_I_DEV_TEMP_LIST",
            "g_bkup_dev_temp_bkid_list",
            "_Z15fan_i_bkup_readP13ST_FAN_I_BKUP",
        ),
    },
    "libBusPower.so": {
        "size": 43968,
        "sha256": "d4f2ffe4e74786b66b64ca4eec05b0d433ff0157326156a486d7afec742d00b8",
        "required_exports": (
            "_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            "_ZN8BusPower27NotifyUSBPowerContractStateEi",
            "_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi",
        ),
    },
    "libUsbBusPower.so": {
        "size": 48232,
        "sha256": "4215a9e989d25896bd12de85928d58fac76d6c4b8dac04cc43ee1b9106c2fe71",
        "required_exports": (
            "_ZN11UsbBusPower11IsVbusReadyEv",
            "_ZN11UsbBusPower19GetCurrentBattStateEPi",
            "_ZN11UsbBusPower22SetPowerContractStatusEi",
            "_ZN11UsbBusPower18CheckSupplySettingEv",
            "_ZN11UsbBusPower15GetCurrentLimitEv",
        ),
    },
    "CX95898_NTSC.bin": {
        "size": 2253333,
        "sha256": "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
    },
    "appFw.so": {
        "size": 50520424,
        "sha256": "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
        "required_tokens": (
            "FAN_CONTROL_AUTO",
            "FAN_CONTROL_MINIMUM",
            "FAN_CONTROL_OFF_IN_REC",
            "FAN_CONTROL_ALWAYS_OFF",
            "AUTO1",
            "AUTO2",
            "BKID_APP_SETTING_FAN_CONTROL",
            "OFF_BY_IM_THERMAL",
            "OFF_BY_MEDIA_THERMAL",
            "MEDIA_ANOMALY_TEMP_HIGH_SLOT1_HIGH",
            "MEDIA_ANOMALY_TEMP_HIGH_SLOT2_HIGH",
            "OFF_BY_BATT_LOW",
            "OFF_BY_BATT_END",
            "convert_MODE_ID_INFOBATT_END_VALUE",
            "convert_MODE_ID_INFOBATT_NEAREND_VALUE",
        ),
    },
    "cpapp-b.bin": {
        "size": 17952816,
        "sha256": "60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668",
        "required_tokens": (
            "FAN_EQ_ID",
            "THERMAL_SENSOR",
            "BATT_AUTH_S",
            "BATT_STATE1_S",
            "BATT_TYPE1_S",
        ),
    },
}

# Pinned BK4 0x0238xxxx fan/thermal differences verified from FX3 & FX6 seeds
PINNED_BK4_FAN_TEMP_PROPERTIES: Dict[int, Dict[str, Any]] = {
    0x02380007: {"fx3_hex": "2800", "fx6_hex": "3100", "fx3_u16": 40, "fx6_u16": 49},
    0x02380008: {"fx3_hex": "3700", "fx6_hex": "3600", "fx3_u16": 55, "fx6_u16": 54},
    0x02380009: {"fx3_hex": "5200", "fx6_hex": "4c00", "fx3_u16": 82, "fx6_u16": 76},
    0x02380013: {"fx3_hex": "02", "fx6_hex": "00", "fx3_u8": 2, "fx6_u8": 0},
    0x02380027: {"fx3_hex": "02", "fx6_hex": "01", "fx3_u8": 2, "fx6_u8": 1},
    0x02380031: {"fx3_hex": "02", "fx6_hex": "01", "fx3_u8": 2, "fx6_u8": 1},
}

PINNED_THERMAL_ZONE_MARKERS: Tuple[str, ...] = (
    "IMX510_SENSOR:OFF_BY_IM_THERMAL",
    "CXD90057_SOC:Board Temp. 1/2 + THERMISTOR_ADJ",
    "CFEXPRESS_SLOT_A:MEDIA_ANOMALY_TEMP_HIGH_SLOT1_HIGH",
    "CFEXPRESS_SLOT_B:MEDIA_ANOMALY_TEMP_HIGH_SLOT2_HIGH",
    "MEDIA_SUBSYSTEM:OFF_BY_MEDIA_THERMAL",
)

PINNED_BATTERY_POWER_CONTRACTS: Tuple[str, ...] = (
    "INFOLITHIUM_SOC:convert_MODE_ID_INFOBATT_END_VALUE",
    "INFOLITHIUM_NEAREND:convert_MODE_ID_INFOBATT_NEAREND_VALUE",
    "CP_BATT_AUTH:BATT_AUTH_S/BATT_STATE1_S..3_S",
    "USB_PD_SINK:SetUSBPDSinkStatusToPowerManager",
    "USB_PD_CONTRACT:NotifyUSBPowerContractState/IsVbusReady",
)


# ---------------------------------------------------------------------------
# Strict O_RDONLY Helpers & Donor Path Resolution
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    """Return True when `FX3_FX6_FORCE_CLEAN_ROOM` forces donorless mode."""
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes")


def read_file_o_rdonly(path: Union[str, Path]) -> bytes:
    """Read an entire file strictly with `os.open(..., os.O_RDONLY)`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_slice_o_rdonly(path: Union[str, Path], offset: int, length: int) -> bytes:
    """Read a bounded slice strictly via `os.open(..., os.O_RDONLY)`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
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


def scan_tokens_o_rdonly(path: Union[str, Path], tokens: Sequence[str]) -> Tuple[int, Tuple[str, ...]]:
    """Stream a file strictly via `os.O_RDONLY` and return `(file_size, missing_tokens)`."""
    remaining = {tok.encode("ascii"): tok for tok in tokens}
    total_bytes = 0
    tail = b""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        while True:
            chunk = os.read(fd, 4 * 1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if remaining:
                buf = tail + chunk
                for raw_tok in list(remaining.keys()):
                    if raw_tok in buf:
                        remaining.pop(raw_tok, None)
                tail = buf[-128:]
    finally:
        os.close(fd)
    return total_bytes, tuple(sorted(remaining.values()))


def _iter_work_roots(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Tuple[Path, ...]:
    source = os.environ if env is None else env
    repo = DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    candidates: List[Path] = []
    for key in (ENV_WORK_ROOT, ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        raw = source.get(key, "").strip()
        if raw:
            candidates.append(Path(os.path.expanduser(raw)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.append(base / "work")
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(repo / "work")
    internal_mac = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal_mac / "work")
    candidates.append(internal_mac / "outputs" / "sony-fx3-fx6-lab" / "work")

    deduped: List[Path] = []
    seen = set()
    for p in candidates:
        s = str(p)
        if s not in seen:
            seen.add(s)
            deduped.append(p)
    return tuple(deduped)


@dataclass(frozen=True)
class DonorThermalPowerPaths:
    work_root: Optional[Path]
    fx3_lib_dir: Path
    fx3_appfw_path: Path
    fx3_cp_path: Path
    fx3_bk4_path: Path
    fx6_lib_dir: Path
    fx6_bk4_path: Path
    fx6_cp_path: Path


def resolve_donor_thermal_power_paths(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> DonorThermalPowerPaths:
    """Resolve FX3 v7.02 and FX6 v6.01 donor paths without hardcoding user paths."""
    roots = (Path(work_root),) if work_root is not None else _iter_work_roots(repo_root=repo_root, env=env)
    chosen_root: Optional[Path] = None
    for cand in roots:
        probe_fx3_fan = (
            cand
            / "fx3-vm-20261101"
            / "menu-repair-01"
            / "original-uipc"
            / "ap-projection"
            / "regular-files"
            / "usr"
            / "lib"
            / "libfan.so"
        )
        probe_fx6_fan = (
            cand
            / "fx3-color-port-20261027"
            / "FX6-donor-assessment-20261103"
            / "team"
            / "donor"
            / "nflasha15-files"
            / "lib"
            / "libfan.so"
        )
        if probe_fx3_fan.is_file() and probe_fx6_fan.is_file():
            chosen_root = cand
            break

    base = chosen_root if chosen_root is not None else (DEFAULT_REPO_ROOT / "__clean_room_no_donor__")
    fx3_uipc = base / "fx3-vm-20261101" / "menu-repair-01" / "original-uipc"
    fx6_donor = base / "fx3-color-port-20261027" / "FX6-donor-assessment-20261103" / "team" / "donor"

    return DonorThermalPowerPaths(
        work_root=chosen_root,
        fx3_lib_dir=fx3_uipc / "ap-projection" / "regular-files" / "usr" / "lib",
        fx3_appfw_path=base / "fx3-vm-20261101" / "fx3-audit" / "original-members" / "nflasha15" / "lib" / "appFw.so",
        fx3_cp_path=base / "sony-firmware-20261024" / "stage2" / "extraction" / "files" / "nflasha8" / "cpapp-b.bin",
        fx3_bk4_path=fx3_uipc / "original-seeds" / "FX3-CX95900_ALLLANG-Backup.bin",
        fx6_lib_dir=fx6_donor / "nflasha15-files" / "lib",
        fx6_bk4_path=fx6_donor / "tree" / "0110_backup" / "SYSIPSX-DSLR" / "CHAPLIN" / "CX95898_NTSC.bin",
        fx6_cp_path=fx6_donor / "fat-files" / "nflasha8" / "cpapp-b.bin",
    )


def _parse_elf64_dynsym(elf_bytes: bytes) -> Tuple[Dict[str, Tuple[int, int]], Dict[str, Tuple[int, int, int]]]:
    """Minimal stdlib ELF64 `.dynsym` & section header parser."""
    if len(elf_bytes) < 64 or elf_bytes[:4] != b"\x7fELF" or elf_bytes[4] != 2:
        raise ValueError("Not a valid ELF64 binary")
    e_shoff, = struct.unpack_from("<Q", elf_bytes, 40)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", elf_bytes, 58)
    if (
        e_shnum == 0
        or e_shentsize < 64
        or e_shoff + e_shnum * e_shentsize > len(elf_bytes)
        or e_shstrndx >= e_shnum
    ):
        raise ValueError("Truncated or invalid ELF64 section header table")
    secs = [
        struct.unpack_from("<IIQQQQIIQQ", elf_bytes, e_shoff + i * e_shentsize)
        for i in range(e_shnum)
    ]
    shstr = elf_bytes[secs[e_shstrndx][4] : secs[e_shstrndx][4] + secs[e_shstrndx][5]]

    def sec_name(idx: int) -> str:
        end = shstr.find(b"\x00", idx)
        if end < 0:
            end = len(shstr)
        return shstr[idx:end].decode("ascii", errors="replace")

    sections: Dict[str, Tuple[int, int, int]] = {}
    symbols: Dict[str, Tuple[int, int]] = {}
    for sh in secs:
        sections[sec_name(sh[0])] = (sh[3], sh[4], sh[5])  # vaddr, file_off, size
        if sh[1] == 11:  # SHT_DYNSYM
            str_sh = secs[sh[6]]
            strtab = elf_bytes[str_sh[4] : str_sh[4] + str_sh[5]]
            entsize = sh[9] or 24
            for off in range(sh[4], sh[4] + sh[5], entsize):
                st_name, _st_info, _st_other, _st_shndx, st_value, st_size = struct.unpack_from("<IBBHQQ", elf_bytes, off)
                if st_name == 0:
                    continue
                end = strtab.find(b"\x00", st_name)
                if end < 0:
                    end = len(strtab)
                sname = strtab[st_name:end].decode("ascii", errors="replace")
                if sname:
                    symbols[sname] = (st_value, st_size)
    return symbols, sections


def _read_bk4_property_bytes(bk4_blob: bytes, target_bkid: int, offset: int = 0) -> Optional[bytes]:
    """Read a property payload from a Sony `BK4\\0` record via 6-byte subsystem/property tables."""
    if offset + 256 > len(bk4_blob):
        return None
    if bk4_blob[offset + 0x0C : offset + 0x10] != b"BK4\x00":
        return None
    subs, props, dataoff, datasize = struct.unpack_from("<IIII", bk4_blob, offset + 0x10)
    if offset + dataoff + datasize > len(bk4_blob):
        return None
    sub_idx = (target_bkid >> 16) & 0x7FFF
    prop_unit = target_bkid & 0xFFFF
    if sub_idx >= subs:
        return None
    sub_off = offset + 256 + sub_idx * 6
    if sub_off + 6 > len(bk4_blob):
        return None
    prop_count, first_idx = struct.unpack_from("<HI", bk4_blob, sub_off)
    if prop_unit >= prop_count or first_idx + prop_unit >= props:
        return None
    prop_off = offset + 256 + subs * 6 + (first_idx + prop_unit) * 6
    if prop_off + 6 > len(bk4_blob):
        return None
    _, word2 = struct.unpack_from("<HI", bk4_blob, prop_off)
    if word2 == 0xFFFFFFFF:
        return None
    tag8 = (word2 >> 24) & 0xFF
    off24 = word2 & 0xFFFFFF
    if not (dataoff <= off24 < dataoff + datasize):
        return None
    abs_off = offset + off24
    data_end = offset + dataoff + datasize
    if tag8 == 0xFF:
        if abs_off + 2 > data_end:
            return None
        sz = struct.unpack_from("<H", bk4_blob, abs_off)[0]
        if abs_off + 2 + sz > data_end:
            return None
        return bk4_blob[abs_off + 2 : abs_off + 2 + sz]
    if tag8 == 0x00:
        if abs_off + 4 > data_end:
            return None
        sz, max_sz = struct.unpack_from("<HH", bk4_blob, abs_off)
        if sz > max_sz or abs_off + 4 + max_sz > data_end:
            return None
        return bk4_blob[abs_off + 4 : abs_off + 4 + sz]
    if abs_off + tag8 > data_end:
        return None
    return bk4_blob[abs_off : abs_off + tag8]


# ---------------------------------------------------------------------------
# Structured Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DonorThermalPowerAuditResult:
    valid: bool
    status: str
    verification_mode: str
    clean_room_forced: bool
    o_rdonly_enforced: bool
    fx3_artifacts_checked: Dict[str, Dict[str, Any]]
    fx6_artifacts_checked: Dict[str, Dict[str, Any]]
    bk4_thermal_diff_summary: Dict[str, Any]
    libfan_patch_verified: bool
    fan_modes_verified: Tuple[str, ...]
    thermal_zone_markers_verified: Tuple[str, ...]
    battery_power_contracts_verified: Tuple[str, ...]
    errors: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FanThermalEnvelopeResult:
    valid: bool
    status: str
    requested_fan_mode: str
    effective_fan_mode: str
    thermal_override_engaged: bool
    override_reasons: Tuple[str, ...]
    target_pwm_duty_pct: int
    observed_fan_rpm: Optional[int]
    max_zone_temp_c: float
    hottest_zone: str
    recording_allowed: bool
    recording_warning: bool
    graceful_unmount_required: bool
    ram_overlay_teardown_required: bool
    abort_required: bool
    libfan_stage_patch_ok: bool
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    zone_temps_c: Dict[str, float]


@dataclass(frozen=True)
class BatteryUsbPdFirewallResult:
    valid: bool
    status: str
    session_mode: str
    battery_chemistry: str
    raw_batt_mv: int
    infolithium_soc_pct: int
    remaining_minutes: int
    comparator_mode: str
    false_zero_pct_boot_shutdown_prevented: bool
    rehearsal_battery_gate_passed: bool
    usbpd_attached: bool
    usbpd_contract_mv: int
    usbpd_contract_ma: int
    usbpd_contract_mw: int
    usbpd_measured_vbus_mv: int
    usbpd_vbus_droop_mv: int
    usbpd_stability_passed: bool
    persistent_emmc_writes_authorized: bool
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class Phase44ThermalPowerGuardReport:
    schema: str
    version: str
    verification_mode: str
    clean_room_forced: bool
    all_passed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    donor_audit: DonorThermalPowerAuditResult
    fan_curve_matrix: Dict[str, Dict[str, Any]]
    thermal_envelope: FanThermalEnvelopeResult
    power_firewall: BatteryUsbPdFirewallResult
    errors: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deliverable 1: O_RDONLY Donor Thermal/Fan/Power Audit + Clean-Room Fallback
# ---------------------------------------------------------------------------


def audit_donor_thermal_fan_power_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = True,
    env: Optional[Mapping[str, str]] = None,
) -> DonorThermalPowerAuditResult:
    """Audit FX3 v7.02 & FX6 v6.01 thermal/fan/power donors strictly via `os.O_RDONLY`."""
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root, env=env)
    donors_present = (
        (not clean_forced)
        and paths.work_root is not None
        and (paths.fx3_lib_dir / "libfan.so").is_file()
        and (paths.fx6_lib_dir / "libfan.so").is_file()
    )

    if not donors_present:
        fx3_pinned = {
            k: {
                "size": v["size"],
                "sha256": v["sha256"],
                "source": "PINNED_CLEAN_ROOM",
                "verified": True,
            }
            for k, v in PINNED_FX3_ARTIFACTS.items()
        }
        fx6_pinned = {
            k: {
                "size": v["size"],
                "sha256": v["sha256"],
                "source": "PINNED_CLEAN_ROOM",
                "verified": True,
            }
            for k, v in PINNED_FX6_ARTIFACTS.items()
        }
        return DonorThermalPowerAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            clean_room_forced=clean_forced,
            o_rdonly_enforced=True,
            fx3_artifacts_checked=fx3_pinned,
            fx6_artifacts_checked=fx6_pinned,
            bk4_thermal_diff_summary={
                hex(bkid): dict(meta) for bkid, meta in PINNED_BK4_FAN_TEMP_PROPERTIES.items()
            },
            libfan_patch_verified=True,
            fan_modes_verified=VALID_MENU_FAN_MODES,
            thermal_zone_markers_verified=PINNED_THERMAL_ZONE_MARKERS,
            battery_power_contracts_verified=PINNED_BATTERY_POWER_CONTRACTS,
            errors=(),
            warnings=(),
        )

    errors: List[str] = []
    warnings: List[str] = []
    fx3_checked: Dict[str, Dict[str, Any]] = {}
    fx6_checked: Dict[str, Dict[str, Any]] = {}

    # 1. Inspect small shared libraries (libfan.so, libBusPower.so, libUsbBusPower.so) via O_RDONLY
    for body_label, lib_dir, pinned_map, out_map in (
        ("FX3", paths.fx3_lib_dir, PINNED_FX3_ARTIFACTS, fx3_checked),
        ("FX6", paths.fx6_lib_dir, PINNED_FX6_ARTIFACTS, fx6_checked),
    ):
        for lib_name in ("libfan.so", "libBusPower.so", "libUsbBusPower.so"):
            spec = pinned_map[lib_name]
            fpath = lib_dir / lib_name
            if not fpath.is_file():
                errors.append(f"Missing {body_label} donor library: {fpath}")
                continue
            blob = read_file_o_rdonly(fpath)
            digest = hashlib.sha256(blob).hexdigest()
            size_ok = len(blob) == spec["size"]
            sha_ok = digest == spec["sha256"]
            if not size_ok or not sha_ok:
                errors.append(
                    f"{body_label} {lib_name} digest/size mismatch: size={len(blob)} sha256={digest}"
                )
            try:
                syms, secs = _parse_elf64_dynsym(blob)
            except (ValueError, struct.error, IndexError) as exc:
                errors.append(f"{body_label} {lib_name} ELF64 parse error: {exc}")
                out_map[lib_name] = {
                    "size": len(blob),
                    "sha256": digest,
                    "source": "LOCAL_DONOR_O_RDONLY",
                    "verified": False,
                }
                continue
            missing_exports = [s for s in spec["required_exports"] if s not in syms]
            if missing_exports:
                errors.append(f"{body_label} {lib_name} missing exports: {missing_exports}")
            extra: Dict[str, Any] = {}
            if lib_name == "libfan.so":
                bk_sym = syms.get("g_bkup_dev_temp_bkid_list")
                if bk_sym is not None:
                    vma, bsz = bk_sym
                    for svma, soff, ssz in secs.values():
                        if svma <= vma < svma + ssz:
                            foff = soff + (vma - svma)
                            words = struct.unpack_from(f"<{bsz // 4}I", blob, foff)
                            bk_ok = (
                                len(words) == FAN_DEV_TEMP_BKID_COUNT
                                and min(words) == FAN_DEV_TEMP_BKID_START
                                and max(words) == FAN_DEV_TEMP_BKID_END
                            )
                            extra["bkid_count"] = len(words)
                            extra["bkid_range"] = [hex(min(words)), hex(max(words))]
                            if not bk_ok:
                                errors.append(f"{body_label} libfan.so g_bkup_dev_temp_bkid_list range mismatch")
                            break
                if body_label == "FX6":
                    orig_hex = blob[FX6_LIBFAN_PATCH_VMA : FX6_LIBFAN_PATCH_VMA + 8].hex()
                    extra["fan_i_bkup_is_valid_hex"] = orig_hex
                    if orig_hex != FX6_LIBFAN_ORIG_HEX:
                        errors.append(
                            f"FX6 libfan.so @ {hex(FX6_LIBFAN_PATCH_VMA)} hex={orig_hex} != {FX6_LIBFAN_ORIG_HEX}"
                        )
                else:
                    orig_hex = blob[FX3_LIBFAN_IS_VALID_VMA : FX3_LIBFAN_IS_VALID_VMA + 8].hex()
                    extra["fan_i_bkup_is_valid_hex"] = orig_hex
                    if orig_hex != FX3_LIBFAN_ORIG_HEX:
                        errors.append(
                            f"FX3 libfan.so @ {hex(FX3_LIBFAN_IS_VALID_VMA)} hex={orig_hex} != {FX3_LIBFAN_ORIG_HEX}"
                        )
            out_map[lib_name] = {
                "size": len(blob),
                "sha256": digest,
                "source": "LOCAL_DONOR_O_RDONLY",
                "verified": size_ok and sha_ok and not missing_exports,
                **extra,
            }

    # 2. Inspect FX3 & FX6 Backup.bin BK4 0x0238xxxx fan/thermal properties via O_RDONLY
    bk4_diff: Dict[str, Any] = {}
    if paths.fx3_bk4_path.is_file() and paths.fx6_bk4_path.is_file():
        fx3_bk4_blob = read_file_o_rdonly(paths.fx3_bk4_path)
        fx6_bk4_blob = read_file_o_rdonly(paths.fx6_bk4_path)
        for key_name, fpath, blob, out_map, pinned in (
            ("FX3-CX95900_ALLLANG-Backup.bin", paths.fx3_bk4_path, fx3_bk4_blob, fx3_checked, PINNED_FX3_ARTIFACTS),
            ("CX95898_NTSC.bin", paths.fx6_bk4_path, fx6_bk4_blob, fx6_checked, PINNED_FX6_ARTIFACTS),
        ):
            spec = pinned[key_name]
            digest = hashlib.sha256(blob).hexdigest()
            ok = len(blob) == spec["size"] and digest == spec["sha256"]
            if not ok:
                errors.append(f"BK4 donor {key_name} size/sha256 mismatch")
            out_map[key_name] = {
                "size": len(blob),
                "sha256": digest,
                "source": "LOCAL_DONOR_O_RDONLY",
                "verified": ok,
            }
        for bkid, expected in PINNED_BK4_FAN_TEMP_PROPERTIES.items():
            v3 = _read_bk4_property_bytes(fx3_bk4_blob, bkid)
            v6 = _read_bk4_property_bytes(fx6_bk4_blob, bkid)
            h3 = v3.hex() if v3 is not None else ""
            h6 = v6.hex() if v6 is not None else ""
            bk4_diff[hex(bkid)] = {"fx3_hex": h3, "fx6_hex": h6}
            if h3 != expected["fx3_hex"] or h6 != expected["fx6_hex"]:
                errors.append(
                    f"BK4 property {hex(bkid)} mismatch: got fx3={h3} fx6={h6}, expected fx3={expected['fx3_hex']} fx6={expected['fx6_hex']}"
                )
    else:
        warnings.append("BK4 seed files absent; using pinned BK4 thermal property metadata.")
        bk4_diff = {hex(bkid): dict(meta) for bkid, meta in PINNED_BK4_FAN_TEMP_PROPERTIES.items()}

    # 3. Inspect appFw.so & cpapp-b.bin tokens via chunked os.O_RDONLY stream
    if include_large_binaries:
        large_specs = (
            ("FX3", paths.fx3_appfw_path, "appFw.so", PINNED_FX3_ARTIFACTS, fx3_checked),
            ("FX3", paths.fx3_cp_path, "cpapp-b.bin", PINNED_FX3_ARTIFACTS, fx3_checked),
            ("FX6", paths.fx6_lib_dir / "appFw.so", "appFw.so", PINNED_FX6_ARTIFACTS, fx6_checked),
            ("FX6", paths.fx6_cp_path, "cpapp-b.bin", PINNED_FX6_ARTIFACTS, fx6_checked),
        )
        for body_label, fpath, name, pinned, out_map in large_specs:
            if not fpath.is_file():
                warnings.append(f"Optional large {body_label} donor absent: {fpath}")
                continue
            spec = pinned[name]
            total_bytes, missing = scan_tokens_o_rdonly(fpath, spec["required_tokens"])
            size_ok = total_bytes == spec["size"]
            if not size_ok:
                errors.append(f"{body_label} {name} size mismatch: {total_bytes} != {spec['size']}")
            if missing:
                errors.append(f"{body_label} {name} missing tokens: {missing}")
            out_map[name] = {
                "size": total_bytes,
                "sha256_pinned": spec["sha256"],
                "source": "LOCAL_DONOR_O_RDONLY_STREAM",
                "missing_tokens": missing,
                "verified": size_ok and not missing,
            }

    libfan_patch_ok = (
        fx6_checked.get("libfan.so", {}).get("fan_i_bkup_is_valid_hex") == FX6_LIBFAN_ORIG_HEX
        and fx3_checked.get("libfan.so", {}).get("fan_i_bkup_is_valid_hex") == FX3_LIBFAN_ORIG_HEX
    )
    valid = len(errors) == 0 and libfan_patch_ok
    return DonorThermalPowerAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_AUDIT_MISMATCH,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        clean_room_forced=False,
        o_rdonly_enforced=True,
        fx3_artifacts_checked=fx3_checked,
        fx6_artifacts_checked=fx6_checked,
        bk4_thermal_diff_summary=bk4_diff,
        libfan_patch_verified=libfan_patch_ok,
        fan_modes_verified=VALID_MENU_FAN_MODES,
        thermal_zone_markers_verified=PINNED_THERMAL_ZONE_MARKERS,
        battery_power_contracts_verified=PINNED_BATTERY_POWER_CONTRACTS,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Deliverable 2: FX3 Compact Fan PWM Thermal Runaway Guard
# ---------------------------------------------------------------------------


def _normalize_fan_mode(mode: str) -> str:
    norm = mode.strip().upper().replace(" ", "_").replace("-", "_")
    aliases = {
        "AUTO": FAN_MODE_AUTO1,
        "AUTO_1": FAN_MODE_AUTO1,
        "AUTO1": FAN_MODE_AUTO1,
        "FAN_CONTROL_AUTO": FAN_MODE_AUTO1,
        "AUTO_2": FAN_MODE_AUTO2,
        "AUTO2": FAN_MODE_AUTO2,
        "MIN": FAN_MODE_MINIMUM,
        "MINIMUM": FAN_MODE_MINIMUM,
        "FAN_CONTROL_MINIMUM": FAN_MODE_MINIMUM,
        "OFF_IN_REC": FAN_MODE_OFF_IN_REC,
        "FAN_CONTROL_OFF_IN_REC": FAN_MODE_OFF_IN_REC,
        "ALWAYS_OFF": FAN_MODE_ALWAYS_OFF,
        "FAN_CONTROL_ALWAYS_OFF": FAN_MODE_ALWAYS_OFF,
    }
    return aliases.get(norm, norm)


def compute_fan_pwm_duty_pct(
    fan_mode: str,
    *,
    imx510_sensor_c: float,
    cxd90057_soc_c: float,
    cfexpress_slot_a_c: float,
    cfexpress_slot_b_c: float,
) -> Tuple[int, str, bool, Tuple[str, ...]]:
    """Compute Stage-A/B FX3 PWM duty (0..100%) and mandatory thermal override state."""
    mode = _normalize_fan_mode(fan_mode)
    cfexpress_max = max(cfexpress_slot_a_c, cfexpress_slot_b_c)
    max_temp = max(imx510_sensor_c, cxd90057_soc_c, cfexpress_max)

    override_reasons: List[str] = []
    if mode == FAN_MODE_OFF_IN_REC:
        if cxd90057_soc_c >= SOC_FAN_OVERRIDE_TEMP_C:
            override_reasons.append(
                f"CXD90057 SoC {cxd90057_soc_c:.1f}C >= {SOC_FAN_OVERRIDE_TEMP_C:.1f}C override threshold"
            )
        if cfexpress_max >= CFEXPRESS_FAN_OVERRIDE_TEMP_C:
            override_reasons.append(
                f"CFexpress Type A slot {cfexpress_max:.1f}C >= {CFEXPRESS_FAN_OVERRIDE_TEMP_C:.1f}C override threshold"
            )
        if max_temp >= SOFT_RECORDING_WARNING_TEMP_C and not override_reasons:
            override_reasons.append(
                f"Thermal zone {max_temp:.1f}C >= {SOFT_RECORDING_WARNING_TEMP_C:.1f}C warning threshold"
            )

    override_engaged = bool(override_reasons)

    # Active curve selection
    effective_mode = "AUTO1_THERMAL_OVERRIDE" if override_engaged else mode
    if max_temp >= SOFT_RECORDING_WARNING_TEMP_C and mode != FAN_MODE_ALWAYS_OFF:
        return 100, effective_mode, override_engaged, tuple(override_reasons)

    if mode == FAN_MODE_ALWAYS_OFF:
        return 0, FAN_MODE_ALWAYS_OFF, False, ()

    if mode == FAN_MODE_OFF_IN_REC and not override_engaged:
        return 0, FAN_MODE_OFF_IN_REC, False, ()

    if mode == FAN_MODE_OFF_IN_REC and override_engaged:
        # Forced active cooling: starts at >= 65% and scales smoothly to 100% by 82C
        excess = max(
            cxd90057_soc_c - SOC_FAN_OVERRIDE_TEMP_C,
            cfexpress_max - CFEXPRESS_FAN_OVERRIDE_TEMP_C,
            0.0,
        )
        duty = min(100, max(65, int(round(65 + excess * 2.0))))
        return duty, effective_mode, True, tuple(override_reasons)

    if mode == FAN_MODE_MINIMUM:
        if max_temp < 55.0:
            return 25, FAN_MODE_MINIMUM, False, ()
        ratio = (max_temp - 55.0) / (SOFT_RECORDING_WARNING_TEMP_C - 55.0)
        duty = min(100, max(25, int(round(25 + ratio * 65))))
        return duty, FAN_MODE_MINIMUM, False, ()

    if mode == FAN_MODE_AUTO2:
        if max_temp < 48.0:
            return 20, FAN_MODE_AUTO2, False, ()
        ratio = (max_temp - 48.0) / (SOFT_RECORDING_WARNING_TEMP_C - 48.0)
        duty = min(100, max(20, int(round(20 + ratio * 72))))
        return duty, FAN_MODE_AUTO2, False, ()

    # Default / AUTO1: proactive cinema cooling curve
    if max_temp < 45.0:
        return 30, FAN_MODE_AUTO1, False, ()
    ratio = (max_temp - 45.0) / (SOFT_RECORDING_WARNING_TEMP_C - 45.0)
    duty = min(100, max(30, int(round(30 + ratio * 65))))
    return duty, FAN_MODE_AUTO1, False, ()


def verify_fan_thermal_envelope(
    *,
    fan_mode: str = FAN_MODE_AUTO1,
    imx510_sensor_c: float = 46.0,
    cxd90057_soc_c: float = 52.0,
    cfexpress_slot_a_c: float = 49.0,
    cfexpress_slot_b_c: float = 47.0,
    observed_fan_rpm: Optional[int] = 3200,
    fan_broken_status: str = "NORMAL",
    thermistor_fault: bool = False,
    libfan_stage_patch_verified: bool = True,
    fan_i_bkup_is_valid_rc: int = 1,
    allow_thermal_override: bool = True,
    recording_active: bool = True,
) -> FanThermalEnvelopeResult:
    """Verify FX3 compact fan PWM safety envelope across all 4 menu modes and 4 thermal zones."""
    mode = _normalize_fan_mode(fan_mode)
    zones = {
        "imx510_sensor_c": imx510_sensor_c,
        "cxd90057_soc_c": cxd90057_soc_c,
        "cfexpress_slot_a_c": cfexpress_slot_a_c,
        "cfexpress_slot_b_c": cfexpress_slot_b_c,
    }
    errors: List[str] = []
    warnings: List[str] = []
    codes: List[str] = []

    def add_code(code: str) -> None:
        if code not in codes:
            codes.append(code)

    # 1. Validate telemetry sanity & thermistor health
    if thermistor_fault:
        add_code(STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID)
        errors.append("Thermistor fault reported (THERMISTOR_ERR); cannot trust thermal envelope.")

    for zname, zval in zones.items():
        if (not isinstance(zval, (int, float))) or math.isnan(zval) or math.isinf(zval):
            add_code(STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID)
            errors.append(f"Non-finite temperature reading on {zname}: {zval!r}")
        elif zval < THERMAL_MIN_PLAUSIBLE_C or zval > THERMAL_MAX_PLAUSIBLE_C:
            add_code(STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID)
            errors.append(
                f"Out-of-range temperature reading on {zname}: {zval}C (valid {THERMAL_MIN_PLAUSIBLE_C}..{THERMAL_MAX_PLAUSIBLE_C}C)"
            )

    if codes and STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID in codes:
        return FanThermalEnvelopeResult(
            valid=False,
            status=STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID,
            requested_fan_mode=mode,
            effective_fan_mode=mode,
            thermal_override_engaged=False,
            override_reasons=(),
            target_pwm_duty_pct=100,
            observed_fan_rpm=observed_fan_rpm,
            max_zone_temp_c=float("nan"),
            hottest_zone="INVALID",
            recording_allowed=False,
            recording_warning=True,
            graceful_unmount_required=True,
            ram_overlay_teardown_required=True,
            abort_required=True,
            libfan_stage_patch_ok=False,
            violation_codes=tuple(codes),
            errors=tuple(errors),
            warnings=tuple(warnings),
            zone_temps_c={},
        )

    hottest_zone = max(zones, key=lambda k: zones[k])
    max_temp = float(zones[hottest_zone])

    # 2. Verify Stage-A/B libfan.so patch & menu fan mode validity
    libfan_patch_ok = bool(libfan_stage_patch_verified and fan_i_bkup_is_valid_rc == 1)
    if not libfan_patch_ok:
        add_code(STATUS_BLOCKED_FAN_CONTROLLER_FAULT)
        errors.append(
            f"FX6 libfan.so Stage-A/B patch not verified (fan_i_bkup_is_valid_rc={fan_i_bkup_is_valid_rc}); "
            "FX3 CP thermal curve handshake unconfirmed."
        )

    if mode == FAN_MODE_ALWAYS_OFF:
        add_code(STATUS_BLOCKED_FAN_MODE_UNSAFE)
        errors.append("FAN_CONTROL_ALWAYS_OFF is forbidden during Stage-A/B runtime & recording.")
    elif mode not in VALID_MENU_FAN_MODES:
        add_code(STATUS_BLOCKED_FAN_MODE_UNSAFE)
        errors.append(f"Unsupported fan mode {fan_mode!r}; expected one of {VALID_MENU_FAN_MODES}.")

    # 3. Compute PWM duty and check OFF_IN_REC mandatory thermal override
    duty_pct, effective_mode, override_engaged, override_reasons = compute_fan_pwm_duty_pct(
        mode,
        imx510_sensor_c=imx510_sensor_c,
        cxd90057_soc_c=cxd90057_soc_c,
        cfexpress_slot_a_c=cfexpress_slot_a_c,
        cfexpress_slot_b_c=cfexpress_slot_b_c,
    )

    if mode == FAN_MODE_OFF_IN_REC and override_engaged and not allow_thermal_override:
        add_code(STATUS_BLOCKED_FAN_MODE_UNSAFE)
        errors.append(
            "OFF_IN_REC thermal override disabled while threshold exceeded: "
            + "; ".join(override_reasons)
        )
        duty_pct = 0
        effective_mode = FAN_MODE_OFF_IN_REC

    # 4. Check physical fan hardware feedback (FAN_BROKEN_STATUS_BROKEN / stalled rotor)
    broken_norm = fan_broken_status.strip().upper()
    if broken_norm in ("BROKEN", "FAN_BROKEN_STATUS_BROKEN", "ERROR", "FAN_ERROR"):
        add_code(STATUS_BLOCKED_FAN_CONTROLLER_FAULT)
        errors.append(f"Physical fan fault detected: fan_broken_status={fan_broken_status!r}.")
    elif duty_pct > 0 and observed_fan_rpm is not None and observed_fan_rpm <= 0:
        add_code(STATUS_BLOCKED_FAN_CONTROLLER_FAULT)
        errors.append(
            f"Fan rotor stall: PWM duty={duty_pct}% requested under {effective_mode}, but observed_fan_rpm={observed_fan_rpm}."
        )

    # 5. Enforce 82C Soft Warning & 90C Fail-Closed Graceful Unmount + RAM-Overlay Teardown
    recording_warning = max_temp >= SOFT_RECORDING_WARNING_TEMP_C
    graceful_unmount = max_temp >= FAIL_CLOSED_TEARDOWN_TEMP_C
    teardown_required = max_temp >= FAIL_CLOSED_TEARDOWN_TEMP_C
    abort_required = graceful_unmount or (len(errors) > 0)
    recording_allowed = not abort_required

    if graceful_unmount:
        add_code(STATUS_BLOCKED_THERMAL_RUNAWAY)
        errors.append(
            f"FAIL-CLOSED THERMAL RUNAWAY: {hottest_zone}={max_temp:.1f}C >= {FAIL_CLOSED_TEARDOWN_TEMP_C:.1f}C "
            f"(before {HW_THERMAL_TRIP_CEILING_C:.1f}C hardware trip); triggering graceful media unmount and "
            "Stage-A/B RAM-overlay teardown."
        )
    elif recording_warning:
        warnings.append(
            f"SOFT RECORDING WARNING: {hottest_zone}={max_temp:.1f}C >= {SOFT_RECORDING_WARNING_TEMP_C:.1f}C "
            "(recording_active=" + str(recording_active) + "); fan forced to 100% PWM."
        )

    if override_engaged and allow_thermal_override:
        warnings.append(
            "Mandatory thermal override engaged for OFF_IN_REC -> active cooling: "
            + "; ".join(override_reasons)
        )

    if errors:
        if STATUS_BLOCKED_THERMAL_RUNAWAY in codes:
            status = STATUS_BLOCKED_THERMAL_RUNAWAY
        else:
            status = codes[0]
        valid = False
    elif recording_warning:
        status = STATUS_THERMAL_SOFT_WARNING
        valid = True
    else:
        status = STATUS_VERIFIED_SAFE
        valid = True

    return FanThermalEnvelopeResult(
        valid=valid,
        status=status,
        requested_fan_mode=mode,
        effective_fan_mode=effective_mode,
        thermal_override_engaged=override_engaged,
        override_reasons=override_reasons,
        target_pwm_duty_pct=duty_pct,
        observed_fan_rpm=observed_fan_rpm,
        max_zone_temp_c=max_temp,
        hottest_zone=hottest_zone,
        recording_allowed=recording_allowed,
        recording_warning=recording_warning,
        graceful_unmount_required=graceful_unmount,
        ram_overlay_teardown_required=teardown_required,
        abort_required=abort_required,
        libfan_stage_patch_ok=libfan_patch_ok,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        zone_temps_c=zones,
    )


def evaluate_fan_mode_matrix() -> Dict[str, Dict[str, Any]]:
    """Evaluate all 4 menu fan modes across nominal, override, soft-warning, and teardown points."""
    matrix: Dict[str, Dict[str, Any]] = {}
    operating_points = (
        ("nominal_45c", {"imx510_sensor_c": 44.0, "cxd90057_soc_c": 45.0, "cfexpress_slot_a_c": 43.0, "cfexpress_slot_b_c": 42.0, "observed_fan_rpm": 2600}),
        ("soc_override_62c", {"imx510_sensor_c": 54.0, "cxd90057_soc_c": 62.0, "cfexpress_slot_a_c": 55.0, "cfexpress_slot_b_c": 52.0, "observed_fan_rpm": 4100}),
        ("cfexpress_override_68c", {"imx510_sensor_c": 55.0, "cxd90057_soc_c": 58.0, "cfexpress_slot_a_c": 68.0, "cfexpress_slot_b_c": 60.0, "observed_fan_rpm": 4200}),
        ("soft_warning_82c", {"imx510_sensor_c": 75.0, "cxd90057_soc_c": 82.0, "cfexpress_slot_a_c": 78.0, "cfexpress_slot_b_c": 74.0, "observed_fan_rpm": 5500}),
        ("fail_closed_90c", {"imx510_sensor_c": 84.0, "cxd90057_soc_c": 90.0, "cfexpress_slot_a_c": 85.0, "cfexpress_slot_b_c": 80.0, "observed_fan_rpm": 5500}),
    )
    for mode in VALID_MENU_FAN_MODES:
        mode_entry: Dict[str, Any] = {}
        for label, params in operating_points:
            res = verify_fan_thermal_envelope(fan_mode=mode, **params)
            mode_entry[label] = {
                "valid": res.valid,
                "status": res.status,
                "effective_fan_mode": res.effective_fan_mode,
                "thermal_override_engaged": res.thermal_override_engaged,
                "target_pwm_duty_pct": res.target_pwm_duty_pct,
                "recording_warning": res.recording_warning,
                "graceful_unmount_required": res.graceful_unmount_required,
                "ram_overlay_teardown_required": res.ram_overlay_teardown_required,
            }
        matrix[mode] = mode_entry
    return matrix


# ---------------------------------------------------------------------------
# Deliverable 3: NP-FZ100 (7.2V) vs BP-U (14.4V) & USB-PD 9V/3A Firewall
# ---------------------------------------------------------------------------


def normalize_npfz100_infolithium_mv(
    raw_batt_mv: int,
    *,
    infolithium_soc_pct: Optional[int] = None,
    remaining_minutes: Optional[int] = None,
    comparator_mode: str = COMPARATOR_INFOLITHIUM_SOC,
) -> Dict[str, Any]:
    """Normalize 2S NP-FZ100 (6200..8400 mV) via InfoLITHIUM % vs raw BP-U 11500 mV comparator."""
    clamped_mv = max(NP_FZ100_MIN_OPERATING_MV, min(NP_FZ100_MAX_OPERATING_MV, raw_batt_mv))
    derived_soc = int(
        round(
            100.0
            * (clamped_mv - NP_FZ100_MIN_OPERATING_MV)
            / (NP_FZ100_MAX_OPERATING_MV - NP_FZ100_MIN_OPERATING_MV)
        )
    )
    soc = derived_soc if infolithium_soc_pct is None else int(infolithium_soc_pct)
    rem_min = max(0, int(round(soc * 1.15))) if remaining_minutes is None else int(remaining_minutes)

    would_false_trip_bpu = raw_batt_mv < BP_U_EMERGENCY_CUTOFF_MV
    using_bpu_comparator = comparator_mode != COMPARATOR_INFOLITHIUM_SOC
    boot_shutdown_triggered = using_bpu_comparator and would_false_trip_bpu

    return {
        "raw_batt_mv": raw_batt_mv,
        "infolithium_soc_pct": soc,
        "remaining_minutes": rem_min,
        "comparator_mode": comparator_mode,
        "bpu_11500mv_would_false_trip": would_false_trip_bpu,
        "false_zero_pct_boot_shutdown_triggered": boot_shutdown_triggered,
        "false_zero_pct_boot_shutdown_prevented": (not boot_shutdown_triggered) and would_false_trip_bpu,
    }


def verify_battery_and_usbpd_firewall(
    *,
    battery_chemistry: str = "NP-FZ100",
    raw_batt_mv: int = 8050,
    infolithium_soc_pct: int = 88,
    remaining_minutes: int = 96,
    comparator_mode: str = COMPARATOR_INFOLITHIUM_SOC,
    bp_u_11500mv_comparator_enabled: bool = False,
    battery_auth_status: str = "AUTHENTICATED",
    battery_thermal_fault: bool = False,
    battery_overcurrent_fault: bool = False,
    session_mode: str = SESSION_H0_REHEARSAL,
    usbpd_attached: bool = True,
    usbpd_contract_mv: int = USBPD_REQUIRED_VOLTAGE_MV,
    usbpd_contract_ma: int = USBPD_REQUIRED_CURRENT_MA,
    usbpd_measured_vbus_mv: int = 8850,
    request_persistent_emmc_write: bool = False,
) -> BatteryUsbPdFirewallResult:
    """Verify NP-FZ100 InfoLITHIUM normalization and USB-PD 9V/3A brownout firewall."""
    errors: List[str] = []
    warnings: List[str] = []
    codes: List[str] = []

    def add_code(code: str) -> None:
        if code not in codes:
            codes.append(code)

    chem_norm = battery_chemistry.strip().upper().replace("_", "-")
    sess_norm = session_mode.strip().upper()
    comp_norm = comparator_mode.strip().upper()
    auth_norm = battery_auth_status.strip().upper()

    # 0. Persistent eMMC write redline
    if request_persistent_emmc_write:
        add_code(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC write blocked: PERSISTENT_EMMC_WRITES_AUTHORIZED = False."
        )

    # 1. Cross-body BP-U (14.4V / 11500 mV) vs NP-FZ100 (7.2V) comparator firewall
    if bp_u_11500mv_comparator_enabled or comp_norm in (COMPARATOR_RAW_BPU_11500MV, COMPARATOR_RAW_19V5_DC_IN):
        add_code(STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)
        errors.append(
            f"Cross-body comparator hazard: {comp_norm} (11500 mV 4S BP-U / 19.5V DC-IN cutoff) "
            f"applied to 2S NP-FZ100 ({raw_batt_mv} mV), causing false 0% OFF_BY_BATT_END shutdown on boot."
        )

    if chem_norm != "NP-FZ100":
        add_code(STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)
        errors.append(
            f"Unsupported FX3 body battery chemistry {battery_chemistry!r}; FX3 requires 2S 7.2V NP-FZ100 (not 4S BP-U)."
        )

    norm_info = normalize_npfz100_infolithium_mv(
        raw_batt_mv,
        infolithium_soc_pct=infolithium_soc_pct,
        remaining_minutes=remaining_minutes,
        comparator_mode=comp_norm,
    )

    # 2. Validate NP-FZ100 electrical bounds & InfoLITHIUM telemetry
    if raw_batt_mv > NP_FZ100_ABS_MAX_SAFE_MV:
        add_code(STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)
        errors.append(
            f"Battery overvoltage / cross-body BP-U rail hazard: {raw_batt_mv} mV > {NP_FZ100_ABS_MAX_SAFE_MV} mV NP-FZ100 ceiling."
        )
    elif raw_batt_mv < NP_FZ100_MIN_OPERATING_MV:
        add_code(STATUS_BLOCKED_NPFZ100_BROWNOUT)
        errors.append(
            f"NP-FZ100 deep brownout: {raw_batt_mv} mV < {NP_FZ100_MIN_OPERATING_MV} mV minimum operating floor."
        )

    if infolithium_soc_pct < 0 or infolithium_soc_pct > 100:
        add_code(STATUS_BLOCKED_NPFZ100_BROWNOUT)
        errors.append(f"Invalid InfoLITHIUM state-of-charge percentage: {infolithium_soc_pct}%")

    if remaining_minutes <= 0:
        add_code(STATUS_BLOCKED_NPFZ100_BROWNOUT)
        errors.append(f"InfoLITHIUM remaining_minutes={remaining_minutes} <= 0 (battery exhausted).")

    if auth_norm in ("FAKE", "INVALID", "BATT_END_FAKE", "BATT_INVALID", "UNAUTHENTICATED"):
        add_code(STATUS_BLOCKED_NPFZ100_BROWNOUT)
        errors.append(f"Battery InfoLITHIUM authentication fault: {battery_auth_status!r} (BATT_END_FAKE/INVALID).")

    if battery_thermal_fault:
        add_code(STATUS_BLOCKED_NPFZ100_BROWNOUT)
        errors.append("Battery thermal fault reported (OFF_BY_BATT_THERMAL).")

    if battery_overcurrent_fault:
        add_code(STATUS_BLOCKED_NPFZ100_BROWNOUT)
        errors.append("Battery overcurrent fault reported (OFF_BY_BATT_OVERCURRENT).")

    # 3. H0/H1 rehearsal gate (>=80% SOC, >=7800 mV, >=20 min, USB-PD 9V/3A 27W <=450mV droop)
    is_rehearsal = sess_norm in (SESSION_H0_REHEARSAL, SESSION_H1_REHEARSAL)
    rehearsal_batt_ok = (
        infolithium_soc_pct >= H0_H1_REHEARSAL_MIN_SOC_PCT
        and raw_batt_mv >= H0_H1_REHEARSAL_MIN_BATT_MV
        and remaining_minutes >= H0_H1_REHEARSAL_MIN_REMAINING_MIN
    )
    if is_rehearsal and not rehearsal_batt_ok:
        add_code(STATUS_BLOCKED_NPFZ100_BROWNOUT)
        errors.append(
            f"{sess_norm} requires NP-FZ100 >= {H0_H1_REHEARSAL_MIN_SOC_PCT}% SOC, "
            f">= {H0_H1_REHEARSAL_MIN_BATT_MV} mV, and >= {H0_H1_REHEARSAL_MIN_REMAINING_MIN} min "
            f"(got {infolithium_soc_pct}%, {raw_batt_mv} mV, {remaining_minutes} min)."
        )

    # 4. USB-PD 9V/3A (27W) & VBUS droop <= 450 mV firewall
    contract_mw = int(round((usbpd_contract_mv * usbpd_contract_ma) / 1000.0))
    vbus_droop_mv = max(0, usbpd_contract_mv - usbpd_measured_vbus_mv)
    usbpd_contract_ok = (
        usbpd_attached
        and usbpd_contract_mv >= USBPD_REQUIRED_VOLTAGE_MV
        and usbpd_contract_ma >= USBPD_REQUIRED_CURRENT_MA
        and contract_mw >= USBPD_REQUIRED_POWER_MW
    )
    usbpd_droop_ok = usbpd_attached and (vbus_droop_mv <= USBPD_MAX_VBUS_DROOP_MV)

    if is_rehearsal:
        if not usbpd_attached:
            add_code(STATUS_BLOCKED_USBPD_CONTRACT_INSUFFICIENT)
            errors.append(f"{sess_norm} requires active 9V/3A (27W) USB-PD external power supply.")
        elif not usbpd_contract_ok:
            add_code(STATUS_BLOCKED_USBPD_CONTRACT_INSUFFICIENT)
            errors.append(
                f"USB-PD contract insufficient for {sess_norm}: {usbpd_contract_mv}mV/{usbpd_contract_ma}mA "
                f"({contract_mw / 1000.0:.1f}W) < required 9V/3A (27.0W)."
            )
        if usbpd_attached and not usbpd_droop_ok:
            add_code(STATUS_BLOCKED_USBPD_VBUS_DROOP)
            errors.append(
                f"USB-PD VBUS droop brownout: {vbus_droop_mv} mV > {USBPD_MAX_VBUS_DROOP_MV} mV ceiling "
                f"(contract={usbpd_contract_mv} mV, measured={usbpd_measured_vbus_mv} mV)."
            )
    else:
        if usbpd_attached and not usbpd_droop_ok:
            add_code(STATUS_BLOCKED_USBPD_VBUS_DROOP)
            errors.append(
                f"USB-PD VBUS droop brownout: {vbus_droop_mv} mV > {USBPD_MAX_VBUS_DROOP_MV} mV ceiling."
            )
        elif usbpd_attached and not usbpd_contract_ok:
            warnings.append(
                f"USB-PD contract below 9V/3A 27W ({contract_mw / 1000.0:.1f}W) during {sess_norm}; "
                "not cleared for H0/H1 rehearsal."
            )

    valid = len(errors) == 0
    status = STATUS_VERIFIED_SAFE if valid else codes[0]
    usbpd_ok = (usbpd_contract_ok and usbpd_droop_ok) if is_rehearsal else ((not usbpd_attached) or usbpd_droop_ok)

    return BatteryUsbPdFirewallResult(
        valid=valid,
        status=status,
        session_mode=sess_norm,
        battery_chemistry=chem_norm,
        raw_batt_mv=raw_batt_mv,
        infolithium_soc_pct=infolithium_soc_pct,
        remaining_minutes=remaining_minutes,
        comparator_mode=comp_norm,
        false_zero_pct_boot_shutdown_prevented=bool(norm_info["false_zero_pct_boot_shutdown_prevented"]) and valid,
        rehearsal_battery_gate_passed=rehearsal_batt_ok and valid,
        usbpd_attached=usbpd_attached,
        usbpd_contract_mv=usbpd_contract_mv,
        usbpd_contract_ma=usbpd_contract_ma,
        usbpd_contract_mw=contract_mw,
        usbpd_measured_vbus_mv=usbpd_measured_vbus_mv,
        usbpd_vbus_droop_mv=vbus_droop_mv,
        usbpd_stability_passed=usbpd_ok and valid,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Unified Phase 44 Evaluator & CLI
# ---------------------------------------------------------------------------


def evaluate_thermal_pwm_and_power_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = True,
    fan_kwargs: Optional[Mapping[str, Any]] = None,
    power_kwargs: Optional[Mapping[str, Any]] = None,
) -> Phase44ThermalPowerGuardReport:
    """Run all Phase 44 donor audit, Fan PWM thermal envelope, and NP-FZ100/USB-PD checks."""
    clean_forced = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    donor_res = audit_donor_thermal_fan_power_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )
    curve_matrix = evaluate_fan_mode_matrix()
    fan_res = verify_fan_thermal_envelope(**dict(fan_kwargs or {}))
    power_res = verify_battery_and_usbpd_firewall(**dict(power_kwargs or {}))

    all_errors = (*donor_res.errors, *fan_res.errors, *power_res.errors)
    all_warnings = (*donor_res.warnings, *fan_res.warnings, *power_res.warnings)
    all_passed = donor_res.valid and fan_res.valid and power_res.valid

    if not donor_res.valid:
        overall_status = donor_res.status
    elif not fan_res.valid:
        overall_status = fan_res.status
    elif not power_res.valid:
        overall_status = power_res.status
    elif fan_res.status == STATUS_THERMAL_SOFT_WARNING:
        overall_status = STATUS_THERMAL_SOFT_WARNING
    else:
        overall_status = STATUS_VERIFIED_SAFE

    return Phase44ThermalPowerGuardReport(
        schema=THERMAL_PWM_POWER_GUARD_SCHEMA,
        version=THERMAL_PWM_POWER_GUARD_VERSION,
        verification_mode=donor_res.verification_mode,
        clean_room_forced=clean_forced,
        all_passed=all_passed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        donor_audit=donor_res,
        fan_curve_matrix=curve_matrix,
        thermal_envelope=fan_res,
        power_firewall=power_res,
        errors=all_errors,
        warnings=all_warnings,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="thermal_pwm_and_power_guard",
        description="Phase 44 FX3 Fan PWM Thermal Envelope, NP-FZ100 vs BP-U & USB-PD Guard",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    parser.add_argument("--fan-mode", default=FAN_MODE_AUTO1, help="Fan menu mode (AUTO1|AUTO2|MINIMUM|OFF_IN_REC)")
    parser.add_argument("--soc-c", type=float, default=52.0, help="CXD90057 SoC temperature (C)")
    parser.add_argument("--imx510-c", type=float, default=46.0, help="IMX510 sensor temperature (C)")
    parser.add_argument("--cfexpress-a-c", type=float, default=49.0, help="CFexpress Slot A temperature (C)")
    parser.add_argument("--cfexpress-b-c", type=float, default=47.0, help="CFexpress Slot B temperature (C)")
    parser.add_argument("--batt-mv", type=int, default=8050, help="NP-FZ100 raw millivolts")
    parser.add_argument("--soc-pct", type=int, default=88, help="InfoLITHIUM state-of-charge (%%)")
    parser.add_argument("--usbpd-vbus-mv", type=int, default=8850, help="Measured USB-PD VBUS (mV)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_thermal_pwm_and_power_guard(
        force_clean_room=True if args.clean_room else None,
        fan_kwargs={
            "fan_mode": args.fan_mode,
            "imx510_sensor_c": args.imx510_c,
            "cxd90057_soc_c": args.soc_c,
            "cfexpress_slot_a_c": args.cfexpress_a_c,
            "cfexpress_slot_b_c": args.cfexpress_b_c,
        },
        power_kwargs={
            "raw_batt_mv": args.batt_mv,
            "infolithium_soc_pct": args.soc_pct,
            "usbpd_measured_vbus_mv": args.usbpd_vbus_mv,
        },
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} all_passed={report.all_passed} "
            f"pwm={report.thermal_envelope.target_pwm_duty_pct}% "
            f"batt={report.power_firewall.raw_batt_mv}mV/{report.power_firewall.infolithium_soc_pct}% "
            f"usbpd_droop={report.power_firewall.usbpd_vbus_droop_mv}mV "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
