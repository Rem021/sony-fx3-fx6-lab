#!/usr/bin/env python3
"""Default-disabled host-only planning entry. No QEMU start, no guest writes."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import observer_core as core
TOKEN='APPROVE_GRMREAL46_TWO_KEYS_0214_0218'
def plan(serial):
 m=core.choose_appfw(serial.read_bytes(),core.APP_ELF);bias=m['ap']['bias']
 return {'schema':'fx6-backup-observer-plan-v1','status':'PLAN_ONLY_NOT_RUN','serial_sha256':core.sha(serial),'appfw_sha256':core.sha(core.APP_ELF),'target_cpio_sha256':core.TARGET_CPIO_SHA256,
  'pid':m['pid'],'epoch':m['epoch'],'bias':hex(bias),'appfw_tids':m['appfw_tids'],
  'breakpoints':[{'key':k['name'],'entry_va':hex(k['thunk_va']),'entry_address':hex(bias+k['thunk_va']),'return_va':hex(k['return_va']),'return_address':hex(bias+k['return_va']),'slot_off':hex(k['slot_off']),'capacity':4,'thunk_word':k['thunk_word'],'return_word':k['return_word']} for k in core.KEYS],
  'budgets':{'one_start':True,'keys':0,'observe_seconds':core.MAX_SECONDS,'total_seconds':180,'max_simultaneous_Z1':2,'max_stops':core.MAX_STOPS,'max_data_reads':core.MAX_READS,'max_read_bytes':core.MAX_READ_BYTES,'identity_reads_bounded':128},
  'policy':{'z0':False,'memory_or_register_write':False,'software_step':False,'patch':False,'stub':False,'veneer':False,'keys':False,'old_ASLR':False,'serial_map_required':True,'live_elf_phdr_words_required':True,'same_tid_tls_frame_required':True,'cleanup':'Z1/z1 only; residual => QMP stop/quit, no guest resume'}}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--serial',type=Path);ap.add_argument('--plan',action='store_true');ap.add_argument('--approved-token')
 a=ap.parse_args()
 if a.approved_token is None:
  if a.plan:
   if not a.serial or not a.serial.is_file():print('DENIED: serial path required');return 2
   p=plan(a.serial);(HERE.parent/'receipts/plan.json').write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(p,indent=2));print('PLAN_ONLY: no VM started');return 0
  print('DISABLED: host-only candidate; pass --plan for a no-VM plan, explicit token only after new approval')
  return 2
 if a.approved_token!=TOKEN:print('DENIED: approval token mismatch');return 2
 if not a.serial or not a.serial.is_file():print('DENIED: current serial path required');return 2
 p=plan(a.serial);(HERE.parent/'receipts/plan.json').write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(p,indent=2))
 print('READY_FOR_REVIEW: execution adapter is intentionally absent in this host-only candidate; no VM was started.')
 return 3
if __name__=='__main__':sys.exit(main())
