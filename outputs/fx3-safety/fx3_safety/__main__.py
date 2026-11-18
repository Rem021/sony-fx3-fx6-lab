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
from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    evaluate_124gate_preflight,
    evaluate_g123_sensor_cleaning_and_ev_comp_guard,
    evaluate_g124_focus_mode_and_playback_rotate_guard,
)
from .realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard import (
    evaluate_126gate_preflight,
    evaluate_g125_lens_comp_and_af_illuminator_guard,
    evaluate_g126_aperture_drive_and_folder_rating_guard,
)
from .realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard import (
    evaluate_128gate_preflight,
    evaluate_g127_switch_vh_af_and_exposure_stdadj_guard,
    evaluate_g128_tcub_format_and_playback_copy_slot_guard,
)
from .realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard import (
    evaluate_130gate_preflight,
    evaluate_g129_touch_shooting_and_disp_evf_absence_guard,
    evaluate_g130_ael_wireless_flash_and_interval_pb_edit_guard,
)
from .realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard import (
    evaluate_132gate_preflight,
    evaluate_g131_dial_customize_mydial_fn_guard,
    evaluate_g132_liveview_grid_lut_embed_guard,
)
from .realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard import (
    evaluate_134gate_preflight,
    evaluate_g133_steadyshot_selftimer_guard,
    evaluate_g134_zebra_streaming_firewall_guard,
)
from .realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard import (
    evaluate_136gate_preflight,
    evaluate_g135_bright_mon_shotmark_vault_guard,
    evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard,
)
from .realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard import (
    evaluate_138gate_preflight,
    evaluate_g137_big6_home_framing_interval_vault_guard,
    evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard,
)
from .realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard import (
    evaluate_140gate_preflight,
    evaluate_g139_rec_media_autoswitch_proxy_vault_guard,
    evaluate_g140_creators_cloud_zerorf_mymenu42_guard,
)
from .realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard import (
    evaluate_142gate_preflight,
    evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard,
    evaluate_g142_movie_af_focusmap_marker_peaking_guard,
)
from .realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (
    evaluate_144gate_preflight,
    evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard,
    evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard,
)
from .realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
    evaluate_146gate_preflight,
    evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard,
    evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard,
)
from .realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard import (
    evaluate_148gate_preflight,
    evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard,
    evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard,
)
from .realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard import (
    evaluate_150gate_preflight,
    evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard,
    evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall,
)
from .realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard import (
    evaluate_152gate_preflight,
    evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard,
    evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard,
)
from .realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard import (
    evaluate_154gate_preflight,
    evaluate_g153_pixelmap_apr_monitor_vfadjust_guard,
    evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard,
)
from .realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard import (
    evaluate_156gate_preflight,
    evaluate_g155_areadate_dst_grid_cleanhdmi_guard,
    evaluate_g156_saveload_camset_mishoe_genlock_guard,
)
from .realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard import (
    evaluate_158gate_preflight,
    evaluate_g157_pbmag_varshutter_ecs_guard,
    evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard,
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

    # 143. verify-sensor-cleaning-and-ev-comp-guard
    p_g123 = sub.add_parser(
        "verify-sensor-cleaning-and-ev-comp-guard",
        aliases=["verify-g123-sensor-cleaning-ev-comp"],
        help="Verify Gate G123: [Sensor Cleaning] (>= 51%% NP-FZ100 Battery Gate & Mandatory Power-OFF vs FX6 e-ND Optical Block) + [Exposure Comp.] (+/-5.0 EV Still / +/-2.0 EV Movie, [Exposure step] 0.3EV/0.5EV, Manual M + Fixed ISO Disable, & Total [Cine EI]/[Cine EI Quick] Lockout)",
    )
    p_g123.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g123.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g123.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g123.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g123.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 144. verify-focus-mode-and-playback-rotate-guard
    p_g124 = sub.add_parser(
        "verify-focus-mode-and-playback-rotate-guard",
        aliases=["verify-g124-focus-mode-playback-rotate"],
        help="Verify Gate G124: [Focus Mode] Still 5-Mode (AF-S/AF-A/AF-C/DMF/MF) vs Movie/S&Q 2-Mode (AF-C [MOVIE_AUTO]/MF) + [Priority Set in AF-S/AF-C]/[AF Assist]/[AF Illuminator] + [Playback] [View Mode]/[Image Index] (9/25 vs Dormant 12/30)/[Display as Group]/[Display Rotation]/[Rotate] Slot-1 Read-Only Vault EROFS/EBUSY Firewall",
    )
    p_g124.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g124.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g124.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g124.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g124.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 145. verify-124-gates
    p_124 = sub.add_parser(
        "verify-124-gates",
        help="Run Phase 290 (290th Phase Milestone) Unified 124-Gate Master Safety Preflight Engine (G01..G124)",
    )
    p_124.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_124.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_124.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G124 gates can be rehearsed offline",
    )
    p_124.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_124.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 146. verify-lens-comp-and-af-illuminator-guard
    p_g125 = sub.add_parser(
        "verify-lens-comp-and-af-illuminator-guard",
        aliases=["verify-g125-lens-comp-af-illuminator"],
        help="Verify Gate G125: [Lens Compensation] (Shading/CA/Distortion Auto/Off vs Dormant Auto: Low, E-Mount/SteadyShot Active Lock, FX6 Technical > Lens) + Movie [AF Transition Speed]/[AF Subj. Shift Sensitivity]/[AF Assist] & [AF Illuminator] Front LED Hardware Reality Split",
    )
    p_g125.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g125.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g125.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g125.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g125.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 147. verify-aperture-drive-and-folder-rating-guard
    p_g126 = sub.add_parser(
        "verify-aperture-drive-and-folder-rating-guard",
        aliases=["verify-g126-aperture-drive-folder-rating"],
        help="Verify Gate G126: Still [Aperture Drive in AF]/[AF w/ Shutter]/[Pre-AF]/[Circ. of Focus Point]/[Focus Area Color] (Initialize-Only Survival vs FX6 Iris) + [File/Folder Settings] & Playback [Rating] Slot-1 Tier-0 Vault EROFS/EOPNOTSUPP Write Firewall",
    )
    p_g126.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g126.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g126.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g126.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g126.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 148. verify-126-gates
    p_126 = sub.add_parser(
        "verify-126-gates",
        help="Run Phase 294 Unified 126-Gate Master Safety Preflight Engine (G01..G126)",
    )
    p_126.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_126.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_126.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G126 gates can be rehearsed offline",
    )
    p_126.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_126.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 149. verify-switch-vh-af-and-exposure-stdadj-guard
    p_g127 = sub.add_parser(
        "verify-switch-vh-af-and-exposure-stdadj-guard",
        aliases=["verify-g127-switch-vh-af-exposure-stdadj"],
        help="Verify Gate G127: [Switch V/H AF Area] (Still AF-C 0/90/270 deg vs INVALID pitch & 8 lockouts) + [Focus Area Limit] (14 checkboxes vs dormant XL/XS/Custom1..3, >=2 min) + [Exposure Std. Adjust] (5 metering modes @ 1/6 EV, Initialize-only) & Still [Bracket Settings]",
    )
    p_g127.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g127.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g127.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g127.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g127.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 150. verify-tcub-format-and-playback-copy-slot-guard
    p_g128 = sub.add_parser(
        "verify-tcub-format-and-playback-copy-slot-guard",
        aliases=["verify-g128-tcub-playback-copy-slot"],
        help="Verify Gate G128: [TC/UB] 6-item & [TC/UB Disp. Setting] (Initialize-only), [Time Code Format] (NTSC 23.98p/24p NDF lock & PAL hide), & Playback [Copy] Directional Asymmetry Firewall (Slot 2 -> Slot 1 Tier-0 Vault) + [Slide Show] Sleep Bypass",
    )
    p_g128.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g128.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g128.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g128.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g128.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 151. verify-128-gates
    p_128 = sub.add_parser(
        "verify-128-gates",
        help="Run Phase 297 Milestone Unified 128-Gate Master Safety Preflight Engine (G01..G128)",
    )
    p_128.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_128.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_128.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G128 gates can be rehearsed offline",
    )
    p_128.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_128.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 152. verify-touch-shooting-and-disp-evf-absence-guard
    p_g129 = sub.add_parser(
        "verify-touch-shooting-and-disp-evf-absence-guard",
        aliases=["verify-g129-touch-shooting-disp-evf"],
        help="Verify Gate G129: [Touch Operation] 4-item menu (Standard/Sensitive, Touch Focus/Tracking/Off, Initialize-only) vs dormant Touch Shutter/AE/Pad/Footer traps + [DISP (Screen Disp) Set] (Operation Customize 4-mode shoot / 3-mode play) & Total Zero-EVF Blackout Trap Firewall",
    )
    p_g129.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g129.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g129.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g129.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g129.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 153. verify-ael-wireless-flash-and-interval-pb-edit-guard
    p_g130 = sub.add_parser(
        "verify-ael-wireless-flash-and-interval-pb-edit-guard",
        aliases=["verify-g130-ael-flash-interval-pb-edit"],
        help="Verify Gate G130: Still-only [AEL w/ Shutter] & [Flash] submenu ([Exp.comp.set], Camera-Resettable [Wireless Flash], Direct MI-Shoe [External Flash Set.] vs FX6 Flash Band Reduce) + Playback [Viewing] [Play Speed for Interval] 1..9 scale (default 5) & Active [Edit] 4-item vs Dormant [Beauty Effect]/[Trimming] Slot-1 Tier-0 Vault Firewall",
    )
    p_g130.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g130.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g130.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g130.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g130.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 154. verify-130-gates
    p_130 = sub.add_parser(
        "verify-130-gates",
        help="Run Phase 299 Milestone Unified 130-Gate Master Safety Preflight Engine (G01..G130)",
    )
    p_130.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_130.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_130.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G130 gates can be rehearsed offline",
    )
    p_130.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_130.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 155. verify-dial-customize-mydial-fn-guard
    p_g131 = sub.add_parser(
        "verify-dial-customize-mydial-fn-guard",
        aliases=["verify-g131-dial-customize-mydial-fn"],
        help="Verify Gate G131: [Dial Customize] 5-Item Ver. 7.02 Truth (Initialize-only vs legacy Dial Setup / Dial-Wheel Lock), Physical 3-Dial Topology vs Dormant 4-Dial Rear Dial L/R (EOPNOTSUPP=95), [My Dial Settings] 1..3 Shared NVRAM & Lock Override, and [Fn Menu Settings] 12 Still + 12 Movie Split vs FX6 Multi Function Dial / Direct Menu",
    )
    p_g131.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g131.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g131.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g131.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g131.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 156. verify-liveview-grid-lut-embed-guard
    p_g132 = sub.add_parser(
        "verify-liveview-grid-lut-embed-guard",
        aliases=["verify-g132-liveview-grid-lut-embed"],
        help="Verify Gate G132: Still-only [Live View Display Set.] 3-Item + Bright Monitoring Override, [Grid Line] Clean-HDMI Isolation vs FX6 Marker Safety Zone 80/90/92.5/95%% & Dormant Custom PNG Grids, and [Manage User LUTs] (709(800%%) / .cube O_RDONLY) vs [Embed LUT File] (SD/SDHC Off Lock) vs PPLUT1..4 + Slot-1 Tier-0 Vault Firewall (EROFS=30 / EBUSY=16)",
    )
    p_g132.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g132.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g132.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g132.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g132.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 157. verify-132-gates
    p_132 = sub.add_parser(
        "verify-132-gates",
        help="Run Phase 303 Wave-56 Unified 132-Gate Master Safety Preflight Engine (G01..G132)",
    )
    p_132.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_132.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_132.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G132 gates can be rehearsed offline",
    )
    p_132.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_132.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 158. verify-steadyshot-selftimer-guard
    p_g133 = sub.add_parser(
        "verify-steadyshot-selftimer-guard",
        aliases=["verify-g133-steadyshot-selftimer"],
        help="Verify Gate G133: SteadyShot 5-Axis IBIS 4-Lock Active Matrix (119.88p/100p Movie, >=120/100fps S&Q, HDMI RAW, De-Squeeze 1.3x..2.0x) and Exact 47-Entry Focal Length Table (8..1000mm) vs Dormant Dynamic active (EOPNOTSUPP=95) & IBIS-less FX6 + Dormant Movie Self-timer vs Still Drive Self-timer, Front #8 Lamp, and Audio signals Suppression",
    )
    p_g133.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g133.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g133.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g133.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g133.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 159. verify-zebra-peaking-streaming-firewall-guard
    p_g134 = sub.add_parser(
        "verify-zebra-peaking-streaming-firewall-guard",
        aliases=["verify-g134-zebra-streaming-firewall"],
        help="Verify Gate G134: Zebra Custom1 (Std+Range 0..109%% +- 1..10%%) & Custom2 (Lower Limit 0..109+), S-Log3 18%% Grey=41%% / Clip ~94%% & Display LUT Post-LUT Measurement + 4-Color Peaking vs FX6 3-Way Off/Zebra1/Zebra2 Selector (No Both), Network Streaming (RTMP/RTMPS/SRT 59.94/50/29.97/25p vs 23.98p/24p) & FTP Transfer + Airplane Mode=On Zero-RF / Slot-1 Tier-0 Vault Firewall (EROFS=30 / EBUSY=16)",
    )
    p_g134.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g134.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g134.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g134.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g134.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 160. verify-134-gates
    p_134 = sub.add_parser(
        "verify-134-gates",
        help="Run Phase 305 Wave-57 Unified 134-Gate Master Safety Preflight Engine (G01..G134)",
    )
    p_134.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_134.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_134.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G134 gates can be rehearsed offline",
    )
    p_134.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_134.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 161. verify-bright-mon-shotmark-vault-guard
    p_g135 = sub.add_parser(
        "verify-bright-mon-shotmark-vault-guard",
        aliases=["verify-g135-bright-mon-shotmark-vault"],
        help="Verify Gate G135: Custom-key-only Bright Monitoring + Ver. 7.00+ Focus Magnifier coexistence, Monitor Brightness Manual (-2..+2) / Sunny Weather vs FX6 VF Setting / AE Backlight, and Shot Mark 1/2 + Clip Flag + Create Divider Frame Slot-1 Tier-0 Vault Firewall (EROFS=30 / EBUSY=16)",
    )
    p_g135.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g135.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g135.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g135.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g135.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 162. verify-tc-link-wifi-usblan-bulb-dormant-guard
    p_g136 = sub.add_parser(
        "verify-tc-link-wifi-usblan-bulb-dormant-guard",
        aliases=["verify-g136-tc-link-wifi-usblan-bulb-dormant"],
        help="Verify Gate G136: Zero Bluetooth Timecode Link vs wired VMC-BNCM1 EXT-LK & FX6 BNC TC IN/OUT, Wi-Fi WPA2-PSK/WPA3-SAE SKU (WW728473 vs WW558244) + USB-LAN CDC-NCM/r8152/ASIX Zero-RF isolation, and dormant Bulb Timer / Auto HDR vs mechanical-only Still BULB + DRO Lock Guard",
    )
    p_g136.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g136.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g136.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g136.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g136.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 163. verify-136-gates
    p_136 = sub.add_parser(
        "verify-136-gates",
        help="Run Phase 310 Wave-58 Unified 136-Gate Master Safety Preflight Engine (G01..G136)",
    )
    p_136.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_136.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_136.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G136 gates can be rehearsed offline",
    )
    p_136.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_136.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 164. verify-big6-home-framing-interval-vault-guard
    p_g137 = sub.add_parser(
        "verify-big6-home-framing-interval-vault-guard",
        aliases=["verify-g137-big6-home-framing-interval"],
        help="Verify Gate G137: Ver. 7.00+ BIG6 Home screen Fixed/Variable prerequisite and Manual ND metadata vs FX6 e-ND, Manual Framing Settings vs dormant Auto Framing (EOPNOTSUPP=95), and Still Interval Shoot Func. 9999-shot Slot-1 Tier-0 Vault Firewall (EROFS=30 / EBUSY=16)",
    )
    p_g137.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g137.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g137.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g137.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g137.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 165. verify-tc-make-hdmi-rec-ssh-authen-fan-guard
    p_g138 = sub.add_parser(
        "verify-tc-make-hdmi-rec-ssh-authen-fan-guard",
        aliases=["verify-g138-tc-make-hdmi-rec-ssh-fan"],
        help="Verify Gate G138: Time Code Make Regenerate forced Rec Run and HDMI REC Control state machine, Ver. 7.00+ SSH-based Access Authen. vs Zero HTTPS/Digest, and 4-mode FX3 vs 3-mode FX6 Fan Control Zero-Max truth (EOPNOTSUPP=95)",
    )
    p_g138.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g138.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g138.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g138.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g138.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 166. verify-138-gates
    p_138 = sub.add_parser(
        "verify-138-gates",
        help="Run Phase 313 Wave-59 Unified 138-Gate Master Safety Preflight Engine (G01..G138)",
    )
    p_138.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_138.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_138.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G138 gates can be rehearsed offline",
    )
    p_138.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_138.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 167. verify-rec-media-autoswitch-proxy-vault-guard
    p_g139 = sub.add_parser(
        "verify-rec-media-autoswitch-proxy-vault-guard",
        aliases=["verify-g139-rec-media-autoswitch-proxy"],
        help="Verify Gate G139: Split [Recording Media] (Still/Movie) vs dormant [Prioritize Rec. Media] (EOPNOTSUPP=95), [Auto Switch Media] Slot-2->Slot-1 overflow EROFS=30 Tier-0 Vault Firewall, V60/V90/CFexpress VPG200/VPG400 speed gates (Type B ENODEV=19), and [Proxy Settings] M4ROOT/SUB Vault Firewall vs FX6 Simul Rec / Chunk Proxy",
    )
    p_g139.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g139.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g139.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g139.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g139.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 168. verify-creators-cloud-zerorf-mymenu42-guard
    p_g140 = sub.add_parser(
        "verify-creators-cloud-zerorf-mymenu42-guard",
        aliases=["verify-g140-creators-cloud-zerorf-mymenu"],
        help="Verify Gate G140: [Creators' Cloud]/[C3 Portal] Initialize-persistence & FTP exclusion, [Cnct. while Power OFF] BLE Zero-RF firewall (Airplane=On AND Cnct. while Power OFF=Off) vs Bluetooth-less FX6, and exact 42-slot [My Menu] (6x7, rejecting >=42 & Playback tab EINVAL=22) vs 20-item FX6 User Menu with Lock",
    )
    p_g140.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g140.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g140.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g140.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g140.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 169. verify-140-gates
    p_140 = sub.add_parser(
        "verify-140-gates",
        help="Run Phase 317 Wave-60 Grand Milestone Unified 140-Gate Master Safety Preflight Engine (G01..G140)",
    )
    p_140.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_140.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_140.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G140 gates can be rehearsed offline",
    )
    p_140.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_140.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 170. verify-ftp-ftpes-avf-vault-customwb-guard
    p_g141 = sub.add_parser(
        "verify-ftp-ftpes-avf-vault-customwb-guard",
        aliases=["verify-g141-ftp-ftpes-customwb"],
        help="Verify Gate G141: FX3 9-slot FTP/FTPES (Passive-only, zero SFTP/Active/dormant Transfer JPEG/HEIF Size EOPNOTSUPP=95), Slot-1 AVF_INFO EROFS=30 Vault & O_RDONLY cacert.pem, Zero-RF USB-LAN bypass lock, and White Balance (Custom 1..3 Initialize-only, 0x0220 error, Cine EI Auto lockout, Shutter AWB Lock & Shockless WB vs FX6 ATW/Memory A..H)",
    )
    p_g141.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g141.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g141.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g141.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g141.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 171. verify-movie-af-focusmap-marker-peaking-guard
    p_g142 = sub.add_parser(
        "verify-movie-af-focusmap-marker-peaking-guard",
        aliases=["verify-g142-movie-af-focusmap-marker"],
        help="Verify Gate G142: Movie AF Transition Speed 1..7 & Subj. Shift Sens. 1..5 (BOTH FX3 & FX6, rejecting 6/7 EINVAL=22) + AF Assist, External Monitor & Control Focus Map (>=150fps block vs zero on-body FX3 menu EOPNOTSUPP=95), and Initialize-only 15-Aspect Marker (80%%/90%% Safety Zone) + 4-Color Peaking (never HDMI) vs FX6 User Box",
    )
    p_g142.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g142.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g142.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g142.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g142.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 172. verify-142-gates
    p_142 = sub.add_parser(
        "verify-142-gates",
        help="Run Phase 319 Wave-61 Unified 142-Gate Master Safety Preflight Engine (G01..G142)",
    )
    p_142.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_142.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_142.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G142 gates can be rehearsed offline",
    )
    p_142.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_142.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 173. verify-shoe-audio-4ch-subject-recog-guard
    p_g143 = sub.add_parser(
        "verify-shoe-audio-4ch-subject-recog-guard",
        aliases=["verify-g143-shoe-audio-subject-recog", "verify-g143"],
        help="Verify Gate G143: Shooting -> [Audio Recording] -> [Audio Out Timing] (Live/Lip Sync, S&Q lock, NOT Sound Option), removed [Audio Level Display], [Audio Rec Level] 0..31 default 26 + always-on limiter, [Shoe Audio Set.] 48kHz/24bit 4ch vs 3.5mm MIC override & AAC-LC Proxy, plus [Face/Eye Subject] Human/Animal vs dormant Bird/Animal-Bird/Insect/Car-Train/Airplane (EOPNOTSUPP=95) & Still-only Animal Eye AF",
    )
    p_g143.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g143.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g143.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g143.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g143.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 174. verify-silent-target-bodydata-nogo-guard
    p_g144 = sub.add_parser(
        "verify-silent-target-bodydata-nogo-guard",
        aliases=["verify-g144-silent-target-bodydata-nogo", "verify-g144"],
        help="Verify Gate G144: [Silent Mode Settings] 5-disabled-func lock (AF Illuminator NOT disabled), 2-item [Target Function Settings] (Aperture Drive in AF & Auto Pixel Mapping Off), dormant [Shutter When Pwr OFF]/[Anti-dust Function] EOPNOTSUPP=95 & shutterless FX6 Auto Pixel Restore, Zero-RF [Version] badge silence, FX3 Slot 1 NP-FZ100 >= 51%% + Ver. 2.04/2.05 stepping-stone vs FX6 Slot B + AC Adaptor, and HARD NO-GO Slot-1 BODYDATA.DAT / eMMC flash firewall (EROFS=30 / EPERM=1)",
    )
    p_g144.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g144.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g144.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g144.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g144.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 175. verify-144-gates
    p_144 = sub.add_parser(
        "verify-144-gates",
        help="Run Phase 323 Wave-62 Unified 144-Gate (12^2 Gross Milestone) Master Safety Preflight Engine (G01..G144)",
    )
    p_144.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_144.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_144.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G144 gates can be rehearsed offline",
    )
    p_144.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_144.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 176. verify-hdmi-raw-desqueeze-guard
    p_g145 = sub.add_parser(
        "verify-hdmi-raw-desqueeze-guard",
        aliases=["verify-g145-hdmi-raw-desqueeze", "verify-g145"],
        help="Verify Gate G145: 8-item Initialize-only [HDMI Output Settings], removed [Color Gamut for RAW Output] EOPNOTSUPP=95, 24.00p reboot gate & dormant 8bit EOPNOTSUPP=95, RAW+Rec.Media Slot-1 EROFS=30 co-rec vault vs Off(HDMI Only), LCD blanking, and 5-state [De-Squeeze Display] (1.6x->1.65x, absent 1.8x, 4 lockouts, 6 auto-bypasses)",
    )
    p_g145.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g145.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g145.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g145.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g145.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 177. verify-reclamp-varshutter-apsc-guard
    p_g146 = sub.add_parser(
        "verify-reclamp-varshutter-apsc-guard",
        aliases=["verify-g146-reclamp-varshutter-apsc", "verify-g146"],
        help="Verify Gate G146: Initialize-only 3-lamp [REC Lamp] (independent of Silent Mode, dormant Tally/ONLY_ONE EOPNOTSUPP=95), resettable [Emphasized REC Display], [Remain Shoot Display], Still-only [Auto Review], dormant [Var. Shutter] EOPNOTSUPP=95 vs Still Mech [Anti-flicker Shoot.], and Wave-42 Reset Errata on Initialize-only [APS-C S35 Shooting] (4K/Still 12M clamp)",
    )
    p_g146.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g146.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g146.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g146.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g146.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 178. verify-146-gates
    p_146 = sub.add_parser(
        "verify-146-gates",
        help="Run Phase 327 Wave-63 Unified 146-Gate Master Safety Preflight Engine (G01..G146)",
    )
    p_146.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_146.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_146.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G146 gates can be rehearsed offline",
    )
    p_146.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_146.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 179. verify-breathing-camid-reel-sdhc-guard
    p_g147 = sub.add_parser(
        "verify-breathing-camid-reel-sdhc-guard",
        aliases=["verify-g147-breathing-camid-reel", "verify-g147"],
        help="Verify Gate G147: Resettable [Breathing Comp.] Wave-41 120p/S&Q>=100fps/Macro-TC/HDMI-RAW/Catalyst-Prepare errata & Initialize-only [File Settings] ([File Number], [File Name Format], SDHC FAT32 Standard-only & 4GB split, [Cam ID + Reel#] C999->D001, 37-char [Title], Slot-1 EROFS=30)",
    )
    p_g147.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g147.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g147.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g147.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g147.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 180. verify-copyright-powersave-ntscpal-guard
    p_g148 = sub.add_parser(
        "verify-copyright-powersave-ntscpal-guard",
        aliases=["verify-g148-copyright-powersave-ntscpal", "verify-g148"],
        help="Verify Gate G148: Round-57 Reset Errata on [Copyright Info] (46-char ASCII, CAMSET excluded) + active Still+Movie [Write Serial Number], 2-item [Power Setting Option] (9 bypasses, Auto Power OFF Temp., dormant [Power Save by Monitor] EOPNOTSUPP=95), and [NTSC/PAL Selector] reboot + Slot-1 Format/SD-Erase/TRIM EROFS=30",
    )
    p_g148.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g148.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g148.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g148.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g148.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 181. verify-148-gates
    p_148 = sub.add_parser(
        "verify-148-gates",
        help="Run Phase 331 (Task H400, Wave-64) Unified 148-Gate Master Safety Preflight Engine (G01..G148)",
    )
    p_148.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_148.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_148.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G148 gates can be rehearsed offline",
    )
    p_148.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_148.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 182. verify-zoom-ciz-autoslow-baseiso-guard
    p_g149 = sub.add_parser(
        "verify-zoom-ciz-autoslow-baseiso-guard",
        aliases=["verify-g149-zoom-ciz-autoslow-baseiso", "verify-g149"],
        help="Verify Gate G149: Reset-immune [Zoom Range] & [Zoom Ring Rotate] vs Resettable 8-step [Zoom Lever Speed]/[Custom Key Z. Speed]/[Remote Zoom Speed] + pre-entry/active lockouts, Movie-only [Auto Slow Shutter] 7-cond locks, Reset-immune [ISO Range Limit], Still-only [ISO AUTO Min. SS], and Dual Base ISO (Cine EI 800/12800 vs 20x per-Gamma auto)",
    )
    p_g149.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g149.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g149.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g149.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g149.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 183. verify-still-arw-hlg-usblun-uvc-guard
    p_g150 = sub.add_parser(
        "verify-still-arw-hlg-usblun-uvc-guard",
        aliases=["verify-g150-still-arw-hlg-usblun-uvc", "verify-g150"],
        help="Verify Gate G150: Still [RAW File Type] Compressed/Uncompressed vs 100%% dormant Lossless Comp (EOPNOTSUPP=95), [HLG Still Image] BT.2100 + ISO 100/125, [Sort Recording] Slot-1 EROFS=30, [USB LUN Setting]=Single Slot-1 exposure trap & host-MSC firewall, NP-FZ100 PD boot gate vs DC-C1, and Dual FX3/FX6 native UVC myth-busting (EOPNOTSUPP=95)",
    )
    p_g150.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g150.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g150.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g150.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g150.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 184. verify-150-gates
    p_150 = sub.add_parser(
        "verify-150-gates",
        help="Run Phase 347 (Task H432, Wave-65) Unified 150-Gate Milestone Master Safety Preflight Engine (G01..G150)",
    )
    p_150.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_150.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_150.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G150 gates can be rehearsed offline",
    )
    p_150.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_150.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 185. verify-drive-focusbracket-shutter-efcs-nr-guard
    p_g151 = sub.add_parser(
        "verify-drive-focusbracket-shutter-efcs-nr-guard",
        aliases=["verify-g151-drive-shutter-efcs-nr", "verify-g151"],
        help="Verify Gate G151: Still-only [Drive Mode] 10 fps Hi+ / >F11 AF lock / Uncompressed RAW & Flash drop vs 0-exposed dormant [Focus Bracket] (EOPNOTSUPP=95), 2-option [Shutter Type] zero-Auto + 1/250 s X-Sync + Reset-immune [e-Front Curtain Shut.] (curtaion) + [Long Exposure NR] (>=1s) + [High ISO NR] vs FX6 APR",
    )
    p_g151.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g151.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g151.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g151.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g151.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 186. verify-creative-look-soft-skin-delete-protect-recoverdb-guard
    p_g152 = sub.add_parser(
        "verify-creative-look-soft-skin-delete-protect-recoverdb-guard",
        aliases=["verify-g152-creativelook-delete-recoverdb", "verify-g152"],
        help="Verify Gate G152: [Creative Look] 10+6 slots / 0..9 asymmetric Fade-Sharpness-Clarity bounds + PP/Log/HLG [-] lock vs 100%% dormant [Soft Skin Effect] on FX3 & FX6 (EOPNOTSUPP=95), Playback [Delete]/[Protect]/[Display Media Info.]/[Recover Image DB] + Tier-0 Slot-1 EROFS=30 Firewall",
    )
    p_g152.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g152.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g152.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g152.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g152.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 187. verify-152-gates
    p_152 = sub.add_parser(
        "verify-152-gates",
        help="Run Phase 351 (Task H439, Wave-66) Unified 152-Gate Milestone Master Safety Preflight Engine (G01..G152)",
    )
    p_152.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_152.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_152.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G152 gates can be rehearsed offline",
    )
    p_152.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_152.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 188. verify-pixelmap-apr-monitor-vfadjust-guard
    p_g153 = sub.add_parser(
        "verify-pixelmap-apr-monitor-vfadjust-guard",
        aliases=["verify-g153-pixelmap-apr-monitor", "verify-g153"],
        help="Verify Gate G153: [Pixel Mapping] / Dual [Auto Pixel Mapping] Reset Split (Setup Init-only vs Silent Target Resettable) & Sony Typos vs FX6 APR + Dormant ABB (EOPNOTSUPP=95), Setup -> [Monitor] 3 Init-only Items vs Zero [Finder/Monitor] & 4 Dormant EVF Symbols vs FX6 VF Setting/VF Adjust",
    )
    p_g153.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g153.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g153.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g153.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g153.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 189. verify-recall-custom-hold-hdmi-reccontrol-guard
    p_g154 = sub.add_parser(
        "verify-recall-custom-hold-hdmi-reccontrol-guard",
        aliases=["verify-g154-customhold-hdmi-reccontrol", "verify-g154"],
        help="Verify Gate G154: Still-only P/A/S/M [Recall Custom hold 1..3] Exact 11 Params with Zero Standalone WB vs FX6 Push AF/AGC/Iris & Dormant High/Low Key, plus Setup -> [External Output] HDMI Rec. Media = On Slot-1 EROFS=30 Vault, REC Control TC Output=On Prerequisite, and ctrl_for_hmdi Typo",
    )
    p_g154.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g154.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g154.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g154.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g154.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 190. verify-154-gates
    p_154 = sub.add_parser(
        "verify-154-gates",
        help="Run Phase 356 (Task H446, Wave-67) Unified 154-Gate Milestone Master Safety Preflight Engine (G01..G154)",
    )
    p_154.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_154.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_154.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G154 gates can be rehearsed offline",
    )
    p_154.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_154.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 191. verify-areadate-grid-cleanhdmi-guard
    p_g155 = sub.add_parser(
        "verify-areadate-grid-cleanhdmi-guard",
        aliases=["verify-g155-areadate-grid-cleanhdmi", "verify-g155"],
        help="Verify Gate G155: Area/Date/Time Setting 30 GMT Zones (saylight_saving Typo & 24h Soldered RTC vs FX6 Clock Set) plus Grid Line Display HDMI Pass-Through vs Marker Display (80%%/90%% Safety Zone, 15 Ratios) Zero-HDMI & 5-Item Reset-Resistance Firewall",
    )
    p_g155.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g155.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g155.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g155.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g155.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 192. verify-saveload-camset-mishoe-genlock-guard
    p_g156 = sub.add_parser(
        "verify-saveload-camset-mishoe-genlock-guard",
        aliases=["verify-g156-saveload-camset-mishoe", "verify-g156"],
        help="Verify Gate G156: [Save/Load Settings] Slot 1 EROFS=30 %%c:%%s/SONY/SETTING/%%s/CAMSET/%%s.DAT (CAMSET%%02d / FTPSET%%02d / CAMPR%%02d%%c.DAT, libSaveLoadSettings.so, Zero PRO/CAMERA) vs FX6 All File, plus Zero Sync Terminal + XLR-H1 vs HVL-LBPC MI-Shoe Exclusion & PMIC 5V <= 900mA vs FX6 Zero GENLOCK Firewall",
    )
    p_g156.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g156.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g156.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g156.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g156.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 193. verify-156-gates
    p_156 = sub.add_parser(
        "verify-156-gates",
        help="Run Phase 359 (Task H451, Wave-68) Unified 156-Gate Milestone Master Safety Preflight Engine (G01..G156)",
    )
    p_156.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_156.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_156.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G156 gates can be rehearsed offline",
    )
    p_156.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_156.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 194. verify-pbmag-varshutter-ecs-guard
    p_g157 = sub.add_parser(
        "verify-pbmag-varshutter-ecs-guard",
        aliases=["verify-g157-pbmag-varshutter-ecs", "verify-g157"],
        help="Verify Gate G157: Still-Only Playback -> [Magnification] (maginify Typo & Zero Movie Zoom vs FX6 Thumbnail/Rec Review/Focus Mag) plus Still [Anti-flicker Shoot.] 100/120Hz vs Dormant [Var. Shutter] / [Anti-flicker Tv Scan] (EOPNOTSUPP=95) vs FX6 ECS 23.99..8000Hz Firewall",
    )
    p_g157.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g157.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g157.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g157.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g157.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 195. verify-wifi5ghz-nvs-ir-lanc-cec-guard
    p_g158 = sub.add_parser(
        "verify-wifi5ghz-nvs-ir-lanc-cec-guard",
        aliases=["verify-g158-wifi5ghz-nvs-ir-lanc-cec", "verify-g158"],
        help="Verify Gate G158: Wi-Fi WW728473/WW558244 5GHz SKU Lock + WPA2/WPA3-Only + [Airplane Mode] Survives [Reset Network Set.] + p12/p13 MS_RDONLY RF NVS Shield plus Front #5 [IR Remote Ctrl] (vs FX3A Removal) / [CTRL FOR HDMI] (ctrl_for_hmdi Default-On 41-Key CEC Bench Hijack Firewall) vs FX6 2.5mm LANC",
    )
    p_g158.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_g158.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_g158.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Optional dry-run rehearsal compatibility flag",
    )
    p_g158.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_g158.add_argument("--summary", action="store_true", help="Emit concise summary output")

    # 196. verify-158-gates
    p_158 = sub.add_parser(
        "verify-158-gates",
        help="Run Phase 363 (Task H457, Wave-69) Unified 158-Gate Milestone Master Safety Preflight Engine (G01..G158)",
    )
    p_158.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    p_158.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    p_158.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G158 gates can be rehearsed offline",
    )
    p_158.add_argument("--json", action="store_true", help="Emit structured JSON report")
    p_158.add_argument("--summary", action="store_true", help="Emit concise summary output")

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

    if args.cmd in (
        "verify-sensor-cleaning-and-ev-comp-guard",
        "verify-g123-sensor-cleaning-ev-comp",
    ):
        verdict, res = evaluate_g123_sensor_cleaning_and_ev_comp_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "battery_pct": res.sensor_cleaning_ev_comp_guard["battery_pct"],
                    "sensor_cleaning_allowed": res.sensor_cleaning_ev_comp_guard["sensor_cleaning_allowed"],
                    "fx6_has_ibis": res.sensor_cleaning_ev_comp_guard["fx6_has_ibis"],
                    "effective_ev_comp": res.sensor_cleaning_ev_comp_guard["effective_ev_comp"],
                    "cine_ei_locks_ev_comp": res.sensor_cleaning_ev_comp_guard["cine_ei_locks_ev_comp"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.sensor_cleaning_ev_comp_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} clean_batt>={guard['battery_pct']}%(allowed={guard['sensor_cleaning_allowed']},"
                f"pwr_off={guard['power_switch_off_after_cleaning']},fx6_ibis={guard['fx6_has_ibis']},"
                f"fx6_end={guard['fx6_front_end_assembly_present']}) "
                f"ev_comp={guard['effective_ev_comp']:+.1f}EV(range={tuple(guard['ev_comp_allowed_range'])},"
                f"step={guard['effective_exposure_step']},cine_ei_lock={guard['cine_ei_locks_ev_comp']},"
                f"fx3_dial={guard['fx3_has_physical_ev_dial']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-focus-mode-and-playback-rotate-guard",
        "verify-g124-focus-mode-playback-rotate",
    ):
        verdict, res = evaluate_g124_focus_mode_and_playback_rotate_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_focus_mode": res.focus_mode_playback_rotate_guard["effective_focus_mode"],
                    "internal_focus_enum": res.focus_mode_playback_rotate_guard["internal_focus_enum"],
                    "effective_view_mode": res.focus_mode_playback_rotate_guard["effective_view_mode"],
                    "effective_image_index": res.focus_mode_playback_rotate_guard["effective_image_index"],
                    "slot_1_write_protected": res.focus_mode_playback_rotate_guard["slot_1_write_protected"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.focus_mode_playback_rotate_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} focus={guard['effective_focus_mode']}"
                f"(enum={guard['internal_focus_enum']},illum={guard['effective_af_illuminator']},"
                f"fx6_af={guard['fx6_supports_af_a_dmf_illuminator']}) "
                f"playback=(view={guard['effective_view_mode']},idx={guard['effective_image_index']},"
                f"group={guard['effective_display_as_group']},rot_disp={guard['effective_display_rotation']},"
                f"slot1_wp={guard['slot_1_write_protected']},rotate_blk={guard['rotate_blocked']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-124-gates":
        report = evaluate_124gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g123_status": report.g123_result["status"],
                    "g124_status": report.g124_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/124 "
                f"g123_to_g124_all_passed={report.g123_to_g124_all_passed} "
                f"all_124_gates_verified={report.all_124_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_124_gates_verified if args.dry_run_simulated else report.offline_121_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-lens-comp-and-af-illuminator-guard",
        "verify-g125-lens-comp-af-illuminator",
    ):
        verdict, res = evaluate_g125_lens_comp_and_af_illuminator_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_shading_comp": res.lens_comp_af_illuminator_guard["effective_shading_comp"],
                    "effective_ca_comp": res.lens_comp_af_illuminator_guard["effective_ca_comp"],
                    "effective_distortion_comp": res.lens_comp_af_illuminator_guard["effective_distortion_comp"],
                    "af_transition_speed": res.lens_comp_af_illuminator_guard["af_transition_speed"],
                    "af_subj_shift_sens": res.lens_comp_af_illuminator_guard["af_subj_shift_sens"],
                    "af_assist_setting": res.lens_comp_af_illuminator_guard["af_assist_setting"],
                    "fx3_has_built_in_af_illuminator_led": res.lens_comp_af_illuminator_guard["fx3_has_built_in_af_illuminator_led"],
                    "fx6_has_built_in_af_illuminator_led": res.lens_comp_af_illuminator_guard["fx6_has_built_in_af_illuminator_led"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.lens_comp_af_illuminator_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} lens_comp=(shading={guard['effective_shading_comp']},"
                f"ca={guard['effective_ca_comp']},dist={guard['effective_distortion_comp']},"
                f"breath={guard['effective_breathing_comp']}) "
                f"af=(trans={guard['af_transition_speed']},shift={guard['af_subj_shift_sens']},"
                f"assist={guard['af_assist_setting']},fx3_led={guard['fx3_has_built_in_af_illuminator_led']},"
                f"fx6_led={guard['fx6_has_built_in_af_illuminator_led']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-aperture-drive-and-folder-rating-guard",
        "verify-g126-aperture-drive-folder-rating",
    ):
        verdict, res = evaluate_g126_aperture_drive_and_folder_rating_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_aperture_drive_in_af": res.aperture_drive_folder_rating_guard["effective_aperture_drive_in_af"],
                    "effective_af_w_shutter": res.aperture_drive_folder_rating_guard["effective_af_w_shutter"],
                    "effective_pre_af": res.aperture_drive_folder_rating_guard["effective_pre_af"],
                    "effective_circ_of_focus_point": res.aperture_drive_folder_rating_guard["effective_circ_of_focus_point"],
                    "effective_focus_area_color": res.aperture_drive_folder_rating_guard["effective_focus_area_color"],
                    "effective_folder_name_form": res.aperture_drive_folder_rating_guard["effective_folder_name_form"],
                    "slot_1_contains_tier0_vault": res.aperture_drive_folder_rating_guard["slot_1_contains_tier0_vault"],
                    "slot1_metadata_sector_writes": res.aperture_drive_folder_rating_guard["slot1_metadata_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.aperture_drive_folder_rating_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} focus=(ap={guard['effective_aperture_drive_in_af']},"
                f"shutter={guard['effective_af_w_shutter']},pre_af={guard['effective_pre_af']},"
                f"circ={guard['effective_circ_of_focus_point']},color={guard['effective_focus_area_color']}) "
                f"folder=(form={guard['effective_folder_name_form']},slot1_vault={guard['slot_1_contains_tier0_vault']},"
                f"s1_writes={guard['slot1_metadata_sector_writes']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-126-gates":
        report = evaluate_126gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g125_status": report.g125_result["status"],
                    "g126_status": report.g126_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/126 "
                f"g125_to_g126_all_passed={report.g125_to_g126_all_passed} "
                f"all_126_gates_verified={report.all_126_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_126_gates_verified if args.dry_run_simulated else report.offline_123_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-switch-vh-af-and-exposure-stdadj-guard",
        "verify-g127-switch-vh-af-exposure-stdadj",
    ):
        verdict, res = evaluate_g127_switch_vh_af_and_exposure_stdadj_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_switch_vh_af_area": res.switch_vh_af_exposure_stdadj_guard["effective_switch_vh_af_area"],
                    "enabled_focus_area_limit_count": res.switch_vh_af_exposure_stdadj_guard["enabled_focus_area_limit_count"],
                    "exposure_std_adjust_metering_mode_count": res.switch_vh_af_exposure_stdadj_guard["exposure_std_adjust_metering_mode_count"],
                    "exposure_std_adjust_survived_cam_reset": res.switch_vh_af_exposure_stdadj_guard["exposure_std_adjust_survived_cam_reset"],
                    "effective_bracket_selftimer": res.switch_vh_af_exposure_stdadj_guard["effective_bracket_selftimer"],
                    "effective_bracket_order": res.switch_vh_af_exposure_stdadj_guard["effective_bracket_order"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.switch_vh_af_exposure_stdadj_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} vh={guard['effective_switch_vh_af_area']} "
                f"limit_n={guard['enabled_focus_area_limit_count']} "
                f"std_modes={guard['exposure_std_adjust_metering_mode_count']} "
                f"std_survived={guard['exposure_std_adjust_survived_cam_reset']} "
                f"bracket=({guard['effective_bracket_selftimer']},{guard['effective_bracket_order']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-tcub-format-and-playback-copy-slot-guard",
        "verify-g128-tcub-playback-copy-slot",
    ):
        verdict, res = evaluate_g128_tcub_format_and_playback_copy_slot_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_tc_format": res.tcub_playback_copy_slot_guard["effective_tc_format"],
                    "effective_tcub_disp_setting": res.tcub_playback_copy_slot_guard["effective_tcub_disp_setting"],
                    "tcub_6_items_survived_cam_reset": res.tcub_playback_copy_slot_guard["tcub_6_items_survived_cam_reset"],
                    "copy_direction_label": res.tcub_playback_copy_slot_guard["copy_direction_label"],
                    "slot_1_contains_tier0_vault": res.tcub_playback_copy_slot_guard["slot_1_contains_tier0_vault"],
                    "slot1_data_sector_writes": res.tcub_playback_copy_slot_guard["slot1_data_sector_writes"],
                    "effective_slide_show_interval": res.tcub_playback_copy_slot_guard["effective_slide_show_interval"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.tcub_playback_copy_slot_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} tcub=(fmt={guard['effective_tc_format']},"
                f"disp={guard['effective_tcub_disp_setting']},survived={guard['tcub_6_items_survived_cam_reset']}) "
                f"copy=(dir={guard['copy_direction_label']},slot1_vault={guard['slot_1_contains_tier0_vault']},"
                f"s1_writes={guard['slot1_data_sector_writes']}) "
                f"slideshow=(int={guard['effective_slide_show_interval']}) "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-128-gates":
        report = evaluate_128gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g127_status": report.g127_result["status"],
                    "g128_status": report.g128_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/128 "
                f"g127_to_g128_all_passed={report.g127_to_g128_all_passed} "
                f"all_128_gates_verified={report.all_128_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_128_gates_verified if args.dry_run_simulated else report.offline_125_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-touch-shooting-and-disp-evf-absence-guard",
        "verify-g129-touch-shooting-disp-evf",
    ):
        verdict, res = evaluate_g129_touch_shooting_and_disp_evf_absence_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_touch_operation": res.touch_shooting_disp_evf_guard["effective_touch_operation"],
                    "effective_touch_sensitivity": res.touch_shooting_disp_evf_guard["effective_touch_sensitivity"],
                    "effective_touch_func_in_shooting": res.touch_shooting_disp_evf_guard["effective_touch_func_in_shooting"],
                    "effective_swipe_up": res.touch_shooting_disp_evf_guard["effective_swipe_up"],
                    "disp_shoot_pages_enabled": res.touch_shooting_disp_evf_guard["disp_shoot_pages_enabled"],
                    "disp_play_pages_enabled": res.touch_shooting_disp_evf_guard["disp_play_pages_enabled"],
                    "fx3_has_builtin_evf": res.touch_shooting_disp_evf_guard["fx3_has_builtin_evf"],
                    "evf_scanout_blocked": res.touch_shooting_disp_evf_guard["evf_scanout_blocked"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.touch_shooting_disp_evf_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} touch=({guard['effective_touch_operation']},"
                f"{guard['effective_touch_sensitivity']},{guard['effective_touch_func_in_shooting']},"
                f"{guard['effective_swipe_up']}) disp_shoot={len(guard['disp_shoot_pages_enabled'])} "
                f"fx3_evf={guard['fx3_has_builtin_evf']} evf_blocked={guard['evf_scanout_blocked']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-ael-wireless-flash-and-interval-pb-edit-guard",
        "verify-g130-ael-flash-interval-pb-edit",
    ):
        verdict, res = evaluate_g130_ael_wireless_flash_and_interval_pb_edit_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_ael_w_shutter": res.ael_flash_interval_pb_edit_guard["effective_ael_w_shutter"],
                    "effective_exp_comp_set": res.ael_flash_interval_pb_edit_guard["effective_exp_comp_set"],
                    "effective_wireless_flash": res.ael_flash_interval_pb_edit_guard["effective_wireless_flash"],
                    "effective_play_speed_for_interval": res.ael_flash_interval_pb_edit_guard["effective_play_speed_for_interval"],
                    "play_speed_scale_max": res.ael_flash_interval_pb_edit_guard["play_speed_scale_max"],
                    "slot_1_contains_tier0_vault": res.ael_flash_interval_pb_edit_guard["slot_1_contains_tier0_vault"],
                    "slot1_data_sector_writes": res.ael_flash_interval_pb_edit_guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.ael_flash_interval_pb_edit_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} ael={guard['effective_ael_w_shutter']} "
                f"exp_comp_set={guard['effective_exp_comp_set']} "
                f"wireless={guard['effective_wireless_flash']} "
                f"interval_spd={guard['effective_play_speed_for_interval']}/9 "
                f"slot1_vault={guard['slot_1_contains_tier0_vault']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-130-gates":
        report = evaluate_130gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g129_status": report.g129_result["status"],
                    "g130_status": report.g130_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/130 "
                f"g129_to_g130_all_passed={report.g129_to_g130_all_passed} "
                f"all_130_gates_verified={report.all_130_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_130_gates_verified if args.dry_run_simulated else report.offline_127_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-dial-customize-mydial-fn-guard",
        "verify-g131-dial-customize-mydial-fn",
    ):
        verdict, res = evaluate_g131_dial_customize_mydial_fn_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "dial_customize_5_items": res.dial_customize_mydial_fn_guard["dial_customize_5_items"],
                    "fx3_physical_3_dials": res.dial_customize_mydial_fn_guard["fx3_physical_3_dials"],
                    "effective_av_tv_rotate": res.dial_customize_mydial_fn_guard["effective_av_tv_rotate"],
                    "effective_function_ring": res.dial_customize_mydial_fn_guard["effective_function_ring"],
                    "effective_lock_operation_parts": res.dial_customize_mydial_fn_guard["effective_lock_operation_parts"],
                    "fn_menu_still_slots": res.dial_customize_mydial_fn_guard["fn_menu_still_slots"],
                    "fn_menu_movie_slots": res.dial_customize_mydial_fn_guard["fn_menu_movie_slots"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.dial_customize_mydial_fn_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} dials={len(guard['fx3_physical_3_dials'])} "
                f"av_tv={guard['effective_av_tv_rotate']} ring={guard['effective_function_ring']} "
                f"lock={guard['effective_lock_operation_parts']} "
                f"fn_split={guard['fn_menu_still_slots']}+{guard['fn_menu_movie_slots']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-liveview-grid-lut-embed-guard",
        "verify-g132-liveview-grid-lut-embed",
    ):
        verdict, res = evaluate_g132_liveview_grid_lut_embed_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_live_view_display": res.liveview_grid_lut_embed_guard["effective_live_view_display"],
                    "effective_exposure_effect": res.liveview_grid_lut_embed_guard["effective_exposure_effect"],
                    "effective_frame_rate_low_limit": res.liveview_grid_lut_embed_guard["effective_frame_rate_low_limit"],
                    "effective_grid_line_display": res.liveview_grid_lut_embed_guard["effective_grid_line_display"],
                    "effective_grid_line_type": res.liveview_grid_lut_embed_guard["effective_grid_line_type"],
                    "effective_select_lut": res.liveview_grid_lut_embed_guard["effective_select_lut"],
                    "effective_embed_lut_file": res.liveview_grid_lut_embed_guard["effective_embed_lut_file"],
                    "slot_1_contains_tier0_vault": res.liveview_grid_lut_embed_guard["slot_1_contains_tier0_vault"],
                    "slot1_data_sector_writes": res.liveview_grid_lut_embed_guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.liveview_grid_lut_embed_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} lv={guard['effective_live_view_display']} "
                f"fr_low={guard['effective_frame_rate_low_limit']} "
                f"grid={guard['effective_grid_line_display']} "
                f"lut={guard['effective_select_lut']} embed={guard['effective_embed_lut_file']} "
                f"slot1_vault={guard['slot_1_contains_tier0_vault']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-132-gates":
        report = evaluate_132gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g131_status": report.g131_result["status"],
                    "g132_status": report.g132_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/132 "
                f"g131_to_g132_all_passed={report.g131_to_g132_all_passed} "
                f"all_132_gates_verified={report.all_132_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_132_gates_verified if args.dry_run_simulated else report.offline_129_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-steadyshot-selftimer-guard",
        "verify-g133-steadyshot-selftimer",
    ):
        verdict, res = evaluate_g133_steadyshot_selftimer_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.steadyshot_selftimer_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_movie_steadyshot": guard["effective_movie_steadyshot"],
                    "effective_still_steadyshot": guard["effective_still_steadyshot"],
                    "effective_focal_length_mm": guard["effective_focal_length_mm"],
                    "focal_length_table_count": guard["focal_length_table_count"],
                    "movie_active_locked_out": guard["movie_active_locked_out"],
                    "effective_drive_mode": guard["effective_drive_mode"],
                    "effective_audio_signals": guard["effective_audio_signals"],
                    "fx3_has_5axis_ibis": guard["fx3_has_5axis_ibis"],
                    "fx6_has_5axis_ibis": guard["fx6_has_5axis_ibis"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.steadyshot_selftimer_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} movie_ss={guard['effective_movie_steadyshot']} "
                f"still_ss={guard['effective_still_steadyshot']} "
                f"fl={guard['effective_focal_length_mm']}mm/{guard['focal_length_table_count']} "
                f"drive={guard['effective_drive_mode']} audio={guard['effective_audio_signals']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-zebra-peaking-streaming-firewall-guard",
        "verify-g134-zebra-streaming-firewall",
    ):
        verdict, res = evaluate_g134_zebra_streaming_firewall_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.zebra_peaking_streaming_firewall_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_zebra_display": guard["effective_zebra_display"],
                    "effective_zebra_level": guard["effective_zebra_level"],
                    "effective_peaking_display": guard["effective_peaking_display"],
                    "effective_peaking_color": guard["effective_peaking_color"],
                    "streaming_protocol": guard["streaming_protocol"],
                    "streaming_resolution": guard["streaming_resolution"],
                    "streaming_frame_rate": guard["streaming_frame_rate"],
                    "effective_airplane_mode": guard["effective_airplane_mode"],
                    "wireless_packets_emitted": guard["wireless_packets_emitted"],
                    "slot_1_contains_tier0_vault": guard["slot_1_contains_tier0_vault"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.zebra_peaking_streaming_firewall_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} zebra={guard['effective_zebra_display']}/{guard['effective_zebra_level']} "
                f"peak={guard['effective_peaking_display']}/{guard['effective_peaking_color']} "
                f"proto={guard['streaming_protocol']}@{guard['streaming_resolution']}/{guard['streaming_frame_rate']} "
                f"air={guard['effective_airplane_mode']} rf_pkts={guard['wireless_packets_emitted']} "
                f"slot1_vault={guard['slot_1_contains_tier0_vault']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-134-gates":
        report = evaluate_134gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g133_status": report.g133_result["status"],
                    "g134_status": report.g134_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/134 "
                f"g133_to_g134_all_passed={report.g133_to_g134_all_passed} "
                f"all_134_gates_verified={report.all_134_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_134_gates_verified if args.dry_run_simulated else report.offline_131_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-bright-mon-shotmark-vault-guard",
        "verify-g135-bright-mon-shotmark-vault",
    ):
        verdict, res = evaluate_g135_bright_mon_shotmark_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.bright_mon_shotmark_vault_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_bright_monitoring_active": guard["effective_bright_monitoring_active"],
                    "effective_live_view_display": guard["effective_live_view_display"],
                    "focus_magnifier_coexists_with_bright_monitoring": guard[
                        "focus_magnifier_coexists_with_bright_monitoring"
                    ],
                    "effective_monitor_brightness_mode": guard["effective_monitor_brightness_mode"],
                    "effective_monitor_brightness_level": guard["effective_monitor_brightness_level"],
                    "requested_card_op": guard["requested_card_op"],
                    "slot_1_contains_tier0_vault": guard["slot_1_contains_tier0_vault"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.bright_mon_shotmark_vault_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} bright_mon={guard['effective_bright_monitoring_active']} "
                f"lv={guard['effective_live_view_display']} "
                f"mon={guard['effective_monitor_brightness_mode']}({guard['effective_monitor_brightness_level']}) "
                f"op={guard['requested_card_op']} "
                f"slot1_vault={guard['slot_1_contains_tier0_vault']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-tc-link-wifi-usblan-bulb-dormant-guard",
        "verify-g136-tc-link-wifi-usblan-bulb-dormant",
    ):
        verdict, res = evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.tc_link_wifi_usblan_bulb_dormant_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "fx3_bluetooth_tc_link_symbols": guard["fx3_bluetooth_tc_link_symbols"],
                    "ext_tc_lock_status": guard["ext_tc_lock_status"],
                    "fx3_sku_code": guard["fx3_sku_code"],
                    "requested_wifi_security": guard["requested_wifi_security"],
                    "usb_lan_active": guard["usb_lan_active"],
                    "effective_airplane_mode": guard["effective_airplane_mode"],
                    "wireless_packets_emitted": guard["wireless_packets_emitted"],
                    "effective_bulb_active": guard["effective_bulb_active"],
                    "effective_dro_mode": guard["effective_dro_mode"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.tc_link_wifi_usblan_bulb_dormant_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} bt_tc={guard['fx3_bluetooth_tc_link_symbols']} "
                f"ext_lk={guard['ext_tc_lock_status']} sku={guard['fx3_sku_code']} "
                f"wifi_sec={guard['requested_wifi_security']} usblan={guard['usb_lan_active']} "
                f"air={guard['effective_airplane_mode']} rf_pkts={guard['wireless_packets_emitted']} "
                f"bulb={guard['effective_bulb_active']} dro={guard['effective_dro_mode']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-136-gates":
        report = evaluate_136gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g135_status": report.g135_result["status"],
                    "g136_status": report.g136_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/136 "
                f"g135_to_g136_all_passed={report.g135_to_g136_all_passed} "
                f"all_136_gates_verified={report.all_136_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_136_gates_verified if args.dry_run_simulated else report.offline_133_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-big6-home-framing-interval-vault-guard",
        "verify-g137-big6-home-framing-interval",
    ):
        verdict, res = evaluate_g137_big6_home_framing_interval_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.big6_home_framing_interval_vault_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_mode_settings": guard["effective_mode_settings"],
                    "big6_screen_active": guard["big6_screen_active"],
                    "big6_hdmi_output_active": guard["big6_hdmi_output_active"],
                    "effective_home_lower_left": guard["effective_home_lower_left"],
                    "fx3_physical_end_actuator_present": guard["fx3_physical_end_actuator_present"],
                    "effective_framing_on": guard["effective_framing_on"],
                    "fx3_framing_support_lock": guard["fx3_framing_support_lock"],
                    "effective_interval_shooting": guard["effective_interval_shooting"],
                    "interval_shot_count": guard["interval_shot_count"],
                    "slot_1_contains_tier0_vault": guard["slot_1_contains_tier0_vault"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.big6_home_framing_interval_vault_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} big6_mode={guard['effective_mode_settings']} "
                f"big6_active={guard['big6_screen_active']} "
                f"lower_left={guard['effective_home_lower_left']} "
                f"fx3_end_hw={guard['fx3_physical_end_actuator_present']} "
                f"framing={guard['effective_framing_on']} "
                f"interval={guard['effective_interval_shooting']} "
                f"slot1_vault={guard['slot_1_contains_tier0_vault']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-tc-make-hdmi-rec-ssh-authen-fan-guard",
        "verify-g138-tc-make-hdmi-rec-ssh-fan",
    ):
        verdict, res = evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.tc_make_hdmi_rec_ssh_authen_fan_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_tc_make": guard["effective_tc_make"],
                    "effective_tc_run": guard["effective_tc_run"],
                    "tc_regenerate_forced_rec_run": guard["tc_regenerate_forced_rec_run"],
                    "ext_tc_lock_status": guard["ext_tc_lock_status"],
                    "effective_hdmi_rec_control": guard["effective_hdmi_rec_control"],
                    "cardless_hdmi_rec_ctrl_permitted": guard["cardless_hdmi_rec_ctrl_permitted"],
                    "effective_access_authen_settings": guard["effective_access_authen_settings"],
                    "sshd_control_active": guard["sshd_control_active"],
                    "access_authen_transports": guard["access_authen_transports"],
                    "effective_fan_control": guard["effective_fan_control"],
                    "fx3_exact_fan_modes_count": guard["fx3_exact_fan_modes_count"],
                    "fx6_exact_fan_modes_count": guard["fx6_exact_fan_modes_count"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.tc_make_hdmi_rec_ssh_authen_fan_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} tc_make={guard['effective_tc_make']} "
                f"tc_run={guard['effective_tc_run']} "
                f"hdmi_rec={guard['effective_hdmi_rec_control']} "
                f"authen={guard['effective_access_authen_settings']} "
                f"sshd={guard['sshd_control_active']} "
                f"fan={guard['effective_fan_control']} "
                f"fx3_fan_modes={guard['fx3_exact_fan_modes_count']} "
                f"fx6_fan_modes={guard['fx6_exact_fan_modes_count']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-138-gates":
        report = evaluate_138gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g137_status": report.g137_result["status"],
                    "g138_status": report.g138_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/138 "
                f"g137_to_g138_all_passed={report.g137_to_g138_all_passed} "
                f"all_138_gates_verified={report.all_138_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_138_gates_verified if args.dry_run_simulated else report.offline_135_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-rec-media-autoswitch-proxy-vault-guard",
        "verify-g139-rec-media-autoswitch-proxy",
    ):
        verdict, res = evaluate_g139_rec_media_autoswitch_proxy_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.rec_media_autoswitch_proxy_vault_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_recording_media": guard["effective_recording_media"],
                    "effective_auto_switch_media": guard["effective_auto_switch_media"],
                    "auto_switch_survived_cam_reset": guard["auto_switch_survived_cam_reset"],
                    "slot1_vault_firewall_blocked": guard["slot1_vault_firewall_blocked"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "media_card_type": guard["media_card_type"],
                    "effective_proxy_recording": guard["effective_proxy_recording"],
                    "proxy_file_format": guard["proxy_file_format"],
                    "proxy_record_setting": guard["proxy_record_setting"],
                    "proxy_sub_dir_path": guard["proxy_sub_dir_path"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.rec_media_autoswitch_proxy_vault_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} rec_media={guard['effective_recording_media']} "
                f"auto_switch={guard['effective_auto_switch_media']} "
                f"card={guard['media_card_type']} "
                f"proxy={guard['effective_proxy_recording']} "
                f"proxy_fmt={guard['proxy_file_format']}/{guard['proxy_record_setting']} "
                f"slot1_vault={guard['slot_1_contains_tier0_vault']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-creators-cloud-zerorf-mymenu42-guard",
        "verify-g140-creators-cloud-zerorf-mymenu",
    ):
        verdict, res = evaluate_g140_creators_cloud_zerorf_mymenu42_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.creators_cloud_zerorf_mymenu42_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_cloud_connection": guard["effective_cloud_connection"],
                    "effective_airplane_mode": guard["effective_airplane_mode"],
                    "effective_cnct_while_power_off": guard["effective_cnct_while_power_off"],
                    "ble_power_off_energized": guard["ble_power_off_energized"],
                    "zero_rf_enforced": guard["zero_rf_enforced"],
                    "rf_packets_transmitted": guard["rf_packets_transmitted"],
                    "mymenu_exact_slots": guard["mymenu_exact_slots"],
                    "fx6_user_menu_max_items": guard["fx6_user_menu_max_items"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.creators_cloud_zerorf_mymenu42_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} cloud={guard['effective_cloud_connection']} "
                f"airplane={guard['effective_airplane_mode']} "
                f"cnct_power_off={guard['effective_cnct_while_power_off']} "
                f"ble_energized={guard['ble_power_off_energized']} "
                f"zero_rf={guard['zero_rf_enforced']} "
                f"rf_pkts={guard['rf_packets_transmitted']} "
                f"mymenu_slots={guard['mymenu_exact_slots']} "
                f"fx6_user_menu={guard['fx6_user_menu_max_items']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-140-gates":
        report = evaluate_140gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g139_status": report.g139_result["status"],
                    "g140_status": report.g140_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/140 "
                f"g139_to_g140_all_passed={report.g139_to_g140_all_passed} "
                f"all_140_gates_verified={report.all_140_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_140_gates_verified if args.dry_run_simulated else report.offline_137_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-ftp-ftpes-avf-vault-customwb-guard",
        "verify-g141-ftp-ftpes-customwb",
    ):
        verdict, res = evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.ftp_ftpes_customwb_vault_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_ftp_function": guard["effective_ftp_function"],
                    "ftp_server_slot": guard["ftp_server_slot"],
                    "ftp_protocol": guard["ftp_protocol"],
                    "ftp_transfer_mode": guard["ftp_transfer_mode"],
                    "slot1_avf_info_firewall_blocked": guard["slot1_avf_info_firewall_blocked"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "effective_airplane_mode": guard["effective_airplane_mode"],
                    "effective_usblan_tethering": guard["effective_usblan_tethering"],
                    "zero_rf_and_usblan_isolated": guard["zero_rf_and_usblan_isolated"],
                    "wired_usblan_ftp_packets": guard["wired_usblan_ftp_packets"],
                    "effective_white_balance": guard["effective_white_balance"],
                    "effective_shutter_awb_lock": guard["effective_shutter_awb_lock"],
                    "effective_shockless_wb": guard["effective_shockless_wb"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.ftp_ftpes_customwb_vault_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} ftp={guard['effective_ftp_function']} "
                f"slot={guard['ftp_server_slot']} proto={guard['ftp_protocol']} "
                f"usblan={guard['effective_usblan_tethering']} "
                f"zero_rf_usblan={guard['zero_rf_and_usblan_isolated']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"wb={guard['effective_white_balance']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-movie-af-focusmap-marker-peaking-guard",
        "verify-g142-movie-af-focusmap-marker",
    ):
        verdict, res = evaluate_g142_movie_af_focusmap_marker_peaking_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.movie_af_focusmap_marker_peaking_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_af_transition_speed": guard["effective_af_transition_speed"],
                    "effective_af_subj_shift_sensitivity": guard["effective_af_subj_shift_sensitivity"],
                    "effective_af_assist": guard["effective_af_assist"],
                    "fx3_onbody_focus_map_menu_present": guard["fx3_onbody_focus_map_menu_present"],
                    "external_monitor_control_focus_map_active": guard["external_monitor_control_focus_map_active"],
                    "effective_marker_display": guard["effective_marker_display"],
                    "effective_aspect_marker": guard["effective_aspect_marker"],
                    "exact_15_active_aspect_ratios_verified": guard["exact_15_active_aspect_ratios_verified"],
                    "effective_peaking_display": guard["effective_peaking_display"],
                    "effective_peaking_color": guard["effective_peaking_color"],
                    "marker_hdmi_output": guard["marker_hdmi_output"],
                    "peaking_hdmi_output": guard["peaking_hdmi_output"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.movie_af_focusmap_marker_peaking_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} af_speed={guard['effective_af_transition_speed']} "
                f"af_sens={guard['effective_af_subj_shift_sensitivity']} "
                f"af_assist={guard['effective_af_assist']} "
                f"onbody_fm={guard['fx3_onbody_focus_map_menu_present']} "
                f"aspect={guard['effective_aspect_marker']} "
                f"peaking={guard['effective_peaking_color']} "
                f"hdmi_marker={guard['marker_hdmi_output']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-142-gates":
        report = evaluate_142gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g141_status": report.g141_result["status"],
                    "g142_status": report.g142_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/142 "
                f"g141_to_g142_all_passed={report.g141_to_g142_all_passed} "
                f"all_142_gates_verified={report.all_142_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_142_gates_verified if args.dry_run_simulated else report.offline_139_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-shoe-audio-4ch-subject-recog-guard",
        "verify-g143-shoe-audio-subject-recog",
        "verify-g143",
    ):
        verdict, res = evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.shoe_audio_4ch_subject_recog_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "audio_out_timing_menu_path": guard["audio_out_timing_menu_path"],
                    "effective_audio_out_timing": guard["effective_audio_out_timing"],
                    "effective_audio_rec_level": guard["effective_audio_rec_level"],
                    "effective_shoe_audio_set": guard["effective_shoe_audio_set"],
                    "audio_limiter_always_on_fx3": guard["audio_limiter_always_on_fx3"],
                    "effective_face_eye_subject": guard["effective_face_eye_subject"],
                    "animal_eye_af_active_in_mode": guard["animal_eye_af_active_in_mode"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.shoe_audio_4ch_subject_recog_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} out_timing={guard['effective_audio_out_timing']} "
                f"rec_level={guard['effective_audio_rec_level']} "
                f"shoe_audio={guard['effective_shoe_audio_set']} "
                f"subject={guard['effective_face_eye_subject']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-silent-target-bodydata-nogo-guard",
        "verify-g144-silent-target-bodydata-nogo",
        "verify-g144",
    ):
        verdict, res = evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.silent_target_bodydata_nogo_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_silent_mode": guard["effective_silent_mode"],
                    "target_function_exact_2_items": guard["target_function_exact_2_items"],
                    "dormant_shutter_when_pwr_off_blocked": guard["dormant_shutter_when_pwr_off_blocked"],
                    "fx3_bodydata_required_slot": guard["fx3_bodydata_required_slot"],
                    "fx6_bodydata_required_slot": guard["fx6_bodydata_required_slot"],
                    "emmc_writes_authorized": res.emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "hardware_live_attachment_authorized": res.hardware_live_attachment_authorized,
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.silent_target_bodydata_nogo_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} silent={guard['effective_silent_mode']} "
                f"target_items={len(guard['target_function_exact_2_items'])} "
                f"fx3_slot={guard['fx3_bodydata_required_slot']} "
                f"fx6_slot={guard['fx6_bodydata_required_slot']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"emmc_writes_authorized={res.emmc_writes_authorized} "
                f"cross_model_flash_authorized={res.cross_model_flash_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-144-gates":
        report = evaluate_144gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g143_status": report.g143_result["status"],
                    "g144_status": report.g144_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/144 "
                f"g143_to_g144_all_passed={report.g143_to_g144_all_passed} "
                f"all_144_gates_verified={report.all_144_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_144_gates_verified if args.dry_run_simulated else report.offline_141_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-hdmi-raw-desqueeze-guard",
        "verify-g145-hdmi-raw-desqueeze",
        "verify-g145",
    ):
        verdict, res = evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.hdmi_raw_desqueeze_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_rec_media_dur_hdmi": guard["effective_rec_media_dur_hdmi"],
                    "effective_hdmi_output_resolution": guard["effective_hdmi_output_resolution"],
                    "effective_hdmi_4k_output_setting": guard["effective_hdmi_4k_output_setting"],
                    "effective_raw_output": guard["effective_raw_output"],
                    "effective_desqueeze_display": guard["effective_desqueeze_display"],
                    "effective_desqueeze_exec_ratio": guard["effective_desqueeze_exec_ratio"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.hdmi_raw_desqueeze_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} rec_media={guard['effective_rec_media_dur_hdmi']} "
                f"res={guard['effective_hdmi_output_resolution']} "
                f"raw={guard['effective_raw_output']} "
                f"desqueeze={guard['effective_desqueeze_display']}->{guard['effective_desqueeze_exec_ratio']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-reclamp-varshutter-apsc-guard",
        "verify-g146-reclamp-varshutter-apsc",
        "verify-g146",
    ):
        verdict, res = evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.reclamp_varshutter_apsc_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_rec_lamp": guard["effective_rec_lamp"],
                    "effective_emphasized_rec_display": guard["effective_emphasized_rec_display"],
                    "effective_remain_shoot_display": guard["effective_remain_shoot_display"],
                    "effective_auto_review": guard["effective_auto_review"],
                    "effective_anti_flicker_shoot": guard["effective_anti_flicker_shoot"],
                    "effective_apsc_s35_shooting": guard["effective_apsc_s35_shooting"],
                    "apsc_s35_resettable_by_camset_reset": guard["apsc_s35_resettable_by_camset_reset"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.reclamp_varshutter_apsc_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} rec_lamp={guard['effective_rec_lamp']} "
                f"emph={guard['effective_emphasized_rec_display']} "
                f"remain={guard['effective_remain_shoot_display']} "
                f"auto_rev={guard['effective_auto_review']} "
                f"apsc={guard['effective_apsc_s35_shooting']} "
                f"apsc_resettable={guard['apsc_s35_resettable_by_camset_reset']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-146-gates":
        report = evaluate_146gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g145_status": report.g145_result["status"],
                    "g146_status": report.g146_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/146 "
                f"g145_to_g146_all_passed={report.g145_to_g146_all_passed} "
                f"all_146_gates_verified={report.all_146_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_146_gates_verified if args.dry_run_simulated else report.offline_143_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-breathing-camid-reel-sdhc-guard",
        "verify-g147-breathing-camid-reel",
        "verify-g147",
    ):
        verdict, res = evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.breathing_camid_reel_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_breathing_comp": guard["effective_breathing_comp"],
                    "breathing_comp_resettable_by_camset_reset": guard["breathing_comp_resettable_by_camset_reset"],
                    "effective_file_number_mode": guard["effective_file_number_mode"],
                    "effective_file_name_format": guard["effective_file_name_format"],
                    "effective_camera_id": guard["effective_camera_id"],
                    "effective_reel_number": guard["effective_reel_number"],
                    "effective_title_name": guard["effective_title_name"],
                    "sample_output_clip_stem": guard["sample_output_clip_stem"],
                    "sdhc_standard_format_locked": guard["sdhc_standard_format_locked"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.breathing_camid_reel_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} breathing={guard['effective_breathing_comp']} "
                f"fmt={guard['effective_file_name_format']} "
                f"stem={guard['sample_output_clip_stem']} "
                f"sdhc_lock={guard['sdhc_standard_format_locked']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-copyright-powersave-ntscpal-guard",
        "verify-g148-copyright-powersave-ntscpal",
        "verify-g148",
    ):
        verdict, res = evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.copyright_powersave_ntscpal_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_write_copyright_info": guard["effective_write_copyright_info"],
                    "effective_write_serial_number": guard["effective_write_serial_number"],
                    "copyright_and_serial_resettable_by_camset_reset": guard["copyright_and_serial_resettable_by_camset_reset"],
                    "copyright_excluded_from_camset_dat": guard["copyright_excluded_from_camset_dat"],
                    "exact_2_power_setting_items_verified": guard["exact_2_power_setting_items_verified"],
                    "effective_power_save_start_time": guard["effective_power_save_start_time"],
                    "effective_auto_power_off_temp": guard["effective_auto_power_off_temp"],
                    "effective_video_system": guard["effective_video_system"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.copyright_powersave_ntscpal_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} write_copy={guard['effective_write_copyright_info']} "
                f"write_serial={guard['effective_write_serial_number']} "
                f"ps={guard['effective_power_save_start_time']} "
                f"temp={guard['effective_auto_power_off_temp']} "
                f"vsys={guard['effective_video_system']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-148-gates":
        report = evaluate_148gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g147_status": report.g147_result["status"],
                    "g148_status": report.g148_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/148 "
                f"g147_to_g148_all_passed={report.g147_to_g148_all_passed} "
                f"all_148_gates_verified={report.all_148_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_148_gates_verified if args.dry_run_simulated else report.offline_145_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-zoom-ciz-autoslow-baseiso-guard",
        "verify-g149-zoom-ciz-autoslow-baseiso",
        "verify-g149",
    ):
        verdict, res = evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.zoom_ciz_autoslow_baseiso_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_zoom_range": guard["effective_zoom_range"],
                    "effective_max_zoom_scale": guard["effective_max_zoom_scale"],
                    "zoom_range_and_ring_resettable_by_camset_reset": guard["zoom_range_and_ring_resettable_by_camset_reset"],
                    "zoom_speeds_resettable_by_camset_reset": guard["zoom_speeds_resettable_by_camset_reset"],
                    "effective_auto_slow_shutter": guard["effective_auto_slow_shutter"],
                    "effective_low_base_iso": guard["effective_low_base_iso"],
                    "effective_high_base_iso": guard["effective_high_base_iso"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.zoom_ciz_autoslow_baseiso_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} zoom_range={guard['effective_zoom_range']} "
                f"scale={guard['effective_max_zoom_scale']} "
                f"autoslow={guard['effective_auto_slow_shutter']} "
                f"base_iso={guard['effective_low_base_iso']}/{guard['effective_high_base_iso']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-still-arw-hlg-usblun-uvc-guard",
        "verify-g150-still-arw-hlg-usblun-uvc",
        "verify-g150",
    ):
        verdict, res = evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.still_arw_hlg_usblun_uvc_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_raw_file_type": guard["effective_raw_file_type"],
                    "dormant_lossless_raw_rejected": guard["dormant_lossless_raw_rejected"],
                    "effective_hlg_still_image": guard["effective_hlg_still_image"],
                    "effective_usb_lun_setting": guard["effective_usb_lun_setting"],
                    "np_fz100_pd_boot_gate_satisfied": guard["np_fz100_pd_boot_gate_satisfied"],
                    "dormant_native_uvc_streaming_rejected": guard["dormant_native_uvc_streaming_rejected"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.still_arw_hlg_usblun_uvc_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} raw={guard['effective_raw_file_type']} "
                f"hlg={guard['effective_hlg_still_image']} "
                f"lun={guard['effective_usb_lun_setting']} "
                f"pd_ok={guard['np_fz100_pd_boot_gate_satisfied']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-150-gates":
        report = evaluate_150gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g149_status": report.g149_result["status"],
                    "g150_status": report.g150_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/150 "
                f"g149_to_g150_all_passed={report.g149_to_g150_all_passed} "
                f"all_150_gates_verified={report.all_150_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_150_gates_verified if args.dry_run_simulated else report.offline_147_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-drive-focusbracket-shutter-efcs-nr-guard",
        "verify-g151-drive-shutter-efcs-nr",
        "verify-g151",
    ):
        verdict, res = evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.drive_focusbracket_shutter_efcs_nr_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_drive_mode": guard["effective_drive_mode"],
                    "effective_max_fps": guard["effective_max_fps"],
                    "dormant_focus_bracket_rejected": guard["dormant_focus_bracket_rejected"],
                    "effective_shutter_type": guard["effective_shutter_type"],
                    "dormant_shutter_auto_rejected": guard["dormant_shutter_auto_rejected"],
                    "effective_flash_xsync_ceiling": guard["effective_flash_xsync_ceiling"],
                    "effective_efcs": guard["effective_efcs"],
                    "efcs_resettable_by_camset_reset": guard["efcs_resettable_by_camset_reset"],
                    "effective_long_exposure_nr": guard["effective_long_exposure_nr"],
                    "effective_high_iso_nr": guard["effective_high_iso_nr"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.drive_focusbracket_shutter_efcs_nr_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} drive={guard['effective_drive_mode']} "
                f"fps={guard['effective_max_fps']} "
                f"shutter={guard['effective_shutter_type']} "
                f"xsync={guard['effective_flash_xsync_ceiling']} "
                f"efcs={guard['effective_efcs']} "
                f"long_nr={guard['effective_long_exposure_nr']} "
                f"high_iso_nr={guard['effective_high_iso_nr']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-creative-look-soft-skin-delete-protect-recoverdb-guard",
        "verify-g152-creativelook-delete-recoverdb",
        "verify-g152",
    ):
        verdict, res = evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.creative_look_delete_protect_recoverdb_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_creative_look": guard["effective_creative_look"],
                    "dormant_soft_skin_rejected": guard["dormant_soft_skin_rejected"],
                    "effective_delete_confirm": guard["effective_delete_confirm"],
                    "effective_delete_pressing_twice": guard["effective_delete_pressing_twice"],
                    "slot1_tier0_vault_firewall_blocked": guard["slot1_tier0_vault_firewall_blocked"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "emmc_nflasha_write_count": guard["emmc_nflasha_write_count"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.creative_look_delete_protect_recoverdb_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} look={guard['effective_creative_look']} "
                f"del_confirm={guard['effective_delete_confirm']} "
                f"del_twice={guard['effective_delete_pressing_twice']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-152-gates":
        report = evaluate_152gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g151_status": report.g151_result["status"],
                    "g152_status": report.g152_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/152 "
                f"g151_to_g152_all_passed={report.g151_to_g152_all_passed} "
                f"all_152_gates_verified={report.all_152_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_152_gates_verified if args.dry_run_simulated else report.offline_149_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-pixelmap-apr-monitor-vfadjust-guard",
        "verify-g153-pixelmap-apr-monitor",
        "verify-g153",
    ):
        verdict, res = evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.pixelmap_apr_monitor_vfadjust_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_auto_pixel_mapping_setup": guard["effective_auto_pixel_mapping_setup"],
                    "effective_auto_pixel_mapping_silent": guard["effective_auto_pixel_mapping_silent"],
                    "effective_monitor_brightness_mode": guard["effective_monitor_brightness_mode"],
                    "effective_display_quality": guard["effective_display_quality"],
                    "effective_monitor_flip_direction": guard["effective_monitor_flip_direction"],
                    "dormant_evf_exposed_items_fx3": guard["dormant_evf_exposed_items_fx3"],
                    "fx3_finder_monitor_group_present": guard["fx3_finder_monitor_group_present"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.pixelmap_apr_monitor_vfadjust_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} setup_apm={guard['effective_auto_pixel_mapping_setup']} "
                f"silent_apm={guard['effective_auto_pixel_mapping_silent']} "
                f"dq={guard['effective_display_quality']} "
                f"flip={guard['effective_monitor_flip_direction']} "
                f"dormant_evf={guard['dormant_evf_exposed_items_fx3']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-recall-custom-hold-hdmi-reccontrol-guard",
        "verify-g154-customhold-hdmi-reccontrol",
        "verify-g154",
    ):
        verdict, res = evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.recall_custom_hold_hdmi_reccontrol_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "recall_custom_hold_available": guard["recall_custom_hold_available"],
                    "recall_custom_hold_standalone_wb_present": guard["recall_custom_hold_standalone_wb_present"],
                    "effective_rec_media_dur_hdmi_output": guard["effective_rec_media_dur_hdmi_output"],
                    "effective_time_code_output": guard["effective_time_code_output"],
                    "effective_rec_control": guard["effective_rec_control"],
                    "slot1_tier0_vault_firewall_blocked": guard["slot1_tier0_vault_firewall_blocked"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "emmc_nflasha_write_count": guard["emmc_nflasha_write_count"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.recall_custom_hold_hdmi_reccontrol_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} hold_avail={guard['recall_custom_hold_available']} "
                f"rec_media={guard['effective_rec_media_dur_hdmi_output']} "
                f"tc_out={guard['effective_time_code_output']} "
                f"rec_ctrl={guard['effective_rec_control']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-154-gates":
        report = evaluate_154gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g153_status": report.g153_result["status"],
                    "g154_status": report.g154_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/154 "
                f"g153_to_g154_all_passed={report.g153_to_g154_all_passed} "
                f"all_154_gates_verified={report.all_154_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_154_gates_verified if args.dry_run_simulated else report.offline_151_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-areadate-grid-cleanhdmi-guard",
        "verify-g155-areadate-grid-cleanhdmi",
        "verify-g155",
    ):
        verdict, res = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.areadate_grid_cleanhdmi_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "area_gmt_zones_count": guard["area_gmt_zones_count"],
                    "rtc_battery_charged": guard["rtc_battery_charged"],
                    "grid_rendered_on_hdmi": guard["grid_rendered_on_hdmi"],
                    "marker_rendered_on_hdmi": guard["marker_rendered_on_hdmi"],
                    "hdmi_marker_injected_pixels": guard["hdmi_marker_injected_pixels"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.areadate_grid_cleanhdmi_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} zones={guard['area_gmt_zones_count']} "
                f"rtc={guard['rtc_battery_charged']} "
                f"grid_hdmi={guard['grid_rendered_on_hdmi']} "
                f"marker_hdmi={guard['marker_rendered_on_hdmi']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-saveload-camset-mishoe-genlock-guard",
        "verify-g156-saveload-camset-mishoe",
        "verify-g156",
    ):
        verdict, res = evaluate_g156_saveload_camset_mishoe_genlock_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.saveload_camset_mishoe_genlock_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_operation": guard["effective_operation"],
                    "effective_target_media": guard["effective_target_media"],
                    "slot1_tier0_vault_firewall_blocked": guard["slot1_tier0_vault_firewall_blocked"],
                    "slot1_data_sector_writes": guard["slot1_data_sector_writes"],
                    "emmc_nflasha_write_count": guard["emmc_nflasha_write_count"],
                    "fx3_physical_sync_terminal_present": guard["fx3_physical_sync_terminal_present"],
                    "mishoe_xlr_h1_exclusion_triggered": guard["mishoe_xlr_h1_exclusion_triggered"],
                    "fx6_physical_genlock_bnc_present": guard["fx6_physical_genlock_bnc_present"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.saveload_camset_mishoe_genlock_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} op={guard['effective_operation']} "
                f"media={guard['effective_target_media']} "
                f"s1_writes={guard['slot1_data_sector_writes']} "
                f"sync={guard['fx3_physical_sync_terminal_present']} "
                f"xlr_excl={guard['mishoe_xlr_h1_exclusion_triggered']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-156-gates":
        report = evaluate_156gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g155_status": report.g155_result["status"],
                    "g156_status": report.g156_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/156 "
                f"g155_to_g156_all_passed={report.g155_to_g156_all_passed} "
                f"all_156_gates_verified={report.all_156_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_156_gates_verified if args.dry_run_simulated else report.offline_153_gates_verified
        return 0 if ok else 1

    if args.cmd in (
        "verify-pbmag-varshutter-ecs-guard",
        "verify-g157-pbmag-varshutter-ecs",
        "verify-g157",
    ):
        verdict, res = evaluate_g157_pbmag_varshutter_ecs_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.pbmag_varshutter_ecs_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "effective_playback_media_kind": guard["effective_playback_media_kind"],
                    "effective_mag_factor": guard["effective_mag_factor"],
                    "movie_playback_zoom_supported": guard["movie_playback_zoom_supported"],
                    "effective_anti_flicker_shoot": guard["effective_anti_flicker_shoot"],
                    "fx3_var_shutter_exposed": guard["fx3_var_shutter_exposed"],
                    "fx3_anti_flicker_tv_scan_exposed": guard["fx3_anti_flicker_tv_scan_exposed"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.pbmag_varshutter_ecs_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} pb_kind={guard['effective_playback_media_kind']} "
                f"mag={guard['effective_mag_factor']} "
                f"movie_zoom={guard['movie_playback_zoom_supported']} "
                f"af_shoot={guard['effective_anti_flicker_shoot']} "
                f"var_shutter={guard['fx3_var_shutter_exposed']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd in (
        "verify-wifi5ghz-nvs-ir-lanc-cec-guard",
        "verify-g158-wifi5ghz-nvs-ir-lanc-cec",
        "verify-g158",
    ):
        verdict, res = evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
            repo_root=args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
        )
        if args.json:
            guard = res.wifi5ghz_nvs_ir_lanc_cec_guard
            payload = (
                {
                    "gate": verdict.gate_id,
                    "status": res.status,
                    "verification_mode": res.verification_mode,
                    "valid": res.valid,
                    "wifi_sku_code": guard["wifi_sku_code"],
                    "effective_wifi_band": guard["effective_wifi_band"],
                    "effective_airplane_mode": guard["effective_airplane_mode"],
                    "p12_p13_ms_readonly_enforced": guard["p12_p13_ms_readonly_enforced"],
                    "rf_nvs_mutation_bytes": guard["rf_nvs_mutation_bytes"],
                    "effective_ctrl_for_hdmi": guard["effective_ctrl_for_hdmi"],
                    "cec_key_events_count": guard["cec_key_events_count"],
                    "cec_rec_event_count": guard["cec_rec_event_count"],
                    "fx3_physical_lanc_25mm_present": guard["fx3_physical_lanc_25mm_present"],
                    "persistent_emmc_writes_authorized": res.persistent_emmc_writes_authorized,
                    "cross_model_flash_authorized": res.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": res.raw_firmware_bytes_leaked,
                }
                if args.summary
                else res.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            guard = res.wifi5ghz_nvs_ir_lanc_cec_guard
            sys.stdout.write(
                f"gate={verdict.gate_id} status={res.status} mode={res.verification_mode} "
                f"valid={res.valid} sku={guard['wifi_sku_code']} "
                f"band={guard['effective_wifi_band']} "
                f"p12_p13_ro={guard['p12_p13_ms_readonly_enforced']} "
                f"ctrl_hdmi={guard['effective_ctrl_for_hdmi']} "
                f"cec_keys={guard['cec_key_events_count']} "
                f"fx3_lanc={guard['fx3_physical_lanc_25mm_present']} "
                f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized} "
                f"raw_firmware_bytes_leaked={res.raw_firmware_bytes_leaked}\n"
            )
        return 0 if res.valid else 1

    if args.cmd == "verify-158-gates":
        report = evaluate_158gate_preflight(
            args.repo_root,
            force_clean_room=True if args.force_clean_room else None,
            dry_run_simulated=bool(args.dry_run_simulated),
        )
        if args.json:
            payload = (
                {
                    "schema_version": report.schema_version,
                    "status": report.status,
                    "verification_mode": report.verification_mode,
                    "summary": report.summary,
                    "g157_status": report.g157_result["status"],
                    "g158_status": report.g158_result["status"],
                }
                if args.summary
                else report.to_dict()
            )
            try:
                sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                import os as _os

                devnull = _os.open(_os.devnull, _os.O_WRONLY)
                _os.dup2(devnull, sys.stdout.fileno())
                _os.close(devnull)
        else:
            sys.stdout.write(
                f"status={report.status} mode={report.verification_mode} "
                f"verified={report.summary['verified_gates']}/158 "
                f"g157_to_g158_all_passed={report.g157_to_g158_all_passed} "
                f"all_158_gates_verified={report.all_158_gates_verified} "
                f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
                f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
                f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                f"usb_packets_transmitted={report.usb_packets_transmitted} "
                f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
            )
        ok = report.all_158_gates_verified if args.dry_run_simulated else report.offline_155_gates_verified
        return 0 if ok else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
