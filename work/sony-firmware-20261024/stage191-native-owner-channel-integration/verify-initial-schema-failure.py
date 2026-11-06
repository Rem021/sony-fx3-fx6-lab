"""Bind final builds, executed tests and unchanged authority; no device action."""
from pathlib import Path
from hashlib import sha256
import json, subprocess, zipfile
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def digest(p):return sha256(p.read_bytes()).hexdigest()
b=json.loads((HERE/'build-receipt-v5.json').read_text())
assert b['owner_ABI']==4 and b['entry_schema']==3 and not b['native_build_released'] and not b['native_helper_executed']
for r in b['sources']:assert digest(HERE/r['path'])==r['sha256'],r['path']
for name,r in b['builds'].items():
 assert digest(Path(r['path']))==r['sha256'] and r['returncode']==0
 if name!='native':assert 'IOKit.framework' not in r['dependencies'] and 'libusb' not in r['dependencies']
t=json.loads((HERE/'integration-results.json').read_text())
assert t['tests_run']==len(t['results'])==32 and all(r['status']=='PASS' for r in t['results'])
assert t['test_source_sha256']==digest(HERE/'test_integration.py') and t['build_receipt_sha256']==digest(HERE/'build-receipt-v5.json')
assert t['real_unprivileged_kernel_peer_UID_PID_birth_checks'] and not t['cross_UID_root_peer_tested']
assert not t['native_helper_executed'] and t['administrator_or_camera_operations']==0
w=json.loads((HERE/'wire-regression/results.json').read_text())
assert w['case_count']==len(w['cases'])==55 and w['flow_count']==len(w['inert_flows'])==2
assert w['real_USB_or_camera_operations']==w['root_admin_or_privacy_changes']==0
for r in w['sources']:
 p=Path(r['path'])
 if not p.is_absolute():p=HERE/p
 assert digest(p)==r['sha256'],p
for r in json.loads((HERE/'source-before.json').read_text()):assert digest(Path(r['source']))==r['sha256']
for receipt,archive in [('build-receipt.json','initial-compiled-sources.zip')]+[(f'build-receipt-v{n}.json',f'v{n}-compiled-sources.zip') for n in (2,3,4)]:
 d=json.loads((HERE/receipt).read_text())
 with zipfile.ZipFile(HERE/archive) as z:
  for r in d['sources']:assert sha256(z.read(r['path'])).hexdigest()==r['sha256']
assert '#define FX3_NATIVE_RELEASED 0' in (HERE/'entry_target.h').read_text()
assert 'c->scope!=1' in (HERE/'owner_channel.c').read_text()
assert 'c->protocol_scope>1' in (HERE/'owner_iokit.c').read_text()
assert 'if(private_return==FX3_RETAINED)' in (HERE/'owner_entry_main.c').read_text()
assert digest(BASE/'stage190-AP-process-launch-and-loader/final-receipt.json')=='291c4e26ff2858ffcdf3ec005441152bc363df6dce61efc847e48b31d688b7c4'
before=json.loads((HERE/'goal-status-before.json').read_text())
assert len(before['requirements'])==16 and not before['goal_complete'] and not before['persistent_write_release']
processes=subprocess.check_output(['/bin/ps','-axo','pid,ppid,state,comm'],text=True)
assert not any('/owner-fixture-helper' in line for line in processes.splitlines()),'own fixture still running'
limitations={
 'live_release':False,'native_helper_executed':False,'new_administrator_or_camera_operations':0,
 'kernel_peer_tests':'real same-UID501 processes only; root-to-user cross-UID behavior untested',
 'native_scope':'compiled native candidate is wholly unreleased; native path additionally enforces observe/status/end only',
 'physical_protocol':'MSC START/AUTH/STOP in tests used only fake IOKit vtables; no actual mode transition, SERVICE profile, authentication or exit proof',
 'cleanup':'after any START attempt, even a returned STOP, private lifetime is retained; no body completion fabricated',
 'remaining':['fixed Terminal/bootstrap/user supervisor and result-receipt delivery must be ported to ABI4/schema3',
              'global fencing across future grants/processes is not implemented by a per-process once flag or per-grant lease',
              'shared frame is a cooperating observer interface, not a proven hostile-client security boundary; truncation/hostile mapping lifetime is not tested',
              'real root peer and physical ownership/return need their own concrete reviewed grant',
              'actual Sony wire/profiles, post-START re-enumeration, worker completion and read admission remain unproven',
              'same-body p1 backup, guarded ET_DYN loading, clean boot/WBI and independent restoration remain unproven'],
 'test_counter_correction':{'integration_report_helper_processes':t['helper_processes'],
    'meaning':'jobs launched by primary Job counter only',
    'additional_owner_job_in_orphan_observer':1,'additional_replay_helper_execution':1,
    'total_fake_owner_jobs':32,'total_fake_helper_executions':33,'own_observer_processes_intentionally_terminated':1,
    'no_real_owner_or_pending_device_process_killed':True},
}
with (HERE/'implementation-review.json').open('x') as f:json.dump(limitations,f,ensure_ascii=False,indent=2);f.write('\n')
refs=[{'url':'https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/un.h','use':'LOCAL_PEERPID/SOL_LOCAL definition and104-byte sockaddr path; checked against local build SDK'},
 {'url':'https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/uipc_syscalls.c','use':'control copyout truncation and sockargs MCLBYTES bound; web read only'},
 {'url':'https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/uipc_usrreq.c','use':'512 FD control bound/externalization before user control copyout; downloaded main is reference, not proof of exact running-kernel source identity','local_sha256':digest(HERE/'apple-uipc_usrreq.c.txt')}]
with (HERE/'primary-source-review.json').open('x') as f:json.dump({'references':refs,'host_version':subprocess.check_output(['/usr/bin/sw_vers','-productVersion'],text=True).strip(),'kernel':subprocess.check_output(['/usr/bin/uname','-r'],text=True).strip(),'SDK':b['SDK'],'new_device_operations':0},f,indent=2);f.write('\n')
members=['build-receipt-v5.json','integration-results.json','wire-build-receipt.json','wire-regression/results.json','implementation-review.json','primary-source-review.json','verify_review.py']
report={'status':'PASS_NATIVE_OWNER_CHANNEL_OFFLINE_INTEGRATION_REVIEW','integration_tests':32,'wire_regression_tests':55,'total_local_checks':87,'additional_inert_flows':2,
        'final_fixture_sanitizers':['address','undefined'],'native_candidate_released_or_executed':False,
        'new_administrator_or_camera_operations':0,'root_cross_UID_or_physical_backup_restore_proven':False,
        'files':[{'path':p,'sha256':digest(HERE/p),'bytes':(HERE/p).stat().st_size} for p in members]}
with (HERE/'verification-receipt.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
