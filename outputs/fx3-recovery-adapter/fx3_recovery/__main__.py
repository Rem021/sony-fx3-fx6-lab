"""CLI exposes local-file operations only; no camera transport exists."""
import argparse
import json
from .engine import inspect_image, create_bundle, load_bundle, diagnose, rollback
from .fat import MAX_P1
from .files import read_file, encode, new_directory
from .capture import capture_local, verify_capture
from .worker import assemble_worker_windows
from .elflink import build_worker
from . import boot_worker as B
from .ab_bank_and_interrupted_ota_verifier import run_ab_bank_and_interrupted_ota_suite
from .bootrom_usb_and_emmc_bootpart_verifier import run_bootrom_usb_and_emmc_bootpart_suite
from .emmc_dump_forensic_verifier import (
    VALID_ROLES,
    report_to_dict,
    run_clean_room_forensic_suite,
    verify_emmc_dump_file,
)
from .factory_cal_ibis_defectpixel_and_nvs_verifier import run_factory_cal_ibis_defectpixel_and_nvs_suite
from .fdt_bootargs_and_kernel_verifier import run_fdt_bootargs_and_kernel_suite
from .firmware_updata_and_antirollback_guard import run_antirollback_and_byof_guard_suite
from .gpt_rpmb_and_rescue_bundle_verifier import run_gpt_rpmb_and_rescue_bundle_suite
from .init2_escape_and_watchdog_simulator import run_init2_escape_and_watchdog_suite
from .ramdisk_overlay_and_emmc_health_verifier import run_ramdisk_overlay_and_emmc_health_suite
from .realhw_22pillar_master_recovery_verifier import (
    run_pillar22_standalone_suite,
    verify_22pillar_recovery_suite,
)
from .realhw_24pillar_master_recovery_verifier import (
    run_pillar24_standalone_suite,
    verify_24pillar_recovery_suite,
)
from .realhw_26pillar_master_recovery_verifier import (
    run_pillar26_standalone_suite,
    verify_26pillar_recovery_suite,
)
from .realhw_27pillar_dcc1_pd_lut_vault_verifier import (
    run_pillar27_standalone_suite,
    verify_27pillar_recovery_suite,
)
from .realhw_28pillar_fan_pwm_shutter_lut_split_verifier import (
    run_pillar28_standalone_suite,
    verify_28pillar_recovery_suite,
)
from .realhw_29pillar_camset_slot1_simult_vault_verifier import (
    run_pillar29_standalone_suite,
    verify_29pillar_recovery_suite,
)
from .realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier import (
    run_pillar30_standalone_suite,
    verify_30pillar_recovery_suite,
    verify_proxy_coupled_and_hdmi_only_vault,
)
from .realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier import (
    run_pillar31_standalone_suite,
    verify_31pillar_recovery_suite,
    verify_filesettings_shotmark_and_tcregen_slot1_vault,
)
from .realhw_32pillar_ntscpal_pixelmap_vault_verifier import (
    run_pillar32_standalone_suite,
    verify_32pillar_recovery_suite,
    verify_ntscpal_persistence_and_pixelmap_cnflasha_vault,
)
from .realhw_33pillar_powersave_9cond_temp_vault_verifier import (
    run_pillar33_standalone_suite,
    verify_33pillar_recovery_suite,
    verify_powersave_9cond_and_autotemp_steadyshot_vault,
)
from .realhw_34pillar_zebra_fullformat_chord_vault_verifier import (
    run_pillar34_standalone_suite,
    verify_34pillar_recovery_suite,
    verify_zebra_persistence_and_fullformat_chord_slot1_vault,
)
from .realhw_35pillar_silent_autopixelmap_marker_vault_verifier import (
    run_pillar35_standalone_suite,
    verify_35pillar_recovery_suite,
    verify_silent_autopixelmap_and_marker_flexexp_vault,
)
from .realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier import (
    run_pillar36_standalone_suite,
    verify_36pillar_recovery_suite,
    verify_recover_imagedb_and_monitor_flip_af_vault,
)
from .realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier import (
    run_pillar37_standalone_suite,
    verify_37pillar_recovery_suite,
    verify_touch_recframe_hdmi_and_sunny_weather_vault,
)
from .realhw_38pillar_shoe_audio_wind_saveload_vault_verifier import (
    run_pillar38_standalone_suite,
    verify_38pillar_recovery_suite,
    verify_shoe_audio_wind_and_saveload_vault,
)
from .realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier import (
    run_pillar39_standalone_suite,
    verify_39pillar_recovery_suite,
    verify_framing_usbpower_lun_and_antiflicker_vault,
)
from .realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier import (
    run_pillar40_standalone_suite,
    verify_40pillar_recovery_suite,
    verify_lock_op_parts_audio_timing_and_exp_step_vault,
)
from .realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier import (
    run_pillar41_standalone_suite,
    verify_41pillar_recovery_suite,
    verify_display_quality_bt_rmt_and_mymenu_vault,
)
from .realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier import (
    run_pillar42_standalone_suite,
    verify_42pillar_recovery_suite,
    verify_diff_set_still_mv_custom_key_and_remain_shoot_vault,
)
from .realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier import (
    run_pillar43_standalone_suite,
    verify_43pillar_recovery_suite,
    verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault,
)
from .realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier import (
    run_pillar44_standalone_suite,
    verify_44pillar_recovery_suite,
    verify_apsc_s35_face_eye_af_and_version_vault,
)
from .realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier import (
    P265_ENV_CLEAN_ROOM_TEST,
    run_pillar45_standalone_suite,
    verify_45pillar_recovery_suite,
    verify_release_wo_card_lens_audio_meter_and_copyright_vault,
)
from .realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier import (
    P269_ENV_CLEAN_ROOM_TEST,
    run_pillar46_standalone_suite,
    verify_46pillar_recovery_suite,
    verify_file_settings_gamma_assist_and_tcub_vault,
)
from .realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier import (
    P272_ENV_CLEAN_ROOM_TEST,
    run_pillar47_standalone_suite,
    verify_47pillar_recovery_suite,
    verify_focus_mag_datetime_videolight_hdmires_and_vault,
)
from .realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier import (
    P277_ENV_CLEAN_ROOM_TEST,
    run_pillar48_standalone_suite,
    verify_48pillar_recovery_suite,
    verify_power_save_monitor_language_volume_delete_and_vault,
)
from .realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier import (
    P282_ENV_CLEAN_ROOM_TEST,
    run_pillar49_standalone_suite,
    verify_49pillar_recovery_suite,
    verify_usb_mode_hdmi_info_protect_network_reset_and_vault,
)
from .realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier import (
    P287_ENV_CLEAN_ROOM_TEST,
    run_pillar50_standalone_suite,
    verify_50pillar_recovery_suite,
    verify_pp_scinetone_creativelook_dro_wb_metering_and_vault,
)
from .realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier import (
    P292_ENV_CLEAN_ROOM_TEST,
    run_pillar51_standalone_suite,
    verify_51pillar_recovery_suite,
    verify_raw_heif_colorspace_shuttertype_nr_drive_and_vault,
)
from .realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier import (
    P296_ENV_CLEAN_ROOM_TEST,
    run_pillar52_standalone_suite,
    verify_52pillar_recovery_suite,
    verify_focus_area_zoom_lever_iso_minss_flash_and_vault,
)
from .realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier import (
    P300_ENV_CLEAN_ROOM_TEST,
    run_pillar53_standalone_suite,
    verify_53pillar_recovery_suite,
    verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault,
)
from .realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier import (
    P304_ENV_CLEAN_ROOM_TEST,
    run_pillar54_standalone_suite,
    verify_54pillar_recovery_suite,
    verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault,
)
from .realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier import (
    P308_ENV_CLEAN_ROOM_TEST,
    run_pillar55_standalone_suite,
    verify_55pillar_recovery_suite,
    verify_lens_comp_af_illuminator_folder_rating_and_vault,
)
from .realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier import (
    P314_ENV_CLEAN_ROOM_TEST,
    run_pillar56_standalone_suite,
    verify_56pillar_recovery_suite,
    verify_switch_vh_af_stdadj_tcub_copy_and_vault,
)
from .realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier import (
    P320_ENV_CLEAN_ROOM_TEST,
    run_pillar57_standalone_suite,
    verify_57pillar_recovery_suite,
    verify_touch_disp_zero_evf_flash_interval_pb_and_vault,
)
from .realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier import (
    P326_ENV_CLEAN_ROOM_TEST,
    run_pillar58_standalone_suite,
    verify_58pillar_recovery_suite,
    verify_dial_customize_mydial_fn12x2_liveview_lut_embed_and_vault,
)
from .realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier import (
    P332_ENV_CLEAN_ROOM_TEST,
    run_pillar59_standalone_suite,
    verify_59pillar_recovery_suite,
    verify_steadyshot_47focal_selftimer_zebra_streaming_and_vault,
)
from .realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier import (
    P336_ENV_CLEAN_ROOM_TEST,
    run_pillar60_standalone_suite,
    verify_60pillar_recovery_suite,
    verify_bright_mon_shotmark_usblan_bulb_and_vault,
)
from .realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier import (
    P340_ENV_CLEAN_ROOM_TEST,
    run_pillar61_standalone_suite,
    verify_61pillar_recovery_suite,
    verify_big6_framing_interval_tc_auth_fan_and_vault,
)
from .realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier import (
    P344_ENV_CLEAN_ROOM_TEST,
    run_pillar62_standalone_suite,
    verify_62pillar_recovery_suite,
    verify_rec_media_autoswitch_proxy_cloud_mymenu_and_vault,
)
from .realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier import (
    P348_ENV_CLEAN_ROOM_TEST,
    run_pillar63_standalone_suite,
    verify_63pillar_recovery_suite,
    verify_ftp_ftpes_customwb_afspeed_focusmap_marker_and_vault,
)
from .realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier import (
    P352_ENV_CLEAN_ROOM_TEST,
    run_pillar64_standalone_suite,
    verify_64pillar_recovery_suite,
    verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_and_vault,
)
from .realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier import (
    P355_ENV_CLEAN_ROOM_TEST,
    run_pillar65_standalone_suite,
    verify_65pillar_recovery_suite,
    verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_and_vault,
)
from .realhw_adjustcontrol_streaming_backup_client import run_adjustcontrol_streaming_backup_suite
from .realhw_airgap_sd_bundle_manifest_verifier import run_airgap_sd_bundle_manifest_suite
from .realhw_bootrom_el3_and_ufu_stock_reflash_verifier import run_realhw_bootrom_el3_and_ufu_stock_reflash_suite
from .realhw_ext2_installer_and_p1_rescue_verifier import run_realhw_ext2_installer_and_p1_rescue_suite
from .realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier import run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite
from .realhw_service_usb_session_and_libjit_elf_hardener import run_realhw_service_usb_and_libjit_hardener_suite
from .realhw_uart_460800_post_triage_and_isp_guard import run_realhw_uart_460800_post_triage_and_isp_suite
from .realhw_wbi_powerloss_and_100cycle_transition_verifier import run_wbi_powerloss_and_100cycle_suite
from .recovery_master_suite_and_uart_decoder import run_recovery_master_suite
from .rp2040_multiport_fixture_selftest import run_rp2040_multiport_fixture_selftest
from .secureboot_chain_and_partition_align_verifier import run_secureboot_chain_and_partition_align_suite
from .squashfs_and_hibdrv_wbi_verifier import run_squashfs_and_hibdrv_wbi_suite
from .tier0_backup_parity_and_manifest_guard import run_tier0_backup_parity_suite
from .unbrick_ladder_and_capsule_verifier import run_unbrick_ladder_and_capsule_suite


def main():
    p = argparse.ArgumentParser(description='FX3 7.02 recovery adaptation v0.5 — local files only')
    sub = p.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect', help='inspect a local logical/decrypted P1 image')
    inspect.add_argument('--input', required=True);inspect.add_argument('--out', required=True)
    build = sub.add_parser('build', help='build a local reference-profile candidate and preserve full original')
    build.add_argument('--input', required=True);build.add_argument('--out', required=True)
    build.add_argument('--scope', choices=['reference', 'unverified-snapshot'], default='reference')
    build.add_argument('--body-tag', help='opaque64hex operator tag; never a serial; not device-verified')
    verify = sub.add_parser('verify', help='verify all image hashes and exact transformation')
    verify.add_argument('--bundle', required=True)
    state = sub.add_parser('diagnose', help='classify original/candidate/mixed/unknown local image')
    state.add_argument('--bundle', required=True);state.add_argument('--input', required=True)
    restore = sub.add_parser('rollback', help='create an exact local backup reconstruction in a new directory')
    restore.add_argument('--bundle', required=True);restore.add_argument('--input', required=True);restore.add_argument('--out', required=True)
    capture = sub.add_parser('capture-local', help='bounded capture of an existing full local P1 file; no camera provider')
    capture.add_argument('--input', required=True);capture.add_argument('--out', required=True)
    capture.add_argument('--sha256', required=True, help='external expected whole-file SHA-256')
    capture.add_argument('--body-tag', required=True, help='opaque64hex local grouping tag; never camera attestation')
    captured = sub.add_parser('verify-capture', help='verify complete local capture evidence with an external digest')
    captured.add_argument('--capture', required=True);captured.add_argument('--sha256', required=True)
    worker = sub.add_parser('assemble-worker', help='decode three saved worker windows; never loads or executes native code')
    worker.add_argument('--windows',nargs=3,required=True)
    worker.add_argument('--returns',nargs=3,type=int,required=True,help='separately recorded producer return codes; caller supplied, not attested')
    worker.add_argument('--out',required=True);worker.add_argument('--body-tag',required=True)
    linker = sub.add_parser('build-worker', help='compile/link our pinned sources locally; never executes the ELF or accesses a camera')
    linker.add_argument('--out',required=True)
    bootreq = sub.add_parser('boot-request', help='create a local boot0/boot1 request file; no upload or execution')
    bootreq.add_argument('--capture-id',required=True);bootreq.add_argument('--target',choices=['boot0','boot1'],required=True)
    bootreq.add_argument('--window',type=int,required=True);bootreq.add_argument('--expected-total',type=int,default=0)
    bootreq.add_argument('--out',required=True)
    bootbuild = sub.add_parser('build-boot-worker', help='compile/link boot reader candidate locally; never launches it')
    bootbuild.add_argument('--out',required=True)
    bootassemble = sub.add_parser('assemble-boot-worker', help='verify/assemble one to four saved boot windows locally')
    bootassemble.add_argument('--windows',nargs='+',required=True)
    bootassemble.add_argument('--returns',nargs='+',type=int,required=True)
    bootassemble.add_argument('--out',required=True);bootassemble.add_argument('--body-tag',required=True)
    forensic = sub.add_parser('verify-emmc-forensics', help='offline O_RDONLY Tier-4 eMMC dump & EXT_CSD forensic verifier')
    forensic.add_argument('--input', help='path to regular eMMC dump file opened strictly O_RDONLY')
    forensic.add_argument('--role', choices=list(VALID_ROLES), default='generic')
    forensic.add_argument('--expected-size', type=int, default=None)
    forensic.add_argument('--expect-encrypted', action='store_true')
    forensic.add_argument('--ext-csd', dest='ext_csd', help='optional 512B EXT_CSD register dump path')
    forensic.add_argument('--manifest', help='optional JSON manifest path to audit against boot-chain firewall')
    forensic.add_argument('--clean-room', action='store_true', help='run clean-room synthetic Tier-4 forensic suite')
    forensic.add_argument('--out', help='optional exclusive new output directory for forensic-report.json')
    ladder = sub.add_parser('verify-unbrick-ladder', help='Phase 47 Tier-0..Tier-4 unbrick escalation ladder & p1 VFAT capsule verifier')
    ladder.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    ladder.add_argument('--json', action='store_true', help='emit full structured JSON report')
    ladder.add_argument('--out', help='optional exclusive new output directory for unbrick-ladder-report.json')
    fixture = sub.add_parser('verify-rp2040-fixture', help='Phase 59 camera-disconnected RP2040-Zero -DOPEN_DRAIN 1.8V Multi-Port bench fixture self-test')
    fixture.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    fixture.add_argument('--json', action='store_true', help='emit full structured JSON report')
    fixture.add_argument('--out', help='optional exclusive new output directory for rp2040-fixture-report.json')
    init2esc = sub.add_parser('verify-init2-escape', help='Phase 66 init2 SD-card sentinel escape shell, CXD90057 WDT & p1 FAT12/FAT16 verifier')
    init2esc.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    init2esc.add_argument('--json', action='store_true', help='emit full structured JSON report')
    init2esc.add_argument('--out', help='optional exclusive new output directory for init2-escape-report.json')
    tier0bak = sub.add_parser('verify-tier0-backup', help='Phase 72 Tier-0 11-partition GF(256) parity healer & cross-body anti-transplant verifier')
    tier0bak.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    tier0bak.add_argument('--json', action='store_true', help='emit full structured JSON report')
    tier0bak.add_argument('--out', help='optional exclusive new output directory for tier0-backup-report.json')
    antirollback = sub.add_parser('verify-antirollback-guard', help='Phase 79 CXD90057 OTP/RPMB anti-rollback firewall, BYOF compatibility matrix & EXT_CSD WP guard')
    antirollback.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    antirollback.add_argument('--json', action='store_true', help='emit full structured JSON report')
    antirollback.add_argument('--out', help='optional exclusive new output directory for antirollback-guard-report.json')
    master = sub.add_parser('verify-all-recovery', help='Phase 86 unified 7-pillar fx3_recovery master readiness audit & passive 1.8V RX-only UART boot-stage decoder')
    master.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    master.add_argument('--out', help='optional exclusive new output directory for recovery-master-report.json')
    master.add_argument('--with-phase94', action='store_true', help='also run Phase 94 Pillar 8 GPT/RPMB/SD-rescue verifier')
    master.add_argument('--with-phase101', action='store_true', help='also run Phase 101 Pillar 9 init2 cpio firewall, EXT_CSD health & tmpfs isolation verifier')
    master.add_argument('--with-phase106', action='store_true', help='also run Phase 106 Pillar 10 FDT /chosen/bootargs firewall & ARM64 kernel verifier')
    master.add_argument('--with-phase113', action='store_true', help='also run Phase 113 Pillar 11 CXD90057 Dual-Bank A/B & Interrupted BODYDATA.DAT/USB-OTA forensic triage verifier')
    master.add_argument('--with-phase119', action='store_true', help='also run Phase 119 Pillar 12 SquashFS 4.0 hsqs & Sony Warp-Boot hibdrv WBI2 triage verifier')
    master.add_argument('--with-phase124', action='store_true', help='also run Phase 124 Pillar 13 CXD90057 Mask-BootROM USB cold-plug & JEDEC eMMC BOOT0/BOOT1 triage verifier')
    master.add_argument('--with-phase126', action='store_true', help='also run Phase 126 Pillar 14 factory calibration nvs/cnflasha/adj, IMX510 defect-pixel & 5-axis IBIS verifier')
    master.add_argument('--with-phase134', action='store_true', help='also run Phase 134 Pillar 15 CXD90057 secure-boot chain envelope & nflasha1..20 4KiB/512KiB partition-align verifier')
    master.add_argument('--with-phase138', action='store_true', help='also run Phase 138 Pillar 16 reversible ext2 /dev/nflasha15 atomic Stage-B installer, hash-rollback & p1/p3 mutual-exclusion rescue verifier')
    master.add_argument('--with-phase139', action='store_true', help='also run Phase 139 Pillar 17 host-side AdjustControl (0x40) streaming cold-backup client, p6 25 MiB sliding-window pull & Fake-IOKit verifier')
    master.add_argument('--with-phase144', action='store_true', help='also run Phase 144 Pillar 18 MSC->SERVICE exclusive session, op=0xFF zero-mount RAM canary & Stage-288 s4 hardened ARM64 libJit.so verifier')
    master.add_argument('--with-phase151', action='store_true', help='also run Phase 151 Pillar 19 /dev/pnflasha* raw ISP + /dev/cnflasha* logical + /dev/mtd*ro SPI NOR dual-layer Tier-0 vault verifier')
    master.add_argument('--with-phase155', action='store_true', help='also run Phase 155 Pillar 20 real-hardware CXD90057 1.8V ttyAMA0 460800n8 boot-stage triage, multi-USB firewall & last-resort ISP checklist verifier (20/20 milestone)')
    master.add_argument('--with-phase160', action='store_true', help='also run Phase 160 Pillar 21 real-hardware 5-tier unbrickable recovery escalation, CXD90057 EL3 (0xfe020000) cold-boot guard & official BODYDATA.DAT (\\x89UFU) stock-reflash verifier (21/21 milestone)')
    master.add_argument('--with-phase166', action='store_true', help='also run Phase 166 Pillar 22 dual-media Tier-0 cold-backup bit-rot scrub & GF(256) pre-restore verifier (22/22 milestone)')
    gpt_rpmb = sub.add_parser('verify-gpt-rpmb-bundle', help='Phase 94 CXD90057 GPT CRC32 healer, RPMB replay guard & offline SD-rescue bundle verifier')
    gpt_rpmb.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    gpt_rpmb.add_argument('--json', action='store_true', help='emit full structured JSON report')
    gpt_rpmb.add_argument('--out', help='optional exclusive new output directory for gpt-rpmb-bundle-report.json')
    ramdisk_emmc = sub.add_parser('verify-ramdisk-emmc-health', help='Phase 101 init2 newc cpio firewall, JEDEC EXT_CSD [267..269] health auditor & tmpfs isolation verifier')
    ramdisk_emmc.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    ramdisk_emmc.add_argument('--json', action='store_true', help='emit full structured JSON report')
    ramdisk_emmc.add_argument('--out', help='optional exclusive new output directory for ramdisk-emmc-health-report.json')
    fdt_kern = sub.add_parser('verify-fdt-bootargs', help='Phase 106 FDT 0xd00dfeed /chosen/bootargs firewall & ARM64 kernel Image verifier')
    fdt_kern.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    fdt_kern.add_argument('--json', action='store_true', help='emit full structured JSON report')
    fdt_kern.add_argument('--out', help='optional exclusive new output directory for fdt-bootargs-kernel-report.json')
    ab_ota = sub.add_parser('verify-ab-bank-triage', help='Phase 113 CXD90057 Dual-Bank A/B consistency & interrupted BODYDATA.DAT/USB-OTA forensic triage verifier')
    ab_ota.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    ab_ota.add_argument('--json', action='store_true', help='emit full structured JSON report')
    ab_ota.add_argument('--out', help='optional exclusive new output directory for ab-bank-ota-triage-report.json')
    sq_wbi = sub.add_parser('verify-squashfs-wbi-triage', help='Phase 119 SquashFS 4.0 superblock/table-bounds & Sony Warp-Boot hibdrv WBI2 stale-resume/noresume triage verifier')
    sq_wbi.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    sq_wbi.add_argument('--json', action='store_true', help='emit full structured JSON report')
    sq_wbi.add_argument('--out', help='optional exclusive new output directory for squashfs-wbi-triage-report.json')
    br_bp = sub.add_parser('verify-bootrom-bootpart', help='Phase 124 CXD90057 Mask-BootROM USB cold-plug RAM-load sandbox & JEDEC eMMC BOOT0/BOOT1 EXT_CSD verifier')
    br_bp.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    br_bp.add_argument('--json', action='store_true', help='emit full structured JSON report')
    br_bp.add_argument('--out', help='optional exclusive new output directory for bootrom-bootpart-report.json')
    fc_cal = sub.add_parser('verify-factory-cal-guard', help='Phase 126 per-body nvs/cnflasha/adj factory calibration parity firewall, IMX510 defect-pixel/dual-ISO & 5-axis IBIS/IMU verifier')
    fc_cal.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    fc_cal.add_argument('--json', action='store_true', help='emit full structured JSON report')
    fc_cal.add_argument('--out', help='optional exclusive new output directory for factory-cal-guard-report.json')
    sb_pa = sub.add_parser('verify-secureboot-partalign', help='Phase 134 CXD90057 IPL/BLoader/BL31/Kernel secure-boot envelope & nflasha1..20 4KiB/512KiB partition-align bleed firewall verifier')
    sb_pa.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    sb_pa.add_argument('--json', action='store_true', help='emit full structured JSON report')
    sb_pa.add_argument('--out', help='optional exclusive new output directory for secureboot-partalign-report.json')
    rh_ext2 = sub.add_parser('verify-realhw-ext2-installer', help='Phase 138 reversible ext2 /dev/nflasha15 atomic Stage-B installer, hash-rollback & p1/p3 mutual-exclusion rescue verifier')
    rh_ext2.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    rh_ext2.add_argument('--json', action='store_true', help='emit full structured JSON report')
    rh_ext2.add_argument('--out', help='optional exclusive new output directory for realhw-ext2-installer-p1-rescue-report.json')
    adj_bak = sub.add_parser('verify-adjustcontrol-backup-client', help='Phase 139 host-side AdjustControl (0x40) streaming cold-backup client, p6 25 MiB sliding-window pull & Fake-IOKit verifier')
    adj_bak.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    adj_bak.add_argument('--json', action='store_true', help='emit full structured JSON report')
    adj_bak.add_argument('--out', help='optional exclusive new output directory for adjustcontrol-streaming-backup-report.json')
    svc_jit = sub.add_parser('verify-service-usb-libjit', help='Phase 144 Pillar 18 MSC->SERVICE exclusive session, op=0xFF zero-mount RAM canary & Stage-288 s4 hardened ARM64 libJit.so verifier')
    svc_jit.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    svc_jit.add_argument('--json', action='store_true', help='emit full structured JSON report')
    svc_jit.add_argument('--out', help='optional exclusive new output directory for service-usb-libjit-report.json')
    t0_vault = sub.add_parser('verify-tier0-dual-layer-vault', help='Phase 151 Pillar 19 /dev/pnflasha* raw ISP + /dev/cnflasha* logical + /dev/mtd*ro SPI NOR + Sector 0 30-partition Tier-0 vault verifier')
    t0_vault.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    t0_vault.add_argument('--json', action='store_true', help='emit full structured JSON report')
    t0_vault.add_argument('--out', help='optional exclusive new output directory for tier0-dual-layer-vault-report.json')
    u460800 = sub.add_parser('verify-uart-460800-isp-triage', help='Phase 155 Pillar 20 real-hardware CXD90057 1.8V ttyAMA0 460800n8 boot-stage triage, multi-USB firewall & last-resort ISP checklist verifier')
    u460800.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    u460800.add_argument('--json', action='store_true', help='emit full structured JSON report')
    u460800.add_argument('--out', help='optional exclusive new output directory for uart-460800-isp-triage-report.json')
    p160_5tier = sub.add_parser('verify-realhw-5tier-el3-ufu', help='Phase 160 Pillar 21 real-hardware 5-tier unbrickable recovery escalation, CXD90057 EL3 (0xfe020000) cold-boot guard & official BODYDATA.DAT (\\x89UFU) stock-reflash verifier')
    p160_5tier.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p160_5tier.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p160_5tier.add_argument('--out', help='optional exclusive new output directory for realhw-5tier-el3-ufu-report.json')
    p166_master = sub.add_parser('verify-22pillar-recovery', help='Phase 166 Pillar 22 (22/22) unified real-hardware recovery master verifier & dual-media Tier-0 GF(256) bit-rot/pre-restore rehearsal engine')
    p166_master.add_argument('--clean-room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p166_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p166_master.add_argument('--out', help='optional exclusive new output directory for 22pillar-recovery-master-report.json')
    p176_wbi = sub.add_parser('verify-wbi-powerloss-recovery', help='Phase 176 Pillar 23 p5:/wbi (WBI2/hibdrv.ko) contamination firewall, battery-pull recovery & 100-cycle H0==H3 verifier')
    p176_wbi.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p176_wbi.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p176_wbi.add_argument('--out', help='optional exclusive new output directory for wbi-powerloss-100cycle-report.json')
    p180_slot1 = sub.add_parser('verify-slot1-ufu-reflash-readiness', help='Phase 180 Pillar 24 standalone Slot-1 BODYDATA.DAT (>=2.04 floor) stock-reflash readiness & WPA2/WPA3 HDMI-BRAW/LUT rollback hygiene verifier')
    p180_slot1.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p180_slot1.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p180_slot1.add_argument('--out', help='optional exclusive new output directory for pillar24-slot1-ufu-hygiene-report.json')
    p180_master = sub.add_parser('verify-24pillar-recovery', help='Phase 180 unified 24/24 real-hardware recovery master aggregator (Pillars 1..22 + Pillar 23 + Pillar 24)')
    p180_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p180_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p180_master.add_argument('--out', help='optional exclusive new output directory for 24pillar-recovery-master-report.json')
    p184_sd = sub.add_parser('verify-airgap-sd-bundle', help='Phase 184 Pillar 25 real-hardware air-gapped bench SD/CFexpress BYOF bundle manifest (FX3BNDL1), dual-copy FX3RCPT1 cross-binding & ExFAT/AppleDouble/BODYDATA.DAT guard')
    p184_sd.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p184_sd.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p184_sd.add_argument('--out', help='optional exclusive new output directory for pillar25-airgap-sd-bundle-report.json')
    p190_fw = sub.add_parser('verify-fx3a-branch-recovery-firewall', help='Phase 190 Pillar 26 ILME-FX3 vs ILME-FX3A cross-branch recovery & CAMSET firewall + XLR-H1 4ch/24bit audio hygiene verifier')
    p190_fw.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p190_fw.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p190_fw.add_argument('--out', help='optional exclusive new output directory for pillar26-fx3a-branch-firewall-report.json')
    p190_master = sub.add_parser('verify-26pillar-recovery', help='Phase 190 unified 26/26 real-hardware recovery master aggregator (Pillars 1..24 + Pillar 25 + Pillar 26)')
    p190_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p190_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p190_master.add_argument('--out', help='optional exclusive new output directory for 26pillar-recovery-master-report.json')
    p195_p27 = sub.add_parser('verify-dcc1-pd-lut-vault', help='Phase 195 Pillar 27 NP-FZ100 & DC-C1 (>=65W/5A) brownout interlock + dual-media .cube LUT p2:/setting vault verifier')
    p195_p27.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p195_p27.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p195_p27.add_argument('--out', help='optional exclusive new output directory for pillar27-dcc1-pd-lut-vault-report.json')
    p195_master = sub.add_parser('verify-27pillar-recovery', help='Phase 195 unified 27/27 real-hardware recovery master aggregator (Pillars 1..26 + Pillar 27)')
    p195_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p195_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p195_master.add_argument('--out', help='optional exclusive new output directory for 27pillar-recovery-master-report.json')
    p198_p28 = sub.add_parser('verify-fan-pwm-lut-split-vault', help='Phase 198 Pillar 28 ILME-FX3 4-mode Fan PWM pre-backup Auto interlock + 6.01 vs 7.02 LUT split & Shutter Speed/Angle vault verifier')
    p198_p28.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p198_p28.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p198_p28.add_argument('--out', help='optional exclusive new output directory for pillar28-fan-pwm-lut-split-vault-report.json')
    p198_master = sub.add_parser('verify-28pillar-recovery', help='Phase 198 unified 28/28 real-hardware recovery master aggregator (Pillars 1..27 + Pillar 28)')
    p198_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p198_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p198_master.add_argument('--out', help='optional exclusive new output directory for 28pillar-recovery-master-report.json')
    p208_p29 = sub.add_parser('verify-camset-simult-vault', help='Phase 208 Pillar 29 Slot-1 CAMSET dual-media vault, BIG6 zero e-ND guard, Simult + Auto Switch Off, VMC-BNCM1 body TC IN & De-Squeeze 1.65x verifier')
    p208_p29.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p208_p29.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p208_p29.add_argument('--out', help='optional exclusive new output directory for pillar29-camset-simult-vault-report.json')
    p208_master = sub.add_parser('verify-29pillar-recovery', help='Phase 208 unified 29/29 real-hardware recovery master aggregator (Pillars 1..28 + Pillar 29)')
    p208_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p208_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p208_master.add_argument('--out', help='optional exclusive new output directory for 29pillar-recovery-master-report.json')
    p212_p30 = sub.add_parser('verify-proxy-coupled-hdmi-vault', help='Phase 212 Pillar 30 Px atomic main+proxy coupled vault (Slot 1/2), Off(HDMI Only) zero-card interlock, Log/PPLUT 1080p downshift & FocusMag x BrightMon verifier')
    p212_p30.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p212_p30.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p212_p30.add_argument('--out', help='optional exclusive new output directory for pillar30-proxy-coupled-hdmi-vault-report.json')
    p212_master = sub.add_parser('verify-30pillar-recovery', help='Phase 212 unified 30/30 milestone real-hardware recovery master aggregator (Pillars 1..29 + Pillar 30)')
    p212_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p212_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p212_master.add_argument('--out', help='optional exclusive new output directory for 30pillar-recovery-master-report.json')
    p215_p31 = sub.add_parser('verify-filesettings-shotmark-tcregen-vault', help='Phase 215 Pillar 31 File Settings SDHC/37-char vault, Shot Mark1/2 *M01.XML sidecars, TC Regenerate Slot-1 continuity & EXT-LK drop guard')
    p215_p31.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p215_p31.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p215_p31.add_argument('--out', help='optional exclusive new output directory for pillar31-filesettings-shotmark-tcregen-vault-report.json')
    p215_master = sub.add_parser('verify-31pillar-recovery', help='Phase 215 unified 31/31 real-hardware recovery master aggregator (Pillars 1..30 + Pillar 31)')
    p215_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p215_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p215_master.add_argument('--out', help='optional exclusive new output directory for 31pillar-recovery-master-report.json')
    p220_p32 = sub.add_parser('verify-ntscpal-pixelmap-vault', help='Phase 220 Pillar 32 NTSC/PAL reset asymmetry & dual-slot media DB separation, Gamma Display Assist vs Display LUT parity & Pixel Mapping auto-restart cnflasha read-only vault verifier')
    p220_p32.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p220_p32.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p220_p32.add_argument('--out', help='optional exclusive new output directory for pillar32-ntscpal-pixelmap-vault-report.json')
    p220_master = sub.add_parser('verify-32pillar-recovery', help='Phase 220 unified 32/32 real-hardware recovery master aggregator (Pillars 1..31 + Pillar 32)')
    p220_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p220_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p220_master.add_argument('--out', help='optional exclusive new output directory for 32pillar-recovery-master-report.json')
    p225_p33 = sub.add_parser('verify-powersave-9cond-temp-vault', help='Phase 225 Pillar 33 Power Save Start Time 9-condition air-gap backup interlock, Auto Power OFF Temp. + Fan Control cool-down & SteadyShot Active / Clear Image Zoom vault verifier')
    p225_p33.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p225_p33.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p225_p33.add_argument('--out', help='optional exclusive new output directory for pillar33-powersave-9cond-temp-vault-report.json')
    p225_master = sub.add_parser('verify-33pillar-recovery', help='Phase 225 unified 33/33 real-hardware recovery master aggregator (Pillars 1..32 + Pillar 33)')
    p225_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p225_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p225_master.add_argument('--out', help='optional exclusive new output directory for 33pillar-recovery-master-report.json')
    p229_p34 = sub.add_parser('verify-zebra-fullformat-chord-vault', help='Phase 229 Pillar 34 Slot-1 Tier-0 Full Format / MENU+Delete 2s chord firewall, Zebra reset survival, HDMI assist isolation & S&Q state recovery verifier')
    p229_p34.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p229_p34.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p229_p34.add_argument('--out', help='optional exclusive new output directory for pillar34-zebra-fullformat-chord-vault-report.json')
    p229_master = sub.add_parser('verify-34pillar-recovery', help='Phase 229 unified 34/34 real-hardware recovery master aggregator (Pillars 1..33 + Pillar 34)')
    p229_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p229_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p229_master.add_argument('--out', help='optional exclusive new output directory for 34pillar-recovery-master-report.json')
    p231_p35 = sub.add_parser('verify-silent-autopixelmap-marker-vault', help='Phase 231 Pillar 35 Silent Mode Auto Pixel Mapping bench shutdown firewall, Shutter When Pwr OFF absence & Marker / Flexible Exp. Mode reset-split vault verifier')
    p231_p35.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p231_p35.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p231_p35.add_argument('--out', help='optional exclusive new output directory for pillar35-silent-autopixelmap-marker-vault-report.json')
    p231_master = sub.add_parser('verify-35pillar-recovery', help='Phase 231 unified 35/35 milestone real-hardware recovery master aggregator (Pillars 1..34 + Pillar 35)')
    p231_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p231_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p231_master.add_argument('--out', help='optional exclusive new output directory for 35pillar-recovery-master-report.json')
    p234_p36 = sub.add_parser('verify-recover-imagedb-monitor-flip-vault', help='Phase 234 Pillar 36 Recover Image DB depleted-battery & Slot-1 Tier-0 vault mutation firewall + Monitor Flip Direction reset survival / playback non-inversion & AF/Interval vault verifier')
    p234_p36.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p234_p36.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p234_p36.add_argument('--out', help='optional exclusive new output directory for pillar36-recover-imagedb-monitor-flip-vault-report.json')
    p234_master = sub.add_parser('verify-36pillar-recovery', help='Phase 234 unified 36/36 real-hardware recovery master aggregator (Pillars 1..35 + Pillar 36)')
    p234_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p234_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p234_master.add_argument('--out', help='optional exclusive new output directory for 36pillar-recovery-master-report.json')
    p238_p37 = sub.add_parser('verify-touch-recframe-hdmi-sunny-vault', help='Phase 238 Pillar 37 Touch Operation 4-item reset survival & bench tap firewall, Emphasized REC / Grid Line HDMI clean-feed clamp & Sunny Weather indoor battery vault verifier')
    p238_p37.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p238_p37.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p238_p37.add_argument('--out', help='optional exclusive new output directory for pillar37-touch-recframe-hdmi-sunny-vault-report.json')
    p238_master = sub.add_parser('verify-37pillar-recovery', help='Phase 238 unified 37/37 real-hardware recovery master aggregator (Pillars 1..36 + Pillar 37)')
    p238_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p238_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p238_master.add_argument('--out', help='optional exclusive new output directory for 37pillar-recovery-master-report.json')
    p240_p38 = sub.add_parser('verify-shoe-audio-wind-saveload-vault', help='Phase 240 Pillar 38 Shoe Audio Set. 48kHz/24bit 4ch recovery & 3 lockouts + Wind Noise Reduct. built-in-mic-only guard + Save/Load Settings CAMSET/C3 Portal exclusions & Slot-1 Tier-0 vault write lock verifier')
    p240_p38.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p240_p38.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p240_p38.add_argument('--out', help='optional exclusive new output directory for pillar38-shoe-audio-wind-saveload-vault-report.json')
    p240_master = sub.add_parser('verify-38pillar-recovery', help='Phase 240 unified 38/38 real-hardware recovery master aggregator (Pillars 1..37 + Pillar 38)')
    p240_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p240_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p240_master.add_argument('--out', help='optional exclusive new output directory for 38pillar-recovery-master-report.json')
    p243_p39 = sub.add_parser('verify-framing-usbpower-lun-antiflicker-vault', help='Phase 243 Pillar 39 Framing Settings asymmetric Full/Crop recovery & HDMI RAW crop guard + Anti-flicker Shoot. mechanical-still-only / no-Var. Shutter lock + USB Power Supply mandatory NP-FZ100 / USB Type-C exclusivity & USB LUN Multi/Single Setup persistence verifier')
    p243_p39.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p243_p39.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p243_p39.add_argument('--out', help='optional exclusive new output directory for pillar39-framing-usbpower-lun-antiflicker-vault-report.json')
    p243_master = sub.add_parser('verify-39pillar-recovery', help='Phase 243 unified 39/39 real-hardware recovery master aggregator (Pillars 1..38 + Pillar 39)')
    p243_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p243_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p243_master.add_argument('--out', help='optional exclusive new output directory for 39pillar-recovery-master-report.json')
    p245_p40 = sub.add_parser('verify-lock-op-parts-audio-timing-exp-step-vault', help='Phase 245 Milestone Pillar 40 Lock Operation Parts survival, Fn hold, MENU + Fn 5s full-body chord vs MENU + Delete 2s guard & My Dial override + Audio Out Timing / Audio signals / Exposure step vs Shutter Angle constant-table verifier')
    p245_p40.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p245_p40.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p245_p40.add_argument('--out', help='optional exclusive new output directory for pillar40-lock-op-parts-audio-timing-exp-step-vault-report.json')
    p245_master = sub.add_parser('verify-40pillar-recovery', help='Phase 245 Milestone unified 40/40 real-hardware recovery master aggregator (Pillars 1..39 + Pillar 40)')
    p245_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p245_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p245_master.add_argument('--out', help='optional exclusive new output directory for 40pillar-recovery-master-report.json')
    p247_p41 = sub.add_parser('verify-display-quality-bt-rmt-mymenu-vault', help='Phase 247 Pillar 41 Display Quality Standard/High battery bench guard & Bluetooth Rmt Ctrl IR lockout / 3-way Reset Network Set. split + My Menu Setting 6-operation persistence & O_RDONLY CAMSET01.DAT round-trip verifier')
    p247_p41.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p247_p41.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p247_p41.add_argument('--out', help='optional exclusive new output directory for pillar41-display-quality-bt-rmt-mymenu-vault-report.json')
    p247_master = sub.add_parser('verify-41pillar-recovery', help='Phase 247 unified 41/41 real-hardware recovery master aggregator (Pillars 1..40 + Pillar 41)')
    p247_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p247_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p247_master.add_argument('--out', help='optional exclusive new output directory for 41pillar-recovery-master-report.json')
    p251_p42 = sub.add_parser('verify-diff-set-still-mv-custom-key-remain-shoot-vault', help='Phase 251 Pillar 42 Different Set for Still/Mv 8-item asymmetric transitions & Shutter Angle split + Custom Key/Dial Set. ISO/EI persistence & Remain Shoot Display EVF-less vault verifier')
    p251_p42.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p251_p42.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p251_p42.add_argument('--out', help='optional exclusive new output directory for pillar42-diff-set-still-mv-custom-key-remain-shoot-vault-report.json')
    p251_master = sub.add_parser('verify-42pillar-recovery', help='Phase 251 unified 42/42 real-hardware recovery master aggregator (Pillars 1..41 + Pillar 42)')
    p251_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p251_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p251_master.add_argument('--out', help='optional exclusive new output directory for 42pillar-recovery-master-report.json')
    p255_p43 = sub.add_parser('verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault', help='Phase 255 Pillar 43 Auto Slow Shutter 6-condition lockout & Shutter Angle disjointness + HDMI Output Settings REC Control <- Time Code Output gate & 4ch Audio Output + Breathing Comp. vault verifier')
    p255_p43.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p255_p43.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p255_p43.add_argument('--out', help='optional exclusive new output directory for pillar43-auto-slow-shutter-hdmi-reccontrol-breathing-vault-report.json')
    p255_master = sub.add_parser('verify-43pillar-recovery', help='Phase 255 unified 43/43 real-hardware recovery master aggregator (Pillars 1..42 + Pillar 43)')
    p255_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p255_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p255_master.add_argument('--out', help='optional exclusive new output directory for 43pillar-recovery-master-report.json')
    p260_p44 = sub.add_parser('verify-apsc-s35-face-eye-af-version-vault', help='Phase 260 (260th Milestone) Pillar 44 APS-C S35 Shooting 12.1MP 4K movie lockout, Face/Eye AF Right/Left Eye & Clean-HDMI isolation + Version read-only vs hard-blocked BODYDATA.DAT vault verifier')
    p260_p44.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p260_p44.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p260_p44.add_argument('--out', help='optional exclusive new output directory for pillar44-apsc-s35-face-eye-af-version-vault-report.json')
    p260_master = sub.add_parser('verify-44pillar-recovery', help='Phase 260 (260th Milestone) unified 44/44 real-hardware recovery master aggregator (Pillars 1..43 + Pillar 44)')
    p260_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p260_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p260_master.add_argument('--out', help='optional exclusive new output directory for 44pillar-recovery-master-report.json')
    p265_p45 = sub.add_parser('verify-release-wo-card-lens-audio-meter-copyright-vault', help='Phase 265 (Grand Milestone 45/45) Pillar 45 Release w/o Card & Release w/o Lens, Ver. 7.02 5-item Audio Recording vs DISP audio meter, and Copyright Info 46-char EXIF hygiene vault verifier')
    p265_p45.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p265_p45.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p265_p45.add_argument('--out', help='optional exclusive new output directory for pillar45-release-wo-card-lens-audio-meter-copyright-vault-report.json')
    p265_master = sub.add_parser('verify-45pillar-recovery', help='Phase 265 (Grand Milestone 45/45) unified 45/45 real-hardware recovery master aggregator (Pillars 1..44 + Pillar 45)')
    p265_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p265_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p265_master.add_argument('--out', help='optional exclusive new output directory for 45pillar-recovery-master-report.json')
    p269_p46 = sub.add_parser('verify-file-settings-gamma-assist-tcub-vault', help='Phase 269 Pillar 46 Movie File Settings Cam ID + Reel# & 37-char Title Name vs Still File/Folder DSC & Slot-1 vault, Gamma Display Assist Log Shooting lockout vs Display LUT/Select LUT, Auto Review Off default & 6-item TC/UB persistence verifier')
    p269_p46.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p269_p46.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p269_p46.add_argument('--out', help='optional exclusive new output directory for pillar46-file-settings-gamma-assist-tcub-vault-report.json')
    p269_master = sub.add_parser('verify-46pillar-recovery', help='Phase 269 unified 46/46 real-hardware recovery master aggregator (Pillars 1..45 + Pillar 46)')
    p269_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p269_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p269_master.add_argument('--out', help='optional exclusive new output directory for 46pillar-recovery-master-report.json')
    p272_p47 = sub.add_parser('verify-focus-mag-datetime-videolight-hdmires-vault', help='Phase 272 Pillar 47 Focus Assistant Auto Magnifier in MF, C5, dual Initial Focus Mag. x1.0, Peaking clean-HDMI & Still AF Illuminator + Area/Date/Time Setting zero-RF, Video Light 5V <= 900mA & HDMI Resolution Log 1080p vault verifier')
    p272_p47.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p272_p47.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p272_p47.add_argument('--out', help='optional exclusive new output directory for pillar47-focus-mag-datetime-videolight-hdmires-vault-report.json')
    p272_master = sub.add_parser('verify-47pillar-recovery', help='Phase 272 unified 47/47 real-hardware recovery master aggregator (Pillars 1..46 + Pillar 47)')
    p272_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p272_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p272_master.add_argument('--out', help='optional exclusive new output directory for 47pillar-recovery-master-report.json')
    p277_p48 = sub.add_parser('verify-power-save-monitor-language-volume-delete-vault', help='Phase 277 Pillar 48 Power Save by Monitor reality split & Power Save Start Time 9-condition recovery guard, Language BK_LANG 4-language Stage-B parity, Volume Settings 0..15 + XLR-H1 feedback guard, 4ch Audio Monitoring 5 routes, Delete confirm. Cancel-first & Slot-1 vault delete/format firewall verifier')
    p277_p48.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p277_p48.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p277_p48.add_argument('--out', help='optional exclusive new output directory for pillar48-power-save-monitor-language-volume-delete-vault-report.json')
    p277_master = sub.add_parser('verify-48pillar-recovery', help='Phase 277 unified 48/48 real-hardware recovery master aggregator (Pillars 1..47 + Pillar 48)')
    p277_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p277_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p277_master.add_argument('--out', help='optional exclusive new output directory for 48pillar-recovery-master-report.json')
    p282_p49 = sub.add_parser('verify-usb-mode-hdmi-info-protect-network-reset-vault', help='Phase 282 Pillar 49 USB Connection Mode 4-mode vs dormant NOUVC USB Streaming split, data-isolated USB PD guard, HDMI Info. Display LCD-blanking and 1080 Log/PPLUT clamp vs 4K clean-feed, Protect 4 scopes vs Format wipe Slot-1 dual-layer WP+firewall & Reset Network Set. auto-reboot + Airplane Mode zero-RF verifier')
    p282_p49.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p282_p49.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p282_p49.add_argument('--out', help='optional exclusive new output directory for pillar49-usb-mode-hdmi-info-protect-network-reset-vault-report.json')
    p282_master = sub.add_parser('verify-49pillar-recovery', help='Phase 282 unified 49/49 real-hardware recovery master aggregator (Pillars 1..48 + Pillar 49)')
    p282_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p282_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p282_master.add_argument('--out', help='optional exclusive new output directory for 49pillar-recovery-master-report.json')
    p287_p50 = sub.add_parser('verify-pp-scinetone-wb-metering-vault', help='Phase 287 Pillar 50 Picture Profile PP11 S-Cinetone default vs Creative Look / DRO / Log Shooting mutual exclusivity, PPLUT 1080p clamp & PP1..11 reset trap, White Balance 2500K..9900K / Custom 1..3 CAMSET exclusion / Cine EI guard & Metering 6-mode / De-Squeeze Face Priority / Base ISO invariance vault verifier')
    p287_p50.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p287_p50.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p287_p50.add_argument('--out', help='optional exclusive new output directory for pillar50-pp-scinetone-wb-metering-vault-report.json')
    p287_master = sub.add_parser('verify-50pillar-recovery', help='Phase 287 milestone unified 50/50 real-hardware recovery master aggregator (Pillars 1..49 + Pillar 50)')
    p287_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p287_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p287_master.add_argument('--out', help='optional exclusive new output directory for 50pillar-recovery-master-report.json')
    p292_p51 = sub.add_parser('verify-pillar51-raw-heif-colorspace-shuttertype-vault', help='Phase 292 Pillar 51 Still Image Quality Compressed/Uncompressed RAW vs dormant Lossless Comp, HEIF 4:2:0/4:2:2, HLG Still BT.2100 vs still-less FX6, Color Space AdobeRGB _DSC prefix and leading-underscore ban, Shutter Type 2-option Mechanical/Electronic without Auto, 1/250s sync and 5-lock matrix, e-Front Curtain, Long Exposure/High ISO NR, Drive Mode 10 fps Hi+ and Slot-1 EROFS/EBUSY vault verifier')
    p292_p51.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p292_p51.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p292_p51.add_argument('--out', help='optional exclusive new output directory for pillar51-raw-heif-colorspace-shuttertype-vault-report.json')
    p292_master = sub.add_parser('verify-51pillar-recovery', help='Phase 292 unified 51/51 real-hardware recovery master aggregator (Pillars 1..50 + Pillar 51)')
    p292_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p292_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p292_master.add_argument('--out', help='optional exclusive new output directory for 51pillar-recovery-master-report.json')
    p296_p52 = sub.add_parser('verify-pillar52-focus-area-zoom-iso-flash-vault', help='Phase 296 Pillar 52 Focus Area 14-area Still+Movie vs Tracking lockout, Focus Area Limit >= 2, AF Area Registration Lock Operation Parts Off and Initialize survival, body W/T Zoom Lever vs handle-less XLR-H1 myth-bust and FX6 Smart Handle 0..99 display contrast, ISO Range Limit and Still-only ISO AUTO Min. SS vs Cine EI Base ISO lock, Flash Mode Mechanical-Shutter Still 1/250s gate vs Video Light Mode PMIC 5V <= 900 mA and Slot-1 EROFS/EBUSY vault verifier')
    p296_p52.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p296_p52.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p296_p52.add_argument('--out', help='optional exclusive new output directory for pillar52-focus-area-zoom-iso-flash-vault-report.json')
    p296_master = sub.add_parser('verify-52pillar-recovery', help='Phase 296 unified 52/52 real-hardware recovery master aggregator (Pillars 1..51 + Pillar 52)')
    p296_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p296_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p296_master.add_argument('--out', help='optional exclusive new output directory for 52pillar-recovery-master-report.json')
    p300_p53 = sub.add_parser('verify-pillar53-dci4k-aspect-custom-hold-camset-vault', help='Phase 300 Milestone Pillar 53 XAVC S-I DCI 4K (4096x2160 17:9) vs Long-GOP UHD split, 24.00p mandatory reboot volatile /tmp Stage-B wipe & quarantine, 4264x2408 HDMI RAW, Still Aspect Ratio (3:2..1:1), Reg. Custom Shoot Set 11 checkboxes & HLG Off, Camera Set. Memory %%c:%%s/SONY/SETTING/%%s/CAMPR%%02d%%c.DAT & CAMSET isolation vs FX6 PRO/CAMERA, Playback Photo Capture (8.3M/2.1M DCI 4K lockout) / Enlarge Image & Slot-1 EROFS/EBUSY vault verifier')
    p300_p53.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p300_p53.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p300_p53.add_argument('--out', help='optional exclusive new output directory for pillar53-dci4k-aspect-custom-hold-camset-vault-report.json')
    p300_master = sub.add_parser('verify-53pillar-recovery', help='Phase 300 (300th Phase Milestone) unified 53/53 real-hardware recovery master aggregator (Pillars 1..52 + Pillar 53)')
    p300_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p300_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p300_master.add_argument('--out', help='optional exclusive new output directory for 53pillar-recovery-master-report.json')
    p304_p54 = sub.add_parser('verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault', help='Phase 304 Pillar 54 Sensor Cleaning >= 51%% NP-FZ100 battery gate + mandatory power-switch OFF vs FX6 e-ND + Technical APR, Exposure Comp. +-5.0/+-2.0 EV (M+ISO AUTO only, Exposure step Initialize-only, 100%% Cine EI lockout), Focus Mode 5-Still vs 2-Movie AF-C/MF clamp (EOPNOTSUPP=95/EINVAL=22) + Priority Set/AF Illuminator, Playback View Mode / exact 9-25 Image Index / Display as Group / Display Rotation / Rotate Slot-1 Tier-0 EROFS/EBUSY Vault Firewall verifier')
    p304_p54.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p304_p54.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p304_p54.add_argument('--out', help='optional exclusive new output directory for pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault-report.json')
    p304_master = sub.add_parser('verify-54pillar-recovery', help='Phase 304 unified 54/54 real-hardware recovery master aggregator (Pillars 1..53 + Pillar 54)')
    p304_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p304_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p304_master.add_argument('--out', help='optional exclusive new output directory for 54pillar-recovery-master-report.json')
    p308_p55 = sub.add_parser('verify-pillar55-lens-comp-af-illuminator-folder-rating-vault', help='Phase 308 Pillar 55 Lens Compensation Shading Auto/Off vs dormant Auto: Low (0x6c9c EOPNOTSUPP=95) + Distortion Auto-lock + Breathing + FX6 Technical > Lens, Movie AF Transition Speed/Subj. Shift Sens./AF Assist, Built-in Front AF Illuminator LED #8 vs zero-LED FX6, 5 Initialize-only items (Aperture Drive in AF / AF w/ Shutter / Pre-AF / orthogonal Circ. of Focus Point / Focus Area Color), File/Folder Settings + Playback Rating 1..5 stars Slot-1 Tier-0 EROFS/EBUSY Vault Firewall verifier')
    p308_p55.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p308_p55.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p308_p55.add_argument('--out', help='optional exclusive new output directory for pillar55-lens-comp-af-illuminator-folder-rating-vault-report.json')
    p308_master = sub.add_parser('verify-55pillar-recovery', help='Phase 308 (55/55 Recovery Pillars Milestone) unified 55/55 real-hardware recovery master aggregator (Pillars 1..54 + Pillar 55)')
    p308_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p308_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p308_master.add_argument('--out', help='optional exclusive new output directory for 55pillar-recovery-master-report.json')
    p314_p56 = sub.add_parser('verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault', help='Phase 314 Pillar 56 Still-only Switch V/H AF Area (0/90/270/INVALID orientation + 8 lockouts + coords clear) + 14-checkbox Focus Area Limit (>= 2 EINVAL=22 vs dormant xl/xs/custom_1..3 EOPNOTSUPP=95) + Initialize-only Focus Area Color vs FX6, 5-mode Exposure Std. Adjust (1/6 EV Initialize-only, EXIF isolation, M.M.) + Bracket Settings, 7-item Initialize-only TC/UB & TC/UB Disp. Setting (23.98p/24p/PAL format locks vs FX6 BNC TC IN/OUT), and Fail-Closed Slot-2 -> Slot-1 Reverse Copy Tier-0 Vault EROFS=30/EBUSY=16 Firewall + Slide Show Power-Save Bypass verifier')
    p314_p56.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p314_p56.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p314_p56.add_argument('--out', help='optional exclusive new output directory for pillar56-switch-vh-af-stdadj-tcub-copy-vault-report.json')
    p314_master = sub.add_parser('verify-56pillar-recovery', help='Phase 314 (56/56 Recovery Pillars) unified 56/56 real-hardware recovery master aggregator (Pillars 1..55 + Pillar 56)')
    p314_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p314_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p314_master.add_argument('--out', help='optional exclusive new output directory for 56pillar-recovery-master-report.json')
    p320_p57 = sub.add_parser('verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault', help='Phase 320 Pillar 57 Wave-55 Touch Operation 4-item Initialize-only tree vs dormant Touch Shutter/AE/Pad/Footer (EOPNOTSUPP=95), Operation Customize -> DISP (Screen Disp) Set 4-shoot/3-PB pages + Zero-EVF Blackout Guard (zero built-in EVF/eye sensor/FINDER-MONITOR vs FX6 detachable LCD Viewfinder), Still-only AEL w/ Shutter & Flash Submenu reset split (Wireless Flash ONLY Camera Settings Reset vs direct MI-Shoe External Flash Set. vs FX6 Flash Band Reduce), Playback -> Viewing 9-speed Interval PB (1..9 default 5 read-only), and Playback -> Edit Slot-1 Tier-0 EROFS=30 / dormant Beauty Effect & Trimming EOPNOTSUPP=95 Vault Firewall verifier')
    p320_p57.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p320_p57.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p320_p57.add_argument('--out', help='optional exclusive new output directory for pillar57-touch-disp-zero-evf-flash-interval-pb-vault-report.json')
    p320_master = sub.add_parser('verify-57pillar-recovery', help='Phase 320 (57/57 Recovery Pillars) unified 57/57 real-hardware recovery master aggregator (Pillars 1..56 + Pillar 57)')
    p320_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p320_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p320_master.add_argument('--out', help='optional exclusive new output directory for 57pillar-recovery-master-report.json')
    p326_p58 = sub.add_parser('verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault', help='Phase 326 Pillar 58 Wave-56 Dial Customize 5-item Initialize-only tree vs dormant Dial Setup/Dial-Wheel Lock/Rear Dial L-R (EOPNOTSUPP=95), My Dial 1..3 skip-empty + Lock override, Operation Customize -> Fn Menu Settings 12+12 slots vs FX6 Multi Function/Grip/Handle/IRIS/ND Dial, Still-only Live View Display Set. 3-item reset split (Frame Rate Low Limit Resettable) + Bright Monitoring OFF, Grid Line Clean-HDMI/RAW OSD isolation, and Manage User LUTs / Select LUT (s709 vs 709(800%%)) / Log Shooting Embed LUT File container embed vs PPLUT1..4 bake & Slot-1 Tier-0 EROFS=30 Vault Firewall verifier')
    p326_p58.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p326_p58.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p326_p58.add_argument('--out', help='optional exclusive new output directory for pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault-report.json')
    p326_master = sub.add_parser('verify-58pillar-recovery', help='Phase 326 (58/58 Recovery Pillars) unified 58/58 real-hardware recovery master aggregator (Pillars 1..57 + Pillar 58)')
    p326_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p326_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p326_master.add_argument('--out', help='optional exclusive new output directory for 58pillar-recovery-master-report.json')
    p332_p59 = sub.add_parser('verify-pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault', help='Phase 332 Pillar 59 Wave-57 SteadyShot 5-Axis IBIS 47-step Focal Length (8..1000mm) & 4 Active Lockouts vs dormant Dynamic active (EOPNOTSUPP=95) & FX6 zero IBIS, dormant Movie Self-timer vs Still Self-timer #8 LED & Initialize-only Audio signals vs FX6 Picture Cache/Interval Rec, Initialize-only Zebra Custom1-2 IRE (Std+Range 0..109 +/- 1..10%% / Lower Limit 0..109+) + 4-color Peaking Clean-HDMI isolation vs FX6 Off/Zebra1/Zebra2+B&W, and Network Streaming RTMP/RTMPS/SRT (59.94/50/29.97/25p only, no 23.98p/24p, Movie Rec During Streaming 4K lockout, Reset Network Set. preserving Airplane Mode=On) Zero-RF & Slot-1 Tier-0 EROFS=30 Vault Firewall verifier')
    p332_p59.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p332_p59.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p332_p59.add_argument('--out', help='optional exclusive new output directory for pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault-report.json')
    p332_p59_alias = sub.add_parser('verify-pillar59-recovery', help='Phase 332 Pillar 59 standalone verifier alias (Wave-57 SteadyShot 47-Focal / Self-Timer / Zebra Custom1-2 / Peaking / RTMP-RTMPS-SRT Streaming Zero-RF & Slot-1 EROFS=30 Vault Firewall)')
    p332_p59_alias.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p332_p59_alias.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p332_p59_alias.add_argument('--out', help='optional exclusive new output directory for pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault-report.json')
    p332_master = sub.add_parser('verify-59pillar-recovery', help='Phase 332 (59/59 Recovery Pillars) unified 59/59 real-hardware recovery master aggregator (Pillars 1..58 + Pillar 59)')
    p332_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p332_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p332_master.add_argument('--out', help='optional exclusive new output directory for 59pillar-recovery-master-report.json')
    p336_p60 = sub.add_parser('verify-pillar60-bright-mon-shotmark-usblan-bulb-vault', help='Phase 336 Pillar 60 (Bright Monitoring Ver.7.00+ Focus-Mag Coexistence, Monitor Brightness & Mechanical BULB vs Dormant Bulb Timer/Auto HDR / Shot Mark 1-2 & Clip Flag vs Dormant Divide, VMC-BNCM1 EXT-LK, WPA3-SAE & USB-LAN Airplane-Mode Isolation + Slot-1 EROFS=30 Vault Firewall)')
    p336_p60.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p336_p60.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p336_p60.add_argument('--out', help='optional exclusive new output directory for pillar60-bright-mon-shotmark-usblan-bulb-vault-report.json')
    p336_p60_alias = sub.add_parser('verify-pillar60-recovery', help='Alias for verify-pillar60-bright-mon-shotmark-usblan-bulb-vault (Phase 336 Pillar 60 standalone 12-scenario suite)')
    p336_p60_alias.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p336_p60_alias.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p336_p60_alias.add_argument('--out', help='optional exclusive new output directory for pillar60-bright-mon-shotmark-usblan-bulb-vault-report.json')
    p336_master = sub.add_parser('verify-60pillar-recovery', help='Phase 336 (60/60 Milestone) unified 60/60 real-hardware recovery master aggregator (Pillars 1..59 + Pillar 60)')
    p336_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p336_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p336_master.add_argument('--out', help='optional exclusive new output directory for 60pillar-recovery-master-report.json')
    p340_p61 = sub.add_parser('verify-pillar61-big6-framing-interval-tc-auth-fan-vault', help='Phase 340 Pillar 61 (Wave-59 Ver.7.00/7.02 HOME BIG6 Fixed/Variable & Lower-Left metadata-only ND vs FX6 e-ND, Manual Framing Settings vs dormant Auto Framing EOPNOTSUPP=95, Still Interval Shoot Func. 9999 shots Slot-1 EROFS=30 vs FX6 Interval Rec, Initialize-only Time Code Make/Run Regenerate forced Rec Run & HDMI REC Control TC Output=On gate, Ver.7.00+ Access Authen. SSH+PTP-IP & outbound TLS Root Cert, Fan Control 4-mode FX3 / 3-mode FX6 with ZERO Max + Zero-RF Slot-1 Vault Firewall)')
    p340_p61.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p340_p61.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p340_p61.add_argument('--out', help='optional exclusive new output directory for pillar61-big6-framing-interval-tc-auth-fan-vault-report.json')
    p340_p61_alias = sub.add_parser('verify-pillar61-recovery', help='Alias for verify-pillar61-big6-framing-interval-tc-auth-fan-vault (Phase 340 Pillar 61 standalone 12-scenario suite)')
    p340_p61_alias.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p340_p61_alias.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p340_p61_alias.add_argument('--out', help='optional exclusive new output directory for pillar61-big6-framing-interval-tc-auth-fan-vault-report.json')
    p340_master = sub.add_parser('verify-61pillar-recovery', help='Phase 340 (61/61 Milestone) unified 61/61 real-hardware recovery master aggregator (Pillars 1..60 + Pillar 61)')
    p340_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p340_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p340_master.add_argument('--out', help='optional exclusive new output directory for 61pillar-recovery-master-report.json')
    p344_p62 = sub.add_parser(
        'verify-pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault',
        help='Phase 344 Pillar 62 (Wave-60 Rec. Media Settings, dormant Prioritize Rec. Media, Reset-immune Auto Switch Media Slot-1 spillover hazard, VPG200/VPG400 card-speed gates, Proxy Settings sq_proxy XAVC S-I DCI 4K allowed vs 120p/100p lockout and M4ROOT/SUB/*S03.MP4, Creators Cloud star Initialize-persistence, Cnct. while Power OFF BLE RF hazard, and My Menu 6x7=42 slots vs FX6 20-item User Menu with Lock + Slot-1 EROFS=30 Vault Firewall)',
    )
    p344_p62.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p344_p62.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p344_p62.add_argument('--out', help='optional exclusive new output directory for pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault-report.json')
    p344_p62_alias = sub.add_parser(
        'verify-pillar62-recovery',
        help='Alias for verify-pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault (Phase 344 Pillar 62 standalone 12-scenario suite)',
    )
    p344_p62_alias.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p344_p62_alias.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p344_p62_alias.add_argument('--out', help='optional exclusive new output directory for pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault-report.json')
    p344_master = sub.add_parser(
        'verify-62pillar-recovery',
        help='Phase 344 (62/62 Milestone) unified 62/62 real-hardware recovery master aggregator (Pillars 1..61 + Pillar 62)',
    )
    p344_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p344_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p344_master.add_argument('--out', help='optional exclusive new output directory for 62pillar-recovery-master-report.json')
    p348_p63 = sub.add_parser(
        'verify-pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault',
        help='Phase 348 Pillar 63 (Wave-61 [FTP Transfer Func.] FTP/FTPES Explicit TLS vs 0 SFTP, 9 Server Slots, Dormant Transfer JPEG/HEIF Size, USB-LAN Airplane-Mode Bypass & Slot-1 AVF_INFO EROFS=30 Firewall; White Balance Custom 1..3 / Cine EI Lockout / Shockless WB / Reset-immune Shutter AWB Lock vs FX6 ATW/Memory A..H; Movie AF Transition Speed 1..7 & AF Subj. Shift Sens. 1..5 Parity, App-Only Focus Map Ver. 6.00+ vs 0 In-Body UI; and 8 Reset-immune Marker Display 15 Ratios + 4-Color Peaking Display Clean-HDMI 0px Isolation vs FX6 80%%/90%%/92.5%%/95%% & User Box)',
    )
    p348_p63.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p348_p63.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p348_p63.add_argument('--out', help='optional exclusive new output directory for pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault-report.json')
    p348_p63_alias = sub.add_parser(
        'verify-pillar63-recovery',
        help='Alias for verify-pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault (Phase 348 Pillar 63 standalone 12-scenario suite)',
    )
    p348_p63_alias.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p348_p63_alias.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p348_p63_alias.add_argument('--out', help='optional exclusive new output directory for pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault-report.json')
    p348_master = sub.add_parser(
        'verify-63pillar-recovery',
        help='Phase 348 (63/63 Milestone) unified 63/63 real-hardware recovery master aggregator (Pillars 1..62 + Pillar 63)',
    )
    p348_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p348_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p348_master.add_argument('--out', help='optional exclusive new output directory for 63pillar-recovery-master-report.json')
    p352_p64 = sub.add_parser(
        'verify-pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault',
        help='Phase 352 Pillar 64 (Wave-62 Digital MI Shoe [Shoe Audio Set.] 48kHz/24bit 4ch vs 3.5mm/XLR-H1 ANALOG Preemption, [Audio Out Timing] Live/Lip Sync under Shooting, Removed [Audio Level Display], Proxy 2ch AAC & >=100p Lockout; [Face/Eye Subject] Human/Animal Still-Only vs Dormant Bird/Insect/Car/Airplane, Active 8-Face [Face Memory] & 0px Clean-HDMI; [Silent Mode Settings] 5-Lockout + 2-Item Target Matrix + Zero [Shutter When Pwr OFF]; and [Version] BODYDATA.DAT Slot 1 Root, >=51%% Battery, Ver. 2.04/2.05 Stepping Stone & NO-GO EROFS=30 Flash Firewall)',
    )
    p352_p64.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p352_p64.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p352_p64.add_argument('--out', help='optional exclusive new output directory for pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault-report.json')
    p352_p64_alias = sub.add_parser(
        'verify-pillar64-recovery',
        help='Alias for verify-pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault (Phase 352 Pillar 64 standalone 12-scenario suite)',
    )
    p352_p64_alias.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p352_p64_alias.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p352_p64_alias.add_argument('--out', help='optional exclusive new output directory for pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault-report.json')
    p352_master = sub.add_parser(
        'verify-64pillar-recovery',
        help='Phase 352 (64/64 Milestone) unified 64/64 real-hardware recovery master aggregator (Pillars 1..63 + Pillar 64)',
    )
    p352_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p352_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p352_master.add_argument('--out', help='optional exclusive new output directory for 64pillar-recovery-master-report.json')
    p355_p65 = sub.add_parser(
        'verify-pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault',
        help='Phase 355 Pillar 65 (Wave-63 HDMI Output 8-item reset-resistant tree, 4264x2408 16-bit linear RAW, Rec. Media dur HDMI Output On Slot-1 EROFS=30 vs Off(HDMI Only) zero-write, removed Color Gamut for RAW Output, 24.00p reboot + TC->REC Control vs FX6 12G-SDI RAW & RAW(HDMI) no-24Hz; De-Squeeze Display 1.3x/1.5x/1.6x[1.65x]/2.0x zero 1.8x, 4 hard locks, 6 bypasses, Focus Magnifier/Bright Mon allowed vs FX6 SDI non-desqueeze; REC Lamp 3-LED rear+top coupled Only Front Off & Silent Mode decoupling + Emphasized REC Display Clean-HDMI 0px; dormant Var. Shutter vs FX6 ECS 23.99..8000Hz & APS-C S35 Reset-Resistant 4K lockout + 5.1M Still)',
    )
    p355_p65.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p355_p65.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p355_p65.add_argument('--out', help='optional exclusive new output directory for pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault-report.json')
    p355_p65_alias = sub.add_parser(
        'verify-pillar65-recovery',
        help='Alias for verify-pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault (Phase 355 Pillar 65 standalone 12-scenario suite)',
    )
    p355_p65_alias.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p355_p65_alias.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p355_p65_alias.add_argument('--out', help='optional exclusive new output directory for pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault-report.json')
    p355_master = sub.add_parser(
        'verify-65pillar-recovery',
        help='Phase 355 (65/65 Milestone) unified 65/65 real-hardware recovery master aggregator (Pillars 1..64 + Pillar 65)',
    )
    p355_master.add_argument('--force-clean-room', '--clean-room', dest='force_clean_room', action='store_true', help='force clean-room synthetic mode without local donor files')
    p355_master.add_argument('--json', action='store_true', help='emit full structured JSON report')
    p355_master.add_argument('--out', help='optional exclusive new output directory for 65pillar-recovery-master-report.json')
    args = p.parse_args()
    try:
        if args.command == 'inspect':
            result = inspect_image(read_file(args.input, MAX_P1))
            new_directory(args.out, {'inspection.json': encode(result)})
        elif args.command == 'build':
            result = create_bundle(args.input, args.out, args.scope, args.body_tag)
        elif args.command == 'verify':
            manifest, source, candidate = load_bundle(args.bundle)
            result = {'status': 'VERIFIED_OFFLINE_ONLY', 'source_sha256': manifest['source_sha256'],
                      'candidate_sha256': manifest['candidate_sha256'], 'flashable': False}
        elif args.command == 'diagnose':
            result = diagnose(args.bundle, args.input)
        elif args.command == 'rollback':
            result = rollback(args.bundle, args.input, args.out)
        elif args.command == 'capture-local':
            result = capture_local(args.input, args.out, args.sha256, args.body_tag)
        elif args.command == 'verify-capture':
            result = verify_capture(args.capture, args.sha256)
        elif args.command == 'assemble-worker':
            result = assemble_worker_windows(args.windows,args.returns,args.out,args.body_tag)
        elif args.command == 'build-worker':
            result = build_worker(args.out)
        elif args.command == 'boot-request':
            result = B.create_request(args.capture_id,args.target,args.window,args.expected_total,args.out)
        elif args.command == 'build-boot-worker':
            result = B.build_worker(args.out)
        elif args.command == 'assemble-boot-worker':
            result = B.assemble_windows(args.windows,args.returns,args.out,args.body_tag)
        elif args.command == 'verify-emmc-forensics':
            if args.clean_room:
                result = run_clean_room_forensic_suite()
                if args.out:
                    new_directory(args.out, {'forensic-report.json': encode(result)})
            else:
                if not args.input:
                    raise ValueError('--input or --clean-room is required for verify-emmc-forensics')
                manifest_obj = None
                if args.manifest:
                    manifest_obj = json.loads(read_file(args.manifest, 1024 * 1024).decode('utf-8'))
                rep = verify_emmc_dump_file(
                    args.input,
                    role=args.role,
                    expected_size=args.expected_size,
                    expect_encrypted=args.expect_encrypted,
                    ext_csd_path=args.ext_csd,
                    manifest=manifest_obj,
                )
                result = report_to_dict(rep)
                result['status'] = 'VERIFIED_READONLY' if rep.passed else 'REJECTED'
                if args.out:
                    new_directory(args.out, {'forensic-report.json': encode(result)})
                if not rep.passed:
                    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
                    return 2
        elif args.command == 'verify-unbrick-ladder':
            report = run_unbrick_ladder_and_capsule_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'unbrick-ladder-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"scenarios_passed={report.scenarios_passed}/{report.scenario_count} "
                    f"capsule_fat12_sha256={report.capsule_fat12_tripped.capsule_sha256} "
                    f"capsule_fat16_sha256={report.capsule_fat16_tripped.capsule_sha256} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-rp2040-fixture':
            report = run_rp2040_multiport_fixture_selftest(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'rp2040-fixture-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} board={report.board} "
                    f"camera_connected={report.camera_connected} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-init2-escape':
            report = run_init2_escape_and_watchdog_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'init2-escape-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"escape_drills={report.escape_sandbox_suite.drills_passed}/{report.escape_sandbox_suite.drills_total} "
                    f"wdt_scenarios={report.watchdog_suite.scenarios_passed}/{report.watchdog_suite.scenarios_total} "
                    f"physical_writes={report.physical_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-tier0-backup':
            report = run_tier0_backup_parity_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'tier0-backup-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"partitions={report.bundle_validation.partition_count} "
                    f"body_binding_sha256={report.manifest.body_identity_binding_sha256[:16]} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-antirollback-guard':
            report = run_antirollback_and_byof_guard_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'antirollback-guard-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"antirollback_brick_risk={report.antirollback_brick_risk} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-all-recovery':
            report = run_recovery_master_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            overall_ok = report.all_passed
            if args.with_phase94:
                p94_report = run_gpt_rpmb_and_rescue_bundle_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase94_pillar8_gpt_rpmb_rescue'] = p94_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p94_report.all_passed else 0)
                overall_ok = overall_ok and p94_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase101:
                p101_report = run_ramdisk_overlay_and_emmc_health_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase101_pillar9_ramdisk_emmc_health'] = p101_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p101_report.all_passed else 0)
                overall_ok = overall_ok and p101_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase106:
                p106_report = run_fdt_bootargs_and_kernel_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase106_pillar10_fdt_bootargs_kernel'] = p106_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p106_report.all_passed else 0)
                overall_ok = overall_ok and p106_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase113:
                p113_report = run_ab_bank_and_interrupted_ota_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase113_pillar11_ab_bank_interrupted_ota'] = p113_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p113_report.all_passed else 0)
                overall_ok = overall_ok and p113_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase119:
                p119_report = run_squashfs_and_hibdrv_wbi_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase119_pillar12_squashfs_wbi_hibdrv'] = p119_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p119_report.all_passed else 0)
                overall_ok = overall_ok and p119_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase124:
                p124_report = run_bootrom_usb_and_emmc_bootpart_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase124_pillar13_bootrom_usb_emmc_bootpart'] = p124_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p124_report.all_passed else 0)
                overall_ok = overall_ok and p124_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase126:
                p126_report = run_factory_cal_ibis_defectpixel_and_nvs_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase126_pillar14_factory_cal_ibis_defectpixel_nvs'] = p126_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p126_report.all_passed else 0)
                overall_ok = overall_ok and p126_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase134:
                p134_report = run_secureboot_chain_and_partition_align_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase134_pillar15_secureboot_chain_partalign'] = p134_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p134_report.all_passed else 0)
                overall_ok = overall_ok and p134_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase138:
                p138_report = run_realhw_ext2_installer_and_p1_rescue_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase138_pillar16_realhw_ext2_installer_p1_rescue'] = p138_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p138_report.all_passed else 0)
                overall_ok = overall_ok and p138_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase139:
                p139_report = run_adjustcontrol_streaming_backup_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase139_pillar17_adjustcontrol_streaming_backup'] = p139_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p139_report.all_passed else 0)
                overall_ok = overall_ok and p139_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase144:
                p144_report = run_realhw_service_usb_and_libjit_hardener_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase144_pillar18_service_usb_libjit_hardener'] = p144_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p144_report.all_passed else 0)
                overall_ok = overall_ok and p144_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase151:
                p151_report = run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase151_pillar19_tier0_dual_layer_vault'] = p151_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p151_report.all_passed else 0)
                overall_ok = overall_ok and p151_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase155:
                p155_report = run_realhw_uart_460800_post_triage_and_isp_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase155_pillar20_uart_460800_isp_triage'] = p155_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p155_report.all_passed else 0)
                overall_ok = overall_ok and p155_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase160:
                p160_report = run_realhw_bootrom_el3_and_ufu_stock_reflash_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase160_pillar21_5tier_el3_ufu_recovery'] = p160_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p160_report.all_passed else 0)
                overall_ok = overall_ok and p160_report.all_passed
                result['all_passed'] = overall_ok
            if args.with_phase166:
                p166_report = run_pillar22_standalone_suite(
                    force_clean_room=True if args.clean_room else None,
                )
                result['phase166_pillar22_dual_media_cold_backup_gf256'] = p166_report.to_dict()
                result['pillar_count'] = result.get('pillar_count', report.pillar_count) + 1
                result['pillars_passed'] = result.get('pillars_passed', report.pillars_passed) + (1 if p166_report.all_passed else 0)
                overall_ok = overall_ok and p166_report.all_passed
                result['all_passed'] = overall_ok
            if args.out:
                new_directory(args.out, {'recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                has_opt_in = (
                    args.with_phase94
                    or args.with_phase101
                    or args.with_phase106
                    or args.with_phase113
                    or args.with_phase119
                    or args.with_phase124
                    or args.with_phase126
                    or args.with_phase134
                    or args.with_phase138
                    or args.with_phase139
                    or args.with_phase144
                    or args.with_phase151
                    or args.with_phase155
                    or args.with_phase160
                    or args.with_phase166
                )
                pillar_num = result['pillars_passed'] if has_opt_in else report.pillars_passed
                pillar_den = result['pillar_count'] if has_opt_in else report.pillar_count
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={overall_ok} "
                    f"pillars={pillar_num}/{pillar_den} "
                    f"uart_scenarios={report.uart_decoder_suite.scenarios_passed}/{report.uart_decoder_suite.scenarios_total} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"recovery_master_sha256={report.recovery_master_sha256[:16]} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if overall_ok else 2
        elif args.command == 'verify-gpt-rpmb-bundle':
            report = run_gpt_rpmb_and_rescue_bundle_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'gpt-rpmb-bundle-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"gpt_partitions={report.gpt_healthy_check.primary_audit.active_partition_count} "
                    f"rpmb_writes_emitted={report.rpmb_writes_emitted} "
                    f"stage_b_rehearsal_permitted={report.sd_rescue_valid_report.stage_b_rehearsal_permitted} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-ramdisk-emmc-health':
            report = run_ramdisk_overlay_and_emmc_health_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'ramdisk-emmc-health-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"cpio_entries={report.cpio_valid_report.entry_count} "
                    f"emmc_pre_eol={report.emmc_healthy_report.pre_eol_info_hex} "
                    f"emmc_life_a={report.emmc_healthy_report.life_time_typ_a_hex} "
                    f"emmc_life_b={report.emmc_healthy_report.life_time_typ_b_hex} "
                    f"zero_rw_block_mounts={report.mount_isolation_report.zero_rw_block_mounts} "
                    f"stage_b_containment_ready={report.stage_b_containment_ready} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-fdt-bootargs':
            report = run_fdt_bootargs_and_kernel_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'fdt-bootargs-kernel-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"fdt_nodes={report.stage_b_fdt_parse_report.node_count} "
                    f"kernel_magic={report.fx3_kernel_valid_report.magic_hex} "
                    f"kernel_release={report.fx3_kernel_valid_report.kernel_release} "
                    f"stage_b_boot_gate_ready={report.stage_b_boot_gate_ready} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-ab-bank-triage':
            report = run_ab_bank_and_interrupted_ota_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'ab-bank-ota-triage-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"ota_scenarios={report.ota_6_scenario_suite.scenarios_passed}/{report.ota_6_scenario_suite.scenarios_total} "
                    f"stage_b_u5_zero_brick_verified={report.ota_6_scenario_suite.stage_b_u5_zero_brick_verified} "
                    f"split_deadlock_rejected={not report.dual_bank_split_deadlock_report.passed} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-squashfs-wbi-triage':
            report = run_squashfs_and_hibdrv_wbi_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'squashfs-wbi-triage-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"squashfs_compressions={len(report.squashfs_compression_reports)} "
                    f"wbi_scenarios={report.wbi_6_scenario_suite.scenarios_passed}/{report.wbi_6_scenario_suite.scenarios_total} "
                    f"wbi_partition_writes={report.wbi_partition_writes} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-bootrom-bootpart':
            report = run_bootrom_usb_and_emmc_bootpart_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'bootrom-bootpart-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"bootpart_scenarios={report.emmc_bootpart_6_scenario_suite.scenarios_passed}/{report.emmc_bootpart_6_scenario_suite.scenarios_total} "
                    f"bootrom_scenarios={report.bootrom_usb_5_scenario_suite.scenarios_passed}/{report.bootrom_usb_5_scenario_suite.scenarios_total} "
                    f"emmc_persistent_program_commands={report.emmc_persistent_program_commands} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-factory-cal-guard':
            report = run_factory_cal_ibis_defectpixel_and_nvs_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'factory-cal-guard-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"factory_cal_scenarios={report.factory_cal_6_scenario_firewall.scenarios_passed}/{report.factory_cal_6_scenario_firewall.scenarios_total} "
                    f"sensor_ibis_scenarios={report.sensor_ibis_6_scenario_suite.scenarios_passed}/{report.sensor_ibis_6_scenario_suite.scenarios_total} "
                    f"factory_cal_mutation_bytes={report.factory_cal_mutation_bytes} "
                    f"private_key_bytes_read={report.private_key_bytes_read} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-secureboot-partalign':
            report = run_secureboot_chain_and_partition_align_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'secureboot-partalign-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"secureboot_scenarios={report.secureboot_6_scenario_firewall.scenarios_passed}/{report.secureboot_6_scenario_firewall.scenarios_total} "
                    f"partalign_scenarios={report.partition_align_6_scenario_firewall.scenarios_passed}/{report.partition_align_6_scenario_firewall.scenarios_total} "
                    f"otp_fuse_writes={report.otp_fuse_writes} "
                    f"spacc_key_reads={report.spacc_key_reads} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-realhw-ext2-installer':
            report = run_realhw_ext2_installer_and_p1_rescue_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'realhw-ext2-installer-p1-rescue-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"ext2_installer_scenarios={report.pillar_a_ext2_installer_6_scenarios.scenarios_passed}/{report.pillar_a_ext2_installer_6_scenarios.scenarios_total} "
                    f"p1_rescue_scenarios={report.pillar_b_p1_rescue_6_scenarios.scenarios_passed}/{report.pillar_b_p1_rescue_6_scenarios.scenarios_total} "
                    f"tier0_lock_scenarios={report.pillar_c_tier0_lock_4_scenarios.scenarios_passed}/{report.pillar_c_tier0_lock_4_scenarios.scenarios_total} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"otp_fuse_writes={report.otp_fuse_writes} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-adjustcontrol-backup-client':
            report = run_adjustcontrol_streaming_backup_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'adjustcontrol-streaming-backup-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"wire_preflight_scenarios={report.pillar_a_wire_and_preflight_7_scenarios.scenarios_passed}/{report.pillar_a_wire_and_preflight_7_scenarios.scenarios_total} "
                    f"dual_path_backup_scenarios={report.pillar_b_dual_path_backup_6_scenarios.scenarios_passed}/{report.pillar_b_dual_path_backup_6_scenarios.scenarios_total} "
                    f"fake_iokit_scenarios={report.pillar_c_fake_iokit_regression_5_scenarios.scenarios_passed}/{report.pillar_c_fake_iokit_regression_5_scenarios.scenarios_total} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"live_usb_iokit_transmit_enabled={report.live_usb_iokit_transmit_enabled} "
                    f"physical_usb_bytes_transmitted={report.physical_usb_bytes_transmitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-service-usb-libjit':
            report = run_realhw_service_usb_and_libjit_hardener_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'service-usb-libjit-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"service_usb_scenarios={report.pillar_a_service_usb_8_scenarios.scenarios_passed}/{report.pillar_a_service_usb_8_scenarios.scenarios_total} "
                    f"hardened_libjit_scenarios={report.pillar_b_hardened_libjit_8_scenarios.scenarios_passed}/{report.pillar_b_hardened_libjit_8_scenarios.scenarios_total} "
                    f"hardened_elf_bytes={report.pillar_b_hardened_libjit_8_scenarios.hardened_elf_bytes} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"live_usb_iokit_transmit_enabled={report.live_usb_iokit_transmit_enabled} "
                    f"usb_tx_packets_emitted={report.usb_tx_packets_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-tier0-dual-layer-vault':
            report = run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'tier0-dual-layer-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"surfaces={report.pillar_a_vault_manifest_report.surface_count}/16 "
                    f"pillar_a_scenarios={report.pillar_a_firewall_8_scenarios.scenarios_passed}/{report.pillar_a_firewall_8_scenarios.scenarios_total} "
                    f"pillar_b_scenarios={report.pillar_b_gate_6_scenarios.scenarios_passed}/{report.pillar_b_gate_6_scenarios.scenarios_total} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"mtd_rw_opens_or_erase_ioctls={report.mtd_rw_opens_or_erase_ioctls} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-uart-460800-isp-triage':
            report = run_realhw_uart_460800_post_triage_and_isp_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'uart-460800-isp-triage-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_a_triage={report.pillar_a_triage_8_scenarios.scenarios_passed}/{report.pillar_a_triage_8_scenarios.scenarios_total} "
                    f"pillar_b_firewall={report.pillar_b_firewall_6_scenarios.scenarios_passed}/{report.pillar_b_firewall_6_scenarios.scenarios_total} "
                    f"pillar_c_isp={report.pillar_c_isp_6_scenarios.scenarios_passed}/{report.pillar_c_isp_6_scenarios.scenarios_total} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"persistent_write_release={report.persistent_write_release}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-realhw-5tier-el3-ufu':
            report = run_realhw_bootrom_el3_and_ufu_stock_reflash_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'realhw-5tier-el3-ufu-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_a_ufu={report.pillar_a_ufu_8_scenarios.scenarios_passed}/{report.pillar_a_ufu_8_scenarios.scenarios_total} "
                    f"pillar_b_el3={report.pillar_b_el3_6_scenarios.scenarios_passed}/{report.pillar_b_el3_6_scenarios.scenarios_total} "
                    f"pillar_c_5tier={report.pillar_c_5tier_8_scenarios.scenarios_passed}/{report.pillar_c_5tier_8_scenarios.scenarios_total} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"physical_device_writes={report.physical_device_writes}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-22pillar-recovery':
            report = verify_22pillar_recovery_suite(
                force_clean_room=True if args.clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'22pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_2s_budget={report.under_2s_budget} "
                    f"pillar22_a={report.pillar22_a_dual_media.scenarios_passed}/{report.pillar22_a_dual_media.scenarios_total} "
                    f"pillar22_b={report.pillar22_b_gf256_scrub.scenarios_passed}/{report.pillar22_b_gf256_scrub.scenarios_total} "
                    f"master_22pillar_sha256={report.master_22pillar_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-wbi-powerloss-recovery':
            report = run_wbi_powerloss_and_100cycle_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'wbi-powerloss-100cycle-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_23a={report.pillar_23a_wbi_firewall.scenarios_passed}/{report.pillar_23a_wbi_firewall.scenarios_total} "
                    f"pillar_23b={report.pillar_23b_powerloss_100cycle.scenarios_passed}/{report.pillar_23b_powerloss_100cycle.scenarios_total} "
                    f"cycles={report.pillar_23b_powerloss_100cycle.cycles_passed}/{report.pillar_23b_powerloss_100cycle.cycles_executed} "
                    f"emmc_bit_drift_count={report.pillar_23b_powerloss_100cycle.emmc_bit_drift_count} "
                    f"h0_equals_h3={report.pillar_23b_powerloss_100cycle.h0_equals_h3} "
                    f"wbi_persistent_writes={report.wbi_persistent_writes} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1s_budget={report.under_1s_budget} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-slot1-ufu-reflash-readiness':
            report = run_pillar24_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar24-slot1-ufu-hygiene-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_24a={report.pillar_24a_slot1_ufu_readiness.scenarios_passed}/{report.pillar_24a_slot1_ufu_readiness.scenarios_total} "
                    f"pillar_24b={report.pillar_24b_rollback_hygiene.scenarios_passed}/{report.pillar_24b_rollback_hygiene.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-24pillar-recovery':
            report = verify_24pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'24pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_8s_budget={report.under_1_8s_budget} "
                    f"nominal_under_1_8s={report.nominal_under_1_8s} "
                    f"pillar24_a={report.pillar24_a_slot1_ufu_readiness.scenarios_passed}/{report.pillar24_a_slot1_ufu_readiness.scenarios_total} "
                    f"pillar24_b={report.pillar24_b_rollback_hygiene.scenarios_passed}/{report.pillar24_b_rollback_hygiene.scenarios_total} "
                    f"master_24pillar_sha256={report.master_24pillar_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-airgap-sd-bundle':
            report = run_airgap_sd_bundle_manifest_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar25-airgap-sd-bundle-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_25a={report.pillar_25a_fx3bndl1_binding.scenarios_passed}/{report.pillar_25a_fx3bndl1_binding.scenarios_total} "
                    f"pillar_25b={report.pillar_25b_exfat_hygiene.scenarios_passed}/{report.pillar_25b_exfat_hygiene.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"airgap_sockets_opened={report.airgap_sockets_opened} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-fx3a-branch-recovery-firewall':
            report = run_pillar26_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar26-fx3a-branch-firewall-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_26a={report.pillar_26a_fx3a_firewall.scenarios_passed}/{report.pillar_26a_fx3a_firewall.scenarios_total} "
                    f"pillar_26b={report.pillar_26b_xlrh1_hygiene.scenarios_passed}/{report.pillar_26b_xlrh1_hygiene.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-26pillar-recovery':
            report = verify_26pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'26pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_2s={report.nominal_under_2s} "
                    f"pillar26_a={report.pillar26_a_fx3a_firewall.scenarios_passed}/{report.pillar26_a_fx3a_firewall.scenarios_total} "
                    f"pillar26_b={report.pillar26_b_xlrh1_hygiene.scenarios_passed}/{report.pillar26_b_xlrh1_hygiene.scenarios_total} "
                    f"master_26pillar_sha256={report.master_26pillar_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-dcc1-pd-lut-vault':
            report = run_pillar27_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar27-dcc1-pd-lut-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_27a={report.pillar_27a_dcc1_pd_interlock.scenarios_passed}/{report.pillar_27a_dcc1_pd_interlock.scenarios_total} "
                    f"pillar_27b={report.pillar_27b_cube_lut_vault.scenarios_passed}/{report.pillar_27b_cube_lut_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-27pillar-recovery':
            report = verify_27pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'27pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_2_2s={report.nominal_under_2_2s} "
                    f"pillar27_a={report.pillar27_a_dcc1_pd_interlock.scenarios_passed}/{report.pillar27_a_dcc1_pd_interlock.scenarios_total} "
                    f"pillar27_b={report.pillar27_b_cube_lut_vault.scenarios_passed}/{report.pillar27_b_cube_lut_vault.scenarios_total} "
                    f"master_27pillar_sha256={report.master_27pillar_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-fan-pwm-lut-split-vault':
            report = run_pillar28_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar28-fan-pwm-lut-split-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_28a={report.pillar_28a_fan_pwm_interlock.scenarios_passed}/{report.pillar_28a_fan_pwm_interlock.scenarios_total} "
                    f"pillar_28b={report.pillar_28b_lut_split_shutter_vault.scenarios_passed}/{report.pillar_28b_lut_split_shutter_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-28pillar-recovery':
            report = verify_28pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'28pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_2_4s={report.nominal_under_2_4s} "
                    f"pillar28_a={report.pillar28_a_fan_pwm_interlock.scenarios_passed}/{report.pillar28_a_fan_pwm_interlock.scenarios_total} "
                    f"pillar28_b={report.pillar28_b_lut_split_shutter_vault.scenarios_passed}/{report.pillar28_b_lut_split_shutter_vault.scenarios_total} "
                    f"master_28pillar_sha256={report.master_28pillar_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-camset-simult-vault':
            report = run_pillar29_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar29-camset-simult-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_29a={report.pillar_29a_camset_big6_vault.scenarios_passed}/{report.pillar_29a_camset_big6_vault.scenarios_total} "
                    f"pillar_29b={report.pillar_29b_simult_tcin_desqueeze_vault.scenarios_passed}/{report.pillar_29b_simult_tcin_desqueeze_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-29pillar-recovery':
            report = verify_29pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'29pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_2_5s={report.nominal_under_2_5s} "
                    f"pillar29_a={report.pillar29_a_camset_big6_vault.scenarios_passed}/{report.pillar29_a_camset_big6_vault.scenarios_total} "
                    f"pillar29_b={report.pillar29_b_simult_tcin_desqueeze_vault.scenarios_passed}/{report.pillar29_b_simult_tcin_desqueeze_vault.scenarios_total} "
                    f"master_29pillar_sha256={report.master_29pillar_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-proxy-coupled-hdmi-vault':
            report = run_pillar30_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar30-proxy-coupled-hdmi-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_30a={report.pillar_30a_proxy_coupled_vault.scenarios_passed}/{report.pillar_30a_proxy_coupled_vault.scenarios_total} "
                    f"pillar_30b={report.pillar_30b_hdmi_only_interlock.scenarios_passed}/{report.pillar_30b_hdmi_only_interlock.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-30pillar-recovery':
            report = verify_30pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'30pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_2_6s={report.nominal_under_2_6s} "
                    f"pillar30_a={report.pillar30_a_proxy_coupled_vault.scenarios_passed}/{report.pillar30_a_proxy_coupled_vault.scenarios_total} "
                    f"pillar30_b={report.pillar30_b_hdmi_only_interlock.scenarios_passed}/{report.pillar30_b_hdmi_only_interlock.scenarios_total} "
                    f"master_30pillar_sha256={report.master_30pillar_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-filesettings-shotmark-tcregen-vault':
            report = run_pillar31_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar31-filesettings-shotmark-tcregen-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_31a={report.pillar_31a_filesettings_shotmark_vault.scenarios_passed}/{report.pillar_31a_filesettings_shotmark_vault.scenarios_total} "
                    f"pillar_31b={report.pillar_31b_tcregen_slot1_extlk_vault.scenarios_passed}/{report.pillar_31b_tcregen_slot1_extlk_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-31pillar-recovery':
            report = verify_31pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'31pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_2_8s={report.nominal_under_2_8s} "
                    f"pillar31_a={report.pillar31_a_filesettings_shotmark_vault.scenarios_passed}/{report.pillar31_a_filesettings_shotmark_vault.scenarios_total} "
                    f"pillar31_b={report.pillar31_b_tcregen_slot1_extlk_vault.scenarios_passed}/{report.pillar31_b_tcregen_slot1_extlk_vault.scenarios_total} "
                    f"master_31pillar_sha256={report.master_31pillar_sha256[:16]} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-ntscpal-pixelmap-vault':
            report = run_pillar32_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar32-ntscpal-pixelmap-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_32a={report.pillar_32a_ntscpal_gamma_vault.scenarios_passed}/{report.pillar_32a_ntscpal_gamma_vault.scenarios_total} "
                    f"pillar_32b={report.pillar_32b_pixelmap_cnflasha_vault.scenarios_passed}/{report.pillar_32b_pixelmap_cnflasha_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-32pillar-recovery':
            report = verify_32pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'32pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_3_0s={report.nominal_under_3_0s} "
                    f"pillar32_a={report.pillar32_a_ntscpal_gamma_vault.scenarios_passed}/{report.pillar32_a_ntscpal_gamma_vault.scenarios_total} "
                    f"pillar32_b={report.pillar32_b_pixelmap_cnflasha_vault.scenarios_passed}/{report.pillar32_b_pixelmap_cnflasha_vault.scenarios_total} "
                    f"master_32pillar_sha256={report.master_32pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-powersave-9cond-temp-vault':
            report = run_pillar33_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar33-powersave-9cond-temp-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_33a={report.pillar_33a_powersave_autotemp_vault.scenarios_passed}/{report.pillar_33a_powersave_autotemp_vault.scenarios_total} "
                    f"pillar_33b={report.pillar_33b_steadyshot_ciz_vault.scenarios_passed}/{report.pillar_33b_steadyshot_ciz_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-33pillar-recovery':
            report = verify_33pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'33pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_3_2s={report.nominal_under_3_2s} "
                    f"pillar33_a={report.pillar33_a_powersave_autotemp_vault.scenarios_passed}/{report.pillar33_a_powersave_autotemp_vault.scenarios_total} "
                    f"pillar33_b={report.pillar33_b_steadyshot_ciz_vault.scenarios_passed}/{report.pillar33_b_steadyshot_ciz_vault.scenarios_total} "
                    f"master_33pillar_sha256={report.master_33pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-zebra-fullformat-chord-vault':
            report = run_pillar34_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar34-zebra-fullformat-chord-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_34a={report.pillar_34a_fullformat_chord_vault.scenarios_passed}/{report.pillar_34a_fullformat_chord_vault.scenarios_total} "
                    f"pillar_34b={report.pillar_34b_zebra_sq_recovery_vault.scenarios_passed}/{report.pillar_34b_zebra_sq_recovery_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-34pillar-recovery':
            report = verify_34pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'34pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_3_4s={report.nominal_under_3_4s} "
                    f"pillar34_a={report.pillar34_a_fullformat_chord_vault.scenarios_passed}/{report.pillar34_a_fullformat_chord_vault.scenarios_total} "
                    f"pillar34_b={report.pillar34_b_zebra_sq_recovery_vault.scenarios_passed}/{report.pillar34_b_zebra_sq_recovery_vault.scenarios_total} "
                    f"master_34pillar_sha256={report.master_34pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-silent-autopixelmap-marker-vault':
            report = run_pillar35_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar35-silent-autopixelmap-marker-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_35a={report.pillar_35a_silent_autopixelmap_firewall.scenarios_passed}/{report.pillar_35a_silent_autopixelmap_firewall.scenarios_total} "
                    f"pillar_35b={report.pillar_35b_marker_hdmi_flexexp_vault.scenarios_passed}/{report.pillar_35b_marker_hdmi_flexexp_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-35pillar-recovery':
            report = verify_35pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'35pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_3_6s={report.nominal_under_3_6s} "
                    f"pillar35_a={report.pillar35_a_silent_autopixelmap_firewall.scenarios_passed}/{report.pillar35_a_silent_autopixelmap_firewall.scenarios_total} "
                    f"pillar35_b={report.pillar35_b_marker_hdmi_flexexp_vault.scenarios_passed}/{report.pillar35_b_marker_hdmi_flexexp_vault.scenarios_total} "
                    f"master_35pillar_sha256={report.master_35pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-recover-imagedb-monitor-flip-vault':
            report = run_pillar36_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar36-recover-imagedb-monitor-flip-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_36a={report.pillar_36a_recover_imagedb_vault_firewall.scenarios_passed}/{report.pillar_36a_recover_imagedb_vault_firewall.scenarios_total} "
                    f"pillar_36b={report.pillar_36b_monitor_flip_af_interval_vault.scenarios_passed}/{report.pillar_36b_monitor_flip_af_interval_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-36pillar-recovery':
            report = verify_36pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'36pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_3_8s={report.nominal_under_3_8s} "
                    f"pillar36_a={report.pillar36_a_recover_imagedb_vault_firewall.scenarios_passed}/{report.pillar36_a_recover_imagedb_vault_firewall.scenarios_total} "
                    f"pillar36_b={report.pillar36_b_monitor_flip_af_interval_vault.scenarios_passed}/{report.pillar36_b_monitor_flip_af_interval_vault.scenarios_total} "
                    f"master_36pillar_sha256={report.master_36pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-touch-recframe-hdmi-sunny-vault':
            report = run_pillar37_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar37-touch-recframe-hdmi-sunny-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_37a={report.pillar_37a_touch_bench_sunny_weather_guard.scenarios_passed}/{report.pillar_37a_touch_bench_sunny_weather_guard.scenarios_total} "
                    f"pillar_37b={report.pillar_37b_recframe_grid_hdmi_clean_feed_vault.scenarios_passed}/{report.pillar_37b_recframe_grid_hdmi_clean_feed_vault.scenarios_total} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-37pillar-recovery':
            report = verify_37pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'37pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar37_a={report.pillar37_a_touch_bench_sunny_weather_guard.scenarios_passed}/{report.pillar37_a_touch_bench_sunny_weather_guard.scenarios_total} "
                    f"pillar37_b={report.pillar37_b_recframe_grid_hdmi_clean_feed_vault.scenarios_passed}/{report.pillar37_b_recframe_grid_hdmi_clean_feed_vault.scenarios_total} "
                    f"master_37pillar_sha256={report.master_37pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-shoe-audio-wind-saveload-vault':
            report = run_pillar38_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar38-shoe-audio-wind-saveload-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_38a={report.pillar_38a_shoe_audio_wind_vault.scenarios_passed}/{report.pillar_38a_shoe_audio_wind_vault.scenarios_total} "
                    f"pillar_38b={report.pillar_38b_saveload_c3_exclusion_vault.scenarios_passed}/{report.pillar_38b_saveload_c3_exclusion_vault.scenarios_total} "
                    f"excluded_secret_or_cal_leak_count={report.excluded_secret_or_cal_leak_count} "
                    f"slot1_unverified_camset_save_mutations={report.slot1_unverified_camset_save_mutations} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-38pillar-recovery':
            report = verify_38pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'38pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar38_a={report.pillar38_a_shoe_audio_wind_vault.scenarios_passed}/{report.pillar38_a_shoe_audio_wind_vault.scenarios_total} "
                    f"pillar38_b={report.pillar38_b_saveload_c3_exclusion_vault.scenarios_passed}/{report.pillar38_b_saveload_c3_exclusion_vault.scenarios_total} "
                    f"excluded_secret_or_cal_leak_count={report.excluded_secret_or_cal_leak_count} "
                    f"slot1_unverified_camset_save_mutations={report.slot1_unverified_camset_save_mutations} "
                    f"master_38pillar_sha256={report.master_38pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-framing-usbpower-lun-antiflicker-vault':
            report = run_pillar39_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar39-framing-usbpower-lun-antiflicker-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_39a={report.pillar_39a_framing_antiflicker_vault.scenarios_passed}/{report.pillar_39a_framing_antiflicker_vault.scenarios_total} "
                    f"pillar_39b={report.pillar_39b_usb_power_lun_vault.scenarios_passed}/{report.pillar_39b_usb_power_lun_vault.scenarios_total} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-39pillar-recovery':
            report = verify_39pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'39pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar39_a={report.pillar39_a_framing_antiflicker_vault.scenarios_passed}/{report.pillar39_a_framing_antiflicker_vault.scenarios_total} "
                    f"pillar39_b={report.pillar39_b_usb_power_lun_vault.scenarios_passed}/{report.pillar39_b_usb_power_lun_vault.scenarios_total} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_39pillar_sha256={report.master_39pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-lock-op-parts-audio-timing-exp-step-vault':
            report = run_pillar40_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar40-lock-op-parts-audio-timing-exp-step-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_40a={report.pillar_40a_lock_op_parts_vault.scenarios_passed}/{report.pillar_40a_lock_op_parts_vault.scenarios_total} "
                    f"pillar_40b={report.pillar_40b_audio_timing_exp_step_vault.scenarios_passed}/{report.pillar_40b_audio_timing_exp_step_vault.scenarios_total} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-40pillar-recovery':
            report = verify_40pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'40pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar40_a={report.pillar40_a_lock_op_parts_vault.scenarios_passed}/{report.pillar40_a_lock_op_parts_vault.scenarios_total} "
                    f"pillar40_b={report.pillar40_b_audio_timing_exp_step_vault.scenarios_passed}/{report.pillar40_b_audio_timing_exp_step_vault.scenarios_total} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_40pillar_sha256={report.master_40pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-display-quality-bt-rmt-mymenu-vault':
            report = run_pillar41_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar41-display-quality-bt-rmt-mymenu-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_41a={report.pillar_41a_display_quality_bt_rmt_vault.scenarios_passed}/{report.pillar_41a_display_quality_bt_rmt_vault.scenarios_total} "
                    f"pillar_41b={report.pillar_41b_my_menu_camset_vault.scenarios_passed}/{report.pillar_41b_my_menu_camset_vault.scenarios_total} "
                    f"tier0_battery_high_display_violations={report.tier0_battery_high_display_violations} "
                    f"bt_rmt_ir_lockout_violations={report.bt_rmt_ir_lockout_violations} "
                    f"slot1_mymenu_vault_mutation_bytes={report.slot1_mymenu_vault_mutation_bytes} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-41pillar-recovery':
            report = verify_41pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'41pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar41_a={report.pillar41_a_display_quality_bt_rmt_vault.scenarios_passed}/{report.pillar41_a_display_quality_bt_rmt_vault.scenarios_total} "
                    f"pillar41_b={report.pillar41_b_my_menu_camset_vault.scenarios_passed}/{report.pillar41_b_my_menu_camset_vault.scenarios_total} "
                    f"tier0_battery_high_display_violations={report.tier0_battery_high_display_violations} "
                    f"bt_rmt_ir_lockout_violations={report.bt_rmt_ir_lockout_violations} "
                    f"slot1_mymenu_vault_mutation_bytes={report.slot1_mymenu_vault_mutation_bytes} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_41pillar_sha256={report.master_41pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-diff-set-still-mv-custom-key-remain-shoot-vault':
            report = run_pillar42_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar42-diff-set-still-mv-custom-key-remain-shoot-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_42a={report.pillar_42a_diff_set_still_mv_vault.scenarios_passed}/{report.pillar_42a_diff_set_still_mv_vault.scenarios_total} "
                    f"pillar_42b={report.pillar_42b_custom_key_remain_shoot_vault.scenarios_passed}/{report.pillar_42b_custom_key_remain_shoot_vault.scenarios_total} "
                    f"diff_set_transition_corruption_events={report.diff_set_transition_corruption_events} "
                    f"shutter_angle_common_bleed_events={report.shutter_angle_common_bleed_events} "
                    f"slot1_custom_key_vault_mutation_bytes={report.slot1_custom_key_vault_mutation_bytes} "
                    f"fx3_has_builtin_evf={report.fx3_has_builtin_evf} "
                    f"evf_finder_monitor_spoof_events={report.evf_finder_monitor_spoof_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-42pillar-recovery':
            report = verify_42pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'42pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar42_a={report.pillar42_a_diff_set_still_mv_vault.scenarios_passed}/{report.pillar42_a_diff_set_still_mv_vault.scenarios_total} "
                    f"pillar42_b={report.pillar42_b_custom_key_remain_shoot_vault.scenarios_passed}/{report.pillar42_b_custom_key_remain_shoot_vault.scenarios_total} "
                    f"diff_set_transition_corruption_events={report.diff_set_transition_corruption_events} "
                    f"shutter_angle_common_bleed_events={report.shutter_angle_common_bleed_events} "
                    f"slot1_custom_key_vault_mutation_bytes={report.slot1_custom_key_vault_mutation_bytes} "
                    f"fx3_has_builtin_evf={report.fx3_has_builtin_evf} "
                    f"evf_finder_monitor_spoof_events={report.evf_finder_monitor_spoof_events} "
                    f"tier0_battery_high_display_violations={report.tier0_battery_high_display_violations} "
                    f"bt_rmt_ir_lockout_violations={report.bt_rmt_ir_lockout_violations} "
                    f"slot1_mymenu_vault_mutation_bytes={report.slot1_mymenu_vault_mutation_bytes} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_42pillar_sha256={report.master_42pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault':
            report = run_pillar43_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar43-auto-slow-shutter-hdmi-reccontrol-breathing-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_43a={report.pillar_43a_auto_slow_shutter_breathing_vault.scenarios_passed}/{report.pillar_43a_auto_slow_shutter_breathing_vault.scenarios_total} "
                    f"pillar_43b={report.pillar_43b_hdmi_reccontrol_4chaudio_vault.scenarios_passed}/{report.pillar_43b_hdmi_reccontrol_4chaudio_vault.scenarios_total} "
                    f"auto_slow_shutter_lockout_bypass_events={report.auto_slow_shutter_lockout_bypass_events} "
                    f"auto_slow_shutter_angle_overlap_events={report.auto_slow_shutter_angle_overlap_events} "
                    f"breathing_comp_raw_or_240p_bypass_events={report.breathing_comp_raw_or_240p_bypass_events} "
                    f"hdmi_rec_ctrl_without_tc_violations={report.hdmi_rec_ctrl_without_tc_violations} "
                    f"slot1_hdmi_rec_vault_mutation_bytes={report.slot1_hdmi_rec_vault_mutation_bytes} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-43pillar-recovery':
            report = verify_43pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'43pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar43_a={report.pillar43_a_auto_slow_shutter_breathing_vault.scenarios_passed}/{report.pillar43_a_auto_slow_shutter_breathing_vault.scenarios_total} "
                    f"pillar43_b={report.pillar43_b_hdmi_reccontrol_4chaudio_vault.scenarios_passed}/{report.pillar43_b_hdmi_reccontrol_4chaudio_vault.scenarios_total} "
                    f"auto_slow_shutter_lockout_bypass_events={report.auto_slow_shutter_lockout_bypass_events} "
                    f"auto_slow_shutter_angle_overlap_events={report.auto_slow_shutter_angle_overlap_events} "
                    f"breathing_comp_raw_or_240p_bypass_events={report.breathing_comp_raw_or_240p_bypass_events} "
                    f"hdmi_rec_ctrl_without_tc_violations={report.hdmi_rec_ctrl_without_tc_violations} "
                    f"slot1_hdmi_rec_vault_mutation_bytes={report.slot1_hdmi_rec_vault_mutation_bytes} "
                    f"diff_set_transition_corruption_events={report.diff_set_transition_corruption_events} "
                    f"shutter_angle_common_bleed_events={report.shutter_angle_common_bleed_events} "
                    f"slot1_custom_key_vault_mutation_bytes={report.slot1_custom_key_vault_mutation_bytes} "
                    f"fx3_has_builtin_evf={report.fx3_has_builtin_evf} "
                    f"evf_finder_monitor_spoof_events={report.evf_finder_monitor_spoof_events} "
                    f"tier0_battery_high_display_violations={report.tier0_battery_high_display_violations} "
                    f"bt_rmt_ir_lockout_violations={report.bt_rmt_ir_lockout_violations} "
                    f"slot1_mymenu_vault_mutation_bytes={report.slot1_mymenu_vault_mutation_bytes} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_43pillar_sha256={report.master_43pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-apsc-s35-face-eye-af-version-vault':
            report = run_pillar44_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar44-apsc-s35-face-eye-af-version-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_44a={report.pillar_44a_apsc_s35_face_eye_af_vault.scenarios_passed}/{report.pillar_44a_apsc_s35_face_eye_af_vault.scenarios_total} "
                    f"pillar_44b={report.pillar_44b_version_readonly_bodydata_vault.scenarios_passed}/{report.pillar_44b_version_readonly_bodydata_vault.scenarios_total} "
                    f"apsc_s35_4k_or_raw_bypass_events={report.apsc_s35_4k_or_raw_bypass_events} "
                    f"ai_unit_subject_recog_spoof_events={report.ai_unit_subject_recog_spoof_events} "
                    f"hdmi_clean_feed_eye_frame_baked_pixels={report.hdmi_clean_feed_eye_frame_baked_pixels} "
                    f"version_dialog_flash_writes={report.version_dialog_flash_writes} "
                    f"bodydata_flash_attempts_blocked={report.bodydata_flash_attempts_blocked} "
                    f"slot1_bodydata_vault_mutation_bytes={report.slot1_bodydata_vault_mutation_bytes} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-44pillar-recovery':
            report = verify_44pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'44pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar44_a={report.pillar44_a_apsc_s35_face_eye_af_vault.scenarios_passed}/{report.pillar44_a_apsc_s35_face_eye_af_vault.scenarios_total} "
                    f"pillar44_b={report.pillar44_b_version_readonly_bodydata_vault.scenarios_passed}/{report.pillar44_b_version_readonly_bodydata_vault.scenarios_total} "
                    f"apsc_s35_4k_or_raw_bypass_events={report.apsc_s35_4k_or_raw_bypass_events} "
                    f"ai_unit_subject_recog_spoof_events={report.ai_unit_subject_recog_spoof_events} "
                    f"hdmi_clean_feed_eye_frame_baked_pixels={report.hdmi_clean_feed_eye_frame_baked_pixels} "
                    f"version_dialog_flash_writes={report.version_dialog_flash_writes} "
                    f"bodydata_flash_attempts_blocked={report.bodydata_flash_attempts_blocked} "
                    f"slot1_bodydata_vault_mutation_bytes={report.slot1_bodydata_vault_mutation_bytes} "
                    f"auto_slow_shutter_lockout_bypass_events={report.auto_slow_shutter_lockout_bypass_events} "
                    f"auto_slow_shutter_angle_overlap_events={report.auto_slow_shutter_angle_overlap_events} "
                    f"breathing_comp_raw_or_240p_bypass_events={report.breathing_comp_raw_or_240p_bypass_events} "
                    f"hdmi_rec_ctrl_without_tc_violations={report.hdmi_rec_ctrl_without_tc_violations} "
                    f"slot1_hdmi_rec_vault_mutation_bytes={report.slot1_hdmi_rec_vault_mutation_bytes} "
                    f"diff_set_transition_corruption_events={report.diff_set_transition_corruption_events} "
                    f"shutter_angle_common_bleed_events={report.shutter_angle_common_bleed_events} "
                    f"slot1_custom_key_vault_mutation_bytes={report.slot1_custom_key_vault_mutation_bytes} "
                    f"fx3_has_builtin_evf={report.fx3_has_builtin_evf} "
                    f"evf_finder_monitor_spoof_events={report.evf_finder_monitor_spoof_events} "
                    f"tier0_battery_high_display_violations={report.tier0_battery_high_display_violations} "
                    f"bt_rmt_ir_lockout_violations={report.bt_rmt_ir_lockout_violations} "
                    f"slot1_mymenu_vault_mutation_bytes={report.slot1_mymenu_vault_mutation_bytes} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_44pillar_sha256={report.master_44pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-release-wo-card-lens-audio-meter-copyright-vault':
            report = run_pillar45_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar45-release-wo-card-lens-audio-meter-copyright-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_45a={report.pillar_45a_release_wo_card_lens_audio_meter_vault.scenarios_passed}/{report.pillar_45a_release_wo_card_lens_audio_meter_vault.scenarios_total} "
                    f"pillar_45b={report.pillar_45b_copyright_info_46char_exif_vault.scenarios_passed}/{report.pillar_45b_copyright_info_46char_exif_vault.scenarios_total} "
                    f"fx3_has_builtin_end_filter={report.fx3_has_builtin_end_filter} "
                    f"e_nd_actuator_tx_count={report.e_nd_actuator_tx_count} "
                    f"cardless_unrecorded_production_violations={report.cardless_unrecorded_production_violations} "
                    f"legacy_v1_audio_level_menu_spoof_events={report.legacy_v1_audio_level_menu_spoof_events} "
                    f"photographer_copyright_pii_leaked_bytes={report.photographer_copyright_pii_leaked_bytes} "
                    f"copyright_char_overflow_or_movie_mutation_events={report.copyright_char_overflow_or_movie_mutation_events} "
                    f"slot1_copyright_vault_mutation_bytes={report.slot1_copyright_vault_mutation_bytes} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-45pillar-recovery':
            report = verify_45pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'45pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_2s_fast_cli_budget={report.under_2s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar45_a={report.pillar45_a_release_wo_card_lens_audio_meter_vault.scenarios_passed}/{report.pillar45_a_release_wo_card_lens_audio_meter_vault.scenarios_total} "
                    f"pillar45_b={report.pillar45_b_copyright_info_46char_exif_vault.scenarios_passed}/{report.pillar45_b_copyright_info_46char_exif_vault.scenarios_total} "
                    f"fx3_has_builtin_end_filter={report.fx3_has_builtin_end_filter} "
                    f"e_nd_actuator_tx_count={report.e_nd_actuator_tx_count} "
                    f"cardless_unrecorded_production_violations={report.cardless_unrecorded_production_violations} "
                    f"legacy_v1_audio_level_menu_spoof_events={report.legacy_v1_audio_level_menu_spoof_events} "
                    f"photographer_copyright_pii_leaked_bytes={report.photographer_copyright_pii_leaked_bytes} "
                    f"copyright_char_overflow_or_movie_mutation_events={report.copyright_char_overflow_or_movie_mutation_events} "
                    f"slot1_copyright_vault_mutation_bytes={report.slot1_copyright_vault_mutation_bytes} "
                    f"apsc_s35_4k_or_raw_bypass_events={report.apsc_s35_4k_or_raw_bypass_events} "
                    f"ai_unit_subject_recog_spoof_events={report.ai_unit_subject_recog_spoof_events} "
                    f"hdmi_clean_feed_eye_frame_baked_pixels={report.hdmi_clean_feed_eye_frame_baked_pixels} "
                    f"version_dialog_flash_writes={report.version_dialog_flash_writes} "
                    f"bodydata_flash_attempts_blocked={report.bodydata_flash_attempts_blocked} "
                    f"slot1_bodydata_vault_mutation_bytes={report.slot1_bodydata_vault_mutation_bytes} "
                    f"auto_slow_shutter_lockout_bypass_events={report.auto_slow_shutter_lockout_bypass_events} "
                    f"auto_slow_shutter_angle_overlap_events={report.auto_slow_shutter_angle_overlap_events} "
                    f"breathing_comp_raw_or_240p_bypass_events={report.breathing_comp_raw_or_240p_bypass_events} "
                    f"hdmi_rec_ctrl_without_tc_violations={report.hdmi_rec_ctrl_without_tc_violations} "
                    f"slot1_hdmi_rec_vault_mutation_bytes={report.slot1_hdmi_rec_vault_mutation_bytes} "
                    f"diff_set_transition_corruption_events={report.diff_set_transition_corruption_events} "
                    f"shutter_angle_common_bleed_events={report.shutter_angle_common_bleed_events} "
                    f"slot1_custom_key_vault_mutation_bytes={report.slot1_custom_key_vault_mutation_bytes} "
                    f"fx3_has_builtin_evf={report.fx3_has_builtin_evf} "
                    f"evf_finder_monitor_spoof_events={report.evf_finder_monitor_spoof_events} "
                    f"tier0_battery_high_display_violations={report.tier0_battery_high_display_violations} "
                    f"bt_rmt_ir_lockout_violations={report.bt_rmt_ir_lockout_violations} "
                    f"slot1_mymenu_vault_mutation_bytes={report.slot1_mymenu_vault_mutation_bytes} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_45pillar_sha256={report.master_45pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-file-settings-gamma-assist-tcub-vault':
            report = run_pillar46_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar46-file-settings-gamma-assist-tcub-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_46a={report.pillar_46a_file_settings_still_folder_vault.scenarios_passed}/{report.pillar_46a_file_settings_still_folder_vault.scenarios_total} "
                    f"pillar_46b={report.pillar_46b_gamma_assist_lut_auto_review_tcub_vault.scenarios_passed}/{report.pillar_46b_gamma_assist_lut_auto_review_tcub_vault.scenarios_total} "
                    f"slot1_vault_folder_mutation_events={report.slot1_vault_folder_mutation_events} "
                    f"slot1_vault_folder_mutation_bytes={report.slot1_vault_folder_mutation_bytes} "
                    f"movie_custom_folder_or_title_overflow_events={report.movie_custom_folder_or_title_overflow_events} "
                    f"still_prefix_underscore_lead_or_len_violations={report.still_prefix_underscore_lead_or_len_violations} "
                    f"gamma_assist_log_lockout_bypass_events={report.gamma_assist_log_lockout_bypass_events} "
                    f"gamma_assist_external_hdmi_leak_events={report.gamma_assist_external_hdmi_leak_events} "
                    f"tcub_camera_reset_wipe_or_format_violations={report.tcub_camera_reset_wipe_or_format_violations} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-46pillar-recovery':
            report = verify_46pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'46pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_2s_fast_cli_budget={report.under_2s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar46_a={report.pillar46_a_file_settings_still_folder_vault.scenarios_passed}/{report.pillar46_a_file_settings_still_folder_vault.scenarios_total} "
                    f"pillar46_b={report.pillar46_b_gamma_assist_lut_auto_review_tcub_vault.scenarios_passed}/{report.pillar46_b_gamma_assist_lut_auto_review_tcub_vault.scenarios_total} "
                    f"slot1_vault_folder_mutation_events={report.slot1_vault_folder_mutation_events} "
                    f"slot1_vault_folder_mutation_bytes={report.slot1_vault_folder_mutation_bytes} "
                    f"movie_custom_folder_or_title_overflow_events={report.movie_custom_folder_or_title_overflow_events} "
                    f"still_prefix_underscore_lead_or_len_violations={report.still_prefix_underscore_lead_or_len_violations} "
                    f"gamma_assist_log_lockout_bypass_events={report.gamma_assist_log_lockout_bypass_events} "
                    f"gamma_assist_external_hdmi_leak_events={report.gamma_assist_external_hdmi_leak_events} "
                    f"tcub_camera_reset_wipe_or_format_violations={report.tcub_camera_reset_wipe_or_format_violations} "
                    f"fx3_has_builtin_end_filter={report.fx3_has_builtin_end_filter} "
                    f"e_nd_actuator_tx_count={report.e_nd_actuator_tx_count} "
                    f"cardless_unrecorded_production_violations={report.cardless_unrecorded_production_violations} "
                    f"legacy_v1_audio_level_menu_spoof_events={report.legacy_v1_audio_level_menu_spoof_events} "
                    f"photographer_copyright_pii_leaked_bytes={report.photographer_copyright_pii_leaked_bytes} "
                    f"copyright_char_overflow_or_movie_mutation_events={report.copyright_char_overflow_or_movie_mutation_events} "
                    f"slot1_copyright_vault_mutation_bytes={report.slot1_copyright_vault_mutation_bytes} "
                    f"apsc_s35_4k_or_raw_bypass_events={report.apsc_s35_4k_or_raw_bypass_events} "
                    f"ai_unit_subject_recog_spoof_events={report.ai_unit_subject_recog_spoof_events} "
                    f"hdmi_clean_feed_eye_frame_baked_pixels={report.hdmi_clean_feed_eye_frame_baked_pixels} "
                    f"version_dialog_flash_writes={report.version_dialog_flash_writes} "
                    f"bodydata_flash_attempts_blocked={report.bodydata_flash_attempts_blocked} "
                    f"slot1_bodydata_vault_mutation_bytes={report.slot1_bodydata_vault_mutation_bytes} "
                    f"auto_slow_shutter_lockout_bypass_events={report.auto_slow_shutter_lockout_bypass_events} "
                    f"auto_slow_shutter_angle_overlap_events={report.auto_slow_shutter_angle_overlap_events} "
                    f"breathing_comp_raw_or_240p_bypass_events={report.breathing_comp_raw_or_240p_bypass_events} "
                    f"hdmi_rec_ctrl_without_tc_violations={report.hdmi_rec_ctrl_without_tc_violations} "
                    f"slot1_hdmi_rec_vault_mutation_bytes={report.slot1_hdmi_rec_vault_mutation_bytes} "
                    f"diff_set_transition_corruption_events={report.diff_set_transition_corruption_events} "
                    f"shutter_angle_common_bleed_events={report.shutter_angle_common_bleed_events} "
                    f"slot1_custom_key_vault_mutation_bytes={report.slot1_custom_key_vault_mutation_bytes} "
                    f"fx3_has_builtin_evf={report.fx3_has_builtin_evf} "
                    f"evf_finder_monitor_spoof_events={report.evf_finder_monitor_spoof_events} "
                    f"tier0_battery_high_display_violations={report.tier0_battery_high_display_violations} "
                    f"bt_rmt_ir_lockout_violations={report.bt_rmt_ir_lockout_violations} "
                    f"slot1_mymenu_vault_mutation_bytes={report.slot1_mymenu_vault_mutation_bytes} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_46pillar_sha256={report.master_46pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-focus-mag-datetime-videolight-hdmires-vault':
            report = run_pillar47_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar47-focus-mag-datetime-videolight-hdmires-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_47a={report.pillar_47a_focus_mag_peaking_still_af_illuminator_vault.scenarios_passed}/{report.pillar_47a_focus_mag_peaking_still_af_illuminator_vault.scenarios_total} "
                    f"pillar_47b={report.pillar_47b_area_datetime_videolight_hdmires_vault.scenarios_passed}/{report.pillar_47b_area_datetime_videolight_hdmires_vault.scenarios_total} "
                    f"legacy_mf_assist_spoof_events={report.legacy_mf_assist_spoof_events} "
                    f"still_movie_initial_mag_couplings={report.still_movie_initial_mag_couplings} "
                    f"movie_af_in_focus_mag_events={report.movie_af_in_focus_mag_events} "
                    f"hdmi_clean_feed_focus_mag_or_peaking_leak_pixels={report.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels} "
                    f"movie_sq_af_illuminator_fire_events={report.movie_sq_af_illuminator_fire_events} "
                    f"legacy_datetime_setup_spoof_events={report.legacy_datetime_setup_spoof_events} "
                    f"unsolicited_rtc_timezone_jump_events={report.unsolicited_rtc_timezone_jump_events} "
                    f"mishoe_5v_overcurrent_events={report.mishoe_5v_overcurrent_events} "
                    f"hdmi_res_log_internal_rec_2160p_bypass_events={report.hdmi_res_log_internal_rec_2160p_bypass_events} "
                    f"slot1_vault_mutation_events={report.slot1_vault_mutation_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-47pillar-recovery':
            report = verify_47pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'47pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_2s_fast_cli_budget={report.under_2s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar47_a={report.pillar47_a_focus_mag_peaking_still_af_illuminator_vault.scenarios_passed}/{report.pillar47_a_focus_mag_peaking_still_af_illuminator_vault.scenarios_total} "
                    f"pillar47_b={report.pillar47_b_area_datetime_videolight_hdmires_vault.scenarios_passed}/{report.pillar47_b_area_datetime_videolight_hdmires_vault.scenarios_total} "
                    f"legacy_mf_assist_spoof_events={report.legacy_mf_assist_spoof_events} "
                    f"still_movie_initial_mag_couplings={report.still_movie_initial_mag_couplings} "
                    f"movie_af_in_focus_mag_events={report.movie_af_in_focus_mag_events} "
                    f"hdmi_clean_feed_focus_mag_or_peaking_leak_pixels={report.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels} "
                    f"movie_sq_af_illuminator_fire_events={report.movie_sq_af_illuminator_fire_events} "
                    f"legacy_datetime_setup_spoof_events={report.legacy_datetime_setup_spoof_events} "
                    f"unsolicited_rtc_timezone_jump_events={report.unsolicited_rtc_timezone_jump_events} "
                    f"mishoe_5v_overcurrent_events={report.mishoe_5v_overcurrent_events} "
                    f"hdmi_res_log_internal_rec_2160p_bypass_events={report.hdmi_res_log_internal_rec_2160p_bypass_events} "
                    f"slot1_vault_mutation_events={report.slot1_vault_mutation_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_vault_folder_mutation_events={report.slot1_vault_folder_mutation_events} "
                    f"slot1_vault_folder_mutation_bytes={report.slot1_vault_folder_mutation_bytes} "
                    f"movie_custom_folder_or_title_overflow_events={report.movie_custom_folder_or_title_overflow_events} "
                    f"still_prefix_underscore_lead_or_len_violations={report.still_prefix_underscore_lead_or_len_violations} "
                    f"gamma_assist_log_lockout_bypass_events={report.gamma_assist_log_lockout_bypass_events} "
                    f"gamma_assist_external_hdmi_leak_events={report.gamma_assist_external_hdmi_leak_events} "
                    f"tcub_camera_reset_wipe_or_format_violations={report.tcub_camera_reset_wipe_or_format_violations} "
                    f"fx3_has_builtin_end_filter={report.fx3_has_builtin_end_filter} "
                    f"e_nd_actuator_tx_count={report.e_nd_actuator_tx_count} "
                    f"cardless_unrecorded_production_violations={report.cardless_unrecorded_production_violations} "
                    f"legacy_v1_audio_level_menu_spoof_events={report.legacy_v1_audio_level_menu_spoof_events} "
                    f"photographer_copyright_pii_leaked_bytes={report.photographer_copyright_pii_leaked_bytes} "
                    f"copyright_char_overflow_or_movie_mutation_events={report.copyright_char_overflow_or_movie_mutation_events} "
                    f"slot1_copyright_vault_mutation_bytes={report.slot1_copyright_vault_mutation_bytes} "
                    f"apsc_s35_4k_or_raw_bypass_events={report.apsc_s35_4k_or_raw_bypass_events} "
                    f"ai_unit_subject_recog_spoof_events={report.ai_unit_subject_recog_spoof_events} "
                    f"hdmi_clean_feed_eye_frame_baked_pixels={report.hdmi_clean_feed_eye_frame_baked_pixels} "
                    f"version_dialog_flash_writes={report.version_dialog_flash_writes} "
                    f"bodydata_flash_attempts_blocked={report.bodydata_flash_attempts_blocked} "
                    f"slot1_bodydata_vault_mutation_bytes={report.slot1_bodydata_vault_mutation_bytes} "
                    f"auto_slow_shutter_lockout_bypass_events={report.auto_slow_shutter_lockout_bypass_events} "
                    f"auto_slow_shutter_angle_overlap_events={report.auto_slow_shutter_angle_overlap_events} "
                    f"breathing_comp_raw_or_240p_bypass_events={report.breathing_comp_raw_or_240p_bypass_events} "
                    f"hdmi_rec_ctrl_without_tc_violations={report.hdmi_rec_ctrl_without_tc_violations} "
                    f"slot1_hdmi_rec_vault_mutation_bytes={report.slot1_hdmi_rec_vault_mutation_bytes} "
                    f"diff_set_transition_corruption_events={report.diff_set_transition_corruption_events} "
                    f"shutter_angle_common_bleed_events={report.shutter_angle_common_bleed_events} "
                    f"slot1_custom_key_vault_mutation_bytes={report.slot1_custom_key_vault_mutation_bytes} "
                    f"fx3_has_builtin_evf={report.fx3_has_builtin_evf} "
                    f"evf_finder_monitor_spoof_events={report.evf_finder_monitor_spoof_events} "
                    f"tier0_battery_high_display_violations={report.tier0_battery_high_display_violations} "
                    f"bt_rmt_ir_lockout_violations={report.bt_rmt_ir_lockout_violations} "
                    f"slot1_mymenu_vault_mutation_bytes={report.slot1_mymenu_vault_mutation_bytes} "
                    f"destructive_menu_delete_confusions={report.destructive_menu_delete_confusions} "
                    f"shutter_angle_exposure_step_drift_events={report.shutter_angle_exposure_step_drift_events} "
                    f"fx3_has_var_shutter={report.fx3_has_var_shutter} "
                    f"unbuffered_battery_pull_events={report.unbuffered_battery_pull_events} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_47pillar_sha256={report.master_47pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-power-save-monitor-language-volume-delete-vault':
            report = run_pillar48_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar48-power-save-monitor-language-volume-delete-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_48a={report.pillar_48a_power_save_monitor_language_vault.scenarios_passed}/{report.pillar_48a_power_save_monitor_language_vault.scenarios_total} "
                    f"pillar_48b={report.pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault.scenarios_passed}/{report.pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault.scenarios_total} "
                    f"fx3_ui_exposes_power_save_by_monitor={report.fx3_ui_exposes_power_save_by_monitor} "
                    f"legacy_power_save_monitor_spoof_events={report.legacy_power_save_monitor_spoof_events} "
                    f"unsafe_power_save_sleep_interference_events={report.unsafe_power_save_sleep_interference_events} "
                    f"bk_lang_parity_drift_events={report.bk_lang_parity_drift_events} "
                    f"stage_b_4lang_uxc_ltt_drift_events={report.stage_b_4lang_uxc_ltt_drift_events} "
                    f"xlrh1_acoustic_feedback_violations={report.xlrh1_acoustic_feedback_violations} "
                    f"audio_mon_4ch_hdmi_confusion_events={report.audio_mon_4ch_hdmi_confusion_events} "
                    f"destructive_delete_confirm_drift_events={report.destructive_delete_confirm_drift_events} "
                    f"slot1_vault_delete_events={report.slot1_vault_delete_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-48pillar-recovery':
            report = verify_48pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'48pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_2s_fast_cli_budget={report.under_2s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar48_a={report.pillar48_a_power_save_monitor_language_vault.scenarios_passed}/{report.pillar48_a_power_save_monitor_language_vault.scenarios_total} "
                    f"pillar48_b={report.pillar48_b_volume_4ch_mon_delete_confirm_slot1_vault.scenarios_passed}/{report.pillar48_b_volume_4ch_mon_delete_confirm_slot1_vault.scenarios_total} "
                    f"fx3_ui_exposes_power_save_by_monitor={report.fx3_ui_exposes_power_save_by_monitor} "
                    f"legacy_power_save_monitor_spoof_events={report.legacy_power_save_monitor_spoof_events} "
                    f"unsafe_power_save_sleep_interference_events={report.unsafe_power_save_sleep_interference_events} "
                    f"bk_lang_parity_drift_events={report.bk_lang_parity_drift_events} "
                    f"stage_b_4lang_uxc_ltt_drift_events={report.stage_b_4lang_uxc_ltt_drift_events} "
                    f"xlrh1_acoustic_feedback_violations={report.xlrh1_acoustic_feedback_violations} "
                    f"audio_mon_4ch_hdmi_confusion_events={report.audio_mon_4ch_hdmi_confusion_events} "
                    f"destructive_delete_confirm_drift_events={report.destructive_delete_confirm_drift_events} "
                    f"slot1_vault_delete_events={report.slot1_vault_delete_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_48pillar_sha256={report.master_48pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-usb-mode-hdmi-info-protect-network-reset-vault':
            report = run_pillar49_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar49-usb-mode-hdmi-info-protect-network-reset-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_49a={report.pillar_49a_usb_mode_pd_hdmi_info_vault.scenarios_passed}/{report.pillar_49a_usb_mode_pd_hdmi_info_vault.scenarios_total} "
                    f"pillar_49b={report.pillar_49b_protect_format_network_reset_vault.scenarios_passed}/{report.pillar_49b_protect_format_network_reset_vault.scenarios_total} "
                    f"fx3_ui_exposes_usb_streaming={report.fx3_ui_exposes_usb_streaming} "
                    f"nouvc_spoof_events={report.nouvc_spoof_events} "
                    f"usb_host_data_enumeration_events={report.usb_host_data_enumeration_events} "
                    f"hdmi_lcd_blanking_violations={report.hdmi_lcd_blanking_violations} "
                    f"hdmi_log_1080_bypass_events={report.hdmi_log_1080_bypass_events} "
                    f"slot1_protect_only_vault_violations={report.slot1_protect_only_vault_violations} "
                    f"slot1_vault_format_or_delete_events={report.slot1_vault_format_or_delete_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"network_reset_zero_rf_violations={report.network_reset_zero_rf_violations} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-49pillar-recovery':
            report = verify_49pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'49pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_2s_fast_cli_budget={report.under_2s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar49_a={report.pillar49_a_usb_mode_pd_hdmi_info_vault.scenarios_passed}/{report.pillar49_a_usb_mode_pd_hdmi_info_vault.scenarios_total} "
                    f"pillar49_b={report.pillar49_b_protect_format_network_reset_vault.scenarios_passed}/{report.pillar49_b_protect_format_network_reset_vault.scenarios_total} "
                    f"fx3_ui_exposes_usb_streaming={report.fx3_ui_exposes_usb_streaming} "
                    f"nouvc_spoof_events={report.nouvc_spoof_events} "
                    f"usb_host_data_enumeration_events={report.usb_host_data_enumeration_events} "
                    f"hdmi_lcd_blanking_violations={report.hdmi_lcd_blanking_violations} "
                    f"hdmi_log_1080_bypass_events={report.hdmi_log_1080_bypass_events} "
                    f"slot1_protect_only_vault_violations={report.slot1_protect_only_vault_violations} "
                    f"slot1_vault_format_or_delete_events={report.slot1_vault_format_or_delete_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"network_reset_zero_rf_violations={report.network_reset_zero_rf_violations} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_49pillar_sha256={report.master_49pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pp-scinetone-wb-metering-vault':
            report = run_pillar50_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar50-pp-scinetone-wb-metering-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_50a={report.pillar_50a_pp_scinetone_creativelook_dro_vault.scenarios_passed}/{report.pillar_50a_pp_scinetone_creativelook_dro_vault.scenarios_total} "
                    f"pillar_50b={report.pillar_50b_wb_camset_exclusion_metering_vault.scenarios_passed}/{report.pillar_50b_wb_camset_exclusion_metering_vault.scenarios_total} "
                    f"double_log_or_lockout_bypass_events={report.double_log_or_lockout_bypass_events} "
                    f"pplut_1080p_clamp_bypass_events={report.pplut_1080p_clamp_bypass_events} "
                    f"pp_internal_reset_trap_violations={report.pp_internal_reset_trap_violations} "
                    f"fx6_baselook_confusion_events={report.fx6_baselook_confusion_events} "
                    f"wb_cine_ei_awb_or_custom_setup_trap_events={report.wb_cine_ei_awb_or_custom_setup_trap_events} "
                    f"wb_custom_camset_exclusion_drift_events={report.wb_custom_camset_exclusion_drift_events} "
                    f"metering_desqueeze_or_cine_ei_base_iso_drift_events={report.metering_desqueeze_or_cine_ei_base_iso_drift_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-50pillar-recovery':
            report = verify_50pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'50pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_2_2s_fast_cli_budget={report.under_2_2s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar50_a={report.pillar50_a_pp_scinetone_creativelook_dro_vault.scenarios_passed}/{report.pillar50_a_pp_scinetone_creativelook_dro_vault.scenarios_total} "
                    f"pillar50_b={report.pillar50_b_wb_camset_exclusion_metering_vault.scenarios_passed}/{report.pillar50_b_wb_camset_exclusion_metering_vault.scenarios_total} "
                    f"double_log_or_lockout_bypass_events={report.double_log_or_lockout_bypass_events} "
                    f"pplut_1080p_clamp_bypass_events={report.pplut_1080p_clamp_bypass_events} "
                    f"pp_internal_reset_trap_violations={report.pp_internal_reset_trap_violations} "
                    f"fx6_baselook_confusion_events={report.fx6_baselook_confusion_events} "
                    f"wb_cine_ei_awb_or_custom_setup_trap_events={report.wb_cine_ei_awb_or_custom_setup_trap_events} "
                    f"wb_custom_camset_exclusion_drift_events={report.wb_custom_camset_exclusion_drift_events} "
                    f"metering_desqueeze_or_cine_ei_base_iso_drift_events={report.metering_desqueeze_or_cine_ei_base_iso_drift_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_50pillar_sha256={report.master_50pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pillar51-raw-heif-colorspace-shuttertype-vault':
            report = run_pillar51_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar51-raw-heif-colorspace-shuttertype-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_51a={report.pillar_51a_raw_heif_hlg_colorspace_vault.scenarios_passed}/{report.pillar_51a_raw_heif_hlg_colorspace_vault.scenarios_total} "
                    f"pillar_51b={report.pillar_51b_shuttertype_nr_drive_vault.scenarios_passed}/{report.pillar_51b_shuttertype_nr_drive_vault.scenarios_total} "
                    f"dormant_lossless_raw_exposure_events={report.dormant_lossless_raw_exposure_events} "
                    f"fx6_still_pipeline_conflation_events={report.fx6_still_pipeline_conflation_events} "
                    f"hlg_still_prereq_or_lockout_drift_events={report.hlg_still_prereq_or_lockout_drift_events} "
                    f"colorspace_adobergb_prefix_violations={report.colorspace_adobergb_prefix_violations} "
                    f"shutter_type_auto_spoof_events={report.shutter_type_auto_spoof_events} "
                    f"fx6_mechanical_shutter_conflation_events={report.fx6_mechanical_shutter_conflation_events} "
                    f"electronic_silent_5lock_bypass_events={report.electronic_silent_5lock_bypass_events} "
                    f"nr_or_drive_burst_wall_violations={report.nr_or_drive_burst_wall_violations} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-51pillar-recovery':
            report = verify_51pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'51pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_2s_fast_cli_budget={report.under_1_2s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar51_a={report.pillar51_a_raw_heif_hlg_colorspace_vault.scenarios_passed}/{report.pillar51_a_raw_heif_hlg_colorspace_vault.scenarios_total} "
                    f"pillar51_b={report.pillar51_b_shuttertype_nr_drive_vault.scenarios_passed}/{report.pillar51_b_shuttertype_nr_drive_vault.scenarios_total} "
                    f"dormant_lossless_raw_exposure_events={report.dormant_lossless_raw_exposure_events} "
                    f"fx6_still_pipeline_conflation_events={report.fx6_still_pipeline_conflation_events} "
                    f"hlg_still_prereq_or_lockout_drift_events={report.hlg_still_prereq_or_lockout_drift_events} "
                    f"colorspace_adobergb_prefix_violations={report.colorspace_adobergb_prefix_violations} "
                    f"shutter_type_auto_spoof_events={report.shutter_type_auto_spoof_events} "
                    f"fx6_mechanical_shutter_conflation_events={report.fx6_mechanical_shutter_conflation_events} "
                    f"electronic_silent_5lock_bypass_events={report.electronic_silent_5lock_bypass_events} "
                    f"nr_or_drive_burst_wall_violations={report.nr_or_drive_burst_wall_violations} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_51pillar_sha256={report.master_51pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pillar52-focus-area-zoom-iso-flash-vault':
            report = run_pillar52_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'pillar52-focus-area-zoom-iso-flash-vault-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_52a={report.pillar_52a_focus_area_zoom_xlrh1_vault.scenarios_passed}/{report.pillar_52a_focus_area_zoom_xlrh1_vault.scenarios_total} "
                    f"pillar_52b={report.pillar_52b_iso_minss_flash_videolight_vault.scenarios_passed}/{report.pillar_52b_iso_minss_flash_videolight_vault.scenarios_total} "
                    f"movie_tracking_area_or_limit_violations={report.movie_tracking_area_or_limit_violations} "
                    f"af_area_reg_lock_or_reset_drift_events={report.af_area_reg_lock_or_reset_drift_events} "
                    f"xlrh1_zoom_or_hold_spoof_events={report.xlrh1_zoom_or_hold_spoof_events} "
                    f"fx6_handle_or_pos_display_conflation_events={report.fx6_handle_or_pos_display_conflation_events} "
                    f"iso_minss_or_cine_ei_lock_drift_events={report.iso_minss_or_cine_ei_lock_drift_events} "
                    f"flash_still_mech_gate_violations={report.flash_still_mech_gate_violations} "
                    f"mishoe_5v_overcurrent_events={report.mishoe_5v_overcurrent_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-52pillar-recovery':
            report = verify_52pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'52pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_2s_fast_cli_budget={report.under_1_2s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar52_a={report.pillar52_a_focus_area_zoom_xlrh1_vault.scenarios_passed}/{report.pillar52_a_focus_area_zoom_xlrh1_vault.scenarios_total} "
                    f"pillar52_b={report.pillar52_b_iso_minss_flash_videolight_vault.scenarios_passed}/{report.pillar52_b_iso_minss_flash_videolight_vault.scenarios_total} "
                    f"movie_tracking_area_or_limit_violations={report.movie_tracking_area_or_limit_violations} "
                    f"af_area_reg_lock_or_reset_drift_events={report.af_area_reg_lock_or_reset_drift_events} "
                    f"xlrh1_zoom_or_hold_spoof_events={report.xlrh1_zoom_or_hold_spoof_events} "
                    f"fx6_handle_or_pos_display_conflation_events={report.fx6_handle_or_pos_display_conflation_events} "
                    f"iso_minss_or_cine_ei_lock_drift_events={report.iso_minss_or_cine_ei_lock_drift_events} "
                    f"flash_still_mech_gate_violations={report.flash_still_mech_gate_violations} "
                    f"mishoe_pmic_5v_overcurrent_events={report.mishoe_pmic_5v_overcurrent_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_52pillar_sha256={report.master_52pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pillar53-dci4k-aspect-custom-hold-camset-vault':
            report = run_pillar53_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar53-dci4k-aspect-custom-hold-camset-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_53a={report.pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault.scenarios_passed}/{report.pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault.scenarios_total} "
                    f"pillar_53b={report.pillar_53b_custom_hold_camset_photo_capture_vault.scenarios_passed}/{report.pillar_53b_custom_hold_camset_photo_capture_vault.scenarios_total} "
                    f"dci4k_long_gop_or_8k_violations={report.dci4k_long_gop_or_8k_violations} "
                    f"reboot_2400p_stage_b_wipe_violations={report.reboot_2400p_stage_b_wipe_violations} "
                    f"hdmi_raw_or_still_aspect_drift_events={report.hdmi_raw_or_still_aspect_drift_events} "
                    f"fx6_still_or_raw_conflation_events={report.fx6_still_or_raw_conflation_events} "
                    f"reg_custom_hold_or_hlg_lock_drift_events={report.reg_custom_hold_or_hlg_lock_drift_events} "
                    f"camset_cross_model_path_drift_events={report.camset_cross_model_path_drift_events} "
                    f"photo_capture_dci4k_lockout_bypass_events={report.photo_capture_dci4k_lockout_bypass_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-53pillar-recovery':
            report = verify_53pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'53pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_2s_fast_cli_budget={report.under_1_2s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar53_a={report.pillar53_a_dci4k_2400p_hdmi_raw_aspect_vault.scenarios_passed}/{report.pillar53_a_dci4k_2400p_hdmi_raw_aspect_vault.scenarios_total} "
                    f"pillar53_b={report.pillar53_b_custom_hold_camset_photo_capture_vault.scenarios_passed}/{report.pillar53_b_custom_hold_camset_photo_capture_vault.scenarios_total} "
                    f"dci4k_long_gop_or_8k_violations={report.dci4k_long_gop_or_8k_violations} "
                    f"reboot_2400p_stage_b_wipe_violations={report.reboot_2400p_stage_b_wipe_violations} "
                    f"hdmi_raw_or_still_aspect_drift_events={report.hdmi_raw_or_still_aspect_drift_events} "
                    f"fx6_still_or_raw_conflation_events={report.fx6_still_or_raw_conflation_events} "
                    f"reg_custom_hold_or_hlg_lock_drift_events={report.reg_custom_hold_or_hlg_lock_drift_events} "
                    f"camset_cross_model_path_drift_events={report.camset_cross_model_path_drift_events} "
                    f"photo_capture_dci4k_lockout_bypass_events={report.photo_capture_dci4k_lockout_bypass_events} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_53pillar_sha256={report.master_53pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault':
            report = run_pillar54_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_54a={report.pillar_54a_sensor_cleaning_ev_comp_vault.scenarios_passed}/{report.pillar_54a_sensor_cleaning_ev_comp_vault.scenarios_total} "
                    f"pillar_54b={report.pillar_54b_focus_mode_playback_rotate_vault.scenarios_passed}/{report.pillar_54b_focus_mode_playback_rotate_vault.scenarios_total} "
                    f"sensor_cleaning_low_battery_bypass_events={report.sensor_cleaning_low_battery_bypass_events} "
                    f"sensor_cleaning_no_power_off_violations={report.sensor_cleaning_no_power_off_violations} "
                    f"fx6_ibis_shake_conflation_events={report.fx6_ibis_shake_conflation_events} "
                    f"ev_comp_range_or_cine_ei_lockout_violations={report.ev_comp_range_or_cine_ei_lockout_violations} "
                    f"exposure_step_or_dormant_reset_ev_drift_events={report.exposure_step_or_dormant_reset_ev_drift_events} "
                    f"focus_mode_movie_clamp_or_dormant_drift_events={report.focus_mode_movie_clamp_or_dormant_drift_events} "
                    f"priority_set_or_illuminator_gate_violations={report.priority_set_or_illuminator_gate_violations} "
                    f"image_index_dormant_or_view_mode_drift_events={report.image_index_dormant_or_view_mode_drift_events} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_rotate_exif_mutation_bytes={report.slot1_rotate_exif_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-54pillar-recovery':
            report = verify_54pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'54pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar54_a={report.pillar54_a_sensor_cleaning_ev_comp_vault.scenarios_passed}/{report.pillar54_a_sensor_cleaning_ev_comp_vault.scenarios_total} "
                    f"pillar54_b={report.pillar54_b_focus_mode_playback_rotate_vault.scenarios_passed}/{report.pillar54_b_focus_mode_playback_rotate_vault.scenarios_total} "
                    f"sensor_cleaning_low_battery_bypass_events={report.sensor_cleaning_low_battery_bypass_events} "
                    f"sensor_cleaning_no_power_off_violations={report.sensor_cleaning_no_power_off_violations} "
                    f"fx6_ibis_shake_conflation_events={report.fx6_ibis_shake_conflation_events} "
                    f"ev_comp_range_or_cine_ei_lockout_violations={report.ev_comp_range_or_cine_ei_lockout_violations} "
                    f"exposure_step_or_dormant_reset_ev_drift_events={report.exposure_step_or_dormant_reset_ev_drift_events} "
                    f"focus_mode_movie_clamp_or_dormant_drift_events={report.focus_mode_movie_clamp_or_dormant_drift_events} "
                    f"priority_set_or_illuminator_gate_violations={report.priority_set_or_illuminator_gate_violations} "
                    f"image_index_dormant_or_view_mode_drift_events={report.image_index_dormant_or_view_mode_drift_events} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_rotate_exif_mutation_bytes={report.slot1_rotate_exif_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_54pillar_sha256={report.master_54pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pillar55-lens-comp-af-illuminator-folder-rating-vault':
            report = run_pillar55_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar55-lens-comp-af-illuminator-folder-rating-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_55a={report.pillar_55a_lens_comp_af_illuminator_vault.scenarios_passed}/{report.pillar_55a_lens_comp_af_illuminator_vault.scenarios_total} "
                    f"pillar_55b={report.pillar_55b_aperture_drive_folder_rating_vault.scenarios_passed}/{report.pillar_55b_aperture_drive_folder_rating_vault.scenarios_total} "
                    f"dormant_shading_auto_low_exposure_events={report.dormant_shading_auto_low_exposure_events} "
                    f"lens_comp_lock_or_arw_conflation_events={report.lens_comp_lock_or_arw_conflation_events} "
                    f"af_illuminator_gate_or_fx6_spoof_events={report.af_illuminator_gate_or_fx6_spoof_events} "
                    f"movie_af_transition_or_assist_drift_events={report.movie_af_transition_or_assist_drift_events} "
                    f"aperture_drive_pre_af_shutter_reset_drift_events={report.aperture_drive_pre_af_shutter_reset_drift_events} "
                    f"circ_focus_diagonal_or_color_drift_events={report.circ_focus_diagonal_or_color_drift_events} "
                    f"folder_name_or_leading_underscore_violations={report.folder_name_or_leading_underscore_violations} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_folder_dir_mutation_bytes={report.slot1_folder_dir_mutation_bytes} "
                    f"slot1_rating_avf_info_mutation_bytes={report.slot1_rating_avf_info_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-55pillar-recovery':
            report = verify_55pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'55pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar55_a={report.pillar55_a_lens_comp_af_illuminator_vault.scenarios_passed}/{report.pillar55_a_lens_comp_af_illuminator_vault.scenarios_total} "
                    f"pillar55_b={report.pillar55_b_aperture_drive_folder_rating_vault.scenarios_passed}/{report.pillar55_b_aperture_drive_folder_rating_vault.scenarios_total} "
                    f"dormant_shading_auto_low_exposure_events={report.dormant_shading_auto_low_exposure_events} "
                    f"lens_comp_lock_or_arw_conflation_events={report.lens_comp_lock_or_arw_conflation_events} "
                    f"af_illuminator_gate_or_fx6_spoof_events={report.af_illuminator_gate_or_fx6_spoof_events} "
                    f"movie_af_transition_or_assist_drift_events={report.movie_af_transition_or_assist_drift_events} "
                    f"aperture_drive_pre_af_shutter_reset_drift_events={report.aperture_drive_pre_af_shutter_reset_drift_events} "
                    f"circ_focus_diagonal_or_color_drift_events={report.circ_focus_diagonal_or_color_drift_events} "
                    f"folder_name_or_leading_underscore_violations={report.folder_name_or_leading_underscore_violations} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_folder_dir_mutation_bytes={report.slot1_folder_dir_mutation_bytes} "
                    f"slot1_rating_avf_info_mutation_bytes={report.slot1_rating_avf_info_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_55pillar_sha256={report.master_55pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault':
            report = run_pillar56_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar56-switch-vh-af-stdadj-tcub-copy-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_56a={report.pillar_56a_switch_vh_af_focus_limit_color_vault.scenarios_passed}/{report.pillar_56a_switch_vh_af_focus_limit_color_vault.scenarios_total} "
                    f"pillar_56b={report.pillar_56b_exposure_std_tcub_reverse_copy_vault.scenarios_passed}/{report.pillar_56b_exposure_std_tcub_reverse_copy_vault.scenarios_total} "
                    f"switch_vh_af_lockout_or_coords_drift_events={report.switch_vh_af_lockout_or_coords_drift_events} "
                    f"focus_limit_lt2_or_dormant_symbol_events={report.focus_limit_lt2_or_dormant_symbol_events} "
                    f"focus_area_color_or_fx6_spoof_events={report.focus_area_color_or_fx6_spoof_events} "
                    f"exp_std_adj_mode_conflation_or_reset_drift_events={report.exp_std_adj_mode_conflation_or_reset_drift_events} "
                    f"bracket_settings_reset_or_fx6_spoof_events={report.bracket_settings_reset_or_fx6_spoof_events} "
                    f"tcub_reset_wipe_or_format_lock_violations={report.tcub_reset_wipe_or_format_lock_violations} "
                    f"reverse_copy_slot2_to_slot1_bypass_events={report.reverse_copy_slot2_to_slot1_bypass_events} "
                    f"slideshow_power_save_or_fx6_copy_clip_spoof_events={report.slideshow_power_save_or_fx6_copy_clip_spoof_events} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_copy_avf_info_mutation_bytes={report.slot1_copy_avf_info_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-56pillar-recovery':
            report = verify_56pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'56pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar56_a={report.pillar56_a_switch_vh_af_focus_limit_color_vault.scenarios_passed}/{report.pillar56_a_switch_vh_af_focus_limit_color_vault.scenarios_total} "
                    f"pillar56_b={report.pillar56_b_exposure_std_tcub_reverse_copy_vault.scenarios_passed}/{report.pillar56_b_exposure_std_tcub_reverse_copy_vault.scenarios_total} "
                    f"switch_vh_af_lockout_or_coords_drift_events={report.switch_vh_af_lockout_or_coords_drift_events} "
                    f"focus_limit_lt2_or_dormant_symbol_events={report.focus_limit_lt2_or_dormant_symbol_events} "
                    f"focus_area_color_or_fx6_spoof_events={report.focus_area_color_or_fx6_spoof_events} "
                    f"exp_std_adj_mode_conflation_or_reset_drift_events={report.exp_std_adj_mode_conflation_or_reset_drift_events} "
                    f"bracket_settings_reset_or_fx6_spoof_events={report.bracket_settings_reset_or_fx6_spoof_events} "
                    f"tcub_reset_wipe_or_format_lock_violations={report.tcub_reset_wipe_or_format_lock_violations} "
                    f"reverse_copy_slot2_to_slot1_bypass_events={report.reverse_copy_slot2_to_slot1_bypass_events} "
                    f"slideshow_power_save_or_fx6_copy_clip_spoof_events={report.slideshow_power_save_or_fx6_copy_clip_spoof_events} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_copy_avf_info_mutation_bytes={report.slot1_copy_avf_info_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_56pillar_sha256={report.master_56pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault':
            report = run_pillar57_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar57-touch-disp-zero-evf-flash-interval-pb-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_57a={report.pillar_57a_touch_disp_zero_evf_vault.scenarios_passed}/{report.pillar_57a_touch_disp_zero_evf_vault.scenarios_total} "
                    f"pillar_57b={report.pillar_57b_still_ael_flash_interval_pb_edit_vault.scenarios_passed}/{report.pillar_57b_still_ael_flash_interval_pb_edit_vault.scenarios_total} "
                    f"touch_op_dormant_trap_or_reset_drift_events={report.touch_op_dormant_trap_or_reset_drift_events} "
                    f"disp_set_or_zero_evf_blackout_events={report.disp_set_or_zero_evf_blackout_events} "
                    f"fx6_touch_or_evf_spoof_events={report.fx6_touch_or_evf_spoof_events} "
                    f"still_ael_flash_reset_split_or_mishoe_drift_events={report.still_ael_flash_reset_split_or_mishoe_drift_events} "
                    f"interval_pb_9scale_or_path_drift_events={report.interval_pb_9scale_or_path_drift_events} "
                    f"playback_edit_dormant_or_slot1_vault_bypass_events={report.playback_edit_dormant_or_slot1_vault_bypass_events} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_edit_avf_info_mutation_bytes={report.slot1_edit_avf_info_mutation_bytes} "
                    f"slot1_avf_info_mutated={report.slot1_avf_info_mutated} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-57pillar-recovery':
            report = verify_57pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'57pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar57_a={report.pillar57_a_touch_disp_zero_evf_vault.scenarios_passed}/{report.pillar57_a_touch_disp_zero_evf_vault.scenarios_total} "
                    f"pillar57_b={report.pillar57_b_still_ael_flash_interval_pb_edit_vault.scenarios_passed}/{report.pillar57_b_still_ael_flash_interval_pb_edit_vault.scenarios_total} "
                    f"touch_op_dormant_trap_or_reset_drift_events={report.touch_op_dormant_trap_or_reset_drift_events} "
                    f"disp_set_or_zero_evf_blackout_events={report.disp_set_or_zero_evf_blackout_events} "
                    f"fx6_touch_or_evf_spoof_events={report.fx6_touch_or_evf_spoof_events} "
                    f"still_ael_flash_reset_split_or_mishoe_drift_events={report.still_ael_flash_reset_split_or_mishoe_drift_events} "
                    f"interval_pb_9scale_or_path_drift_events={report.interval_pb_9scale_or_path_drift_events} "
                    f"playback_edit_dormant_or_slot1_vault_bypass_events={report.playback_edit_dormant_or_slot1_vault_bypass_events} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_edit_avf_info_mutation_bytes={report.slot1_edit_avf_info_mutation_bytes} "
                    f"slot1_avf_info_mutated={report.slot1_avf_info_mutated} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_57pillar_sha256={report.master_57pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault':
            report = run_pillar58_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_58a={report.pillar_58a_dial_customize_mydial_fn12x2_vault.scenarios_passed}/{report.pillar_58a_dial_customize_mydial_fn12x2_vault.scenarios_total} "
                    f"pillar_58b={report.pillar_58b_liveview_grid_lut_embed_pplut_vault.scenarios_passed}/{report.pillar_58b_liveview_grid_lut_embed_pplut_vault.scenarios_total} "
                    f"dial_customize_dormant_trap_or_reset_drift_events={report.dial_customize_dormant_trap_or_reset_drift_events} "
                    f"rear_dial_lr_or_mydial_override_drift_events={report.rear_dial_lr_or_mydial_override_drift_events} "
                    f"fn_menu_12x2_or_fx6_dial_spoof_events={report.fn_menu_12x2_or_fx6_dial_spoof_events} "
                    f"live_view_display_reset_split_or_mode_drift_events={report.live_view_display_reset_split_or_mode_drift_events} "
                    f"grid_line_or_hdmi_clean_feed_leak_events={report.grid_line_or_hdmi_clean_feed_leak_events} "
                    f"lut_path_embed_sidecar_or_slot1_vault_bypass_events={report.lut_path_embed_sidecar_or_slot1_vault_bypass_events} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_lut_mutation_bytes={report.slot1_lut_mutation_bytes} "
                    f"slot1_avf_info_mutated={report.slot1_avf_info_mutated} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-58pillar-recovery':
            report = verify_58pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'58pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar58_a={report.pillar58_a_dial_customize_mydial_fn12x2_vault.scenarios_passed}/{report.pillar58_a_dial_customize_mydial_fn12x2_vault.scenarios_total} "
                    f"pillar58_b={report.pillar58_b_liveview_grid_lut_embed_pplut_vault.scenarios_passed}/{report.pillar58_b_liveview_grid_lut_embed_pplut_vault.scenarios_total} "
                    f"dial_customize_dormant_trap_or_reset_drift_events={report.dial_customize_dormant_trap_or_reset_drift_events} "
                    f"rear_dial_lr_or_mydial_override_drift_events={report.rear_dial_lr_or_mydial_override_drift_events} "
                    f"fn_menu_12x2_or_fx6_dial_spoof_events={report.fn_menu_12x2_or_fx6_dial_spoof_events} "
                    f"live_view_display_reset_split_or_mode_drift_events={report.live_view_display_reset_split_or_mode_drift_events} "
                    f"grid_line_or_hdmi_clean_feed_leak_events={report.grid_line_or_hdmi_clean_feed_leak_events} "
                    f"lut_path_embed_sidecar_or_slot1_vault_bypass_events={report.lut_path_embed_sidecar_or_slot1_vault_bypass_events} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_lut_mutation_bytes={report.slot1_lut_mutation_bytes} "
                    f"slot1_avf_info_mutated={report.slot1_avf_info_mutated} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_58pillar_sha256={report.master_58pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command in (
            'verify-pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault',
            'verify-pillar59-recovery',
        ):
            report = run_pillar59_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_59a={report.pillar_59a_steadyshot_47focal_selftimer_vault.scenarios_passed}/{report.pillar_59a_steadyshot_47focal_selftimer_vault.scenarios_total} "
                    f"pillar_59b={report.pillar_59b_zebra_peaking_streaming_vault.scenarios_passed}/{report.pillar_59b_zebra_peaking_streaming_vault.scenarios_total} "
                    f"steadyshot_47focal_or_lockout_drift_events={report.steadyshot_47focal_or_lockout_drift_events} "
                    f"selftimer_dormant_or_led8_audio_drift_events={report.selftimer_dormant_or_led8_audio_drift_events} "
                    f"fx6_ibis_or_selftimer_spoof_events={report.fx6_ibis_or_selftimer_spoof_events} "
                    f"zebra_custom_ire_or_peaking_clean_hdmi_drift_events={report.zebra_custom_ire_or_peaking_clean_hdmi_drift_events} "
                    f"streaming_24p_rec_or_network_reset_drift_events={report.streaming_24p_rec_or_network_reset_drift_events} "
                    f"zero_rf_or_slot1_vault_bypass_events={report.zero_rf_or_slot1_vault_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_streaming_or_ftp_mutation_bytes={report.slot1_streaming_or_ftp_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-59pillar-recovery':
            report = verify_59pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'59pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar59_a={report.pillar59_a_steadyshot_47focal_selftimer_vault.scenarios_passed}/{report.pillar59_a_steadyshot_47focal_selftimer_vault.scenarios_total} "
                    f"pillar59_b={report.pillar59_b_zebra_peaking_streaming_vault.scenarios_passed}/{report.pillar59_b_zebra_peaking_streaming_vault.scenarios_total} "
                    f"steadyshot_47focal_or_lockout_drift_events={report.steadyshot_47focal_or_lockout_drift_events} "
                    f"selftimer_dormant_or_led8_audio_drift_events={report.selftimer_dormant_or_led8_audio_drift_events} "
                    f"fx6_ibis_or_selftimer_spoof_events={report.fx6_ibis_or_selftimer_spoof_events} "
                    f"zebra_custom_ire_or_peaking_clean_hdmi_drift_events={report.zebra_custom_ire_or_peaking_clean_hdmi_drift_events} "
                    f"streaming_24p_rec_or_network_reset_drift_events={report.streaming_24p_rec_or_network_reset_drift_events} "
                    f"zero_rf_or_slot1_vault_bypass_events={report.zero_rf_or_slot1_vault_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_streaming_or_ftp_mutation_bytes={report.slot1_streaming_or_ftp_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_59pillar_sha256={report.master_59pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command in (
            'verify-pillar60-bright-mon-shotmark-usblan-bulb-vault',
            'verify-pillar60-recovery',
        ):
            report = run_pillar60_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar60-bright-mon-shotmark-usblan-bulb-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_60a={report.pillar_60a_bright_mon_monitor_brightness_bulb_vault.scenarios_passed}/{report.pillar_60a_bright_mon_monitor_brightness_bulb_vault.scenarios_total} "
                    f"pillar_60b={report.pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault.scenarios_passed}/{report.pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault.scenarios_total} "
                    f"bright_mon_or_monitor_brightness_drift_events={report.bright_mon_or_monitor_brightness_drift_events} "
                    f"bulb_mech_or_dormant_bulb_timer_hdr_drift_events={report.bulb_mech_or_dormant_bulb_timer_hdr_drift_events} "
                    f"fx6_vf_backlight_or_still_spoof_events={report.fx6_vf_backlight_or_still_spoof_events} "
                    f"shotmark_clipflag_or_dormant_divide_drift_events={report.shotmark_clipflag_or_dormant_divide_drift_events} "
                    f"tc_link_wpa3_or_usblan_mutex_drift_events={report.tc_link_wpa3_or_usblan_mutex_drift_events} "
                    f"zero_rf_or_slot1_vault_bypass_events={report.zero_rf_or_slot1_vault_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_m4root_avf_mutation_bytes={report.slot1_m4root_avf_mutation_bytes} "
                    f"slot1_dcim_divider_mutation_bytes={report.slot1_dcim_divider_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-60pillar-recovery':
            report = verify_60pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'60pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar60_a={report.pillar60_a_bright_mon_monitor_brightness_bulb_vault.scenarios_passed}/{report.pillar60_a_bright_mon_monitor_brightness_bulb_vault.scenarios_total} "
                    f"pillar60_b={report.pillar60_b_shotmark_edit_tclink_wpa3_usblan_vault.scenarios_passed}/{report.pillar60_b_shotmark_edit_tclink_wpa3_usblan_vault.scenarios_total} "
                    f"bright_mon_or_monitor_brightness_drift_events={report.bright_mon_or_monitor_brightness_drift_events} "
                    f"bulb_mech_or_dormant_bulb_timer_hdr_drift_events={report.bulb_mech_or_dormant_bulb_timer_hdr_drift_events} "
                    f"fx6_vf_backlight_or_still_spoof_events={report.fx6_vf_backlight_or_still_spoof_events} "
                    f"shotmark_clipflag_or_dormant_divide_drift_events={report.shotmark_clipflag_or_dormant_divide_drift_events} "
                    f"tc_link_wpa3_or_usblan_mutex_drift_events={report.tc_link_wpa3_or_usblan_mutex_drift_events} "
                    f"zero_rf_or_slot1_vault_bypass_events={report.zero_rf_or_slot1_vault_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_m4root_avf_mutation_bytes={report.slot1_m4root_avf_mutation_bytes} "
                    f"slot1_dcim_divider_mutation_bytes={report.slot1_dcim_divider_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_60pillar_sha256={report.master_60pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command in (
            'verify-pillar61-big6-framing-interval-tc-auth-fan-vault',
            'verify-pillar61-recovery',
        ):
            report = run_pillar61_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar61-big6-framing-interval-tc-auth-fan-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_61a={report.pillar_61a_big6_home_framing_interval_vault.scenarios_passed}/{report.pillar_61a_big6_home_framing_interval_vault.scenarios_total} "
                    f"pillar_61b={report.pillar_61b_tc_make_hdmi_auth_fan_vault.scenarios_passed}/{report.pillar_61b_tc_make_hdmi_auth_fan_vault.scenarios_total} "
                    f"big6_home_or_lower_left_nd_drift_events={report.big6_home_or_lower_left_nd_drift_events} "
                    f"framing_manual_or_dormant_auto_framing_drift_events={report.framing_manual_or_dormant_auto_framing_drift_events} "
                    f"interval_shoot_9999_or_fx6_mxf_spoof_events={report.interval_shoot_9999_or_fx6_mxf_spoof_events} "
                    f"tc_make_regen_or_hdmi_rec_ctrl_drift_events={report.tc_make_regen_or_hdmi_rec_ctrl_drift_events} "
                    f"access_authen_ssh_tls_or_fan_max_drift_events={report.access_authen_ssh_tls_or_fan_max_drift_events} "
                    f"zero_rf_or_slot1_vault_bypass_events={report.zero_rf_or_slot1_vault_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_dcim_avf_mutation_bytes={report.slot1_dcim_avf_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-61pillar-recovery':
            report = verify_61pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'61pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar61_a={report.pillar61_a_big6_home_framing_interval_vault.scenarios_passed}/{report.pillar61_a_big6_home_framing_interval_vault.scenarios_total} "
                    f"pillar61_b={report.pillar61_b_tc_make_hdmi_auth_fan_vault.scenarios_passed}/{report.pillar61_b_tc_make_hdmi_auth_fan_vault.scenarios_total} "
                    f"big6_home_or_lower_left_nd_drift_events={report.big6_home_or_lower_left_nd_drift_events} "
                    f"framing_manual_or_dormant_auto_framing_drift_events={report.framing_manual_or_dormant_auto_framing_drift_events} "
                    f"interval_shoot_9999_or_fx6_mxf_spoof_events={report.interval_shoot_9999_or_fx6_mxf_spoof_events} "
                    f"tc_make_regen_or_hdmi_rec_ctrl_drift_events={report.tc_make_regen_or_hdmi_rec_ctrl_drift_events} "
                    f"access_authen_ssh_tls_or_fan_max_drift_events={report.access_authen_ssh_tls_or_fan_max_drift_events} "
                    f"zero_rf_or_slot1_vault_bypass_events={report.zero_rf_or_slot1_vault_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_dcim_avf_mutation_bytes={report.slot1_dcim_avf_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_61pillar_sha256={report.master_61pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command in (
            'verify-pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault',
            'verify-pillar62-recovery',
        ):
            report = run_pillar62_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_62a={report.pillar_62a_rec_media_autoswitch_proxy_vault.scenarios_passed}/{report.pillar_62a_rec_media_autoswitch_proxy_vault.scenarios_total} "
                    f"pillar_62b={report.pillar_62b_cloud_poweroff_ble_mymenu_vault.scenarios_passed}/{report.pillar_62b_cloud_poweroff_ble_mymenu_vault.scenarios_total} "
                    f"rec_media_prioritize_or_autoswitch_drift_events={report.rec_media_prioritize_or_autoswitch_drift_events} "
                    f"card_speed_vpg200_vpg400_gate_drift_events={report.card_speed_vpg200_vpg400_gate_drift_events} "
                    f"proxy_sq_dci4k_or_120p_lockout_drift_events={report.proxy_sq_dci4k_or_120p_lockout_drift_events} "
                    f"cloud_init_persist_or_power_off_ble_rf_events={report.cloud_init_persist_or_power_off_ble_rf_events} "
                    f"mymenu_42slot_or_fx6_lock_spoof_events={report.mymenu_42slot_or_fx6_lock_spoof_events} "
                    f"zero_rf_or_slot1_vault_bypass_events={report.zero_rf_or_slot1_vault_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_dcim_m4root_avf_mutation_bytes={report.slot1_dcim_m4root_avf_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-62pillar-recovery':
            report = verify_62pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'62pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar62_a={report.pillar62_a_rec_media_autoswitch_proxy_vault.scenarios_passed}/{report.pillar62_a_rec_media_autoswitch_proxy_vault.scenarios_total} "
                    f"pillar62_b={report.pillar62_b_cloud_poweroff_ble_mymenu_vault.scenarios_passed}/{report.pillar62_b_cloud_poweroff_ble_mymenu_vault.scenarios_total} "
                    f"rec_media_prioritize_or_autoswitch_drift_events={report.rec_media_prioritize_or_autoswitch_drift_events} "
                    f"card_speed_vpg200_vpg400_gate_drift_events={report.card_speed_vpg200_vpg400_gate_drift_events} "
                    f"proxy_sq_dci4k_or_120p_lockout_drift_events={report.proxy_sq_dci4k_or_120p_lockout_drift_events} "
                    f"cloud_init_persist_or_power_off_ble_rf_events={report.cloud_init_persist_or_power_off_ble_rf_events} "
                    f"mymenu_42slot_or_fx6_lock_spoof_events={report.mymenu_42slot_or_fx6_lock_spoof_events} "
                    f"zero_rf_or_slot1_vault_bypass_events={report.zero_rf_or_slot1_vault_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_dcim_m4root_avf_mutation_bytes={report.slot1_dcim_m4root_avf_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_62pillar_sha256={report.master_62pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command in (
            'verify-pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault',
            'verify-pillar63-recovery',
        ):
            report = run_pillar63_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_63a={report.pillar_63a_ftp_ftpes_usblan_customwb_vault.scenarios_passed}/{report.pillar_63a_ftp_ftpes_usblan_customwb_vault.scenarios_total} "
                    f"pillar_63b={report.pillar_63b_movie_af_focusmap_marker_peaking_vault.scenarios_passed}/{report.pillar_63b_movie_af_focusmap_marker_peaking_vault.scenarios_total} "
                    f"ftp_protocol_sftp_or_jpeg_size_drift_events={report.ftp_protocol_sftp_or_jpeg_size_drift_events} "
                    f"wb_custom_cine_ei_or_shockless_drift_events={report.wb_custom_cine_ei_or_shockless_drift_events} "
                    f"movie_af_speed_or_focus_map_spoof_events={report.movie_af_speed_or_focus_map_spoof_events} "
                    f"marker_15ratio_peaking_hdmi_leak_events={report.marker_15ratio_peaking_hdmi_leak_events} "
                    f"zero_rf_usblan_or_slot1_avf_bypass_events={report.zero_rf_usblan_or_slot1_avf_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"usblan_packets_transmitted={report.usblan_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"hdmi_marker_peaking_pixels_emitted={report.hdmi_marker_peaking_pixels_emitted} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_avf_info_mutation_bytes={report.slot1_avf_info_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-63pillar-recovery':
            report = verify_63pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'63pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar63_a={report.pillar63_a_ftp_ftpes_usblan_customwb_vault.scenarios_passed}/{report.pillar63_a_ftp_ftpes_usblan_customwb_vault.scenarios_total} "
                    f"pillar63_b={report.pillar63_b_movie_af_focusmap_marker_peaking_vault.scenarios_passed}/{report.pillar63_b_movie_af_focusmap_marker_peaking_vault.scenarios_total} "
                    f"ftp_protocol_sftp_or_jpeg_size_drift_events={report.ftp_protocol_sftp_or_jpeg_size_drift_events} "
                    f"wb_custom_cine_ei_or_shockless_drift_events={report.wb_custom_cine_ei_or_shockless_drift_events} "
                    f"movie_af_speed_or_focus_map_spoof_events={report.movie_af_speed_or_focus_map_spoof_events} "
                    f"marker_15ratio_peaking_hdmi_leak_events={report.marker_15ratio_peaking_hdmi_leak_events} "
                    f"zero_rf_usblan_or_slot1_avf_bypass_events={report.zero_rf_usblan_or_slot1_avf_bypass_events} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"usblan_packets_transmitted={report.usblan_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"hdmi_marker_peaking_pixels_emitted={report.hdmi_marker_peaking_pixels_emitted} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_avf_info_mutation_bytes={report.slot1_avf_info_mutation_bytes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_63pillar_sha256={report.master_63pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command in (
            'verify-pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault',
            'verify-pillar64-recovery',
        ):
            report = run_pillar64_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_64a={report.pillar_64a_shoe_audio_4ch_subject_recog_vault.scenarios_passed}/{report.pillar_64a_shoe_audio_4ch_subject_recog_vault.scenarios_total} "
                    f"pillar_64b={report.pillar_64b_silent_target_version_bodydata_vault.scenarios_passed}/{report.pillar_64b_silent_target_version_bodydata_vault.scenarios_total} "
                    f"shoe_audio_preemption_or_limiter_drift_events={report.shoe_audio_preemption_or_limiter_drift_events} "
                    f"subject_recog_myth_or_face_memory_drift_events={report.subject_recog_myth_or_face_memory_drift_events} "
                    f"silent_mode_target_or_barrier_drift_events={report.silent_mode_target_or_barrier_drift_events} "
                    f"bodydata_version_flash_or_slot1_vault_drift_events={report.bodydata_version_flash_or_slot1_vault_drift_events} "
                    f"dormant_shutter_when_pwr_off_exposed_events={report.dormant_shutter_when_pwr_off_exposed_events} "
                    f"hdmi_face_frame_pixels_emitted={report.hdmi_face_frame_pixels_emitted} "
                    f"cnflasha_pixel_map_mutation_bytes={report.cnflasha_pixel_map_mutation_bytes} "
                    f"slot1_bodydata_mutation_bytes={report.slot1_bodydata_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"bodydata_placement_or_flash_authorized={report.bodydata_placement_or_flash_authorized} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-64pillar-recovery':
            report = verify_64pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'64pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar64_a={report.pillar64_a_shoe_audio_4ch_subject_recog_vault.scenarios_passed}/{report.pillar64_a_shoe_audio_4ch_subject_recog_vault.scenarios_total} "
                    f"pillar64_b={report.pillar64_b_silent_target_version_bodydata_vault.scenarios_passed}/{report.pillar64_b_silent_target_version_bodydata_vault.scenarios_total} "
                    f"shoe_audio_preemption_or_limiter_drift_events={report.shoe_audio_preemption_or_limiter_drift_events} "
                    f"subject_recog_myth_or_face_memory_drift_events={report.subject_recog_myth_or_face_memory_drift_events} "
                    f"silent_mode_target_or_barrier_drift_events={report.silent_mode_target_or_barrier_drift_events} "
                    f"bodydata_version_flash_or_slot1_vault_drift_events={report.bodydata_version_flash_or_slot1_vault_drift_events} "
                    f"dormant_shutter_when_pwr_off_exposed_events={report.dormant_shutter_when_pwr_off_exposed_events} "
                    f"hdmi_face_frame_pixels_emitted={report.hdmi_face_frame_pixels_emitted} "
                    f"cnflasha_pixel_map_mutation_bytes={report.cnflasha_pixel_map_mutation_bytes} "
                    f"slot1_bodydata_mutation_bytes={report.slot1_bodydata_mutation_bytes} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"bodydata_placement_or_flash_authorized={report.bodydata_placement_or_flash_authorized} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_64pillar_sha256={report.master_64pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command in (
            'verify-pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault',
            'verify-pillar65-recovery',
        ):
            report = run_pillar65_standalone_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(
                    args.out,
                    {'pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault-report.json': encode(result)},
                )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillar_65a={report.pillar_65a_hdmi_raw_16bit_rec_media_vault.scenarios_passed}/{report.pillar_65a_hdmi_raw_16bit_rec_media_vault.scenarios_total} "
                    f"pillar_65b={report.pillar_65b_desqueeze_reclamp_varshutter_apsc_vault.scenarios_passed}/{report.pillar_65b_desqueeze_reclamp_varshutter_apsc_vault.scenarios_total} "
                    f"hdmi_raw_output_or_media_vault_drift_events={report.hdmi_raw_output_or_media_vault_drift_events} "
                    f"hdmi_4k_only_or_gamut_removal_drift_events={report.hdmi_4k_only_or_gamut_removal_drift_events} "
                    f"desqueeze_ratio_lock_or_bypass_drift_events={report.desqueeze_ratio_lock_or_bypass_drift_events} "
                    f"rec_lamp_tally_or_emph_display_drift_events={report.rec_lamp_tally_or_emph_display_drift_events} "
                    f"dormant_var_shutter_or_apsc_reset_drift_events={report.dormant_var_shutter_or_apsc_reset_drift_events} "
                    f"dormant_var_shutter_exposed_events={report.dormant_var_shutter_exposed_events} "
                    f"hdmi_red_border_clean_feed_leak_pixels={report.hdmi_red_border_clean_feed_leak_pixels} "
                    f"recorded_media_desqueeze_pixels={report.recorded_media_desqueeze_pixels} "
                    f"fx6_sdi_desqueeze_pixels={report.fx6_sdi_desqueeze_pixels} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"suite_sha256={report.suite_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        elif args.command == 'verify-65pillar-recovery':
            report = verify_65pillar_recovery_suite(
                force_clean_room=True if args.force_clean_room else None,
            )
            result = report.to_dict()
            if args.out:
                new_directory(args.out, {'65pillar-recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                print(
                    f"status={report.status} mode={report.verification_mode} "
                    f"all_passed={report.all_passed} "
                    f"pillars={report.pillars_passed}/{report.pillar_count} "
                    f"elapsed_seconds={report.elapsed_seconds:.3f} "
                    f"under_1_5s_fast_cli_budget={report.under_1_5s_fast_cli_budget} "
                    f"under_2_5s_fast_cli_budget={report.under_2_5s_fast_cli_budget} "
                    f"under_6s_budget={report.under_6s_budget} "
                    f"nominal_under_4_0s={report.nominal_under_4_0s} "
                    f"pillar65_a={report.pillar65_a_hdmi_raw_16bit_rec_media_vault.scenarios_passed}/{report.pillar65_a_hdmi_raw_16bit_rec_media_vault.scenarios_total} "
                    f"pillar65_b={report.pillar65_b_desqueeze_reclamp_varshutter_apsc_vault.scenarios_passed}/{report.pillar65_b_desqueeze_reclamp_varshutter_apsc_vault.scenarios_total} "
                    f"hdmi_raw_output_or_media_vault_drift_events={report.hdmi_raw_output_or_media_vault_drift_events} "
                    f"hdmi_4k_only_or_gamut_removal_drift_events={report.hdmi_4k_only_or_gamut_removal_drift_events} "
                    f"desqueeze_ratio_lock_or_bypass_drift_events={report.desqueeze_ratio_lock_or_bypass_drift_events} "
                    f"rec_lamp_tally_or_emph_display_drift_events={report.rec_lamp_tally_or_emph_display_drift_events} "
                    f"dormant_var_shutter_or_apsc_reset_drift_events={report.dormant_var_shutter_or_apsc_reset_drift_events} "
                    f"dormant_var_shutter_exposed_events={report.dormant_var_shutter_exposed_events} "
                    f"fx3_desqueeze_1_8x_hits={report.fx3_desqueeze_1_8x_hits} "
                    f"fx3_type_menu_item_high_res_hits={report.fx3_type_menu_item_high_res_hits} "
                    f"apsc_s35_resettable_by_camera_settings_reset={report.apsc_s35_resettable_by_camera_settings_reset} "
                    f"hdmi_red_border_clean_feed_leak_pixels={report.hdmi_red_border_clean_feed_leak_pixels} "
                    f"recorded_media_desqueeze_pixels={report.recorded_media_desqueeze_pixels} "
                    f"fx6_sdi_desqueeze_pixels={report.fx6_sdi_desqueeze_pixels} "
                    f"slot1_data_sector_writes={report.slot1_data_sector_writes} "
                    f"slot1_vault_mutation_bytes={report.slot1_vault_mutation_bytes} "
                    f"rf_packets_transmitted={report.rf_packets_transmitted} "
                    f"rf_nvs_mutation_bytes={report.rf_nvs_mutation_bytes} "
                    f"slot1_format_hard_locked={report.slot1_format_hard_locked} "
                    f"slot1_vault_erofs_eopnotsupp_enforced={report.slot1_vault_erofs_eopnotsupp_enforced} "
                    f"slot1_vault_erofs_ebusy_enforced={report.slot1_vault_erofs_ebusy_enforced} "
                    f"bodydata_placement_or_flash_authorized={report.bodydata_placement_or_flash_authorized} "
                    f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
                    f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
                    f"hardware_live_attachment_authorized={report.hardware_live_attachment_authorized} "
                    f"master_65pillar_sha256={report.master_65pillar_sha256[:16]} "
                    f"cnflasha_userspace_write_blocked={report.cnflasha_userspace_write_blocked} "
                    f"otp_fuse_touches={report.otp_fuse_touches} "
                    f"rpmb_counter_increments={report.rpmb_counter_increments} "
                    f"passive_tx_bytes_emitted={report.passive_tx_bytes_emitted} "
                    f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
                    f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
                    f"isp_write_authorized={report.isp_write_authorized} "
                    f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
                    f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
                    f"physical_device_writes={report.physical_device_writes} "
                    f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}"
                )
            return 0 if report.all_passed else 2
        else:
            raise ValueError('unknown local operation')
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'REJECTED', 'error_type': type(error).__name__, 'error': str(error),
                          'camera_operations': 0, 'automatic_retry': False}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
