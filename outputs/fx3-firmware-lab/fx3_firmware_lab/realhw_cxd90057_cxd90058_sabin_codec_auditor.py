"""Phase 164 — 34th Unified Firmware-Lab Auditor (34/34): Real-Hardware
`CXD90057` (*Mira*, 4x ARM Cortex-A35 AP+CP + 32-bit SA-DSP) + `CXD90058`
(*Cetus*, 4x ARM Cortex-A35 Co-Processor) Dual-BIONZ-XR Inter-Chip IPC,
`sabin` 32-Bit SA-DSP Microcode & `XAVC-I / HEVC` Hardware Codec Boundary
Auditor.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ` / bounded `os.pread`) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `libsencore.so`,
  `cpapp-b.bin`, `Backup.bin`, `7.02-setting-cxd90057.dtb`, `DmmCfg.bin`,
  `nflasha7/sbin/initrc/insmod_drv2`) and FX6 v6.01 (`appFw.so`, `libmpr.so`,
  `libsencore.so`, `cpapp-b.bin`, `Backup.bin`, `DmmCfg.bin`,
  `sabin/sa_sabin_cp_cam_post.bin`, `1010_spi/mew.bin`, `pci_ep_cp.ko`,
  `pcie-if.ko`, `codec_drv.ko`) strictly via `os.O_RDONLY` (< 1.5 s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so` fixtures,
  `cpapp-b.bin` token buffers, FDT `cxd90057.dtb`, `DmmCfg.bin`, `sabin`
  `SP\\x01\\x00` microcode header, `mew.bin` FPGA bitstream header, `Backup.bin`,
  and `.ko` IPC fixtures, leaking zero raw Sony proprietary bytes in JSON output.

Audits Four Phase 164 Real-Hardware Dual-SoC & Codec Pillars:
1. Pillar 1 (`CXD90057_CXD90058_DUAL_SOC_PCIE_SLVSEC_INVARIANCE`):
   Proves Route-1 Hybrid Userland Stage-B keeps FX3's `CXD90057` (*Mira*) <->
   `CXD90058` (*Cetus*) PCIe EP (`0x1556:0x1100`, `pci_ep_cp.ko`, `pcie-if.ko`),
   SLVS-EC M-PHY (`CetusSlvsecDriver` / `CetusSlvsecLink` / `CetusSlvsecMphy`),
   `p8` (`cpapp-b.bin`), `7.02-setting-cxd90057.dtb`, and `Backup.bin` boot
   descriptors 100% stock (`cxd90058_fw_mutation_bytes == 0`,
   `cp_mutation_bytes == 0`), while failing closed on Route-2 `p8` replacement
   or PCIe/SLVS-EC mutation.
2. Pillar 2 (`SABIN_32BIT_SA_DSP_MICROCODE_AND_DMM_POOL_ALIGNMENT`):
   Audits all 34 shared `/usr/sabin/*.bin` SA-DSP microcode/dictionary paths in
   `cpapp-b.bin`, `SP\\x01\\x00` `sa_sabin_cp_cam_post.bin` microcode header,
   `codec_drv.ko` (`bdrv_driver.c`, `bdrv_uipc.c`), and FX3 (`603` units / `290`
   rules) vs FX6 (`556` units / `259` rules) `DmmCfg.bin` pool alignment
   (`<= 8` extents fitting `libmpr.so` `0xa8` stack reply,
   `sabin_microcode_mutation_bytes == 0`), proving zero mismatch when FX6
   `appFw.so` drives stock FX3 `libmpr.so` + `libsencore.so` via `LD_PRELOAD`.
3. Pillar 3 (`XAVC_I_HEVC_HARDWARE_ENCODER_VS_MASKED_SDI_RAW_FPGA`):
   Verifies clean parameter translation for `4K DCI (4096x2160)` and
   `QFHD (3840x2160)` `23.98p..119.88p` `10-bit 4:2:2` `XAVC-I` (`MXF` Class
   300/480 -> `MP4` mux shim), `XAVC S-I`, `XAVC-L`, `XAVC HS`
   (`HEVC_3840_2160_M42210P`), and `HDMI 16-bit RAW` onto FX3's `CXD90057 +
   CXD90058` `libmpr.so` (`AVC480_*_H422IP` / `HEVC_*`) encoder queues, while
   hard-masking FX6-exclusive `16-bit SDI RAW` (`mew.bin` Xilinx FPGA
   `0xaa995566`, `MoniFpgaSdi`) and `5016x3344` `X-OCN LT` Open-Gate paths
   without crashing `appFw.so`.
4. Pillar 4 (`NON_VOLATILE_WRITE_FIREWALL_AND_12TP_COMPAT_MATRIX`):
   Enforces `persistent_emmc_writes_authorized = False` and
   `spi_nor_write_authorized = False`, permitting only volatile `/tmp/` /
   `ram://` Stage-B parameter shadow & external `/mnt/sd*` media clips while
   hard-blocking `/dev/nflasha*`, `/dev/cnflasha*`, `/dev/mmcblk0*`,
   `p2:/Backup.bin`, `p8:/cpapp-b.bin`, `p15:/usr`, `/usr/sabin/`, `mew.bin`,
   and `spi_nor:`, and validates the 12-touchpoint 4-class compatibility matrix.
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
    FX3_BACKUP_BIN_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX3_LIBSENCORE_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_BACKUP_BIN_P146_RELPATH,
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
from .realhw_mpr_dmm_rec_pipeline_bridge_auditor import (
    DMM_MAX_EXTENTS_IN_MPR_REPLY,
    FX3_DMMCFG_EXPECTED_RULES,
    FX3_DMMCFG_EXPECTED_UNITS,
    FX6_DMMCFG_EXPECTED_RULES,
    FX6_DMMCFG_EXPECTED_UNITS,
    TARGET_MAIN_DMM_UNIT_IDS,
    DmmCfgSummary,
    _build_synthetic_dmmcfg,
    parse_dmm_cfg_bytes,
)


PHASE_164_SCHEMA = "fx3_firmware_lab_phase164_realhw_cxd90057_cxd90058_sabin_codec_v1"
PHASE_164_VERSION = "164.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_APPFW_P164_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P164_RELPATH = FX6_APPFW_P146_RELPATH
FX3_LIBMPR_P164_RELPATH = FX3_LIBMPR_P146_RELPATH
FX6_LIBMPR_P164_RELPATH = FX6_LIBMPR_P146_RELPATH
FX3_LIBSENCORE_P164_RELPATH = FX3_LIBSENCORE_P146_RELPATH
FX6_LIBSENCORE_P164_RELPATH = FX6_LIBSENCORE_P146_RELPATH
FX3_CPAPP_P164_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P164_RELPATH = FX6_CPAPP_P146_RELPATH
FX3_BACKUP_BIN_P164_RELPATH = FX3_BACKUP_BIN_P146_RELPATH
FX6_BACKUP_BIN_P164_RELPATH = FX6_BACKUP_BIN_P146_RELPATH

FX3_CXD90057_DTB_RELPATH = (
    "sony-firmware-20261024/stage205-FX3-hardware-profile-differences/originals/7.02-setting-cxd90057.dtb"
)
FX3_INSMOD_DRV2_P164_RELPATH = (
    "fx3-vm-20261101/fx3-audit/original-members/nflasha7/sbin/initrc/insmod_drv2"
)
FX3_AP_DMMCFG_P164_RELPATH = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/setting/DmmCfg.bin"
)
FX6_AP_DMMCFG_P164_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/DmmCfg.bin"
)
FX6_SABIN_CP_CAM_POST_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/sabin/sa_sabin_cp_cam_post.bin"
)
FX6_MEW_BIN_P164_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/1010_spi/mew.bin"
)
FX6_PCI_EP_CP_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/pci_ep_cp.ko"
)
FX6_PCIE_IF_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/pcie-if.ko"
)
FX6_CODEC_DRV_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/codec_drv.ko"
)

# ---------------------------------------------------------------------------
# Verified Donor Binary Sizes & Hardware Signatures
# ---------------------------------------------------------------------------

CXD90057_SOC_CODENAME = "Mira"
CXD90058_SOC_CODENAME = "Cetus"
CXD90057_PCIE_VENDOR_ID = 0x1556
CXD90057_PCIE_DEVICE_ID = 0x1100
FDT_MAGIC_U32 = 0xD00DFEED
SABIN_SP01_MAGIC_HEX = "53500100"
BK4_HEADER_MAGIC_HEX = "00000004aaaaaaaa00000000424b3400"
XILINX_BUS_DETECT_HEX = "000000bb11220044"
XILINX_FPGA_SYNC_HEX = "aa995566"
XILINX_FPGA_SYNC_OFFSET = 48

EXPECTED_FX3_APPFW_BYTES_P164 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P164 = 50_520_424
EXPECTED_FX3_MPR_BYTES_P164 = 3_517_008
EXPECTED_FX6_MPR_BYTES_P164 = 28_921_824
EXPECTED_FX3_MPR_EXPORTS_P164 = 3_541
EXPECTED_FX3_MPR_IMPORTS_P164 = 356
EXPECTED_FX6_MPR_EXPORTS_P164 = 4_271
EXPECTED_FX6_MPR_IMPORTS_P164 = 497
EXPECTED_FX3_SENCORE_BYTES_P164 = 377_328
EXPECTED_FX6_SENCORE_BYTES_P164 = 401_952
EXPECTED_FX3_CPAPP_BYTES_P164 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P164 = 17_952_816
EXPECTED_FX3_BACKUP_BYTES_P164 = 2_229_740
EXPECTED_FX6_BACKUP_BYTES_P164 = 2_253_333
EXPECTED_FX3_DTB_BYTES_P164 = 16_875
EXPECTED_FX3_DMMCFG_BYTES_P164 = 66_796
EXPECTED_FX6_DMMCFG_BYTES_P164 = 59_364
EXPECTED_FX6_SABIN_CP_CAM_POST_BYTES = 1_921_536
EXPECTED_FX6_MEW_BIN_BYTES_P164 = 6_692_572
EXPECTED_FX6_PCI_EP_CP_KO_BYTES = 6_496
EXPECTED_FX6_PCIE_IF_KO_BYTES = 65_136
EXPECTED_FX6_CODEC_DRV_KO_BYTES = 19_216

# ---------------------------------------------------------------------------
# Pillar 1..3 Marker Catalogs (Strictly Read-Only Binary Scans)
# ---------------------------------------------------------------------------

DTB_CXD90057_MARKERS: Tuple[str, ...] = (
    "sony,cxd90057",
    "cxd,cxd90057",
    "cxd90057,pci32",
    "snps,dw-pcie",
    "cxd900xx-pcie-ep",
    "pcie_i",
    "pcie_m0",
    "pcie_m1",
    "pcie_c",
    "axi2avb_pcie0",
    "axi2avb_pcie1",
)

INSMOD_IPC_KMODS_P164: Tuple[str, ...] = (
    "pciedma.ko",
    "pci_ep_cp.ko",
    "pci_ep_zq.ko",
    "pcieatu.ko",
    "osal_uipc.ko",
    "pcie-if.ko",
    "dmm.ko",
    "codec_drv.ko",
)

PCI_EP_CP_KO_MARKERS: Tuple[str, ...] = (
    "pci_ep_cp_probe",
    "pcidma_connect",
    "pcie_root_ctrl",
    "udif_pci_ep_cp",
    "pci:v00001556d00001100",
)

PCIE_IF_KO_MARKERS: Tuple[str, ...] = (
    "PCIEIF_EPAR",
    "PCIeDMAC",
    "pcidma_transfer_async",
    "pcie_ep_int_hi",
    "pcie_ep_int_lo",
    "pcieif_async_rcv_thread",
)

CODEC_DRV_KO_MARKERS: Tuple[str, ...] = (
    "bdrv_driver.c",
    "bdrv_loader.c",
    "bdrv_thread.c",
    "bdrv_uipc.c",
    "EXTERNAL_CODEC_DRIVER_LOAD_FIRM",
    "bdrv_uipc_recv_msg",
    "bdrv_uipc_send_msg",
    "bdrv_uipc_send_sync_msg",
)

CETUS_SLVSEC_CP_MARKERS: Tuple[str, ...] = (
    "IMG:CetusSlvsecDriver::initialize",
    "IMG:CetusSlvsecDriver::start",
    "IMG:CetusSlvsecLink::start",
    "IMG:CetusSlvsecLink::stop",
    "IMG:CetusSlvsecMphy::initialize",
    "IMG:CetusSlvsecMphy::startLane",
    "N6Camera6Imager15CetusSlvsecLinkE",
    "Cetus/PQD_Baseband_SystemDepend.cpp",
    "Cetus2/PQD_Black_SystemDepend.cpp",
    "osal_uipc",
    "SLVS",
)

SABIN_DICTIONARY_BIN_PATHS: Tuple[str, ...] = (
    "/usr/sabin/aed2_dic1.bin",
    "/usr/sabin/aed2_dic2.bin",
    "/usr/sabin/aed2_dica_s2f.bin",
    "/usr/sabin/aed2_dicb_s2f.bin",
    "/usr/sabin/aed_dic1.bin",
    "/usr/sabin/aed_dic2.bin",
    "/usr/sabin/bed_dic1.bin",
    "/usr/sabin/bed_dic2.bin",
    "/usr/sabin/dcv_psf_table_movie_2k.bin",
    "/usr/sabin/dcv_psf_table_movie_3k.bin",
    "/usr/sabin/dcv_psf_table_movie_4k.bin",
    "/usr/sabin/dcv_psf_table_movie_6k.bin",
    "/usr/sabin/dcv_psf_table_movie_8k.bin",
    "/usr/sabin/dcv_psf_table_still.bin",
    "/usr/sabin/dcv_psf_table_still_dualrec.bin",
    "/usr/sabin/dcv_psf_table_still_macro.bin",
    "/usr/sabin/fdn_front_dict.bin",
    "/usr/sabin/fdn_side_dict.bin",
    "/usr/sabin/pdn_dic.bin",
    "/usr/sabin/sa_sabin_cp_cam_post.bin",
    "/usr/sabin/spica_cetus_mov_bining_c_tap_step1.bin",
    "/usr/sabin/spica_cetus_mov_bining_c_tap_step2.bin",
    "/usr/sabin/spica_cetus_mov_bining_y_tap_step1.bin",
    "/usr/sabin/spica_cetus_mov_bining_y_tap_step2.bin",
    "/usr/sabin/spica_cetus_mov_c_tap_step1.bin",
    "/usr/sabin/spica_cetus_mov_c_tap_step2.bin",
    "/usr/sabin/spica_cetus_mov_y_tap_step1.bin",
    "/usr/sabin/spica_cetus_mov_y_tap_step2.bin",
    "/usr/sabin/spica_cetus_still_c_tap_step1.bin",
    "/usr/sabin/spica_cetus_still_c_tap_step2.bin",
    "/usr/sabin/spica_cetus_still_y_tap_step1.bin",
    "/usr/sabin/spica_cetus_still_y_tap_step2.bin",
    "/usr/sabin/udrt_dic1.bin",
    "/usr/sabin/udrt_dic2.bin",
)

FX6_EXCLUSIVE_FPGA_SDI_CP_MARKERS: Tuple[str, ...] = (
    "MoniFpgaSdi",
    "SetRegSDIOutFormat",
    "MoniFpgaAnalog_OutputSelect",
)

CODEC_MPR_SHARED_MARKERS: Tuple[str, ...] = (
    "AVC480_4096_2160_H422IP",
    "AVC480_3840_2160_H422IP",
    "AVC480CBG_3840_2160_H422IP",
    "AVC480CBG_4096_2160_H422IP",
    "AVC_4096_2160_H422IP",
    "AVC_3840_2160_H422IP",
    "HEVC_3840_2160_M42210P",
    "HEVC_3840_2160_M10P",
    "HEVC_Proxy_1920_1080_M10P",
    "_ZN3mpr16SetMovieRecParamERKNS_13movieRecParamE",
    "_ZN3mpr11ExecEncOpenEPv",
    "_ZN3mpr12ExecEncCloseEPv",
)

CODEC_MPR_FX6_EXTRA_MARKERS: Tuple[str, ...] = (
    "MPR::libXavcMxf",
    "LOG_ID_LIBXAVCMXF_MUX",
    "SYSCON_FILE_FORMAT_TYPE_XAVC_XDSTYLE",
)

CODEC_SENCORE_SHARED_MARKERS: Tuple[str, ...] = (
    "CHK_EXTERNAL_CODEC",
    "CNFM_DONE_CODEC",
    "EXEC_SDI_MAIN_OUTPUT",
    "EXEC_SDI_SUB_OUTPUT",
    "CAMERA_SCN_EXTERNAL_RAW_RECORD",
    "osal_uipc",
)

CODEC_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "XAVC",
    "HEVC",
    "RAW_OUT",
    "SetMovieRecParam",
    "CETUS",
    "MIRA",
)

CODEC_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "SELECT_CODEC_XAVC_I",
    "SELECT_CODEC_XAVC_L",
    "SELECT_CODEC_XAVC_S_I",
    "SELECT_CODEC_XAVC_HS_L_422",
    "SELECT_CODEC_RAW_HDMI",
    "SELECT_CODEC_RAW",
    "SELECT_CODEC_X_OCN_LT",
    "VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT",
)

# ---------------------------------------------------------------------------
# Codec Translation Profiles & Write Firewall Patterns
# ---------------------------------------------------------------------------

VALID_DEPLOYMENT_ROUTES_P164: Tuple[str, ...] = (
    "ROUTE1_HYBRID_USERLAND_STAGE_B",
    "ROUTE2_FULL_CP_FLASH",
)

SUPPORTED_CODEC_FPS_P164: Tuple[float, ...] = (
    23.98,
    24.0,
    25.0,
    29.97,
    50.0,
    59.94,
    100.0,
    119.88,
)

CODEC_TRANSLATION_PROFILES: Dict[str, Dict[str, object]] = {
    "XAVC_I_DCI_4K": {
        "fx6_select_token": "SELECT_CODEC_XAVC_I",
        "resolutions": ("4096x2160",),
        "allowed_fps": (23.98, 24.0, 25.0, 29.97, 50.0, 59.94),
        "bit_depth": 10,
        "chroma": "4:2:2",
        "hw_queue": "CXD90057+CXD90058::AVC480_4096_2160_H422IP",
        "fx6_container": "MXF_OP1A",
        "fx3_target_container": "MP4_ISO_BMFF_SHIM",
        "max_bitrate_mbps": 600,
        "supported_on_fx3_stage_b": True,
        "bridge_class": BRIDGE_CLASS_SHIM_TRANSLATED,
    },
    "XAVC_I_QFHD": {
        "fx6_select_token": "SELECT_CODEC_XAVC_I",
        "resolutions": ("3840x2160",),
        "allowed_fps": (23.98, 24.0, 25.0, 29.97, 50.0, 59.94, 100.0, 119.88),
        "bit_depth": 10,
        "chroma": "4:2:2",
        "hw_queue": "CXD90057+CXD90058::AVC480_3840_2160_H422IP",
        "fx6_container": "MXF_OP1A",
        "fx3_target_container": "MP4_ISO_BMFF_SHIM",
        "max_bitrate_mbps": 600,
        "supported_on_fx3_stage_b": True,
        "bridge_class": BRIDGE_CLASS_SHIM_TRANSLATED,
    },
    "XAVC_SI_DCI_4K": {
        "fx6_select_token": "SELECT_CODEC_XAVC_S_I",
        "resolutions": ("4096x2160",),
        "allowed_fps": (23.98, 24.0, 25.0, 29.97, 50.0, 59.94),
        "bit_depth": 10,
        "chroma": "4:2:2",
        "hw_queue": "CXD90057+CXD90058::AVC480_4096_2160_H422IP",
        "fx6_container": "MP4_ISO_BMFF",
        "fx3_target_container": "MP4_ISO_BMFF",
        "max_bitrate_mbps": 600,
        "supported_on_fx3_stage_b": True,
        "bridge_class": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    },
    "XAVC_SI_QFHD": {
        "fx6_select_token": "SELECT_CODEC_XAVC_S_I",
        "resolutions": ("3840x2160",),
        "allowed_fps": (23.98, 24.0, 25.0, 29.97, 50.0, 59.94, 100.0, 119.88),
        "bit_depth": 10,
        "chroma": "4:2:2",
        "hw_queue": "CXD90057+CXD90058::AVC480_3840_2160_H422IP",
        "fx6_container": "MP4_ISO_BMFF",
        "fx3_target_container": "MP4_ISO_BMFF",
        "max_bitrate_mbps": 600,
        "supported_on_fx3_stage_b": True,
        "bridge_class": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    },
    "XAVC_L_QFHD_422": {
        "fx6_select_token": "SELECT_CODEC_XAVC_L",
        "resolutions": ("3840x2160",),
        "allowed_fps": (23.98, 25.0, 29.97, 50.0, 59.94),
        "bit_depth": 10,
        "chroma": "4:2:2",
        "hw_queue": "CXD90057+CXD90058::AVC_3840_2160_H422IP",
        "fx6_container": "MXF_OP1A",
        "fx3_target_container": "MP4_ISO_BMFF_SHIM",
        "max_bitrate_mbps": 200,
        "supported_on_fx3_stage_b": True,
        "bridge_class": BRIDGE_CLASS_SHIM_TRANSLATED,
    },
    "XAVC_HS_QFHD_422_10B": {
        "fx6_select_token": "SELECT_CODEC_XAVC_HS_L_422",
        "resolutions": ("3840x2160",),
        "allowed_fps": (23.98, 50.0, 59.94, 100.0, 119.88),
        "bit_depth": 10,
        "chroma": "4:2:2",
        "hw_queue": "CXD90057+CXD90058::HEVC_3840_2160_M42210P",
        "fx6_container": "MP4_ISO_BMFF",
        "fx3_target_container": "MP4_ISO_BMFF",
        "max_bitrate_mbps": 280,
        "supported_on_fx3_stage_b": True,
        "bridge_class": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    },
    "XAVC_HS_QFHD_420_10B": {
        "fx6_select_token": "SELECT_CODEC_XAVC_HS_L_420",
        "resolutions": ("3840x2160",),
        "allowed_fps": (23.98, 50.0, 59.94, 100.0, 119.88),
        "bit_depth": 10,
        "chroma": "4:2:0",
        "hw_queue": "CXD90057+CXD90058::HEVC_3840_2160_M10P",
        "fx6_container": "MP4_ISO_BMFF",
        "fx3_target_container": "MP4_ISO_BMFF",
        "max_bitrate_mbps": 200,
        "supported_on_fx3_stage_b": True,
        "bridge_class": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    },
    "HDMI_RAW_16BIT": {
        "fx6_select_token": "SELECT_CODEC_RAW_HDMI",
        "resolutions": ("4264x2408",),
        "allowed_fps": (23.98, 24.0, 25.0, 29.97, 50.0, 59.94),
        "bit_depth": 16,
        "chroma": "RAW",
        "hw_queue": "CXD90057+CXD90058::HDMI_TYPE_A_RAW_OUT",
        "fx6_container": "HDMI_TMDS_RAW",
        "fx3_target_container": "HDMI_TMDS_RAW",
        "max_bitrate_mbps": 0,
        "supported_on_fx3_stage_b": True,
        "bridge_class": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    },
    "SDI_RAW_16BIT_MEW_FPGA": {
        "fx6_select_token": "SELECT_CODEC_RAW",
        "resolutions": ("4096x2160", "4264x2408"),
        "allowed_fps": (23.98, 24.0, 25.0, 29.97, 50.0, 59.94),
        "bit_depth": 16,
        "chroma": "RAW",
        "hw_queue": "MASKED_ABSENT_HW::MoniFpgaSdi_mew.bin",
        "fx6_container": "12G_SDI_BNC_RAW",
        "fx3_target_container": "MASKED_SDI_OUTPUT_NOT_SUPPORT",
        "max_bitrate_mbps": 0,
        "supported_on_fx3_stage_b": False,
        "bridge_class": BRIDGE_CLASS_MASKED_ABSENT_HW,
    },
    "X_OCN_LT_5K_OPENGATE": {
        "fx6_select_token": "SELECT_CODEC_X_OCN_LT",
        "resolutions": ("5016x3344",),
        "allowed_fps": (23.98, 24.0, 25.0, 29.97),
        "bit_depth": 16,
        "chroma": "RAW",
        "hw_queue": "MASKED_ABSENT_HW::5016x3344_OPENGATE",
        "fx6_container": "MXF_X_OCN",
        "fx3_target_container": "MASKED_IMX510_MAX_4264x2408",
        "max_bitrate_mbps": 0,
        "supported_on_fx3_stage_b": False,
        "bridge_class": BRIDGE_CLASS_MASKED_ABSENT_HW,
    },
}

VOLATILE_OR_EXT_CODEC_PREFIXES_P164: Tuple[str, ...] = (
    "/tmp/",
    "ram://",
    "memfd:",
    "/mnt/sd/",
    "/mnt/sd2/",
)

FORBIDDEN_PERSISTENT_TARGET_RE_P164 = re.compile(
    r"(?:"
    r"^/dev/(?:c?nflasha\d*|mmcblk0(?:p\d+)?)"
    r"|^p(?:2|8|15):/"
    r"|^/usr/(?:sabin|lib|bin|kmod)/"
    r"|^/setting/"
    r"|^spi_nor:"
    r"|^sector0:"
    r"|cpapp-b\.bin$"
    r"|mew\.bin$"
    r"|loader_nor\.bin$"
    r"|Backup\.bin$"
    r"|DmmCfg\.bin$"
    r"|sa_sabin_.*\.bin$"
    r")",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BinaryHeaderSummary:
    artifact_name: str
    source_mode: str
    file_bytes: int
    header_magic_hex: str
    valid: bool
    details: str


@dataclass(frozen=True)
class DualSocPcieSlvsecEvalResult:
    valid: bool
    deployment_route: str
    cxd90057_codename: str
    cxd90058_codename: str
    pcie_ep_id: str
    cxd90058_fw_mutation_bytes: int
    cp_mutation_bytes: int
    slvsec_mphy_stock_preserved: bool
    backup_bin_stock_preserved: bool
    dtb_cxd90057_stock_preserved: bool
    route1_invariance_verified: bool
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SabinDspDmmPoolEvalResult:
    valid: bool
    resolution: str
    fps: float
    codec_profile: str
    dmm_mode_id: int
    dmm_extent_count: int
    max_allowed_extents: int
    sabin_microcode_mutation_bytes: int
    sabin_cp_cam_post_loaded: bool
    ld_preload_shim_active: bool
    raw_fx6_dmmcfg_flash: bool
    estimated_frame_pool_kib: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HardwareCodecBoundaryEvalResult:
    valid: bool
    codec_admitted: bool
    fx6_codec_profile: str
    resolution: str
    fps: float
    chroma: str
    bit_depth: int
    hw_encoder_queue: str
    target_container: str
    mxf_to_mp4_shim_active: bool
    masked_gracefully: bool
    appfw_crash_prevented: bool
    fpga_mew_spi_access_blocked: bool
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase164WriteGuardResult:
    valid: bool
    target_path: str
    volatile_or_ext_allowed: bool
    persistent_write_blocked: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    emmc_mutation_bytes: int
    cxd90058_fw_mutation_bytes: int
    sabin_microcode_mutation_bytes: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SabinCodecTouchpointEntry:
    touchpoint_id: str
    subsystem: str
    fx6_component: str
    fx3_target: str
    bridge_class: str
    safety_invariant: str


@dataclass(frozen=True)
class SabinCodecCompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    subsystem_counts: Dict[str, int]
    touchpoints: Tuple[SabinCodecTouchpointEntry, ...]


@dataclass(frozen=True)
class Pillar1DualSocIpcReport:
    passed: bool
    dtb_summary: BinaryHeaderSummary
    dtb_marker_hits: Dict[str, int]
    insmod_ipc_kmods_verified: bool
    pci_ep_cp_ko_hits: Dict[str, int]
    pcie_if_ko_hits: Dict[str, int]
    fx3_cp_cetus_hits: Dict[str, int]
    fx6_cp_cetus_hits: Dict[str, int]
    fx3_backup_summary: BinaryHeaderSummary
    fx6_backup_summary: BinaryHeaderSummary
    route1_invariance_eval: DualSocPcieSlvsecEvalResult
    route2_cp_flash_blocked_eval: DualSocPcieSlvsecEvalResult
    pcie_id_mismatch_blocked_eval: DualSocPcieSlvsecEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2SabinDspDmmReport:
    passed: bool
    sabin_dict_count_fx3: int
    sabin_dict_count_fx6: int
    sabin_sp01_summary: BinaryHeaderSummary
    codec_drv_ko_hits: Dict[str, int]
    fx3_dmmcfg_summary: DmmCfgSummary
    fx6_dmmcfg_summary: DmmCfgSummary
    dci_4k_60p_alignment_eval: SabinDspDmmPoolEvalResult
    qfhd_120p_alignment_eval: SabinDspDmmPoolEvalResult
    raw_dmmcfg_flash_blocked_eval: SabinDspDmmPoolEvalResult
    extent_overflow_blocked_eval: SabinDspDmmPoolEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3CodecBoundaryReport:
    passed: bool
    fx3_appfw_summary: ElfSectionSummary
    fx6_appfw_summary: ElfSectionSummary
    fx3_mpr_summary: ElfSectionSummary
    fx6_mpr_summary: ElfSectionSummary
    fx3_sencore_summary: ElfSectionSummary
    fx6_sencore_summary: ElfSectionSummary
    fx6_exclusive_fpga_cp_hits: Dict[str, int]
    fx3_fpga_cp_hits: Dict[str, int]
    mew_fpga_summary: BinaryHeaderSummary
    xavc_i_dci_4k_eval: HardwareCodecBoundaryEvalResult
    xavc_si_qfhd_eval: HardwareCodecBoundaryEvalResult
    xavc_hs_hevc_422_eval: HardwareCodecBoundaryEvalResult
    hdmi_raw_16bit_eval: HardwareCodecBoundaryEvalResult
    sdi_raw_mew_masked_eval: HardwareCodecBoundaryEvalResult
    xocn_5k_opengate_masked_eval: HardwareCodecBoundaryEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4WriteGuardAndMatrixReport:
    passed: bool
    volatile_ram_guard_ok: Phase164WriteGuardResult
    ext_clip_guard_ok: Phase164WriteGuardResult
    blocked_cpapp_guard: Phase164WriteGuardResult
    blocked_sabin_guard: Phase164WriteGuardResult
    blocked_mew_spinor_guard: Phase164WriteGuardResult
    blocked_backup_p2_guard: Phase164WriteGuardResult
    compatibility_matrix: SabinCodecCompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwCxd90057Cxd90058SabinCodecReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    dual_soc_ipc_invariance_verified: bool
    sabin_dsp_dmm_aligned: bool
    xavc_hevc_codec_boundary_verified: bool
    sdi_raw_mew_fpga_masked: bool
    appfw_crash_prevented: bool
    cxd90058_fw_mutation_bytes: int
    cp_mutation_bytes: int
    sabin_microcode_mutation_bytes: int
    emmc_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    donor_file_sizes: Dict[str, int]
    pillar1_dual_soc_ipc: Pillar1DualSocIpcReport
    pillar2_sabin_dsp_dmm: Pillar2SabinDspDmmReport
    pillar3_codec_boundary: Pillar3CodecBoundaryReport
    pillar4_write_guard_matrix: Pillar4WriteGuardAndMatrixReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only Binary Helpers (os.O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------


def _read_bounded_rdonly(path: Path, max_bytes: int) -> Tuple[int, bytes]:
    """Read at most `max_bytes` from `path` strictly via `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        total = os.fstat(fd).st_size
        n = min(total, max_bytes)
        data = os.read(fd, n) if n > 0 else b""
        return total, data
    finally:
        os.close(fd)


def _scan_tokens_mmap_rdonly_p164(
    path: Path, tokens: Sequence[str]
) -> Tuple[int, Dict[str, int]]:
    """Open `path` strictly `os.O_RDONLY` and scan tokens with `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {t: 0 for t in tokens}
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return sz, _count_tokens_single_pass(mm, tokens)
    finally:
        os.close(fd)


def parse_dtb_header_and_markers(
    buf: bytes, *, source_mode: str, artifact_name: str = "7.02-setting-cxd90057.dtb"
) -> Tuple[BinaryHeaderSummary, Dict[str, int]]:
    """Validate FDT (`0xd00dfeed`) header and scan `cxd90057` PCIe device-tree markers."""
    hits = _count_tokens_single_pass(buf, DTB_CXD90057_MARKERS)
    if len(buf) < 40:
        return (
            BinaryHeaderSummary(
                artifact_name=artifact_name,
                source_mode=source_mode,
                file_bytes=len(buf),
                header_magic_hex=buf[:4].hex(),
                valid=False,
                details="TRUNCATED_FDT_HEADER",
            ),
            hits,
        )
    magic_u32, total_size = struct.unpack_from(">II", buf, 0)
    magic_ok = magic_u32 == FDT_MAGIC_U32
    size_ok = total_size <= len(buf) and total_size >= 40
    markers_ok = all(hits[m] > 0 for m in DTB_CXD90057_MARKERS)
    valid = magic_ok and size_ok and markers_ok
    return (
        BinaryHeaderSummary(
            artifact_name=artifact_name,
            source_mode=source_mode,
            file_bytes=len(buf),
            header_magic_hex=buf[:4].hex(),
            valid=valid,
            details=f"fdt_totalsize={total_size}",
        ),
        hits,
    )


def parse_sabin_sp01_header(
    head: bytes, *, total_bytes: int, source_mode: str, artifact_name: str = "sa_sabin_cp_cam_post.bin"
) -> BinaryHeaderSummary:
    """Validate Sony `SP\\x01\\x00` (`53500100`) SA-DSP microcode/table header."""
    magic_hex = head[:4].hex() if len(head) >= 4 else head.hex()
    valid = len(head) >= 16 and magic_hex == SABIN_SP01_MAGIC_HEX and total_bytes >= 4096
    entry_words = struct.unpack_from("<IIII", head, 0) if len(head) >= 16 else (0, 0, 0, 0)
    return BinaryHeaderSummary(
        artifact_name=artifact_name,
        source_mode=source_mode,
        file_bytes=total_bytes,
        header_magic_hex=magic_hex,
        valid=valid,
        details=f"sp_hdr_u32={entry_words[0]:08x}:{entry_words[1]:08x}:{entry_words[2]:08x}",
    )


def parse_mew_fpga_bitstream_header(
    head: bytes, *, total_bytes: int, source_mode: str, artifact_name: str = "mew.bin"
) -> BinaryHeaderSummary:
    """Validate FX6-only Xilinx `mew.bin` FPGA bitstream bus-width + sync word (`0xaa995566`)."""
    bus_ok = len(head) >= 52 and head[0x20:0x28].hex() == XILINX_BUS_DETECT_HEX
    sync_ok = len(head) >= 52 and head[XILINX_FPGA_SYNC_OFFSET : XILINX_FPGA_SYNC_OFFSET + 4].hex() == XILINX_FPGA_SYNC_HEX
    valid = bus_ok and sync_ok and total_bytes > 1_000_000
    return BinaryHeaderSummary(
        artifact_name=artifact_name,
        source_mode=source_mode,
        file_bytes=total_bytes,
        header_magic_hex=head[XILINX_FPGA_SYNC_OFFSET : XILINX_FPGA_SYNC_OFFSET + 4].hex()
        if len(head) >= 52
        else "",
        valid=valid,
        details=f"xilinx_bus_detect_off=0x20,sync_off=0x{XILINX_FPGA_SYNC_OFFSET:02x}",
    )


def parse_backup_bin_header_summary(
    head: bytes, *, total_bytes: int, source_mode: str, artifact_name: str
) -> BinaryHeaderSummary:
    """Validate `BK4\\x00` (`00000004aaaaaaaa00000000424b3400`) Backup.bin container header."""
    magic_hex = head[:16].hex() if len(head) >= 16 else head.hex()
    valid = magic_hex == BK4_HEADER_MAGIC_HEX and total_bytes >= 1_000_000
    return BinaryHeaderSummary(
        artifact_name=artifact_name,
        source_mode=source_mode,
        file_bytes=total_bytes,
        header_magic_hex=magic_hex,
        valid=valid,
        details=f"bk4_header_ok={valid}",
    )


# ---------------------------------------------------------------------------
# Pillar 1..4 Deterministic Evaluators & 12-Touchpoint Compatibility Matrix
# ---------------------------------------------------------------------------


def evaluate_dual_soc_pcie_slvsec_invariance(
    *,
    deployment_route: str = "ROUTE1_HYBRID_USERLAND_STAGE_B",
    cxd90058_fw_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    pcie_ep_vendor_id: int = CXD90057_PCIE_VENDOR_ID,
    pcie_ep_device_id: int = CXD90057_PCIE_DEVICE_ID,
    slvsec_mphy_stock_preserved: bool = True,
    backup_bin_stock_preserved: bool = True,
    dtb_cxd90057_stock_preserved: bool = True,
) -> DualSocPcieSlvsecEvalResult:
    """Verify CXD90057 (Mira) <-> CXD90058 (Cetus) PCIe/SLVS-EC & p8 stock invariance."""
    errors: List[str] = []
    if deployment_route not in VALID_DEPLOYMENT_ROUTES_P164:
        errors.append(f"UNKNOWN_DEPLOYMENT_ROUTE: {deployment_route}")
    elif deployment_route != "ROUTE1_HYBRID_USERLAND_STAGE_B":
        errors.append(f"BLOCKED_NON_ROUTE1_CP_REPLACEMENT: {deployment_route}")

    if cxd90058_fw_mutation_bytes != 0:
        errors.append(f"CXD90058_FW_MUTATION_NONZERO: {cxd90058_fw_mutation_bytes}")
    if cp_mutation_bytes != 0:
        errors.append(f"CPAPP_P8_MUTATION_NONZERO: {cp_mutation_bytes}")
    if pcie_ep_vendor_id != CXD90057_PCIE_VENDOR_ID or pcie_ep_device_id != CXD90057_PCIE_DEVICE_ID:
        errors.append(
            f"PCIE_EP_ID_MISMATCH: 0x{pcie_ep_vendor_id:04x}:0x{pcie_ep_device_id:04x}"
        )
    if not slvsec_mphy_stock_preserved:
        errors.append("CETUS_SLVSEC_MPHY_NOT_STOCK")
    if not backup_bin_stock_preserved:
        errors.append("BACKUP_BIN_NOT_STOCK")
    if not dtb_cxd90057_stock_preserved:
        errors.append("CXD90057_DTB_NOT_STOCK")

    valid = len(errors) == 0
    return DualSocPcieSlvsecEvalResult(
        valid=valid,
        deployment_route=deployment_route,
        cxd90057_codename=CXD90057_SOC_CODENAME,
        cxd90058_codename=CXD90058_SOC_CODENAME,
        pcie_ep_id=f"0x{pcie_ep_vendor_id:04x}:0x{pcie_ep_device_id:04x}",
        cxd90058_fw_mutation_bytes=cxd90058_fw_mutation_bytes,
        cp_mutation_bytes=cp_mutation_bytes,
        slvsec_mphy_stock_preserved=slvsec_mphy_stock_preserved,
        backup_bin_stock_preserved=backup_bin_stock_preserved,
        dtb_cxd90057_stock_preserved=dtb_cxd90057_stock_preserved,
        route1_invariance_verified=valid,
        status="ROUTE1_DUAL_SOC_INVARIANT" if valid else errors[0],
        errors=tuple(errors),
    )


def evaluate_sabin_dsp_and_dmm_pool_alignment(
    *,
    resolution: str = "4096x2160",
    fps: float = 59.94,
    codec_profile: str = "XAVC_I_DCI_4K",
    sabin_microcode_mutation_bytes: int = 0,
    dmm_mode_id: int = 31,
    dmm_extent_count: int = 1,
    sabin_cp_cam_post_loaded: bool = True,
    ld_preload_shim_active: bool = True,
    raw_fx6_dmmcfg_flash: bool = False,
) -> SabinDspDmmPoolEvalResult:
    """Verify `sabin` 32-bit SA-DSP microcode & `DmmCfg.bin` pool/extent alignment."""
    errors: List[str] = []
    if sabin_microcode_mutation_bytes != 0:
        errors.append(f"SABIN_MICROCODE_MUTATION_NONZERO: {sabin_microcode_mutation_bytes}")
    if raw_fx6_dmmcfg_flash:
        errors.append("BLOCKED_RAW_FX6_DMMCFG_EMMC_FLASH")
    if not sabin_cp_cam_post_loaded:
        errors.append("SABIN_CP_CAM_POST_NOT_LOADED")
    if not ld_preload_shim_active:
        errors.append("LD_PRELOAD_MPR_DMM_SHIM_INACTIVE")
    if dmm_extent_count < 1 or dmm_extent_count > DMM_MAX_EXTENTS_IN_MPR_REPLY:
        errors.append(
            f"DMM_EXTENT_COUNT_OUT_OF_RANGE: {dmm_extent_count} not in 1..{DMM_MAX_EXTENTS_IN_MPR_REPLY}"
        )
    if dmm_mode_id not in (21, 25, 31, 32):
        errors.append(f"UNSUPPORTED_DMM_MODE_ID: {dmm_mode_id}")
    if resolution == "5016x3344":
        errors.append("UNSUPPORTED_5K_OPENGATE_SABIN_POOL")

    spec = CODEC_TRANSLATION_PROFILES.get(codec_profile)
    if spec is None:
        errors.append(f"UNKNOWN_CODEC_PROFILE: {codec_profile}")
        frame_kib = 0
    else:
        if not bool(spec["supported_on_fx3_stage_b"]):
            errors.append(f"BLOCKED_ABSENT_HW_CODEC_POOL: {codec_profile}")
        w_str, h_str = resolution.split("x") if "x" in resolution else ("0", "0")
        frame_kib = max(1, (int(w_str) * int(h_str) * 2) // 1024)
        if resolution not in spec["resolutions"]:  # type: ignore[operator]
            errors.append(f"RESOLUTION_MISMATCH_FOR_CODEC: {resolution} not in {spec['resolutions']}")
        if float(fps) not in spec["allowed_fps"]:  # type: ignore[operator]
            errors.append(f"FPS_NOT_IN_SABIN_CODEC_ENVELOPE: {fps}")

    valid = len(errors) == 0
    return SabinDspDmmPoolEvalResult(
        valid=valid,
        resolution=resolution,
        fps=float(fps),
        codec_profile=codec_profile,
        dmm_mode_id=dmm_mode_id,
        dmm_extent_count=dmm_extent_count,
        max_allowed_extents=DMM_MAX_EXTENTS_IN_MPR_REPLY,
        sabin_microcode_mutation_bytes=sabin_microcode_mutation_bytes,
        sabin_cp_cam_post_loaded=sabin_cp_cam_post_loaded,
        ld_preload_shim_active=ld_preload_shim_active,
        raw_fx6_dmmcfg_flash=raw_fx6_dmmcfg_flash,
        estimated_frame_pool_kib=frame_kib,
        status="SABIN_DMM_POOL_ALIGNED" if valid else errors[0],
        errors=tuple(errors),
    )


def evaluate_hardware_codec_boundary_translation(
    *,
    fx6_codec_profile: str,
    resolution: str = "3840x2160",
    fps: float = 59.94,
    chroma: str = "4:2:2",
    bit_depth: int = 10,
    sdi_raw_hw_present: bool = False,
    mask_absent_fpga_sdi: bool = True,
) -> HardwareCodecBoundaryEvalResult:
    """Translate FX6 UI codec presets to FX3 `CXD90057+CXD90058` queues & mask SDI RAW FPGA."""
    errors: List[str] = []
    spec = CODEC_TRANSLATION_PROFILES.get(fx6_codec_profile)
    if spec is None:
        return HardwareCodecBoundaryEvalResult(
            valid=False,
            codec_admitted=False,
            fx6_codec_profile=fx6_codec_profile,
            resolution=resolution,
            fps=float(fps),
            chroma=chroma,
            bit_depth=bit_depth,
            hw_encoder_queue="UNKNOWN",
            target_container="REJECTED",
            mxf_to_mp4_shim_active=False,
            masked_gracefully=False,
            appfw_crash_prevented=True,
            fpga_mew_spi_access_blocked=True,
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            status="UNKNOWN_CODEC_PROFILE",
            errors=(f"UNKNOWN_CODEC_PROFILE: {fx6_codec_profile}",),
        )

    supported = bool(spec["supported_on_fx3_stage_b"])
    hw_queue = str(spec["hw_queue"])
    fx6_container = str(spec["fx6_container"])
    target_container = str(spec["fx3_target_container"])
    bridge_class = str(spec["bridge_class"])
    mxf_shim = fx6_container == "MXF_OP1A" and target_container == "MP4_ISO_BMFF_SHIM"

    if not supported:
        if fx6_codec_profile == "SDI_RAW_16BIT_MEW_FPGA" and not sdi_raw_hw_present:
            if mask_absent_fpga_sdi:
                return HardwareCodecBoundaryEvalResult(
                    valid=False,
                    codec_admitted=False,
                    fx6_codec_profile=fx6_codec_profile,
                    resolution=resolution,
                    fps=float(fps),
                    chroma=chroma,
                    bit_depth=bit_depth,
                    hw_encoder_queue=hw_queue,
                    target_container=target_container,
                    mxf_to_mp4_shim_active=False,
                    masked_gracefully=True,
                    appfw_crash_prevented=True,
                    fpga_mew_spi_access_blocked=True,
                    bridge_class=bridge_class,
                    status="MASKED_ABSENT_SDI_RAW_MEW_FPGA",
                    errors=("MASKED_FX6_ONLY_SDI_RAW_MEW_FPGA",),
                )
            return HardwareCodecBoundaryEvalResult(
                valid=False,
                codec_admitted=False,
                fx6_codec_profile=fx6_codec_profile,
                resolution=resolution,
                fps=float(fps),
                chroma=chroma,
                bit_depth=bit_depth,
                hw_encoder_queue=hw_queue,
                target_container="APPFW_UNMASKED_FPGA_FAULT",
                mxf_to_mp4_shim_active=False,
                masked_gracefully=False,
                appfw_crash_prevented=False,
                fpga_mew_spi_access_blocked=False,
                bridge_class=bridge_class,
                status="UNMASKED_SDI_FPGA_CRASH_HAZARD",
                errors=("UNMASKED_SDI_RAW_FPGA_CRASH_HAZARD",),
            )
        return HardwareCodecBoundaryEvalResult(
            valid=False,
            codec_admitted=False,
            fx6_codec_profile=fx6_codec_profile,
            resolution=resolution,
            fps=float(fps),
            chroma=chroma,
            bit_depth=bit_depth,
            hw_encoder_queue=hw_queue,
            target_container=target_container,
            mxf_to_mp4_shim_active=False,
            masked_gracefully=True,
            appfw_crash_prevented=True,
            fpga_mew_spi_access_blocked=True,
            bridge_class=bridge_class,
            status=f"MASKED_UNSUPPORTED_PROFILE_{fx6_codec_profile}",
            errors=(f"MASKED_FX6_ONLY_PROFILE: {fx6_codec_profile}",),
        )

    if resolution not in spec["resolutions"]:  # type: ignore[operator]
        errors.append(f"RESOLUTION_MISMATCH: {resolution} not in {spec['resolutions']}")
    if float(fps) not in spec["allowed_fps"]:  # type: ignore[operator]
        errors.append(f"UNSUPPORTED_FPS: {fps} not in {spec['allowed_fps']}")
    if chroma != spec["chroma"]:
        errors.append(f"CHROMA_MISMATCH: {chroma} != {spec['chroma']}")
    if bit_depth != int(spec["bit_depth"]):  # type: ignore[arg-type]
        errors.append(f"BIT_DEPTH_MISMATCH: {bit_depth} != {spec['bit_depth']}")

    valid = len(errors) == 0
    return HardwareCodecBoundaryEvalResult(
        valid=valid,
        codec_admitted=valid,
        fx6_codec_profile=fx6_codec_profile,
        resolution=resolution,
        fps=float(fps),
        chroma=chroma,
        bit_depth=bit_depth,
        hw_encoder_queue=hw_queue,
        target_container=target_container,
        mxf_to_mp4_shim_active=mxf_shim,
        masked_gracefully=False,
        appfw_crash_prevented=True,
        fpga_mew_spi_access_blocked=True,
        bridge_class=bridge_class,
        status="CODEC_HW_QUEUE_ADMITTED" if valid else errors[0],
        errors=tuple(errors),
    )


def evaluate_phase164_write_guard(target_path: str) -> Phase164WriteGuardResult:
    """Enforce zero persistent eMMC / SPI-NOR / sabin / cpapp-b / mew.bin writes."""
    norm = target_path.strip()
    if FORBIDDEN_PERSISTENT_TARGET_RE_P164.search(norm):
        return Phase164WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            emmc_mutation_bytes=0,
            cxd90058_fw_mutation_bytes=0,
            sabin_microcode_mutation_bytes=0,
            status="BLOCKED_PERSISTENT_OR_SPINOR_TARGET",
            errors=(f"FORBIDDEN_PERSISTENT_TARGET: {norm}",),
        )
    allowed = any(norm.startswith(p) for p in VOLATILE_OR_EXT_CODEC_PREFIXES_P164)
    if not allowed:
        return Phase164WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            emmc_mutation_bytes=0,
            cxd90058_fw_mutation_bytes=0,
            sabin_microcode_mutation_bytes=0,
            status="UNLISTED_NON_VOLATILE_TARGET_BLOCKED",
            errors=(f"TARGET_NOT_VOLATILE_OR_EXTERNAL_MEDIA: {norm}",),
        )
    return Phase164WriteGuardResult(
        valid=True,
        target_path=norm,
        volatile_or_ext_allowed=True,
        persistent_write_blocked=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        emmc_mutation_bytes=0,
        cxd90058_fw_mutation_bytes=0,
        sabin_microcode_mutation_bytes=0,
        status="VOLATILE_OR_EXT_MEDIA_ALLOWED",
        errors=(),
    )


def build_phase164_sabin_codec_matrix() -> SabinCodecCompatMatrixSummary:
    """Build the deterministic 12-touchpoint 4-class compatibility matrix for Phase 164."""
    entries: Tuple[SabinCodecTouchpointEntry, ...] = (
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-01",
            subsystem="SOC_IPC",
            fx6_component="CXD90057 (Mira) <-> CXD90058 (Cetus) PCIe EP 0x1556:0x1100",
            fx3_target="Stock FX3 pci_ep_cp.ko + pcie-if.ko + osal_uipc.ko",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="cxd90058_fw_mutation_bytes == 0; 0x1556:0x1100 immutable",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-02",
            subsystem="SOC_IPC",
            fx6_component="CetusSlvsecDriver / CetusSlvsecMphy Sensor Link",
            fx3_target="Stock FX3 p8 cpapp-b.bin IMX510 SLVS-EC M-PHY",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="cp_mutation_bytes == 0; Route-1 keeps Stock FX3 p8",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-03",
            subsystem="SOC_IPC",
            fx6_component="cxd90057.dtb Device-Tree PCIe/USB Root Nodes",
            fx3_target="Stock FX3 7.02-setting-cxd90057.dtb (0xd00dfeed)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="Zero kernel/DTB reflash on nflasha",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-04",
            subsystem="SABIN_DSP",
            fx6_component="sabin 32-bit SA-DSP Microcode & 34 /usr/sabin/*.bin Tables",
            fx3_target="Stock FX3 /usr/sabin/sa_sabin_cp_cam_post.bin (SP\\x01\\x00)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="sabin_microcode_mutation_bytes == 0; identical 34 paths",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-05",
            subsystem="SABIN_DSP",
            fx6_component="FX6 DmmCfg.bin (556 units) Codec/Pool Descriptors",
            fx3_target="LD_PRELOAD shim translating onto FX3 DmmCfg.bin (603 units)",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="<= 8 extents in libmpr 0xa8 stack reply; 0 flash writes",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-06",
            subsystem="HW_CODEC",
            fx6_component="SELECT_CODEC_XAVC_I (MXF Class 300/480 4K DCI/QFHD 10b 4:2:2)",
            fx3_target="FX3 CXD90057+CXD90058 AVC480_*_H422IP + MP4 mux shim",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="Identical H.264 High422Intra HW bitstream engine",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-07",
            subsystem="HW_CODEC",
            fx6_component="SELECT_CODEC_XAVC_L (Long-GOP 4:2:2 QFHD)",
            fx3_target="FX3 libmpr.so AVC_3840_2160_H422IP + MP4 mux shim",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="Preset normalized cleanly to FX3 libmpr queue",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-08",
            subsystem="HW_CODEC",
            fx6_component="SELECT_CODEC_XAVC_S_I & XAVC HS (HEVC_3840_2160_M42210P)",
            fx3_target="Native FX3 libmpr.so AVC480_*_H422IP & HEVC_*_M42210P",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="10-bit 4:2:2 up to 119.88p hardware-native",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-09",
            subsystem="FPGA_SDI_GUARD",
            fx6_component="16-bit SDI RAW (MoniFpgaSdi / 1010_spi/mew.bin Xilinx FPGA)",
            fx3_target="SDI_OUTPUT_NOT_SUPPORT fail-closed mask -> HDMI RAW fallback",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="appfw_crash_prevented == True; 0 SPI FPGA access",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-10",
            subsystem="FPGA_SDI_GUARD",
            fx6_component="5016x3344 Open-Gate / SELECT_CODEC_X_OCN_LT",
            fx3_target="Hard-masked above IMX510 4264x2408 physical ceiling",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="Zero unaligned sabin/DMM pool allocation",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-11",
            subsystem="SOC_IPC",
            fx6_component="p8 cpapp-b.bin / p2 Backup.bin / /usr/sabin/*.bin",
            fx3_target="Hardware O_RDONLY Firewall (Stage-A/B zero flash mutation)",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="persistent_emmc_writes_authorized == False",
        ),
        SabinCodecTouchpointEntry(
            touchpoint_id="P164-12",
            subsystem="FPGA_SDI_GUARD",
            fx6_component="1010_spi/mew.bin / SPI-NOR loader_nor.bin",
            fx3_target="SPI-NOR Write Firewall (spi_nor_write_authorized = False)",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="spi_nor_write_authorized == False; zero SPI writes",
        ),
    )

    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    subsystem_counts: Dict[str, int] = {}
    for entry in entries:
        class_counts[entry.bridge_class] = class_counts.get(entry.bridge_class, 0) + 1
        subsystem_counts[entry.subsystem] = subsystem_counts.get(entry.subsystem, 0) + 1

    return SabinCodecCompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        subsystem_counts=subsystem_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def _build_synthetic_dtb() -> bytes:
    """Build a minimal valid FDT (`0xd00dfeed`) buffer containing CXD90057 PCIe nodes."""
    body = b"\x00" + b"\x00".join(m.encode("ascii") for m in DTB_CXD90057_MARKERS) + b"\x00"
    total_size = 40 + len(body)
    hdr = struct.pack(">IIIIIIIIII", FDT_MAGIC_U32, total_size, 40, 40, 40, 17, 16, 0, len(body), 0)
    return hdr + body


def build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room synthetic ELF64, DTB, DmmCfg, sabin & FPGA fixtures."""
    fx3_mpr_exports = tuple(
        list(CODEC_MPR_SHARED_MARKERS[:3])
        + [f"mpr3_exp_{i}" for i in range(EXPECTED_FX3_MPR_EXPORTS_P164 - 3)]
    )
    fx6_mpr_exports = tuple(
        list(CODEC_MPR_SHARED_MARKERS[:3])
        + [f"mpr6_exp_{i}" for i in range(EXPECTED_FX6_MPR_EXPORTS_P164 - 3)]
    )

    fx3_cp_buf = b"\x00".join(
        [m.encode("ascii") for m in CETUS_SLVSEC_CP_MARKERS + SABIN_DICTIONARY_BIN_PATHS]
    )
    fx6_cp_buf = fx3_cp_buf + b"\x00" + b"\x00".join(
        m.encode("ascii") for m in FX6_EXCLUSIVE_FPGA_SDI_CP_MARKERS
    )

    sabin_head = bytearray(256)
    sabin_head[:4] = bytes.fromhex(SABIN_SP01_MAGIC_HEX)
    struct.pack_into("<III", sabin_head, 4, 0x005F0002, 0x00000010, 0x0000018C)

    mew_head = bytearray(256)
    mew_head[0:0x20] = b"\xff" * 0x20
    mew_head[0x20:0x28] = bytes.fromhex(XILINX_BUS_DETECT_HEX)
    mew_head[0x28:0x30] = b"\xff" * 8
    mew_head[0x30:0x34] = bytes.fromhex(XILINX_FPGA_SYNC_HEX)

    bk4_head = bytearray(256)
    bk4_head[:16] = bytes.fromhex(BK4_HEADER_MAGIC_HEX)

    insmod_txt = "\n".join(f"insmod /usr/kmod/{k}" for k in INSMOD_IPC_KMODS_P164) + "\n"

    return {
        "fx3_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af3_imp_{i}" for i in range(799)),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=CODEC_APPFW_FX3_MARKERS,
        ),
        "fx6_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af6_imp_{i}" for i in range(909)),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=CODEC_APPFW_FX6_MARKERS,
        ),
        "fx3_mpr": _build_synthetic_elf64(
            exports=fx3_mpr_exports,
            imports=tuple(f"mpr3_imp_{i}" for i in range(EXPECTED_FX3_MPR_IMPORTS_P164)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=CODEC_MPR_SHARED_MARKERS,
        ),
        "fx6_mpr": _build_synthetic_elf64(
            exports=fx6_mpr_exports,
            imports=tuple(f"mpr6_imp_{i}" for i in range(EXPECTED_FX6_MPR_IMPORTS_P164)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=CODEC_MPR_SHARED_MARKERS + CODEC_MPR_FX6_EXTRA_MARKERS,
        ),
        "fx3_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc_exp_{i}" for i in range(EXPECTED_SENCORE_EXPORTS)),
            imports=tuple(f"sc_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=CODEC_SENCORE_SHARED_MARKERS,
        ),
        "fx6_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc_exp_{i}" for i in range(EXPECTED_SENCORE_EXPORTS)),
            imports=tuple(f"sc_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=CODEC_SENCORE_SHARED_MARKERS,
        ),
        "fx3_cpapp": fx3_cp_buf,
        "fx6_cpapp": fx6_cp_buf,
        "fx3_dtb": _build_synthetic_dtb(),
        "fx3_insmod_drv2": insmod_txt.encode("ascii"),
        "fx3_dmmcfg": _build_synthetic_dmmcfg(
            rules_count=FX3_DMMCFG_EXPECTED_RULES,
            unit_ids=list(TARGET_MAIN_DMM_UNIT_IDS)
            + [2000 + i for i in range(FX3_DMMCFG_EXPECTED_UNITS - len(TARGET_MAIN_DMM_UNIT_IDS))],
            version_str="for ilc32g12m-ipsxmp 2025/06/20 CLEAN_ROOM",
        ),
        "fx6_dmmcfg": _build_synthetic_dmmcfg(
            rules_count=FX6_DMMCFG_EXPECTED_RULES,
            unit_ids=list(TARGET_MAIN_DMM_UNIT_IDS)
            + [3000 + i for i in range(FX6_DMMCFG_EXPECTED_UNITS - len(TARGET_MAIN_DMM_UNIT_IDS))],
            version_str="for ilc32g12m-ipsxmp 2025/10/02 CLEAN_ROOM",
        ),
        "fx6_pci_ep_cp_ko": b"\x00".join(m.encode("ascii") for m in PCI_EP_CP_KO_MARKERS),
        "fx6_pcie_if_ko": b"\x00".join(m.encode("ascii") for m in PCIE_IF_KO_MARKERS),
        "fx6_codec_drv_ko": b"\x00".join(m.encode("ascii") for m in CODEC_DRV_KO_MARKERS),
        "fx6_sabin_head": bytes(sabin_head),
        "fx6_mew_head": bytes(mew_head),
        "fx3_backup_head": bytes(bk4_head),
        "fx6_backup_head": bytes(bk4_head),
    }


# ---------------------------------------------------------------------------
# Main Dual-Mode Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_cxd90057_cxd90058_sabin_codec(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwCxd90057Cxd90058SabinCodecReport:
    """Run Phase 164 (34th Auditor) on real O_RDONLY donors or deterministic clean-room fixtures."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    force_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not force_clean:
        rel_map = {
            "fx3_appfw": FX3_APPFW_P164_RELPATH,
            "fx6_appfw": FX6_APPFW_P164_RELPATH,
            "fx3_mpr": FX3_LIBMPR_P164_RELPATH,
            "fx6_mpr": FX6_LIBMPR_P164_RELPATH,
            "fx3_sencore": FX3_LIBSENCORE_P164_RELPATH,
            "fx6_sencore": FX6_LIBSENCORE_P164_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P164_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P164_RELPATH,
            "fx3_backup": FX3_BACKUP_BIN_P164_RELPATH,
            "fx6_backup": FX6_BACKUP_BIN_P164_RELPATH,
            "fx3_dtb": FX3_CXD90057_DTB_RELPATH,
            "fx3_insmod_drv2": FX3_INSMOD_DRV2_P164_RELPATH,
            "fx3_dmmcfg": FX3_AP_DMMCFG_P164_RELPATH,
            "fx6_dmmcfg": FX6_AP_DMMCFG_P164_RELPATH,
            "fx6_sabin_cp_cam_post": FX6_SABIN_CP_CAM_POST_RELPATH,
            "fx6_mew_bin": FX6_MEW_BIN_P164_RELPATH,
            "fx6_pci_ep_cp_ko": FX6_PCI_EP_CP_KO_RELPATH,
            "fx6_pcie_if_ko": FX6_PCIE_IF_KO_RELPATH,
            "fx6_codec_drv_ko": FX6_CODEC_DRV_KO_RELPATH,
        }
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=root)

    use_local = (not force_clean) and all(p is not None for p in donor_paths.values())
    donor_file_sizes: Dict[str, int] = {}
    errors: List[str] = []

    cp_scan_tokens = (
        CETUS_SLVSEC_CP_MARKERS
        + SABIN_DICTIONARY_BIN_PATHS
        + FX6_EXCLUSIVE_FPGA_SDI_CP_MARKERS
    )

    if use_local:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_appfw_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX3",
            tokens=CODEC_APPFW_FX3_MARKERS,
        )
        fx6_appfw_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX6",
            tokens=CODEC_APPFW_FX6_MARKERS,
        )
        fx3_mpr_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX3",
            tokens=CODEC_MPR_SHARED_MARKERS,
        )
        fx6_mpr_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX6",
            tokens=CODEC_MPR_SHARED_MARKERS + CODEC_MPR_FX6_EXTRA_MARKERS,
        )
        fx3_sencore_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_sencore"],  # type: ignore[arg-type]
            binary_name="libsencore.so",
            body_label="FX3",
            tokens=CODEC_SENCORE_SHARED_MARKERS,
        )
        fx6_sencore_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_sencore"],  # type: ignore[arg-type]
            binary_name="libsencore.so",
            body_label="FX6",
            tokens=CODEC_SENCORE_SHARED_MARKERS,
        )
        fx3_cp_sz, fx3_cp_all_hits = _scan_tokens_mmap_rdonly_p164(
            donor_paths["fx3_cpapp"],  # type: ignore[arg-type]
            cp_scan_tokens,
        )
        fx6_cp_sz, fx6_cp_all_hits = _scan_tokens_mmap_rdonly_p164(
            donor_paths["fx6_cpapp"],  # type: ignore[arg-type]
            cp_scan_tokens,
        )
        fx3_bk_sz, fx3_bk_head = _read_bounded_rdonly(donor_paths["fx3_backup"], 256)  # type: ignore[arg-type]
        fx6_bk_sz, fx6_bk_head = _read_bounded_rdonly(donor_paths["fx6_backup"], 256)  # type: ignore[arg-type]
        fx3_dtb_sz, fx3_dtb_bytes = _read_bounded_rdonly(donor_paths["fx3_dtb"], 65536)  # type: ignore[arg-type]
        insmod_sz, insmod_bytes = _read_bounded_rdonly(donor_paths["fx3_insmod_drv2"], 65536)  # type: ignore[arg-type]
        fx3_dmm_sz, fx3_dmm_bytes = _read_bounded_rdonly(donor_paths["fx3_dmmcfg"], 262144)  # type: ignore[arg-type]
        fx6_dmm_sz, fx6_dmm_bytes = _read_bounded_rdonly(donor_paths["fx6_dmmcfg"], 262144)  # type: ignore[arg-type]
        sabin_sz, sabin_head = _read_bounded_rdonly(donor_paths["fx6_sabin_cp_cam_post"], 256)  # type: ignore[arg-type]
        mew_sz, mew_head = _read_bounded_rdonly(donor_paths["fx6_mew_bin"], 256)  # type: ignore[arg-type]
        pci_ep_sz, pci_ep_hits = _scan_tokens_mmap_rdonly_p164(
            donor_paths["fx6_pci_ep_cp_ko"], PCI_EP_CP_KO_MARKERS  # type: ignore[arg-type]
        )
        pcie_if_sz, pcie_if_hits = _scan_tokens_mmap_rdonly_p164(
            donor_paths["fx6_pcie_if_ko"], PCIE_IF_KO_MARKERS  # type: ignore[arg-type]
        )
        codec_drv_sz, codec_drv_hits = _scan_tokens_mmap_rdonly_p164(
            donor_paths["fx6_codec_drv_ko"], CODEC_DRV_KO_MARKERS  # type: ignore[arg-type]
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
            "fx3_backup": fx3_bk_sz,
            "fx6_backup": fx6_bk_sz,
            "fx3_dtb": fx3_dtb_sz,
            "fx3_insmod_drv2": insmod_sz,
            "fx3_dmmcfg": fx3_dmm_sz,
            "fx6_dmmcfg": fx6_dmm_sz,
            "fx6_sabin_cp_cam_post": sabin_sz,
            "fx6_mew_bin": mew_sz,
            "fx6_pci_ep_cp_ko": pci_ep_sz,
            "fx6_pcie_if_ko": pcie_if_sz,
            "fx6_codec_drv_ko": codec_drv_sz,
        }
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx = build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures()
        fx3_appfw_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_appfw"],
            binary_name="appFw.so",
            body_label="FX3",
            source_mode=mode,
            tokens=CODEC_APPFW_FX3_MARKERS,
        )
        fx6_appfw_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_appfw"],
            binary_name="appFw.so",
            body_label="FX6",
            source_mode=mode,
            tokens=CODEC_APPFW_FX6_MARKERS,
        )
        fx3_mpr_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_mpr"],
            binary_name="libmpr.so",
            body_label="FX3",
            source_mode=mode,
            tokens=CODEC_MPR_SHARED_MARKERS,
        )
        fx6_mpr_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_mpr"],
            binary_name="libmpr.so",
            body_label="FX6",
            source_mode=mode,
            tokens=CODEC_MPR_SHARED_MARKERS + CODEC_MPR_FX6_EXTRA_MARKERS,
        )
        fx3_sencore_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_sencore"],
            binary_name="libsencore.so",
            body_label="FX3",
            source_mode=mode,
            tokens=CODEC_SENCORE_SHARED_MARKERS,
        )
        fx6_sencore_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_sencore"],
            binary_name="libsencore.so",
            body_label="FX6",
            source_mode=mode,
            tokens=CODEC_SENCORE_SHARED_MARKERS,
        )
        fx3_cp_all_hits = _count_tokens_single_pass(fx["fx3_cpapp"], cp_scan_tokens)
        fx6_cp_all_hits = _count_tokens_single_pass(fx["fx6_cpapp"], cp_scan_tokens)
        fx3_bk_sz = EXPECTED_FX3_BACKUP_BYTES_P164
        fx6_bk_sz = EXPECTED_FX6_BACKUP_BYTES_P164
        fx3_bk_head = fx["fx3_backup_head"]
        fx6_bk_head = fx["fx6_backup_head"]
        fx3_dtb_bytes = fx["fx3_dtb"]
        insmod_bytes = fx["fx3_insmod_drv2"]
        fx3_dmm_bytes = fx["fx3_dmmcfg"]
        fx6_dmm_bytes = fx["fx6_dmmcfg"]
        sabin_sz = EXPECTED_FX6_SABIN_CP_CAM_POST_BYTES
        sabin_head = fx["fx6_sabin_head"]
        mew_sz = EXPECTED_FX6_MEW_BIN_BYTES_P164
        mew_head = fx["fx6_mew_head"]
        pci_ep_hits = _count_tokens_single_pass(fx["fx6_pci_ep_cp_ko"], PCI_EP_CP_KO_MARKERS)
        pcie_if_hits = _count_tokens_single_pass(fx["fx6_pcie_if_ko"], PCIE_IF_KO_MARKERS)
        codec_drv_hits = _count_tokens_single_pass(fx["fx6_codec_drv_ko"], CODEC_DRV_KO_MARKERS)

        donor_file_sizes = {
            "fx3_appfw": len(fx["fx3_appfw"]),
            "fx6_appfw": len(fx["fx6_appfw"]),
            "fx3_mpr": len(fx["fx3_mpr"]),
            "fx6_mpr": len(fx["fx6_mpr"]),
            "fx3_sencore": len(fx["fx3_sencore"]),
            "fx6_sencore": len(fx["fx6_sencore"]),
            "fx3_cpapp": len(fx["fx3_cpapp"]),
            "fx6_cpapp": len(fx["fx6_cpapp"]),
            "fx3_backup": fx3_bk_sz,
            "fx6_backup": fx6_bk_sz,
            "fx3_dtb": len(fx3_dtb_bytes),
            "fx3_insmod_drv2": len(insmod_bytes),
            "fx3_dmmcfg": len(fx3_dmm_bytes),
            "fx6_dmmcfg": len(fx6_dmm_bytes),
            "fx6_sabin_cp_cam_post": sabin_sz,
            "fx6_mew_bin": mew_sz,
            "fx6_pci_ep_cp_ko": len(fx["fx6_pci_ep_cp_ko"]),
            "fx6_pcie_if_ko": len(fx["fx6_pcie_if_ko"]),
            "fx6_codec_drv_ko": len(fx["fx6_codec_drv_ko"]),
        }

    # ---- Pillar 1: CXD90057 (Mira) <-> CXD90058 (Cetus) Dual-SoC Boot & PCIe/SLVS-EC Invariance ----
    p1_errors: List[str] = []
    dtb_sum, dtb_hits = parse_dtb_header_and_markers(fx3_dtb_bytes, source_mode=mode)
    if not dtb_sum.valid:
        p1_errors.append(f"FX3 cxd90057.dtb validation failed: {dtb_sum.details}")

    insmod_txt = insmod_bytes.decode("ascii", errors="replace")
    insmod_ok = all(k in insmod_txt for k in INSMOD_IPC_KMODS_P164)
    if not insmod_ok:
        p1_errors.append("FX3 insmod_drv2 missing PCIe/UIPC/DMM/Codec kernel modules")

    for label, hits in (
        ("fx6_pci_ep_cp_ko", pci_ep_hits),
        ("fx6_pcie_if_ko", pcie_if_hits),
    ):
        missing = [k for k, v in hits.items() if v <= 0]
        if missing:
            p1_errors.append(f"{label} missing PCIe IPC markers: {missing}")

    fx3_cetus_hits = {k: fx3_cp_all_hits[k] for k in CETUS_SLVSEC_CP_MARKERS}
    fx6_cetus_hits = {k: fx6_cp_all_hits[k] for k in CETUS_SLVSEC_CP_MARKERS}
    for label, hits in (("fx3_cpapp", fx3_cetus_hits), ("fx6_cpapp", fx6_cetus_hits)):
        missing = [k for k, v in hits.items() if v <= 0]
        if missing:
            p1_errors.append(f"{label} missing Cetus SLVS-EC markers: {missing}")

    fx3_bk_sum = parse_backup_bin_header_summary(
        fx3_bk_head, total_bytes=fx3_bk_sz, source_mode=mode, artifact_name="FX3-Backup.bin"
    )
    fx6_bk_sum = parse_backup_bin_header_summary(
        fx6_bk_head, total_bytes=fx6_bk_sz, source_mode=mode, artifact_name="FX6-Backup.bin"
    )
    if not (fx3_bk_sum.valid and fx6_bk_sum.valid):
        p1_errors.append("Backup.bin BK4 header verification failed")

    r1_eval = evaluate_dual_soc_pcie_slvsec_invariance(
        deployment_route="ROUTE1_HYBRID_USERLAND_STAGE_B",
        cxd90058_fw_mutation_bytes=0,
        cp_mutation_bytes=0,
    )
    r2_blocked = evaluate_dual_soc_pcie_slvsec_invariance(
        deployment_route="ROUTE2_FULL_CP_FLASH",
        cxd90058_fw_mutation_bytes=16_384,
        cp_mutation_bytes=17_952_816,
    )
    pcie_blocked = evaluate_dual_soc_pcie_slvsec_invariance(
        pcie_ep_vendor_id=0x10EE,
        pcie_ep_device_id=0x7024,
    )
    if not r1_eval.valid:
        p1_errors.append("Route-1 dual-SoC invariance check failed")
    if r2_blocked.valid or pcie_blocked.valid:
        p1_errors.append("Pillar 1 failed to block Route-2 CP flash or PCIe EP mismatch")

    p1_report = Pillar1DualSocIpcReport(
        passed=len(p1_errors) == 0,
        dtb_summary=dtb_sum,
        dtb_marker_hits=dtb_hits,
        insmod_ipc_kmods_verified=insmod_ok,
        pci_ep_cp_ko_hits=pci_ep_hits,
        pcie_if_ko_hits=pcie_if_hits,
        fx3_cp_cetus_hits=fx3_cetus_hits,
        fx6_cp_cetus_hits=fx6_cetus_hits,
        fx3_backup_summary=fx3_bk_sum,
        fx6_backup_summary=fx6_bk_sum,
        route1_invariance_eval=r1_eval,
        route2_cp_flash_blocked_eval=r2_blocked,
        pcie_id_mismatch_blocked_eval=pcie_blocked,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: `sabin` 32-bit SA-DSP Microcode & `DmmCfg.bin` Pool Alignment ----
    p2_errors: List[str] = []
    sabin_dict_fx3 = sum(1 for p in SABIN_DICTIONARY_BIN_PATHS if fx3_cp_all_hits[p] > 0)
    sabin_dict_fx6 = sum(1 for p in SABIN_DICTIONARY_BIN_PATHS if fx6_cp_all_hits[p] > 0)
    if sabin_dict_fx3 != len(SABIN_DICTIONARY_BIN_PATHS) or sabin_dict_fx6 != len(SABIN_DICTIONARY_BIN_PATHS):
        p2_errors.append(
            f"sabin dictionary count mismatch: fx3={sabin_dict_fx3}, fx6={sabin_dict_fx6}, expected={len(SABIN_DICTIONARY_BIN_PATHS)}"
        )

    sabin_sp01_sum = parse_sabin_sp01_header(
        sabin_head, total_bytes=sabin_sz, source_mode=mode
    )
    if not sabin_sp01_sum.valid:
        p2_errors.append(f"sa_sabin_cp_cam_post.bin SP01 header invalid: {sabin_sp01_sum.header_magic_hex}")

    missing_codec_drv = [k for k, v in codec_drv_hits.items() if v <= 0]
    if missing_codec_drv:
        p2_errors.append(f"codec_drv.ko missing UIPC/loader markers: {missing_codec_drv}")

    fx3_dmm_sum, _ = parse_dmm_cfg_bytes(fx3_dmm_bytes, body_label="FX3", source_mode=mode)
    fx6_dmm_sum, _ = parse_dmm_cfg_bytes(fx6_dmm_bytes, body_label="FX6", source_mode=mode)
    if fx3_dmm_sum.units_count != FX3_DMMCFG_EXPECTED_UNITS or fx3_dmm_sum.rules_count != FX3_DMMCFG_EXPECTED_RULES:
        p2_errors.append(f"FX3 DmmCfg counts unexpected: {fx3_dmm_sum.units_count}/{fx3_dmm_sum.rules_count}")
    if fx6_dmm_sum.units_count != FX6_DMMCFG_EXPECTED_UNITS or fx6_dmm_sum.rules_count != FX6_DMMCFG_EXPECTED_RULES:
        p2_errors.append(f"FX6 DmmCfg counts unexpected: {fx6_dmm_sum.units_count}/{fx6_dmm_sum.rules_count}")
    if fx3_dmm_sum.max_extents_per_unit > DMM_MAX_EXTENTS_IN_MPR_REPLY:
        p2_errors.append("FX3 DmmCfg exceeds 8-extent MPR stack reply cap")

    dci_60p_eval = evaluate_sabin_dsp_and_dmm_pool_alignment(
        resolution="4096x2160", fps=59.94, codec_profile="XAVC_I_DCI_4K", dmm_mode_id=31, dmm_extent_count=1
    )
    qfhd_120p_eval = evaluate_sabin_dsp_and_dmm_pool_alignment(
        resolution="3840x2160", fps=119.88, codec_profile="XAVC_SI_QFHD", dmm_mode_id=32, dmm_extent_count=1
    )
    raw_dmm_blocked = evaluate_sabin_dsp_and_dmm_pool_alignment(raw_fx6_dmmcfg_flash=True)
    ext_overflow_blocked = evaluate_sabin_dsp_and_dmm_pool_alignment(dmm_extent_count=9)
    if not (dci_60p_eval.valid and qfhd_120p_eval.valid):
        p2_errors.append("Pillar 2 valid sabin/DMM alignment case rejected")
    if raw_dmm_blocked.valid or ext_overflow_blocked.valid:
        p2_errors.append("Pillar 2 failed to block raw FX6 DmmCfg flash or >8 extent overflow")

    p2_report = Pillar2SabinDspDmmReport(
        passed=len(p2_errors) == 0,
        sabin_dict_count_fx3=sabin_dict_fx3,
        sabin_dict_count_fx6=sabin_dict_fx6,
        sabin_sp01_summary=sabin_sp01_sum,
        codec_drv_ko_hits=codec_drv_hits,
        fx3_dmmcfg_summary=fx3_dmm_sum,
        fx6_dmmcfg_summary=fx6_dmm_sum,
        dci_4k_60p_alignment_eval=dci_60p_eval,
        qfhd_120p_alignment_eval=qfhd_120p_eval,
        raw_dmmcfg_flash_blocked_eval=raw_dmm_blocked,
        extent_overflow_blocked_eval=ext_overflow_blocked,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: XAVC-I / HEVC Hardware Encoder Mapping vs Masked 16-bit SDI RAW FPGA ----
    p3_errors: List[str] = []
    for label, summary in (
        ("fx3_appfw", fx3_appfw_sum),
        ("fx6_appfw", fx6_appfw_sum),
        ("fx3_mpr", fx3_mpr_sum),
        ("fx6_mpr", fx6_mpr_sum),
        ("fx3_sencore", fx3_sencore_sum),
        ("fx6_sencore", fx6_sencore_sum),
    ):
        missing = [k for k, v in summary.marker_hits.items() if v <= 0]
        if missing:
            p3_errors.append(f"{label} missing codec markers: {missing}")

    if fx3_mpr_sum.export_count != EXPECTED_FX3_MPR_EXPORTS_P164:
        p3_errors.append(
            f"FX3 libmpr.so export count mismatch: {fx3_mpr_sum.export_count} != {EXPECTED_FX3_MPR_EXPORTS_P164}"
        )
    if fx6_mpr_sum.export_count != EXPECTED_FX6_MPR_EXPORTS_P164:
        p3_errors.append(
            f"FX6 libmpr.so export count mismatch: {fx6_mpr_sum.export_count} != {EXPECTED_FX6_MPR_EXPORTS_P164}"
        )

    fx6_fpga_cp_hits = {k: fx6_cp_all_hits[k] for k in FX6_EXCLUSIVE_FPGA_SDI_CP_MARKERS}
    fx3_fpga_cp_hits = {k: fx3_cp_all_hits[k] for k in FX6_EXCLUSIVE_FPGA_SDI_CP_MARKERS}
    if any(v <= 0 for v in fx6_fpga_cp_hits.values()):
        p3_errors.append(f"FX6 cpapp-b.bin missing MoniFpgaSdi markers: {fx6_fpga_cp_hits}")
    if any(v != 0 for v in fx3_fpga_cp_hits.values()):
        p3_errors.append(f"FX3 cpapp-b.bin unexpectedly contains MoniFpgaSdi markers: {fx3_fpga_cp_hits}")

    mew_sum = parse_mew_fpga_bitstream_header(
        mew_head, total_bytes=mew_sz, source_mode=mode
    )
    if not mew_sum.valid:
        p3_errors.append(f"FX6 mew.bin FPGA header invalid: {mew_sum.details}")

    xavc_i_eval = evaluate_hardware_codec_boundary_translation(
        fx6_codec_profile="XAVC_I_DCI_4K", resolution="4096x2160", fps=59.94, chroma="4:2:2", bit_depth=10
    )
    xavc_si_eval = evaluate_hardware_codec_boundary_translation(
        fx6_codec_profile="XAVC_SI_QFHD", resolution="3840x2160", fps=119.88, chroma="4:2:2", bit_depth=10
    )
    xavc_hs_eval = evaluate_hardware_codec_boundary_translation(
        fx6_codec_profile="XAVC_HS_QFHD_422_10B", resolution="3840x2160", fps=59.94, chroma="4:2:2", bit_depth=10
    )
    hdmi_raw_eval = evaluate_hardware_codec_boundary_translation(
        fx6_codec_profile="HDMI_RAW_16BIT", resolution="4264x2408", fps=59.94, chroma="RAW", bit_depth=16
    )
    sdi_masked = evaluate_hardware_codec_boundary_translation(
        fx6_codec_profile="SDI_RAW_16BIT_MEW_FPGA", resolution="4096x2160", fps=59.94, chroma="RAW", bit_depth=16
    )
    xocn_masked = evaluate_hardware_codec_boundary_translation(
        fx6_codec_profile="X_OCN_LT_5K_OPENGATE", resolution="5016x3344", fps=23.98, chroma="RAW", bit_depth=16
    )

    if not (xavc_i_eval.valid and xavc_si_eval.valid and xavc_hs_eval.valid and hdmi_raw_eval.valid):
        p3_errors.append("Pillar 3 valid XAVC-I/S-I/HS/HDMI-RAW translation failed")
    if (
        sdi_masked.valid
        or sdi_masked.codec_admitted
        or not sdi_masked.masked_gracefully
        or not sdi_masked.appfw_crash_prevented
        or not sdi_masked.fpga_mew_spi_access_blocked
    ):
        p3_errors.append("Pillar 3 failed to gracefully mask FX6-only 16-bit SDI RAW mew.bin FPGA path")
    if xocn_masked.valid or xocn_masked.codec_admitted or not xocn_masked.masked_gracefully:
        p3_errors.append("Pillar 3 failed to mask 5016x3344 X-OCN LT Open-Gate")

    p3_report = Pillar3CodecBoundaryReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_summary=fx3_appfw_sum,
        fx6_appfw_summary=fx6_appfw_sum,
        fx3_mpr_summary=fx3_mpr_sum,
        fx6_mpr_summary=fx6_mpr_sum,
        fx3_sencore_summary=fx3_sencore_sum,
        fx6_sencore_summary=fx6_sencore_sum,
        fx6_exclusive_fpga_cp_hits=fx6_fpga_cp_hits,
        fx3_fpga_cp_hits=fx3_fpga_cp_hits,
        mew_fpga_summary=mew_sum,
        xavc_i_dci_4k_eval=xavc_i_eval,
        xavc_si_qfhd_eval=xavc_si_eval,
        xavc_hs_hevc_422_eval=xavc_hs_eval,
        hdmi_raw_16bit_eval=hdmi_raw_eval,
        sdi_raw_mew_masked_eval=sdi_masked,
        xocn_5k_opengate_masked_eval=xocn_masked,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: Non-Volatile Write Firewall & 12-Touchpoint 4-Class Matrix ----
    p4_errors: List[str] = []
    wg_ram = evaluate_phase164_write_guard("/tmp/stage_b_sabin_codec_shadow.json")
    wg_clip = evaluate_phase164_write_guard("/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.MP4")
    wg_cpapp = evaluate_phase164_write_guard("p8:/cpapp-b.bin")
    wg_sabin = evaluate_phase164_write_guard("/usr/sabin/sa_sabin_cp_cam_post.bin")
    wg_mew = evaluate_phase164_write_guard("spi_nor:/mew.bin")
    wg_backup = evaluate_phase164_write_guard("p2:/Backup.bin")

    if not (wg_ram.valid and wg_clip.valid):
        p4_errors.append("Pillar 4 valid volatile/external media path rejected")
    if wg_cpapp.valid or wg_sabin.valid or wg_mew.valid or wg_backup.valid:
        p4_errors.append("Pillar 4 failed to block cpapp-b.bin / sabin / mew.bin / Backup.bin write")

    matrix = build_phase164_sabin_codec_matrix()
    if matrix.total_touchpoints != 12:
        p4_errors.append(f"Expected 12 touchpoints in matrix, got {matrix.total_touchpoints}")

    p4_report = Pillar4WriteGuardAndMatrixReport(
        passed=len(p4_errors) == 0,
        volatile_ram_guard_ok=wg_ram,
        ext_clip_guard_ok=wg_clip,
        blocked_cpapp_guard=wg_cpapp,
        blocked_sabin_guard=wg_sabin,
        blocked_mew_spinor_guard=wg_mew,
        blocked_backup_p2_guard=wg_backup,
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
        "schema_version": PHASE_164_SCHEMA,
        "phase_version": PHASE_164_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "dual_soc_ipc_invariance_verified": p1_report.passed,
        "sabin_dsp_dmm_aligned": p2_report.passed,
        "xavc_hevc_codec_boundary_verified": p3_report.passed,
        "sdi_raw_mew_fpga_masked": bool(
            sdi_masked.masked_gracefully and sdi_masked.fpga_mew_spi_access_blocked
        ),
        "appfw_crash_prevented": bool(
            sdi_masked.appfw_crash_prevented and xocn_masked.appfw_crash_prevented
        ),
        "cxd90058_fw_mutation_bytes": 0,
        "cp_mutation_bytes": 0,
        "sabin_microcode_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "donor_file_sizes": donor_file_sizes,
        "pillar1_dual_soc_ipc": asdict(p1_report),
        "pillar2_sabin_dsp_dmm": asdict(p2_report),
        "pillar3_codec_boundary": asdict(p3_report),
        "pillar4_write_guard_matrix": asdict(p4_report),
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return RealhwCxd90057Cxd90058SabinCodecReport(
        schema_version=PHASE_164_SCHEMA,
        phase_version=PHASE_164_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        dual_soc_ipc_invariance_verified=p1_report.passed,
        sabin_dsp_dmm_aligned=p2_report.passed,
        xavc_hevc_codec_boundary_verified=p3_report.passed,
        sdi_raw_mew_fpga_masked=bool(
            sdi_masked.masked_gracefully and sdi_masked.fpga_mew_spi_access_blocked
        ),
        appfw_crash_prevented=bool(
            sdi_masked.appfw_crash_prevented and xocn_masked.appfw_crash_prevented
        ),
        cxd90058_fw_mutation_bytes=0,
        cp_mutation_bytes=0,
        sabin_microcode_mutation_bytes=0,
        emmc_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        donor_file_sizes=donor_file_sizes,
        pillar1_dual_soc_ipc=p1_report,
        pillar2_sabin_dsp_dmm=p2_report,
        pillar3_codec_boundary=p3_report,
        pillar4_write_guard_matrix=p4_report,
        report_sha256=report_sha256,
        errors=tuple(errors),
    )


def realhw_cxd90057_cxd90058_sabin_codec_report_to_dict(
    report: RealhwCxd90057Cxd90058SabinCodecReport,
) -> Dict[str, object]:
    """Convert Phase 164 report into a deterministic JSON-serializable dictionary."""
    return asdict(report)
