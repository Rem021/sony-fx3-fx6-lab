"""CLI entrypoint for `fx3_firmware_lab` clean-room container, HAITA/BK4, and .uxc/LDEC audits."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import json
from typing import Dict, Optional, Sequence

from .haita_bk4_feature_analyzer import (
    analyze_haita_and_bk4_features,
    haita_report_to_dict,
)
from .ufu_container_auditor import audit_ufu_suite
from .uxc_ldec_inspector import inspect_uxc_and_ldec, uxc_report_to_dict
from .uxc_multilang_and_font_verifier import (
    multilang_report_to_dict,
    verify_multilang_and_fonts,
)


def run_audit_all(*, clean_room: bool = False) -> Dict[str, object]:
    """Run all four clean-room auditors and return a deterministic JSON-serializable summary."""
    ufu = audit_ufu_suite()
    haita = haita_report_to_dict(analyze_haita_and_bk4_features(clean_room=clean_room))
    uxc = uxc_report_to_dict(inspect_uxc_and_ldec(clean_room=clean_room))
    multilang = multilang_report_to_dict(verify_multilang_and_fonts(clean_room=clean_room))

    all_passed = bool(
        ufu.get("all_checks_passed")
        and haita.get("all_checks_passed")
        and uxc.get("all_checks_passed")
        and multilang.get("all_checks_passed")
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
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m fx3_firmware_lab",
        description="Clean-room Sony FX3/FX6 UFU container, HAITA/BK4 feature, and .uxc/LDEC/CJK font asset auditor.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_all = sub.add_parser("audit-all", help="Run UFU, HAITA/BK4, .uxc/LDEC, and multilang/font audits and emit JSON")
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
    else:
        parser.error(f"Unknown command: {args.command}")
        return 2

    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload.get("all_checks_passed", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
