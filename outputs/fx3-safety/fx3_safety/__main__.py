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
from .realhw_service0336_mpr_ibis_and_46gate_guard import (
    evaluate_46gate_preflight,
    evaluate_g45_service_0336_canary,
    evaluate_g46_mpr_ibis_p18_guard,
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

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
