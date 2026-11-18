"""Phase 284 — 9th Real-Hardware Physical Bench Readiness Verifier (`preflight-pp-scinetone-wb-metering-and-shutter-type`).

Dedicated host-side read-only 9th physical bench & pre-shoot readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, `ilc/2210`, Model `0x91030080`) vs `ILME-FX6` (`Ver. 6.01`),
extending the operator bench preflight series (`preflight-card-insert` ->
`preflight-bench-cable-fan-slot1` -> `preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop` ->
`preflight-diffset-customkey-autoslow-and-apsc` ->
`preflight-file-settings-gamma-assist-focus-mag-and-videolight` ->
`preflight-usb-mode-hdmi-info-protect-and-network-reset` ->
`preflight-pp-scinetone-wb-metering-and-shutter-type`) by synthesizing Waves 48-49 official
Sony `ILME-FX3` Help Guide (`ilc/2210`), `appFw.so`, `BK4`, and `.uxc` hardware boundaries
into 4 deterministic fail-closed check groups (`A..D`), bounded `O_RDONLY` donor inspection
(`< 0.15s`), `16/16 H0 == H3` baseline invariance, and dual-media `528 B FX3RCPT1` Tier-0
receipt gating:

1. **Check Group A (`GROUP_A_PP11_SCINETONE_CREATIVE_LOOK_DRO_LOG_LOCKOUT_AND_RESET_TRAP` — Wave 48 §1)**:
   - Stock `ILME-FX3 Ver. 7.02` defaults `[Picture Profile]` (`_f.uxc` `0x6830`) to
     **`PP11` (`S-Cinetone`)** for BOTH Movie & Still unless decoupled via
     `[Different Set for Still/Mv]` (`0x62ee`), locking `[Creative Look]` (`0x6823`,
     `10` looks `ST..SE`) to `'-'` and `[D-Range Optimizer]` (`0xe89c`) to `Off` whenever
     `[Picture Profile] != Off`.
   - `[Log Shooting]` (`Flexible ISO`, `Cine EI Quick`, `Cine EI`, `0x6020`) locks
     `[Picture Profile] = Off`, `[Creative Look] = '-'`, `[DRO] = Off`, while `PPLUT1..4`
     are Movie-only (`1080p` internal-recording HDMI clamp); verifies `PP1..11` customized
     internal parameters and `[Different Set]` check marks survive `[Camera Settings Reset]`
     & `[Initialize]` unless per-profile `[Reset]` is executed.

2. **Check Group B (`GROUP_B_WHITE_BALANCE_CINE_EI_CUSTOM13_AND_METERING_6MODE_MM` — Wave 48 §2)**:
   - `[White Balance]` (`2500K..9900K` `100K` steps + `A7..B7`/`G7..M7`, `Custom 1..3`,
     `Priority Set in AWB`, non-resettable `Shutter AWB Lock` `Off`, `Shockless WB`
     `1 (Fast)`): `Cine EI` / `Cine EI Quick` blocks `Auto` & `Underwater Auto` WB;
     `[Custom Setup]` while `Log Shooting != Off` or `S-Log3` (`PP8`/`PP9`) / `PPLUT1..4`
     triggers custom WB setup error trap; `Custom 1..3` survives `[Camera Settings Reset]`
     yet is excluded from `CAMSET`.
   - `[Metering Mode]` (`Multi`, `Center`, `Spot: Standard`, `Spot: Large`,
     `Entire Screen Avg.`, `Highlight`), `Face Priority in Multi Metering` (`Off` forced
     when `De-Squeeze != Off`), `Spot Metering Point` (`Center` / `Focus Point Link`),
     non-resettable `AEL w/ Shutter` (`Auto`), and `Cine EI` Base ISO (`800`/`12800`)
     invariance where metering drives `M.M.` indicator only.

3. **Check Group C (`GROUP_C_STILL_RAW_2OPTION_NO_LOSSLESS_HLG_AND_ADOBERGB_DSC` — Wave 49 §1)**:
   - Stock `ILME-FX3` exposes ONLY `Compressed` (default) and `Uncompressed` 14-bit `.ARW`
     (reject dormant `Lossless Comp` `0x6b56` spoofing; contrast Still-less `ILME-FX6`
     `mechanical_shutter == False`), `[HLG Still Image] = [On]` requires `HEIF`-only in
     `P/A/S/M` (`BT.2100`/`BT.2020`, locking out `PP`/`Creative Look`/`DRO`/`DRO Bracket`),
     and `[Color Space]` (`Shooting -> [Image Quality/Rec]` `0x68b7`: `sRGB` `DSC00001` vs
     `AdobeRGB` `_DSC0001` DCF 2.0 leading `_` rule forbidding manual leading `_` in
     `[Set File Name]`).

4. **Check Group D (`GROUP_D_SHUTTER_TYPE_2OPTION_NO_AUTO_FLASH_5LOCKOUT_HIP_AND_TIER0` — Wave 49 §2 + Tier-0)**:
   - Stock `ILME-FX3` `[Shutter Type]` (`0x7aa9`) exposes ONLY `Mechanical Shutter`
     (default) and `Electronic Shutter` (no `Auto`!; `Silent Mode = On` forces
     `Electronic`; `[e-Front Curtain Shut.] = [On]` survives `Camera Settings Reset`),
     `1/250 s` mechanical flash sync ceiling, Electronic Shutter / Silent Mode 5-function
     lockout (`Flash`, `Long Exposure NR`, `e-Front Curtain Shut.`, `BULB`,
     `Anti-flicker Shoot.`), `Cont. Shooting: Hi+` (`10 fps` speed drop on `Uncompressed`
     RAW / Flash, AF locked to 1st frame at `> F11`), plus `16/16 H0 == H3` and dual-media
     `528 B FX3RCPT1` Tier-0 receipt validation.

Hard-Locked Safety Invariants (UNCONDITIONAL):
- `overall_ready_for_hardware_attach = False`
- `hardware_live_attachment_authorized = False`
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `sd_physical_media_written = False`
- `lossless_comp_exposed_in_fx3_ui = False`
- `shutter_type_auto_exposed_in_fx3_ui = False`
- `usb_packets_transmitted = 0` (`physical_usb_packets_emitted = 0`)
- `raw_firmware_bytes_leaked = 0`
- `passive_tx_bytes_emitted = 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _ensure_cross_package_paths(repo_root: Path) -> None:
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (  # noqa: E402
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import is_forced_clean_room, resolve_work_subpath  # noqa: E402
from .hardware_readiness_packet import (  # noqa: E402
    BODY_SERIAL_RE,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    HEX32_CID_RE,
    HEX64_RE,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_WLAN_RSRC_DONOR_SHA256,
)
from .realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    FX3_LIBUSBBUSPOWER_EXPECTED_SHA256,
    FX3_LIBUSBBUSPOWER_EXPECTED_SIZE,
    FX3_LIBUSBBUSPOWER_RELPATH,
)
from .realhw_card_insert_readiness_verifier import (  # noqa: E402
    DONOR_INSPECTION_MAX_SECONDS,
    EM_AARCH64,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    MIN_BODY_FW_TUPLE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_INT,
    _parse_elf64_header_and_pt_load,
    _parse_fw_tuple,
    _read_bounded_slice_o_rdonly,
    build_default_h0_baselines,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    LIBJIRITSU_EXPECTED_SHA256,
    LIBJIRITSU_EXPECTED_SIZE,
    LIBJIRITSU_RELPATH,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
    FX3_IM_ELF_EXPECTED_SHA256,
    FX3_IM_ELF_EXPECTED_SIZE,
    FX3_IM_ELF_RELPATH,
    FX6_APPFW_EXPECTED_SIZE,
    SIXTEEN_STORAGE_SURFACES,
    read_only_o_rdonly_digest_and_header,
)

# ---------------------------------------------------------------------------
# Schema, Verdicts & Non-Shadowing P284_* Domain Constants
# ---------------------------------------------------------------------------

PHASE_284_SCHEMA: str = "realhw_pp_scinetone_wb_metering_and_shutter_type_verifier_v1"
P284_SCHEMA: str = PHASE_284_SCHEMA
REALHW_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_SCHEMA: str = PHASE_284_SCHEMA
PHASE_284_VERSION: str = "284.0.0"
P284_VERSION: str = PHASE_284_VERSION
P284_SONY_HELP_GUIDE_ID: str = "ilc/2210"

P284_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS: str = (
    "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
)
P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED: str = (
    "GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_READONLY_PREFLIGHT_VERIFIED"
)
P284_GO_NO_GO_BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_FAILURE: str = (
    "BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_CHECK_FAILURE"
)
PHASE_284_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    P284_GO_NO_GO_BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED,
)

P284_CHECK_GROUP_A_ID: str = (
    "GROUP_A_PP11_SCINETONE_CREATIVE_LOOK_DRO_LOG_LOCKOUT_AND_RESET_TRAP"
)
P284_CHECK_GROUP_B_ID: str = (
    "GROUP_B_WHITE_BALANCE_CINE_EI_CUSTOM13_AND_METERING_6MODE_MM"
)
P284_CHECK_GROUP_C_ID: str = (
    "GROUP_C_STILL_RAW_2OPTION_NO_LOSSLESS_HLG_AND_ADOBERGB_DSC"
)
P284_CHECK_GROUP_D_ID: str = (
    "GROUP_D_SHUTTER_TYPE_2OPTION_NO_AUTO_FLASH_5LOCKOUT_HIP_AND_TIER0"
)
PHASE_284_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P284_CHECK_GROUP_A_ID,
    P284_CHECK_GROUP_B_ID,
    P284_CHECK_GROUP_C_ID,
    P284_CHECK_GROUP_D_ID,
)

PHASE284_RAW_FIRMWARE_BYTES_LEAKED: int = 0
PHASE284_PASSIVE_TX_BYTES_EMITTED: int = 0
PHASE284_USB_PACKETS_TRANSMITTED: int = 0

# Group A Constants (Wave 48 §1 — Out-of-Box PP11 S-Cinetone, Creative Look, DRO, Log Lockout & PP Reset Trap)
P284_PP_BKID: str = "BKID_APP_setting_picture_profile"
P284_PP_RESID16_HEX: str = "0x6830"
P284_PP_DEFAULT_PROFILE: str = "PP11"
P284_PP11_GAMMA_NAME: str = "S-Cinetone"
P284_PP11_RESIDS: Tuple[str, ...] = ("0x67ab", "0x6e61")
P284_PP11_CAUTION_ID: str = "CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG"
P284_DIFF_SET_BKID: str = "BKID_APP_setting_different_set"
P284_DIFF_SET_RESID16_HEX: str = "0x62ee"
P284_PP1_TO_PP11_PROFILES: Tuple[str, ...] = (
    "PP1",
    "PP2",
    "PP3",
    "PP4",
    "PP5",
    "PP6",
    "PP7",
    "PP8",
    "PP9",
    "PP10",
    "PP11",
)
P284_PPLUT_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P284_SLOG3_PROFILES: Tuple[str, ...] = ("PP8", "PP9")
P284_VALID_PICTURE_PROFILES: Tuple[str, ...] = (
    ("OFF",) + P284_PP1_TO_PP11_PROFILES + P284_PPLUT_PROFILES
)
P284_CREATIVE_LOOK_BKID: str = "BKID_APP_setting_creative_style_plus"
P284_CREATIVE_LOOK_RESID16_HEX: str = "0x6823"
P284_CREATIVE_LOOK_TEN_PRESETS: Tuple[str, ...] = (
    "ST",
    "PT",
    "NT",
    "VV",
    "VV2",
    "FL",
    "IN",
    "SH",
    "BW",
    "SE",
)
P284_CREATIVE_LOOK_DEFAULT: str = "ST"
P284_CREATIVE_LOOK_LOCKED_DASH: str = "-"
P284_DRO_BKID: str = "BKID_APP_setting_dro"
P284_DRO_RESID16_HEX: str = "0xe89c"
P284_DRO_VALID_MODES: Tuple[str, ...] = (
    "OFF",
    "AUTO",
    "LV1",
    "LV2",
    "LV3",
    "LV4",
    "LV5",
)
P284_LOG_SHOOTING_BKID: str = "BKID_APP_setting_log_shooting"
P284_LOG_SHOOTING_RESID16_HEX: str = "0x6020"
P284_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "FLEXIBLE_ISO",
    "CINE_EI_QUICK",
    "CINE_EI",
)
P284_ACTIVE_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "FLEXIBLE_ISO",
    "CINE_EI_QUICK",
    "CINE_EI",
)
P284_DISPLAY_LUT_RESID16_HEX: str = "0x729a"
P284_SELECT_LUT_RESID16_HEX: str = "0x643e"
P284_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P284_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "INITIALIZE",
    "PP_INDIVIDUAL_RESET",
)

# Group B Constants (Wave 48 §2 — White Balance, Cine EI, Custom 1..3, Metering 6-Mode, M.M.)
P284_WB_BKID: str = "BKID_APP_setting_white_balance"
P284_WB_RESID16_HEX: str = "0xe5d4"
P284_WB_CTEMP_RESID16_HEX: str = "0xe2ac"
P284_WB_FILTER_RESID16_HEX: str = "0xe992"
P284_WB_KELVIN_MIN_K: int = 2500
P284_WB_KELVIN_MAX_K: int = 9900
P284_WB_KELVIN_STEP_K: int = 100
P284_WB_AB_MIN: int = -7
P284_WB_AB_MAX: int = 7
P284_WB_GM_MIN: int = -7
P284_WB_GM_MAX: int = 7
P284_WB_CUSTOM_SLOTS: Tuple[str, ...] = ("CUSTOM_1", "CUSTOM_2", "CUSTOM_3")
P284_WB_CINE_EI_BLOCKED_MODES: Tuple[str, ...] = ("AUTO", "UNDERWATER_AUTO")
P284_WB_VALID_MODES: Tuple[str, ...] = (
    "AUTO",
    "DAYLIGHT",
    "SHADE",
    "CLOUDY",
    "INCANDESCENT",
    "FLUOR_WARM",
    "FLUOR_COOL",
    "FLUOR_DAY",
    "FLUOR_DAYLIGHT",
    "FLASH",
    "UNDERWATER_AUTO",
    "C_TEMP_FILTER",
    "CUSTOM_1",
    "CUSTOM_2",
    "CUSTOM_3",
)
P284_PRIORITY_AWB_RESID16_HEX: str = "0x67a7"
P284_VALID_PRIORITY_AWB_MODES: Tuple[str, ...] = ("STANDARD", "AMBIENCE", "WHITE")
P284_SHUTTER_AWB_LOCK_RESID16_HEX: str = "0x66db"
P284_VALID_SHUTTER_AWB_LOCK_MODES: Tuple[str, ...] = (
    "OFF",
    "SHUTTER_HALF_PRESS",
    "CONT_SHOOTING",
)
P284_SHOCKLESS_WB_RESID16_HEX: str = "0x62fe"
P284_VALID_SHOCKLESS_WB_MODES: Tuple[str, ...] = ("OFF", "1", "2", "3")
P284_METERING_MODE_BKID: str = "BKID_APP_setting_metering_mode"
P284_METERING_MODE_RESID16_HEX: str = "0xe5cf"
P284_METERING_SIX_MODES: Tuple[str, ...] = (
    "MULTI",
    "CENTER",
    "SPOT_STANDARD",
    "SPOT_LARGE",
    "ENTIRE_SCREEN_AVG",
    "HIGHLIGHT",
)
P284_METERING_MODE_RESIDS: Dict[str, str] = {
    "MULTI": "0xe631",
    "CENTER": "0xe787",
    "SPOT_STANDARD": "0x630e",
    "SPOT_LARGE": "0x7357",
    "ENTIRE_SCREEN_AVG": "0x6aa1",
    "HIGHLIGHT": "0x6491",
}
P284_FACE_PRIORITY_MULTI_METERING_RESID16_HEX: str = "0x69c7"
P284_SPOT_METERING_POINT_RESID16_HEX: str = "0x71b5"
P284_VALID_SPOT_METERING_POINTS: Tuple[str, ...] = ("CENTER", "FOCUS_POINT_LINK")
P284_AEL_WITH_SHUTTER_RESID16_HEX: str = "0x669d"
P284_VALID_AEL_WITH_SHUTTER_MODES: Tuple[str, ...] = ("AUTO", "ON", "OFF")
P284_CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)

# Group C Constants (Wave 49 §1 — Still 2-Option RAW File Type, HLG Still Image, Color Space & AdobeRGB _DSC)
P284_STILL_RAW_FILE_TYPE_BKID: str = "BKID_APP_setting_still_raw_file_type"
P284_STILL_RAW_FILE_TYPE_RESID16_HEX: str = "0x6ff2"
P284_FX3_RAW_TWO_OPTIONS: Tuple[str, ...] = ("COMPRESSED", "UNCOMPRESSED")
P284_FX3_RAW_OPTION_RESIDS: Dict[str, str] = {
    "COMPRESSED": "0x6f67",
    "UNCOMPRESSED": "0x67a9",
}
P284_DORMANT_LOSSLESS_COMP_RESID16_HEX: str = "0x6b56"
P284_DORMANT_LOSSLESS_RAW_OPTIONS: Tuple[str, ...] = (
    "LOSSLESS_COMP",
    "LOSSLESS_COMPRESSED",
    "LOSSLESS_COMP_L",
    "LOSSLESS_COMP_M",
    "LOSSLESS_COMP_S",
)
P284_JH_FILE_TYPE_BKID: str = "BKID_APP_setting_jh_file_type"
P284_JH_FILE_TYPE_RESID16_HEX: str = "0x742a"
P284_VALID_JH_FILE_TYPES: Tuple[str, ...] = ("JPEG", "HEIF_420", "HEIF_422")
P284_VALID_STILL_FILE_FORMATS: Tuple[str, ...] = (
    "RAW",
    "RAW_AND_JPEG",
    "RAW_AND_HEIF",
    "JPEG",
    "HEIF",
)
P284_HLG_STILL_BKID: str = "BKID_APP_setting_still_hlg_photo"
P284_HLG_STILL_RESID16_HEX: str = "0x76c8"
P284_HLG_BT2020_RESID16_HEX: str = "0x79e1"
P284_PASM_EXPOSURE_MODES: Tuple[str, ...] = (
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "MANUAL_EXPOSURE",
)
P284_VALID_EXPOSURE_MODES: Tuple[str, ...] = P284_PASM_EXPOSURE_MODES + (
    "INTELLIGENT_AUTO",
    "FLEXIBLE_EXP",
)
P284_COLOR_SPACE_BKID: str = "BKID_APP_setting_still_color_space"
P284_COLOR_SPACE_RESID16_HEX: str = "0x68b7"
P284_VALID_COLOR_SPACES: Tuple[str, ...] = ("SRGB", "ADOBERGB")
P284_COLOR_SPACE_RESIDS: Dict[str, str] = {
    "SRGB": "0xe07d",
    "ADOBERGB": "0xe07e",
}
P284_SET_FILE_NAME_RESID16_HEX: str = "0x6993"
P284_DEFAULT_STILL_PREFIX: str = "DSC"
P284_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]{2}$")

# Group D Constants (Wave 49 §2 — 2-Option Shutter Type, 1/250s Flash Sync, 5-Lockout, Hi+ 10fps & Tier-0)
P284_SHUTTER_TYPE_BKID: str = "BKID_APP_setting_still_shutter_type"
P284_SHUTTER_TYPE_RESID16_HEX: str = "0x7aa9"
P284_FX3_SHUTTER_TWO_TYPES: Tuple[str, ...] = (
    "MECHANICAL_SHUTTER",
    "ELECTRONIC_SHUTTER",
)
P284_FX3_SHUTTER_TYPE_RESIDS: Dict[str, str] = {
    "MECHANICAL_SHUTTER": "0x6ddb",
    "ELECTRONIC_SHUTTER": "0x60a1",
}
P284_FORBIDDEN_SHUTTER_TYPE_AUTO: str = "AUTO"
P284_SILENT_MODE_RESID16_HEX: str = "0x7a53"
P284_E_FRONT_CURTAIN_BKID: str = "BKID_APP_setting_front_curtaion_shutter"
P284_E_FRONT_CURTAIN_RESID16_HEX: str = "0x64c6"
P284_MECHANICAL_FLASH_SYNC_DENOM_CEILING: int = 250
P284_FLASH_SYNC_RESID16_HEX: str = "0x759b"
P284_ELECTRONIC_SHUTTER_FIVE_LOCKOUTS: Tuple[str, ...] = (
    "FLASH",
    "LONG_EXPOSURE_NR",
    "E_FRONT_CURTAIN_SHUT",
    "BULB",
    "ANTI_FLICKER_SHOOT",
)
P284_LONG_EXPOSURE_NR_BKID: str = "BKID_APP_setting_long_exposure_nr"
P284_LONG_EXPOSURE_NR_RESID16_HEX: str = "0x6cd7"
P284_HIGH_ISO_NR_BKID: str = "BKID_APP_setting_high_iso_nr"
P284_HIGH_ISO_NR_RESID16_HEX: str = "0x650b"
P284_VALID_HIGH_ISO_NR_MODES: Tuple[str, ...] = ("OFF", "LOW", "NORMAL")
P284_DRIVE_MODE_BKID: str = "BKID_APP_setting_drive_mode"
P284_DRIVE_MODE_RESID16_HEX: str = "0x7228"
P284_CONT_HIP_RESID16_HEX: str = "0x68d1"
P284_DRIVE_EIGHT_MODES: Tuple[str, ...] = (
    "SINGLE_SHOOTING",
    "CONT_HI_PLUS",
    "CONT_HI",
    "CONT_MID",
    "CONT_LO",
    "SELF_TIMER_SINGLE",
    "SELF_TIMER_CONT",
    "CONT_BRACKET",
)
P284_CONT_HIP_MAX_FPS: int = 10
P284_AF_LOCK_APERTURE_THRESHOLD_F: float = 11.0

# Error Codes
P284_GA_ERR_MODEL_OR_FW_FLOOR: str = "P284_GA_ERR_MODEL_OR_FW_FLOOR"
P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING: str = (
    "P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING"
)
P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT: str = (
    "P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT"
)
P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP: str = (
    "P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP"
)
P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE: str = (
    "P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE"
)

P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE: str = (
    "P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE"
)
P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP: str = (
    "P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP"
)
P284_GB_ERR_CUSTOM_WB_RESET_OR_CAMSET_EXCLUSION: str = (
    "P284_GB_ERR_CUSTOM_WB_RESET_OR_CAMSET_EXCLUSION"
)
P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO: str = (
    "P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO"
)

P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF: str = (
    "P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF"
)
P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED: str = (
    "P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED"
)
P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX: str = (
    "P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX"
)

P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK: str = (
    "P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK"
)
P284_GD_ERR_FLASH_SYNC_1_250_OR_ELECTRONIC_5LOCKOUT: str = (
    "P284_GD_ERR_FLASH_SYNC_1_250_OR_ELECTRONIC_5LOCKOUT"
)
P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE: str = (
    "P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE"
)
P284_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P284_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)

_TRIVIAL_HEX64_SET = {"0" * 64, "f" * 64}


# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase284DonorInspectionResult:
    passed: bool
    verification_mode: str
    read_only_o_rdonly_enforced: bool
    elapsed_seconds: float
    within_150ms_budget: bool
    inspected_artifacts: Tuple[str, ...]
    fx3_im_elf_verified: bool
    fx3_libjiritsu_verified: bool
    fx3_libusbbuspower_verified: bool
    fx6_appfw_verified: bool
    fx6_wlan_rsrc_verified: bool
    fx3_upm_ko_verified: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P284CheckGroupAPpScinetoneLookDroLogResult:
    check_group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    sony_help_guide_id: str
    reset_action: str
    pp_bkid: str
    pp_resid16_hex: str
    factory_default_pp: str
    different_set_pp_checked: bool
    shoot_mode: str
    log_shooting_mode: str
    effective_picture_profile: str
    movie_picture_profile: str
    still_picture_profile: str
    creative_look: str
    exposed_creative_look_count: int
    dro_mode: str
    creative_look_and_dro_locked_out: bool
    pplut_movie_only_enforced: bool
    hdmi_output_resolution: str
    pplut_1080p_hdmi_clamp_verified: bool
    pp1_11_internal_params_survive_resets: bool
    different_set_checkmarks_survive_resets: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P284CheckGroupBWbCineEiCustom13MeteringResult:
    check_group_id: str
    passed: bool
    wb_resid16_hex: str
    log_shooting_mode: str
    picture_profile: str
    wb_mode: str
    wb_kelvin_k: int
    wb_ab_shift: int
    wb_gm_shift: int
    priority_set_in_awb: str
    shutter_awb_lock: str
    shockless_wb: str
    cine_ei_blocks_auto_and_underwater_wb: bool
    custom_wb_setup_requested: bool
    custom_wb_survives_camera_reset: bool
    custom_wb_excluded_from_camset: bool
    shutter_awb_lock_survives_camera_reset: bool
    metering_mode: str
    exposed_metering_modes: Tuple[str, ...]
    desqueeze_display: str
    face_priority_in_multi_metering: str
    spot_metering_point: str
    ael_with_shutter: str
    ael_with_shutter_survives_camera_reset: bool
    cine_ei_base_iso: int
    metering_drives_mm_only_in_cine_ei: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P284CheckGroupCRaw2OptionHlgAdobeRgbDscResult:
    check_group_id: str
    passed: bool
    fx3_mechanical_shutter_present: bool
    fx6_reference_mechanical_shutter: bool
    raw_file_type_resid16_hex: str
    exposed_raw_file_types: Tuple[str, ...]
    raw_file_type: str
    lossless_comp_exposed_in_fx3_ui: bool
    jh_file_type: str
    still_file_format: str
    exposure_mode: str
    hlg_still_image: str
    hlg_still_prerequisites_met: bool
    hlg_still_lockouts_enforced: bool
    color_space: str
    still_file_prefix: str
    effective_dcf_sample_filename: str
    adobergb_underscore_prefix_rule_verified: bool
    set_file_name_survives_camera_reset: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P284CheckGroupDShutterType5LockoutHipTier0Result:
    check_group_id: str
    passed: bool
    shutter_type_resid16_hex: str
    exposed_shutter_types: Tuple[str, ...]
    effective_shutter_type: str
    shutter_type_auto_exposed_in_fx3_ui: bool
    silent_mode: str
    audio_signals: str
    e_front_curtain_shutter: str
    e_front_curtain_survives_camera_reset: bool
    flash_sync_denominator: int
    flash_enabled: bool
    long_exposure_nr: str
    bulb_enabled: bool
    anti_flicker_shoot: str
    electronic_5function_lockout_verified: bool
    high_iso_nr: str
    drive_mode: str
    cont_fps: int
    aperture_f_number: float
    af_locked_to_first_frame_above_f11: bool
    passive_tx_bytes_emitted: int
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    tier0_receipt_present: bool
    tier0_receipt_verified: bool
    distinct_physical_media_verified: bool
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwPpScinetoneWbMeteringShutterTypeReport:
    schema: str
    phase_version: str
    verification_mode: str
    simulate_bench_dry_run: bool
    overall_status: str
    go_no_go: str
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    lossless_comp_exposed_in_fx3_ui: bool
    shutter_type_auto_exposed_in_fx3_ui: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    passive_tx_bytes_emitted: int
    check_group_count: int
    check_groups_passed: int
    all_4_check_groups_passed: bool
    tier0_receipt_verified: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    donor_inspection: Phase284DonorInspectionResult
    check_group_a_pp_scinetone_look_dro_log: P284CheckGroupAPpScinetoneLookDroLogResult
    check_group_b_wb_cine_ei_custom13_metering: P284CheckGroupBWbCineEiCustom13MeteringResult
    check_group_c_raw_2option_hlg_adobergb_dsc: P284CheckGroupCRaw2OptionHlgAdobeRgbDscResult
    check_group_d_shutter_type_5lockout_hip_tier0: P284CheckGroupDShutterType5LockoutHipTier0Result
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase284ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers & Bounded O_RDONLY Donor Inspection (< 0.15s)
# ---------------------------------------------------------------------------


def _norm_token(raw: str) -> str:
    return re.sub(r"[\s\-:/\.]+", "_", str(raw).strip().upper()).strip("_")


def _norm_creative_look(raw: str) -> str:
    s = str(raw).strip()
    if s == "-":
        return "-"
    return _norm_token(s)


def _norm_wb_mode(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "AWB": "AUTO",
        "AUTO": "AUTO",
        "UNDERWATER": "UNDERWATER_AUTO",
        "UNDERWATER_AUTO": "UNDERWATER_AUTO",
        "C_TEMP": "C_TEMP_FILTER",
        "C_TEMP_FILTER": "C_TEMP_FILTER",
        "CTEMP_FILTER": "C_TEMP_FILTER",
        "KELVIN": "C_TEMP_FILTER",
        "CUSTOM1": "CUSTOM_1",
        "CUSTOM_1": "CUSTOM_1",
        "CUSTOM2": "CUSTOM_2",
        "CUSTOM_2": "CUSTOM_2",
        "CUSTOM3": "CUSTOM_3",
        "CUSTOM_3": "CUSTOM_3",
    }
    return aliases.get(tok, tok)


def _norm_metering_mode(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "MULTI": "MULTI",
        "CENTER": "CENTER",
        "SPOT_STANDARD": "SPOT_STANDARD",
        "SPOT_STD": "SPOT_STANDARD",
        "SPOT_LARGE": "SPOT_LARGE",
        "ENTIRE_SCREEN_AVG": "ENTIRE_SCREEN_AVG",
        "ENTIRE_SCREEN_AVERAGE": "ENTIRE_SCREEN_AVG",
        "HIGHLIGHT": "HIGHLIGHT",
    }
    return aliases.get(tok, tok)


def _norm_still_format(raw: str) -> str:
    s = str(raw).strip().upper().replace("&", " AND ")
    tok = re.sub(r"[\s\-:/\.]+", "_", s).strip("_")
    aliases = {
        "RAW": "RAW",
        "RAW_AND_JPEG": "RAW_AND_JPEG",
        "RAW_JPEG": "RAW_AND_JPEG",
        "RAW_AND_HEIF": "RAW_AND_HEIF",
        "RAW_HEIF": "RAW_AND_HEIF",
        "JPEG": "JPEG",
        "HEIF": "HEIF",
    }
    return aliases.get(tok, tok)


def _norm_jh_type(raw: str) -> str:
    tok = re.sub(r"[\s\-:/\.()]+", "_", str(raw).strip().upper()).strip("_")
    aliases = {
        "JPEG": "JPEG",
        "HEIF_420": "HEIF_420",
        "HEIF_4_2_0": "HEIF_420",
        "HEIF_422": "HEIF_422",
        "HEIF_4_2_2": "HEIF_422",
    }
    return aliases.get(tok, tok)


def _norm_shutter_type(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "MECHANICAL": "MECHANICAL_SHUTTER",
        "MECHANICAL_SHUTTER": "MECHANICAL_SHUTTER",
        "ELECTRONIC": "ELECTRONIC_SHUTTER",
        "ELECTRONIC_SHUTTER": "ELECTRONIC_SHUTTER",
        "AUTO": "AUTO",
    }
    return aliases.get(tok, tok)


def _canonical_sha256_dict(obj: Mapping[str, Any], exclude_key: Optional[str] = None) -> str:
    body = dict(copy.deepcopy(obj))
    if exclude_key:
        body.pop(exclude_key, None)
    donor_sub = body.get("donor_inspection")
    if isinstance(donor_sub, dict):
        donor_sub.pop("elapsed_seconds", None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _is_trivial_hex64(val: str) -> bool:
    norm = str(val).strip().lower()
    if not HEX64_RE.match(norm):
        return True
    return norm in _TRIVIAL_HEX64_SET


def inspect_phase284_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase284DonorInspectionResult:
    """Inspect local BYOF donors strictly via O_RDONLY within < 0.15s, or Clean-Room fallback."""
    t0 = time.perf_counter()
    errors: List[str] = []
    eff_clean = force_clean_room if force_clean_room is not None else synthetic_clean_room
    env_clean_room = is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )
    clean_room = env_clean_room if eff_clean is None else bool(eff_clean)

    fx3_im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False)
    fx3_jit_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=False)
    fx3_usb_pwr_path = resolve_work_subpath(FX3_LIBUSBBUSPOWER_RELPATH, require_file=False)
    fx6_appfw_path = fx6_lib_dir / "appFw.so"
    fx6_wlan_path = fx6_lib_dir / "libWlanResource.so"
    fx3_upm_path = fx3_modules_dir / "upm.ko"

    donors_present = (
        fx3_im_path.is_file()
        and fx3_jit_path.is_file()
        and fx3_usb_pwr_path.is_file()
        and fx6_appfw_path.is_file()
        and fx6_wlan_path.is_file()
        and fx3_upm_path.is_file()
    )

    if eff_clean is False and not donors_present:
        elapsed = round(time.perf_counter() - t0, 6)
        return Phase284DonorInspectionResult(
            passed=False,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            read_only_o_rdonly_enforced=True,
            elapsed_seconds=elapsed,
            within_150ms_budget=(elapsed < max_seconds),
            inspected_artifacts=(),
            fx3_im_elf_verified=fx3_im_path.is_file(),
            fx3_libjiritsu_verified=fx3_jit_path.is_file(),
            fx3_libusbbuspower_verified=fx3_usb_pwr_path.is_file(),
            fx6_appfw_verified=fx6_appfw_path.is_file(),
            fx6_wlan_rsrc_verified=fx6_wlan_path.is_file(),
            fx3_upm_ko_verified=fx3_upm_path.is_file(),
            raw_firmware_bytes_leaked=PHASE284_RAW_FIRMWARE_BYTES_LEAKED,
            errors=(f"Local BYOF donors missing under fx6_lib_dir={fx6_lib_dir}",),
        )

    use_live = (not clean_room) and donors_present
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"
    inspected: List[str] = []

    if use_live:
        im_sz, im_sha, im_head = read_only_o_rdonly_digest_and_header(fx3_im_path)
        im_mag, im_64, im_mach, _ = _parse_elf64_header_and_pt_load(im_head)
        im_ok = (
            im_sz == FX3_IM_ELF_EXPECTED_SIZE
            and im_sha == FX3_IM_ELF_EXPECTED_SHA256
            and im_mag
            and im_64
            and im_mach == EM_AARCH64
        )
        inspected.append("im.elf")
        if not im_ok:
            errors.append(f"im.elf O_RDONLY verification failed: size={im_sz}")

        jit_sz, jit_sha, jit_head = read_only_o_rdonly_digest_and_header(fx3_jit_path)
        jit_mag, jit_64, jit_mach, _ = _parse_elf64_header_and_pt_load(jit_head)
        jit_ok = (
            jit_sz == LIBJIRITSU_EXPECTED_SIZE
            and jit_sha == LIBJIRITSU_EXPECTED_SHA256
            and jit_mag
            and jit_64
            and jit_mach == EM_AARCH64
        )
        inspected.append("libJiritsu.so")
        if not jit_ok:
            errors.append(f"libJiritsu.so O_RDONLY verification failed: size={jit_sz}")

        pwr_sz, pwr_sha, pwr_head = read_only_o_rdonly_digest_and_header(fx3_usb_pwr_path)
        pwr_mag, pwr_64, pwr_mach, _ = _parse_elf64_header_and_pt_load(pwr_head)
        pwr_ok = (
            pwr_sz == FX3_LIBUSBBUSPOWER_EXPECTED_SIZE
            and pwr_sha == FX3_LIBUSBBUSPOWER_EXPECTED_SHA256
            and pwr_mag
            and pwr_64
            and pwr_mach == EM_AARCH64
        )
        inspected.append("libUsbBusPower.so")
        if not pwr_ok:
            errors.append(f"libUsbBusPower.so O_RDONLY verification failed: size={pwr_sz}")

        appfw_sz, appfw_head, _ = _read_bounded_slice_o_rdonly(fx6_appfw_path, 4096)
        appfw_mag, appfw_64, appfw_mach, _ = _parse_elf64_header_and_pt_load(appfw_head)
        appfw_ok = (
            appfw_sz == FX6_APPFW_EXPECTED_SIZE
            and appfw_mag
            and appfw_64
            and appfw_mach == EM_AARCH64
        )
        inspected.append("appFw.so(bounded-4KiB)")
        if not appfw_ok:
            errors.append(f"appFw.so bounded O_RDONLY header failed: size={appfw_sz}")

        wlan_sz, wlan_sha, wlan_head = read_only_o_rdonly_digest_and_header(fx6_wlan_path)
        wlan_mag, wlan_64, wlan_mach, _ = _parse_elf64_header_and_pt_load(wlan_head)
        wlan_ok = (
            wlan_sz > 0
            and wlan_sha == FX6_WLAN_RSRC_DONOR_SHA256
            and wlan_mag
            and wlan_64
            and wlan_mach == EM_AARCH64
        )
        inspected.append("libWlanResource.so")
        if not wlan_ok:
            errors.append("libWlanResource.so O_RDONLY SHA-256 verification failed")

        upm_sz, upm_head, _ = _read_bounded_slice_o_rdonly(fx3_upm_path, 4096)
        upm_mag, upm_64, upm_mach, _ = _parse_elf64_header_and_pt_load(upm_head)
        upm_ok = upm_sz > 0 and upm_mag and upm_64 and upm_mach == EM_AARCH64
        inspected.append("upm.ko(bounded-4KiB)")
        if not upm_ok:
            errors.append(f"upm.ko bounded O_RDONLY header failed: size={upm_sz}")
    else:
        im_ok = jit_ok = pwr_ok = appfw_ok = wlan_ok = upm_ok = True
        inspected.extend(
            [
                "synthetic_clean_room:im.elf",
                "synthetic_clean_room:libJiritsu.so",
                "synthetic_clean_room:libUsbBusPower.so",
                "synthetic_clean_room:appFw.so",
                "synthetic_clean_room:libWlanResource.so",
                "synthetic_clean_room:upm.ko",
            ]
        )

    elapsed = round(time.perf_counter() - t0, 6)
    within_budget = elapsed < max_seconds
    if not within_budget:
        errors.append(f"Bounded donor inspection exceeded {max_seconds}s: {elapsed}s")

    return Phase284DonorInspectionResult(
        passed=(
            im_ok
            and jit_ok
            and pwr_ok
            and appfw_ok
            and wlan_ok
            and upm_ok
            and within_budget
            and len(errors) == 0
        ),
        verification_mode=mode,
        read_only_o_rdonly_enforced=True,
        elapsed_seconds=elapsed,
        within_150ms_budget=within_budget,
        inspected_artifacts=tuple(inspected),
        fx3_im_elf_verified=im_ok,
        fx3_libjiritsu_verified=jit_ok,
        fx3_libusbbuspower_verified=pwr_ok,
        fx6_appfw_verified=appfw_ok,
        fx6_wlan_rsrc_verified=wlan_ok,
        fx3_upm_ko_verified=upm_ok,
        raw_firmware_bytes_leaked=PHASE284_RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group A (Wave 48 §1 — Out-of-Box PP11 S-Cinetone, Creative Look, DRO, Log Lockout & PP Reset Trap)
# ---------------------------------------------------------------------------


def evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P284_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    pp_bkid: str = P284_PP_BKID,
    pp_resid16_hex: str = P284_PP_RESID16_HEX,
    factory_default_pp: str = P284_PP_DEFAULT_PROFILE,
    different_set_pp_checked: bool = False,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    movie_picture_profile: Optional[str] = None,
    still_picture_profile: Optional[str] = None,
    creative_look: str = P284_CREATIVE_LOOK_LOCKED_DASH,
    exposed_creative_looks: Sequence[str] = P284_CREATIVE_LOOK_TEN_PRESETS,
    dro_mode: str = "OFF",
    hlg_still_image: str = "OFF",
    movie_gamma_display_assist: str = "OFF",
    internal_recording_active: bool = True,
    hdmi_output_resolution: str = "1080P",
    expect_creative_look_or_dro_active_with_pp_or_log: bool = False,
    expect_pplut_in_still: bool = False,
    pp1_11_custom_params_modified: bool = True,
    pp_individual_reset_executed: bool = False,
    claimed_pp1_11_internal_params_wiped: bool = False,
    claimed_diff_set_checkmarks_wiped: bool = False,
    claimed_pp_active_selector_remains_non_pp11_after_camera_reset: bool = False,
) -> P284CheckGroupAPpScinetoneLookDroLogResult:
    """Validate Wave 48 §1: PP11 S-Cinetone default, Creative Look/DRO mutual exclusivity, Log lockout & PP reset trap."""
    errors: List[str] = []

    fw_tuple = _parse_fw_tuple(body_fw)
    if body_model_id != TARGET_MODEL_ID_INT or fw_tuple is None or fw_tuple < MIN_BODY_FW_TUPLE:
        errors.append(
            f"{P284_GA_ERR_MODEL_OR_FW_FLOOR}: model=0x{body_model_id:08x}, fw={body_fw!r} "
            f"(requires 0x{TARGET_MODEL_ID_INT:08x} & >= 2.04)"
        )
    if str(sony_help_guide_id).strip() != P284_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P284_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id={sony_help_guide_id!r} != {P284_SONY_HELP_GUIDE_ID!r}"
        )

    norm_reset = _norm_token(reset_action)
    if norm_reset not in P284_VALID_RESET_ACTIONS:
        errors.append(
            f"{P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE}: invalid reset_action={reset_action!r}"
        )

    norm_shoot = _norm_token(shoot_mode)
    if norm_shoot not in P284_VALID_SHOOT_MODES:
        errors.append(
            f"{P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING}: invalid shoot_mode={shoot_mode!r}"
        )

    norm_log = _norm_token(log_shooting_mode)
    if norm_log not in P284_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: invalid log_shooting_mode={log_shooting_mode!r}"
        )

    norm_factory_pp = _norm_token(factory_default_pp)
    norm_pp = _norm_token(picture_profile)
    norm_mv_pp = norm_pp if movie_picture_profile is None else _norm_token(movie_picture_profile)
    norm_st_pp = norm_pp if still_picture_profile is None else _norm_token(still_picture_profile)
    norm_look = _norm_creative_look(creative_look)
    norm_dro = _norm_token(dro_mode)
    norm_hlg_still = _norm_token(hlg_still_image)
    norm_gamma_assist = _norm_token(movie_gamma_display_assist)
    norm_hdmi_res = _norm_token(hdmi_output_resolution)
    norm_exposed_looks = tuple(_norm_creative_look(x) for x in exposed_creative_looks)

    if pp_bkid != P284_PP_BKID or pp_resid16_hex.lower() != P284_PP_RESID16_HEX:
        errors.append(
            f"{P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING}: BKID/resid16 mismatch ({pp_bkid}/{pp_resid16_hex})"
        )
    if norm_factory_pp != P284_PP_DEFAULT_PROFILE:
        errors.append(
            f"{P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING}: stock FX3 out-of-box default must be PP11 (S-Cinetone), got {factory_default_pp!r}"
        )
    if norm_pp not in P284_VALID_PICTURE_PROFILES:
        errors.append(
            f"{P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING}: unknown picture_profile={picture_profile!r}"
        )
    if norm_mv_pp not in P284_VALID_PICTURE_PROFILES or norm_st_pp not in P284_VALID_PICTURE_PROFILES:
        errors.append(
            f"{P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING}: invalid movie/still PP ({movie_picture_profile!r}/{still_picture_profile!r})"
        )

    if not different_set_pp_checked:
        if norm_mv_pp != norm_pp or norm_st_pp != norm_pp:
            errors.append(
                f"{P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING}: Movie ({norm_mv_pp}) & Still ({norm_st_pp}) must share Picture Profile ({norm_pp}) when [Different Set for Still/Mv] is unchecked"
            )

    effective_pp = norm_st_pp if (different_set_pp_checked and norm_shoot == "PHOTO") else (
        norm_mv_pp if different_set_pp_checked else norm_pp
    )

    # Creative Look & DRO checks
    if norm_exposed_looks != P284_CREATIVE_LOOK_TEN_PRESETS:
        errors.append(
            f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: Creative Look must expose 10 presets ST..SE, got {exposed_creative_looks!r}"
        )
    if norm_dro not in P284_DRO_VALID_MODES:
        errors.append(
            f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: invalid dro_mode={dro_mode!r}"
        )

    log_active = norm_log in P284_ACTIVE_LOG_SHOOTING_MODES
    if expect_creative_look_or_dro_active_with_pp_or_log:
        errors.append(
            f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: Creative Look & DRO cannot be active alongside [Picture Profile]!=Off or [Log Shooting]!=Off"
        )

    creative_look_dro_locked = False
    if log_active:
        creative_look_dro_locked = True
        if effective_pp != "OFF":
            errors.append(
                f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: [Log Shooting]={norm_log} locks [Picture Profile]=Off, got {effective_pp}"
            )
        if norm_look != P284_CREATIVE_LOOK_LOCKED_DASH:
            errors.append(
                f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: [Log Shooting]={norm_log} locks [Creative Look]='-', got {creative_look!r}"
            )
        if norm_dro != "OFF":
            errors.append(
                f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: [Log Shooting]={norm_log} locks [D-Range Optimizer]=Off, got {dro_mode!r}"
            )
        if norm_gamma_assist != "OFF":
            errors.append(
                f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: [Log Shooting]={norm_log} locks movie [Gamma Display Assist]=Off, got {movie_gamma_display_assist!r}"
            )
    elif effective_pp != "OFF":
        creative_look_dro_locked = True
        if norm_look != P284_CREATIVE_LOOK_LOCKED_DASH:
            errors.append(
                f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: [Picture Profile]={effective_pp} locks [Creative Look]='-', got {creative_look!r}"
            )
        if norm_dro != "OFF":
            errors.append(
                f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: [Picture Profile]={effective_pp} locks [D-Range Optimizer]=Off, got {dro_mode!r}"
            )
    else:
        if norm_look not in P284_CREATIVE_LOOK_TEN_PRESETS:
            errors.append(
                f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: when Log=Off & PP=Off, Creative Look must be one of {P284_CREATIVE_LOOK_TEN_PRESETS}, got {creative_look!r}"
            )
        if norm_hlg_still == "ON" and norm_shoot == "PHOTO" and norm_dro != "OFF":
            errors.append(
                f"{P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT}: [HLG Still Image]=On locks out [DRO], got {dro_mode!r}"
            )

    # PPLUT1..4 Movie-only & 1080p HDMI clamp
    pplut_movie_only_ok = True
    if (
        expect_pplut_in_still
        or ((different_set_pp_checked or still_picture_profile is not None) and norm_st_pp in P284_PPLUT_PROFILES)
        or (norm_shoot == "PHOTO" and effective_pp in P284_PPLUT_PROFILES)
    ):
        pplut_movie_only_ok = False
        errors.append(
            f"{P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP}: PPLUT1..4 are Movie-only (invalid in Still mode)"
        )

    pplut_1080p_clamp_ok = True
    if effective_pp in P284_PPLUT_PROFILES and internal_recording_active and norm_hdmi_res == "2160P":
        pplut_1080p_clamp_ok = False
        errors.append(
            f"{P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP}: PPLUT1..4 + internal recording clamps HDMI to 1080p (2160P rejected)"
        )

    # PP1..11 Internal Reset Trap & Different Set check mark persistence
    pp1_11_survives = not claimed_pp1_11_internal_params_wiped
    diff_set_survives = not claimed_diff_set_checkmarks_wiped
    if norm_reset in ("CAMERA_SETTINGS_RESET", "INITIALIZE") and not pp_individual_reset_executed:
        if pp1_11_custom_params_modified and claimed_pp1_11_internal_params_wiped:
            errors.append(
                f"{P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE}: PP1..11 customized internal parameters survive {norm_reset} (per-profile [Reset] required)"
            )
        if claimed_diff_set_checkmarks_wiped:
            errors.append(
                f"{P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE}: [Different Set for Still/Mv] check marks survive {norm_reset}"
            )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_pp_active_selector_remains_non_pp11_after_camera_reset:
        errors.append(
            f"{P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE}: [Camera Settings Reset] restores active PP selector to stock PP11 even though internal params survive"
        )

    return P284CheckGroupAPpScinetoneLookDroLogResult(
        check_group_id=P284_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        body_model_id_hex=f"0x{body_model_id:08x}",
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=norm_reset,
        pp_bkid=pp_bkid,
        pp_resid16_hex=pp_resid16_hex,
        factory_default_pp=norm_factory_pp,
        different_set_pp_checked=different_set_pp_checked,
        shoot_mode=norm_shoot,
        log_shooting_mode=norm_log,
        effective_picture_profile=effective_pp,
        movie_picture_profile=norm_mv_pp,
        still_picture_profile=norm_st_pp,
        creative_look=norm_look,
        exposed_creative_look_count=len(norm_exposed_looks),
        dro_mode=norm_dro,
        creative_look_and_dro_locked_out=creative_look_dro_locked,
        pplut_movie_only_enforced=pplut_movie_only_ok,
        hdmi_output_resolution=norm_hdmi_res,
        pplut_1080p_hdmi_clamp_verified=pplut_1080p_clamp_ok,
        pp1_11_internal_params_survive_resets=pp1_11_survives,
        different_set_checkmarks_survive_resets=diff_set_survives,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B (Wave 48 §2 — White Balance, Cine EI, Custom 1..3, Metering 6-Mode, M.M.)
# ---------------------------------------------------------------------------


def evaluate_p284_check_group_b_wb_and_metering(
    *,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    reset_action: str = "NONE",
    wb_resid16_hex: str = P284_WB_RESID16_HEX,
    wb_mode: str = "C_TEMP_FILTER",
    wb_kelvin_k: int = 5600,
    wb_ab_shift: int = 0,
    wb_gm_shift: int = 0,
    priority_set_in_awb: str = "STANDARD",
    shutter_awb_lock: str = "OFF",
    shockless_wb: str = "1",
    custom_wb_setup_requested: bool = False,
    custom_wb_survives_camera_reset: bool = True,
    custom_wb_excluded_from_camset: bool = True,
    shutter_awb_lock_survives_camera_reset: bool = True,
    claimed_custom_wb_saved_in_camset: bool = False,
    claimed_custom_wb_wiped_by_camera_reset: bool = False,
    metering_mode: str = "MULTI",
    exposed_metering_modes: Sequence[str] = P284_METERING_SIX_MODES,
    desqueeze_display: str = "OFF",
    face_priority_in_multi_metering: str = "ON",
    spot_metering_point: str = "CENTER",
    ael_with_shutter: str = "AUTO",
    ael_with_shutter_survives_camera_reset: bool = True,
    cine_ei_base_iso: int = 800,
    expect_metering_changes_cine_ei_iso: bool = False,
) -> P284CheckGroupBWbCineEiCustom13MeteringResult:
    """Validate Wave 48 §2: WB Kelvin/filter grid, Cine EI restrictions, Custom 1..3 & 6-mode Metering / M.M."""
    errors: List[str] = []

    norm_shoot = _norm_token(shoot_mode)
    norm_log = _norm_token(log_shooting_mode)
    norm_pp = _norm_token(picture_profile)
    norm_reset = _norm_token(reset_action)
    norm_wb = _norm_wb_mode(wb_mode)
    norm_priority_awb = _norm_token(priority_set_in_awb)
    norm_shutter_awb = _norm_token(shutter_awb_lock)
    norm_shockless = _norm_token(shockless_wb)
    norm_metering = _norm_metering_mode(metering_mode)
    norm_exposed_metering = tuple(_norm_metering_mode(m) for m in exposed_metering_modes)
    norm_desqueeze = _norm_token(desqueeze_display)
    norm_face_prio = _norm_token(face_priority_in_multi_metering)
    norm_spot_pt = _norm_token(spot_metering_point)
    norm_ael = _norm_token(ael_with_shutter)

    if wb_resid16_hex.lower() != P284_WB_RESID16_HEX:
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: wb_resid16_hex={wb_resid16_hex!r} != {P284_WB_RESID16_HEX!r}"
        )
    if norm_wb not in P284_WB_VALID_MODES:
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: invalid wb_mode={wb_mode!r}"
        )
    if norm_wb == "FLASH" and norm_shoot != "PHOTO":
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: Flash WB is Still-only (invalid in {norm_shoot})"
        )
    if (
        wb_kelvin_k < P284_WB_KELVIN_MIN_K
        or wb_kelvin_k > P284_WB_KELVIN_MAX_K
        or (wb_kelvin_k % P284_WB_KELVIN_STEP_K) != 0
    ):
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: wb_kelvin_k={wb_kelvin_k} must be 2500..9900K in 100K steps"
        )
    if not (P284_WB_AB_MIN <= wb_ab_shift <= P284_WB_AB_MAX):
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: wb_ab_shift={wb_ab_shift} out of A7..B7 (-7..7)"
        )
    if not (P284_WB_GM_MIN <= wb_gm_shift <= P284_WB_GM_MAX):
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: wb_gm_shift={wb_gm_shift} out of G7..M7 (-7..7)"
        )
    if norm_priority_awb not in P284_VALID_PRIORITY_AWB_MODES:
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: invalid priority_set_in_awb={priority_set_in_awb!r}"
        )
    if norm_shutter_awb not in P284_VALID_SHUTTER_AWB_LOCK_MODES:
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: invalid shutter_awb_lock={shutter_awb_lock!r}"
        )
    if norm_shockless not in P284_VALID_SHOCKLESS_WB_MODES:
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: invalid shockless_wb={shockless_wb!r}"
        )
    if not shutter_awb_lock_survives_camera_reset:
        errors.append(
            f"{P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE}: [Shutter AWB Lock] is NOT resettable by [Camera Settings Reset]"
        )

    # Cine EI / Cine EI Quick blocks Auto & Underwater Auto; Custom Setup error trap
    cine_ei_blocks_auto = norm_log in ("CINE_EI", "CINE_EI_QUICK")
    if cine_ei_blocks_auto and norm_wb in P284_WB_CINE_EI_BLOCKED_MODES:
        errors.append(
            f"{P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP}: {norm_log} blocks {norm_wb} White Balance"
        )
    if custom_wb_setup_requested and (
        norm_log in P284_ACTIVE_LOG_SHOOTING_MODES
        or norm_pp in P284_SLOG3_PROFILES
        or norm_pp in P284_PPLUT_PROFILES
    ):
        errors.append(
            f"{P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP}: [Custom Setup] triggers error trap while Log Shooting={norm_log} or PP={norm_pp} (S-Log3/PPLUT)"
        )

    # Custom 1..3 persistence & CAMSET exclusion
    if (
        not custom_wb_survives_camera_reset
        or claimed_custom_wb_wiped_by_camera_reset
        or (norm_reset == "CAMERA_SETTINGS_RESET" and not custom_wb_survives_camera_reset)
    ):
        errors.append(
            f"{P284_GB_ERR_CUSTOM_WB_RESET_OR_CAMSET_EXCLUSION}: Custom 1..3 WB data survives [Camera Settings Reset]"
        )
    if not custom_wb_excluded_from_camset or claimed_custom_wb_saved_in_camset:
        errors.append(
            f"{P284_GB_ERR_CUSTOM_WB_RESET_OR_CAMSET_EXCLUSION}: Custom 1..3 WB is excluded from CAMSET [Save/Load Settings]"
        )

    # Metering 6-Mode, Face Priority vs De-Squeeze, Spot Metering Point, AEL w/ Shutter, Cine EI M.M.
    if norm_exposed_metering != P284_METERING_SIX_MODES:
        errors.append(
            f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: Metering Mode must expose all 6 modes {P284_METERING_SIX_MODES}, got {exposed_metering_modes!r}"
        )
    if norm_metering not in P284_METERING_SIX_MODES:
        errors.append(
            f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: invalid metering_mode={metering_mode!r}"
        )
    if norm_face_prio not in ("ON", "OFF"):
        errors.append(
            f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: invalid face_priority_in_multi_metering={face_priority_in_multi_metering!r}"
        )
    if norm_desqueeze != "OFF" and norm_face_prio != "OFF":
        errors.append(
            f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: [Face Priority in Multi Metering] is forced Off when [De-Squeeze Display]={norm_desqueeze}"
        )
    if norm_spot_pt not in P284_VALID_SPOT_METERING_POINTS:
        errors.append(
            f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: invalid spot_metering_point={spot_metering_point!r}"
        )
    if norm_ael not in P284_VALID_AEL_WITH_SHUTTER_MODES:
        errors.append(
            f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: invalid ael_with_shutter={ael_with_shutter!r}"
        )
    if not ael_with_shutter_survives_camera_reset:
        errors.append(
            f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: [AEL w/ Shutter] is NOT resettable by [Camera Settings Reset]"
        )

    mm_only_in_cine_ei = False
    if norm_log in ("CINE_EI", "CINE_EI_QUICK"):
        mm_only_in_cine_ei = not expect_metering_changes_cine_ei_iso
        if cine_ei_base_iso not in P284_CINE_EI_BASE_ISOS:
            errors.append(
                f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: Cine EI Base ISO must be 800 or 12800, got {cine_ei_base_iso}"
            )
        if expect_metering_changes_cine_ei_iso:
            errors.append(
                f"{P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO}: in Cine EI, metering drives M.M. indicator only and never alters Base ISO gain"
            )

    return P284CheckGroupBWbCineEiCustom13MeteringResult(
        check_group_id=P284_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        wb_resid16_hex=wb_resid16_hex,
        log_shooting_mode=norm_log,
        picture_profile=norm_pp,
        wb_mode=norm_wb,
        wb_kelvin_k=wb_kelvin_k,
        wb_ab_shift=wb_ab_shift,
        wb_gm_shift=wb_gm_shift,
        priority_set_in_awb=norm_priority_awb,
        shutter_awb_lock=norm_shutter_awb,
        shockless_wb=norm_shockless,
        cine_ei_blocks_auto_and_underwater_wb=cine_ei_blocks_auto,
        custom_wb_setup_requested=custom_wb_setup_requested,
        custom_wb_survives_camera_reset=custom_wb_survives_camera_reset,
        custom_wb_excluded_from_camset=custom_wb_excluded_from_camset,
        shutter_awb_lock_survives_camera_reset=shutter_awb_lock_survives_camera_reset,
        metering_mode=norm_metering,
        exposed_metering_modes=norm_exposed_metering,
        desqueeze_display=norm_desqueeze,
        face_priority_in_multi_metering=norm_face_prio,
        spot_metering_point=norm_spot_pt,
        ael_with_shutter=norm_ael,
        ael_with_shutter_survives_camera_reset=ael_with_shutter_survives_camera_reset,
        cine_ei_base_iso=cine_ei_base_iso,
        metering_drives_mm_only_in_cine_ei=mm_only_in_cine_ei,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C (Wave 49 §1 — Still 2-Option RAW File Type, HLG Still Image, & DCF 2.0 AdobeRGB _DSC)
# ---------------------------------------------------------------------------


def evaluate_p284_check_group_c_raw_hlg_and_colorspace(
    *,
    fx3_mechanical_shutter_present: bool = True,
    fx6_reference_mechanical_shutter: bool = False,
    raw_file_type_resid16_hex: str = P284_STILL_RAW_FILE_TYPE_RESID16_HEX,
    exposed_raw_file_types: Sequence[str] = P284_FX3_RAW_TWO_OPTIONS,
    raw_file_type: str = "COMPRESSED",
    lossless_comp_exposed_in_fx3_ui: bool = False,
    expect_lossless_comp_raw: bool = False,
    jh_file_type: str = "JPEG",
    still_file_format: str = "RAW",
    exposure_mode: str = "MANUAL_EXPOSURE",
    hlg_still_image: str = "OFF",
    picture_profile: str = "OFF",
    creative_look: str = P284_CREATIVE_LOOK_LOCKED_DASH,
    dro_mode: str = "OFF",
    dro_bracket_active: bool = False,
    color_space: str = "SRGB",
    still_file_prefix: str = P284_DEFAULT_STILL_PREFIX,
    expected_dcf_sample_filename: str = "DSC00001.ARW",
    set_file_name_survives_camera_reset: bool = True,
) -> P284CheckGroupCRaw2OptionHlgAdobeRgbDscResult:
    """Validate Wave 49 §1: 2-option Still RAW vs dormant Lossless Comp, HLG Still Image, & AdobeRGB _DSC rule."""
    errors: List[str] = []

    norm_exposed_raw = tuple(_norm_token(x) for x in exposed_raw_file_types)
    norm_raw_type = _norm_token(raw_file_type)
    norm_jh = _norm_jh_type(jh_file_type)
    norm_fmt = _norm_still_format(still_file_format)
    norm_exp = _norm_token(exposure_mode)
    norm_hlg = _norm_token(hlg_still_image)
    norm_pp = _norm_token(picture_profile)
    norm_look = _norm_creative_look(creative_look)
    norm_dro = _norm_token(dro_mode)
    norm_cs = _norm_token(color_space)
    prefix = str(still_file_prefix).strip()
    sample_fn = str(expected_dcf_sample_filename).strip()

    if not fx3_mechanical_shutter_present or fx6_reference_mechanical_shutter:
        errors.append(
            f"{P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF}: ILME-FX3 has mechanical shutter (True) vs Still-less ILME-FX6 (False)"
        )
    if raw_file_type_resid16_hex.lower() != P284_STILL_RAW_FILE_TYPE_RESID16_HEX:
        errors.append(
            f"{P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF}: RAW File Type resid16 mismatch ({raw_file_type_resid16_hex!r})"
        )
    if norm_exposed_raw != P284_FX3_RAW_TWO_OPTIONS:
        errors.append(
            f"{P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF}: FX3 exposes ONLY 2 RAW options {P284_FX3_RAW_TWO_OPTIONS}, got {exposed_raw_file_types!r}"
        )
    if lossless_comp_exposed_in_fx3_ui or expect_lossless_comp_raw or (
        norm_raw_type in P284_DORMANT_LOSSLESS_RAW_OPTIONS
    ):
        errors.append(
            f"{P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF}: dormant Lossless Comp (0x6b56) is NOT exposed on stock ILME-FX3"
        )
    if norm_raw_type not in P284_FX3_RAW_TWO_OPTIONS:
        errors.append(
            f"{P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF}: invalid raw_file_type={raw_file_type!r}"
        )

    if norm_jh not in P284_VALID_JH_FILE_TYPES:
        errors.append(
            f"{P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED}: invalid jh_file_type={jh_file_type!r}"
        )
    if norm_fmt not in P284_VALID_STILL_FILE_FORMATS:
        errors.append(
            f"{P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED}: invalid still_file_format={still_file_format!r}"
        )
    if norm_exp not in P284_VALID_EXPOSURE_MODES:
        errors.append(
            f"{P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED}: invalid exposure_mode={exposure_mode!r}"
        )
    if norm_hlg not in ("ON", "OFF"):
        errors.append(
            f"{P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED}: invalid hlg_still_image={hlg_still_image!r}"
        )

    hlg_prereq_ok = True
    hlg_lockouts_ok = True
    if norm_hlg == "ON":
        if (
            norm_jh not in ("HEIF_420", "HEIF_422")
            or norm_fmt != "HEIF"
            or norm_exp not in P284_PASM_EXPOSURE_MODES
        ):
            hlg_prereq_ok = False
            errors.append(
                f"{P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED}: [HLG Still Image]=On requires HEIF (4:2:0/4:2:2), [File Format]=HEIF-only, and P/A/S/M mode"
            )
        if (
            norm_pp != "OFF"
            or norm_look != P284_CREATIVE_LOOK_LOCKED_DASH
            or norm_dro != "OFF"
            or dro_bracket_active
        ):
            hlg_lockouts_ok = False
            errors.append(
                f"{P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED}: [HLG Still Image]=On locks out Picture Profile, Creative Look, DRO & DRO Bracket"
            )

    if norm_cs not in P284_VALID_COLOR_SPACES:
        errors.append(
            f"{P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX}: invalid color_space={color_space!r}"
        )
    if not P284_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE.match(prefix):
        errors.append(
            f"{P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX}: [Set File Name] prefix {still_file_prefix!r} must be 3 ASCII chars without leading '_'"
        )
    if not set_file_name_survives_camera_reset:
        errors.append(
            f"{P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX}: [Set File Name] prefix is NOT resettable by [Camera Settings Reset]"
        )

    dcf_rule_ok = True
    if norm_fmt != "HEIF":
        if norm_cs == "ADOBERGB":
            if not sample_fn.startswith("_"):
                dcf_rule_ok = False
                errors.append(
                    f"{P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX}: AdobeRGB requires DCF 2.0 leading '_' filename (_DSC0001), got {sample_fn!r}"
                )
        elif norm_cs == "SRGB":
            if sample_fn.startswith("_") or not sample_fn.startswith(prefix):
                dcf_rule_ok = False
                errors.append(
                    f"{P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX}: sRGB filename must start with {prefix!r} without leading '_', got {sample_fn!r}"
                )

    return P284CheckGroupCRaw2OptionHlgAdobeRgbDscResult(
        check_group_id=P284_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        fx3_mechanical_shutter_present=fx3_mechanical_shutter_present,
        fx6_reference_mechanical_shutter=fx6_reference_mechanical_shutter,
        raw_file_type_resid16_hex=raw_file_type_resid16_hex,
        exposed_raw_file_types=norm_exposed_raw,
        raw_file_type=norm_raw_type,
        lossless_comp_exposed_in_fx3_ui=lossless_comp_exposed_in_fx3_ui,
        jh_file_type=norm_jh,
        still_file_format=norm_fmt,
        exposure_mode=norm_exp,
        hlg_still_image=norm_hlg,
        hlg_still_prerequisites_met=hlg_prereq_ok,
        hlg_still_lockouts_enforced=hlg_lockouts_ok,
        color_space=norm_cs,
        still_file_prefix=prefix,
        effective_dcf_sample_filename=sample_fn,
        adobergb_underscore_prefix_rule_verified=dcf_rule_ok,
        set_file_name_survives_camera_reset=set_file_name_survives_camera_reset,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group D (Wave 49 §2 — Shutter Type 2-Option No-Auto, 1/250s Flash Sync, 5-Lockout, Hi+ 10fps & Tier-0)
# ---------------------------------------------------------------------------


def build_simulated_phase284_tier0_receipts(
    *,
    body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    body_fw: str = TARGET_BODY_FW,
) -> Tuple[bytes, bytes, Dict[str, str]]:
    """Build deterministic in-memory 528 B FX3RCPT1 dual receipts for `--simulate-bench-dry-run`."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE284_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE284_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
    *,
    shutter_type_resid16_hex: str = P284_SHUTTER_TYPE_RESID16_HEX,
    exposed_shutter_types: Sequence[str] = P284_FX3_SHUTTER_TWO_TYPES,
    shutter_type: str = "MECHANICAL_SHUTTER",
    shutter_type_auto_exposed_in_fx3_ui: bool = False,
    expect_shutter_type_auto: bool = False,
    silent_mode: str = "OFF",
    audio_signals: str = "ON",
    e_front_curtain_shutter: str = "ON",
    e_front_curtain_survives_camera_reset: bool = True,
    exposure_mode: str = "MANUAL_EXPOSURE",
    flash_sync_denominator: int = 250,
    flash_enabled: bool = False,
    long_exposure_nr: str = "ON",
    bulb_enabled: bool = False,
    anti_flicker_shoot: str = "OFF",
    high_iso_nr: str = "NORMAL",
    still_file_format: str = "RAW",
    expect_high_iso_nr_applies_to_raw: bool = False,
    drive_mode: str = "SINGLE_SHOOTING",
    cont_fps: int = 10,
    raw_file_type: str = "COMPRESSED",
    aperture_f_number: float = 2.8,
    expect_af_tracks_all_frames_above_f11: bool = False,
    expect_10fps_with_uncompressed_or_flash: bool = False,
    simulated_passive_tx_bytes: int = 0,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
    simulate_bench_dry_run: bool = False,
) -> Tuple[P284CheckGroupDShutterType5LockoutHipTier0Result, Tuple[str, ...]]:
    """Validate Wave 49 §2 + Tier-0: 2-option Shutter Type, 1/250s flash sync, 5-lockout, Hi+ 10fps, >F11 AF & FX3RCPT1."""
    errors: List[str] = []
    tier0_errors: List[str] = []
    warnings: List[str] = []

    norm_exposed_shutter = tuple(_norm_shutter_type(x) for x in exposed_shutter_types)
    norm_shutter = _norm_shutter_type(shutter_type)
    norm_silent = _norm_token(silent_mode)
    norm_audio = _norm_token(audio_signals)
    norm_efcs = _norm_token(e_front_curtain_shutter)
    norm_exp = _norm_token(exposure_mode)
    norm_lenr = _norm_token(long_exposure_nr)
    norm_aflick = _norm_token(anti_flicker_shoot)
    norm_hisnr = _norm_token(high_iso_nr)
    norm_fmt = _norm_still_format(still_file_format)
    norm_drive = _norm_token(drive_mode)
    norm_raw = _norm_token(raw_file_type)

    if shutter_type_resid16_hex.lower() != P284_SHUTTER_TYPE_RESID16_HEX:
        errors.append(
            f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: Shutter Type resid16 mismatch ({shutter_type_resid16_hex!r})"
        )
    if norm_exposed_shutter != P284_FX3_SHUTTER_TWO_TYPES:
        errors.append(
            f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: FX3 [Shutter Type] exposes ONLY {P284_FX3_SHUTTER_TWO_TYPES}, got {exposed_shutter_types!r}"
        )
    if (
        shutter_type_auto_exposed_in_fx3_ui
        or expect_shutter_type_auto
        or norm_shutter == P284_FORBIDDEN_SHUTTER_TYPE_AUTO
    ):
        errors.append(
            f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: [Shutter Type]=[Auto] does NOT exist on stock ILME-FX3"
        )
    if norm_shutter not in P284_FX3_SHUTTER_TWO_TYPES:
        errors.append(
            f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: invalid shutter_type={shutter_type!r}"
        )
    if norm_silent not in ("ON", "OFF"):
        errors.append(
            f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: invalid silent_mode={silent_mode!r}"
        )
    if norm_silent == "ON":
        if norm_shutter != "ELECTRONIC_SHUTTER":
            errors.append(
                f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: [Silent Mode]=On forces [Shutter Type]=Electronic Shutter, got {norm_shutter}"
            )
        if norm_audio != "OFF":
            errors.append(
                f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: [Silent Mode]=On forces [Audio signals]=Off, got {audio_signals!r}"
            )
    if norm_shutter == "ELECTRONIC_SHUTTER" and norm_exp not in P284_PASM_EXPOSURE_MODES:
        errors.append(
            f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: Electronic Shutter is restricted to P/A/S/M, got {exposure_mode!r}"
        )
    if not e_front_curtain_survives_camera_reset:
        errors.append(
            f"{P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK}: [e-Front Curtain Shut.] is NOT resettable by [Camera Settings Reset]"
        )

    # 1/250 s flash sync & Electronic Shutter 5-function lockout
    if flash_sync_denominator <= 0 or flash_sync_denominator > P284_MECHANICAL_FLASH_SYNC_DENOM_CEILING:
        errors.append(
            f"{P284_GD_ERR_FLASH_SYNC_1_250_OR_ELECTRONIC_5LOCKOUT}: mechanical flash sync ceiling is 1/250 s, got 1/{flash_sync_denominator} s"
        )

    effective_electronic = norm_shutter == "ELECTRONIC_SHUTTER" or norm_silent == "ON"
    lockout_5_ok = True
    if effective_electronic:
        violated_locks: List[str] = []
        if flash_enabled:
            violated_locks.append("FLASH")
        if norm_lenr != "OFF":
            violated_locks.append("LONG_EXPOSURE_NR")
        if norm_efcs != "OFF":
            violated_locks.append("E_FRONT_CURTAIN_SHUT")
        if bulb_enabled:
            violated_locks.append("BULB")
        if norm_aflick != "OFF":
            violated_locks.append("ANTI_FLICKER_SHOOT")
        if violated_locks:
            lockout_5_ok = False
            errors.append(
                f"{P284_GD_ERR_FLASH_SYNC_1_250_OR_ELECTRONIC_5LOCKOUT}: Electronic Shutter / Silent Mode locks out 5 functions {P284_ELECTRONIC_SHUTTER_FIVE_LOCKOUTS}; active={violated_locks}"
            )

    # NR, Drive Mode, Hi+ 10fps, & > F11 AF Lock
    if norm_hisnr not in P284_VALID_HIGH_ISO_NR_MODES:
        errors.append(
            f"{P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE}: invalid high_iso_nr={high_iso_nr!r}"
        )
    if expect_high_iso_nr_applies_to_raw and norm_fmt in ("RAW", "RAW_AND_JPEG", "RAW_AND_HEIF"):
        errors.append(
            f"{P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE}: [High ISO NR] never alters .ARW RAW frames"
        )
    if norm_drive not in P284_DRIVE_EIGHT_MODES:
        errors.append(
            f"{P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE}: invalid drive_mode={drive_mode!r}"
        )
    if norm_drive.startswith("CONT_") and norm_lenr == "ON":
        errors.append(
            f"{P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE}: [Long Exposure NR] is unavailable in Continuous Shooting / Cont. Bracket"
        )
    if cont_fps <= 0 or cont_fps > P284_CONT_HIP_MAX_FPS:
        errors.append(
            f"{P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE}: cont_fps={cont_fps} exceeds ILME-FX3 Hi+ 10 fps ceiling"
        )
    if expect_10fps_with_uncompressed_or_flash or (
        norm_drive == "CONT_HI_PLUS"
        and (norm_raw == "UNCOMPRESSED" or flash_enabled)
        and cont_fps >= P284_CONT_HIP_MAX_FPS
    ):
        errors.append(
            f"{P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE}: Hi+ 10 fps drops below 10 fps on Uncompressed RAW or Flash"
        )

    af_locked_above_f11 = norm_drive in ("CONT_HI_PLUS", "CONT_HI", "CONT_MID") and (
        aperture_f_number > P284_AF_LOCK_APERTURE_THRESHOLD_F
    )
    if expect_af_tracks_all_frames_above_f11 and af_locked_above_f11:
        errors.append(
            f"{P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE}: Hi+/Hi/Mid locks AF to 1st frame when aperture F{aperture_f_number:.1f} > F11"
        )

    if simulated_passive_tx_bytes != 0:
        errors.append(
            f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: passive_tx_bytes_emitted={simulated_passive_tx_bytes} != 0"
        )

    # 16/16 H0 == H3 invariance
    surface_count = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_count, int(simulated_h0_h3_drifted_surfaces)))
    equals_count = max(0, surface_count - drifted)
    if drifted != 0:
        errors.append(
            f"{P284_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: {drifted} surfaces drifted between H0 and H3"
        )

    # Tier-0 dual-media 528B FX3RCPT1 receipt verification
    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    dev_a = st_dev_a_override
    dev_b = st_dev_b_override
    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
    eff_h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None

    if (
        simulate_bench_dry_run
        and raw_a is None
        and raw_b is None
        and receipt_a_path is None
        and receipt_b_path is None
    ):
        eff_serial = eff_serial or DEFAULT_TARGET_BODY_SERIAL
        eff_cid = eff_cid or DEFAULT_TARGET_EMMC_CID
        raw_a, raw_b, sim_h0 = build_simulated_phase284_tier0_receipts(
            body_serial=eff_serial, emmc_cid=eff_cid, body_fw=body_fw
        )
        dev_a = 101 if dev_a is None else dev_a
        dev_b = 202 if dev_b is None else dev_b
        eff_h0_a = eff_h0_a if eff_h0_a is not None else dict(sim_h0)
        eff_h0_b = eff_h0_b if eff_h0_b is not None else dict(sim_h0)
        warnings.append(
            "SIMULATED_DRY_RUN_ONLY: Tier-0 528B FX3RCPT1 receipts synthesized in memory; no physical bench authorization granted"
        )

    if raw_a is None and receipt_a_path is not None:
        try:
            _, raw_a, st_a = _read_bounded_slice_o_rdonly(
                Path(receipt_a_path), SD_RECEIPT_BYTES + 64
            )
            if dev_a is None:
                dev_a = int(st_a)
        except OSError as exc:
            tier0_errors.append(
                f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
            )

    if raw_b is None and receipt_b_path is not None:
        try:
            _, raw_b, st_b = _read_bounded_slice_o_rdonly(
                Path(receipt_b_path), SD_RECEIPT_BYTES + 64
            )
            if dev_b is None:
                dev_b = int(st_b)
        except OSError as exc:
            tier0_errors.append(
                f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
            )

    receipt_present = (
        (raw_a is not None)
        or (raw_b is not None)
        or (receipt_a_path is not None)
        or (receipt_b_path is not None)
    )
    distinct_media_ok = False
    receipt_verified = False

    if not receipt_present:
        warnings.append(
            "OFFLINE_AWAITING_PHYSICAL_TIER0_RECEIPT: provide dual-device Copy A and Copy B 528B FX3RCPT1 receipts"
        )
        tier0_errors.append(
            f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    elif raw_a is None or raw_b is None:
        tier0_errors.append(
            f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528B FX3RCPT1 receipts are required"
        )
    else:
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media_ok = True
            else:
                tier0_errors.append(
                    f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    group_result = P284CheckGroupDShutterType5LockoutHipTier0Result(
        check_group_id=P284_CHECK_GROUP_D_ID,
        passed=(len(errors) == 0),
        shutter_type_resid16_hex=shutter_type_resid16_hex,
        exposed_shutter_types=norm_exposed_shutter,
        effective_shutter_type=norm_shutter,
        shutter_type_auto_exposed_in_fx3_ui=shutter_type_auto_exposed_in_fx3_ui,
        silent_mode=norm_silent,
        audio_signals=norm_audio,
        e_front_curtain_shutter=norm_efcs,
        e_front_curtain_survives_camera_reset=e_front_curtain_survives_camera_reset,
        flash_sync_denominator=flash_sync_denominator,
        flash_enabled=flash_enabled,
        long_exposure_nr=norm_lenr,
        bulb_enabled=bulb_enabled,
        anti_flicker_shoot=norm_aflick,
        electronic_5function_lockout_verified=lockout_5_ok,
        high_iso_nr=norm_hisnr,
        drive_mode=norm_drive,
        cont_fps=cont_fps,
        aperture_f_number=aperture_f_number,
        af_locked_to_first_frame_above_f11=af_locked_above_f11,
        passive_tx_bytes_emitted=simulated_passive_tx_bytes,
        h0_h3_surface_count=surface_count,
        h0_equals_h3_count=equals_count,
        tier0_receipt_present=receipt_present,
        tier0_receipt_verified=receipt_verified,
        distinct_physical_media_verified=distinct_media_ok,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )
    return group_result, tuple(tier0_errors)


# ---------------------------------------------------------------------------
# Top-Level Pre-Shoot Readiness Orchestrator & Tamper-Evident Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P284_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    # Check Group A (Wave 48 §1 — PP11 S-Cinetone, Creative Look, DRO, Log Lockout & PP Reset Trap)
    pp_bkid: str = P284_PP_BKID,
    pp_resid16_hex: str = P284_PP_RESID16_HEX,
    factory_default_pp: str = P284_PP_DEFAULT_PROFILE,
    different_set_pp_checked: bool = False,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    movie_picture_profile: Optional[str] = None,
    still_picture_profile: Optional[str] = None,
    creative_look: str = P284_CREATIVE_LOOK_LOCKED_DASH,
    exposed_creative_looks: Sequence[str] = P284_CREATIVE_LOOK_TEN_PRESETS,
    dro_mode: str = "OFF",
    hlg_still_image: str = "OFF",
    movie_gamma_display_assist: str = "OFF",
    internal_recording_active: bool = True,
    hdmi_output_resolution: str = "1080P",
    expect_creative_look_or_dro_active_with_pp_or_log: bool = False,
    expect_pplut_in_still: bool = False,
    pp1_11_custom_params_modified: bool = True,
    pp_individual_reset_executed: bool = False,
    claimed_pp1_11_internal_params_wiped: bool = False,
    claimed_diff_set_checkmarks_wiped: bool = False,
    claimed_pp_active_selector_remains_non_pp11_after_camera_reset: bool = False,
    # Check Group B (Wave 48 §2 — WB Cine EI Restrictions, Custom 1..3 & Metering 6-Mode / M.M.)
    wb_resid16_hex: str = P284_WB_RESID16_HEX,
    wb_mode: str = "C_TEMP_FILTER",
    wb_kelvin_k: int = 5600,
    wb_ab_shift: int = 0,
    wb_gm_shift: int = 0,
    priority_set_in_awb: str = "STANDARD",
    shutter_awb_lock: str = "OFF",
    shockless_wb: str = "1",
    custom_wb_setup_requested: bool = False,
    custom_wb_survives_camera_reset: bool = True,
    custom_wb_excluded_from_camset: bool = True,
    shutter_awb_lock_survives_camera_reset: bool = True,
    claimed_custom_wb_saved_in_camset: bool = False,
    claimed_custom_wb_wiped_by_camera_reset: bool = False,
    metering_mode: str = "MULTI",
    exposed_metering_modes: Sequence[str] = P284_METERING_SIX_MODES,
    desqueeze_display: str = "OFF",
    face_priority_in_multi_metering: str = "ON",
    spot_metering_point: str = "CENTER",
    ael_with_shutter: str = "AUTO",
    ael_with_shutter_survives_camera_reset: bool = True,
    cine_ei_base_iso: int = 800,
    expect_metering_changes_cine_ei_iso: bool = False,
    # Check Group C (Wave 49 §1 — Still 2-Option RAW File Type, HLG Still Image & DCF 2.0 AdobeRGB _DSC)
    fx3_mechanical_shutter_present: bool = True,
    fx6_reference_mechanical_shutter: bool = False,
    raw_file_type_resid16_hex: str = P284_STILL_RAW_FILE_TYPE_RESID16_HEX,
    exposed_raw_file_types: Sequence[str] = P284_FX3_RAW_TWO_OPTIONS,
    raw_file_type: str = "COMPRESSED",
    lossless_comp_exposed_in_fx3_ui: bool = False,
    expect_lossless_comp_raw: bool = False,
    jh_file_type: str = "JPEG",
    still_file_format: str = "RAW",
    exposure_mode: str = "MANUAL_EXPOSURE",
    dro_bracket_active: bool = False,
    color_space: str = "SRGB",
    still_file_prefix: str = P284_DEFAULT_STILL_PREFIX,
    expected_dcf_sample_filename: str = "DSC00001.ARW",
    set_file_name_survives_camera_reset: bool = True,
    # Check Group D (Wave 49 §2 + Tier-0 — 2-Option Shutter Type, Flash Sync, 5-Lockout, Hi+ & Tier-0)
    shutter_type_resid16_hex: str = P284_SHUTTER_TYPE_RESID16_HEX,
    exposed_shutter_types: Sequence[str] = P284_FX3_SHUTTER_TWO_TYPES,
    shutter_type: str = "MECHANICAL_SHUTTER",
    shutter_type_auto_exposed_in_fx3_ui: bool = False,
    expect_shutter_type_auto: bool = False,
    silent_mode: str = "OFF",
    audio_signals: str = "ON",
    e_front_curtain_shutter: str = "ON",
    e_front_curtain_survives_camera_reset: bool = True,
    flash_sync_denominator: int = 250,
    flash_enabled: bool = False,
    long_exposure_nr: str = "ON",
    bulb_enabled: bool = False,
    anti_flicker_shoot: str = "OFF",
    high_iso_nr: str = "NORMAL",
    expect_high_iso_nr_applies_to_raw: bool = False,
    drive_mode: str = "SINGLE_SHOOTING",
    cont_fps: int = 10,
    aperture_f_number: float = 2.8,
    expect_af_tracks_all_frames_above_f11: bool = False,
    expect_10fps_with_uncompressed_or_flash: bool = False,
    simulated_passive_tx_bytes: int = 0,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
) -> RealHwPpScinetoneWbMeteringShutterTypeReport:
    """Execute Phase 284 read-only 9th physical bench readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase284_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        pp_bkid=pp_bkid,
        pp_resid16_hex=pp_resid16_hex,
        factory_default_pp=factory_default_pp,
        different_set_pp_checked=different_set_pp_checked,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        movie_picture_profile=movie_picture_profile,
        still_picture_profile=still_picture_profile,
        creative_look=creative_look,
        exposed_creative_looks=exposed_creative_looks,
        dro_mode=dro_mode,
        hlg_still_image=hlg_still_image,
        movie_gamma_display_assist=movie_gamma_display_assist,
        internal_recording_active=internal_recording_active,
        hdmi_output_resolution=hdmi_output_resolution,
        expect_creative_look_or_dro_active_with_pp_or_log=expect_creative_look_or_dro_active_with_pp_or_log,
        expect_pplut_in_still=expect_pplut_in_still,
        pp1_11_custom_params_modified=pp1_11_custom_params_modified,
        pp_individual_reset_executed=pp_individual_reset_executed,
        claimed_pp1_11_internal_params_wiped=claimed_pp1_11_internal_params_wiped,
        claimed_diff_set_checkmarks_wiped=claimed_diff_set_checkmarks_wiped,
        claimed_pp_active_selector_remains_non_pp11_after_camera_reset=claimed_pp_active_selector_remains_non_pp11_after_camera_reset,
    )
    gb = evaluate_p284_check_group_b_wb_and_metering(
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        reset_action=reset_action,
        wb_resid16_hex=wb_resid16_hex,
        wb_mode=wb_mode,
        wb_kelvin_k=wb_kelvin_k,
        wb_ab_shift=wb_ab_shift,
        wb_gm_shift=wb_gm_shift,
        priority_set_in_awb=priority_set_in_awb,
        shutter_awb_lock=shutter_awb_lock,
        shockless_wb=shockless_wb,
        custom_wb_setup_requested=custom_wb_setup_requested,
        custom_wb_survives_camera_reset=custom_wb_survives_camera_reset,
        custom_wb_excluded_from_camset=custom_wb_excluded_from_camset,
        shutter_awb_lock_survives_camera_reset=shutter_awb_lock_survives_camera_reset,
        claimed_custom_wb_saved_in_camset=claimed_custom_wb_saved_in_camset,
        claimed_custom_wb_wiped_by_camera_reset=claimed_custom_wb_wiped_by_camera_reset,
        metering_mode=metering_mode,
        exposed_metering_modes=exposed_metering_modes,
        desqueeze_display=desqueeze_display,
        face_priority_in_multi_metering=face_priority_in_multi_metering,
        spot_metering_point=spot_metering_point,
        ael_with_shutter=ael_with_shutter,
        ael_with_shutter_survives_camera_reset=ael_with_shutter_survives_camera_reset,
        cine_ei_base_iso=cine_ei_base_iso,
        expect_metering_changes_cine_ei_iso=expect_metering_changes_cine_ei_iso,
    )
    gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
        fx3_mechanical_shutter_present=fx3_mechanical_shutter_present,
        fx6_reference_mechanical_shutter=fx6_reference_mechanical_shutter,
        raw_file_type_resid16_hex=raw_file_type_resid16_hex,
        exposed_raw_file_types=exposed_raw_file_types,
        raw_file_type=raw_file_type,
        lossless_comp_exposed_in_fx3_ui=lossless_comp_exposed_in_fx3_ui,
        expect_lossless_comp_raw=expect_lossless_comp_raw,
        jh_file_type=jh_file_type,
        still_file_format=still_file_format,
        exposure_mode=exposure_mode,
        hlg_still_image=hlg_still_image,
        picture_profile=picture_profile,
        creative_look=creative_look,
        dro_mode=dro_mode,
        dro_bracket_active=dro_bracket_active,
        color_space=color_space,
        still_file_prefix=still_file_prefix,
        expected_dcf_sample_filename=expected_dcf_sample_filename,
        set_file_name_survives_camera_reset=set_file_name_survives_camera_reset,
    )
    gd, tier0_errors = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
        shutter_type_resid16_hex=shutter_type_resid16_hex,
        exposed_shutter_types=exposed_shutter_types,
        shutter_type=shutter_type,
        shutter_type_auto_exposed_in_fx3_ui=shutter_type_auto_exposed_in_fx3_ui,
        expect_shutter_type_auto=expect_shutter_type_auto,
        silent_mode=silent_mode,
        audio_signals=audio_signals,
        e_front_curtain_shutter=e_front_curtain_shutter,
        e_front_curtain_survives_camera_reset=e_front_curtain_survives_camera_reset,
        exposure_mode=exposure_mode,
        flash_sync_denominator=flash_sync_denominator,
        flash_enabled=flash_enabled,
        long_exposure_nr=long_exposure_nr,
        bulb_enabled=bulb_enabled,
        anti_flicker_shoot=anti_flicker_shoot,
        high_iso_nr=high_iso_nr,
        still_file_format=still_file_format,
        expect_high_iso_nr_applies_to_raw=expect_high_iso_nr_applies_to_raw,
        drive_mode=drive_mode,
        cont_fps=cont_fps,
        raw_file_type=raw_file_type,
        aperture_f_number=aperture_f_number,
        expect_af_tracks_all_frames_above_f11=expect_af_tracks_all_frames_above_f11,
        expect_10fps_with_uncompressed_or_flash=expect_10fps_with_uncompressed_or_flash,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_model_id=body_model_id,
        body_fw=body_fw,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        simulate_bench_dry_run=eff_sim,
    )

    groups_passed = sum(1 for item in (ga, gb, gc, gd) if item.passed)
    all_4_passed = donor_res.passed and groups_passed == 4

    all_errors: List[str] = []
    all_errors.extend(donor_res.errors)
    for item in (ga, gb, gc, gd):
        all_errors.extend(item.errors)
    all_errors.extend(tier0_errors)

    remediations: List[str] = []
    if not ga.passed:
        remediations.append(
            "Verify out-of-box PP11 (S-Cinetone) & [Different Set] coupling, lock [Creative Look]='-' & [DRO]=Off under PP!=Off or [Log Shooting]!=Off, enforce Movie-only PPLUT1..4 1080p HDMI clamp, and reset PP1..11 internals per profile."
        )
    if not gb.passed:
        remediations.append(
            "Avoid Auto/Underwater Auto WB under Cine EI/Quick, exit Log/S-Log3/PPLUT before [Custom Setup], note Custom 1..3 is excluded from CAMSET, force Face Priority=Off under De-Squeeze, and treat Cine EI metering as M.M. only."
        )
    if not gc.passed:
        remediations.append(
            "Enforce stock 2-option FX3 [RAW File Type] (Compressed/Uncompressed, never dormant Lossless Comp 0x6b56), require HEIF-only + P/A/S/M for [HLG Still Image]=On, and preserve DCF 2.0 AdobeRGB '_DSC' leading underscore semantics."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Enforce 2-option FX3 [Shutter Type] (Mechanical/Electronic, no Auto), 1/250 s flash sync, Electronic/Silent 5-function lockout, Hi+ 10fps / >F11 AF-lock boundaries, 16/16 H0==H3, and dual-device 528B FX3RCPT1 Tier-0 receipts."
        )

    if not all_4_passed:
        verdict = P284_GO_NO_GO_BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_FAILURE
        overall_status = verdict
    elif not gd.tier0_receipt_verified:
        if not gd.tier0_receipt_present:
            verdict = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            overall_status = P284_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        else:
            verdict = P284_GO_NO_GO_BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_FAILURE
            overall_status = verdict
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED
        overall_status = P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED

    provisional = RealHwPpScinetoneWbMeteringShutterTypeReport(
        schema=PHASE_284_SCHEMA,
        phase_version=PHASE_284_VERSION,
        verification_mode=donor_res.verification_mode,
        simulate_bench_dry_run=eff_sim,
        overall_status=overall_status,
        go_no_go=verdict,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        lossless_comp_exposed_in_fx3_ui=gc.lossless_comp_exposed_in_fx3_ui,
        shutter_type_auto_exposed_in_fx3_ui=gd.shutter_type_auto_exposed_in_fx3_ui,
        usb_packets_transmitted=PHASE284_USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHASE284_USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=PHASE284_RAW_FIRMWARE_BYTES_LEAKED,
        passive_tx_bytes_emitted=gd.passive_tx_bytes_emitted,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_pp_scinetone_look_dro_log=ga,
        check_group_b_wb_cine_ei_custom13_metering=gb,
        check_group_c_raw_2option_hlg_adobergb_dsc=gc,
        check_group_d_shutter_type_5lockout_hip_tier0=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwPpScinetoneWbMeteringShutterTypeReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_pp_scinetone_look_dro_log": ga,
            "check_group_b_wb_cine_ei_custom13_metering": gb,
            "check_group_c_raw_2option_hlg_adobergb_dsc": gc,
            "check_group_d_shutter_type_5lockout_hip_tier0": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_pp_scinetone_wb_metering_and_shutter_type_preflight = (
    evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness
)


def verify_phase284_report(payload: Mapping[str, Any]) -> Phase284ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 284 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_284_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_284_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_284_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go verdict: {payload.get('go_no_go')!r}")

    for lock_key in (
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "lossless_comp_exposed_in_fx3_ui",
        "shutter_type_auto_exposed_in_fx3_ui",
    ):
        if payload.get(lock_key) is not False:
            errors.append(f"Safety lock violated: {lock_key}={payload.get(lock_key)!r}")

    for zero_key in (
        "usb_packets_transmitted",
        "physical_usb_packets_emitted",
        "raw_firmware_bytes_leaked",
        "passive_tx_bytes_emitted",
    ):
        if payload.get(zero_key) != 0:
            errors.append(f"Zero-counter violated: {zero_key}={payload.get(zero_key)!r}")

    if payload.get("check_group_count") != 4:
        errors.append(f"Expected check_group_count==4, got {payload.get('check_group_count')!r}")

    if payload.get("go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT and (
        payload.get("overall_status") != P284_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    ):
        errors.append(
            "Offline awaiting-receipt verdict must carry overall_status=READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
        )

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go") == P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase284ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase284_markdown(report: RealHwPpScinetoneWbMeteringShutterTypeReport) -> str:
    """Render concise deterministic Markdown summary for Phase 284 physical bench preflight."""
    ga = report.check_group_a_pp_scinetone_look_dro_log
    gb = report.check_group_b_wb_cine_ei_custom13_metering
    gc = report.check_group_c_raw_2option_hlg_adobergb_dsc
    gd = report.check_group_d_shutter_type_5lockout_hip_tier0
    lines = [
        f"# Phase 284 9th Physical Bench Readiness (`{report.schema}`)",
        "",
        f"- **OVERALL**: `{report.overall_status}` (`go_no_go={report.go_no_go}`, mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `spi_nor={report.spi_nor_write_authorized}`, `el3_tx={report.el3_payload_transmit_authorized}`, `lossless_comp={report.lossless_comp_exposed_in_fx3_ui}`, `shutter_auto={report.shutter_type_auto_exposed_in_fx3_ui}`, `usb_pkts={report.usb_packets_transmitted}`, `passive_tx={report.passive_tx_bytes_emitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | Default=`{ga.factory_default_pp}`, DiffSet=`{ga.different_set_pp_checked}`, Log=`{ga.log_shooting_mode}`, PP=`{ga.effective_picture_profile}`, Look=`{ga.creative_look}` (`{ga.exposed_creative_look_count}`), DRO=`{ga.dro_mode}`, PP1..11_Survives=`{ga.pp1_11_internal_params_survive_resets}` |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | WB=`{gb.wb_mode}` (`{gb.wb_kelvin_k}K`, AB=`{gb.wb_ab_shift}`, GM=`{gb.wb_gm_shift}`), Metering=`{gb.metering_mode}` (`{len(gb.exposed_metering_modes)}` modes), FacePrio=`{gb.face_priority_in_multi_metering}`, BaseISO=`{gb.cine_ei_base_iso}` (`M.M.`), CustomWB_CAMSET_Excl=`{gb.custom_wb_excluded_from_camset}` |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | RAW=`{gc.raw_file_type}` (`{len(gc.exposed_raw_file_types)}` opts, LosslessExposed=`{gc.lossless_comp_exposed_in_fx3_ui}`), HLG=`{gc.hlg_still_image}`, CS=`{gc.color_space}`, Sample=`{gc.effective_dcf_sample_filename}` |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | Shutter=`{gd.effective_shutter_type}` (`{len(gd.exposed_shutter_types)}` opts, AutoExposed=`{gd.shutter_type_auto_exposed_in_fx3_ui}`), Silent=`{gd.silent_mode}`, FlashSync=`1/{gd.flash_sync_denominator}s`, Drive=`{gd.drive_mode}` (`{gd.cont_fps}fps`), Tier0=`{gd.tier0_receipt_verified}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
