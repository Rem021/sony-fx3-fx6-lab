"""CLI entrypoint for `python3 -m fx3_safety`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .boot_contracts import (
    parse_bk4_record,
    parse_fa0080_table,
    verify_bksb_ldr_bkup,
    verify_boot_screen_enum_contract,
    verify_sector0_partition_table,
)
from .brick_classifier import classify_brick_state, generate_failsafe_init2_overlay_hook
from .preflight import evaluate_12_safety_gates, verify_tier0_backup_manifest


def main(argv: list[str] | None = None) -> int:
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

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
