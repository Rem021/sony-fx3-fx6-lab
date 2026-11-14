"""CLI entrypoint for `fx3_firmware_lab` clean-room container, HAITA/BK4, and .uxc/LDEC audits."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import json
from typing import Dict, Optional, Sequence

from .audio_tc_hdmi_sdi_routing_auditor import (
    analyze_audio_tc_hdmi_sdi_routing,
    audio_tc_hdmi_sdi_routing_report_to_dict,
)
from .cube_lut_and_rtmd_verifier import (
    analyze_cube_lut_and_rtmd,
    cube_lut_and_rtmd_report_to_dict,
)
from .global_xdb_and_menu_tree_auditor import (
    analyze_global_xdb_and_menu_tree,
    global_xdb_and_menu_tree_report_to_dict,
)
from .haita_bk4_feature_analyzer import (
    analyze_haita_and_bk4_features,
    haita_report_to_dict,
)
from .sensor_codec_compatibility_analyzer import (
    analyze_sensor_and_codec_compatibility,
    sensor_codec_report_to_dict,
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


def run_audit_all(*, clean_room: bool = False) -> Dict[str, object]:
    """Run all nine clean-room auditors and return a deterministic JSON-serializable summary."""
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
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m fx3_firmware_lab",
        description="Clean-room Sony FX3/FX6 UFU container, HAITA/BK4 feature, .uxc/LDEC/CJK font, IMX510/XAVC codec, .cube 3D LUT / RTMD, WBI2/hibdrv/ELF64 ABI, global.xdb/128-page menu, and 4-ch audio / SMPTE 12M TC / HDMI-SDI routing auditor.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_all = sub.add_parser("audit-all", help="Run all 9 firmware lab auditors and emit JSON")
    p_all.add_argument("--clean-room", action="store_true", help="Force synthetic clean-room mode without local donors")

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
    else:
        parser.error(f"Unknown command: {args.command}")
        return 2

    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload.get("all_checks_passed", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
