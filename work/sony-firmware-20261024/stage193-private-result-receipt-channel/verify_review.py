"""Read-only local evidence review, then exclusive new receipts; no helper run."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,plistlib,stat,subprocess,zipfile
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[1]
PRIOR=BASE/'stage192-global-owner-fence-and-frame-IO'
PRIOR_SHA='1f7a34f67f28c998863b1eed5219597a115dfb05c7491b884b207a4896831079'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
 with (HERE/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert digest(PRIOR/'final-receipt.json')==PRIOR_SHA
prior=json.loads((PRIOR/'final-receipt.json').read_text())
for m in prior['files']:
 p=ROOT/m['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==m['bytes'] and digest(p)==m['sha256']
for name in ('build-receipt.json','build-receipt-v2.json','build-receipt-v3.json'):
 b=json.loads((HERE/name).read_text());assert not b['native_build_released'] and not b['native_helper_executed']
 for m in b['builds'].values():assert digest(Path(m['path']))==m['sha256']
 if name=='build-receipt-v3.json':
  for m in b['sources']:assert digest(HERE/m['path'])==m['sha256']
 else:
  zipped='initial-compiled-sources.zip' if name=='build-receipt.json' else 'v2-compiled-sources.zip'
  with zipfile.ZipFile(HERE/zipped) as z:
   for m in b['sources']:assert sha256(z.read(m['path'])).hexdigest()==m['sha256']
 for key in ('fixture','ipc'):assert 'IOKit.framework' not in b['builds'][key]['dependencies'] and 'libusb' not in b['builds'][key]['dependencies']
integration=json.loads((HERE/'integration-results.json').read_text());receipts=json.loads((HERE/'receipt-results.json').read_text())
assert integration['tests_run']==38 and receipts['tests_run']==20
for report in (integration,receipts):
 assert all(x['status']=='PASS' for x in report['results'])
 assert report['build_receipt_sha256']==digest(HERE/'build-receipt-v3.json')
 assert report['administrator_or_camera_operations']==0 and not report['native_helper_executed']
assert integration['test_source_sha256']==digest(HERE/'test_integration.py')
assert receipts['test_source_sha256']==digest(HERE/'test_receipt.py')
assert receipts['receiver_source_sha256']==digest(HERE/'receipt_receiver.py')
assert receipts['integration_source_sha256']==digest(HERE/'test_integration.py')
for m in json.loads((HERE/'source-before.json').read_text()):assert digest(ROOT/m['source'])==m['sha256']
lowlevel=['iokit_wire.c','iokit_wire.h','native_session.c','native_session.h','owner_channel.c','owner_channel.h','owner_core.c','owner_iokit.c','global_guard.c','global_guard.h','frame_io.c','frame_io.h']
for name in lowlevel:assert (HERE/name).read_bytes()==(PRIOR/name).read_bytes()
target=(HERE/'entry_target.h').read_text();entry=(HERE/'owner_entry_main.c').read_text()
assert '#define FX3_NATIVE_RELEASED 0' in target and '20261029-09' in target
assert 'mmap(' not in entry and 'msync(' not in entry
assert 'channel.scope=(option&4096)?2:1;' in entry and 'channel.path=FX3_FIXED_PEER_PATH;' in entry
assert '!fx3_receipt_peer_ack(&channel,peer_ack_deadline) && pre_owner_ready(&context)' in entry
assert 'FX3_RECEIPT_HELD' in entry and 'for(;;)pause_short();' in entry
ps=subprocess.check_output(['/bin/ps','-axo','command='],text=True)
assert not any(str(HERE) in line and ('/owner-fixture-helper' in line or '/owner-native-helper' in line) for line in ps.splitlines()),'own helper remains active'
goal=json.loads((BASE/'GOAL_STATUS.json').read_text());before=json.loads((HERE/'goal-status-before.json').read_text())
assert goal==before and len(goal['requirements'])==16 and not goal['goal_complete'] and not goal['persistent_write_release']
native=json.loads((HERE/'native-goal-observed.json').read_text());assert native['goal']['status']=='active'
now=datetime.now(timezone.utc).isoformat()
put('primary-source-review.json',{'checked_utc':now,'sources':[
 {'url':'https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/uipc_usrreq.c','access':'web rendered Apple primary source; main not pinned as current OS implementation','relevant':'LOCAL_PEERPID refuses disconnected unp_conn; supports observed ENOTCONN race'},
 {'url':'https://github.com/apple/darwin-xnu/blob/main/bsd/sys/socket.h','access':'web search primary header','relevant':'SO_NOSIGPIPE and MSG_DONTWAIT definitions; local build SDK remains authoritative for this build'}],
 'API_source_download':'Python HTTPS API fetch failed SSL EOF; no source file or commit digest was obtained; not represented as a fetched/pinned revision',
 'local_observation':'first integration failed after peer exit; fixed with live pre-owner ACK barrier; failed artifact and sources retained','camera_or_root_test':False})
put('implementation-review.json',{'status':'PRIVATE_RECEIPT_DELIVERY_IMPLEMENTED_OFFLINE_NOT_RELEASED','candidate':'fx3-702-private-receipt-channel-20261029-09',
 'local_checks':58,'integration':38,'targeted_receipts':20,'root_cross_UID_tested':False,'native_helper_executed':False,'new_administrator_or_camera_operations':0,
 'identity_scope':'kernel UID/PID captured while helper alive; prior kernel birth/path/hash before entry ACK; same accepted stream and private nonce/grant-bound header; no socket FD passing/import by this controller',
 'digest_scope':'SHA256 integrity, not digital signature or administrator-resistant proof; fixture same-user peers are not an authority boundary against that same user',
 'terminal_scope':'COMPLETE private return plus separate incarnation-absence observation; HELD never authorizes exit/release; pending call still retains owner after observer timeout',
 'persistent_receipt_scope':'saved user-owned JSON/bin are evidence snapshots only; no restart rehydration implemented or accepted as newly authenticated',
 'previous_checks_not_rerun':{'stage192_journal':18,'stage191_wire':55},
 'remaining':['fixed bootstrap, Terminal and full user supervisor integration to schema3/ABI4 + socket ACK/receipt',
 'durable trusted receipt verification after controller restart; relay PID must not substitute for helper PID',
 'new concrete separate host-only root-to-UID501 fake-object validation before native USB trial authorization',
 'current same-body p1 acquisition, guarded launch route, real cold boot/WBI and independent recovery',
 'actual target MAIN HD HEVC record and long-record acceptance'],
 'goal_complete':False,'persistent_write_release':False})
files=[]
for name in ('build-receipt-v3.json','integration-results.json','receipt-results.json','implementation-review.json','primary-source-review.json','native-goal-observed.json','README.md','receipt_receiver.py','test_integration.py','test_receipt.py'):
 p=HERE/name;files.append({'path':name,'bytes':p.stat().st_size,'sha256':digest(p)})
put('verification-receipt.json',{'status':'PASS_PRIVATE_OWNER_RECEIPT_REVIEW','created_utc':now,'local_checks':58,
 'integration':38,'targeted_receipts':20,'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),
 'lowlevel_byte_identical_to192':lowlevel,'native_candidate_released_or_executed':False,'new_administrator_or_camera_operations':0,
 'native_goal_observed':'active','physical_backup_restore_or_boot_proven':False,'files':files})
print(json.dumps({'review':'PASS','checks':58,'prior_manifest_members':len(prior['files']),'native_released_or_executed':False,'administrator_or_camera_operations':0}))
