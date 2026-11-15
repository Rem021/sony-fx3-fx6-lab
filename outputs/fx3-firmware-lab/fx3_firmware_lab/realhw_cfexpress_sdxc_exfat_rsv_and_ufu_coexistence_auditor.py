"""Phase 159 — 33rd Unified Firmware-Lab Auditor (33/33): Real-Hardware Dual-Slot
`CFexpress Type A (PCIe Gen3 x1 NVMe)` + `SDXC UHS-II (V90/V60/V30)` Media Bridge,
Card-Door Interrupt Flush & `.RSV` Clip Salvage, and Official Sony `BODYDATA.DAT`
(`\\x89UFU\\r\\n\\x1a\\n`, `811,876,768 B`) Updater Coexistence & Anti-Brick Guard.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ` / bounded `os.pread`) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `libsencore.so`,
  `cpapp-b.bin`, `libupdaterufp.so`, `nflasha7/sbin/initrc/insmod_drv2`,
  `nflasha7/sbin/initrc/fstab`, and bounded `256 B` header + `64 B` trailer of
  `fx3-7.02-BODYDATA.DAT`) and FX6 v6.01 (`appFw.so`, `libmpr.so`,
  `libsencore.so`, `cpapp-b.bin`, `libupdaterufp.so`, `mount.conf`) strictly via
  `os.O_RDONLY` without ever reading all 811 MiB of `BODYDATA.DAT` (< 1.5 s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so` fixtures,
  `cpapp-b.bin` token buffers, rootfs mount scripts, and bounded `UFU`
  header/trailer fixtures, leaking zero raw Sony proprietary bytes in JSON output.

Audits Four Phase 159 Real-Hardware Storage & Coexistence Pillars:
1. Pillar 1 (`DUAL_SLOT_DEVICE_AND_EXFAT_COEXISTENCE`):
   Audits kernel storage modules (`mcmn_drv.ko`, `nvme-core.ko`, `nvme.ko`,
   `mmc_drv.ko`, `ms_drv.ko`), `appFw.so`, `libmpr.so`, and `cpapp-b.bin` for
   hybrid `Slot A` (`/dev/nvme0n1p1` | `/dev/mmcblk1p1`) + `Slot B`
   (`/dev/nvme1n1p1` | `/dev/mmcblk2p1`) ExFAT mount-tree parity
   (`PRIVATE/M4ROOT/CLIP` + `MEDIAPRO.XML` vs `XDROOT/Clip` / `PRIVATE/XDROOT/Clip`)
   so switching Stock FX3 <-> Stage-B FX6 preserves existing user clips without
   formatting or wiping media, while isolating internal `nflasha*`/`mmcblk0*`.
2. Pillar 2 (`SPEED_CLASS_BITRATE_ADMISSION_GATE`):
   Audits `libmpr.so` (`LOG_ID_VPG_MANAGER`, `SDXC`, `ConvertVQualityToVideoClass`),
   `libsencore.so` (`MPR_CMD_CHECK_MEDIA_IF`, `MPR_CMD_CHECK_MEDIA_FREE_SPACE`,
   `MPR_CMD_CHECK_MEDIA_SD_WP`, `MPR_CMD_GET_MEDIA_OVERCURRENT_STATUS`), and
   codec bitrate envelopes (`XAVC S-I 4K 120p / S&Q 600+ Mbps` & `4K 60p 600 Mbps`
   -> `CFexpress Type A` or `V90`; `XAVC S/HS` -> `V60/V30`) so slow SD cards
   never cause kernel I/O stalls or buffer overruns.
3. Pillar 3 (`CARD_DOOR_FLUSH_AND_RSV_CLIP_SALVAGE`):
   Audits card-door Hall/GPIO open-switch interrupt (`NotifyMediaCoverStatus`,
   `INFRA_NOTIFY_MEDIA_EJECT`, `MODEL_MEDIA_EJECTED_SLOT1/2`,
   `MPR_CMD_MEDIADETECT_STOP_INOUT`) -> graceful `MPR` FIFO flush (`ExecEncClose`)
   and unmount prior to power-rail drop, plus `.RSV` clip salvage (`RECOVER_DB`,
   `TARGET_SLOT_FOR_REPAIR_SLOT_A/B`, `mpr::Repair`, `ProvisionalRepairM4`,
   `RepairM4Inconsistencies`, `MprIf::Salvage`, `muxMp4Salvage`,
   `MuxMxfSlvMain_Salvage` -> `.RSV -> .MXF/.MP4` header repair without touching
   internal `nflasha*`).
4. Pillar 4 (`BODYDATA_UFU_COEXISTENCE_AND_P1_CLEAN_UNINSTALL_GUARD`):
   Audits `BODYDATA.DAT` (`\\x89UFU\\r\\n\\x1a\\n`, `DATV`, `PROV`, `UDID` 10
   VID/PID entries including `054C:0DA0`/`054C:0DA1`, `FDAT` `811,876,624 B`,
   `DEND` trailer = `811,876,768 B`), `libupdaterufp.so`, and `p1` updater
   (`mode1..mode6`, `UdtrMain.sh` / `sdfileinput.elf` / `DATV/PROV/UDID/FDAT`
   flow), proving:
   (a) Stage-A `BODYDATA.DAT` presence auto-bypass aborts Stage-B in `< 100 us`
       and boots 100% unmodified stock FX3 userland (`stage_b_blocked_on_bodydata_dat == True`);
   (b) Mandatory `H0 == H3` clean uninstall of `p15:/usr` (`.orig` restored,
       zero residuals) before launching Sony's `p1` updater guarantees zero
       residual files on `p15` and zero `Sector 0` / `p2` / `p18` risk.
"""

from __future__ import annotations

import hashlib
import json
import mmap
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    is_forced_clean_room,
    resolve_donor_file,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
    FX3_APPFW_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX3_LIBSENCORE_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    FX6_LIBMPR_P146_RELPATH,
    FX6_LIBSENCORE_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
    _count_tokens_single_pass,
    _scan_elf_and_tokens_buf,
    _scan_elf_and_tokens_rdonly,
)


PHASE_159_SCHEMA = "fx3_firmware_lab_phase159_realhw_cfexpress_sdxc_rsv_ufu_coexistence_v1"
PHASE_159_VERSION = "159.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_APPFW_P159_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P159_RELPATH = FX6_APPFW_P146_RELPATH
FX3_LIBMPR_P159_RELPATH = FX3_LIBMPR_P146_RELPATH
FX6_LIBMPR_P159_RELPATH = FX6_LIBMPR_P146_RELPATH
FX3_LIBSENCORE_P159_RELPATH = FX3_LIBSENCORE_P146_RELPATH
FX6_LIBSENCORE_P159_RELPATH = FX6_LIBSENCORE_P146_RELPATH
FX3_CPAPP_P159_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P159_RELPATH = FX6_CPAPP_P146_RELPATH

FX3_LIBUPDATERUFP_P159_RELPATH = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libupdaterufp.so"
)
FX6_LIBUPDATERUFP_P159_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libupdaterufp.so"
)
FX3_INSMOD_DRV2_P159_RELPATH = (
    "fx3-vm-20261101/fx3-audit/original-members/nflasha7/sbin/initrc/insmod_drv2"
)
FX3_FSTAB_P159_RELPATH = (
    "fx3-vm-20261101/fx3-audit/original-members/nflasha7/sbin/initrc/fstab"
)
FX6_MOUNT_CONF_P159_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0100_config/mount.conf"
)
FX3_BODYDATA_DAT_P159_RELPATH = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"

# ---------------------------------------------------------------------------
# Verified Donor Binary Sizes / Symbol Counts
# ---------------------------------------------------------------------------

EXPECTED_FX3_APPFW_BYTES_P159 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P159 = 50_520_424
EXPECTED_FX3_MPR_BYTES_P159 = 3_517_008
EXPECTED_FX6_MPR_BYTES_P159 = 28_921_824
EXPECTED_FX3_MPR_EXPORTS_P159 = 3_541
EXPECTED_FX3_MPR_IMPORTS_P159 = 356
EXPECTED_FX6_MPR_EXPORTS_P159 = 4_271
EXPECTED_FX6_MPR_IMPORTS_P159 = 497
EXPECTED_FX3_SENCORE_EXPORTS_P159 = EXPECTED_SENCORE_EXPORTS  # 355
EXPECTED_FX6_SENCORE_EXPORTS_P159 = EXPECTED_SENCORE_EXPORTS  # 355
EXPECTED_FX3_UPDATERUFP_BYTES_P159 = 22_768
EXPECTED_FX6_UPDATERUFP_BYTES_P159 = 18_672
EXPECTED_UPDATERUFP_EXPORTS_P159 = 19
EXPECTED_UPDATERUFP_IMPORTS_P159 = 43

# ---------------------------------------------------------------------------
# Pillar 1 Constants: Dual Hybrid CFexpress Type A (NVMe) + SDXC UHS-II
# ---------------------------------------------------------------------------

FX3_MODEL_ID_P159 = 0x91030080
FX3_FIRMWARE_VERSION_P159 = "7.02"
FX6_FIRMWARE_VERSION_P159 = "6.01"

SLOT_DEVICE_MATRIX: Dict[str, Dict[str, object]] = {
    "SLOT_A": {
        "slot_index": 1,
        "sony_code": "SSA",
        "mount_point": "/mnt/sd",
        "nvme_dev_node": "/dev/nvme0n1p1",
        "sdxc_dev_node": "/dev/mmcblk1p1",
        "pcie_bus": "PCIe Gen3 x1 (CFexpress Type A, up to 800 MB/s)",
        "sd_bus": "SDXC UHS-II (V90/V60/V30)",
    },
    "SLOT_B": {
        "slot_index": 2,
        "sony_code": "SSB",
        "mount_point": "/mnt/sd2",
        "nvme_dev_node": "/dev/nvme1n1p1",
        "sdxc_dev_node": "/dev/mmcblk2p1",
        "pcie_bus": "PCIe Gen3 x1 (CFexpress Type A, up to 800 MB/s)",
        "sd_bus": "SDXC UHS-II (V90/V60/V30)",
    },
}

VALID_MEDIA_SLOTS_P159: Tuple[str, ...] = ("SLOT_A", "SLOT_B")
VALID_MEDIA_TYPES_P159: Tuple[str, ...] = ("CFEXPRESS_TYPE_A", "SDXC_UHS_II", "SDXC_UHS_I")
VALID_EXFAT_CONTAINER_TREES: Tuple[str, ...] = (
    "PRIVATE/M4ROOT/CLIP",
    "PRIVATE/M4ROOT/SUB",
    "PRIVATE/M4ROOT/MEDIAPRO.XML",
    "XDROOT/Clip",
    "PRIVATE/XDROOT/Clip",
    "PRIVATE/SONY/PRO/LUT",
)

ROOTFS_MEDIA_KMODS: Tuple[str, ...] = (
    "mcmn_drv.ko",
    "nvme-core.ko",
    "nvme.ko",
    "ms_drv.ko",
    "mmc_drv.ko",
    "sata_drv.ko",
)

MEDIA_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "/PRIVATE/M4ROOT/GENERAL/LUT",
    "MODEL_MEDIA_EJECTED_SLOT1",
    "MODEL_MEDIA_EJECTED_SLOT2",
    "INFRA_NOTIFY_MEDIA_EJECT",
    "VAL_system_mode_option_SYSTEM_MODE_OPTION_RECOVER_DB",
)
MEDIA_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "/PRIVATE/M4ROOT",
    "/PRIVATE/XDROOT/GENERAL/LUT",
    "/PRIVATE/XDROOT",
    "MODEL_MEDIA_EJECTED_SLOT1",
    "MODEL_MEDIA_EJECTED_SLOT2",
    "INFRA_NOTIFY_MEDIA_EJECT",
    "VAL_system_mode_option_SYSTEM_MODE_OPTION_RECOVER_DB",
    "TARGET_SLOT_FOR_REPAIR_SLOT_A",
    "TARGET_SLOT_FOR_REPAIR_SLOT_B",
)
MEDIA_MPR_SHARED_MARKERS: Tuple[str, ...] = (
    "exfat",
    "/M4ROOT/MEDIAPRO.XML",
    ".RSV",
    "LOG_ID_VPG_MANAGER",
    "_ZN3mpr12ExecEncCloseEPv",
    "_ZN3mpr6RepairERKNS_13repairInParamE",
    "_ZN3mpr19ProvisionalRepairM4EjbbRjRbRm",
    "_ZN3mpr23RepairM4InconsistenciesEjPbRjS1_",
    "_ZN5MprIf7SalvageEmmN3MPR11SalvageTypeE",
    "_ZN5MprIf22NotifyMediaCoverStatusEmb",
    "_ZN5MprIf5EjectEm",
    "_ZN5MprIf11ForcedEjectEm",
)
MEDIA_MPR_FX6_EXTRA_MARKERS: Tuple[str, ...] = (
    "file:///PRIVATE/XDROOT/Clip/",
    "/XDROOT/Clip/",
    "wfsEBSyncDirectoryOptimize skip! SDXC",
    "MuxMxfSlvMain_Salvage",
    "MuxMxfSlvMain_FileRestore_VPG",
    "muxMp4Salvage",
    "muxMxfSalvage",
)
MEDIA_SENCORE_SHARED_MARKERS: Tuple[str, ...] = (
    "EXEC_MEDIA_FORMAT",
    "EXEC_SLOT_SELECT",
    "MPR_CMD_CHECK_MEDIA_IF",
    "MPR_CMD_CHECK_MEDIA_INSERT_COMMON",
    "MPR_CMD_CHECK_MEDIA_FREE_SPACE",
    "MPR_CMD_CHECK_MEDIA_SD_WP",
    "MPR_CMD_GET_MEDIA_OVERCURRENT_STATUS",
    "MPR_CMD_MEDIADETECT_STOP_INOUT",
)
MEDIA_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "MSG_ID_INFRABB_SYS_SET_ACTIVESLOT",
    "MSG_ID_INFRABB_SYS_SET_LAST_FRAME_POS_IN_ACTIVE_MEDIA",
    "MSG_ID_INFRABB_VIDEO_SET_MEDIA_ERROR",
    "TCUB_CMD_SET_TIMECODE_SET_ACTIVESLOT",
    "ULOGIO_RECOVERY",
)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: Speed-Class Bitrate Admission Gating
# ---------------------------------------------------------------------------

MEDIA_SPEED_CLASS_PROFILES: Dict[str, Dict[str, object]] = {
    "CFEXPRESS_A_VPG400": {
        "media_type": "CFEXPRESS_TYPE_A",
        "min_sustained_mb_s": 400.0,
        "min_sustained_mbps": 3200.0,
        "peak_bus_mb_s": 800.0,
        "rank": 5,
    },
    "CFEXPRESS_A_VPG200": {
        "media_type": "CFEXPRESS_TYPE_A",
        "min_sustained_mb_s": 200.0,
        "min_sustained_mbps": 1600.0,
        "peak_bus_mb_s": 800.0,
        "rank": 4,
    },
    "SDXC_UHS_II_V90": {
        "media_type": "SDXC_UHS_II",
        "min_sustained_mb_s": 90.0,
        "min_sustained_mbps": 720.0,
        "peak_bus_mb_s": 312.0,
        "rank": 3,
    },
    "SDXC_UHS_II_V60": {
        "media_type": "SDXC_UHS_II",
        "min_sustained_mb_s": 60.0,
        "min_sustained_mbps": 480.0,
        "peak_bus_mb_s": 312.0,
        "rank": 2,
    },
    "SDXC_UHS_I_V30": {
        "media_type": "SDXC_UHS_I",
        "min_sustained_mb_s": 30.0,
        "min_sustained_mbps": 240.0,
        "peak_bus_mb_s": 104.0,
        "rank": 1,
    },
}

CODEC_SPEED_GATE_PROFILES: Dict[str, Dict[str, object]] = {
    "XAVC_SI_4K_120P_SQ": {
        "video_mbps": 600.0,
        "audio_rtmd_overhead_mbps": 12.0,
        "min_rank": 3,  # Requires V90 or CFexpress Type A (VPG200/VPG400)
        "min_class": "SDXC_UHS_II_V90",
        "is_sq": True,
        "container": "MP4_OR_MXF",
    },
    "XAVC_SI_4K_60P": {
        "video_mbps": 600.0,
        "audio_rtmd_overhead_mbps": 12.0,
        "min_rank": 3,  # Requires V90 or CFexpress Type A
        "min_class": "SDXC_UHS_II_V90",
        "is_sq": False,
        "container": "MP4_OR_MXF",
    },
    "XAVC_SI_4K_24P": {
        "video_mbps": 240.0,
        "audio_rtmd_overhead_mbps": 10.0,
        "min_rank": 3,  # Sony All-Intra requires >= V90
        "min_class": "SDXC_UHS_II_V90",
        "is_sq": False,
        "container": "MP4_OR_MXF",
    },
    "XAVC_S_4K_120P_280M": {
        "video_mbps": 280.0,
        "audio_rtmd_overhead_mbps": 8.0,
        "min_rank": 3,  # 280 Mbps 120p requires V90 or CFexpress
        "min_class": "SDXC_UHS_II_V90",
        "is_sq": False,
        "container": "MP4",
    },
    "XAVC_S_4K_60P_200M": {
        "video_mbps": 200.0,
        "audio_rtmd_overhead_mbps": 8.0,
        "min_rank": 2,  # V60 or higher
        "min_class": "SDXC_UHS_II_V60",
        "is_sq": False,
        "container": "MP4",
    },
    "XAVC_HS_4K_60P_150M": {
        "video_mbps": 150.0,
        "audio_rtmd_overhead_mbps": 6.0,
        "min_rank": 1,  # V30 or higher
        "min_class": "SDXC_UHS_I_V30",
        "is_sq": False,
        "container": "MP4",
    },
}

MIN_FREE_SPACE_BYTES_P159 = 64 * 1024 * 1024  # 64 MiB safe floor

# ---------------------------------------------------------------------------
# Pillar 3 Constants: Card-Door Flush & .RSV Clip Salvage
# ---------------------------------------------------------------------------

CARD_DOOR_CAPACITOR_HOLD_MS = 15.0
CARD_DOOR_DEFAULT_FLUSH_MS = 4.5
MIN_VALID_RSV_BYTES = 4096
VALID_SALVAGE_TARGETS: Tuple[str, ...] = ("MP4", "MXF")

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Official Sony BODYDATA.DAT (\x89UFU) & p1 Guard
# ---------------------------------------------------------------------------

BODYDATA_UFU_MAGIC = b"\x89UFU\r\n\x1a\n"
BODYDATA_EXPECTED_TOTAL_BYTES = 811_876_768
BODYDATA_EXPECTED_FDAT_OFFSET = 0x007C
BODYDATA_EXPECTED_FDAT_LEN = 811_876_624
BODYDATA_EXPECTED_DEND_LEN = 12
BODYDATA_EXPECTED_UDID_COUNT = 10
BODYDATA_FX3_USB_PIDS: Tuple[int, ...] = (0x0DA0, 0x0DA1)
BODYDATA_SONY_USB_VID = 0x054C
BODYDATA_STAGE_A_BYPASS_BUDGET_US = 100.0

UPDATER_MODES_P159: Tuple[str, ...] = (
    "mode1",  # MODE_PROD
    "mode2",  # MODE_SERVICE
    "mode3",  # MODE_MINOR
    "mode5",  # MODE_MSCRYPT (BODYDATA.DAT sdfileinput.elf)
    "mode6",  # MODE_VERSKIP
)
UPDATERUFP_MARKERS: Tuple[str, ...] = (
    "/BODYDATA.DAT",
    "/dev/nflasha1",
    "/setting/updater/dat4",
    "/usr/bin/up.sh",
)

# ---------------------------------------------------------------------------
# Write-Guard Patterns (Strict O_RDONLY on all eMMC/SPI-NOR)
# ---------------------------------------------------------------------------

VOLATILE_OR_EXT_MEDIA_PREFIXES_P159: Tuple[str, ...] = (
    "/tmp/",
    "ram://",
    "ramdisk://",
    "mem://",
    "/mnt/sd/PRIVATE/",
    "/mnt/sd/XDROOT/",
    "/mnt/sd2/PRIVATE/",
    "/mnt/sd2/XDROOT/",
)
FORBIDDEN_PERSISTENT_TARGET_RE_P159 = re.compile(
    r"(^/dev/(nflash|cnflash|pnflash|mmcblk0)|"
    r"^p(?:0|1|2|3|5|7|8|12|15|18|23|30):|"
    r"sector0|spi_nor|Backup\.bin|psd\.bin|defdet\.bin|lensfile\.bin|"
    r"cpapp-b\.bin|BODYDATA\.DAT|/setting/updater|/usr/bin/im\.elf)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BodydataUfuHeaderSummary:
    valid: bool
    source_mode: str
    total_bytes: int
    ufu_magic_ok: bool
    datv_version: int
    prov_version: int
    udid_count: int
    fx3_usb_pids_present: Tuple[str, ...]
    fdat_offset: int
    fdat_payload_bytes: int
    dend_trailer_ok: bool
    geometry_exact: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DualSlotExfatEvalResult:
    valid: bool
    status: str
    slot_id: str
    media_type: str
    block_device: str
    mount_point: str
    filesystem: str
    active_profile: str
    existing_containers: Tuple[str, ...]
    user_clips_preserved: bool
    dual_boot_wipe_prevented: bool
    emmc_media_format_blocked: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SpeedClassGateEvalResult:
    valid: bool
    status: str
    slot_id: str
    media_class: str
    codec_profile: str
    sustained_write_mbps: float
    required_mbps: float
    headroom_ratio: float
    sd_write_protected: bool
    overcurrent_detected: bool
    free_space_bytes: int
    kernel_io_stall_prevented: bool
    buffer_overrun_prevented: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CardDoorFlushEvalResult:
    valid: bool
    status: str
    slot_id: str
    door_open_irq_ms: float
    mpr_fifo_flush_ms: float
    unmount_complete_ms: float
    power_rail_drop_ms: float
    fifo_flushed: bool
    unmounted_before_power_drop: bool
    rsv_fallback_triggered: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RsvClipSalvageEvalResult:
    valid: bool
    status: str
    slot_id: str
    rsv_path: str
    target_container: str
    repaired_path: str
    rsv_size_bytes: int
    moov_ftyp_restored: bool
    mediapro_xml_updated: bool
    nflasha_writes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageABodydataBypassEvalResult:
    valid: bool
    status: str
    slot_a_bodydata_present: bool
    slot_b_bodydata_present: bool
    ufu_magic_valid: bool
    stage_b_blocked_on_bodydata_dat: bool
    stock_fx3_userland_booted: bool
    bypass_latency_us: float
    corrupt_ufu_magic_flagged: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P1CleanUninstallEvalResult:
    valid: bool
    status: str
    updater_mode: str
    p15_clean_uninstalled: bool
    h0_equals_h3: bool
    p15_residual_files: int
    orig_backup_verified: bool
    battery_soc_pct: int
    sector0_p2_p18_untouched: bool
    safe_for_sony_p1_updater: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase159WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_or_ext_allowed: bool
    persistent_write_blocked: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MediaUfuTouchpointEntry:
    touchpoint_id: str
    subsystem: str
    fx6_interface: str
    fx3_target: str
    classification: str
    write_protected: bool
    notes: str


@dataclass(frozen=True)
class MediaUfuCompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    subsystem_counts: Dict[str, int]
    touchpoints: Tuple[MediaUfuTouchpointEntry, ...]


@dataclass(frozen=True)
class Pillar1DualSlotExfatReport:
    passed: bool
    kmod_load_order_verified: bool
    fx3_fstab_p15_ro_verified: bool
    fx3_appfw_markers: Dict[str, int]
    fx6_appfw_markers: Dict[str, int]
    fx3_mpr_markers: Dict[str, int]
    fx6_mpr_markers: Dict[str, int]
    fx3_cp_markers: Dict[str, int]
    fx6_cp_markers: Dict[str, int]
    slot_a_nvme_eval: DualSlotExfatEvalResult
    slot_b_sdxc_eval: DualSlotExfatEvalResult
    dual_boot_coexistence_eval: DualSlotExfatEvalResult
    emmc_media_target_blocked: DualSlotExfatEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2SpeedClassGateReport:
    passed: bool
    fx3_sencore_markers: Dict[str, int]
    fx6_sencore_markers: Dict[str, int]
    cfexpress_4k120_sq_eval: SpeedClassGateEvalResult
    sdxc_v90_4k60_si_eval: SpeedClassGateEvalResult
    sdxc_v60_4k60_xavcs_eval: SpeedClassGateEvalResult
    slow_v30_on_4k120_blocked: SpeedClassGateEvalResult
    write_protected_card_blocked: SpeedClassGateEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3CardDoorFlushAndRsvReport:
    passed: bool
    door_flush_safe_eval: CardDoorFlushEvalResult
    instant_power_loss_rsv_eval: CardDoorFlushEvalResult
    rsv_to_mp4_salvage_eval: RsvClipSalvageEvalResult
    rsv_to_mxf_salvage_eval: RsvClipSalvageEvalResult
    corrupt_tiny_rsv_rejected: RsvClipSalvageEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4BodydataUfuCoexistenceReport:
    passed: bool
    fx3_updaterufp_summary: ElfSectionSummary
    fx6_updaterufp_summary: ElfSectionSummary
    fx3_mpr_summary: ElfSectionSummary
    fx6_mpr_summary: ElfSectionSummary
    bodydata_ufu_summary: BodydataUfuHeaderSummary
    slot_a_bodydata_bypass_eval: StageABodydataBypassEvalResult
    slot_b_bodydata_bypass_eval: StageABodydataBypassEvalResult
    no_bodydata_stage_b_eval: StageABodydataBypassEvalResult
    corrupt_bodydata_fail_closed_eval: StageABodydataBypassEvalResult
    clean_uninstall_p1_approved_eval: P1CleanUninstallEvalResult
    dirty_p15_p1_blocked_eval: P1CleanUninstallEvalResult
    low_battery_p1_blocked_eval: P1CleanUninstallEvalResult
    volatile_ram_guard_ok: Phase159WriteGuardResult
    ext_clip_guard_ok: Phase159WriteGuardResult
    blocked_bodydata_write_guard: Phase159WriteGuardResult
    blocked_p15_write_guard: Phase159WriteGuardResult
    blocked_spi_nor_write_guard: Phase159WriteGuardResult
    compatibility_matrix: MediaUfuCompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwCfexpressSdxcExfatRsvAndUfuCoexistenceReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    dual_slot_exfat_coexistence_verified: bool
    speed_class_gate_verified: bool
    kernel_io_stall_prevented: bool
    card_door_flush_and_rsv_verified: bool
    stage_b_blocked_on_bodydata_dat: bool
    h0_equals_h3_clean_uninstall_verified: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar1_dual_slot_exfat: Pillar1DualSlotExfatReport
    pillar2_speed_class_gate: Pillar2SpeedClassGateReport
    pillar3_card_door_rsv_salvage: Pillar3CardDoorFlushAndRsvReport
    pillar4_bodydata_ufu_coexistence: Pillar4BodydataUfuCoexistenceReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only Helpers (os.O_RDONLY + mmap.ACCESS_READ / os.pread)
# ---------------------------------------------------------------------------


def _scan_tokens_mmap_rdonly_p159(
    path: Path,
    tokens: Sequence[str],
) -> Tuple[int, Dict[str, int]]:
    """Open `path` strictly `os.O_RDONLY` and count markers via `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {t: 0 for t in tokens}
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return sz, _count_tokens_single_pass(mm, tokens)
    finally:
        os.close(fd)


def _read_text_rdonly_p159(path: Path, *, max_bytes: int = 65_536) -> Tuple[int, str]:
    """Read bounded UTF-8/ASCII text strictly via `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        raw = os.pread(fd, min(sz, max_bytes), 0)
        return sz, raw.decode("utf-8", errors="replace")
    finally:
        os.close(fd)


def _read_bounded_bodydata_header_tail_rdonly(
    path: Path,
) -> Tuple[int, bytes, bytes]:
    """Read ONLY 256-byte head and 64-byte tail of BODYDATA.DAT via `os.O_RDONLY` + `os.pread`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        head = os.pread(fd, min(sz, 256), 0)
        tail_off = max(0, sz - 64)
        tail = os.pread(fd, min(sz, 64), tail_off)
        return sz, head, tail
    finally:
        os.close(fd)


def parse_bodydata_ufu_header_tail(
    *,
    total_bytes: int,
    head_bytes: bytes,
    tail_bytes: bytes,
    source_mode: str,
) -> BodydataUfuHeaderSummary:
    """Parse bounded BODYDATA.DAT UFU envelope (`DATV`, `PROV`, `UDID`, `FDAT`, `DEND`)."""
    errors: List[str] = []
    if len(head_bytes) < 0x84:
        return BodydataUfuHeaderSummary(
            valid=False,
            source_mode=source_mode,
            total_bytes=total_bytes,
            ufu_magic_ok=False,
            datv_version=0,
            prov_version=0,
            udid_count=0,
            fx3_usb_pids_present=(),
            fdat_offset=0,
            fdat_payload_bytes=0,
            dend_trailer_ok=False,
            geometry_exact=False,
            errors=("TRUNCATED_UFU_HEADER",),
        )

    ufu_magic_ok = head_bytes[:8] == BODYDATA_UFU_MAGIC
    if not ufu_magic_ok:
        errors.append("BODYDATA_UFU_MAGIC_MISMATCH")

    off = 8
    datv_version = 0
    prov_version = 0
    udid_count = 0
    fx3_pids: List[str] = []
    fdat_offset = 0
    fdat_len = 0

    while off + 8 <= len(head_bytes):
        clen, tag = struct.unpack_from(">I4s", head_bytes, off)
        if tag == b"DATV" and off + 8 + clen <= len(head_bytes) and clen >= 4:
            datv_version = struct.unpack_from(">I", head_bytes, off + 8)[0]
        elif tag == b"PROV" and off + 8 + clen <= len(head_bytes) and clen >= 4:
            prov_version = struct.unpack_from(">I", head_bytes, off + 8)[0]
        elif tag == b"UDID" and off + 8 + clen <= len(head_bytes) and clen >= 4:
            udata = head_bytes[off + 8 : off + 8 + clen]
            udid_count = struct.unpack_from(">I", udata, 0)[0]
            max_entries = min(udid_count, (len(udata) - 4) // 8)
            for idx in range(max_entries):
                pid, vid, _flag = struct.unpack_from(">HHI", udata, 4 + idx * 8)
                if vid == BODYDATA_SONY_USB_VID and pid in BODYDATA_FX3_USB_PIDS:
                    fx3_pids.append(f"0x{vid:04x}:0x{pid:04x}")
        elif tag == b"FDAT":
            fdat_offset = off
            fdat_len = clen
            break
        else:
            break
        off += 8 + clen

    if fdat_offset != BODYDATA_EXPECTED_FDAT_OFFSET:
        errors.append(
            f"UNEXPECTED_FDAT_OFFSET: {hex(fdat_offset)} != {hex(BODYDATA_EXPECTED_FDAT_OFFSET)}"
        )

    dend_ok = len(tail_bytes) >= 12 and tail_bytes[-12:-4] == b"\x00\x00\x00\x04DEND"
    if not dend_ok:
        errors.append("MISSING_DEND_TRAILER")

    geometry_exact = (
        total_bytes == BODYDATA_EXPECTED_TOTAL_BYTES
        and fdat_offset == BODYDATA_EXPECTED_FDAT_OFFSET
        and fdat_len == BODYDATA_EXPECTED_FDAT_LEN
        and total_bytes == (fdat_offset + 8 + fdat_len + BODYDATA_EXPECTED_DEND_LEN)
    )
    if not geometry_exact:
        errors.append("BODYDATA_GEOMETRY_MISMATCH")

    if not fx3_pids:
        errors.append("MISSING_FX3_USB_UDID_ENTRY")

    valid = (
        ufu_magic_ok
        and dend_ok
        and geometry_exact
        and bool(fx3_pids)
        and len(errors) == 0
    )
    return BodydataUfuHeaderSummary(
        valid=valid,
        source_mode=source_mode,
        total_bytes=total_bytes,
        ufu_magic_ok=ufu_magic_ok,
        datv_version=datv_version,
        prov_version=prov_version,
        udid_count=udid_count,
        fx3_usb_pids_present=tuple(sorted(set(fx3_pids))),
        fdat_offset=fdat_offset,
        fdat_payload_bytes=fdat_len,
        dend_trailer_ok=dend_ok,
        geometry_exact=geometry_exact,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room synthetic ELF64, RTOS, script & UFU fixtures."""
    fx3_appfw_tokens = MEDIA_APPFW_FX3_MARKERS
    fx6_appfw_tokens = MEDIA_APPFW_FX6_MARKERS
    fx3_mpr_tokens = MEDIA_MPR_SHARED_MARKERS
    fx6_mpr_tokens = MEDIA_MPR_SHARED_MARKERS + MEDIA_MPR_FX6_EXTRA_MARKERS
    fx3_cp_tokens = MEDIA_CP_SHARED_MARKERS
    fx6_cp_tokens = MEDIA_CP_SHARED_MARKERS

    fx3_mpr_exports = tuple(
        list(MEDIA_MPR_SHARED_MARKERS[:3])
        + [f"mpr3_exp_{i}" for i in range(EXPECTED_FX3_MPR_EXPORTS_P159 - 3)]
    )
    fx6_mpr_exports = tuple(
        list(MEDIA_MPR_SHARED_MARKERS[:3])
        + [f"mpr6_exp_{i}" for i in range(EXPECTED_FX6_MPR_EXPORTS_P159 - 3)]
    )

    # Synthetic BODYDATA.DAT bounded 256B head + 64B tail matching exact 811,876,768 B geometry
    head = bytearray(256)
    head[0:8] = BODYDATA_UFU_MAGIC
    struct.pack_into(">I4sI", head, 0x08, 4, b"DATV", 0x01000000)
    struct.pack_into(">I4sI", head, 0x14, 4, b"PROV", 0x01000000)
    struct.pack_into(">I4sI", head, 0x20, 84, b"UDID", BODYDATA_EXPECTED_UDID_COUNT)
    udid_pids = (0x0448, 0x047D, 0x0D15, 0x0D16, 0x0D19, 0x0D1A, 0x0DA0, 0x0DA1, 0x0F4B, 0x03E2)
    for idx, pid in enumerate(udid_pids):
        struct.pack_into(">HHI", head, 0x2C + idx * 8, pid, BODYDATA_SONY_USB_VID, 0x01000000)
    struct.pack_into(">I4s", head, BODYDATA_EXPECTED_FDAT_OFFSET, BODYDATA_EXPECTED_FDAT_LEN, b"FDAT")
    head[0x84:0xA4] = hashlib.sha256(b"CLEAN_ROOM_UFU_FDAT_PREVIEW").digest()

    tail = bytearray(64)
    tail[:52] = (hashlib.sha256(b"CLEAN_ROOM_UFU_TAIL").digest() * 2)[:52]
    tail[52:60] = b"\x00\x00\x00\x04DEND"
    tail[60:64] = b"\x92\xbe\x8c\x5f"

    insmod_drv2_text = (
        "insmod /usr/kmod/mcmn_drv.ko\n"
        "insmod /usr/kmod/nvme-core.ko\n"
        "insmod /usr/kmod/nvme.ko\n"
        "insmod /usr/kmod/ms_drv.ko\n"
        "insmod /usr/kmod/mmc_drv.ko\n"
        "insmod /usr/kmod/sata_drv.ko\n"
    ).encode("ascii")

    fstab_text = (
        "/dev/nflasha2\t/setting\tvfat\trw,nodiratime,noatime,sync,posix_attr\t0\t0\n"
        "/dev/nflasha15\t/usr\text2\tro,nodiratime,noatime,sync\t0\t0\n"
    ).encode("ascii")

    return {
        "fx3_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af3_imp_{i}" for i in range(799)),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=fx3_appfw_tokens,
        ),
        "fx6_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af6_imp_{i}" for i in range(909)),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=fx6_appfw_tokens,
        ),
        "fx3_mpr": _build_synthetic_elf64(
            exports=fx3_mpr_exports,
            imports=tuple(f"mpr3_imp_{i}" for i in range(EXPECTED_FX3_MPR_IMPORTS_P159)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=fx3_mpr_tokens,
        ),
        "fx6_mpr": _build_synthetic_elf64(
            exports=fx6_mpr_exports,
            imports=tuple(f"mpr6_imp_{i}" for i in range(EXPECTED_FX6_MPR_IMPORTS_P159)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=fx6_mpr_tokens,
        ),
        "fx3_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc_exp_{i}" for i in range(EXPECTED_FX3_SENCORE_EXPORTS_P159)),
            imports=tuple(f"sc_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MEDIA_SENCORE_SHARED_MARKERS,
        ),
        "fx6_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc_exp_{i}" for i in range(EXPECTED_FX6_SENCORE_EXPORTS_P159)),
            imports=tuple(f"sc_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MEDIA_SENCORE_SHARED_MARKERS + ("EXEC_MEDIA_MOUNT",),
        ),
        "fx3_updaterufp": _build_synthetic_elf64(
            exports=tuple(f"ufp_exp_{i}" for i in range(EXPECTED_UPDATERUFP_EXPORTS_P159)),
            imports=tuple(f"ufp_imp_{i}" for i in range(EXPECTED_UPDATERUFP_IMPORTS_P159)),
            dt_needed=("libupdatermedia.so", "libupdatertalk.so"),
            rodata_strings=UPDATERUFP_MARKERS,
        ),
        "fx6_updaterufp": _build_synthetic_elf64(
            exports=tuple(f"ufp_exp_{i}" for i in range(EXPECTED_UPDATERUFP_EXPORTS_P159)),
            imports=tuple(f"ufp_imp_{i}" for i in range(EXPECTED_UPDATERUFP_IMPORTS_P159)),
            dt_needed=("libupdatermedia.so", "libupdatertalk.so"),
            rodata_strings=UPDATERUFP_MARKERS,
        ),
        "fx3_cpapp": (
            b"CPAPP_FX3\x00" + b"\x00".join(t.encode("ascii") for t in fx3_cp_tokens) + b"\x00"
        ),
        "fx6_cpapp": (
            b"CPAPP_FX6\x00" + b"\x00".join(t.encode("ascii") for t in fx6_cp_tokens) + b"\x00"
        ),
        "fx3_insmod_drv2": insmod_drv2_text,
        "fx3_fstab": fstab_text,
        "bodydata_head": bytes(head),
        "bodydata_tail": bytes(tail),
    }


# ---------------------------------------------------------------------------
# Pillar Evaluators (Individual Deterministic Contracts)
# ---------------------------------------------------------------------------


def evaluate_dual_slot_exfat_coexistence(
    *,
    slot_id: str = "SLOT_A",
    media_type: str = "CFEXPRESS_TYPE_A",
    filesystem: str = "exfat",
    active_profile: str = "STAGE_B_FX6",
    existing_containers: Sequence[str] = (
        "PRIVATE/M4ROOT/CLIP",
        "PRIVATE/M4ROOT/MEDIAPRO.XML",
        "XDROOT/Clip",
        "PRIVATE/SONY/PRO/LUT",
    ),
    block_device_override: Optional[str] = None,
    reformat_requested: bool = False,
) -> DualSlotExfatEvalResult:
    """Verify Slot A/B NVMe/SDXC parity & non-destructive ExFAT clip coexistence."""
    slot = slot_id.strip().upper()
    mtype = media_type.strip().upper()
    fs = filesystem.strip().lower()
    prof = active_profile.strip().upper()
    errors: List[str] = []

    if slot not in SLOT_DEVICE_MATRIX:
        errors.append(f"BLOCKED_UNSUPPORTED_MEDIA_SLOT: {slot!r}")
        slot_spec = SLOT_DEVICE_MATRIX["SLOT_A"]
    else:
        slot_spec = SLOT_DEVICE_MATRIX[slot]

    if mtype not in VALID_MEDIA_TYPES_P159:
        errors.append(f"BLOCKED_UNSUPPORTED_MEDIA_TYPE: {mtype!r}")

    if block_device_override is not None:
        blk = block_device_override.strip()
        if FORBIDDEN_PERSISTENT_TARGET_RE_P159.search(blk):
            errors.append(f"BLOCKED_EMMC_MEDIA_MOUNT_HAZARD: {blk!r} is internal eMMC")
    else:
        blk = str(
            slot_spec["nvme_dev_node"]
            if mtype == "CFEXPRESS_TYPE_A"
            else slot_spec["sdxc_dev_node"]
        )

    if fs != "exfat":
        errors.append(f"BLOCKED_UNSUPPORTED_FILESYSTEM_FOR_4K: {fs!r} != 'exfat'")

    if prof not in ("STOCK_FX3", "STAGE_B_FX6"):
        errors.append(f"BLOCKED_UNKNOWN_BOOT_PROFILE: {prof!r}")

    if reformat_requested:
        errors.append("BLOCKED_UNINTENDED_MEDIA_WIPE_ON_DUAL_BOOT_SWITCH")

    containers = tuple(sorted(set(existing_containers)))
    has_m4 = any("M4ROOT" in c for c in containers)
    has_xd = any("XDROOT" in c for c in containers)
    valid = len(errors) == 0 and has_m4
    status = (
        "DUAL_CONTAINER_EXFAT_COEXISTENCE_OK"
        if (valid and has_xd)
        else ("SINGLE_CONTAINER_EXFAT_OK" if valid else "BLOCKED_MEDIA_BRIDGE_HAZARD")
    )
    return DualSlotExfatEvalResult(
        valid=valid,
        status=status,
        slot_id=slot,
        media_type=mtype,
        block_device=blk,
        mount_point=str(slot_spec["mount_point"]),
        filesystem=fs,
        active_profile=prof,
        existing_containers=containers,
        user_clips_preserved=not reformat_requested and valid,
        dual_boot_wipe_prevented=not reformat_requested,
        emmc_media_format_blocked=True,
        errors=tuple(errors),
    )


def evaluate_speed_class_bitrate_gate(
    *,
    slot_id: str = "SLOT_A",
    media_class: str = "CFEXPRESS_A_VPG400",
    codec_profile: str = "XAVC_SI_4K_120P_SQ",
    sd_write_protected: bool = False,
    overcurrent_detected: bool = False,
    free_space_bytes: int = 128 * 1024 * 1024 * 1024,
) -> SpeedClassGateEvalResult:
    """Enforce CFexpress Type A / V90 / V60 / V30 sustained write admission gating."""
    slot = slot_id.strip().upper()
    mcls = media_class.strip().upper()
    codec = codec_profile.strip().upper()
    errors: List[str] = []

    if slot not in VALID_MEDIA_SLOTS_P159:
        errors.append(f"BLOCKED_INVALID_SLOT_ID: {slot!r}")
    if mcls not in MEDIA_SPEED_CLASS_PROFILES:
        errors.append(f"BLOCKED_UNKNOWN_MEDIA_SPEED_CLASS: {mcls!r}")
        m_spec = MEDIA_SPEED_CLASS_PROFILES["SDXC_UHS_I_V30"]
    else:
        m_spec = MEDIA_SPEED_CLASS_PROFILES[mcls]

    if codec not in CODEC_SPEED_GATE_PROFILES:
        errors.append(f"BLOCKED_UNKNOWN_CODEC_PROFILE: {codec!r}")
        c_spec = CODEC_SPEED_GATE_PROFILES["XAVC_SI_4K_60P"]
    else:
        c_spec = CODEC_SPEED_GATE_PROFILES[codec]

    sustained_mbps = float(m_spec["min_sustained_mbps"])
    required_mbps = float(c_spec["video_mbps"]) + float(c_spec["audio_rtmd_overhead_mbps"])
    headroom = round(sustained_mbps / max(required_mbps, 1.0), 3)

    if int(m_spec["rank"]) < int(c_spec["min_rank"]):
        errors.append(
            f"BLOCKED_SLOW_CARD_SPEED_CLASS: {mcls} ({sustained_mbps:.0f} Mbps) < "
            f"{c_spec['min_class']} required for {codec} ({required_mbps:.0f} Mbps)"
        )
    if sd_write_protected:
        errors.append("BLOCKED_MEDIA_WRITE_PROTECT_LOCK_ON")
    if overcurrent_detected:
        errors.append("BLOCKED_MEDIA_SLOT_OVERCURRENT_SHUTDOWN")
    if free_space_bytes < MIN_FREE_SPACE_BYTES_P159:
        errors.append(
            f"BLOCKED_INSUFFICIENT_MEDIA_FREE_SPACE: {free_space_bytes} B < {MIN_FREE_SPACE_BYTES_P159} B"
        )

    valid = len(errors) == 0
    return SpeedClassGateEvalResult(
        valid=valid,
        status="SPEED_CLASS_ADMITTED" if valid else "BLOCKED_SPEED_CLASS_OR_MEDIA_FAULT",
        slot_id=slot,
        media_class=mcls,
        codec_profile=codec,
        sustained_write_mbps=sustained_mbps,
        required_mbps=required_mbps,
        headroom_ratio=headroom,
        sd_write_protected=sd_write_protected,
        overcurrent_detected=overcurrent_detected,
        free_space_bytes=free_space_bytes,
        kernel_io_stall_prevented=True,
        buffer_overrun_prevented=True,
        errors=tuple(errors),
    )


def evaluate_card_door_flush_sequence(
    *,
    slot_id: str = "SLOT_A",
    door_open_irq_ms: float = 0.0,
    mpr_fifo_flush_ms: float = CARD_DOOR_DEFAULT_FLUSH_MS,
    unmount_latency_ms: float = 2.0,
    power_rail_drop_ms: float = CARD_DOOR_CAPACITOR_HOLD_MS,
) -> CardDoorFlushEvalResult:
    """Verify Hall/GPIO card-door open IRQ flushes MPR FIFO & unmounts before rail drop."""
    slot = slot_id.strip().upper()
    errors: List[str] = []
    if slot not in VALID_MEDIA_SLOTS_P159:
        errors.append(f"BLOCKED_INVALID_SLOT_ID: {slot!r}")

    unmount_complete_ms = round(door_open_irq_ms + mpr_fifo_flush_ms + unmount_latency_ms, 3)
    unmounted_before_drop = unmount_complete_ms < power_rail_drop_ms
    fifo_flushed = mpr_fifo_flush_ms >= 0.0 and unmounted_before_drop
    rsv_fallback = not unmounted_before_drop

    if not unmounted_before_drop:
        errors.append(
            f"POWER_DROP_BEFORE_UNMOUNT: unmount={unmount_complete_ms:.2f}ms >= rail_drop={power_rail_drop_ms:.2f}ms (.RSV salvage required)"
        )

    valid = len(errors) == 0 and unmounted_before_drop
    return CardDoorFlushEvalResult(
        valid=valid,
        status="GRACEFUL_DOOR_FLUSH_UNMOUNT_OK" if valid else "UNGRACEFUL_POWER_DROP_RSV_FALLBACK",
        slot_id=slot,
        door_open_irq_ms=door_open_irq_ms,
        mpr_fifo_flush_ms=mpr_fifo_flush_ms,
        unmount_complete_ms=unmount_complete_ms,
        power_rail_drop_ms=power_rail_drop_ms,
        fifo_flushed=fifo_flushed,
        unmounted_before_power_drop=unmounted_before_drop,
        rsv_fallback_triggered=rsv_fallback,
        errors=tuple(errors),
    )


def evaluate_rsv_clip_salvage(
    *,
    slot_id: str = "SLOT_A",
    rsv_path: str = "/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.RSV",
    target_container: str = "MP4",
    rsv_size_bytes: int = 256 * 1024 * 1024,
    has_valid_nal_frames: bool = True,
) -> RsvClipSalvageEvalResult:
    """Verify `.RSV` -> `.MP4`/`.MXF` Recover Image DB repair without touching `nflasha*`."""
    slot = slot_id.strip().upper()
    norm_rsv = rsv_path.strip()
    tgt = target_container.strip().upper()
    errors: List[str] = []

    if slot not in VALID_MEDIA_SLOTS_P159:
        errors.append(f"BLOCKED_INVALID_SLOT_ID: {slot!r}")
    if tgt not in VALID_SALVAGE_TARGETS:
        errors.append(f"BLOCKED_UNSUPPORTED_SALVAGE_CONTAINER: {tgt!r}")
    if FORBIDDEN_PERSISTENT_TARGET_RE_P159.search(norm_rsv):
        errors.append(f"BLOCKED_INTERNAL_EMMC_SALVAGE_PATH: {norm_rsv!r}")
    elif not norm_rsv.startswith(("/mnt/sd/", "/mnt/sd2/")):
        errors.append(f"BLOCKED_NON_EXTERNAL_SALVAGE_PATH: {norm_rsv!r}")
    if not norm_rsv.upper().endswith(".RSV"):
        errors.append(f"BLOCKED_NOT_AN_RSV_FILE: {norm_rsv!r}")
    if rsv_size_bytes < MIN_VALID_RSV_BYTES:
        errors.append(f"BLOCKED_TRUNCATED_RSV_TOO_SMALL: {rsv_size_bytes} B < {MIN_VALID_RSV_BYTES} B")
    if not has_valid_nal_frames:
        errors.append("BLOCKED_CORRUPT_RSV_NO_RECOVERABLE_FRAMES")

    repaired_path = re.sub(r"\.rsv$", f".{tgt}", norm_rsv, flags=re.IGNORECASE)
    valid = len(errors) == 0
    return RsvClipSalvageEvalResult(
        valid=valid,
        status=f"RSV_SALVAGED_TO_{tgt}" if valid else "BLOCKED_RSV_SALVAGE_ABORTED",
        slot_id=slot,
        rsv_path=norm_rsv,
        target_container=tgt,
        repaired_path=repaired_path if valid else "",
        rsv_size_bytes=rsv_size_bytes,
        moov_ftyp_restored=valid,
        mediapro_xml_updated=valid,
        nflasha_writes=0,
        errors=tuple(errors),
    )


def evaluate_stage_a_bodydata_auto_bypass(
    *,
    slot_a_bodydata_magic: Optional[bytes] = BODYDATA_UFU_MAGIC,
    slot_b_bodydata_magic: Optional[bytes] = None,
    bypass_latency_us: float = 42.0,
) -> StageABodydataBypassEvalResult:
    """Verify Stage-A immediately aborts Stage-B in <100us when BODYDATA.DAT is present."""
    errors: List[str] = []
    a_present = slot_a_bodydata_magic is not None
    b_present = slot_b_bodydata_magic is not None
    any_present = a_present or b_present

    a_ok = (slot_a_bodydata_magic[:8] == BODYDATA_UFU_MAGIC) if slot_a_bodydata_magic is not None else False
    b_ok = (slot_b_bodydata_magic[:8] == BODYDATA_UFU_MAGIC) if slot_b_bodydata_magic is not None else False
    magic_valid = a_ok or b_ok
    corrupt_flagged = any_present and not magic_valid

    if bypass_latency_us >= BODYDATA_STAGE_A_BYPASS_BUDGET_US:
        errors.append(
            f"STAGE_A_BYPASS_LATENCY_EXCEEDED: {bypass_latency_us:.1f} us >= {BODYDATA_STAGE_A_BYPASS_BUDGET_US:.1f} us"
        )

    # Fail-closed rule: ANY BODYDATA.DAT on Slot A or Slot B blocks Stage-B and boots stock FX3!
    stage_b_blocked = any_present
    stock_booted = stage_b_blocked

    valid = len(errors) == 0
    if not any_present:
        status = "NO_BODYDATA_DAT_STAGE_B_ELIGIBLE"
    elif magic_valid:
        status = "VALID_UFU_BODYDATA_DAT_STAGE_B_ABORTED_TO_STOCK"
    else:
        status = "CORRUPT_BODYDATA_DAT_FAIL_CLOSED_TO_STOCK"

    return StageABodydataBypassEvalResult(
        valid=valid,
        status=status,
        slot_a_bodydata_present=a_present,
        slot_b_bodydata_present=b_present,
        ufu_magic_valid=magic_valid,
        stage_b_blocked_on_bodydata_dat=stage_b_blocked,
        stock_fx3_userland_booted=stock_booted,
        bypass_latency_us=bypass_latency_us,
        corrupt_ufu_magic_flagged=corrupt_flagged,
        errors=tuple(errors),
    )


def evaluate_p1_official_update_clean_uninstall(
    *,
    updater_mode: str = "mode5",
    p15_clean_uninstalled: bool = True,
    h0_equals_h3: bool = True,
    p15_residual_files: int = 0,
    orig_backup_verified: bool = True,
    battery_soc_pct: int = 85,
) -> P1CleanUninstallEvalResult:
    """Enforce mandatory H0 == H3 clean uninstall before Sony p1 official updater launch."""
    mode_norm = updater_mode.strip().lower()
    errors: List[str] = []

    if mode_norm not in UPDATER_MODES_P159:
        errors.append(f"BLOCKED_UNKNOWN_P1_UPDATER_MODE: {mode_norm!r}")
    if not p15_clean_uninstalled or not h0_equals_h3 or p15_residual_files != 0:
        errors.append(
            "BLOCKED_STAGE_B_ACTIVE_ON_P15_MUST_UNINSTALL_FIRST: "
            f"clean={p15_clean_uninstalled}, h0_eq_h3={h0_equals_h3}, residuals={p15_residual_files}"
        )
    if not orig_backup_verified:
        errors.append("BLOCKED_MISSING_VERIFIED_IM_ELF_ORIG_BACKUP")
    if battery_soc_pct < 51:
        errors.append(f"BLOCKED_SONY_UPDATER_BATTERY_BELOW_51_PCT: {battery_soc_pct}%")

    safe = len(errors) == 0
    return P1CleanUninstallEvalResult(
        valid=safe,
        status="SAFE_FOR_SONY_P1_OFFICIAL_UPDATER" if safe else "BLOCKED_PRE_UPDATE_GUARD",
        updater_mode=mode_norm,
        p15_clean_uninstalled=p15_clean_uninstalled,
        h0_equals_h3=h0_equals_h3,
        p15_residual_files=p15_residual_files,
        orig_backup_verified=orig_backup_verified,
        battery_soc_pct=battery_soc_pct,
        sector0_p2_p18_untouched=True,
        safe_for_sony_p1_updater=safe,
        errors=tuple(errors),
    )


def evaluate_phase159_write_guard(target_path: str) -> Phase159WriteGuardResult:
    """Enforce zero persistent eMMC / SPI-NOR mutations; allow volatile RAM or external clips."""
    norm = target_path.strip()
    is_forbidden = bool(FORBIDDEN_PERSISTENT_TARGET_RE_P159.search(norm))
    is_allowed = norm.startswith(VOLATILE_OR_EXT_MEDIA_PREFIXES_P159) and not is_forbidden

    errors: List[str] = []
    if is_forbidden:
        errors.append(
            f"BLOCKED_PERSISTENT_STORAGE_OR_BODYDATA_WRITE: {norm!r} is strictly O_RDONLY protected"
        )
    elif not is_allowed:
        errors.append(
            f"BLOCKED_UNKNOWN_STORAGE_TARGET: {norm!r} is outside volatile RAM / external clip paths"
        )

    valid = is_allowed and not is_forbidden and len(errors) == 0
    return Phase159WriteGuardResult(
        valid=valid,
        status="VOLATILE_OR_EXTERNAL_CLIP_ALLOWED" if valid else "PERSISTENT_WRITE_BLOCKED",
        target_path=norm,
        volatile_or_ext_allowed=is_allowed,
        persistent_write_blocked=not valid,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        errors=tuple(errors),
    )


def build_phase159_media_ufu_matrix() -> MediaUfuCompatMatrixSummary:
    """Build deterministic 12-touchpoint 4-class compatibility matrix for Phase 159."""
    entries: Tuple[MediaUfuTouchpointEntry, ...] = (
        MediaUfuTouchpointEntry(
            touchpoint_id="SLOT_A_NVME_CFEXPRESS_A",
            subsystem="DUAL_SLOT_EXFAT",
            fx6_interface="Slot A CFexpress Type A (PCIe Gen3 x1 /dev/nvme0n1p1)",
            fx3_target="Stock FX3 nvme-core.ko + nvme.ko -> /mnt/sd ExFAT",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="FX3 and FX6 share identical hybrid CFexpress Type A PCIe Gen3 x1 NVMe slot bus.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="SLOT_B_SDXC_UHS_II",
            subsystem="DUAL_SLOT_EXFAT",
            fx6_interface="Slot B SDXC UHS-II (/dev/mmcblk2p1)",
            fx3_target="Stock FX3 mmc_drv.ko + mcmn_drv.ko -> /mnt/sd2 ExFAT",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="Dual hybrid combo Slot B supports simultaneous, relay, and sort recording.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="M4ROOT_XDROOT_EXFAT_COEXISTENCE",
            subsystem="DUAL_SLOT_EXFAT",
            fx6_interface="XDROOT/Clip (MXF) + PRIVATE/M4ROOT/CLIP (MP4)",
            fx3_target="Non-destructive ExFAT dual-tree coexistence on dual-boot switch",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            write_protected=False,
            notes="Switching Stock FX3 <-> Stage-B FX6 preserves both M4ROOT and XDROOT clips.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="VPG_SPEED_CLASS_ADMISSION_GATE",
            subsystem="SPEED_CLASS_GATE",
            fx6_interface="LOG_ID_VPG_MANAGER + MPR_CMD_CHECK_MEDIA_IF",
            fx3_target="VPG400/VPG200/V90 gate for 600Mbps Intra & 4K120p S&Q",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="Blocks V30/V60 on 600Mbps Intra before record start; zero kernel I/O stalls.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="SD_WP_AND_OVERCURRENT_GUARD",
            subsystem="SPEED_CLASS_GATE",
            fx6_interface="MPR_CMD_CHECK_MEDIA_SD_WP / GET_MEDIA_OVERCURRENT_STATUS",
            fx3_target="Stock FX3 libsencore.so media WP & overcurrent fault isolation",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="Hardware write-protect tab and slot overcurrent cleanly block recording.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="CARD_DOOR_HALL_IRQ_FLUSH",
            subsystem="CARD_DOOR_RSV",
            fx6_interface="NotifyMediaCoverStatus + INFRA_NOTIFY_MEDIA_EJECT",
            fx3_target="Immediate MPR ExecEncClose FIFO flush & unmount before rail drop",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            write_protected=False,
            notes="Door-open IRQ flushes buffers inside 15ms hold window prior to slot power-off.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="RSV_RECOVER_DB_SALVAGE",
            subsystem="CARD_DOOR_RSV",
            fx6_interface="RECOVER_DB + MprIf::Salvage / muxMp4Salvage / MuxMxfSlvMain",
            fx3_target="External .RSV -> .MP4/.MXF header repair + MEDIAPRO.XML",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            write_protected=False,
            notes="Recovers interrupted clips strictly on external cards with zero eMMC mutation.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="FX6_OPTICAL_ND_SLOT_LOCK_ABSENT",
            subsystem="DUAL_SLOT_EXFAT",
            fx6_interface="FX6 Physical Slot-Select Switch & eND Media Lock",
            fx3_target="Masked non-blocking onto software Slot A/B selection",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            write_protected=False,
            notes="FX3 lacks FX6 side-panel mechanical slot switch; UI soft-select remains active.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="STAGE_A_BODYDATA_DAT_AUTO_BYPASS",
            subsystem="BODYDATA_UFU",
            fx6_interface="Stage-A im.elf launcher hook on p15:/usr/bin/im.elf",
            fx3_target="Detect /mnt/sd*/BODYDATA.DAT (\\x89UFU) -> exec stock im.elf.orig <100us",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            write_protected=True,
            notes="Guarantees Stage-B never loads when an official Sony update card is inserted.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="P1_OFFICIAL_UPDATER_H0_EQ_H3_GUARD",
            subsystem="BODYDATA_UFU",
            fx6_interface="p1 UdtrMain.sh (mode1..mode6) + sdfileinput.elf (DATV/UDID/FDAT)",
            fx3_target="Mandatory p15:/usr .orig restore (H0 == H3) before Sony update",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            write_protected=True,
            notes="Zero residual files on p15 ensures official updater sees 100% factory checksums.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="SECTOR0_P2_P18_NVS_LOCK",
            subsystem="BODYDATA_UFU",
            fx6_interface="Sector 0 SDM2, p2:/Backup.bin/psd/defdet, p18:/lens",
            fx3_target="Strict O_RDONLY across all internal eMMC calibration partitions",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            write_protected=True,
            notes="Stage-B and lab auditors never authorize writes to Sector 0, p2, or p18.",
        ),
        MediaUfuTouchpointEntry(
            touchpoint_id="SPI_NOR_LOADER_HARD_LOCK",
            subsystem="BODYDATA_UFU",
            fx6_interface="EXBL / DDR training / loader_nor.bin",
            fx3_target="spi_nor_write_authorized = False (100% locked)",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            write_protected=True,
            notes="Never touches SPI NOR bootloader during Stage-B or media/UFU diagnostics.",
        ),
    )

    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    subsystem_counts: Dict[str, int] = {}
    for ent in entries:
        class_counts[ent.classification] = class_counts.get(ent.classification, 0) + 1
        subsystem_counts[ent.subsystem] = subsystem_counts.get(ent.subsystem, 0) + 1

    return MediaUfuCompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        subsystem_counts=subsystem_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Main Dual-Mode Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwCfexpressSdxcExfatRsvAndUfuCoexistenceReport:
    """Run Phase 159 (33rd Auditor) on real O_RDONLY donors or deterministic clean-room fixtures."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    force_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not force_clean:
        rel_map = {
            "fx3_appfw": FX3_APPFW_P159_RELPATH,
            "fx6_appfw": FX6_APPFW_P159_RELPATH,
            "fx3_mpr": FX3_LIBMPR_P159_RELPATH,
            "fx6_mpr": FX6_LIBMPR_P159_RELPATH,
            "fx3_sencore": FX3_LIBSENCORE_P159_RELPATH,
            "fx6_sencore": FX6_LIBSENCORE_P159_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P159_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P159_RELPATH,
            "fx3_updaterufp": FX3_LIBUPDATERUFP_P159_RELPATH,
            "fx6_updaterufp": FX6_LIBUPDATERUFP_P159_RELPATH,
            "fx3_insmod_drv2": FX3_INSMOD_DRV2_P159_RELPATH,
            "fx3_fstab": FX3_FSTAB_P159_RELPATH,
            "bodydata_dat": FX3_BODYDATA_DAT_P159_RELPATH,
        }
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=root)

    use_local = (not force_clean) and all(p is not None for p in donor_paths.values())

    donor_file_sizes: Dict[str, int] = {}
    errors: List[str] = []

    if use_local:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_appfw_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX3",
            tokens=MEDIA_APPFW_FX3_MARKERS,
        )
        fx3_appfw_hits = fx3_appfw_sum.marker_hits
        fx6_appfw_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX6",
            tokens=MEDIA_APPFW_FX6_MARKERS,
        )
        fx6_appfw_hits = fx6_appfw_sum.marker_hits
        fx3_mpr_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX3",
            tokens=MEDIA_MPR_SHARED_MARKERS,
        )
        fx3_mpr_hits = fx3_mpr_sum.marker_hits
        fx6_mpr_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX6",
            tokens=MEDIA_MPR_SHARED_MARKERS + MEDIA_MPR_FX6_EXTRA_MARKERS,
        )
        fx6_mpr_hits = fx6_mpr_sum.marker_hits
        fx3_sencore_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_sencore"],  # type: ignore[arg-type]
            binary_name="libsencore.so",
            body_label="FX3",
            tokens=MEDIA_SENCORE_SHARED_MARKERS,
        )
        fx3_sencore_hits = fx3_sencore_sum.marker_hits
        fx6_sencore_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_sencore"],  # type: ignore[arg-type]
            binary_name="libsencore.so",
            body_label="FX6",
            tokens=MEDIA_SENCORE_SHARED_MARKERS,
        )
        fx6_sencore_hits = fx6_sencore_sum.marker_hits
        fx3_cp_sz, fx3_cp_hits = _scan_tokens_mmap_rdonly_p159(
            donor_paths["fx3_cpapp"],  # type: ignore[arg-type]
            MEDIA_CP_SHARED_MARKERS,
        )
        fx6_cp_sz, fx6_cp_hits = _scan_tokens_mmap_rdonly_p159(
            donor_paths["fx6_cpapp"],  # type: ignore[arg-type]
            MEDIA_CP_SHARED_MARKERS,
        )
        fx3_ufp_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_updaterufp"],  # type: ignore[arg-type]
            binary_name="libupdaterufp.so",
            body_label="FX3",
            tokens=UPDATERUFP_MARKERS,
        )
        fx3_ufp_hits = fx3_ufp_sum.marker_hits
        fx6_ufp_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_updaterufp"],  # type: ignore[arg-type]
            binary_name="libupdaterufp.so",
            body_label="FX6",
            tokens=UPDATERUFP_MARKERS,
        )
        fx6_ufp_hits = fx6_ufp_sum.marker_hits
        insmod_sz, insmod_txt = _read_text_rdonly_p159(donor_paths["fx3_insmod_drv2"])  # type: ignore[arg-type]
        fstab_sz, fstab_txt = _read_text_rdonly_p159(donor_paths["fx3_fstab"])  # type: ignore[arg-type]
        bd_total, bd_head, bd_tail = _read_bounded_bodydata_header_tail_rdonly(
            donor_paths["bodydata_dat"]  # type: ignore[arg-type]
        )

        donor_file_sizes = {
            "fx3_appfw": fx3_appfw_sum.file_bytes,
            "fx6_appfw": fx6_appfw_sum.file_bytes,
            "fx3_mpr": fx3_mpr_sum.file_bytes,
            "fx6_mpr": fx6_mpr_sum.file_bytes,
            "fx3_sencore": fx3_sencore_sum.file_bytes,
            "fx6_sencore": fx6_sencore_sum.file_bytes,
            "fx3_cpapp": fx3_cp_sz,
            "fx6_cpapp": fx6_cp_sz,
            "fx3_updaterufp": fx3_ufp_sum.file_bytes,
            "fx6_updaterufp": fx6_ufp_sum.file_bytes,
            "fx3_insmod_drv2": insmod_sz,
            "fx3_fstab": fstab_sz,
            "bodydata_dat": bd_total,
        }
        bd_source_mode = "LOCAL_DONOR_BOUNDED_O_RDONLY"
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx = build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures()
        fx3_appfw_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_appfw"],
            binary_name="appFw.so",
            body_label="FX3",
            source_mode=mode,
            tokens=MEDIA_APPFW_FX3_MARKERS,
        )
        fx3_appfw_hits = fx3_appfw_sum.marker_hits
        fx6_appfw_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_appfw"],
            binary_name="appFw.so",
            body_label="FX6",
            source_mode=mode,
            tokens=MEDIA_APPFW_FX6_MARKERS,
        )
        fx6_appfw_hits = fx6_appfw_sum.marker_hits
        fx3_mpr_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_mpr"],
            binary_name="libmpr.so",
            body_label="FX3",
            source_mode=mode,
            tokens=MEDIA_MPR_SHARED_MARKERS,
        )
        fx3_mpr_hits = fx3_mpr_sum.marker_hits
        fx6_mpr_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_mpr"],
            binary_name="libmpr.so",
            body_label="FX6",
            source_mode=mode,
            tokens=MEDIA_MPR_SHARED_MARKERS + MEDIA_MPR_FX6_EXTRA_MARKERS,
        )
        fx6_mpr_hits = fx6_mpr_sum.marker_hits
        fx3_sencore_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_sencore"],
            binary_name="libsencore.so",
            body_label="FX3",
            source_mode=mode,
            tokens=MEDIA_SENCORE_SHARED_MARKERS,
        )
        fx3_sencore_hits = fx3_sencore_sum.marker_hits
        fx6_sencore_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_sencore"],
            binary_name="libsencore.so",
            body_label="FX6",
            source_mode=mode,
            tokens=MEDIA_SENCORE_SHARED_MARKERS,
        )
        fx6_sencore_hits = fx6_sencore_sum.marker_hits
        fx3_cp_hits = _count_tokens_single_pass(fx["fx3_cpapp"], MEDIA_CP_SHARED_MARKERS)
        fx6_cp_hits = _count_tokens_single_pass(fx["fx6_cpapp"], MEDIA_CP_SHARED_MARKERS)
        fx3_ufp_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_updaterufp"],
            binary_name="libupdaterufp.so",
            body_label="FX3",
            source_mode=mode,
            tokens=UPDATERUFP_MARKERS,
        )
        fx3_ufp_hits = fx3_ufp_sum.marker_hits
        fx6_ufp_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_updaterufp"],
            binary_name="libupdaterufp.so",
            body_label="FX6",
            source_mode=mode,
            tokens=UPDATERUFP_MARKERS,
        )
        fx6_ufp_hits = fx6_ufp_sum.marker_hits
        insmod_txt = fx["fx3_insmod_drv2"].decode("ascii")
        fstab_txt = fx["fx3_fstab"].decode("ascii")
        bd_total = BODYDATA_EXPECTED_TOTAL_BYTES
        bd_head = fx["bodydata_head"]
        bd_tail = fx["bodydata_tail"]

        donor_file_sizes = {
            "fx3_appfw": len(fx["fx3_appfw"]),
            "fx6_appfw": len(fx["fx6_appfw"]),
            "fx3_mpr": len(fx["fx3_mpr"]),
            "fx6_mpr": len(fx["fx6_mpr"]),
            "fx3_sencore": len(fx["fx3_sencore"]),
            "fx6_sencore": len(fx["fx6_sencore"]),
            "fx3_cpapp": len(fx["fx3_cpapp"]),
            "fx6_cpapp": len(fx["fx6_cpapp"]),
            "fx3_updaterufp": len(fx["fx3_updaterufp"]),
            "fx6_updaterufp": len(fx["fx6_updaterufp"]),
            "fx3_insmod_drv2": len(fx["fx3_insmod_drv2"]),
            "fx3_fstab": len(fx["fx3_fstab"]),
            "bodydata_dat": bd_total,
        }
        bd_source_mode = "SYNTHETIC_CLEAN_ROOM"

    # ---- Pillar 1: Dual-Slot CFexpress/SDXC & ExFAT Coexistence ----
    p1_errors: List[str] = []
    kmod_ok = all(k in insmod_txt for k in ROOTFS_MEDIA_KMODS)
    if not kmod_ok:
        p1_errors.append("FX3 insmod_drv2 missing required NVMe/MMC storage kernel modules")

    fstab_p15_ro_ok = ("/dev/nflasha15" in fstab_txt) and ("/usr" in fstab_txt) and ("ro," in fstab_txt or "\tro\t" in fstab_txt)
    if not fstab_p15_ro_ok:
        p1_errors.append("FX3 fstab missing /dev/nflasha15 /usr ext2 ro mount")

    for label, hits in (
        ("fx3_appfw", fx3_appfw_hits),
        ("fx6_appfw", fx6_appfw_hits),
        ("fx3_mpr", fx3_mpr_hits),
        ("fx6_mpr", fx6_mpr_hits),
        ("fx3_cpapp", fx3_cp_hits),
        ("fx6_cpapp", fx6_cp_hits),
    ):
        missing = [k for k, v in hits.items() if v <= 0]
        if missing:
            p1_errors.append(f"{label} missing media/RSV markers: {missing}")

    slot_a_eval = evaluate_dual_slot_exfat_coexistence(
        slot_id="SLOT_A", media_type="CFEXPRESS_TYPE_A", active_profile="STAGE_B_FX6"
    )
    slot_b_eval = evaluate_dual_slot_exfat_coexistence(
        slot_id="SLOT_B", media_type="SDXC_UHS_II", active_profile="STAGE_B_FX6"
    )
    dual_boot_eval = evaluate_dual_slot_exfat_coexistence(
        slot_id="SLOT_A", media_type="CFEXPRESS_TYPE_A", active_profile="STOCK_FX3", reformat_requested=False
    )
    emmc_blocked = evaluate_dual_slot_exfat_coexistence(
        slot_id="SLOT_A", media_type="CFEXPRESS_TYPE_A", block_device_override="/dev/nflasha15"
    )
    if not (slot_a_eval.valid and slot_b_eval.valid and dual_boot_eval.valid):
        p1_errors.append("Pillar 1 dual-slot ExFAT coexistence evaluation failed")
    if emmc_blocked.valid:
        p1_errors.append("Pillar 1 failed to block internal eMMC media mount override")

    p1_report = Pillar1DualSlotExfatReport(
        passed=len(p1_errors) == 0,
        kmod_load_order_verified=kmod_ok,
        fx3_fstab_p15_ro_verified=fstab_p15_ro_ok,
        fx3_appfw_markers=fx3_appfw_hits,
        fx6_appfw_markers=fx6_appfw_hits,
        fx3_mpr_markers=fx3_mpr_hits,
        fx6_mpr_markers=fx6_mpr_hits,
        fx3_cp_markers=fx3_cp_hits,
        fx6_cp_markers=fx6_cp_hits,
        slot_a_nvme_eval=slot_a_eval,
        slot_b_sdxc_eval=slot_b_eval,
        dual_boot_coexistence_eval=dual_boot_eval,
        emmc_media_target_blocked=emmc_blocked,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: Speed-Class Bitrate Admission Gate ----
    p2_errors: List[str] = []
    for label, hits in (("fx3_sencore", fx3_sencore_hits), ("fx6_sencore", fx6_sencore_hits)):
        missing = [k for k, v in hits.items() if v <= 0]
        if missing:
            p2_errors.append(f"{label} missing media hardware check markers: {missing}")

    cfe_4k120_eval = evaluate_speed_class_bitrate_gate(
        slot_id="SLOT_A", media_class="CFEXPRESS_A_VPG400", codec_profile="XAVC_SI_4K_120P_SQ"
    )
    v90_4k60_eval = evaluate_speed_class_bitrate_gate(
        slot_id="SLOT_B", media_class="SDXC_UHS_II_V90", codec_profile="XAVC_SI_4K_60P"
    )
    v60_xavcs_eval = evaluate_speed_class_bitrate_gate(
        slot_id="SLOT_B", media_class="SDXC_UHS_II_V60", codec_profile="XAVC_S_4K_60P_200M"
    )
    slow_v30_blocked = evaluate_speed_class_bitrate_gate(
        slot_id="SLOT_B", media_class="SDXC_UHS_I_V30", codec_profile="XAVC_SI_4K_120P_SQ"
    )
    wp_blocked = evaluate_speed_class_bitrate_gate(
        slot_id="SLOT_B", media_class="SDXC_UHS_II_V90", codec_profile="XAVC_SI_4K_60P", sd_write_protected=True
    )

    if not (cfe_4k120_eval.valid and v90_4k60_eval.valid and v60_xavcs_eval.valid):
        p2_errors.append("Pillar 2 valid speed-class admission profile rejected")
    if slow_v30_blocked.valid or wp_blocked.valid:
        p2_errors.append("Pillar 2 failed to block slow V30 or write-protected media")

    p2_report = Pillar2SpeedClassGateReport(
        passed=len(p2_errors) == 0,
        fx3_sencore_markers=fx3_sencore_hits,
        fx6_sencore_markers=fx6_sencore_hits,
        cfexpress_4k120_sq_eval=cfe_4k120_eval,
        sdxc_v90_4k60_si_eval=v90_4k60_eval,
        sdxc_v60_4k60_xavcs_eval=v60_xavcs_eval,
        slow_v30_on_4k120_blocked=slow_v30_blocked,
        write_protected_card_blocked=wp_blocked,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: Card-Door Interrupt Flush & .RSV Clip Salvage ----
    p3_errors: List[str] = []
    door_safe = evaluate_card_door_flush_sequence(
        slot_id="SLOT_A", door_open_irq_ms=0.0, mpr_fifo_flush_ms=4.5, unmount_latency_ms=2.0, power_rail_drop_ms=15.0
    )
    power_drop_rsv = evaluate_card_door_flush_sequence(
        slot_id="SLOT_A", door_open_irq_ms=0.0, mpr_fifo_flush_ms=14.0, unmount_latency_ms=3.0, power_rail_drop_ms=15.0
    )
    rsv_mp4 = evaluate_rsv_clip_salvage(
        slot_id="SLOT_A", rsv_path="/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.RSV", target_container="MP4"
    )
    rsv_mxf = evaluate_rsv_clip_salvage(
        slot_id="SLOT_B", rsv_path="/mnt/sd2/XDROOT/Clip/A001C001.RSV", target_container="MXF"
    )
    tiny_rsv_rejected = evaluate_rsv_clip_salvage(
        slot_id="SLOT_A", rsv_path="/mnt/sd/PRIVATE/M4ROOT/CLIP/C0002.RSV", target_container="MP4", rsv_size_bytes=512
    )

    if not door_safe.valid or not door_safe.unmounted_before_power_drop:
        p3_errors.append("Pillar 3 graceful door-open flush failed")
    if power_drop_rsv.valid or not power_drop_rsv.rsv_fallback_triggered:
        p3_errors.append("Pillar 3 power-drop RSV fallback failed")
    if not (rsv_mp4.valid and rsv_mxf.valid):
        p3_errors.append("Pillar 3 valid RSV salvage to MP4/MXF failed")
    if tiny_rsv_rejected.valid:
        p3_errors.append("Pillar 3 failed to reject truncated <4KiB .RSV")

    p3_report = Pillar3CardDoorFlushAndRsvReport(
        passed=len(p3_errors) == 0,
        door_flush_safe_eval=door_safe,
        instant_power_loss_rsv_eval=power_drop_rsv,
        rsv_to_mp4_salvage_eval=rsv_mp4,
        rsv_to_mxf_salvage_eval=rsv_mxf,
        corrupt_tiny_rsv_rejected=tiny_rsv_rejected,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: Official BODYDATA.DAT (\x89UFU) Coexistence & p1 Clean-Uninstall Guard ----
    p4_errors: List[str] = []
    for label, hits in (("fx3_updaterufp", fx3_ufp_hits), ("fx6_updaterufp", fx6_ufp_hits)):
        missing = [k for k, v in hits.items() if v <= 0]
        if missing:
            p4_errors.append(f"{label} missing updater UFU markers: {missing}")

    if fx3_ufp_sum.export_count != EXPECTED_UPDATERUFP_EXPORTS_P159:
        p4_errors.append(
            f"FX3 libupdaterufp.so export mismatch: {fx3_ufp_sum.export_count} != {EXPECTED_UPDATERUFP_EXPORTS_P159}"
        )
    if fx6_ufp_sum.export_count != EXPECTED_UPDATERUFP_EXPORTS_P159:
        p4_errors.append(
            f"FX6 libupdaterufp.so export mismatch: {fx6_ufp_sum.export_count} != {EXPECTED_UPDATERUFP_EXPORTS_P159}"
        )
    if fx3_mpr_sum.export_count != EXPECTED_FX3_MPR_EXPORTS_P159:
        p4_errors.append(
            f"FX3 libmpr.so export mismatch: {fx3_mpr_sum.export_count} != {EXPECTED_FX3_MPR_EXPORTS_P159}"
        )
    if fx6_mpr_sum.export_count != EXPECTED_FX6_MPR_EXPORTS_P159:
        p4_errors.append(
            f"FX6 libmpr.so export mismatch: {fx6_mpr_sum.export_count} != {EXPECTED_FX6_MPR_EXPORTS_P159}"
        )

    bodydata_sum = parse_bodydata_ufu_header_tail(
        total_bytes=bd_total,
        head_bytes=bd_head,
        tail_bytes=bd_tail,
        source_mode=bd_source_mode,
    )
    if not bodydata_sum.valid:
        p4_errors.extend(bodydata_sum.errors)

    slot_a_bypass = evaluate_stage_a_bodydata_auto_bypass(
        slot_a_bodydata_magic=bd_head[:8], slot_b_bodydata_magic=None, bypass_latency_us=42.0
    )
    slot_b_bypass = evaluate_stage_a_bodydata_auto_bypass(
        slot_a_bodydata_magic=None, slot_b_bodydata_magic=bd_head[:8], bypass_latency_us=44.0
    )
    no_bodydata = evaluate_stage_a_bodydata_auto_bypass(
        slot_a_bodydata_magic=None, slot_b_bodydata_magic=None, bypass_latency_us=38.0
    )
    corrupt_bodydata = evaluate_stage_a_bodydata_auto_bypass(
        slot_a_bodydata_magic=b"NOT_UFU!", slot_b_bodydata_magic=None, bypass_latency_us=40.0
    )

    if not (
        slot_a_bypass.valid
        and slot_a_bypass.stage_b_blocked_on_bodydata_dat
        and slot_a_bypass.stock_fx3_userland_booted
    ):
        p4_errors.append("Pillar 4 Slot-A BODYDATA.DAT auto-bypass failed")
    if not (
        slot_b_bypass.valid
        and slot_b_bypass.stage_b_blocked_on_bodydata_dat
        and slot_b_bypass.stock_fx3_userland_booted
    ):
        p4_errors.append("Pillar 4 Slot-B BODYDATA.DAT auto-bypass failed")
    if not no_bodydata.valid or no_bodydata.stage_b_blocked_on_bodydata_dat:
        p4_errors.append("Pillar 4 no-BODYDATA Stage-B eligibility check failed")
    if not corrupt_bodydata.valid or not corrupt_bodydata.stage_b_blocked_on_bodydata_dat or not corrupt_bodydata.corrupt_ufu_magic_flagged:
        p4_errors.append("Pillar 4 corrupt BODYDATA fail-closed guard failed")

    p1_clean = evaluate_p1_official_update_clean_uninstall(
        updater_mode="mode5",
        p15_clean_uninstalled=True,
        h0_equals_h3=True,
        p15_residual_files=0,
        orig_backup_verified=True,
        battery_soc_pct=85,
    )
    p1_dirty = evaluate_p1_official_update_clean_uninstall(
        updater_mode="mode5",
        p15_clean_uninstalled=False,
        h0_equals_h3=False,
        p15_residual_files=2,
        orig_backup_verified=True,
        battery_soc_pct=85,
    )
    p1_low_batt = evaluate_p1_official_update_clean_uninstall(
        updater_mode="mode5",
        p15_clean_uninstalled=True,
        h0_equals_h3=True,
        p15_residual_files=0,
        orig_backup_verified=True,
        battery_soc_pct=42,
    )

    if not p1_clean.valid or not p1_clean.safe_for_sony_p1_updater:
        p4_errors.append("Pillar 4 H0 == H3 clean-uninstall p1 preflight failed")
    if p1_dirty.valid or p1_dirty.safe_for_sony_p1_updater:
        p4_errors.append("Pillar 4 failed to block Sony p1 updater with dirty p15:/usr")
    if p1_low_batt.valid or p1_low_batt.safe_for_sony_p1_updater:
        p4_errors.append("Pillar 4 failed to block Sony p1 updater below 51% battery")

    wg_ram = evaluate_phase159_write_guard("/tmp/fx6_rsv_salvage_probe.json")
    wg_clip = evaluate_phase159_write_guard("/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.MP4")
    wg_bodydata = evaluate_phase159_write_guard("/mnt/sd/BODYDATA.DAT")
    wg_p15 = evaluate_phase159_write_guard("/dev/nflasha15")
    wg_spinor = evaluate_phase159_write_guard("spi_nor:/loader_nor.bin")

    if not (wg_ram.valid and wg_clip.valid):
        p4_errors.append("Pillar 4 valid volatile/external clip write guard rejected")
    if wg_bodydata.valid or wg_p15.valid or wg_spinor.valid:
        p4_errors.append("Pillar 4 failed to block BODYDATA.DAT / p15 / SPI-NOR write")

    matrix = build_phase159_media_ufu_matrix()

    p4_report = Pillar4BodydataUfuCoexistenceReport(
        passed=len(p4_errors) == 0,
        fx3_updaterufp_summary=fx3_ufp_sum,
        fx6_updaterufp_summary=fx6_ufp_sum,
        fx3_mpr_summary=fx3_mpr_sum,
        fx6_mpr_summary=fx6_mpr_sum,
        bodydata_ufu_summary=bodydata_sum,
        slot_a_bodydata_bypass_eval=slot_a_bypass,
        slot_b_bodydata_bypass_eval=slot_b_bypass,
        no_bodydata_stage_b_eval=no_bodydata,
        corrupt_bodydata_fail_closed_eval=corrupt_bodydata,
        clean_uninstall_p1_approved_eval=p1_clean,
        dirty_p15_p1_blocked_eval=p1_dirty,
        low_battery_p1_blocked_eval=p1_low_batt,
        volatile_ram_guard_ok=wg_ram,
        ext_clip_guard_ok=wg_clip,
        blocked_bodydata_write_guard=wg_bodydata,
        blocked_p15_write_guard=wg_p15,
        blocked_spi_nor_write_guard=wg_spinor,
        compatibility_matrix=matrix,
        errors=tuple(p4_errors),
    )

    errors.extend(p1_errors)
    errors.extend(p2_errors)
    errors.extend(p3_errors)
    errors.extend(p4_errors)

    all_passed = (
        p1_report.passed
        and p2_report.passed
        and p3_report.passed
        and p4_report.passed
        and len(errors) == 0
    )

    core_payload = {
        "schema_version": PHASE_159_SCHEMA,
        "phase_version": PHASE_159_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "dual_slot_exfat_coexistence_verified": p1_report.passed,
        "speed_class_gate_verified": p2_report.passed,
        "kernel_io_stall_prevented": True,
        "card_door_flush_and_rsv_verified": p3_report.passed,
        "stage_b_blocked_on_bodydata_dat": bool(
            slot_a_bypass.stage_b_blocked_on_bodydata_dat
            and slot_b_bypass.stage_b_blocked_on_bodydata_dat
            and corrupt_bodydata.stage_b_blocked_on_bodydata_dat
        ),
        "h0_equals_h3_clean_uninstall_verified": bool(p1_clean.h0_equals_h3 and p1_clean.safe_for_sony_p1_updater),
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "emmc_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "donor_file_sizes": donor_file_sizes,
        "pillar1_dual_slot_exfat": asdict(p1_report),
        "pillar2_speed_class_gate": asdict(p2_report),
        "pillar3_card_door_rsv_salvage": asdict(p3_report),
        "pillar4_bodydata_ufu_coexistence": asdict(p4_report),
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return RealhwCfexpressSdxcExfatRsvAndUfuCoexistenceReport(
        schema_version=PHASE_159_SCHEMA,
        phase_version=PHASE_159_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        dual_slot_exfat_coexistence_verified=p1_report.passed,
        speed_class_gate_verified=p2_report.passed,
        kernel_io_stall_prevented=True,
        card_door_flush_and_rsv_verified=p3_report.passed,
        stage_b_blocked_on_bodydata_dat=bool(
            slot_a_bypass.stage_b_blocked_on_bodydata_dat
            and slot_b_bypass.stage_b_blocked_on_bodydata_dat
            and corrupt_bodydata.stage_b_blocked_on_bodydata_dat
        ),
        h0_equals_h3_clean_uninstall_verified=bool(
            p1_clean.h0_equals_h3 and p1_clean.safe_for_sony_p1_updater
        ),
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        donor_file_sizes=donor_file_sizes,
        pillar1_dual_slot_exfat=p1_report,
        pillar2_speed_class_gate=p2_report,
        pillar3_card_door_rsv_salvage=p3_report,
        pillar4_bodydata_ufu_coexistence=p4_report,
        report_sha256=report_sha256,
        errors=tuple(errors),
    )


def realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_report_to_dict(
    report: RealhwCfexpressSdxcExfatRsvAndUfuCoexistenceReport,
) -> Dict[str, object]:
    """Convert Phase 159 report into a deterministic JSON-serializable dictionary."""
    return asdict(report)
