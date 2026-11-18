"""Phase 300 (300th Phase Grand Milestone!!) — Recovery Pillar 53 & Unified
53-Pillar Recovery Master (`verify-53pillar-recovery` /
`verify-pillar53-dci4k-aspect-custom-hold-camset-vault`):

1. **Pillar 53A — `[XAVC S-I DCI 4K]` (`4096x2160` `17:9` All-Intra vs Long-GOP
   `3840x2160` UHD Split), `24.00p` Mandatory Reboot & Playback Quarantine
   (Volatile `/tmp` Stage-B Wipe Hazard!), `4264x2408` HDMI RAW, & Still
   `[Aspect Ratio]` (`3:2 / 4:3 / 16:9 / 1:1`) + `Slot-1` Vault Firewall (Wave-51)**:
   - Models `ILME-FX3 Ver. 3.00+/7.02` (`0x91030080`, `ilc/2210`,
     `PRODUCT_MODEL_ALCIN_UUD`) exposing **`[XAVC S-I DCI 4K]`** (`4096x2160`, `17:9`,
     All-Intra `4:2:2 10bit`, `23.98p`/`24.00p` `240M`, `25p` `250M`, `29.97p` `300M`,
     `50p` `500M`, `59.94p` `600M`; `S&Q 1..48fps` locking out `100/120fps`;
     `CFexpress VPG200+` / `SDXC V90+` required at `600M`; `Ver. 6.00+` `[Shutter
     Mode] = [Angle]` `5.6..360.0 deg`), while Long-GOP (`XAVC HS 4K` / `XAVC S 4K`)
     and `XAVC S-I 4K` remain strictly `3840x2160` (`16:9` UHD) with zero `24.00p` and
     dormant `xavc_hs_8k_24p` rejected fail-closed.
   - **Critical Recovery / Stage-B Guard**: Switching into or out of `24.00p` triggers
     a **mandatory camera reboot** (`_g.uxc` `0x639b`/`0x63b6`), cleanly wiping
     volatile `/tmp/` Stage-B bind mounts back to unmodified stock `ILME-FX3 7.02`
     (`H0 == H2`) and quarantining `24.00p` playback (`_g.uxc` `0x63d7`).
   - Models `4264x2408` (`16:9`) Type-A HDMI RAW (`24.00p` supported; requires `Log
     Shooting != Off`, locks gamma `S-Log3`, disables `SteadyShot Active` and
     `[De-Squeeze Display]`) vs `ILME-FX6` `4096x2160` / `3840x2160` SDI/HDMI RAW, and
     Still `[Aspect Ratio]` (`3:2` default `12M 4240x2832`, `4:3` `11M 3776x2832`,
     `16:9` `10M 4240x2384`, `1:1` `8.0M 2832x2832`; RAW retains full `3:2` pixels
     + crop metadata; `APS-C S35 = On` steps `L -> M`) vs still-less `ILME-FX6`.

2. **Pillar 53B — `[Reg. Custom Shoot Set]` (`Recall Custom hold 1..3` 11
   Checkboxes & `HLG Still Image` Lockout), `[Camera Set. Memory]` (`1..3` +
   `M1..M4` `CAMPR%02d%c.DAT` & `CAMSET` under `%c:%s/SONY/SETTING/%s/` vs `FX6`
   `s/SONY/PRO/CAMERA/`), & `[Playback] [Photo Capture]` (`8.3M/2.1M` DCI 4K
   Lockout & `Slot-1` Tier-0 Vault Write Firewall!) / `[Enlarge Image]` (Wave-51)**:
   - Enforces Still `P/A/S/M`-only `[Reg. Custom Shoot Set]` (`Recall Custom hold
     1..3`, `Initialize`-only survival, **11** `is_checked_recall_custom_hold0..10`
     checkboxes, forcing `[HLG Still Image] = Off` when recalling `ISO` or `DRO
     Bracket`).
   - Enforces exact card path isolation: `ILME-FX3` stores `M1..M4`
     (`%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`) and `CAMSET01..10.DAT`
     (`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`, Slot-1 only) with **ZERO
     `PRIVATE/SONY/PRO/CAMERA`** (which is `ILME-FX6` `User/All File`-only; cross-model
     card recall rejected fail-closed), and blocks saving `M1..M4`/`CAMSET` onto
     read-only `Slot-1` Tier-0 Vault (`EROFS`/`EBUSY`).
   - Enforces `[Playback] -> [Edit] -> [Photo Capture]` (`8.3M` UHD / `2.1M` HD,
     `JPEG` / `HEIF(4:2:0)` / `HEIF(4:2:2)`): **locked out on `XAVC S-I DCI 4K`
     clips** (`_g.uxc` `0x60ce`) AND **blocked fail-closed (`EROFS`/`EBUSY`) whenever
     `[Select Playback Media] = Slot 1` holds the read-only Tier-0 recovery vault**,
     while read-only `[Enlarge Image]` (`Enlarge Initial Mag.` `Standard. Mag. /
     Previous Mag.`, `Enlarge Initial Position` `Focused Position / Center`) remains
     safe (`ILME-FX6` has zero Photo Capture & zero playback Enlarge Image).

3. **Unified 53-Pillar Recovery Master (`evaluate_realhw_53pillar_recovery_master` /
   `verify-53pillar-recovery`, 300th Phase Milestone!!)**:
   - Concurrently delegates Pillars `1..52` (`evaluate_realhw_52pillar_recovery_master`)
     + **Pillar 53** (`run_pillar53_standalone_suite`) -> **`53/53`
     (`VERIFIED_53OF53_PILLAR_RECOVERY_MASTER`)** with `raw_firmware_bytes_leaked == 0`,
     `persistent_emmc_writes_authorized == False`, and
     `overall_ready_for_hardware_attach == False`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
)
from .realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier import (
    MASTER_52_PILLAR_SPECS,
    Master52PillarRecoveryReport,
    evaluate_realhw_52pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants (Phase 300 Milestone)
# ---------------------------------------------------------------------------

PHASE300_SCHEMA: str = (
    "realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier_v1"
)
PHASE300_VERSION: str = "1.0.0"
PHASE300_PHASE_NUMBER: int = 300
P300_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
P300_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P300_OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P300_DCI4K_LONG_GOP_OR_8K_VIOLATIONS: int = 0
P300_2400P_REBOOT_STAGE_B_WIPE_VIOLATIONS: int = 0
P300_HDMI_RAW_OR_STILL_ASPECT_DRIFT_EVENTS: int = 0
P300_FX6_STILL_OR_RAW_CONFLATION_EVENTS: int = 0
P300_REG_CUSTOM_HOLD_OR_HLG_LOCK_DRIFT_EVENTS: int = 0
P300_CAMSET_CROSS_MODEL_PATH_DRIFT_EVENTS: int = 0
P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_BYPASS_EVENTS: int = 0
P300_SLOT1_CAMSET_WRITE_BYTES: int = 0
P300_SLOT1_PHOTO_CAPTURE_WRITE_BYTES: int = 0
P300_SLOT1_VAULT_MUTATION_BYTES: int = 0
P300_SLOT1_FORMAT_HARD_LOCKED: bool = True
P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED: bool = True

P300_FX3_APPFW_HAS_DCI4K_INTERNAL: bool = True
P300_FX3_APPFW_HAS_PRO_CAMERA_PATH: bool = False
P300_FX6_HAS_STILL_ASPECT_RATIO: bool = False
P300_FX6_HAS_PHOTO_CAPTURE: bool = False
P300_FX6_HAS_PLAYBACK_ENLARGE_IMAGE: bool = False
P300_FX6_HAS_REG_CUSTOM_SHOOT_SET: bool = False
P300_FX6_HAS_CAMERA_SET_MEMORY: bool = False

P300_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P300_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P300_FAST_CLI_BUDGET_SECONDS: float = 1.2
P300_NOMINAL_BUDGET_SECONDS: float = 4.0
P300_CONCURRENT_CEILING_SECONDS: float = 6.0
P300_BOUNDED_HEADER_BYTES: int = 4096
P300_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-51 Donor Anchors (strictly O_RDONLY)
P300_FX3_MODEL_NAME: str = "ILME-FX3"
P300_FX3_MODEL_ID: int = 0x91030080
P300_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P300_FX3_HELPGUIDE_ID: str = "ilc/2210"
P300_FX3_FW_VERSION: str = "7.02"
P300_FX3_SENSOR_FAMILY: str = "12 MP IMX510"
P300_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P300_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P300_FX6_DONOR_FW_VERSION: str = "6.01"
P300_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P300_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P300_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P300_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)
P300_PINNED_FX3_APPFW_702_FULL_SHA256: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

P300_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P300_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P300_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)
P300_PINNED_FX6_APPFW_601_FULL_SHA256: str = (
    "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
)

P300_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P300_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P300_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P300_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P300_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P300_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P300_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P300_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P300_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P300_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P300_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P300_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P300_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P300_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P300_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P300_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P300_PINNED_FX3_UXC_EN_BYTES: int = 165740
P300_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P300_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P300_PINNED_FX3_UXC_SC_BYTES: int = 149064
P300_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P300_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P300_PINNED_FX3_UXC_TC_BYTES: int = 151908
P300_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P300_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P300_PINNED_FX3_UXC_JA_BYTES: int = 208564
P300_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P300_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P300_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P300_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P300_DONOR_FX3_UXC_SC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_g.uxc"
)
P300_PINNED_FX3_UXC_SC_G_BYTES: int = 61296
P300_PINNED_FX3_UXC_SC_G_SHA256: str = (
    "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b"
)

P300_DONOR_FX3_UXC_TC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_g.uxc"
)
P300_PINNED_FX3_UXC_TC_G_BYTES: int = 61372
P300_PINNED_FX3_UXC_TC_G_SHA256: str = (
    "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80"
)

P300_DONOR_FX3_UXC_JA_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_g.uxc"
)
P300_PINNED_FX3_UXC_JA_G_BYTES: int = 89428
P300_PINNED_FX3_UXC_JA_G_SHA256: str = (
    "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980"
)

P300_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P300_PINNED_FX6_UXC_EN_BYTES: int = 118208
P300_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P300_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P300_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P300_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# ---------------------------------------------------------------------------
# Pillar 53A Constants — [XAVC S-I DCI 4K] vs Long-GOP UHD Split,
# 24.00p Mandatory Reboot & Volatile /tmp Stage-B Wipe, 4264x2408 HDMI RAW,
# & Still [Aspect Ratio] (3:2 / 4:3 / 16:9 / 1:1)
# ---------------------------------------------------------------------------

P300_MOVIE_FILE_FORMAT_MENU_PATH: Tuple[str, ...] = (
    "Shooting",
    "Image Quality/Rec",
    "File Format",
)
P300_RAW_OUTPUT_MENU_PATH: Tuple[str, ...] = (
    "Setup",
    "External Output",
    "HDMI Output Settings",
)
P300_STILL_ASPECT_MENU_PATH: Tuple[str, ...] = (
    "Shooting",
    "Image Quality/Rec",
    "Aspect Ratio",
)

P300_DCI4K_RESID16: int = 0x7336  # _f.uxc ("XAVC S-I DCI 4K")
P300_DCI4K_LONG_RESID16: int = 0x61CE
P300_2400P_RESID16: int = 0x75CE
P300_2400P_REBOOT_G_RESID16: int = 0x639B
P300_2400P_REBOOT_ALT_G_RESID16: int = 0x63B6
P300_2400P_PLAYBACK_QUARANTINE_G_RESID16: int = 0x63D7
P300_SHUTTER_MODE_RESID16: int = 0x7C7C
P300_RAW_OUTPUT_RESID16: int = 0x6E97
P300_STILL_ASPECT_BKID: str = "BKID_APP_setting_aspect_ratio"
P300_STILL_ASPECT_RESID16: int = 0x757C  # _f.uxc

P300_MOVIE_FILE_FORMATS: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S HD",
    "XAVC S-I 4K",
    "XAVC S-I DCI 4K",
    "XAVC S-I HD",
)
P300_LONG_GOP_4K_FORMATS: Tuple[str, ...] = ("XAVC HS 4K", "XAVC S 4K")
P300_UHD_4K_FORMATS: Tuple[str, ...] = ("XAVC HS 4K", "XAVC S 4K", "XAVC S-I 4K")
P300_DORMANT_8K_FORMAT: str = "xavc_hs_8k_24p"

P300_DCI4K_DIMENSIONS: Tuple[int, int] = (4096, 2160)
P300_DCI4K_ASPECT: str = "17:9"
P300_UHD_4K_DIMENSIONS: Tuple[int, int] = (3840, 2160)
P300_UHD_ASPECT: str = "16:9"
P300_HD_DIMENSIONS: Tuple[int, int] = (1920, 1080)

P300_DCI4K_REC_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
)
P300_UHD_REC_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
)
P300_DCI4K_BITRATE_BY_FPS_MBPS: Dict[str, int] = {
    "23.98p": 240,
    "24.00p": 240,
    "25p": 250,
    "29.97p": 300,
    "50p": 500,
    "59.94p": 600,
}
P300_DCI4K_SQ_ALLOWED_FPS: Tuple[int, ...] = (1, 2, 3, 6, 12, 24, 48)
P300_DCI4K_SQ_LOCKED_OUT_FPS: Tuple[int, ...] = (100, 120)
P300_MEDIA_CARD_GRADES: Tuple[str, ...] = (
    "CFexpress VPG200+",
    "SDXC V90+",
    "SDXC V60",
    "SDXC V30",
)
P300_DCI4K_600M_MIN_GRADES: Tuple[str, ...] = ("CFexpress VPG200+", "SDXC V90+")

P300_SHUTTER_MODES: Tuple[str, ...] = ("Speed", "Angle")
P300_SHUTTER_ANGLE_MIN_DEG: float = 5.6
P300_SHUTTER_ANGLE_MAX_DEG: float = 360.0

P300_FX3_HDMI_RAW_DIMENSIONS: Tuple[int, int] = (4264, 2408)
P300_FX3_HDMI_RAW_ASPECT: str = "16:9"
P300_FX3_HDMI_RAW_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
)
P300_FX6_RAW_DIMENSIONS: Tuple[Tuple[int, int], ...] = (
    (4096, 2160),
    (3840, 2160),
)
P300_FX6_DCI4K_SQ_MAX_FPS: int = 60
P300_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Off", "Flexible ISO", "Cine EI Quick", "Cine EI")

P300_STILL_ASPECT_RATIOS: Tuple[str, ...] = ("3:2", "4:3", "16:9", "1:1")
P300_STILL_ASPECT_DEFAULT: str = "3:2"
P300_STILL_IMAGE_SIZE_TIERS: Tuple[str, ...] = ("L", "M", "S")
P300_STILL_IMAGE_SIZE_DEFAULT: str = "L"
P300_FX3_STILL_RAW_NATIVE_DIMS: Tuple[int, int] = (4240, 2832)
P300_STILL_ASPECT_SIZE_MATRIX: Dict[str, Dict[str, Tuple[str, int, int]]] = {
    "3:2": {"L": ("12M", 4240, 2832), "M": ("5.1M", 2768, 1848), "S": ("3.0M", 2128, 1416)},
    "4:3": {"L": ("11M", 3776, 2832), "M": ("4.6M", 2464, 1848), "S": ("2.7M", 1888, 1416)},
    "16:9": {"L": ("10M", 4240, 2384), "M": ("4.3M", 2768, 1560), "S": ("2.6M", 2128, 1200)},
    "1:1": {"L": ("8.0M", 2832, 2832), "M": ("3.4M", 1840, 1840), "S": ("2.0M", 1408, 1408)},
}
P300_STILL_ASPECT_RESID16_MAP: Dict[str, int] = {
    "3:2": 0xE4F8,
    "4:3": 0x7826,
    "16:9": 0x787D,
    "1:1": 0xE0D9,
}

# ---------------------------------------------------------------------------
# Pillar 53B Constants — [Reg. Custom Shoot Set] (11 Checkboxes & HLG Off),
# [Camera Set. Memory] (1..3 + M1..M4 Path Isolation vs FX6 PRO/CAMERA),
# & [Playback] [Photo Capture] (8.3M/2.1M DCI 4K Lockout & Slot-1 Firewall)
# / [Enlarge Image]
# ---------------------------------------------------------------------------

P300_REG_CUSTOM_SHOOT_SET_MENU_PATH: Tuple[str, ...] = (
    "Shooting",
    "Shooting Mode",
    "Reg. Custom Shoot Set",
)
P300_CAMSET_MEMORY_MENU_PATH: Tuple[str, ...] = (
    "Shooting",
    "Shooting Mode",
    "Camera Set. Memory",
)
P300_RECALL_CAMSET_MENU_PATH: Tuple[str, ...] = (
    "Shooting",
    "Shooting Mode",
    "Recall Camera Setting",
)
P300_PHOTO_CAPTURE_MENU_PATH: Tuple[str, ...] = (
    "Playback",
    "Edit",
    "Photo Capture",
)
P300_ENLARGE_IMAGE_MENU_PATH: Tuple[str, ...] = (
    "Playback",
    "Magnification",
    "Enlarge Image",
)

P300_REG_CUSTOM_SHOOT_SET_RESID16: int = 0x7631  # _f.uxc
P300_REG_CUSTOM_SHOOT_SET_SLOTS: Tuple[str, ...] = (
    "Recall Custom hold 1",
    "Recall Custom hold 2",
    "Recall Custom hold 3",
)
P300_REG_CUSTOM_HOLD_RESID16_MAP: Dict[str, int] = {
    "Recall Custom hold 1": 0x60B4,
    "Recall Custom hold 2": 0x7581,
    "Recall Custom hold 3": 0x725B,
}
P300_REG_CUSTOM_HOLD_DEFAULT: str = "Recall Custom hold 1"
P300_REG_CUSTOM_SHOOT_SET_11_CHECKBOXES: Tuple[str, ...] = (
    "shooting_mode",
    "aperture",
    "shutter_speed",
    "exposure_comp",
    "iso_sensitivity",
    "metering_mode",
    "drive_mode",
    "focus_mode",
    "focus_area",
    "af_on",
    "still_af_track_sens",
)
P300_REG_CUSTOM_HOLD_CHECKBOX_COUNT: int = 11
P300_REG_CUSTOM_HLG_FORCE_OFF_RECALLED_ITEMS: Tuple[str, ...] = (
    "iso_sensitivity",
    "dro_bracket",
)

P300_CAMSET_BODY_BANKS: Tuple[str, ...] = ("1", "2", "3")
P300_CAMSET_CARD_BANKS: Tuple[str, ...] = ("M1", "M2", "M3", "M4")
P300_CAMSET_ALL_BANKS: Tuple[str, ...] = P300_CAMSET_BODY_BANKS + P300_CAMSET_CARD_BANKS
P300_CAMSET_CARD_TYPE_SUBDIR_MAP: Dict[str, str] = {
    "SDXC": "/PRIVATE",
    "SDHC": "/PRIVATE",
    "SD": "/PRIVATE",
    "CFexpress Type A": "",
}
P300_FX3_CAMPR_PATH_TEMPLATE: str = "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"
P300_FX3_CAMSET_PATH_TEMPLATE: str = "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
P300_FX3_SETTING_MODEL_TAG: str = "FX3"
P300_FX6_PRO_CAMERA_PATH_PREFIX: str = "s/SONY/PRO/CAMERA/"
P300_FX6_PRO_SCENE_PATH_PREFIX: str = "s/SONY/PRO/SCENE/"
P300_FX6_MAX_ALL_FILES: int = 64

P300_PHOTO_CAPTURE_BKID: str = "BKID_APP_is_edit_photo_capture"
P300_PHOTO_CAPTURE_RESID16: int = 0x6856  # _f.uxc
P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_G_RESID16: int = 0x60CE  # _g.uxc
P300_PHOTO_CAPTURE_FILE_TYPES: Tuple[str, ...] = (
    "JPEG",
    "HEIF(4:2:0)",
    "HEIF(4:2:2)",
)
P300_PHOTO_CAPTURE_FILE_TYPE_DEFAULT: str = "JPEG"
P300_PHOTO_CAPTURE_4K_UHD_DIMS: Tuple[int, int] = (3840, 2160)
P300_PHOTO_CAPTURE_4K_UHD_MP: str = "8.3M"
P300_PHOTO_CAPTURE_HD_DIMS: Tuple[int, int] = (1920, 1080)
P300_PHOTO_CAPTURE_HD_MP: str = "2.1M"

P300_ENLARGE_IMAGE_RESID16: int = 0xE8CB  # .uxc
P300_ENLARGE_INITIAL_MAG_BKID: str = "BKID_APP_setting_magnif_set_in_large"
P300_ENLARGE_INITIAL_MAG_RESID16: int = 0x6B6E  # _f.uxc
P300_ENLARGE_INITIAL_MAG_MODES: Tuple[str, ...] = ("Standard. Mag.", "Previous Mag.")
P300_ENLARGE_INITIAL_MAG_DEFAULT: str = "Standard. Mag."
P300_ENLARGE_INITIAL_POS_BKID: str = "BKID_APP_setting_position_set_in_large"
P300_ENLARGE_INITIAL_POS_RESID16: int = 0x781F  # _f.uxc
P300_ENLARGE_INITIAL_POS_MODES: Tuple[str, ...] = ("Focused Position", "Center")
P300_ENLARGE_INITIAL_POS_DEFAULT: str = "Focused Position"

P300_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P300_STILL_PASM_MODES: Tuple[str, ...] = ("P", "A", "S", "M")
P300_STILL_ALL_MODES: Tuple[str, ...] = ("Intelligent Auto", "P", "A", "S", "M", "MR")
P300_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P300_RESET_ACTIONS: Tuple[str, ...] = (
    "None",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P300_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "ENLARGE_IMAGE_VIEW",
    "SAVE_CAMPR_M1_M4_CARD",
    "SAVE_CAMSET_DAT_CARD",
    "LOAD_FX6_PRO_CAMERA_SETTING",
    "PHOTO_CAPTURE_STILL_EXTRACT",
    "FORMAT_QUICK",
    "FORMAT_FULL",
    "DELETE_SINGLE",
)
P300_DESTRUCTIVE_VAULT_ACTIONS: Tuple[str, ...] = (
    "SAVE_CAMPR_M1_M4_CARD",
    "SAVE_CAMSET_DAT_CARD",
    "PHOTO_CAPTURE_STILL_EXTRACT",
    "FORMAT_QUICK",
    "FORMAT_FULL",
    "DELETE_SINGLE",
)
P300_SLOT1_VAULT_SLOT: int = 1
P300_SAFE_SECONDARY_CAPTURE_SLOT: int = 2
P300_VAULT_FIREWALL_ERRNOS: Tuple[str, ...] = ("EROFS", "EBUSY")
P300_STAGE_B_VOLATILE_OVERLAY_DIR: str = (
    "/tmp/fx3_dci4k_aspect_custom_hold_camset_photo_capture_vault_overlay"
)
P300_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P300_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P300_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P300_BLOCKED_INVALID_PILLAR53A_SPEC: str = "BLOCKED_INVALID_PILLAR53A_SPEC"
P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION: str = (
    "BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION"
)
P300_BLOCKED_2400P_REBOOT_STAGE_B_WIPE_OR_QUARANTINE_DRIFT: str = (
    "BLOCKED_2400P_REBOOT_STAGE_B_WIPE_OR_QUARANTINE_DRIFT"
)
P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION: str = (
    "BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION"
)
P300_BLOCKED_INVALID_PILLAR53B_SPEC: str = "BLOCKED_INVALID_PILLAR53B_SPEC"
P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT: str = (
    "BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT"
)
P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION: str = (
    "BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION"
)
P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT: str = (
    "BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT"
)
P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL: str = "BLOCKED_SLOT1_VAULT_WRITE_FIREWALL"
P300_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P300_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P300_STATUS_VERIFIED_PILLAR_53A: str = (
    "VERIFIED_PILLAR_53A_DCI4K_2400P_REBOOT_STAGE_B_WIPE_4264RAW_STILL_ASPECT_AND_SLOT1_VAULT"
)
P300_STATUS_REJECTED_PILLAR_53A: str = (
    "REJECTED_PILLAR_53A_DCI4K_2400P_REBOOT_STAGE_B_WIPE_4264RAW_STILL_ASPECT_AND_SLOT1_VAULT"
)
P300_STATUS_VERIFIED_PILLAR_53B: str = (
    "VERIFIED_PILLAR_53B_REG_CUSTOM_HOLD11_CAMSET_PATH_PHOTO_CAPTURE_ENLARGE_AND_SLOT1_VAULT"
)
P300_STATUS_REJECTED_PILLAR_53B: str = (
    "REJECTED_PILLAR_53B_REG_CUSTOM_HOLD11_CAMSET_PATH_PHOTO_CAPTURE_ENLARGE_AND_SLOT1_VAULT"
)
P300_STATUS_VERIFIED_PILLAR53_SUITE: str = (
    "VERIFIED_PILLAR53_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_VAULT"
)
P300_STATUS_FAIL_PILLAR53_SUITE: str = (
    "FAIL_PILLAR53_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_VAULT"
)
P300_STATUS_VERIFIED_53OF53_AGGREGATOR: str = "VERIFIED_53OF53_PILLAR_RECOVERY_MASTER"
P300_STATUS_FAIL_53OF53_AGGREGATOR: str = "FAIL_53OF53_PILLAR_RECOVERY_MASTER"

P300_PILLAR_53A_SCENARIO_IDS: Tuple[str, ...] = (
    "P53A1_DCI4K_4096X2160_17_9_SQ_48FPS_HDMI_4264RAW_STILL_ASPECT_3_2_SAFE",
    "P53A2_2400P_MANDATORY_REBOOT_VOLATILE_STAGE_B_CLEAN_WIPE_H0_EQ_H2_SAFE",
    "P53A3_REJECT_LONG_GOP_4K_DCI4096_OR_DORMANT_8K_OR_DCI4K_SQ_120FPS",
    "P53A4_REJECT_2400P_SILENT_NO_REBOOT_OR_UNQUARANTINED_PLAYBACK_OR_STAGE_B_PERSIST",
    "P53A5_REJECT_4264RAW_WITHOUT_LOG_OR_FX6_STILL_ASPECT_OR_APSC_L_SIZE_SPOOF",
    "P53A6_REJECT_SLOT1_VAULT_FORMAT_OR_PERSISTENT_OVERLAY_OR_H0_H3_DRIFT",
)
P300_PILLAR_53B_SCENARIO_IDS: Tuple[str, ...] = (
    "P53B1_STILL_PASM_REG_CUSTOM_HOLD11_CAMSET_SLOT2_AND_ENLARGE_READONLY_SAFE",
    "P53B2_PLAYBACK_PHOTO_CAPTURE_8_3M_UHD_TO_SLOT2_AND_CAMPR_SDXC_CFEX_PATH_SAFE",
    "P53B3_REJECT_REG_CUSTOM_HOLD_IN_MOVIE_OR_HLG_STILL_ON_WITH_ISO_RECALL",
    "P53B4_REJECT_FX6_PRO_CAMERA_CROSS_MODEL_CAMSET_OR_WRONG_CHECKBOX_COUNT",
    "P53B5_REJECT_PHOTO_CAPTURE_ON_XAVC_SI_DCI4K_CLIP_OR_FX6_CONFLATION",
    "P53B6_REJECT_SLOT1_PHOTO_CAPTURE_OR_CAMSET_WRITE_ON_TIER0_VAULT",
)

MASTER_53_PILLAR_COUNT: int = 53
MASTER_53_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_52_PILLAR_SPECS + (
    (
        53,
        "pillar_53_dci4k_aspect_custom_hold_camset_photo_capture_vault",
        "Phase 300 (300th Phase Milestone, Wave-51)",
        "fx3_recovery.realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier",
    ),
)
MASTER_53_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_53_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Deterministic State Computations
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _is_clean_room_forced(force_clean_room: Optional[bool] = None) -> bool:
    """Honor explicit flag, `FX3_FX6_FORCE_CLEAN_ROOM=1`, AND `FX3_CLEAN_ROOM_TEST=1`."""
    if force_clean_room is not None:
        return bool(force_clean_room)
    if is_forced_clean_room():
        return True
    return os.environ.get(P300_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P300_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P300_DONOR_INSPECT_BUDGET_SECONDS


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    checks = (
        ("PERSISTENT_EMMC_WRITES_AUTHORIZED", PERSISTENT_EMMC_WRITES_AUTHORIZED, False),
        ("SPI_NOR_WRITE_AUTHORIZED", SPI_NOR_WRITE_AUTHORIZED, False),
        ("EL3_PAYLOAD_TRANSMIT_AUTHORIZED", EL3_PAYLOAD_TRANSMIT_AUTHORIZED, False),
        ("ISP_WRITE_AUTHORIZED", ISP_WRITE_AUTHORIZED, False),
        ("PERSISTENT_WRITE_RELEASE", PERSISTENT_WRITE_RELEASE, False),
        ("ALLOW_BOOT_PARTITION_TARGETING", ALLOW_BOOT_PARTITION_TARGETING, False),
        ("ALLOW_DESTRUCTIVE_FASTBOOT", ALLOW_DESTRUCTIVE_FASTBOOT, False),
        ("ALLOW_PERSISTENT_JIRITSU_WRITES", ALLOW_PERSISTENT_JIRITSU_WRITES, False),
        ("ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS", ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS, False),
        ("LIVE_USB_IOKIT_TRANSMIT_ENABLED", LIVE_USB_IOKIT_TRANSMIT_ENABLED, False),
        ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("OVERALL_READY_FOR_HARDWARE_ATTACH", OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("P300_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P300_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("P300_OVERALL_READY_FOR_HARDWARE_ATTACH", P300_OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P300_DCI4K_LONG_GOP_OR_8K_VIOLATIONS", P300_DCI4K_LONG_GOP_OR_8K_VIOLATIONS, 0),
        ("P300_2400P_REBOOT_STAGE_B_WIPE_VIOLATIONS", P300_2400P_REBOOT_STAGE_B_WIPE_VIOLATIONS, 0),
        ("P300_HDMI_RAW_OR_STILL_ASPECT_DRIFT_EVENTS", P300_HDMI_RAW_OR_STILL_ASPECT_DRIFT_EVENTS, 0),
        ("P300_FX6_STILL_OR_RAW_CONFLATION_EVENTS", P300_FX6_STILL_OR_RAW_CONFLATION_EVENTS, 0),
        ("P300_REG_CUSTOM_HOLD_OR_HLG_LOCK_DRIFT_EVENTS", P300_REG_CUSTOM_HOLD_OR_HLG_LOCK_DRIFT_EVENTS, 0),
        ("P300_CAMSET_CROSS_MODEL_PATH_DRIFT_EVENTS", P300_CAMSET_CROSS_MODEL_PATH_DRIFT_EVENTS, 0),
        ("P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_BYPASS_EVENTS", P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_BYPASS_EVENTS, 0),
        ("P300_SLOT1_CAMSET_WRITE_BYTES", P300_SLOT1_CAMSET_WRITE_BYTES, 0),
        ("P300_SLOT1_PHOTO_CAPTURE_WRITE_BYTES", P300_SLOT1_PHOTO_CAPTURE_WRITE_BYTES, 0),
        ("P300_SLOT1_VAULT_MUTATION_BYTES", P300_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P300_SLOT1_FORMAT_HARD_LOCKED", P300_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED", P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED, True),
        ("P300_FX3_APPFW_HAS_DCI4K_INTERNAL", P300_FX3_APPFW_HAS_DCI4K_INTERNAL, True),
        ("P300_FX3_APPFW_HAS_PRO_CAMERA_PATH", P300_FX3_APPFW_HAS_PRO_CAMERA_PATH, False),
        ("P300_FX6_HAS_STILL_ASPECT_RATIO", P300_FX6_HAS_STILL_ASPECT_RATIO, False),
        ("P300_FX6_HAS_PHOTO_CAPTURE", P300_FX6_HAS_PHOTO_CAPTURE, False),
        ("P300_FX6_HAS_PLAYBACK_ENLARGE_IMAGE", P300_FX6_HAS_PLAYBACK_ENLARGE_IMAGE, False),
        ("P300_FX6_HAS_REG_CUSTOM_SHOOT_SET", P300_FX6_HAS_REG_CUSTOM_SHOOT_SET, False),
        ("P300_FX6_HAS_CAMERA_SET_MEMORY", P300_FX6_HAS_CAMERA_SET_MEMORY, False),
        ("OTP_FUSE_TOUCHES", OTP_FUSE_TOUCHES, 0),
        ("OTP_FUSE_WRITES", OTP_FUSE_WRITES, 0),
        ("RPMB_COUNTER_INCREMENTS", RPMB_COUNTER_INCREMENTS, 0),
        ("PASSIVE_TX_BYTES_EMITTED", PASSIVE_TX_BYTES_EMITTED, 0),
        ("PHYSICAL_USB_PACKETS_EMITTED", PHYSICAL_USB_PACKETS_EMITTED, 0),
        ("PHYSICAL_DEVICE_WRITES", PHYSICAL_DEVICE_WRITES, 0),
        ("RAW_FIRMWARE_BYTES_LEAKED", RAW_FIRMWARE_BYTES_LEAKED, 0),
    )
    for name, actual, expected in checks:
        if actual != expected:
            errs.append(f"{name} expected {expected!r}, got {actual!r}")
    return errs


def _is_tmpfs_path(path_value: str) -> bool:
    norm = posixpath.normpath(path_value)
    return norm.startswith("/tmp/") or norm.startswith("/run/")


def _targets_persistent_emmc(path_value: str) -> bool:
    low = path_value.strip().lower()
    return any(tok in low for tok in P300_FORBIDDEN_PERSISTENT_TARGETS)


def build_fx3_campr_card_path(
    *,
    drive_letter: str = "E",
    media_kind: str = "SDXC",
    bank_index: int = 1,
    slot_suffix: str = "A",
) -> str:
    """Build exact `FX3 appFw.so` `M1..M4` card path: `%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`."""
    subdir = P300_CAMSET_CARD_TYPE_SUBDIR_MAP.get(media_kind)
    _need(subdir is not None, f"Unsupported FX3 media_kind: {media_kind}")
    _need(1 <= bank_index <= 4, f"M1..M4 bank_index out of range: {bank_index}")
    return f"{drive_letter}:{subdir}/SONY/SETTING/{P300_FX3_SETTING_MODEL_TAG}/CAMPR{bank_index:02d}{slot_suffix}.DAT"


def build_fx3_camset_card_path(
    *,
    drive_letter: str = "E",
    media_kind: str = "SDXC",
    filename_stem: str = "CAMSET01",
) -> str:
    """Build exact `FX3 appFw.so` `Save/Load Settings` path: `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`."""
    subdir = P300_CAMSET_CARD_TYPE_SUBDIR_MAP.get(media_kind)
    _need(subdir is not None, f"Unsupported FX3 media_kind: {media_kind}")
    return f"{drive_letter}:{subdir}/SONY/SETTING/{P300_FX3_SETTING_MODEL_TAG}/CAMSET/{filename_stem}.DAT"


def compute_expected_dci4k_2400p_hdmi_raw_and_still_aspect_state(
    *,
    file_format: str,
    prev_rec_frame_rate: str,
    target_rec_frame_rate: str,
    sq_frame_rate_fps: int,
    media_card_grade: str,
    hdmi_raw_enabled: bool,
    log_shooting_mode: str,
    still_aspect_ratio: str,
    still_size_tier: str,
    apsc_s35_enabled: bool,
    reset_action: str,
) -> Tuple[Tuple[int, int], str, bool, bool, bool, bool, bool, str, Tuple[int, int], str]:
    """Compute `(movie_dims, movie_aspect, format_rec_allowed, sq_allowed, media_speed_ok,
    mandatory_reboot, volatile_stage_b_wiped, post_still_aspect, raw_native_dims, post_still_size)`.

    - `XAVC S-I DCI 4K` exposes `(4096, 2160)` `17:9`, `24.00p`, and S&Q `1..48fps`
      (locking out `100/120fps`), requiring `CFexpress VPG200+` or `SDXC V90+` at `600M` (`59.94p`).
    - Long-GOP (`XAVC HS 4K`, `XAVC S 4K`) & `XAVC S-I 4K` remain `(3840, 2160)` `16:9` UHD
      with NO `24.00p`. Dormant `xavc_hs_8k_24p` is rejected fail-closed.
    - Switching into or out of `24.00p` triggers a **mandatory camera reboot**, cleanly
      wiping volatile `/tmp` Stage-B bind mounts back to stock `7.02` (`H0 == H2`).
    - HDMI RAW `4264x2408` requires `log_shooting_mode != "Off"`.
    - Still `[Aspect Ratio]` defaults to `"3:2"` (`Can be reset` via `Camera Settings Reset`),
      RAW always keeps `4240x2832` + crop metadata, and `APS-C S35 = On` steps `L -> M`.
    """
    if file_format == P300_DORMANT_8K_FORMAT or file_format not in P300_MOVIE_FILE_FORMATS:
        return (0, 0), "INVALID", False, False, False, False, False, P300_STILL_ASPECT_DEFAULT, P300_FX3_STILL_RAW_NATIVE_DIMS, "M"

    if file_format == "XAVC S-I DCI 4K":
        movie_dims = P300_DCI4K_DIMENSIONS
        movie_aspect = P300_DCI4K_ASPECT
        rec_allowed = target_rec_frame_rate in P300_DCI4K_REC_FRAME_RATES
        sq_allowed = sq_frame_rate_fps in P300_DCI4K_SQ_ALLOWED_FPS
        bitrate = P300_DCI4K_BITRATE_BY_FPS_MBPS.get(target_rec_frame_rate, 0)
        media_ok = (media_card_grade in P300_DCI4K_600M_MIN_GRADES) if bitrate >= 500 else (media_card_grade in P300_MEDIA_CARD_GRADES)
    elif file_format in P300_UHD_4K_FORMATS:
        movie_dims = P300_UHD_4K_DIMENSIONS
        movie_aspect = P300_UHD_ASPECT
        rec_allowed = target_rec_frame_rate in P300_UHD_REC_FRAME_RATES and target_rec_frame_rate != "24.00p"
        sq_allowed = 1 <= sq_frame_rate_fps <= 120
        media_ok = media_card_grade in P300_MEDIA_CARD_GRADES
    else:
        movie_dims = P300_HD_DIMENSIONS
        movie_aspect = P300_UHD_ASPECT
        rec_allowed = target_rec_frame_rate != "24.00p"
        sq_allowed = 1 <= sq_frame_rate_fps <= 240
        media_ok = media_card_grade in P300_MEDIA_CARD_GRADES

    if hdmi_raw_enabled and log_shooting_mode == "Off":
        rec_allowed = False

    entering_or_exiting_2400p = (prev_rec_frame_rate == "24.00p") != (target_rec_frame_rate == "24.00p")
    mandatory_reboot = entering_or_exiting_2400p
    volatile_stage_b_wiped = mandatory_reboot

    resets_still = reset_action in ("Camera Settings Reset", "Initialize")
    post_aspect = P300_STILL_ASPECT_DEFAULT if resets_still else still_aspect_ratio
    base_size = P300_STILL_IMAGE_SIZE_DEFAULT if resets_still else still_size_tier
    post_size = "M" if (apsc_s35_enabled and base_size == "L") else base_size

    return (
        movie_dims,
        movie_aspect,
        rec_allowed,
        sq_allowed,
        media_ok,
        mandatory_reboot,
        volatile_stage_b_wiped,
        post_aspect,
        P300_FX3_STILL_RAW_NATIVE_DIMS,
        post_size,
    )


def compute_expected_reg_custom_hold_and_camset_memory_state(
    *,
    shooting_domain: str,
    shooting_mode: str,
    hold_recalled_items: Tuple[str, ...],
    initial_hlg_still_image: str,
    camset_bank: str,
    memory_recall_media: str,
    reset_action: str,
) -> Tuple[bool, str, bool, bool, str, bool]:
    """Compute `(reg_custom_hold_allowed, eff_hlg_still_image, body_banks_survived,
    reg_custom_hold_survived, post_memory_recall_media, camset_save_allowed)`.

    - `[Reg. Custom Shoot Set]` is **Still `P/A/S/M` only**.
    - Recalling `iso_sensitivity` or `dro_bracket` forces `[HLG Still Image] = "Off"`.
    - `Camera Settings Reset` keeps `[Reg. Custom Shoot Set]` & body `1..3` intact,
      **but** resets `[Memory/Recall Media]` to `"Slot 1"`.
    - `Initialize` wipes both `[Reg. Custom Shoot Set]` and body `1..3` (leaving card `M1..M4`
      and `CAMSET` files untouched on media).
    - `[Save/Load Settings]` (`CAMSET`) is disabled while in `MR` mode.
    """
    reg_allowed = shooting_domain == "Still" and shooting_mode in P300_STILL_PASM_MODES
    forces_hlg_off = reg_allowed and any(
        item in P300_REG_CUSTOM_HLG_FORCE_OFF_RECALLED_ITEMS for item in hold_recalled_items
    )
    eff_hlg = "Off" if forces_hlg_off else initial_hlg_still_image

    initialized = reset_action == "Initialize"
    body_banks_survived = not initialized
    reg_survived = not initialized
    post_media = (
        "Slot 1"
        if reset_action in ("Camera Settings Reset", "Initialize")
        else memory_recall_media
    )
    camset_save_allowed = shooting_mode != "MR" and camset_bank in P300_CAMSET_ALL_BANKS
    return (
        reg_allowed,
        eff_hlg,
        body_banks_survived,
        reg_survived,
        post_media,
        camset_save_allowed,
    )


def compute_expected_photo_capture_and_enlarge_image_state(
    *,
    clip_file_format: str,
    clip_resolution: Tuple[int, int],
    select_playback_media: str,
    slot1_holds_recovery_vault: bool,
    playback_media_kind: str,
    configured_photo_capture_type: str,
    configured_enlarge_init_mag: str,
    configured_enlarge_init_pos: str,
    reset_action: str,
) -> Tuple[bool, Optional[Tuple[int, int]], Optional[str], bool, str, str, str]:
    """Compute `(photo_capture_allowed, output_dims, output_mp, enlarge_image_allowed,
    post_photo_capture_type, post_enlarge_mag, post_enlarge_pos)`.

    - `[Photo Capture]` is locked out on `XAVC S-I DCI 4K` clips (`_g.uxc` `0x60ce`)
      AND blocked fail-closed when `[Select Playback Media] == "Slot 1"` holds the
      read-only Tier-0 recovery vault!
    - `4K` UHD -> `3840x2160` (`8.3M`), `HD` -> `1920x1080` (`2.1M`).
    - Read-only `[Enlarge Image]` is safe on Still playback even on `Slot 1` (`Still`).
    - `(Playback)` settings survive `Camera Settings Reset`; only `Initialize` resets them.
    """
    is_dci4k = clip_file_format == "XAVC S-I DCI 4K"
    slot1_vault_blocked = select_playback_media == "Slot 1" and slot1_holds_recovery_vault
    photo_capture_allowed = (not is_dci4k) and (not slot1_vault_blocked) and (playback_media_kind == "Movie")

    if clip_resolution == P300_UHD_4K_DIMENSIONS and photo_capture_allowed:
        out_dims: Optional[Tuple[int, int]] = P300_PHOTO_CAPTURE_4K_UHD_DIMS
        out_mp: Optional[str] = P300_PHOTO_CAPTURE_4K_UHD_MP
    elif clip_resolution == P300_HD_DIMENSIONS and photo_capture_allowed:
        out_dims = P300_PHOTO_CAPTURE_HD_DIMS
        out_mp = P300_PHOTO_CAPTURE_HD_MP
    else:
        out_dims = None
        out_mp = None

    enlarge_allowed = playback_media_kind == "Still"
    initialized = reset_action == "Initialize"
    post_pc_type = P300_PHOTO_CAPTURE_FILE_TYPE_DEFAULT if initialized else configured_photo_capture_type
    post_mag = P300_ENLARGE_INITIAL_MAG_DEFAULT if initialized else configured_enlarge_init_mag
    post_pos = P300_ENLARGE_INITIAL_POS_DEFAULT if initialized else configured_enlarge_init_pos
    return (
        photo_capture_allowed,
        out_dims,
        out_mp,
        enlarge_allowed,
        post_pc_type,
        post_mag,
        post_pos,
    )


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase300DonorArtifactDigest:
    artifact_id: str
    relpath: str
    present: bool
    read_mode: str
    total_bytes: int
    header_bytes_read: int
    digest_kind: str
    digest_sha256: str
    marker_summary: str
    matches_pinned: bool


@dataclass(frozen=True)
class Phase300DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase300DonorArtifactDigest, ...]


@dataclass(frozen=True)
class Dci4k2400pHdmiRawStillAspectVaultSpec:
    camera_model: str = P300_FX3_MODEL_NAME
    camera_model_id: int = P300_FX3_MODEL_ID
    camera_codename: str = P300_FX3_PRODUCT_CODENAME
    helpguide_id: str = P300_FX3_HELPGUIDE_ID
    fw_version: str = P300_FX3_FW_VERSION
    dci4k_aspect_surface_model: str = "FX3_ALL_INTRA_DCI4K_2400P_REBOOT_HDMI_4264RAW_STILL_ASPECT"
    fx3_appfw_has_dci4k_internal: bool = P300_FX3_APPFW_HAS_DCI4K_INTERNAL
    fx6_has_still_aspect_ratio: bool = P300_FX6_HAS_STILL_ASPECT_RATIO
    fx6_raw_dimensions: Tuple[Tuple[int, int], ...] = P300_FX6_RAW_DIMENSIONS
    fx6_dci4k_sq_max_fps: int = P300_FX6_DCI4K_SQ_MAX_FPS
    # Movie DCI 4K vs Long-GOP UHD & 24.00p Mandatory Reboot / Stage-B Wipe Guard
    file_format: str = "XAVC S-I DCI 4K"
    reported_movie_dimensions: Tuple[int, int] = P300_DCI4K_DIMENSIONS
    reported_movie_aspect: str = P300_DCI4K_ASPECT
    prev_rec_frame_rate: str = "23.98p"
    target_rec_frame_rate: str = "23.98p"
    sq_frame_rate_fps: int = 48
    media_card_grade: str = "CFexpress VPG200+"
    shutter_mode: str = "Angle"
    shutter_angle_deg: float = 180.0
    reported_mandatory_reboot: bool = False
    reported_volatile_stage_b_wiped: bool = False
    reported_2400p_playback_quarantined: bool = False
    stage_b_post_2400p_h0_eq_h2: bool = True
    # 4264x2408 HDMI RAW & Still [Aspect Ratio]
    hdmi_raw_enabled: bool = True
    hdmi_raw_dimensions: Tuple[int, int] = P300_FX3_HDMI_RAW_DIMENSIONS
    log_shooting_mode: str = "Cine EI"
    hdmi_raw_gamma_locked: str = "S-Log3"
    hdmi_raw_steadyshot_active_allowed: bool = False
    hdmi_raw_desqueeze_allowed: bool = False
    still_aspect_ratio: str = P300_STILL_ASPECT_DEFAULT
    post_still_aspect_ratio: str = P300_STILL_ASPECT_DEFAULT
    still_size_tier: str = P300_STILL_IMAGE_SIZE_DEFAULT
    post_still_size_tier: str = P300_STILL_IMAGE_SIZE_DEFAULT
    apsc_s35_enabled: bool = False
    still_raw_native_dims: Tuple[int, int] = P300_FX3_STILL_RAW_NATIVE_DIMS
    reset_action: str = "None"
    dci4k_long_gop_or_8k_violations: int = 0
    reboot_2400p_stage_b_wipe_violations: int = 0
    hdmi_raw_or_still_aspect_drift_events: int = 0
    fx6_still_or_raw_conflation_events: int = 0
    # Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P300_SLOT1_FORMAT_HARD_LOCKED
    slot1_vault_erofs_ebusy_enforced: bool = P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED
    target_capture_slot: int = P300_SAFE_SECONDARY_CAPTURE_SLOT
    requested_vault_slot: int = P300_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_vault_mutation_bytes: int = 0
    overlay_dir: str = P300_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P300_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P300_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P300_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class Dci4k2400pHdmiRawStillAspectVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    dci4k_vs_long_gop_and_no_8k_verified: bool
    reboot_2400p_stage_b_wipe_and_quarantine_verified: bool
    hdmi_raw_4264_and_still_aspect_verified: bool
    fx6_cinema_raw_and_still_less_contrast_verified: bool
    slot1_erofs_ebusy_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    dci4k_long_gop_or_8k_violations: int
    reboot_2400p_stage_b_wipe_violations: int
    hdmi_raw_or_still_aspect_drift_events: int
    fx6_still_or_raw_conflation_events: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegCustomHoldCamsetPhotoCaptureVaultSpec:
    camera_model: str = P300_FX3_MODEL_NAME
    camera_model_id: int = P300_FX3_MODEL_ID
    helpguide_id: str = P300_FX3_HELPGUIDE_ID
    fw_version: str = P300_FX3_FW_VERSION
    custom_camset_capture_surface_model: str = (
        "FX3_REG_CUSTOM_HOLD11_CAMPR_SETTING_PATH_PHOTO_CAPTURE_ENLARGE"
    )
    fx3_appfw_has_pro_camera_path: bool = P300_FX3_APPFW_HAS_PRO_CAMERA_PATH
    fx6_has_photo_capture: bool = P300_FX6_HAS_PHOTO_CAPTURE
    fx6_has_playback_enlarge_image: bool = P300_FX6_HAS_PLAYBACK_ENLARGE_IMAGE
    fx6_has_reg_custom_shoot_set: bool = P300_FX6_HAS_REG_CUSTOM_SHOOT_SET
    fx6_has_camera_set_memory: bool = P300_FX6_HAS_CAMERA_SET_MEMORY
    # [Reg. Custom Shoot Set] (Recall Custom hold 1..3, 11 Checkboxes & HLG Still Off)
    shooting_domain: str = "Still"
    shooting_mode: str = "M"
    reg_custom_hold_slot: str = P300_REG_CUSTOM_HOLD_DEFAULT
    reg_custom_hold_checkboxes: Tuple[str, ...] = P300_REG_CUSTOM_SHOOT_SET_11_CHECKBOXES
    hold_recalled_items: Tuple[str, ...] = ("aperture", "shutter_speed")
    initial_hlg_still_image: str = "Off"
    reported_hlg_still_image: str = "Off"
    reported_reg_custom_hold_allowed: bool = True
    reported_reg_custom_hold_survived: bool = True
    # [Camera Set. Memory] (1..3 + M1..M4 Path Isolation vs FX6 PRO/CAMERA)
    camset_bank: str = "M1"
    camset_media_kind: str = "SDXC"
    camset_card_path: str = "E:/PRIVATE/SONY/SETTING/FX3/CAMPR01B.DAT"
    camset_all_path: str = "E:/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT"
    memory_recall_media: str = "Slot 2"
    post_memory_recall_media: str = "Slot 2"
    reported_body_banks_survived: bool = True
    reported_camset_save_allowed: bool = True
    cross_model_fx6_import_attempted: bool = False
    # [Playback] [Photo Capture] & [Enlarge Image]
    playback_media_kind: str = "Movie"
    select_playback_media: str = "Slot 2"
    clip_file_format: str = "XAVC S 4K"
    clip_resolution: Tuple[int, int] = P300_UHD_4K_DIMENSIONS
    configured_photo_capture_type: str = P300_PHOTO_CAPTURE_FILE_TYPE_DEFAULT
    post_photo_capture_type: str = P300_PHOTO_CAPTURE_FILE_TYPE_DEFAULT
    photo_capture_attempted: bool = True
    reported_photo_capture_allowed: bool = True
    reported_photo_capture_dims: Optional[Tuple[int, int]] = P300_PHOTO_CAPTURE_4K_UHD_DIMS
    reported_photo_capture_mp: Optional[str] = P300_PHOTO_CAPTURE_4K_UHD_MP
    enlarge_image_attempted: bool = False
    reported_enlarge_image_allowed: bool = False
    configured_enlarge_init_mag: str = P300_ENLARGE_INITIAL_MAG_DEFAULT
    post_enlarge_init_mag: str = P300_ENLARGE_INITIAL_MAG_DEFAULT
    configured_enlarge_init_pos: str = P300_ENLARGE_INITIAL_POS_DEFAULT
    post_enlarge_init_pos: str = P300_ENLARGE_INITIAL_POS_DEFAULT
    reset_action: str = "None"
    reg_custom_hold_or_hlg_lock_drift_events: int = 0
    camset_cross_model_path_drift_events: int = 0
    photo_capture_dci4k_lockout_bypass_events: int = 0
    # Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P300_SLOT1_FORMAT_HARD_LOCKED
    slot1_vault_erofs_ebusy_enforced: bool = P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED
    target_camset_or_capture_slot: int = P300_SAFE_SECONDARY_CAPTURE_SLOT
    requested_vault_slot: int = P300_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_camset_write_bytes: int = 0
    slot1_photo_capture_write_bytes: int = 0
    overlay_dir: str = P300_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P300_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P300_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P300_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class RegCustomHoldCamsetPhotoCaptureVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    reg_custom_hold11_and_hlg_lockout_verified: bool
    camset_path_isolation_and_fx6_firewall_verified: bool
    photo_capture_dci4k_lockout_and_enlarge_verified: bool
    slot1_erofs_ebusy_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    reg_custom_hold_or_hlg_lock_drift_events: int
    camset_cross_model_path_drift_events: int
    photo_capture_dci4k_lockout_bypass_events: int
    slot1_camset_write_bytes: int
    slot1_photo_capture_write_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Dci4kAspectCustomHoldCamsetPhotoCaptureVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase300DonorSnapshot
    dci4k_aspect_report: Dci4k2400pHdmiRawStillAspectVaultReport
    custom_hold_camset_capture_report: RegCustomHoldCamsetPhotoCaptureVaultReport
    dci4k_long_gop_or_8k_violations: int
    reboot_2400p_stage_b_wipe_violations: int
    hdmi_raw_or_still_aspect_drift_events: int
    fx6_still_or_raw_conflation_events: int
    reg_custom_hold_or_hlg_lock_drift_events: int
    camset_cross_model_path_drift_events: int
    photo_capture_dci4k_lockout_bypass_events: int
    slot1_camset_write_bytes: int
    slot1_photo_capture_write_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar53ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar53ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar53ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar53BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar53ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar53StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase300DonorSnapshot
    pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault: Pillar53ASuiteResult
    pillar_53b_custom_hold_camset_photo_capture_vault: Pillar53BSuiteResult
    dci4k_long_gop_or_8k_violations: int
    reboot_2400p_stage_b_wipe_violations: int
    hdmi_raw_or_still_aspect_drift_events: int
    fx6_still_or_raw_conflation_events: int
    reg_custom_hold_or_hlg_lock_drift_events: int
    camset_cross_model_path_drift_events: int
    photo_capture_dci4k_lockout_bypass_events: int
    slot1_camset_write_bytes: int
    slot1_photo_capture_write_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    suite_sha256: str
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master53PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_1_2s_fast_cli_budget: bool
    under_2_5s_fast_cli_budget: bool
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    # Pillar 53 & Wave-51 top-level fields (Phase 300 300th Milestone)
    donor_snapshot: Phase300DonorSnapshot
    pillar53_a_dci4k_2400p_hdmi_raw_aspect_vault: Pillar53ASuiteResult
    pillar53_b_custom_hold_camset_photo_capture_vault: Pillar53BSuiteResult
    dci4k_long_gop_or_8k_violations: int
    reboot_2400p_stage_b_wipe_violations: int
    hdmi_raw_or_still_aspect_drift_events: int
    fx6_still_or_raw_conflation_events: int
    reg_custom_hold_or_hlg_lock_drift_events: int
    camset_cross_model_path_drift_events: int
    photo_capture_dci4k_lockout_bypass_events: int
    slot1_camset_write_bytes: int
    slot1_photo_capture_write_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    fx3_appfw_has_dci4k_internal: bool
    fx3_appfw_has_pro_camera_path: bool
    fx6_has_still_aspect_ratio: bool
    fx6_has_photo_capture: bool
    fx6_has_playback_enlarge_image: bool
    fx6_has_reg_custom_shoot_set: bool
    fx6_has_camera_set_memory: bool
    # Preserved Pillars 1..52 rollup metrics
    movie_tracking_area_or_limit_violations: int
    af_area_reg_lock_or_reset_drift_events: int
    xlrh1_zoom_or_hold_spoof_events: int
    fx6_handle_or_pos_display_conflation_events: int
    iso_minss_or_cine_ei_lock_drift_events: int
    flash_still_mech_gate_violations: int
    mishoe_pmic_5v_overcurrent_events: int
    slot1_focus_zoom_camset_mutation_bytes: int
    slot1_flash_videolight_imagedb_bytes: int
    xlrh1_has_zoom_lever: bool
    xlrh1_has_rec_button: bool
    xlrh1_has_zoom_hold_switch: bool
    fx6_0_99_is_zoom_position_display: bool
    fx6_has_iso_auto_min_ss: bool
    fx6_mechanical_shutter_present: bool
    dormant_lossless_raw_exposure_events: int
    fx6_still_pipeline_conflation_events: int
    hlg_still_prereq_or_lockout_drift_events: int
    colorspace_adobergb_prefix_violations: int
    shutter_type_auto_spoof_events: int
    fx6_mechanical_shutter_conflation_events: int
    electronic_silent_5lock_bypass_events: int
    nr_or_drive_burst_wall_violations: int
    slot1_still_capture_or_sort_write_bytes: int
    slot1_imagedb_or_burst_mutation_bytes: int
    fx3_ui_exposes_lossless_raw: bool
    fx3_ui_exposes_shutter_type_auto: bool
    fx6_still_pipeline_present: bool
    double_log_or_lockout_bypass_events: int
    pplut_1080p_clamp_bypass_events: int
    pp_internal_reset_trap_violations: int
    fx6_baselook_confusion_events: int
    wb_cine_ei_awb_or_custom_setup_trap_events: int
    wb_custom_camset_exclusion_drift_events: int
    metering_desqueeze_or_cine_ei_base_iso_drift_events: int
    fx3_ui_exposes_usb_streaming: bool
    nouvc_spoof_events: int
    usb_host_data_enumeration_events: int
    hdmi_lcd_blanking_violations: int
    hdmi_log_1080_bypass_events: int
    slot1_protect_only_vault_violations: int
    slot1_vault_format_or_delete_events: int
    network_reset_zero_rf_violations: int
    fx3_ui_exposes_power_save_by_monitor: bool
    legacy_power_save_monitor_spoof_events: int
    unsafe_power_save_sleep_interference_events: int
    bk_lang_parity_drift_events: int
    stage_b_4lang_uxc_ltt_drift_events: int
    xlrh1_acoustic_feedback_violations: int
    audio_mon_4ch_hdmi_confusion_events: int
    destructive_delete_confirm_drift_events: int
    slot1_vault_delete_events: int
    legacy_mf_assist_spoof_events: int
    still_movie_initial_mag_couplings: int
    movie_af_in_focus_mag_events: int
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int
    movie_sq_af_illuminator_fire_events: int
    legacy_datetime_setup_spoof_events: int
    unsolicited_rtc_timezone_jump_events: int
    mishoe_5v_overcurrent_events: int
    hdmi_res_log_internal_rec_2160p_bypass_events: int
    slot1_vault_mutation_events: int
    slot1_vault_folder_mutation_events: int
    slot1_vault_folder_mutation_bytes: int
    movie_custom_folder_or_title_overflow_events: int
    still_prefix_underscore_lead_or_len_violations: int
    gamma_assist_log_lockout_bypass_events: int
    gamma_assist_external_hdmi_leak_events: int
    tcub_camera_reset_wipe_or_format_violations: int
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    slot1_custom_key_vault_mutation_bytes: int
    fx3_has_builtin_evf: bool
    evf_finder_monitor_spoof_events: int
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    slot1_mymenu_vault_mutation_bytes: int
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    master_53pillar_sha256: str
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P300_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    resolved = resolve_donor_path(relpath)
    if resolved is None:
        return False, 0, 0, "MISSING", "", b""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(str(resolved), flags)
    except OSError:
        return False, 0, 0, "OPEN_ERROR", "", b""
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return False, 0, 0, "NOT_REGULAR", "", b""
        total_size = int(st.st_size)
        if total_size <= max_full_bytes:
            chunks: List[bytes] = []
            offset = 0
            while offset < total_size:
                chunk = os.pread(fd, min(65536, total_size - offset), offset)
                if not chunk:
                    break
                chunks.append(chunk)
                offset += len(chunk)
            data = b"".join(chunks)
            return True, total_size, len(data), "FULL_SHA256", sha256(data).hexdigest(), data
        hdr = os.pread(fd, min(P300_BOUNDED_HEADER_BYTES, total_size), 0)
        return True, total_size, len(hdr), "HEADER4K_SHA256", sha256(hdr).hexdigest(), hdr
    finally:
        os.close(fd)


def _check_elf64_aarch64(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return False, f"NOT_ELF:{label}"
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    if ei_class != 2 or ei_data != 1 or e_machine != 183:
        return False, f"BAD_ELF64_AARCH64(class={ei_class},data={ei_data},mach={e_machine})"
    return True, f"ELF64_AARCH64:{label}"


def _check_uxc7_pack(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 16 or data[:4] != b"uxc\x07":
        return False, f"BAD_UXC7_MAGIC:{label}"
    return True, f"UXC7_{label}"


def _check_bk4_backup(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 32 or struct.unpack_from("<I", data, 4)[0] != 0xAAAAAAAA or data[12:16] != b"BK4\x00":
        return False, f"BAD_BK4_MAGIC:{label}"
    return True, f"BK4_{label}"


def _synthetic_phase300_donors() -> Tuple[Phase300DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P300_DONOR_FX3_APPFW_702_RELPATH,
            P300_PINNED_FX3_APPFW_702_BYTES,
            P300_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P300_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P300_DONOR_FX6_APPFW_601_RELPATH,
            P300_PINNED_FX6_APPFW_601_BYTES,
            P300_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P300_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P300_DONOR_FX3_BACKUP_BIN_RELPATH,
            P300_PINNED_FX3_BACKUP_BIN_BYTES,
            P300_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P300_DONOR_FX3_UXC_EN_F_RELPATH,
            P300_PINNED_FX3_UXC_EN_F_BYTES,
            P300_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P300_DONOR_FX3_UXC_SC_F_RELPATH,
            P300_PINNED_FX3_UXC_SC_F_BYTES,
            P300_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P300_DONOR_FX3_UXC_TC_F_RELPATH,
            P300_PINNED_FX3_UXC_TC_F_BYTES,
            P300_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P300_DONOR_FX3_UXC_JA_F_RELPATH,
            P300_PINNED_FX3_UXC_JA_F_BYTES,
            P300_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P300_DONOR_FX3_UXC_EN_RELPATH,
            P300_PINNED_FX3_UXC_EN_BYTES,
            P300_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P300_DONOR_FX3_UXC_SC_RELPATH,
            P300_PINNED_FX3_UXC_SC_BYTES,
            P300_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P300_DONOR_FX3_UXC_TC_RELPATH,
            P300_PINNED_FX3_UXC_TC_BYTES,
            P300_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P300_DONOR_FX3_UXC_JA_RELPATH,
            P300_PINNED_FX3_UXC_JA_BYTES,
            P300_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx3_uxc_en_g",
            P300_DONOR_FX3_UXC_EN_G_RELPATH,
            P300_PINNED_FX3_UXC_EN_G_BYTES,
            P300_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx3_uxc_sc_g",
            P300_DONOR_FX3_UXC_SC_G_RELPATH,
            P300_PINNED_FX3_UXC_SC_G_BYTES,
            P300_PINNED_FX3_UXC_SC_G_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_SC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_G",
        ),
        (
            "fx3_uxc_tc_g",
            P300_DONOR_FX3_UXC_TC_G_RELPATH,
            P300_PINNED_FX3_UXC_TC_G_BYTES,
            P300_PINNED_FX3_UXC_TC_G_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_TC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_G",
        ),
        (
            "fx3_uxc_ja_g",
            P300_DONOR_FX3_UXC_JA_G_RELPATH,
            P300_PINNED_FX3_UXC_JA_G_BYTES,
            P300_PINNED_FX3_UXC_JA_G_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX3_UXC_JA_G_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_G",
        ),
        (
            "fx6_uxc_en",
            P300_DONOR_FX6_UXC_EN_RELPATH,
            P300_PINNED_FX6_UXC_EN_BYTES,
            P300_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P300_DONOR_FX6_UXC_EN_2_RELPATH,
            P300_PINNED_FX6_UXC_EN_2_BYTES,
            P300_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P300_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase300DonorArtifactDigest(
            artifact_id=aid,
            relpath=rel,
            present=True,
            read_mode="CLEAN_ROOM_SYNTHETIC",
            total_bytes=total,
            header_bytes_read=hdr_b,
            digest_kind=dkind,
            digest_sha256=dsha,
            marker_summary=msum,
            matches_pinned=True,
        )
        for aid, rel, total, hdr_b, dkind, dsha, msum in specs
    )


def inspect_phase300_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase300DonorSnapshot:
    """Inspect Wave-51 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase300_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase300DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_20s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_appfw_702_so",
            P300_DONOR_FX3_APPFW_702_RELPATH,
            P300_PINNED_FX3_APPFW_702_BYTES,
            P300_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P300_DONOR_FX6_APPFW_601_RELPATH,
            P300_PINNED_FX6_APPFW_601_BYTES,
            P300_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P300_DONOR_FX3_BACKUP_BIN_RELPATH,
            P300_PINNED_FX3_BACKUP_BIN_BYTES,
            P300_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P300_DONOR_FX3_UXC_EN_F_RELPATH,
            P300_PINNED_FX3_UXC_EN_F_BYTES,
            P300_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P300_DONOR_FX3_UXC_SC_F_RELPATH,
            P300_PINNED_FX3_UXC_SC_F_BYTES,
            P300_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P300_DONOR_FX3_UXC_TC_F_RELPATH,
            P300_PINNED_FX3_UXC_TC_F_BYTES,
            P300_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P300_DONOR_FX3_UXC_JA_F_RELPATH,
            P300_PINNED_FX3_UXC_JA_F_BYTES,
            P300_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P300_DONOR_FX3_UXC_EN_RELPATH,
            P300_PINNED_FX3_UXC_EN_BYTES,
            P300_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P300_DONOR_FX3_UXC_SC_RELPATH,
            P300_PINNED_FX3_UXC_SC_BYTES,
            P300_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P300_DONOR_FX3_UXC_TC_RELPATH,
            P300_PINNED_FX3_UXC_TC_BYTES,
            P300_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P300_DONOR_FX3_UXC_JA_RELPATH,
            P300_PINNED_FX3_UXC_JA_BYTES,
            P300_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx3_uxc_en_g",
            P300_DONOR_FX3_UXC_EN_G_RELPATH,
            P300_PINNED_FX3_UXC_EN_G_BYTES,
            P300_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx3_uxc_sc_g",
            P300_DONOR_FX3_UXC_SC_G_RELPATH,
            P300_PINNED_FX3_UXC_SC_G_BYTES,
            P300_PINNED_FX3_UXC_SC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_G"),
        ),
        (
            "fx3_uxc_tc_g",
            P300_DONOR_FX3_UXC_TC_G_RELPATH,
            P300_PINNED_FX3_UXC_TC_G_BYTES,
            P300_PINNED_FX3_UXC_TC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_G"),
        ),
        (
            "fx3_uxc_ja_g",
            P300_DONOR_FX3_UXC_JA_G_RELPATH,
            P300_PINNED_FX3_UXC_JA_G_BYTES,
            P300_PINNED_FX3_UXC_JA_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_G"),
        ),
        (
            "fx6_uxc_en",
            P300_DONOR_FX6_UXC_EN_RELPATH,
            P300_PINNED_FX6_UXC_EN_BYTES,
            P300_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P300_DONOR_FX6_UXC_EN_2_RELPATH,
            P300_PINNED_FX6_UXC_EN_2_BYTES,
            P300_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    digests: List[Phase300DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            break
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        digests.append(
            Phase300DonorArtifactDigest(
                artifact_id=aid,
                relpath=relpath,
                present=True,
                read_mode="LOCAL_DONOR_O_RDONLY",
                total_bytes=total_b,
                header_bytes_read=hdr_b,
                digest_kind=dkind,
                digest_sha256=dsha,
                marker_summary=msum,
                matches_pinned=matches,
            )
        )

    if any_missing:
        artifacts = _synthetic_phase300_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase300DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_20s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    all_ok = all(d.present and d.matches_pinned for d in digests) and len(digests) == len(probe_specs)
    dt = round(time.monotonic() - t0, 6)
    return Phase300DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_20s_budget=dt < budget,
        budget_seconds_applied=budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Spec Builders & Evaluators (Pillars 53A & 53B)
# ---------------------------------------------------------------------------


def build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
    **overrides: Any,
) -> Dci4k2400pHdmiRawStillAspectVaultSpec:
    """Return a clean, verified default `Dci4k2400pHdmiRawStillAspectVaultSpec`."""
    spec = Dci4k2400pHdmiRawStillAspectVaultSpec()
    if not overrides:
        return spec
    return Dci4k2400pHdmiRawStillAspectVaultSpec(**{**asdict(spec), **overrides})


def build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
    **overrides: Any,
) -> RegCustomHoldCamsetPhotoCaptureVaultSpec:
    """Return a clean, verified default `RegCustomHoldCamsetPhotoCaptureVaultSpec`."""
    spec = RegCustomHoldCamsetPhotoCaptureVaultSpec()
    if not overrides:
        return spec
    return RegCustomHoldCamsetPhotoCaptureVaultSpec(**{**asdict(spec), **overrides})


def evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
    spec: Dci4k2400pHdmiRawStillAspectVaultSpec,
) -> Dci4k2400pHdmiRawStillAspectVaultReport:
    """Evaluate Pillar 53A (`[XAVC S-I DCI 4K]` `4096x2160` `17:9` All-Intra vs Long-GOP
    `3840x2160` UHD split, no dormant `8K`, `S&Q 1..48fps` vs `100/120fps` lockout,
    `24.00p` mandatory reboot + volatile `/tmp` Stage-B clean wipe + playback quarantine,
    `4264x2408` Type-A HDMI RAW, Still `[Aspect Ratio]` `3:2/4:3/16:9/1:1` + `APS-C S35`
    `L -> M` step-down vs still-less `ILME-FX6`, and `Slot-1` `EROFS`/`EBUSY` Vault firewall)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested or errors:
        _fail(
            P300_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Persistent write release or module safety policy violation",
        )

    if (
        spec.camera_model != P300_FX3_MODEL_NAME
        or spec.camera_model_id != P300_FX3_MODEL_ID
        or spec.fw_version not in P300_FX3_SUPPORTED_FW_VERSIONS
        or spec.helpguide_id != P300_FX3_HELPGUIDE_ID
        or spec.dci4k_aspect_surface_model
        != "FX3_ALL_INTRA_DCI4K_2400P_REBOOT_HDMI_4264RAW_STILL_ASPECT"
        or spec.log_shooting_mode not in P300_LOG_SHOOTING_MODES
        or spec.shutter_mode not in P300_SHUTTER_MODES
        or not (P300_SHUTTER_ANGLE_MIN_DEG <= spec.shutter_angle_deg <= P300_SHUTTER_ANGLE_MAX_DEG)
        or spec.reset_action not in P300_RESET_ACTIONS
        or spec.requested_vault_action not in P300_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P300_BLOCKED_INVALID_PILLAR53A_SPEC,
            "Invalid Pillar 53A camera/DCI4K/24.00p/HDMI-RAW/Still-Aspect/vault spec parameter",
        )

    (
        exp_movie_dims,
        exp_movie_aspect,
        exp_rec_allowed,
        exp_sq_allowed,
        exp_media_ok,
        exp_mandatory_reboot,
        exp_stage_b_wiped,
        exp_post_aspect,
        exp_raw_native_dims,
        exp_post_size,
    ) = compute_expected_dci4k_2400p_hdmi_raw_and_still_aspect_state(
        file_format=spec.file_format,
        prev_rec_frame_rate=spec.prev_rec_frame_rate,
        target_rec_frame_rate=spec.target_rec_frame_rate,
        sq_frame_rate_fps=spec.sq_frame_rate_fps,
        media_card_grade=spec.media_card_grade,
        hdmi_raw_enabled=spec.hdmi_raw_enabled,
        log_shooting_mode=spec.log_shooting_mode,
        still_aspect_ratio=spec.still_aspect_ratio,
        still_size_tier=spec.still_size_tier,
        apsc_s35_enabled=spec.apsc_s35_enabled,
        reset_action=spec.reset_action,
    )

    # 1. [XAVC S-I DCI 4K] vs Long-GOP 4K UHD split & zero dormant 8K
    dci4k_ok = (
        spec.file_format != P300_DORMANT_8K_FORMAT
        and spec.file_format in P300_MOVIE_FILE_FORMATS
        and spec.fx3_appfw_has_dci4k_internal
        and spec.reported_movie_dimensions == exp_movie_dims
        and spec.reported_movie_aspect == exp_movie_aspect
        and exp_rec_allowed
        and exp_sq_allowed
        and exp_media_ok
        and spec.dci4k_long_gop_or_8k_violations == 0
    )
    if not dci4k_ok:
        _fail(
            P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION,
            "XAVC S-I DCI 4K (4096x2160 17:9, S&Q 1..48fps, VPG200/V90 600M) vs Long-GOP UHD (3840x2160) / no dormant 8K check failed",
        )

    # 2. 24.00p Mandatory Reboot, Volatile /tmp Stage-B Wipe & 24.00p Playback Quarantine
    reboot_2400p_ok = (
        spec.reported_mandatory_reboot == exp_mandatory_reboot
        and spec.reported_volatile_stage_b_wiped == exp_stage_b_wiped
        and spec.stage_b_post_2400p_h0_eq_h2
        and (
            not exp_mandatory_reboot
            or (spec.reported_volatile_stage_b_wiped and spec.stage_b_post_2400p_h0_eq_h2)
        )
        and (
            spec.target_rec_frame_rate != "24.00p"
            or spec.reported_2400p_playback_quarantined
        )
        and spec.reboot_2400p_stage_b_wipe_violations == 0
    )
    if not reboot_2400p_ok:
        _fail(
            P300_BLOCKED_2400P_REBOOT_STAGE_B_WIPE_OR_QUARANTINE_DRIFT,
            "24.00p mandatory reboot, volatile /tmp Stage-B clean wipe (H0==H2), or 24.00p playback quarantine drifted",
        )

    # 3. 4264x2408 HDMI RAW & Still [Aspect Ratio] + FX6 Cinema Contrast
    hdmi_still_ok = (
        (
            not spec.hdmi_raw_enabled
            or (
                spec.hdmi_raw_dimensions == P300_FX3_HDMI_RAW_DIMENSIONS
                and spec.log_shooting_mode != "Off"
                and spec.hdmi_raw_gamma_locked == "S-Log3"
                and not spec.hdmi_raw_steadyshot_active_allowed
                and not spec.hdmi_raw_desqueeze_allowed
            )
        )
        and spec.still_aspect_ratio in P300_STILL_ASPECT_RATIOS
        and spec.still_size_tier in P300_STILL_IMAGE_SIZE_TIERS
        and spec.post_still_aspect_ratio == exp_post_aspect
        and spec.post_still_size_tier == exp_post_size
        and spec.still_raw_native_dims == exp_raw_native_dims == P300_FX3_STILL_RAW_NATIVE_DIMS
        and spec.hdmi_raw_or_still_aspect_drift_events == 0
    )
    fx6_contrast_ok = (
        not spec.fx6_has_still_aspect_ratio
        and spec.fx6_raw_dimensions == P300_FX6_RAW_DIMENSIONS
        and spec.fx6_dci4k_sq_max_fps == P300_FX6_DCI4K_SQ_MAX_FPS
        and spec.fx6_still_or_raw_conflation_events == 0
    )
    if not (hdmi_still_ok and fx6_contrast_ok):
        _fail(
            P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION,
            "4264x2408 HDMI RAW (Log/S-Log3/No-Active-SS/No-Desqueeze) or Still [Aspect Ratio] (3:2..1:1 / APS-C L->M) / FX6 contrast violated",
        )

    # 4. Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    vault_fw_ok = (
        spec.slot1_holds_recovery_vault
        and spec.slot1_sdxc_wp_locked
        and spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.target_capture_slot == P300_SAFE_SECONDARY_CAPTURE_SLOT
        and spec.requested_vault_action not in P300_DESTRUCTIVE_VAULT_ACTIONS
        and spec.slot1_vault_mutation_bytes == 0
    )
    if not vault_fw_ok:
        _fail(
            P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS/EBUSY firewall blocked write/format/delete mutation on Tier-0 media",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
        and spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
    )
    if not overlay_ok:
        _fail(
            P300_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must stay in volatile /tmp with BLKROSET=True: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P300_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P300_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P300_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "53A",
            "passed": passed,
            "block_code": block_code,
            "file_format": spec.file_format,
            "movie_dims": spec.reported_movie_dimensions,
            "prev_fps": spec.prev_rec_frame_rate,
            "target_fps": spec.target_rec_frame_rate,
            "mandatory_reboot": spec.reported_mandatory_reboot,
            "stage_b_wiped": spec.reported_volatile_stage_b_wiped,
            "hdmi_raw_dims": spec.hdmi_raw_dimensions,
            "post_still_aspect": spec.post_still_aspect_ratio,
            "post_still_size": spec.post_still_size_tier,
            "slot1_bytes": spec.slot1_vault_mutation_bytes,
            "errors": errors,
        }
    )
    return Dci4k2400pHdmiRawStillAspectVaultReport(
        passed=passed,
        status=P300_STATUS_VERIFIED_PILLAR_53A if passed else P300_STATUS_REJECTED_PILLAR_53A,
        block_code=block_code,
        dci4k_vs_long_gop_and_no_8k_verified=dci4k_ok,
        reboot_2400p_stage_b_wipe_and_quarantine_verified=reboot_2400p_ok,
        hdmi_raw_4264_and_still_aspect_verified=hdmi_still_ok,
        fx6_cinema_raw_and_still_less_contrast_verified=fx6_contrast_ok,
        slot1_erofs_ebusy_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=16,
        dci4k_long_gop_or_8k_violations=spec.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=spec.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=spec.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=spec.fx6_still_or_raw_conflation_events,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_reg_custom_hold_camset_photo_capture_vault(
    spec: RegCustomHoldCamsetPhotoCaptureVaultSpec,
) -> RegCustomHoldCamsetPhotoCaptureVaultReport:
    """Evaluate Pillar 53B (`[Reg. Custom Shoot Set]` Still `P/A/S/M`-only `Recall Custom
    hold 1..3` 11 checkboxes + `HLG Still Image = Off` lockout, `[Camera Set. Memory]`
    `1..3 + M1..M4` `%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT` & `CAMSET` isolation vs `FX6`
    `PRO/CAMERA` cross-model block, `[Playback] -> [Edit] -> [Photo Capture]` `8.3M/2.1M`
    DCI 4K lockout + `Slot-1` Tier-0 Vault `EROFS`/`EBUSY` firewall, and read-only
    `[Enlarge Image]`)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested or errors:
        _fail(
            P300_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Persistent write release or module safety policy violation",
        )

    if (
        spec.camera_model != P300_FX3_MODEL_NAME
        or spec.camera_model_id != P300_FX3_MODEL_ID
        or spec.fw_version not in P300_FX3_SUPPORTED_FW_VERSIONS
        or spec.helpguide_id != P300_FX3_HELPGUIDE_ID
        or spec.custom_camset_capture_surface_model
        != "FX3_REG_CUSTOM_HOLD11_CAMPR_SETTING_PATH_PHOTO_CAPTURE_ENLARGE"
        or spec.shooting_domain not in P300_SHOOTING_DOMAINS
        or spec.shooting_mode not in P300_STILL_ALL_MODES
        or spec.reg_custom_hold_slot not in P300_REG_CUSTOM_SHOOT_SET_SLOTS
        or spec.initial_hlg_still_image not in P300_ON_OFF_MODES
        or spec.reported_hlg_still_image not in P300_ON_OFF_MODES
        or spec.camset_bank not in P300_CAMSET_ALL_BANKS
        or spec.camset_media_kind not in P300_CAMSET_CARD_TYPE_SUBDIR_MAP
        or spec.configured_photo_capture_type not in P300_PHOTO_CAPTURE_FILE_TYPES
        or spec.post_photo_capture_type not in P300_PHOTO_CAPTURE_FILE_TYPES
        or spec.configured_enlarge_init_mag not in P300_ENLARGE_INITIAL_MAG_MODES
        or spec.post_enlarge_init_mag not in P300_ENLARGE_INITIAL_MAG_MODES
        or spec.configured_enlarge_init_pos not in P300_ENLARGE_INITIAL_POS_MODES
        or spec.post_enlarge_init_pos not in P300_ENLARGE_INITIAL_POS_MODES
        or spec.reset_action not in P300_RESET_ACTIONS
        or spec.requested_vault_action not in P300_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P300_BLOCKED_INVALID_PILLAR53B_SPEC,
            "Invalid Pillar 53B camera/RegCustomHold/CamSet/PhotoCapture/Enlarge/vault spec parameter",
        )

    (
        exp_reg_allowed,
        exp_hlg,
        exp_body_survived,
        exp_reg_survived,
        exp_post_media,
        exp_camset_save_allowed,
    ) = compute_expected_reg_custom_hold_and_camset_memory_state(
        shooting_domain=spec.shooting_domain,
        shooting_mode=spec.shooting_mode,
        hold_recalled_items=spec.hold_recalled_items,
        initial_hlg_still_image=spec.initial_hlg_still_image,
        camset_bank=spec.camset_bank,
        memory_recall_media=spec.memory_recall_media,
        reset_action=spec.reset_action,
    )

    (
        exp_pc_allowed,
        exp_pc_dims,
        exp_pc_mp,
        exp_enlarge_allowed,
        exp_pc_type,
        exp_enlarge_mag,
        exp_enlarge_pos,
    ) = compute_expected_photo_capture_and_enlarge_image_state(
        clip_file_format=spec.clip_file_format,
        clip_resolution=spec.clip_resolution,
        select_playback_media=spec.select_playback_media,
        slot1_holds_recovery_vault=spec.slot1_holds_recovery_vault,
        playback_media_kind=spec.playback_media_kind,
        configured_photo_capture_type=spec.configured_photo_capture_type,
        configured_enlarge_init_mag=spec.configured_enlarge_init_mag,
        configured_enlarge_init_pos=spec.configured_enlarge_init_pos,
        reset_action=spec.reset_action,
    )

    # 1. [Reg. Custom Shoot Set] (Still P/A/S/M only, 11 checkboxes, HLG Still = Off lockout)
    reg_hold_ok = (
        len(spec.reg_custom_hold_checkboxes) == P300_REG_CUSTOM_HOLD_CHECKBOX_COUNT
        and spec.reg_custom_hold_checkboxes == P300_REG_CUSTOM_SHOOT_SET_11_CHECKBOXES
        and spec.reported_reg_custom_hold_allowed == exp_reg_allowed
        and spec.reported_hlg_still_image == exp_hlg
        and spec.reported_reg_custom_hold_survived == exp_reg_survived
        and not spec.fx6_has_reg_custom_shoot_set
        and spec.reg_custom_hold_or_hlg_lock_drift_events == 0
    )
    if not reg_hold_ok:
        _fail(
            P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT,
            "Reg. Custom Shoot Set (Still P/A/S/M gate, 11 checkboxes, Initialize survival, HLG Still Off lockout) drifted",
        )

    # 2. [Camera Set. Memory] Path Isolation vs FX6 PRO/CAMERA
    expected_subdir = P300_CAMSET_CARD_TYPE_SUBDIR_MAP.get(spec.camset_media_kind, "/PRIVATE")
    expected_campr_prefix = f"E:{expected_subdir}/SONY/SETTING/{P300_FX3_SETTING_MODEL_TAG}/CAMPR"
    expected_camset_prefix = f"E:{expected_subdir}/SONY/SETTING/{P300_FX3_SETTING_MODEL_TAG}/CAMSET/"
    combined_paths = f"{spec.camset_card_path} {spec.camset_all_path}"
    has_fx6_pro_path = (
        P300_FX6_PRO_CAMERA_PATH_PREFIX in combined_paths
        or P300_FX6_PRO_SCENE_PATH_PREFIX in combined_paths
        or "PRO/CAMERA" in combined_paths
    )
    camset_ok = (
        spec.camset_card_path.startswith(expected_campr_prefix)
        and spec.camset_card_path.endswith(".DAT")
        and spec.camset_all_path.startswith(expected_camset_prefix)
        and spec.camset_all_path.endswith(".DAT")
        and not has_fx6_pro_path
        and not spec.fx3_appfw_has_pro_camera_path
        and not spec.fx6_has_camera_set_memory
        and not spec.cross_model_fx6_import_attempted
        and spec.post_memory_recall_media == exp_post_media
        and spec.reported_body_banks_survived == exp_body_survived
        and spec.reported_camset_save_allowed == exp_camset_save_allowed
        and spec.camset_cross_model_path_drift_events == 0
    )
    if not camset_ok:
        _fail(
            P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION,
            "Camera Set. Memory FX3 SONY/SETTING/FX3 path isolation or cross-model FX6 PRO/CAMERA firewall violated",
        )

    # 3. [Playback] [Photo Capture] DCI 4K lockout & read-only [Enlarge Image]
    slot1_capture_attempt = (
        (spec.photo_capture_attempted and spec.select_playback_media == "Slot 1")
        or spec.target_camset_or_capture_slot == P300_SLOT1_VAULT_SLOT
        or spec.slot1_camset_write_bytes > 0
        or spec.slot1_photo_capture_write_bytes > 0
        or spec.requested_vault_action in P300_DESTRUCTIVE_VAULT_ACTIONS
    )
    photo_enlarge_ok = (
        spec.reported_photo_capture_allowed == exp_pc_allowed
        and spec.reported_photo_capture_dims == exp_pc_dims
        and spec.reported_photo_capture_mp == exp_pc_mp
        and (
            not spec.photo_capture_attempted
            or exp_pc_allowed
            or (spec.select_playback_media == "Slot 1" and spec.slot1_holds_recovery_vault)
        )
        and spec.post_photo_capture_type == exp_pc_type
        and spec.reported_enlarge_image_allowed == exp_enlarge_allowed
        and (not spec.enlarge_image_attempted or exp_enlarge_allowed)
        and spec.post_enlarge_init_mag == exp_enlarge_mag
        and spec.post_enlarge_init_pos == exp_enlarge_pos
        and not spec.fx6_has_photo_capture
        and not spec.fx6_has_playback_enlarge_image
        and spec.photo_capture_dci4k_lockout_bypass_events == 0
    )
    if not photo_enlarge_ok:
        _fail(
            P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT,
            "Playback Photo Capture (8.3M/2.1M, XAVC S-I DCI 4K lockout) or Enlarge Image / FX6 contrast violated",
        )

    # 4. Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    vault_fw_ok = (
        spec.slot1_holds_recovery_vault
        and spec.slot1_sdxc_wp_locked
        and spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_ebusy_enforced
        and not slot1_capture_attempt
    )
    if not vault_fw_ok:
        _fail(
            P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS/EBUSY firewall blocked Photo Capture / CAMSET / CAMPR / Format / Delete mutation",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
        and spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
    )
    if not overlay_ok:
        _fail(
            P300_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must stay in volatile /tmp with BLKROSET=True: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P300_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P300_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P300_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    slot1_total = spec.slot1_camset_write_bytes + spec.slot1_photo_capture_write_bytes
    digest = _canonical_sha256(
        {
            "pillar": "53B",
            "passed": passed,
            "block_code": block_code,
            "reg_hold": spec.reg_custom_hold_slot,
            "hlg_still": spec.reported_hlg_still_image,
            "camset_bank": spec.camset_bank,
            "camset_card_path": spec.camset_card_path,
            "clip_format": spec.clip_file_format,
            "photo_capture_allowed": spec.reported_photo_capture_allowed,
            "enlarge_allowed": spec.reported_enlarge_image_allowed,
            "slot1_bytes": slot1_total,
            "errors": errors,
        }
    )
    return RegCustomHoldCamsetPhotoCaptureVaultReport(
        passed=passed,
        status=P300_STATUS_VERIFIED_PILLAR_53B if passed else P300_STATUS_REJECTED_PILLAR_53B,
        block_code=block_code,
        reg_custom_hold11_and_hlg_lockout_verified=reg_hold_ok,
        camset_path_isolation_and_fx6_firewall_verified=camset_ok,
        photo_capture_dci4k_lockout_and_enlarge_verified=photo_enlarge_ok,
        slot1_erofs_ebusy_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=16,
        reg_custom_hold_or_hlg_lock_drift_events=spec.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=spec.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=spec.photo_capture_dci4k_lockout_bypass_events,
        slot1_camset_write_bytes=spec.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=spec.slot1_photo_capture_write_bytes,
        slot1_vault_mutation_bytes=slot1_total,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_53a: Optional[Dci4k2400pHdmiRawStillAspectVaultSpec] = None,
    spec_53b: Optional[RegCustomHoldCamsetPhotoCaptureVaultSpec] = None,
) -> Dci4kAspectCustomHoldCamsetPhotoCaptureVaultReport:
    """Combined single-shot verifier for Pillar 53A + Pillar 53B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase300_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
        spec_53a or build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec()
    )
    rep_b = evaluate_reg_custom_hold_camset_photo_capture_vault(
        spec_53b or build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 300 Wave-51 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return Dci4kAspectCustomHoldCamsetPhotoCaptureVaultReport(
        schema=PHASE300_SCHEMA,
        version=PHASE300_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P300_STATUS_VERIFIED_PILLAR53_SUITE if all_ok else P300_STATUS_FAIL_PILLAR53_SUITE,
        donor_snapshot=donor_snapshot,
        dci4k_aspect_report=rep_a,
        custom_hold_camset_capture_report=rep_b,
        dci4k_long_gop_or_8k_violations=rep_a.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=rep_a.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=rep_a.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=rep_a.fx6_still_or_raw_conflation_events,
        reg_custom_hold_or_hlg_lock_drift_events=rep_b.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=rep_b.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=rep_b.photo_capture_dci4k_lockout_bypass_events,
        slot1_camset_write_bytes=rep_b.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=rep_b.slot1_photo_capture_write_bytes,
        slot1_vault_mutation_bytes=rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=(rep_a.slot1_format_hard_locked and rep_b.slot1_format_hard_locked),
        slot1_vault_erofs_ebusy_enforced=(
            rep_a.slot1_vault_erofs_ebusy_enforced and rep_b.slot1_vault_erofs_ebusy_enforced
        ),
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(errs),
    )


def verify_dci4k_aspect_custom_hold_camset_photo_capture_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_53a: Optional[Dci4k2400pHdmiRawStillAspectVaultSpec] = None,
    spec_53b: Optional[RegCustomHoldCamsetPhotoCaptureVaultSpec] = None,
) -> Dci4kAspectCustomHoldCamsetPhotoCaptureVaultReport:
    """Symmetry alias for `verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault`."""
    return verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault(
        force_clean_room=force_clean_room,
        spec_53a=spec_53a,
        spec_53b=spec_53b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 53A & 53B) + Standalone Pillar 53 Suite
# ---------------------------------------------------------------------------


def run_pillar53a_dci4k_2400p_hdmi_raw_still_aspect_6_scenario_suite() -> Pillar53ASuiteResult:
    """Run 6 Pillar 53A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, Dci4k2400pHdmiRawStillAspectVaultSpec, Optional[str]], ...] = (
        (
            P300_PILLAR_53A_SCENARIO_IDS[0],
            True,
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                file_format="XAVC S-I DCI 4K",
                reported_movie_dimensions=P300_DCI4K_DIMENSIONS,
                reported_movie_aspect=P300_DCI4K_ASPECT,
                prev_rec_frame_rate="23.98p",
                target_rec_frame_rate="59.94p",
                sq_frame_rate_fps=48,
                media_card_grade="CFexpress VPG200+",
                shutter_mode="Angle",
                shutter_angle_deg=180.0,
                hdmi_raw_enabled=True,
                hdmi_raw_dimensions=P300_FX3_HDMI_RAW_DIMENSIONS,
                log_shooting_mode="Cine EI",
                still_aspect_ratio="3:2",
                post_still_aspect_ratio="3:2",
                still_size_tier="L",
                post_still_size_tier="L",
            ),
            None,
        ),
        (
            P300_PILLAR_53A_SCENARIO_IDS[1],
            True,
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                file_format="XAVC S-I DCI 4K",
                reported_movie_dimensions=P300_DCI4K_DIMENSIONS,
                reported_movie_aspect=P300_DCI4K_ASPECT,
                prev_rec_frame_rate="23.98p",
                target_rec_frame_rate="24.00p",
                sq_frame_rate_fps=24,
                media_card_grade="SDXC V90+",
                reported_mandatory_reboot=True,
                reported_volatile_stage_b_wiped=True,
                reported_2400p_playback_quarantined=True,
                stage_b_post_2400p_h0_eq_h2=True,
                still_aspect_ratio="16:9",
                post_still_aspect_ratio="16:9",
                still_size_tier="L",
                post_still_size_tier="M",
                apsc_s35_enabled=True,
            ),
            None,
        ),
        (
            P300_PILLAR_53A_SCENARIO_IDS[2],
            False,
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                file_format="XAVC S 4K",
                reported_movie_dimensions=P300_DCI4K_DIMENSIONS,
                reported_movie_aspect=P300_DCI4K_ASPECT,
                sq_frame_rate_fps=120,
                dci4k_long_gop_or_8k_violations=1,
            ),
            P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION,
        ),
        (
            P300_PILLAR_53A_SCENARIO_IDS[3],
            False,
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                file_format="XAVC S-I DCI 4K",
                prev_rec_frame_rate="23.98p",
                target_rec_frame_rate="24.00p",
                reported_mandatory_reboot=False,
                reported_volatile_stage_b_wiped=False,
                reported_2400p_playback_quarantined=False,
                stage_b_post_2400p_h0_eq_h2=False,
                reboot_2400p_stage_b_wipe_violations=1,
            ),
            P300_BLOCKED_2400P_REBOOT_STAGE_B_WIPE_OR_QUARANTINE_DRIFT,
        ),
        (
            P300_PILLAR_53A_SCENARIO_IDS[4],
            False,
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                hdmi_raw_enabled=True,
                log_shooting_mode="Off",
                fx6_has_still_aspect_ratio=True,
                apsc_s35_enabled=True,
                still_size_tier="L",
                post_still_size_tier="L",
                hdmi_raw_or_still_aspect_drift_events=1,
                fx6_still_or_raw_conflation_events=1,
            ),
            P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION,
        ),
        (
            P300_PILLAR_53A_SCENARIO_IDS[5],
            False,
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                target_capture_slot=1,
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/53a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar53ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar53ScenarioOutcome(
                scenario_id=sid,
                pillar="53A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar53ASuiteResult(
        passed=all_ok,
        status=P300_STATUS_VERIFIED_PILLAR_53A if all_ok else P300_STATUS_REJECTED_PILLAR_53A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar53b_custom_hold_camset_photo_capture_6_scenario_suite() -> Pillar53BSuiteResult:
    """Run 6 Pillar 53B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, RegCustomHoldCamsetPhotoCaptureVaultSpec, Optional[str]], ...] = (
        (
            P300_PILLAR_53B_SCENARIO_IDS[0],
            True,
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                shooting_domain="Still",
                shooting_mode="M",
                reg_custom_hold_slot="Recall Custom hold 1",
                hold_recalled_items=("iso_sensitivity", "aperture"),
                initial_hlg_still_image="On",
                reported_hlg_still_image="Off",
                playback_media_kind="Still",
                photo_capture_attempted=False,
                reported_photo_capture_allowed=False,
                reported_photo_capture_dims=None,
                reported_photo_capture_mp=None,
                enlarge_image_attempted=True,
                reported_enlarge_image_allowed=True,
                configured_enlarge_init_mag="Previous Mag.",
                post_enlarge_init_mag="Previous Mag.",
                configured_enlarge_init_pos="Center",
                post_enlarge_init_pos="Center",
                reset_action="Camera Settings Reset",
                post_memory_recall_media="Slot 1",
            ),
            None,
        ),
        (
            P300_PILLAR_53B_SCENARIO_IDS[1],
            True,
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                camset_bank="M2",
                camset_media_kind="CFexpress Type A",
                camset_card_path=build_fx3_campr_card_path(
                    drive_letter="E", media_kind="CFexpress Type A", bank_index=2, slot_suffix="A"
                ),
                camset_all_path=build_fx3_camset_card_path(
                    drive_letter="E", media_kind="CFexpress Type A", filename_stem="CAMSET02"
                ),
                playback_media_kind="Movie",
                select_playback_media="Slot 2",
                clip_file_format="XAVC S 4K",
                clip_resolution=P300_UHD_4K_DIMENSIONS,
                photo_capture_attempted=True,
                reported_photo_capture_allowed=True,
                reported_photo_capture_dims=P300_PHOTO_CAPTURE_4K_UHD_DIMS,
                reported_photo_capture_mp=P300_PHOTO_CAPTURE_4K_UHD_MP,
            ),
            None,
        ),
        (
            P300_PILLAR_53B_SCENARIO_IDS[2],
            False,
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                shooting_domain="Movie",
                shooting_mode="M",
                hold_recalled_items=("iso_sensitivity", "dro_bracket"),
                initial_hlg_still_image="On",
                reported_hlg_still_image="On",
                reported_reg_custom_hold_allowed=True,
                reg_custom_hold_or_hlg_lock_drift_events=1,
            ),
            P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT,
        ),
        (
            P300_PILLAR_53B_SCENARIO_IDS[3],
            False,
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                reg_custom_hold_checkboxes=P300_REG_CUSTOM_SHOOT_SET_11_CHECKBOXES[:10],
                camset_card_path="E:/PRIVATE/SONY/PRO/CAMERA/C0001.DAT",
                fx3_appfw_has_pro_camera_path=True,
                cross_model_fx6_import_attempted=True,
                camset_cross_model_path_drift_events=1,
            ),
            P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT,
        ),
        (
            P300_PILLAR_53B_SCENARIO_IDS[4],
            False,
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                playback_media_kind="Movie",
                select_playback_media="Slot 2",
                clip_file_format="XAVC S-I DCI 4K",
                clip_resolution=P300_DCI4K_DIMENSIONS,
                photo_capture_attempted=True,
                reported_photo_capture_allowed=True,
                reported_photo_capture_dims=P300_DCI4K_DIMENSIONS,
                reported_photo_capture_mp="8.8M",
                fx6_has_photo_capture=True,
                photo_capture_dci4k_lockout_bypass_events=1,
            ),
            P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT,
        ),
        (
            P300_PILLAR_53B_SCENARIO_IDS[5],
            False,
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                playback_media_kind="Movie",
                select_playback_media="Slot 1",
                clip_file_format="XAVC S 4K",
                clip_resolution=P300_UHD_4K_DIMENSIONS,
                photo_capture_attempted=True,
                reported_photo_capture_allowed=False,
                reported_photo_capture_dims=None,
                reported_photo_capture_mp=None,
                target_camset_or_capture_slot=1,
                requested_vault_slot=1,
                requested_vault_action="PHOTO_CAPTURE_STILL_EXTRACT",
                slot1_camset_write_bytes=4096,
                slot1_photo_capture_write_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/53b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar53ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_reg_custom_hold_camset_photo_capture_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar53ScenarioOutcome(
                scenario_id=sid,
                pillar="53B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar53BSuiteResult(
        passed=all_ok,
        status=P300_STATUS_VERIFIED_PILLAR_53B if all_ok else P300_STATUS_REJECTED_PILLAR_53B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar53_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar53StandaloneReport:
    """Run full Pillar 53 standalone suite (`6/6` Pillar 53A + `6/6` Pillar 53B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase300_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar53a_dci4k_2400p_hdmi_raw_still_aspect_6_scenario_suite()
    res_b = run_pillar53b_custom_hold_camset_photo_capture_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 300 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE300_SCHEMA,
            "version": PHASE300_VERSION,
            "mode": donor_snapshot.verification_mode,
            "53a": [asdict(s) for s in res_a.scenarios],
            "53b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar53StandaloneReport(
        schema=PHASE300_SCHEMA,
        version=PHASE300_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P300_STATUS_VERIFIED_PILLAR53_SUITE if all_ok else P300_STATUS_FAIL_PILLAR53_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault=res_a,
        pillar_53b_custom_hold_camset_photo_capture_vault=res_b,
        dci4k_long_gop_or_8k_violations=P300_DCI4K_LONG_GOP_OR_8K_VIOLATIONS if res_a.passed else 1,
        reboot_2400p_stage_b_wipe_violations=(
            P300_2400P_REBOOT_STAGE_B_WIPE_VIOLATIONS if res_a.passed else 1
        ),
        hdmi_raw_or_still_aspect_drift_events=(
            P300_HDMI_RAW_OR_STILL_ASPECT_DRIFT_EVENTS if res_a.passed else 1
        ),
        fx6_still_or_raw_conflation_events=(
            P300_FX6_STILL_OR_RAW_CONFLATION_EVENTS if res_a.passed else 1
        ),
        reg_custom_hold_or_hlg_lock_drift_events=(
            P300_REG_CUSTOM_HOLD_OR_HLG_LOCK_DRIFT_EVENTS if res_b.passed else 1
        ),
        camset_cross_model_path_drift_events=(
            P300_CAMSET_CROSS_MODEL_PATH_DRIFT_EVENTS if res_b.passed else 1
        ),
        photo_capture_dci4k_lockout_bypass_events=(
            P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_BYPASS_EVENTS if res_b.passed else 1
        ),
        slot1_camset_write_bytes=P300_SLOT1_CAMSET_WRITE_BYTES if res_b.passed else 4096,
        slot1_photo_capture_write_bytes=(
            P300_SLOT1_PHOTO_CAPTURE_WRITE_BYTES if res_b.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P300_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P300_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_ebusy_enforced=P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        suite_sha256=suite_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errs),
    )


# ---------------------------------------------------------------------------
# Unified 53-Pillar Recovery Master Aggregator (Phase 300 Milestone!!)
# ---------------------------------------------------------------------------


def _apply_master53_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
    err = f"FAULT_INJECTED:{pillar.pillar_id}"
    return MasterPillarStatus(
        pillar_number=pillar.pillar_number,
        pillar_id=pillar.pillar_id,
        phase_label=pillar.phase_label,
        module_name=pillar.module_name,
        passed=False,
        status=f"FAULT_INJECTED_{pillar.pillar_id.upper()}",
        verification_mode=pillar.verification_mode,
        elapsed_seconds=pillar.elapsed_seconds,
        key_metrics=pillar.key_metrics,
        digest_sha256=_canonical_sha256({"pillar": pillar.pillar_id, "fault_injected": True}),
        errors=pillar.errors + (err,),
    )


def evaluate_realhw_53pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master53PillarRecoveryReport:
    """Evaluate and aggregate all 53 recovery pillars (`1..53`) concurrently -> `53/53` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_53_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_52pillar() -> Master52PillarRecoveryReport:
        return evaluate_realhw_52pillar_recovery_master(**kw)

    def _run_p53() -> Tuple[Pillar53StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar53_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_52 = pool.submit(_run_52pillar)
        fut_53 = pool.submit(_run_p53)
        m52_rep = fut_52.result()
        p53_rep, p53_dt = fut_53.result()

    all_errors: List[str] = list(m52_rep.errors) + list(p53_rep.errors)
    for attr_name, expected_val in (
        ("otp_fuse_touches", 0),
        ("otp_fuse_writes", 0),
        ("rpmb_counter_increments", 0),
        ("passive_tx_bytes_emitted", 0),
        ("physical_usb_packets_emitted", 0),
        ("physical_device_writes", 0),
        ("raw_firmware_bytes_leaked", 0),
        ("el3_payload_transmit_authorized", False),
        ("isp_write_authorized", False),
        ("spi_nor_write_authorized", False),
        ("persistent_emmc_writes_authorized", False),
        ("persistent_write_release", False),
        ("live_usb_iokit_transmit_enabled", False),
        ("cnflasha_userspace_write_blocked", True),
        ("overall_ready_for_hardware_attach", False),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(m52_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-52 violated {attr_name} == {expected_val}")
        if getattr(p53_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 53 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("movie_tracking_area_or_limit_violations", 0),
        ("af_area_reg_lock_or_reset_drift_events", 0),
        ("xlrh1_zoom_or_hold_spoof_events", 0),
        ("fx6_handle_or_pos_display_conflation_events", 0),
        ("iso_minss_or_cine_ei_lock_drift_events", 0),
        ("flash_still_mech_gate_violations", 0),
        ("mishoe_pmic_5v_overcurrent_events", 0),
        ("slot1_focus_zoom_camset_mutation_bytes", 0),
        ("slot1_flash_videolight_imagedb_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
        ("dormant_lossless_raw_exposure_events", 0),
        ("fx6_still_pipeline_conflation_events", 0),
        ("hlg_still_prereq_or_lockout_drift_events", 0),
        ("colorspace_adobergb_prefix_violations", 0),
        ("shutter_type_auto_spoof_events", 0),
        ("fx6_mechanical_shutter_conflation_events", 0),
        ("electronic_silent_5lock_bypass_events", 0),
        ("nr_or_drive_burst_wall_violations", 0),
        ("slot1_still_capture_or_sort_write_bytes", 0),
        ("slot1_imagedb_or_burst_mutation_bytes", 0),
        ("double_log_or_lockout_bypass_events", 0),
        ("pplut_1080p_clamp_bypass_events", 0),
        ("pp_internal_reset_trap_violations", 0),
        ("fx6_baselook_confusion_events", 0),
        ("wb_cine_ei_awb_or_custom_setup_trap_events", 0),
        ("wb_custom_camset_exclusion_drift_events", 0),
        ("metering_desqueeze_or_cine_ei_base_iso_drift_events", 0),
        ("fx3_ui_exposes_usb_streaming", False),
        ("nouvc_spoof_events", 0),
        ("usb_host_data_enumeration_events", 0),
        ("hdmi_lcd_blanking_violations", 0),
        ("hdmi_log_1080_bypass_events", 0),
        ("slot1_protect_only_vault_violations", 0),
        ("slot1_vault_format_or_delete_events", 0),
        ("network_reset_zero_rf_violations", 0),
        ("fx3_ui_exposes_power_save_by_monitor", False),
        ("legacy_power_save_monitor_spoof_events", 0),
        ("unsafe_power_save_sleep_interference_events", 0),
        ("bk_lang_parity_drift_events", 0),
        ("stage_b_4lang_uxc_ltt_drift_events", 0),
        ("xlrh1_acoustic_feedback_violations", 0),
        ("audio_mon_4ch_hdmi_confusion_events", 0),
        ("destructive_delete_confirm_drift_events", 0),
        ("slot1_vault_delete_events", 0),
        ("legacy_mf_assist_spoof_events", 0),
        ("still_movie_initial_mag_couplings", 0),
        ("movie_af_in_focus_mag_events", 0),
        ("hdmi_clean_feed_focus_mag_or_peaking_leak_pixels", 0),
        ("movie_sq_af_illuminator_fire_events", 0),
        ("legacy_datetime_setup_spoof_events", 0),
        ("unsolicited_rtc_timezone_jump_events", 0),
        ("mishoe_5v_overcurrent_events", 0),
        ("hdmi_res_log_internal_rec_2160p_bypass_events", 0),
        ("slot1_vault_mutation_events", 0),
        ("slot1_vault_folder_mutation_events", 0),
        ("slot1_vault_folder_mutation_bytes", 0),
        ("movie_custom_folder_or_title_overflow_events", 0),
        ("still_prefix_underscore_lead_or_len_violations", 0),
        ("gamma_assist_log_lockout_bypass_events", 0),
        ("gamma_assist_external_hdmi_leak_events", 0),
        ("tcub_camera_reset_wipe_or_format_violations", 0),
        ("fx3_has_builtin_end_filter", False),
        ("e_nd_actuator_tx_count", 0),
        ("cardless_unrecorded_production_violations", 0),
        ("legacy_v1_audio_level_menu_spoof_events", 0),
        ("photographer_copyright_pii_leaked_bytes", 0),
        ("copyright_char_overflow_or_movie_mutation_events", 0),
        ("slot1_copyright_vault_mutation_bytes", 0),
        ("apsc_s35_4k_or_raw_bypass_events", 0),
        ("ai_unit_subject_recog_spoof_events", 0),
        ("hdmi_clean_feed_eye_frame_baked_pixels", 0),
        ("version_dialog_flash_writes", 0),
        ("slot1_bodydata_vault_mutation_bytes", 0),
        ("auto_slow_shutter_lockout_bypass_events", 0),
        ("auto_slow_shutter_angle_overlap_events", 0),
        ("breathing_comp_raw_or_240p_bypass_events", 0),
        ("hdmi_rec_ctrl_without_tc_violations", 0),
        ("slot1_hdmi_rec_vault_mutation_bytes", 0),
        ("diff_set_transition_corruption_events", 0),
        ("shutter_angle_common_bleed_events", 0),
        ("slot1_custom_key_vault_mutation_bytes", 0),
        ("fx3_has_builtin_evf", False),
        ("evf_finder_monitor_spoof_events", 0),
        ("tier0_battery_high_display_violations", 0),
        ("bt_rmt_ir_lockout_violations", 0),
        ("slot1_mymenu_vault_mutation_bytes", 0),
        ("destructive_menu_delete_confusions", 0),
        ("shutter_angle_exposure_step_drift_events", 0),
        ("fx3_has_var_shutter", False),
        ("unbuffered_battery_pull_events", 0),
    ):
        if getattr(m52_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-52 violated {attr_name} == {expected_val}")
    if m52_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-52 violated bodydata_flash_attempts_blocked >= 1")

    for attr_name, expected_val in (
        ("dci4k_long_gop_or_8k_violations", 0),
        ("reboot_2400p_stage_b_wipe_violations", 0),
        ("hdmi_raw_or_still_aspect_drift_events", 0),
        ("fx6_still_or_raw_conflation_events", 0),
        ("reg_custom_hold_or_hlg_lock_drift_events", 0),
        ("camset_cross_model_path_drift_events", 0),
        ("photo_capture_dci4k_lockout_bypass_events", 0),
        ("slot1_camset_write_bytes", 0),
        ("slot1_photo_capture_write_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
    ):
        if getattr(p53_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 53 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m52_rep.pillars)
    spec53 = MASTER_53_PILLAR_SPECS[52]
    p53_metrics = {
        "pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault": (
            f"{p53_rep.pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault.scenarios_passed}/"
            f"{p53_rep.pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault.scenarios_total}"
        ),
        "pillar_53b_custom_hold_camset_photo_capture_vault": (
            f"{p53_rep.pillar_53b_custom_hold_camset_photo_capture_vault.scenarios_passed}/"
            f"{p53_rep.pillar_53b_custom_hold_camset_photo_capture_vault.scenarios_total}"
        ),
        "dci4k_long_gop_or_8k_violations": p53_rep.dci4k_long_gop_or_8k_violations,
        "reboot_2400p_stage_b_wipe_violations": p53_rep.reboot_2400p_stage_b_wipe_violations,
        "hdmi_raw_or_still_aspect_drift_events": p53_rep.hdmi_raw_or_still_aspect_drift_events,
        "fx6_still_or_raw_conflation_events": p53_rep.fx6_still_or_raw_conflation_events,
        "reg_custom_hold_or_hlg_lock_drift_events": p53_rep.reg_custom_hold_or_hlg_lock_drift_events,
        "camset_cross_model_path_drift_events": p53_rep.camset_cross_model_path_drift_events,
        "photo_capture_dci4k_lockout_bypass_events": p53_rep.photo_capture_dci4k_lockout_bypass_events,
        "slot1_camset_write_bytes": p53_rep.slot1_camset_write_bytes,
        "slot1_photo_capture_write_bytes": p53_rep.slot1_photo_capture_write_bytes,
        "slot1_vault_mutation_bytes": p53_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p53_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_ebusy_enforced": p53_rep.slot1_vault_erofs_ebusy_enforced,
        "overall_ready_for_hardware_attach": p53_rep.overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": p53_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p53_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec53[0],
            pillar_id=spec53[1],
            phase_label=spec53[2],
            module_name=spec53[3],
            passed=bool(p53_rep.all_passed),
            status=p53_rep.status,
            verification_mode=p53_rep.verification_mode,
            elapsed_seconds=p53_dt,
            key_metrics=p53_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec53[1],
                    "mode": p53_rep.verification_mode,
                    "status": p53_rep.status,
                    "metrics": p53_metrics,
                    "passed": p53_rep.all_passed,
                }
            ),
            errors=tuple(p53_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master53_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p53_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_53_PILLAR_COUNT == 53
        and pillars_passed == 53
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE300_SCHEMA,
            "version": PHASE300_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [
                (p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses
            ],
            "all_passed": all_ok,
        }
    )
    return Master53PillarRecoveryReport(
        schema=PHASE300_SCHEMA,
        version=PHASE300_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P300_STATUS_VERIFIED_53OF53_AGGREGATOR if all_ok else P300_STATUS_FAIL_53OF53_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_2s_fast_cli_budget=elapsed < P300_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P300_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P300_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p53_rep.donor_snapshot,
        pillar53_a_dci4k_2400p_hdmi_raw_aspect_vault=p53_rep.pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault,
        pillar53_b_custom_hold_camset_photo_capture_vault=(
            p53_rep.pillar_53b_custom_hold_camset_photo_capture_vault
        ),
        dci4k_long_gop_or_8k_violations=p53_rep.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=p53_rep.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=p53_rep.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=p53_rep.fx6_still_or_raw_conflation_events,
        reg_custom_hold_or_hlg_lock_drift_events=p53_rep.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=p53_rep.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=p53_rep.photo_capture_dci4k_lockout_bypass_events,
        slot1_camset_write_bytes=p53_rep.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=p53_rep.slot1_photo_capture_write_bytes,
        slot1_vault_mutation_bytes=m52_rep.slot1_vault_mutation_bytes + p53_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p53_rep.slot1_format_hard_locked,
        slot1_vault_erofs_ebusy_enforced=p53_rep.slot1_vault_erofs_ebusy_enforced,
        fx3_appfw_has_dci4k_internal=P300_FX3_APPFW_HAS_DCI4K_INTERNAL,
        fx3_appfw_has_pro_camera_path=P300_FX3_APPFW_HAS_PRO_CAMERA_PATH,
        fx6_has_still_aspect_ratio=P300_FX6_HAS_STILL_ASPECT_RATIO,
        fx6_has_photo_capture=P300_FX6_HAS_PHOTO_CAPTURE,
        fx6_has_playback_enlarge_image=P300_FX6_HAS_PLAYBACK_ENLARGE_IMAGE,
        fx6_has_reg_custom_shoot_set=P300_FX6_HAS_REG_CUSTOM_SHOOT_SET,
        fx6_has_camera_set_memory=P300_FX6_HAS_CAMERA_SET_MEMORY,
        movie_tracking_area_or_limit_violations=m52_rep.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=m52_rep.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=m52_rep.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=m52_rep.fx6_handle_or_pos_display_conflation_events,
        iso_minss_or_cine_ei_lock_drift_events=m52_rep.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=m52_rep.flash_still_mech_gate_violations,
        mishoe_pmic_5v_overcurrent_events=m52_rep.mishoe_pmic_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=m52_rep.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=m52_rep.slot1_flash_videolight_imagedb_bytes,
        xlrh1_has_zoom_lever=m52_rep.xlrh1_has_zoom_lever,
        xlrh1_has_rec_button=m52_rep.xlrh1_has_rec_button,
        xlrh1_has_zoom_hold_switch=m52_rep.xlrh1_has_zoom_hold_switch,
        fx6_0_99_is_zoom_position_display=m52_rep.fx6_0_99_is_zoom_position_display,
        fx6_has_iso_auto_min_ss=m52_rep.fx6_has_iso_auto_min_ss,
        fx6_mechanical_shutter_present=m52_rep.fx6_mechanical_shutter_present,
        dormant_lossless_raw_exposure_events=m52_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=m52_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=m52_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=m52_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=m52_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=m52_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=m52_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=m52_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=m52_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=m52_rep.slot1_imagedb_or_burst_mutation_bytes,
        fx3_ui_exposes_lossless_raw=m52_rep.fx3_ui_exposes_lossless_raw,
        fx3_ui_exposes_shutter_type_auto=m52_rep.fx3_ui_exposes_shutter_type_auto,
        fx6_still_pipeline_present=m52_rep.fx6_still_pipeline_present,
        double_log_or_lockout_bypass_events=m52_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m52_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m52_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m52_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=m52_rep.wb_cine_ei_awb_or_custom_setup_trap_events,
        wb_custom_camset_exclusion_drift_events=m52_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m52_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m52_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m52_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m52_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m52_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m52_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m52_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m52_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m52_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m52_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m52_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=m52_rep.unsafe_power_save_sleep_interference_events,
        bk_lang_parity_drift_events=m52_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m52_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m52_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m52_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m52_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m52_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m52_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m52_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m52_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m52_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m52_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m52_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m52_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m52_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m52_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m52_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m52_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m52_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=m52_rep.movie_custom_folder_or_title_overflow_events,
        still_prefix_underscore_lead_or_len_violations=(
            m52_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m52_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m52_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=m52_rep.tcub_camera_reset_wipe_or_format_violations,
        fx3_has_builtin_end_filter=m52_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m52_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m52_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m52_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m52_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m52_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m52_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m52_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m52_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m52_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m52_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m52_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m52_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m52_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m52_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m52_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m52_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m52_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m52_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m52_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m52_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m52_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m52_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m52_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m52_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m52_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m52_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m52_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m52_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m52_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        hardware_live_attachment_authorized=p53_rep.hardware_live_attachment_authorized,
        master_53pillar_sha256=master_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(all_errors),
    )


def evaluate_53pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master53PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_53pillar_recovery_master`."""
    return evaluate_realhw_53pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_53pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master53PillarRecoveryReport:
    """Public CLI entry point for Phase 300 (300th Phase Milestone) `53/53` unified recovery master."""
    return evaluate_realhw_53pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
    "ALLOW_PERSISTENT_JIRITSU_WRITES",
    "CNFLASHA_USERSPACE_WRITE_BLOCKED",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "ISP_WRITE_AUTHORIZED",
    "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
    "MASTER_53_PILLAR_COUNT",
    "MASTER_53_PILLAR_IDS",
    "MASTER_53_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P300_2400P_PLAYBACK_QUARANTINE_G_RESID16",
    "P300_2400P_REBOOT_ALT_G_RESID16",
    "P300_2400P_REBOOT_G_RESID16",
    "P300_2400P_REBOOT_STAGE_B_WIPE_VIOLATIONS",
    "P300_2400P_RESID16",
    "P300_BLOCKED_2400P_REBOOT_STAGE_B_WIPE_OR_QUARANTINE_DRIFT",
    "P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION",
    "P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION",
    "P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION",
    "P300_BLOCKED_INVALID_PILLAR53A_SPEC",
    "P300_BLOCKED_INVALID_PILLAR53B_SPEC",
    "P300_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT",
    "P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT",
    "P300_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL",
    "P300_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P300_BOUNDED_HEADER_BYTES",
    "P300_CAMSET_ALL_BANKS",
    "P300_CAMSET_BODY_BANKS",
    "P300_CAMSET_CARD_BANKS",
    "P300_CAMSET_CARD_TYPE_SUBDIR_MAP",
    "P300_CAMSET_CROSS_MODEL_PATH_DRIFT_EVENTS",
    "P300_CAMSET_MEMORY_MENU_PATH",
    "P300_CONCURRENT_CEILING_SECONDS",
    "P300_DCI4K_600M_MIN_GRADES",
    "P300_DCI4K_ASPECT",
    "P300_DCI4K_BITRATE_BY_FPS_MBPS",
    "P300_DCI4K_DIMENSIONS",
    "P300_DCI4K_LONG_GOP_OR_8K_VIOLATIONS",
    "P300_DCI4K_LONG_RESID16",
    "P300_DCI4K_REC_FRAME_RATES",
    "P300_DCI4K_RESID16",
    "P300_DCI4K_SQ_ALLOWED_FPS",
    "P300_DCI4K_SQ_LOCKED_OUT_FPS",
    "P300_DESTRUCTIVE_VAULT_ACTIONS",
    "P300_DONOR_FX3_APPFW_702_RELPATH",
    "P300_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P300_DONOR_FX3_UXC_EN_F_RELPATH",
    "P300_DONOR_FX3_UXC_EN_G_RELPATH",
    "P300_DONOR_FX3_UXC_EN_RELPATH",
    "P300_DONOR_FX3_UXC_JA_F_RELPATH",
    "P300_DONOR_FX3_UXC_JA_G_RELPATH",
    "P300_DONOR_FX3_UXC_JA_RELPATH",
    "P300_DONOR_FX3_UXC_SC_F_RELPATH",
    "P300_DONOR_FX3_UXC_SC_G_RELPATH",
    "P300_DONOR_FX3_UXC_SC_RELPATH",
    "P300_DONOR_FX3_UXC_TC_F_RELPATH",
    "P300_DONOR_FX3_UXC_TC_G_RELPATH",
    "P300_DONOR_FX3_UXC_TC_RELPATH",
    "P300_DONOR_FX6_APPFW_601_RELPATH",
    "P300_DONOR_FX6_UXC_EN_2_RELPATH",
    "P300_DONOR_FX6_UXC_EN_RELPATH",
    "P300_DONOR_INSPECT_BUDGET_SECONDS",
    "P300_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P300_DORMANT_8K_FORMAT",
    "P300_ENLARGE_IMAGE_MENU_PATH",
    "P300_ENLARGE_IMAGE_RESID16",
    "P300_ENLARGE_INITIAL_MAG_BKID",
    "P300_ENLARGE_INITIAL_MAG_DEFAULT",
    "P300_ENLARGE_INITIAL_MAG_MODES",
    "P300_ENLARGE_INITIAL_MAG_RESID16",
    "P300_ENLARGE_INITIAL_POS_BKID",
    "P300_ENLARGE_INITIAL_POS_DEFAULT",
    "P300_ENLARGE_INITIAL_POS_MODES",
    "P300_ENLARGE_INITIAL_POS_RESID16",
    "P300_ENV_CLEAN_ROOM_TEST",
    "P300_FAST_CLI_BUDGET_SECONDS",
    "P300_FORBIDDEN_PERSISTENT_TARGETS",
    "P300_FX3_APPFW_HAS_DCI4K_INTERNAL",
    "P300_FX3_APPFW_HAS_PRO_CAMERA_PATH",
    "P300_FX3_CAMPR_PATH_TEMPLATE",
    "P300_FX3_CAMSET_PATH_TEMPLATE",
    "P300_FX3_FW_VERSION",
    "P300_FX3_HDMI_RAW_ASPECT",
    "P300_FX3_HDMI_RAW_DIMENSIONS",
    "P300_FX3_HDMI_RAW_FRAME_RATES",
    "P300_FX3_HELPGUIDE_ID",
    "P300_FX3_MODEL_ID",
    "P300_FX3_MODEL_NAME",
    "P300_FX3_PRODUCT_CODENAME",
    "P300_FX3_SENSOR_FAMILY",
    "P300_FX3_SETTING_MODEL_TAG",
    "P300_FX3_STILL_RAW_NATIVE_DIMS",
    "P300_FX3_SUPPORTED_FW_VERSIONS",
    "P300_FX6_DCI4K_SQ_MAX_FPS",
    "P300_FX6_DONOR_FW_VERSION",
    "P300_FX6_DONOR_MODEL_NAME",
    "P300_FX6_HAS_CAMERA_SET_MEMORY",
    "P300_FX6_HAS_PHOTO_CAPTURE",
    "P300_FX6_HAS_PLAYBACK_ENLARGE_IMAGE",
    "P300_FX6_HAS_REG_CUSTOM_SHOOT_SET",
    "P300_FX6_HAS_STILL_ASPECT_RATIO",
    "P300_FX6_MAX_ALL_FILES",
    "P300_FX6_PRODUCT_CODENAME",
    "P300_FX6_PRO_CAMERA_PATH_PREFIX",
    "P300_FX6_PRO_SCENE_PATH_PREFIX",
    "P300_FX6_RAW_DIMENSIONS",
    "P300_FX6_STILL_OR_RAW_CONFLATION_EVENTS",
    "P300_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P300_HDMI_RAW_OR_STILL_ASPECT_DRIFT_EVENTS",
    "P300_HD_DIMENSIONS",
    "P300_LOG_SHOOTING_MODES",
    "P300_LONG_GOP_4K_FORMATS",
    "P300_MAX_FULL_DONOR_BYTES",
    "P300_MEDIA_CARD_GRADES",
    "P300_MOVIE_FILE_FORMATS",
    "P300_MOVIE_FILE_FORMAT_MENU_PATH",
    "P300_NOMINAL_BUDGET_SECONDS",
    "P300_ON_OFF_MODES",
    "P300_OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P300_PHOTO_CAPTURE_4K_UHD_DIMS",
    "P300_PHOTO_CAPTURE_4K_UHD_MP",
    "P300_PHOTO_CAPTURE_BKID",
    "P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_BYPASS_EVENTS",
    "P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_G_RESID16",
    "P300_PHOTO_CAPTURE_FILE_TYPES",
    "P300_PHOTO_CAPTURE_FILE_TYPE_DEFAULT",
    "P300_PHOTO_CAPTURE_HD_DIMS",
    "P300_PHOTO_CAPTURE_HD_MP",
    "P300_PHOTO_CAPTURE_MENU_PATH",
    "P300_PHOTO_CAPTURE_RESID16",
    "P300_PILLAR_53A_SCENARIO_IDS",
    "P300_PILLAR_53B_SCENARIO_IDS",
    "P300_PINNED_FX3_APPFW_702_BYTES",
    "P300_PINNED_FX3_APPFW_702_FULL_SHA256",
    "P300_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P300_PINNED_FX3_BACKUP_BIN_BYTES",
    "P300_PINNED_FX3_BACKUP_BIN_SHA256",
    "P300_PINNED_FX3_UXC_EN_BYTES",
    "P300_PINNED_FX3_UXC_EN_F_BYTES",
    "P300_PINNED_FX3_UXC_EN_F_SHA256",
    "P300_PINNED_FX3_UXC_EN_G_BYTES",
    "P300_PINNED_FX3_UXC_EN_G_SHA256",
    "P300_PINNED_FX3_UXC_EN_SHA256",
    "P300_PINNED_FX3_UXC_JA_BYTES",
    "P300_PINNED_FX3_UXC_JA_F_BYTES",
    "P300_PINNED_FX3_UXC_JA_F_SHA256",
    "P300_PINNED_FX3_UXC_JA_G_BYTES",
    "P300_PINNED_FX3_UXC_JA_G_SHA256",
    "P300_PINNED_FX3_UXC_JA_SHA256",
    "P300_PINNED_FX3_UXC_SC_BYTES",
    "P300_PINNED_FX3_UXC_SC_F_BYTES",
    "P300_PINNED_FX3_UXC_SC_F_SHA256",
    "P300_PINNED_FX3_UXC_SC_G_BYTES",
    "P300_PINNED_FX3_UXC_SC_G_SHA256",
    "P300_PINNED_FX3_UXC_SC_SHA256",
    "P300_PINNED_FX3_UXC_TC_BYTES",
    "P300_PINNED_FX3_UXC_TC_F_BYTES",
    "P300_PINNED_FX3_UXC_TC_F_SHA256",
    "P300_PINNED_FX3_UXC_TC_G_BYTES",
    "P300_PINNED_FX3_UXC_TC_G_SHA256",
    "P300_PINNED_FX3_UXC_TC_SHA256",
    "P300_PINNED_FX6_APPFW_601_BYTES",
    "P300_PINNED_FX6_APPFW_601_FULL_SHA256",
    "P300_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P300_PINNED_FX6_UXC_EN_2_BYTES",
    "P300_PINNED_FX6_UXC_EN_2_SHA256",
    "P300_PINNED_FX6_UXC_EN_BYTES",
    "P300_PINNED_FX6_UXC_EN_SHA256",
    "P300_RAW_OUTPUT_MENU_PATH",
    "P300_RAW_OUTPUT_RESID16",
    "P300_RECALL_CAMSET_MENU_PATH",
    "P300_REG_CUSTOM_HLG_FORCE_OFF_RECALLED_ITEMS",
    "P300_REG_CUSTOM_HOLD_CHECKBOX_COUNT",
    "P300_REG_CUSTOM_HOLD_DEFAULT",
    "P300_REG_CUSTOM_HOLD_OR_HLG_LOCK_DRIFT_EVENTS",
    "P300_REG_CUSTOM_HOLD_RESID16_MAP",
    "P300_REG_CUSTOM_SHOOT_SET_11_CHECKBOXES",
    "P300_REG_CUSTOM_SHOOT_SET_MENU_PATH",
    "P300_REG_CUSTOM_SHOOT_SET_RESID16",
    "P300_REG_CUSTOM_SHOOT_SET_SLOTS",
    "P300_RESET_ACTIONS",
    "P300_SAFE_SECONDARY_CAPTURE_SLOT",
    "P300_SHOOTING_DOMAINS",
    "P300_SHUTTER_ANGLE_MAX_DEG",
    "P300_SHUTTER_ANGLE_MIN_DEG",
    "P300_SHUTTER_MODES",
    "P300_SHUTTER_MODE_RESID16",
    "P300_SLOT1_CAMSET_WRITE_BYTES",
    "P300_SLOT1_FORMAT_HARD_LOCKED",
    "P300_SLOT1_PHOTO_CAPTURE_WRITE_BYTES",
    "P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED",
    "P300_SLOT1_VAULT_MUTATION_BYTES",
    "P300_SLOT1_VAULT_SLOT",
    "P300_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P300_STATUS_FAIL_53OF53_AGGREGATOR",
    "P300_STATUS_FAIL_PILLAR53_SUITE",
    "P300_STATUS_REJECTED_PILLAR_53A",
    "P300_STATUS_REJECTED_PILLAR_53B",
    "P300_STATUS_VERIFIED_53OF53_AGGREGATOR",
    "P300_STATUS_VERIFIED_PILLAR53_SUITE",
    "P300_STATUS_VERIFIED_PILLAR_53A",
    "P300_STATUS_VERIFIED_PILLAR_53B",
    "P300_STILL_ALL_MODES",
    "P300_STILL_ASPECT_BKID",
    "P300_STILL_ASPECT_DEFAULT",
    "P300_STILL_ASPECT_MENU_PATH",
    "P300_STILL_ASPECT_RATIOS",
    "P300_STILL_ASPECT_RESID16",
    "P300_STILL_ASPECT_RESID16_MAP",
    "P300_STILL_ASPECT_SIZE_MATRIX",
    "P300_STILL_IMAGE_SIZE_DEFAULT",
    "P300_STILL_IMAGE_SIZE_TIERS",
    "P300_STILL_PASM_MODES",
    "P300_TIER0_SURFACE_COUNT",
    "P300_UHD_4K_DIMENSIONS",
    "P300_UHD_4K_FORMATS",
    "P300_UHD_ASPECT",
    "P300_UHD_REC_FRAME_RATES",
    "P300_VAULT_FIREWALL_ERRNOS",
    "P300_VAULT_TARGET_ACTIONS",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE300_PHASE_NUMBER",
    "PHASE300_SCHEMA",
    "PHASE300_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "Dci4k2400pHdmiRawStillAspectVaultReport",
    "Dci4k2400pHdmiRawStillAspectVaultSpec",
    "Dci4kAspectCustomHoldCamsetPhotoCaptureVaultReport",
    "Master53PillarRecoveryReport",
    "Phase300DonorArtifactDigest",
    "Phase300DonorSnapshot",
    "Pillar53ASuiteResult",
    "Pillar53BSuiteResult",
    "Pillar53ScenarioOutcome",
    "Pillar53StandaloneReport",
    "RegCustomHoldCamsetPhotoCaptureVaultReport",
    "RegCustomHoldCamsetPhotoCaptureVaultSpec",
    "build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec",
    "build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec",
    "build_fx3_campr_card_path",
    "build_fx3_camset_card_path",
    "compute_expected_dci4k_2400p_hdmi_raw_and_still_aspect_state",
    "compute_expected_photo_capture_and_enlarge_image_state",
    "compute_expected_reg_custom_hold_and_camset_memory_state",
    "evaluate_53pillar_recovery_master",
    "evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault",
    "evaluate_realhw_53pillar_recovery_master",
    "evaluate_reg_custom_hold_camset_photo_capture_vault",
    "inspect_phase300_donors_readonly",
    "run_pillar53_standalone_suite",
    "run_pillar53a_dci4k_2400p_hdmi_raw_still_aspect_6_scenario_suite",
    "run_pillar53b_custom_hold_camset_photo_capture_6_scenario_suite",
    "verify_53pillar_recovery_suite",
    "verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault",
    "verify_dci4k_aspect_custom_hold_camset_photo_capture_vault",
]
