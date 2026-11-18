"""Grand Milestone Phase 349: 6-Pillar Real-Hardware `ILME-FX3 Ver. 7.02` Master Gate.

Forward-compatible capstone unifying all 6 real-hardware closure pillars across
Waves 21..72 (`ilc/2210`, FX3 `Ver. 7.02` vs `ILME-FX6 Ver. 6.01`):
  * P1 (`SAFETY_148PLUS_GATE_REALHW_MASTER_PREFLIGHT`): dynamic discovery of the
    highest `evaluate_<N>gate_preflight` (`N >= 148`, verifying `145/148` offline
    fail-closed on Tier-0 `G10..G12` and `148+/148+` simulated dry-run across
    `G01..G148+`, `cross_model_flash_authorized=False`).
  * P2 (`SIXTY_TWO_PLUS_PILLAR_RECOVERY_MASTER_VAULT`): dynamic discovery of the
    highest `evaluate_realhw_<M>pillar_recovery_master` (`M >= 62`), validating
    `cnflasha` `O_RDONLY`, zero OTP/RPMB/passive-UART/USB/e-ND/RF/Slot-1 writes,
    and strict FX3-vs-FX6 boundaries.
  * P3 (`FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS`): all `45+`
    `fx3_firmware_lab` real-binary auditors (`raw_firmware_bytes_leaked == 0`,
    `calibration_mutation_bytes == 0`, `wbi_mutation_bytes == 0`).
  * P4 (`SEVENTY_FIVE_PLUS_STAGE_VM_HIL_COEMULATION`): `>= 75/75` FX3-VM HIL
    co-emulation stages (Stages `1..66` via Phase 324 + Stages `67..75` Waves
    `57..72`, plus forward-compatible Stage `76+` discovery).
  * P5 (`ICOSUPLE_20_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH345`): ALL `20/20`
    physical bench readiness preflights (`Ph136`, `Ph143`, `Ph154`, plus `Ph186`,
    `Ph204`, `Ph216`, `Ph227`, `Ph248`, `Ph261`, `Ph275`, `Ph279`, `Ph284`,
    `Ph291`, `Ph302`, `Ph307`, `Ph316`, `Ph321`, `Ph329`, `Ph334`, `Ph338`,
    `Ph341`, `Ph342`, `Ph345`) with `16/16 H0 == H3` immutability and
    `overall_ready_for_hardware_attach=False`.
  * P6 (`REAL_FX3_702_QEMU_ROUNDS_28_TO_72_PLUS_AND_PNG_RECEIPTS`): `>= 45/45`
    live FX3 `7.02` (`4.9.337-scel+`) QEMU rounds (`R28..R72+`, `>= 135/135`
    sub-runs, `>= 90/90` `< 50 KiB` PNG receipts with observed baseline max
    `27,467 B`, `nop=0`, `crashes=0`, `emmc_writes=0`, `leaked=0 B`).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import copy
from dataclasses import asdict, dataclass, field
import hashlib
import inspect
import json
import multiprocessing as mp
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

sys.dont_write_bytecode = True

from .realhw_milestone295_master_gate import (
    DEFAULT_REPO_ROOT,
    _ensure_cross_package_paths,
)

_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

import fx3_recovery  # noqa: E402
import fx3_safety  # noqa: E402
from .hardware_readiness_packet import _is_forced_clean_room
from .patcher import (
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
)
from .realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier import (
    evaluate_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight,
    verify_phase341_report,
)
from .realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_verifier import (
    evaluate_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight,
    verify_phase345_report,
)
from .realhw_bench_cable_fan_and_slot1_verifier import (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from .realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier import (
    evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight,
    verify_phase334_report,
)
from .realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier import (
    evaluate_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight,
    verify_phase338_report,
)
from .realhw_milestone147_master_gate import _worker_phase136
from .realhw_milestone175_master_gate import (
    MILESTONE175_SCHEMA_VERSION,
    RoundQemuReceiptSpec,
)
from .realhw_milestone193_master_gate import (
    _66GATE_FAULT_FIELDS,
    MILESTONE193_SCHEMA_VERSION,
    _load_round28_to_37_summary,
    _read_file_o_rdonly,
    _worker_phase143_154_186,
)
from .realhw_milestone209_master_gate import (
    _72GATE_EXTRA_FAULT_FIELDS,
    MILESTONE209_SCHEMA_VERSION,
    _worker_phase204,
)
from .realhw_milestone221_master_gate import (
    _78GATE_EXTRA_FAULT_FIELDS,
    MILESTONE221_SCHEMA_VERSION,
    _worker_phase216,
)
from .realhw_milestone233_master_gate import (
    _90GATE_EXTRA_FAULT_FIELDS,
    MILESTONE233_SCHEMA_VERSION,
    _inspect_round_png_receipt_50kib,
    _worker_phase227,
    _worker_pillar_3_batch_233,
)
from .realhw_milestone254_master_gate import (
    _96GATE_EXTRA_FAULT_FIELDS,
    MILESTONE254_SCHEMA_VERSION,
    _check_vm_stage45_to_47_redlines,
    _worker_phase248,
)
from .realhw_milestone264_master_gate import (
    _102GATE_EXTRA_FAULT_FIELDS,
    MILESTONE264_SCHEMA_VERSION,
    _worker_phase261,
)
from .realhw_milestone295_master_gate import (
    _124GATE_EXTRA_FAULT_FIELDS,
    MILESTONE295_SCHEMA_VERSION,
    _worker_phase275_279,
    _worker_phase284_291,
    _worker_pillar_4_295,
)
from .realhw_milestone311_master_gate import (
    _134GATE_EXTRA_FAULT_FIELDS,
    MILESTONE311_SCHEMA_VERSION,
    _extract_nested_g_valid_and_g71_end_tx,
    _worker_phase302_307,
)
from .realhw_milestone324_master_gate import (
    _136GATE_EXTRA_FAULT_FIELDS,
    _138GATE_EXTRA_FAULT_FIELDS,
    _140GATE_EXTRA_FAULT_FIELDS,
    _142GATE_EXTRA_FAULT_FIELDS,
    _NEGATIVE_AUDIT_BOOL_KEYS as _M324_NEGATIVE_AUDIT_BOOL_KEYS,
    AGENT_AUTO_FLASH_BLOCKED,
    CALIBRATION_MUTATION_BYTES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CP_MUTATION_BYTES,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITE_COUNT,
    E_ND_ACTUATOR_TX_COUNT,
    FIRMWARE_LAB_45_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    ISP_WRITE_AUTHORIZED,
    MILESTONE324_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    ROUND28_TO_65_PNG_RECEIPTS,
    ROUND28_TO_65_SPECS,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_66_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone324FaultInjection,
    _build_master_140_chain_override,
    _evaluate_pillar_3 as _eval_m324_p3,
    _evaluate_pillar_4 as _eval_m324_p4,
    _evaluate_pillar_5 as _eval_m324_p5,
    _fault_to_142gate_worker_dict,
    _worker_phase316_321,
)
from .realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier import (
    evaluate_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight,
    verify_phase342_report,
)
from .realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier import (
    evaluate_realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight,
    verify_phase329_report,
)

# ---------------------------------------------------------------------------
# Constants & Anchors
# ---------------------------------------------------------------------------

REALHW_MILESTONE349_SCHEMA = "realhw_milestone349_master_gate_v1"
MILESTONE349_SCHEMA_VERSION = REALHW_MILESTONE349_SCHEMA
P349_SCHEMA = REALHW_MILESTONE349_SCHEMA
SCHEMA_VERSION = REALHW_MILESTONE349_SCHEMA
PHASE_349_VERSION = "349.0.0"
P349_VERSION = PHASE_349_VERSION

STATUS_MILESTONE_READY = "MILESTONE_349_PREBENCH_MASTER_VERIFIED"
P349_STATUS_MILESTONE_READY = STATUS_MILESTONE_READY
P349_STATUS_FAIL_CLOSED = STATUS_FAIL_CLOSED

P349_PHYSICAL_DEVICE_WRITES = PHYSICAL_DEVICE_WRITES
P349_RAW_FIRMWARE_BYTES_LEAKED = RAW_FIRMWARE_BYTES_LEAKED
P349_PNG_MAX_SIZE_BYTES = PNG_MAX_SIZE_BYTES
P349_BASELINE_PNG_MAX_OBSERVED_BYTES = 27_467

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_148PLUS_GATE_REALHW_MASTER_PREFLIGHT"),
    ("P2", "SIXTY_TWO_PLUS_PILLAR_RECOVERY_MASTER_VAULT"),
    ("P3", "FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS"),
    ("P4", "SEVENTY_FIVE_PLUS_STAGE_VM_HIL_COEMULATION"),
    ("P5", "ICOSUPLE_20_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH345"),
    ("P6", "REAL_FX3_702_QEMU_ROUNDS_28_TO_72_PLUS_AND_PNG_RECEIPTS"),
)
P349_PILLAR_SPECS = PILLAR_SPECS
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)
P349_PILLAR_IDS = PILLAR_IDS

RECOVERY_62_PILLAR_IDS: Tuple[str, ...] = tuple(fx3_recovery.MASTER_62_PILLAR_IDS)

VM_COEMULATION_75_STAGE_KEYS: Tuple[str, ...] = VM_COEMULATION_66_STAGE_KEYS + (
    "stage67_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil",
    "stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil",
    "stage69_realhw_big6_home_framing_interval_tc_ssh_fan_hil",
    "stage70_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil",
    "stage71_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil",
    "stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil",
    "stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil",
    "stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil",
    "stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil",
)

ROUND66_SUMMARY_RELPATH = (
    "reports/2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu/"
    "summary.json"
)
ROUND66_EXPECTED_SCHEMA = (
    "fx6-on-fx3-round66-realhw-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu-v1"
)
ROUND67_SUMMARY_RELPATH = (
    "reports/2026-11-17-round67-milestone40-lens-comp-af-illuminator-init5-folder-rating-qemu/"
    "summary.json"
)
ROUND67_EXPECTED_SCHEMA = (
    "fx6-on-fx3-round67-milestone40-lens-comp-af-illuminator-init5-folder-rating-qemu-v1"
)
ROUND68_SUMMARY_RELPATH = (
    "reports/2026-11-17-round68-switch-vh-af-limit14-exp-stdadj-tc-format-copy-reverse-qemu/"
    "summary.json"
)
ROUND68_EXPECTED_SCHEMA = (
    "fx6-on-fx3-round68-switch-vh-af-limit14-exp-stdadj-tc-format-copy-reverse-qemu-v1"
)
ROUND69_SUMMARY_RELPATH = (
    "reports/2026-11-17-round69-touch-4item-disp-zero-evf-flash-reset-interval-pb-edit-erofs-qemu/"
    "summary.json"
)
ROUND69_EXPECTED_SCHEMA = (
    "fx6-on-fx3-round69-touch-4item-disp-zero-evf-flash-reset-interval-pb-edit-erofs-qemu-v1"
)
ROUND70_SUMMARY_RELPATH = (
    "reports/2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu/"
    "summary.json"
)
ROUND70_EXPECTED_SCHEMA = (
    "fx6-on-fx3-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu-v1"
)
ROUND71_SUMMARY_RELPATH = (
    "reports/2026-11-17-round71-steadyshot-47focal-selftimer-zebra-streaming-erofs-qemu/"
    "summary.json"
)
ROUND71_EXPECTED_SCHEMA = (
    "fx6-on-fx3-round71-steadyshot-47focal-selftimer-zebra-streaming-erofs-qemu-v1"
)
ROUND72_SUMMARY_RELPATH = (
    "reports/2026-11-18-round72-milestone-bright-mon-shotmark-usblan-bulb-dormant-qemu/"
    "summary.json"
)
ROUND72_EXPECTED_SCHEMA = (
    "fx6-on-fx3-round72-milestone-bright-mon-shotmark-usblan-bulb-dormant-qemu-v1"
)

ROUND28_TO_72_SPECS: Tuple[RoundQemuReceiptSpec, ...] = ROUND28_TO_65_SPECS + (
    RoundQemuReceiptSpec(
        round_num=66,
        summary_relpath=ROUND66_SUMMARY_RELPATH,
        expected_schema=ROUND66_EXPECTED_SCHEMA,
        audit_key="r66_sensor_cleaning_ev_comp_focus_mode_index_rotate_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r66a_wave52_cleaning_evcomp_focusmode_rotate_verified",
            "r66a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r66b_wave52_guard_fail_closed",
            "r66c_clean_unmount_wave52_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r66a_cleaning_evcomp_focusmode_rotate_big6_schinese", 1),
            ("r66b_wave52_cleaning_evcomp_focusmode_rotate_guard", 1),
            ("r66c_clean_unmount_wave52_reset_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=67,
        summary_relpath=ROUND67_SUMMARY_RELPATH,
        expected_schema=ROUND67_EXPECTED_SCHEMA,
        audit_key="r67_milestone40_lens_comp_af_illuminator_init5_folder_rating_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r67a_wave53_lenscomp_afillum_init5_rating_verified",
            "r67a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r67b_wave53_guard_fail_closed",
            "r67c_clean_unmount_wave53_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r67a_lenscomp_afillum_init5_rating_big6_schinese", 1),
            ("r67b_wave53_lenscomp_afillum_init5_rating_guard", 1),
            ("r67c_clean_unmount_wave53_reset_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=68,
        summary_relpath=ROUND68_SUMMARY_RELPATH,
        expected_schema=ROUND68_EXPECTED_SCHEMA,
        audit_key="r68_switch_vh_af_limit14_exp_stdadj_tc_format_copy_reverse_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r68a_wave54_switch_vh_limit14_stdadj_tc_copy_verified",
            "r68a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r68b_wave54_guard_fail_closed",
            "r68c_clean_unmount_wave54_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r68a_switchvh_stdadj_tcformat_copy_big6_schinese", 1),
            ("r68b_wave54_switchvh_stdadj_tcformat_copy_guard", 1),
            ("r68c_clean_unmount_wave54_reset_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=69,
        summary_relpath=ROUND69_SUMMARY_RELPATH,
        expected_schema=ROUND69_EXPECTED_SCHEMA,
        audit_key="r69_touch_4item_disp_zero_evf_flash_reset_interval_pb_edit_erofs_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r69a_wave55_touch4_disp_flash_interval_edit_verified",
            "r69a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r69b_wave55_guard_fail_closed",
            "r69c_clean_unmount_wave55_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r69a_touch4_disp_flash_intervalpb_big6_schinese", 1),
            ("r69b_wave55_touch4_disp_zero_evf_flash_interval_erofs_guard", 1),
            ("r69c_clean_unmount_wave55_reset_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=70,
        summary_relpath=ROUND70_SUMMARY_RELPATH,
        expected_schema=ROUND70_EXPECTED_SCHEMA,
        audit_key="r70_dial_customize_mydial_fn12x2_liveview_lut_embed_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r70a_wave56_dial_mydial_fn_liveview_lut_verified",
            "r70a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r70b_wave56_guard_fail_closed",
            "r70c_clean_unmount_wave56_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r70a_dial_mydial_fn12x2_liveview_lut_big6_schinese", 1),
            ("r70b_wave56_dial_mydial_fn_liveview_lut_erofs_guard", 1),
            ("r70c_clean_unmount_wave56_reset_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=71,
        summary_relpath=ROUND71_SUMMARY_RELPATH,
        expected_schema=ROUND71_EXPECTED_SCHEMA,
        audit_key="r71_steadyshot_47focal_selftimer_zebra_streaming_erofs_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r71a_wave57_steadyshot_selftimer_zebra_streaming_verified",
            "r71a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r71b_wave57_guard_fail_closed",
            "r71c_clean_unmount_wave57_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r71a_steadyshot_47focal_selftimer_zebra_streaming_big6_schinese", 1),
            ("r71b_wave57_steadyshot_selftimer_zebra_streaming_erofs_guard", 1),
            ("r71c_clean_unmount_wave57_reset_h0_h3_big6_schinese", 1),
        ),
    ),
    RoundQemuReceiptSpec(
        round_num=72,
        summary_relpath=ROUND72_SUMMARY_RELPATH,
        expected_schema=ROUND72_EXPECTED_SCHEMA,
        audit_key="r72_bright_mon_shotmark_usblan_bulb_erofs_audit",
        audit_bool_keys=(
            "all_3_runs_crashes_zero",
            "all_3_runs_emmc_write_zero",
            "all_3_runs_cnflasha_write_zero",
            "r72a_wave58_bright_mon_shotmark_usblan_bulb_verified",
            "r72a_stageb_big6_sid_0a_ge_300k_pixels_verified",
            "r72b_wave58_guard_fail_closed",
            "r72c_clean_unmount_wave58_reset_and_16_h0_eq_h3_verified",
        ),
        run_specs=(
            ("r72a_bright_mon_shotmark_usblan_bulb_big6_schinese", 1),
            ("r72b_wave58_bright_mon_shotmark_usblan_bulb_erofs_guard", 1),
            ("r72c_clean_unmount_wave58_reset_h0_h3_big6_schinese", 1),
        ),
    ),
)

ROUND28_TO_72_PNG_RECEIPTS: Dict[int, Tuple[str, str]] = {
    **ROUND28_TO_65_PNG_RECEIPTS,
    66: (
        "reports/2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu/"
        "assets/r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-alpha.png",
        "reports/2026-11-17-round66-sensor-cleaning-ev-comp-cineei-focus-mode-index-rotate-qemu/"
        "assets/r66a-cleaning-evcomp-focusmode-rotate-4ch-big6-schinese-composited.png",
    ),
    67: (
        "reports/2026-11-17-round67-milestone40-lens-comp-af-illuminator-init5-folder-rating-qemu/"
        "assets/r67a-lenscomp-afillum-init5-rating-4ch-big6-schinese-alpha.png",
        "reports/2026-11-17-round67-milestone40-lens-comp-af-illuminator-init5-folder-rating-qemu/"
        "assets/r67a-lenscomp-afillum-init5-rating-4ch-big6-schinese-composited.png",
    ),
    68: (
        "reports/2026-11-17-round68-switch-vh-af-limit14-exp-stdadj-tc-format-copy-reverse-qemu/"
        "assets/r68a-switchvh-stdadj-tcformat-copy-4ch-big6-schinese-alpha.png",
        "reports/2026-11-17-round68-switch-vh-af-limit14-exp-stdadj-tc-format-copy-reverse-qemu/"
        "assets/r68a-switchvh-stdadj-tcformat-copy-4ch-big6-schinese-composited.png",
    ),
    69: (
        "reports/2026-11-17-round69-touch-4item-disp-zero-evf-flash-reset-interval-pb-edit-erofs-qemu/"
        "assets/r69a-touch-disp-flash-intervalpb-4ch-big6-schinese-alpha.png",
        "reports/2026-11-17-round69-touch-4item-disp-zero-evf-flash-reset-interval-pb-edit-erofs-qemu/"
        "assets/r69a-touch-disp-flash-intervalpb-4ch-big6-schinese-composited.png",
    ),
    70: (
        "reports/2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu/"
        "assets/r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-alpha.png",
        "reports/2026-11-17-round70-milestone-dial-customize-mydial-fn12x2-liveview-lut-embed-qemu/"
        "assets/r70a-dial-mydial-fn12x2-liveview-lut-4ch-big6-schinese-composited.png",
    ),
    71: (
        "reports/2026-11-17-round71-steadyshot-47focal-selftimer-zebra-streaming-erofs-qemu/"
        "assets/r71a-steadyshot-selftimer-zebra-streaming-big6-schinese-alpha.png",
        "reports/2026-11-17-round71-steadyshot-47focal-selftimer-zebra-streaming-erofs-qemu/"
        "assets/r71a-steadyshot-selftimer-zebra-streaming-big6-schinese-composited.png",
    ),
    72: (
        "reports/2026-11-18-round72-milestone-bright-mon-shotmark-usblan-bulb-dormant-qemu/"
        "assets/r72a-brightmon-shotmark-usblan-bulb-big6-schinese-alpha.png",
        "reports/2026-11-18-round72-milestone-bright-mon-shotmark-usblan-bulb-dormant-qemu/"
        "assets/r72a-brightmon-shotmark-usblan-bulb-big6-schinese-composited.png",
    ),
}

_SAFETY_GATE_FN_RE = re.compile(r"^evaluate_(\d+)gate_preflight$")
_RECOVERY_MASTER_FN_RE = re.compile(r"^evaluate_realhw_(\d+)pillar_recovery_master$")
_VM_STAGE_KEY_RE = re.compile(r"^stage(\d+)_")
_ROUND_DIR_RE = re.compile(r"-round(\d+)-")
_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_NEGATIVE_AUDIT_BOOL_KEYS: frozenset[str] = _M324_NEGATIVE_AUDIT_BOOL_KEYS | frozenset(
    {
        "fx3_has_builtin_evf",
        "fx3_has_eye_sensor",
        "fx3_has_finder_monitor_button",
        "fx3_has_var_shutter",
        "fx3_has_builtin_end_filter",
        "fx3_has_bt_timecode_link",
        "fx3_bird_eye_af_present",
        "fx3_shutter_when_pwr_off_present",
        "fx3_focus_bracket_present",
        "fx3_shutter_type_auto_present",
        "fx3_soft_skin_effect_present",
        "fx3_finder_monitor_group_present",
        "fx3_sync_terminal_present",
        "fx6_has_ibis",
        "fx6_has_builtin_evf",
        "fx6_has_still_flash_stack",
        "fx6_has_still_pipeline_present",
        "fx6_mechanical_shutter_present",
        "fx6_soft_skin_effect_present",
        "fx6_abb_menu_present",
        "fx6_genlock_bnc_present",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "cross_model_flash_authorized",
    }
)
_UNSET = object()


@dataclass(frozen=True)
class RealHwMilestone349FaultInjection:
    """Fault-injection surface for testing fail-closed behaviour across all 6 Milestone 349 pillars."""

    # P1 >= 148-gate safety preflight (G143..G148 + forward-compat 149+)
    p1_request_persistent_writes: bool = False
    p1_shoe_audio_subject_recog_kwargs: Optional[Dict[str, Any]] = None
    p1_silent_target_bodydata_kwargs: Optional[Dict[str, Any]] = None
    p1_hdmi_raw_desqueeze_kwargs: Optional[Dict[str, Any]] = None
    p1_reclamp_varshutter_apsc_kwargs: Optional[Dict[str, Any]] = None
    p1_breathing_camid_reel_kwargs: Optional[Dict[str, Any]] = None
    p1_copyright_powersave_ntscpal_kwargs: Optional[Dict[str, Any]] = None

    # P2 >= 62-pillar recovery master (Pillars 57..62 + forward-compat 63+)
    p2_fault_inject_pillar: Optional[str] = None
    p2_cnflasha_write_unblocked_fault: bool = False
    p2_otp_fuse_touches_override: int = 0
    p2_rpmb_counter_increments_override: int = 0
    p2_passive_tx_bytes_override: int = 0
    p2_physical_usb_packets_override: int = 0
    p2_physical_device_writes_override: int = 0
    p2_raw_firmware_bytes_leaked_override: int = 0

    # P3 >= 45 firmware-lab auditors (#45 + forward-compat 46+)
    p3_filesettings_tcregen_reclamp_guard_fault: bool = False
    p3_raw_firmware_bytes_leaked_override: int = 0

    # P4 >= 75 VM HIL stages (Stages 67..75 + forward-compat 76+)
    p4_stage67_steadyshot_47focal_selftimer_zebra_streaming_faults: int = 0
    p4_stage68_bright_mon_shotmark_usblan_bulb_dormant_faults: int = 0
    p4_stage69_big6_home_framing_interval_tc_ssh_fan_faults: int = 0
    p4_stage70_rec_media_autoswitch_proxy_cloud_mymenu_faults: int = 0
    p4_stage71_ftp_ftpes_usblan_customwb_af_focusmap_marker_faults: int = 0
    p4_stage72_shoe_audio_4ch_subject_recog_silent_target_version_faults: int = 0
    p4_stage73_hdmi_raw_desqueeze_reclamp_varshutter_apsc_faults: int = 0
    p4_stage74_breathing_camid_copyright_powersave_ntsc_pal_faults: int = 0
    p4_stage75_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_faults: int = 0
    p4_physical_device_writes_override: int = 0
    p4_raw_firmware_bytes_leaked_override: int = 0

    # P5 Icosuple 20/20 bench readiness preflights (Ph186..Ph345; 15th..20th are Ph329..Ph345)
    p5_inject_p329_shoe_audio_subject_hdmi_raw_desqueeze_varshutter_fault: bool = False
    p5_inject_p329_h0_h3_drift: bool = False
    p5_inject_p329_usb_packets_override: int = 0
    p5_inject_p329_passive_tx_bytes_override: int = 0
    p5_inject_p329_wireless_rf_packets_override: int = 0

    p5_inject_p334_breathing_camid_copyright_powersave_zoom_rawcomp_usblun_fault: bool = False
    p5_inject_p334_h0_h3_drift: bool = False
    p5_inject_p334_usb_packets_override: int = 0
    p5_inject_p334_passive_tx_bytes_override: int = 0
    p5_inject_p334_wireless_rf_packets_override: int = 0

    p5_inject_p338_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_hdmi_tc_fault: bool = False
    p5_inject_p338_h0_h3_drift: bool = False
    p5_inject_p338_usb_packets_override: int = 0
    p5_inject_p338_passive_tx_bytes_override: int = 0
    p5_inject_p338_wireless_rf_packets_override: int = 0

    p5_inject_p341_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_cec_fault: bool = False
    p5_inject_p341_h0_h3_drift: bool = False
    p5_inject_p341_usb_packets_override: int = 0
    p5_inject_p341_passive_tx_bytes_override: int = 0
    p5_inject_p341_wireless_rf_packets_override: int = 0

    p5_inject_p342_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_usbtether_fault: bool = False
    p5_inject_p342_h0_h3_drift: bool = False
    p5_inject_p342_usb_packets_override: int = 0
    p5_inject_p342_passive_tx_bytes_override: int = 0
    p5_inject_p342_wireless_rf_packets_override: int = 0

    p5_inject_p345_audio_reclevel_outtiming_4ch_mon_touch_dormant_remote_shoot_fault: bool = False
    p5_inject_p345_h0_h3_drift: bool = False
    p5_inject_p345_usb_packets_override: int = 0
    p5_inject_p345_passive_tx_bytes_override: int = 0
    p5_inject_p345_wireless_rf_packets_override: int = 0

    # P6 Rounds 28..72+ live QEMU kernel rehearsal & < 50 KiB PNG receipts
    p6_round_nop_override_num: Optional[int] = None
    p6_round_nop_count_override: Optional[int] = None
    p6_round_crash_override_num: Optional[int] = None
    p6_round_crashes_override: Optional[int] = None
    p6_round_emmc_override_num: Optional[int] = None
    p6_round_emmc_writes_override: Optional[int] = None
    p6_tamper_schema_round_num: Optional[int] = None
    p6_png_size_override_round_num: Optional[int] = None
    p6_png_size_override_bytes: Optional[int] = None
    p6_raw_firmware_bytes_leaked_override: int = 0

    # Optional upstream Milestone 324 fault injection pass-through
    m324_faults: Optional[RealHwMilestone324FaultInjection] = None


@dataclass(frozen=True)
class Milestone349PillarResult:
    pillar_id: str
    pillar_name: str
    passed: bool
    status: str
    summary: str
    evidence: Dict[str, Any]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwMilestone349MasterGateReport:
    schema: str
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    cnflasha_userspace_write_blocked: bool
    agent_auto_flash_blocked: bool
    cross_model_flash_authorized: bool
    overall_ready_for_hardware_attach: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    hardware_live_attachment_authorized: bool
    hardware_live_attachment_requirements: Tuple[str, ...]
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    e_nd_actuator_tx_count: int
    emmc_write_count: int
    rf_packets_transmitted: int
    slot1_data_sector_writes: int
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    calibration_mutation_bytes: int
    usb_or_camera_operations: int
    otp_fuse_writes: int
    otp_fuse_touches: int
    rpmb_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes: int
    passive_tx_bytes_emitted: int
    temp_dir_cleaned: bool
    pillar_count: int
    passed_pillar_count: int
    failed_pillar_ids: Tuple[str, ...]
    pillars: Tuple[Milestone349PillarResult, ...]
    gate148_total_gates: int
    gate148_offline_verified: int
    gate148_simulated_verified: int
    gate148_all_verified: bool
    recovery_status: str
    recovery_pillar_count: int
    recovery_pillars_passed: int
    auditors_total: int
    auditors_passed: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_stages_total: int
    vm_stages_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    vm_physical_device_writes: int
    vm_raw_firmware_bytes_leaked: int
    vm_emmc_corruptions: int
    vm_wf12_00342260_hits: int
    p136_u6_command_count: int
    p136_u4_u5_u6_closed: bool
    p143_sd_escape_absent_us: int
    p143_h0_equals_h3_count: int
    p143_h0_h3_surface_count: int
    p154_bench_go: bool
    p154_usb_packets_emitted: int
    p154_iokit_handles_opened: int
    p186_offline_go_no_go: str
    p186_sim_go_no_go: str
    p186_sim_gates_passed: int
    p186_card_insert_authorized: bool
    p186_h0_equals_h3_count: int
    p204_offline_go_no_go: str
    p204_sim_go_no_go: str
    p204_sim_groups_passed: int
    p204_hardware_live_attachment_authorized: bool
    p204_h0_equals_h3_count: int
    p204_e_nd_actuator_tx_count: int
    p216_offline_go_no_go: str
    p216_sim_go_no_go: str
    p216_sim_checklists_passed: int
    p216_hardware_live_attachment_authorized: bool
    p216_h0_equals_h3_count: int
    p227_offline_go_no_go: str
    p227_sim_go_no_go: str
    p227_sim_check_groups_passed: int
    p227_hardware_live_attachment_authorized: bool
    p227_h0_equals_h3_count: int
    p248_offline_go_no_go: str
    p248_sim_go_no_go: str
    p248_sim_check_groups_passed: int
    p248_hardware_live_attachment_authorized: bool
    p248_h0_equals_h3_count: int
    p261_offline_go_no_go: str
    p261_sim_go_no_go: str
    p261_sim_check_groups_passed: int
    p261_hardware_live_attachment_authorized: bool
    p261_h0_equals_h3_count: int
    p261_e_nd_uart_bytes_transmitted: int
    p275_offline_go_no_go: str
    p275_sim_go_no_go: str
    p275_sim_check_groups_passed: int
    p275_hardware_live_attachment_authorized: bool
    p275_h0_equals_h3_count: int
    p279_offline_go_no_go: str
    p279_sim_go_no_go: str
    p279_sim_check_groups_passed: int
    p279_hardware_live_attachment_authorized: bool
    p279_h0_equals_h3_count: int
    p284_offline_go_no_go: str
    p284_sim_go_no_go: str
    p284_sim_check_groups_passed: int
    p284_hardware_live_attachment_authorized: bool
    p284_h0_equals_h3_count: int
    p291_offline_go_no_go: str
    p291_sim_go_no_go: str
    p291_sim_check_groups_passed: int
    p291_hardware_live_attachment_authorized: bool
    p291_h0_equals_h3_count: int
    p302_offline_go_no_go: str
    p302_sim_go_no_go: str
    p302_sim_check_groups_passed: int
    p302_hardware_live_attachment_authorized: bool
    p302_h0_equals_h3_count: int
    p307_offline_go_no_go: str
    p307_sim_go_no_go: str
    p307_sim_check_groups_passed: int
    p307_hardware_live_attachment_authorized: bool
    p307_h0_equals_h3_count: int
    p307_wireless_rf_packets_emitted: int
    p307_slot1_data_sector_writes: int
    p316_offline_go_no_go: str
    p316_sim_go_no_go: str
    p316_sim_check_groups_passed: int
    p316_hardware_live_attachment_authorized: bool
    p316_h0_equals_h3_count: int
    p316_wireless_rf_packets_emitted: int
    p316_rf_packets_transmitted: int
    p316_e_nd_actuator_tx_count: int
    p316_slot1_data_sector_writes: int
    p321_offline_go_no_go: str
    p321_sim_go_no_go: str
    p321_sim_check_groups_passed: int
    p321_hardware_live_attachment_authorized: bool
    p321_h0_equals_h3_count: int
    p321_wireless_rf_packets_emitted: int
    p321_rf_packets_transmitted: int
    p321_e_nd_actuator_tx_count: int
    p321_slot1_data_sector_writes: int
    p329_offline_go_no_go: str
    p329_sim_go_no_go: str
    p329_sim_check_groups_passed: int
    p329_hardware_live_attachment_authorized: bool
    p329_h0_equals_h3_count: int
    p329_wireless_rf_packets_emitted: int
    p329_rf_packets_transmitted: int
    p329_e_nd_actuator_tx_count: int
    p329_slot1_data_sector_writes: int
    p334_offline_go_no_go: str
    p334_sim_go_no_go: str
    p334_sim_check_groups_passed: int
    p334_hardware_live_attachment_authorized: bool
    p334_h0_equals_h3_count: int
    p334_wireless_rf_packets_emitted: int
    p334_rf_packets_transmitted: int
    p334_e_nd_actuator_tx_count: int
    p334_slot1_data_sector_writes: int
    p338_offline_go_no_go: str
    p338_sim_go_no_go: str
    p338_sim_check_groups_passed: int
    p338_hardware_live_attachment_authorized: bool
    p338_h0_equals_h3_count: int
    p338_wireless_rf_packets_emitted: int
    p338_rf_packets_transmitted: int
    p338_e_nd_actuator_tx_count: int
    p338_slot1_data_sector_writes: int
    p341_offline_go_no_go: str
    p341_sim_go_no_go: str
    p341_sim_check_groups_passed: int
    p341_hardware_live_attachment_authorized: bool
    p341_h0_equals_h3_count: int
    p341_wireless_rf_packets_emitted: int
    p341_rf_packets_transmitted: int
    p341_e_nd_actuator_tx_count: int
    p341_slot1_data_sector_writes: int
    p342_offline_go_no_go: str
    p342_sim_go_no_go: str
    p342_sim_check_groups_passed: int
    p342_hardware_live_attachment_authorized: bool
    p342_h0_equals_h3_count: int
    p342_wireless_rf_packets_emitted: int
    p342_rf_packets_transmitted: int
    p342_e_nd_actuator_tx_count: int
    p342_slot1_data_sector_writes: int
    p345_offline_go_no_go: str
    p345_sim_go_no_go: str
    p345_sim_check_groups_passed: int
    p345_hardware_live_attachment_authorized: bool
    p345_h0_equals_h3_count: int
    p345_wireless_rf_packets_emitted: int
    p345_rf_packets_transmitted: int
    p345_e_nd_actuator_tx_count: int
    p345_slot1_data_sector_writes: int
    bench_preflight_verifier_count: int
    h0_equals_h3_count: int
    qemu_rounds_total: int
    qemu_rounds_verified: int
    qemu_runs_total: int
    qemu_runs_verified: int
    qemu_png_receipts_total: int
    qemu_png_receipts_verified: int
    qemu_png_max_bytes: int
    qemu_round_runs_by_round: Dict[str, int]
    qemu_real_kernel_nop_count: int
    qemu_real_kernel_crashes: int
    qemu_real_kernel_emmc_writes: int
    errors: Tuple[str, ...]
    milestone349_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class RealHwMilestone349VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone349_sha256: str
    observed_milestone349_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_milestone349_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `RealHwMilestone349MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone349_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Dynamic Discovery Helpers (Forward-Compat >= Lower Bounds)
# ---------------------------------------------------------------------------


def _discover_highest_safety_gate_evaluator(
    safety_mod: Any = fx3_safety,
) -> Tuple[int, Callable[..., Any]]:
    """Discover highest `evaluate_<N>gate_preflight` in `fx3_safety` (`N >= 148`)."""
    best_n = 0
    best_fn: Optional[Callable[..., Any]] = None
    for attr in dir(safety_mod):
        m = _SAFETY_GATE_FN_RE.match(attr)
        if not m:
            continue
        n_val = int(m.group(1))
        if n_val >= 148 and n_val > best_n:
            cand = getattr(safety_mod, attr, None)
            if callable(cand):
                best_n = n_val
                best_fn = cand
    if best_fn is not None:
        return best_n, best_fn
    return 148, fx3_safety.evaluate_148gate_preflight


def _discover_highest_recovery_master(
    recovery_mod: Any = fx3_recovery,
) -> Tuple[int, Callable[..., Any], Tuple[str, ...]]:
    """Discover highest `evaluate_realhw_<M>pillar_recovery_master` (`M >= 62`)."""
    best_m = 0
    best_fn: Optional[Callable[..., Any]] = None
    for attr in dir(recovery_mod):
        m = _RECOVERY_MASTER_FN_RE.match(attr)
        if not m:
            continue
        m_val = int(m.group(1))
        if m_val >= 62 and m_val > best_m:
            cand = getattr(recovery_mod, attr, None)
            if callable(cand):
                best_m = m_val
                best_fn = cand
    if best_fn is None:
        best_m = 62
        best_fn = fx3_recovery.evaluate_realhw_62pillar_recovery_master
    ids_raw = getattr(recovery_mod, f"MASTER_{best_m}_PILLAR_IDS", None)
    if ids_raw is None:
        ids_raw = getattr(recovery_mod, "MASTER_62_PILLAR_IDS", RECOVERY_62_PILLAR_IDS)
    return best_m, best_fn, tuple(str(x) for x in ids_raw)


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor)
# ---------------------------------------------------------------------------

_144GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_shoe_audio_subject_recog_kwargs", "shoe_audio_subject_recog_kwargs"),
    ("p1_silent_target_bodydata_kwargs", "silent_target_bodydata_kwargs"),
)
_146GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_hdmi_raw_desqueeze_kwargs", "hdmi_raw_desqueeze_kwargs"),
    ("p1_reclamp_varshutter_apsc_kwargs", "reclamp_varshutter_apsc_kwargs"),
)
_148GATE_EXTRA_FAULT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("p1_breathing_camid_reel_kwargs", "breathing_camid_reel_kwargs"),
    ("p1_copyright_powersave_ntscpal_kwargs", "copyright_powersave_ntscpal_kwargs"),
)

_ALL_M349_P1_EXTRA_FIELDS: Tuple[Tuple[str, str], ...] = (
    *_144GATE_EXTRA_FAULT_FIELDS,
    *_146GATE_EXTRA_FAULT_FIELDS,
    *_148GATE_EXTRA_FAULT_FIELDS,
)


def _effective_m324_faults(
    faults: RealHwMilestone349FaultInjection,
) -> RealHwMilestone324FaultInjection:
    base = faults.m324_faults or RealHwMilestone324FaultInjection()
    need_p1 = faults.p1_request_persistent_writes and not base.p1_request_persistent_writes
    need_p3 = (
        faults.p3_filesettings_tcregen_reclamp_guard_fault
        and not base.p3_filesettings_tcregen_reclamp_guard_fault
    )
    if need_p1 or need_p3:
        d = asdict(base)
        if base.m311_faults is not None:
            d["m311_faults"] = base.m311_faults
        if need_p1:
            d["p1_request_persistent_writes"] = True
        if need_p3:
            d["p3_filesettings_tcregen_reclamp_guard_fault"] = True
        return RealHwMilestone324FaultInjection(**d)
    return base


def _fault_to_148gate_worker_dict(faults: RealHwMilestone349FaultInjection) -> Dict[str, Any]:
    m324_f = _effective_m324_faults(faults)
    out = _fault_to_142gate_worker_dict(m324_f)
    out["p1_request_persistent_writes"] = bool(
        out.get("p1_request_persistent_writes", False) or faults.p1_request_persistent_writes
    )
    for src_attr, _ in _ALL_M349_P1_EXTRA_FIELDS:
        val = getattr(faults, src_attr)
        out[src_attr] = dict(val) if val is not None else None
    return out


def _build_master_146_chain_override(
    *,
    repo_root: Path,
    work_root_kw: Dict[str, Any],
    use_clean_room: bool,
    dry_run_sim: bool,
    req_persist: bool,
    fault_dict: Mapping[str, Any],
) -> Any:
    """Chain G1..G146 overrides cleanly when caller supplies pre-G147 fault kwargs."""
    up_to_140_kw: Dict[str, Any] = {}
    for src_attr, dst_kw in (
        *_66GATE_FAULT_FIELDS,
        *_72GATE_EXTRA_FAULT_FIELDS,
        *_78GATE_EXTRA_FAULT_FIELDS,
        *_90GATE_EXTRA_FAULT_FIELDS,
        *_96GATE_EXTRA_FAULT_FIELDS,
        *_102GATE_EXTRA_FAULT_FIELDS,
        *_124GATE_EXTRA_FAULT_FIELDS,
        *_134GATE_EXTRA_FAULT_FIELDS,
        *_136GATE_EXTRA_FAULT_FIELDS,
        *_138GATE_EXTRA_FAULT_FIELDS,
        *_140GATE_EXTRA_FAULT_FIELDS,
    ):
        val = fault_dict.get(src_attr)
        if val is not None:
            up_to_140_kw[dst_kw] = val

    if up_to_140_kw:
        m140_rep = _build_master_140_chain_override(
            repo_root=repo_root,
            use_clean_room=use_clean_room,
            dry_run_sim=dry_run_sim,
            req_persist=req_persist,
            fault_dict=fault_dict,
        )
        kw142: Dict[str, Any] = {"master_140_override": m140_rep}
    else:
        kw142 = {}
    for src_attr, dst_kw in _142GATE_EXTRA_FAULT_FIELDS:
        val = fault_dict.get(src_attr)
        if val is not None:
            kw142[dst_kw] = val
    m142_rep = fx3_safety.evaluate_142gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **work_root_kw,
        **kw142,
    )
    kw144: Dict[str, Any] = {"master_142_override": m142_rep}
    for src_attr, dst_kw in _144GATE_EXTRA_FAULT_FIELDS:
        val = fault_dict.get(src_attr)
        if val is not None:
            kw144[dst_kw] = val
    m144_rep = fx3_safety.evaluate_144gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **work_root_kw,
        **kw144,
    )
    kw146: Dict[str, Any] = {"master_144_override": m144_rep}
    for src_attr, dst_kw in _146GATE_EXTRA_FAULT_FIELDS:
        val = fault_dict.get(src_attr)
        if val is not None:
            kw146[dst_kw] = val
    return fx3_safety.evaluate_146gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **work_root_kw,
        **kw146,
    )


def _worker_148plus_gate_single(
    args: Tuple[str, bool, bool, Dict[str, Any], Optional[bool]]
) -> Dict[str, Any]:
    repo_root_str, use_clean_room, dry_run_sim, fault_dict, donorless_work_root_none = args
    repo_root = Path(repo_root_str)
    discovered_n, eval_fn = _discover_highest_safety_gate_evaluator()
    sig = inspect.signature(eval_fn)
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    req_persist = bool(fault_dict.get("p1_request_persistent_writes", False))

    work_root_kw: Dict[str, Any] = {"work_root": None} if donorless_work_root_none else {}
    kwargs: Dict[str, Any] = {"request_persistent_emmc_writes": req_persist}
    if donorless_work_root_none and (has_varkw or "work_root" in sig.parameters):
        kwargs["work_root"] = None

    unsupported_upstream = False
    for src_attr, dst_kw in (
        *_66GATE_FAULT_FIELDS,
        *_72GATE_EXTRA_FAULT_FIELDS,
        *_78GATE_EXTRA_FAULT_FIELDS,
        *_90GATE_EXTRA_FAULT_FIELDS,
        *_96GATE_EXTRA_FAULT_FIELDS,
        *_102GATE_EXTRA_FAULT_FIELDS,
        *_124GATE_EXTRA_FAULT_FIELDS,
        *_134GATE_EXTRA_FAULT_FIELDS,
        *_136GATE_EXTRA_FAULT_FIELDS,
        *_138GATE_EXTRA_FAULT_FIELDS,
        *_140GATE_EXTRA_FAULT_FIELDS,
        *_142GATE_EXTRA_FAULT_FIELDS,
        *_144GATE_EXTRA_FAULT_FIELDS,
        *_146GATE_EXTRA_FAULT_FIELDS,
        *_148GATE_EXTRA_FAULT_FIELDS,
    ):
        val = fault_dict.get(src_attr)
        if val is not None:
            if has_varkw or dst_kw in sig.parameters:
                kwargs[dst_kw] = val
            else:
                unsupported_upstream = True

    if unsupported_upstream:
        m146_rep = _build_master_146_chain_override(
            repo_root=repo_root,
            work_root_kw=work_root_kw,
            use_clean_room=use_clean_room,
            dry_run_sim=dry_run_sim,
            req_persist=req_persist,
            fault_dict=fault_dict,
        )
        if "master_146_override" in sig.parameters:
            kwargs["master_146_override"] = m146_rep
        elif "master_148_override" in sig.parameters:
            kw148: Dict[str, Any] = {"master_146_override": m146_rep}
            for src_attr, dst_kw in _148GATE_EXTRA_FAULT_FIELDS:
                val = fault_dict.get(src_attr)
                if val is not None:
                    kw148[dst_kw] = val
            kwargs["master_148_override"] = fx3_safety.evaluate_148gate_preflight(
                repo_root=repo_root,
                force_clean_room=use_clean_room,
                simulate_bench_dry_run=dry_run_sim,
                request_persistent_emmc_writes=req_persist,
                **work_root_kw,
                **kw148,
            )

    rep = eval_fn(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=dry_run_sim,
        **kwargs,
    )
    nested_g_valid, g71_end_tx = _extract_nested_g_valid_and_g71_end_tx(rep)
    s = rep.summary
    total_gates = int(s["total_gates"])
    offline_target = total_gates - 3
    offline_key = f"offline_{offline_target}_gates_verified"
    all_key = f"all_{total_gates}_gates_verified"
    chain_key = f"g13_to_g{total_gates}_all_passed"
    tail_key = f"g{total_gates - 1}_to_g{total_gates}_all_passed"

    return {
        "schema": rep.schema,
        "discovered_gate_count": discovered_n,
        "total_gates": total_gates,
        "verified_gates": int(s["verified_gates"]),
        "blocked_or_pending_gates": int(s["blocked_or_pending_gates"]),
        "offline_minus3_verified": bool(s.get(offline_key, False)),
        "all_n_gates_verified": bool(s.get(all_key, False)),
        "g13_to_gn_all_passed": bool(s.get(chain_key, False)),
        "gn_minus1_to_gn_all_passed": bool(s.get(tail_key, True)),
        "overall_ready_for_hardware_attach": bool(s["overall_ready_for_hardware_attach"]),
        "hardware_live_attachment_authorized": bool(
            s.get("hardware_live_attachment_authorized", False)
        ),
        "cross_model_flash_authorized": bool(s.get("cross_model_flash_authorized", False)),
        "agent_auto_flash_blocked": bool(s["agent_auto_flash_blocked"]),
        "human_hardware_attach_token": bool(s.get("human_hardware_attach_token", False)),
        "physical_flash_auto_exec_authorized": bool(
            s.get("physical_flash_auto_exec_authorized", False)
        ),
        "persistent_emmc_writes_authorized": bool(s["persistent_emmc_writes_authorized"]),
        "persistent_write_release": bool(s["persistent_write_release"]),
        "spi_nor_write_authorized": bool(s["spi_nor_write_authorized"]),
        "el3_payload_transmit_authorized": bool(s["el3_payload_transmit_authorized"]),
        "usb_packets_transmitted": int(s.get("usb_packets_transmitted", 0)),
        "physical_usb_packets_emitted": int(s.get("physical_usb_packets_emitted", 0)),
        "raw_firmware_bytes_leaked": int(s.get("raw_firmware_bytes_leaked", 0)),
        "g71_e_nd_actuator_tx_count": g71_end_tx,
        "nested_g_valid": nested_g_valid,
    }


def _normalize_62plus_pillar_fault_id(
    fault_id: Optional[str],
    pillar_ids: Tuple[str, ...] = RECOVERY_62_PILLAR_IDS,
) -> Optional[str]:
    if not fault_id:
        return None
    if fault_id in pillar_ids:
        return fault_id
    m = re.match(r"^pillar_(\d+)$", fault_id.strip().lower())
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(pillar_ids):
            return pillar_ids[idx]
    return fault_id


def _worker_recovery_62plus_pillar(args: Tuple[bool, Optional[str]]) -> Dict[str, Any]:
    use_clean_room, fault_pillar = args
    _, eval_fn, pillar_ids = _discover_highest_recovery_master()
    rep = eval_fn(
        force_clean_room=use_clean_room,
        fault_inject_pillar=_normalize_62plus_pillar_fault_id(fault_pillar, pillar_ids),
    )
    return rep.to_dict()


def _worker_phase329_334(
    args: Tuple[Optional[str], Optional[str], bool, bool, Dict[str, Any], Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, work_root_none, p329_faults, p334_faults = args
    fx6_dir = Path(fx6_str) if fx6_str is not None else None
    fx3_dir = Path(fx3_str) if fx3_str is not None else None
    wr_kw: Dict[str, Any] = {"work_root": None} if work_root_none else {}

    rep329_off = evaluate_realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
        **wr_kw,
    )
    kw329: Dict[str, Any] = dict(wr_kw)
    if p329_faults.get("shoe_audio_subject_hdmi_raw_desqueeze_varshutter"):
        kw329["dormant_subject_requested"] = True
        kw329["slot1_bodydata_stage_requested"] = True
        kw329["wireless_rf_packets_emitted"] = 1
        kw329["e_nd_actuator_tx_count"] = 1
    if p329_faults.get("h0_h3_drift"):
        kw329["simulated_h0_h3_drifted_surfaces"] = 1
    rep329_sim = evaluate_realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw329,
    )

    rep334_off = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
        **wr_kw,
    )
    kw334: Dict[str, Any] = dict(wr_kw)
    if p334_faults.get("breathing_camid_copyright_powersave_zoom_rawcomp_usblun"):
        kw334["dormant_lossless_comp_requested"] = True
        kw334["slot1_format_requested"] = True
        kw334["wireless_rf_packets_emitted"] = 1
        kw334["e_nd_actuator_tx_count"] = 1
    if p334_faults.get("h0_h3_drift"):
        kw334["simulated_h0_h3_drifted_surfaces"] = 1
    rep334_sim = evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw334,
    )
    return (
        rep329_off.to_dict(),
        rep329_sim.to_dict(),
        rep334_off.to_dict(),
        rep334_sim.to_dict(),
    )


def _worker_phase338_341(
    args: Tuple[Optional[str], Optional[str], bool, bool, Dict[str, Any], Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, work_root_none, p338_faults, p341_faults = args
    fx6_dir = Path(fx6_str) if fx6_str is not None else None
    fx3_dir = Path(fx3_str) if fx3_str is not None else None
    wr_kw: Dict[str, Any] = {"work_root": None} if work_root_none else {}

    rep338_off = evaluate_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
        **wr_kw,
    )
    kw338: Dict[str, Any] = dict(wr_kw)
    if p338_faults.get("drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_hdmi_tc"):
        kw338["dormant_focus_bracket_requested"] = True
        kw338["slot1_data_sector_writes"] = 1
        kw338["wireless_rf_packets_emitted"] = 1
        kw338["e_nd_actuator_tx_count"] = 1
    if p338_faults.get("h0_h3_drift"):
        kw338["simulated_h0_h3_drifted_surfaces"] = 1
    rep338_sim = evaluate_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw338,
    )

    rep341_off = evaluate_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
        **wr_kw,
    )
    kw341: Dict[str, Any] = dict(wr_kw)
    if p341_faults.get("area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_cec"):
        kw341["dormant_var_shutter_requested"] = True
        kw341["slot1_data_sector_writes"] = 1
        kw341["wireless_rf_packets_emitted"] = 1
        kw341["e_nd_actuator_tx_count"] = 1
    if p341_faults.get("h0_h3_drift"):
        kw341["simulated_h0_h3_drifted_surfaces"] = 1
    rep341_sim = evaluate_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw341,
    )
    return (
        rep338_off.to_dict(),
        rep338_sim.to_dict(),
        rep341_off.to_dict(),
        rep341_sim.to_dict(),
    )


def _worker_phase342_345(
    args: Tuple[Optional[str], Optional[str], bool, bool, Dict[str, Any], Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    fx6_str, fx3_str, use_clean_room, work_root_none, p342_faults, p345_faults = args
    fx6_dir = Path(fx6_str) if fx6_str is not None else None
    fx3_dir = Path(fx3_str) if fx3_str is not None else None
    wr_kw: Dict[str, Any] = {"work_root": None} if work_root_none else {}

    rep342_off = evaluate_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
        **wr_kw,
    )
    kw342: Dict[str, Any] = dict(wr_kw)
    if p342_faults.get("peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_usbtether"):
        kw342["dormant_anti_dust_function_requested"] = True
        kw342["slot1_host_usb_write_requested"] = True
        kw342["wireless_rf_packets_emitted"] = 1
        kw342["e_nd_actuator_tx_count"] = 1
    if p342_faults.get("h0_h3_drift"):
        kw342["simulated_h0_h3_drifted_surfaces"] = 1
    rep342_sim = evaluate_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw342,
    )

    rep345_off = evaluate_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=False,
        **wr_kw,
    )
    kw345: Dict[str, Any] = dict(wr_kw)
    if p345_faults.get("audio_reclevel_outtiming_4ch_mon_touch_dormant_remote_shoot"):
        kw345["dormant_touch_shutter_requested"] = True
        kw345["slot1_write_requested"] = True
        kw345["wireless_rf_packets_emitted"] = 1
        kw345["e_nd_actuator_tx_count"] = 1
    if p345_faults.get("h0_h3_drift"):
        kw345["simulated_h0_h3_drifted_surfaces"] = 1
    rep345_sim = evaluate_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
        fx6_lib_dir=fx6_dir,
        fx3_modules_dir=fx3_dir,
        force_clean_room=use_clean_room,
        simulate_bench_dry_run=True,
        **kw345,
    )
    return (
        rep342_off.to_dict(),
        rep342_sim.to_dict(),
        rep345_off.to_dict(),
        rep345_sim.to_dict(),
    )
# ---------------------------------------------------------------------------
# Pillar Evaluators (P1..P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
) -> Milestone349PillarResult:
    errors: List[str] = []
    off_total = int(raw_off["total_gates"])
    off_ver = int(raw_off["verified_gates"])
    sim_total = int(raw_sim["total_gates"])
    sim_ver = int(raw_sim["verified_gates"])

    if (
        off_total < 148
        or off_ver < off_total - 3
        or off_ver != off_total - 3
        or int(raw_off["blocked_or_pending_gates"]) != 3
        or raw_off["overall_ready_for_hardware_attach"] is not False
        or raw_off["hardware_live_attachment_authorized"] is not False
        or raw_off.get("cross_model_flash_authorized") is not False
        or not bool(raw_off.get("offline_minus3_verified", False))
    ):
        errors.append(
            f"p1_offline: expected {off_total - 3}/{off_total} (>=145/148, 3 Tier-0 gates fail-closed) "
            f"and hardware_attach=False, got {off_ver}/{off_total}"
        )

    if (
        sim_total < 148
        or sim_ver != sim_total
        or not bool(raw_sim.get("all_n_gates_verified", False))
        or not bool(raw_sim.get("g13_to_gn_all_passed", False))
        or not bool(raw_sim.get("gn_minus1_to_gn_all_passed", True))
        or raw_sim["overall_ready_for_hardware_attach"] is not False
        or raw_sim["hardware_live_attachment_authorized"] is not False
        or raw_sim.get("cross_model_flash_authorized") is not False
        or raw_sim["agent_auto_flash_blocked"] is not True
    ):
        errors.append(
            f"p1_simulated: expected {sim_total}/{sim_total} (>=148/148) with all_n_gates_verified=True "
            f"and hardware_attach=False, got {sim_ver}/{sim_total}"
        )

    for mode_tag, rmap in (("offline", raw_off), ("simulated", raw_sim)):
        if (
            rmap["persistent_emmc_writes_authorized"] is not False
            or rmap["persistent_write_release"] is not False
            or rmap["spi_nor_write_authorized"] is not False
            or rmap["el3_payload_transmit_authorized"] is not False
            or rmap.get("cross_model_flash_authorized", True) is not False
            or rmap.get("human_hardware_attach_token", False) is not False
            or rmap.get("physical_flash_auto_exec_authorized", False) is not False
            or int(rmap["usb_packets_transmitted"]) != 0
            or int(rmap["physical_usb_packets_emitted"]) != 0
            or int(rmap["raw_firmware_bytes_leaked"]) != 0
            or int(rmap["g71_e_nd_actuator_tx_count"]) != 0
        ):
            errors.append(
                f"p1_{mode_tag}: hard-locked zero-write / zero-cross-model-flash / zero-USB-TX / "
                f"zero-leak / zero-e-ND redline breached"
            )

    nested_sim: Mapping[str, bool] = raw_sim["nested_g_valid"]
    failed_gates = [g.upper() for g in sorted(nested_sim) if not nested_sim[g]]
    if failed_gates:
        errors.append(f"p1: real-hardware gates failed: {', '.join(failed_gates)}")
    if len(nested_sim) < (148 - 62):
        errors.append(f"p1: expected >=86 nested G63..G148+ gates, got {len(nested_sim)}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_sim["schema"],
        "discovered_gate_count": int(raw_sim.get("discovered_gate_count", sim_total)),
        "offline_total_gates": off_total,
        "offline_verified_gates": off_ver,
        "simulated_total_gates": sim_total,
        "simulated_verified_gates": sim_ver,
        "all_148plus_gates_verified": bool(raw_sim.get("all_n_gates_verified", False)),
        "offline_ready_for_hardware_attach": raw_off["overall_ready_for_hardware_attach"],
        "simulated_ready_for_hardware_attach": raw_sim["overall_ready_for_hardware_attach"],
        "hardware_live_attachment_authorized": raw_sim["hardware_live_attachment_authorized"],
        "cross_model_flash_authorized": bool(raw_sim.get("cross_model_flash_authorized", True)),
        "agent_auto_flash_blocked": raw_sim["agent_auto_flash_blocked"],
        "persistent_emmc_writes_authorized": raw_sim["persistent_emmc_writes_authorized"],
        "spi_nor_write_authorized": raw_sim["spi_nor_write_authorized"],
        "el3_payload_transmit_authorized": raw_sim["el3_payload_transmit_authorized"],
        "usb_packets_transmitted": int(raw_sim["usb_packets_transmitted"]),
        "raw_firmware_bytes_leaked": int(raw_sim["raw_firmware_bytes_leaked"]),
        "g71_e_nd_actuator_tx_count": raw_sim["g71_e_nd_actuator_tx_count"],
        "g63_to_gn_valid": dict(nested_sim),
    }
    return Milestone349PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_148PLUS_GATE_REALHW_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"148+-Gate Safety: offline={off_ver}/{off_total} (3 Tier-0 gates fail-closed), "
            f"simulated={sim_ver}/{sim_total} (G63..G{sim_total} Waves 21-65+, "
            f"cross_model_flash={raw_sim.get('cross_model_flash_authorized')}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    rec_62plus: Mapping[str, Any],
    faults: RealHwMilestone349FaultInjection,
) -> Tuple[Milestone349PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    p_count = int(rec_62plus.get("pillar_count", 0))
    p_passed = int(rec_62plus.get("pillars_passed", 0))
    rec_status = str(rec_62plus.get("status", ""))

    cnflasha_blocked = bool(rec_62plus.get("cnflasha_userspace_write_blocked", False)) and not bool(
        faults.p2_cnflasha_write_unblocked_fault
    )
    otp = (
        max(
            int(rec_62plus.get("otp_fuse_writes", 0) or 0),
            int(rec_62plus.get("otp_fuse_touches", -1)),
        )
        + int(faults.p2_otp_fuse_touches_override)
    )
    rpmb = int(rec_62plus.get("rpmb_counter_increments", -1)) + int(
        faults.p2_rpmb_counter_increments_override
    )
    ptx = int(rec_62plus.get("passive_tx_bytes_emitted", -1)) + int(
        faults.p2_passive_tx_bytes_override
    )
    usb_pkts = int(rec_62plus.get("physical_usb_packets_emitted", -1)) + int(
        faults.p2_physical_usb_packets_override
    )
    dev_writes = int(rec_62plus.get("physical_device_writes", -1)) + int(
        faults.p2_physical_device_writes_override
    )
    leaked = int(rec_62plus.get("raw_firmware_bytes_leaked", -1)) + int(
        faults.p2_raw_firmware_bytes_leaked_override
    )

    p62_required_subkeys = (
        "pillar62_a_rec_media_autoswitch_proxy_vault",
        "pillar62_b_cloud_poweroff_ble_mymenu_vault",
    )
    sub_ok = True
    for sub_k in p62_required_subkeys:
        sub_obj = rec_62plus.get(sub_k, {})
        if p_count > 62 and not sub_obj:
            continue
        if not (isinstance(sub_obj, Mapping) and bool(sub_obj.get("passed"))):
            sub_ok = False

    expected_status = f"VERIFIED_{p_count}OF{p_count}_PILLAR_RECOVERY_MASTER"
    status_ok = rec_status == expected_status and p_count >= 62 and p_passed == p_count
    pillars_seq = rec_62plus.get("pillars", ())
    pillars_items_ok = (
        isinstance(pillars_seq, Sequence)
        and len(pillars_seq) >= 62
        and all(isinstance(item, Mapping) and bool(item.get("passed")) for item in pillars_seq)
    )

    if (
        not bool(rec_62plus.get("all_passed"))
        or not status_ok
        or not pillars_items_ok
        or p_count < 62
        or p_passed < 62
        or p_passed != p_count
        or not sub_ok
    ):
        errors.append(
            f"p2_62plus_pillar: expected >=62/62 {expected_status}, "
            f"got {p_passed}/{p_count} (status={rec_status!r}, p62_sub={sub_ok})"
        )

    zero_violation_keys = (
        # Pillars 45..56 zero-violation counters
        "double_log_or_lockout_bypass_events",
        "pplut_1080p_clamp_bypass_events",
        "pp_internal_reset_trap_violations",
        "fx6_baselook_confusion_events",
        "wb_cine_ei_awb_or_custom_setup_trap_events",
        "wb_custom_camset_exclusion_drift_events",
        "metering_desqueeze_or_cine_ei_base_iso_drift_events",
        "nouvc_spoof_events",
        "usb_host_data_enumeration_events",
        "hdmi_lcd_blanking_violations",
        "hdmi_log_1080_bypass_events",
        "slot1_protect_only_vault_violations",
        "slot1_vault_format_or_delete_events",
        "slot1_vault_mutation_bytes",
        "network_reset_zero_rf_violations",
        "legacy_power_save_monitor_spoof_events",
        "unsafe_power_save_sleep_interference_events",
        "bk_lang_parity_drift_events",
        "stage_b_4lang_uxc_ltt_drift_events",
        "xlrh1_acoustic_feedback_violations",
        "audio_mon_4ch_hdmi_confusion_events",
        "destructive_delete_confirm_drift_events",
        "slot1_vault_delete_events",
        "e_nd_actuator_tx_count",
        "af_area_reg_lock_or_reset_drift_events",
        "camset_cross_model_path_drift_events",
        "colorspace_adobergb_prefix_violations",
        "dci4k_long_gop_or_8k_violations",
        "dormant_lossless_raw_exposure_events",
        "electronic_silent_5lock_bypass_events",
        "ev_comp_range_or_cine_ei_lockout_violations",
        "exposure_step_or_dormant_reset_ev_drift_events",
        "flash_still_mech_gate_violations",
        "focus_mode_movie_clamp_or_dormant_drift_events",
        "fx6_handle_or_pos_display_conflation_events",
        "fx6_ibis_shake_conflation_events",
        "fx6_mechanical_shutter_conflation_events",
        "fx6_still_or_raw_conflation_events",
        "fx6_still_pipeline_conflation_events",
        "hdmi_raw_or_still_aspect_drift_events",
        "hlg_still_prereq_or_lockout_drift_events",
        "image_index_dormant_or_view_mode_drift_events",
        "iso_minss_or_cine_ei_lock_drift_events",
        "mishoe_pmic_5v_overcurrent_events",
        "movie_tracking_area_or_limit_violations",
        "nr_or_drive_burst_wall_violations",
        "photo_capture_dci4k_lockout_bypass_events",
        "priority_set_or_illuminator_gate_violations",
        "reboot_2400p_stage_b_wipe_violations",
        "reg_custom_hold_or_hlg_lock_drift_events",
        "sensor_cleaning_low_battery_bypass_events",
        "sensor_cleaning_no_power_off_violations",
        "shutter_type_auto_spoof_events",
        "slot1_camset_write_bytes",
        "slot1_data_sector_writes",
        "slot1_flash_videolight_imagedb_bytes",
        "slot1_focus_zoom_camset_mutation_bytes",
        "slot1_imagedb_or_burst_mutation_bytes",
        "slot1_photo_capture_write_bytes",
        "slot1_rotate_exif_mutation_bytes",
        "slot1_still_capture_or_sort_write_bytes",
        "xlrh1_zoom_or_hold_spoof_events",
        "dormant_shading_auto_low_exposure_events",
        "lens_comp_lock_or_arw_conflation_events",
        "af_illuminator_gate_or_fx6_spoof_events",
        "aperture_drive_pre_af_shutter_reset_drift_events",
        "circ_focus_diagonal_or_color_drift_events",
        "focus_area_color_or_fx6_spoof_events",
        "folder_name_or_leading_underscore_violations",
        "slot1_folder_dir_mutation_bytes",
        "slot1_rating_avf_info_mutation_bytes",
        "switch_vh_af_lockout_or_coords_drift_events",
        "focus_limit_lt2_or_dormant_symbol_events",
        "exp_std_adj_mode_conflation_or_reset_drift_events",
        "bracket_settings_reset_or_fx6_spoof_events",
        "tcub_reset_wipe_or_format_lock_violations",
        "reverse_copy_slot2_to_slot1_bypass_events",
        "slot1_copy_avf_info_mutation_bytes",
        # Pillars 57..62 zero-violation counters
        "access_authen_ssh_tls_or_fan_max_drift_events",
        "big6_home_or_lower_left_nd_drift_events",
        "bright_mon_or_monitor_brightness_drift_events",
        "bulb_mech_or_dormant_bulb_timer_hdr_drift_events",
        "card_speed_vpg200_vpg400_gate_drift_events",
        "cloud_init_persist_or_power_off_ble_rf_events",
        "dial_customize_dormant_trap_or_reset_drift_events",
        "fn_menu_12x2_or_fx6_dial_spoof_events",
        "framing_manual_or_dormant_auto_framing_drift_events",
        "fx6_ibis_or_selftimer_spoof_events",
        "fx6_vf_backlight_or_still_spoof_events",
        "grid_line_or_hdmi_clean_feed_leak_events",
        "interval_shoot_9999_or_fx6_mxf_spoof_events",
        "live_view_display_reset_split_or_mode_drift_events",
        "lut_path_embed_sidecar_or_slot1_vault_bypass_events",
        "mymenu_42slot_or_fx6_lock_spoof_events",
        "proxy_sq_dci4k_or_120p_lockout_drift_events",
        "rear_dial_lr_or_mydial_override_drift_events",
        "rec_media_prioritize_or_autoswitch_drift_events",
        "rf_nvs_mutation_bytes",
        "selftimer_dormant_or_led8_audio_drift_events",
        "shotmark_clipflag_or_dormant_divide_drift_events",
        "slot1_dcim_avf_mutation_bytes",
        "slot1_dcim_divider_mutation_bytes",
        "slot1_dcim_m4root_avf_mutation_bytes",
        "slot1_lut_mutation_bytes",
        "slot1_m4root_avf_mutation_bytes",
        "slot1_streaming_or_ftp_mutation_bytes",
        "steadyshot_47focal_or_lockout_drift_events",
        "streaming_24p_rec_or_network_reset_drift_events",
        "tc_link_wpa3_or_usblan_mutex_drift_events",
        "tc_make_regen_or_hdmi_rec_ctrl_drift_events",
        "zebra_custom_ire_or_peaking_clean_hdmi_drift_events",
        "zero_rf_or_slot1_vault_bypass_events",
    )
    violations_nonzero = any(int(rec_62plus.get(vk, 0)) != 0 for vk in zero_violation_keys)

    if (
        cnflasha_blocked is not True
        or otp != 0
        or rpmb != 0
        or ptx != 0
        or usb_pkts != 0
        or dev_writes != 0
        or leaked != 0
        or violations_nonzero
        or rec_62plus.get("slot1_format_hard_locked", True) is not True
        or rec_62plus.get("slot1_vault_erofs_eopnotsupp_enforced", True) is not True
        or rec_62plus.get("slot1_vault_erofs_ebusy_enforced", True) is not True
        or rec_62plus.get("fx3_has_var_shutter", False) is not False
        or rec_62plus.get("fx3_has_builtin_evf", False) is not False
        or rec_62plus.get("fx3_has_builtin_end_filter", False) is not False
        or rec_62plus.get("fx3_has_bt_timecode_link", False) is not False
        or rec_62plus.get("fx3_has_dormant_auto_framing", False) is not False
        or rec_62plus.get("fx3_has_dormant_auto_hdr", False) is not False
        or rec_62plus.get("fx3_has_dormant_bulb_timer", False) is not False
        or rec_62plus.get("fx3_has_dormant_divide_extract", False) is not False
        or rec_62plus.get("fx3_has_fan_control_max", False) is not False
        or rec_62plus.get("fx3_has_movie_self_timer", False) is not False
        or rec_62plus.get("fx3_has_movie_sort_recording", False) is not False
        or rec_62plus.get("fx3_has_physical_end_hw", False) is not False
        or rec_62plus.get("fx6_has_ibis", False) is not False
        or rec_62plus.get("fx6_has_fan_control_max", False) is not False
        or rec_62plus.get("fx6_has_still_self_timer", False) is not False
        or rec_62plus.get("fx6_has_fn_menu", False) is not False
        or rec_62plus.get("fx6_has_my_dial", False) is not False
        or rec_62plus.get("fx6_has_bluetooth_hardware", False) is not False
        or rec_62plus.get("fx6_has_av_tv_rotate", False) is not False
        or rec_62plus.get("hardware_live_attachment_authorized", False) is not False
        or rec_62plus.get("el3_payload_transmit_authorized", False) is not False
        or rec_62plus.get("isp_write_authorized", False) is not False
        or rec_62plus.get("cross_model_flash_authorized", False) is not False
        or rec_62plus.get("overall_ready_for_hardware_attach", False) is not False
    ):
        errors.append(
            "p2: cnflasha RO / zero-touch OTP-RPMB-passive-USB-eND / FX3-vs-FX6 boundary / "
            "Slot1 Tier0-RO redline breached"
        )

    passed = len(errors) == 0
    master_sha_key = f"master_{p_count}pillar_sha256"
    master_sha = rec_62plus.get(master_sha_key) or rec_62plus.get("master_62pillar_sha256")
    evidence = {
        "schema": rec_62plus.get("schema", ""),
        "status": rec_status,
        "pillar_count": p_count,
        "pillars_passed": p_passed,
        "all_passed": bool(rec_62plus.get("all_passed")),
        "cnflasha_userspace_write_blocked": cnflasha_blocked,
        "fx3_has_builtin_evf": rec_62plus.get("fx3_has_builtin_evf", False),
        "fx3_has_builtin_end_filter": rec_62plus.get("fx3_has_builtin_end_filter", False),
        "fx3_has_bt_timecode_link": rec_62plus.get("fx3_has_bt_timecode_link", False),
        "fx3_has_5axis_ibis": rec_62plus.get("fx3_has_5axis_ibis", True),
        "fx6_has_ibis": rec_62plus.get("fx6_has_ibis", False),
        "otp_fuse_writes": otp,
        "rpmb_writes": rpmb,
        "passive_tx_bytes": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "physical_device_writes": dev_writes,
        "raw_firmware_bytes_leaked": leaked,
        "master_recovery_sha256": master_sha,
    }
    pillar = Milestone349PillarResult(
        pillar_id="P2",
        pillar_name="SIXTY_TWO_PLUS_PILLAR_RECOVERY_MASTER_VAULT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Recovery Master {p_passed}/{p_count} pillars (>=62 required; Pillars 57..62 "
            f"DialCustomize-LUTEmbed-SteadyShot-Streaming-BrightMon-BIG6-RecMedia-Cloud-MyMenu), "
            f"cnflasha_ro={cnflasha_blocked}, OTP={otp}, RPMB={rpmb}, passive_tx={ptx} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "recovery_status": rec_status,
        "recovery_pillar_count": p_count,
        "recovery_pillars_passed": p_passed,
        "cnflasha_userspace_write_blocked": cnflasha_blocked,
        "otp_fuse_writes": otp,
        "rpmb_writes": rpmb,
        "passive_tx_bytes": ptx,
        "physical_usb_packets_emitted": usb_pkts,
        "physical_device_writes": dev_writes,
        "raw_firmware_bytes_leaked": leaked,
    }
    return pillar, meta


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: RealHwMilestone349FaultInjection,
) -> Tuple[Milestone349PillarResult, Dict[str, Any]]:
    m324_f = _effective_m324_faults(faults)
    m324_p3, meta = _eval_m324_p3(auditors, m324_f)
    errors: List[str] = list(m324_p3.errors)
    extra_leak = int(faults.p3_raw_firmware_bytes_leaked_override)
    total_leaked = int(meta["raw_firmware_bytes_leaked"]) + extra_leak
    if extra_leak != 0:
        msg = f"p3: raw_firmware_bytes_leaked={total_leaked} != 0"
        if msg not in errors:
            errors.append(msg)
    evidence = dict(m324_p3.evidence)
    evidence["raw_firmware_bytes_leaked"] = total_leaked
    meta = dict(meta)
    meta["raw_firmware_bytes_leaked"] = total_leaked
    passed = (
        len(errors) == 0
        and int(meta["passed_count"]) >= 45
        and int(meta["passed_count"]) == int(meta["auditor_count"])
        and total_leaked == 0
        and int(meta["e_nd_actuator_tx_count"]) == 0
        and int(meta["calibration_mutation_bytes"]) == 0
    )
    pillar = Milestone349PillarResult(
        pillar_id="P3",
        pillar_name="FORTY_FIVE_PLUS_FIRMWARE_LAB_REALBIN_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            m324_p3.summary
            if extra_leak == 0
            else f"p3 raw_firmware_bytes_leaked={total_leaked} FAIL_CLOSED"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: RealHwMilestone349FaultInjection,
) -> Tuple[Milestone349PillarResult, Dict[str, Any]]:
    m324_f = _effective_m324_faults(faults)
    m324_p4, meta_66 = _eval_m324_p4(vm_rep, m324_f)
    errors: List[str] = [
        e for e in m324_p4.errors if not e.startswith("p4: expected >= 66 VM stages")
    ]
    stage_statuses: Dict[str, bool] = dict(m324_p4.evidence["stage_statuses"])

    for skey in VM_COEMULATION_75_STAGE_KEYS[66:]:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if (
            not ok
            and f"p4: forward-compat VM stage {skey} failed" not in errors
            and f"p4: VM co-emulation {skey} failed" not in errors
        ):
            errors.append(f"p4: VM co-emulation {skey} failed")

    stage67_to_75_specs: Tuple[Tuple[str, str, str, Tuple[str, ...], int], ...] = (
        (
            "stage67_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil",
            "67/67",
            "phase322_audit_digest_sha256",
            (
                "steadyshot_active_lockout_bypass_events",
                "dormant_dynamic_active_exposed_events",
                "dormant_movie_selftimer_exposed_events",
                "fx3_led8_tally_confusion_events",
                "zebra_peaking_hdmi_clean_feed_leaked_pixels",
                "fx6_zebra_simultaneous_both_bypass_events",
                "streaming_24p_bypass_events",
                "streaming_rec_4k_lock_bypass_events",
                "slot1_data_sector_writes",
                "slot1_vault_streaming_mutation_bytes",
            ),
            int(faults.p4_stage67_steadyshot_47focal_selftimer_zebra_streaming_faults),
        ),
        (
            "stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil",
            "68/68",
            "phase325_audit_digest_sha256",
            (
                "dormant_lcd_brightness_auto_exposed_events",
                "dormant_divide_extract_or_ftp_cut_exposed_events",
                "dormant_bt_timecode_link_exposed_events",
                "removed_wep_wpa_ipsec_exposed_events",
                "dormant_bulb_timer_or_auto_hdr_exposed_events",
                "bulb_non_mech_or_cont_bypass_events",
                "post_reset_airplane_off_rf_leak_events",
                "slot1_data_sector_writes",
                "slot1_vault_shotmark_edit_mutation_bytes",
            ),
            int(faults.p4_stage68_bright_mon_shotmark_usblan_bulb_dormant_faults),
        ),
        (
            "stage69_realhw_big6_home_framing_interval_tc_ssh_fan_hil",
            "69/69",
            "phase328_audit_digest_sha256",
            (
                "hdmi_sdi_status_bar_leaked_pixels",
                "dormant_auto_framing_exposed_events",
                "framing_highfps_or_rec_bypass_events",
                "interval_inbody_movie_mux_events",
                "interval_iauto_or_bulb_bypass_events",
                "slot1_data_sector_writes",
                "slot1_vault_interval_write_events",
                "fx3_clock_tc_make_exposed_events",
                "hdmi_rec_ctrl_s_and_q_or_notc_bypass_events",
                "ssh_http_basic_https_auth_spoof_events",
                "fan_control_max_exposed_events",
                "fx6_fan_always_off_exposed_events",
            ),
            int(faults.p4_stage69_big6_home_framing_interval_tc_ssh_fan_faults),
        ),
        (
            "stage70_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil",
            "70/70",
            "phase330_audit_digest_sha256",
            (
                "prioritize_rec_media_exposed_events",
                "movie_sort_recording_exposed_events",
                "simult_fs_mismatch_bypass_events",
                "slot2_to_slot1_overflow_bypass_events",
                "sdxc_1200m_or_cfex_b_bypass_events",
                "proxy_highfps_100p_120fps_bypass_events",
                "proxy_coupled_delete_split_events",
                "slot1_data_sector_writes",
                "slot1_vault_proxy_mutation_events",
                "fx6_bluetooth_poweroff_wake_exposed_events",
                "mymenu_out_of_bounds_or_playback_events",
                "fx6_user_menu_lock_pin_file_leak_events",
            ),
            int(faults.p4_stage70_rec_media_autoswitch_proxy_cloud_mymenu_faults),
        ),
        (
            "stage71_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil",
            "71/71",
            "phase333_audit_digest_sha256",
            (
                "dormant_sftp_exposed_events",
                "active_ftp_or_implicit_ftps_bypass_events",
                "dormant_transfer_jpeg_heif_size_exposed_events",
                "usblan_zero_rf_bypass_events",
                "slot1_data_sector_writes",
                "slot1_vault_ftp_mutation_events",
                "custom_wb_camset_leak_events",
                "cine_ei_auto_wb_bypass_events",
                "inbody_focus_map_exposed_events",
                "focus_map_150fps_or_autoframing_bypass_events",
                "af_subj_shift_6_7_spoof_events",
                "hdmi_marker_or_peaking_leaked_pixels",
                "camera_reset_marker_or_peaking_wipe_events",
                "marker_focus_magnifier_collision_events",
            ),
            int(faults.p4_stage71_ftp_ftpes_usblan_customwb_af_focusmap_marker_faults),
        ),
        (
            "stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil",
            "72/72",
            "phase335_audit_digest_sha256",
            (
                "external_mic_wind_reduction_leak_events",
                "proxy_4ch_audio_bypass_events",
                "standalone_audio_level_display_spoof_events",
                "audio_out_timing_setup_misroute_events",
                "dormant_bird_insect_car_airplane_exposed_events",
                "animal_eye_af_in_movie_bypass_events",
                "face_eye_frame_hdmi_leaked_pixels",
                "face_memory_camset_leak_events",
                "face_memory_camera_reset_wipe_events",
                "silent_mode_5lock_bypass_events",
                "target_function_extra_item_spoof_events",
                "shutter_when_pwr_off_exposed_events",
                "airplane_mode_version_dot_leak_events",
                "bodydata_stepping_stone_bypass_events",
                "bodydata_slot2_or_fx6_slota_bypass_events",
                "bodydata_flash_execution_events",
                "cross_model_flash_attempt_admitted_events",
                "slot1_data_sector_writes",
            ),
            int(faults.p4_stage72_shoe_audio_4ch_subject_recog_silent_target_version_faults),
        ),
        (
            "stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil",
            "73/73",
            "phase337_audit_digest_sha256",
            (
                "dormant_color_gamut_raw_out_exposed_events",
                "hdmi_only_card_write_leak_events",
                "rec_media_on_slot1_erofs_bypass_events",
                "rec_control_without_tc_bypass_events",
                "desqueeze_1_8x_exposed_events",
                "desqueeze_4lock_bypass_events",
                "desqueeze_inbody_stream_mutation_events",
                "fx6_sdi_desqueeze_leak_events",
                "dormant_tally_light_menu_exposed_events",
                "dormant_rec_lamp_single_rear_exposed_events",
                "emph_rec_clean_hdmi_leaked_pixels",
                "dormant_var_shutter_exposed_events",
                "antiflicker_silent_or_eshutter_bypass_events",
                "apsc_s35_camera_reset_wipe_events",
                "apsc_s35_4k_or_dci4k_bypass_events",
                "still_apsc_l_12m_bypass_events",
                "slot1_data_sector_writes",
            ),
            int(faults.p4_stage73_hdmi_raw_desqueeze_reclamp_varshutter_apsc_faults),
        ),
        (
            "stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil",
            "74/74",
            "phase339_audit_digest_sha256",
            (
                "breathing_comp_120p_raw_sq_bypass_events",
                "breathing_comp_reset_immunity_drift_events",
                "fx6_all_sq_breathing_leak_events",
                "sdhc_nonstandard_format_bypass_events",
                "sdhc_exfat_simult_bypass_events",
                "camid_pos_rollover_menu_mutation_events",
                "slot1_file_settings_erofs_bypass_events",
                "copyright_reset_wipe_errata_events",
                "write_serial_number_reset_wipe_events",
                "camset_copyright_pii_leak_events",
                "photographer_copyright_pii_leaked_bytes",
                "body_serial_number_leaked_bytes",
                "dormant_power_save_by_monitor_exposed_events",
                "dormant_power_save_steps_exposed_events",
                "ntsc_pal_slot1_format_erofs_bypass_events",
                "pal_2398p_or_df_bypass_events",
                "slot1_data_sector_writes",
            ),
            int(faults.p4_stage74_breathing_camid_copyright_powersave_ntsc_pal_faults),
        ),
        (
            "stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil",
            "75/75",
            "phase343_audit_digest_sha256",
            (
                "zoom_range_reset_immunity_drift_events",
                "zoom_ring_rotate_reset_immunity_drift_events",
                "non_optical_zoom_af_tracking_bypass_events",
                "fx6_digital_zoom_leak_events",
                "auto_slow_shutter_6lock_bypass_events",
                "iso_range_limit_reset_immunity_drift_events",
                "iso_range_limit_leaked_to_auto_events",
                "iso_auto_min_ss_movie_or_sq_bypass_events",
                "fx6_iso_auto_min_ss_exposed_events",
                "dormant_lossless_raw_exposed_events",
                "hlg_still_prerequisite_bypass_events",
                "sort_recording_slot1_erofs_bypass_events",
                "fx6_still_arw_or_heif_exposed_events",
                "usb_lun_slot1_host_pollution_events",
                "usb_pd_batteryless_power_bypass_events",
                "fx3_native_uvc_exposed_events",
                "fx6_native_uvc_exposed_events",
                "streaming_movie_rec_slot1_erofs_bypass_events",
                "slot1_data_sector_writes",
            ),
            int(faults.p4_stage75_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_faults),
        ),
    )

    extra_emmc = 0
    extra_wf12 = 0
    for skey, exp_milestone, digest_key, fault_counters, injected in stage67_to_75_specs:
        sobj = vm_rep.get(skey, {})
        if isinstance(sobj, Mapping):
            extra_emmc += max(0, int(sobj.get("emmc_mutation_bytes", 0)))
            extra_wf12 += max(0, int(sobj.get("wf12_00342260_hits", 0)))
        counter_sum = injected + sum(
            int(sobj.get(ck, -1)) if isinstance(sobj, Mapping) else -1 for ck in fault_counters
        )
        milestone_ok = isinstance(sobj, Mapping) and sobj.get("milestone") == exp_milestone
        digest_val = sobj.get(digest_key, "") if isinstance(sobj, Mapping) else ""
        digest_ok = isinstance(digest_val, str) and len(digest_val) == 64
        avf_ok = isinstance(sobj, Mapping) and sobj.get("slot1_avf_info_mutated") is False
        if (
            not _check_vm_stage45_to_47_redlines(sobj)
            or not avf_ok
            or counter_sum != 0
            or not milestone_ok
            or not digest_ok
        ):
            errors.append(
                f"p4: {skey} redlines/milestone ({exp_milestone})/digest violated (fault_sum={counter_sum})"
            )
            stage_statuses[skey] = False

    # Forward-compatible discovery of Stage 76+ keys (e.g., concurrent H430 Stage 76)
    _opt_zero_keys = (
        "nop_count",
        "cp_mutation_bytes",
        "wbi_mutation_bytes",
        "calibration_mutation_bytes",
        "emmc_mutation_bytes",
        "spi_nor_mutation_bytes",
        "cnflasha_mutation_bytes",
        "bk4_persistent_nvram_writes",
        "physical_device_writes",
        "raw_firmware_bytes_leaked",
        "wf12_00342260_hits",
        "rsv_orphan_count",
        "emmc_corruptions",
    )
    for skey, sobj in sorted(vm_rep.items()):
        m = _VM_STAGE_KEY_RE.match(str(skey))
        if m and int(m.group(1)) >= 76 and isinstance(sobj, Mapping):
            full_redlines_ok = (
                _check_vm_stage45_to_47_redlines(sobj)
                if "nop_count" in sobj
                else True
            )
            opt_zero_ok = all(int(sobj[k]) == 0 for k in _opt_zero_keys if k in sobj)
            opt_lock_ok = (
                sobj.get("cnflasha_userspace_write_blocked", True) is True
                and sobj.get("persistent_emmc_writes_authorized", False) is False
                and sobj.get("spi_nor_write_authorized", False) is False
                and sobj.get("el3_payload_transmit_authorized", False) is False
            )
            ok = (
                bool(sobj.get("all_checks_passed"))
                and full_redlines_ok
                and opt_zero_ok
                and opt_lock_ok
                and sobj.get("slot1_avf_info_mutated", False) is False
            )
            extra_emmc += max(0, int(sobj.get("emmc_mutation_bytes", 0)))
            extra_wf12 += max(0, int(sobj.get("wf12_00342260_hits", 0)))
            stage_statuses[str(skey)] = ok
            if not ok and f"p4: forward-compat VM stage {skey} failed" not in errors:
                errors.append(f"p4: forward-compat VM stage {skey} failed")

    vm_raw_leaked = int(meta_66.get("raw_firmware_bytes_leaked", 0)) + int(
        faults.p4_raw_firmware_bytes_leaked_override
    )
    vm_phys_writes = int(meta_66.get("physical_device_writes", 0)) + int(
        faults.p4_physical_device_writes_override
    )
    vm_stages_total = len(stage_statuses)
    vm_stages_passed = sum(1 for v in stage_statuses.values() if v)
    emmc_corruptions = int(meta_66.get("emmc_corruptions", 0)) + extra_emmc
    total_wf12_hits = int(meta_66.get("wf12_00342260_hits", 0)) + extra_wf12
    total_end_tx = int(meta_66.get("e_nd_actuator_tx_count", 0))

    if not (vm_stages_passed >= 75 and vm_stages_passed == vm_stages_total):
        errors.append(
            f"p4: expected >= 75 VM stages and all passing, got {vm_stages_passed}/{vm_stages_total}"
        )
    if vm_raw_leaked != 0:
        msg = f"p4: raw_firmware_bytes_leaked={vm_raw_leaked} != 0"
        if msg not in errors:
            errors.append(msg)
    if vm_phys_writes != 0:
        msg = f"p4: physical_device_writes={vm_phys_writes} != 0"
        if msg not in errors:
            errors.append(msg)
    if emmc_corruptions != 0:
        msg = f"p4: emmc_corruptions={emmc_corruptions} != 0"
        if msg not in errors:
            errors.append(msg)

    passed = len(errors) == 0
    evidence = dict(m324_p4.evidence)
    evidence.update(
        {
            "vm_stages_total": vm_stages_total,
            "vm_stages_passed": vm_stages_passed,
            "stage_count": vm_stages_total,
            "passed_count": vm_stages_passed,
            "passed_stage_count": vm_stages_passed,
            "stage_statuses": stage_statuses,
            "raw_firmware_bytes_leaked": vm_raw_leaked,
            "physical_device_writes": vm_phys_writes,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "e_nd_actuator_tx_count": total_end_tx,
            "stage67_digest_sha256": vm_rep.get(
                "stage67_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil", {}
            ).get("phase322_audit_digest_sha256"),
            "stage72_digest_sha256": vm_rep.get(
                "stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil", {}
            ).get("phase335_audit_digest_sha256"),
            "stage75_digest_sha256": vm_rep.get(
                "stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil", {}
            ).get("phase343_audit_digest_sha256"),
            "stage75_milestone": vm_rep.get(
                "stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil", {}
            ).get("milestone"),
        }
    )
    pillar = Milestone349PillarResult(
        pillar_id="P4",
        pillar_name="SEVENTY_FIVE_PLUS_STAGE_VM_HIL_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {vm_stages_passed}/{vm_stages_total} stages (>=75 required; Stages 67..75 "
            f"SteadyShot47-BrightMon-BIG6-RecMedia-FTP-ShoeAudio4ch-HDMIRawDeSqueeze-Breathing-CIZ-USBLUN), "
            f"phys_writes={vm_phys_writes}, leaked={vm_raw_leaked}B, emmc_corruptions={emmc_corruptions} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_66)
    meta.update(
        {
            "stage_count": vm_stages_total,
            "passed_count": vm_stages_passed,
            "raw_firmware_bytes_leaked": vm_raw_leaked,
            "physical_device_writes": vm_phys_writes,
            "emmc_corruptions": emmc_corruptions,
            "wf12_00342260_hits": total_wf12_hits,
            "e_nd_actuator_tx_count": total_end_tx,
        }
    )
    return pillar, meta


def _check_uniform_4group_bench_verifier(
    *,
    tag: str,
    raw_off: Mapping[str, Any],
    raw_sim: Mapping[str, Any],
    verify_fn: Callable[[Mapping[str, Any]], Any],
    errors: List[str],
    extra_usb_override: int = 0,
    extra_passive_override: int = 0,
    extra_wrf_override: int = 0,
) -> Dict[str, Any]:
    """Verify uniform 4-group bench readiness verifier (P329/P334/P338/P341/P342/P345)."""
    off_dict = copy.deepcopy(dict(raw_off))
    v_off = verify_fn(off_dict)
    off_ready = bool(off_dict.get("overall_ready_for_hardware_attach", False))
    if (
        not v_off.valid
        or off_dict.get("go_no_go") != GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        or off_dict.get("hardware_live_attachment_authorized") is not False
        or off_ready is not False
        or off_dict.get("tier0_receipt_verified") is not False
        or int(off_dict.get("check_groups_passed", -1)) != 4
        or int(off_dict.get("check_group_count", -1)) != 4
        or off_dict.get("sd_physical_media_written") is not False
        or int(off_dict.get("usb_packets_transmitted", -1)) != 0
        or int(off_dict.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(off_dict.get("passive_tx_bytes_emitted", -1)) != 0
    ):
        errors.append(
            f"p5_{tag}_off: expected {GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT} "
            f"(got {off_dict.get('go_no_go')}, valid={v_off.valid}, errs={v_off.errors})"
        )

    sim_dict = copy.deepcopy(dict(raw_sim))
    if extra_usb_override:
        sim_dict["usb_packets_transmitted"] = int(
            sim_dict.get("usb_packets_transmitted", 0)
        ) + int(extra_usb_override)
    if extra_passive_override:
        sim_dict["passive_tx_bytes_emitted"] = int(
            sim_dict.get("passive_tx_bytes_emitted", 0)
        ) + int(extra_passive_override)

    v_sim = verify_fn(sim_dict)
    sim_passed = int(sim_dict.get("check_groups_passed", -1))
    sim_pkts = int(sim_dict.get("usb_packets_transmitted", -1))
    sim_leaked = int(sim_dict.get("raw_firmware_bytes_leaked", -1))
    sim_passive = int(sim_dict.get("passive_tx_bytes_emitted", -1))
    sim_h0_h3 = int(sim_dict.get("h0_equals_h3_count", -1))
    sim_ready = bool(sim_dict.get("overall_ready_for_hardware_attach", False))
    all_cgs_ok = all(
        isinstance(sim_dict.get(gk), Mapping) and bool(sim_dict[gk].get("passed"))
        for gk in ("check_group_a", "check_group_b", "check_group_c", "check_group_d")
    )

    if (
        not v_sim.valid
        or sim_dict.get("go_no_go") != GO_NO_GO_DRY_RUN_SIMULATED_READY
        or int(sim_dict.get("check_group_count", -1)) != 4
        or sim_passed != 4
        or not all_cgs_ok
        or not bool(sim_dict.get("tier0_receipt_verified"))
        or sim_dict.get("hardware_live_attachment_authorized") is not False
        or sim_ready is not False
        or sim_dict.get("sd_physical_media_written") is not False
        or sim_h0_h3 != 16
        or sim_pkts != 0
        or sim_leaked != 0
        or sim_passive != 0
        or sim_dict.get("persistent_emmc_writes_authorized") is not False
        or sim_dict.get("spi_nor_write_authorized") is not False
        or sim_dict.get("el3_payload_transmit_authorized") is not False
    ):
        errors.append(
            f"p5_{tag}_sim: simulated dry-run failed "
            f"(go={sim_dict.get('go_no_go')}, groups={sim_passed}/4, valid={v_sim.valid}, errs={v_sim.errors})"
        )

    wrf = int(sim_dict.get("wireless_rf_packets_emitted", -1)) + int(extra_wrf_override)
    rf = int(sim_dict.get("rf_packets_transmitted", -1)) + int(extra_wrf_override)
    end_tx = int(sim_dict.get("e_nd_actuator_tx_count", -1))
    slot1_wr = int(sim_dict.get("slot1_data_sector_writes", -1))
    if (
        wrf != 0
        or rf != 0
        or end_tx != 0
        or slot1_wr != 0
        or sim_dict.get("rf_nvs_p12_p13_writes_authorized", True) is not False
        or sim_dict.get("slot1_tier0_vault_mutated", True) is not False
    ):
        errors.append(
            f"p5_{tag}_zero_rf_end_slot1: wrf={wrf}, rf={rf}, e_nd={end_tx}, "
            f"slot1_writes={slot1_wr}, rf_nvs_auth={sim_dict.get('rf_nvs_p12_p13_writes_authorized')}, "
            f"slot1_mutated={sim_dict.get('slot1_tier0_vault_mutated')}"
        )

    return {
        f"{tag}_offline_go_no_go": str(off_dict.get("go_no_go", "")),
        f"{tag}_offline_check_groups_passed": int(off_dict.get("check_groups_passed", 0)),
        f"{tag}_offline_report_verified": bool(v_off.valid),
        f"{tag}_sim_go_no_go": str(sim_dict.get("go_no_go", "")),
        f"{tag}_sim_check_groups_passed": sim_passed,
        f"{tag}_hardware_live_attachment_authorized": bool(
            sim_dict.get("hardware_live_attachment_authorized", True)
        ),
        f"{tag}_h0_equals_h3_count": sim_h0_h3,
        f"{tag}_sim_usb_packets_transmitted": sim_pkts,
        f"{tag}_sim_raw_firmware_bytes_leaked": sim_leaked,
        f"{tag}_sim_passive_tx_bytes_emitted": sim_passive,
        f"{tag}_wireless_rf_packets_emitted": wrf,
        f"{tag}_rf_packets_transmitted": rf,
        f"{tag}_e_nd_actuator_tx_count": end_tx,
        f"{tag}_slot1_data_sector_writes": slot1_wr,
        f"{tag}_sim_report_verified": bool(v_sim.valid),
        f"{tag}_sim_report_sha256": str(sim_dict.get("report_sha256", "")),
        "_any_attach_ready": bool(off_ready or sim_ready),
    }


def _evaluate_pillar_5(
    raw_p136: Mapping[str, Any],
    raw_p143: Mapping[str, Any],
    raw_p154: Mapping[str, Any],
    raw_p186_off: Mapping[str, Any],
    raw_p186_sim: Mapping[str, Any],
    raw_p204_off: Mapping[str, Any],
    raw_p204_sim: Mapping[str, Any],
    raw_p216_off: Mapping[str, Any],
    raw_p216_sim: Mapping[str, Any],
    raw_p227_off: Mapping[str, Any],
    raw_p227_sim: Mapping[str, Any],
    raw_p248_off: Mapping[str, Any],
    raw_p248_sim: Mapping[str, Any],
    raw_p261_off: Mapping[str, Any],
    raw_p261_sim: Mapping[str, Any],
    raw_p275_off: Mapping[str, Any],
    raw_p275_sim: Mapping[str, Any],
    raw_p279_off: Mapping[str, Any],
    raw_p279_sim: Mapping[str, Any],
    raw_p284_off: Mapping[str, Any],
    raw_p284_sim: Mapping[str, Any],
    raw_p291_off: Mapping[str, Any],
    raw_p291_sim: Mapping[str, Any],
    raw_p302_off: Mapping[str, Any],
    raw_p302_sim: Mapping[str, Any],
    raw_p307_off: Mapping[str, Any],
    raw_p307_sim: Mapping[str, Any],
    raw_p316_off: Mapping[str, Any],
    raw_p316_sim: Mapping[str, Any],
    raw_p321_off: Mapping[str, Any],
    raw_p321_sim: Mapping[str, Any],
    raw_p329_off: Mapping[str, Any],
    raw_p329_sim: Mapping[str, Any],
    raw_p334_off: Mapping[str, Any],
    raw_p334_sim: Mapping[str, Any],
    raw_p338_off: Mapping[str, Any],
    raw_p338_sim: Mapping[str, Any],
    raw_p341_off: Mapping[str, Any],
    raw_p341_sim: Mapping[str, Any],
    raw_p342_off: Mapping[str, Any],
    raw_p342_sim: Mapping[str, Any],
    raw_p345_off: Mapping[str, Any],
    raw_p345_sim: Mapping[str, Any],
    faults: RealHwMilestone349FaultInjection,
) -> Tuple[Milestone349PillarResult, Dict[str, Any]]:
    m324_p5, meta_p5_324 = _eval_m324_p5(
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        raw_p227_off,
        raw_p227_sim,
        raw_p248_off,
        raw_p248_sim,
        raw_p261_off,
        raw_p261_sim,
        raw_p275_off,
        raw_p275_sim,
        raw_p279_off,
        raw_p279_sim,
        raw_p284_off,
        raw_p284_sim,
        raw_p291_off,
        raw_p291_sim,
        raw_p302_off,
        raw_p302_sim,
        raw_p307_off,
        raw_p307_sim,
        raw_p316_off,
        raw_p316_sim,
        raw_p321_off,
        raw_p321_sim,
        _effective_m324_faults(faults),
    )
    errors: List[str] = [
        e
        for e in m324_p5.errors
        if e != "p5: overall_ready_for_hardware_attach must remain False across all 14 verifiers"
    ]

    info_329 = _check_uniform_4group_bench_verifier(
        tag="p329",
        raw_off=raw_p329_off,
        raw_sim=raw_p329_sim,
        verify_fn=verify_phase329_report,
        errors=errors,
        extra_usb_override=faults.p5_inject_p329_usb_packets_override,
        extra_passive_override=faults.p5_inject_p329_passive_tx_bytes_override,
        extra_wrf_override=faults.p5_inject_p329_wireless_rf_packets_override,
    )
    info_334 = _check_uniform_4group_bench_verifier(
        tag="p334",
        raw_off=raw_p334_off,
        raw_sim=raw_p334_sim,
        verify_fn=verify_phase334_report,
        errors=errors,
        extra_usb_override=faults.p5_inject_p334_usb_packets_override,
        extra_passive_override=faults.p5_inject_p334_passive_tx_bytes_override,
        extra_wrf_override=faults.p5_inject_p334_wireless_rf_packets_override,
    )
    info_338 = _check_uniform_4group_bench_verifier(
        tag="p338",
        raw_off=raw_p338_off,
        raw_sim=raw_p338_sim,
        verify_fn=verify_phase338_report,
        errors=errors,
        extra_usb_override=faults.p5_inject_p338_usb_packets_override,
        extra_passive_override=faults.p5_inject_p338_passive_tx_bytes_override,
        extra_wrf_override=faults.p5_inject_p338_wireless_rf_packets_override,
    )
    info_341 = _check_uniform_4group_bench_verifier(
        tag="p341",
        raw_off=raw_p341_off,
        raw_sim=raw_p341_sim,
        verify_fn=verify_phase341_report,
        errors=errors,
        extra_usb_override=faults.p5_inject_p341_usb_packets_override,
        extra_passive_override=faults.p5_inject_p341_passive_tx_bytes_override,
        extra_wrf_override=faults.p5_inject_p341_wireless_rf_packets_override,
    )
    info_342 = _check_uniform_4group_bench_verifier(
        tag="p342",
        raw_off=raw_p342_off,
        raw_sim=raw_p342_sim,
        verify_fn=verify_phase342_report,
        errors=errors,
        extra_usb_override=faults.p5_inject_p342_usb_packets_override,
        extra_passive_override=faults.p5_inject_p342_passive_tx_bytes_override,
        extra_wrf_override=faults.p5_inject_p342_wireless_rf_packets_override,
    )
    info_345 = _check_uniform_4group_bench_verifier(
        tag="p345",
        raw_off=raw_p345_off,
        raw_sim=raw_p345_sim,
        verify_fn=verify_phase345_report,
        errors=errors,
        extra_usb_override=faults.p5_inject_p345_usb_packets_override,
        extra_passive_override=faults.p5_inject_p345_passive_tx_bytes_override,
        extra_wrf_override=faults.p5_inject_p345_wireless_rf_packets_override,
    )

    any_attach_ready = bool(
        meta_p5_324["overall_ready_for_hardware_attach"]
        or info_329.pop("_any_attach_ready")
        or info_334.pop("_any_attach_ready")
        or info_338.pop("_any_attach_ready")
        or info_341.pop("_any_attach_ready")
        or info_342.pop("_any_attach_ready")
        or info_345.pop("_any_attach_ready")
    )
    if any_attach_ready:
        errors.append("p5: overall_ready_for_hardware_attach must remain False across all 20 verifiers")

    passed = len(errors) == 0
    evidence = dict(m324_p5.evidence)
    for extra in (info_329, info_334, info_338, info_341, info_342, info_345):
        evidence.update(extra)
    evidence["bench_preflight_verifier_count"] = 20
    evidence["overall_ready_for_hardware_attach"] = any_attach_ready

    pillar = Milestone349PillarResult(
        pillar_id="P5",
        pillar_name="ICOSUPLE_20_BENCH_READINESS_PREFLIGHTS_PH186_TO_PH345",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"20/20 Bench Preflights: Ph186..Ph321(14/14) + "
            f"Ph329({info_329['p329_sim_check_groups_passed']}/4) + "
            f"Ph334({info_334['p334_sim_check_groups_passed']}/4) + "
            f"Ph338({info_338['p338_sim_check_groups_passed']}/4) + "
            f"Ph341({info_341['p341_sim_check_groups_passed']}/4) + "
            f"Ph342({info_342['p342_sim_check_groups_passed']}/4) + "
            f"Ph345({info_345['p345_sim_check_groups_passed']}/4, H0==H3={info_345['p345_h0_equals_h3_count']}/16) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = dict(meta_p5_324)
    for extra in (info_329, info_334, info_338, info_341, info_342, info_345):
        meta.update(extra)
    meta["bench_preflight_verifier_count"] = 20
    meta["overall_ready_for_hardware_attach"] = any_attach_ready
    return pillar, meta


def _evaluate_pillar_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: RealHwMilestone349FaultInjection,
    p1_meta: Mapping[str, Any],
    p2_meta: Mapping[str, Any],
    p3_meta: Mapping[str, Any],
    p4_meta: Mapping[str, Any],
    p5_meta: Mapping[str, Any],
) -> Tuple[Milestone349PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    round_sources: Dict[str, str] = {}
    round_schemas: Dict[str, str] = {}
    runs_by_round: Dict[str, int] = {}
    png_sizes_by_asset: Dict[str, int] = {}
    png_sources_by_round: Dict[str, str] = {}

    total_nops = 0
    total_crashes = 0
    total_emmc = 0
    total_qemu_leaked = max(0, int(faults.p6_raw_firmware_bytes_leaked_override))
    rounds_verified = 0
    total_runs_verified = 0
    pngs_verified = 0
    max_png_bytes = 0

    expected_rounds = len(ROUND28_TO_72_SPECS)
    expected_runs = sum(len(s.run_specs) for s in ROUND28_TO_72_SPECS)
    expected_pngs = sum(len(ROUND28_TO_72_PNG_RECEIPTS[s.round_num]) for s in ROUND28_TO_72_SPECS)

    for spec in ROUND28_TO_72_SPECS:
        r_tag = f"r{spec.round_num}"
        raw_round, r_src = _load_round28_to_37_summary(
            spec, repo_root=repo_root, use_clean_room=use_clean_room
        )
        if faults.p6_tamper_schema_round_num == spec.round_num:
            raw_round = copy.deepcopy(raw_round)
            raw_round["schema"] = "tampered-invalid-schema"

        round_sources[r_tag] = r_src
        r_schema = str(raw_round.get("schema", ""))
        r_kver = str(raw_round.get("kernel_version", ""))
        round_schemas[r_tag] = r_schema
        r_leaked = max(0, int(raw_round.get("raw_firmware_bytes_leaked", 0)))
        total_qemu_leaked += r_leaked

        round_ok = True
        if r_schema != spec.expected_schema:
            errors.append(f"p6_{r_tag}: unexpected schema {r_schema!r}")
            round_ok = False
        if "4.9.337-scel+" not in r_kver:
            errors.append(f"p6_{r_tag}: unexpected kernel_version {r_kver!r}")
            round_ok = False
        if r_leaked != 0:
            errors.append(f"p6_{r_tag}: raw_firmware_bytes_leaked={r_leaked} != 0")
            round_ok = False

        audit_obj = raw_round.get(spec.audit_key, {})
        if not isinstance(audit_obj, Mapping):
            errors.append(f"p6_{r_tag}: missing audit block {spec.audit_key}")
            round_ok = False
        else:
            for bkey in spec.audit_bool_keys:
                if not bool(audit_obj.get(bkey, False)):
                    errors.append(f"p6_{r_tag}: audit flag {bkey} is False")
                    round_ok = False

        png_pair = ROUND28_TO_72_PNG_RECEIPTS[spec.round_num]
        for png_idx, png_rel in enumerate(png_pair):
            png_ok, png_size, png_src = _inspect_round_png_receipt_50kib(
                png_rel, repo_root=repo_root, use_clean_room=use_clean_room
            )
            if (
                png_idx == 0
                and faults.p6_png_size_override_round_num == spec.round_num
                and faults.p6_png_size_override_bytes is not None
            ):
                png_size = int(faults.p6_png_size_override_bytes)
                png_ok = 0 < png_size < PNG_MAX_SIZE_50KIB_BYTES
            png_sizes_by_asset[Path(png_rel).name] = png_size
            png_sources_by_round[r_tag] = png_src
            if png_size > max_png_bytes:
                max_png_bytes = png_size
            if png_ok:
                pngs_verified += 1
            else:
                errors.append(
                    f"p6_{r_tag}: PNG receipt invalid or >= {PNG_MAX_SIZE_50KIB_BYTES}B ({png_rel}, size={png_size})"
                )
                round_ok = False

        runs_map = raw_round.get("runs", {})
        if not isinstance(runs_map, Mapping):
            errors.append(f"p6_{r_tag}: missing runs mapping")
            runs_by_round[r_tag] = 0
            continue

        verified_in_round = 0
        for run_idx, (rid, exp_faithful) in enumerate(spec.run_specs):
            robj = runs_map.get(rid)
            if not isinstance(robj, Mapping):
                errors.append(f"p6_{r_tag}: missing run {rid}")
                round_ok = False
                continue

            if (
                run_idx == 0
                and faults.p6_round_nop_override_num == spec.round_num
                and faults.p6_round_nop_count_override is not None
            ):
                rnop = int(faults.p6_round_nop_count_override)
            elif exp_faithful is not None:
                rnop = int(robj.get("nop_count", -1))
            else:
                rnop = int(robj.get("nop_count") or 0)

            if (
                run_idx == 0
                and faults.p6_round_crash_override_num == spec.round_num
                and faults.p6_round_crashes_override is not None
            ):
                rcrash = int(faults.p6_round_crashes_override)
            else:
                rcrash = int(robj.get("crashes", -1))

            if (
                run_idx == 0
                and faults.p6_round_emmc_override_num == spec.round_num
                and faults.p6_round_emmc_writes_override is not None
            ):
                remmc = int(faults.p6_round_emmc_writes_override)
            else:
                remmc = int(robj.get("emmc_write_count", -1))

            total_nops += max(0, rnop)
            total_crashes += max(0, rcrash)
            total_emmc += max(0, remmc)

            rkver = str(robj.get("kernel_version", r_kver))
            sb = robj.get("stage_b", {})
            sb_count = int(sb.get("manifest_count", -1)) if isinstance(sb, Mapping) else -1
            fi_ok = True
            if exp_faithful is not None:
                fi = robj.get("faithful_invariants", {})
                fi_val = int(fi.get("FX6_NATIVE_FAITHFUL", -1)) if isinstance(fi, Mapping) else -1
                if fi_val != exp_faithful:
                    fi_ok = False

            if (
                "4.9.337-scel+" not in rkver
                or rnop != 0
                or rcrash != 0
                or remmc != 0
                or sb_count != 13
                or not fi_ok
            ):
                errors.append(
                    f"p6_{r_tag}:{rid}: failed invariants (nop={rnop}, crash={rcrash}, emmc={remmc}, sb={sb_count}, fi_ok={fi_ok})"
                )
                round_ok = False
                continue

            verified_in_round += 1

        runs_by_round[r_tag] = verified_in_round
        total_runs_verified += verified_in_round
        if round_ok and verified_in_round == len(spec.run_specs):
            rounds_verified += 1

    # Forward-compatible discovery of Round 73+ reports (e.g., concurrent H431 Round 73)
    reports_dir = repo_root / "reports"
    round_73plus_re = re.compile(r"-round(\d+)-")
    if reports_dir.is_dir():
        seen_extra_rounds: Dict[int, Path] = {}
        for d in sorted(reports_dir.iterdir()):
            if not d.is_dir() or d.is_symlink():
                continue
            m = round_73plus_re.search(d.name)
            if not m:
                continue
            rnum = int(m.group(1))
            if rnum >= 73 and (d / "summary.json").is_file():
                seen_extra_rounds[rnum] = d

        for rnum, rdir in sorted(seen_extra_rounds.items()):
            r_tag = f"r{rnum}"
            sj_path = rdir / "summary.json"
            raw_round = json.loads(_read_file_o_rdonly(sj_path).decode("utf-8"))
            round_sources[r_tag] = "REPO_SUMMARY_O_RDONLY"
            r_schema = str(raw_round.get("schema", ""))
            r_kver = str(raw_round.get("kernel_version", ""))
            round_schemas[r_tag] = r_schema
            r_leaked = max(0, int(raw_round.get("raw_firmware_bytes_leaked", 0)))
            total_qemu_leaked += r_leaked
            round_ok = "4.9.337-scel+" in r_kver and r_leaked == 0
            if not round_ok:
                errors.append(f"p6_{r_tag}: forward-compat round kernel/leak check failed")

            for ak, av in raw_round.items():
                if ak.startswith(f"r{rnum}_") and ak.endswith("_audit") and isinstance(av, Mapping):
                    for bk, bv in av.items():
                        if isinstance(bv, bool):
                            is_neg = bk in _NEGATIVE_AUDIT_BOOL_KEYS or (
                                bk.startswith(("fx3_", "fx6_"))
                                and (
                                    bk.endswith(("_present", "_only", "_exposed", "_supported"))
                                    or "_has_" in bk
                                )
                            )
                            if is_neg:
                                if bv is not False:
                                    errors.append(f"p6_{r_tag}: forward-compat audit flag {bk} is True")
                                    round_ok = False
                            elif not bv:
                                errors.append(f"p6_{r_tag}: forward-compat audit flag {bk} is False")
                                round_ok = False

            png_files = sorted(p for p in rdir.rglob("*.png") if p.is_file() and not p.is_symlink())
            expected_pngs += len(png_files)
            for pfile in png_files:
                rel_p = pfile.relative_to(repo_root).as_posix()
                png_ok, png_size, png_src = _inspect_round_png_receipt_50kib(
                    rel_p, repo_root=repo_root, use_clean_room=use_clean_room
                )
                png_sizes_by_asset[pfile.name] = png_size
                png_sources_by_round[r_tag] = png_src
                if png_size > max_png_bytes:
                    max_png_bytes = png_size
                if png_ok:
                    pngs_verified += 1
                else:
                    errors.append(f"p6_{r_tag}: forward-compat PNG invalid ({rel_p})")
                    round_ok = False

            runs_map = raw_round.get("runs", {})
            run_items = list(runs_map.items()) if isinstance(runs_map, Mapping) else []
            expected_rounds += 1
            expected_runs += len(run_items)
            v_runs = 0
            for rid, robj in run_items:
                if not isinstance(robj, Mapping):
                    round_ok = False
                    continue
                rnop = int(robj.get("nop_count") or 0)
                rcrash = int(robj.get("crashes", -1))
                remmc = int(robj.get("emmc_write_count", -1))
                sb_count = int(robj.get("stage_b", {}).get("manifest_count", 13))
                total_nops += max(0, rnop)
                total_crashes += max(0, rcrash)
                total_emmc += max(0, remmc)
                if rnop == 0 and rcrash == 0 and remmc == 0 and sb_count == 13:
                    v_runs += 1
                else:
                    errors.append(f"p6_{r_tag}:{rid}: forward-compat run invariants failed")
                    round_ok = False
            runs_by_round[r_tag] = v_runs
            total_runs_verified += v_runs
            if round_ok and len(run_items) > 0 and v_runs == len(run_items):
                rounds_verified += 1

    if total_qemu_leaked != 0:
        errors.append(f"p6: QEMU raw_firmware_bytes_leaked={total_qemu_leaked} != 0")

    # Cross-pillar hardware-lock, 16/16 H0 == H3, zero eMMC, zero RF & zero e-ND invariants
    if (
        p1_meta.get("persistent_emmc_writes_authorized") is not False
        or p1_meta.get("spi_nor_write_authorized") is not False
        or p1_meta.get("el3_payload_transmit_authorized") is not False
        or p1_meta.get("cross_model_flash_authorized") is not False
        or p1_meta.get("simulated_ready_for_hardware_attach") is not False
        or p1_meta.get("hardware_live_attachment_authorized") is not False
        or int(p1_meta.get("g71_e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P1 hardware-lock, cross-model-flash, or zero e-ND invariant breached")
    if (
        p2_meta.get("cnflasha_userspace_write_blocked") is not True
        or int(p2_meta.get("otp_fuse_writes", -1)) != 0
        or int(p2_meta.get("rpmb_writes", -1)) != 0
        or int(p2_meta.get("passive_tx_bytes", -1)) != 0
        or int(p2_meta.get("physical_usb_packets_emitted", -1)) != 0
        or int(p2_meta.get("physical_device_writes", -1)) != 0
        or int(p2_meta.get("raw_firmware_bytes_leaked", -1)) != 0
    ):
        errors.append("p6: P2 cnflasha RO or zero-touch OTP/RPMB/passive-UART/USB-PKT invariant breached")
    if (
        int(p3_meta.get("calibration_mutation_bytes", -1)) != 0
        or int(p3_meta.get("wbi_mutation_bytes", -1)) != 0
        or int(p3_meta.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(p3_meta.get("e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P3 calibration/WBI/raw-FW/zero-e-ND invariant breached")
    if (
        int(p4_meta.get("cp_mutation_bytes", -1)) != 0
        or int(p4_meta.get("bk4_persistent_nvram_writes", -1)) != 0
        or int(p4_meta.get("wf12_00342260_hits", -1)) != 0
        or int(p4_meta.get("emmc_corruptions", -1)) != 0
        or int(p4_meta.get("physical_device_writes", -1)) != 0
        or int(p4_meta.get("raw_firmware_bytes_leaked", -1)) != 0
        or int(p4_meta.get("e_nd_actuator_tx_count", -1)) != 0
    ):
        errors.append("p6: P4 CP/BK4/WF-12/eMMC/zero-device-write/zero-e-ND invariant breached")

    if (
        int(p5_meta.get("h0_equals_h3_count", -1)) != 16
        or p5_meta.get("overall_ready_for_hardware_attach") is not False
        or not bool(p5_meta.get("p154_bench_go"))
        or int(p5_meta.get("bench_preflight_verifier_count", -1)) != 20
        or any(
            int(p5_meta.get(f"{tag}_sim_check_groups_passed", -1)) != 4
            or p5_meta.get(f"{tag}_hardware_live_attachment_authorized") is not False
            or int(p5_meta.get(f"{tag}_h0_equals_h3_count", -1)) != 16
            or int(p5_meta.get(f"{tag}_sim_usb_packets_transmitted", -1)) != 0
            or int(p5_meta.get(f"{tag}_sim_raw_firmware_bytes_leaked", -1)) != 0
            or int(p5_meta.get(f"{tag}_sim_passive_tx_bytes_emitted", -1)) != 0
            or int(p5_meta.get(f"{tag}_wireless_rf_packets_emitted", -1)) != 0
            or int(p5_meta.get(f"{tag}_rf_packets_transmitted", -1)) != 0
            or int(p5_meta.get(f"{tag}_e_nd_actuator_tx_count", -1)) != 0
            or int(p5_meta.get(f"{tag}_slot1_data_sector_writes", -1)) != 0
            for tag in ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345")
        )
    ):
        errors.append(
            "p6: P5 H0==H3 (16/16) or 20/20 icosuple bench preflight (Ph186..Ph345) invariant breached"
        )

    passed = (
        len(errors) == 0
        and rounds_verified >= 45
        and rounds_verified == expected_rounds
        and total_runs_verified >= 135
        and total_runs_verified == expected_runs
        and pngs_verified >= 90
        and pngs_verified == expected_pngs
        and 0 < max_png_bytes < PNG_MAX_SIZE_50KIB_BYTES
        and total_qemu_leaked == 0
        and total_nops == 0
        and total_crashes == 0
        and total_emmc == 0
    )
    max_round_num = 27 + expected_rounds
    evidence = {
        "round_sources": round_sources,
        "round_schemas": round_schemas,
        "rounds_verified": rounds_verified,
        "expected_rounds": expected_rounds,
        "runs_by_round": runs_by_round,
        "total_runs_verified": total_runs_verified,
        "expected_total_runs": expected_runs,
        "png_receipts_verified": pngs_verified,
        "expected_png_receipts": expected_pngs,
        "png_max_bytes": max_png_bytes,
        "png_max_ceiling_bytes": PNG_MAX_SIZE_50KIB_BYTES,
        "png_baseline_max_observed_bytes": P349_BASELINE_PNG_MAX_OBSERVED_BYTES,
        "png_sizes_by_asset": png_sizes_by_asset,
        "png_sources_by_round": png_sources_by_round,
        "h0_equals_h3_count": int(p5_meta.get("p345_h0_equals_h3_count", 0)),
        "emmc_write_count": total_emmc,
        "e_nd_actuator_tx_count": max(0, int(p1_meta.get("g71_e_nd_actuator_tx_count", 0)))
        + max(0, int(p4_meta.get("e_nd_actuator_tx_count", 0)))
        + max(0, int(p5_meta.get("p204_e_nd_actuator_tx_count", 0)))
        + max(0, int(p5_meta.get("p261_e_nd_uart_bytes_transmitted", 0)))
        + sum(
            max(0, int(p5_meta.get(f"{tag}_e_nd_actuator_tx_count", 0)))
            for tag in ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345")
        ),
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "raw_firmware_bytes_leaked": total_qemu_leaked,
        "milestone175_schema_anchor": MILESTONE175_SCHEMA_VERSION,
        "milestone193_schema_anchor": MILESTONE193_SCHEMA_VERSION,
        "milestone209_schema_anchor": MILESTONE209_SCHEMA_VERSION,
        "milestone221_schema_anchor": MILESTONE221_SCHEMA_VERSION,
        "milestone233_schema_anchor": MILESTONE233_SCHEMA_VERSION,
        "milestone254_schema_anchor": MILESTONE254_SCHEMA_VERSION,
        "milestone264_schema_anchor": MILESTONE264_SCHEMA_VERSION,
        "milestone295_schema_anchor": MILESTONE295_SCHEMA_VERSION,
        "milestone311_schema_anchor": MILESTONE311_SCHEMA_VERSION,
        "milestone324_schema_anchor": MILESTONE324_SCHEMA_VERSION,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
    }
    pillar = Milestone349PillarResult(
        pillar_id="P6",
        pillar_name="REAL_FX3_702_QEMU_ROUNDS_28_TO_72_PLUS_AND_PNG_RECEIPTS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Live FX3 7.02 QEMU Rounds 28..{max_round_num}={rounds_verified}/{expected_rounds} rounds "
            f"({total_runs_verified}/{expected_runs} runs, PNGs={pngs_verified}/{expected_pngs} "
            f"max={max_png_bytes}B < 50KiB), H0==H3=16/16, nop={total_nops}, crashes={total_crashes}, "
            f"emmc={total_emmc}, leaked={total_qemu_leaked}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "qemu_rounds_total": expected_rounds,
        "qemu_rounds_verified": rounds_verified,
        "qemu_runs_total": expected_runs,
        "qemu_runs_verified": total_runs_verified,
        "qemu_png_receipts_total": expected_pngs,
        "qemu_png_receipts_verified": pngs_verified,
        "qemu_png_max_bytes": max_png_bytes,
        "qemu_round_runs_by_round": runs_by_round,
        "qemu_real_kernel_nop_count": total_nops,
        "qemu_real_kernel_crashes": total_crashes,
        "qemu_real_kernel_emmc_writes": total_emmc,
        "qemu_raw_firmware_bytes_leaked": total_qemu_leaked,
    }
    return pillar, meta


# ---------------------------------------------------------------------------
# Parallel Collector, Builder, Fail-Closed Verifier & CLI
# ---------------------------------------------------------------------------


def _collect_parallel_milestone349_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Optional[Path],
    fx3_modules_dir: Optional[Path],
    use_clean_room: bool,
    faults: RealHwMilestone349FaultInjection,
    donorless_work_root_none: bool = False,
) -> Tuple[Any, ...]:
    from .realhw_milestone324_master_gate import (
        _effective_m264_faults,
        _effective_m295_from_m311,
        _effective_m311_faults,
    )
    from .realhw_milestone264_master_gate import _effective_m254_faults
    from .realhw_milestone254_master_gate import _effective_m233_faults
    from .realhw_milestone233_master_gate import _effective_m221_faults
    from .realhw_milestone221_master_gate import _effective_m209_faults
    from .realhw_milestone209_master_gate import _effective_m193_faults

    m324_f = _effective_m324_faults(faults)
    m311_f = _effective_m311_faults(m324_f)
    m295_f = _effective_m295_from_m311(m311_f)
    m264_f = _effective_m264_faults(m295_f)
    m254_f = _effective_m254_faults(m264_f)
    m233_f = _effective_m233_faults(m254_f)
    m221_f = _effective_m221_faults(m233_f)
    m209_f = _effective_m209_faults(m221_f)
    m193_f = _effective_m193_faults(m209_f)
    gate_fault_dict = _fault_to_148gate_worker_dict(faults)
    p154_sim_ready = not m193_f.p5_inject_p154_no_go_fault

    fx6_leg_str = (
        str(fx6_lib_dir)
        if fx6_lib_dir is not None
        else str(repo_root / "__nonexistent_fx6_lib__")
    )
    fx3_leg_str = (
        str(fx3_modules_dir)
        if fx3_modules_dir is not None
        else str(repo_root / "__nonexistent_fx3_modules__")
    )
    fx6_opt_str = str(fx6_lib_dir) if fx6_lib_dir is not None else None
    fx3_opt_str = str(fx3_modules_dir) if fx3_modules_dir is not None else None

    p186_fault_dict = {
        "inject_appledouble_fault": bool(m193_f.p5_inject_p186_appledouble_fault),
        "inject_h0_h3_drift": bool(m193_f.p5_inject_p186_h0_h3_drift),
        "inject_fw_below_204": bool(m193_f.p5_inject_p186_fw_below_204),
        "inject_single_device_collision": bool(m193_f.p5_inject_p186_single_device_collision),
    }
    p204_fault_dict = {
        "fan_auto1": bool(m209_f.p5_inject_p204_fan_auto1_fault),
        "always_off": bool(m209_f.p5_inject_p204_always_off_fault),
        "end_tx": bool(m209_f.p5_inject_p204_end_tx_fault),
        "camset_slot2": bool(m209_f.p5_inject_p204_camset_slot2_fault),
        "vmc_xlrh1_port": bool(m209_f.p5_inject_p204_vmc_xlrh1_port_fault),
        "h0_h3_drift": bool(m209_f.p5_inject_p204_h0_h3_drift),
    }
    p216_fault_dict = {
        "desqueeze_lock": bool(m221_f.p5_inject_p216_desqueeze_lock_fault),
        "hdmi_only_card_rec": bool(m221_f.p5_inject_p216_hdmi_only_card_rec_fault),
        "proxy_orphan": bool(m221_f.p5_inject_p216_proxy_orphan_fault),
        "title_38char": bool(m221_f.p5_inject_p216_title_38char_fault),
        "h0_h3_drift": bool(m221_f.p5_inject_p216_h0_h3_drift),
    }
    p227_fault_dict = {
        "pixelmap_lowbatt": bool(m233_f.p5_inject_p227_pixelmap_lowbatt_fault),
        "ntscpal_fps_conflict": bool(m233_f.p5_inject_p227_ntscpal_fps_conflict_fault),
        "powersave_p3_sleep": bool(m233_f.p5_inject_p227_powersave_p3_sleep_fault),
        "autotemp_no_tripod": bool(m233_f.p5_inject_p227_autotemp_no_tripod_fault),
        "h0_h3_drift": bool(m233_f.p5_inject_p227_h0_h3_drift),
    }
    p248_fault_dict = {
        "imagedb_slot1_vault": bool(m254_f.p5_inject_p248_imagedb_slot1_vault_fault),
        "touch_bench_tap": bool(m254_f.p5_inject_p248_touch_bench_tap_fault),
        "shoe_audio_sq_lockout": bool(m254_f.p5_inject_p248_shoe_audio_sq_lockout_fault),
        "lockop_destructive_chord": bool(m254_f.p5_inject_p248_lockop_destructive_chord_fault),
        "usb_power_no_battery": bool(m254_f.p5_inject_p248_usb_power_no_battery_fault),
        "h0_h3_drift": bool(m254_f.p5_inject_p248_h0_h3_drift),
    }
    p261_fault_dict = {
        "diffset_customkey_vault": bool(m264_f.p5_inject_p261_diffset_customkey_vault_fault),
        "autoslow_hdmi_rec_ctrl": bool(m264_f.p5_inject_p261_autoslow_hdmi_rec_ctrl_fault),
        "apsc_4k_or_bodydata_flash": bool(m264_f.p5_inject_p261_apsc_4k_or_bodydata_flash_fault),
        "end_uart_or_copyright_pii": bool(m264_f.p5_inject_p261_end_uart_or_copyright_pii_fault),
        "h0_h3_drift": bool(m264_f.p5_inject_p261_h0_h3_drift),
    }
    p275_fault_dict = {
        "file_gamma_focusmag_vault": bool(m295_f.p5_inject_p275_file_gamma_focusmag_vault_fault),
        "h0_h3_drift": bool(m295_f.p5_inject_p275_h0_h3_drift),
    }
    p279_fault_dict = {
        "usb_hdmi_protect_nw": bool(m295_f.p5_inject_p279_usb_hdmi_protect_nw_fault),
        "h0_h3_drift": bool(m295_f.p5_inject_p279_h0_h3_drift),
    }
    p284_fault_dict = {
        "pp_wb_raw_shutter": bool(m295_f.p5_inject_p284_pp_wb_raw_shutter_fault),
        "h0_h3_drift": bool(m295_f.p5_inject_p284_h0_h3_drift),
    }
    p291_fault_dict = {
        "focus_zoom_dci4k_clean": bool(m295_f.p5_inject_p291_focus_zoom_dci4k_clean_fault),
        "h0_h3_drift": bool(m295_f.p5_inject_p291_h0_h3_drift),
    }
    p302_fault_dict = {
        "lens_af_copy_evf": bool(m311_f.p5_inject_p302_lens_af_copy_evf_fault),
        "h0_h3_drift": bool(m311_f.p5_inject_p302_h0_h3_drift),
    }
    p307_fault_dict = {
        "dial_lut_ibis_rf_slot1": bool(m311_f.p5_inject_p307_dial_lut_ibis_rf_slot1_fault),
        "h0_h3_drift": bool(m311_f.p5_inject_p307_h0_h3_drift),
    }
    p316_fault_dict = {
        "bright_mon_shotmark_big6_ssh": bool(
            m324_f.p5_inject_p316_bright_mon_shotmark_big6_ssh_fault
        ),
        "h0_h3_drift": bool(m324_f.p5_inject_p316_h0_h3_drift),
    }
    p321_fault_dict = {
        "rec_media_proxy_cloud_mymenu_ftpes": bool(
            m324_f.p5_inject_p321_rec_media_proxy_cloud_mymenu_ftpes_fault
        ),
        "h0_h3_drift": bool(m324_f.p5_inject_p321_h0_h3_drift),
    }
    p329_fault_dict = {
        "shoe_audio_subject_hdmi_raw_desqueeze_varshutter": bool(
            faults.p5_inject_p329_shoe_audio_subject_hdmi_raw_desqueeze_varshutter_fault
        ),
        "h0_h3_drift": bool(faults.p5_inject_p329_h0_h3_drift),
    }
    p334_fault_dict = {
        "breathing_camid_copyright_powersave_zoom_rawcomp_usblun": bool(
            faults.p5_inject_p334_breathing_camid_copyright_powersave_zoom_rawcomp_usblun_fault
        ),
        "h0_h3_drift": bool(faults.p5_inject_p334_h0_h3_drift),
    }
    p338_fault_dict = {
        "drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_hdmi_tc": bool(
            faults.p5_inject_p338_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_hdmi_tc_fault
        ),
        "h0_h3_drift": bool(faults.p5_inject_p338_h0_h3_drift),
    }
    p341_fault_dict = {
        "area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_cec": bool(
            faults.p5_inject_p341_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_cec_fault
        ),
        "h0_h3_drift": bool(faults.p5_inject_p341_h0_h3_drift),
    }
    p342_fault_dict = {
        "peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_usbtether": bool(
            faults.p5_inject_p342_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_usbtether_fault
        ),
        "h0_h3_drift": bool(faults.p5_inject_p342_h0_h3_drift),
    }
    p345_fault_dict = {
        "audio_reclevel_outtiming_4ch_mon_touch_dormant_remote_shoot": bool(
            faults.p5_inject_p345_audio_reclevel_outtiming_4ch_mon_touch_dormant_remote_shoot_fault
        ),
        "h0_h3_drift": bool(faults.p5_inject_p345_h0_h3_drift),
    }

    p3_batches: Tuple[Tuple[str, ...], ...] = (
        (
            "realhw_fan_shutter_lut601_702",
            "realhw_big6_camset_vmcbncm1",
            "realhw_desqueeze_focusmap_shocklesswb",
            "realhw_hdmi_log1080_proxy_focusmag",
            "realhw_filesettings_shotmark_tcregen_reclamp",
            "discover_forward_compat_46plus",
        ),
        ("multilang",),
        ("realhw_peripheral", "realhw_controls_fan", "realhw_wifi_usb"),
        ("realhw_c2pa_tc_gyro", "realhw_wbi2_hibdrv"),
        ("group_b",),
        ("realhw_imx510",),
        ("realhw_cfexpress_ufu", "realhw_cxd90058_sabin"),
        ("assignable", "falsecolor", "playback", "gyroflow"),
        ("interval_ftp", "lut3d_sdi", "c2pa_mc", "hdr_hlg"),
        ("sensor",),
        ("haita",),
        ("group_a",),
        ("emount",),
        ("wbi",),
        ("prores_mishoe", "uvc_crsdk", "mxf_tally", "vp_ledwall"),
        ("realhw_hdmi_braw_wpa3", "realhw_emount_info3d"),
        ("xavc_fz100", "realhw_cp_backup", "realhw_mpr_dmm"),
        ("realhw_fx3a_xlrh1", "realhw_nouvc_dcc1_lut"),
    )

    eff_p2_fault = faults.p2_fault_inject_pillar or m324_f.p2_fault_inject_pillar

    auditors: Dict[str, Dict[str, Any]] = {}
    try:
        auditors.update(_worker_pillar_3_batch_233((p3_batches[0], use_clean_room)))
        ctx = mp.get_context("fork")
        pool_workers = min(8, max(4, mp.cpu_count() or 8))
        with ProcessPoolExecutor(max_workers=pool_workers, mp_context=ctx) as ex:
            fut_vm = ex.submit(_worker_pillar_4_295, use_clean_room)
            fut_1_off = ex.submit(
                _worker_148plus_gate_single,
                (
                    str(repo_root),
                    use_clean_room,
                    False,
                    gate_fault_dict,
                    donorless_work_root_none,
                ),
            )
            fut_1_sim = ex.submit(
                _worker_148plus_gate_single,
                (
                    str(repo_root),
                    use_clean_room,
                    True,
                    gate_fault_dict,
                    donorless_work_root_none,
                ),
            )
            fut_62p = ex.submit(
                _worker_recovery_62plus_pillar, (use_clean_room, eff_p2_fault)
            )
            fut_p136 = ex.submit(_worker_phase136, use_clean_room)
            fut_143_154_186 = ex.submit(
                _worker_phase143_154_186,
                (
                    fx6_leg_str,
                    fx3_leg_str,
                    use_clean_room,
                    p154_sim_ready,
                    p186_fault_dict,
                ),
            )
            fut_3 = [
                ex.submit(_worker_pillar_3_batch_233, (batch, use_clean_room))
                for batch in p3_batches[1:]
            ]
            fut_204 = ex.submit(
                _worker_phase204,
                (fx6_leg_str, fx3_leg_str, use_clean_room, p204_fault_dict),
            )
            fut_216 = ex.submit(
                _worker_phase216,
                (fx6_leg_str, fx3_leg_str, use_clean_room, p216_fault_dict),
            )
            fut_227 = ex.submit(
                _worker_phase227,
                (fx6_leg_str, fx3_leg_str, use_clean_room, p227_fault_dict),
            )
            fut_248 = ex.submit(
                _worker_phase248,
                (fx6_leg_str, fx3_leg_str, use_clean_room, p248_fault_dict),
            )
            fut_261 = ex.submit(
                _worker_phase261,
                (fx6_leg_str, fx3_leg_str, use_clean_room, p261_fault_dict),
            )
            fut_275_279 = ex.submit(
                _worker_phase275_279,
                (
                    fx6_leg_str,
                    fx3_leg_str,
                    use_clean_room,
                    p275_fault_dict,
                    p279_fault_dict,
                ),
            )
            fut_284_291 = ex.submit(
                _worker_phase284_291,
                (
                    fx6_leg_str,
                    fx3_leg_str,
                    use_clean_room,
                    p284_fault_dict,
                    p291_fault_dict,
                ),
            )
            fut_302_307 = ex.submit(
                _worker_phase302_307,
                (
                    fx6_leg_str,
                    fx3_leg_str,
                    use_clean_room,
                    p302_fault_dict,
                    p307_fault_dict,
                ),
            )
            fut_316_321 = ex.submit(
                _worker_phase316_321,
                (
                    fx6_leg_str,
                    fx3_leg_str,
                    use_clean_room,
                    p316_fault_dict,
                    p321_fault_dict,
                ),
            )
            fut_329_334 = ex.submit(
                _worker_phase329_334,
                (
                    fx6_opt_str,
                    fx3_opt_str,
                    use_clean_room,
                    donorless_work_root_none,
                    p329_fault_dict,
                    p334_fault_dict,
                ),
            )
            fut_338_341 = ex.submit(
                _worker_phase338_341,
                (
                    fx6_opt_str,
                    fx3_opt_str,
                    use_clean_room,
                    donorless_work_root_none,
                    p338_fault_dict,
                    p341_fault_dict,
                ),
            )
            fut_342_345 = ex.submit(
                _worker_phase342_345,
                (
                    fx6_opt_str,
                    fx3_opt_str,
                    use_clean_room,
                    donorless_work_root_none,
                    p342_fault_dict,
                    p345_fault_dict,
                ),
            )

            raw_1_off = fut_1_off.result()
            raw_1_sim = fut_1_sim.result()
            raw_62p = fut_62p.result()
            for fg in fut_3:
                auditors.update(fg.result())
            raw_vm = fut_vm.result()
            raw_p136 = fut_p136.result()
            raw_p143, raw_p154, raw_p186_off, raw_p186_sim = fut_143_154_186.result()
            raw_p204_off, raw_p204_sim = fut_204.result()
            raw_p216_off, raw_p216_sim = fut_216.result()
            raw_p227_off, raw_p227_sim = fut_227.result()
            raw_p248_off, raw_p248_sim = fut_248.result()
            raw_p261_off, raw_p261_sim = fut_261.result()
            raw_p275_off, raw_p275_sim, raw_p279_off, raw_p279_sim = fut_275_279.result()
            raw_p284_off, raw_p284_sim, raw_p291_off, raw_p291_sim = fut_284_291.result()
            raw_p302_off, raw_p302_sim, raw_p307_off, raw_p307_sim = fut_302_307.result()
            raw_p316_off, raw_p316_sim, raw_p321_off, raw_p321_sim = fut_316_321.result()
            raw_p329_off, raw_p329_sim, raw_p334_off, raw_p334_sim = fut_329_334.result()
            raw_p338_off, raw_p338_sim, raw_p341_off, raw_p341_sim = fut_338_341.result()
            raw_p342_off, raw_p342_sim, raw_p345_off, raw_p345_sim = fut_342_345.result()
            return (
                raw_1_off,
                raw_1_sim,
                raw_62p,
                auditors,
                raw_vm,
                raw_p136,
                raw_p143,
                raw_p154,
                raw_p186_off,
                raw_p186_sim,
                raw_p204_off,
                raw_p204_sim,
                raw_p216_off,
                raw_p216_sim,
                raw_p227_off,
                raw_p227_sim,
                raw_p248_off,
                raw_p248_sim,
                raw_p261_off,
                raw_p261_sim,
                raw_p275_off,
                raw_p275_sim,
                raw_p279_off,
                raw_p279_sim,
                raw_p284_off,
                raw_p284_sim,
                raw_p291_off,
                raw_p291_sim,
                raw_p302_off,
                raw_p302_sim,
                raw_p307_off,
                raw_p307_sim,
                raw_p316_off,
                raw_p316_sim,
                raw_p321_off,
                raw_p321_sim,
                raw_p329_off,
                raw_p329_sim,
                raw_p334_off,
                raw_p334_sim,
                raw_p338_off,
                raw_p338_sim,
                raw_p341_off,
                raw_p341_sim,
                raw_p342_off,
                raw_p342_sim,
                raw_p345_off,
                raw_p345_sim,
            )
    except (ValueError, RuntimeError, OSError):
        pass

    raw_1_off = _worker_148plus_gate_single(
        (str(repo_root), use_clean_room, False, gate_fault_dict, donorless_work_root_none)
    )
    raw_1_sim = _worker_148plus_gate_single(
        (str(repo_root), use_clean_room, True, gate_fault_dict, donorless_work_root_none)
    )
    raw_62p = _worker_recovery_62plus_pillar((use_clean_room, eff_p2_fault))
    auditors = {}
    for batch in p3_batches:
        auditors.update(_worker_pillar_3_batch_233((batch, use_clean_room)))
    raw_vm = _worker_pillar_4_295(use_clean_room)
    raw_p136 = _worker_phase136(use_clean_room)
    raw_p143, raw_p154, raw_p186_off, raw_p186_sim = _worker_phase143_154_186(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p154_sim_ready, p186_fault_dict)
    )
    raw_p204_off, raw_p204_sim = _worker_phase204(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p204_fault_dict)
    )
    raw_p216_off, raw_p216_sim = _worker_phase216(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p216_fault_dict)
    )
    raw_p227_off, raw_p227_sim = _worker_phase227(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p227_fault_dict)
    )
    raw_p248_off, raw_p248_sim = _worker_phase248(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p248_fault_dict)
    )
    raw_p261_off, raw_p261_sim = _worker_phase261(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p261_fault_dict)
    )
    raw_p275_off, raw_p275_sim, raw_p279_off, raw_p279_sim = _worker_phase275_279(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p275_fault_dict, p279_fault_dict)
    )
    raw_p284_off, raw_p284_sim, raw_p291_off, raw_p291_sim = _worker_phase284_291(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p284_fault_dict, p291_fault_dict)
    )
    raw_p302_off, raw_p302_sim, raw_p307_off, raw_p307_sim = _worker_phase302_307(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p302_fault_dict, p307_fault_dict)
    )
    raw_p316_off, raw_p316_sim, raw_p321_off, raw_p321_sim = _worker_phase316_321(
        (fx6_leg_str, fx3_leg_str, use_clean_room, p316_fault_dict, p321_fault_dict)
    )
    raw_p329_off, raw_p329_sim, raw_p334_off, raw_p334_sim = _worker_phase329_334(
        (
            fx6_opt_str,
            fx3_opt_str,
            use_clean_room,
            donorless_work_root_none,
            p329_fault_dict,
            p334_fault_dict,
        )
    )
    raw_p338_off, raw_p338_sim, raw_p341_off, raw_p341_sim = _worker_phase338_341(
        (
            fx6_opt_str,
            fx3_opt_str,
            use_clean_room,
            donorless_work_root_none,
            p338_fault_dict,
            p341_fault_dict,
        )
    )
    raw_p342_off, raw_p342_sim, raw_p345_off, raw_p345_sim = _worker_phase342_345(
        (
            fx6_opt_str,
            fx3_opt_str,
            use_clean_room,
            donorless_work_root_none,
            p342_fault_dict,
            p345_fault_dict,
        )
    )
    return (
        raw_1_off,
        raw_1_sim,
        raw_62p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        raw_p227_off,
        raw_p227_sim,
        raw_p248_off,
        raw_p248_sim,
        raw_p261_off,
        raw_p261_sim,
        raw_p275_off,
        raw_p275_sim,
        raw_p279_off,
        raw_p279_sim,
        raw_p284_off,
        raw_p284_sim,
        raw_p291_off,
        raw_p291_sim,
        raw_p302_off,
        raw_p302_sim,
        raw_p307_off,
        raw_p307_sim,
        raw_p316_off,
        raw_p316_sim,
        raw_p321_off,
        raw_p321_sim,
        raw_p329_off,
        raw_p329_sim,
        raw_p334_off,
        raw_p334_sim,
        raw_p338_off,
        raw_p338_sim,
        raw_p341_off,
        raw_p341_sim,
        raw_p342_off,
        raw_p342_sim,
        raw_p345_off,
        raw_p345_sim,
    )


def evaluate_realhw_milestone349_master_gate(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Optional[Path] = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Optional[Path] = DEFAULT_FX3_MODULES_DIR,
    work_root: Any = _UNSET,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    simulate_bench_dry_run: Optional[bool] = None,
    faults: Optional[RealHwMilestone349FaultInjection] = None,
    _raw_bundle_override: Optional[Tuple[Any, ...]] = None,
) -> RealHwMilestone349MasterGateReport:
    """Build & evaluate the Grand Milestone Phase 349 6-Pillar Real-Hardware Master Gate."""
    _ = simulate_bench_dry_run  # All pillars verify BOTH offline fail-closed and dry-run paths
    donorless_work_root_none = work_root is None
    if force_clean_room is not None:
        use_clean_room = bool(force_clean_room)
    elif synthetic_clean_room is not None:
        use_clean_room = bool(synthetic_clean_room)
    elif donorless_work_root_none or fx6_lib_dir is None or fx3_modules_dir is None:
        use_clean_room = True
    else:
        use_clean_room = _is_forced_clean_room(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
        ) or (
            os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower()
            in {"1", "true", "yes", "on"}
        )

    active_faults = faults or RealHwMilestone349FaultInjection()

    bundle = _raw_bundle_override or _collect_parallel_milestone349_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
        donorless_work_root_none=donorless_work_root_none,
    )
    (
        raw_1_off,
        raw_1_sim,
        raw_62p,
        auditors,
        raw_vm,
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        raw_p227_off,
        raw_p227_sim,
        raw_p248_off,
        raw_p248_sim,
        raw_p261_off,
        raw_p261_sim,
        raw_p275_off,
        raw_p275_sim,
        raw_p279_off,
        raw_p279_sim,
        raw_p284_off,
        raw_p284_sim,
        raw_p291_off,
        raw_p291_sim,
        raw_p302_off,
        raw_p302_sim,
        raw_p307_off,
        raw_p307_sim,
        raw_p316_off,
        raw_p316_sim,
        raw_p321_off,
        raw_p321_sim,
        raw_p329_off,
        raw_p329_sim,
        raw_p334_off,
        raw_p334_sim,
        raw_p338_off,
        raw_p338_sim,
        raw_p341_off,
        raw_p341_sim,
        raw_p342_off,
        raw_p342_sim,
        raw_p345_off,
        raw_p345_sim,
    ) = bundle

    p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
    p2, meta_2 = _evaluate_pillar_2(raw_62p, active_faults)
    p3, meta_3 = _evaluate_pillar_3(auditors, active_faults)
    p4, meta_4 = _evaluate_pillar_4(raw_vm, active_faults)
    p5, meta_5 = _evaluate_pillar_5(
        raw_p136,
        raw_p143,
        raw_p154,
        raw_p186_off,
        raw_p186_sim,
        raw_p204_off,
        raw_p204_sim,
        raw_p216_off,
        raw_p216_sim,
        raw_p227_off,
        raw_p227_sim,
        raw_p248_off,
        raw_p248_sim,
        raw_p261_off,
        raw_p261_sim,
        raw_p275_off,
        raw_p275_sim,
        raw_p279_off,
        raw_p279_sim,
        raw_p284_off,
        raw_p284_sim,
        raw_p291_off,
        raw_p291_sim,
        raw_p302_off,
        raw_p302_sim,
        raw_p307_off,
        raw_p307_sim,
        raw_p316_off,
        raw_p316_sim,
        raw_p321_off,
        raw_p321_sim,
        raw_p329_off,
        raw_p329_sim,
        raw_p334_off,
        raw_p334_sim,
        raw_p338_off,
        raw_p338_sim,
        raw_p341_off,
        raw_p341_sim,
        raw_p342_off,
        raw_p342_sim,
        raw_p345_off,
        raw_p345_sim,
        active_faults,
    )
    p1_meta = {
        "persistent_emmc_writes_authorized": raw_1_sim["persistent_emmc_writes_authorized"],
        "spi_nor_write_authorized": raw_1_sim["spi_nor_write_authorized"],
        "el3_payload_transmit_authorized": raw_1_sim["el3_payload_transmit_authorized"],
        "cross_model_flash_authorized": raw_1_sim.get("cross_model_flash_authorized", True),
        "simulated_ready_for_hardware_attach": raw_1_sim["overall_ready_for_hardware_attach"],
        "hardware_live_attachment_authorized": raw_1_sim["hardware_live_attachment_authorized"],
        "g71_e_nd_actuator_tx_count": raw_1_sim["g71_e_nd_actuator_tx_count"],
    }
    p6, meta_6 = _evaluate_pillar_6(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=active_faults,
        p1_meta=p1_meta,
        p2_meta=meta_2,
        p3_meta=meta_3,
        p4_meta=meta_4,
        p5_meta=meta_5,
    )

    pillars = (p1, p2, p3, p4, p5, p6)
    passed_count = sum(1 for p in pillars if p.passed)
    failed_ids = tuple(p.pillar_id for p in pillars if not p.passed)
    all_errors: List[str] = []
    for p in pillars:
        all_errors.extend(p.errors)
    all_ready = passed_count == 6 and len(failed_ids) == 0 and len(all_errors) == 0

    mode_str = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"
    new_tags = ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345")
    legacy_sim_leak_tags = (
        "p186",
        "p204",
        "p216",
        "p227",
        "p248",
        "p261",
        "p275",
        "p279",
        "p284",
        "p291",
        "p302",
        "p307",
        "p316",
        "p321",
        "p329",
        "p334",
        "p338",
        "p341",
        "p342",
        "p345",
    )
    total_raw_leaked = (
        int(raw_1_sim["raw_firmware_bytes_leaked"])
        + int(meta_2["raw_firmware_bytes_leaked"])
        + int(meta_3["raw_firmware_bytes_leaked"])
        + int(meta_4["raw_firmware_bytes_leaked"])
        + sum(int(meta_5[f"{tag}_sim_raw_firmware_bytes_leaked"]) for tag in legacy_sim_leak_tags)
        + int(meta_6["qemu_raw_firmware_bytes_leaked"])
    )
    total_usb_pkts = (
        int(raw_1_sim["usb_packets_transmitted"])
        + int(meta_2["physical_usb_packets_emitted"])
        + int(meta_5["p186_sim_usb_packets_emitted"])
        + int(meta_5["p204_sim_usb_packets_emitted"])
        + sum(
            int(meta_5[f"{tag}_sim_usb_packets_transmitted"])
            for tag in legacy_sim_leak_tags[2:]
        )
    )
    total_passive_tx = int(meta_2["passive_tx_bytes"]) + sum(
        max(0, int(meta_5[f"{tag}_sim_passive_tx_bytes_emitted"]))
        for tag in (
            "p275",
            "p279",
            "p284",
            "p291",
            "p302",
            "p307",
            "p316",
            "p321",
            "p329",
            "p334",
            "p338",
            "p341",
            "p342",
            "p345",
        )
    )
    total_phys_dev_writes = int(meta_2["physical_device_writes"]) + int(
        meta_4["physical_device_writes"]
    )
    total_end_tx = (
        max(0, int(p1.evidence["g71_e_nd_actuator_tx_count"]))
        + int(meta_3["e_nd_actuator_tx_count"])
        + int(meta_4["e_nd_actuator_tx_count"])
        + max(0, int(meta_5["p204_e_nd_actuator_tx_count"]))
        + max(0, int(meta_5["p261_e_nd_uart_bytes_transmitted"]))
        + sum(max(0, int(meta_5[f"{tag}_e_nd_actuator_tx_count"])) for tag in new_tags)
    )
    total_rf_pkts = max(0, int(meta_5["p307_wireless_rf_packets_emitted"])) + sum(
        max(0, int(meta_5[f"{tag}_wireless_rf_packets_emitted"]))
        + max(0, int(meta_5[f"{tag}_rf_packets_transmitted"]))
        for tag in new_tags
    )
    total_slot1_writes = max(0, int(meta_5["p307_slot1_data_sector_writes"])) + sum(
        max(0, int(meta_5[f"{tag}_slot1_data_sector_writes"])) for tag in new_tags
    )
    min_h0_eq_h3 = min(
        int(meta_5["h0_equals_h3_count"]),
        *(int(meta_5[f"{tag}_h0_equals_h3_count"]) for tag in legacy_sim_leak_tags),
    )
    overall_ready_attach = bool(
        raw_1_off["overall_ready_for_hardware_attach"]
        or raw_1_sim["overall_ready_for_hardware_attach"]
        or meta_5["overall_ready_for_hardware_attach"]
    )
    cross_model_flash_auth = bool(
        raw_1_off.get("cross_model_flash_authorized", False)
        or raw_1_sim.get("cross_model_flash_authorized", False)
    )

    common_fields: Dict[str, Any] = {
        "schema": REALHW_MILESTONE349_SCHEMA,
        "schema_version": REALHW_MILESTONE349_SCHEMA,
        "phase_version": PHASE_349_VERSION,
        "verification_mode": mode_str,
        "all_pillars_milestone_ready": all_ready,
        "status": STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        "o_rdonly_enforced": True,
        "cnflasha_userspace_write_blocked": bool(meta_2["cnflasha_userspace_write_blocked"]),
        "agent_auto_flash_blocked": bool(raw_1_sim["agent_auto_flash_blocked"]),
        "cross_model_flash_authorized": cross_model_flash_auth,
        "overall_ready_for_hardware_attach": overall_ready_attach,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "hardware_live_attachment_requirements": HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        "usb_packets_transmitted": total_usb_pkts,
        "physical_usb_packets_emitted": total_usb_pkts,
        "physical_device_writes": total_phys_dev_writes,
        "raw_firmware_bytes_leaked": total_raw_leaked,
        "e_nd_actuator_tx_count": total_end_tx,
        "emmc_write_count": int(meta_6["qemu_real_kernel_emmc_writes"]),
        "rf_packets_transmitted": total_rf_pkts,
        "slot1_data_sector_writes": total_slot1_writes,
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "wbi_p5_write_and_hibernation_forbidden": WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        "cp_mutation_bytes": meta_4["cp_mutation_bytes"],
        "wbi_mutation_bytes": meta_3["wbi_mutation_bytes"],
        "calibration_mutation_bytes": meta_3["calibration_mutation_bytes"],
        "usb_or_camera_operations": USB_OR_CAMERA_OPERATIONS,
        "otp_fuse_writes": meta_2["otp_fuse_writes"],
        "otp_fuse_touches": meta_2["otp_fuse_writes"],
        "rpmb_writes": meta_2["rpmb_writes"],
        "rpmb_counter_increments": meta_2["rpmb_writes"],
        "passive_tx_bytes": total_passive_tx,
        "passive_tx_bytes_emitted": total_passive_tx,
        "temp_dir_cleaned": True,
        "pillar_count": len(pillars),
        "passed_pillar_count": passed_count,
        "failed_pillar_ids": failed_ids,
        "gate148_total_gates": raw_1_sim["total_gates"],
        "gate148_offline_verified": raw_1_off["verified_gates"],
        "gate148_simulated_verified": raw_1_sim["verified_gates"],
        "gate148_all_verified": bool(raw_1_sim.get("all_n_gates_verified", False)),
        "recovery_status": meta_2["recovery_status"],
        "recovery_pillar_count": meta_2["recovery_pillar_count"],
        "recovery_pillars_passed": meta_2["recovery_pillars_passed"],
        "auditors_total": meta_3["auditor_count"],
        "auditors_passed": meta_3["passed_count"],
        "firmware_lab_auditor_count": meta_3["auditor_count"],
        "firmware_lab_auditors_passed": meta_3["passed_count"],
        "vm_stages_total": meta_4["stage_count"],
        "vm_stages_passed": meta_4["passed_count"],
        "vm_coemulation_stage_count": meta_4["stage_count"],
        "vm_coemulation_stages_passed": meta_4["passed_count"],
        "vm_physical_device_writes": meta_4["physical_device_writes"],
        "vm_raw_firmware_bytes_leaked": meta_4["raw_firmware_bytes_leaked"],
        "vm_emmc_corruptions": meta_4["emmc_corruptions"],
        "vm_wf12_00342260_hits": meta_4["wf12_00342260_hits"],
        "p136_u6_command_count": meta_5["u6_command_count"],
        "p136_u4_u5_u6_closed": meta_5["u4_u5_u6_closed"],
        "p143_sd_escape_absent_us": meta_5["eh1_observed_latency_us"],
        "p143_h0_equals_h3_count": meta_5["h0_equals_h3_count"],
        "p143_h0_h3_surface_count": meta_5["h0_h3_surface_count"],
        "p154_bench_go": meta_5["p154_bench_go"],
        "p154_usb_packets_emitted": meta_5["p154_usb_packets_emitted"],
        "p154_iokit_handles_opened": meta_5["p154_iokit_handles_opened"],
        "p186_offline_go_no_go": meta_5["p186_offline_go_no_go"],
        "p186_sim_go_no_go": meta_5["p186_sim_go_no_go"],
        "p186_sim_gates_passed": meta_5["p186_sim_gates_passed"],
        "p186_card_insert_authorized": meta_5["p186_card_insert_authorized"],
        "p186_h0_equals_h3_count": meta_5["p186_h0_equals_h3_count"],
        "p204_offline_go_no_go": meta_5["p204_offline_go_no_go"],
        "p204_sim_go_no_go": meta_5["p204_sim_go_no_go"],
        "p204_sim_groups_passed": meta_5["p204_sim_groups_passed"],
        "p204_hardware_live_attachment_authorized": meta_5[
            "p204_hardware_live_attachment_authorized"
        ],
        "p204_h0_equals_h3_count": meta_5["p204_h0_equals_h3_count"],
        "p204_e_nd_actuator_tx_count": meta_5["p204_e_nd_actuator_tx_count"],
        "p216_offline_go_no_go": meta_5["p216_offline_go_no_go"],
        "p216_sim_go_no_go": meta_5["p216_sim_go_no_go"],
        "p216_sim_checklists_passed": meta_5["p216_sim_checklists_passed"],
        "p216_hardware_live_attachment_authorized": meta_5[
            "p216_hardware_live_attachment_authorized"
        ],
        "p216_h0_equals_h3_count": meta_5["p216_h0_equals_h3_count"],
        "p227_offline_go_no_go": meta_5["p227_offline_go_no_go"],
        "p227_sim_go_no_go": meta_5["p227_sim_go_no_go"],
        "p227_sim_check_groups_passed": meta_5["p227_sim_check_groups_passed"],
        "p227_hardware_live_attachment_authorized": meta_5[
            "p227_hardware_live_attachment_authorized"
        ],
        "p227_h0_equals_h3_count": meta_5["p227_h0_equals_h3_count"],
        "p248_offline_go_no_go": meta_5["p248_offline_go_no_go"],
        "p248_sim_go_no_go": meta_5["p248_sim_go_no_go"],
        "p248_sim_check_groups_passed": meta_5["p248_sim_check_groups_passed"],
        "p248_hardware_live_attachment_authorized": meta_5[
            "p248_hardware_live_attachment_authorized"
        ],
        "p248_h0_equals_h3_count": meta_5["p248_h0_equals_h3_count"],
        "p261_offline_go_no_go": meta_5["p261_offline_go_no_go"],
        "p261_sim_go_no_go": meta_5["p261_sim_go_no_go"],
        "p261_sim_check_groups_passed": meta_5["p261_sim_check_groups_passed"],
        "p261_hardware_live_attachment_authorized": meta_5[
            "p261_hardware_live_attachment_authorized"
        ],
        "p261_h0_equals_h3_count": meta_5["p261_h0_equals_h3_count"],
        "p261_e_nd_uart_bytes_transmitted": meta_5["p261_e_nd_uart_bytes_transmitted"],
        "p275_offline_go_no_go": meta_5["p275_offline_go_no_go"],
        "p275_sim_go_no_go": meta_5["p275_sim_go_no_go"],
        "p275_sim_check_groups_passed": meta_5["p275_sim_check_groups_passed"],
        "p275_hardware_live_attachment_authorized": meta_5[
            "p275_hardware_live_attachment_authorized"
        ],
        "p275_h0_equals_h3_count": meta_5["p275_h0_equals_h3_count"],
        "p279_offline_go_no_go": meta_5["p279_offline_go_no_go"],
        "p279_sim_go_no_go": meta_5["p279_sim_go_no_go"],
        "p279_sim_check_groups_passed": meta_5["p279_sim_check_groups_passed"],
        "p279_hardware_live_attachment_authorized": meta_5[
            "p279_hardware_live_attachment_authorized"
        ],
        "p279_h0_equals_h3_count": meta_5["p279_h0_equals_h3_count"],
        "p284_offline_go_no_go": meta_5["p284_offline_go_no_go"],
        "p284_sim_go_no_go": meta_5["p284_sim_go_no_go"],
        "p284_sim_check_groups_passed": meta_5["p284_sim_check_groups_passed"],
        "p284_hardware_live_attachment_authorized": meta_5[
            "p284_hardware_live_attachment_authorized"
        ],
        "p284_h0_equals_h3_count": meta_5["p284_h0_equals_h3_count"],
        "p291_offline_go_no_go": meta_5["p291_offline_go_no_go"],
        "p291_sim_go_no_go": meta_5["p291_sim_go_no_go"],
        "p291_sim_check_groups_passed": meta_5["p291_sim_check_groups_passed"],
        "p291_hardware_live_attachment_authorized": meta_5[
            "p291_hardware_live_attachment_authorized"
        ],
        "p291_h0_equals_h3_count": meta_5["p291_h0_equals_h3_count"],
        "p302_offline_go_no_go": meta_5["p302_offline_go_no_go"],
        "p302_sim_go_no_go": meta_5["p302_sim_go_no_go"],
        "p302_sim_check_groups_passed": meta_5["p302_sim_check_groups_passed"],
        "p302_hardware_live_attachment_authorized": meta_5[
            "p302_hardware_live_attachment_authorized"
        ],
        "p302_h0_equals_h3_count": meta_5["p302_h0_equals_h3_count"],
        "p307_offline_go_no_go": meta_5["p307_offline_go_no_go"],
        "p307_sim_go_no_go": meta_5["p307_sim_go_no_go"],
        "p307_sim_check_groups_passed": meta_5["p307_sim_check_groups_passed"],
        "p307_hardware_live_attachment_authorized": meta_5[
            "p307_hardware_live_attachment_authorized"
        ],
        "p307_h0_equals_h3_count": meta_5["p307_h0_equals_h3_count"],
        "p307_wireless_rf_packets_emitted": meta_5["p307_wireless_rf_packets_emitted"],
        "p307_slot1_data_sector_writes": meta_5["p307_slot1_data_sector_writes"],
        "bench_preflight_verifier_count": int(meta_5.get("bench_preflight_verifier_count", 20)),
        "h0_equals_h3_count": min_h0_eq_h3,
        "qemu_rounds_total": meta_6["qemu_rounds_total"],
        "qemu_rounds_verified": meta_6["qemu_rounds_verified"],
        "qemu_runs_total": meta_6["qemu_runs_total"],
        "qemu_runs_verified": meta_6["qemu_runs_verified"],
        "qemu_png_receipts_total": meta_6["qemu_png_receipts_total"],
        "qemu_png_receipts_verified": meta_6["qemu_png_receipts_verified"],
        "qemu_png_max_bytes": meta_6["qemu_png_max_bytes"],
        "qemu_round_runs_by_round": meta_6["qemu_round_runs_by_round"],
        "qemu_real_kernel_nop_count": meta_6["qemu_real_kernel_nop_count"],
        "qemu_real_kernel_crashes": meta_6["qemu_real_kernel_crashes"],
        "qemu_real_kernel_emmc_writes": meta_6["qemu_real_kernel_emmc_writes"],
        "errors": tuple(all_errors),
    }
    for tag in new_tags:
        for suffix in (
            "offline_go_no_go",
            "sim_go_no_go",
            "sim_check_groups_passed",
            "hardware_live_attachment_authorized",
            "h0_equals_h3_count",
            "wireless_rf_packets_emitted",
            "rf_packets_transmitted",
            "e_nd_actuator_tx_count",
            "slot1_data_sector_writes",
        ):
            common_fields[f"{tag}_{suffix}"] = meta_5[f"{tag}_{suffix}"]

    payload_no_sha = {**common_fields, "pillars": [p.to_dict() for p in pillars]}
    digest = compute_milestone349_sha256(payload_no_sha)

    return RealHwMilestone349MasterGateReport(
        **common_fields,
        pillars=pillars,
        milestone349_sha256=digest,
    )


build_realhw_milestone349_master_gate_report = evaluate_realhw_milestone349_master_gate
evaluate_milestone_349_master_gate = evaluate_realhw_milestone349_master_gate
evaluate_milestone349_master_gate = evaluate_realhw_milestone349_master_gate


def verify_realhw_milestone349_master_gate(
    report: object,
) -> RealHwMilestone349VerifyResult:
    """Fail-closed verifier for a Grand Milestone Phase 349 Real-Hardware Master Gate JSON / report."""
    payload: Mapping[str, Any]
    if isinstance(report, RealHwMilestone349MasterGateReport):
        payload = report.to_dict()
    elif isinstance(report, Mapping):
        payload = report
    else:
        return RealHwMilestone349VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone349_sha256="",
            observed_milestone349_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("report payload is not a Mapping or RealHwMilestone349MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = (
        payload.get("schema") == REALHW_MILESTONE349_SCHEMA
        and payload.get("schema_version") == REALHW_MILESTONE349_SCHEMA
        and payload.get("phase_version") == PHASE_349_VERSION
    )
    if not schema_ok:
        errors.append(
            f"schema mismatch: schema={payload.get('schema')!r} schema_version={payload.get('schema_version')!r}"
        )

    expected_sha = compute_milestone349_sha256(payload)
    observed_sha = str(payload.get("milestone349_sha256", ""))
    digest_matched = bool(observed_sha) and observed_sha == expected_sha
    if not digest_matched:
        errors.append(
            f"milestone349_sha256 mismatch: observed={observed_sha!r} expected={expected_sha!r}"
        )

    new_tags = ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345")
    redlines_ok = (
        payload.get("o_rdonly_enforced") is True
        and payload.get("cnflasha_userspace_write_blocked") is True
        and payload.get("agent_auto_flash_blocked") is True
        and payload.get("cross_model_flash_authorized") is False
        and payload.get("overall_ready_for_hardware_attach") is False
        and payload.get("persistent_emmc_writes_authorized") is False
        and payload.get("persistent_write_release") is False
        and payload.get("spi_nor_write_authorized") is False
        and payload.get("el3_payload_transmit_authorized") is False
        and payload.get("isp_write_authorized") is False
        and payload.get("hardware_live_attachment_authorized") is False
        and payload.get("usb_packets_transmitted") == 0
        and payload.get("physical_usb_packets_emitted") == 0
        and payload.get("physical_device_writes") == 0
        and payload.get("raw_firmware_bytes_leaked") == 0
        and payload.get("e_nd_actuator_tx_count") == 0
        and payload.get("emmc_write_count") == 0
        and payload.get("rf_packets_transmitted") == 0
        and payload.get("slot1_data_sector_writes") == 0
        and payload.get("p8_cp_mutation_forbidden") is True
        and payload.get("wbi_p5_write_and_hibernation_forbidden") is True
        and payload.get("cp_mutation_bytes") == 0
        and payload.get("wbi_mutation_bytes") == 0
        and payload.get("calibration_mutation_bytes") == 0
        and payload.get("usb_or_camera_operations") == 0
        and payload.get("otp_fuse_writes") == 0
        and payload.get("otp_fuse_touches") == 0
        and payload.get("rpmb_writes") == 0
        and payload.get("rpmb_counter_increments") == 0
        and payload.get("passive_tx_bytes") == 0
        and payload.get("passive_tx_bytes_emitted") == 0
        and payload.get("p154_usb_packets_emitted") == 0
        and payload.get("p154_iokit_handles_opened") == 0
        and payload.get("p186_card_insert_authorized") is False
        and payload.get("p204_hardware_live_attachment_authorized") is False
        and payload.get("p204_e_nd_actuator_tx_count") == 0
        and payload.get("p216_hardware_live_attachment_authorized") is False
        and payload.get("p227_hardware_live_attachment_authorized") is False
        and payload.get("p248_hardware_live_attachment_authorized") is False
        and payload.get("p261_hardware_live_attachment_authorized") is False
        and payload.get("p261_e_nd_uart_bytes_transmitted") == 0
        and payload.get("p275_hardware_live_attachment_authorized") is False
        and payload.get("p279_hardware_live_attachment_authorized") is False
        and payload.get("p284_hardware_live_attachment_authorized") is False
        and payload.get("p291_hardware_live_attachment_authorized") is False
        and payload.get("p302_hardware_live_attachment_authorized") is False
        and payload.get("p307_hardware_live_attachment_authorized") is False
        and payload.get("p307_wireless_rf_packets_emitted") == 0
        and payload.get("p307_slot1_data_sector_writes") == 0
        and all(
            payload.get(f"{tag}_hardware_live_attachment_authorized") is False
            and payload.get(f"{tag}_wireless_rf_packets_emitted") == 0
            and payload.get(f"{tag}_rf_packets_transmitted") == 0
            and payload.get(f"{tag}_e_nd_actuator_tx_count") == 0
            and payload.get(f"{tag}_slot1_data_sector_writes") == 0
            for tag in new_tags
        )
    )
    if not redlines_ok:
        errors.append(
            "hard-locked zero-write / cnflasha-RO / zero-cross-model / zero-SPI-NOR / zero-EL3 / "
            "zero-USB-TX / zero-RF / zero-Slot1 / zero-leak / zero-attach redlines breached"
        )

    pillars_raw = payload.get("pillars", [])
    pillars_seq = list(pillars_raw) if isinstance(pillars_raw, (list, tuple)) else []
    seen_ids = tuple(str(p.get("pillar_id", "")) for p in pillars_seq if isinstance(p, Mapping))
    all_6_ok = (
        seen_ids == PILLAR_IDS
        and len(pillars_seq) == 6
        and all(
            isinstance(p, Mapping)
            and bool(p.get("passed"))
            and p.get("status") == STATUS_MILESTONE_READY
            for p in pillars_seq
        )
    )
    if not all_6_ok:
        errors.append(f"all_6_pillars_ok check failed (seen={seen_ids!r})")

    g_total = int(payload.get("gate148_total_gates", -1))
    g_off = int(payload.get("gate148_offline_verified", -1))
    g_sim = int(payload.get("gate148_simulated_verified", -1))
    rec_total = int(payload.get("recovery_pillar_count", -1))
    rec_passed = int(payload.get("recovery_pillars_passed", -2))
    aud_total = int(payload.get("auditors_total", -1))
    aud_passed = int(payload.get("auditors_passed", -2))
    vm_total = int(payload.get("vm_stages_total", -1))
    vm_passed = int(payload.get("vm_stages_passed", -2))
    q_rounds_tot = int(payload.get("qemu_rounds_total", -1))
    q_rounds_ver = int(payload.get("qemu_rounds_verified", -2))
    q_runs_tot = int(payload.get("qemu_runs_total", -1))
    q_runs_ver = int(payload.get("qemu_runs_verified", -2))
    q_pngs_tot = int(payload.get("qemu_png_receipts_total", -1))
    q_pngs_ver = int(payload.get("qemu_png_receipts_verified", -2))

    legacy_4group_tags = ("p248", "p261", "p275", "p279", "p284", "p291", "p302", "p307")
    counts_ok = (
        g_total >= 148
        and g_off >= g_total - 3
        and g_off == g_total - 3
        and g_sim >= 148
        and g_sim == g_total
        and payload.get("gate148_all_verified") is True
        and rec_total >= 62
        and rec_passed == rec_total
        and aud_passed >= 45
        and aud_passed == aud_total
        and vm_passed >= 75
        and vm_passed == vm_total
        and int(payload.get("vm_physical_device_writes", -1)) == 0
        and int(payload.get("vm_raw_firmware_bytes_leaked", -1)) == 0
        and int(payload.get("vm_emmc_corruptions", -1)) == 0
        and int(payload.get("vm_wf12_00342260_hits", -1)) == 0
        and int(payload.get("p136_u6_command_count", -1)) >= 19
        and payload.get("p136_u4_u5_u6_closed") is True
        and int(payload.get("p143_sd_escape_absent_us", 999)) <= 50
        and int(payload.get("p143_h0_equals_h3_count", -1)) == 16
        and int(payload.get("p143_h0_h3_surface_count", -1)) == 16
        and payload.get("p154_bench_go") is True
        and payload.get("p186_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p186_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p186_sim_gates_passed", -1)) >= 4
        and int(payload.get("p186_h0_equals_h3_count", -1)) == 16
        and payload.get("p204_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p204_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p204_sim_groups_passed", -1)) >= 3
        and int(payload.get("p204_h0_equals_h3_count", -1)) == 16
        and payload.get("p216_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p216_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p216_sim_checklists_passed", -1)) >= 5
        and int(payload.get("p216_h0_equals_h3_count", -1)) == 16
        and payload.get("p227_offline_go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        and payload.get("p227_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
        and int(payload.get("p227_sim_check_groups_passed", -1)) >= 3
        and int(payload.get("p227_h0_equals_h3_count", -1)) == 16
        and all(
            payload.get(f"{tag}_offline_go_no_go")
            == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            and payload.get(f"{tag}_sim_go_no_go") == GO_NO_GO_DRY_RUN_SIMULATED_READY
            and int(payload.get(f"{tag}_sim_check_groups_passed", -1)) >= 4
            and int(payload.get(f"{tag}_h0_equals_h3_count", -1)) == 16
            for tag in (*legacy_4group_tags, *new_tags)
        )
        and int(payload.get("bench_preflight_verifier_count", -1)) == 20
        and int(payload.get("h0_equals_h3_count", -1)) == 16
        and q_rounds_ver >= 45
        and q_rounds_ver == q_rounds_tot
        and q_runs_ver >= 135
        and q_runs_ver == q_runs_tot
        and q_pngs_ver >= 90
        and q_pngs_ver == q_pngs_tot
        and 0 < int(payload.get("qemu_png_max_bytes", -1)) < PNG_MAX_SIZE_50KIB_BYTES
        and int(payload.get("qemu_real_kernel_nop_count", -1)) == 0
        and int(payload.get("qemu_real_kernel_crashes", -1)) == 0
        and int(payload.get("qemu_real_kernel_emmc_writes", -1)) == 0
    )
    if not counts_ok:
        errors.append("milestone349 verification threshold counters mismatch")

    ready = bool(
        payload.get("all_pillars_milestone_ready")
        and payload.get("status") == STATUS_MILESTONE_READY
        and counts_ok
    )
    if not ready:
        errors.append(
            "all_pillars_milestone_ready / status is not MILESTONE_349_PREBENCH_MASTER_VERIFIED"
        )

    raw_text = json.dumps(dict(payload), sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(raw_text):
        errors.append("raw binary bytes literal detected in serialized Milestone 349 payload")

    valid = bool(
        schema_ok and digest_matched and redlines_ok and all_6_ok and ready and len(errors) == 0
    )
    return RealHwMilestone349VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone349_sha256=expected_sha,
        observed_milestone349_sha256=observed_sha,
        safety_redlines_ok=redlines_ok,
        all_6_pillars_ok=all_6_ok,
        all_pillars_milestone_ready=ready,
        errors=tuple(errors),
    )


verify_milestone_349_master_gate = verify_realhw_milestone349_master_gate


def render_milestone349_markdown(report: RealHwMilestone349MasterGateReport) -> str:
    """Render deterministic bilingual (EN / 简体中文) Markdown summary for Phase 349 Master Gate."""
    lines = [
        f"# Grand Milestone Phase 349 — Real-Hardware `ILME-FX3 Ver. 7.02` 6-Pillar Master Gate (`{report.schema}`)",
        "",
        f"> **Status / 状态**: `{report.status}` | **Mode / 模式**: `{report.verification_mode}` | "
        f"**Pillars / 六大支柱**: `{report.passed_pillar_count}/{report.pillar_count}` | "
        f"**SHA-256**: `{report.milestone349_sha256}`",
        "",
        "## Hard-Locked Safety Redlines / 硬锁定安全红线",
        f"- `overall_ready_for_hardware_attach = {report.overall_ready_for_hardware_attach}`, "
        f"`hardware_live_attachment_authorized = {report.hardware_live_attachment_authorized}`, "
        f"`cnflasha_userspace_write_blocked = {report.cnflasha_userspace_write_blocked}`, "
        f"`persistent_emmc_writes_authorized = {report.persistent_emmc_writes_authorized}`, "
        f"`cross_model_flash_authorized = {report.cross_model_flash_authorized}`, "
        f"`spi_nor_write_authorized = {report.spi_nor_write_authorized}`, "
        f"`el3_payload_transmit_authorized = {report.el3_payload_transmit_authorized}`",
        f"- `usb_packets_transmitted = {report.usb_packets_transmitted}`, "
        f"`physical_device_writes = {report.physical_device_writes}`, "
        f"`raw_firmware_bytes_leaked = {report.raw_firmware_bytes_leaked}`, "
        f"`e_nd_actuator_tx_count = {report.e_nd_actuator_tx_count}`, "
        f"`otp_fuse_touches = {report.otp_fuse_touches}`, "
        f"`rpmb_counter_increments = {report.rpmb_counter_increments}`, "
        f"`passive_tx_bytes_emitted = {report.passive_tx_bytes_emitted}`, "
        f"`rf_packets_transmitted = {report.rf_packets_transmitted}`, "
        f"`slot1_data_sector_writes = {report.slot1_data_sector_writes}`",
        "",
        "## Pillar Matrix / 六大支柱总览",
        "| Pillar | Name | Status | Summary |",
        "|---|---|---|---|",
    ]
    for p in report.pillars:
        lines.append(f"| `{p.pillar_id}` | `{p.pillar_name}` | `{p.status}` | {p.summary} |")
    lines.extend(
        [
            "",
            "## Key Grand Milestone Phase 349 Metrics / 实机总闭环核心指标",
            f"- 148+-Gate Preflight (`G01..G{report.gate148_total_gates}`): offline=`{report.gate148_offline_verified}/{report.gate148_total_gates}` (`G10..G12` locked), simulated=`{report.gate148_simulated_verified}/{report.gate148_total_gates}` (`gate148_all_verified={report.gate148_all_verified}`, `cross_model_flash={report.cross_model_flash_authorized}`)",
            f"- 62+-Pillar Recovery Master (`verify-{report.recovery_pillar_count}pillar-recovery`): `{report.recovery_pillars_passed}/{report.recovery_pillar_count}` (`{report.recovery_status}`, `cnflasha_ro={report.cnflasha_userspace_write_blocked}`)",
            f"- 45+ Firmware-Lab Auditors (`auditors_passed >= 45`): `{report.auditors_passed}/{report.auditors_total}` (`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`)",
            f"- 75+ Stage VM HIL Co-Emulation (`vm_stages_passed >= 75`): `{report.vm_stages_passed}/{report.vm_stages_total}` (`physical_device_writes={report.vm_physical_device_writes}`, `emmc_corruptions={report.vm_emmc_corruptions}`)",
            f"- Icosuple (20/20) Bench Readiness Preflights (`Ph186..Ph345`): `Ph186={report.p186_offline_go_no_go}/{report.p186_sim_go_no_go}`, `Ph204={report.p204_offline_go_no_go}/{report.p204_sim_go_no_go}`, `Ph216={report.p216_offline_go_no_go}/{report.p216_sim_go_no_go}`, `Ph227={report.p227_offline_go_no_go}/{report.p227_sim_go_no_go}`, `Ph248={report.p248_offline_go_no_go}/{report.p248_sim_go_no_go}`, `Ph261={report.p261_offline_go_no_go}/{report.p261_sim_go_no_go}`, `Ph275={report.p275_offline_go_no_go}/{report.p275_sim_go_no_go}`, `Ph279={report.p279_offline_go_no_go}/{report.p279_sim_go_no_go}`, `Ph284={report.p284_offline_go_no_go}/{report.p284_sim_go_no_go}`, `Ph291={report.p291_offline_go_no_go}/{report.p291_sim_go_no_go}`, `Ph302={report.p302_offline_go_no_go}/{report.p302_sim_go_no_go}`, `Ph307={report.p307_offline_go_no_go}/{report.p307_sim_go_no_go}`, `Ph316={report.p316_offline_go_no_go}/{report.p316_sim_go_no_go}`, `Ph321={report.p321_offline_go_no_go}/{report.p321_sim_go_no_go}`, `Ph329={report.p329_offline_go_no_go}/{report.p329_sim_go_no_go}`, `Ph334={report.p334_offline_go_no_go}/{report.p334_sim_go_no_go}`, `Ph338={report.p338_offline_go_no_go}/{report.p338_sim_go_no_go}`, `Ph341={report.p341_offline_go_no_go}/{report.p341_sim_go_no_go}`, `Ph342={report.p342_offline_go_no_go}/{report.p342_sim_go_no_go}`, `Ph345={report.p345_offline_go_no_go}/{report.p345_sim_go_no_go}` (`H0==H3={report.h0_equals_h3_count}/16`)",
            f"- Live FX3 `7.02` (`4.9.337-scel+`) QEMU Receipts (`Rounds 28..72+`): `{report.qemu_rounds_verified}/{report.qemu_rounds_total}` rounds (`{report.qemu_runs_verified}/{report.qemu_runs_total}` sub-runs, `PNGs={report.qemu_png_receipts_verified}/{report.qemu_png_receipts_total}` max=`{report.qemu_png_max_bytes}B < 50KiB`), `nop={report.qemu_real_kernel_nop_count}`, `crashes={report.qemu_real_kernel_crashes}`, `emmc_writes={report.qemu_real_kernel_emmc_writes}`",
            "",
        ]
    )
    return "\n".join(lines)


def verify_milestone_349_cli(
    argv: Optional[Sequence[str]] = None,
    *,
    repo_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    simulate_bench_dry_run: Optional[bool] = None,
    json_output: bool = False,
    markdown_out: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> int:
    """Execute `verify-milestone-349` CLI supporting `--clean-room`/`--force-clean-room`/`--simulate-bench-dry-run`/`--json`/`--out`."""
    if argv is not None:
        parser = argparse.ArgumentParser(prog="verify-milestone-349")
        parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
        parser.add_argument("--fx6-lib-dir", type=Path, default=DEFAULT_FX6_DONOR_LIB_DIR)
        parser.add_argument("--fx3-modules-dir", type=Path, default=DEFAULT_FX3_MODULES_DIR)
        parser.add_argument(
            "--force-clean-room",
            "--clean-room",
            dest="force_clean_room",
            action="store_true",
        )
        parser.add_argument(
            "--simulate-bench-dry-run",
            "--simulate-ready-bench",
            dest="simulate_bench_dry_run",
            action="store_true",
        )
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--output", "--out", dest="output", type=Path, default=None)
        parser.add_argument("--markdown-out", type=Path, default=None)
        ns = parser.parse_args(list(argv))
        repo_root = ns.repo_root
        fx6_lib_dir = ns.fx6_lib_dir
        fx3_modules_dir = ns.fx3_modules_dir
        force_clean_room = True if ns.force_clean_room else None
        simulate_bench_dry_run = bool(ns.simulate_bench_dry_run)
        json_output = bool(ns.json)
        output_path = ns.output
        markdown_out = ns.markdown_out

    rep = evaluate_realhw_milestone349_master_gate(
        repo_root=repo_root or DEFAULT_REPO_ROOT,
        fx6_lib_dir=fx6_lib_dir if fx6_lib_dir is not None else DEFAULT_FX6_DONOR_LIB_DIR,
        fx3_modules_dir=fx3_modules_dir if fx3_modules_dir is not None else DEFAULT_FX3_MODULES_DIR,
        force_clean_room=force_clean_room,
        simulate_bench_dry_run=simulate_bench_dry_run,
    )
    rendered = rep.to_deterministic_json(indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_milestone349_markdown(rep), encoding="utf-8")
    v_res = verify_realhw_milestone349_master_gate(rep.to_dict())
    ok = rep.all_pillars_milestone_ready and v_res.valid
    try:
        if json_output:
            sys.stdout.write(rendered)
        else:
            summary = (
                f"status={'OK' if ok else 'FAILED'} "
                f"schema={rep.schema} "
                f"mode={rep.verification_mode} "
                f"pillars={rep.passed_pillar_count}/{rep.pillar_count} "
                f"gate148={rep.gate148_offline_verified}/{rep.gate148_simulated_verified} "
                f"recovery={rep.recovery_pillars_passed}/{rep.recovery_pillar_count} "
                f"cnflasha_ro={rep.cnflasha_userspace_write_blocked} "
                f"otp={rep.otp_fuse_touches} "
                f"rpmb={rep.rpmb_counter_increments} "
                f"passive_tx={rep.passive_tx_bytes_emitted} "
                f"auditors={rep.auditors_passed}/{rep.auditors_total} "
                f"vm_stages={rep.vm_stages_passed}/{rep.vm_stages_total} "
                f"preflights=20/20(p329={rep.p329_sim_go_no_go},p345={rep.p345_sim_go_no_go}) "
                f"h0_eq_h3={rep.h0_equals_h3_count}/16 "
                f"e_nd_tx={rep.e_nd_actuator_tx_count} "
                f"rf_pkts={rep.rf_packets_transmitted} "
                f"slot1_writes={rep.slot1_data_sector_writes} "
                f"qemu={rep.qemu_rounds_verified}/{rep.qemu_rounds_total}({rep.qemu_runs_verified}/{rep.qemu_runs_total}) "
                f"pngs={rep.qemu_png_receipts_verified}/{rep.qemu_png_receipts_total}(max={rep.qemu_png_max_bytes}B) "
                f"ready_attach={rep.overall_ready_for_hardware_attach} "
                f"live_attach_auth={rep.hardware_live_attachment_authorized} "
                f"emmc_writes_auth={rep.persistent_emmc_writes_authorized} "
                f"cross_model_flash_auth={rep.cross_model_flash_authorized} "
                f"spi_nor_auth={rep.spi_nor_write_authorized} "
                f"el3_tx_auth={rep.el3_payload_transmit_authorized} "
                f"usb_tx={rep.usb_packets_transmitted} "
                f"leaked={rep.raw_firmware_bytes_leaked} "
                f"milestone349_sha256={rep.milestone349_sha256[:16]}...\n"
            )
            sys.stdout.write(summary)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 0 if ok else 1


__all__ = [
    "AGENT_AUTO_FLASH_BLOCKED",
    "CALIBRATION_MUTATION_BYTES",
    "CNFLASHA_USERSPACE_WRITE_BLOCKED",
    "CP_MUTATION_BYTES",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "DEFAULT_REPO_ROOT",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "EMMC_WRITE_COUNT",
    "E_ND_ACTUATOR_TX_COUNT",
    "FIRMWARE_LAB_45_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "ISP_WRITE_AUTHORIZED",
    "MILESTONE349_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P8_CP_MUTATION_FORBIDDEN",
    "P349_BASELINE_PNG_MAX_OBSERVED_BYTES",
    "P349_PHYSICAL_DEVICE_WRITES",
    "P349_PILLAR_IDS",
    "P349_PILLAR_SPECS",
    "P349_PNG_MAX_SIZE_BYTES",
    "P349_RAW_FIRMWARE_BYTES_LEAKED",
    "P349_SCHEMA",
    "P349_STATUS_FAIL_CLOSED",
    "P349_STATUS_MILESTONE_READY",
    "P349_VERSION",
    "PASSIVE_TX_BYTES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_349_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "PNG_MAGIC_BYTES",
    "PNG_MAX_SIZE_50KIB_BYTES",
    "PNG_MAX_SIZE_BYTES",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_MILESTONE349_SCHEMA",
    "RECOVERY_62_PILLAR_IDS",
    "ROUND28_TO_72_PNG_RECEIPTS",
    "ROUND28_TO_72_SPECS",
    "ROUND66_EXPECTED_SCHEMA",
    "ROUND66_SUMMARY_RELPATH",
    "ROUND67_EXPECTED_SCHEMA",
    "ROUND67_SUMMARY_RELPATH",
    "ROUND68_EXPECTED_SCHEMA",
    "ROUND68_SUMMARY_RELPATH",
    "ROUND69_EXPECTED_SCHEMA",
    "ROUND69_SUMMARY_RELPATH",
    "ROUND70_EXPECTED_SCHEMA",
    "ROUND70_SUMMARY_RELPATH",
    "ROUND71_EXPECTED_SCHEMA",
    "ROUND71_SUMMARY_RELPATH",
    "ROUND72_EXPECTED_SCHEMA",
    "ROUND72_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "RPMB_WRITES",
    "SCHEMA_VERSION",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "USB_PACKETS_TRANSMITTED",
    "VM_COEMULATION_75_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone349PillarResult",
    "RealHwMilestone349FaultInjection",
    "RealHwMilestone349MasterGateReport",
    "RealHwMilestone349VerifyResult",
    "build_realhw_milestone349_master_gate_report",
    "compute_milestone349_sha256",
    "evaluate_milestone349_master_gate",
    "evaluate_milestone_349_master_gate",
    "evaluate_realhw_milestone349_master_gate",
    "render_milestone349_markdown",
    "verify_milestone_349_cli",
    "verify_milestone_349_master_gate",
    "verify_realhw_milestone349_master_gate",
]
