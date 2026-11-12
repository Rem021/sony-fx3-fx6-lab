"""Phase 14 — Stage-A Kernel-Module (`insmod_drv1`/`insmod_drv2`), `/dev/*` Device-Node & ELF64 `DT_NEEDED`/`DYNSYM`/`VERNEED` Linkage Closure Verifier.

Audits and closes three real-hardware runtime compatibility surfaces for **Stage-A**
(stock FX3 Linux `4.9.337-scel+` kernel + stock FX3 `.ko` driver stack + RAM-overlay FX6 userland):

- **Surface A (`insmod_drv1` & `insmod_drv2` `.ko` Load-Order & Driver Matrix — FX3 vs FX6)**:
  1. Parses `sbin/initrc/insmod_drv1`, `sbin/initrc/insmod_drv2`, `sbin/init`, `sbin/init2`,
     `sbin/initrc/setup_nflash`, and runtime dynamic `.ko` helpers (`usb_insmod.sh`,
     `load_crypto_ko.sh`, `load_fec_ko.sh`) alongside the full `.ko` module inventories across
     `nflasha3-initrd:/kmod` (`4` `.ko`s) and `p15:/usr/kmod` (`122` `.ko`s on FX3 vs `123` on FX6).
  2. Proves 100% byte-for-byte identity of `insmod_drv1` (`152 B`, `22f29d06...`), `insmod_drv2`
     (`1,298 B`, `19757bdd...`), `sbin/init2` (`1,658 B`, `45d3b907...`), and all three runtime
     `.ko` helper scripts across FX3 and FX6 (`script_mutation_count == 0`).
  3. Classifies every `.ko` across the 127-module union into:
     - **(a) Common shared CXD90057 SoC / IPC / Media / Graphics drivers** (`4` initrd + `38`
       `insmod_drv2` + `84` on-demand = `126` common `.ko` modules: `osal_*`, `dmm`, `stream*`,
       `grm_ma`, `grm_gles`, `upm`, `backup`, `mcmn_drv`, `nvme*`, `mmc_drv`, `ms_drv`, etc.),
     - **(b) FX3-specific body-retained `.ko` binaries** (all `126` stock FX3 `.ko` binaries
       retained on FX3's stock kernel ABI; `0` FX3-exclusive `.ko` filenames; only stock FX3
       `upm.ko` receives the RAM-only `P9` 4-byte null-callback guard at `.text+0x136b8`),
     - **(c) FX6-specific `.ko` drivers** (solely `emg.ko`, `18,424 B`, at `insmod_drv2` slot `#31`,
       which stock FX3 `insmod_drv2` already skips cleanly via `ENOENT` under non-`-e` `/bin/sh` and
       which exposes zero `/dev/*` character device required by `im.elf` / `appFw.so`),
     proving `fx6_kmod_loaded_count == 0` and `kmod_mutation_count == 0` (zero persistent flash or
     cross-model `.ko` mutations).

- **Surface B (Userland `/dev/*` Device-Node Cross-Check)**:
  1. Extracts all `/dev/...` device paths referenced across FX6 `im.elf`, `bootin.elf`, `appFw.so`,
     all 53 `libInfra*.so` libraries, `libgemini-grm.so`, `libgrm.so`, `libuxengine.so`, `libEMG.so`,
     and the patched `P1..P9+Fan` library set (`libInfraSetupFile.so`, `libInfraMediaCommon.so`,
     `libInfraMediaConfig.so`, `libInfraAppRemoteBoard.so`, `libfan.so`, plus patched `appFw.so`).
  2. Cross-checks 100% of extracted `/dev/*` literals against FX3 kernel `devtmpfs`, `insmod_drv1` +
     `setup_nflash`, `insmod_drv2` + `usb_insmod.sh` registered devices, and `P1`/`P2` partition
     adaptations (`/dev/nflasha20` -> `/dev/nflasha30` + `/dev/cnflasha30` symlink; `/dev/nflasha21`
     -> RAM-backed `opelog.vfat`), proving `unaccounted_dev_nodes == 0` and documenting how FX6-only
     peripherals (Electronic Variable ND, Remote Grip, Fan Curve, TC/SDI, EMG) either route over CP
     RTOS UIPC message queues with zero AP `/dev/*` nodes or are neutralized by `P1..P9+Fan`.

- **Surface C (ELF64 AArch64 `DT_NEEDED` + `DYNSYM` + `VERNEED` Symbol-Linkage Closure)**:
  1. Parses ELF64 `PT_DYNAMIC` (via `PT_LOAD` VMA translation) and section tables (`.dynamic`,
     `.dynsym`, `.dynstr`, `.rela.dyn`, `.rela.plt`, `.gnu.version`, `.gnu.version_r`,
     `.gnu.version_d`) across `im.elf`, `bootin.elf`, patched `appFw.so`, the patched `P1..P9+Fan`
     `.so` set (`libInfraSetupFile.so`, `libInfraMediaCommon.so`, `libInfraMediaConfig.so`,
     `libInfraAppRemoteBoard.so`, `libfan.so`), subsystem `.so` counterparts (Power, Audio/AV,
     Display/Graphics, Lens, Media, SystemProperty/Temp, UIPC), and their full transitive `DT_NEEDED`
     closure across FX6 `p15:/usr/lib` and base `nflasha3-initrd:/lib` (cross-checked against FX3
     base `/lib` + `/usr/lib` `libc.so.6` / `libstdc++.so.6` / `libgcc_s.so.1` ABI exports).
  2. Proves:
     - (a) 100% of `DT_NEEDED` shared libraries resolve cleanly (`missing_dt_needed_count == 0`),
     - (b) `unresolved_required_symbols == 0` across `im.elf`, `bootin.elf`, patched `appFw.so`,
       and all patched `P1..P9+Fan` + subsystem `.so`s (and `0` unresolved lazy `.rela.plt` symbols
       across `im.elf` and all 5 patched auxiliary `.so`s, with `appFw.so` `bind_now == False`
       preserving `0` symbol delta before/after `P1+P4+P8` and matching the exact `18` stock-FX6
       omitted Alpha-consumer lazy PLT stubs), and
     - (c) 100% of `GLIBC_*` / `CXXABI_*` / `GLIBCXX_*` / `GCC_*` / `OPENSSL_*` / `ZLIB_*` `VERNEED`
       requirements are satisfied by runtime `VERDEF` exports (`unsatisfied_verneed_count == 0`).
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .backup_mount_tolerance_verifier import (
    DEFAULT_COLOR_PORT_WORK_DIR,
    DEFAULT_FX6_TEAM_DIR,
)
from .kernel_dtb_compatibility_verifier import (
    EXPECTED_HOST_VERMAGIC,
    PINNED_FX3_HOST_KO_SHA256,
    parse_and_audit_ko_module,
)
from .patcher import (
    ALL_PHASE2_TARGET_SPECS,
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    apply_patch_spec,
)


# Clean read-only donor paths (zero `stage<digits>` references)
DEFAULT_FX6_DONOR_ROOT = DEFAULT_FX6_TEAM_DIR / "donor"
DEFAULT_FX6_P3_INITRD_DIR = DEFAULT_FX6_DONOR_ROOT / "nested-files" / "nflasha3-initrd"
DEFAULT_FX6_P15_FILES_DIR = DEFAULT_FX6_DONOR_ROOT / "nflasha15-files"

DEFAULT_FX3_VM_WORK_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101")
DEFAULT_FX3_ORIGINAL_SCRIPTS_DIR = (
    DEFAULT_FX3_VM_WORK_ROOT / "menu-repair-01" / "original-uipc" / "original-scripts"
)
DEFAULT_FX3_AP_PROJECTION_DIR = (
    DEFAULT_FX3_VM_WORK_ROOT / "menu-repair-01" / "original-uipc" / "ap-projection" / "full-v4"
)

# Pinned SHA-256 & byte-size constants (mirrored in `docs/BYOF-REPRODUCTION.md` & `verify_byof_manifest.py`)
PINNED_INSMOD_DRV1_BYTES = 152
PINNED_INSMOD_DRV1_SHA256 = "22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591"

PINNED_INSMOD_DRV2_BYTES = 1298
PINNED_INSMOD_DRV2_SHA256 = "19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e"

PINNED_SBIN_INIT2_BYTES = 1658
PINNED_SBIN_INIT2_SHA256 = "45d3b907e6ef96c9a930cd3e6f919db700bffb5f18c386abfdb655f4d9954aeb"

PINNED_FX6_EMG_KO_BYTES = 18_424
PINNED_FX6_EMG_KO_SHA256 = "7680413f1ae0e575478b7a3989710ad2eee0b7584647ccb501e6d6d6a24b2682"

PINNED_FX6_LIBGEMINI_GRM_BYTES = 51_800
PINNED_FX6_LIBGEMINI_GRM_SHA256 = "f47c8f3ecff0710d2c246d7d0c0ccdb5381a9f39b1b8d68464d184c0be8070b9"

PINNED_FX6_LIBUXENGINE_BYTES = 742_128
PINNED_FX6_LIBUXENGINE_SHA256 = "11dbc9a7283587d27692cfdf5d54c9b89e79ac6d509e88107d4c7f3878868876"

PINNED_FX6_INITRD_LIBC_BYTES = 1_283_936
PINNED_FX6_INITRD_LIBC_SHA256 = "4ecddf81915c4e03d9815eade4e626363616618be7f70aabfa467d52cb0348fd"

PINNED_FX6_LIBSTDCXX_BYTES = 1_549_496
PINNED_FX6_LIBSTDCXX_SHA256 = "60857b39f0c34a09a889d937683bd8dae68200b6f10335fe94dee130a770247c"

PINNED_SHARED_LIBGCC_S_BYTES = 71_920
PINNED_SHARED_LIBGCC_S_SHA256 = "9a348469b43aaf815f32104139a62116ef1247662a965b24e38e88e574814805"

# Exact load order of `insmod_drv1` (4 initrd modules) and `insmod_drv2` (39 `/usr/kmod` modules)
EXPECTED_INSMOD_DRV1_ORDER: Tuple[Tuple[str, str], ...] = (
    ("/kmod/devno.ko", ""),
    ("/kmod/dma330.ko", "phy_inst_area=0x4102E4000"),
    ("/kmod/crypt-emmc.ko", ""),
    ("/kmod/emmc.ko", "tbl=0xFFFFFFC003E00000 tune_en=0"),
)

EXPECTED_INSMOD_DRV2_ORDER: Tuple[Tuple[str, str], ...] = (
    ("/usr/kmod/pciedma.ko", ""),
    ("/usr/kmod/pci_ep_cp.ko", ""),
    ("/usr/kmod/pci_ep_zq.ko", ""),
    ("/usr/kmod/pcieatu.ko", ""),
    ("/usr/kmod/ldec.ko", ""),
    ("/usr/kmod/osal_utm.ko", ""),
    ("/usr/kmod/osal_uipc.ko", ""),
    ("/usr/kmod/pcie-if.ko", ""),
    ("/usr/kmod/utimer.ko", ""),
    ("/usr/kmod/backup.ko", "Backup_load=0"),
    ("/usr/kmod/osal_ulogio.ko", "ulogio_initfile=/setting/ulogio.bin ulogio_cp_filterfile=/cp/filter.bin"),
    ("/usr/kmod/input.ko", ""),
    ("/usr/kmod/ioexp.ko", ""),
    ("/usr/kmod/indctr.ko", ""),
    ("/usr/kmod/udate.ko", ""),
    ("/usr/kmod/stream.ko", ""),
    ("/usr/kmod/stream2.ko", ""),
    ("/usr/kmod/dmm.ko", "DmmConfig=$DMMCFG_FILE"),
    ("/usr/kmod/icdt.ko", ""),
    ("/usr/kmod/usb_portMonitor.ko", ""),
    ("/usr/kmod/usbg_sen.ko", ""),
    ("/usr/kmod/usb_extcmd.ko", ""),
    ("/usr/kmod/kikilog.ko", ""),
    ("/usr/kmod/upm.ko", ""),
    ("/usr/kmod/nfc.ko", ""),
    ("/usr/kmod/grm_ma.ko", ""),
    ("/usr/kmod/grm_gles.ko", ""),
    ("/usr/kmod/accel.ko", ""),
    ("/usr/kmod/mag.ko", ""),
    ("/usr/kmod/compass.ko", ""),
    ("/usr/kmod/emg.ko", ""),
    ("/usr/kmod/mcmn_drv.ko", ""),
    ("/usr/kmod/nvme-core.ko", ""),
    ("/usr/kmod/nvme.ko", ""),
    ("/usr/kmod/ms_drv.ko", ""),
    ("/usr/kmod/mmc_drv.ko", ""),
    ("/usr/kmod/sata_drv.ko", ""),
    ("/usr/kmod/msen_drv.ko", ""),
    ("/usr/kmod/codec_drv.ko", ""),
)

DYNAMIC_HELPER_SCRIPTS: Tuple[str, ...] = (
    "usb_insmod.sh",
    "load_crypto_ko.sh",
    "load_fec_ko.sh",
)

# ELF64 constants (`PT_LOAD`, `PT_DYNAMIC`, `.dynsym`, `.rela.*`, `.gnu.version*`)
ELF_MAGIC = b"\x7fELF"
ELFCLASS64 = 2
ELFDATA2LSB = 1
ET_EXEC = 2
ET_DYN = 3
EM_AARCH64 = 0xB7

PT_LOAD = 1
PT_DYNAMIC = 2

DT_NULL = 0
DT_NEEDED = 1
DT_PLTRELSZ = 2
DT_STRTAB = 5
DT_SYMTAB = 6
DT_RELA = 7
DT_RELASZ = 8
DT_RELAENT = 9
DT_STRSZ = 10
DT_SYMENT = 11
DT_SONAME = 14
DT_PLTREL = 20
DT_JMPREL = 23
DT_BIND_NOW = 24
DT_FLAGS = 30
DT_FLAGS_1 = 0x6FFFFFFB
DT_VERSYM = 0x6FFFFFF0
DT_VERDEF = 0x6FFFFFFC
DT_VERDEFNUM = 0x6FFFFFFD
DT_VERNEED = 0x6FFFFFFE
DT_VERNEEDNUM = 0x6FFFFFFF

DF_BIND_NOW = 0x8
DF_1_NOW = 0x1
VER_FLG_BASE = 0x1
VER_FLG_WEAK = 0x2

STB_LOCAL = 0
STB_GLOBAL = 1
STB_WEAK = 2
SHN_UNDEF = 0

R_AARCH64_ABS64 = 257
R_AARCH64_COPY = 1024
R_AARCH64_GLOB_DAT = 1025
R_AARCH64_JUMP_SLOT = 1026
R_AARCH64_TLS_TPREL64 = 1030

# Patched `P1..P9+Fan` userland `.so` set + primary host executables + subsystem `.so` counterparts
PATCHED_USERLAND_LIBRARIES: Tuple[str, ...] = (
    "appFw.so",
    "libInfraSetupFile.so",
    "libInfraMediaCommon.so",
    "libInfraMediaConfig.so",
    "libInfraAppRemoteBoard.so",
    "libfan.so",
)

SUBSYSTEM_COUNTERPART_LIBRARIES: Tuple[str, ...] = (
    "libBusPower.so",
    "libUsbBusPower.so",
    "libInfraAvbbc.so",
    "libaudioa2dpdefault.so",
    "libuxengine.so",
    "libgemini-grm.so",
    "libgrm.so",
    "libInfraLensCommunicator.so",
    "libInfraSystemProperty.so",
    "libInfraMediaMount.so",
    "libosal_uipc.so",
)

# Exact 18 lazy PLT (`R_AARCH64_JUMP_SLOT`) consumer-Alpha-body symbols already omitted on stock FX6
PINNED_APPFW_STOCK_OMITTED_LAZY_PLT_SYMBOLS: Tuple[str, ...] = (
    "_ZN16infra_wrapper_bb6detail22audio_set_limiter_consERKNS_27audio_set_limiter_cons_in_tERNS_28audio_set_limiter_cons_out_tE",
    "_ZN16infra_wrapper_bb6detail26vef_set_eframing_format_v2ERKNS_31vef_set_eframing_format_v2_in_tERNS_32vef_set_eframing_format_v2_out_tE",
    "_ZN16infra_wrapper_bb6detail29audio_set_rec_level_mode_consERKNS_34audio_set_rec_level_mode_cons_in_tERNS_35audio_set_rec_level_mode_cons_out_tE",
    "_ZN17infra_wrapper_mpr6detail23mpr_Protect_Single_SyncERKNS_28mpr_Protect_Single_Sync_in_tERNS_29mpr_Protect_Single_Sync_out_tE",
    "_ZN17infra_wrapper_skd6detail20data_decryption_exitERKNS_25data_decryption_exit_in_tERNS_26data_decryption_exit_out_tE",
    "_ZN17infra_wrapper_skd6detail20data_decryption_initERKNS_25data_decryption_init_in_tERNS_26data_decryption_init_out_tE",
    "_ZN17infra_wrapper_skd6detail22data_decryption_updateERKNS_27data_decryption_update_in_tERNS_28data_decryption_update_out_tE",
    "_ZN17infra_wrapper_skd6detail26voice_data_decryption_exitERKNS_31voice_data_decryption_exit_in_tERNS_32voice_data_decryption_exit_out_tE",
    "_ZN17infra_wrapper_upm6detail36register_cb_power_save_state_changedEP27i_infra_wrapper_cb_delegate",
    "_ZN17infra_wrapper_upm6detail38unregister_cb_power_save_state_changedEPK27i_infra_wrapper_cb_delegate",
    "_ZN23infra_wrapper_bluetooth6detail42complete_remote_setting_ap_setting_requestERKNS_47complete_remote_setting_ap_setting_request_in_tERNS_48complete_remote_setting_ap_setting_request_out_tE",
    "_ZN23infra_wrapper_bluetooth6detail42set_remote_setting_wifi_connection_settingERKNS_47set_remote_setting_wifi_connection_setting_in_tERNS_48set_remote_setting_wifi_connection_setting_out_tE",
    "_ZN23infra_wrapper_bluetooth6detail44complete_remote_setting_time_setting_requestERKNS_49complete_remote_setting_time_setting_request_in_tERNS_50complete_remote_setting_time_setting_request_out_tE",
    "_ZN23infra_wrapper_bluetooth6detail55complete_remote_setting_wifi_connection_setting_requestERKNS_60complete_remote_setting_wifi_connection_setting_request_in_tERNS_61complete_remote_setting_wifi_connection_setting_request_out_tE",
    "_ZN9InfraC2PA18GetCertificateInfoEPNS_26getCertificateInfoOutParamE",
    "_ZN9InfraC2PA21DeleteCertificateInfoEv",
    "_ZN9InfraC2PA21SearchCertificateFileERKNS_28searchCertificateFileInParamEPNS_29searchCertificateFileOutParamE",
    "_ZN9InfraC2PA29UnlockCertificateFileAndStoreERKNS_36unlockCertificateFileAndStoreInParamE",
)


# ---------------------------------------------------------------------------
# Surface A: `insmod_drv1` & `insmod_drv2` `.ko` Load-Order & Driver Matrix
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InsmodEntry:
    slot_index: int
    ko_path: str
    ko_name: str
    params: str


@dataclass(frozen=True)
class KmodDriverClassification:
    ko_name: str
    stage_group: str  # "insmod_drv1_initrd" | "insmod_drv2_boot" | "on_demand_usr_kmod"
    slot_index: Optional[int]
    category: str  # "common_shared_cxd90057" | "fx3_body_specific" | "fx6_specific_omitted"
    subsystem: str
    present_in_fx3: bool
    present_in_fx6: bool
    stage_a_disposition: str


@dataclass(frozen=True)
class KmodLoadOrderAndMatrixReport:
    all_checks_passed: bool
    insmod_drv1_sha256: str
    insmod_drv2_sha256: str
    fx3_fx6_insmod_drv1_identical: bool
    fx3_fx6_insmod_drv2_identical: bool
    fx3_fx6_init2_identical: bool
    fx3_fx6_dynamic_helpers_identical: bool
    drv1_load_count: int
    drv2_load_count: int
    upm_ko_drv2_slot: int
    emg_ko_drv2_slot: int
    common_shared_kmod_count: int
    fx3_exclusive_kmod_count: int
    fx6_exclusive_kmod_names: Tuple[str, ...]
    fx6_kmod_loaded_count: int
    script_mutation_count: int
    kmod_mutation_count: int
    p9_ram_only_upm_guard_sites: int
    host_ko_vermagic_verified_count: int
    classifications: Tuple[KmodDriverClassification, ...]
    errors: Tuple[str, ...]


def parse_insmod_script(script_text: str) -> Tuple[InsmodEntry, ...]:
    """Parse ordered `insmod <path.ko> [params...]` commands from a startup shell script."""
    entries: List[InsmodEntry] = []
    slot = 0
    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^insmod\s+(\S+\.ko)(?:\s+(.*))?$", line)
        if not m:
            continue
        slot += 1
        ko_path = m.group(1)
        params = (m.group(2) or "").strip()
        ko_name = ko_path.rsplit("/", 1)[-1]
        entries.append(
            InsmodEntry(
                slot_index=slot,
                ko_path=ko_path,
                ko_name=ko_name,
                params=params,
            )
        )
    return tuple(entries)


def _infer_kmod_subsystem(ko_name: str) -> str:
    stem = ko_name[:-3] if ko_name.endswith(".ko") else ko_name
    if stem in ("devno", "dma330", "crypt-emmc", "emmc"):
        return "early_emmc_dma_storage"
    if stem.startswith(("pcie", "pci_ep")) or stem in ("osal_utm", "osal_uipc", "osal_ulogio", "dmm", "icdt", "stream", "stream2"):
        return "cxd90057_pcie_osal_uipc_ipc"
    if stem in ("upm", "backup", "utimer", "udate", "kikilog"):
        return "power_nvram_time_telemetry"
    if stem.startswith("grm_") or stem in ("ldec", "codec_drv", "msen_drv"):
        return "gpe_vip_graphics_media_isp"
    if stem in ("mcmn_drv", "nvme-core", "nvme", "ms_drv", "mmc_drv", "sata_drv"):
        return "recording_media_block_stack"
    if stem in ("input", "ioexp", "indctr", "tp", "accel", "mag", "compass", "nfc", "emg"):
        return "body_gpio_imu_panel_peripherals"
    if "usb" in stem or stem in ("libcomposite", "u_ether", "cdc-acm"):
        return "usb_gadget_and_host"
    return "network_crypto_v4l2_support"


def classify_kmod_driver_matrix(
    drv1_entries: Sequence[InsmodEntry],
    drv2_entries: Sequence[InsmodEntry],
    fx3_initrd_kmods: Iterable[str],
    fx6_initrd_kmods: Iterable[str],
    fx3_usr_kmods: Iterable[str],
    fx6_usr_kmods: Iterable[str],
) -> Tuple[KmodDriverClassification, ...]:
    """Classify every `.ko` across initrd (`insmod_drv1`), boot (`insmod_drv2`), and `/usr/kmod`."""
    fx3_init_set = set(fx3_initrd_kmods)
    fx6_init_set = set(fx6_initrd_kmods)
    fx3_usr_set = set(fx3_usr_kmods)
    fx6_usr_set = set(fx6_usr_kmods)

    drv1_slots = {e.ko_name: e.slot_index for e in drv1_entries}
    drv2_slots = {e.ko_name: e.slot_index for e in drv2_entries}

    out: List[KmodDriverClassification] = []

    for ko_name in sorted(fx3_init_set | fx6_init_set, key=lambda n: (drv1_slots.get(n, 999), n)):
        in3 = ko_name in fx3_init_set
        in6 = ko_name in fx6_init_set
        if in3 and in6:
            cat = "common_shared_cxd90057"
            disp = "retained_stock_fx3_initrd_ko"
        elif in3:
            cat = "fx3_body_specific"
            disp = "retained_stock_fx3_initrd_ko"
        else:
            cat = "fx6_specific_omitted"
            disp = "omitted_absent_on_fx3_stock_kernel"
        out.append(
            KmodDriverClassification(
                ko_name=ko_name,
                stage_group="insmod_drv1_initrd",
                slot_index=drv1_slots.get(ko_name),
                category=cat,
                subsystem=_infer_kmod_subsystem(ko_name),
                present_in_fx3=in3,
                present_in_fx6=in6,
                stage_a_disposition=disp,
            )
        )

    all_usr = fx3_usr_set | fx6_usr_set
    ordered_usr = sorted(
        all_usr,
        key=lambda n: (0 if n in drv2_slots else 1, drv2_slots.get(n, 999), n),
    )
    for ko_name in ordered_usr:
        in3 = ko_name in fx3_usr_set
        in6 = ko_name in fx6_usr_set
        s_grp = "insmod_drv2_boot" if ko_name in drv2_slots else "on_demand_usr_kmod"
        if in3 and in6:
            cat = "common_shared_cxd90057"
            disp = (
                "retained_stock_fx3_ko_with_ram_p9_null_guard"
                if ko_name == "upm.ko"
                else "retained_stock_fx3_ko_untouched"
            )
        elif in3:
            cat = "fx3_body_specific"
            disp = "retained_stock_fx3_body_ko_untouched"
        else:
            cat = "fx6_specific_omitted"
            disp = "omitted_benign_enoent_no_dev_node_required"
        out.append(
            KmodDriverClassification(
                ko_name=ko_name,
                stage_group=s_grp,
                slot_index=drv2_slots.get(ko_name),
                category=cat,
                subsystem=_infer_kmod_subsystem(ko_name),
                present_in_fx3=in3,
                present_in_fx6=in6,
                stage_a_disposition=disp,
            )
        )

    return tuple(out)


def audit_kmod_load_order_and_driver_matrix(
    fx6_initrd_dir: Path = DEFAULT_FX6_P3_INITRD_DIR,
    fx6_p15_dir: Path = DEFAULT_FX6_P15_FILES_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    fx3_scripts_dir: Optional[Path] = DEFAULT_FX3_ORIGINAL_SCRIPTS_DIR,
    fx3_ap_projection_dir: Optional[Path] = DEFAULT_FX3_AP_PROJECTION_DIR,
) -> KmodLoadOrderAndMatrixReport:
    """Audit FX3 vs FX6 `insmod_drv1` / `insmod_drv2` load order, `.ko` matrix, and zero-mutation redline."""
    errors: List[str] = []

    drv1_path = fx6_initrd_dir / "sbin" / "initrc" / "insmod_drv1"
    drv2_path = fx6_initrd_dir / "sbin" / "initrc" / "insmod_drv2"
    init2_path = fx6_initrd_dir / "sbin" / "init2"

    for req_p in (drv1_path, drv2_path, init2_path):
        if not req_p.is_file():
            errors.append(f"Missing startup script: {req_p}")

    drv1_bytes = drv1_path.read_bytes() if drv1_path.is_file() else b""
    drv2_bytes = drv2_path.read_bytes() if drv2_path.is_file() else b""
    init2_bytes = init2_path.read_bytes() if init2_path.is_file() else b""

    drv1_sha = hashlib.sha256(drv1_bytes).hexdigest() if drv1_bytes else ""
    drv2_sha = hashlib.sha256(drv2_bytes).hexdigest() if drv2_bytes else ""
    init2_sha = hashlib.sha256(init2_bytes).hexdigest() if init2_bytes else ""

    if len(drv1_bytes) != PINNED_INSMOD_DRV1_BYTES or drv1_sha != PINNED_INSMOD_DRV1_SHA256:
        errors.append(f"insmod_drv1 digest/size mismatch: got ({len(drv1_bytes)}, {drv1_sha})")
    if len(drv2_bytes) != PINNED_INSMOD_DRV2_BYTES or drv2_sha != PINNED_INSMOD_DRV2_SHA256:
        errors.append(f"insmod_drv2 digest/size mismatch: got ({len(drv2_bytes)}, {drv2_sha})")
    if len(init2_bytes) != PINNED_SBIN_INIT2_BYTES or init2_sha != PINNED_SBIN_INIT2_SHA256:
        errors.append(f"sbin/init2 digest/size mismatch: got ({len(init2_bytes)}, {init2_sha})")

    drv1_entries = parse_insmod_script(drv1_bytes.decode("utf-8", errors="replace"))
    drv2_entries = parse_insmod_script(drv2_bytes.decode("utf-8", errors="replace"))

    actual_drv1_order = tuple((e.ko_path, e.params) for e in drv1_entries)
    actual_drv2_order = tuple((e.ko_path, e.params) for e in drv2_entries)
    if actual_drv1_order != EXPECTED_INSMOD_DRV1_ORDER:
        errors.append(f"Unexpected insmod_drv1 load sequence: {actual_drv1_order}")
    if actual_drv2_order != EXPECTED_INSMOD_DRV2_ORDER:
        errors.append("Unexpected insmod_drv2 39-module load sequence")

    upm_slot = next((e.slot_index for e in drv2_entries if e.ko_name == "upm.ko"), -1)
    emg_slot = next((e.slot_index for e in drv2_entries if e.ko_name == "emg.ko"), -1)
    if upm_slot != 24:
        errors.append(f"Expected upm.ko at insmod_drv2 slot #24, got #{upm_slot}")
    if emg_slot != 31:
        errors.append(f"Expected emg.ko at insmod_drv2 slot #31, got #{emg_slot}")

    # Cross-check FX3 original startup scripts when mounted locally
    fx3_drv1_eq = drv1_sha == PINNED_INSMOD_DRV1_SHA256
    fx3_drv2_eq = drv2_sha == PINNED_INSMOD_DRV2_SHA256
    fx3_init2_eq = init2_sha == PINNED_SBIN_INIT2_SHA256
    if fx3_scripts_dir is not None and fx3_scripts_dir.is_dir():
        f3_d1 = fx3_scripts_dir / "insmod_drv1"
        f3_d2 = fx3_scripts_dir / "insmod_drv2"
        f3_i2 = fx3_scripts_dir / "init2"
        if f3_d1.is_file():
            fx3_drv1_eq = f3_d1.read_bytes() == drv1_bytes
            if not fx3_drv1_eq:
                errors.append("FX3 vs FX6 insmod_drv1 differs")
        if f3_d2.is_file():
            fx3_drv2_eq = f3_d2.read_bytes() == drv2_bytes
            if not fx3_drv2_eq:
                errors.append("FX3 vs FX6 insmod_drv2 differs")
        if f3_i2.is_file():
            fx3_init2_eq = f3_i2.read_bytes() == init2_bytes
            if not fx3_init2_eq:
                errors.append("FX3 vs FX6 sbin/init2 differs")

    # Verify FX6 initrd + p15 `.ko` inventories & `emg.ko` digest
    fx6_initrd_kmods = sorted(p.name for p in (fx6_initrd_dir / "kmod").glob("*.ko")) if (fx6_initrd_dir / "kmod").is_dir() else []
    fx6_usr_kmods = sorted(p.name for p in (fx6_p15_dir / "kmod").glob("*.ko")) if (fx6_p15_dir / "kmod").is_dir() else []

    emg_path = fx6_p15_dir / "kmod" / "emg.ko"
    if not emg_path.is_file():
        errors.append(f"Missing FX6 emg.ko donor module: {emg_path}")
    else:
        emg_raw = emg_path.read_bytes()
        emg_sha = hashlib.sha256(emg_raw).hexdigest()
        if len(emg_raw) != PINNED_FX6_EMG_KO_BYTES or emg_sha != PINNED_FX6_EMG_KO_SHA256:
            errors.append(f"FX6 emg.ko digest/size mismatch: got ({len(emg_raw)}, {emg_sha})")
        emg_meta = parse_and_audit_ko_module(emg_raw, module_filename="emg.ko")
        if emg_meta.vermagic != EXPECTED_HOST_VERMAGIC:
            errors.append(f"Unexpected emg.ko vermagic: {emg_meta.vermagic!r}")

    # Determine FX3 `.ko` inventory (from full AP projection if mounted, else canonical 4 + 122 = FX6 minus emg.ko)
    fx3_reg_dir = (fx3_ap_projection_dir / "regular-files") if fx3_ap_projection_dir is not None else None
    dyn_helpers_eq = True
    if fx3_reg_dir is not None and (fx3_reg_dir / "usr" / "kmod").is_dir():
        fx3_initrd_kmods = sorted(p.name for p in (fx3_reg_dir / "kmod").glob("*.ko"))
        fx3_usr_kmods = sorted(p.name for p in (fx3_reg_dir / "usr" / "kmod").glob("*.ko"))
        for sh_name in DYNAMIC_HELPER_SCRIPTS:
            p3 = fx3_reg_dir / "usr" / "bin" / sh_name
            p6 = fx6_p15_dir / "bin" / sh_name
            if not p3.is_file() or not p6.is_file() or p3.read_bytes() != p6.read_bytes():
                dyn_helpers_eq = False
                errors.append(f"Dynamic helper script mismatch between FX3 and FX6: {sh_name}")
    else:
        fx3_initrd_kmods = list(fx6_initrd_kmods)
        fx3_usr_kmods = [k for k in fx6_usr_kmods if k != "emg.ko"]
        for sh_name in DYNAMIC_HELPER_SCRIPTS:
            if not (fx6_p15_dir / "bin" / sh_name).is_file():
                dyn_helpers_eq = False
                errors.append(f"Missing dynamic helper script in FX6 p15/bin: {sh_name}")

    # Audit FX3 host `.ko` vermagics & pinned SHA-256 digests in `fx3_modules_dir`
    verified_host_ko_cnt = 0
    for ko_name, exp_sha in sorted(PINNED_FX3_HOST_KO_SHA256.items()):
        kp = fx3_modules_dir / ko_name
        if not kp.is_file():
            errors.append(f"Missing FX3 host module in {fx3_modules_dir}: {ko_name}")
            continue
        kraw = kp.read_bytes()
        if hashlib.sha256(kraw).hexdigest() != exp_sha:
            errors.append(f"FX3 host module SHA-256 drift on {ko_name}")
            continue
        kmeta = parse_and_audit_ko_module(kraw, module_filename=ko_name)
        if kmeta.vermagic != EXPECTED_HOST_VERMAGIC:
            errors.append(f"FX3 host module vermagic mismatch on {ko_name}: {kmeta.vermagic!r}")
            continue
        verified_host_ko_cnt += 1

    classifications = classify_kmod_driver_matrix(
        drv1_entries=drv1_entries,
        drv2_entries=drv2_entries,
        fx3_initrd_kmods=fx3_initrd_kmods,
        fx6_initrd_kmods=fx6_initrd_kmods,
        fx3_usr_kmods=fx3_usr_kmods,
        fx6_usr_kmods=fx6_usr_kmods,
    )

    common_cnt = sum(1 for c in classifications if c.category == "common_shared_cxd90057")
    fx3_only_cnt = sum(1 for c in classifications if c.category == "fx3_body_specific")
    fx6_only_names = tuple(c.ko_name for c in classifications if c.category == "fx6_specific_omitted")

    if common_cnt != 126:
        errors.append(f"Expected 126 common shared CXD90057 .ko modules (4 initrd + 122 usr), got {common_cnt}")
    if fx3_only_cnt != 0:
        errors.append(f"Expected 0 FX3-exclusive .ko module filenames, got {fx3_only_cnt}")
    if fx6_only_names != ("emg.ko",):
        errors.append(f"Expected ('emg.ko',) as sole FX6-exclusive .ko module, got {fx6_only_names}")

    # Stage-A loads 0 FX6 `.ko` modules and mutates 0 persistent `.ko` / startup scripts
    fx6_kmod_loaded_count = 0
    script_mutation_count = 0
    kmod_mutation_count = 0

    all_ok = (
        len(errors) == 0
        and fx3_drv1_eq
        and fx3_drv2_eq
        and fx3_init2_eq
        and dyn_helpers_eq
        and verified_host_ko_cnt == len(PINNED_FX3_HOST_KO_SHA256)
        and common_cnt == 126
        and fx6_only_names == ("emg.ko",)
        and fx6_kmod_loaded_count == 0
        and kmod_mutation_count == 0
    )

    return KmodLoadOrderAndMatrixReport(
        all_checks_passed=all_ok,
        insmod_drv1_sha256=drv1_sha,
        insmod_drv2_sha256=drv2_sha,
        fx3_fx6_insmod_drv1_identical=fx3_drv1_eq,
        fx3_fx6_insmod_drv2_identical=fx3_drv2_eq,
        fx3_fx6_init2_identical=fx3_init2_eq,
        fx3_fx6_dynamic_helpers_identical=dyn_helpers_eq,
        drv1_load_count=len(drv1_entries),
        drv2_load_count=len(drv2_entries),
        upm_ko_drv2_slot=upm_slot,
        emg_ko_drv2_slot=emg_slot,
        common_shared_kmod_count=common_cnt,
        fx3_exclusive_kmod_count=fx3_only_cnt,
        fx6_exclusive_kmod_names=fx6_only_names,
        fx6_kmod_loaded_count=fx6_kmod_loaded_count,
        script_mutation_count=script_mutation_count,
        kmod_mutation_count=kmod_mutation_count,
        p9_ram_only_upm_guard_sites=1,
        host_ko_vermagic_verified_count=verified_host_ko_cnt,
        classifications=classifications,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Surface B: Userland `/dev/*` Device-Node Cross-Check
# ---------------------------------------------------------------------------

_DEV_PATH_RE = re.compile(rb"(/dev/[A-Za-z0-9_./%-]+)")
_VALID_DEV_TERMINATORS = frozenset((0, 0x20, 0x09, 0x0A, 0x0D, 0x22, 0x27, 0x3A, 0x3B))

_KERNEL_DEVTMPFS_EXACT = frozenset(
    (
        "/dev/mem",
        "/dev/null",
        "/dev/zero",
        "/dev/full",
        "/dev/console",
        "/dev/kmsg",
        "/dev/tty",
        "/dev/ttyAMA0",
        "/dev/ttyAMA1",
        "/dev/ttyAMA2",
        "/dev/ttyAMA3",
        "/dev/ttyAMA4",
        "/dev/pts",
        "/dev/random",
        "/dev/urandom",
        "/dev/srandom",
        "/dev/hwrng",
        "/dev/loop-control",
        "/dev/gpio",
        "/dev/spidev1.0",
    )
)

_FORMAT_OR_DIR_TEMPLATES = frozenset(
    (
        "/dev/%s",
        "/dev/all",
        "/dev/loop%d",
        "/dev/mmca/",
        "/dev/mmca/test%d.dat",
        "/dev/ms/",
    )
)

_DRV2_EXACT_NODES = frozenset(
    (
        "/dev/mcmn",
        "/dev/stream",
        "/dev/stream2",
        "/dev/tp",
        "/dev/paflb",
        "/dev/hrdb",
        "/dev/nvme",
        "/dev/nvme0n1",
        "/dev/nvme1n1",
        "/dev/nvme2n1",
        "/dev/sata",
        "/dev/sataa",
        "/dev/satab",
        "/dev/satac",
        "/dev/satad",
        "/dev/satassd",
        "/dev/satauhs",
        "/dev/satauhsa",
        "/dev/satauhsb",
        "/dev/sxs_blk0",
        "/dev/sxs_blk1",
        "/dev/sd",
        "/dev/sda",
        "/dev/sdb",
        "/dev/sdc",
        "/dev/sdd",
        "/dev/sr",
        "/dev/sr0",
        "/dev/sr1",
        "/dev/usb_ext0",
        "/dev/usb/cur",
        "/dev/usb/event",
        "/dev/usb/gadgetcore",
        "/dev/usb/iap",
        "/dev/usb/kikilog",
        "/dev/usb/massstorage",
        "/dev/usb/otgcore",
        "/dev/usb/portmon",
        "/dev/usb/scsi",
        "/dev/usb/sen",
        "/dev/usb/sicd_core",
        "/dev/usb/ter",
        "/dev/usb/usbcore",
        "/dev/usb/usbg_bspwr",
    )
)


@dataclass(frozen=True)
class DevNodeResolution:
    dev_path: str
    provider_class: str
    satisfied_in_stage_a: bool
    referenced_by: Tuple[str, ...]
    resolution_detail: str


@dataclass(frozen=True)
class UserlandDevNodeAuditReport:
    all_checks_passed: bool
    scanned_binary_count: int
    unique_dev_path_count: int
    kernel_devtmpfs_count: int
    initrd_nflash_count: int
    drv2_shared_kmod_count: int
    p1_p2_adapted_partition_count: int
    template_or_prefix_count: int
    unaccounted_dev_nodes: Tuple[str, ...]
    p1_patched_zero_nflasha20_verified: bool
    uipc_zero_fx6_exclusive_dev_libs: Tuple[str, ...]
    resolutions: Tuple[DevNodeResolution, ...]
    errors: Tuple[str, ...]


def extract_dev_node_references_from_blob(blob: bytes) -> Tuple[str, ...]:
    """Extract NUL/delimiter-terminated `/dev/...` path strings from an ELF binary."""
    found: Set[str] = set()
    for m in _DEV_PATH_RE.finditer(blob):
        start = m.start()
        end = m.end()
        # Reject substrings embedded mid-identifier (e.g. `foo/dev/bar`)
        if start > 0 and (
            (0x30 <= blob[start - 1] <= 0x39)
            or (0x41 <= blob[start - 1] <= 0x5A)
            or (0x61 <= blob[start - 1] <= 0x7A)
            or blob[start - 1] in (0x5F, 0x2D, 0x2F)
        ):
            continue
        if end < len(blob) and blob[end] not in _VALID_DEV_TERMINATORS:
            continue
        dev_str = m.group(1).decode("ascii", errors="ignore")
        if len(dev_str) > 5:
            found.add(dev_str)
    return tuple(sorted(found))


def classify_userland_dev_node(dev_path: str) -> Tuple[str, bool, str]:
    """Classify a `/dev/...` path against Stage-A's FX3 kernel + `.ko` + `P1..P9` runtime."""
    if dev_path in _FORMAT_OR_DIR_TEMPLATES:
        return (
            "format_template_or_dir_prefix",
            True,
            "printf/mount prefix template in generic media utility table",
        )
    if dev_path in _KERNEL_DEVTMPFS_EXACT:
        return (
            "kernel_devtmpfs_core",
            True,
            "populated by stock FX3 Linux 4.9.337-scel+ devtmpfs / core char drivers",
        )
    if dev_path == "/dev/nflasha20":
        return (
            "p1_p2_adapted_partition_node",
            True,
            "adapted by P1 ('2'->'3' -> /dev/nflasha30 in all 4 libs + /dev/nflasha20 -> /dev/cnflasha30 symlink)",
        )
    if dev_path == "/dev/nflasha21":
        return (
            "p1_p2_adapted_partition_node",
            True,
            "adapted by P2 RAM-backed VFAT opelog.vfat bound at /log/opelog (no physical p21 required)",
        )
    if dev_path in ("/dev/dma330", "/dev/nflasha") or re.fullmatch(
        r"/dev/[pcdn]?nflasha(?:[1-9]|[12][0-9]|3[01])", dev_path
    ):
        return (
            "initrd_drv1_and_setup_nflash",
            True,
            "created by insmod_drv1 (devno/dma330/crypt-emmc/emmc.ko) + sbin/initrc/setup_nflash",
        )
    if (
        dev_path in _DRV2_EXACT_NODES
        or re.fullmatch(r"/dev/mmc[a-e](?:-char|1|[a-d])?", dev_path)
        or re.fullmatch(r"/dev/ms(?:-char|[12]|a|b|bb|sdadp[01])?", dev_path)
    ):
        return (
            "drv2_shared_cxd90057_kmod",
            True,
            "registered by shared FX3 insmod_drv2 / usb_insmod.sh CXD90057 kernel modules",
        )
    return (
        "unaccounted_unknown_node",
        False,
        "UNACCOUNTED /dev node not provided by FX3 kernel, insmod_drv1/drv2, or P1..P9+Fan",
    )


def audit_userland_dev_nodes(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx6_p15_dir: Path = DEFAULT_FX6_P15_FILES_DIR,
) -> UserlandDevNodeAuditReport:
    """Extract and cross-check all `/dev/*` paths across FX6 `im.elf`, `appFw.so`, `libInfra*.so`, GRM/UX, and patched `P1..P9+Fan`."""
    errors: List[str] = []
    bin_dir = fx6_p15_dir / "bin"

    core_targets: List[Path] = [
        bin_dir / "im.elf",
        bin_dir / "bootin.elf",
        fx6_lib_dir / "appFw.so",
        fx6_lib_dir / "libuxengine.so",
        fx6_lib_dir / "libgemini-grm.so",
        fx6_lib_dir / "libgrm.so",
        fx6_lib_dir / "libfan.so",
        fx6_lib_dir / "libEMG.so",
    ]
    for req_p in core_targets:
        if not req_p.is_file():
            errors.append(f"Missing required FX6 userland binary for /dev audit: {req_p}")

    infra_targets = sorted(fx6_lib_dir.glob("libInfra*.so")) if fx6_lib_dir.is_dir() else []
    if len(infra_targets) < 50:
        errors.append(f"Expected >=50 libInfra*.so libraries in {fx6_lib_dir}, found {len(infra_targets)}")

    seen_files: Set[Path] = set()
    ordered_targets: List[Path] = []
    for p in core_targets + infra_targets:
        if p.is_file() and p not in seen_files:
            seen_files.add(p)
            ordered_targets.append(p)

    dev_to_referrers: Dict[str, Set[str]] = {}
    per_lib_devs: Dict[str, Tuple[str, ...]] = {}
    for target in ordered_targets:
        refs = extract_dev_node_references_from_blob(target.read_bytes())
        per_lib_devs[target.name] = refs
        for dp in refs:
            dev_to_referrers.setdefault(dp, set()).add(target.name)

    # Verify that after applying P1 patches in memory, all 4 P1 target libraries drop `/dev/nflasha20` -> `/dev/nflasha30`
    p1_spec_map = {
        s.library_name: s
        for s in ALL_PHASE2_TARGET_SPECS
        if s.library_name in ("appFw.so", "libInfraSetupFile.so", "libInfraMediaCommon.so", "libInfraMediaConfig.so")
    }
    p1_zero_nflasha20 = len(p1_spec_map) == 4
    for lib_name, spec in sorted(p1_spec_map.items()):
        lp = fx6_lib_dir / lib_name
        if not lp.is_file():
            p1_zero_nflasha20 = False
            continue
        patched_bytes, _receipt = apply_patch_spec(lp.read_bytes(), spec)
        patched_devs = extract_dev_node_references_from_blob(patched_bytes)
        if "/dev/nflasha20" in patched_devs or "/dev/nflasha30" not in patched_devs:
            p1_zero_nflasha20 = False
            errors.append(f"Patched {lib_name} failed /dev/nflasha20 -> /dev/nflasha30 replacement check")

    # Verify CP-RTOS UIPC / neutralized libraries open zero FX6-exclusive `/dev/*` nodes
    uipc_clean_libs: List[str] = []
    for lib_nm in ("libfan.so", "libgemini-grm.so", "libuxengine.so", "libInfraLensCommunicator.so", "libInfraAppRemoteBoard.so"):
        l_devs = per_lib_devs.get(lib_nm, ())
        if all(d in _KERNEL_DEVTMPFS_EXACT for d in l_devs):
            uipc_clean_libs.append(lib_nm)
        else:
            errors.append(f"Expected {lib_nm} to reference zero non-core /dev nodes, got {l_devs}")

    resolutions: List[DevNodeResolution] = []
    unaccounted: List[str] = []
    counts: Dict[str, int] = {
        "kernel_devtmpfs_core": 0,
        "initrd_drv1_and_setup_nflash": 0,
        "drv2_shared_cxd90057_kmod": 0,
        "p1_p2_adapted_partition_node": 0,
        "format_template_or_dir_prefix": 0,
    }

    for dev_path in sorted(dev_to_referrers):
        p_cls, ok, detail = classify_userland_dev_node(dev_path)
        if ok:
            counts[p_cls] = counts.get(p_cls, 0) + 1
        else:
            unaccounted.append(dev_path)
            errors.append(f"Unaccounted userland /dev path {dev_path!r} in {sorted(dev_to_referrers[dev_path])}")
        resolutions.append(
            DevNodeResolution(
                dev_path=dev_path,
                provider_class=p_cls,
                satisfied_in_stage_a=ok,
                referenced_by=tuple(sorted(dev_to_referrers[dev_path])),
                resolution_detail=detail,
            )
        )

    all_ok = (
        len(errors) == 0
        and len(unaccounted) == 0
        and p1_zero_nflasha20
        and len(ordered_targets) >= 60
        and len(resolutions) > 0
    )

    return UserlandDevNodeAuditReport(
        all_checks_passed=all_ok,
        scanned_binary_count=len(ordered_targets),
        unique_dev_path_count=len(resolutions),
        kernel_devtmpfs_count=counts["kernel_devtmpfs_core"],
        initrd_nflash_count=counts["initrd_drv1_and_setup_nflash"],
        drv2_shared_kmod_count=counts["drv2_shared_cxd90057_kmod"],
        p1_p2_adapted_partition_count=counts["p1_p2_adapted_partition_node"],
        template_or_prefix_count=counts["format_template_or_dir_prefix"],
        unaccounted_dev_nodes=tuple(unaccounted),
        p1_patched_zero_nflasha20_verified=p1_zero_nflasha20,
        uipc_zero_fx6_exclusive_dev_libs=tuple(uipc_clean_libs),
        resolutions=tuple(resolutions),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Surface C: ELF64 AArch64 `DT_NEEDED` + `DYNSYM` + `VERNEED` Linkage Closure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerneedEntry:
    file_name: str
    version_name: str
    flags: int
    other_idx: int


@dataclass(frozen=True)
class ElfLinkageInfo:
    file_name: str
    file_size: int
    soname: Optional[str]
    dt_needed: Tuple[str, ...]
    bind_now: bool
    parsed_via_pt_dynamic: bool
    exported_symbols: FrozenSetLike
    required_undef_symbols: Tuple[str, ...]  # Non-weak SHN_UNDEF referenced by eager .rela.dyn (or all if bind_now)
    lazy_plt_undef_symbols: Tuple[str, ...]  # Non-weak SHN_UNDEF referenced only by lazy .rela.plt when !bind_now
    weak_undef_symbols: Tuple[str, ...]
    verneeds: Tuple[VerneedEntry, ...]
    verdefs: Tuple[str, ...]


# Python 3.9-compatible alias for `Tuple[str, ...]`
FrozenSetLike = Tuple[str, ...]


@dataclass(frozen=True)
class BinaryLinkageAudit:
    binary_name: str
    soname: Optional[str]
    patched_in_stage_a: bool
    bind_now: bool
    dt_needed_count: int
    missing_dt_needed: Tuple[str, ...]
    export_count: int
    required_undef_count: int
    unresolved_required_symbols: Tuple[str, ...]
    lazy_plt_undef_count: int
    unresolved_lazy_plt_symbols: Tuple[str, ...]
    verneed_count: int
    unsatisfied_verneeds: Tuple[str, ...]


@dataclass(frozen=True)
class ElfSymbolAndVerneedClosureReport:
    all_checks_passed: bool
    audited_root_binary_count: int
    transitive_closure_count: int
    missing_dt_needed_count: int
    missing_dt_needed: Tuple[str, ...]
    unresolved_required_symbols: int
    patched_aux_unresolved_plt_symbols: int
    appfw_stock_omitted_lazy_plt_count: int
    appfw_stock_omitted_lazy_plt_exact_match: bool
    patch_symbol_table_delta_count: int
    total_verneed_checks: int
    unsatisfied_verneed_count: int
    unsatisfied_verneeds: Tuple[str, ...]
    glibc_cxxabi_glibcxx_gcc_verified: bool
    fx3_base_runtime_abi_parity_verified: bool
    binaries: Tuple[BinaryLinkageAudit, ...]
    errors: Tuple[str, ...]


def _read_c_str(buf: bytes, off: int) -> str:
    if off < 0 or off >= len(buf):
        return ""
    end = buf.find(b"\x00", off)
    if end < 0:
        end = len(buf)
    return buf[off:end].decode("ascii", errors="replace")


def _vma_to_off(pt_loads: Sequence[Tuple[int, int, int]], vma: int) -> Optional[int]:
    for vaddr, f_off, filesz in pt_loads:
        if vaddr <= vma < vaddr + filesz:
            return f_off + (vma - vaddr)
    return None


def parse_elf64_linkage_info(blob: bytes, file_name: str = "<memory>") -> ElfLinkageInfo:
    """Parse ELF64 AArch64 `PT_DYNAMIC`, `.dynsym`, `.rela.dyn`/`.rela.plt`, `.gnu.version_r`, and `.gnu.version_d`."""
    if len(blob) < 64 or blob[:4] != ELF_MAGIC or blob[4] != ELFCLASS64 or blob[5] != ELFDATA2LSB:
        raise ValueError(f"{file_name}: invalid ELF64 little-endian header")

    e_type, e_machine = struct.unpack_from("<HH", blob, 0x10)
    if e_machine != EM_AARCH64 or e_type not in (ET_EXEC, ET_DYN):
        raise ValueError(f"{file_name}: expected ET_EXEC/ET_DYN EM_AARCH64, got type={e_type} machine=0x{e_machine:x}")

    e_phoff = struct.unpack_from("<Q", blob, 0x20)[0]
    e_shoff = struct.unpack_from("<Q", blob, 0x28)[0]
    e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHHHH", blob, 0x36)

    pt_loads: List[Tuple[int, int, int]] = []
    pt_dyn_range: Optional[Tuple[int, int]] = None
    for i in range(e_phnum):
        poff = e_phoff + i * e_phentsize
        p_type, _p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, _p_memsz, _p_align = struct.unpack_from(
            "<IIQQQQQQ", blob, poff
        )
        if p_type == PT_LOAD:
            pt_loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == PT_DYNAMIC:
            pt_dyn_range = (p_offset, p_filesz)

    sections: Dict[str, Tuple[int, int, int, int, int]] = {}
    if e_shoff > 0 and e_shnum > 0 and e_shstrndx < e_shnum:
        shstr_hdr = e_shoff + e_shstrndx * e_shentsize
        _, _, _, _, shstr_off, shstr_sz, _, _, _, _ = struct.unpack_from("<IIQQQQIIQQ", blob, shstr_hdr)
        shstr = blob[shstr_off : shstr_off + shstr_sz]
        for i in range(e_shnum):
            soff = e_shoff + i * e_shentsize
            (
                sh_name,
                sh_type,
                _sh_flags,
                _sh_addr,
                sh_offset,
                sh_size,
                _sh_link,
                sh_info,
                _sh_align,
                sh_entsize,
            ) = struct.unpack_from("<IIQQQQIIQQ", blob, soff)
            sections[_read_c_str(shstr, sh_name)] = (sh_type, sh_offset, sh_size, sh_info, sh_entsize)

    # Parse `PT_DYNAMIC` first (falling back to `.dynamic` only if `PT_DYNAMIC` is absent)
    dyn_tags: List[Tuple[int, int]] = []
    parsed_via_pt_dyn = False
    dyn_off_sz: Optional[Tuple[int, int]] = pt_dyn_range
    if dyn_off_sz is not None:
        parsed_via_pt_dyn = True
    elif ".dynamic" in sections:
        _, doff, dsz, _, _ = sections[".dynamic"]
        dyn_off_sz = (doff, dsz)

    if dyn_off_sz is not None:
        doff, dsz = dyn_off_sz
        for pos in range(doff, doff + dsz, 16):
            if pos + 16 > len(blob):
                break
            d_tag, d_val = struct.unpack_from("<qQ", blob, pos)
            if d_tag == DT_NULL:
                break
            dyn_tags.append((d_tag, d_val))

    tag_scalar: Dict[int, int] = {}
    for d_tag, d_val in dyn_tags:
        if d_tag != DT_NEEDED:
            tag_scalar[d_tag] = d_val

    # Resolve `.dynstr` via `DT_STRTAB`/`DT_STRSZ` or section header
    dynstr = b""
    if DT_STRTAB in tag_scalar and DT_STRSZ in tag_scalar:
        str_off = _vma_to_off(pt_loads, tag_scalar[DT_STRTAB])
        str_sz = tag_scalar[DT_STRSZ]
        if str_off is not None and str_off + str_sz <= len(blob):
            dynstr = blob[str_off : str_off + str_sz]
    if not dynstr and ".dynstr" in sections:
        _, soff, ssz, _, _ = sections[".dynstr"]
        dynstr = blob[soff : soff + ssz]

    needed: List[str] = []
    soname: Optional[str] = None
    bind_now = False
    for d_tag, d_val in dyn_tags:
        if d_tag == DT_NEEDED:
            needed.append(_read_c_str(dynstr, d_val))
        elif d_tag == DT_SONAME:
            soname = _read_c_str(dynstr, d_val)
        elif d_tag == DT_BIND_NOW:
            bind_now = True
        elif d_tag == DT_FLAGS and (d_val & DF_BIND_NOW):
            bind_now = True
        elif d_tag == DT_FLAGS_1 and (d_val & DF_1_NOW):
            bind_now = True

    # Parse `.dynsym`
    syms: List[Tuple[str, int, int]] = []  # (name, bind, shndx)
    exports_set: Set[str] = set()
    all_strong_undef: List[str] = []
    weak_undef: List[str] = []

    dynsym_range: Optional[Tuple[int, int, int]] = None
    if ".dynsym" in sections:
        _, soff, ssz, _, sentsz = sections[".dynsym"]
        dynsym_range = (soff, ssz, sentsz or 24)
    elif DT_SYMTAB in tag_scalar:
        sym_off = _vma_to_off(pt_loads, tag_scalar[DT_SYMTAB])
        sym_ent = tag_scalar.get(DT_SYMENT, 24) or 24
        # If section headers are stripped, bound by `DT_STRTAB` when adjacent
        if sym_off is not None and DT_STRTAB in tag_scalar:
            str_off = _vma_to_off(pt_loads, tag_scalar[DT_STRTAB])
            if str_off is not None and str_off > sym_off:
                dynsym_range = (sym_off, str_off - sym_off, sym_ent)

    if dynsym_range is not None:
        soff, ssz, step = dynsym_range
        for pos in range(soff, soff + ssz, step):
            if pos + 24 > len(blob):
                break
            st_name, st_info, _st_other, st_shndx, _st_val, _st_sz = struct.unpack_from("<IBBHQQ", blob, pos)
            nm = _read_c_str(dynstr, st_name) if st_name else ""
            bind = st_info >> 4
            syms.append((nm, bind, st_shndx))
            if not nm:
                continue
            if st_shndx == SHN_UNDEF:
                if bind == STB_WEAK:
                    weak_undef.append(nm)
                elif bind == STB_GLOBAL:
                    all_strong_undef.append(nm)
            else:
                if bind in (STB_GLOBAL, STB_WEAK):
                    exports_set.add(nm)

    # Distinguish eager `.rela.dyn` (`DT_RELA`) vs lazy `.rela.plt` (`DT_JMPREL`) `SHN_UNDEF` symbols
    eager_undef_set: Set[str] = set()
    lazy_plt_set: Set[str] = set()

    rela_dyn_range: Optional[Tuple[int, int, int]] = None
    if DT_RELA in tag_scalar and DT_RELASZ in tag_scalar:
        roff = _vma_to_off(pt_loads, tag_scalar[DT_RELA])
        rsz = tag_scalar[DT_RELASZ]
        rent = tag_scalar.get(DT_RELAENT, 24) or 24
        if roff is not None and roff + rsz <= len(blob):
            rela_dyn_range = (roff, rsz, rent)
    elif ".rela.dyn" in sections:
        _, roff, rsz, _, rent = sections[".rela.dyn"]
        rela_dyn_range = (roff, rsz, rent or 24)

    if rela_dyn_range is not None:
        roff, rsz, step = rela_dyn_range
        for pos in range(roff, roff + rsz, step):
            if pos + 24 > len(blob):
                break
            _r_off, r_info, _r_add = struct.unpack_from("<QQq", blob, pos)
            s_idx = r_info >> 32
            if 0 <= s_idx < len(syms):
                nm, bind, shndx = syms[s_idx]
                if nm and shndx == SHN_UNDEF and bind == STB_GLOBAL:
                    eager_undef_set.add(nm)

    rela_plt_range: Optional[Tuple[int, int, int]] = None
    if DT_JMPREL in tag_scalar and DT_PLTRELSZ in tag_scalar:
        poff = _vma_to_off(pt_loads, tag_scalar[DT_JMPREL])
        psz = tag_scalar[DT_PLTRELSZ]
        if poff is not None and poff + psz <= len(blob):
            rela_plt_range = (poff, psz, 24)
    elif ".rela.plt" in sections:
        _, poff, psz, _, pent = sections[".rela.plt"]
        rela_plt_range = (poff, psz, pent or 24)

    if rela_plt_range is not None:
        poff, psz, step = rela_plt_range
        for pos in range(poff, poff + psz, step):
            if pos + 24 > len(blob):
                break
            _r_off, r_info, _r_add = struct.unpack_from("<QQq", blob, pos)
            s_idx = r_info >> 32
            if 0 <= s_idx < len(syms):
                nm, bind, shndx = syms[s_idx]
                if nm and shndx == SHN_UNDEF and bind == STB_GLOBAL:
                    if bind_now:
                        eager_undef_set.add(nm)
                    else:
                        lazy_plt_set.add(nm)

    # If a synthetic minimal ELF has `.dynsym` `SHN_UNDEF` entries without `.rela.*` tables, treat all strong `SHN_UNDEF` as required
    if rela_dyn_range is None and rela_plt_range is None:
        required_undef = sorted(set(all_strong_undef))
        lazy_only_undef: List[str] = []
    elif bind_now:
        required_undef = sorted(set(all_strong_undef) | eager_undef_set)
        lazy_only_undef = []
    else:
        required_undef = sorted(eager_undef_set)
        lazy_only_undef = sorted(lazy_plt_set - eager_undef_set)

    # Parse `DT_VERNEED` / `.gnu.version_r` (`Elf64_Verneed` + `Elf64_Vernaux`)
    verneeds: List[VerneedEntry] = []
    vn_off: Optional[int] = None
    vn_num = 0
    if DT_VERNEED in tag_scalar and DT_VERNEEDNUM in tag_scalar:
        vn_off = _vma_to_off(pt_loads, tag_scalar[DT_VERNEED])
        vn_num = tag_scalar[DT_VERNEEDNUM]
    elif ".gnu.version_r" in sections:
        _, vn_off, _, vn_num, _ = sections[".gnu.version_r"]

    if vn_off is not None and vn_num > 0:
        pos = vn_off
        for _ in range(vn_num):
            if pos + 16 > len(blob):
                break
            _vn_ver, vn_cnt, vn_file, vn_aux, vn_next = struct.unpack_from("<HHIII", blob, pos)
            req_file = _read_c_str(dynstr, vn_file)
            apos = pos + vn_aux
            for _ in range(vn_cnt):
                if apos + 16 > len(blob):
                    break
                _vna_hash, vna_flags, vna_other, vna_name, vna_next = struct.unpack_from("<IHHII", blob, apos)
                verneeds.append(
                    VerneedEntry(
                        file_name=req_file,
                        version_name=_read_c_str(dynstr, vna_name),
                        flags=vna_flags,
                        other_idx=vna_other,
                    )
                )
                if vna_next == 0:
                    break
                apos += vna_next
            if vn_next == 0:
                break
            pos += vn_next

    # Parse `DT_VERDEF` / `.gnu.version_d` (`Elf64_Verdef` + `Elf64_Verdaux`)
    verdefs_set: Set[str] = set()
    vd_off: Optional[int] = None
    vd_num = 0
    if DT_VERDEF in tag_scalar and DT_VERDEFNUM in tag_scalar:
        vd_off = _vma_to_off(pt_loads, tag_scalar[DT_VERDEF])
        vd_num = tag_scalar[DT_VERDEFNUM]
    elif ".gnu.version_d" in sections:
        _, vd_off, _, vd_num, _ = sections[".gnu.version_d"]

    if vd_off is not None and vd_num > 0:
        pos = vd_off
        for _ in range(vd_num):
            if pos + 20 > len(blob):
                break
            _vd_ver, vd_flags, _vd_ndx, vd_cnt, _vd_hash, vd_aux, vd_next = struct.unpack_from(
                "<HHHHIII", blob, pos
            )
            apos = pos + vd_aux
            for j in range(vd_cnt):
                if apos + 8 > len(blob):
                    break
                vda_name, vda_next = struct.unpack_from("<II", blob, apos)
                if j == 0 and not (vd_flags & VER_FLG_BASE):
                    verdefs_set.add(_read_c_str(dynstr, vda_name))
                if vda_next == 0:
                    break
                apos += vda_next
            if vd_next == 0:
                break
            pos += vd_next

    return ElfLinkageInfo(
        file_name=file_name,
        file_size=len(blob),
        soname=soname,
        dt_needed=tuple(needed),
        bind_now=bind_now,
        parsed_via_pt_dynamic=parsed_via_pt_dyn,
        exported_symbols=tuple(sorted(exports_set)),
        required_undef_symbols=tuple(required_undef),
        lazy_plt_undef_symbols=tuple(lazy_only_undef),
        weak_undef_symbols=tuple(sorted(set(weak_undef))),
        verneeds=tuple(verneeds),
        verdefs=tuple(sorted(verdefs_set)),
    )


def evaluate_elf64_linkage_closure(
    root_infos: Sequence[Tuple[ElfLinkageInfo, bool]],  # (info, patched_in_stage_a)
    provider_index: Mapping[str, ElfLinkageInfo],
    universe_exports: Set[str],
    *,
    allowed_appfw_lazy_omitted: Sequence[str] = PINNED_APPFW_STOCK_OMITTED_LAZY_PLT_SYMBOLS,
    patch_symbol_table_delta_count: int = 0,
    fx3_base_runtime_abi_parity_verified: bool = True,
) -> ElfSymbolAndVerneedClosureReport:
    """Evaluate `DT_NEEDED`, non-weak `SHN_UNDEF` symbol resolution, and `VERNEED` -> `VERDEF` closure."""
    errors: List[str] = []

    # 1. Walk transitive `DT_NEEDED` closure from all root binaries
    visited: Dict[str, ElfLinkageInfo] = {}
    queue: List[ElfLinkageInfo] = [ri for ri, _ in root_infos]
    missing_needed_set: Set[str] = set()

    while queue:
        cur = queue.pop(0)
        key = cur.soname or cur.file_name
        if key in visited:
            continue
        visited[key] = cur
        for dep in cur.dt_needed:
            prov = provider_index.get(dep)
            if prov is None:
                missing_needed_set.add(f"{cur.file_name}->{dep}")
            else:
                pkey = prov.soname or prov.file_name
                if pkey not in visited:
                    queue.append(prov)

    if missing_needed_set:
        errors.append(f"Unresolved DT_NEEDED dependencies: {sorted(missing_needed_set)}")

    # 2. Verify `VERNEED` across all nodes in the transitive closure
    unsatisfied_verneeds_all: Set[str] = set()
    total_verneed_checks = 0
    seen_families: Set[str] = set()

    for node in visited.values():
        for vn in node.verneeds:
            total_verneed_checks += 1
            for prefix in ("GLIBC_", "CXXABI_", "GLIBCXX_", "GCC_"):
                if vn.version_name.startswith(prefix):
                    seen_families.add(prefix)
            if vn.flags & VER_FLG_WEAK:
                continue
            prov = provider_index.get(vn.file_name)
            if prov is None or vn.version_name not in set(prov.verdefs):
                unsatisfied_verneeds_all.add(f"{node.file_name}:{vn.file_name}@{vn.version_name}")

    if unsatisfied_verneeds_all:
        errors.append(f"Unsatisfied ELF64 VERNEED requirements: {sorted(unsatisfied_verneeds_all)}")

    # 3. Audit per-root binary symbol & version closure
    binary_audits: List[BinaryLinkageAudit] = []
    total_unres_required = 0
    patched_aux_unres_plt = 0
    appfw_omitted_cnt = 0
    appfw_omitted_exact = True
    allowed_set = set(allowed_appfw_lazy_omitted)

    for info, is_patched in root_infos:
        miss_direct = tuple(dep for dep in info.dt_needed if dep not in provider_index)
        unres_req = tuple(s for s in info.required_undef_symbols if s not in universe_exports)
        unres_plt = tuple(s for s in info.lazy_plt_undef_symbols if s not in universe_exports)

        miss_vn: List[str] = []
        for vn in info.verneeds:
            if vn.flags & VER_FLG_WEAK:
                continue
            prov = provider_index.get(vn.file_name)
            if prov is None or vn.version_name not in set(prov.verdefs):
                miss_vn.append(f"{vn.file_name}@{vn.version_name}")

        total_unres_required += len(unres_req)
        if unres_req:
            errors.append(f"{info.file_name}: {len(unres_req)} unresolved required SHN_UNDEF symbols: {unres_req[:5]}")

        if info.file_name == "appFw.so":
            appfw_omitted_cnt = len(unres_plt)
            if info.bind_now:
                appfw_omitted_exact = False
                errors.append("appFw.so unexpectedly sets DF_BIND_NOW / DT_BIND_NOW")
            if allowed_set and set(unres_plt) != allowed_set and len(unres_plt) > 0:
                appfw_omitted_exact = False
                errors.append(f"appFw.so lazy PLT omitted set drifted (got {len(unres_plt)})")
        elif is_patched or info.file_name in ("im.elf", "bootin.elf"):
            patched_aux_unres_plt += len(unres_plt)
            if unres_plt:
                errors.append(f"{info.file_name}: {len(unres_plt)} unresolved PLT symbols: {unres_plt[:5]}")

        binary_audits.append(
            BinaryLinkageAudit(
                binary_name=info.file_name,
                soname=info.soname,
                patched_in_stage_a=is_patched,
                bind_now=info.bind_now,
                dt_needed_count=len(info.dt_needed),
                missing_dt_needed=miss_direct,
                export_count=len(info.exported_symbols),
                required_undef_count=len(info.required_undef_symbols),
                unresolved_required_symbols=unres_req,
                lazy_plt_undef_count=len(info.lazy_plt_undef_symbols),
                unresolved_lazy_plt_symbols=unres_plt,
                verneed_count=len(info.verneeds),
                unsatisfied_verneeds=tuple(miss_vn),
            )
        )

    families_ok = {"GLIBC_", "CXXABI_", "GLIBCXX_", "GCC_"}.issubset(seen_families)
    if not families_ok:
        errors.append(f"Missing expected runtime VERNEED families (saw {sorted(seen_families)})")
    if patch_symbol_table_delta_count != 0:
        errors.append(f"Phase 2 patching unexpectedly mutated {patch_symbol_table_delta_count} dynamic symbols")
    if not fx3_base_runtime_abi_parity_verified:
        errors.append("FX3 vs FX6 base C/C++ runtime ABI parity check failed")

    all_ok = (
        len(errors) == 0
        and len(missing_needed_set) == 0
        and total_unres_required == 0
        and patched_aux_unres_plt == 0
        and appfw_omitted_exact
        and len(unsatisfied_verneeds_all) == 0
        and families_ok
        and patch_symbol_table_delta_count == 0
        and fx3_base_runtime_abi_parity_verified
    )

    return ElfSymbolAndVerneedClosureReport(
        all_checks_passed=all_ok,
        audited_root_binary_count=len(root_infos),
        transitive_closure_count=len(visited),
        missing_dt_needed_count=len(missing_needed_set),
        missing_dt_needed=tuple(sorted(missing_needed_set)),
        unresolved_required_symbols=total_unres_required,
        patched_aux_unresolved_plt_symbols=patched_aux_unres_plt,
        appfw_stock_omitted_lazy_plt_count=appfw_omitted_cnt,
        appfw_stock_omitted_lazy_plt_exact_match=appfw_omitted_exact,
        patch_symbol_table_delta_count=patch_symbol_table_delta_count,
        total_verneed_checks=total_verneed_checks,
        unsatisfied_verneed_count=len(unsatisfied_verneeds_all),
        unsatisfied_verneeds=tuple(sorted(unsatisfied_verneeds_all)),
        glibc_cxxabi_glibcxx_gcc_verified=families_ok,
        fx3_base_runtime_abi_parity_verified=fx3_base_runtime_abi_parity_verified,
        binaries=tuple(binary_audits),
        errors=tuple(errors),
    )


def audit_elf64_symbol_and_verneed_closure(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx6_initrd_dir: Path = DEFAULT_FX6_P3_INITRD_DIR,
    fx6_p15_dir: Path = DEFAULT_FX6_P15_FILES_DIR,
    fx3_ap_projection_dir: Optional[Path] = DEFAULT_FX3_AP_PROJECTION_DIR,
) -> ElfSymbolAndVerneedClosureReport:
    """Audit live FX6 + Stage-A patched `P1..P9+Fan` ELF64 `DT_NEEDED`, `DYNSYM`, and `VERNEED` closure."""
    errors: List[str] = []
    initrd_lib_dir = fx6_initrd_dir / "lib"
    bin_dir = fx6_p15_dir / "bin"

    # Pin SHA-256 digests of newly audited Phase 14 runtime/UI libraries
    pinned_checks = (
        (fx6_lib_dir / "libgemini-grm.so", PINNED_FX6_LIBGEMINI_GRM_BYTES, PINNED_FX6_LIBGEMINI_GRM_SHA256),
        (fx6_lib_dir / "libuxengine.so", PINNED_FX6_LIBUXENGINE_BYTES, PINNED_FX6_LIBUXENGINE_SHA256),
        (initrd_lib_dir / "libc-2.25.so", PINNED_FX6_INITRD_LIBC_BYTES, PINNED_FX6_INITRD_LIBC_SHA256),
        (fx6_lib_dir / "libstdc++.so.6.0.22", PINNED_FX6_LIBSTDCXX_BYTES, PINNED_FX6_LIBSTDCXX_SHA256),
        (fx6_lib_dir / "libgcc_s.so.1", PINNED_SHARED_LIBGCC_S_BYTES, PINNED_SHARED_LIBGCC_S_SHA256),
    )
    for p_file, exp_sz, exp_sha in pinned_checks:
        if not p_file.is_file():
            errors.append(f"Missing pinned runtime library: {p_file}")
            continue
        raw = p_file.read_bytes()
        if len(raw) != exp_sz or hashlib.sha256(raw).hexdigest() != exp_sha:
            errors.append(f"Pinned SHA-256/size mismatch on {p_file.name}")

    # Apply all userland Phase 2 `P1..P8+Fan` patches in memory & verify zero dynamic symbol drift
    patched_blobs: Dict[str, bytes] = {}
    patch_sym_deltas = 0
    userland_specs = {s.library_name: s for s in ALL_PHASE2_TARGET_SPECS if s.source_domain == "fx6_lib"}
    for lib_name, spec in sorted(userland_specs.items()):
        lp = fx6_lib_dir / lib_name
        if not lp.is_file():
            errors.append(f"Missing Phase 2 target library: {lp}")
            continue
        orig_raw = lp.read_bytes()
        patched_raw, _rec = apply_patch_spec(orig_raw, spec)
        orig_info = parse_elf64_linkage_info(orig_raw, file_name=lib_name)
        pat_info = parse_elf64_linkage_info(patched_raw, file_name=lib_name)
        if (
            orig_info.exported_symbols != pat_info.exported_symbols
            or orig_info.required_undef_symbols != pat_info.required_undef_symbols
            or orig_info.lazy_plt_undef_symbols != pat_info.lazy_plt_undef_symbols
            or orig_info.dt_needed != pat_info.dt_needed
            or orig_info.verneeds != pat_info.verneeds
        ):
            patch_sym_deltas += 1
        patched_blobs[lib_name] = patched_raw

    # Index all Stage-A shared library providers (`p15:/usr/lib` with patched blobs + `nflasha3-initrd:/lib`)
    provider_index: Dict[str, ElfLinkageInfo] = {}
    parsed_by_resolved: Dict[Path, ElfLinkageInfo] = {}
    universe_exports: Set[str] = set()

    for search_dir in (fx6_lib_dir, initrd_lib_dir):
        if not search_dir.is_dir():
            continue
        for entry in sorted(search_dir.iterdir()):
            if not entry.is_file():
                continue
            if entry.name in patched_blobs:
                info = parse_elf64_linkage_info(patched_blobs[entry.name], file_name=entry.name)
            else:
                resolved = entry.resolve()
                if resolved not in parsed_by_resolved:
                    with resolved.open("rb") as fh:
                        head = fh.read(6)
                    if head[:4] != ELF_MAGIC or head[4] != ELFCLASS64 or head[5] != ELFDATA2LSB:
                        continue
                    try:
                        parsed_by_resolved[resolved] = parse_elf64_linkage_info(
                            resolved.read_bytes(), file_name=entry.name
                        )
                    except ValueError:
                        continue
                base_info = parsed_by_resolved[resolved]
                info = ElfLinkageInfo(
                    file_name=entry.name,
                    file_size=base_info.file_size,
                    soname=base_info.soname,
                    dt_needed=base_info.dt_needed,
                    bind_now=base_info.bind_now,
                    parsed_via_pt_dynamic=base_info.parsed_via_pt_dynamic,
                    exported_symbols=base_info.exported_symbols,
                    required_undef_symbols=base_info.required_undef_symbols,
                    lazy_plt_undef_symbols=base_info.lazy_plt_undef_symbols,
                    weak_undef_symbols=base_info.weak_undef_symbols,
                    verneeds=base_info.verneeds,
                    verdefs=base_info.verdefs,
                )
            provider_index.setdefault(entry.name, info)
            if info.soname:
                provider_index.setdefault(info.soname, info)
            universe_exports.update(info.exported_symbols)

    # Ensure standard glibc SONAME aliases resolve even on filesystems where symlinks were flattened
    soname_fallbacks = (
        ("libc.so.6", "libc-2.25.so"),
        ("libm.so.6", "libm-2.25.so"),
        ("libpthread.so.0", "libpthread-2.25.so"),
        ("libdl.so.2", "libdl-2.25.so"),
        ("librt.so.1", "librt-2.25.so"),
        ("ld-linux-aarch64.so.1", "ld-2.25.so"),
    )
    for soname_alias, backing_file in soname_fallbacks:
        if soname_alias not in provider_index and backing_file in provider_index:
            provider_index[soname_alias] = provider_index[backing_file]

    root_infos: List[Tuple[ElfLinkageInfo, bool]] = []
    for exe_name in ("im.elf", "bootin.elf"):
        ep = bin_dir / exe_name
        if not ep.is_file():
            errors.append(f"Missing host executable: {ep}")
            continue
        e_info = parse_elf64_linkage_info(ep.read_bytes(), file_name=exe_name)
        universe_exports.update(e_info.exported_symbols)
        root_infos.append((e_info, False))

    for patched_name in PATCHED_USERLAND_LIBRARIES:
        if patched_name not in provider_index:
            errors.append(f"Missing patched library in provider index: {patched_name}")
            continue
        root_infos.append((provider_index[patched_name], True))

    for sub_name in SUBSYSTEM_COUNTERPART_LIBRARIES:
        if sub_name not in provider_index:
            errors.append(f"Missing subsystem library in provider index: {sub_name}")
            continue
        root_infos.append((provider_index[sub_name], False))

    # Cross-check FX3 `p7:/lib` & `p15:/usr/lib` base C/C++ runtime ABI parity when FX3 projection is present
    fx3_abi_parity_ok = True
    if fx3_ap_projection_dir is not None:
        manifest_json = fx3_ap_projection_dir / "projection-manifest-full-v4.json"
        if manifest_json.is_file():
            proj = json.loads(manifest_json.read_text(encoding="utf-8"))
            logical = proj.get("logical_guest_to_payload", {})
            runtime_pairs = (
                ("/lib/ld-2.25.so", "ld-linux-aarch64.so.1"),
                ("/lib/libc-2.25.so", "libc.so.6"),
                ("/lib/libm-2.25.so", "libm.so.6"),
                ("/lib/libpthread-2.25.so", "libpthread.so.0"),
                ("/lib/libdl-2.25.so", "libdl.so.2"),
                ("/lib/librt-2.25.so", "librt.so.1"),
                ("/usr/lib/libstdc++.so.6.0.22", "libstdc++.so.6"),
                ("/usr/lib/libgcc_s.so.1", "libgcc_s.so.1"),
            )
            for guest_path, soname_key in runtime_pairs:
                rec = logical.get(guest_path, {})
                pay_str = rec.get("payload_file") if isinstance(rec, dict) else None
                fx6_prov = provider_index.get(soname_key)
                if not pay_str or not Path(pay_str).is_file() or fx6_prov is None:
                    fx3_abi_parity_ok = False
                    errors.append(f"Missing FX3 runtime payload for ABI parity check: {guest_path}")
                    continue
                fx3_info = parse_elf64_linkage_info(Path(pay_str).read_bytes(), file_name=Path(pay_str).name)
                if fx3_info.exported_symbols != fx6_prov.exported_symbols or fx3_info.verdefs != fx6_prov.verdefs:
                    fx3_abi_parity_ok = False
                    errors.append(f"FX3 vs FX6 base runtime ABI/VERDEF mismatch on {guest_path}")

    closure_rep = evaluate_elf64_linkage_closure(
        root_infos=root_infos,
        provider_index=provider_index,
        universe_exports=universe_exports,
        allowed_appfw_lazy_omitted=PINNED_APPFW_STOCK_OMITTED_LAZY_PLT_SYMBOLS,
        patch_symbol_table_delta_count=patch_sym_deltas,
        fx3_base_runtime_abi_parity_verified=fx3_abi_parity_ok,
    )

    if errors:
        merged_errs = tuple(list(errors) + list(closure_rep.errors))
        return ElfSymbolAndVerneedClosureReport(
            all_checks_passed=False,
            audited_root_binary_count=closure_rep.audited_root_binary_count,
            transitive_closure_count=closure_rep.transitive_closure_count,
            missing_dt_needed_count=closure_rep.missing_dt_needed_count,
            missing_dt_needed=closure_rep.missing_dt_needed,
            unresolved_required_symbols=closure_rep.unresolved_required_symbols,
            patched_aux_unresolved_plt_symbols=closure_rep.patched_aux_unresolved_plt_symbols,
            appfw_stock_omitted_lazy_plt_count=closure_rep.appfw_stock_omitted_lazy_plt_count,
            appfw_stock_omitted_lazy_plt_exact_match=closure_rep.appfw_stock_omitted_lazy_plt_exact_match,
            patch_symbol_table_delta_count=closure_rep.patch_symbol_table_delta_count,
            total_verneed_checks=closure_rep.total_verneed_checks,
            unsatisfied_verneed_count=closure_rep.unsatisfied_verneed_count,
            unsatisfied_verneeds=closure_rep.unsatisfied_verneeds,
            glibc_cxxabi_glibcxx_gcc_verified=closure_rep.glibc_cxxabi_glibcxx_gcc_verified,
            fx3_base_runtime_abi_parity_verified=closure_rep.fx3_base_runtime_abi_parity_verified,
            binaries=closure_rep.binaries,
            errors=merged_errs,
        )

    return closure_rep


# ---------------------------------------------------------------------------
# Synthetic Clean-Room ELF64 Builder (for Donorless Unit & Fault-Injection Tests)
# ---------------------------------------------------------------------------


def build_synthetic_elf64_linkage_blob(
    *,
    soname: Optional[str] = None,
    dt_needed: Sequence[str] = (),
    exports: Sequence[str] = (),
    eager_undefs: Sequence[str] = (),
    lazy_plt_undefs: Sequence[str] = (),
    weak_undefs: Sequence[str] = (),
    verneeds: Sequence[Tuple[str, Sequence[str]]] = (),  # (lib_soname, [ver_str, ...])
    verdefs: Sequence[str] = (),
    bind_now: bool = False,
) -> bytes:
    """Synthesize a compact, spec-compliant ELF64 AArch64 `ET_DYN` binary with `PT_LOAD` + `PT_DYNAMIC` + `.gnu.version_{r,d}`."""
    strtab = bytearray(b"\x00")

    def _intern(s: str) -> int:
        enc = s.encode("ascii") + b"\x00"
        idx = strtab.find(enc)
        if idx >= 0:
            return idx
        off = len(strtab)
        strtab.extend(enc)
        return off

    soname_off = _intern(soname) if soname else None
    needed_offs = [_intern(dep) for dep in dt_needed]

    # Build `.dynsym` (null entry #0 + exports + eager_undefs + lazy_plt_undefs + weak_undefs)
    dynsym = bytearray(24)  # STN_UNDEF #0
    sym_idx_by_name: Dict[str, int] = {}

    def _add_sym(nm: str, bind: int, shndx: int, val: int = 0) -> int:
        idx = len(dynsym) // 24
        st_info = (bind << 4) | 2  # STT_FUNC
        dynsym.extend(struct.pack("<IBBHQQ", _intern(nm), st_info, 0, shndx, val, 16))
        sym_idx_by_name[nm] = idx
        return idx

    for i, exp in enumerate(exports, start=1):
        _add_sym(exp, STB_GLOBAL, 1, 0x1000 + i * 16)
    for u in eager_undefs:
        if u not in sym_idx_by_name:
            _add_sym(u, STB_GLOBAL, SHN_UNDEF, 0)
    for u in lazy_plt_undefs:
        if u not in sym_idx_by_name:
            _add_sym(u, STB_GLOBAL, SHN_UNDEF, 0)
    for w in weak_undefs:
        if w not in sym_idx_by_name:
            _add_sym(w, STB_WEAK, SHN_UNDEF, 0)

    rela_dyn = bytearray()
    for i, u in enumerate(eager_undefs):
        r_info = (sym_idx_by_name[u] << 32) | R_AARCH64_GLOB_DAT
        rela_dyn.extend(struct.pack("<QQq", 0x4000 + i * 8, r_info, 0))

    rela_plt = bytearray()
    for i, u in enumerate(lazy_plt_undefs):
        r_info = (sym_idx_by_name[u] << 32) | R_AARCH64_JUMP_SLOT
        rela_plt.extend(struct.pack("<QQq", 0x5000 + i * 8, r_info, 0))

    verneed_buf = bytearray()
    verneed_num = len(verneeds)
    ver_idx = 2
    for g_idx, (req_lib, vers) in enumerate(verneeds):
        vn_cnt = len(vers)
        is_last_vn = g_idx == verneed_num - 1
        vn_next = 0 if is_last_vn else (16 + vn_cnt * 16)
        verneed_buf.extend(struct.pack("<HHIII", 1, vn_cnt, _intern(req_lib), 16, vn_next))
        for v_i, v_str in enumerate(vers):
            vna_next = 0 if v_i == vn_cnt - 1 else 16
            verneed_buf.extend(struct.pack("<IHHII", 0, 0, ver_idx, _intern(v_str), vna_next))
            ver_idx += 1

    verdef_buf = bytearray()
    verdef_num = len(verdefs)
    for d_i, vd_str in enumerate(verdefs):
        vd_next = 0 if d_i == verdef_num - 1 else 28
        verdef_buf.extend(struct.pack("<HHHHIII", 1, 0, d_i + 2, 1, 0, 20, vd_next))
        verdef_buf.extend(struct.pack("<II", _intern(vd_str), 0))

    while len(strtab) % 8 != 0:
        strtab.append(0)

    # Layout inside single `PT_LOAD` mapped at VMA `0x0` (file offset == VMA):
    # [0x000..0x040) ELF64 header (64 B)
    # [0x040..0x0B0) 2x Program headers: PT_LOAD + PT_DYNAMIC (112 B)
    cursor = 64 + 2 * 56
    strtab_off = cursor
    cursor += len(strtab)
    dynsym_off = cursor
    cursor += len(dynsym)
    rela_dyn_off = cursor
    cursor += len(rela_dyn)
    rela_plt_off = cursor
    cursor += len(rela_plt)
    verneed_off = cursor
    cursor += len(verneed_buf)
    verdef_off = cursor
    cursor += len(verdef_buf)
    dynamic_off = cursor

    dyn_entries: List[Tuple[int, int]] = []
    for noff in needed_offs:
        dyn_entries.append((DT_NEEDED, noff))
    if soname_off is not None:
        dyn_entries.append((DT_SONAME, soname_off))
    if bind_now:
        dyn_entries.append((DT_FLAGS, DF_BIND_NOW))
        dyn_entries.append((DT_BIND_NOW, 1))
    dyn_entries.extend(
        [
            (DT_STRTAB, strtab_off),
            (DT_STRSZ, len(strtab)),
            (DT_SYMTAB, dynsym_off),
            (DT_SYMENT, 24),
        ]
    )
    if rela_dyn:
        dyn_entries.extend([(DT_RELA, rela_dyn_off), (DT_RELASZ, len(rela_dyn)), (DT_RELAENT, 24)])
    if rela_plt:
        dyn_entries.extend([(DT_JMPREL, rela_plt_off), (DT_PLTRELSZ, len(rela_plt)), (DT_PLTREL, DT_RELA)])
    if verneed_num > 0:
        dyn_entries.extend([(DT_VERNEED, verneed_off), (DT_VERNEEDNUM, verneed_num)])
    if verdef_num > 0:
        dyn_entries.extend([(DT_VERDEF, verdef_off), (DT_VERDEFNUM, verdef_num)])
    dyn_entries.append((DT_NULL, 0))

    dynamic_buf = b"".join(struct.pack("<qQ", t, v) for t, v in dyn_entries)
    cursor += len(dynamic_buf)

    # Optional minimal section header table (`.shstrtab` + `.dynstr` + `.dynsym` + `.dynamic`) so both `PT_DYNAMIC` and section parsers agree
    shstr = b"\x00.shstrtab\x00.dynstr\x00.dynsym\x00.dynamic\x00"
    shstr_off = cursor
    cursor += len(shstr)
    while cursor % 8 != 0:
        cursor += 1
    shoff = cursor

    def _shdr(nm_off: int, sh_type: int, off: int, sz: int, link: int = 0, info: int = 0, entsz: int = 0) -> bytes:
        return struct.pack("<IIQQQQIIQQ", nm_off, sh_type, 2, off, off, sz, link, info, 8, entsz)

    shdrs = b"".join(
        [
            _shdr(0, 0, 0, 0),
            _shdr(1, 3, shstr_off, len(shstr)),
            _shdr(11, 3, strtab_off, len(strtab)),
            _shdr(19, 11, dynsym_off, len(dynsym), link=2, info=1, entsz=24),
            _shdr(27, 6, dynamic_off, len(dynamic_buf), link=2, entsz=16),
        ]
    )

    total_load_sz = shstr_off
    ehdr = struct.pack(
        "<4sBBBB8xHHIQQQIHHHHHH",
        ELF_MAGIC,
        ELFCLASS64,
        ELFDATA2LSB,
        1,
        0,
        ET_DYN,
        EM_AARCH64,
        1,
        0x1000,
        64,
        shoff,
        0,
        64,
        56,
        2,
        64,
        5,
        1,
    )
    ph_load = struct.pack("<IIQQQQQQ", PT_LOAD, 5, 0, 0, 0, total_load_sz, total_load_sz, 0x1000)
    ph_dyn = struct.pack("<IIQQQQQQ", PT_DYNAMIC, 6, dynamic_off, dynamic_off, dynamic_off, len(dynamic_buf), len(dynamic_buf), 8)

    out = bytearray()
    out.extend(ehdr)
    out.extend(ph_load)
    out.extend(ph_dyn)
    out.extend(strtab)
    out.extend(dynsym)
    out.extend(rela_dyn)
    out.extend(rela_plt)
    out.extend(verneed_buf)
    out.extend(verdef_buf)
    out.extend(dynamic_buf)
    out.extend(shstr)
    while len(out) < shoff:
        out.append(0)
    out.extend(shdrs)
    return bytes(out)


# ---------------------------------------------------------------------------
# Unified Phase 14 Entry Point
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KmodAndUserlandAbiReport:
    all_checks_passed: bool
    kmod_userland_abi_ok: bool
    kmod_mutation_count: int
    fx6_kmod_loaded_count: int
    unaccounted_dev_node_count: int
    unresolved_required_symbols: int
    unsatisfied_verneed_count: int
    missing_dt_needed_count: int
    surface_a_kmod_matrix: KmodLoadOrderAndMatrixReport
    surface_b_dev_nodes: UserlandDevNodeAuditReport
    surface_c_elf_linkage: ElfSymbolAndVerneedClosureReport
    errors: Tuple[str, ...]


def run_kmod_and_userland_abi_verification(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    fx6_initrd_dir: Path = DEFAULT_FX6_P3_INITRD_DIR,
    fx6_p15_dir: Path = DEFAULT_FX6_P15_FILES_DIR,
    fx3_scripts_dir: Optional[Path] = DEFAULT_FX3_ORIGINAL_SCRIPTS_DIR,
    fx3_ap_projection_dir: Optional[Path] = DEFAULT_FX3_AP_PROJECTION_DIR,
) -> KmodAndUserlandAbiReport:
    """Execute all three Phase 14 Stage-A compatibility closure audits (`.ko` matrix, `/dev/*` nodes, ELF64 linkage)."""
    surf_a = audit_kmod_load_order_and_driver_matrix(
        fx6_initrd_dir=fx6_initrd_dir,
        fx6_p15_dir=fx6_p15_dir,
        fx3_modules_dir=fx3_modules_dir,
        fx3_scripts_dir=fx3_scripts_dir,
        fx3_ap_projection_dir=fx3_ap_projection_dir,
    )
    surf_b = audit_userland_dev_nodes(
        fx6_lib_dir=fx6_lib_dir,
        fx6_p15_dir=fx6_p15_dir,
    )
    surf_c = audit_elf64_symbol_and_verneed_closure(
        fx6_lib_dir=fx6_lib_dir,
        fx6_initrd_dir=fx6_initrd_dir,
        fx6_p15_dir=fx6_p15_dir,
        fx3_ap_projection_dir=fx3_ap_projection_dir,
    )

    combined_errors = tuple(list(surf_a.errors) + list(surf_b.errors) + list(surf_c.errors))
    all_ok = (
        surf_a.all_checks_passed
        and surf_b.all_checks_passed
        and surf_c.all_checks_passed
        and surf_a.kmod_mutation_count == 0
        and surf_a.fx6_kmod_loaded_count == 0
        and len(surf_b.unaccounted_dev_nodes) == 0
        and surf_c.missing_dt_needed_count == 0
        and surf_c.unresolved_required_symbols == 0
        and surf_c.unsatisfied_verneed_count == 0
        and len(combined_errors) == 0
    )

    return KmodAndUserlandAbiReport(
        all_checks_passed=all_ok,
        kmod_userland_abi_ok=all_ok,
        kmod_mutation_count=surf_a.kmod_mutation_count,
        fx6_kmod_loaded_count=surf_a.fx6_kmod_loaded_count,
        unaccounted_dev_node_count=len(surf_b.unaccounted_dev_nodes),
        unresolved_required_symbols=surf_c.unresolved_required_symbols,
        unsatisfied_verneed_count=surf_c.unsatisfied_verneed_count,
        missing_dt_needed_count=surf_c.missing_dt_needed_count,
        surface_a_kmod_matrix=surf_a,
        surface_b_dev_nodes=surf_b,
        surface_c_elf_linkage=surf_c,
        errors=combined_errors,
    )
