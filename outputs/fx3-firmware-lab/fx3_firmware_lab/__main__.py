"""CLI entrypoint for `fx3_firmware_lab` clean-room container, HAITA/BK4, and .uxc/LDEC audits."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import json
from typing import Dict, Optional, Sequence

from .assignable_zoom_ciz_and_fn_auditor import (
    analyze_assignable_zoom_ciz_and_fn,
    assignable_zoom_ciz_and_fn_report_to_dict,
)
from .audio_tc_hdmi_sdi_routing_auditor import (
    analyze_audio_tc_hdmi_sdi_routing,
    audio_tc_hdmi_sdi_routing_report_to_dict,
)
from .c2pa_lens_shading_and_mc_fleet_auditor import (
    analyze_c2pa_lens_shading_and_mc_fleet,
    c2pa_lens_shading_and_mc_fleet_report_to_dict,
)
from .cube_lut_and_rtmd_verifier import (
    analyze_cube_lut_and_rtmd,
    cube_lut_and_rtmd_report_to_dict,
)
from .emount_af_breathing_and_ibis_auditor import (
    analyze_emount_af_breathing_and_ibis,
    emount_af_breathing_and_ibis_report_to_dict,
)
from .falsecolor_lpcm_tc_ub_auditor import (
    analyze_falsecolor_lpcm_tc_ub,
    falsecolor_lpcm_tc_ub_report_to_dict,
)
from .global_xdb_and_menu_tree_auditor import (
    analyze_global_xdb_and_menu_tree,
    global_xdb_and_menu_tree_report_to_dict,
)
from .haita_bk4_feature_analyzer import (
    analyze_haita_and_bk4_features,
    haita_report_to_dict,
)
from .hdr_hlg_bt2100_and_display_assist_auditor import (
    analyze_hdr_hlg_bt2100_and_display_assist,
    hdr_hlg_bt2100_and_display_assist_report_to_dict,
)
from .hdmi_raw_prores_breathing_and_mishoe_clock_auditor import (
    analyze_hdmi_raw_prores_breathing_and_mishoe_clock,
    hdmi_raw_prores_breathing_and_mishoe_clock_report_to_dict,
)
from .interval_cache_and_ftp_auditor import (
    analyze_interval_cache_and_ftp,
    interval_cache_and_ftp_report_to_dict,
)
from .lut3d_cube_tetrahedral_and_sdi_hdmi_auditor import (
    analyze_lut3d_cube_tetrahedral_and_sdi_hdmi,
    lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict,
)
from .metadata_gyro_catalyst_and_anamorphic_auditor import (
    analyze_metadata_gyro_catalyst_and_anamorphic,
    metadata_gyro_catalyst_and_anamorphic_report_to_dict,
)
from .playback_shotmark_and_ae_auditor import (
    analyze_playback_shotmark_and_ae,
    playback_shotmark_and_ae_report_to_dict,
)
from .proxy_clipname_and_sidecar_auditor import (
    analyze_proxy_clipname_and_sidecar,
    proxy_clipname_and_sidecar_report_to_dict,
)
from .sensor_codec_compatibility_analyzer import (
    analyze_sensor_and_codec_compatibility,
    sensor_codec_report_to_dict,
)
from .shutter_ecs_sq_and_tally_auditor import (
    analyze_shutter_ecs_sq_and_tally,
    shutter_ecs_sq_and_tally_report_to_dict,
)
from .usb_uvc_uac_srt_and_crsdk_ptp_auditor import (
    analyze_usb_uvc_uac_srt_and_crsdk_ptp,
    usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict,
)
from .ufu_container_auditor import audit_ufu_suite
from .uxc_ldec_inspector import inspect_uxc_and_ldec, uxc_report_to_dict
from .uxc_multilang_and_font_verifier import (
    multilang_report_to_dict,
    verify_multilang_and_fonts,
)
from .wbi_hibdrv_and_elf_abi_differ import (
    analyze_wbi_hibdrv_and_elf_abi,
    wbi_hibdrv_and_elf_abi_report_to_dict,
)
from .wb_color_matrix_and_look_auditor import (
    analyze_wb_color_matrix_and_look,
    wb_color_matrix_and_look_report_to_dict,
)


def run_audit_all(*, clean_room: bool = False) -> Dict[str, object]:
    """Run all twenty-three clean-room auditors and return a deterministic JSON-serializable summary."""
    ufu = audit_ufu_suite()
    haita = haita_report_to_dict(analyze_haita_and_bk4_features(clean_room=clean_room))
    uxc = uxc_report_to_dict(inspect_uxc_and_ldec(clean_room=clean_room))
    multilang = multilang_report_to_dict(verify_multilang_and_fonts(clean_room=clean_room))
    sensor_codec = sensor_codec_report_to_dict(
        analyze_sensor_and_codec_compatibility(clean_room=clean_room)
    )
    lut_rtmd = cube_lut_and_rtmd_report_to_dict(
        analyze_cube_lut_and_rtmd(clean_room=clean_room)
    )
    wbi_elf = wbi_hibdrv_and_elf_abi_report_to_dict(
        analyze_wbi_hibdrv_and_elf_abi(clean_room=clean_room)
    )
    xdb_menu = global_xdb_and_menu_tree_report_to_dict(
        analyze_global_xdb_and_menu_tree(clean_room=clean_room)
    )
    audio_tc_hdmi = audio_tc_hdmi_sdi_routing_report_to_dict(
        analyze_audio_tc_hdmi_sdi_routing(clean_room=clean_room)
    )
    emount_af_ibis = emount_af_breathing_and_ibis_report_to_dict(
        analyze_emount_af_breathing_and_ibis(clean_room=clean_room)
    )
    shutter_ecs_sq_tally = shutter_ecs_sq_and_tally_report_to_dict(
        analyze_shutter_ecs_sq_and_tally(clean_room=clean_room)
    )
    wb_color_look = wb_color_matrix_and_look_report_to_dict(
        analyze_wb_color_matrix_and_look(clean_room=clean_room)
    )
    proxy_clipname_sidecar = proxy_clipname_and_sidecar_report_to_dict(
        analyze_proxy_clipname_and_sidecar(clean_room=clean_room)
    )
    assignable_zoom_ciz_fn = assignable_zoom_ciz_and_fn_report_to_dict(
        analyze_assignable_zoom_ciz_and_fn(clean_room=clean_room)
    )
    falsecolor_lpcm_tc_ub = falsecolor_lpcm_tc_ub_report_to_dict(
        analyze_falsecolor_lpcm_tc_ub(clean_room=clean_room)
    )
    playback_shotmark_ae = playback_shotmark_and_ae_report_to_dict(
        analyze_playback_shotmark_and_ae(clean_room=clean_room)
    )
    gyroflow_anamorphic_ibis = metadata_gyro_catalyst_and_anamorphic_report_to_dict(
        analyze_metadata_gyro_catalyst_and_anamorphic(clean_room=clean_room)
    )
    interval_cache_ftp = interval_cache_and_ftp_report_to_dict(
        analyze_interval_cache_and_ftp(clean_room=clean_room)
    )
    lut3d_sdi_hdmi = lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict(
        analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=clean_room)
    )
    c2pa_shading_mc = c2pa_lens_shading_and_mc_fleet_report_to_dict(
        analyze_c2pa_lens_shading_and_mc_fleet(clean_room=clean_room)
    )
    hdr_hlg_assist = hdr_hlg_bt2100_and_display_assist_report_to_dict(
        analyze_hdr_hlg_bt2100_and_display_assist(clean_room=clean_room)
    )
    proresraw_breathing_mishoe = hdmi_raw_prores_breathing_and_mishoe_clock_report_to_dict(
        analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=clean_room)
    )
    uvc_srt_crsdk = usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict(
        analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=clean_room)
    )

    all_passed = bool(
        ufu.get("all_checks_passed")
        and haita.get("all_checks_passed")
        and uxc.get("all_checks_passed")
        and multilang.get("all_checks_passed")
        and sensor_codec.get("all_checks_passed")
        and lut_rtmd.get("all_checks_passed")
        and wbi_elf.get("all_checks_passed")
        and xdb_menu.get("all_checks_passed")
        and audio_tc_hdmi.get("all_checks_passed")
        and emount_af_ibis.get("all_checks_passed")
        and shutter_ecs_sq_tally.get("all_checks_passed")
        and wb_color_look.get("all_checks_passed")
        and proxy_clipname_sidecar.get("all_checks_passed")
        and assignable_zoom_ciz_fn.get("all_checks_passed")
        and falsecolor_lpcm_tc_ub.get("all_checks_passed")
        and playback_shotmark_ae.get("all_checks_passed")
        and gyroflow_anamorphic_ibis.get("all_checks_passed")
        and interval_cache_ftp.get("all_checks_passed")
        and lut3d_sdi_hdmi.get("all_checks_passed")
        and c2pa_shading_mc.get("all_checks_passed")
        and hdr_hlg_assist.get("all_checks_passed")
        and proresraw_breathing_mishoe.get("all_checks_passed")
        and uvc_srt_crsdk.get("all_checks_passed")
    )
    return {
        "schema_version": "1.0.0",
        "all_checks_passed": all_passed,
        "clean_room_forced": clean_room,
        "keyless_byof_compliant": True,
        "hardware_ldec_required": False,
        "ufu_container_audit": ufu,
        "haita_bk4_feature_audit": haita,
        "uxc_ldec_asset_audit": uxc,
        "uxc_multilang_and_font_audit": multilang,
        "sensor_codec_compatibility_audit": sensor_codec,
        "cube_lut_and_rtmd_audit": lut_rtmd,
        "wbi_hibdrv_and_elf_abi_audit": wbi_elf,
        "global_xdb_and_menu_tree_audit": xdb_menu,
        "audio_tc_hdmi_sdi_routing_audit": audio_tc_hdmi,
        "emount_af_breathing_and_ibis_audit": emount_af_ibis,
        "shutter_ecs_sq_and_tally_audit": shutter_ecs_sq_tally,
        "wb_color_matrix_and_look_audit": wb_color_look,
        "proxy_clipname_and_sidecar_audit": proxy_clipname_sidecar,
        "assignable_zoom_ciz_and_fn_audit": assignable_zoom_ciz_fn,
        "falsecolor_lpcm_tc_ub_audit": falsecolor_lpcm_tc_ub,
        "playback_shotmark_and_ae_audit": playback_shotmark_ae,
        "metadata_gyro_catalyst_and_anamorphic_audit": gyroflow_anamorphic_ibis,
        "interval_cache_and_ftp_audit": interval_cache_ftp,
        "lut3d_cube_tetrahedral_and_sdi_hdmi_audit": lut3d_sdi_hdmi,
        "c2pa_lens_shading_and_mc_fleet_audit": c2pa_shading_mc,
        "hdr_hlg_bt2100_and_display_assist_audit": hdr_hlg_assist,
        "hdmi_raw_prores_breathing_and_mishoe_clock_audit": proresraw_breathing_mishoe,
        "usb_uvc_uac_srt_and_crsdk_ptp_audit": uvc_srt_crsdk,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m fx3_firmware_lab",
        description="Clean-room Sony FX3/FX6 UFU container, HAITA/BK4 feature, .uxc/LDEC/CJK font, IMX510/XAVC codec, .cube 3D LUT / RTMD, WBI2/hibdrv/ELF64 ABI, global.xdb/128-page menu, 4-ch audio/TC/HDMI-SDI, E-Mount PZ/PDAF/Breathing/IBIS, Shutter Angle/ECS/S&Q/Tally/Curtain, WB/Base Look/Paint Matrix/Calibration, Dual-Slot Proxy/CamID-Reel/NonRealTimeMeta XML, Assignable/CIZ/Touch-AF/Big6+Fn, False Color/EL-Zone S-Log3/LPCM DSP/SMPTE UB, Playback/Thumbnail/ShotMark EssenceMark XML/Push Auto Iris AE Shift, Gyroflow/Catalyst RTMD/Anamorphic 5-Axis IBIS/IMX510 Rolling-Shutter, Interval Rec/Picture Cache DDR/Wired USB-LAN FTP P12, User 3D LUT Tetrahedral/AVI InfoFrame/HDMI->12G-SDI REC-Trigger, C2PA 2.1/cnflasha Key-Vault/E-Mount Shading-CA-Distortion/Monitor & Control Wired PTP-IP Fleet, ITU-R BT.2100 ARIB STD-B67 HLG/Gamma Display Assist/CTA-861.3 HDR InfoFrame 0x87, HDMI RAW 16->12 Log ProRes RAW/BRAW/Focus Breathing FOV Guard/MI-Shoe 48kHz PLL Drift/OB-Clamp, and USB-C UVC 1.5/UAC 2.0/Wired P12-Safe SRT-RTMPS/CRSDK PTP Flash-Opcode Firewall auditor.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_all = sub.add_parser("audit-all", help="Run all 23 firmware lab auditors and emit JSON")
    p_all.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode without local donors")
    p_all.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    sub.add_parser("audit-ufu", help="Run keyless UFU/FDAT/UDTRFIRM & SDM2 structural audit")

    p_haita = sub.add_parser("audit-haita", help="Run FX3 ALCIN_UUD vs FX6 HAITA/BK4 differential audit")
    p_haita.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_uxc = sub.add_parser("audit-uxc", help="Run hardware-free .uxc / CPU LDEC asset audit")
    p_uxc.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_ml = sub.add_parser(
        "audit-multilang",
        help="Run 62-pack .uxc multi-language, CJK/JP/EN font cmap, and CPU sprite sweep audit",
    )
    p_ml.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_sc = sub.add_parser(
        "audit-sensor-codec",
        help="Run Phase 31 IMX510 sensor, Dual Base ISO, HDMI RAW, XAVC encoder, and slot/video boundary audit",
    )
    p_sc.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_lr = sub.add_parser(
        "audit-lut-rtmd",
        help="Run Phase 37 .cube (17^3/33^3) LUT sanitizer/P1+P11 packer and Sony RTMD (0xE304 IMX510 IBIS) audit",
    )
    p_lr.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_we = sub.add_parser(
        "audit-wbi-elf",
        help="Run Phase 43 WBI2 hibernation snapshot, hibdrv mismatch guard, and pure-Python ELF64 .dynsym/DT_NEEDED ABI diff",
    )
    p_we.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_xm = sub.add_parser(
        "audit-xdb-menu",
        help="Run Phase 46 global.xdb UX database & 128-page FX6-on-FX3 multilingual menu / hardware predicate audit",
    )
    p_xm.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_at = sub.add_parser(
        "audit-audio-tc-hdmi",
        help="Run Phase 51 4-ch 24-bit 48kHz XLR-H1 audio, SMPTE 12M TC (VMC-BNCM1 EXT-LK & HDMI TC), and 12G-SDI->HDMI Type-A 16-bit RAW matrix audit",
    )
    p_at.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_em = sub.add_parser(
        "audit-emount-af",
        help="Run Phase 55 E-Mount Power Zoom (PZ), 627-pt Fast Hybrid PDAF, Focus Breathing (UDAM/RTMD), and 5-axis IBIS/OSS matrix audit",
    )
    p_em.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_st = sub.add_parser(
        "audit-shutter-tally",
        help="Run Phase 60 Shutter Angle (5.6..360 deg), ECS, S&Q (1..240fps), Tally LEDs, and FX3 Mechanical Shutter Curtain Protection audit",
    )
    p_st.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")

    p_wb = sub.add_parser(
        "audit-wb-color-look",
        help="Run Phase 65 White Balance (Shockless WB/ATW/WHT BAL soft-map), Base Look, Paint 3x3 Color Matrix, and cnflasha Calibration audit",
    )
    p_wb.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_wb.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_pc = sub.add_parser(
        "audit-proxy-clipname",
        help="Run Phase 70 Dual-Slot Proxy (XAVC HS/S), CamID/Reel# Clip Naming, and NonRealTimeMeta.xml Sidecar audit",
    )
    p_pc.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_pc.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_ac = sub.add_parser(
        "audit-assignable-ciz",
        help="Run Phase 75 Assignable Buttons (FX6 1..11 -> FX3), T/W 8-Step & Clear Image Zoom (CIZ), Touch AF + Anamorphic Desqueeze, and Big6/Fn Volatile BK4 Shadow audit",
    )
    p_ac.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_ac.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_fc = sub.add_parser(
        "audit-falsecolor-lpcm-ub",
        help="Run Phase 80 False Color / EL-Zone S-Log3 Exposure Mapping, 4-Ch 24-bit 48kHz LPCM Headroom & Limiter DSP, and SMPTE 12M User-Bits + TC Direction audit",
    )
    p_fc.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_fc.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_psa = sub.add_parser(
        "audit-playback-shotmark-ae",
        help="Run Phase 85 Playback/Thumbnail Presenter + p1 Media Firewall, ShotMark1/2 EssenceMark XML, and Push Auto Iris / AE Shift + P4 Auto-ND Redirect audit",
    )
    p_psa.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_psa.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_ga = sub.add_parser(
        "audit-gyroflow-anamorphic",
        help="Run Phase 89 Gyroflow/Catalyst Sony RTMD 2000Hz IMU, Anamorphic 5-Axis IBIS Asymmetric Gain, IMX510 Rolling-Shutter Readout, and Stock-CP IMU Calibration Immutability audit",
    )
    p_ga.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_ga.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_icf = sub.add_parser(
        "audit-interval-cache-ftp",
        help="Run Phase 93 Interval Recording Electronic-Shutter Wear Firewall, FX6 Picture Cache DDR Ring-Buffer, Wired USB-LAN FTP/FTPS P12 RF-Off, and NonRealTimeMeta XML audit",
    )
    p_icf.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_icf.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_lut3d = sub.add_parser(
        "audit-lut3d-sdi-hdmi",
        help="Run Phase 98 User 3D LUT (.cube 17^3/33^3/65^3) Domain/NaN Sanitizer & Tetrahedral vs Trilinear CXD90058 Quantization, S-Log3 HDMI AVI InfoFrame Guard, and HDMI->12G-SDI REC-Trigger Parity audit",
    )
    p_lut3d.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_lut3d.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_c2pa = sub.add_parser(
        "audit-c2pa-shading-mc",
        help="Run Phase 105 C2PA 2.1 / cnflasha Key-Vault Firewall, E-Mount Lens Shading/CA/Distortion + Unchipped Identity Fail-Safe, Monitor & Control Wired PTP-IP 4-Cam Fleet (P12), and Factory Shading/Defect-Pixel Preservation audit",
    )
    p_c2pa.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_c2pa.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_hlg = sub.add_parser(
        "audit-hdr-hlg-assist",
        help="Run Phase 111 ITU-R BT.2100 / ARIB STD-B67 HLG (HLG1/2/3 & BT.2020 vs BT.709), Gamma Display Assist EVF/LCD Isolation, CTA-861.3 HDMI HDR InfoFrame 0x87, and NonRealTimeMeta SMPTE UL Parity audit",
    )
    p_hlg.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_hlg.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_prbm = sub.add_parser(
        "audit-proresraw-breathing-mishoe",
        help="Run Phase 114 HDMI 16-bit Linear->12-bit Log RAW ProRes RAW/BRAW Handshake, Focus-Breathing Dynamic FOV Crop vs RAW/120p Guard, MI-Shoe 48kHz I2S PLL 6h Drift Firewall, and Factory OB-Clamp Preservation audit",
    )
    p_prbm.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_prbm.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    p_usc = sub.add_parser(
        "audit-uvc-srt-crsdk",
        help="Run Phase 118 USB-C UVC 1.5/UAC 2.0, Wired P12-Safe SRT/RTMPS, & CRSDK PTP/PTP-IP Property + Flash-Opcode Firewall audit",
    )
    p_usc.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode")
    p_usc.add_argument("--json", action="store_true", help="Emit deterministic JSON (default behavior)")

    args = parser.parse_args(argv)

    if args.command == "audit-all":
        payload = run_audit_all(clean_room=bool(args.clean_room))
    elif args.command == "audit-ufu":
        payload = audit_ufu_suite()
    elif args.command == "audit-haita":
        payload = haita_report_to_dict(analyze_haita_and_bk4_features(clean_room=bool(args.clean_room)))
    elif args.command == "audit-uxc":
        payload = uxc_report_to_dict(inspect_uxc_and_ldec(clean_room=bool(args.clean_room)))
    elif args.command == "audit-multilang":
        payload = multilang_report_to_dict(verify_multilang_and_fonts(clean_room=bool(args.clean_room)))
    elif args.command == "audit-sensor-codec":
        payload = sensor_codec_report_to_dict(
            analyze_sensor_and_codec_compatibility(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-lut-rtmd":
        payload = cube_lut_and_rtmd_report_to_dict(
            analyze_cube_lut_and_rtmd(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-wbi-elf":
        payload = wbi_hibdrv_and_elf_abi_report_to_dict(
            analyze_wbi_hibdrv_and_elf_abi(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-xdb-menu":
        payload = global_xdb_and_menu_tree_report_to_dict(
            analyze_global_xdb_and_menu_tree(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-audio-tc-hdmi":
        payload = audio_tc_hdmi_sdi_routing_report_to_dict(
            analyze_audio_tc_hdmi_sdi_routing(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-emount-af":
        payload = emount_af_breathing_and_ibis_report_to_dict(
            analyze_emount_af_breathing_and_ibis(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-shutter-tally":
        payload = shutter_ecs_sq_and_tally_report_to_dict(
            analyze_shutter_ecs_sq_and_tally(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-wb-color-look":
        payload = wb_color_matrix_and_look_report_to_dict(
            analyze_wb_color_matrix_and_look(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-proxy-clipname":
        payload = proxy_clipname_and_sidecar_report_to_dict(
            analyze_proxy_clipname_and_sidecar(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-assignable-ciz":
        payload = assignable_zoom_ciz_and_fn_report_to_dict(
            analyze_assignable_zoom_ciz_and_fn(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-falsecolor-lpcm-ub":
        payload = falsecolor_lpcm_tc_ub_report_to_dict(
            analyze_falsecolor_lpcm_tc_ub(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-playback-shotmark-ae":
        payload = playback_shotmark_and_ae_report_to_dict(
            analyze_playback_shotmark_and_ae(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-gyroflow-anamorphic":
        payload = metadata_gyro_catalyst_and_anamorphic_report_to_dict(
            analyze_metadata_gyro_catalyst_and_anamorphic(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-interval-cache-ftp":
        payload = interval_cache_and_ftp_report_to_dict(
            analyze_interval_cache_and_ftp(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-lut3d-sdi-hdmi":
        payload = lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict(
            analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-c2pa-shading-mc":
        payload = c2pa_lens_shading_and_mc_fleet_report_to_dict(
            analyze_c2pa_lens_shading_and_mc_fleet(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-hdr-hlg-assist":
        payload = hdr_hlg_bt2100_and_display_assist_report_to_dict(
            analyze_hdr_hlg_bt2100_and_display_assist(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-proresraw-breathing-mishoe":
        payload = hdmi_raw_prores_breathing_and_mishoe_clock_report_to_dict(
            analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=bool(args.clean_room))
        )
    elif args.command == "audit-uvc-srt-crsdk":
        payload = usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict(
            analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=bool(args.clean_room))
        )
    else:
        parser.error(f"Unknown command: {args.command}")
        return 2

    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload.get("all_checks_passed", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
