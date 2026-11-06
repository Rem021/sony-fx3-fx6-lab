#!/usr/bin/env python3
"""Targeted offline gates; never starts QEMU."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'v25-menu-osd-diagnostic'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 source=(HERE/'src/fx3-osd-headless-v25-r3.c').read_text()
 prior=(PREV/'src/fx3-osd-headless-v25-r2.c').read_text()
 for call in ('int rc=hwait(id,timeout)','int rc=hsignal(id)','if(ack_freed&&!ho_signal_begin(&hm,id,kind))','if(consume&&!rc)((U *)ring)[6]++'):
  assert source.count(call)==prior.count(call)==1,call
 assert 'if(!__atomic_compare_exchange_n(&v25_diag_writer' in source
 critical=source.split('if(!__atomic_compare_exchange_n(&v25_diag_writer',1)[1].split('__atomic_store_n(&v25_diag_writer,0',1)[0]
 assert all(op not in critical for op in ('hsend(', 'hwait(', 'hsignal(', 'own_lock(', 'usleep(', 'dprintf('))
 old=set(subprocess.check_output(['xcrun','llvm-nm','-D','-u',str(PREV/'build/fx3-osd-headless-v25-r2.so')],text=True).splitlines())
 new=set(subprocess.check_output(['xcrun','llvm-nm','-D','-u',str(HERE/'build/fx3-osd-headless-v25-r3.so')],text=True).splitlines())
 assert not new-old
 cand_path=HERE/'vmopt-20261104-v25-menu-osd-diagnostic-r3/candidate.json'
 candidate=json.loads(cand_path.read_text());receipt=json.loads((cand_path.parent/'build-receipt.json').read_text())
 assert sha(cand_path)==receipt['candidate_sha256']
 assert sha(HERE/'src/fx3-osd-headless-v25-r3.c')==candidate['v25_diagnostic_contract']['source_sha256']
 assert sha(HERE/'build/fx3-osd-headless-v25-r3.so')==candidate['v25_diagnostic_contract']['new_member_sha256']
 assert sha(candidate['initrd']['path'])==candidate['initrd']['sha256']
 assert sha(candidate['dtb']['path'])==candidate['dtb']['sha256']
 assert sha(candidate['native_Backup_seed']['path'])==candidate['native_Backup_seed']['sha256']
 assert receipt['member_count']==1140 and len(receipt['changed_members'])==1 and receipt['dtb_only_initrd_end_changed']
 runner=(HERE/'run_trial_v25_diag_r3.py').read_text()
 assert 'capture_quiesced_diag(qmp, run)' in runner and 'restore_native_api(qmp, input_gate, run, timeout=20)' in runner
 assert runner.index('capture_quiesced_diag(qmp, run)')<runner.index('restore_native_api(qmp, input_gate, run, timeout=20)')
 assert "diagnostic_readback_pass = shutdown.get('diag_snapshot', {}).get('consistent') is True" in runner
 subprocess.run([sys.executable,str(HERE/'test_parse_v25_diag_r3.py')],check=True)
 subprocess.run([sys.executable,str(HERE/'test_quiesced_diag_readback.py')],check=True)
 subprocess.run([str(HERE/'build/test_diag_concurrency')],check=True)
 result={'status':'offline_pass','QEMU_started':False,'guest_validated':False,
         'candidate_sha256':sha(cand_path),'cpio_sha256':sha(candidate['initrd']['path']),
         'dtb_sha256':sha(candidate['dtb']['path']),'source_sha256':sha(HERE/'src/fx3-osd-headless-v25-r3.c'),
         'so_sha256':sha(HERE/'build/fx3-osd-headless-v25-r3.so'),
         'runner_sha256':sha(HERE/'run_trial_v25_diag_r3.py'),
         'new_undefined_imports':sorted(new-old),
         'diagnostic_only_lock_no_native_calls':True,'original_wait_signal_and_5000ms_preserved':True,
         'single_changed_cpio_member':receipt['changed_members'][0]['member'],
         'quiesced_snapshot_and_parser_fixture_pass':True}
 (HERE/'verification-r3.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
