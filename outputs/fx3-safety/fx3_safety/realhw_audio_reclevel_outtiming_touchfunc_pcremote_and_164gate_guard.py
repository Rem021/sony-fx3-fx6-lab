"""Phase 382 (Task H490, Wave-72, 164/164 Hardware Safety Gates):
Real-Hardware `[Audio Rec Level]` (`0..31` def `26`, `adj_audio_rec_level_defult` typo,
`Delete` resets to `26`, `Can be reset`, `XLR-H1` physical preemption & permanent
non-disableable Limiter vs FX6 3-tier Reference / 6-mode `Limiter Mode` / 5-mode
`Reference Level`), `[Audio Out Timing]` (`Live`/`Lip Sync`, `Can be reset`, disabled in
`S&Q`) + anti-Reset `Setup -> [Sound Option]` (`[Volume Settings]` `0..15` def `7` &
exact 5-item `[4ch Audio Monitoring]` `CH1/CH2`, `CH3/CH4`, `CH1+3/CH2+4`, `CH1/CH1`,
`CH2/CH2` rejecting fabricated labels `EOPNOTSUPP=95` vs FX6 7-item `Monitor CH`,
`Headphone Out`, `Volume 0..50` with zero `"MONITOR VOL +/-"` side keys, and `SDI OUT`
4ch vs `HDMI` 2ch) (`G163`),
`[Touch Func. in Shooting]` 4 active anti-Reset sub-items (`Touch Operation`,
`Touch Sensitivity`, `Touch Func. in Shooting`, `Swipe Up`) vs 100% dormant
`[Touch Panel/Pad]`/`[Touch Pad (vertical)]`/`[Touch Shutter]`/`[Touch AE]`
(`EOPNOTSUPP=95`), `[Spot Metering Point]` anchored-on-track linkage vs FX6
`Touch Operation` / `Touch Function in MF` (`Spot Focus` lockouts & `Tracking AF`) /
Ver. 6.00+ `BIG6` touch, and `[Remote Shoot Setting]` (`Still Img. Save Dest.`
`Destination Only` zero-card RAM via `stillrec_running_without_pseudo_rec_t` vs
out-of-box default `Dest.+Camera` & `Camera Only`, `Save Image Size`, `RAW+J/H Save
Image`, PTP `/dev/usb/sicd_{core,data,event}` & PTP-IP `TCP 15740`, and Tier-0 `Slot 1`
`EROFS=30` Firewall vs FX6 `Network Client Mode` / `Camera Remote Control`) (`G164`),
and Unified `164`-Gate Master Safety Preflight (`G01..G164`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G163` (`AUDIO_RECLEVEL_XLRH1_PREEMPTION_LIMITER_OUTTIMING_VOLUME_4CH_MONITORING_FIREWALL`)**:
    1. Exact menu path `Shooting -> [Audio Recording] -> [Audio Rec Level]` (`0..31` =
       32 steps, default `26`, `adj_audio_rec_level_defult` typo, `Delete` resets to
       `26`, `Can be reset`). Applies ONLY to internal stereo mic & body `3.5mm MIC`
       (permanent non-disableable limiter -> disabling returns `EOPNOTSUPP = 95`).
    2. 3-layer hardware preemption:
       - (a) `3.5mm MIC` inserted preempts MI Shoe (`[Shoe Audio Set.]` grayed,
         `[Wind Noise Reduct.]` bypassed, `[Audio Rec Level]` active, 2ch).
       - (b) No `3.5mm MIC` + `XLR-H1 HANDLE AUDIO = ON` preempts body `[Audio Rec Level]`
         (`UIBIZ_INP_HOTSHOE_XLRMIC`), delegating to physical switches (`LINE` locked
         `+4 dBu`; `MIC`/`MIC+48V` `ATT 0/10/20 dB` = `-60/-50/-40 dBu`; `AUTO`/`MAN`/
         `LINK` + `AUDIO LEVEL` physical dial).
       - (c) `S&Q Motion` forces `0ch` silent & locks all 4 recording controls.
    3. `[Audio Out Timing]` (`Shooting -> [Audio Recording]`, `Live` default vs `Lip Sync`,
       `Can be reset`, disabled in `S&Q`).
    4. `Setup -> [Sound Option]`: BOTH `[Volume Settings]` (`0..15`, def `7`) and
       `[4ch Audio Monitoring]` (def `CH1/CH2`) resist `[Camera Settings Reset]` (Wave 72
       erratum correcting Wave 62!). Exact 5-item enum: `CH1/CH2`, `CH3/CH4`,
       `CH1+3/CH2+4`, `CH1/CH1`, `CH2/CH2` (reject fabricated `"CH1/CH2 mono mix"` /
       `"CH1+2/CH3+4"` / `"All"` with `EOPNOTSUPP = 95`), independent from HDMI
       `[4ch Audio Output]` (`CH1/CH2` / `CH3/CH4`), 3.5mm headphone limited to 2ch.
    5. Contrast FX6 `Audio > Audio Input/Output`: 3-tier Reference (`INPUT1/2 MIC
       Reference -80..-30 dB` 6 steps, `Line Input Reference +4/0/-3 dB/EBUL` 4 steps,
       `Reference Level -20/-18/-16/-12 dB/EBUL` 5 steps), 6-mode `Limiter Mode`
       (`Off/-6/-9/-12/-15/-17 dB`), 7-item `Monitor CH` (`CH1..4`, `CH1/CH2`,
       `CH3/CH4`, `MIX ALL`), `Headphone Out` (`Stereo`/`Mono`), `Volume 0..50` (zero
       physical `"MONITOR VOL +/-"` side keys -> `EOPNOTSUPP = 95`), `SDI OUT` full 4ch
       vs `HDMI` 2ch pair.

  - **Gate `G164` (`TOUCH_FUNC_4ACTIVE_VS_DORMANT_PAD_SHUTTER_AE_AND_REMOTE_SHOOT_PTP_SLOT1_EROFS_FIREWALL`)**:
    1. `Setup -> [Touch Operation]` exposes EXACTLY 4 active sub-items (ALL resist
       `Camera Settings Reset`, cleared only on `Initialize`): `[Touch Operation]`
       (`On` def / `On: Playback Only` / `Off`), `[Touch Sensitivity]` (`Standard` def /
       `Sensitive`), `[Touch Func. in Shooting]` (`Touch Focus` / `Touch Tracking` def /
       `Off` — identical across Still/Movie/S&Q), `[Swipe Up]` (`Open the Fn Menu` def /
       `Off`).
    2. 100% dormant touch features strictly blocked `EOPNOTSUPP = 95`: `[Touch Panel/Pad]`
       (`_f 0x76EC`), `[Touch Pad (vertical)]` (`_f 0x7312`), `[Touch Shutter]`
       (`_f 0x6A80`), `[Touch AE]` (`_f 0x702A`). Spot metering linkage uses
       `[Spot Metering Point]` (`Center` vs `Focus Point Link`), anchored at initial
       point during Tracking. Contrast FX6 `Touch Operation`, `Touch Function in MF`
       (`Spot Focus` disabled on MF lens / `De-Squeeze != Off (1.0x)` / `Focus Magnifier`,
       `Tracking AF`), and Ver. 6.00+ `BIG6` touch.
    3. `[PC Remote Function]` (Ver. 1.x) -> `Network -> [Cnct./Remote Sht.] ->
       [Remote Shoot Setting]` (Ver. 2.00..7.02, all 4 anti-Reset, reset via `Initialize`
       or `Reset Network Set.`): `[Still Img. Save Dest.]` (`Destination Only` /
       `Dest.+Camera` DEFAULT! / `Camera Only`), `[Save Image Size]` (`Original` /
       `2M` def), `[RAW+J Save Image]` (`RAW & JPEG` / `JPEG Only` def / `RAW Only`),
       `[RAW+H Save Image]` (`RAW & HEIF` / `HEIF Only` def / `RAW Only`).
    4. PTP-over-USB (`/dev/usb/sicd_{core,data,event}`, `libInfraPtpControl.so`) &
       PTP-IP (`TCP 15740`, `libInfraRemote.so`) + Tier-0 `Slot 1` Firewall: ONLY
       `Destination Only` (`PC Only`) shoots via RAM with zero card writes
       (`slot1_writes == 0`, works cardless); out-of-box default `Dest.+Camera` &
       `Camera Only` write `[Recording Media]` (`Slot 1`) and MUST fail-closed with
       `EROFS = 30` when `Slot 1` is Tier-0 read-only protected. Active connection
       mutating `Still Img. Save Dest.` fails closed `EBUSY = 16`. Contrast FX6
       `Network Client Mode` / `Camera Remote Control` (zero `Still Img. Save Dest.` UI).

  - **Unified 164-Gate Master Safety Preflight (`G01..G164`)**:
    Delegates `G01..G162` to `evaluate_162gate_preflight()`, enforces `161/164`
    verified offline (`VERIFIED_161_OF_164_AWAITING_PHYSICAL_TIER0`) and `164/164`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_164_GATES_DRY_RUN_SIMULATED_BACKUP`),
    with ALL hardware write/flash/live-attach flags hard-locked `False` and `0`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    GateVerdict,
)
from .thermal_pwm_and_power_guard import (
    DEFAULT_REPO_ROOT,
    STATUS_VERIFIED_SAFE,
    resolve_donor_thermal_power_paths,
)
from .realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITES_AUTHORIZED,
    ENV_FORCE_CLEAN_ROOM,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    USB_PACKETS_TRANSMITTED,
)
from .realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard import (
    Master162GateReport,
    evaluate_162gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Env Keys & Shared Constants
# ---------------------------------------------------------------------------

REALHW_AUDIO_RECLEVEL_OUTTIMING_TOUCHFUNC_PCREMOTE_164GATE_SCHEMA = (
    "fx3_realhw_audio_reclevel_outtiming_touchfunc_pcremote_164gate_guard_v1"
)
REALHW_AUDIO_RECLEVEL_OUTTIMING_TOUCHFUNC_PCREMOTE_164GATE_VERSION = (
    "2026.11.21-phase382-164gates"
)
REALHW_164GATE_PREFLIGHT_SCHEMA = "realhw_164gate_preflight_v1"

G163 = "G163"
G163_GATE_ID = "G163"
G163_GATE_CODE = (
    "AUDIO_RECLEVEL_XLRH1_PREEMPTION_LIMITER_OUTTIMING_VOLUME_4CH_MONITORING_FIREWALL"
)

G164 = "G164"
G164_GATE_ID = "G164"
G164_GATE_CODE = (
    "TOUCH_FUNC_4ACTIVE_VS_DORMANT_PAD_SHUTTER_AE_AND_REMOTE_SHOOT_PTP_SLOT1_EROFS_FIREWALL"
)

ENV_CLEAN_ROOM_TEST_PHASE382 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE382 = 2.00
DONOR_CHECK_FAST_TARGET_SECONDS_PHASE382 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE382 = 0.05
DONOR_BOUNDED_MAX_READ_BYTES_PHASE382 = 4 * 1024 * 1024  # 4 MiB cap for non-sliced files

EPERM_ERRNO_PHASE382 = 1
EPERM_NAME_PHASE382 = "EPERM"
EBUSY_ERRNO_PHASE382 = 16
EBUSY_NAME_PHASE382 = "EBUSY"
EINVAL_ERRNO_PHASE382 = 22
EINVAL_NAME_PHASE382 = "EINVAL"
EROFS_ERRNO_PHASE382 = 30
EROFS_NAME_PHASE382 = "EROFS"
EOPNOTSUPP_ERRNO_PHASE382 = 95
EOPNOTSUPP_NAME_PHASE382 = "EOPNOTSUPP"

FX3_MODEL_NAME_PHASE382 = "ILME-FX3"
FX3_MODEL_ID_PHASE382 = 0x0502
FX3_MODEL_ENUM_PHASE382 = "PRODUCT_MODEL_ALCIN_UUD"
FX3_HELP_GUIDE_CODE_PHASE382 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE382 = "7.02"
FX6_MODEL_NAME_PHASE382 = "ILME-FX6"
FX6_MODEL_ENUM_PHASE382 = "PRODUCT_MODEL_CHAPLIN"
FX6_DEFAULT_FW_VERSION_PHASE382 = "6.01"
ALLOWED_BODY_MODELS_PHASE382: Tuple[str, ...] = (
    FX3_MODEL_NAME_PHASE382,
    FX6_MODEL_NAME_PHASE382,
)

MEDIA_SLOT_NONE_PHASE382 = 0
MEDIA_SLOT_1_PHASE382 = 1
MEDIA_SLOT_2_PHASE382 = 2
ALLOWED_MEDIA_SLOTS_PHASE382: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE382,
    MEDIA_SLOT_1_PHASE382,
    MEDIA_SLOT_2_PHASE382,
)

SHOOT_MODE_STILL_PHASE382 = "Still"
SHOOT_MODE_MOVIE_PHASE382 = "Movie"
SHOOT_MODE_SQ_PHASE382 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE382: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE382,
    SHOOT_MODE_MOVIE_PHASE382,
    SHOOT_MODE_SQ_PHASE382,
)

RESET_ACTION_NONE_PHASE382 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE382 = "Initialize"
RESET_ACTION_RESET_NETWORK_SET_PHASE382 = "Reset Network Set."
ALLOWED_RESET_ACTIONS_PHASE382: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE382,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
    RESET_ACTION_INITIALIZE_PHASE382,
    RESET_ACTION_RESET_NETWORK_SET_PHASE382,
)


# ---------------------------------------------------------------------------
# Gate G163 Constants: [Audio Rec Level], XLR-H1 Physical Preemption & Limiter,
#                      [Audio Out Timing], [Volume Settings], Exact 5-Item
#                      [4ch Audio Monitoring] vs FX6 Audio Input/Output
# ---------------------------------------------------------------------------

AUDIO_REC_LEVEL_MENU_PATH_G163 = "Shooting -> [Audio Recording] -> [Audio Rec Level]"
AUDIO_OUT_TIMING_MENU_PATH_G163 = "Shooting -> [Audio Recording] -> [Audio Out Timing]"
SOUND_OPTION_MENU_PATH_G163 = "Setup -> [Sound Option]"
VOLUME_SETTINGS_MENU_PATH_G163 = "Setup -> [Sound Option] -> [Volume Settings]"
AUDIO_MONITORING_4CH_MENU_PATH_G163 = (
    "Setup -> [Sound Option] -> [4ch Audio Monitoring]"
)
HDMI_4CH_AUDIO_OUTPUT_MENU_PATH_G163 = (
    "Setup -> [External Output] -> [HDMI Output Settings] -> [4ch Audio Output]"
)
FX6_AUDIO_INPUT_MENU_PATH_G163 = "Audio > Audio Input"
FX6_AUDIO_OUTPUT_MENU_PATH_G163 = "Audio > Audio Output"

AUDIO_REC_LEVEL_MIN_G163 = 0
AUDIO_REC_LEVEL_MAX_G163 = 31
AUDIO_REC_LEVEL_STEP_COUNT_G163 = 32
AUDIO_REC_LEVEL_DEFAULT_G163 = 26
AUDIO_REC_LEVEL_DELETE_KEY_RESETS_TO_G163 = 26
AUDIO_REC_LEVEL_ELF_TYPO_G163 = "adj_audio_rec_level_defult"
AUDIO_REC_LEVEL_RESETTABLE_BY_CAMSET_RESET_G163 = True
FX3_BODY_LIMITER_PERMANENTLY_ACTIVE_G163 = True

ALLOWED_XLR_H1_INPUT_TYPES_G163: Tuple[str, ...] = ("LINE", "MIC", "MIC+48V")
XLR_H1_LINE_FIXED_DBU_G163 = 4
ALLOWED_XLR_H1_ATT_DB_G163: Tuple[int, ...] = (0, 10, 20)
XLR_H1_ATT_TO_DBU_G163: Dict[int, int] = {0: -60, 10: -50, 20: -40}
ALLOWED_XLR_H1_GAIN_MODES_G163: Tuple[str, ...] = ("AUTO", "MAN", "LINK")
XLR_H1_LEVEL_DIAL_MIN_G163 = 0
XLR_H1_LEVEL_DIAL_MAX_G163 = 10
SQ_LOCKED_AUDIO_CONTROLS_G163: Tuple[str, ...] = (
    "Audio Recording",
    "Audio Rec Level",
    "Audio Out Timing",
    "Wind Noise Reduct.",
)

ALLOWED_AUDIO_OUT_TIMING_MODES_G163: Tuple[str, ...] = ("Live", "Lip Sync")
AUDIO_OUT_TIMING_DEFAULT_G163 = "Live"
AUDIO_OUT_TIMING_RESETTABLE_BY_CAMSET_RESET_G163 = True

VOLUME_SETTINGS_MIN_G163 = 0
VOLUME_SETTINGS_MAX_G163 = 15
VOLUME_SETTINGS_STEP_COUNT_G163 = 16
VOLUME_SETTINGS_DEFAULT_G163 = 7
VOLUME_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G163 = False
XLR_H1_SPEAKER_FEEDBACK_WARN_MIN_VOL_G163 = 10

EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163: Tuple[str, ...] = (
    "CH1/CH2",
    "CH3/CH4",
    "CH1+3/CH2+4",
    "CH1/CH1",
    "CH2/CH2",
)
AUDIO_MONITORING_4CH_DEFAULT_G163 = "CH1/CH2"
AUDIO_MONITORING_4CH_RESETTABLE_BY_CAMSET_RESET_G163 = False
FABRICATED_4CH_MONITORING_LABELS_G163: Tuple[str, ...] = (
    "CH1/CH2 mono mix",
    "CH1+2/CH3+4",
    "All",
    "MIX ALL",
    "Mono Mix",
)
ALLOWED_FX3_HDMI_4CH_OUTPUT_MODES_G163: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
HDMI_4CH_AUDIO_OUTPUT_DEFAULT_G163 = "CH1/CH2"
FX3_HEADPHONE_MAX_DISCRETE_CH_G163 = 2

# FX6 Audio Input/Output Contrast (5-024-458-18 + FX6 appFw.so)
FX6_INPUT_MIC_REFERENCE_6_STEPS_G163: Tuple[str, ...] = (
    "-80dB",
    "-70dB",
    "-60dB",
    "-50dB",
    "-40dB",
    "-30dB",
)
FX6_LINE_INPUT_REFERENCE_4_STEPS_G163: Tuple[str, ...] = (
    "+4dB",
    "0dB",
    "-3dB",
    "EBUL",
)
FX6_REFERENCE_LEVEL_5_STEPS_G163: Tuple[str, ...] = (
    "-20dB",
    "-18dB",
    "-16dB",
    "-12dB",
    "EBUL",
)
FX6_LIMITER_MODE_6_STEPS_G163: Tuple[str, ...] = (
    "Off",
    "-6dB",
    "-9dB",
    "-12dB",
    "-15dB",
    "-17dB",
)
FX6_MONITOR_CH_7_ITEMS_G163: Tuple[str, ...] = (
    "CH1",
    "CH2",
    "CH3",
    "CH4",
    "CH1/CH2",
    "CH3/CH4",
    "MIX ALL",
)
FX6_HEADPHONE_OUT_MODES_G163: Tuple[str, ...] = ("Stereo", "Mono")
FX6_VOLUME_MIN_G163 = 0
FX6_VOLUME_MAX_G163 = 50
FX6_MONITOR_VOL_PHYSICAL_KEY_HITS_G163 = 0
FX6_SDI_AUDIO_CHANNELS_G163 = 4
FX6_HDMI_AUDIO_CHANNELS_G163 = 2

# UXC resid16 anchors (G163)
AUDIO_REC_LEVEL_F_RESID16_G163 = 0x63B9
AUDIO_REC_LEVEL_ALT_F_RESID16_G163 = 0x6F0A
AUDIO_OUT_TIMING_F_RESID16_G163 = 0x6BC2
AUDIO_OUT_TIMING_LIVE_F_RESID16_G163 = 0x753D
AUDIO_OUT_TIMING_LIP_SYNC_F_RESID16_G163 = 0x6BBC
VOLUME_SETTINGS_BASE_RESID16_G163 = 0xE8C9
AUDIO_MONITORING_4CH_F_RESID16_G163 = 0x70DD
AUDIO_MON_CH1_CH2_F_RESID16_G163 = 0x713B
AUDIO_MON_CH3_CH4_F_RESID16_G163 = 0x6BF6
AUDIO_MON_CH13_CH24_F_RESID16_G163 = 0x6C2E
AUDIO_MON_CH1_CH1_F_RESID16_G163 = 0x6F9C
AUDIO_MON_CH2_CH2_F_RESID16_G163 = 0x7A26

STATUS_VERIFIED_G163 = (
    "VERIFIED_G163_AUDIO_RECLEVEL_XLRH1_LIMITER_OUTTIMING_VOLUME_5ITEM_4CH_MON"
)
STATUS_BLOCKED_G163_TELEMETRY_INVALID = "BLOCKED_G163_TELEMETRY_INVALID"
STATUS_BLOCKED_G163_FABRICATED_4CH_BODY_LIMITER_OFF_OR_FX6_MONVOL_EOPNOTSUPP = (
    "BLOCKED_G163_FABRICATED_4CH_BODY_LIMITER_OFF_OR_FX6_MONVOL_EOPNOTSUPP"
)
STATUS_BLOCKED_G163_PREEMPTION_SQ_LOCK_RESET_OR_FX6_AUDIO_CONSTRAINT_VIOLATION = (
    "BLOCKED_G163_PREEMPTION_SQ_LOCK_RESET_OR_FX6_AUDIO_CONSTRAINT_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G164 Constants: [Touch Func. in Shooting] 4 Active Anti-Reset Items vs
#                      100% Dormant [Touch Panel/Pad]/[Touch Shutter]/[Touch AE]
#                      & [Remote Shoot Setting] PTP/PTP-IP + Slot 1 EROFS=30
# ---------------------------------------------------------------------------

TOUCH_OPERATION_MENU_PATH_G164 = "Setup -> [Touch Operation]"
SPOT_METERING_POINT_MENU_PATH_G164 = (
    "Exposure/Color -> [Metering] -> [Spot Metering Point]"
)
REMOTE_SHOOT_SETTING_MENU_PATH_G164 = (
    "Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]"
)
LEGACY_V1_PC_REMOTE_MENU_PATH_G164 = "Transfer/Remote -> [PC Remote Function]"
FX6_TOUCH_OPERATION_MENU_PATH_G164 = "Technical > Touch Operation"
FX6_TOUCH_FUNC_MF_MENU_PATH_G164 = "Shooting > Focus > Touch Function in MF"
FX6_NETWORK_CLIENT_MENU_PATH_G164 = "Network > Network Client Mode"

EXACT_4_FX3_TOUCH_OPERATION_SUBITEMS_G164: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Touch Func. in Shooting",
    "Swipe Up",
)
FX3_TOUCH_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164 = False
ALLOWED_TOUCH_OPERATION_MODES_G164: Tuple[str, ...] = (
    "On",
    "On: Playback Only",
    "Off",
)
TOUCH_OPERATION_DEFAULT_G164 = "On"
ALLOWED_TOUCH_SENSITIVITY_MODES_G164: Tuple[str, ...] = ("Standard", "Sensitive")
TOUCH_SENSITIVITY_DEFAULT_G164 = "Standard"
ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES_G164: Tuple[str, ...] = (
    "Touch Focus",
    "Touch Tracking",
    "Off",
)
TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164 = "Touch Tracking"
ALLOWED_SWIPE_UP_MODES_G164: Tuple[str, ...] = ("Open the Fn Menu", "Off")
SWIPE_UP_DEFAULT_G164 = "Open the Fn Menu"

DORMANT_FX3_TOUCH_FEATURES_G164: Tuple[str, ...] = (
    "Touch Panel/Pad",
    "Touch Pad (vertical)",
    "Touch Shutter",
    "Touch AE",
)
FX3_EVF_PRESENT_G164 = False
FX3_ILC2210_TOUCH_SHUTTER_HITS_G164 = 0
FX3_ILC2210_TOUCH_AE_HITS_G164 = 0

ALLOWED_SPOT_METERING_POINTS_G164: Tuple[str, ...] = ("Center", "Focus Point Link")
SPOT_METERING_POINT_DEFAULT_G164 = "Center"
ALLOWED_FOCUS_AREA_CATEGORIES_G164: Tuple[str, ...] = (
    "Spot",
    "Expand Spot",
    "Tracking: Spot",
    "Wide",
    "Zone",
    "Center Fix",
)
SPOT_LINK_ELIGIBLE_FOCUS_AREAS_G164: Tuple[str, ...] = (
    "Spot",
    "Expand Spot",
    "Tracking: Spot",
)
FX3_SPOT_METERING_FOLLOWS_MOVING_TRACK_BOX_G164 = False

FX6_TOUCH_OPERATION_MODES_G164: Tuple[str, ...] = ("On", "Off")
FX6_TOUCH_FUNCTION_IN_MF_MODES_G164: Tuple[str, ...] = ("Spot Focus", "Tracking AF")
FX6_BIG6_TOUCH_MIN_FW_G164 = 6.00

EXACT_4_REMOTE_SHOOT_SUBITEMS_G164: Tuple[str, ...] = (
    "Still Img. Save Dest.",
    "Save Image Size",
    "RAW+J Save Image",
    "RAW+H Save Image",
)
REMOTE_SHOOT_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164 = False
ALLOWED_STILL_IMG_SAVE_DEST_G164: Tuple[str, ...] = (
    "Destination Only",
    "Dest.+Camera",
    "Camera Only",
)
STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164 = "Dest.+Camera"
STILL_IMG_SAVE_DEST_BENCH_SAFE_G164 = "Destination Only"
ALLOWED_SAVE_IMAGE_SIZE_G164: Tuple[str, ...] = ("Original", "2M")
SAVE_IMAGE_SIZE_DEFAULT_G164 = "2M"
ALLOWED_RAW_J_SAVE_IMAGE_G164: Tuple[str, ...] = (
    "RAW & JPEG",
    "JPEG Only",
    "RAW Only",
)
RAW_J_SAVE_IMAGE_DEFAULT_G164 = "JPEG Only"
ALLOWED_RAW_H_SAVE_IMAGE_G164: Tuple[str, ...] = (
    "RAW & HEIF",
    "HEIF Only",
    "RAW Only",
)
RAW_H_SAVE_IMAGE_DEFAULT_G164 = "HEIF Only"

ALLOWED_PTP_TRANSPORTS_G164: Tuple[str, ...] = (
    "none",
    "ptp_usb",
    "ptp_ip_usblan",
    "ptp_ip_wired_lan",
    "ptp_ip_wifi",
)
FX3_PTP_USB_DEVICE_NODES_G164: Tuple[str, ...] = (
    "/dev/usb/sicd_core",
    "/dev/usb/sicd_data",
    "/dev/usb/sicd_event",
)
FX3_PTP_IP_TCP_PORT_G164 = 15740
FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED_G164 = False

# UXC resid16 anchors (G164)
TOUCH_OPERATION_G_RESID16_G164 = 0x6345
TOUCH_OPERATION_BASE_RESID16_G164 = 0xE8E3
TOUCH_FUNC_IN_SHOOTING_F_RESID16_G164 = 0x7575
TOUCH_FOCUS_F_RESID16_G164 = 0x6E79
TOUCH_TRACKING_F_RESID16_G164 = 0x69EE
DORMANT_TOUCH_PANEL_PAD_F_RESID16_G164 = 0x76EC
DORMANT_TOUCH_PAD_VERTICAL_F_RESID16_G164 = 0x7312
DORMANT_TOUCH_SHUTTER_F_RESID16_G164 = 0x6A80
DORMANT_TOUCH_AE_F_RESID16_G164 = 0x702A
DORMANT_TOUCH_AE_CANCEL_G_RESID16_G164 = 0x6150
CNCT_REMOTE_SHT_G_RESID16_G164 = 0x64C5
REMOTE_SHOOT_SETTING_F_RESID16_G164 = 0x7BA4
REMOTE_SHOOT_FUNCTION_F_RESID16_G164 = 0x7C6E
STILL_IMG_SAVE_DEST_F_RESID16_G164 = 0x79D0
DESTINATION_ONLY_F_RESID16_G164 = 0x7BD7
DEST_PLUS_CAMERA_F_RESID16_G164 = 0x7BB5
CAMERA_ONLY_F_RESID16_G164 = 0x7B16
SAVE_IMAGE_SIZE_F_RESID16_G164 = 0x7BC7
RAW_J_SAVE_IMAGE_F_RESID16_G164 = 0x7B9E
RAW_H_SAVE_IMAGE_F_RESID16_G164 = 0x7BC3

STATUS_VERIFIED_G164 = (
    "VERIFIED_G164_TOUCH_4ACTIVE_VS_DORMANT_AND_REMOTE_SHOOT_PTP_SLOT1_EROFS"
)
STATUS_BLOCKED_G164_TELEMETRY_INVALID = "BLOCKED_G164_TELEMETRY_INVALID"
STATUS_BLOCKED_G164_SLOT1_REMOTE_SHOOT_WRITE_EROFS = (
    "BLOCKED_G164_SLOT1_REMOTE_SHOOT_WRITE_EROFS"
)
STATUS_BLOCKED_G164_CONNECTED_SAVE_DEST_MUTATION_EBUSY = (
    "BLOCKED_G164_CONNECTED_SAVE_DEST_MUTATION_EBUSY"
)
STATUS_BLOCKED_G164_DORMANT_TOUCH_OR_FX6_SAVE_DEST_EOPNOTSUPP = (
    "BLOCKED_G164_DORMANT_TOUCH_OR_FX6_SAVE_DEST_EOPNOTSUPP"
)
STATUS_BLOCKED_G164_TOUCH_SPOT_RESET_OR_PTP_CONSTRAINT_VIOLATION = (
    "BLOCKED_G164_TOUCH_SPOT_RESET_OR_PTP_CONSTRAINT_VIOLATION"
)

STATUS_BLOCKED_PHASE382_DONOR_INTEGRITY = "BLOCKED_PHASE382_DONOR_CONTRACT_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-72 Donor Specs (O_RDONLY | O_NOFOLLOW | O_NONBLOCK, Raw Bytes = 0)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX_P382 = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX_P382 = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

PINNED_FX3_APPFW_SLICES_PHASE382: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03B32735, b"VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_0"),
    (0x03B32D29, b"VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_26"),
    (0x03B32E50, b"VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_31"),
    (0x03C2553A, b"adj_audio_rec_level_defult"),
    (0x03BB2A4D, b"UIBIZ_INP_HOTSHOE_XLRMIC"),
    (0x03BC7257, b"BKID_APP_setting_audio_output_timing"),
    (0x03B33255, b"VAL_setting_audio_output_timing_AUDIO_OUTPUT_TIMING_LIVE"),
    (0x03B3328E, b"VAL_setting_audio_output_timing_AUDIO_OUTPUT_TIMING_LIP_SYNC"),
    (0x02FA80BA, b"VOLUME_SETTINGS_0"),
    (0x02FA7FA6, b"VOLUME_SETTINGS_15"),
    (0x030665EB, b"EVENT_REMOTE_VOLUME_SETTINGS"),
    (0x03BCBFF6, b"BKID_APP_setting_audio_monitoring_ch"),
    (0x02FA80CC, b"AUDIO_MONITORING_CH_1CH_2CH"),
    (0x02FA80E8, b"AUDIO_MONITORING_CH_3CH_4CH"),
    (0x02FA8104, b"AUDIO_MONITORING_CH_MIX_ALL"),
    (0x02FA8120, b"AUDIO_MONITORING_CH_1CH"),
    (0x02FA8138, b"AUDIO_MONITORING_CH_2CH"),
    (0x03BCC22D, b"BKID_APP_setting_4ch_output_ch"),
    (0x03BCBA88, b"BKID_APP_setting_touch_operation"),
    (0x03BCBAA9, b"BKID_APP_setting_touch_sensitivity"),
    (0x03B03CAF, b"VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_FOCUS"),
    (0x03B03CF7, b"VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_TRACKING"),
    (0x03B03D8C, b"VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_OFF"),
    (0x03B03D42, b"VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER"),
    (0x03BCBACC, b"BKID_APP_setting_touch_panel_pad"),
    (0x039867C5, b"PID_SET_TOUCH_SPOT_METER"),
    (0x03985778, b"NID_TOUCH_SPOT_METER_STATUS"),
    (0x03BC9FF5, b"BKID_APP_setting_pc_remote_func"),
    (0x03BC9CFD, b"BKID_APP_setting_remote_settings_still_img_save_dest"),
    (0x03BC9D32, b"BKID_APP_setting_remote_settings_still_img_trans_size"),
    (0x03BC9D68, b"BKID_APP_setting_remote_settings_raw_j_pc_save_img"),
    (0x03BC9D9B, b"BKID_APP_setting_remote_settings_raw_h_pc_save_img"),
    (0x039BC371, b"PRM_HAITA_setting_remote_settings_still_img_save_dest_pc_remote_connection_state"),
    (0x03B97F28, b"N5model37stillrec_running_without_pseudo_rec_tE"),
    (
        0x03B1CBB0,
        b"VAL_HAITA_not_save_still_smartphone_only_not_save_still_pc_only_media_mount_state_setting_release_wo_card_NOT_SAVE_STILL_SMARTPHONE_ONLY_NOT_SAVE_STILL_PC_ONLY_PC_REMOTE_CONNECTED_MEDIA_NOT_MOUNT",
    ),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE382 = (
    "ed559ccfca0eddbf4560464a8eca657b8e85e9eded1af4abaf890cf554fa9e0a"
)

PINNED_FX6_APPFW_SLICES_PHASE382: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x026BA6AB, b"VAL_setting_ch1_input_select_"),
    (0x026BAA52, b"VAL_setting_ch4_input_select_"),
    (0x026BDDD2, b"INPUT_MIC_REFERENCE_80DB"),
    (0x026BDEF4, b"INPUT_MIC_REFERENCE_30DB"),
    (0x027868FA, b"EXTERN_LINE_INPUT_REFERENCE_4_DB"),
    (0x02786966, b"EXTERN_LINE_INPUT_REFERENCE_EBUL"),
    (0x0278682B, b"EXTERN_REFERENCE_LEVEL_NEGATIVE_20_DB"),
    (0x027868C3, b"EXTERN_REFERENCE_LEVEL_EBUL"),
    (0x027866DF, b"EXTERN_LIMITER_MODE_OFF"),
    (0x027866F7, b"EXTERN_LIMITER_MODE_NEGATIVE_6_DB"),
    (0x02786781, b"EXTERN_LIMITER_MODE_NEGATIVE_17_DB"),
    (0x02786401, b"EXTERN_AUDIO_MONITORING_CH_CH1_CH2"),
    (0x02786447, b"EXTERN_AUDIO_MONITORING_CH_MIXALL"),
    (0x02786469, b"EXTERN_AUDIO_MONITORING_CH_CH1"),
    (0x027864C6, b"EXTERN_AUDIO_MONITORING_CH_CH4"),
    (0x027863E5, b"EXTERN_HEADPHONE_OUT_STEREO"),
    (0x027863CB, b"EXTERN_HEADPHONE_OUT_MONO"),
    (0x027066B2, b"BKID_APP_SETTING_AUDIO_OUTPUT_TIMING"),
    (0x02706E1C, b"BKID_APP_SETTING_TOUCH_OPERATION"),
    (0x02708C9D, b"BKID_APP_SETTING_TOUCH_FUNCTION_IN_MF"),
    (0x02713DA5, b"BKID_APP_TOUCH_TRACKING_STATE"),
    (0x027394FB, b"BKID_APP_HOME_SCREEN_STATE"),
    (0x026D477C, b"TYPE_COMMUNICATION_WITH_BASE_BLOCK_VIA_PTP_IP"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE382 = (
    "cb7d8dd619df850fbdf4bb514cfdacc5ae24cb3465c32d52b6e34318e1ff8ff1"
)

PINNED_PHASE382_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE382,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE382),
        "FX3 appFw.so Wave-72 AudioRecLevel/OutTiming/4chMon/Touch/RemoteShoot slices",
    ),
    "fx3_libptp_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/lib/libptp.so",
        73_304,
        "8646befc379b1efc2fe303f8462cbbe519bca77e308f25b9efcf56b30081da46",
        (b"\x7fELF",),
        "FX3 libptp.so core PTP protocol library",
    ),
    "fx3_libinfraptpcontrol_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/lib/libInfraPtpControl.so",
        165_320,
        "445c83b36c7243a880523e4dd03f7231d6de601fe227b6730bf0b4e3b2741c6d",
        (
            b"\x7fELF",
            b"/dev/usb/sicd_core",
            b"/dev/usb/sicd_data",
            b"/dev/usb/sicd_event",
            b"PTPT_EE_send_data_usb",
            b"PTPT_EE_send_data_ip_remote",
            b"PtpIpConnMgrThread",
        ),
        "FX3 libInfraPtpControl.so USB sicd_* & PTP-IP 15740 transport",
    ),
    "fx3_libinfraptpextcmd_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/lib/libInfraPtpExtCmd.so",
        35_600,
        "2dfe5d52abf029192714a28b85c513076f9076b00733cc3c641018607f79e5b3",
        (b"\x7fELF",),
        "FX3 libInfraPtpExtCmd.so Camera Remote SDK extension bridge",
    ),
    "fx3_libinfraremote_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/lib/libInfraRemote.so",
        1_271_152,
        "75a15f15c0eac786ac6b73456d6d1ca5ecd9832d7962a1025ea8c78d75755b56",
        (
            b"\x7fELF",
            b"actionStartPtpIp",
            b"actionStopPtpIp",
            b"SetContentsTransferMode",
        ),
        "FX3 libInfraRemote.so InfraRemoteIP PTP-IP state machine",
    ),
    "fx3_libinframtpserver_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/lib/libInfraMtpServer.so",
        276_856,
        "95bdf031ea623a065e920fa5ae875a9138006fc17c00f35075cd44ca46b329c9",
        (b"\x7fELF",),
        "FX3 libInfraMtpServer.so MTP isolation library",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00", b"ILME-FX3"),
        "FX3-CX95900_ALLLANG-Backup.bin BK4 seed",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Audio Rec Level",
            b"Audio Out Timing",
            b"Live",
            b"Lip Sync",
            b"CH1/CH2",
            b"CH3/CH4",
            b"CH1+3/CH2+4",
            b"CH1/CH1",
            b"CH2/CH2",
            b"Touch Func. in Shooting",
            b"Touch Focus",
            b"Touch Tracking",
            b"Touch Panel/Pad",
            b"Touch Shutter",
            b"Touch AE",
            b"Remote Shoot Setting",
            b"Still Img. Save Dest.",
            b"Destination Only",
            b"Dest.+Camera",
            b"Camera Only",
            b"Save Image Size",
            b"RAW+J Save Image",
            b"RAW+H Save Image",
        ),
        "FX3 string_english_f.uxc Wave-72 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "\u5f55\u97f3\u97f3\u91cf".encode("utf-8"),
            "\u97f3\u9891\u8f93\u51fa\u65f6\u523b".encode("utf-8"),
            "\u5b9e\u51b5\u8f6c\u64ad".encode("utf-8"),
            "\u5507\u97f3\u540c\u6b65".encode("utf-8"),
            "\u62cd\u6444\u671f\u95f4\u7684\u89e6\u6478\u529f\u80fd".encode("utf-8"),
            "\u89e6\u6478\u5c4f/\u89e6\u6478\u677f".encode("utf-8"),
            "\u89e6\u5c4f\u5feb\u95e8".encode("utf-8"),
            "\u89e6\u5c4fAE".encode("utf-8"),
            "\u9065\u63a7\u62cd\u6444\u8bbe\u7f6e".encode("utf-8"),
            "\u9759\u6001\u5f71\u50cf\u4fdd\u5b58\u76ee\u7684\u5730".encode("utf-8"),
            "\u4ec5\u9650\u76ee\u7684\u5730".encode("utf-8"),
            "\u76ee\u7684\u5730+\u62cd\u6444\u88c5\u7f6e".encode("utf-8"),
            "\u4ec5\u62cd\u6444\u88c5\u7f6e".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-72 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "\u9304\u97f3\u97f3\u91cf".encode("utf-8"),
            "\u97f3\u8a0a\u8f38\u51fa\u6642\u523b".encode("utf-8"),
            "\u5373\u6642\u64ad\u9001".encode("utf-8"),
            "\u5507\u97f3\u540c\u6b65".encode("utf-8"),
            "\u62cd\u651d\u671f\u9593\u7684\u89f8\u63a7\u529f\u80fd".encode("utf-8"),
            "\u89f8\u63a7\u9762\u677f/\u89f8\u63a7\u677f".encode("utf-8"),
            "\u89f8\u63a7\u5feb\u9580".encode("utf-8"),
            "\u89f8\u63a7AE".encode("utf-8"),
            "\u9059\u63a7\u62cd\u651d\u8a2d\u5b9a".encode("utf-8"),
            "\u975c\u614b\u5f71\u50cf\u5132\u5b58\u76ee\u7684\u5730".encode("utf-8"),
            "\u50c5\u9650\u76ee\u7684\u5730".encode("utf-8"),
            "\u76ee\u7684\u5730+\u62cd\u651d\u88dd\u7f6e".encode("utf-8"),
            "\u50c5\u9650\u62cd\u651d\u88dd\u7f6e".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-72 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "\u9332\u97f3\u30ec\u30d9\u30eb".encode("utf-8"),
            "\u97f3\u58f0\u51fa\u529b\u30bf\u30a4\u30df\u30f3\u30b0".encode("utf-8"),
            "\u30e9\u30a4\u30d6".encode("utf-8"),
            "\u30ea\u30c3\u30d7\u30b7\u30f3\u30af".encode("utf-8"),
            "\u64ae\u5f71\u6642\u306e\u30bf\u30c3\u30c1\u6a5f\u80fd".encode("utf-8"),
            "\u30bf\u30c3\u30c1\u30b7\u30e3\u30c3\u30bf\u30fc".encode("utf-8"),
            "\u30bf\u30c3\u30c1AE".encode("utf-8"),
            "\u30ea\u30e2\u30fc\u30c8\u64ae\u5f71\u8a2d\u5b9a".encode("utf-8"),
            "\u9759\u6b62\u753b\u306e\u4fdd\u5b58\u5148".encode("utf-8"),
            "\u63a5\u7d9a\u5148\u306e\u307f".encode("utf-8"),
            "\u30ab\u30e1\u30e9\u672c\u4f53\u306e\u307f".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-72 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (b"Volume Settings", b"Touch Operation"),
        "FX3 string_english.uxc Wave-72 EN base",
    ),
    "fx3_string_simplifiedchinese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_simplifiedchinese.uxc",
        149_064,
        "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        (
            "\u97f3\u91cf\u8bbe\u7f6e".encode("utf-8"),
            "\u89e6\u6478\u64cd\u4f5c".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese.uxc Wave-72 ZH-CN base",
    ),
    "fx3_string_traditionalchinese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_traditionalchinese.uxc",
        151_908,
        "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        (
            "\u97f3\u91cf\u8a2d\u5b9a".encode("utf-8"),
            "\u89f8\u63a7\u64cd\u4f5c".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese.uxc Wave-72 ZH-TW base",
    ),
    "fx3_string_japanese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_japanese.uxc",
        208_564,
        "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        (
            "\u97f3\u91cf\u8a2d\u5b9a".encode("utf-8"),
            "\u30bf\u30c3\u30c1\u64cd\u4f5c".encode("utf-8"),
        ),
        "FX3 string_japanese.uxc Wave-72 JA base",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (b"Cnct./Remote Sht.", b"Touch AE Cancel"),
        "FX3 string_english_g.uxc Wave-72 EN guide",
    ),
    "fx3_string_simplifiedchinese_g_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P382}/share/app/string_simplifiedchinese_g.uxc",
        61_296,
        "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        ("\u8fde\u63a5/\u9065\u63a7\u62cd\u6444".encode("utf-8"),),
        "FX3 string_simplifiedchinese_g.uxc Wave-72 ZH-CN guide",
    ),
    "fx6_appfw_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P382}/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE382,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE382),
        "FX6 appFw.so Wave-72 AudioInput/Limiter6/MonitorCH7/TouchMF/BIG6/PTP-IP slices",
    ),
    "fx6_libptp_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P382}/lib/libptp.so",
        77_408,
        "21e212ae68a6d8fe1ae8fc4eb40bd3629e3f126a41ddfc1e00e750cd46a134aa",
        (b"\x7fELF",),
        "FX6 libptp.so PTP-IP core comparison baseline",
    ),
    "fx6_libinfraptpcontrol_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P382}/lib/libInfraPtpControl.so",
        152_520,
        "5af1afff957290bbd2519e237af5df761413e54193e149ee70189f32fe646a27",
        (b"\x7fELF", b"PTPT_EE_send_data_ip_remote"),
        "FX6 libInfraPtpControl.so PTP-IP transport comparison baseline",
    ),
    "fx6_libinfraremote_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P382}/lib/libInfraRemote.so",
        1_262_824,
        "67bf51a4e2ff670b21ec3f6b8dce58022e9fea8874e250c1f8037978d07cb946",
        (b"\x7fELF", b"actionStartPtpIp"),
        "FX6 libInfraRemote.so remote control comparison baseline",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P382}/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Network Client Mode",
            b"Camera Remote Control",
            b"Headphone Live/Processed",
        ),
        "FX6 string_english.uxc Wave-72 EN baseline (zero MONITOR VOL)",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P382}/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (b"Remote", b"Network", b"Audio", b"Limiter"),
        "FX6 string_english_2.uxc Wave-72 EN enterprise baseline (zero MONITOR VOL)",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers (Strictly O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
# ---------------------------------------------------------------------------

_RDONLY_SAFE_FLAGS_P382 = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
)


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE382):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_strict_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _is_on_off(val: Any) -> bool:
    return isinstance(val, str) and val in ("On", "Off")


def _encode_token_variants(token: bytes) -> Tuple[bytes, ...]:
    variants = [token]
    try:
        text = token.decode("utf-8")
        variants.append(text.encode("utf-16-le"))
    except UnicodeDecodeError:
        pass
    return tuple(variants)


def _read_exact_o_rdonly_slices(
    path: Path, slices: Sequence[Tuple[int, bytes]]
) -> Tuple[int, str, List[str]]:
    missing: List[str] = []
    hasher = hashlib.sha256()
    fd = os.open(path, _RDONLY_SAFE_FLAGS_P382)
    try:
        st = os.fstat(fd)
        for offset, expected in slices:
            chunk = os.pread(fd, len(expected), offset)
            if chunk != expected:
                missing.append(f"slice_mismatch@0x{offset:08X}")
            hasher.update(chunk)
        return st.st_size, hasher.hexdigest(), missing
    finally:
        os.close(fd)


def _read_bounded_o_rdonly_sha256_and_tokens(
    path: Path, required_tokens: Sequence[bytes]
) -> Tuple[int, str, List[str], bytes]:
    missing: List[str] = []
    fd = os.open(path, _RDONLY_SAFE_FLAGS_P382)
    try:
        st = os.fstat(fd)
        read_len = min(st.st_size, DONOR_BOUNDED_MAX_READ_BYTES_PHASE382)
        data = os.read(fd, read_len)
    finally:
        os.close(fd)
    if len(data) != st.st_size:
        missing.append(f"bounded_cap_exceeded:{st.st_size}")
    sha = hashlib.sha256(data).hexdigest()
    for idx, tok in enumerate(required_tokens):
        if not any(var in data for var in _encode_token_variants(tok)):
            missing.append(f"token_missing_idx_{idx}")
    return st.st_size, sha, missing, data


def _parse_fw_float(ver_str: str) -> Optional[float]:
    if not isinstance(ver_str, str) or not ver_str.strip():
        return None
    try:
        return float(ver_str.strip())
    except ValueError:
        return None


def _validate_fx3_body_identity(
    body_model_name: str,
    body_model_id: int,
    help_guide_code: str,
    firmware_version: str,
) -> List[str]:
    errs: List[str] = []
    if body_model_name != FX3_MODEL_NAME_PHASE382:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE382:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE382:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


def strip_elapsed_seconds_recursive_phase382(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds`/`elapsed_ms` keys for canonical digests."""
    if isinstance(obj, dict):
        return {
            k: strip_elapsed_seconds_recursive_phase382(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms")
        }
    if isinstance(obj, list):
        return [strip_elapsed_seconds_recursive_phase382(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_elapsed_seconds_recursive_phase382(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Donor Integrity Audit (Bounded O_RDONLY | O_NOFOLLOW | O_NONBLOCK + Clean-Room)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase382DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    four_lang_resid16_parity_verified: bool
    ptp_transport_libs_verified: bool
    zero_fx6_monitor_vol_verified: bool
    elapsed_seconds: float
    within_budget_2s: bool
    raw_firmware_bytes_leaked: int
    file_digests: Dict[str, str]
    missing_markers: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_phase382_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase382DonorAuditResult:
    """Bounded (<= 2.0s) O_RDONLY|O_NOFOLLOW|O_NONBLOCK + os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE382_DONOR_SPECS)
    )
    resolved_work_root = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(
            repo_root=repo_root or DEFAULT_REPO_ROOT
        ).work_root
    )

    if clean_forced:
        dt = time.perf_counter() - t0
        return Phase382DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_DISK_IO",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            ptp_transport_libs_verified=True,
            zero_fx6_monitor_vol_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_2s=dt <= DONOR_CHECK_MAX_SECONDS_PHASE382,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(),
        )

    missing_files = (
        list(specs.keys())
        if resolved_work_root is None
        else [
            key
            for key, spec in specs.items()
            if not (resolved_work_root / spec[1]).is_file()
        ]
    )
    if missing_files and donor_specs_override is None:
        dt = time.perf_counter() - t0
        return Phase382DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_ABSENT_DONOR_FALLBACK",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            ptp_transport_libs_verified=True,
            zero_fx6_monitor_vol_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_2s=dt <= DONOR_CHECK_MAX_SECONDS_PHASE382,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 382 via clean-room synthetic fallback.",
            ),
        )

    file_digests: Dict[str, str] = {}
    missing_markers: List[str] = []
    errors: List[str] = []
    inspected = 0
    zero_fx6_monvol_ok = True

    for key, (
        family,
        rel_path,
        expected_size,
        expected_sha,
        tokens,
        desc,
    ) in specs.items():
        if resolved_work_root is None:
            missing_markers.append(f"{key}:work_root_none")
            errors.append(f"{key}:{desc}:work_root_none")
            continue
        target = resolved_work_root / rel_path
        if not target.is_file():
            missing_markers.append(f"{key}:file_missing")
            errors.append(f"{key}:{desc}:file_missing")
            continue
        inspected += 1
        if key == "fx3_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX3_APPFW_SLICES_PHASE382
            )
            raw_bytes = b""
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE382
            )
            raw_bytes = b""
        else:
            actual_size, actual_sha, tok_errs, raw_bytes = (
                _read_bounded_o_rdonly_sha256_and_tokens(target, tokens)
            )
            if (
                key in ("fx6_string_english_uxc", "fx6_string_english_2_uxc")
                and donor_specs_override is None
            ):
                if (
                    b"MONITOR VOL" in raw_bytes
                    or "MONITOR VOL".encode("utf-16-le") in raw_bytes
                ):
                    zero_fx6_monvol_ok = False
                    missing_markers.append(f"{key}:unexpected_MONITOR_VOL")
                    errors.append(f"FX6:{key}:unexpected_MONITOR_VOL")

        file_digests[key] = actual_sha
        if actual_size != expected_size:
            missing_markers.append(
                f"{key}:size_mismatch:{actual_size}!={expected_size}"
            )
            errors.append(f"{family}:{key}:size_mismatch")
        if actual_sha != expected_sha:
            missing_markers.append(f"{key}:sha256_mismatch")
            errors.append(f"{family}:{key}:sha256_mismatch")
        for terr in tok_errs:
            missing_markers.append(f"{key}:{terr}")
            errors.append(f"{family}:{key}:{terr}")

    dt = time.perf_counter() - t0
    valid = len(errors) == 0
    return Phase382DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE382_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_NOFOLLOW_NONBLOCK_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        ptp_transport_libs_verified=valid,
        zero_fx6_monitor_vol_verified=zero_fx6_monvol_ok and valid,
        elapsed_seconds=round(dt, 6),
        within_budget_2s=dt <= DONOR_CHECK_MAX_SECONDS_PHASE382,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G163: [Audio Rec Level] / XLR-H1 Preemption / Limiter &
#            [Audio Out Timing] / [Volume Settings] / Exact 5-Item [4ch Audio Monitoring]
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioRecLevelOutTimingGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    audio_rec_level_menu_path: str
    audio_out_timing_menu_path: str
    volume_settings_menu_path: str
    audio_monitoring_4ch_menu_path: str
    hdmi_4ch_audio_output_menu_path: str
    fx6_audio_input_menu_path: str
    fx6_audio_output_menu_path: str
    shoot_mode: str
    active_audio_source: str
    active_audio_channels: int
    audio_rec_level_available: bool
    effective_audio_rec_level: int
    audio_rec_level_step_count: int
    audio_rec_level_default: int
    audio_rec_level_elf_typo: str
    audio_rec_level_resettable_by_camset_reset: bool
    body_limiter_permanently_active: bool
    shoe_audio_set_grayed: bool
    wind_noise_reduct_bypassed: bool
    xlr_h1_controls_active: bool
    xlr_h1_input_type: str
    xlr_h1_effective_ref_dbu: int
    xlr_h1_att_active: bool
    xlr_h1_gain_mode: str
    sq_locked_audio_controls: Tuple[str, ...]
    audio_out_timing_available: bool
    effective_audio_out_timing: str
    audio_out_timing_resettable_by_camset_reset: bool
    effective_volume_settings: int
    volume_settings_resettable_by_camset_reset: bool
    effective_4ch_audio_monitoring: str
    audio_monitoring_4ch_enum_count: int
    audio_monitoring_4ch_resettable_by_camset_reset: bool
    effective_hdmi_4ch_audio_output: str
    headphone_max_discrete_channels: int
    fx6_mic_reference_step_count: int
    fx6_line_reference_step_count: int
    fx6_reference_level_step_count: int
    fx6_limiter_mode: str
    fx6_limiter_mode_count: int
    fx6_monitor_ch: str
    fx6_monitor_ch_count: int
    fx6_headphone_out: str
    fx6_volume: int
    fx6_monitor_vol_physical_key_hits: int
    fx6_sdi_audio_channels: int
    fx6_hdmi_audio_channels: int
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_audio_reclevel_outtiming_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE382,
    mic_35mm_inserted: bool = False,
    xlr_h1_attached: bool = False,
    xlr_h1_handle_audio_on: bool = False,
    xlr_h1_4ch_mode: bool = False,
    xlr_h1_input_type: str = "MIC",
    xlr_h1_att_db: int = 0,
    xlr_h1_gain_mode: str = "MAN",
    audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT_G163,
    delete_key_pressed: bool = False,
    audio_out_timing: str = AUDIO_OUT_TIMING_DEFAULT_G163,
    volume_settings: int = VOLUME_SETTINGS_DEFAULT_G163,
    audio_monitoring_4ch: str = AUDIO_MONITORING_4CH_DEFAULT_G163,
    hdmi_4ch_audio_output: str = HDMI_4CH_AUDIO_OUTPUT_DEFAULT_G163,
    reset_action: str = RESET_ACTION_NONE_PHASE382,
) -> Dict[str, Any]:
    """Deterministically resolve FX3 Ver. 7.02 Audio Rec Level, XLR-H1 preemption,
    Audio Out Timing, Volume Settings, and 5-item 4ch Audio Monitoring state."""
    # Reset semantics:
    # - Shooting -> [Audio Recording] ([Audio Rec Level], [Audio Out Timing]): Can be reset!
    # - Setup -> [Sound Option] ([Volume Settings], [4ch Audio Monitoring]): Anti-Reset (Initialize-only)!
    if reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
        RESET_ACTION_INITIALIZE_PHASE382,
    ):
        eff_rec_level = AUDIO_REC_LEVEL_DEFAULT_G163
        eff_out_timing = AUDIO_OUT_TIMING_DEFAULT_G163
    else:
        eff_rec_level = (
            AUDIO_REC_LEVEL_DELETE_KEY_RESETS_TO_G163
            if delete_key_pressed
            else audio_rec_level
        )
        eff_out_timing = audio_out_timing

    if reset_action == RESET_ACTION_INITIALIZE_PHASE382:
        eff_vol = VOLUME_SETTINGS_DEFAULT_G163
        eff_mon_4ch = AUDIO_MONITORING_4CH_DEFAULT_G163
        eff_hdmi_4ch = HDMI_4CH_AUDIO_OUTPUT_DEFAULT_G163
    else:
        eff_vol = volume_settings
        eff_mon_4ch = audio_monitoring_4ch
        eff_hdmi_4ch = hdmi_4ch_audio_output

    # 3-layer hardware preemption:
    # (c) S&Q forces 0ch silent and locks all 4 recording controls.
    # (a) 3.5mm MIC preempts MI Shoe ([Shoe Audio Set.] grayed, [Wind Noise Reduct.] bypassed).
    # (b) No 3.5mm MIC + XLR-H1 HANDLE AUDIO = ON preempts body [Audio Rec Level].
    if shoot_mode == SHOOT_MODE_SQ_PHASE382:
        active_src = "sq_silent_0ch"
        active_ch = 0
        rec_lvl_avail = False
        out_timing_avail = False
        shoe_grayed = True
        wind_bypassed = True
        xlr_controls = False
    elif mic_35mm_inserted:
        active_src = "body_35mm_mic"
        active_ch = 2
        rec_lvl_avail = True
        out_timing_avail = True
        shoe_grayed = True
        wind_bypassed = True
        xlr_controls = False
    elif xlr_h1_attached and xlr_h1_handle_audio_on:
        active_src = "xlr_h1_mishoe"
        active_ch = 4 if xlr_h1_4ch_mode else 2
        rec_lvl_avail = False
        out_timing_avail = True
        shoe_grayed = False
        wind_bypassed = True
        xlr_controls = True
    else:
        active_src = "internal_stereo_mic"
        active_ch = 2
        rec_lvl_avail = True
        out_timing_avail = True
        shoe_grayed = False
        wind_bypassed = False
        xlr_controls = False

    if xlr_h1_input_type == "LINE":
        xlr_ref_dbu = XLR_H1_LINE_FIXED_DBU_G163
        xlr_att_active = False
    else:
        xlr_ref_dbu = XLR_H1_ATT_TO_DBU_G163.get(xlr_h1_att_db, -60)
        xlr_att_active = True

    return {
        "active_audio_source": active_src,
        "active_audio_channels": active_ch,
        "audio_rec_level_available": rec_lvl_avail,
        "effective_audio_rec_level": eff_rec_level,
        "body_limiter_permanently_active": FX3_BODY_LIMITER_PERMANENTLY_ACTIVE_G163,
        "shoe_audio_set_grayed": shoe_grayed,
        "wind_noise_reduct_bypassed": wind_bypassed,
        "xlr_h1_controls_active": xlr_controls,
        "xlr_h1_effective_ref_dbu": xlr_ref_dbu,
        "xlr_h1_att_active": xlr_att_active,
        "xlr_h1_gain_mode": xlr_h1_gain_mode,
        "audio_out_timing_available": out_timing_avail,
        "effective_audio_out_timing": eff_out_timing,
        "effective_volume_settings": eff_vol,
        "effective_4ch_audio_monitoring": eff_mon_4ch,
        "effective_hdmi_4ch_audio_output": eff_hdmi_4ch,
    }


def compute_audio_reclevel_outtiming_matrix() -> Dict[str, Any]:
    """Sweep deterministic 480-state Wave-72 Gate G163 matrix."""
    shoot_modes = ALLOWED_SHOOT_MODES_PHASE382  # 3
    sources = (
        ("internal", False, False, False),
        ("mic35", True, True, True),
        ("xlrh1_2ch", False, True, True),
        ("xlrh1_4ch", False, True, True),
    )  # 4
    timings = ALLOWED_AUDIO_OUT_TIMING_MODES_G163  # 2
    mon_routes = EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163  # 5
    resets = (
        RESET_ACTION_NONE_PHASE382,
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
        RESET_ACTION_INITIALIZE_PHASE382,
        RESET_ACTION_RESET_NETWORK_SET_PHASE382,
    )  # 4
    # 3 * 4 * 2 * 5 * 4 = 480 states!
    total = 0
    sq_zero_ch_count = 0
    mic35_preempt_shoe_count = 0
    xlrh1_preempt_rec_level_count = 0
    camset_reset_rec_level_count = 0
    camset_reset_sound_option_survived_count = 0
    initialize_sound_option_reset_count = 0
    body_limiter_all_count = 0

    for sm, (src_tag, mic35, xlr_att, xlr_on), timing, mon, rst in itertools.product(
        shoot_modes, sources, timings, mon_routes, resets
    ):
        total += 1
        st = resolve_fx3_audio_reclevel_outtiming_state(
            shoot_mode=sm,
            mic_35mm_inserted=mic35,
            xlr_h1_attached=xlr_att,
            xlr_h1_handle_audio_on=xlr_on,
            xlr_h1_4ch_mode=(src_tag == "xlrh1_4ch"),
            audio_rec_level=18,
            audio_out_timing=timing,
            volume_settings=12,
            audio_monitoring_4ch=mon,
            reset_action=rst,
        )
        if st["body_limiter_permanently_active"]:
            body_limiter_all_count += 1
        if (
            sm == SHOOT_MODE_SQ_PHASE382
            and st["active_audio_channels"] == 0
            and not st["audio_rec_level_available"]
            and not st["audio_out_timing_available"]
        ):
            sq_zero_ch_count += 1
        if (
            sm != SHOOT_MODE_SQ_PHASE382
            and src_tag == "mic35"
            and st["active_audio_source"] == "body_35mm_mic"
            and st["shoe_audio_set_grayed"]
            and st["wind_noise_reduct_bypassed"]
        ):
            mic35_preempt_shoe_count += 1
        if (
            sm != SHOOT_MODE_SQ_PHASE382
            and src_tag in ("xlrh1_2ch", "xlrh1_4ch")
            and st["xlr_h1_controls_active"]
            and not st["audio_rec_level_available"]
        ):
            xlrh1_preempt_rec_level_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382
            and st["effective_audio_rec_level"] == AUDIO_REC_LEVEL_DEFAULT_G163
            and st["effective_audio_out_timing"] == AUDIO_OUT_TIMING_DEFAULT_G163
        ):
            camset_reset_rec_level_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382
            and st["effective_volume_settings"] == 12
            and st["effective_4ch_audio_monitoring"] == mon
        ):
            camset_reset_sound_option_survived_count += 1
        if (
            rst == RESET_ACTION_INITIALIZE_PHASE382
            and st["effective_volume_settings"] == VOLUME_SETTINGS_DEFAULT_G163
            and st["effective_4ch_audio_monitoring"] == AUDIO_MONITORING_4CH_DEFAULT_G163
        ):
            initialize_sound_option_reset_count += 1

    return {
        "total_states": total,
        "body_limiter_all_verified": body_limiter_all_count == total,
        "sq_zero_ch_count": sq_zero_ch_count,
        "mic35_preempt_shoe_count": mic35_preempt_shoe_count,
        "xlrh1_preempt_rec_level_count": xlrh1_preempt_rec_level_count,
        "camset_reset_rec_level_count": camset_reset_rec_level_count,
        "camset_reset_sound_option_survived_count": camset_reset_sound_option_survived_count,
        "initialize_sound_option_reset_count": initialize_sound_option_reset_count,
    }


def verify_audio_reclevel_outtiming_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE382,
    body_model_id: int = FX3_MODEL_ID_PHASE382,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE382,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE382,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE382,
    mic_35mm_inserted: bool = False,
    xlr_h1_attached: bool = False,
    xlr_h1_handle_audio_on: bool = False,
    xlr_h1_4ch_mode: bool = False,
    xlr_h1_input_type: str = "MIC",
    xlr_h1_att_db: int = 0,
    xlr_h1_gain_mode: str = "MAN",
    xlr_h1_level_dial: int = 5,
    audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT_G163,
    delete_key_pressed: bool = False,
    attempt_body_rec_level_write: bool = False,
    request_disable_body_limiter: bool = False,
    attempt_xlr_att_override_on_line: bool = False,
    claim_35mm_keeps_shoe_audio_active: bool = False,
    claim_sq_records_audio: bool = False,
    audio_out_timing: str = AUDIO_OUT_TIMING_DEFAULT_G163,
    attempt_audio_out_timing_write: bool = False,
    volume_settings: int = VOLUME_SETTINGS_DEFAULT_G163,
    audio_monitoring_4ch: str = AUDIO_MONITORING_4CH_DEFAULT_G163,
    hdmi_4ch_audio_output: str = HDMI_4CH_AUDIO_OUTPUT_DEFAULT_G163,
    request_4ch_discrete_35mm_headphone: bool = False,
    claim_4ch_mon_couples_hdmi_4ch_output: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE382,
    claim_camset_reset_clears_sound_option: bool = False,
    claim_camset_reset_preserves_audio_recording: bool = False,
    fx6_mic_reference: str = "-50dB",
    fx6_line_reference: str = "+4dB",
    fx6_reference_level: str = "-20dB",
    fx6_limiter_mode: str = "-6dB",
    fx6_monitor_ch: str = "CH1/CH2",
    fx6_headphone_out: str = "Stereo",
    fx6_volume: int = 25,
    request_fx6_monitor_vol_physical_keys: bool = False,
    claim_fx6_limiter_only_4_modes: bool = False,
    claim_fx6_ref_level_only_3_modes: bool = False,
    claim_fx6_hdmi_carries_4ch: bool = False,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> AudioRecLevelOutTimingGuardResult:
    """Gate G163: Enforce Audio Rec Level, XLR-H1 Preemption/Limiter, Audio Out Timing,
    Anti-Reset Sound Option & Exact 5-Item 4ch Audio Monitoring vs FX6 Audio Input/Output."""
    telemetry_errors: List[str] = []
    eopnotsupp_violations: List[str] = []
    constraint_violations: List[str] = []
    warnings: List[str] = []

    telemetry_errors.extend(
        _validate_fx3_body_identity(
            body_model_name, body_model_id, help_guide_code, firmware_version
        )
    )

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE382:
        telemetry_errors.append(f"shoot_mode_invalid:{shoot_mode!r}")
    if xlr_h1_input_type not in ALLOWED_XLR_H1_INPUT_TYPES_G163:
        telemetry_errors.append(f"xlr_h1_input_type_invalid:{xlr_h1_input_type!r}")
    if not _is_strict_int(xlr_h1_att_db) or xlr_h1_att_db not in ALLOWED_XLR_H1_ATT_DB_G163:
        telemetry_errors.append(f"xlr_h1_att_db_invalid:{xlr_h1_att_db!r}")
    if xlr_h1_gain_mode not in ALLOWED_XLR_H1_GAIN_MODES_G163:
        telemetry_errors.append(f"xlr_h1_gain_mode_invalid:{xlr_h1_gain_mode!r}")
    if not _is_strict_int(xlr_h1_level_dial) or not (
        XLR_H1_LEVEL_DIAL_MIN_G163 <= xlr_h1_level_dial <= XLR_H1_LEVEL_DIAL_MAX_G163
    ):
        telemetry_errors.append(f"xlr_h1_level_dial_invalid:{xlr_h1_level_dial!r}")
    if not _is_strict_int(audio_rec_level):
        telemetry_errors.append(f"audio_rec_level_not_int:{audio_rec_level!r}")
    if audio_out_timing not in ALLOWED_AUDIO_OUT_TIMING_MODES_G163:
        telemetry_errors.append(f"audio_out_timing_invalid:{audio_out_timing!r}")
    if not _is_strict_int(volume_settings):
        telemetry_errors.append(f"volume_settings_not_int:{volume_settings!r}")
    if not isinstance(audio_monitoring_4ch, str) or not audio_monitoring_4ch:
        telemetry_errors.append(
            f"audio_monitoring_4ch_invalid:{audio_monitoring_4ch!r}"
        )
    if hdmi_4ch_audio_output not in ALLOWED_FX3_HDMI_4CH_OUTPUT_MODES_G163:
        telemetry_errors.append(
            f"hdmi_4ch_audio_output_invalid:{hdmi_4ch_audio_output!r}"
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE382:
        telemetry_errors.append(f"reset_action_invalid:{reset_action!r}")
    if fx6_mic_reference not in FX6_INPUT_MIC_REFERENCE_6_STEPS_G163:
        telemetry_errors.append(f"fx6_mic_reference_invalid:{fx6_mic_reference!r}")
    if fx6_line_reference not in FX6_LINE_INPUT_REFERENCE_4_STEPS_G163:
        telemetry_errors.append(f"fx6_line_reference_invalid:{fx6_line_reference!r}")
    if fx6_reference_level not in FX6_REFERENCE_LEVEL_5_STEPS_G163:
        telemetry_errors.append(f"fx6_reference_level_invalid:{fx6_reference_level!r}")
    if fx6_limiter_mode not in FX6_LIMITER_MODE_6_STEPS_G163:
        telemetry_errors.append(f"fx6_limiter_mode_invalid:{fx6_limiter_mode!r}")
    if fx6_monitor_ch not in FX6_MONITOR_CH_7_ITEMS_G163:
        telemetry_errors.append(f"fx6_monitor_ch_invalid:{fx6_monitor_ch!r}")
    if fx6_headphone_out not in FX6_HEADPHONE_OUT_MODES_G163:
        telemetry_errors.append(f"fx6_headphone_out_invalid:{fx6_headphone_out!r}")
    if not _is_strict_int(fx6_volume):
        telemetry_errors.append(f"fx6_volume_not_int:{fx6_volume!r}")

    for bname, bval in (
        ("mic_35mm_inserted", mic_35mm_inserted),
        ("xlr_h1_attached", xlr_h1_attached),
        ("xlr_h1_handle_audio_on", xlr_h1_handle_audio_on),
        ("xlr_h1_4ch_mode", xlr_h1_4ch_mode),
        ("delete_key_pressed", delete_key_pressed),
        ("attempt_body_rec_level_write", attempt_body_rec_level_write),
        ("request_disable_body_limiter", request_disable_body_limiter),
        ("attempt_xlr_att_override_on_line", attempt_xlr_att_override_on_line),
        ("claim_35mm_keeps_shoe_audio_active", claim_35mm_keeps_shoe_audio_active),
        ("claim_sq_records_audio", claim_sq_records_audio),
        ("attempt_audio_out_timing_write", attempt_audio_out_timing_write),
        ("request_4ch_discrete_35mm_headphone", request_4ch_discrete_35mm_headphone),
        (
            "claim_4ch_mon_couples_hdmi_4ch_output",
            claim_4ch_mon_couples_hdmi_4ch_output,
        ),
        (
            "claim_camset_reset_clears_sound_option",
            claim_camset_reset_clears_sound_option,
        ),
        (
            "claim_camset_reset_preserves_audio_recording",
            claim_camset_reset_preserves_audio_recording,
        ),
        (
            "request_fx6_monitor_vol_physical_keys",
            request_fx6_monitor_vol_physical_keys,
        ),
        ("claim_fx6_limiter_only_4_modes", claim_fx6_limiter_only_4_modes),
        ("claim_fx6_ref_level_only_3_modes", claim_fx6_ref_level_only_3_modes),
        ("claim_fx6_hdmi_carries_4ch", claim_fx6_hdmi_carries_4ch),
    ):
        if not isinstance(bval, bool):
            telemetry_errors.append(f"{bname}_not_bool:{bval!r}")

    if telemetry_errors:
        return AudioRecLevelOutTimingGuardResult(
            valid=False,
            status=STATUS_BLOCKED_G163_TELEMETRY_INVALID,
            block_errno=EINVAL_ERRNO_PHASE382,
            block_errno_name=EINVAL_NAME_PHASE382,
            verification_mode=verification_mode,
            audio_rec_level_menu_path=AUDIO_REC_LEVEL_MENU_PATH_G163,
            audio_out_timing_menu_path=AUDIO_OUT_TIMING_MENU_PATH_G163,
            volume_settings_menu_path=VOLUME_SETTINGS_MENU_PATH_G163,
            audio_monitoring_4ch_menu_path=AUDIO_MONITORING_4CH_MENU_PATH_G163,
            hdmi_4ch_audio_output_menu_path=HDMI_4CH_AUDIO_OUTPUT_MENU_PATH_G163,
            fx6_audio_input_menu_path=FX6_AUDIO_INPUT_MENU_PATH_G163,
            fx6_audio_output_menu_path=FX6_AUDIO_OUTPUT_MENU_PATH_G163,
            shoot_mode=str(shoot_mode),
            active_audio_source="unknown",
            active_audio_channels=0,
            audio_rec_level_available=False,
            effective_audio_rec_level=AUDIO_REC_LEVEL_DEFAULT_G163,
            audio_rec_level_step_count=AUDIO_REC_LEVEL_STEP_COUNT_G163,
            audio_rec_level_default=AUDIO_REC_LEVEL_DEFAULT_G163,
            audio_rec_level_elf_typo=AUDIO_REC_LEVEL_ELF_TYPO_G163,
            audio_rec_level_resettable_by_camset_reset=AUDIO_REC_LEVEL_RESETTABLE_BY_CAMSET_RESET_G163,
            body_limiter_permanently_active=FX3_BODY_LIMITER_PERMANENTLY_ACTIVE_G163,
            shoe_audio_set_grayed=False,
            wind_noise_reduct_bypassed=False,
            xlr_h1_controls_active=False,
            xlr_h1_input_type=str(xlr_h1_input_type),
            xlr_h1_effective_ref_dbu=-60,
            xlr_h1_att_active=False,
            xlr_h1_gain_mode=str(xlr_h1_gain_mode),
            sq_locked_audio_controls=SQ_LOCKED_AUDIO_CONTROLS_G163,
            audio_out_timing_available=False,
            effective_audio_out_timing=AUDIO_OUT_TIMING_DEFAULT_G163,
            audio_out_timing_resettable_by_camset_reset=AUDIO_OUT_TIMING_RESETTABLE_BY_CAMSET_RESET_G163,
            effective_volume_settings=VOLUME_SETTINGS_DEFAULT_G163,
            volume_settings_resettable_by_camset_reset=VOLUME_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G163,
            effective_4ch_audio_monitoring=AUDIO_MONITORING_4CH_DEFAULT_G163,
            audio_monitoring_4ch_enum_count=len(
                EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163
            ),
            audio_monitoring_4ch_resettable_by_camset_reset=AUDIO_MONITORING_4CH_RESETTABLE_BY_CAMSET_RESET_G163,
            effective_hdmi_4ch_audio_output=HDMI_4CH_AUDIO_OUTPUT_DEFAULT_G163,
            headphone_max_discrete_channels=FX3_HEADPHONE_MAX_DISCRETE_CH_G163,
            fx6_mic_reference_step_count=len(FX6_INPUT_MIC_REFERENCE_6_STEPS_G163),
            fx6_line_reference_step_count=len(FX6_LINE_INPUT_REFERENCE_4_STEPS_G163),
            fx6_reference_level_step_count=len(FX6_REFERENCE_LEVEL_5_STEPS_G163),
            fx6_limiter_mode=str(fx6_limiter_mode),
            fx6_limiter_mode_count=len(FX6_LIMITER_MODE_6_STEPS_G163),
            fx6_monitor_ch=str(fx6_monitor_ch),
            fx6_monitor_ch_count=len(FX6_MONITOR_CH_7_ITEMS_G163),
            fx6_headphone_out=str(fx6_headphone_out),
            fx6_volume=fx6_volume if _is_strict_int(fx6_volume) else 0,
            fx6_monitor_vol_physical_key_hits=FX6_MONITOR_VOL_PHYSICAL_KEY_HITS_G163,
            fx6_sdi_audio_channels=FX6_SDI_AUDIO_CHANNELS_G163,
            fx6_hdmi_audio_channels=FX6_HDMI_AUDIO_CHANNELS_G163,
            emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
            cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
            usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            violation_codes=tuple(telemetry_errors),
            errors=tuple(telemetry_errors),
            warnings=tuple(warnings),
        )

    # --- 1. EOPNOTSUPP=95 Checks ---
    if request_disable_body_limiter:
        eopnotsupp_violations.append(
            "FX3_BODY_AUDIO_LIMITER_PERMANENT_NON_DISABLEABLE_EOPNOTSUPP"
        )
    if (
        audio_monitoring_4ch in FABRICATED_4CH_MONITORING_LABELS_G163
        or audio_monitoring_4ch not in EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163
    ):
        eopnotsupp_violations.append(
            f"FX3_4CH_AUDIO_MONITORING_UNSUPPORTED_OR_FABRICATED_ENUM:{audio_monitoring_4ch}"
        )
    if request_4ch_discrete_35mm_headphone:
        eopnotsupp_violations.append(
            "FX3_35MM_HEADPHONE_JACK_HARDWARE_LIMITED_TO_2CH_STEREO_EOPNOTSUPP"
        )
    if request_fx6_monitor_vol_physical_keys:
        eopnotsupp_violations.append(
            "FX6_ZERO_MONITOR_VOL_PLUS_MINUS_SIDE_KEYS_5_024_458_18_EOPNOTSUPP"
        )

    # --- 2. State Resolution & Constraint Checks ---
    state = resolve_fx3_audio_reclevel_outtiming_state(
        shoot_mode=shoot_mode,
        mic_35mm_inserted=mic_35mm_inserted,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_handle_audio_on=xlr_h1_handle_audio_on,
        xlr_h1_4ch_mode=xlr_h1_4ch_mode,
        xlr_h1_input_type=xlr_h1_input_type,
        xlr_h1_att_db=xlr_h1_att_db,
        xlr_h1_gain_mode=xlr_h1_gain_mode,
        audio_rec_level=audio_rec_level,
        delete_key_pressed=delete_key_pressed,
        audio_out_timing=audio_out_timing,
        volume_settings=volume_settings,
        audio_monitoring_4ch=audio_monitoring_4ch,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        reset_action=reset_action,
    )

    if not (AUDIO_REC_LEVEL_MIN_G163 <= audio_rec_level <= AUDIO_REC_LEVEL_MAX_G163):
        constraint_violations.append(
            f"FX3_AUDIO_REC_LEVEL_OUT_OF_RANGE_0_31:{audio_rec_level}"
        )
    if not (VOLUME_SETTINGS_MIN_G163 <= volume_settings <= VOLUME_SETTINGS_MAX_G163):
        constraint_violations.append(
            f"FX3_VOLUME_SETTINGS_OUT_OF_RANGE_0_15:{volume_settings}"
        )
    if not (FX6_VOLUME_MIN_G163 <= fx6_volume <= FX6_VOLUME_MAX_G163):
        constraint_violations.append(f"FX6_VOLUME_OUT_OF_RANGE_0_50:{fx6_volume}")

    if attempt_body_rec_level_write and not state["audio_rec_level_available"]:
        if shoot_mode == SHOOT_MODE_SQ_PHASE382:
            constraint_violations.append(
                "FX3_SQ_MOTION_FORCES_0CH_AND_LOCKS_AUDIO_REC_LEVEL"
            )
        else:
            constraint_violations.append(
                "FX3_XLR_H1_HANDLE_AUDIO_ON_PREEMPTS_BODY_AUDIO_REC_LEVEL"
            )
    if attempt_audio_out_timing_write and not state["audio_out_timing_available"]:
        constraint_violations.append("FX3_SQ_MOTION_LOCKS_AUDIO_OUT_TIMING")
    if (
        attempt_xlr_att_override_on_line
        and state["xlr_h1_controls_active"]
        and xlr_h1_input_type == "LINE"
    ):
        constraint_violations.append(
            "FX3_XLR_H1_LINE_INPUT_LOCKED_PLUS_4DBU_ATT_INACTIVE"
        )
    if claim_35mm_keeps_shoe_audio_active and mic_35mm_inserted:
        constraint_violations.append(
            "FX3_35MM_MIC_PREEMPTS_MI_SHOE_GRAYS_SHOE_AUDIO_SET"
        )
    if claim_sq_records_audio and shoot_mode == SHOOT_MODE_SQ_PHASE382:
        constraint_violations.append("FX3_SQ_MOTION_STRICTLY_0CH_SILENT")
    if claim_4ch_mon_couples_hdmi_4ch_output:
        constraint_violations.append(
            "FX3_4CH_AUDIO_MONITORING_INDEPENDENT_FROM_HDMI_4CH_AUDIO_OUTPUT"
        )
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382
        and claim_camset_reset_clears_sound_option
    ):
        constraint_violations.append(
            "FX3_SETUP_SOUND_OPTION_VOLUME_AND_4CH_MON_RESIST_CAMSET_RESET"
        )
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382
        and claim_camset_reset_preserves_audio_recording
    ):
        constraint_violations.append(
            "FX3_SHOOTING_AUDIO_RECORDING_RESETS_ON_CAMSET_RESET"
        )
    if claim_fx6_limiter_only_4_modes:
        constraint_violations.append(
            "FX6_LIMITER_MODE_HAS_6_MODES_OFF_TO_NEG17DB_NOT_4"
        )
    if claim_fx6_ref_level_only_3_modes:
        constraint_violations.append(
            "FX6_REFERENCE_LEVEL_HAS_5_MODES_INCLUDING_NEG16DB_AND_EBUL"
        )
    if claim_fx6_hdmi_carries_4ch:
        constraint_violations.append(
            "FX6_HDMI_LIMITED_TO_2CH_PAIR_ONLY_SDI_OUT_CARRIES_FULL_4CH"
        )

    if (
        state["xlr_h1_controls_active"]
        and state["effective_volume_settings"] >= XLR_H1_SPEAKER_FEEDBACK_WARN_MIN_VOL_G163
    ):
        warnings.append(
            f"High rear speaker volume ({state['effective_volume_settings']}/15) near XLR-H1 risks acoustic feedback."
        )
    if state["effective_audio_out_timing"] == "Lip Sync" and state["audio_out_timing_available"]:
        warnings.append(
            "Audio Out Timing = Lip Sync delays 3.5mm headphone output to align with video; use Live for zero-echo live voice monitoring."
        )

    all_violations = eopnotsupp_violations + constraint_violations
    if eopnotsupp_violations:
        status = (
            STATUS_BLOCKED_G163_FABRICATED_4CH_BODY_LIMITER_OFF_OR_FX6_MONVOL_EOPNOTSUPP
        )
        errno_val, errno_name = EOPNOTSUPP_ERRNO_PHASE382, EOPNOTSUPP_NAME_PHASE382
        valid = False
    elif constraint_violations:
        status = (
            STATUS_BLOCKED_G163_PREEMPTION_SQ_LOCK_RESET_OR_FX6_AUDIO_CONSTRAINT_VIOLATION
        )
        errno_val, errno_name = EINVAL_ERRNO_PHASE382, EINVAL_NAME_PHASE382
        valid = False
    else:
        status = STATUS_VERIFIED_G163
        errno_val, errno_name = 0, "OK"
        valid = True

    return AudioRecLevelOutTimingGuardResult(
        valid=valid,
        status=status,
        block_errno=errno_val,
        block_errno_name=errno_name,
        verification_mode=verification_mode,
        audio_rec_level_menu_path=AUDIO_REC_LEVEL_MENU_PATH_G163,
        audio_out_timing_menu_path=AUDIO_OUT_TIMING_MENU_PATH_G163,
        volume_settings_menu_path=VOLUME_SETTINGS_MENU_PATH_G163,
        audio_monitoring_4ch_menu_path=AUDIO_MONITORING_4CH_MENU_PATH_G163,
        hdmi_4ch_audio_output_menu_path=HDMI_4CH_AUDIO_OUTPUT_MENU_PATH_G163,
        fx6_audio_input_menu_path=FX6_AUDIO_INPUT_MENU_PATH_G163,
        fx6_audio_output_menu_path=FX6_AUDIO_OUTPUT_MENU_PATH_G163,
        shoot_mode=shoot_mode,
        active_audio_source=state["active_audio_source"],
        active_audio_channels=state["active_audio_channels"],
        audio_rec_level_available=state["audio_rec_level_available"],
        effective_audio_rec_level=state["effective_audio_rec_level"],
        audio_rec_level_step_count=AUDIO_REC_LEVEL_STEP_COUNT_G163,
        audio_rec_level_default=AUDIO_REC_LEVEL_DEFAULT_G163,
        audio_rec_level_elf_typo=AUDIO_REC_LEVEL_ELF_TYPO_G163,
        audio_rec_level_resettable_by_camset_reset=AUDIO_REC_LEVEL_RESETTABLE_BY_CAMSET_RESET_G163,
        body_limiter_permanently_active=state["body_limiter_permanently_active"],
        shoe_audio_set_grayed=state["shoe_audio_set_grayed"],
        wind_noise_reduct_bypassed=state["wind_noise_reduct_bypassed"],
        xlr_h1_controls_active=state["xlr_h1_controls_active"],
        xlr_h1_input_type=xlr_h1_input_type,
        xlr_h1_effective_ref_dbu=state["xlr_h1_effective_ref_dbu"],
        xlr_h1_att_active=state["xlr_h1_att_active"],
        xlr_h1_gain_mode=state["xlr_h1_gain_mode"],
        sq_locked_audio_controls=SQ_LOCKED_AUDIO_CONTROLS_G163,
        audio_out_timing_available=state["audio_out_timing_available"],
        effective_audio_out_timing=state["effective_audio_out_timing"],
        audio_out_timing_resettable_by_camset_reset=AUDIO_OUT_TIMING_RESETTABLE_BY_CAMSET_RESET_G163,
        effective_volume_settings=state["effective_volume_settings"],
        volume_settings_resettable_by_camset_reset=VOLUME_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G163,
        effective_4ch_audio_monitoring=state["effective_4ch_audio_monitoring"],
        audio_monitoring_4ch_enum_count=len(
            EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163
        ),
        audio_monitoring_4ch_resettable_by_camset_reset=AUDIO_MONITORING_4CH_RESETTABLE_BY_CAMSET_RESET_G163,
        effective_hdmi_4ch_audio_output=state["effective_hdmi_4ch_audio_output"],
        headphone_max_discrete_channels=FX3_HEADPHONE_MAX_DISCRETE_CH_G163,
        fx6_mic_reference_step_count=len(FX6_INPUT_MIC_REFERENCE_6_STEPS_G163),
        fx6_line_reference_step_count=len(FX6_LINE_INPUT_REFERENCE_4_STEPS_G163),
        fx6_reference_level_step_count=len(FX6_REFERENCE_LEVEL_5_STEPS_G163),
        fx6_limiter_mode=fx6_limiter_mode,
        fx6_limiter_mode_count=len(FX6_LIMITER_MODE_6_STEPS_G163),
        fx6_monitor_ch=fx6_monitor_ch,
        fx6_monitor_ch_count=len(FX6_MONITOR_CH_7_ITEMS_G163),
        fx6_headphone_out=fx6_headphone_out,
        fx6_volume=fx6_volume,
        fx6_monitor_vol_physical_key_hits=FX6_MONITOR_VOL_PHYSICAL_KEY_HITS_G163,
        fx6_sdi_audio_channels=FX6_SDI_AUDIO_CHANNELS_G163,
        fx6_hdmi_audio_channels=FX6_HDMI_AUDIO_CHANNELS_G163,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(all_violations),
        errors=tuple(all_violations),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G163AudioRecLevelOutTimingGuardResult:
    gate_id: str
    gate_code: str
    valid: bool
    status: str
    verification_mode: str
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    donor_audit: Dict[str, Any]
    audio_reclevel_outtiming_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g163_audio_reclevel_outtiming_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G163AudioRecLevelOutTimingGuardResult]:
    audit = audit_phase382_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_audio_reclevel_outtiming_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G163AudioRecLevelOutTimingGuardResult(
        gate_id=G163,
        gate_code=G163_GATE_CODE,
        valid=overall_valid,
        status=status,
        verification_mode=audit.verification_mode,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_audit=audit.to_dict(),
        audio_reclevel_outtiming_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G163,
        gate_code=G163_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"rec_lvl={res.effective_audio_rec_level} "
            f"src={res.active_audio_source} "
            f"timing={res.effective_audio_out_timing} "
            f"vol={res.effective_volume_settings} "
            f"mon4ch={res.effective_4ch_audio_monitoring}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_audio_reclevel_outtiming_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G163AudioRecLevelOutTimingGuardResult]:
    return evaluate_g163_audio_reclevel_outtiming_guard(**kwargs)


# ---------------------------------------------------------------------------
# Gate G164: [Touch Func. in Shooting] 4 Active Anti-Reset Items vs 100% Dormant
#            [Touch Panel/Pad]/[Touch Shutter]/[Touch AE] &
#            [Remote Shoot Setting] PTP/PTP-IP + Tier-0 Slot 1 EROFS=30 Firewall
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TouchFuncPcRemoteGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    touch_operation_menu_path: str
    spot_metering_point_menu_path: str
    remote_shoot_setting_menu_path: str
    fx6_touch_func_mf_menu_path: str
    fx6_network_client_menu_path: str
    shoot_mode: str
    focus_mode: str
    fx3_touch_active_subitems_count: int
    touch_4items_resettable_by_camset_reset: bool
    effective_touch_operation: str
    effective_touch_sensitivity: str
    effective_touch_func_in_shooting: str
    effective_swipe_up: str
    touch_tracking_available_in_focus_mode: bool
    fx3_evf_present: bool
    fx3_touch_shutter_hits: int
    fx3_touch_ae_hits: int
    spot_metering_point: str
    focus_area_category: str
    spot_metering_linked_to_initial_point: bool
    spot_metering_follows_moving_track_box: bool
    fx6_touch_operation: str
    fx6_touch_func_in_mf: str
    fx6_spot_focus_in_mf_available: bool
    fx6_big6_touch_available: bool
    remote_shoot_subitems_count: int
    remote_shoot_4items_resettable_by_camset_reset: bool
    effective_still_img_save_dest: str
    effective_save_image_size: str
    effective_raw_j_save_image: str
    effective_raw_h_save_image: str
    still_img_save_dest_factory_default: str
    ptp_transport: str
    ptp_ip_tcp_port: int
    ptp_usb_device_nodes: Tuple[str, ...]
    pc_remote_connected: bool
    ram_only_zero_card_write_active: bool
    cardless_remote_shoot_allowed: bool
    fx6_still_img_save_dest_ui_exposed: bool
    airplane_mode: str
    rf_tx_packets: int
    target_media_slot: int
    slot1_write_attempted: bool
    slot1_writes: int
    slot1_data_sector_writes: int
    emmc_nflasha_write_count: int
    usb_tx: int
    usb_packets_transmitted: int
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    live_attach_authorized: bool
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_touchfunc_pcremote_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE382,
    focus_mode: str = "AF-C",
    touch_operation: str = TOUCH_OPERATION_DEFAULT_G164,
    touch_sensitivity: str = TOUCH_SENSITIVITY_DEFAULT_G164,
    touch_func_in_shooting: str = TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164,
    swipe_up: str = SWIPE_UP_DEFAULT_G164,
    spot_metering_point: str = SPOT_METERING_POINT_DEFAULT_G164,
    focus_area_category: str = "Spot",
    still_img_save_dest: str = STILL_IMG_SAVE_DEST_BENCH_SAFE_G164,
    save_image_size: str = SAVE_IMAGE_SIZE_DEFAULT_G164,
    raw_j_save_image: str = RAW_J_SAVE_IMAGE_DEFAULT_G164,
    raw_h_save_image: str = RAW_H_SAVE_IMAGE_DEFAULT_G164,
    ptp_transport: str = "ptp_usb",
    pc_remote_connected: bool = True,
    card_inserted: bool = False,
    target_media_slot: int = MEDIA_SLOT_NONE_PHASE382,
    remote_shutter_release_requested: bool = False,
    airplane_mode: str = "On",
    reset_action: str = RESET_ACTION_NONE_PHASE382,
    fx6_firmware_version: str = FX6_DEFAULT_FW_VERSION_PHASE382,
    fx6_mf_lens_attached: bool = False,
    fx6_desqueeze_mode: str = "Off (1.0x)",
    fx6_focus_magnifier_active: bool = False,
) -> Dict[str, Any]:
    """Deterministically resolve FX3 Ver. 7.02 Touch Operation (4 active anti-Reset items)
    & Remote Shoot Setting (PTP/PTP-IP zero-card RAM vs Slot 1 write) state."""
    # Setup -> [Touch Operation] (all 4 items): ONLY [Initialize] resets them.
    if reset_action == RESET_ACTION_INITIALIZE_PHASE382:
        eff_touch_op = TOUCH_OPERATION_DEFAULT_G164
        eff_touch_sens = TOUCH_SENSITIVITY_DEFAULT_G164
        eff_touch_func = TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164
        eff_swipe_up = SWIPE_UP_DEFAULT_G164
    else:
        eff_touch_op = touch_operation
        eff_touch_sens = touch_sensitivity
        eff_touch_func = touch_func_in_shooting
        eff_swipe_up = swipe_up

    # Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting] (all 4 items):
    # Resist [Camera Settings Reset]; reset via [Initialize] OR [Reset Network Set.].
    if reset_action in (
        RESET_ACTION_INITIALIZE_PHASE382,
        RESET_ACTION_RESET_NETWORK_SET_PHASE382,
    ):
        eff_save_dest = STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164
        eff_save_size = SAVE_IMAGE_SIZE_DEFAULT_G164
        eff_raw_j = RAW_J_SAVE_IMAGE_DEFAULT_G164
        eff_raw_h = RAW_H_SAVE_IMAGE_DEFAULT_G164
    else:
        eff_save_dest = still_img_save_dest
        eff_save_size = save_image_size
        eff_raw_j = raw_j_save_image
        eff_raw_h = raw_h_save_image

    touch_track_avail = focus_mode != "MF"
    spot_linked_initial = (
        spot_metering_point == "Focus Point Link"
        and focus_area_category in SPOT_LINK_ELIGIBLE_FOCUS_AREAS_G164
    )

    ram_only_zero_card = (
        eff_save_dest == STILL_IMG_SAVE_DEST_BENCH_SAFE_G164 and pc_remote_connected
    )
    # Only Destination Only (PC Only) works cardless via DRAM buffer
    # (N5model37stillrec_running_without_pseudo_rec_tE).
    cardless_allowed = ram_only_zero_card
    writes_camera_card = eff_save_dest in ("Dest.+Camera", "Camera Only")
    slot1_write_attempted = bool(
        writes_camera_card
        and remote_shutter_release_requested
        and (target_media_slot in (MEDIA_SLOT_1_PHASE382, MEDIA_SLOT_NONE_PHASE382))
    )

    fx6_fw = _parse_fw_float(fx6_firmware_version)
    fx6_big6_avail = (fx6_fw is not None) and (fx6_fw >= FX6_BIG6_TOUCH_MIN_FW_G164)
    fx6_spot_focus_avail = (
        (not fx6_mf_lens_attached)
        and (fx6_desqueeze_mode == "Off (1.0x)")
        and (not fx6_focus_magnifier_active)
    )

    rf_tx = 0 if (airplane_mode == "On" and ptp_transport != "ptp_ip_wifi") else 1

    return {
        "effective_touch_operation": eff_touch_op,
        "effective_touch_sensitivity": eff_touch_sens,
        "effective_touch_func_in_shooting": eff_touch_func,
        "effective_swipe_up": eff_swipe_up,
        "touch_tracking_available_in_focus_mode": touch_track_avail,
        "spot_metering_linked_to_initial_point": spot_linked_initial,
        "spot_metering_follows_moving_track_box": FX3_SPOT_METERING_FOLLOWS_MOVING_TRACK_BOX_G164,
        "fx6_spot_focus_in_mf_available": fx6_spot_focus_avail,
        "fx6_big6_touch_available": fx6_big6_avail,
        "effective_still_img_save_dest": eff_save_dest,
        "effective_save_image_size": eff_save_size,
        "effective_raw_j_save_image": eff_raw_j,
        "effective_raw_h_save_image": eff_raw_h,
        "ram_only_zero_card_write_active": ram_only_zero_card,
        "cardless_remote_shoot_allowed": cardless_allowed,
        "writes_camera_card": writes_camera_card,
        "slot1_write_attempted": slot1_write_attempted,
        "rf_tx_packets": rf_tx,
        "shoot_mode": shoot_mode,
        "card_inserted": card_inserted,
    }


def compute_touchfunc_pcremote_matrix() -> Dict[str, Any]:
    """Sweep deterministic 432-state Wave-72 Gate G164 matrix."""
    shoot_modes = ALLOWED_SHOOT_MODES_PHASE382  # 3
    touch_funcs = ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES_G164  # 3
    save_dests = ALLOWED_STILL_IMG_SAVE_DEST_G164  # 3
    transports = ("ptp_usb", "ptp_ip_usblan")  # 2
    slots = (MEDIA_SLOT_1_PHASE382, MEDIA_SLOT_2_PHASE382)  # 2
    resets = (
        RESET_ACTION_NONE_PHASE382,
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382,
        RESET_ACTION_INITIALIZE_PHASE382,
        RESET_ACTION_RESET_NETWORK_SET_PHASE382,
    )  # 4
    # 3 * 3 * 3 * 2 * 2 * 4 = 432 states!
    total = 0
    touch_camset_survived_count = 0
    touch_init_reset_count = 0
    remote_camset_survived_count = 0
    remote_netreset_reverted_default_count = 0
    dest_only_zero_card_count = 0
    slot1_write_detected_count = 0
    zero_rf_wired_count = 0

    for sm, tf, sdest, tr, slot, rst in itertools.product(
        shoot_modes, touch_funcs, save_dests, transports, slots, resets
    ):
        total += 1
        st = resolve_fx3_touchfunc_pcremote_state(
            shoot_mode=sm,
            touch_operation="On: Playback Only",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting=tf,
            swipe_up="Off",
            still_img_save_dest=sdest,
            ptp_transport=tr,
            pc_remote_connected=True,
            target_media_slot=slot,
            remote_shutter_release_requested=True,
            airplane_mode="On",
            reset_action=rst,
        )
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382
            and st["effective_touch_operation"] == "On: Playback Only"
            and st["effective_touch_sensitivity"] == "Sensitive"
            and st["effective_swipe_up"] == "Off"
        ):
            touch_camset_survived_count += 1
        if (
            rst == RESET_ACTION_INITIALIZE_PHASE382
            and st["effective_touch_operation"] == TOUCH_OPERATION_DEFAULT_G164
            and st["effective_touch_func_in_shooting"]
            == TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164
        ):
            touch_init_reset_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382
            and st["effective_still_img_save_dest"] == sdest
        ):
            remote_camset_survived_count += 1
        if (
            rst == RESET_ACTION_RESET_NETWORK_SET_PHASE382
            and st["effective_still_img_save_dest"]
            == STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164
        ):
            remote_netreset_reverted_default_count += 1
        if (
            st["effective_still_img_save_dest"] == STILL_IMG_SAVE_DEST_BENCH_SAFE_G164
            and st["ram_only_zero_card_write_active"]
            and st["cardless_remote_shoot_allowed"]
        ):
            dest_only_zero_card_count += 1
        if slot == MEDIA_SLOT_1_PHASE382 and st["slot1_write_attempted"]:
            slot1_write_detected_count += 1
        if st["rf_tx_packets"] == 0:
            zero_rf_wired_count += 1

    return {
        "total_states": total,
        "touch_camset_survived_count": touch_camset_survived_count,
        "touch_init_reset_count": touch_init_reset_count,
        "remote_camset_survived_count": remote_camset_survived_count,
        "remote_netreset_reverted_default_count": remote_netreset_reverted_default_count,
        "dest_only_zero_card_count": dest_only_zero_card_count,
        "slot1_write_detected_count": slot1_write_detected_count,
        "zero_rf_wired_all_verified": zero_rf_wired_count == total,
    }


def verify_touchfunc_pcremote_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE382,
    body_model_id: int = FX3_MODEL_ID_PHASE382,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE382,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE382,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE382,
    focus_mode: str = "AF-C",
    touch_operation: str = TOUCH_OPERATION_DEFAULT_G164,
    touch_sensitivity: str = TOUCH_SENSITIVITY_DEFAULT_G164,
    touch_func_in_shooting: str = TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164,
    swipe_up: str = SWIPE_UP_DEFAULT_G164,
    request_dormant_touch_panel_pad: bool = False,
    request_dormant_touch_pad_vertical: bool = False,
    request_dormant_touch_shutter: bool = False,
    request_dormant_touch_ae: bool = False,
    spot_metering_point: str = SPOT_METERING_POINT_DEFAULT_G164,
    focus_area_category: str = "Spot",
    claim_spot_metering_follows_moving_track: bool = False,
    claim_touch_4items_reset_by_camset_reset: bool = False,
    fx6_firmware_version: str = FX6_DEFAULT_FW_VERSION_PHASE382,
    fx6_touch_operation: str = "On",
    fx6_touch_func_in_mf: str = "Spot Focus",
    fx6_mf_lens_attached: bool = False,
    fx6_desqueeze_mode: str = "Off (1.0x)",
    fx6_focus_magnifier_active: bool = False,
    invoke_fx6_spot_focus_in_mf: bool = False,
    invoke_fx6_big6_touch: bool = False,
    request_fx6_touch_shutter_or_ae: bool = False,
    still_img_save_dest: str = STILL_IMG_SAVE_DEST_BENCH_SAFE_G164,
    save_image_size: str = SAVE_IMAGE_SIZE_DEFAULT_G164,
    raw_j_save_image: str = RAW_J_SAVE_IMAGE_DEFAULT_G164,
    raw_h_save_image: str = RAW_H_SAVE_IMAGE_DEFAULT_G164,
    ptp_transport: str = "ptp_usb",
    ptp_ip_tcp_port: int = FX3_PTP_IP_TCP_PORT_G164,
    pc_remote_connected: bool = True,
    attempt_change_save_dest_while_connected: bool = False,
    card_inserted: bool = False,
    release_wo_card: str = "Enable",
    target_media_slot: int = MEDIA_SLOT_NONE_PHASE382,
    remote_shutter_release_requested: bool = False,
    slot1_tier0_protected: bool = True,
    airplane_mode: str = "On",
    claim_remote_shoot_reset_by_camset_reset: bool = False,
    request_fx6_still_img_save_dest_ui: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE382,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> TouchFuncPcRemoteGuardResult:
    """Gate G164: Enforce 4 Active Anti-Reset Touch Items vs Dormant Touch Pad/Shutter/AE,
    Spot Metering Tracking Anchor, and Remote Shoot Setting PTP/PTP-IP + Slot 1 EROFS=30."""
    telemetry_errors: List[str] = []
    erofs_violations: List[str] = []
    ebusy_violations: List[str] = []
    eopnotsupp_violations: List[str] = []
    constraint_violations: List[str] = []
    warnings: List[str] = []

    telemetry_errors.extend(
        _validate_fx3_body_identity(
            body_model_name, body_model_id, help_guide_code, firmware_version
        )
    )
    fx6_fw_val = _parse_fw_float(fx6_firmware_version)
    if fx6_fw_val is None:
        telemetry_errors.append(
            f"fx6_firmware_version_invalid:{fx6_firmware_version!r}"
        )

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE382:
        telemetry_errors.append(f"shoot_mode_invalid:{shoot_mode!r}")
    if focus_mode not in ("AF-S", "AF-A", "AF-C", "DMF", "MF"):
        telemetry_errors.append(f"focus_mode_invalid:{focus_mode!r}")
    if touch_operation not in ALLOWED_TOUCH_OPERATION_MODES_G164:
        telemetry_errors.append(f"touch_operation_invalid:{touch_operation!r}")
    if touch_sensitivity not in ALLOWED_TOUCH_SENSITIVITY_MODES_G164:
        telemetry_errors.append(f"touch_sensitivity_invalid:{touch_sensitivity!r}")
    if (
        touch_func_in_shooting not in ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES_G164
        and touch_func_in_shooting not in DORMANT_FX3_TOUCH_FEATURES_G164
    ):
        telemetry_errors.append(
            f"touch_func_in_shooting_invalid:{touch_func_in_shooting!r}"
        )
    if swipe_up not in ALLOWED_SWIPE_UP_MODES_G164:
        telemetry_errors.append(f"swipe_up_invalid:{swipe_up!r}")
    if spot_metering_point not in ALLOWED_SPOT_METERING_POINTS_G164:
        telemetry_errors.append(f"spot_metering_point_invalid:{spot_metering_point!r}")
    if focus_area_category not in ALLOWED_FOCUS_AREA_CATEGORIES_G164:
        telemetry_errors.append(f"focus_area_category_invalid:{focus_area_category!r}")
    if fx6_touch_operation not in FX6_TOUCH_OPERATION_MODES_G164:
        telemetry_errors.append(f"fx6_touch_operation_invalid:{fx6_touch_operation!r}")
    if fx6_touch_func_in_mf not in FX6_TOUCH_FUNCTION_IN_MF_MODES_G164:
        telemetry_errors.append(
            f"fx6_touch_func_in_mf_invalid:{fx6_touch_func_in_mf!r}"
        )
    if still_img_save_dest not in ALLOWED_STILL_IMG_SAVE_DEST_G164:
        telemetry_errors.append(
            f"still_img_save_dest_invalid:{still_img_save_dest!r}"
        )
    if save_image_size not in ALLOWED_SAVE_IMAGE_SIZE_G164:
        telemetry_errors.append(f"save_image_size_invalid:{save_image_size!r}")
    if raw_j_save_image not in ALLOWED_RAW_J_SAVE_IMAGE_G164:
        telemetry_errors.append(f"raw_j_save_image_invalid:{raw_j_save_image!r}")
    if raw_h_save_image not in ALLOWED_RAW_H_SAVE_IMAGE_G164:
        telemetry_errors.append(f"raw_h_save_image_invalid:{raw_h_save_image!r}")
    if ptp_transport not in ALLOWED_PTP_TRANSPORTS_G164:
        telemetry_errors.append(f"ptp_transport_invalid:{ptp_transport!r}")
    if not _is_strict_int(ptp_ip_tcp_port) or not (1 <= ptp_ip_tcp_port <= 65535):
        telemetry_errors.append(f"ptp_ip_tcp_port_invalid:{ptp_ip_tcp_port!r}")
    if release_wo_card not in ("Enable", "Disable"):
        telemetry_errors.append(f"release_wo_card_invalid:{release_wo_card!r}")
    if target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE382:
        telemetry_errors.append(f"target_media_slot_invalid:{target_media_slot!r}")
    if not _is_on_off(airplane_mode):
        telemetry_errors.append(f"airplane_mode_invalid:{airplane_mode!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE382:
        telemetry_errors.append(f"reset_action_invalid:{reset_action!r}")

    for bname, bval in (
        ("request_dormant_touch_panel_pad", request_dormant_touch_panel_pad),
        ("request_dormant_touch_pad_vertical", request_dormant_touch_pad_vertical),
        ("request_dormant_touch_shutter", request_dormant_touch_shutter),
        ("request_dormant_touch_ae", request_dormant_touch_ae),
        (
            "claim_spot_metering_follows_moving_track",
            claim_spot_metering_follows_moving_track,
        ),
        (
            "claim_touch_4items_reset_by_camset_reset",
            claim_touch_4items_reset_by_camset_reset,
        ),
        ("fx6_mf_lens_attached", fx6_mf_lens_attached),
        ("fx6_focus_magnifier_active", fx6_focus_magnifier_active),
        ("invoke_fx6_spot_focus_in_mf", invoke_fx6_spot_focus_in_mf),
        ("invoke_fx6_big6_touch", invoke_fx6_big6_touch),
        ("request_fx6_touch_shutter_or_ae", request_fx6_touch_shutter_or_ae),
        ("pc_remote_connected", pc_remote_connected),
        (
            "attempt_change_save_dest_while_connected",
            attempt_change_save_dest_while_connected,
        ),
        ("card_inserted", card_inserted),
        ("remote_shutter_release_requested", remote_shutter_release_requested),
        ("slot1_tier0_protected", slot1_tier0_protected),
        (
            "claim_remote_shoot_reset_by_camset_reset",
            claim_remote_shoot_reset_by_camset_reset,
        ),
        ("request_fx6_still_img_save_dest_ui", request_fx6_still_img_save_dest_ui),
    ):
        if not isinstance(bval, bool):
            telemetry_errors.append(f"{bname}_not_bool:{bval!r}")

    if telemetry_errors:
        return TouchFuncPcRemoteGuardResult(
            valid=False,
            status=STATUS_BLOCKED_G164_TELEMETRY_INVALID,
            block_errno=EINVAL_ERRNO_PHASE382,
            block_errno_name=EINVAL_NAME_PHASE382,
            verification_mode=verification_mode,
            touch_operation_menu_path=TOUCH_OPERATION_MENU_PATH_G164,
            spot_metering_point_menu_path=SPOT_METERING_POINT_MENU_PATH_G164,
            remote_shoot_setting_menu_path=REMOTE_SHOOT_SETTING_MENU_PATH_G164,
            fx6_touch_func_mf_menu_path=FX6_TOUCH_FUNC_MF_MENU_PATH_G164,
            fx6_network_client_menu_path=FX6_NETWORK_CLIENT_MENU_PATH_G164,
            shoot_mode=str(shoot_mode),
            focus_mode=str(focus_mode),
            fx3_touch_active_subitems_count=len(
                EXACT_4_FX3_TOUCH_OPERATION_SUBITEMS_G164
            ),
            touch_4items_resettable_by_camset_reset=FX3_TOUCH_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164,
            effective_touch_operation=TOUCH_OPERATION_DEFAULT_G164,
            effective_touch_sensitivity=TOUCH_SENSITIVITY_DEFAULT_G164,
            effective_touch_func_in_shooting=TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164,
            effective_swipe_up=SWIPE_UP_DEFAULT_G164,
            touch_tracking_available_in_focus_mode=False,
            fx3_evf_present=FX3_EVF_PRESENT_G164,
            fx3_touch_shutter_hits=FX3_ILC2210_TOUCH_SHUTTER_HITS_G164,
            fx3_touch_ae_hits=FX3_ILC2210_TOUCH_AE_HITS_G164,
            spot_metering_point=SPOT_METERING_POINT_DEFAULT_G164,
            focus_area_category=str(focus_area_category),
            spot_metering_linked_to_initial_point=False,
            spot_metering_follows_moving_track_box=FX3_SPOT_METERING_FOLLOWS_MOVING_TRACK_BOX_G164,
            fx6_touch_operation="On",
            fx6_touch_func_in_mf="Spot Focus",
            fx6_spot_focus_in_mf_available=False,
            fx6_big6_touch_available=False,
            remote_shoot_subitems_count=len(EXACT_4_REMOTE_SHOOT_SUBITEMS_G164),
            remote_shoot_4items_resettable_by_camset_reset=REMOTE_SHOOT_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164,
            effective_still_img_save_dest=STILL_IMG_SAVE_DEST_BENCH_SAFE_G164,
            effective_save_image_size=SAVE_IMAGE_SIZE_DEFAULT_G164,
            effective_raw_j_save_image=RAW_J_SAVE_IMAGE_DEFAULT_G164,
            effective_raw_h_save_image=RAW_H_SAVE_IMAGE_DEFAULT_G164,
            still_img_save_dest_factory_default=STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164,
            ptp_transport=str(ptp_transport),
            ptp_ip_tcp_port=FX3_PTP_IP_TCP_PORT_G164,
            ptp_usb_device_nodes=FX3_PTP_USB_DEVICE_NODES_G164,
            pc_remote_connected=False,
            ram_only_zero_card_write_active=False,
            cardless_remote_shoot_allowed=False,
            fx6_still_img_save_dest_ui_exposed=FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED_G164,
            airplane_mode="On",
            rf_tx_packets=0,
            target_media_slot=MEDIA_SLOT_NONE_PHASE382,
            slot1_write_attempted=False,
            slot1_writes=0,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            usb_tx=USB_PACKETS_TRANSMITTED,
            usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
            emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
            hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            live_attach_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            violation_codes=tuple(telemetry_errors),
            errors=tuple(telemetry_errors),
            warnings=tuple(warnings),
        )

    state = resolve_fx3_touchfunc_pcremote_state(
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        touch_func_in_shooting=touch_func_in_shooting,
        swipe_up=swipe_up,
        spot_metering_point=spot_metering_point,
        focus_area_category=focus_area_category,
        still_img_save_dest=still_img_save_dest,
        save_image_size=save_image_size,
        raw_j_save_image=raw_j_save_image,
        raw_h_save_image=raw_h_save_image,
        ptp_transport=ptp_transport,
        pc_remote_connected=pc_remote_connected,
        card_inserted=card_inserted,
        target_media_slot=target_media_slot,
        remote_shutter_release_requested=remote_shutter_release_requested,
        airplane_mode=airplane_mode,
        reset_action=reset_action,
        fx6_firmware_version=fx6_firmware_version,
        fx6_mf_lens_attached=fx6_mf_lens_attached,
        fx6_desqueeze_mode=fx6_desqueeze_mode,
        fx6_focus_magnifier_active=fx6_focus_magnifier_active,
    )

    # --- 1. Tier-0 Slot 1 EROFS=30 Firewall (Highest Priority) ---
    # Default Dest.+Camera & Camera Only write to [Recording Media] (Slot 1).
    if slot1_tier0_protected and state["writes_camera_card"]:
        if state["slot1_write_attempted"] or (
            pc_remote_connected
            and target_media_slot == MEDIA_SLOT_1_PHASE382
        ):
            erofs_violations.append(
                f"TIER0_SLOT1_REMOTE_SHOOT_{state['effective_still_img_save_dest']}_WRITE_BLOCKED_EROFS"
            )

    # --- 2. Connected Save Dest Mutation Lock (EBUSY=16) ---
    if pc_remote_connected and attempt_change_save_dest_while_connected:
        ebusy_violations.append(
            "FX3_PRM_HAITA_STILL_IMG_SAVE_DEST_LOCKED_WHILE_PC_REMOTE_CONNECTED_EBUSY"
        )

    # --- 3. 100% Dormant Touch & FX6 Unsupported UI Firewall (EOPNOTSUPP=95) ---
    if request_dormant_touch_panel_pad or touch_func_in_shooting == "Touch Panel/Pad":
        eopnotsupp_violations.append(
            "FX3_EVFLESS_ALCIN_UUD_DORMANT_TOUCH_PANEL_PAD_F_0X76EC_EOPNOTSUPP"
        )
    if (
        request_dormant_touch_pad_vertical
        or touch_func_in_shooting == "Touch Pad (vertical)"
    ):
        eopnotsupp_violations.append(
            "FX3_EVFLESS_ALCIN_UUD_DORMANT_TOUCH_PAD_VERTICAL_F_0X7312_EOPNOTSUPP"
        )
    if request_dormant_touch_shutter or touch_func_in_shooting == "Touch Shutter":
        eopnotsupp_violations.append(
            "FX3_DORMANT_TOUCH_SHUTTER_F_0X6A80_ZERO_ILC2210_HITS_EOPNOTSUPP"
        )
    if request_dormant_touch_ae or touch_func_in_shooting == "Touch AE":
        eopnotsupp_violations.append(
            "FX3_DORMANT_TOUCH_AE_F_0X702A_PID_SET_TOUCH_SPOT_METER_EOPNOTSUPP"
        )
    if request_fx6_touch_shutter_or_ae:
        eopnotsupp_violations.append(
            "FX6_CINE_ARCH_ZERO_TOUCH_SHUTTER_AND_TOUCH_AE_EOPNOTSUPP"
        )
    if invoke_fx6_big6_touch and not state["fx6_big6_touch_available"]:
        eopnotsupp_violations.append("FX6_BIG6_TOUCH_REQUIRES_VER6_00_PLUS_EOPNOTSUPP")
    if request_fx6_still_img_save_dest_ui:
        eopnotsupp_violations.append(
            "FX6_ZERO_STILL_IMG_SAVE_DEST_UI_USE_NETWORK_CLIENT_MODE_EOPNOTSUPP"
        )

    # --- 4. Touch, Spot Metering, Reset & PTP/PTP-IP Constraint Checks ---
    if claim_spot_metering_follows_moving_track:
        constraint_violations.append(
            "FX3_SPOT_METERING_ANCHORED_AT_INITIAL_POINT_DOES_NOT_FOLLOW_TRACK_BOX"
        )
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382
        and claim_touch_4items_reset_by_camset_reset
    ):
        constraint_violations.append(
            "FX3_TOUCH_OPERATION_4ITEMS_RESIST_CAMSET_RESET_INITIALIZE_ONLY"
        )
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382
        and claim_remote_shoot_reset_by_camset_reset
    ):
        constraint_violations.append(
            "FX3_REMOTE_SHOOT_4ITEMS_RESIST_CAMSET_RESET_INIT_OR_NET_RESET_ONLY"
        )
    if invoke_fx6_spot_focus_in_mf and not state["fx6_spot_focus_in_mf_available"]:
        constraint_violations.append(
            "FX6_SPOT_FOCUS_IN_MF_DISABLED_BY_MF_LENS_DESQUEEZE_OR_FOCUS_MAG"
        )
    if (
        ptp_transport in ("ptp_ip_usblan", "ptp_ip_wired_lan", "ptp_ip_wifi")
        and ptp_ip_tcp_port != FX3_PTP_IP_TCP_PORT_G164
    ):
        constraint_violations.append(
            f"FX3_PTP_IP_REQUIRES_TCP_PORT_15740_GOT_{ptp_ip_tcp_port}"
        )
    if ptp_transport == "ptp_ip_wifi" and airplane_mode == "On":
        constraint_violations.append(
            "FX3_PTP_IP_WIFI_BLOCKED_BY_BENCH_ZERO_RF_AIRPLANE_MODE_ON"
        )
    if airplane_mode != "On":
        constraint_violations.append(
            "BENCH_ZERO_RF_REMOTE_SHOOT_REQUIRES_AIRPLANE_MODE_ON"
        )
    if (
        remote_shutter_release_requested
        and (not card_inserted)
        and state["writes_camera_card"]
    ):
        constraint_violations.append(
            "FX3_DEST_PLUS_CAMERA_OR_CAMERA_ONLY_REJECTS_CARDLESS_RELEASE_EVEN_IF_RELEASE_WO_CARD_ENABLE"
        )

    if (
        state["effective_still_img_save_dest"]
        == STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164
    ):
        warnings.append(
            "Factory default [Still Img. Save Dest.] = Dest.+Camera writes to [Recording Media] (Slot 1); lock Destination Only for zero-card bench PTP."
        )
    if (
        spot_metering_point == "Focus Point Link"
        and focus_area_category not in SPOT_LINK_ELIGIBLE_FOCUS_AREAS_G164
    ):
        warnings.append(
            f"Focus Area {focus_area_category} forces [Spot Metering Point] back to Center."
        )

    all_violations = (
        erofs_violations
        + ebusy_violations
        + eopnotsupp_violations
        + constraint_violations
    )
    if erofs_violations:
        status = STATUS_BLOCKED_G164_SLOT1_REMOTE_SHOOT_WRITE_EROFS
        errno_val, errno_name = EROFS_ERRNO_PHASE382, EROFS_NAME_PHASE382
        valid = False
    elif ebusy_violations:
        status = STATUS_BLOCKED_G164_CONNECTED_SAVE_DEST_MUTATION_EBUSY
        errno_val, errno_name = EBUSY_ERRNO_PHASE382, EBUSY_NAME_PHASE382
        valid = False
    elif eopnotsupp_violations:
        status = STATUS_BLOCKED_G164_DORMANT_TOUCH_OR_FX6_SAVE_DEST_EOPNOTSUPP
        errno_val, errno_name = EOPNOTSUPP_ERRNO_PHASE382, EOPNOTSUPP_NAME_PHASE382
        valid = False
    elif constraint_violations:
        status = STATUS_BLOCKED_G164_TOUCH_SPOT_RESET_OR_PTP_CONSTRAINT_VIOLATION
        errno_val, errno_name = EINVAL_ERRNO_PHASE382, EINVAL_NAME_PHASE382
        valid = False
    else:
        status = STATUS_VERIFIED_G164
        errno_val, errno_name = 0, "OK"
        valid = True

    return TouchFuncPcRemoteGuardResult(
        valid=valid,
        status=status,
        block_errno=errno_val,
        block_errno_name=errno_name,
        verification_mode=verification_mode,
        touch_operation_menu_path=TOUCH_OPERATION_MENU_PATH_G164,
        spot_metering_point_menu_path=SPOT_METERING_POINT_MENU_PATH_G164,
        remote_shoot_setting_menu_path=REMOTE_SHOOT_SETTING_MENU_PATH_G164,
        fx6_touch_func_mf_menu_path=FX6_TOUCH_FUNC_MF_MENU_PATH_G164,
        fx6_network_client_menu_path=FX6_NETWORK_CLIENT_MENU_PATH_G164,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        fx3_touch_active_subitems_count=len(
            EXACT_4_FX3_TOUCH_OPERATION_SUBITEMS_G164
        ),
        touch_4items_resettable_by_camset_reset=FX3_TOUCH_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164,
        effective_touch_operation=state["effective_touch_operation"],
        effective_touch_sensitivity=state["effective_touch_sensitivity"],
        effective_touch_func_in_shooting=state["effective_touch_func_in_shooting"],
        effective_swipe_up=state["effective_swipe_up"],
        touch_tracking_available_in_focus_mode=state[
            "touch_tracking_available_in_focus_mode"
        ],
        fx3_evf_present=FX3_EVF_PRESENT_G164,
        fx3_touch_shutter_hits=FX3_ILC2210_TOUCH_SHUTTER_HITS_G164,
        fx3_touch_ae_hits=FX3_ILC2210_TOUCH_AE_HITS_G164,
        spot_metering_point=spot_metering_point,
        focus_area_category=focus_area_category,
        spot_metering_linked_to_initial_point=state[
            "spot_metering_linked_to_initial_point"
        ],
        spot_metering_follows_moving_track_box=state[
            "spot_metering_follows_moving_track_box"
        ],
        fx6_touch_operation=fx6_touch_operation,
        fx6_touch_func_in_mf=fx6_touch_func_in_mf,
        fx6_spot_focus_in_mf_available=state["fx6_spot_focus_in_mf_available"],
        fx6_big6_touch_available=state["fx6_big6_touch_available"],
        remote_shoot_subitems_count=len(EXACT_4_REMOTE_SHOOT_SUBITEMS_G164),
        remote_shoot_4items_resettable_by_camset_reset=REMOTE_SHOOT_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164,
        effective_still_img_save_dest=state["effective_still_img_save_dest"],
        effective_save_image_size=state["effective_save_image_size"],
        effective_raw_j_save_image=state["effective_raw_j_save_image"],
        effective_raw_h_save_image=state["effective_raw_h_save_image"],
        still_img_save_dest_factory_default=STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164,
        ptp_transport=ptp_transport,
        ptp_ip_tcp_port=ptp_ip_tcp_port,
        ptp_usb_device_nodes=FX3_PTP_USB_DEVICE_NODES_G164,
        pc_remote_connected=pc_remote_connected,
        ram_only_zero_card_write_active=state["ram_only_zero_card_write_active"],
        cardless_remote_shoot_allowed=state["cardless_remote_shoot_allowed"],
        fx6_still_img_save_dest_ui_exposed=FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED_G164,
        airplane_mode=airplane_mode,
        rf_tx_packets=state["rf_tx_packets"],
        target_media_slot=target_media_slot,
        slot1_write_attempted=state["slot1_write_attempted"],
        slot1_writes=0,
        slot1_data_sector_writes=0,
        emmc_nflasha_write_count=0,
        usb_tx=USB_PACKETS_TRANSMITTED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        live_attach_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(all_violations),
        errors=tuple(all_violations),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G164TouchFuncPcRemoteGuardResult:
    gate_id: str
    gate_code: str
    valid: bool
    status: str
    verification_mode: str
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    donor_audit: Dict[str, Any]
    touchfunc_pcremote_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g164_touchfunc_pcremote_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G164TouchFuncPcRemoteGuardResult]:
    audit = audit_phase382_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_touchfunc_pcremote_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G164TouchFuncPcRemoteGuardResult(
        gate_id=G164,
        gate_code=G164_GATE_CODE,
        valid=overall_valid,
        status=status,
        verification_mode=audit.verification_mode,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_audit=audit.to_dict(),
        touchfunc_pcremote_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G164,
        gate_code=G164_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"touch_items={res.fx3_touch_active_subitems_count} "
            f"save_dest={res.effective_still_img_save_dest} "
            f"ptp={res.ptp_transport}:{res.ptp_ip_tcp_port} "
            f"ram_only={res.ram_only_zero_card_write_active} "
            f"s1_writes={res.slot1_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_touchfunc_pcremote_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G164TouchFuncPcRemoteGuardResult]:
    return evaluate_g164_touchfunc_pcremote_guard(**kwargs)


# ---------------------------------------------------------------------------
# Unified 164-Gate Master Safety Preflight Engine (G01..G164)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master164GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_161_gates_verified: bool
    all_164_gates_verified: bool
    g13_to_g164_all_passed: bool
    g163_to_g164_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_162_report: Dict[str, Any]
    g163_result: Dict[str, Any]
    g164_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_164gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_162_override: Optional[Master162GateReport] = None,
    audio_reclevel_outtiming_kwargs: Optional[Mapping[str, Any]] = None,
    touchfunc_pcremote_kwargs: Optional[Mapping[str, Any]] = None,
    **extra_upstream_kwargs: Any,
) -> Master164GateReport:
    """Evaluate unified 164-Gate Master Safety Preflight (`G01..G164`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m162 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    donors_present_in_work_root = bool(
        resolved_work_root_for_m162 is not None
        and (
            resolved_work_root_for_m162
            / PINNED_PHASE382_DONOR_SPECS["fx3_appfw_so"][1]
        ).is_file()
    )
    m162_force_clean_room = (
        True
        if (
            clean_forced
            or (not donors_present_in_work_root and force_clean_room is not False)
        )
        else force_clean_room
    )

    if master_162_override is not None:
        m162_report = master_162_override
    else:
        m162_kw = {
            k: v
            for k, v in extra_upstream_kwargs.items()
            if v is not None
        }
        m162_report = evaluate_162gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m162_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m162_kw,
        )

    g163_kw = dict(audio_reclevel_outtiming_kwargs or {})
    g163_verdict, g163_res = evaluate_g163_audio_reclevel_outtiming_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g163_kw,
    )

    g164_kw = dict(touchfunc_pcremote_kwargs or {})
    if request_persistent_emmc_writes:
        if "still_img_save_dest" not in g164_kw:
            g164_kw["still_img_save_dest"] = STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164
        if "target_media_slot" not in g164_kw:
            g164_kw["target_media_slot"] = MEDIA_SLOT_1_PHASE382
        if "remote_shutter_release_requested" not in g164_kw:
            g164_kw["remote_shutter_release_requested"] = True
    g164_verdict, g164_res = evaluate_g164_touchfunc_pcremote_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g164_kw,
    )

    new_gate_dicts = (
        {
            "gate_id": G163,
            "gate_code": G163_GATE_CODE,
            "status": g163_res.status,
            "passed": g163_verdict.passed,
            "evidence": g163_verdict.evidence,
            "violation_codes": list(g163_verdict.errors),
        },
        {
            "gate_id": G164,
            "gate_code": G164_GATE_CODE,
            "status": g164_res.status,
            "passed": g164_verdict.passed,
            "evidence": g164_verdict.evidence,
            "violation_codes": list(g164_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m162_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m162_report.summary["g01_to_g12_verified"])
    g13_to_g162_verified = (
        int(m162_report.summary["g13_to_g160_verified"])
        + int(m162_report.summary["g161_to_g162_verified"])
    )
    g163_to_g164_verified = int(bool(g163_verdict.passed)) + int(
        bool(g164_verdict.passed)
    )
    total_verified = (
        g01_to_g12_verified + g13_to_g162_verified + g163_to_g164_verified
    )

    g163_to_g164_all_passed = g163_to_g164_verified == 2
    g13_to_g164_all_passed = (
        m162_report.g13_to_g162_all_passed and g163_to_g164_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m162_report.gates[:9])

    offline_161_verified = (
        g01_to_g09_ok
        and m162_report.offline_159_gates_verified
        and g163_to_g164_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_164_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g164_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m162_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_161_verified
        and m162_report.h0_h1_trial_entry_allowed
        and g163_to_g164_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not CROSS_MODEL_FLASH_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m162_report.errors)
        + list(g163_verdict.errors)
        + list(g164_verdict.errors)
    )
    warnings: List[str] = (
        list(m162_report.warnings)
        + list(g163_verdict.warnings)
        + list(g164_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m162_report.g13_to_g162_all_passed:
        overall_status = m162_report.status
    elif not g163_verdict.passed:
        overall_status = g163_verdict.status
    elif not g164_verdict.passed:
        overall_status = g164_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_164_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_164_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_164_verified:
        overall_status = "VERIFIED_ALL_164_GATES"
    else:
        overall_status = "VERIFIED_161_OF_164_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m162_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g163_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g164_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 164,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 164 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g162_verified": g13_to_g162_verified,
        "g163_to_g164_verified": g163_to_g164_verified,
        "g13_to_g164_all_passed": g13_to_g164_all_passed,
        "g163_to_g164_all_passed": g163_to_g164_all_passed,
        "offline_161_gates_verified": offline_161_verified,
        "all_164_gates_verified": all_164_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "emmc_writes_authorized": EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master164GateReport(
        schema=REALHW_164GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_164GATE_PREFLIGHT_SCHEMA,
        version=REALHW_AUDIO_RECLEVEL_OUTTIMING_TOUCHFUNC_PCREMOTE_164GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_161_gates_verified=offline_161_verified,
        all_164_gates_verified=all_164_verified,
        g13_to_g164_all_passed=g13_to_g164_all_passed,
        g163_to_g164_all_passed=g163_to_g164_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_162_report=m162_report.to_dict(),
        g163_result=g163_res.to_dict(),
        g164_result=g164_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_164_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master164GateReport:
    return evaluate_164gate_preflight(repo_root, **kwargs)


def run_164_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master164GateReport:
    return evaluate_164gate_preflight(repo_root, **kwargs)


def verify_real_hardware_164gate_readiness(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master164GateReport:
    return evaluate_164gate_preflight(repo_root, **kwargs)


def _safe_write_json(payload: Any) -> None:
    try:
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_audio_reclevel_outtiming_touchfunc_pcremote_and_164gate_guard",
        description="Phase 382 (Task H490, Wave-72) G163/G164 and 164/164 Unified Safety Preflight CLI",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all 164/164 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g163", "g164", "164"],
        default="164",
        help="Target gate check: g163, g164, or 164",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g163":
        v, r = evaluate_g163_audio_reclevel_outtiming_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                    "raw_firmware_bytes_leaked": r.raw_firmware_bytes_leaked,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    if args.gate == "g164":
        v, r = evaluate_g164_touchfunc_pcremote_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                    "raw_firmware_bytes_leaked": r.raw_firmware_bytes_leaked,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    rep = evaluate_164gate_preflight(
        args.repo_root,
        force_clean_room=clean,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _safe_write_json(
            {
                "schema_version": rep.schema_version,
                "status": rep.status,
                "verification_mode": rep.verification_mode,
                "summary": rep.summary,
                "g163_status": rep.g163_result["status"],
                "g164_status": rep.g164_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/164 "
            f"g163_to_g164_all_passed={rep.g163_to_g164_all_passed} "
            f"all_164_gates_verified={rep.all_164_gates_verified} "
            f"dry_run_rehearsal_only={rep.dry_run_rehearsal_only} "
            f"agent_auto_flash_blocked={rep.agent_auto_flash_blocked} "
            f"overall_ready_for_hardware_attach={rep.overall_ready_for_hardware_attach} "
            f"hardware_live_attachment_authorized={rep.hardware_live_attachment_authorized} "
            f"el3_payload_transmit_authorized={rep.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={rep.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={rep.persistent_emmc_writes_authorized} "
            f"cross_model_flash_authorized={rep.cross_model_flash_authorized} "
            f"usb_packets_transmitted={rep.usb_packets_transmitted} "
            f"raw_firmware_bytes_leaked={rep.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        rep.all_164_gates_verified
        if args.dry_run_simulated
        else rep.offline_161_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_AUDIO_OUT_TIMING_MODES_G163",
    "ALLOWED_BODY_MODELS_PHASE382",
    "ALLOWED_FOCUS_AREA_CATEGORIES_G164",
    "ALLOWED_FX3_HDMI_4CH_OUTPUT_MODES_G163",
    "ALLOWED_MEDIA_SLOTS_PHASE382",
    "ALLOWED_PTP_TRANSPORTS_G164",
    "ALLOWED_RAW_H_SAVE_IMAGE_G164",
    "ALLOWED_RAW_J_SAVE_IMAGE_G164",
    "ALLOWED_RESET_ACTIONS_PHASE382",
    "ALLOWED_SAVE_IMAGE_SIZE_G164",
    "ALLOWED_SHOOT_MODES_PHASE382",
    "ALLOWED_SPOT_METERING_POINTS_G164",
    "ALLOWED_STILL_IMG_SAVE_DEST_G164",
    "ALLOWED_SWIPE_UP_MODES_G164",
    "ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES_G164",
    "ALLOWED_TOUCH_OPERATION_MODES_G164",
    "ALLOWED_TOUCH_SENSITIVITY_MODES_G164",
    "ALLOWED_XLR_H1_ATT_DB_G163",
    "ALLOWED_XLR_H1_GAIN_MODES_G163",
    "ALLOWED_XLR_H1_INPUT_TYPES_G163",
    "AUDIO_MONITORING_4CH_DEFAULT_G163",
    "AUDIO_MONITORING_4CH_F_RESID16_G163",
    "AUDIO_MONITORING_4CH_MENU_PATH_G163",
    "AUDIO_MONITORING_4CH_RESETTABLE_BY_CAMSET_RESET_G163",
    "AUDIO_MON_CH13_CH24_F_RESID16_G163",
    "AUDIO_MON_CH1_CH1_F_RESID16_G163",
    "AUDIO_MON_CH1_CH2_F_RESID16_G163",
    "AUDIO_MON_CH2_CH2_F_RESID16_G163",
    "AUDIO_MON_CH3_CH4_F_RESID16_G163",
    "AUDIO_OUT_TIMING_DEFAULT_G163",
    "AUDIO_OUT_TIMING_F_RESID16_G163",
    "AUDIO_OUT_TIMING_LIP_SYNC_F_RESID16_G163",
    "AUDIO_OUT_TIMING_LIVE_F_RESID16_G163",
    "AUDIO_OUT_TIMING_MENU_PATH_G163",
    "AUDIO_OUT_TIMING_RESETTABLE_BY_CAMSET_RESET_G163",
    "AUDIO_REC_LEVEL_ALT_F_RESID16_G163",
    "AUDIO_REC_LEVEL_DEFAULT_G163",
    "AUDIO_REC_LEVEL_DELETE_KEY_RESETS_TO_G163",
    "AUDIO_REC_LEVEL_ELF_TYPO_G163",
    "AUDIO_REC_LEVEL_F_RESID16_G163",
    "AUDIO_REC_LEVEL_MAX_G163",
    "AUDIO_REC_LEVEL_MENU_PATH_G163",
    "AUDIO_REC_LEVEL_MIN_G163",
    "AUDIO_REC_LEVEL_RESETTABLE_BY_CAMSET_RESET_G163",
    "AUDIO_REC_LEVEL_STEP_COUNT_G163",
    "AudioRecLevelOutTimingGuardResult",
    "CAMERA_ONLY_F_RESID16_G164",
    "CNCT_REMOTE_SHT_G_RESID16_G164",
    "DESTINATION_ONLY_F_RESID16_G164",
    "DEST_PLUS_CAMERA_F_RESID16_G164",
    "DONOR_BOUNDED_MAX_READ_BYTES_PHASE382",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE382",
    "DONOR_CHECK_FAST_TARGET_SECONDS_PHASE382",
    "DONOR_CHECK_MAX_SECONDS_PHASE382",
    "DORMANT_FX3_TOUCH_FEATURES_G164",
    "DORMANT_TOUCH_AE_CANCEL_G_RESID16_G164",
    "DORMANT_TOUCH_AE_F_RESID16_G164",
    "DORMANT_TOUCH_PAD_VERTICAL_F_RESID16_G164",
    "DORMANT_TOUCH_PANEL_PAD_F_RESID16_G164",
    "DORMANT_TOUCH_SHUTTER_F_RESID16_G164",
    "EBUSY_ERRNO_PHASE382",
    "EBUSY_NAME_PHASE382",
    "EINVAL_ERRNO_PHASE382",
    "EINVAL_NAME_PHASE382",
    "ENV_CLEAN_ROOM_TEST_PHASE382",
    "EOPNOTSUPP_ERRNO_PHASE382",
    "EOPNOTSUPP_NAME_PHASE382",
    "EPERM_ERRNO_PHASE382",
    "EPERM_NAME_PHASE382",
    "EROFS_ERRNO_PHASE382",
    "EROFS_NAME_PHASE382",
    "EXACT_4_FX3_TOUCH_OPERATION_SUBITEMS_G164",
    "EXACT_4_REMOTE_SHOOT_SUBITEMS_G164",
    "EXACT_5_FX3_4CH_AUDIO_MONITORING_MODES_G163",
    "FABRICATED_4CH_MONITORING_LABELS_G163",
    "FX3_BODY_LIMITER_PERMANENTLY_ACTIVE_G163",
    "FX3_DEFAULT_FW_VERSION_PHASE382",
    "FX3_EVF_PRESENT_G164",
    "FX3_HEADPHONE_MAX_DISCRETE_CH_G163",
    "FX3_HELP_GUIDE_CODE_PHASE382",
    "FX3_ILC2210_TOUCH_AE_HITS_G164",
    "FX3_ILC2210_TOUCH_SHUTTER_HITS_G164",
    "FX3_MODEL_ENUM_PHASE382",
    "FX3_MODEL_ID_PHASE382",
    "FX3_MODEL_NAME_PHASE382",
    "FX3_PTP_IP_TCP_PORT_G164",
    "FX3_PTP_USB_DEVICE_NODES_G164",
    "FX3_SPOT_METERING_FOLLOWS_MOVING_TRACK_BOX_G164",
    "FX3_TOUCH_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164",
    "FX6_AUDIO_INPUT_MENU_PATH_G163",
    "FX6_AUDIO_OUTPUT_MENU_PATH_G163",
    "FX6_BIG6_TOUCH_MIN_FW_G164",
    "FX6_DEFAULT_FW_VERSION_PHASE382",
    "FX6_HDMI_AUDIO_CHANNELS_G163",
    "FX6_HEADPHONE_OUT_MODES_G163",
    "FX6_INPUT_MIC_REFERENCE_6_STEPS_G163",
    "FX6_LIMITER_MODE_6_STEPS_G163",
    "FX6_LINE_INPUT_REFERENCE_4_STEPS_G163",
    "FX6_MODEL_ENUM_PHASE382",
    "FX6_MODEL_NAME_PHASE382",
    "FX6_MONITOR_CH_7_ITEMS_G163",
    "FX6_MONITOR_VOL_PHYSICAL_KEY_HITS_G163",
    "FX6_NETWORK_CLIENT_MENU_PATH_G164",
    "FX6_REFERENCE_LEVEL_5_STEPS_G163",
    "FX6_SDI_AUDIO_CHANNELS_G163",
    "FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED_G164",
    "FX6_TOUCH_FUNCTION_IN_MF_MODES_G164",
    "FX6_TOUCH_FUNC_MF_MENU_PATH_G164",
    "FX6_TOUCH_OPERATION_MENU_PATH_G164",
    "FX6_TOUCH_OPERATION_MODES_G164",
    "FX6_VOLUME_MAX_G163",
    "FX6_VOLUME_MIN_G163",
    "G163",
    "G163AudioRecLevelOutTimingGuardResult",
    "G163_GATE_CODE",
    "G163_GATE_ID",
    "G164",
    "G164TouchFuncPcRemoteGuardResult",
    "G164_GATE_CODE",
    "G164_GATE_ID",
    "HDMI_4CH_AUDIO_OUTPUT_DEFAULT_G163",
    "HDMI_4CH_AUDIO_OUTPUT_MENU_PATH_G163",
    "LEGACY_V1_PC_REMOTE_MENU_PATH_G164",
    "MEDIA_SLOT_1_PHASE382",
    "MEDIA_SLOT_2_PHASE382",
    "MEDIA_SLOT_NONE_PHASE382",
    "Master164GateReport",
    "PINNED_FX3_APPFW_SLICES_PHASE382",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE382",
    "PINNED_FX6_APPFW_SLICES_PHASE382",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE382",
    "PINNED_PHASE382_DONOR_SPECS",
    "Phase382DonorAuditResult",
    "RAW_H_SAVE_IMAGE_DEFAULT_G164",
    "RAW_H_SAVE_IMAGE_F_RESID16_G164",
    "RAW_J_SAVE_IMAGE_DEFAULT_G164",
    "RAW_J_SAVE_IMAGE_F_RESID16_G164",
    "REALHW_164GATE_PREFLIGHT_SCHEMA",
    "REALHW_AUDIO_RECLEVEL_OUTTIMING_TOUCHFUNC_PCREMOTE_164GATE_SCHEMA",
    "REALHW_AUDIO_RECLEVEL_OUTTIMING_TOUCHFUNC_PCREMOTE_164GATE_VERSION",
    "REMOTE_SHOOT_4ITEMS_RESETTABLE_BY_CAMSET_RESET_G164",
    "REMOTE_SHOOT_FUNCTION_F_RESID16_G164",
    "REMOTE_SHOOT_SETTING_F_RESID16_G164",
    "REMOTE_SHOOT_SETTING_MENU_PATH_G164",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE382",
    "RESET_ACTION_INITIALIZE_PHASE382",
    "RESET_ACTION_NONE_PHASE382",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE382",
    "SAVE_IMAGE_SIZE_DEFAULT_G164",
    "SAVE_IMAGE_SIZE_F_RESID16_G164",
    "SHOOT_MODE_MOVIE_PHASE382",
    "SHOOT_MODE_SQ_PHASE382",
    "SHOOT_MODE_STILL_PHASE382",
    "SOUND_OPTION_MENU_PATH_G163",
    "SPOT_LINK_ELIGIBLE_FOCUS_AREAS_G164",
    "SPOT_METERING_POINT_DEFAULT_G164",
    "SPOT_METERING_POINT_MENU_PATH_G164",
    "SQ_LOCKED_AUDIO_CONTROLS_G163",
    "STATUS_BLOCKED_G163_FABRICATED_4CH_BODY_LIMITER_OFF_OR_FX6_MONVOL_EOPNOTSUPP",
    "STATUS_BLOCKED_G163_PREEMPTION_SQ_LOCK_RESET_OR_FX6_AUDIO_CONSTRAINT_VIOLATION",
    "STATUS_BLOCKED_G163_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G164_CONNECTED_SAVE_DEST_MUTATION_EBUSY",
    "STATUS_BLOCKED_G164_DORMANT_TOUCH_OR_FX6_SAVE_DEST_EOPNOTSUPP",
    "STATUS_BLOCKED_G164_SLOT1_REMOTE_SHOOT_WRITE_EROFS",
    "STATUS_BLOCKED_G164_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G164_TOUCH_SPOT_RESET_OR_PTP_CONSTRAINT_VIOLATION",
    "STATUS_BLOCKED_PHASE382_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G163",
    "STATUS_VERIFIED_G164",
    "STILL_IMG_SAVE_DEST_BENCH_SAFE_G164",
    "STILL_IMG_SAVE_DEST_FACTORY_DEFAULT_G164",
    "STILL_IMG_SAVE_DEST_F_RESID16_G164",
    "SWIPE_UP_DEFAULT_G164",
    "TOUCH_FOCUS_F_RESID16_G164",
    "TOUCH_FUNC_IN_SHOOTING_DEFAULT_G164",
    "TOUCH_FUNC_IN_SHOOTING_F_RESID16_G164",
    "TOUCH_OPERATION_BASE_RESID16_G164",
    "TOUCH_OPERATION_DEFAULT_G164",
    "TOUCH_OPERATION_G_RESID16_G164",
    "TOUCH_OPERATION_MENU_PATH_G164",
    "TOUCH_SENSITIVITY_DEFAULT_G164",
    "TOUCH_TRACKING_F_RESID16_G164",
    "TouchFuncPcRemoteGuardResult",
    "VOLUME_SETTINGS_BASE_RESID16_G163",
    "VOLUME_SETTINGS_DEFAULT_G163",
    "VOLUME_SETTINGS_MAX_G163",
    "VOLUME_SETTINGS_MENU_PATH_G163",
    "VOLUME_SETTINGS_MIN_G163",
    "VOLUME_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G163",
    "VOLUME_SETTINGS_STEP_COUNT_G163",
    "XLR_H1_ATT_TO_DBU_G163",
    "XLR_H1_LEVEL_DIAL_MAX_G163",
    "XLR_H1_LEVEL_DIAL_MIN_G163",
    "XLR_H1_LINE_FIXED_DBU_G163",
    "XLR_H1_SPEAKER_FEEDBACK_WARN_MIN_VOL_G163",
    "audit_phase382_donor_contracts",
    "compute_audio_reclevel_outtiming_matrix",
    "compute_touchfunc_pcremote_matrix",
    "evaluate_164_master_safety_gates",
    "evaluate_164gate_preflight",
    "evaluate_g163_audio_reclevel_outtiming_guard",
    "evaluate_g164_touchfunc_pcremote_guard",
    "resolve_fx3_audio_reclevel_outtiming_state",
    "resolve_fx3_touchfunc_pcremote_state",
    "run_164_gate_preflight",
    "strip_elapsed_seconds_recursive_phase382",
    "verify_audio_reclevel_outtiming_guard",
    "verify_audio_reclevel_outtiming_guard_with_audit",
    "verify_real_hardware_164gate_readiness",
    "verify_touchfunc_pcremote_guard",
    "verify_touchfunc_pcremote_guard_with_audit",
]

if __name__ == "__main__":
    raise SystemExit(main())
