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
from .emmc_dump_forensic_verifier import (
    VALID_ROLES,
    report_to_dict,
    run_clean_room_forensic_suite,
    verify_emmc_dump_file,
)
from .fdt_bootargs_and_kernel_verifier import run_fdt_bootargs_and_kernel_suite
from .firmware_updata_and_antirollback_guard import run_antirollback_and_byof_guard_suite
from .gpt_rpmb_and_rescue_bundle_verifier import run_gpt_rpmb_and_rescue_bundle_suite
from .init2_escape_and_watchdog_simulator import run_init2_escape_and_watchdog_suite
from .ramdisk_overlay_and_emmc_health_verifier import run_ramdisk_overlay_and_emmc_health_suite
from .recovery_master_suite_and_uart_decoder import run_recovery_master_suite
from .rp2040_multiport_fixture_selftest import run_rp2040_multiport_fixture_selftest
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
            if args.out:
                new_directory(args.out, {'recovery-master-report.json': encode(result)})
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
            else:
                has_opt_in = args.with_phase94 or args.with_phase101 or args.with_phase106
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
