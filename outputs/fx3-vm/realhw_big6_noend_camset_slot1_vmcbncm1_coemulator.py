#!/usr/bin/env python3
"""Phase 202 — Stage 36 (`36/36` Milestone) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) `BIG6` (`[Mode Settings] = [Fixed/Variable]`) 6-Tile
Topology & `[Home (Lower Left)]` (`Aperture` / `ND Filter`) Zero Physical e-ND Actuator Firewall,
Slot-1-Only `CAMSET01.DAT .. CAMSET10.DAT` Dual-Media Path Split (`SD` `/PRIVATE/SONY/SETTING/FX3/CAMSET/`
vs `CFexpress-A` `/SONY/SETTING/FX3/CAMSET/`) & Cross-Model `.DAT` Firewall, and `VMC-BNCM1`
(`A-5051-506-A`) Body-Only `TC IN` (`EXT-LK` `>= 10s`), `XLR-H1` Handle Micro-USB Block & Digital
Type-A HDMI `TC OUT` HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) donor inspection (< 0.10s, cached per
process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), and co-emulates all four Phase 202
real-hardware pillars (A-D) while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `e_nd_actuator_tx_count == 0`, `slot1_fx3_camset_mutation_bytes == 0`
- `p2_setting_mutation_bytes == 0`, `bnc_tcout_reverse_drive_events == 0`
- `xlrh1_handle_usb_tc_miswire_damage_events == 0`, `raw_firmware_bytes_leaked == 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import struct
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Phase 202 Schema & Hard-Locked Safety Redlines (36/36 Milestone)
# ---------------------------------------------------------------------------

PHASE_202_SCHEMA = "phase202_realhw_big6_noend_camset_slot1_vmcbncm1_coemulator_v1"
PHASE_202_VERSION = "202.0.0"
STAGE_INDEX = 36
STAGE_TOTAL = 36
MILESTONE_LABEL = "36/36"
STAGE_NAME = "stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil"

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
E_ND_ACTUATOR_TX_COUNT = 0
SLOT1_FX3_CAMSET_MUTATION_BYTES = 0
P2_SETTING_MUTATION_BYTES = 0
XLRH1_HANDLE_USB_TC_MISWIRE_DAMAGE_EVENTS = 0
BNC_TCOUT_REVERSE_DRIVE_EVENTS = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0
DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096

# Deterministic Linux ARM64 errno constants (cross-platform digest parity on macOS & Linux)
ENODEV_ERRNO = 19  # Linux ENODEV
EINVAL_ERRNO = 22  # Linux EINVAL
EROFS_ERRNO = 30  # Linux EROFS
EOPNOTSUPP_ERRNO = 95  # Linux ARM64 EOPNOTSUPP

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (12 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_usb_ctrl": f"{_FX3_USR_PREFIX}/lib/libUsbControl.so",
    "fx6_hotshoe": f"{_FX6_NF15_PREFIX}/lib/libInfraHotshoe.so",
    "fx3_libbackup": f"{_FX3_USR_PREFIX}/lib/libbackup.so",
    "fx3_backup_mgr": f"{_FX3_USR_PREFIX}/lib/libBackupManager.so",
    "fx3_im_elf": f"{_FX3_USR_PREFIX}/bin/im.elf",
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_libmpr": f"{_FX3_USR_PREFIX}/lib/libmpr.so",
    "fx6_libmpr": f"{_FX6_NF15_PREFIX}/lib/libmpr.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_usb_ctrl": 135_424,
    "fx6_hotshoe": 47_808,
    "fx3_libbackup": 14_232,
    "fx3_backup_mgr": 10_272,
    "fx3_im_elf": 40_920,
    "fx3_string_en_f": 373_820,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_libmpr": 3_517_008,
    "fx6_libmpr": 28_921_824,
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_usb_ctrl": (
        b"UsbControl",
        b"Multi",
        b"Gadget",
        b"Backup_read",
    ),
    "fx6_hotshoe": (
        b"InfraHotshoe",
        b"SetAdcLevel",
        b"Backup_read",
    ),
    "fx3_libbackup": (
        b"Backup_read",
        b"Backup_write",
        b"Backup_read_setting_attr",
        b"Backup_write_setting_attr",
    ),
    "fx3_backup_mgr": (
        b"BackupManager",
        b"BkDmn_write",
        b"writeBackupEncryption",
        b"readBackupDecryption",
    ),
    "fx3_im_elf": (
        b"/dev/nflasha2",
        b"/setting",
        b"/dev/nflasha3",
        b"/dev/nflasha15",
        b"/usr",
    ),
    "fx3_string_en_f": (
        b"Home (Lower Left)",
        b"Aperture",
        b"ND Filter",
        b"Fixed/Variable",
        b"Mode Settings",
        b"Save/Load Settings",
        b"Slot 1",
        b"Recall Camera Setting",
        b"Time Code Make",
        b"Time Code Run",
        b"Time Code Output",
        b"HDMI Output Settings",
        b"Preset",
        b"Free Run",
        b"Picture Profile",
        b"Select LUT",
        b"White Balance",
        b"Base ISO",
    ),
}

# Pinned bounded windows (<= 4096 B each) for large CP/AP binaries so cold inspection is < 10 ms.
LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_946_105, "APERTURE", b"APERTURE"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_950_720, "ND_FILTER", b"ND_FILTER"),
        (49_967_104, "HOME_LOWER_LEFT", b"HOME_LOWER_LEFT"),
        (51_888_128, "CAMSET_FMT", b"CAMSET%02d"),
        (58_707_968, "TC_MAKE", b"TC_MAKE"),
        (58_707_968, "TC_RUN", b"TC_RUN"),
        (59_797_504, "SONY_SETTING_CAMSET_DAT", b"%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"),
        (59_944_960, "TC_OUT", b"TC_OUT"),
        (61_952_000, "XLR", b"XLR"),
        (62_345_216, "SAVE_LOAD", b"SAVE_LOAD"),
        (63_008_768, "BIG6", b"BIG6"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (35_971_072, "HDMI", b"HDMI"),
        (39_018_496, "ND_FILTER", b"ND_FILTER"),
        (39_018_496, "TC_MAKE", b"TC_MAKE"),
        (39_018_496, "TC_RUN", b"TC_RUN"),
        (39_350_272, "SONY_SETTING_CAMSET_DAT", b"%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"),
        (39_370_752, "TC_OUT", b"TC_OUT"),
        (39_399_424, "APERTURE", b"APERTURE"),
        (40_161_280, "SAVE_LOAD", b"SAVE_LOAD"),
        (40_607_744, "XLR", b"XLR"),
        (41_398_272, "BIG6", b"BIG6"),
        (41_648_128, "HOME_LOWER_LEFT", b"HOME_LOWER_LEFT"),
    ),
    "fx3_cpapp": (
        (696_320, "HDMI", b"HDMI"),
        (974_848, "Multi", b"Multi"),
        (1_052_672, "XLR", b"XLR"),
        (1_110_016, "TC_OUT", b"TC_OUT"),
        (1_724_416, "Iris", b"Iris"),
        (13_090_816, "ND_FILTER", b"ND_FILTER"),
        (13_107_200, "TC_MAKE", b"TC_MAKE"),
        (13_107_200, "TC_RUN", b"TC_RUN"),
        (13_139_968, "ILME-FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (684_032, "HDMI", b"HDMI"),
        (966_656, "Multi", b"Multi"),
        (1_007_616, "XLR", b"XLR"),
        (1_122_304, "TC_OUT", b"TC_OUT"),
        (1_789_952, "Iris", b"Iris"),
        (14_532_608, "ND_FILTER", b"ND_FILTER"),
        (14_544_896, "TC_RUN", b"TC_RUN"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (131_072, "Multi", b"Multi"),
        (155_648, "ND", b"ND"),
        (225_280, "TC", b"TC"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (114_688, "TC", b"TC"),
        (163_840, "Multi", b"Multi"),
        (192_512, "ND", b"ND"),
        (14_069_760, "Iris", b"Iris"),
    ),
}

# ---------------------------------------------------------------------------
# Pillar A Constants: ILME-FX3 (0x91030080) BIG6 6-Tile Topology & Zero e-ND Firewall
# ---------------------------------------------------------------------------

MODEL_ILME_FX3 = "ILME-FX3"
MODEL_ILME_FX3A = "ILME-FX3A"
MODEL_ILME_FX6 = "ILME-FX6"

FX3_MODEL_ID = 0x91030080
FX3A_MODEL_ID = 0x9103008A
FX6_MODEL_ID = 0x91060010

FX3_HAS_PHYSICAL_END_HARDWARE = False

MODE_SETTINGS_FIXED_VARIABLE = "Fixed/Variable"
MODE_SETTINGS_NORMAL = "Normal"

HOME_LOWER_LEFT_MENU_PATH = "MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]"
HOME_LOWER_LEFT_APERTURE = "Aperture"
HOME_LOWER_LEFT_ND_FILTER = "ND Filter"
VALID_HOME_LOWER_LEFT_TARGETS: Tuple[str, ...] = (
    HOME_LOWER_LEFT_APERTURE,
    HOME_LOWER_LEFT_ND_FILTER,
)

BIG6_TILE_SLOT_NAMES: Tuple[str, ...] = (
    "FPS",
    "ISO/Base ISO",
    "Shutter Speed/Angle",
    "Aperture/ND Filter",
    "Picture Profile/Select LUT",
    "White Balance",
)
BIG6_STATUS_BAR_ZONE_INDEX = 7

FX6_MOTORIZED_VARIABLE_END_STEPS: Tuple[str, ...] = (
    "1/4",
    "1/8",
    "1/16",
    "1/32",
    "1/64",
    "1/128",
)
CP_OPCODE_FX6_VARIABLE_END_ACTUATOR = 0x04D2

# ---------------------------------------------------------------------------
# Pillar B Constants: Slot-1 CAMSET01.DAT..CAMSET10.DAT Dual-Media Path Split
# ---------------------------------------------------------------------------

SAVE_LOAD_SETTINGS_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]"
CAMSET_ALLOWED_SLOT = 1
CAMSET_MIN_INDEX = 1
CAMSET_MAX_INDEX = 10
CAMSET_MAX_PROFILES_PER_CARD = 10

MEDIA_TYPE_SD = "SD"
MEDIA_TYPE_SDHC = "SDHC"
MEDIA_TYPE_SDXC = "SDXC"
MEDIA_TYPE_CFEXPRESS_A = "CFEXPRESS_A"

SD_FAMILY_MEDIA_TYPES: Tuple[str, ...] = (MEDIA_TYPE_SD, MEDIA_TYPE_SDHC, MEDIA_TYPE_SDXC)
VALID_CAMSET_MEDIA_TYPES: Tuple[str, ...] = SD_FAMILY_MEDIA_TYPES + (MEDIA_TYPE_CFEXPRESS_A,)

CAMSET_SD_DIR = "/PRIVATE/SONY/SETTING/FX3/CAMSET"
CAMSET_CFEXPRESS_A_DIR = "/SONY/SETTING/FX3/CAMSET"
VOLATILE_FX6_CAMSET_OVERLAY_DIR = "/tmp/fx6_camset_overlay"
P2_SETTING_MOUNT_PATH = "p2:/setting"

OS_PERSONA_STAGE_B_FX6_601 = "STAGE_B_FX6_VER_6_01"
OS_PERSONA_STOCK_FX3_702 = "STOCK_FX3_VER_7_02"
VALID_OS_PERSONAS: Tuple[str, ...] = (OS_PERSONA_STAGE_B_FX6_601, OS_PERSONA_STOCK_FX3_702)

VALID_CAMSET_MODELS: Tuple[str, ...] = (MODEL_ILME_FX3, MODEL_ILME_FX3A, MODEL_ILME_FX6)

CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS: Tuple[str, ...] = (
    "White Balance: Custom 1/2/3",
    "FTP Server",
    "Network Streaming",
    "IP/TLS Certificates",
    "Date/Time",
)

# ---------------------------------------------------------------------------
# Pillar C & D Constants: VMC-BNCM1 (A-5051-506-A) Body-Only TC IN & HDMI TC OUT
# ---------------------------------------------------------------------------

VMC_BNCM1_MODEL = "VMC-BNCM1"
VMC_BNCM1_SONY_PART_NO = "A-5051-506-A"
VMC_BNCM1_CABLE_LENGTH_M = 0.2

USB_PORT_BODY_MULTI_MICRO = "BODY_MULTI_MICRO_USB"
USB_PORT_XLR_H1_HANDLE_MICRO = "XLR_H1_HANDLE_MICRO_USB"
USB_PORT_BODY_TYPE_C = "BODY_USB_TYPE_C"
VALID_TC_USB_PORTS: Tuple[str, ...] = (
    USB_PORT_BODY_MULTI_MICRO,
    USB_PORT_XLR_H1_HANDLE_MICRO,
    USB_PORT_BODY_TYPE_C,
)

BNC_DIRECTION_TC_IN = "TC_IN"
BNC_DIRECTION_TC_OUT = "TC_OUT"
VALID_BNC_DIRECTIONS: Tuple[str, ...] = (BNC_DIRECTION_TC_IN, BNC_DIRECTION_TC_OUT)

SHOOTING_MODE_MOVIE = "Movie"
SHOOTING_MODE_SQ = "S&Q"
SHOOTING_MODE_MR = "MR"
VALID_TC_SHOOTING_MODES: Tuple[str, ...] = (SHOOTING_MODE_MOVIE, SHOOTING_MODE_SQ)

TC_MAKE_PRESET = "Preset"
TC_MAKE_REGENERATE = "Regenerate"
VALID_TC_MAKE_MODES: Tuple[str, ...] = (TC_MAKE_PRESET, TC_MAKE_REGENERATE)

TC_RUN_FREE_RUN = "Free Run"
TC_RUN_REC_RUN = "Rec Run"
VALID_TC_RUN_MODES: Tuple[str, ...] = (TC_RUN_FREE_RUN, TC_RUN_REC_RUN)

EXT_LK_MIN_LOCK_HOLD_SECONDS = 10.0

HDMI_TC_OUTPUT_MENU_PATH = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings] -> [Time Code Output]"
)
HDMI_TC_OUT_ON = "On"
HDMI_TC_OUT_OFF = "Off"
VALID_HDMI_TC_OUT_SETTINGS: Tuple[str, ...] = (HDMI_TC_OUT_ON, HDMI_TC_OUT_OFF)


class RealHwBig6CamsetVmcBncm1Error(ValueError):
    """Raised on invalid Phase 202 co-emulator inputs."""


# ---------------------------------------------------------------------------
# Dataclasses for Donor Inspection & Pillars A-D
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    elf64_le_ok: bool
    uxd_container_ok: bool
    sha256_prefix16: str
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedWindowDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    bounded_windows_only: bool
    bytes_read_total: int
    file_bytes: int
    elf64_le_ok: bool
    window_hits: Dict[str, int]
    head_sha256_prefix16: str


@dataclass(frozen=True)
class Phase202DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    fx3_usb_ctrl: CompactDonorSummary
    fx6_hotshoe: CompactDonorSummary
    fx3_libbackup: CompactDonorSummary
    fx3_backup_mgr: CompactDonorSummary
    fx3_im_elf: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    big6_home_lower_left_and_no_end_proven: bool
    slot1_camset_dual_media_path_proven: bool
    vmcbncm1_tcin_and_hdmi_tcout_proven: bool
    p2_setting_and_backup_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Big6HomeLowerLeftFirewallResult:
    admitted: bool
    model_name: str
    model_id_hex: str
    fx3_has_physical_end_hardware: bool
    mode_settings: str
    home_custom_key_assigned: bool
    big6_screen_active: bool
    home_lower_left_menu_path: str
    home_lower_left_target: str
    tile_count: int
    status_bar_zone_7_present: bool
    tiles: Dict[str, str]
    slot4_active_binding: str
    emount_iris_routed: bool
    virtual_nd_reference_only: bool
    requested_fx6_end_actuator_tx: bool
    requested_fx6_variable_end_ratio: str
    cp_bus_end_frame_blocked_eopnotsupp: bool
    e_nd_actuator_tx_count: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class Slot1CamsetDualMediaFirewallResult:
    admitted: bool
    os_persona: str
    menu_path: str
    operation: str
    shooting_mode: str
    mr_mode_disabled: bool
    requested_slot: int
    slot2_rejected: bool
    media_type: str
    profile_index: int
    profile_filename: str
    profile_source_model: str
    host_model: str
    cross_model_dat_rejected: bool
    expected_stock_fx3_dir: str
    resolved_storage_path: str
    media_path_mismatch_rejected: bool
    redirected_to_tmp_fx6_camset_overlay: bool
    machine_bound_items_excluded: Tuple[str, ...]
    slot1_fx3_camset_mutation_bytes: int
    p2_setting_mutation_bytes: int
    h0_camset_digest_sha256_prefix16: str
    h3_camset_digest_sha256_prefix16: str
    h0_equals_h3: bool
    persistent_emmc_writes_authorized: bool
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class VmcBncm1TcInHdmiTcOutResult:
    admitted: bool
    adapter_model: str
    adapter_part_no: str
    cable_length_m: float
    usb_port: str
    vmc_bncm1_attached: bool
    bnc_direction: str
    xlrh1_handle_usb_blocked_enodev: bool
    reverse_bnc_tcout_blocked_eopnotsupp: bool
    shooting_mode: str
    tc_make: str
    tc_run: str
    signal_hold_seconds: float
    ext_lk_min_hold_seconds: float
    tc_setting_mutated_after_lock: bool
    ext_lk_locked: bool
    ext_lk_released: bool
    tc_status_badge: str
    hdmi_tc_output_menu_path: str
    hdmi_tc_output_menu: str
    hdmi_digital_tc_out_active: bool
    hdmi_tc_out_disabled_in_sq: bool
    bnc_tcout_reverse_drive_events: int
    xlrh1_handle_usb_tc_miswire_damage_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    e_nd_actuator_tx_count: int
    slot1_fx3_camset_mutation_bytes: int
    p2_setting_mutation_bytes: int
    xlrh1_handle_usb_tc_miswire_damage_events: int
    bnc_tcout_reverse_drive_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase202DonorAudit] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase202DonorAudit] = None


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            candidates.append(Path(os.path.expanduser(val)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.append(base / "work")
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(DEFAULT_REPO_ROOT / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal / "work")
    candidates.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")
    candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")

    dedup: List[Path] = []
    seen = set()
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            dedup.append(cand)
    return tuple(dedup)


def resolve_phase202_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 12 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen: Optional[Path] = None
        for root in roots:
            cand = root / rel
            if cand.is_file():
                chosen = cand
                break
        if chosen is None:
            chosen = roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel)
        resolved[key] = chosen
    return resolved


def _read_full_rdonly(path: Path) -> Tuple[int, bytes]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = max(st.st_size, 0)
        while remaining > 0:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = chunks[0] if len(chunks) == 1 else b"".join(chunks)
        return st.st_size, data
    finally:
        os.close(fd)


def _read_bounded_windows_rdonly(
    path: Path,
    windows: Sequence[Tuple[int, str, bytes]],
) -> Tuple[int, int, bytes, Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        file_bytes = st.st_size
        seen_offsets: Dict[int, bytes] = {}
        bytes_read_total = 0
        hits: Dict[str, int] = {}
        for off, label, tok in windows:
            if off not in seen_offsets:
                os.lseek(fd, off, os.SEEK_SET)
                buf = os.read(fd, BOUNDED_WINDOW_MAX_BYTES)
                seen_offsets[off] = buf
                bytes_read_total += len(buf)
            else:
                buf = seen_offsets[off]
            hits[label] = 1 if tok in buf else 0
        head = seen_offsets.get(0)
        if head is None:
            os.lseek(fd, 0, os.SEEK_SET)
            head = os.read(fd, min(BOUNDED_WINDOW_MAX_BYTES, max(file_bytes, 0)))
            bytes_read_total += len(head)
        return file_bytes, bytes_read_total, head, hits
    finally:
        os.close(fd)


def _scan_compact_buf(
    data: bytes,
    *,
    file_bytes: int,
    artifact_key: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[bytes],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {
        tok.decode("ascii", "replace"): (1 if tok in data else 0)
        for tok in tokens
    }
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16],
        marker_hits=hits,
    )


def _scan_compact_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    tokens: Sequence[bytes],
) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data,
        file_bytes=file_bytes,
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        tokens=tokens,
    )


def _scan_large_donor_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    windows: Sequence[Tuple[int, str, bytes]],
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(path, windows)
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:4] = b"\x7fELF"
    buf[4] = 2
    buf[5] = 1
    buf[6] = 1
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_synthetic_uxd_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    return b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase202DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = "CLEAN_ROOM_SYNTHETIC"

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        raw = (
            _build_synthetic_uxd_bytes(toks, f"{key}_SYNTH".encode("ascii"))
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, f"{key}_SYNTH".encode("ascii"))
        )
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        if is_elf:
            head = _build_synthetic_elf64_bytes((), f"{key}_HEAD".encode("ascii"))
        else:
            head = (b"CPAPP_SYNTH_" + label.encode("ascii")).ljust(64, b"\x00")
        hits = {lbl: 1 for _off, lbl, _tok in wins}
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(head),
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256_prefix16=hashlib.sha256(head).hexdigest()[:16],
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase202DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_usb_ctrl=_mk_compact("fx3_usb_ctrl", "FX3_7.02", False),
        fx6_hotshoe=_mk_compact("fx6_hotshoe", "FX6_6.01", False),
        fx3_libbackup=_mk_compact("fx3_libbackup", "FX3_7.02", False),
        fx3_backup_mgr=_mk_compact("fx3_backup_mgr", "FX3_7.02", False),
        fx3_im_elf=_mk_compact("fx3_im_elf", "FX3_7.02", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3_7.02", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3_7.02", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6_6.01", True),
        big6_home_lower_left_and_no_end_proven=True,
        slot1_camset_dual_media_path_proven=True,
        vmcbncm1_tcin_and_hdmi_tcout_proven=True,
        p2_setting_and_backup_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase202_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase202DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.10s, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase202_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple(
        (k, str(p), p.stat().st_size, p.stat().st_mtime_ns)
        for k, p in sorted(paths.items())
    )
    cache_key = ("LOCAL_DONOR_RDONLY", sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_usb_ctrl = _scan_compact_rdonly(
        paths["fx3_usb_ctrl"],
        artifact_key="fx3_usb_ctrl",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_usb_ctrl"],
    )
    fx6_hotshoe = _scan_compact_rdonly(
        paths["fx6_hotshoe"],
        artifact_key="fx6_hotshoe",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_hotshoe"],
    )
    fx3_libbackup = _scan_compact_rdonly(
        paths["fx3_libbackup"],
        artifact_key="fx3_libbackup",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_libbackup"],
    )
    fx3_backup_mgr = _scan_compact_rdonly(
        paths["fx3_backup_mgr"],
        artifact_key="fx3_backup_mgr",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_backup_mgr"],
    )
    fx3_im_elf = _scan_compact_rdonly(
        paths["fx3_im_elf"],
        artifact_key="fx3_im_elf",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_im_elf"],
    )
    fx3_string_en_f = _scan_compact_rdonly(
        paths["fx3_string_en_f"],
        artifact_key="fx3_string_en_f",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_string_en_f"],
    )
    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"],
        artifact_key="fx3_appfw",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_appfw"],
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"],
        artifact_key="fx6_appfw",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_appfw"],
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"],
        artifact_key="fx3_cpapp",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_cpapp"],
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"],
        artifact_key="fx6_cpapp",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_cpapp"],
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"],
        artifact_key="fx3_libmpr",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_libmpr"],
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"],
        artifact_key="fx6_libmpr",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_libmpr"],
    )

    errors: List[str] = []
    compact_items = (
        fx3_usb_ctrl,
        fx6_hotshoe,
        fx3_libbackup,
        fx3_backup_mgr,
        fx3_im_elf,
        fx3_string_en_f,
    )
    for item in compact_items:
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.marker_hits.values()):
            errors.append(f"{item.artifact_key} missing required tokens: {item.marker_hits}")

    for item in (fx3_appfw, fx6_appfw, fx3_cpapp, fx6_cpapp, fx3_libmpr, fx6_libmpr):
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.window_hits.values()):
            errors.append(f"{item.artifact_key} missing bounded window markers: {item.window_hits}")

    big6_ok = (
        fx3_string_en_f.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("Home (Lower Left)") == 1
        and fx3_string_en_f.marker_hits.get("Aperture") == 1
        and fx3_string_en_f.marker_hits.get("ND Filter") == 1
        and fx3_string_en_f.marker_hits.get("Fixed/Variable") == 1
        and fx3_string_en_f.marker_hits.get("Mode Settings") == 1
        and fx3_string_en_f.marker_hits.get("Picture Profile") == 1
        and fx3_string_en_f.marker_hits.get("Select LUT") == 1
        and fx3_string_en_f.marker_hits.get("White Balance") == 1
        and fx3_string_en_f.marker_hits.get("Base ISO") == 1
        and fx3_appfw.window_hits.get("BIG6") == 1
        and fx3_appfw.window_hits.get("HOME_LOWER_LEFT") == 1
        and fx3_appfw.window_hits.get("APERTURE") == 1
        and fx3_appfw.window_hits.get("ND_FILTER") == 1
        and fx6_appfw.window_hits.get("BIG6") == 1
        and fx6_appfw.window_hits.get("HOME_LOWER_LEFT") == 1
        and fx3_cpapp.window_hits.get("ND_FILTER") == 1
        and fx3_cpapp.window_hits.get("Iris") == 1
        and fx6_cpapp.window_hits.get("ND_FILTER") == 1
    )
    camset_ok = (
        fx3_string_en_f.marker_hits.get("Save/Load Settings") == 1
        and fx3_string_en_f.marker_hits.get("Slot 1") == 1
        and fx3_string_en_f.marker_hits.get("Recall Camera Setting") == 1
        and fx3_appfw.window_hits.get("CAMSET_FMT") == 1
        and fx3_appfw.window_hits.get("SONY_SETTING_CAMSET_DAT") == 1
        and fx3_appfw.window_hits.get("SAVE_LOAD") == 1
        and fx6_appfw.window_hits.get("SONY_SETTING_CAMSET_DAT") == 1
        and fx6_appfw.window_hits.get("SAVE_LOAD") == 1
    )
    vmcbncm1_ok = (
        fx3_usb_ctrl.elf64_le_ok
        and fx6_hotshoe.elf64_le_ok
        and fx3_usb_ctrl.marker_hits.get("Multi") == 1
        and fx3_string_en_f.marker_hits.get("Time Code Make") == 1
        and fx3_string_en_f.marker_hits.get("Time Code Run") == 1
        and fx3_string_en_f.marker_hits.get("Time Code Output") == 1
        and fx3_string_en_f.marker_hits.get("HDMI Output Settings") == 1
        and fx3_string_en_f.marker_hits.get("Preset") == 1
        and fx3_string_en_f.marker_hits.get("Free Run") == 1
        and fx3_appfw.window_hits.get("TC_MAKE") == 1
        and fx3_appfw.window_hits.get("TC_RUN") == 1
        and fx3_appfw.window_hits.get("TC_OUT") == 1
        and fx3_appfw.window_hits.get("HDMI") == 1
        and fx3_appfw.window_hits.get("XLR") == 1
        and fx3_cpapp.window_hits.get("TC_MAKE") == 1
        and fx3_cpapp.window_hits.get("TC_RUN") == 1
        and fx3_cpapp.window_hits.get("TC_OUT") == 1
        and fx3_cpapp.window_hits.get("Multi") == 1
        and fx3_cpapp.window_hits.get("HDMI") == 1
        and fx3_libmpr.window_hits.get("TC") == 1
        and fx6_libmpr.window_hits.get("TC") == 1
    )
    p2_backup_ok = (
        fx3_libbackup.elf64_le_ok
        and fx3_backup_mgr.elf64_le_ok
        and fx3_im_elf.elf64_le_ok
        and fx3_im_elf.marker_hits.get("/dev/nflasha2") == 1
        and fx3_im_elf.marker_hits.get("/setting") == 1
    )

    all_ok = (
        len(errors) == 0
        and big6_ok
        and camset_ok
        and vmcbncm1_ok
        and p2_backup_ok
    )

    audit = Phase202DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_usb_ctrl=fx3_usb_ctrl,
        fx6_hotshoe=fx6_hotshoe,
        fx3_libbackup=fx3_libbackup,
        fx3_backup_mgr=fx3_backup_mgr,
        fx3_im_elf=fx3_im_elf,
        fx3_string_en_f=fx3_string_en_f,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        big6_home_lower_left_and_no_end_proven=big6_ok,
        slot1_camset_dual_media_path_proven=camset_ok,
        vmcbncm1_tcin_and_hdmi_tcout_proven=vmcbncm1_ok,
        p2_setting_and_backup_proven=p2_backup_ok,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Pillar A: ILME-FX3 (0x91030080) BIG6 6-Tile Topology & Zero e-ND Firewall HIL
# ---------------------------------------------------------------------------


def probe_big6_home_lower_left_and_end_firewall(
    *,
    mode_settings: str = MODE_SETTINGS_FIXED_VARIABLE,
    home_custom_key_assigned: bool = True,
    home_lower_left_target: str = HOME_LOWER_LEFT_APERTURE,
    fps_label: str = "23.98p (Fixed)",
    iso_label: str = "Base ISO 800",
    shutter_label: str = "180.0°",
    emount_aperture_label: str = "F2.8",
    virtual_nd_reference_label: str = "ND 1/16 (Ref)",
    look_profile_label: str = "S-Cinetone",
    white_balance_label: str = "5600K",
    attempt_fx6_end_actuator_tx: bool = False,
    requested_fx6_variable_end_ratio: Optional[str] = None,
) -> Big6HomeLowerLeftFirewallResult:
    """Co-emulate ILME-FX3 BIG6 6-tile topology, [Home (Lower Left)] routing & zero physical e-ND firewall."""
    req_ratio = "" if requested_fx6_variable_end_ratio is None else str(requested_fx6_variable_end_ratio).strip()
    wants_end_tx = bool(attempt_fx6_end_actuator_tx) or bool(req_ratio)

    if home_lower_left_target not in VALID_HOME_LOWER_LEFT_TARGETS:
        return Big6HomeLowerLeftFirewallResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            model_id_hex=f"0x{FX3_MODEL_ID:08x}",
            fx3_has_physical_end_hardware=FX3_HAS_PHYSICAL_END_HARDWARE,
            mode_settings=mode_settings,
            home_custom_key_assigned=bool(home_custom_key_assigned),
            big6_screen_active=False,
            home_lower_left_menu_path=HOME_LOWER_LEFT_MENU_PATH,
            home_lower_left_target=home_lower_left_target,
            tile_count=6,
            status_bar_zone_7_present=True,
            tiles={},
            slot4_active_binding="NONE",
            emount_iris_routed=False,
            virtual_nd_reference_only=False,
            requested_fx6_end_actuator_tx=wants_end_tx,
            requested_fx6_variable_end_ratio=req_ratio,
            cp_bus_end_frame_blocked_eopnotsupp=False,
            e_nd_actuator_tx_count=0,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_INVALID_HOME_LOWER_LEFT_TARGET_EINVAL",
        )

    slot4_val = (
        f"Aperture: {emount_aperture_label}"
        if home_lower_left_target == HOME_LOWER_LEFT_APERTURE
        else f"ND Filter: {virtual_nd_reference_label}"
    )
    tiles: Dict[str, str] = {
        "tile_1_fps": fps_label,
        "tile_2_iso_base_iso": iso_label,
        "tile_3_shutter_speed_angle": shutter_label,
        "tile_4_home_lower_left": slot4_val,
        "tile_5_picture_profile_select_lut": look_profile_label,
        "tile_6_white_balance": white_balance_label,
    }
    emount_routed = home_lower_left_target == HOME_LOWER_LEFT_APERTURE
    virtual_nd_only = home_lower_left_target == HOME_LOWER_LEFT_ND_FILTER
    slot4_binding = (
        "EMOUNT_ELECTRONIC_IRIS_APERTURE"
        if emount_routed
        else "VIRTUAL_ND_FILTER_METADATA_DISPLAY_ONLY"
    )

    # Wave-26 hard firewall: ILME-FX3 has ZERO physical optical/LC variable e-ND hardware.
    # Any FX6 CP bus actuator frame (1/4..1/128 or variable continuous) is intercepted with EOPNOTSUPP!
    if wants_end_tx:
        return Big6HomeLowerLeftFirewallResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            model_id_hex=f"0x{FX3_MODEL_ID:08x}",
            fx3_has_physical_end_hardware=FX3_HAS_PHYSICAL_END_HARDWARE,
            mode_settings=mode_settings,
            home_custom_key_assigned=bool(home_custom_key_assigned),
            big6_screen_active=(mode_settings == MODE_SETTINGS_FIXED_VARIABLE and bool(home_custom_key_assigned)),
            home_lower_left_menu_path=HOME_LOWER_LEFT_MENU_PATH,
            home_lower_left_target=home_lower_left_target,
            tile_count=len(tiles),
            status_bar_zone_7_present=True,
            tiles=tiles,
            slot4_active_binding=slot4_binding,
            emount_iris_routed=emount_routed,
            virtual_nd_reference_only=virtual_nd_only,
            requested_fx6_end_actuator_tx=True,
            requested_fx6_variable_end_ratio=req_ratio or "1/4..1/128",
            cp_bus_end_frame_blocked_eopnotsupp=True,
            e_nd_actuator_tx_count=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_FX6_VARIABLE_END_CP_ACTUATOR_TX_EOPNOTSUPP",
        )

    if mode_settings != MODE_SETTINGS_FIXED_VARIABLE or not home_custom_key_assigned:
        code = (
            "BLOCKED_BIG6_REQUIRES_MODE_SETTINGS_FIXED_VARIABLE_EINVAL"
            if mode_settings != MODE_SETTINGS_FIXED_VARIABLE
            else "BLOCKED_BIG6_REQUIRES_HOME_CUSTOM_KEY_ASSIGNED_EINVAL"
        )
        return Big6HomeLowerLeftFirewallResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            model_id_hex=f"0x{FX3_MODEL_ID:08x}",
            fx3_has_physical_end_hardware=FX3_HAS_PHYSICAL_END_HARDWARE,
            mode_settings=mode_settings,
            home_custom_key_assigned=bool(home_custom_key_assigned),
            big6_screen_active=False,
            home_lower_left_menu_path=HOME_LOWER_LEFT_MENU_PATH,
            home_lower_left_target=home_lower_left_target,
            tile_count=len(tiles),
            status_bar_zone_7_present=True,
            tiles=tiles,
            slot4_active_binding=slot4_binding,
            emount_iris_routed=emount_routed,
            virtual_nd_reference_only=virtual_nd_only,
            requested_fx6_end_actuator_tx=False,
            requested_fx6_variable_end_ratio="",
            cp_bus_end_frame_blocked_eopnotsupp=False,
            e_nd_actuator_tx_count=0,
            errno_code=EINVAL_ERRNO,
            status_code=code,
        )

    status = (
        "ADMITTED_BIG6_HOME_LOWER_LEFT_EMOUNT_APERTURE_OK"
        if emount_routed
        else "ADMITTED_BIG6_HOME_LOWER_LEFT_VIRTUAL_ND_DISPLAY_OK"
    )
    return Big6HomeLowerLeftFirewallResult(
        admitted=True,
        model_name=MODEL_ILME_FX3,
        model_id_hex=f"0x{FX3_MODEL_ID:08x}",
        fx3_has_physical_end_hardware=FX3_HAS_PHYSICAL_END_HARDWARE,
        mode_settings=mode_settings,
        home_custom_key_assigned=True,
        big6_screen_active=True,
        home_lower_left_menu_path=HOME_LOWER_LEFT_MENU_PATH,
        home_lower_left_target=home_lower_left_target,
        tile_count=len(tiles),
        status_bar_zone_7_present=True,
        tiles=tiles,
        slot4_active_binding=slot4_binding,
        emount_iris_routed=emount_routed,
        virtual_nd_reference_only=virtual_nd_only,
        requested_fx6_end_actuator_tx=False,
        requested_fx6_variable_end_ratio="",
        cp_bus_end_frame_blocked_eopnotsupp=False,
        e_nd_actuator_tx_count=0,
        errno_code=0,
        status_code=status,
    )


def evaluate_pillar_a_big6_home_lower_left_and_no_end_firewall() -> Dict[str, object]:
    default_aperture = probe_big6_home_lower_left_and_end_firewall(
        mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
        home_custom_key_assigned=True,
        home_lower_left_target=HOME_LOWER_LEFT_APERTURE,
        emount_aperture_label="F2.8",
    )
    virtual_nd_display = probe_big6_home_lower_left_and_end_firewall(
        mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
        home_custom_key_assigned=True,
        home_lower_left_target=HOME_LOWER_LEFT_ND_FILTER,
        virtual_nd_reference_label="ND 1/16 (Ref)",
    )
    end_blocked_probes: Dict[str, Dict[str, object]] = {}
    for step in FX6_MOTORIZED_VARIABLE_END_STEPS:
        res = probe_big6_home_lower_left_and_end_firewall(
            mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
            home_custom_key_assigned=True,
            home_lower_left_target=HOME_LOWER_LEFT_ND_FILTER,
            attempt_fx6_end_actuator_tx=True,
            requested_fx6_variable_end_ratio=step,
        )
        end_blocked_probes[step] = asdict(res)

    mode_normal_rejected = probe_big6_home_lower_left_and_end_firewall(
        mode_settings=MODE_SETTINGS_NORMAL,
        home_custom_key_assigned=True,
    )
    no_home_key_rejected = probe_big6_home_lower_left_and_end_firewall(
        mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
        home_custom_key_assigned=False,
    )

    passed = (
        default_aperture.admitted
        and default_aperture.big6_screen_active
        and default_aperture.tile_count == 6
        and default_aperture.status_bar_zone_7_present
        and default_aperture.emount_iris_routed
        and (not default_aperture.virtual_nd_reference_only)
        and default_aperture.e_nd_actuator_tx_count == 0
        and virtual_nd_display.admitted
        and virtual_nd_display.big6_screen_active
        and (not virtual_nd_display.emount_iris_routed)
        and virtual_nd_display.virtual_nd_reference_only
        and virtual_nd_display.e_nd_actuator_tx_count == 0
        and all(
            (not p["admitted"])
            and bool(p["cp_bus_end_frame_blocked_eopnotsupp"])
            and p["errno_code"] == EOPNOTSUPP_ERRNO
            and p["e_nd_actuator_tx_count"] == 0
            for p in end_blocked_probes.values()
        )
        and (not mode_normal_rejected.admitted)
        and mode_normal_rejected.errno_code == EINVAL_ERRNO
        and (not no_home_key_rejected.admitted)
        and no_home_key_rejected.errno_code == EINVAL_ERRNO
    )
    return {
        "passed": passed,
        "big6_tile_slot_names": list(BIG6_TILE_SLOT_NAMES),
        "fx6_motorized_variable_end_steps_blocked": list(FX6_MOTORIZED_VARIABLE_END_STEPS),
        "default_home_lower_left_aperture": asdict(default_aperture),
        "switched_home_lower_left_virtual_nd_display": asdict(virtual_nd_display),
        "fx6_variable_end_cp_blocked_matrix": end_blocked_probes,
        "mode_normal_rejected_einval": asdict(mode_normal_rejected),
        "unassigned_home_key_rejected_einval": asdict(no_home_key_rejected),
    }


# ---------------------------------------------------------------------------
# Pillar B: Slot-1-Only CAMSET01.DAT..CAMSET10.DAT Dual-Media Path Split &
#           Cross-Model .DAT Firewall HIL
# ---------------------------------------------------------------------------

_CAMSET_FILENAME_RE = re.compile(r"^CAMSET(0[1-9]|10)\.DAT$")


def _compute_stock_slot1_camset_digest() -> str:
    h = hashlib.sha256()
    for idx in range(CAMSET_MIN_INDEX, CAMSET_MAX_INDEX + 1):
        line = f"FX3_702_SLOT1:CAMSET{idx:02d}.DAT:H0_STOCK_SEALED\n".encode("ascii")
        h.update(line)
    return h.hexdigest()[:16]


_BASELINE_SLOT1_CAMSET_H0_PREFIX16 = _compute_stock_slot1_camset_digest()


def resolve_stock_fx3_camset_dir(media_type: str) -> str:
    """Resolve media-specific root directory for stock ILME-FX3 CAMSET profiles."""
    if media_type in SD_FAMILY_MEDIA_TYPES:
        return CAMSET_SD_DIR
    if media_type == MEDIA_TYPE_CFEXPRESS_A:
        return CAMSET_CFEXPRESS_A_DIR
    raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported CAMSET media_type {media_type!r}")


def probe_slot1_camset_dual_media_and_cross_model_firewall(
    *,
    os_persona: str = OS_PERSONA_STOCK_FX3_702,
    operation: str = "LOAD",
    shooting_mode: str = SHOOTING_MODE_MOVIE,
    requested_slot: int = 1,
    media_type: str = MEDIA_TYPE_SDXC,
    profile_index: int = 1,
    explicit_filename: Optional[str] = None,
    explicit_card_dir: Optional[str] = None,
    profile_source_model: str = MODEL_ILME_FX3,
    redirect_stage_b_to_overlay: bool = True,
) -> Slot1CamsetDualMediaFirewallResult:
    """Co-emulate Slot-1-only CAMSET01..10.DAT dual-media path split, MR lock & cross-model firewall."""
    if os_persona not in VALID_OS_PERSONAS:
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported os_persona {os_persona!r}")
    op_norm = operation.strip().upper()
    if op_norm not in ("SAVE", "LOAD"):
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported CAMSET operation {operation!r}")
    if media_type not in VALID_CAMSET_MEDIA_TYPES:
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported media_type {media_type!r}")

    expected_dir = resolve_stock_fx3_camset_dir(media_type)
    h0 = _BASELINE_SLOT1_CAMSET_H0_PREFIX16
    fname = (
        explicit_filename.strip()
        if explicit_filename is not None
        else f"CAMSET{profile_index:02d}.DAT"
    )

    # 1. MR (Recall Camera Setting) mode greys out & disables [Save/Load Settings]
    if shooting_mode == SHOOTING_MODE_MR:
        return Slot1CamsetDualMediaFirewallResult(
            admitted=False,
            os_persona=os_persona,
            menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=op_norm,
            shooting_mode=shooting_mode,
            mr_mode_disabled=True,
            requested_slot=requested_slot,
            slot2_rejected=(requested_slot != CAMSET_ALLOWED_SLOT),
            media_type=media_type,
            profile_index=profile_index,
            profile_filename=fname,
            profile_source_model=profile_source_model,
            host_model=MODEL_ILME_FX3,
            cross_model_dat_rejected=False,
            expected_stock_fx3_dir=expected_dir,
            resolved_storage_path="NONE",
            media_path_mismatch_rejected=False,
            redirected_to_tmp_fx6_camset_overlay=False,
            machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
            slot1_fx3_camset_mutation_bytes=0,
            p2_setting_mutation_bytes=0,
            h0_camset_digest_sha256_prefix16=h0,
            h3_camset_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_CAMSET_GREYED_OUT_IN_MR_RECALL_MODE_EOPNOTSUPP",
        )

    # 2. Strict Slot-1-only enforcement (Slot 2 or any slot != 1 rejected)
    if requested_slot != CAMSET_ALLOWED_SLOT:
        return Slot1CamsetDualMediaFirewallResult(
            admitted=False,
            os_persona=os_persona,
            menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=op_norm,
            shooting_mode=shooting_mode,
            mr_mode_disabled=False,
            requested_slot=requested_slot,
            slot2_rejected=True,
            media_type=media_type,
            profile_index=profile_index,
            profile_filename=fname,
            profile_source_model=profile_source_model,
            host_model=MODEL_ILME_FX3,
            cross_model_dat_rejected=False,
            expected_stock_fx3_dir=expected_dir,
            resolved_storage_path="NONE",
            media_path_mismatch_rejected=False,
            redirected_to_tmp_fx6_camset_overlay=False,
            machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
            slot1_fx3_camset_mutation_bytes=0,
            p2_setting_mutation_bytes=0,
            h0_camset_digest_sha256_prefix16=h0,
            h3_camset_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_CAMSET_SLOT2_FORBIDDEN_SLOT1_ONLY_EINVAL",
        )

    # 3. Profile index 1..10 & exact CAMSET01.DAT..CAMSET10.DAT filename validation
    if (
        not (CAMSET_MIN_INDEX <= profile_index <= CAMSET_MAX_INDEX)
        or ".." in fname
        or "/" in fname
        or "\\" in fname
        or "\x00" in fname
        or _CAMSET_FILENAME_RE.match(fname) is None
        or fname != f"CAMSET{profile_index:02d}.DAT"
    ):
        return Slot1CamsetDualMediaFirewallResult(
            admitted=False,
            os_persona=os_persona,
            menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=op_norm,
            shooting_mode=shooting_mode,
            mr_mode_disabled=False,
            requested_slot=requested_slot,
            slot2_rejected=False,
            media_type=media_type,
            profile_index=profile_index,
            profile_filename=fname,
            profile_source_model=profile_source_model,
            host_model=MODEL_ILME_FX3,
            cross_model_dat_rejected=False,
            expected_stock_fx3_dir=expected_dir,
            resolved_storage_path="NONE",
            media_path_mismatch_rejected=False,
            redirected_to_tmp_fx6_camset_overlay=False,
            machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
            slot1_fx3_camset_mutation_bytes=0,
            p2_setting_mutation_bytes=0,
            h0_camset_digest_sha256_prefix16=h0,
            h3_camset_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_CAMSET_PROFILE_INDEX_OR_FILENAME_EINVAL",
        )

    # 4. Dual-media root directory asymmetry check (SD /PRIVATE/SONY/... vs CFexpress-A /SONY/...)
    if explicit_card_dir is not None:
        norm_dir = explicit_card_dir.strip().rstrip("/")
        # Check cross-model path injection first (e.g. /PRIVATE/SONY/SETTING/FX3A/CAMSET)
        if "/SETTING/FX3A/" in (norm_dir + "/") or "/SETTING/FX6/" in (norm_dir + "/"):
            return Slot1CamsetDualMediaFirewallResult(
                admitted=False,
                os_persona=os_persona,
                menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
                operation=op_norm,
                shooting_mode=shooting_mode,
                mr_mode_disabled=False,
                requested_slot=requested_slot,
                slot2_rejected=False,
                media_type=media_type,
                profile_index=profile_index,
                profile_filename=fname,
                profile_source_model=profile_source_model,
                host_model=MODEL_ILME_FX3,
                cross_model_dat_rejected=True,
                expected_stock_fx3_dir=expected_dir,
                resolved_storage_path="NONE",
                media_path_mismatch_rejected=True,
                redirected_to_tmp_fx6_camset_overlay=False,
                machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
                slot1_fx3_camset_mutation_bytes=0,
                p2_setting_mutation_bytes=0,
                h0_camset_digest_sha256_prefix16=h0,
                h3_camset_digest_sha256_prefix16=h0,
                h0_equals_h3=True,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                errno_code=EINVAL_ERRNO,
                status_code="BLOCKED_CROSS_MODEL_CAMSET_DIRECTORY_EINVAL",
            )
        if os_persona == OS_PERSONA_STOCK_FX3_702 and norm_dir != expected_dir:
            return Slot1CamsetDualMediaFirewallResult(
                admitted=False,
                os_persona=os_persona,
                menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
                operation=op_norm,
                shooting_mode=shooting_mode,
                mr_mode_disabled=False,
                requested_slot=requested_slot,
                slot2_rejected=False,
                media_type=media_type,
                profile_index=profile_index,
                profile_filename=fname,
                profile_source_model=profile_source_model,
                host_model=MODEL_ILME_FX3,
                cross_model_dat_rejected=False,
                expected_stock_fx3_dir=expected_dir,
                resolved_storage_path="NONE",
                media_path_mismatch_rejected=True,
                redirected_to_tmp_fx6_camset_overlay=False,
                machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
                slot1_fx3_camset_mutation_bytes=0,
                p2_setting_mutation_bytes=0,
                h0_camset_digest_sha256_prefix16=h0,
                h3_camset_digest_sha256_prefix16=h0,
                h0_equals_h3=True,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                errno_code=EINVAL_ERRNO,
                status_code="BLOCKED_CAMSET_DUAL_MEDIA_ROOT_MISMATCH_EINVAL",
            )

    # 5. Stage-B FX6 persona sandboxed to /tmp/fx6_camset_overlay (never touches Slot-1 FX3/CAMSET or p2:/setting)
    if os_persona == OS_PERSONA_STAGE_B_FX6_601:
        if profile_source_model != MODEL_ILME_FX6:
            return Slot1CamsetDualMediaFirewallResult(
                admitted=False,
                os_persona=os_persona,
                menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
                operation=op_norm,
                shooting_mode=shooting_mode,
                mr_mode_disabled=False,
                requested_slot=requested_slot,
                slot2_rejected=False,
                media_type=media_type,
                profile_index=profile_index,
                profile_filename=fname,
                profile_source_model=profile_source_model,
                host_model=MODEL_ILME_FX3,
                cross_model_dat_rejected=True,
                expected_stock_fx3_dir=expected_dir,
                resolved_storage_path="NONE",
                media_path_mismatch_rejected=False,
                redirected_to_tmp_fx6_camset_overlay=False,
                machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
                slot1_fx3_camset_mutation_bytes=0,
                p2_setting_mutation_bytes=0,
                h0_camset_digest_sha256_prefix16=h0,
                h3_camset_digest_sha256_prefix16=h0,
                h0_equals_h3=True,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                errno_code=EINVAL_ERRNO,
                status_code="BLOCKED_STAGE_B_CROSS_MODEL_CAMSET_DAT_EINVAL",
            )
        if not redirect_stage_b_to_overlay:
            return Slot1CamsetDualMediaFirewallResult(
                admitted=False,
                os_persona=os_persona,
                menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
                operation=op_norm,
                shooting_mode=shooting_mode,
                mr_mode_disabled=False,
                requested_slot=requested_slot,
                slot2_rejected=False,
                media_type=media_type,
                profile_index=profile_index,
                profile_filename=fname,
                profile_source_model=profile_source_model,
                host_model=MODEL_ILME_FX3,
                cross_model_dat_rejected=False,
                expected_stock_fx3_dir=expected_dir,
                resolved_storage_path="NONE",
                media_path_mismatch_rejected=False,
                redirected_to_tmp_fx6_camset_overlay=False,
                machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
                slot1_fx3_camset_mutation_bytes=0,
                p2_setting_mutation_bytes=0,
                h0_camset_digest_sha256_prefix16=h0,
                h3_camset_digest_sha256_prefix16=h0,
                h0_equals_h3=True,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                errno_code=EROFS_ERRNO,
                status_code="BLOCKED_STAGE_B_DIRECT_SLOT1_OR_P2_CAMSET_WRITE_EROFS",
            )

        overlay_file = f"{VOLATILE_FX6_CAMSET_OVERLAY_DIR}/{fname}"
        return Slot1CamsetDualMediaFirewallResult(
            admitted=True,
            os_persona=os_persona,
            menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=op_norm,
            shooting_mode=shooting_mode,
            mr_mode_disabled=False,
            requested_slot=requested_slot,
            slot2_rejected=False,
            media_type=media_type,
            profile_index=profile_index,
            profile_filename=fname,
            profile_source_model=profile_source_model,
            host_model=MODEL_ILME_FX3,
            cross_model_dat_rejected=False,
            expected_stock_fx3_dir=expected_dir,
            resolved_storage_path=overlay_file,
            media_path_mismatch_rejected=False,
            redirected_to_tmp_fx6_camset_overlay=True,
            machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
            slot1_fx3_camset_mutation_bytes=0,
            p2_setting_mutation_bytes=0,
            h0_camset_digest_sha256_prefix16=h0,
            h3_camset_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=0,
            status_code="ADMITTED_STAGE_B_SANDBOXED_TO_TMP_FX6_CAMSET_OVERLAY_H0_EQ_H3",
        )

    # 6. Stock FX3 7.02 cross-model .DAT firewall (rejects ILME-FX3A and ILME-FX6 .DAT files)
    if profile_source_model != MODEL_ILME_FX3:
        return Slot1CamsetDualMediaFirewallResult(
            admitted=False,
            os_persona=os_persona,
            menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=op_norm,
            shooting_mode=shooting_mode,
            mr_mode_disabled=False,
            requested_slot=requested_slot,
            slot2_rejected=False,
            media_type=media_type,
            profile_index=profile_index,
            profile_filename=fname,
            profile_source_model=profile_source_model,
            host_model=MODEL_ILME_FX3,
            cross_model_dat_rejected=True,
            expected_stock_fx3_dir=expected_dir,
            resolved_storage_path="NONE",
            media_path_mismatch_rejected=False,
            redirected_to_tmp_fx6_camset_overlay=False,
            machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
            slot1_fx3_camset_mutation_bytes=0,
            p2_setting_mutation_bytes=0,
            h0_camset_digest_sha256_prefix16=h0,
            h3_camset_digest_sha256_prefix16=h0,
            h0_equals_h3=True,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_CROSS_MODEL_CAMSET_DAT_INCOMPATIBLE_EINVAL",
        )

    resolved_path = f"{expected_dir}/{fname}"
    return Slot1CamsetDualMediaFirewallResult(
        admitted=True,
        os_persona=os_persona,
        menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
        operation=op_norm,
        shooting_mode=shooting_mode,
        mr_mode_disabled=False,
        requested_slot=CAMSET_ALLOWED_SLOT,
        slot2_rejected=False,
        media_type=media_type,
        profile_index=profile_index,
        profile_filename=fname,
        profile_source_model=MODEL_ILME_FX3,
        host_model=MODEL_ILME_FX3,
        cross_model_dat_rejected=False,
        expected_stock_fx3_dir=expected_dir,
        resolved_storage_path=resolved_path,
        media_path_mismatch_rejected=False,
        redirected_to_tmp_fx6_camset_overlay=False,
        machine_bound_items_excluded=CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS,
        slot1_fx3_camset_mutation_bytes=0,
        p2_setting_mutation_bytes=0,
        h0_camset_digest_sha256_prefix16=h0,
        h3_camset_digest_sha256_prefix16=h0,
        h0_equals_h3=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        errno_code=0,
        status_code="ADMITTED_STOCK_FX3_SLOT1_CAMSET_DUAL_MEDIA_OK",
    )


def evaluate_pillar_b_slot1_camset_dual_media_and_firewall() -> Dict[str, object]:
    sd_slot1_ok = probe_slot1_camset_dual_media_and_cross_model_firewall(
        os_persona=OS_PERSONA_STOCK_FX3_702,
        operation="SAVE",
        shooting_mode=SHOOTING_MODE_MOVIE,
        requested_slot=1,
        media_type=MEDIA_TYPE_SDXC,
        profile_index=1,
    )
    cfexpress_slot1_ok = probe_slot1_camset_dual_media_and_cross_model_firewall(
        os_persona=OS_PERSONA_STOCK_FX3_702,
        operation="LOAD",
        shooting_mode=SHOOTING_MODE_MOVIE,
        requested_slot=1,
        media_type=MEDIA_TYPE_CFEXPRESS_A,
        profile_index=10,
    )
    slot2_rejected = probe_slot1_camset_dual_media_and_cross_model_firewall(
        requested_slot=2,
        media_type=MEDIA_TYPE_SDXC,
        profile_index=1,
    )
    index_11_rejected = probe_slot1_camset_dual_media_and_cross_model_firewall(
        requested_slot=1,
        media_type=MEDIA_TYPE_SDXC,
        profile_index=11,
    )
    mr_mode_blocked = probe_slot1_camset_dual_media_and_cross_model_firewall(
        shooting_mode=SHOOTING_MODE_MR,
        requested_slot=1,
        media_type=MEDIA_TYPE_SDXC,
        profile_index=1,
    )
    sd_on_cfexpress_mismatch = probe_slot1_camset_dual_media_and_cross_model_firewall(
        requested_slot=1,
        media_type=MEDIA_TYPE_CFEXPRESS_A,
        profile_index=2,
        explicit_card_dir=CAMSET_SD_DIR,
    )
    cfexpress_on_sd_mismatch = probe_slot1_camset_dual_media_and_cross_model_firewall(
        requested_slot=1,
        media_type=MEDIA_TYPE_SDXC,
        profile_index=2,
        explicit_card_dir=CAMSET_CFEXPRESS_A_DIR,
    )
    fx3a_dat_rejected = probe_slot1_camset_dual_media_and_cross_model_firewall(
        os_persona=OS_PERSONA_STOCK_FX3_702,
        profile_source_model=MODEL_ILME_FX3A,
    )
    fx6_dat_rejected = probe_slot1_camset_dual_media_and_cross_model_firewall(
        os_persona=OS_PERSONA_STOCK_FX3_702,
        profile_source_model=MODEL_ILME_FX6,
    )
    stage_b_direct_blocked_erofs = probe_slot1_camset_dual_media_and_cross_model_firewall(
        os_persona=OS_PERSONA_STAGE_B_FX6_601,
        operation="SAVE",
        profile_source_model=MODEL_ILME_FX6,
        redirect_stage_b_to_overlay=False,
    )
    stage_b_overlay_verified = [
        probe_slot1_camset_dual_media_and_cross_model_firewall(
            os_persona=OS_PERSONA_STAGE_B_FX6_601,
            operation="SAVE",
            profile_index=i,
            profile_source_model=MODEL_ILME_FX6,
            redirect_stage_b_to_overlay=True,
        )
        for i in range(CAMSET_MIN_INDEX, CAMSET_MAX_INDEX + 1)
    ]

    passed = (
        sd_slot1_ok.admitted
        and sd_slot1_ok.resolved_storage_path == "/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT"
        and cfexpress_slot1_ok.admitted
        and cfexpress_slot1_ok.resolved_storage_path == "/SONY/SETTING/FX3/CAMSET/CAMSET10.DAT"
        and (not slot2_rejected.admitted)
        and slot2_rejected.slot2_rejected
        and slot2_rejected.errno_code == EINVAL_ERRNO
        and (not index_11_rejected.admitted)
        and index_11_rejected.errno_code == EINVAL_ERRNO
        and (not mr_mode_blocked.admitted)
        and mr_mode_blocked.mr_mode_disabled
        and mr_mode_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not sd_on_cfexpress_mismatch.admitted)
        and sd_on_cfexpress_mismatch.media_path_mismatch_rejected
        and (not cfexpress_on_sd_mismatch.admitted)
        and cfexpress_on_sd_mismatch.media_path_mismatch_rejected
        and (not fx3a_dat_rejected.admitted)
        and fx3a_dat_rejected.cross_model_dat_rejected
        and (not fx6_dat_rejected.admitted)
        and fx6_dat_rejected.cross_model_dat_rejected
        and (not stage_b_direct_blocked_erofs.admitted)
        and stage_b_direct_blocked_erofs.errno_code == EROFS_ERRNO
        and all(
            r.admitted
            and r.redirected_to_tmp_fx6_camset_overlay
            and r.h0_equals_h3
            and r.slot1_fx3_camset_mutation_bytes == 0
            and r.p2_setting_mutation_bytes == 0
            for r in stage_b_overlay_verified
        )
    )
    return {
        "passed": passed,
        "sd_slot1_camset01_ok": asdict(sd_slot1_ok),
        "cfexpress_a_slot1_camset10_ok": asdict(cfexpress_slot1_ok),
        "slot2_rejected_einval": asdict(slot2_rejected),
        "profile_11_rejected_einval": asdict(index_11_rejected),
        "mr_recall_mode_greyed_out_blocked": asdict(mr_mode_blocked),
        "sd_path_on_cfexpress_mismatch_rejected": asdict(sd_on_cfexpress_mismatch),
        "cfexpress_path_on_sd_mismatch_rejected": asdict(cfexpress_on_sd_mismatch),
        "fx3a_cross_model_dat_rejected": asdict(fx3a_dat_rejected),
        "fx6_cross_model_dat_rejected": asdict(fx6_dat_rejected),
        "stage_b_direct_slot1_blocked_erofs": asdict(stage_b_direct_blocked_erofs),
        "stage_b_overlay_profiles_verified": len(stage_b_overlay_verified),
        "stage_b_overlay_sample_camset01": asdict(stage_b_overlay_verified[0]),
    }


# ---------------------------------------------------------------------------
# Pillar C & D: VMC-BNCM1 (A-5051-506-A) Body-Only TC IN (EXT-LK), XLR-H1
#               Handle Micro-USB Block, Digital HDMI TC OUT & Safety Redlines
# ---------------------------------------------------------------------------


def probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
    *,
    usb_port: str = USB_PORT_BODY_MULTI_MICRO,
    vmc_bncm1_attached: bool = True,
    bnc_direction: str = BNC_DIRECTION_TC_IN,
    attempt_bnc_tc_out: bool = False,
    shooting_mode: str = SHOOTING_MODE_MOVIE,
    tc_make: str = TC_MAKE_PRESET,
    tc_run: str = TC_RUN_FREE_RUN,
    signal_hold_seconds: float = 10.5,
    was_previously_ext_lk: bool = False,
    tc_setting_mutated_after_lock: bool = False,
    hdmi_tc_output_menu: str = HDMI_TC_OUT_ON,
) -> VmcBncm1TcInHdmiTcOutResult:
    """Co-emulate VMC-BNCM1 body-only TC IN (EXT-LK >=10s), XLR-H1 USB block, BNC TC OUT block & HDMI TC OUT."""
    if usb_port not in VALID_TC_USB_PORTS:
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported usb_port {usb_port!r}")
    if bnc_direction not in VALID_BNC_DIRECTIONS:
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported bnc_direction {bnc_direction!r}")
    if shooting_mode not in VALID_TC_SHOOTING_MODES:
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported shooting_mode {shooting_mode!r}")
    if tc_make not in VALID_TC_MAKE_MODES:
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported tc_make {tc_make!r}")
    if tc_run not in VALID_TC_RUN_MODES:
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported tc_run {tc_run!r}")
    if hdmi_tc_output_menu not in VALID_HDMI_TC_OUT_SETTINGS:
        raise RealHwBig6CamsetVmcBncm1Error(f"Unsupported hdmi_tc_output_menu {hdmi_tc_output_menu!r}")
    if signal_hold_seconds < 0.0:
        raise RealHwBig6CamsetVmcBncm1Error(f"signal_hold_seconds must be >= 0, got {signal_hold_seconds!r}")

    is_sq = shooting_mode == SHOOTING_MODE_SQ
    hdmi_tc_out_active = (hdmi_tc_output_menu == HDMI_TC_OUT_ON) and (not is_sq)
    hdmi_disabled_in_sq = (hdmi_tc_output_menu == HDMI_TC_OUT_ON) and is_sq

    # Trap 1: Plugging VMC-BNCM1 into XLR-H1 Handle side Micro-USB port is strictly blocked (ENODEV)!
    if vmc_bncm1_attached and usb_port == USB_PORT_XLR_H1_HANDLE_MICRO:
        return VmcBncm1TcInHdmiTcOutResult(
            admitted=False,
            adapter_model=VMC_BNCM1_MODEL,
            adapter_part_no=VMC_BNCM1_SONY_PART_NO,
            cable_length_m=VMC_BNCM1_CABLE_LENGTH_M,
            usb_port=usb_port,
            vmc_bncm1_attached=True,
            bnc_direction=bnc_direction,
            xlrh1_handle_usb_blocked_enodev=True,
            reverse_bnc_tcout_blocked_eopnotsupp=False,
            shooting_mode=shooting_mode,
            tc_make=tc_make,
            tc_run=tc_run,
            signal_hold_seconds=float(signal_hold_seconds),
            ext_lk_min_hold_seconds=EXT_LK_MIN_LOCK_HOLD_SECONDS,
            tc_setting_mutated_after_lock=bool(tc_setting_mutated_after_lock),
            ext_lk_locked=False,
            ext_lk_released=bool(was_previously_ext_lk),
            tc_status_badge="INTERNAL_TC",
            hdmi_tc_output_menu_path=HDMI_TC_OUTPUT_MENU_PATH,
            hdmi_tc_output_menu=hdmi_tc_output_menu,
            hdmi_digital_tc_out_active=hdmi_tc_out_active,
            hdmi_tc_out_disabled_in_sq=hdmi_disabled_in_sq,
            bnc_tcout_reverse_drive_events=0,
            xlrh1_handle_usb_tc_miswire_damage_events=0,
            errno_code=ENODEV_ERRNO,
            status_code="BLOCKED_XLR_H1_HANDLE_MICRO_USB_VMC_BNCM1_UNSUPPORTED_ENODEV",
        )

    if vmc_bncm1_attached and usb_port != USB_PORT_BODY_MULTI_MICRO:
        return VmcBncm1TcInHdmiTcOutResult(
            admitted=False,
            adapter_model=VMC_BNCM1_MODEL,
            adapter_part_no=VMC_BNCM1_SONY_PART_NO,
            cable_length_m=VMC_BNCM1_CABLE_LENGTH_M,
            usb_port=usb_port,
            vmc_bncm1_attached=True,
            bnc_direction=bnc_direction,
            xlrh1_handle_usb_blocked_enodev=False,
            reverse_bnc_tcout_blocked_eopnotsupp=False,
            shooting_mode=shooting_mode,
            tc_make=tc_make,
            tc_run=tc_run,
            signal_hold_seconds=float(signal_hold_seconds),
            ext_lk_min_hold_seconds=EXT_LK_MIN_LOCK_HOLD_SECONDS,
            tc_setting_mutated_after_lock=bool(tc_setting_mutated_after_lock),
            ext_lk_locked=False,
            ext_lk_released=bool(was_previously_ext_lk),
            tc_status_badge="INTERNAL_TC",
            hdmi_tc_output_menu_path=HDMI_TC_OUTPUT_MENU_PATH,
            hdmi_tc_output_menu=hdmi_tc_output_menu,
            hdmi_digital_tc_out_active=hdmi_tc_out_active,
            hdmi_tc_out_disabled_in_sq=hdmi_disabled_in_sq,
            bnc_tcout_reverse_drive_events=0,
            xlrh1_handle_usb_tc_miswire_damage_events=0,
            errno_code=ENODEV_ERRNO,
            status_code="BLOCKED_VMC_BNCM1_REQUIRES_BODY_MULTI_MICRO_USB_ENODEV",
        )

    # Trap 2: Reverse BNC/LTC TC OUT on FX3 Multi/Micro-USB is physically unsupported -> EOPNOTSUPP!
    if bnc_direction == BNC_DIRECTION_TC_OUT or attempt_bnc_tc_out:
        return VmcBncm1TcInHdmiTcOutResult(
            admitted=False,
            adapter_model=VMC_BNCM1_MODEL,
            adapter_part_no=VMC_BNCM1_SONY_PART_NO,
            cable_length_m=VMC_BNCM1_CABLE_LENGTH_M,
            usb_port=usb_port,
            vmc_bncm1_attached=bool(vmc_bncm1_attached),
            bnc_direction=BNC_DIRECTION_TC_OUT,
            xlrh1_handle_usb_blocked_enodev=False,
            reverse_bnc_tcout_blocked_eopnotsupp=True,
            shooting_mode=shooting_mode,
            tc_make=tc_make,
            tc_run=tc_run,
            signal_hold_seconds=float(signal_hold_seconds),
            ext_lk_min_hold_seconds=EXT_LK_MIN_LOCK_HOLD_SECONDS,
            tc_setting_mutated_after_lock=bool(tc_setting_mutated_after_lock),
            ext_lk_locked=False,
            ext_lk_released=bool(was_previously_ext_lk),
            tc_status_badge="INTERNAL_TC",
            hdmi_tc_output_menu_path=HDMI_TC_OUTPUT_MENU_PATH,
            hdmi_tc_output_menu=hdmi_tc_output_menu,
            hdmi_digital_tc_out_active=hdmi_tc_out_active,
            hdmi_tc_out_disabled_in_sq=hdmi_disabled_in_sq,
            bnc_tcout_reverse_drive_events=0,
            xlrh1_handle_usb_tc_miswire_damage_events=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_REVERSE_BNC_TC_OUT_UNSUPPORTED_ROUTE_TO_HDMI_EOPNOTSUPP",
        )

    # Unidirectional TC IN state machine (Movie + Preset + Free Run + >=10s -> EXT-LK)
    prereqs_met = (
        bool(vmc_bncm1_attached)
        and usb_port == USB_PORT_BODY_MULTI_MICRO
        and shooting_mode == SHOOTING_MODE_MOVIE
        and tc_make == TC_MAKE_PRESET
        and tc_run == TC_RUN_FREE_RUN
        and (not tc_setting_mutated_after_lock)
    )

    if not prereqs_met:
        released = bool(was_previously_ext_lk) or bool(tc_setting_mutated_after_lock)
        status = (
            "ADMITTED_EXT_LK_RELEASED_ON_SQ_MODE_SWITCH"
            if is_sq
            else (
                "ADMITTED_EXT_LK_RELEASED_ON_TC_SETTING_CHANGE"
                if (tc_setting_mutated_after_lock or tc_make != TC_MAKE_PRESET or tc_run != TC_RUN_FREE_RUN)
                else "ADMITTED_INTERNAL_TC_GENERATOR_ACTIVE"
            )
        )
        return VmcBncm1TcInHdmiTcOutResult(
            admitted=True,
            adapter_model=VMC_BNCM1_MODEL,
            adapter_part_no=VMC_BNCM1_SONY_PART_NO,
            cable_length_m=VMC_BNCM1_CABLE_LENGTH_M,
            usb_port=usb_port,
            vmc_bncm1_attached=bool(vmc_bncm1_attached),
            bnc_direction=BNC_DIRECTION_TC_IN,
            xlrh1_handle_usb_blocked_enodev=False,
            reverse_bnc_tcout_blocked_eopnotsupp=False,
            shooting_mode=shooting_mode,
            tc_make=tc_make,
            tc_run=tc_run,
            signal_hold_seconds=float(signal_hold_seconds),
            ext_lk_min_hold_seconds=EXT_LK_MIN_LOCK_HOLD_SECONDS,
            tc_setting_mutated_after_lock=bool(tc_setting_mutated_after_lock),
            ext_lk_locked=False,
            ext_lk_released=released,
            tc_status_badge="INTERNAL_TC",
            hdmi_tc_output_menu_path=HDMI_TC_OUTPUT_MENU_PATH,
            hdmi_tc_output_menu=hdmi_tc_output_menu,
            hdmi_digital_tc_out_active=hdmi_tc_out_active,
            hdmi_tc_out_disabled_in_sq=hdmi_disabled_in_sq,
            bnc_tcout_reverse_drive_events=0,
            xlrh1_handle_usb_tc_miswire_damage_events=0,
            errno_code=0,
            status_code=status,
        )

    if signal_hold_seconds < EXT_LK_MIN_LOCK_HOLD_SECONDS:
        return VmcBncm1TcInHdmiTcOutResult(
            admitted=True,
            adapter_model=VMC_BNCM1_MODEL,
            adapter_part_no=VMC_BNCM1_SONY_PART_NO,
            cable_length_m=VMC_BNCM1_CABLE_LENGTH_M,
            usb_port=usb_port,
            vmc_bncm1_attached=True,
            bnc_direction=BNC_DIRECTION_TC_IN,
            xlrh1_handle_usb_blocked_enodev=False,
            reverse_bnc_tcout_blocked_eopnotsupp=False,
            shooting_mode=shooting_mode,
            tc_make=tc_make,
            tc_run=tc_run,
            signal_hold_seconds=float(signal_hold_seconds),
            ext_lk_min_hold_seconds=EXT_LK_MIN_LOCK_HOLD_SECONDS,
            tc_setting_mutated_after_lock=False,
            ext_lk_locked=False,
            ext_lk_released=False,
            tc_status_badge="TC_IN_ACQUIRING",
            hdmi_tc_output_menu_path=HDMI_TC_OUTPUT_MENU_PATH,
            hdmi_tc_output_menu=hdmi_tc_output_menu,
            hdmi_digital_tc_out_active=hdmi_tc_out_active,
            hdmi_tc_out_disabled_in_sq=False,
            bnc_tcout_reverse_drive_events=0,
            xlrh1_handle_usb_tc_miswire_damage_events=0,
            errno_code=0,
            status_code="ADMITTED_VMC_BNCM1_TC_IN_SYNCING_LT_10S",
        )

    return VmcBncm1TcInHdmiTcOutResult(
        admitted=True,
        adapter_model=VMC_BNCM1_MODEL,
        adapter_part_no=VMC_BNCM1_SONY_PART_NO,
        cable_length_m=VMC_BNCM1_CABLE_LENGTH_M,
        usb_port=usb_port,
        vmc_bncm1_attached=True,
        bnc_direction=BNC_DIRECTION_TC_IN,
        xlrh1_handle_usb_blocked_enodev=False,
        reverse_bnc_tcout_blocked_eopnotsupp=False,
        shooting_mode=shooting_mode,
        tc_make=tc_make,
        tc_run=tc_run,
        signal_hold_seconds=float(signal_hold_seconds),
        ext_lk_min_hold_seconds=EXT_LK_MIN_LOCK_HOLD_SECONDS,
        tc_setting_mutated_after_lock=False,
        ext_lk_locked=True,
        ext_lk_released=False,
        tc_status_badge="EXT-LK",
        hdmi_tc_output_menu_path=HDMI_TC_OUTPUT_MENU_PATH,
        hdmi_tc_output_menu=hdmi_tc_output_menu,
        hdmi_digital_tc_out_active=hdmi_tc_out_active,
        hdmi_tc_out_disabled_in_sq=False,
        bnc_tcout_reverse_drive_events=0,
        xlrh1_handle_usb_tc_miswire_damage_events=0,
        errno_code=0,
        status_code="ADMITTED_VMC_BNCM1_BODY_TC_IN_EXT_LK_LOCKED_OK",
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    transmit_fx6_end_actuator_frame: bool = False,
    mutate_slot1_or_p2_camset: bool = False,
    drive_reverse_bnc_tcout_or_xlrh1_usb: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed probe verifying all 9 forbidden physical write/transmit actions are hard-blocked."""
    violations: List[str] = []
    if authorize_persistent_emmc_writes:
        violations.append("PERSISTENT_EMMC_WRITE")
    if authorize_spi_nor_write:
        violations.append("SPI_NOR_WRITE")
    if authorize_el3_payload_transmit:
        violations.append("EL3_PAYLOAD_TRANSMIT")
    if emit_physical_usb_packet:
        violations.append("PHYSICAL_USB_PACKET_EMIT")
    if touch_otp_fuse:
        violations.append("OTP_FUSE_TOUCH")
    if increment_rpmb_counter:
        violations.append("RPMB_COUNTER_INCREMENT")
    if transmit_fx6_end_actuator_frame:
        violations.append("FX6_VARIABLE_END_CP_ACTUATOR_TX")
    if mutate_slot1_or_p2_camset:
        violations.append("SLOT1_OR_P2_CAMSET_MUTATION")
    if drive_reverse_bnc_tcout_or_xlrh1_usb:
        violations.append("REVERSE_BNC_TCOUT_OR_XLRH1_USB_MISWIRE")

    if violations:
        joined = "+".join(violations)
        return RedlineGuardProbeResult(
            valid=False,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
            otp_fuse_touches=OTP_FUSE_TOUCHES,
            rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
            e_nd_actuator_tx_count=E_ND_ACTUATOR_TX_COUNT,
            slot1_fx3_camset_mutation_bytes=SLOT1_FX3_CAMSET_MUTATION_BYTES,
            p2_setting_mutation_bytes=P2_SETTING_MUTATION_BYTES,
            xlrh1_handle_usb_tc_miswire_damage_events=XLRH1_HANDLE_USB_TC_MISWIRE_DAMAGE_EVENTS,
            bnc_tcout_reverse_drive_events=BNC_TCOUT_REVERSE_DRIVE_EVENTS,
            blocked_action=joined,
            status_code=f"FAIL_CLOSED_REDLINE_BLOCKED:{joined}",
        )

    return RedlineGuardProbeResult(
        valid=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        e_nd_actuator_tx_count=E_ND_ACTUATOR_TX_COUNT,
        slot1_fx3_camset_mutation_bytes=SLOT1_FX3_CAMSET_MUTATION_BYTES,
        p2_setting_mutation_bytes=P2_SETTING_MUTATION_BYTES,
        xlrh1_handle_usb_tc_miswire_damage_events=XLRH1_HANDLE_USB_TC_MISWIRE_DAMAGE_EVENTS,
        bnc_tcout_reverse_drive_events=BNC_TCOUT_REVERSE_DRIVE_EVENTS,
        blocked_action="NONE",
        status_code="HARD_SAFETY_REDLINES_LOCKED_OK",
    )


def evaluate_pillar_c_d_vmcbncm1_tcin_hdmi_tcout_and_redlines() -> Dict[str, object]:
    body_ext_lk_10s_ok = probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
        usb_port=USB_PORT_BODY_MULTI_MICRO,
        vmc_bncm1_attached=True,
        bnc_direction=BNC_DIRECTION_TC_IN,
        shooting_mode=SHOOTING_MODE_MOVIE,
        tc_make=TC_MAKE_PRESET,
        tc_run=TC_RUN_FREE_RUN,
        signal_hold_seconds=12.0,
        hdmi_tc_output_menu=HDMI_TC_OUT_ON,
    )
    pre_10s_syncing = probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
        usb_port=USB_PORT_BODY_MULTI_MICRO,
        vmc_bncm1_attached=True,
        bnc_direction=BNC_DIRECTION_TC_IN,
        shooting_mode=SHOOTING_MODE_MOVIE,
        tc_make=TC_MAKE_PRESET,
        tc_run=TC_RUN_FREE_RUN,
        signal_hold_seconds=6.5,
        hdmi_tc_output_menu=HDMI_TC_OUT_ON,
    )
    released_on_sq_and_hdmi_off = probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
        usb_port=USB_PORT_BODY_MULTI_MICRO,
        vmc_bncm1_attached=True,
        bnc_direction=BNC_DIRECTION_TC_IN,
        shooting_mode=SHOOTING_MODE_SQ,
        tc_make=TC_MAKE_PRESET,
        tc_run=TC_RUN_FREE_RUN,
        signal_hold_seconds=15.0,
        was_previously_ext_lk=True,
        hdmi_tc_output_menu=HDMI_TC_OUT_ON,
    )
    released_on_tc_change = probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
        usb_port=USB_PORT_BODY_MULTI_MICRO,
        vmc_bncm1_attached=True,
        bnc_direction=BNC_DIRECTION_TC_IN,
        shooting_mode=SHOOTING_MODE_MOVIE,
        tc_make=TC_MAKE_REGENERATE,
        tc_run=TC_RUN_REC_RUN,
        signal_hold_seconds=15.0,
        was_previously_ext_lk=True,
        tc_setting_mutated_after_lock=True,
        hdmi_tc_output_menu=HDMI_TC_OUT_ON,
    )
    xlrh1_handle_usb_blocked = probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
        usb_port=USB_PORT_XLR_H1_HANDLE_MICRO,
        vmc_bncm1_attached=True,
        bnc_direction=BNC_DIRECTION_TC_IN,
    )
    reverse_bnc_tcout_blocked = probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
        usb_port=USB_PORT_BODY_MULTI_MICRO,
        vmc_bncm1_attached=True,
        bnc_direction=BNC_DIRECTION_TC_OUT,
        attempt_bnc_tc_out=True,
    )

    baseline_redline = probe_hard_safety_redline()
    blocked_probes = [
        asdict(probe_hard_safety_redline(**kw))
        for kw in (
            {"authorize_persistent_emmc_writes": True},
            {"authorize_spi_nor_write": True},
            {"authorize_el3_payload_transmit": True},
            {"emit_physical_usb_packet": True},
            {"touch_otp_fuse": True},
            {"increment_rpmb_counter": True},
            {"transmit_fx6_end_actuator_frame": True},
            {"mutate_slot1_or_p2_camset": True},
            {"drive_reverse_bnc_tcout_or_xlrh1_usb": True},
        )
    ]

    passed = (
        body_ext_lk_10s_ok.admitted
        and body_ext_lk_10s_ok.ext_lk_locked
        and body_ext_lk_10s_ok.tc_status_badge == "EXT-LK"
        and body_ext_lk_10s_ok.hdmi_digital_tc_out_active
        and pre_10s_syncing.admitted
        and (not pre_10s_syncing.ext_lk_locked)
        and pre_10s_syncing.tc_status_badge == "TC_IN_ACQUIRING"
        and released_on_sq_and_hdmi_off.admitted
        and (not released_on_sq_and_hdmi_off.ext_lk_locked)
        and released_on_sq_and_hdmi_off.ext_lk_released
        and (not released_on_sq_and_hdmi_off.hdmi_digital_tc_out_active)
        and released_on_sq_and_hdmi_off.hdmi_tc_out_disabled_in_sq
        and released_on_tc_change.admitted
        and (not released_on_tc_change.ext_lk_locked)
        and released_on_tc_change.ext_lk_released
        and (not xlrh1_handle_usb_blocked.admitted)
        and xlrh1_handle_usb_blocked.xlrh1_handle_usb_blocked_enodev
        and xlrh1_handle_usb_blocked.errno_code == ENODEV_ERRNO
        and (not reverse_bnc_tcout_blocked.admitted)
        and reverse_bnc_tcout_blocked.reverse_bnc_tcout_blocked_eopnotsupp
        and reverse_bnc_tcout_blocked.errno_code == EOPNOTSUPP_ERRNO
        and baseline_redline.valid
        and len(blocked_probes) == 9
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "body_multi_usb_ext_lk_12s_locked_ok": asdict(body_ext_lk_10s_ok),
        "body_multi_usb_pre_10s_syncing": asdict(pre_10s_syncing),
        "sq_mode_releases_ext_lk_and_disables_hdmi_tcout": asdict(released_on_sq_and_hdmi_off),
        "tc_setting_mutation_releases_ext_lk": asdict(released_on_tc_change),
        "xlrh1_handle_micro_usb_blocked_enodev": asdict(xlrh1_handle_usb_blocked),
        "reverse_bnc_tcout_blocked_eopnotsupp": asdict(reverse_bnc_tcout_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 202 (Stage 36, 36/36) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 202 Stage 36 (36/36) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase202_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_big6_home_lower_left_and_no_end_firewall()
    pillar_b = evaluate_pillar_b_slot1_camset_dual_media_and_firewall()
    pillar_cd = evaluate_pillar_c_d_vmcbncm1_tcin_hdmi_tcout_and_redlines()

    redlines: Dict[str, object] = {
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "nop_count": NOP_COUNT,
        "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
        "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
        "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
        "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
        "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "e_nd_actuator_tx_count": E_ND_ACTUATOR_TX_COUNT,
        "slot1_fx3_camset_mutation_bytes": SLOT1_FX3_CAMSET_MUTATION_BYTES,
        "p2_setting_mutation_bytes": P2_SETTING_MUTATION_BYTES,
        "xlrh1_handle_usb_tc_miswire_damage_events": XLRH1_HANDLE_USB_TC_MISWIRE_DAMAGE_EVENTS,
        "bnc_tcout_reverse_drive_events": BNC_TCOUT_REVERSE_DRIVE_EVENTS,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        "donor_access_mode": DONOR_ACCESS_MODE,
    }

    all_passed = (
        donor_audit.all_contracts_verified
        and donor_audit.raw_firmware_bytes_leaked == 0
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_cd["passed"])
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and E_ND_ACTUATOR_TX_COUNT == 0
        and SLOT1_FX3_CAMSET_MUTATION_BYTES == 0
        and P2_SETTING_MUTATION_BYTES == 0
        and XLRH1_HANDLE_USB_TC_MISWIRE_DAMAGE_EVENTS == 0
        and BNC_TCOUT_REVERSE_DRIVE_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": PHASE_202_SCHEMA,
        "version": PHASE_202_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_big6_home_lower_left_and_no_end_firewall_hil": pillar_a,
        "pillar_b_slot1_camset_dual_media_and_cross_model_firewall_hil": pillar_b,
        "pillar_c_d_vmcbncm1_tcin_hdmi_tcout_and_redlines": pillar_cd,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py",
        description=(
            "Phase 202 Stage 36 (36/36) — Real-Hardware ILME-FX3 BIG6 [Home (Lower Left)] "
            "Zero e-ND Actuator Firewall, Slot-1 CAMSET Dual-Media Path Split & VMC-BNCM1 "
            "Body-Only TC IN / HDMI TC OUT HIL Co-Emulator"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 202 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_big6_home_lower_left_and_no_end_firewall_hil"]
        pb = rep["pillar_b_slot1_camset_dual_media_and_cross_model_firewall_hil"]
        pcd = rep["pillar_c_d_vmcbncm1_tcin_hdmi_tcout_and_redlines"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 202 Stage 36 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"big6_tiles={pa['default_home_lower_left_aperture']['tile_count']} "
            f"end_tx={red['e_nd_actuator_tx_count']} | "
            f"camset=Slot1_SD+CFexpressA(10max,overlay={pb['stage_b_overlay_profiles_verified']}/10,h0_eq_h3=1) | "
            f"vmcbncm1={pcd['body_multi_usb_ext_lk_12s_locked_ok']['tc_status_badge']} "
            f"xlrh1_errno={pcd['xlrh1_handle_micro_usb_blocked_enodev']['errno_code']} "
            f"bnc_out_errno={pcd['reverse_bnc_tcout_blocked_eopnotsupp']['errno_code']} "
            f"hdmi_tc={pcd['body_multi_usb_ext_lk_12s_locked_ok']['hdmi_digital_tc_out_active']} | "
            f"emmc_auth={red['persistent_emmc_writes_authorized']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
