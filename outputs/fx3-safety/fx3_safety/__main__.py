"""CLI entrypoint for `python3 -m fx3_safety`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .boot_contracts import (
    parse_bk4_record,
    parse_fa0080_table,
    verify_bksb_ldr_bkup,
    verify_boot_screen_enum_contract,
    verify_sector0_partition_table,
)
from .brick_classifier import classify_brick_state, generate_failsafe_init2_overlay_hook
from .dewpoint_tec_usbc_and_24gate_guard import evaluate_24gate_preflight
from .exfat_media_integrity_guard import (
    MEDIA_TYPE_SDXC,
    SLOT_A,
    SLOT_B,
    MediaSlotConfig,
    build_synthetic_exfat_boot_region,
    evaluate_exfat_media_integrity_guard,
)
from .hdmi_aoc_5v_cfexpress_and_36gate_guard import evaluate_36gate_preflight
from .intake_occlusion_tripod_and_26gate_guard import evaluate_26gate_preflight
from .master_16gate_preflight import DEFAULT_REPO_ROOT, evaluate_16_master_safety_gates
from .monsoon_mishoe_cagetwist_and_40gate_guard import evaluate_40gate_preflight
from .phantom48v_gimbal_and_22gate_guard import evaluate_22gate_preflight
from .pl_cantilever_dummybatt_and_32gate_guard import evaluate_32gate_preflight
from .preflight import audit_tier0_worker_syscall_trace, evaluate_12_safety_gates, verify_tier0_backup_manifest
from .realhw_jiritsu_cnflasha_and_44gate_guard import (
    evaluate_44gate_preflight,
    evaluate_g43_jiritsu_service,
    evaluate_g44_cnflasha_dualboot,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import (
    evaluate_48gate_preflight,
    evaluate_g47_pnflasha_mtdro_vault,
    evaluate_g48_rfnvs_fan_power_guard,
)
from .realhw_service0336_mpr_ibis_and_46gate_guard import (
    evaluate_46gate_preflight,
    evaluate_g45_service_0336_canary,
    evaluate_g46_mpr_ibis_p18_guard,
)
from .realhw_uart1v8_imx510_cal_and_50gate_guard import (
    evaluate_50gate_preflight,
    evaluate_g49_uart1v8_isp,
    evaluate_g50_imx510_sensor_cal,
)
from .realhw_cfexpress_ufu_el3_and_52gate_guard import (
    evaluate_52gate_preflight,
    evaluate_g51_cfexpress_ufu,
    evaluate_g52_5tier_el3_guard,
)
from .realhw_cxd90058_sabin_seal_and_54gate_guard import (
    evaluate_54gate_preflight,
    evaluate_g53_cxd90058_sabin,
    evaluate_g54_factory_seal,
)
from .realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard import (
    evaluate_72gate_preflight,
    evaluate_g71_big6_noend_camset_slot1_guard,
    evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard,
)
from .realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard import (
    evaluate_74gate_preflight,
    evaluate_g73_desqueeze_focusmap_guard,
    evaluate_g74_simult_autoswitch_shocklesswb_guard,
)
from .realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard import (
    evaluate_76gate_preflight,
    evaluate_g75_hdmi_log1080_hdmionly_guard,
    evaluate_g76_proxy_focusmag_brightmon_guard,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    evaluate_78gate_preflight,
    evaluate_g77_filesettings_shotmark_guard,
    evaluate_g78_tcregen_reclamp_guard,
)
from .realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard import (
    evaluate_80gate_preflight,
    evaluate_g79_pixelmap_reboot_cnflasha_guard,
    evaluate_g80_ntscpal_gammaassist_displaylut_guard,
)
from .realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard import (
    evaluate_82gate_preflight,
    evaluate_g81_steadyshot_ciz_guard,
    evaluate_g82_powersave_autotemp_guard,
)
from .realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard import (
    evaluate_84gate_preflight,
    evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard,
    evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard,
)
from .realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard import (
    evaluate_86gate_preflight,
    evaluate_g85_silent_autopixelmap_no_pwrshutter_guard,
    evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard,
)
from .realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard import (
    evaluate_88gate_preflight,
    evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard,
    evaluate_g88_monitor_flip_af_sens_and_interval_guard,
)
from .realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard import (
    evaluate_90gate_preflight,
    evaluate_g89_emphasized_rec_and_grid_hdmi_guard,
    evaluate_g90_touch_op_reset_and_sunny_weather_guard,
)
from .realhw_shoe_audio_wind_saveload_c3_and_92gate_guard import (
    evaluate_92gate_preflight,
    evaluate_g91_shoe_audio_and_wind_noise_guard,
    evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard,
)
from .realhw_framing_usbpower_lun_antiflicker_and_94gate_guard import (
    evaluate_94gate_preflight,
    evaluate_g93_framing_and_antiflicker_guard,
    evaluate_g94_usb_power_and_lun_persistence_guard,
)
from .realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard import (
    evaluate_96gate_preflight,
    evaluate_g95_lock_operation_parts_and_chord_guard,
    evaluate_g96_audio_timing_signals_and_exp_step_guard,
)
from .realhw_display_quality_bt_rmt_mymenu_and_98gate_guard import (
    evaluate_98gate_preflight,
    evaluate_g97_display_quality_and_bt_rmt_guard,
    evaluate_g98_mymenu_and_camset_firewall_guard,
)
from .realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard import (
    evaluate_100gate_preflight,
    evaluate_g99_diff_set_still_mv_and_shutter_angle_guard,
    evaluate_g100_custom_key_dial_and_remain_shoot_guard,
)
from .realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard import (
    evaluate_102gate_preflight,
    evaluate_g101_auto_slow_shutter_and_breathing_comp_guard,
    evaluate_g102_hdmi_reccontrol_tcout_4chaudio_guard,
)
from .realhw_apsc_s35_face_eye_af_version_and_104gate_guard import (
    evaluate_104gate_preflight,
    evaluate_g103_apsc_s35_and_face_eye_af_guard,
    evaluate_g104_version_readonly_and_bodydata_flash_block_guard,
)
from .realhw_release_wo_card_audio_meter_copyright_and_106gate_guard import (
    evaluate_106gate_preflight,
    evaluate_g105_release_wo_card_lens_and_v702_audio_disp_guard,
    evaluate_g106_copyright_info_46char_still_exif_and_pii_hygiene_guard,
)
from .realhw_file_settings_gamma_assist_tcub_and_108gate_guard import (
    evaluate_108gate_preflight,
    evaluate_g107_movie_file_settings_still_dsc_and_slot1_vault_guard,
    evaluate_g108_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard,
)
from .realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard import (
    evaluate_110gate_preflight,
    evaluate_g109_focus_mag_peaking_af_illuminator_guard,
    evaluate_g110_area_datetime_videolight_hdmires_guard,
)
from .realhw_power_save_monitor_language_volume_delete_and_112gate_guard import (
    evaluate_112gate_preflight,
    evaluate_g111_power_save_monitor_and_language_guard,
    evaluate_g112_volume_4chmon_delete_confirm_guard,
)
from .realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard import (
    evaluate_114gate_preflight,
    evaluate_g113_usb_mode_and_hdmi_info_guard,
    evaluate_g114_protect_and_network_reset_guard,
)
from .realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard import (
    evaluate_116gate_preflight,
    evaluate_g115_pp_scinetone_creativelook_dro_guard,
    evaluate_g116_wb_cineei_and_metering_guard,
)
from .realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard import (
    evaluate_118gate_preflight,
    evaluate_g117_raw_heif_colorspace_guard,
    evaluate_g118_shutter_type_nr_drive_guard,
)
from .realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard import (
    evaluate_120gate_preflight,
    evaluate_g119_focus_area_and_zoom_lever_guard,
    evaluate_g120_iso_minss_and_flash_guard,
)
from .realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard import (
    evaluate_122gate_preflight,
    evaluate_g121_dci4k_and_aspect_ratio_guard,
    evaluate_g122_custom_hold_camset_photo_capture_guard,
)
from .realhw_c2pa_tc_gyro_and_56gate_guard import (
    evaluate_56gate_preflight,
    evaluate_g55_c2pa_cert,
    evaluate_g56_tc_gyro_meta,
)
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    evaluate_58gate_preflight,
    evaluate_g57_dualmedia_vault,
    evaluate_g58_bench_interlock,
)
from .realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard import (
    evaluate_60gate_preflight,
    evaluate_g59_ssboot_wbi2_guard,
    evaluate_g60_slot1_ufu_c2pa_guard,
)
from .realhw_emount_info3d_hdmi_braw_and_62gate_guard import (
    evaluate_62gate_preflight,
    evaluate_g61_emount_breathing_guard,
    evaluate_g62_hdmi_raw_guard,
)
from .realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard import (
    evaluate_70gate_preflight,
    evaluate_g69_fan_pwm_thermal_guard,
    evaluate_g70_lut_split_shutter_angle_guard,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    evaluate_64gate_preflight,
    evaluate_g63_fx3a_branch_firewall,
    evaluate_g64_xlrh1_mishoe_guard,
)
from .realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard import (
    evaluate_66gate_preflight,
    evaluate_g65_nouvc_dcc1_pd_guard,
    evaluate_g66_lut_path_cineei_bt_guard,
)
from .realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard import (
    evaluate_68gate_preflight,
    evaluate_g67_usblan_rtmp_guard,
    evaluate_g68_clipflag_anamorphic_guard,
)
from .rig_groundloop_lensrail_and_20gate_guard import evaluate_20gate_preflight
from .saltspray_haze_followfocus_and_34gate_guard import evaluate_34gate_preflight
from .sensor_curtain_subzero_and_28gate_guard import evaluate_28gate_preflight
from .thermal_pwm_and_power_guard import evaluate_thermal_pwm_and_power_guard
from .usblan_ptpip_and_18gate_preflight import evaluate_18_master_safety_gates
from .usbpd_trigger_multiterminal_and_38gate_guard import evaluate_38gate_preflight
from .vp_strobe_vehiclerig_ibis_and_42gate_guard import evaluate_42gate_preflight
from .wireless_tx_emi_endurance_and_30gate_guard import evaluate_30gate_preflight


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx3_safety",
        description="Sony FX3 Flash Safety, Boot Contract & Brick Recovery Diagnostic CLI (v2.0)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 1. evaluate-preflight
    p_pre = sub.add_parser("evaluate-preflight", help="Evaluate the 12 Pre-Flash & Recovery Safety Gates")
    p_pre.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_pre.add_argument("--out", type=Path, help="Optional JSON file path to write readiness report")

    # 2. diagnose-brick
    p_diag = sub.add_parser("diagnose-brick", help="Classify an FX3 brick symptom and output recovery protocol")
    p_diag.add_argument(
        "--led",
        default="normal",
        choices=[
            "normal",
            "red_steady",
            "red_5L_6S",
            "red_7L_7S",
            "red_6L",
            "red_5_blinks",
            "red_7_blinks",
            "no_led_dead",
        ],
    )
    p_diag.add_argument(
        "--usb",
        default="none",
        choices=[
            "054C:0DA1",
            "054C:0DA3",
            "054C:0994",
            "054C:0336",
            "054C:03E2",
            "054C:096F",
            "18D1:4EE0",
            "none",
        ],
    )
    p_diag.add_argument(
        "--display",
        default="black",
        choices=["normal_ui", "update_progress_or_error", "black", "boot_logo_freeze"],
    )
    p_diag.add_argument(
        "--regions",
        nargs="*",
        default=[],
        help="Affected regions: p5_wbi p15_usr p7_rootfs p3_system p2_backup p1_updater sector0 spi_nor",
    )
    p_diag.add_argument("--updater-armed", action="store_true", help="/setting/updater/mode* was pre-armed")
    p_diag.add_argument("--oneshot-overlay", action="store_true", help="4-Layer one-shot overlay was used")
    p_diag.add_argument("--has-backup", action="store_true", help="Verified same-body Tier-0 backup exists")

    # 3. verify-sector0
    p_sec0 = sub.add_parser("verify-sector0", help="Verify a 512-byte Sony eMMC Sector 0 ('8246' '2.00') file")
    p_sec0.add_argument("--input", type=Path, required=True, help="Path to 512-byte sector0.bin")

    # 4. verify-backup-manifest
    p_man = sub.add_parser("verify-backup-manifest", help="Verify a Tier-0 per-body backup manifest JSON")
    p_man.add_argument("--manifest", type=Path, required=True, help="Path to backup manifest JSON")

    # 5. generate-failsafe-hook
    p_hook = sub.add_parser(
        "generate-failsafe-hook",
        help="Generate the 4-Layer Fail-Safe Overlay & Watchdog hook for p7:/sbin/init2",
    )
    p_hook.add_argument("--payload", default="/log/mod/appFw.so")
    p_hook.add_argument("--target", default="/usr/lib/appFw.so")
    p_hook.add_argument("--timeout", type=int, default=45)

    # 6. audit-worker-trace
    p_trace = sub.add_parser(
        "audit-worker-trace",
        help="Audit a Tier-0 backup worker Linux AArch64 syscall trace JSON",
    )
    p_trace.add_argument("--trace", type=Path, required=True, help="Path to syscall trace JSON list")

    # 7. verify-thermal-power-guard
    p_therm = sub.add_parser(
        "verify-thermal-power-guard",
        help="Run Phase 44 FX3 Fan PWM Thermal Envelope, NP-FZ100 vs BP-U & USB-PD Guard",
    )
    p_therm.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_therm.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 8. verify-16-gates
    p_16 = sub.add_parser(
        "verify-16-gates",
        help="Run Phase 50 16-Gate Master Safety Preflight Engine (G01..G16)",
    )
    p_16.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_16.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_16.add_argument(
        "--dry-run-tier0",
        action="store_true",
        help="Supply synthetic dry-run Tier-0 inputs so G01..G16 can be exercised offline",
    )
    p_16.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 9. verify-media-guard
    p_media = sub.add_parser(
        "verify-media-guard",
        help="Run Phase 57 Non-Journaled exFAT BootChecksum, Sony Media Tree & Dual CFexpress Firewall",
    )
    p_media.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_media.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_media.add_argument("--slot-a-root", type=Path, help="Optional Slot A mounted directory to scan read-only")
    p_media.add_argument("--slot-b-root", type=Path, help="Optional Slot B mounted directory to scan read-only")
    p_media.add_argument("--slot-a-image", type=Path, help="Optional Slot A exFAT image/VBR file (O_RDONLY)")
    p_media.add_argument("--slot-b-image", type=Path, help="Optional Slot B exFAT image/VBR file (O_RDONLY)")
    p_media.add_argument("--p1-image", type=Path, help="Optional p1 FAT12/FAT16 image/VBR file (O_RDONLY)")

    # 10. verify-18-gates
    p_18 = sub.add_parser(
        "verify-18-gates",
        help="Run Phase 61 18-Gate Master Safety Preflight Engine (G01..G18)",
    )
    p_18.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_18.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_18.add_argument(
        "--dry-run-tier0",
        action="store_true",
        help="Supply synthetic dry-run Tier-0 inputs so G01..G18 can be exercised offline",
    )
    p_18.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 11. verify-20-gates
    p_20 = sub.add_parser(
        "verify-20-gates",
        help="Run Phase 69 20-Gate Master Safety Preflight Engine (G01..G20)",
    )
    p_20.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_20.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_20.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G20 gates can be rehearsed offline",
    )
    p_20.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 12. verify-22-gates
    p_22 = sub.add_parser(
        "verify-22-gates",
        help="Run Phase 77 22-Gate Master Safety Preflight Engine (G01..G22)",
    )
    p_22.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_22.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_22.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G22 gates can be rehearsed offline",
    )
    p_22.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 13. verify-24-gates
    p_24 = sub.add_parser(
        "verify-24-gates",
        help="Run Phase 84 24-Gate Master Safety Preflight Engine (G01..G24)",
    )
    p_24.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_24.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_24.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G24 gates can be rehearsed offline",
    )
    p_24.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 14. verify-26-gates
    p_26 = sub.add_parser(
        "verify-26-gates",
        help="Run Phase 92 26-Gate Master Safety Preflight Engine (G01..G26)",
    )
    p_26.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_26.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_26.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G26 gates can be rehearsed offline",
    )
    p_26.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 15. verify-28-gates
    p_28 = sub.add_parser(
        "verify-28-gates",
        help="Run Phase 97 28-Gate Master Safety Preflight Engine (G01..G28)",
    )
    p_28.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_28.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_28.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G28 gates can be rehearsed offline",
    )
    p_28.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 16. verify-30-gates
    p_30 = sub.add_parser(
        "verify-30-gates",
        help="Run Milestone Phase 100 30-Gate Master Safety Preflight Engine (G01..G30)",
    )
    p_30.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_30.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_30.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G30 gates can be rehearsed offline",
    )
    p_30.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 17. verify-32-gates
    p_32 = sub.add_parser(
        "verify-32-gates",
        help="Run Phase 104 32-Gate Master Safety Preflight Engine (G01..G32)",
    )
    p_32.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_32.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_32.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G32 gates can be rehearsed offline",
    )
    p_32.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 18. verify-34-gates
    p_34 = sub.add_parser(
        "verify-34-gates",
        help="Run Phase 108 34-Gate Master Safety Preflight Engine (G01..G34)",
    )
    p_34.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_34.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_34.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G34 gates can be rehearsed offline",
    )
    p_34.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 19. verify-36-gates
    p_36 = sub.add_parser(
        "verify-36-gates",
        help="Run Phase 115 36-Gate Master Safety Preflight Engine (G01..G36)",
    )
    p_36.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_36.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_36.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G36 gates can be rehearsed offline",
    )
    p_36.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 20. verify-38-gates
    p_38 = sub.add_parser(
        "verify-38-gates",
        help="Run Milestone Phase 120 38-Gate Master Safety Preflight Engine (G01..G38)",
    )
    p_38.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_38.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_38.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G38 gates can be rehearsed offline",
    )
    p_38.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 21. verify-40-gates
    p_40 = sub.add_parser(
        "verify-40-gates",
        help="Run Milestone Phase 125 40-Gate Master Safety Preflight Engine (G01..G40)",
    )
    p_40.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_40.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_40.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G40 gates can be rehearsed offline",
    )
    p_40.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 22. verify-42-gates
    p_42 = sub.add_parser(
        "verify-42-gates",
        help="Run Phase 131 42-Gate Master Safety Preflight Engine (G01..G42)",
    )
    p_42.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_42.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_42.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G42 gates can be rehearsed offline",
    )
    p_42.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 23. verify-g43-jiritsu-service
    p_g43 = sub.add_parser(
        "verify-g43-jiritsu-service",
        help="Run Phase 142 Gate G43 (AdjustControl 0x40 / libJiritsu.so Electrical, /tmp/jbusy & p6 25 MiB Quota Guard)",
    )
    p_g43.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g43.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g43.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 24. verify-g44-cnflasha-dualboot
    p_g44 = sub.add_parser(
        "verify-g44-cnflasha-dualboot",
        help="Run Phase 142 Gate G44 (/dev/cnflasha15 SPACC Cipher-Boundary, Tier-0 Receipt, SD Escape & p1/p3 Mutex)",
    )
    p_g44.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g44.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g44.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 25. verify-44-gates
    p_44 = sub.add_parser(
        "verify-44-gates",
        help="Run Phase 142 44-Gate Master Safety Preflight Engine (G01..G44)",
    )
    p_44.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_44.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_44.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G44 gates can be rehearsed offline",
    )
    p_44.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 26. verify-g45-service-0336-canary
    p_g45 = sub.add_parser(
        "verify-g45-service-0336-canary",
        help="Run Phase 148 Gate G45 (054C:0336 op=0xFF RAM Canary, Single-Flight SenserPacket, 64KiB ELF Self-Unlink & MSC Return Watchdog)",
    )
    p_g45.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g45.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g45.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 27. verify-g46-mpr-ibis-p18-guard
    p_g46 = sub.add_parser(
        "verify-g46-mpr-ibis-p18-guard",
        help="Run Phase 148 Gate G46 (Stage-B p18:/lens MS_RDONLY Lock, 5-Axis IBIS Safe Coil Park & Stock DmmCfg.bin 20-Pool Guard)",
    )
    p_g46.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g46.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g46.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 28. verify-46-gates
    p_46 = sub.add_parser(
        "verify-46-gates",
        help="Run Phase 148 46-Gate Master Safety Preflight Engine (G01..G46)",
    )
    p_46.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_46.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_46.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G46 gates can be rehearsed offline",
    )
    p_46.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 29. verify-g47-pnflasha-mtdro-vault
    p_g47 = sub.add_parser(
        "verify-g47-pnflasha-mtdro-vault",
        help="Run Phase 153 Gate G47 (Dual-Layer pnflasha/cnflasha Cipher-Pairing, Per-Camera CID Binding & /dev/mtd0ro SPI-NOR Guard)",
    )
    p_g47.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g47.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g47.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 30. verify-g48-rfnvs-fan-power-guard
    p_g48 = sub.add_parser(
        "verify-g48-rfnvs-fan-power-guard",
        help="Run Phase 153 Gate G48 (p12/p13 RF NVS Lock, USB MSC 054C:0DA1, Off-in-Rec >=65C 100%% PWM & <=6100mV EncWfiStop Guard)",
    )
    p_g48.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g48.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g48.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 31. verify-48-gates
    p_48 = sub.add_parser(
        "verify-48-gates",
        help="Run Phase 153 48-Gate Master Safety Preflight Engine (G01..G48)",
    )
    p_48.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_48.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_48.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G48 gates can be rehearsed offline",
    )
    p_48.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 32. verify-g49-uart1v8-isp
    p_g49 = sub.add_parser(
        "verify-g49-uart1v8-isp",
        help="Run Phase 158 Gate G49 (1.8V ttyAMA0 460800 8N1 Passive RX, VMC-BNCM1 Contention & 1.8V eMMC ISP Guard)",
    )
    p_g49.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g49.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g49.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 33. verify-g50-imx510-sensor-cal
    p_g50 = sub.add_parser(
        "verify-g50-imx510-sensor-cal",
        help="Run Phase 158 Gate G50 (IMX510 p2/p18 Sensor Cal NVS Lock, Dual-Base ISO 800/12800 & .cube 3D MLUT Guard)",
    )
    p_g50.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g50.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g50.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 34. verify-50-gates
    p_50 = sub.add_parser(
        "verify-50-gates",
        help="Run Phase 158 50-Gate Master Safety Preflight Engine (G01..G50)",
    )
    p_50.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_50.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_50.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G50 gates can be rehearsed offline",
    )
    p_50.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 35. verify-g51-cfexpress-ufu
    p_g51 = sub.add_parser(
        "verify-g51-cfexpress-ufu",
        help="Run Phase 161 Gate G51 (Dual-Slot CFexpress Type A / SDXC V90 Bitrate, Card-Door GPIO Flush & BODYDATA.DAT UFU Guard)",
    )
    p_g51.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g51.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g51.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 36. verify-g52-5tier-el3-guard
    p_g52 = sub.add_parser(
        "verify-g52-5tier-el3-guard",
        help="Run Phase 161 Gate G52 (5-Tier Unbrickable Recovery Ladder, ILME-FX3 0x91030080 Lock & CXD90057 EL3 RO Guard)",
    )
    p_g52.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g52.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g52.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 37. verify-52-gates
    p_52 = sub.add_parser(
        "verify-52-gates",
        help="Run Phase 161 52-Gate Master Safety Preflight Engine (G01..G52)",
    )
    p_52.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_52.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_52.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G52 gates can be rehearsed offline",
    )
    p_52.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 38. verify-g53-cxd90058-sabin
    p_g53 = sub.add_parser(
        "verify-g53-cxd90058-sabin",
        help="Run Phase 165 Gate G53 (CXD90057/CXD90058 Inter-SoC Link, sabin SA-DSP Immutability & SDI RAW Mask Guard)",
    )
    p_g53.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g53.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g53.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 39. verify-g54-factory-seal
    p_g54 = sub.add_parser(
        "verify-g54-factory-seal",
        help="Run Phase 165 Gate G54 (Post-Bench 16/16 H0 == H3 Factory Seal, Zero Residual & Official Readiness Guard)",
    )
    p_g54.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g54.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g54.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 40. verify-54-gates
    p_54 = sub.add_parser(
        "verify-54-gates",
        help="Run Phase 165 54-Gate Master Safety Preflight Engine (G01..G54)",
    )
    p_54.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_54.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_54.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G54 gates can be rehearsed offline",
    )
    p_54.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 41. verify-g55-c2pa-cert
    p_g55 = sub.add_parser(
        "verify-g55-c2pa-cert",
        help="Run Phase 170 Gate G55 (p12:/cert/RQ_LIC.DAT C2PA Read-Only Lock & Cross-Model Signing Firewall)",
    )
    p_g55.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g55.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g55.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 42. verify-g56-tc-gyro-meta
    p_g56 = sub.add_parser(
        "verify-g56-tc-gyro-meta",
        help="Run Phase 170 Gate G56 (VMC-BNCM1 EXT-LK LTC Bounds/Mux, TC-OUT Mask & IMX510 Gyro NonRealTimeMeta.xml Guard)",
    )
    p_g56.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g56.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g56.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 43. verify-56-gates
    p_56 = sub.add_parser(
        "verify-56-gates",
        help="Run Phase 170 56-Gate Master Safety Preflight Engine (G01..G56)",
    )
    p_56.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_56.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_56.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G56 gates can be rehearsed offline",
    )
    p_56.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 44. verify-g57-dualmedia-vault
    p_g57 = sub.add_parser(
        "verify-g57-dualmedia-vault",
        help="Run Phase 173 Gate G57 (Dual-Media Independent Tier-0 Device-ID Separation, 16/16 SHA-256 Parity & GF(256) 0x11d Scrub Guard)",
    )
    p_g57.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g57.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g57.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 45. verify-g58-bench-interlock
    p_g58 = sub.add_parser(
        "verify-g58-bench-interlock",
        help="Run Phase 173 Gate G58 (Two-Step Explicit Human Bench Authorization, NP-FZ100 >= 80%%/7400mV & Zero-Auto-Flash Interlock)",
    )
    p_g58.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g58.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_g58.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 46. verify-58-gates
    p_58 = sub.add_parser(
        "verify-58-gates",
        help="Run Phase 173 58-Gate Master Safety Preflight Engine (G01..G58)",
    )
    p_58.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_58.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    p_58.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G58 gates can be rehearsed offline",
    )
    p_58.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 47. verify-g59-ssboot-wbi2-guard
    p_g59 = sub.add_parser(
        "verify-g59-ssboot-wbi2-guard",
        help="Run Phase 177 Gate G59 (ssboot / WBI2 prsv-img Bootloader-Bypass, liro.ko BLKROSET=1 & H0==H3 Guard)",
    )
    p_g59.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g59.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g59.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 48. verify-g60-slot1-ufu-c2pa-guard
    p_g60 = sub.add_parser(
        "verify-g60-slot1-ufu-c2pa-guard",
        help="Run Phase 177 Gate G60 (FX3 7.02 >=2.04 UFU Floor, Slot-1 Root, C2PA <=100 License & Wireless Floor Guard)",
    )
    p_g60.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g60.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g60.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 49. verify-60-gates
    p_60 = sub.add_parser(
        "verify-60-gates",
        help="Run Phase 177 60-Gate Milestone Master Safety Preflight Engine (G01..G60)",
    )
    p_60.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_60.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_60.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G60 gates can be rehearsed offline",
    )
    p_60.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 50. verify-g61-emount-breathing-guard
    p_g61 = sub.add_parser(
        "verify-g61-emount-breathing-guard",
        help="Run Phase 181 Gate G61 (MIRA_CETUS2 E-Mount info7/info8/info3D, 0x02cf0232 Breathing, Focus Map RO & p18:/lens/LENSFILE.BIN Guard)",
    )
    p_g61.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g61.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g61.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 51. verify-g62-hdmi-raw-guard
    p_g62 = sub.add_parser(
        "verify-g62-hdmi-raw-guard",
        help="Run Phase 181 Gate G62 (Type-A HDMI 4264x2408 16-bit RAW .braw / ProRes RAW vs 12G-SDI MMIO Mask Guard)",
    )
    p_g62.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g62.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g62.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 52. verify-62-gates
    p_62 = sub.add_parser(
        "verify-62-gates",
        help="Run Phase 181 62-Gate Master Safety Preflight Engine (G01..G62)",
    )
    p_62.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_62.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_62.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G62 gates can be rehearsed offline",
    )
    p_62.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 53. verify-g63-fx3a-branch-firewall
    p_g63 = sub.add_parser(
        "verify-g63-fx3a-branch-firewall",
        help="Verify Gate G63: ILME-FX3 vs ILME-FX3A LCD/NFC/IR Hardware-Branch & BODYDATA/CAMSET Firewall",
    )
    p_g63.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g63.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g63.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 54. verify-g64-xlrh1-mishoe-guard
    p_g64 = sub.add_parser(
        "verify-g64-xlrh1-mishoe-guard",
        help="Verify Gate G64: XLR-H1 MI-Shoe 48kHz/24bit 4ch Routing vs Body 3.5mm Override Guard",
    )
    p_g64.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g64.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g64.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 55. verify-64-gates
    p_64 = sub.add_parser(
        "verify-64-gates",
        help="Run Phase 187 64-Gate Master Safety Preflight Engine (G01..G64)",
    )
    p_64.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_64.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_64.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G64 gates can be rehearsed offline",
    )
    p_64.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 56. verify-g65-nouvc-dcc1-pd
    p_g65 = sub.add_parser(
        "verify-g65-nouvc-dcc1-pd",
        help="Verify Gate G65: ILME-FX3 No-UVC USB Gadget Firewall & USB-PD / DC-C1 Electrical Interlock",
    )
    p_g65.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g65.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g65.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 57. verify-g66-lut-path-cineei-bt
    p_g66 = sub.add_parser(
        "verify-g66-lut-path-cineei-bt",
        help="Verify Gate G66: Dual-Media .cube User LUT Path-Asymmetry, Cine EI 800/12800 & RMT-P1BT BT/IR Guard",
    )
    p_g66.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g66.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g66.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 58. verify-66-gates
    p_66 = sub.add_parser(
        "verify-66-gates",
        help="Run Phase 191 66-Gate Master Safety Preflight Engine (G01..G66)",
    )
    p_66.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_66.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_66.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G66 gates can be rehearsed offline",
    )
    p_66.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 59. verify-g67-usblan-rtmp
    p_g67 = sub.add_parser(
        "verify-g67-usblan-rtmp",
        help="Verify Gate G67: ILME-FX3 (7.02) Power-On USB-LAN Auto-Connect & RTMP/RTMPS/SRT <= 38 Mbps Guard",
    )
    p_g67.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g67.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g67.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 60. verify-g68-clipflag-anamorphic
    p_g68 = sub.add_parser(
        "verify-g68-clipflag-anamorphic",
        help="Verify Gate G68: Creators' Cloud Clip-Flag (OK/NG/KEEP) & 1.5x/1.6x Anamorphic / Bright-Monitoring Magnifier Guard",
    )
    p_g68.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g68.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g68.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 61. verify-68-gates
    p_68 = sub.add_parser(
        "verify-68-gates",
        help="Run Phase 196 68-Gate Master Safety Preflight Engine (G01..G68)",
    )
    p_68.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_68.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_68.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G68 gates can be rehearsed offline",
    )
    p_68.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 62. verify-g69-fan-pwm-thermal
    p_g69 = sub.add_parser(
        "verify-g69-fan-pwm-thermal",
        help="Verify Gate G69: ILME-FX3 Exact 4-Mode [Fan Control] (Off in Rec Standby MAX PWM / Always Off Pre-Backup Block) & Thermal Guard",
    )
    p_g69.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g69.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g69.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g69.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 63. verify-g70-lut-601-702-shutter-angle
    p_g70 = sub.add_parser(
        "verify-g70-lut-601-702-shutter-angle",
        help="Verify Gate G70: FX6 Ver. 6.01 vs Stock FX3 Ver. 7.00/7.02 p2:/setting User LUT Binary Split Firewall & Shutter Speed/Angle Guard",
    )
    p_g70.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g70.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g70.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g70.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 64. verify-70-gates
    p_70 = sub.add_parser(
        "verify-70-gates",
        help="Run Phase 199 70-Gate Master Safety Preflight Engine (G01..G70)",
    )
    p_70.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_70.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_70.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G70 gates can be rehearsed offline",
    )
    p_70.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 65. verify-g71-big6-noend-camset-slot1
    p_g71 = sub.add_parser(
        "verify-g71-big6-noend-camset-slot1",
        help="Verify Gate G71: ILME-FX3 (Ver. 7.02) BIG6 Zero e-ND Actuator Firewall & Slot-1 CAMSET Dual-Media Isolation",
    )
    p_g71.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g71.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g71.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g71.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 66. verify-g72-vmcbncm1-tcin-hdmi-tcout
    p_g72 = sub.add_parser(
        "verify-g72-vmcbncm1-tcin-hdmi-tcout",
        help="Verify Gate G72: VMC-BNCM1 Body-Only TC IN (EXT-LK), XLR-H1 Handle Micro-USB Block & Digital HDMI-Only TC OUT Guard",
    )
    p_g72.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g72.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g72.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g72.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 67. verify-72-gates
    p_72 = sub.add_parser(
        "verify-72-gates",
        help="Run Phase 201 72-Gate Master Safety Preflight Engine (G01..G72)",
    )
    p_72.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_72.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_72.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G72 gates can be rehearsed offline",
    )
    p_72.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 68. verify-g73-desqueeze-focusmap
    p_g73 = sub.add_parser(
        "verify-g73-desqueeze-focusmap",
        help="Verify Gate G73: ILME-FX3 (Ver. 7.02) [De-Squeeze Display] (1.6x=1.65x 4-Locks / Auto-Suppression) & External M&C Focus Map (<150fps Cutoff) Guard",
    )
    p_g73.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g73.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g73.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g73.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 69. verify-g74-simult-autoswitch-shocklesswb
    p_g74 = sub.add_parser(
        "verify-g74-simult-autoswitch-shocklesswb",
        help="Verify Gate G74: Dual-Slot [Simult. Recording] + [Auto Switch Media] Parity & [Shockless WB] Immediate-Bypass Guard",
    )
    p_g74.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g74.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g74.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g74.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 70. verify-74-gates
    p_74 = sub.add_parser(
        "verify-74-gates",
        help="Run Phase 206 74-Gate Master Safety Preflight Engine (G01..G74)",
    )
    p_74.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_74.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_74.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all G01..G74 gates can be rehearsed offline",
    )
    p_74.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 71. verify-g75-hdmi-log1080-hdmionly
    p_g75 = sub.add_parser(
        "verify-g75-hdmi-log1080-hdmionly",
        help="Verify Gate G75: [HDMI Output Settings] Log/PPLUT 1080p Downshift, [Off(HDMI Only)] 4K & LCD Blanking Guard",
    )
    p_g75.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g75.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g75.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g75.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 72. verify-g76-proxy-focusmag-brightmon
    p_g76 = sub.add_parser(
        "verify-g76-proxy-focusmag-brightmon",
        help="Verify Gate G76: [Proxy Settings] Coupled Vault Parity & [Focus Magnifier]/[Bright Monitoring] Interlock Guard",
    )
    p_g76.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g76.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g76.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g76.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 73. verify-76-gates
    p_76 = sub.add_parser(
        "verify-76-gates",
        help="Run Phase 210 Unified 76-Gate Master Safety Preflight Engine (G01..G76)",
    )
    p_76.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_76.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_76.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G76 gates can be rehearsed offline",
    )
    p_76.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 74. verify-g77-filesettings-shotmark
    p_g77 = sub.add_parser(
        "verify-g77-filesettings-shotmark",
        help="Verify Gate G77: [File Settings] 5-Mode / 37-Char Title / SDHC Lock & [Shot Mark] XML / Transfer Filter Guard",
    )
    p_g77.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g77.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g77.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g77.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 75. verify-g78-tcregen-reclamp
    p_g78 = sub.add_parser(
        "verify-g78-tcregen-reclamp",
        help="Verify Gate G78: [TC/UB] [Regenerate] Slot-1 Master / VMC-BNCM1 EXT-LK Release & [REC Lamp] Coupled Tally Guard",
    )
    p_g78.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g78.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g78.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g78.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 76. verify-78-gates
    p_78 = sub.add_parser(
        "verify-78-gates",
        help="Run Phase 214 Unified 78-Gate Master Safety Preflight Engine (G01..G78)",
    )
    p_78.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_78.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_78.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G78 gates can be rehearsed offline",
    )
    p_78.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 77. verify-g79-pixelmap-cnflasha
    p_g79 = sub.add_parser(
        "verify-g79-pixelmap-cnflasha",
        help="Verify Gate G79: [Auto Pixel Mapping] / [Pixel Mapping] Reboot, Low-Battery Lockout & cnflasha Read-Only Firewall",
    )
    p_g79.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g79.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g79.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g79.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 78. verify-g80-ntscpal-gammaassist-displaylut
    p_g80 = sub.add_parser(
        "verify-g80-ntscpal-gammaassist-displaylut",
        help="Verify Gate G80: [NTSC/PAL Selector] Reset Persistence & [Gamma Display Assist] / [Display LUT] Split Guard",
    )
    p_g80.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g80.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g80.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g80.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 79. verify-80-gates
    p_80 = sub.add_parser(
        "verify-80-gates",
        help="Run Phase 219 Milestone Unified 80-Gate Master Safety Preflight Engine (G01..G80)",
    )
    p_80.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_80.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_80.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G80 gates can be rehearsed offline",
    )
    p_80.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 80. verify-g81-steadyshot-ciz
    p_g81 = sub.add_parser(
        "verify-g81-steadyshot-ciz",
        help="Verify Gate G81: [SteadyShot] Active RAW/HFR Cutoff & [Clear Image Zoom] / [Digital Zoom] 4-Locks Guard",
    )
    p_g81.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g81.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g81.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g81.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 81. verify-g82-powersave-autotemp
    p_g82 = sub.add_parser(
        "verify-g82-powersave-autotemp",
        help="Verify Gate G82: [Power Save Start Time] 9-Cond Bypass / Air-Gapped Tier-0 Pre-Check & [Auto Power OFF Temp.] Tripod Guard",
    )
    p_g82.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g82.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g82.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g82.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 82. verify-82-gates
    p_82 = sub.add_parser(
        "verify-82-gates",
        help="Run Phase 224 Unified 82-Gate Master Safety Preflight Engine (G01..G82)",
    )
    p_82.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_82.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_82.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G82 gates can be rehearsed offline",
    )
    p_82.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 83. verify-g83-sq-fixedvar-zebra-peaking
    p_g83 = sub.add_parser(
        "verify-g83-sq-fixedvar-zebra-peaking",
        help="Verify Gate G83: Ver. 7.02 [Mode Settings] Fixed/Variable S&Q 6-Lock Matrix & Zebra/Peaking Local-LCD-Only HDMI Clean-Feed Guard",
    )
    p_g83.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g83.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g83.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g83.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 84. verify-g84-zebra-reset-fullformat-chord
    p_g84 = sub.add_parser(
        "verify-g84-zebra-reset-fullformat-chord",
        help="Verify Gate G84: [Zebra Display] Camera Settings Reset Survival & Format Quick/Full + MENU+Delete 2s Chord Tier-0 Vault Guard",
    )
    p_g84.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g84.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g84.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g84.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 85. verify-84-gates
    p_84 = sub.add_parser(
        "verify-84-gates",
        help="Run Phase 228 Unified 84-Gate Master Safety Preflight Engine (G01..G84)",
    )
    p_84.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_84.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_84.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G84 gates can be rehearsed offline",
    )
    p_84.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 86. verify-g85-silent-autopixelmap-no-pwrshutter
    p_g85 = sub.add_parser(
        "verify-g85-silent-autopixelmap-no-pwrshutter",
        help="Verify Gate G85: [Silent Mode Settings] [Auto Pixel Mapping] Suppression Target, 5-Function Lockout & Hardware [Shutter When Pwr OFF] Absence Guard",
    )
    p_g85.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g85.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g85.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g85.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 87. verify-g86-marker-hdmi-flexexp-reset
    p_g86 = sub.add_parser(
        "verify-g86-marker-hdmi-flexexp-reset",
        help="Verify Gate G86: [Marker Display] 15-Ratio Non-Resettable Persistence, Local-LCD-Only HDMI Isolation & [Flexible Exp. Mode] Reset Split Guard",
    )
    p_g86.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g86.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g86.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g86.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 88. verify-86-gates
    p_86 = sub.add_parser(
        "verify-86-gates",
        help="Run Phase 230 Unified 86-Gate Master Safety Preflight Engine (G01..G86)",
    )
    p_86.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_86.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_86.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G86 gates can be rehearsed offline",
    )
    p_86.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 89. verify-g87-recover-imagedb-battery-vault
    p_g87 = sub.add_parser(
        "verify-g87-recover-imagedb-battery-vault",
        help="Verify Gate G87: [Recover Image DB] Depleted-Battery Refusal, Non-Deleting Repair & Unverified Slot-1 Tier-0 Vault Read-Only Mutation Firewall",
    )
    p_g87.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g87.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g87.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g87.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 90. verify-g88-monitor-flip-af-sens-interval
    p_g88 = sub.add_parser(
        "verify-g88-monitor-flip-af-sens-interval",
        help="Verify Gate G88: [Monitor Flip Direction] Reset Survival + [Horizontal Flip] Playback Non-Inversion & [AF Subj. Shift Sensitivity] / [Interval Shoot Func.] Guard",
    )
    p_g88.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g88.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g88.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g88.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 91. verify-88-gates
    p_88 = sub.add_parser(
        "verify-88-gates",
        help="Run Phase 235 Unified 88-Gate Master Safety Preflight Engine (G01..G88)",
    )
    p_88.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_88.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_88.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G88 gates can be rehearsed offline",
    )
    p_88.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 92. verify-g89-emphasized-rec-grid-hdmi
    p_g89 = sub.add_parser(
        "verify-g89-emphasized-rec-grid-hdmi",
        help="Verify Gate G89: [Emphasized REC Display] & [Grid Line] HDMI Info Routing vs Forced [Off(HDMI Only)] / RAW Clean-Feed Suppression Guard",
    )
    p_g89.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g89.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g89.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g89.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 93. verify-g90-touch-op-sunny-weather
    p_g90 = sub.add_parser(
        "verify-g90-touch-op-sunny-weather",
        help="Verify Gate G90: [Touch Operation] 4-Item [Camera Settings Reset] Survival + Bench Accidental-Tap Lock & [Monitor Brightness] Sunny Weather Indoor Guard",
    )
    p_g90.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g90.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g90.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g90.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 94. verify-90-gates
    p_90 = sub.add_parser(
        "verify-90-gates",
        help="Run Phase 237 (90/90 Milestone) Unified 90-Gate Master Safety Preflight Engine (G01..G90)",
    )
    p_90.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_90.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_90.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G90 gates can be rehearsed offline",
    )
    p_90.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 95. verify-shoe-audio-wind-guard
    p_g91 = sub.add_parser(
        "verify-shoe-audio-wind-guard",
        aliases=["verify-g91-shoe-audio-wind"],
        help="Verify Gate G91: [Shoe Audio Set.] 48kHz/24bit 4ch Meter/Routing Guard & [Wind Noise Reduct.] Built-In-Mic-Only Boundary",
    )
    p_g91.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g91.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g91.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g91.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 96. verify-saveload-c3-exclusions-guard
    p_g92 = sub.add_parser(
        "verify-saveload-c3-exclusions-guard",
        aliases=["verify-g92-saveload-c3-exclusions"],
        help="Verify Gate G92: [Save/Load Settings] CAMSET01..10.DAT / C3 Portal Excluded-Items Firewall & Slot-1 Tier-0 Vault Write Guard",
    )
    p_g92.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g92.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g92.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g92.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 97. verify-92-gates
    p_92 = sub.add_parser(
        "verify-92-gates",
        help="Run Phase 241 Unified 92-Gate Master Safety Preflight Engine (G01..G92)",
    )
    p_92.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_92.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_92.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G92 gates can be rehearsed offline",
    )
    p_92.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 98. verify-framing-antiflicker-guard
    p_g93 = sub.add_parser(
        "verify-framing-antiflicker-guard",
        aliases=["verify-g93-framing-antiflicker"],
        help="Verify Gate G93: [Framing Settings] Asymmetric Full/Crop Stream Guard & [Anti-flicker Shoot.] Mechanical-Still-Only / No-Var. Shutter Firewall",
    )
    p_g93.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g93.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g93.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g93.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 99. verify-usbpower-lun-guard
    p_g94 = sub.add_parser(
        "verify-usbpower-lun-guard",
        aliases=["verify-g94-usbpower-lun"],
        help="Verify Gate G94: [USB Power Supply] Mandatory NP-FZ100 Insertion + USB Type-C Exclusivity & [USB LUN Setting] Multi/Single Setup Persistence Guard",
    )
    p_g94.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g94.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g94.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g94.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 100. verify-94-gates
    p_94 = sub.add_parser(
        "verify-94-gates",
        help="Run Phase 246 Unified 94-Gate Master Safety Preflight Engine (G01..G94)",
    )
    p_94.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_94.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_94.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G94 gates can be rehearsed offline",
    )
    p_94.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 101. verify-lock-op-parts-chord-guard
    p_g95 = sub.add_parser(
        "verify-lock-op-parts-chord-guard",
        aliases=["verify-g95-lock-op-parts-chord"],
        help="Verify Gate G95: [Lock Operation Parts] Fn Hold, MENU + Fn 5s Full-Body Lock Chord vs Destructive MENU + Delete 2s Firewall & My Dial Temporary Override Guard",
    )
    p_g95.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g95.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g95.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g95.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 102. verify-audio-timing-exp-step-guard
    p_g96 = sub.add_parser(
        "verify-audio-timing-exp-step-guard",
        aliases=["verify-g96-audio-timing-exp-step"],
        help="Verify Gate G96: [Audio Out Timing] Live/Lip Sync vs [Audio signals] Setup Persistence & [Exposure step] 0.3EV/0.5EV vs [Shutter Angle] Constant-Table Guard",
    )
    p_g96.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g96.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g96.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g96.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 103. verify-96-gates
    p_96 = sub.add_parser(
        "verify-96-gates",
        help="Run Phase 249 Unified 96-Gate Master Safety Preflight Engine (G01..G96)",
    )
    p_96.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_96.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_96.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G96 gates can be rehearsed offline",
    )
    p_96.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 104. verify-display-quality-bt-rmt-guard
    p_g97 = sub.add_parser(
        "verify-display-quality-bt-rmt-guard",
        aliases=["verify-g97-display-quality-bt-rmt"],
        help="Verify Gate G97: [Display Quality] Standard/High Battery Conservation & [Bluetooth Rmt Ctrl] IR Lockout / Reset Network Set. Split Guard",
    )
    p_g97.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g97.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g97.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g97.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 105. verify-mymenu-camset-firewall-guard
    p_g98 = sub.add_parser(
        "verify-mymenu-camset-firewall-guard",
        aliases=["verify-g98-mymenu-camset"],
        help="Verify Gate G98: [My Menu Setting] 6-Op Persistence & Slot-1 CAMSET01.DAT O_RDONLY Load-Only Firewall Guard",
    )
    p_g98.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g98.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g98.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g98.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 106. verify-98-gates
    p_98 = sub.add_parser(
        "verify-98-gates",
        help="Run Phase 252 Unified 98-Gate Master Safety Preflight Engine (G01..G98)",
    )
    p_98.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_98.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_98.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G98 gates can be rehearsed offline",
    )
    p_98.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 107. verify-diff-set-still-mv-shutter-angle-guard
    p_g99 = sub.add_parser(
        "verify-diff-set-still-mv-shutter-angle-guard",
        aliases=["verify-g99-diff-set-still-mv"],
        help="Verify Gate G99: [Different Set for Still/Mv] 8-Item Asymmetric Transitions, Reset Survival & Ver. 7.02 [Shutter Mode] = [Angle] Override Guard",
    )
    p_g99.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g99.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g99.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g99.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 108. verify-custom-key-dial-remain-shoot-guard
    p_g100 = sub.add_parser(
        "verify-custom-key-dial-remain-shoot-guard",
        aliases=["verify-g100-custom-key-remain-shoot"],
        help="Verify Gate G100 (100th Milestone Gate): [Custom Key/Dial Set.] ISO/EI Firewall & [Remain Shoot Display] EVF-Less Guard",
    )
    p_g100.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g100.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g100.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g100.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 109. verify-100-gates
    p_100 = sub.add_parser(
        "verify-100-gates",
        help="Run Phase 256 Grand Milestone Unified 100-Gate Master Safety Preflight Engine (G01..G100)",
    )
    p_100.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_100.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_100.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G100 gates can be rehearsed offline",
    )
    p_100.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 110. verify-auto-slow-shutter-breathing-comp-guard
    p_g101 = sub.add_parser(
        "verify-auto-slow-shutter-breathing-comp-guard",
        aliases=["verify-g101-auto-slow-shutter-breathing"],
        help="Verify Gate G101: [Auto Slow Shutter] 6-Condition Lockout, Ver. 7.02 [Shutter Mode] = [Angle] Disjointness & [Breathing Comp.] Guard",
    )
    p_g101.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g101.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g101.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g101.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 111. verify-hdmi-reccontrol-tcout-4chaudio-guard
    p_g102 = sub.add_parser(
        "verify-hdmi-reccontrol-tcout-4chaudio-guard",
        aliases=["verify-g102-hdmi-reccontrol-4chaudio"],
        help="Verify Gate G102: [HDMI Output Settings] Non-Resettable Survival, [REC Control] <- [Time Code Output] Gate, [4ch Audio Output] & [Rec. Media dur HDMI Output] Vault Guard",
    )
    p_g102.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g102.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g102.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g102.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 112. verify-102-gates
    p_102 = sub.add_parser(
        "verify-102-gates",
        help="Run Phase 259 Unified 102-Gate Master Safety Preflight Engine (G01..G102)",
    )
    p_102.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_102.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_102.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G102 gates can be rehearsed offline",
    )
    p_102.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 113. verify-apsc-s35-face-eye-af-guard
    p_g103 = sub.add_parser(
        "verify-apsc-s35-face-eye-af-guard",
        aliases=["verify-g103-apsc-s35-face-eye-af"],
        help="Verify Gate G103: [APS-C S35 Shooting] 12.1MP 4K Movie Lockout & [Face/Eye AF] Clean-HDMI Isolation Guard",
    )
    p_g103.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g103.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g103.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g103.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 114. verify-version-readonly-bodydata-flash-block-guard
    p_g104 = sub.add_parser(
        "verify-version-readonly-bodydata-flash-block-guard",
        aliases=["verify-g104-version-bodydata-block"],
        help="Verify Gate G104: [Version] Read-Only Inspection, Zero-RF Badge Suppression & Hard-Blocked BODYDATA.DAT Flash Guard",
    )
    p_g104.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g104.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g104.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g104.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 115. verify-104-gates
    p_104 = sub.add_parser(
        "verify-104-gates",
        help="Run Phase 263 Unified 104-Gate Master Safety Preflight Engine (G01..G104)",
    )
    p_104.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_104.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_104.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G104 gates can be rehearsed offline",
    )
    p_104.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 116. verify-release-wo-card-lens-audio-disp-guard
    p_g105 = sub.add_parser(
        "verify-release-wo-card-lens-audio-disp-guard",
        aliases=["verify-g105-release-wo-card-audio-disp"],
        help="Verify Gate G105: [Release w/o Card] & [Release w/o Lens] Scope + Ver. 7.02 5-Item [Audio Recording] vs DISP Audio Meter Guard",
    )
    p_g105.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g105.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g105.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g105.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 117. verify-copyright-info-46char-exif-hygiene-guard
    p_g106 = sub.add_parser(
        "verify-copyright-info-46char-exif-hygiene-guard",
        aliases=["verify-g106-copyright-info-hygiene"],
        help="Verify Gate G106: [Copyright Info] 46-Char Still EXIF Bounds, Reset Survival & Clean-Room Bench PII Hygiene Guard",
    )
    p_g106.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g106.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g106.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g106.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 118. verify-106-gates
    p_106 = sub.add_parser(
        "verify-106-gates",
        help="Run Phase 266 Unified 106-Gate Master Safety Preflight Engine (G01..G106)",
    )
    p_106.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_106.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_106.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G106 gates can be rehearsed offline",
    )
    p_106.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 119. verify-file-settings-dsc-slot1-vault-guard
    p_g107 = sub.add_parser(
        "verify-file-settings-dsc-slot1-vault-guard",
        aliases=["verify-g107-file-settings-vault"],
        help="Verify Gate G107: Movie [File Settings] Cam ID + Reel# & 37-Char Title vs Still DSC Prefix & Slot-1 Vault Guard",
    )
    p_g107.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g107.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g107.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g107.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 120. verify-gamma-disp-assist-auto-review-tcub-guard
    p_g108 = sub.add_parser(
        "verify-gamma-disp-assist-auto-review-tcub-guard",
        aliases=["verify-g108-gamma-assist-tcub"],
        help="Verify Gate G108: [Gamma Display Assist] Log Shooting Lockout vs [Display LUT]/[Select LUT], [Auto Review] Off Default & [TC/UB] Persistence Guard",
    )
    p_g108.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g108.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g108.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g108.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 121. verify-108-gates
    p_108 = sub.add_parser(
        "verify-108-gates",
        help="Run Phase 268 Unified 108-Gate Master Safety Preflight Engine (G01..G108)",
    )
    p_108.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_108.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_108.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G108 gates can be rehearsed offline",
    )
    p_108.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 122. verify-focus-mag-peaking-af-illuminator-guard
    p_g109 = sub.add_parser(
        "verify-focus-mag-peaking-af-illuminator-guard",
        aliases=["verify-g109-focus-mag-peaking"],
        help="Verify Gate G109: [Focus Assistant] [Auto Magnifier in MF] vs MF Assist, Custom Button 5, [Initial Focus Mag.] x1.0, [Peaking Display] Clean-HDMI & Still-Only [AF Illuminator] Guard",
    )
    p_g109.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g109.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g109.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g109.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 123. verify-area-datetime-videolight-hdmires-guard
    p_g110 = sub.add_parser(
        "verify-area-datetime-videolight-hdmires-guard",
        aliases=["verify-g110-datetime-videolight-hdmires"],
        help="Verify Gate G110: [Area/Date/Time Setting], Zero-RF Creators' App Suppression, [Video Light Mode] Power Link & MI-Shoe 5V <= 900 mA & [HDMI Resolution] Auto / Log 1080p Override Guard",
    )
    p_g110.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g110.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g110.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g110.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 124. verify-110-gates
    p_110 = sub.add_parser(
        "verify-110-gates",
        help="Run Phase 271 (110/110 Milestone) Unified 110-Gate Master Safety Preflight Engine (G01..G110)",
    )
    p_110.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_110.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_110.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G110 gates can be rehearsed offline",
    )
    p_110.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 125. verify-power-save-monitor-language-guard
    p_g111 = sub.add_parser(
        "verify-power-save-monitor-language-guard",
        aliases=["verify-g111-power-save-monitor-language"],
        help="Verify Gate G111: [Power Save by Monitor] appFw.so 4-Mode vs ILME-FX3 2-Item [Power Setting Option], [Power Save Start Time] 9-Deactivation Bench Guard, and [Language] BK_LANG 34-vs-29 Parity",
    )
    p_g111.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g111.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g111.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g111.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 126. verify-volume-4chmon-delete-confirm-guard
    p_g112 = sub.add_parser(
        "verify-volume-4chmon-delete-confirm-guard",
        aliases=["verify-g112-volume-4chmon-delete-confirm"],
        help="Verify Gate G112: [Volume Settings] 0..15 Default 7, [4ch Audio Monitoring] 5 Routes vs HDMI Output, and [Delete confirm.] Cancel First + Slot-1 Vault Delete/Format Firewall",
    )
    p_g112.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g112.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g112.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g112.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 127. verify-112-gates
    p_112 = sub.add_parser(
        "verify-112-gates",
        help="Run Phase 273 Unified 112-Gate Master Safety Preflight Engine (G01..G112)",
    )
    p_112.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_112.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_112.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G112 gates can be rehearsed offline",
    )
    p_112.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 128. verify-usb-mode-hdmi-info-guard
    p_g113 = sub.add_parser(
        "verify-usb-mode-hdmi-info-guard",
        aliases=["verify-g113-usb-mode-hdmi-info"],
        help="Verify Gate G113: [USB Connection Mode] 4-Mode vs Dormant NOUVC [USB Streaming], Data-Isolated PD Guard, and [HDMI Info. Display] LCD Blanking / 1080 Clamp / 4K Clean-Feed Override",
    )
    p_g113.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g113.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g113.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g113.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 129. verify-protect-and-network-reset-guard
    p_g114 = sub.add_parser(
        "verify-protect-and-network-reset-guard",
        aliases=["verify-g114-protect-network-reset"],
        help="Verify Gate G114: [Protect] Scopes vs [Format] Slot-1 Dual-Layer Hardware WP Firewall and [Reset Network Set.] Auto-Reboot + Post-Reboot [Airplane Mode] = [On] Zero-RF Sequence",
    )
    p_g114.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g114.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g114.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g114.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 130. verify-114-gates
    p_114 = sub.add_parser(
        "verify-114-gates",
        help="Run Phase 276 Unified 114-Gate Master Safety Preflight Engine (G01..G114)",
    )
    p_114.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_114.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_114.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G114 gates can be rehearsed offline",
    )
    p_114.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 131. verify-pp-scinetone-creativelook-dro-guard
    p_g115 = sub.add_parser(
        "verify-pp-scinetone-creativelook-dro-guard",
        aliases=["verify-g115-pp-scinetone-creativelook-dro"],
        help="Verify Gate G115: [Picture Profile] PP11 (S-Cinetone) Default vs [Creative Look] (10 Looks) & [D-Range Optimizer] under [Log Shooting], PPLUT1..4 Clamp & [PPx] -> [Reset] Trap",
    )
    p_g115.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g115.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g115.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g115.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 132. verify-wb-cineei-and-metering-guard
    p_g116 = sub.add_parser(
        "verify-wb-cineei-and-metering-guard",
        aliases=["verify-g116-wb-cineei-metering"],
        help="Verify Gate G116: [White Balance] (2500K..9900K, Custom 1..3, Cine EI AWB Lockout, Custom Setup Trap) & [Metering Mode] (6 Modes, De-Squeeze Lockout, Cine EI Base ISO M.M.)",
    )
    p_g116.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g116.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g116.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g116.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 133. verify-116-gates
    p_116 = sub.add_parser(
        "verify-116-gates",
        help="Run Phase 280 Milestone Unified 116-Gate Master Safety Preflight Engine (G01..G116)",
    )
    p_116.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_116.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_116.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G116 gates can be rehearsed offline",
    )
    p_116.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 134. verify-raw-heif-colorspace-guard
    p_g117 = sub.add_parser(
        "verify-raw-heif-colorspace-guard",
        aliases=["verify-g117-raw-heif-colorspace"],
        help="Verify Gate G117: Still [Image Quality Settings] 2-Option Compressed/Uncompressed RAW vs Dormant Lossless Comp, JPEG/HEIF 4:2:0/4:2:2, [HLG Still Image], and [Color Space] AdobeRGB _DSC Prefix Rule",
    )
    p_g117.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g117.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g117.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g117.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 135. verify-shutter-type-nr-drive-guard
    p_g118 = sub.add_parser(
        "verify-shutter-type-nr-drive-guard",
        aliases=["verify-g118-shutter-type-nr-drive"],
        help="Verify Gate G118: 2-Option [Shutter Type] Mechanical/Electronic (No Auto), [e-Front Curtain Shut.], 1/250 s Flash Sync & 5-Function Electronic Lockout, [Long Exposure NR], [High ISO NR], and [Drive Mode] 10 fps Couplings",
    )
    p_g118.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g118.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g118.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g118.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 136. verify-118-gates
    p_118 = sub.add_parser(
        "verify-118-gates",
        help="Run Phase 283 Unified 118-Gate Master Safety Preflight Engine (G01..G118)",
    )
    p_118.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_118.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_118.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G118 gates can be rehearsed offline",
    )
    p_118.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 137. verify-focus-area-and-zoom-lever-guard
    p_g119 = sub.add_parser(
        "verify-focus-area-and-zoom-lever-guard",
        aliases=["verify-g119-focus-area-zoom-lever"],
        help="Verify Gate G119: 14-Option [Focus Area] Hierarchy (7 Still-Only AF-C Tracking vs Movie Touch Tracking), [Focus Area Limit] >= 2, [AF Area Registration], XLR-H1 No-Zoom-Lever Myth-Bust, and [Zoom Lever Speed]/[Remote Zoom Speed] 1..8 vs FX6 0..99 Indicator",
    )
    p_g119.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g119.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g119.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g119.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 138. verify-iso-minss-and-flash-guard
    p_g120 = sub.add_parser(
        "verify-iso-minss-and-flash-guard",
        aliases=["verify-g120-iso-minss-flash"],
        help="Verify Gate G120: [ISO Range Limit] / [ISO AUTO Min. SS] vs Cine EI Base-ISO 800/12800 Lockout, Still-Only Mechanical-Shutter [Flash Mode] (<= 1/250 s, < 250V MI-Shoe Sync), and [Video Light Mode]",
    )
    p_g120.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g120.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g120.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g120.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 139. verify-120-gates
    p_120 = sub.add_parser(
        "verify-120-gates",
        help="Run Phase 286 Unified 120-Gate Milestone Master Safety Preflight Engine (G01..G120)",
    )
    p_120.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_120.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_120.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G120 gates can be rehearsed offline",
    )
    p_120.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 140. verify-dci4k-and-aspect-ratio-guard
    p_g121 = sub.add_parser(
        "verify-dci4k-and-aspect-ratio-guard",
        aliases=["verify-g121-dci4k-aspect-ratio"],
        help="Verify Gate G121: XAVC S-I DCI 4K (4096x2160 17:9 All-Intra + Reboot-Gated 24.00p, S&Q 1..48 fps) vs Long-GOP UHD 3840x2160 Boundary, 4264x2408 Type-A HDMI RAW, & Still [Aspect Ratio] (3:2/4:3/16:9/1:1)",
    )
    p_g121.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g121.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g121.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g121.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 141. verify-custom-hold-camset-photo-capture-guard
    p_g122 = sub.add_parser(
        "verify-custom-hold-camset-photo-capture-guard",
        aliases=["verify-g122-custom-hold-camset-photo-capture"],
        help="Verify Gate G122: [Reg. Custom Shoot Set] (11 Checkboxes, Still P/A/S/M) vs [Camera Set. Memory] (1..3 + M1..M4 %%c:%%s/SONY/SETTING/%%s/CAMPR%%02d%%c.DAT vs FX6 s/SONY/PRO/CAMERA/), Playback [Photo Capture] (DCI 4K Lockout + Slot-1 Firewall), & [Enlarge Initial Mag./Position]",
    )
    p_g122.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g122.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g122.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g122.add_argument("--json", action="store_true", help="Emit structured JSON report")

    # 142. verify-122-gates
    p_122 = sub.add_parser(
        "verify-122-gates",
        help="Run Phase 288 Unified 122-Gate Master Safety Preflight Engine (G01..G122)",
    )
    p_122.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_122.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_122.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G122 gates can be rehearsed offline",
    )
    p_122.add_argument("--json", action="store_true", help="Emit structured JSON report")

    args = parser.parse_args(argv)

    if args.cmd == "evaluate-preflight":
        res = evaluate_12_safety_gates(args.repo_root)
        text = json.dumps(res, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        sys.stdout.write(text)
        return 0

    if args.cmd == "diagnose-brick":
        diag = classify_brick_state(
            led_symptom=args.led,
            usb_vid_pid=args.usb,
            display_state=args.display,
            corrupted_regions=args.regions,
            updater_mode_armed=args.updater_armed,
            oneshot_overlay_used=args.oneshot_overlay,
            has_full_body_backup=args.has_backup,
        )
        from dataclasses import asdict

        sys.stdout.write(json.dumps(asdict(diag), indent=2, ensure_ascii=False) + "\n")
        return 0

    if args.cmd == "verify-sector0":
        raw = args.input.read_bytes()
        res = verify_sector0_partition_table(raw)
        from dataclasses import asdict

        sys.stdout.write(json.dumps(asdict(res), indent=2, ensure_ascii=False) + "\n")
        return 0 if res.valid else 1

    if args.cmd == "verify-backup-manifest":
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        res = verify_tier0_backup_manifest(data)
        from dataclasses import asdict

        sys.stdout.write(json.dumps(asdict(res), indent=2, ensure_ascii=False) + "\n")
        return 0 if res.valid else 1

    if args.cmd == "generate-failsafe-hook":
        hook = generate_failsafe_init2_overlay_hook(
            mod_payload_path=args.payload,
            target_mount_path=args.target,
            watchdog_timeout_sec=args.timeout,
        )
        sys.stdout.write(hook)
        return 0

    if args.cmd == "audit-worker-trace":
        raw_trace = json.loads(args.trace.read_text(encoding="utf-8"))
        syscalls = raw_trace["syscalls"] if isinstance(raw_trace, dict) else raw_trace
        res = audit_tier0_worker_syscall_trace(syscalls)
        from dataclasses import asdict

        sys.stdout.write(json.dumps(asdict(res), indent=2, ensure_ascii=False) + "\n")
        return 0 if res.valid else 1

    if args.cmd == "verify-thermal-power-guard":
        report = evaluate_thermal_pwm_and_power_guard(
            force_clean_room=True if args.clean_room else None,
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

    if args.cmd == "verify-16-gates":
        report = evaluate_16_master_safety_gates(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            use_synthetic_dry_run_tier0=bool(args.dry_run_tier0),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/16 "
                f"g13_to_g16_all_passed={report.g13_to_g16_all_passed} "
                f"all_16_gates_verified={report.all_16_gates_verified} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_16_gates_verified if args.dry_run_tier0 else report.offline_13_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-media-guard":
        slot_a: Optional[MediaSlotConfig] = None
        if args.slot_a_root is not None or args.slot_a_image is not None:
            slot_a = MediaSlotConfig(
                slot_id=SLOT_A,
                inserted=True,
                exfat_boot_bytes=None if args.slot_a_image is not None else build_synthetic_exfat_boot_region(),
                exfat_image_path=args.slot_a_image,
                card_root=args.slot_a_root,
                card_entries=None if args.slot_a_root is not None else (),
                dedicated_lab_card=True,
            )
        slot_b: Optional[MediaSlotConfig] = None
        if args.slot_b_root is not None or args.slot_b_image is not None:
            slot_b = MediaSlotConfig(
                slot_id=SLOT_B,
                inserted=True,
                media_type=MEDIA_TYPE_SDXC,
                device_node="/dev/mmcblk2p1",
                mount_point="/mnt/slot_b",
                exfat_boot_bytes=None if args.slot_b_image is not None else build_synthetic_exfat_boot_region(),
                exfat_image_path=args.slot_b_image,
                card_root=args.slot_b_root,
                card_entries=None if args.slot_b_root is not None else (),
                dedicated_lab_card=True,
            )
        report = evaluate_exfat_media_integrity_guard(
            force_clean_room=True if args.clean_room else None,
            slot_a=slot_a,
            slot_b=slot_b,
            p1_image_path=args.p1_image,
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} all_passed={report.all_passed} "
                f"h0_h1_trial_entry_allowed={report.h0_h1_trial_entry_allowed} "
                f"p1_fs={report.filesystem_separation['p1_filesystem']} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        return 0 if report.all_passed else 1

    if args.cmd == "verify-18-gates":
        report = evaluate_18_master_safety_gates(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            use_synthetic_dry_run_tier0=bool(args.dry_run_tier0),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/18 "
                f"g17_to_g18_all_passed={report.g17_to_g18_all_passed} "
                f"all_18_gates_verified={report.all_18_gates_verified} "
                f"h0_h1_trial_entry_allowed={report.h0_h1_trial_entry_allowed} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_18_gates_verified if args.dry_run_tier0 else report.offline_15_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-20-gates":
        report = evaluate_20gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/20 "
                f"g19_to_g20_all_passed={report.g19_to_g20_all_passed} "
                f"all_20_gates_verified={report.all_20_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_20_gates_verified if args.dry_run_simulated_backup else report.offline_17_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-22-gates":
        report = evaluate_22gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/22 "
                f"g21_to_g22_all_passed={report.g21_to_g22_all_passed} "
                f"all_22_gates_verified={report.all_22_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_22_gates_verified if args.dry_run_simulated_backup else report.offline_19_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-24-gates":
        report = evaluate_24gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/24 "
                f"g23_to_g24_all_passed={report.g23_to_g24_all_passed} "
                f"all_24_gates_verified={report.all_24_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_24_gates_verified if args.dry_run_simulated_backup else report.offline_21_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-26-gates":
        report = evaluate_26gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/26 "
                f"g25_to_g26_all_passed={report.g25_to_g26_all_passed} "
                f"all_26_gates_verified={report.all_26_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_26_gates_verified if args.dry_run_simulated_backup else report.offline_23_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-28-gates":
        report = evaluate_28gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/28 "
                f"g27_to_g28_all_passed={report.g27_to_g28_all_passed} "
                f"all_28_gates_verified={report.all_28_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_28_gates_verified if args.dry_run_simulated_backup else report.offline_25_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-30-gates":
        report = evaluate_30gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/30 "
                f"g29_to_g30_all_passed={report.g29_to_g30_all_passed} "
                f"all_30_gates_verified={report.all_30_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_30_gates_verified if args.dry_run_simulated_backup else report.offline_27_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-32-gates":
        report = evaluate_32gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/32 "
                f"g31_to_g32_all_passed={report.g31_to_g32_all_passed} "
                f"all_32_gates_verified={report.all_32_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_32_gates_verified if args.dry_run_simulated_backup else report.offline_29_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-34-gates":
        report = evaluate_34gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/34 "
                f"g33_to_g34_all_passed={report.g33_to_g34_all_passed} "
                f"all_34_gates_verified={report.all_34_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_34_gates_verified if args.dry_run_simulated_backup else report.offline_31_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-36-gates":
        report = evaluate_36gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/36 "
                f"g35_to_g36_all_passed={report.g35_to_g36_all_passed} "
                f"all_36_gates_verified={report.all_36_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_36_gates_verified if args.dry_run_simulated_backup else report.offline_33_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-38-gates":
        report = evaluate_38gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/38 "
                f"g37_to_g38_all_passed={report.g37_to_g38_all_passed} "
                f"all_38_gates_verified={report.all_38_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_38_gates_verified if args.dry_run_simulated_backup else report.offline_35_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-40-gates":
        report = evaluate_40gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/40 "
                f"g39_to_g40_all_passed={report.g39_to_g40_all_passed} "
                f"all_40_gates_verified={report.all_40_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_40_gates_verified if args.dry_run_simulated_backup else report.offline_37_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-42-gates":
        report = evaluate_42gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/42 "
                f"g41_to_g42_all_passed={report.g41_to_g42_all_passed} "
                f"all_42_gates_verified={report.all_42_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_42_gates_verified if args.dry_run_simulated_backup else report.offline_39_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g43-jiritsu-service":
        verdict, res = evaluate_g43_jiritsu_service(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.jiritsu_service_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} soc={guard['np_fz100_soc_pct']}% "
                f"jbusy={guard['jbusy_precheck_code_hex']} "
                f"p6_peak={guard['peak_p6_bytes']}B "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g44-cnflasha-dualboot":
        verdict, res = evaluate_g44_cnflasha_dualboot(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.cnflasha_dualboot_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} dev={guard['target_block_device']} "
                f"sd_escape_us={guard['sd_escape_bypass_latency_us']} "
                f"p1_uart={guard['p1_kemco_cfg_uart']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-44-gates":
        report = evaluate_44gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/44 "
                f"g43_to_g44_all_passed={report.g43_to_g44_all_passed} "
                f"all_44_gates_verified={report.all_44_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_44_gates_verified if args.dry_run_simulated_backup else report.offline_41_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g45-service-0336-canary":
        verdict, res = evaluate_g45_service_0336_canary(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.service_0336_canary_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} slot=0x{guard['op_ff_canary_slot']:02x} "
                f"inflight={guard['concurrent_inflight_packets']} "
                f"pkt={guard['fx3s0ok_packet_bytes']}B/{guard['fx3s0ok_header_magic']} "
                f"msc_return={guard['msc_return_elapsed_ms']}ms->{guard['usb_reenum_msc_vid_pid']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g46-mpr-ibis-p18-guard":
        verdict, res = evaluate_g46_mpr_ibis_p18_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.stageb_mpr_ibis_p18_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} p18_flags={guard['p18_mount_flags']} "
                f"coil={guard['coil_current_ma']}mA "
                f"dmm_pools={guard['allocated_main_pools']}/{guard['shared_main_pools_count']} "
                f"sdi_wait={guard['sdi_blocking_wait_ms']}ms "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-46-gates":
        report = evaluate_46gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/46 "
                f"g45_to_g46_all_passed={report.g45_to_g46_all_passed} "
                f"all_46_gates_verified={report.all_46_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_46_gates_verified if args.dry_run_simulated_backup else report.offline_43_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g47-pnflasha-mtdro-vault":
        verdict, res = evaluate_g47_pnflasha_mtdro_vault(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.pnflasha_mtdro_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} domain={guard['backup_cipher_domain']}->{guard['restore_target_domain']} "
                f"mtd={guard['mtd_device_node']}({guard['mtd_open_mode']}) "
                f"spi_nor_write_authorized={res.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g48-rfnvs-fan-power-guard":
        verdict, res = evaluate_g48_rfnvs_fan_power_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.rfnvs_fan_power_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} p12_flags={guard['p12_mount_flags']} "
                f"rf_mut={guard['rf_nvs_mutation_bytes']}B "
                f"msc={guard['usb_msc_recovery_vid_pid']} "
                f"fan={guard['fan_pwm_pct']:.0f}%@{guard['sensor_temp_c']:.0f}C "
                f"batt={guard['battery_mv']:.0f}mV/{guard['batt_power_state']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-48-gates":
        report = evaluate_48gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/48 "
                f"g47_to_g48_all_passed={report.g47_to_g48_all_passed} "
                f"all_48_gates_verified={report.all_48_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_48_gates_verified if args.dry_run_simulated_backup else report.offline_45_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g49-uart1v8-isp":
        verdict, res = evaluate_g49_uart1v8_isp(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.uart1v8_isp_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} uart={guard['uart_device']}({guard['uart_baud_rate']}{guard['uart_framing']}@{guard['uart_io_voltage_mv']:.0f}mV) "
                f"tx={guard['tx_line_connected']} vmc_simult={guard['vmc_bncm1_simultaneous_attach']} "
                f"isp={guard['isp_vccq_mv']:.0f}mV@{guard['isp_clk_mhz']:.1f}MHz "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g50-imx510-sensor-cal":
        verdict, res = evaluate_g50_imx510_sensor_cal(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.imx510_sensor_cal_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} cal_mut={guard['sensor_cal_mutation_bytes']}B "
                f"iso={guard['base_iso']}/{guard['conversion_gain_mode']}(target={guard['target_iso']},gain={guard['analog_gain_db']:.1f}dB) "
                f"cube={guard['cube_grid_size']}^3 mlut_non_double_bake={guard['mlut_double_bake_blocked']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-50-gates":
        report = evaluate_50gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/50 "
                f"g49_to_g50_all_passed={report.g49_to_g50_all_passed} "
                f"all_50_gates_verified={report.all_50_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_50_gates_verified if args.dry_run_simulated_backup else report.offline_47_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g51-cfexpress-ufu":
        verdict, res = evaluate_g51_cfexpress_ufu(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.cfexpress_ufu_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} codec={guard['codec_profile']}@{guard['codec_bitrate_mbps']:.0f}Mbps "
                f"slotA={guard['slot_a_media_type']}/{guard['slot_a_speed_class']} "
                f"unflushed_fifo={guard['unflushed_fifo_bytes_on_door_open']}B "
                f"ufu_present={guard['bodydata_dat_present']} h0_eq_h3={guard['h0_equals_h3_verified']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g52-5tier-el3-guard":
        verdict, res = evaluate_g52_5tier_el3_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.five_tier_el3_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} tiers={len(guard['recovery_ladder'])}/5 "
                f"model={guard['target_model_name']}({guard['target_model_id_hex']}) "
                f"el3={guard['soc_name']}@{guard['el3_entry_addr_hex']}({guard['el3_monitor_mode']}) "
                f"el3_payload_transmit_authorized={res.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={res.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-52-gates":
        report = evaluate_52gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/52 "
                f"g51_to_g52_all_passed={report.g51_to_g52_all_passed} "
                f"all_52_gates_verified={report.all_52_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_52_gates_verified if args.dry_run_simulated_backup else report.offline_49_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g53-cxd90058-sabin":
        verdict, res = evaluate_g53_cxd90058_sabin(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.cxd90058_sabin_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} link={guard['ap_soc_name']}<->{guard['cp_soc_name']}({guard['intersoc_link_protocol']}) "
                f"cxd90058_mut={guard['cxd90058_mutation_bytes']}B sabin_mut={guard['sabin_dsp_mutation_bytes']}B "
                f"sdi_raw_masked={guard['fx6_sdi_raw_masked']} "
                f"memcfg={guard['allocated_memcfg_mib']:.1f}/{guard['memcfg_total_mib']:.1f}MiB "
                f"el3_payload_transmit_authorized={res.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={res.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g54-factory-seal":
        verdict, res = evaluate_g54_factory_seal(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.factory_seal_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} h0_eq_h3={guard['verified_surface_count']}/{guard['expected_surface_count']} "
                f"residual={guard['residual_artifact_count']} "
                f"otp={guard['otp_write_count']} rpmb={guard['rpmb_write_count']} "
                f"mode_flags={guard['updater_mode_flag_count']} "
                f"official_ready={guard['official_update_ready']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-54-gates":
        report = evaluate_54gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/54 "
                f"g53_to_g54_all_passed={report.g53_to_g54_all_passed} "
                f"all_54_gates_verified={report.all_54_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_54_gates_verified if args.dry_run_simulated_backup else report.offline_51_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g55-c2pa-cert":
        verdict, res = evaluate_g55_c2pa_cert(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.c2pa_rq_lic_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} p12_flags={guard['p12_cert_mount_flags']} "
                f"cert_mut={guard['c2pa_cert_mutation_bytes']}B "
                f"rq_lic_h0_h3={guard['rq_lic_h0_to_h3_preserved']} "
                f"signing={guard['signing_model_name']}({guard['signing_model_id_hex']}) "
                f"cross_model_blocked={guard['c2pa_cross_model_signing_blocked']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g56-tc-gyro-meta":
        verdict, res = evaluate_g56_tc_gyro_meta(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.tc_gyro_meta_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} adapter={guard['adapter_name']}({guard['tc_sync_mode']}) "
                f"ltc_vpp={guard['ltc_peak_to_peak_mv']}mV uart1v8={guard['multi_usb_uart_1v8_active']} "
                f"tc_out_masked={guard['fx6_tc_out_bnc_masked']} "
                f"rs={guard['imx510_rolling_shutter_ms']}ms "
                f"imu={guard['imu_axes']}axis@{guard['imu_sample_rate_hz']}Hz "
                f"nrtm_ok={guard['nrtm_xml_validated']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-56-gates":
        report = evaluate_56gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/56 "
                f"g55_to_g56_all_passed={report.g55_to_g56_all_passed} "
                f"all_56_gates_verified={report.all_56_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_56_gates_verified if args.dry_run_simulated_backup else report.offline_53_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g57-dualmedia-vault":
        verdict, res = evaluate_g57_dualmedia_vault(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.dualmedia_vault_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} st_dev={guard['media_a_st_dev']}/{guard['media_b_st_dev']} "
                f"sep={guard['device_ids_separated']} "
                f"parity={guard['parity_matched_count']}/{guard['expected_surface_count']} "
                f"gf256={guard['gf256_primitive_poly_hex']} unrec={guard['unrecoverable_chunk_count']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g58-bench-interlock":
        verdict, res = evaluate_g58_bench_interlock(
            repo_root=args.repo_root,
            force_clean_room=True if args.clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.bench_interlock_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} auto_flash_blocked={guard['agent_auto_flash_blocked']} "
                f"two_step_armed={guard['two_step_interlock_armed']} "
                f"batt={guard['battery_soc_pct']:.0f}%/{guard['battery_mv']}mV "
                f"canary_ok={guard['op_ff_ram_canary_verified']} "
                f"fx3rcpt1_match={guard['dual_media_fx3rcpt1_match']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-58-gates":
        report = evaluate_58gate_preflight(
            args.repo_root,
            force_clean_room=True if args.clean_room else None,
            dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/58 "
                f"g57_to_g58_all_passed={report.g57_to_g58_all_passed} "
                f"all_58_gates_verified={report.all_58_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
            )
        ok = report.all_58_gates_verified if args.dry_run_simulated_backup else report.offline_55_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g59-ssboot-wbi2-guard":
        verdict, res = evaluate_g59_ssboot_wbi2_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.ssboot_wbi2_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} dev={guard['wbi_partition_dev']} "
                f"magic=0x{guard['wbi2_magic_hex']} "
                f"blkroset=({guard['blkroset_nflasha5']},{guard['blkroset_pnflasha5']}) "
                f"wbi_writes={guard['wbi_persistent_writes']} "
                f"h0_eq_h3={guard['h0_equals_h3_wbi2']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g60-slot1-ufu-c2pa-guard":
        verdict, res = evaluate_g60_slot1_ufu_c2pa_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.slot1_ufu_c2pa_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} body_ver={guard['body_firmware_version']}(>={guard['min_body_firmware_floor']}) "
                f"ufu={guard['target_ufu_version']}({guard['bodydata_size_bytes']}B) "
                f"slot={guard['update_slot']}:{guard['bodydata_path']} "
                f"c2pa_lic={guard['c2pa_license_count']}/{guard['c2pa_max_licenses_ceiling']} "
                f"p12_ro={guard['p12_blkroset']} wifi_ok={guard['wireless_security_floor_valid']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-60-gates":
        report = evaluate_60gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/60 "
                f"g59_to_g60_all_passed={report.g59_to_g60_all_passed} "
                f"all_60_gates_verified={report.all_60_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_60_gates_verified if args.dry_run_simulated else report.offline_57_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g61-emount-breathing-guard":
        verdict, res = evaluate_g61_emount_breathing_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.emount_breathing_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} platform={guard['platform_name']} "
                f"lens_id={guard['lens_id_hex']}(first_party={guard['is_sony_first_party_lens']}) "
                f"bkid={guard['bkid_breathing_hex']} mc_ver={guard['monitor_control_version']} "
                f"p18_blkroset={guard['p18_blkroset']} lens_writes={guard['lens_partition_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g62-hdmi-raw-guard":
        verdict, res = evaluate_g62_hdmi_raw_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.hdmi_raw_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} hdmi={guard['hdmi_raw_width']}x{guard['hdmi_raw_height']}@{guard['hdmi_raw_fps']}fps/{guard['hdmi_raw_bit_depth']}b "
                f"braw_fw={guard['braw_video_assist_fw']} atomos_fw={guard['atomos_fw_version']} "
                f"sdi_mmio_probes={guard['sdi_mmio_probes_emitted']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-62-gates":
        report = evaluate_62gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/62 "
                f"g61_to_g62_all_passed={report.g61_to_g62_all_passed} "
                f"all_62_gates_verified={report.all_62_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_62_gates_verified if args.dry_run_simulated else report.offline_59_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g63-fx3a-branch-firewall":
        verdict, res = evaluate_g63_fx3a_branch_firewall(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.fx3a_branch_firewall
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} body={guard['body_model_name']}({guard['body_model_id_hex']}) "
                f"fw={guard['body_firmware_version']} lcd={guard['lcd_dot_count']} "
                f"nfc={guard['nfc_hardware_present']} ir={guard['ir_receiver_present']} "
                f"bodydata_ver={guard['bodydata_version']}({guard['bodydata_branch']}) "
                f"camset_isolated={guard['camset_isolation_valid']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g64-xlrh1-mishoe-guard":
        verdict, res = evaluate_g64_xlrh1_mishoe_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.xlrh1_mishoe_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} handle={guard['handle_model']}(on={guard['handle_audio_enabled']}) "
                f"fmt={guard['audio_format_mode']} hp={guard['headphone_monitor_matrix']} "
                f"body_35mm={guard['body_35mm_mic_plugged']} sq={guard['sq_mode_active']}(muted={guard['mi_shoe_audio_muted']}) "
                f"48v_glitches={guard['phantom_48v_glitch_events']} usb_fw_guard={guard['usb_fw_payload_guard_valid']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-64-gates":
        report = evaluate_64gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/64 "
                f"g63_to_g64_all_passed={report.g63_to_g64_all_passed} "
                f"all_64_gates_verified={report.all_64_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_64_gates_verified if args.dry_run_simulated else report.offline_61_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g65-nouvc-dcc1-pd":
        verdict, res = evaluate_g65_nouvc_dcc1_pd_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.nouvc_dcc1_pd_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} body={guard['body_model_name']}({guard['body_model_id_hex']}) "
                f"usb_mode={guard['usb_connection_mode']} uvc_blocked={guard['uvc_gadget_blocked']} "
                f"stream={guard['streaming_transport']}@{guard['streaming_bitrate_mbps']:.1f}Mbps "
                f"power={guard['power_source']} np_fz100={guard['np_fz100_inserted']} "
                f"batt={guard['battery_pct']}% pd_w={guard['usb_pd_watts']:.0f}W "
                f"5a={guard['emarked_5a_cable']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g66-lut-path-cineei-bt":
        verdict, res = evaluate_g66_lut_path_cineei_bt_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.lut_path_cineei_bt_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} cube={guard['lut_3d_size']}pt "
                f"slot={guard['lut_slot_index']}/{guard['registered_lut_count']} "
                f"media={guard['media_type']}:{guard['lut_directory']} "
                f"cine_ei={guard['cine_ei_base_iso']}->{guard['cine_ei_index']} "
                f"bt_rmt={guard['bluetooth_rmt_ctrl_enabled']}(ir_off={guard['ir_remote_receiver_disabled']}, "
                f"gps={guard['smartphone_gps_location_link_active']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-66-gates":
        report = evaluate_66gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/66 "
                f"g65_to_g66_all_passed={report.g65_to_g66_all_passed} "
                f"all_66_gates_verified={report.all_66_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_66_gates_verified if args.dry_run_simulated else report.offline_63_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g67-usblan-rtmp":
        verdict, res = evaluate_g67_usblan_rtmp_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.usblan_rtmp_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} body={guard['body_model_name']}({guard['body_model_id_hex']}) "
                f"fw={guard['firmware_version']} usblan={guard['usblan_protocol']}/{guard['adapter_chipset']} "
                f"power={guard['power_mode']} setting_ro={guard['stock_setting_protected']} "
                f"stream={guard['streaming_protocol']}/{guard['streaming_codec']}@{guard['streaming_bitrate_mbps']:.1f}Mbps "
                f"tls_erofs={guard['tls_erofs_valid']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g68-clipflag-anamorphic":
        verdict, res = evaluate_g68_clipflag_anamorphic_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.clipflag_anamorphic_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} creators_app={guard['creators_app_version']} "
                f"m_and_c={guard['monitor_control_version']} clip_flag={guard['clip_flag']} "
                f"sidecar_only={guard['sidecar_metadata_only']} "
                f"anamorphic={guard['anamorphic_desqueeze_ratio']}x "
                f"hdmi_raw_unscaled={guard['hdmi_raw_linear_unscaled']} "
                f"soc={guard['soc_name']} bright={guard['bright_monitoring_active']} "
                f"magnifier={guard['focus_magnifier_factor']}x "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-68-gates":
        report = evaluate_68gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/68 "
                f"g67_to_g68_all_passed={report.g67_to_g68_all_passed} "
                f"all_68_gates_verified={report.all_68_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_68_gates_verified if args.dry_run_simulated else report.offline_65_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g69-fan-pwm-thermal":
        verdict, res = evaluate_g69_fan_pwm_thermal_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.fan_pwm_thermal_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} body={guard['body_model_name']}({guard['body_model_id_hex']}) "
                f"fw={guard['firmware_version']} fan={guard['canonical_fan_mode']} "
                f"pwm={guard['observed_pwm_duty_pct']}% "
                f"off_in_rec_rec={guard['off_in_rec_recording_normal_pwm_pct']}% "
                f"off_in_rec_stby={guard['off_in_rec_standby_pwm_pct']}% "
                f"apo_temp={guard['auto_power_off_temp']} "
                f"cxd90057={guard['cxd90057_temp_c']:.1f}C cxd90058={guard['cxd90058_temp_c']:.1f}C "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g70-lut-601-702-shutter-angle":
        verdict, res = evaluate_g70_lut_split_shutter_angle_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.lut_split_shutter_angle_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} lut_split={guard['donor_stageb_fw_version']}->{guard['host_stock_fx3_fw_version']} "
                f"slot={guard['lut_slot_name']} overlay={guard['volatile_lut_overlay_redirected']} "
                f"h0_eq_h3={guard['h0_equals_h3_p2_setting']} "
                f"shutter={guard['shutter_mode']} angle={guard['shutter_angle_deg']}deg/{guard['shutter_frames_count']}F "
                f"fps={guard['rec_frame_rate']} step={guard['exposure_step_ev']}EV "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-70-gates":
        report = evaluate_70gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/70 "
                f"g69_to_g70_all_passed={report.g69_to_g70_all_passed} "
                f"all_70_gates_verified={report.all_70_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_70_gates_verified if args.dry_run_simulated else report.offline_67_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g71-big6-noend-camset-slot1":
        verdict, res = evaluate_g71_big6_noend_camset_slot1_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.big6_noend_camset_slot1_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} body={guard['body_model_name']}({guard['body_model_id_hex']}) "
                f"fw={guard['firmware_version']} big6={guard['canonical_mode_settings']}/"
                f"{guard['canonical_home_lower_left_item']} e_nd_tx={guard['e_nd_actuator_tx_count']} "
                f"camset=Slot{guard['camset_slot_index']}:{guard['canonical_media_type']}:"
                f"{guard['camset_directory']}{guard['camset_filename']} "
                f"overlay={guard['stageb_camset_sandboxed_in_tmp']} "
                f"h0_eq_h3={guard['h0_equals_h3_camset_surface']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g72-vmcbncm1-tcin-hdmi-tcout":
        verdict, res = evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.vmcbncm1_tcin_hdmi_tcout_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} adapter={guard['adapter_model']}({guard['adapter_part_number']}) "
                f"port={guard['canonical_usb_port']} xlr_h1_blocked={guard['xlr_h1_handle_micro_usb_blocked']} "
                f"dir={guard['tc_signal_direction']} ext_lk={guard['modeled_ext_lk_state']}@"
                f"{guard['continuous_ltc_lock_seconds']:.1f}s "
                f"bnc_mask={guard['stageb_bnc_tcout_mask_errno_name']} "
                f"tcout={guard['canonical_tc_out_transport']}(on={guard['tc_out_enabled']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-72-gates":
        report = evaluate_72gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/72 "
                f"g71_to_g72_all_passed={report.g71_to_g72_all_passed} "
                f"all_72_gates_verified={report.all_72_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_72_gates_verified if args.dry_run_simulated else report.offline_69_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g73-desqueeze-focusmap":
        verdict, res = evaluate_g73_desqueeze_focusmap_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.desqueeze_focusmap_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} body={guard['body_model_name']}({guard['body_model_id_hex']}) "
                f"fw={guard['firmware_version']} desqueeze={guard['canonical_desqueeze_option']}->"
                f"{guard['effective_horizontal_factor']:.2f}x "
                f"suppressed={guard['desqueeze_auto_suppressed']} 4locks={guard['four_locks_enforced']} "
                f"focus_map={guard['canonical_focus_map_target']}@{guard['frame_rate_fps']:.2f}fps "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g74-simult-autoswitch-shocklesswb":
        verdict, res = evaluate_g74_simult_autoswitch_shocklesswb_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.simult_autoswitch_shocklesswb_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} rec_mode={guard['canonical_rec_media_mode']} "
                f"auto_switch={guard['auto_switch_media_enabled']} "
                f"strict_parity={guard['strict_dual_vault_parity_required']} "
                f"state={guard['modeled_dual_slot_state']} slots={guard['active_recording_slot_count']} "
                f"shockless_wb={guard['canonical_shockless_wb_level']}/"
                f"{guard['canonical_wb_operation_type']}@{guard['observed_wb_ramp_frames']}F "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-74-gates":
        report = evaluate_74gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/74 "
                f"g73_to_g74_all_passed={report.g73_to_g74_all_passed} "
                f"all_74_gates_verified={report.all_74_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_74_gates_verified if args.dry_run_simulated else report.offline_71_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g75-hdmi-log1080-hdmionly":
        verdict, res = evaluate_g75_hdmi_log1080_hdmionly_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.hdmi_log1080_hdmionly_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} rec_dur_hdmi={guard['canonical_rec_media_dur_hdmi']} "
                f"log={guard['canonical_log_shooting_mode']} pp={guard['canonical_picture_profile']} "
                f"hdmi_eff={guard['modeled_effective_hdmi_output']} "
                f"downshift1080p={guard['log_or_pplut_1080p_downshift_active']} "
                f"card_rec={guard['internal_card_recording_active']} "
                f"lcd_blanked={guard['camera_lcd_panel_blanked']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g76-proxy-focusmag-brightmon":
        verdict, res = evaluate_g76_proxy_focusmag_brightmon_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.proxy_focusmag_brightmon_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} proxy={guard['canonical_proxy_format']}/"
                f"{guard['canonical_proxy_setting']}({guard['proxy_width']}x{guard['proxy_height']}) "
                f"coupled_del={guard['coupled_vault_delete_parity']} "
                f"coupled_prot={guard['coupled_vault_protect_parity']} "
                f"focus_mag={guard['canonical_initial_focus_mag']} "
                f"bright_mon={guard['bright_monitoring_active']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-76-gates":
        report = evaluate_76gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/76 "
                f"g75_to_g76_all_passed={report.g75_to_g76_all_passed} "
                f"all_76_gates_verified={report.all_76_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_76_gates_verified if args.dry_run_simulated else report.offline_73_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g77-filesettings-shotmark":
        verdict, res = evaluate_g77_filesettings_shotmark_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.filesettings_shotmark_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} fmt={guard['effective_file_name_format']} "
                f"sdhc_lock={guard['sdhc_standard_lock_active']} "
                f"fnum={guard['canonical_file_number_mode']}->#{guard['modeled_next_clip_number']:04d} "
                f"title_len={guard['title_name_length']} "
                f"jump={guard['canonical_image_jump_setting']}({guard['image_jump_matched']}) "
                f"xfer={guard['canonical_transfer_target_movie']}({guard['transfer_filter_eligible']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g78-tcregen-reclamp":
        verdict, res = evaluate_g78_tcregen_reclamp_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.tcregen_reclamp_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} tc_make={guard['canonical_time_code_make']}->"
                f"{guard['effective_time_code_run']}(src={guard['regenerate_reference_slot']}) "
                f"ext_lk={guard['modeled_ext_lk_active']} "
                f"rec_lamp={guard['canonical_rec_lamp_mode']}("
                f"F={guard['front_tally_led_on']},R={guard['rear_tally_led_on']},"
                f"Top={guard['top_rec_button_led_on']}) "
                f"silent={guard['silent_mode_on']}(audio_sig={guard['effective_audio_signals_on']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-78-gates":
        report = evaluate_78gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/78 "
                f"g77_to_g78_all_passed={report.g77_to_g78_all_passed} "
                f"all_78_gates_verified={report.all_78_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_78_gates_verified if args.dry_run_simulated else report.offline_75_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g79-pixelmap-cnflasha":
        verdict, res = evaluate_g79_pixelmap_reboot_cnflasha_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.pixelmap_cnflasha_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} auto_pixel_map={guard['auto_pixel_mapping_on']}"
                f"(shutter_snd={guard['power_off_shutter_sound_expected']}) "
                f"manual={guard['manual_pixel_mapping_requested']}"
                f"(soc={guard['battery_soc_pct']}%,ctrl_lock={guard['operator_controls_locked_during_exec']},"
                f"reboot={guard['auto_camera_restart_on_completion']},h0_eq_h2={guard['h0_equals_h2_post_reboot']}) "
                f"cnflasha_ro={guard['cnflasha_userspace_write_blocked']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g80-ntscpal-gammaassist-displaylut":
        verdict, res = evaluate_g80_ntscpal_gammaassist_displaylut_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.ntscpal_gammaassist_displaylut_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} system={guard['effective_post_reset_system']}"
                f"(fps={guard['selected_frame_rate']},tc={guard['selected_tc_format']},"
                f"banner={guard['startup_notification_banner']}) "
                f"log={guard['canonical_log_shooting_mode']}"
                f"(gov={guard['active_preview_governor']},"
                f"gamma_assist={guard['effective_gamma_display_assist_on']},"
                f"display_lut={guard['effective_display_lut_preview_on']},"
                f"hdmi_gamma={guard['external_hdmi_gamma_assist_applied']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-80-gates":
        report = evaluate_80gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/80 "
                f"g79_to_g80_all_passed={report.g79_to_g80_all_passed} "
                f"all_80_gates_verified={report.all_80_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_80_gates_verified if args.dry_run_simulated else report.offline_77_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g81-steadyshot-ciz":
        verdict, res = evaluate_g81_steadyshot_ciz_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.steadyshot_ciz_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} ss={guard['canonical_steadyshot_mode']}"
                f"(crop={guard['active_narrower_aov_crop_factor']}x,"
                f"disq={guard['steadyshot_active_disqualified']}) "
                f"zoom={guard['zoom_range_setting']}/{guard['active_zoom_domain']}"
                f"(scale={guard['non_optical_zoom_scale']}x,"
                f"4locks={guard['all_4_non_optical_zoom_locks_enforced']},"
                f"meter={guard['effective_metering_mode']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g82-powersave-autotemp":
        verdict, res = evaluate_g82_powersave_autotemp_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.powersave_autotemp_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} psave={guard['configured_power_save_start_time']}"
                f"(bypass={guard['active_bypass_condition_count']}/9,"
                f"airgap_safe={guard['airgapped_tier0_sleep_safe']}) "
                f"autotemp={guard['auto_power_off_temp']}"
                f"(tripod={guard['tripod_mounted']},fan={guard['fan_control_mode']},"
                f"soc={guard['soc_temp_c']}C) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-82-gates":
        report = evaluate_82gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/82 "
                f"g81_to_g82_all_passed={report.g81_to_g82_all_passed} "
                f"all_82_gates_verified={report.all_82_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_82_gates_verified if args.dry_run_simulated else report.offline_79_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g83-sq-fixedvar-zebra-peaking":
        verdict, res = evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.sq_fixedvar_zebra_peaking_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} sq_mode={guard['sq_mode_settings']}"
                f"(sq_locked={guard['legacy_sq_settings_menu_locked']},"
                f"fps={guard['sq_capture_fps']}fps@{guard['movie_file_format']},"
                f"6locks={guard['all_6_sq_locks_enforced']}) "
                f"cleanfeed={guard['hdmi_assist_clean_feed_enforced']}"
                f"(hdmi_zebra={guard['hdmi_zebra_overlay_rendered']},"
                f"hdmi_peaking={guard['hdmi_peaking_overlay_rendered']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g84-zebra-reset-fullformat-chord":
        verdict, res = evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.zebra_reset_fullformat_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} zebra={guard['effective_post_reset_zebra_display']}/"
                f"{guard['effective_post_reset_zebra_level']}(rst={guard['reset_action']},"
                f"survived={guard['zebra_survived_camera_settings_reset']}) "
                f"slot1_vault_lock={guard['slot1_format_hard_locked']}"
                f"(slot={guard['target_slot']},trig={guard['format_trigger']},fmt={guard['format_mode']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-84-gates":
        report = evaluate_84gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/84 "
                f"g83_to_g84_all_passed={report.g83_to_g84_all_passed} "
                f"all_84_gates_verified={report.all_84_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_84_gates_verified if args.dry_run_simulated else report.offline_81_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g85-silent-autopixelmap-no-pwrshutter":
        verdict, res = evaluate_g85_silent_autopixelmap_no_pwrshutter_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.silent_autopixelmap_no_pwrshutter_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} silent={guard['silent_mode']}"
                f"(shutter={guard['effective_shutter_type']},audio={guard['effective_audio_signals']},"
                f"5locks={guard['all_5_functions_disabled_in_silent']}) "
                f"target_apm={guard['target_auto_pixel_mapping']}"
                f"(suppressed={guard['bench_shutdown_autopixelmap_suppressed']}) "
                f"no_pwr_shutter={guard['shutter_when_pwr_off_absent_verified']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g86-marker-hdmi-flexexp-reset":
        verdict, res = evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.marker_hdmi_flexexp_reset_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} marker={guard['effective_post_reset_marker_display']}/"
                f"{guard['effective_post_reset_aspect_marker']}(ratios={guard['aspect_marker_15_ratio_count']},"
                f"hdmi_marker={guard['hdmi_marker_overlay_rendered']},rst={guard['reset_action']},"
                f"survived={guard['marker_survived_camera_settings_reset']}) "
                f"flex_exp={guard['exposure_ctrl_type']}(Av={guard['effective_post_reset_flex_av_mode']},"
                f"Tv={guard['effective_post_reset_flex_tv_mode']},ISO={guard['effective_post_reset_flex_iso_mode']},"
                f"AutoSlow={guard['effective_post_reset_auto_slow_shutter']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-86-gates":
        report = evaluate_86gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/86 "
                f"g85_to_g86_all_passed={report.g85_to_g86_all_passed} "
                f"all_86_gates_verified={report.all_86_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_86_gates_verified if args.dry_run_simulated else report.offline_83_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g87-recover-imagedb-battery-vault":
        verdict, res = evaluate_g87_recover_imagedb_battery_and_tier0_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.recover_imagedb_battery_vault_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} slot={guard['target_slot']} "
                f"executed={guard['recover_executed']} "
                f"deleted={guard['recorded_clips_deleted']} "
                f"battery={guard['battery_soc_pct']}%/{guard['battery_mv']}mV "
                f"slot1_vault_blocked={guard['slot1_recover_imagedb_hard_blocked']} "
                f"slot1_writes={guard['slot1_metadata_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g88-monitor-flip-af-sens-interval":
        verdict, res = evaluate_g88_monitor_flip_af_sens_and_interval_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
        else:
            guard = res.monitor_flip_af_sens_interval_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} flip={guard['effective_post_reset_monitor_flip_direction']}"
                f"(pb_inv={guard['playback_monitor_horizontally_inverted']},rst={guard['reset_action']},"
                f"survived={guard['monitor_flip_survived_camera_settings_reset']}) "
                f"af=({guard['effective_post_reset_af_subj_shift_label']},"
                f"{guard['effective_post_reset_af_transition_label']}) "
                f"interval={guard['interval_capture_format']}"
                f"(start={guard['shooting_start_time_seconds']}s,"
                f"step={guard['shooting_interval_seconds']}s) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-88-gates":
        report = evaluate_88gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/88 "
                f"g87_to_g88_all_passed={report.g87_to_g88_all_passed} "
                f"all_88_gates_verified={report.all_88_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_88_gates_verified if args.dry_run_simulated else report.offline_85_gates_verified
        return 0 if ok else 1

    if args.cmd == "verify-g89-emphasized-rec-grid-hdmi":
        verdict, res = evaluate_g89_emphasized_rec_and_grid_hdmi_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.emphasized_rec_grid_hdmi_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} emp_rec={guard['effective_post_reset_emphasized_rec_display']} "
                f"grid={guard['effective_post_reset_grid_line_display']}/"
                f"{guard['effective_post_reset_grid_line_type']}(rst={guard['reset_action']}, "
                f"survived={guard['grid_line_survived_camera_settings_reset']}) "
                f"hdmi_info={guard['configured_hdmi_info_display']}->{guard['effective_hdmi_info_display']}"
                f"(clamp={guard['hdmi_clean_feed_clamp_active']},baked_px={guard['hdmi_baked_overlay_pixels']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-g90-touch-op-sunny-weather":
        verdict, res = evaluate_g90_touch_op_reset_and_sunny_weather_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.touch_op_sunny_weather_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} touch_op={guard['effective_post_reset_touch_operation']}"
                f"(sens={guard['effective_post_reset_touch_sensitivity']},"
                f"swipe={guard['effective_post_reset_swipe_up']},"
                f"func={guard['effective_post_reset_touch_func_in_shooting']},"
                f"rst={guard['reset_action']},"
                f"bench_locked={guard['shooting_capacitive_touch_locked']}) "
                f"brightness={guard['effective_post_reset_monitor_brightness_mode']}"
                f"({guard['effective_post_reset_manual_brightness_level']},"
                f"sunny_blocked={guard['sunny_weather_indoor_blocked']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-90-gates":
        report = evaluate_90gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/90 "
                f"g89_to_g90_all_passed={report.g89_to_g90_all_passed} "
                f"all_90_gates_verified={report.all_90_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_90_gates_verified if args.dry_run_simulated else report.offline_87_gates_verified
        return 0 if ok else 1

    if args.cmd in ("verify-shoe-audio-wind-guard", "verify-g91-shoe-audio-wind"):
        verdict, res = evaluate_g91_shoe_audio_and_wind_noise_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.shoe_audio_wind_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} shoe_audio={guard['effective_post_reset_shoe_audio_set']}"
                f"->{guard['effective_audio_format']}"
                f"(src={guard['active_audio_input_source']},"
                f"rec_ch={guard['effective_recorded_audio_channels']},"
                f"meter_ch={guard['audio_level_meter_channels']},"
                f"meter_4ch_expanded={guard['four_ch_audio_level_meter_expanded']}) "
                f"wind={guard['effective_post_reset_wind_noise_reduct']}"
                f"(ext_eff={guard['external_mic_wind_reduct_effective']},"
                f"builtin_eff={guard['builtin_mic_wind_reduct_effective']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in ("verify-saveload-c3-exclusions-guard", "verify-g92-saveload-c3-exclusions"):
        verdict, res = evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.saveload_c3_exclusions_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} op={guard['saveload_operation']}@{guard['saveload_target']}"
                f"({guard['camset_filename']},hdr={guard['profile_model_header']},"
                f"same_model={guard['same_model_ilme_fx3_locked']}) "
                f"exclusions_ok={guard['excluded_items_firewall_enforced']} "
                f"load_rdonly={guard['load_is_card_o_rdonly_safe']} "
                f"slot1_save_blocked={guard['slot1_unverified_camset_save_blocked']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-92-gates":
        report = evaluate_92gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/92 "
                f"g91_to_g92_all_passed={report.g91_to_g92_all_passed} "
                f"all_92_gates_verified={report.all_92_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_92_gates_verified if args.dry_run_simulated else report.offline_89_gates_verified
        return 0 if ok else 1

    if args.cmd in ("verify-framing-antiflicker-guard", "verify-g93-framing-antiflicker"):
        verdict, res = evaluate_g93_framing_and_antiflicker_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.framing_antiflicker_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} framing={guard['effective_post_reset_framing']}"
                f"(rec={guard['effective_post_reset_recording_streaming']},"
                f"hdmi={guard['effective_post_reset_hdmi']},"
                f"asym_default={guard['framing_asymmetric_factory_default_preserved']},"
                f"raw_conflict_blocked={guard['hdmi_raw_framing_conflict_blocked']}) "
                f"antiflicker={guard['effective_post_reset_anti_flicker_shoot']}"
                f"(func={guard['anti_flicker_functional']},"
                f"has_var_shutter={guard['fx3_has_var_shutter']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in ("verify-usbpower-lun-guard", "verify-g94-usbpower-lun"):
        verdict, res = evaluate_g94_usb_power_and_lun_persistence_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.usb_power_lun_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} usb_pwr={guard['effective_post_reset_usb_power_supply']}"
                f"(bay={guard['battery_bay_source']},port={guard['usb_power_port']},"
                f"bus_pwr_active={guard['effective_usb_bus_power_active']}) "
                f"lun={guard['effective_post_reset_usb_lun_setting']}"
                f"(luns={guard['effective_msc_exposed_lun_count']},"
                f"survives_reset={guard['usb_setup_survives_camera_settings_reset']}) "
                f"usb_packets_transmitted={res.usb_packets_transmitted} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-94-gates":
        report = evaluate_94gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/94 "
                f"g93_to_g94_all_passed={report.g93_to_g94_all_passed} "
                f"all_94_gates_verified={report.all_94_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_94_gates_verified if args.dry_run_simulated else report.offline_91_gates_verified
        return 0 if ok else 1

    if args.cmd in ("verify-lock-op-parts-chord-guard", "verify-g95-lock-op-parts-chord"):
        verdict, res = evaluate_g95_lock_operation_parts_and_chord_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.lock_op_parts_chord_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} lock_op_parts={guard['effective_post_reset_lock_operation_parts']}"
                f"(survives_reset={guard['lock_op_parts_survives_camera_settings_reset']},"
                f"fn_engaged={guard['fn_hold_lock_engaged']},"
                f"osd={guard['locked_osd_banner']!r}) "
                f"menu_fn_5s={guard['menu_fn_5s_full_body_lock_engaged']}"
                f"(hold={guard['chord_hold_seconds']:.1f}s,"
                f"shutter_unlocked={guard['shutter_button_remains_unlocked']},"
                f"menu_del_blocked={guard['destructive_menu_delete_chord_blocked']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in ("verify-audio-timing-exp-step-guard", "verify-g96-audio-timing-exp-step"):
        verdict, res = evaluate_g96_audio_timing_signals_and_exp_step_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.audio_timing_exp_step_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} audio_timing={guard['effective_post_reset_audio_out_timing']}"
                f"(avail={guard['audio_out_timing_available']}) "
                f"audio_signals={guard['effective_audio_signals']}"
                f"(survives_reset={guard['audio_signals_survives_camera_settings_reset']},"
                f"silent_locked={guard['audio_signals_locked_off_by_silent_mode']}) "
                f"exp_step={guard['effective_post_reset_exposure_step']}"
                f"(shutter_angle_unaffected={guard['shutter_angle_unaffected_by_exposure_step']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-96-gates":
        report = evaluate_96gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/96 "
                f"g95_to_g96_all_passed={report.g95_to_g96_all_passed} "
                f"all_96_gates_verified={report.all_96_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_96_gates_verified if args.dry_run_simulated else report.offline_93_gates_verified
        return 0 if ok else 1

    if args.cmd in ("verify-display-quality-bt-rmt-guard", "verify-g97-display-quality-bt-rmt"):
        verdict, res = evaluate_g97_display_quality_and_bt_rmt_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.display_quality_bt_rmt_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} display_quality={guard['effective_post_reset_display_quality']}"
                f"(tier0_clamped={guard['tier0_battery_clamped_to_standard_and_manual0']},"
                f"batt_viol={guard['tier0_battery_high_display_violations']}) "
                f"bt_rmt={guard['effective_post_reset_bt_rmt_ctrl']}"
                f"(active={guard['effective_bt_rmt_ctrl_active']},"
                f"airplane={guard['airplane_mode']},"
                f"tx={guard['passive_tx_bytes_emitted']},"
                f"ir_viol={guard['bt_rmt_ir_lockout_violations']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in ("verify-mymenu-camset-firewall-guard", "verify-g98-mymenu-camset"):
        verdict, res = evaluate_g98_mymenu_and_camset_firewall_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.mymenu_camset_firewall_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} mymenu_pages={guard['effective_post_reset_page_count']}"
                f"(items={guard['effective_post_reset_total_items']},"
                f"dfmm={guard['effective_post_reset_display_from_my_menu']},"
                f"open={guard['menu_button_open_target']}) "
                f"slot1_camset={guard['slot1_camset_filename']}"
                f"(op={guard['slot1_camset_operation']},"
                f"mut_bytes={guard['slot1_mymenu_vault_mutation_bytes']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-98-gates":
        report = evaluate_98gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/98 "
                f"g97_to_g98_all_passed={report.g97_to_g98_all_passed} "
                f"all_98_gates_verified={report.all_98_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_98_gates_verified if args.dry_run_simulated else report.offline_95_gates_verified
        return 0 if ok else 1

    if args.cmd in ("verify-diff-set-still-mv-shutter-angle-guard", "verify-g99-diff-set-still-mv"):
        verdict, res = evaluate_g99_diff_set_still_mv_and_shutter_angle_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.diff_set_still_mv_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} checked={len(guard['effective_post_reset_checked_items'])}/8"
                f"(transition={guard['transition_mode']},"
                f"corrupt={guard['diff_set_transition_corruption_events']}) "
                f"shutter_mode={guard['movie_shutter_mode']}"
                f"(indep={guard['effective_shutter_still_movie_independent']},"
                f"bleed={guard['shutter_angle_common_bleed_events']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in ("verify-custom-key-dial-remain-shoot-guard", "verify-g100-custom-key-remain-shoot"):
        verdict, res = evaluate_g100_custom_key_dial_and_remain_shoot_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.custom_key_remain_shoot_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} rear_dial={guard['effective_rear_dial_target']}"
                f"(log={guard['log_shooting_mode']},"
                f"camset={guard['slot1_camset_filename']},"
                f"mut_bytes={guard['slot1_custom_key_vault_mutation_bytes']}) "
                f"remain_shoot={guard['effective_post_reset_remain_shoot_display']}"
                f"(evf={guard['fx3_has_builtin_evf']},"
                f"spoof={guard['evf_finder_monitor_spoof_events']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-100-gates":
        report = evaluate_100gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/100 "
                f"g99_to_g100_all_passed={report.g99_to_g100_all_passed} "
                f"all_100_gates_verified={report.all_100_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_100_gates_verified if args.dry_run_simulated else report.offline_97_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-auto-slow-shutter-breathing-comp-guard",
        "verify-g101-auto-slow-shutter-breathing",
    ):
        verdict, res = evaluate_g101_auto_slow_shutter_and_breathing_comp_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.auto_slow_shutter_breathing_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} auto_slow_shutter={guard['effective_post_reset_auto_slow_shutter']}"
                f"(active={guard['auto_slow_shutter_effective_active']},"
                f"locks={len(guard['active_auto_slow_shutter_lockouts'])}/6,"
                f"bypass={guard['auto_slow_shutter_lockout_bypass_events']},"
                f"angle_overlap={guard['auto_slow_shutter_angle_overlap_events']}) "
                f"breathing_comp={guard['effective_post_reset_breathing_comp']}"
                f"(active={guard['breathing_comp_effective_active']},"
                f"bypass={guard['breathing_comp_raw_or_240p_bypass_events']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-hdmi-reccontrol-tcout-4chaudio-guard",
        "verify-g102-hdmi-reccontrol-4chaudio",
    ):
        verdict, res = evaluate_g102_hdmi_reccontrol_tcout_4chaudio_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.hdmi_reccontrol_4chaudio_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} rec_control={guard['effective_post_reset_rec_control']}"
                f"(tc_out={guard['effective_post_reset_time_code_output']},"
                f"tc_viol={guard['hdmi_rec_ctrl_without_tc_violations']}) "
                f"audio_4ch={guard['effective_hdmi_audio_output_pair']} "
                f"rec_media={guard['effective_post_reset_rec_media_dur_hdmi_output']}"
                f"(inhibited={guard['internal_slot1_slot2_recording_inhibited']},"
                f"mut_bytes={guard['slot1_hdmi_rec_vault_mutation_bytes']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-102-gates":
        report = evaluate_102gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/102 "
                f"g101_to_g102_all_passed={report.g101_to_g102_all_passed} "
                f"all_102_gates_verified={report.all_102_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_102_gates_verified if args.dry_run_simulated else report.offline_99_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-apsc-s35-face-eye-af-guard",
        "verify-g103-apsc-s35-face-eye-af",
    ):
        verdict, res = evaluate_g103_apsc_s35_and_face_eye_af_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.apsc_s35_face_eye_af_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} apsc_s35={guard['effective_apsc_s35_state']}"
                f"(locked_off={guard['apsc_s35_hardware_locked_to_off']},"
                f"bypass={guard['apsc_s35_4k_or_raw_bypass_events']}) "
                f"face_eye_af={guard['face_eye_af_menu_label']}"
                f"(spoof={guard['ai_unit_subject_recog_spoof_events']},"
                f"eye={guard['effective_post_reset_right_left_eye_select']},"
                f"clean_hdmi_baked={guard['hdmi_clean_feed_eye_frame_baked_pixels']},"
                f"face_memory={guard['effective_post_reset_registered_face_memory_count']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-version-readonly-bodydata-flash-block-guard",
        "verify-g104-version-bodydata-block",
    ):
        verdict, res = evaluate_g104_version_readonly_and_bodydata_flash_block_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.version_bodydata_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} body={guard['formatted_body_version']}"
                f"(flash_writes={guard['version_dialog_flash_writes']}) "
                f"airplane={guard['airplane_mode']}"
                f"(badge_suppressed={guard['update_notification_badge_suppressed']},"
                f"tx={guard['passive_tx_bytes_emitted']}) "
                f"bodydata_blocked={guard['bodydata_flash_attempts_blocked']}"
                f"(mut_bytes={guard['slot1_bodydata_vault_mutation_bytes']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-104-gates":
        report = evaluate_104gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/104 "
                f"g103_to_g104_all_passed={report.g103_to_g104_all_passed} "
                f"all_104_gates_verified={report.all_104_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_104_gates_verified if args.dry_run_simulated else report.offline_101_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-release-wo-card-lens-audio-disp-guard",
        "verify-g105-release-wo-card-audio-disp",
    ):
        verdict, res = evaluate_g105_release_wo_card_lens_and_v702_audio_disp_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.release_audio_disp_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} rel_wo_card={guard['effective_post_reset_release_wo_card']}"
                f"(cardless={guard['cardless_bench_active']},"
                f"mv_bypass={guard['movie_cardless_internal_rec_bypass_events']}) "
                f"rel_wo_lens={guard['effective_post_reset_release_wo_lens']}"
                f"(e_nd_tx={guard['e_nd_actuator_tx_count']},"
                f"lens_uart={guard['emount_lens_uart_tx_bytes']}) "
                f"audio_5items={guard['v702_audio_menu_exact_5_items_verified']}"
                f"(v1_spoof={guard['legacy_v1_audio_level_menu_spoof_events']},"
                f"disp_meter={guard['effective_audio_meter_channels']}ch) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-copyright-info-46char-exif-hygiene-guard",
        "verify-g106-copyright-info-hygiene",
    ):
        verdict, res = (
            evaluate_g106_copyright_info_46char_still_exif_and_pii_hygiene_guard(
                repo_root=args.repo_root,
                force_clean_room=True if args.force_clean_room else None,
            )
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.copyright_info_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} write_copyright={guard['effective_post_reset_write_copyright_info']}"
                f"(max_chars={guard['copyright_max_chars']},"
                f"pii_leaked={guard['photographer_copyright_pii_leaked_bytes']}) "
                f"container={guard['target_container']}"
                f"(still_exif={guard['still_exif_tags_written']},"
                f"mv_mut={guard['movie_or_raw_exif_mutation_bytes']},"
                f"slot1_mut={guard['slot1_recovery_vault_mutation_bytes']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-106-gates":
        report = evaluate_106gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/106 "
                f"g105_to_g106_all_passed={report.g105_to_g106_all_passed} "
                f"all_106_gates_verified={report.all_106_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_106_gates_verified if args.dry_run_simulated else report.offline_103_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-file-settings-dsc-slot1-vault-guard",
        "verify-g107-file-settings-vault",
    ):
        verdict, res = (
            evaluate_g107_movie_file_settings_still_dsc_and_slot1_vault_guard(
                repo_root=args.repo_root,
                force_clean_room=True if args.force_clean_room else None,
            )
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.file_settings_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} mv_fmt={guard['effective_post_reset_movie_file_name_format']}"
                f"(cam={guard['effective_post_reset_camera_id']}{guard['formatted_reel_number']}{guard['effective_post_reset_camera_position']},"
                f"title_len={guard['title_name_char_length']},"
                f"mv_dir={guard['movie_folder_path']}) "
                f"still_prefix={guard['effective_post_reset_still_set_file_name']}"
                f"(folder={guard['effective_post_reset_still_folder_name']},"
                f"slot1_mut={guard['slot1_vault_folder_mutation_events']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-gamma-disp-assist-auto-review-tcub-guard",
        "verify-g108-gamma-assist-tcub",
    ):
        verdict, res = (
            evaluate_g108_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
                repo_root=args.repo_root,
                force_clean_room=True if args.force_clean_room else None,
            )
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.gamma_assist_auto_review_tcub_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} log={guard['log_shooting_mode']}"
                f"(gamma_assist={guard['effective_gamma_display_assist']},"
                f"disp_lut={guard['effective_post_reset_display_lut']}/{guard['effective_post_reset_select_lut']},"
                f"hdmi_leak={guard['hdmi_gamma_assist_leak_frames']}) "
                f"auto_review={guard['effective_post_reset_auto_review']} "
                f"tc={guard['effective_tc_format']}/{guard['effective_post_reset_tc_run']}/{guard['effective_post_reset_tc_make']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-108-gates":
        report = evaluate_108gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/108 "
                f"g107_to_g108_all_passed={report.g107_to_g108_all_passed} "
                f"all_108_gates_verified={report.all_108_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_108_gates_verified if args.dry_run_simulated else report.offline_105_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-focus-mag-peaking-af-illuminator-guard",
        "verify-g109-focus-mag-peaking",
    ):
        verdict, res = evaluate_g109_focus_mag_peaking_af_illuminator_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.focus_mag_peaking_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} auto_mag={guard['effective_post_reset_auto_mag_in_mf']}"
                f"(btn={guard['focus_magnifier_custom_button']},time={guard['effective_post_reset_focus_mag_time']},spoof={guard['legacy_mf_assist_spoof_events']}) "
                f"init_mag=Still:{guard['effective_post_reset_still_initial_focus_mag']}/"
                f"Movie:{guard['effective_post_reset_movie_initial_focus_mag']} "
                f"peaking={guard['effective_post_reset_peaking_display']}"
                f"({guard['effective_post_reset_peaking_level']}/{guard['effective_post_reset_peaking_color']},"
                f"hdmi_leak={guard['hdmi_clean_feed_focus_mag_or_peaking_leak_pixels']}) "
                f"af_illum={guard['effective_post_reset_af_illuminator']}"
                f"(mv_sq_fire={guard['movie_sq_af_illuminator_fire_events']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-area-datetime-videolight-hdmires-guard",
        "verify-g110-datetime-videolight-hdmires",
    ):
        verdict, res = evaluate_g110_area_datetime_videolight_hdmires_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.area_datetime_videolight_hdmires_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} area_dt={guard['area_datetime_menu_label']}"
                f"(dst={guard['effective_post_reset_daylight_savings']},spoof={guard['legacy_datetime_setup_spoof_events']},"
                f"airplane={guard['airplane_mode']},tx={guard['passive_tx_bytes_emitted']},jumps={guard['unsolicited_rtc_timezone_jump_events']}) "
                f"vlight={guard['effective_post_reset_video_light_mode']}"
                f"(5v={guard['mishoe_5v_draw_ma']}/{guard['mishoe_5v_budget_ma']}mA) "
                f"hdmi_res={guard['effective_post_reset_hdmi_resolution']}->"
                f"{guard['effective_hdmi_output_resolution']}"
                f"(bypass={guard['hdmi_res_log_internal_rec_2160p_bypass_events']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-110-gates":
        report = evaluate_110gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/110 "
                f"g109_to_g110_all_passed={report.g109_to_g110_all_passed} "
                f"all_110_gates_verified={report.all_110_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_110_gates_verified if args.dry_run_simulated else report.offline_107_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-power-save-monitor-language-guard",
        "verify-g111-power-save-monitor-language",
    ):
        verdict, res = evaluate_g111_power_save_monitor_and_language_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.power_save_monitor_language_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} fx3_mon_ui={guard['fx3_ui_exposes_power_save_by_monitor']}"
                f"(items={len(guard['power_setting_option_items'])},spoof={guard['power_save_monitor_ui_spoof_events']},"
                f"appfw_modes={len(guard['appfw_monitor_power_linkage_modes'])}) "
                f"start_time={guard['effective_post_reset_power_save_start_time']}"
                f"(cond9={len(guard['nine_deactivation_conditions'])},idle_sleep={guard['battery_bench_idle_sleep_events']}) "
                f"lang={guard['effective_post_reset_language']}"
                f"(bk={guard['bk_lang_property_id_hex']},fx3={guard['fx3_language_count']},fx6={guard['fx6_language_count']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-volume-4chmon-delete-confirm-guard",
        "verify-g112-volume-4chmon-delete-confirm",
    ):
        verdict, res = evaluate_g112_volume_4chmon_delete_confirm_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.volume_4chmon_delete_confirm_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} vol={guard['effective_post_reset_volume_setting']}"
                f"(xlr_fb={guard['xlr_acoustic_feedback_events']}) "
                f"mon4ch={guard['effective_post_reset_4ch_audio_monitoring']}"
                f"(hp_ch={guard['headphone_35mm_output_channels']},hdmi={guard['hdmi_4ch_audio_output']}) "
                f"del_conf={guard['effective_post_reset_delete_confirm']}"
                f"(twice={guard['effective_post_reset_delete_pressing_twice']},"
                f"slot1_del={guard['slot1_vault_delete_events']},slot1_fmt_lock={guard['slot1_format_hard_locked']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-112-gates":
        report = evaluate_112gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/112 "
                f"g111_to_g112_all_passed={report.g111_to_g112_all_passed} "
                f"all_112_gates_verified={report.all_112_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_112_gates_verified if args.dry_run_simulated else report.offline_109_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-usb-mode-hdmi-info-guard",
        "verify-g113-usb-mode-hdmi-info",
    ):
        verdict, res = evaluate_g113_usb_mode_and_hdmi_info_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.usb_mode_hdmi_info_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} usb_modes={len(guard['fx3_stock_4_usb_modes'])}"
                f"(sel={guard['effective_post_reset_usb_connection_mode']},"
                f"nouvc_spoof={guard['usb_streaming_spoof_events']},"
                f"pd={guard['effective_post_reset_usb_power_supply']},"
                f"data_iso={guard['usb_data_lines_physically_isolated']}) "
                f"hdmi_info={guard['effective_hdmi_info_display']}"
                f"(lcd_blank={guard['lcd_blanked']},"
                f"out_res={guard['effective_hdmi_output_resolution']},"
                f"clean4k={guard['hdmi_clean_feed_4k_forced_off_active']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-protect-and-network-reset-guard",
        "verify-g114-protect-network-reset",
    ):
        verdict, res = evaluate_g114_protect_and_network_reset_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.protect_and_network_reset_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} scope={guard['protect_scope']}"
                f"(slot1_wp={guard['slot1_sd_physical_wp_locked']},"
                f"fmt_lock={guard['slot1_format_hard_locked']},"
                f"wp_viol={guard['slot1_wp_firewall_violation_events']}) "
                f"nw_reset_reboot={guard['auto_reboot_triggered']} "
                f"post_air={guard['post_reset_airplane_mode']}"
                f"(rf_haz={guard['post_network_reset_rf_hazard_events']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-114-gates":
        report = evaluate_114gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/114 "
                f"g113_to_g114_all_passed={report.g113_to_g114_all_passed} "
                f"all_114_gates_verified={report.all_114_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_114_gates_verified if args.dry_run_simulated else report.offline_111_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-pp-scinetone-creativelook-dro-guard",
        "verify-g115-pp-scinetone-creativelook-dro",
    ):
        verdict, res = evaluate_g115_pp_scinetone_creativelook_dro_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.pp_scinetone_creativelook_dro_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} pp={guard['effective_picture_profile']}"
                f"(diff={guard['different_set_pp_checked']},"
                f"internal_cleared={guard['pp_internal_params_cleared']}) "
                f"cl={guard['effective_creative_look']} dro={guard['effective_dro']} "
                f"log={guard['log_shooting']} "
                f"hdmi_out={guard['effective_hdmi_output_resolution']} "
                f"hdmi_clamp={guard['pplut_hdmi_1080p_clamped']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-wb-cineei-and-metering-guard",
        "verify-g116-wb-cineei-metering",
    ):
        verdict, res = evaluate_g116_wb_cineei_and_metering_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.wb_cineei_and_metering_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} wb={guard['effective_white_balance']}"
                f"(k={guard['color_temp_k']},priority={guard['effective_priority_set_in_awb']},"
                f"custom_camset_excl={guard['custom_wb_excluded_from_camset']}) "
                f"metering={guard['effective_metering_mode']}"
                f"(face={guard['effective_face_priority_in_multi']},"
                f"spot={guard['effective_spot_metering_point']},"
                f"mm_passive={guard['metering_drives_mm_monitoring_only']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-116-gates":
        report = evaluate_116gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/116 "
                f"g115_to_g116_all_passed={report.g115_to_g116_all_passed} "
                f"all_116_gates_verified={report.all_116_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_116_gates_verified if args.dry_run_simulated else report.offline_113_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-raw-heif-colorspace-guard",
        "verify-g117-raw-heif-colorspace",
    ):
        verdict, res = evaluate_g117_raw_heif_colorspace_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.raw_heif_colorspace_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} raw={guard['effective_raw_file_type']}"
                f"(2opt={len(guard['fx3_exact_2_raw_file_types'])},"
                f"lossless_blk={guard['fx3_dormant_lossless_raw_blocked']}) "
                f"jh={guard['effective_jpeg_heif_switch']}/{guard['effective_file_format']} "
                f"hlg={guard['effective_hlg_still_image']} "
                f"cs={guard['effective_color_space']}"
                f"(prefix={guard['effective_dcf_filename_prefix']},"
                f"sample={guard['example_still_filename']}) "
                f"fx6_still={guard['fx6_still_pipeline_supported']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-shutter-type-nr-drive-guard",
        "verify-g118-shutter-type-nr-drive",
    ):
        verdict, res = evaluate_g118_shutter_type_nr_drive_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.shutter_type_nr_drive_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} shutter={guard['effective_shutter_type']}"
                f"(2opt={len(guard['fx3_exact_2_shutter_types'])},"
                f"no_auto={guard['fx3_auto_shutter_type_blocked']},"
                f"efront={guard['effective_e_front_curtain']},"
                f"sync={guard['fx3_flash_sync_ceiling_label']}) "
                f"lenr={guard['effective_long_exposure_nr']} "
                f"hinr={guard['effective_high_iso_nr']} "
                f"drive={guard['effective_drive_mode']}(modes={len(guard['fx3_exact_8_drive_modes'])}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-118-gates":
        report = evaluate_118gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/118 "
                f"g117_to_g118_all_passed={report.g117_to_g118_all_passed} "
                f"all_118_gates_verified={report.all_118_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_118_gates_verified if args.dry_run_simulated else report.offline_115_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-focus-area-and-zoom-lever-guard",
        "verify-g119-focus-area-zoom-lever",
    ):
        verdict, res = evaluate_g119_focus_area_and_zoom_lever_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.focus_area_zoom_lever_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} fa={guard['effective_focus_area']}"
                f"(14opt={len(guard['fx3_exact_14_focus_areas'])},"
                f"trk_still_only={len(guard['fx3_still_only_7_tracking_focus_areas'])},"
                f"limit={guard['focus_area_limit_enabled_count']},"
                f"af_reg={guard['effective_af_area_registration']}) "
                f"xlr_h1_zoom_lever={guard['xlr_h1_has_zoom_lever']} "
                f"z_lever=({guard['zoom_lever_1st_speed_stby']}/{guard['zoom_lever_2nd_speed_stby']}) "
                f"remote_z={guard['remote_zoom_speed_type']}({guard['remote_zoom_fixed_speed_stby']}) "
                f"z_range={guard['effective_zoom_range']} "
                f"fx6_zoom_pos={guard['fx6_zoom_position_display_range']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-iso-minss-and-flash-guard",
        "verify-g120-iso-minss-flash",
    ):
        verdict, res = evaluate_g120_iso_minss_and_flash_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.iso_minss_flash_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} iso_range=({guard['effective_iso_range_min']}..{guard['effective_iso_range_max']}) "
                f"min_ss={guard['effective_iso_auto_min_ss']}"
                f"(active={guard['iso_auto_min_ss_active']},cine_ei_pin={guard['cine_ei_base_iso_pinned']}) "
                f"flash={guard['effective_flash_mode']}"
                f"(avail={guard['flash_available']},sync<=1/{guard['fx3_flash_sync_ceiling_denom']},"
                f"v={guard['mi_shoe_trigger_voltage_v']}V) "
                f"vlight={guard['effective_video_light_mode']} "
                f"fx6_still_flash={guard['fx6_still_flash_supported']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-120-gates":
        report = evaluate_120gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/120 "
                f"g119_to_g120_all_passed={report.g119_to_g120_all_passed} "
                f"all_120_gates_verified={report.all_120_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_120_gates_verified if args.dry_run_simulated else report.offline_117_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-dci4k-and-aspect-ratio-guard",
        "verify-g121-dci4k-aspect-ratio",
    ):
        verdict, res = evaluate_g121_dci4k_and_aspect_ratio_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.dci4k_aspect_ratio_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} fmt={guard['effective_file_format']}"
                f"({guard['movie_dimensions'][0]}x{guard['movie_dimensions'][1]}@"
                f"{guard['rec_frame_rate']},sq={guard['sq_fps']}fps,"
                f"24p_quar={guard['playback_24_00p_quarantine_enforced']}) "
                f"hdmi_raw=4264x2408(en={guard['hdmi_raw_output_enabled']},log={guard['log_shooting']}) "
                f"aspect={guard['effective_still_aspect_ratio']}({guard['effective_still_image_size']}="
                f"{guard['still_aspect_megapixel_label']},arw_full_3_2={guard['arw_retains_full_3_2_pixels']}) "
                f"fx6_still_aspect={guard['fx6_still_aspect_supported']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-custom-hold-camset-photo-capture-guard",
        "verify-g122-custom-hold-camset-photo-capture",
    ):
        verdict, res = evaluate_g122_custom_hold_camset_photo_capture_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(res.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.custom_hold_camset_photo_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} hold_keys={len(guard['exact_11_custom_hold_keys'])} "
                f"camset_path=/SONY/SETTING/(fx6_pro_rej={guard['fx6_pro_camera_path_rejected']},"
                f"slot1_fmt_prot={guard['format_slot_1_protected']}) "
                f"photo_cap={guard['effective_photo_capture_file_type']}"
                f"({guard['photo_capture_output_mp_label']},dci4k_blk={guard['photo_capture_dci4k_locked']},"
                f"slot1_blk={guard['photo_capture_slot1_write_blocked']}) "
                f"enlarge=({guard['effective_enlarge_initial_mag']},{guard['effective_enlarge_initial_position']}) "
                f"fx6_photo={guard['fx6_photo_capture_supported']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-122-gates":
        report = evaluate_122gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            try:
                sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/122 "
                f"g121_to_g122_all_passed={report.g121_to_g122_all_passed} "
                f"all_122_gates_verified={report.all_122_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_122_gates_verified if args.dry_run_simulated else report.offline_119_gates_verified
        return 0 if ok else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
