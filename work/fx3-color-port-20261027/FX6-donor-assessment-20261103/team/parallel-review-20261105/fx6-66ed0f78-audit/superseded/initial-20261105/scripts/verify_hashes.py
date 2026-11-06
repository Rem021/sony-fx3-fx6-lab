#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team')
CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; RUN=CP/'runs/cp-bind-66ed0f78'; B1=CP/'runs/cp-bind-6e83a14a'; B2=CP/'runs/cp-bind-9d22099a'; OUT=Path(__file__).resolve().parent.parent/'receipts'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 refresh=json.loads((TEAM/'fx6-primary-readonly-refresh-20261105-66ed0f78.json').read_text())
 cmd=json.loads((RUN/'command.json').read_text()); rec=json.loads((RUN/'run-receipt.json').read_text()); cand=json.loads((CP/'vm-candidate-upmcallsite180.json').read_text())
 memb=json.loads((OUT/'cpio-member-audit.json').read_text()); ser=json.loads((OUT/'serial-evidence.json').read_text())
 target=memb['selected']['target_grmreal46']
 checks={
  'candidate_hash':{'expected':'d318102606785debe0808f2e42750b28181f56dc876ef46f12050d8a87af5802','actual':h(CP/'vm-candidate-upmcallsite180.json')},
  'command_manifest':{'expected':rec['manifest_sha256'],'actual':cmd['manifest_sha256']},
  'receipt_manifest':{'expected':rec['manifest_sha256'],'actual':refresh['candidate_sha256']},
  'candidate_initrd':{'expected':cand['initrd']['sha256'],'actual':h(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio')},
  'kernel':{'expected':cand['kernel']['sha256'],'actual':h(Path(cand['kernel']['path']))},
  'dtb':{'expected':cand['dtb']['sha256'],'actual':h(Path(cand['dtb']['path']))},
  'serial':{'expected':rec['logs']['serial.log']['sha256'],'actual':h(RUN/'serial.log')},
  'host_stdout':{'expected':rec['logs']['host-stdout.log']['sha256'],'actual':h(RUN/'host-stdout.log')},
  'host_stderr':{'expected':rec['logs']['host-stderr.log']['sha256'],'actual':h(RUN/'host-stderr.log')},
  'appFw_member':{'expected':'b1fe2274e19d50b6d7ee12886dc233a742358772383f5cf79523de15cf0b55be','actual':target['usr/lib/appFw.so']},
  'upm_member':{'expected':'5be2aa0b6d6c0a31bb7802400fcd688a980583a08e945245adad7700b9882994','actual':target['usr/kmod/upm.ko']},
  'backup_member':{'expected':'6ae178d5390f847415fcc57236b8d49e33c486f043e906598eb2af81f7fec11e','actual':target['usr/kmod/backup.ko']},
  'helper_member':{'expected':'7e8d859ecb0fc66c5e05909ae5688b966838a6aa7bb0a478b6b4139177004aaa','actual':target['simulation/fx3-cp-backup-reset-v1.ko']},
 }
 for v in checks.values():v['match']=v['expected']==v['actual']
 original={'appFw':h(TEAM/'donor/nflasha15-files/lib/appFw.so'),'upm':h(TEAM/'donor/nflasha15-files/kmod/upm.ko'),'backup':h(TEAM/'donor/nflasha15-files/kmod/backup.ko'),'backup_nested':h(TEAM/'donor/nested-files/nflasha1-initrd/usr/kmod/backup.ko'),'helper_source':h(CP/'fx6-cp-backup-sync100-agnostic-g0.ko')}
 chain={
  'target_cpio':{'source_grmreal41':h(CP/'guest-hybrid-fx6kernel-capid-grmreal41.cpio'),'target':h(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio'),'changed_member':memb['target_vs_source_grmreal41']['changed'],'only_upm_changed':memb['target_vs_source_grmreal41']['only_upm_changed']},
  'appfw_future_build':json.loads((CP/'APPFWFUTURE-CPIO-BUILD.json').read_text())['target'],
  'backup_bug_build':json.loads((CP/'BACKUPBUG-CPIO-BUILD.json').read_text())['target'],
  'upm_callsite_build':json.loads((CP/'UPMCALLSITE-CPIO-BUILD.json').read_text())['target'],
  'original_donor':original,
  'cpio_baseline_grmreal21':memb['selected']['grmreal21'],
  'cpio_original_hybrid':memb['selected']['hybrid_fx6kernel'],
  'cpio_three_entry':memb['selected']['hybrid_three_entry'],
 }
 discrepancies={
  'serial_observation_fault_markers':{'receipt':rec['serial_observation']['fault_markers'],'actual_assert_lines':[{'line':i,'text':l[:300]} for i,l in enumerate((RUN/'serial.log').read_text(errors='replace').splitlines(),1) if 'assert at' in l],'actual_assert_count':sum(1 for l in (RUN/'serial.log').read_text(errors='replace').splitlines() if 'assert at' in l),'note':'serial_observation only treats Kernel panic/Oops/Unable/Internal/SError as faults; assert lines are not in fault_markers.'},
  'cp_helper_rc_line':{'receipt':rec['serial_observation']['cp_helper_rc_line'],'actual_line':ser['target']['bp']['cp_insmod_rc']['first'],'note':'marker exists but is interleaved mid-line; strict whole-line parser returns null; top-level cp_helper_rc0 comes from substring.'},
  'pre_ap_guard':{'receipt':rec['serial_observation']['pre_ap_guard'],'top_level':rec['pre_ap_guard'],'note':'nested false vs top-level true; receipt internally inconsistent.'},
  'reason_vs_timeout':{'receipt':rec['reason'],'elapsed':rec['elapsed_seconds'],'maximum':rec['maximum_seconds'],'note':'loop ended at 180s wall deadline but reason remains ap_guard_observed_continue.'},
  'cleanup':{'run_dir_files':sorted(x.name for x in RUN.iterdir()),'has_RESULT':(RUN/'RESULT.json').exists(),'has_RUN_SHA256SUMS':(RUN/'RUN-SHA256SUMS').exists(),'has_cleanup_receipt':False,'serial_tail':(RUN/'serial.log').read_bytes()[-160:].decode('utf-8','replace'),'note':'no independent cleanup artifact/End marker; qemu_exit/reaped/locks are run-receipt self-report.'}
 }
 value={'schema':'fx6-r50-hash-and-receipt-audit-v1','run':str(RUN),'checks':checks,'all_checks_match':all(v['match'] for v in checks.values()),'original_donor':original,'chain':chain,'discrepancies':discrepancies,
  'baselines':{'6e83a14a':{'command':str(B1/'command.json'),'command_sha256':h(B1/'command.json'),'receipt_sha256':h(B1/'run-receipt.json'),'serial_sha256':h(B1/'serial.log'),'kernel_path':json.loads((B1/'command.json').read_text())['argv'][json.loads((B1/'command.json').read_text())['argv'].index('-kernel')+1],'cpio_arg':next(x for x in json.loads((B1/'command.json').read_text())['argv'] if 'guest-' in x and '.cpio' in x)},'9d22099a':{'command_sha256':h(B2/'command.json'),'receipt_sha256':h(B2/'run-receipt.json'),'serial_sha256':h(B2/'serial.log'),'cpio_arg':next(x for x in json.loads((B2/'command.json').read_text())['argv'] if 'guest-' in x and '.cpio' in x)}},
  'note':'Target hashes verified; known first fault still present in target serial; donor-vs-CPIO baseline upm/backup differ.'}
 (OUT/'hash-audit.json').write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'all_checks_match':value['all_checks_match'],'checks':checks,'discrepancies':discrepancies,'original_donor':original,'target_changed':chain['target_cpio']},indent=2))
if __name__=='__main__':main()
