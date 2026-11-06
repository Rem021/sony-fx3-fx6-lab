from pathlib import Path
import json,hashlib,subprocess,plistlib
R=Path(__file__).resolve().parent;H=R/'helpers';assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();seed=R/'runs/ap100v1sync600-8d0d69c0/Backup-native-file-before-menu.bin';assert sha(seed)=='552fd5f8b422f855aecbe0c3918b56f83f60fb76ea9a3b6fc7a0291c26035d9e';old=(H/'cp88-bank-fixture.bin').read_bytes();bank=seed.read_bytes()[0xd2000:];assert [i for i,(a,b) in enumerate(zip(old,bank)) if a!=b]==[9,32]
# Reviewable constructor-only adaptation. No candidate/run before Lead reply.
def put(p,s):assert not p.exists(),p;p.write_text(s)
put(H/'fx3-cp-backup-profile-v2-native101.h','#define CP_SEED_FNV64 0xee5c1a03bd34104fUL\n#define CP_SEED_SHA256 "b76c2f6c8caf62aa4dd11d0466575f38e12e9b6288d2d003ce326ce5530212e8"\n')
s=(H/'fx3-backup-sync100-v1.h').read_text();s=s.replace('if(!sync100_payload)sync100_payload=sync100_fingerprint(backing);','if(!sync100_payload){sync100_payload=sync100_fingerprint(backing);sync100_suspend=backing[9];}')
put(H/'fx3-backup-sync101-v1.h',s)
s=(H/'fx3-cp-backup-v4-sync100.c').read_text().replace('fx3-cp-backup-profile-v1.h','fx3-cp-backup-profile-v2-native101.h').replace('fx3-backup-sync100-v1.h','fx3-backup-sync101-v1.h')
put(H/'fx3-cp-backup-v5-native101.c',s)
# Keep runtime module name same so existing native unbind helper remains identical.
s=(H/'fx3-cp-backup-v4-sync100-module-unit.c').read_text().replace('fx3-cp-backup-v4-sync100.c','fx3-cp-backup-v5-native101.c')
put(H/'fx3-cp-backup-v5-native101-module-unit.c',s)
s=(R/'run_candidate101_v1.py').read_text();s=s.replace("and candidate['native_Backup_seed']['sha256'] in serial_now", "")
s=s.replace("verified=before_AP and 'FX3_BACKUP_INSMOD_RC=0' in serial_now ","file_receipt=capture_native_file(qmp,run,'native-load-before-AP')\n                    verified=before_AP and 'FX3_BACKUP_INSMOD_RC=0' in serial_now and file_receipt.get('valid') and file_receipt.get('sha256')==candidate['native_Backup_seed']['sha256']")
s=s.replace("'native_file_seen_and_module_load0':verified,","'native_file_seen_and_module_load0':verified,'native_file_O_RDONLY_readback':file_receipt,")
# Wait for actual observer's first complete read before pausing for proof.
s=s.replace("if 'FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN' in serial_now and not replay_input_verified:","if 'FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN' in serial_now and 'FX3_FILE100_NATIVE_FILE_READ generation=1 ' in serial_now and not replay_input_verified:")
put(R/'run_candidate101_r2.py',s);compile(s,'run_candidate101_r2.py','exec')
# The reviewed candidate will start observer before the preAP window, giving an
# actual file snapshot and a shutdown channel even if later gates stop early.
init=(R/'ap101-v1-native-backup-file/init-reviewed.sh').read_text();a=init.index(' echo FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN');z=init.index(' echo FX3_AP_NATURAL_BOOTIN_BEGIN',a)
init=init[:a]+''' /simulation/fx3-file100-observer-v1 &
 echo FX3_FILE100_OBSERVER_PID=$!
 /bin/busybox sleep 2
 echo FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN bounded_seconds=8 original_backupfile_load=1 AP_not_started=1 RAM_replay_absent=1 source_SHA_by_actual_O_RDONLY_export=1
 /bin/busybox sleep 8
 echo FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_END
'''+init[z:];put(R/'ap101-r2-init-proposed.sh',init);subprocess.run(['/bin/sh','-n',str(R/'ap101-r2-init-proposed.sh')],check=True)
args=[x.replace('fx3-cp-backup-v4-sync100','fx3-cp-backup-v5-native101') for x in json.loads((H/'fx3-cp-backup-v4-sync100-build.json').read_text())['args']];q=subprocess.run(args,capture_output=True,text=True);assert q.returncode==0,q.stderr;(H/'fx3-cp-backup-v5-native101-build.json').write_text(json.dumps({'args':args,'exit':0,'state':'REVIEW_PENDING_NOT_DEPLOYED','source_sha256':sha(H/'fx3-cp-backup-v5-native101.c'),'output_sha256':sha(H/'fx3-cp-backup-v5-native101.ko'),'change':'constructor initial bank pin uses actual native saved CP data; read actual SuspendComp once; same model algorithms/transport/ownership/guards'},indent=2)+'\n')
put(R/'ap101-r2-review-proposal-v1.json',json.dumps({'base_run':'ap101v1nativefile600-7c9e5597','own_observer_failure':'BusyBox sha256sum applet absent; raw bank data actually matched native file exactly','proposed_observer_fix':'actual existing O_RDONLY file-export snapshot SHA; start observer before native preAP window, including early stop native API restore','actual_CP_loaded_matches_native_saved_file':True,'native_CP_difference_from_prior_seed':[{'offset':9,'old':old[9],'native':bank[9]},{'offset':32,'old':old[32],'native':bank[32]}],'old_initial_FNV':'0x9c88411e0172b013','native_initial_FNV':'0xee5c1a03bd34104f','old_initial_SuspendComp':0,'native_initial_SuspendComp':1,'review_pending_constructor_profile':str(H/'fx3-cp-backup-v5-native101.c'),'candidate_or_run_created_for_proposal':False,'all_other_models_identical':True},indent=2)+'\n');print('AP101-r2 reviewable sources/driver/constructor built; no candidate or run')
