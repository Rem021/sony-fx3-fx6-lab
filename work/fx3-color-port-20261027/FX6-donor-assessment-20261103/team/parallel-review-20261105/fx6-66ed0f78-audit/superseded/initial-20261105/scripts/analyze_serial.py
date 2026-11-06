#!/usr/bin/env python3
"""Read-only serial evidence parser for target and up to two baselines."""
import hashlib,json,re
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team')
CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; RUNS=CP/'runs'
TARGET=RUNS/'cp-bind-66ed0f78'; B1=RUNS/'cp-bind-6e83a14a'; B2=RUNS/'cp-bind-9d22099a'
MARKERS=['FX3_AP_IM_ENDMAPS','FX3_RM_NATIVE_FREE','FX3_MEDIA_START_BRANCH','FX3_AP89_SCREEN_CREATE','FX3_AP89_UUD_DECISION','FX3_AP_NATURAL_BOOTIN_BEGIN','FX3_AP_BOOTIN_LAUNCH_PID','FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN','FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_END','FX3_BACKUP_CP_INSMOD_RC','FX3_BACKUP_CP_PUBLIC_OWNER','FX3_SYNC100_API_BIND','FX3_SYNC100_BACKEND_BOUND','FX6_SYNC100_AGNOSTIC_BIND','FX3_PROFILE_FRAME','FX3_PROVIDER_CALLER','FX3_CP_HELPER','FX3_DEVTMPFS_RC','FX3_INSMOD_RC','FX3_MENU','FX3_KEY','FX3_FRAME','FX3_SCREEN','FX3_DRAW','FX3_UI_GATE']
FAULT=['assert','BUG:','kernel BUG','Oops','panic','Call trace','Unable to handle','segfault','brk #','send_and_wait_cmp_i','infra_wrapper_bb_procam_chaplin_base']
def analyze(label,run):
 p=run/'serial.log'; b=p.read_bytes(); text=b.decode('utf-8','replace'); lines=text.splitlines()
 out={'label':label,'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'lines':len(lines),'markers':{},'marker_lines':{},'fault_hits':[],'screen_create_lines':[],'menu_lines':[],'bp':{}}
 for m in MARKERS:
  idx=[i for i,l in enumerate(lines,1) if m in l]
  out['markers'][m]=len(idx)
  if idx: out['marker_lines'][m]=[{'line':i,'text':lines[i-1][:500]} for i in idx[:3]]+([{'line':idx[-1],'text':lines[idx[-1]-1][:500]}] if len(idx)>3 else [])
 for f in FAULT:
  idx=[i for i,l in enumerate(lines,1) if f.lower() in l.lower()]
  if idx: out['fault_hits'].append({'needle':f,'count':len(idx),'first':[{'line':i,'text':lines[i-1][:800]} for i in idx[:3]]})
 out['screen_create_lines']=[{'line':i,'text':lines[i-1][:800]} for i,l in enumerate(lines,1) if 'FX3_AP89_SCREEN_CREATE' in l][:5]
 out['menu_lines']=[{'line':i,'text':lines[i-1][:800]} for i,l in enumerate(lines,1) if 'FX3_MENU' in l or ('menu' in l.lower() and 'FX3_' in l)][:5]
 for key,needle in [('cp_insmod_rc','FX3_BACKUP_CP_INSMOD_RC'),('cp_public_owner','FX3_BACKUP_CP_PUBLIC_OWNER'),('cp_bind','FX3_SYNC100_BACKEND_BOUND'),('ap_im','FX3_AP_IM_ENDMAPS'),('ap_rm','FX3_RM_NATIVE_FREE'),('media_start','FX3_MEDIA_START_BRANCH'),('screen','FX3_AP89_SCREEN_CREATE'),('uud','FX3_AP89_UUD_DECISION'),('profile','FX3_PROFILE_FRAME'),('provider','FX3_PROVIDER_CALLER')]:
  rows=[{'line':i,'text':lines[i-1][:800]} for i,l in enumerate(lines,1) if needle in l]
  out['bp'][key]={'count':len(rows),'first':rows[:2],'last':rows[-1:]}
 return out
def main():
 data=[analyze('target_66ed0f78',TARGET),analyze('baseline_6e83a14a_known_CAPID_assert',B1),analyze('baseline_9d22099a_screen_marker',B2)]
 value={'schema':'fx6-r50-serial-evidence-v1','target':data[0],'baselines':data[1:],
  'note':'Exact substring counts on decoded serial; marker presence is not function completion; no fault != initialization success.'}
 out=Path(__file__).resolve().parent.parent/'receipts/serial-evidence.json';out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 for x in data:
  print('\n===',x['label'],x['bytes'],x['sha256'][:16],'lines',x['lines'])
  print('markers',{k:v for k,v in x['markers'].items() if v})
  print('fault hits',[(f['needle'],f['count'],f['first'][0]['line'] if f['first'] else None) for f in x['fault_hits']])
  print('screen',x['screen_create_lines'][:2]); print('cp',x['bp']['cp_insmod_rc'],x['bp']['cp_bind'])

if __name__ == "__main__":
    main()
