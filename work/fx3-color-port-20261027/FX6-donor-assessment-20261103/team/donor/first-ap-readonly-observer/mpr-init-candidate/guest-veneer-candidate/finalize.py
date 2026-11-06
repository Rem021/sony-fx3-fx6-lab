#!/usr/bin/env python3
"""Pin the offline deliverable and distinguish static/host from absent runtime proof."""
import hashlib
import json
from difflib import unified_diff
from pathlib import Path

HERE=Path(__file__).resolve().parent
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    old=(HERE.parent/'run_mpr_once.py').read_text().splitlines(keepends=True)
    new=(HERE/'run_guest_once.py').read_text().splitlines(keepends=True)
    (HERE/'runner-diff.patch').write_text(''.join(unified_diff(old,new,
        fromfile='previous/run_mpr_once.py',tofile='guest/run_guest_once.py')))
    receipts={n:json.loads((HERE/n).read_text()) for n in (
        'ap-patch.json','cpio-build.json','static-receipt.json','elf-audit.json',
        'cross-build.json','host-tests.json','preflight.json')}
    if (receipts['static-receipt.json']['status']!='STATIC_VERIFIED_NOT_RUN'
        or receipts['elf-audit.json']['status']!='ELF_STATIC_AUDITED_NOT_LOADED'
        or receipts['cross-build.json']['status']!='CROSS_REBUILT_IDENTICAL_NOT_RUN'
        or receipts['host-tests.json']['status']!='PASS_NO_QEMU'
        or receipts['preflight.json']['status']!='PREFLIGHT_NO_QEMU'):
        raise ValueError('offline gate failed')
    if receipts['preflight.json']['runner_sha256']!=sha(HERE/'run_guest_once.py'):
        raise ValueError('runner changed after preflight')
    scripts=('patch_ap.py','gen_bridge.py','extract_link_inputs.py','build_guest.py',
        'build_cpio.py','audit_candidate.py','audit_elf.py','guest_probe.py',
        'run_guest_once.py','test_core.c','test_guest_host.py','finalize.py',
        'bridge_core.c','bridge_core.h','bridge_runtime.c','bridge_stops.S',
        'sha256.c','sha256.h','callback_offsets.h','bridge_pins.h')
    products=('appFw-bridge.so','libfx6diag.so','guest-veneer.cpio',
        'genuine-input.bin','ap-patch.json','cpio-build.json','static-receipt.json',
        'elf-audit.json','cross-build.json','host-tests.json','preflight.json',
        'core-tests.txt','runner-diff.patch')
    hashes={name:sha(HERE/name) for name in scripts+products}
    (HERE/'source-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    receipt={'status':'GUEST_BRIDGE_STATIC_AND_HOST_VERIFIED_NOT_RUN',
        'source_cpio_sha256':receipts['static-receipt.json']['source_sha256'],
        'new_cpio_sha256':receipts['static-receipt.json']['candidate_sha256'],
        'new_cpio_bytes':receipts['static-receipt.json']['candidate_bytes'],
        'patched_ap_sha256':hashes['appFw-bridge.so'],
        'bridge_elf_sha256':hashes['libfx6diag.so'],
        'exact_member_changes':['usr/lib/appFw.so','+usr/lib/libfx6diag.so'],
        'other_existing_members_same_header_and_payload':True,
        'host_test_count':len(receipts['host-tests.json']['tests']),
        'prior_observer_test_status':'separately_rerun_PASS_NO_QEMU',
        'source_sha256_file':'source-sha256.json',
        'no_vm_started_in_this_task':True,
        'guest_load_or_Init_return_observed':False,
        'first_unknown_callback_observed':False,
        'API16_restore_in_diagnostic_run':'deliberately_skipped_no_guest_resume',
        'next_gate':'owner-reviewed single fixed-FX3 VM window; pre-call all-Z1 gate and bounded diagnostic stop'}
    (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
