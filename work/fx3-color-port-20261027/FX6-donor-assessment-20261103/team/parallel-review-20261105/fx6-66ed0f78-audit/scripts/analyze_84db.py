#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; OUT=Path(__file__).resolve().parent.parent/'receipts'
B=CP/'runs/cp-bind-84db17c2'; T=CP/'runs/cp-bind-66ed0f78'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def info(run):
 c=json.loads((run/'command.json').read_text()); r=json.loads((run/'run-receipt.json').read_text()); s=(run/'serial.log').read_text(errors='replace'); lines=s.splitlines()
 kp=c['argv'][c['argv'].index('-kernel')+1]; cpio=next(x for x in c['argv'] if 'guest-' in x and '.cpio' in x); cpio_path=Path(cpio.split('file=')[1].split(',addr=')[0]) if 'file=' in cpio else Path(cpio)
 markers={m:sum(1 for l in lines if m in l) for m in ['FX3_AP89_SCREEN_CREATE','FX3_AP89_UUD_DECISION','FX3_MENU','FX3_MEDIA_START_BRANCH','FX3_PROFILE_FRAME','FX3_PROVIDER_CALLER','FX3_AP_IM_ENDMAPS']}
 faults=[{'line':i,'text':l[:500]} for i,l in enumerate(lines,1) if 'Oops:' in l or 'Internal error:' in l or 'Kernel panic' in l or 'assert at' in l]
 return {'run':str(run),'command_sha256':h(run/'command.json'),'receipt_sha256':h(run/'run-receipt.json'),'serial_sha256':h(run/'serial.log'),'serial_bytes':len((run/'serial.log').read_bytes()),'candidate':c.get('candidate'),'kernel_path':kp,'kernel_sha256':h(Path(kp)),'cpio_path':str(cpio_path),'cpio_sha256':h(cpio_path),'mode':c.get('mode'),'model_env':c.get('model_env'),'duration':r.get('elapsed_seconds'),'maximum':r.get('maximum_seconds'),'reason':r.get('reason'),'fault_markers':r['serial_observation'].get('fault_markers'),'ap_markers':r.get('ap_markers'),'markers':markers,'faults':faults[:10]}
def main():
 b=info(B); t=info(T); cand=json.loads((CP/'vm-candidate-upmthofsskip.json').read_text())
 value={'schema':'fx6-r50-baseline-84db-audit-v1','baseline':b,'target':t,
  'same_fx3_kernel':b['kernel_sha256']==t['kernel_sha256']=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c',
  'same_qemu_and_platform':True,'differences':{'cpio':{'baseline':b['cpio_sha256'],'target':t['cpio_sha256'],'baseline_member':'grmreal45','target_member':'grmreal46'},
   'upm_patch':{'baseline':cand.get('upm_thofs_skip'),'target':'upm_callsite_skip (5be2aa0b…)'},
   'duration':{'baseline_seconds':b['duration'],'target_seconds':t['duration'],'baseline_max':b['maximum'],'target_max':t['maximum']},
   'target_extra_timeout':True,'other_skips':{'baseline':[k for k in ('backup_bug_skip','appfw_future_skip','upm_thofs_skip') if cand.get(k)],'target':['backup_bug_skip','appfw_future_skip','upm_callsite_skip']}},
  'single_variable':False,'causal_attribution':'not isolated: CPIO member/upm patch variant and 60s vs 180s timeout differ; kernel/platform same',
  'baseline_first_fault':b['faults'][0] if b['faults'] else None,'target_first_fault':t['faults'][0] if t['faults'] else None,
  'baseline_no_screen_uud_menu':all(b['markers'][k]==0 for k in ('FX3_AP89_SCREEN_CREATE','FX3_AP89_UUD_DECISION','FX3_MENU')),
  'note':'one appended completed baseline only; existing bytes; no new run'}
 (OUT/'baseline-84db-audit.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'baseline':{k:b[k] for k in ('duration','maximum','reason','fault_markers','markers')},'same_kernel':value['same_fx3_kernel'],'single_variable':False,'baseline_fault':value['baseline_first_fault'],'receipt':str(OUT/'baseline-84db-audit.json')},indent=2))
if __name__=='__main__':main()
