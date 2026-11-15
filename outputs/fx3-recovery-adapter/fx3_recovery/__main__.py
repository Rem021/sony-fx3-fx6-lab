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
