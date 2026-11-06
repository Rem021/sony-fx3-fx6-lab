"""Review executed builds/tests and non-device boundaries; never elevate/run native."""
from pathlib import Path
from hashlib import sha256
import json,subprocess,zipfile
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
def digest(p):return sha256(p.read_bytes()).hexdigest()
b=json.loads((HERE/'build-receipt-v2.json').read_text())
for r in b['sources']:assert digest(HERE/r['path'])==r['sha256'],r['path']
for label,r in b['builds'].items():
 assert digest(Path(r['path']))==r['sha256'] and r['returncode']==0
 if label!='native':assert 'IOKit.framework' not in r['dependencies']
assert not b['native_build_released'] and not b['native_helper_executed']
t=json.loads((HERE/'integration-results.json').read_text());g=json.loads((HERE/'guard-results.json').read_text())
assert t['tests_run']==len(t['results'])==38 and all(r['status']=='PASS' for r in t['results'])
assert g['tests_run']==len(g['results'])==18 and all(r['status']=='PASS' for r in g['results'])
assert digest(HERE/'test_integration.py')==t['test_source_sha256']
assert digest(HERE/'test_guard.py')==g['test_source_sha256']
assert digest(HERE/'build-receipt-v2.json')==t['build_receipt_sha256']
assert digest(HERE/'guard-build-receipt-v2.json')==g['build_receipt_sha256']
gb=json.loads((HERE/'guard-build-receipt-v2.json').read_text())
assert digest(Path(gb['path']))==gb['sha256']
for name,want in gb['sources'].items():assert digest(HERE/name)==want
assert t['administrator_or_camera_operations']==g['root_or_camera_operations']==0
assert t['real_unprivileged_kernel_peer_UID_PID_birth_checks'] and not t['cross_UID_root_peer_tested']
assert t['sanitizers']==g['sanitizers']==['address','undefined']
assert '#define FX3_NATIVE_RELEASED 0' in (HERE/'entry_target.h').read_text()
assert 'mmap(' not in (HERE/'owner_entry_main.c').read_text() and 'msync(' not in (HERE/'owner_entry_main.c').read_text()
assert 'FX3_GLOBAL_GUARD' in (HERE/'owner_entry_main.c').read_text()
assert 'global-fx3-owner.journal' in (HERE/'entry_target.h').read_text()
assert digest(BASE/'stage191-native-owner-channel-integration/final-receipt.json')=='3d66f1d070a7ff85933b352b87b3c5a39ee5a680a8e9cf3fa30edc99b123f117'
for r in json.loads((HERE/'source-before.json').read_text()):assert digest(Path(r['source']))==r['sha256']
# Low-level wire/protocol implementation is byte-identical to sealed191, so its
#55 tests are reused evidence, explicitly NOT counted as new test executions.
same=['iokit_wire.c','iokit_wire.h','native_session.c','native_session.h','owner_channel.c','owner_channel.h']
for name in same:assert digest(HERE/name)==digest(BASE/'stage191-native-owner-channel-integration'/name)
old=json.loads((HERE/'build-receipt.json').read_text())
with zipfile.ZipFile(HERE/'initial-compiled-sources.zip') as z:
 for r in old['sources']:assert sha256(z.read(r['path'])).hexdigest()==r['sha256']
processes=subprocess.check_output(['/bin/ps','-axo','pid,ppid,state,comm'],text=True)
assert not any('/owner-fixture-helper' in l or '/guard-fixture' in l for l in processes.splitlines()),'own fixture still alive'
review={
 'status':'OFFLINE_FENCE_AND_PRIVATE_FRAME_IMPLEMENTED_NOT_RELEASED',
 'native_candidate_identifier':'fx3-702-global-owner-channel-20261029-08',
 'native_candidate_released_or_executed':False,'new_administrator_or_camera_operations':0,
 'fence_scope':'cooperating controller helpers using the same protected journal; does not block independent Sony/third-party tools',
 'fence_decision':'OWNED or UNKNOWN tail never clears merely because a PID died; only this owner clean/no-call result appends CLEAN',
 'journal_integrity':'SHA256 chain detects damaged/reordered records; not a signature against an administrator who controls the host',
 'frame_scope':'privileged helper copies4096B then uses pread/pwrite; no user-backed mmap; invalid envelope requests stop and never authorizes pending-call cleanup',
 'root_cross_UID_and_protected_root_files_tested':False,
 'test_counts':{'integration':38,'journal':18,'total':56,'prior_wire55_not_rerun':True,
  'primary_integration_Job_count':t['helper_processes'],'additional_orphan_owner_job':1,'additional_replay_execution':1},
 'remaining':['fixed bootstrap/Terminal/user supervisor still need migration to the new entry and fence contract',
              'authenticated final-result delivery still needs a completion record over the verified channel; shared progress/file alone is insufficient',
              'root-to-UID501 local handshake and protected root journal behavior require separate concrete authorization/test',
              'native entry remains0 and observe-only; no real Sony authentication, SERVICE profile, mode transition or file/partition read',
              'actual same-body p1, guarded ET_DYN, clean boot/WBI and independent rescue remain unproven'],
 'goal_complete':False,'persistent_write_release':False,
}
with (HERE/'implementation-review.json').open('x') as f:json.dump(review,f,ensure_ascii=False,indent=2);f.write('\n')
primary={'references':[{'url':'https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/flock.2.html','scope':'advisory exclusive/nonblocking lock, cooperating processes and descriptor references; archived API reference, actual current host behavior also tested'},
 {'url':'https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/pread.2.html','scope':'offset read semantics; actual private-envelope truncation behavior tested with fake device objects'}],
 'source':'official Apple archived manual + compiled current Mac process tests','new_device_operations':0}
with (HERE/'primary-source-review.json').open('x') as f:json.dump(primary,f,indent=2);f.write('\n')
members=['build-receipt-v2.json','guard-build-receipt-v2.json','integration-results.json','guard-results.json','implementation-review.json','primary-source-review.json','verify_review.py']
report={'status':'PASS_GLOBAL_FENCE_AND_PRIVATE_ENVELOPE_REVIEW','local_checks':56,'integration_checks':38,'journal_checks':18,
 'prior_wire55_reused_not_rerun':True,'native_candidate_released_or_executed':False,
 'new_administrator_or_camera_operations':0,'physical_backup_restore_or_boot_proven':False,
 'files':[{'path':p,'bytes':(HERE/p).stat().st_size,'sha256':digest(HERE/p)} for p in members]}
with (HERE/'verification-receipt.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
