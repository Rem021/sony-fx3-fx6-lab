"""Independent receipt/static-byte cross-check; no guest or device execution."""
from pathlib import Path
from hashlib import sha256
import io, json, struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
def digest(path):
    return sha256(path.read_bytes()).hexdigest()
d = json.loads((HERE / 'launch-inventory-v2.json').read_text())
old = json.loads((HERE / 'launch-inventory-initial-stop-on-data.json').read_text())
assert d['ELFs_reverified'] == 532 and len(d['launch_files']) == 29
assert not d['original_Sony_or_public_client_execution'] and d['new_camera_operations'] == 0
for rec in d['launch_files']:
    c = rec['text_scan_coverage']
    assert c['section_bytes'] == c['decoded_instruction_bytes'] + c['skipped_data_bytes']
    assert c['skipped_data_bytes'] == 4 * len(c['skipped_data_offsets'])
assert sum(len(r['direct_calls']) for r in old['launch_files']) == 77
assert sum(len(r['direct_calls']) for r in d['launch_files']) == 103
review = json.loads((HERE / 'preload-recovery-review.json').read_text())
assert len(review['cases']) == 5 and all(r['normal_return'] for r in review['cases'])
assert [r['return_w0'] for r in review['cases']] == [0, 0, 0, 1, 0]
assert review['real_filesystem_kernel_loader_or_camera_operations'] == 0
assert digest(HERE / 'glibc-2.25-rtld-source.txt') == review['upstream_reference']['sha256']
raw = (BASE / 'stage2/extraction/files/nflasha7/lib/ld-2.25.so').read_bytes()
assert sha256(raw).hexdigest() == review['loader_sha256']
elf = ELFFile(io.BytesIO(raw))
def original(at, length):
    s = next(s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'
             and s['p_vaddr'] <= at and at + length <= s['p_vaddr'] + s['p_filesz'])
    off = s['p_offset'] + at - s['p_vaddr']; return raw[off:off + length]
assert sha256(original(0xb00, 148)).hexdigest() == review['original_do_preload']['sha256']
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
for at in (0x3ab0, 0x3bbc, 0x3c14):
    ins = list(md.disasm(original(at, 4), at)); assert len(ins) == 1
    assert ins[0].mnemonic == 'bl' and ins[0].op_str == '#0xb00'
    assert hex(at) in review['original_do_preload']['direct_caller_VAs']
before = json.loads((HERE / 'goal-status-before.json').read_text())
assert len(before['requirements']) == 16 and before['goal_complete'] is False
wbi = next(r for r in before['requirements'] if r['id'] == 'G09')
assert wbi['status'] == 'partial'
decision = {
    'status': 'PRELOAD_BASELINE_COMPATIBLE_BUT_LIVE_READ_AND_RECOVERY_UNPROVEN',
    'best_known_community_candidate_for_next_offline_implementation': 'fixed debug-child interception with a guarded ET_DYN worker',
    'basis': ['Original BusyBox is dynamically linked to this original glibc2.25 loader.',
              'Original error consumer warns/returns0 for caught lookup errors in explicit guest fixtures.',
              'The normal fixed libJit route first attempts persistent flash mount; TERM_MODE is rejected.'],
    'not_a_proven_exclusive_or_only_route': True,
    'code_prerequisites': ['0.4 worker is ET_EXEC, not an LD_PRELOAD module; guarded ET_DYN build/loader acceptance still needed.',
                           'A preload constructor must never call exit_group in the main im process or an unrelated process.',
                           'Original date trigger has fixed clock side effect if interception fails; original fork failure and unbounded wait remain.',
                           'Native owner, peer identity, whole-operation budget and IOKit channel integration still needed.'],
    'preload_file_is_declared_persistent_not_RAM_only': True,
    'preload_fallback_scope': 'Only a missing volatile library after a genuine clean boot could reach the checked nonfatal error consumer. This is not firmware write rollback.',
    'WBI_gate': {'id': 'G09', 'current_status': wbi['status'],
                 'remaining': wbi['remaining'],
                 'consequence': 'Do not equate ordinary off/on or a restored WBI image with a clean boot that discards the new RAM module. Current WBI state and physical recovery are not observed.'},
    'next_implementation_priority': 'Complete same-process native host owner/channel integration and fixed read admission before preparing a reviewable live preflight. In parallel trace constructor/loader and genuine clean-boot conditions.',
    'requires_separate_authorization_for': ['Sony authentication/service/mode commands', 'camera file or partition reads',
                                            'module upload/execution', '/etc preload creation/removal or other persistent writes', 'firmware writes'],
    'already_consumed_once_only_USB_grants_not_reused': True,
    'new_camera_operations': 0, 'goal_complete': False, 'persistent_write_release': False,
}
with (HERE / 'launch-decision.json').open('x') as out:
    json.dump(decision, out, ensure_ascii=False, indent=2); out.write('\n')
members = ['inventory_launch.py', 'launch-inventory-v2.json', 'inventory-initial-stop-on-data.py',
           'launch-inventory-initial-stop-on-data.json', 'audit_preload_recovery.py',
           'preload-recovery-review.json', 'glibc-2.25-rtld-source.txt', 'launch-decision.json', 'verify_review.py']
receipt = {'status': 'PASS_ORIGINAL_LOADER_REVIEW_AND_INVENTORY_COVERAGE',
           'original_loader_consumer_cases': 5, 'AP_ELFs_reverified': 532,
           'launch_candidate_files': 29, 'direct_call_candidates': 103,
           'prior_inventory_decode_stop_corrected_and_preserved': True,
           'three_original_helper_call_instructions_reconciled': True,
           'new_camera_operations': 0, 'physical_boot_or_recovery_proven': False,
           'files': [{'path': p, 'bytes': (HERE / p).stat().st_size, 'sha256': digest(HERE / p)} for p in members]}
with (HERE / 'verification-receipt.json').open('x') as out:
    json.dump(receipt, out, indent=2); out.write('\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'files'}))
