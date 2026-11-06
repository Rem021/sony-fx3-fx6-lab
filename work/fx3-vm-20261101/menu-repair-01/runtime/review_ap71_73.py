from pathlib import Path
import json,re,fcntl,os,sys,datetime
R=Path(__file__).resolve().parent;state=json.loads((R/'STATE.json').read_text());run=Path(sys.argv[2] if len(sys.argv)>2 else state['last_run']);stage=sys.argv[1];ls=(run/'serial.log').read_text(errors='replace').split('\n');receipt=json.loads((run/'receipt.json').read_text());matches=lambda key:[{'line':i+1,'text':x} for i,x in enumerate(ls) if key in x]
start=next((i for i,x in enumerate(ls) if 'FX3_LCD_BRIGHTNESS_COMMIT' in x),len(ls));timeline=[{'line':i+1,'text':x} for i,x in enumerate(ls) if i>=start and ('FX3_UIPC_PASS' in x or 'FX3_VDF_OBSERVE' in x or 'FX3_PROVIDER_REQUEST' in x or 'FX3_UIPC_SEND_UNIQUE' in x or 'FX3_' in x and ('COMMIT' in x or 'NATIVE_FREE' in x))]
locks=[]
for item in state['locks']:
 with open(item['path'],'rb') as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN);locks.append({'path':item['path'],'released_verified':True})
try:os.kill(receipt['qemu_pid'],0);absent=False
except ProcessLookupError:absent=True
snapshots=[]
for n in (1,2,3):
 a=next((i for i,x in enumerate(ls) if f'FX3_AP_SNAPSHOT_{n}_BEGIN' in x),len(ls));b=next((i for i,x in enumerate(ls) if f'FX3_AP_SNAPSHOT_{n}_END' in x),len(ls));snapshots.append({'turn':n,'complete':b<len(ls),'im_process':[{ 'line':i+1,'text':x} for i,x in enumerate(ls) if a<i<b and ('FX3_AP_IM_PROCESS=' in x or '/usr/bin/im.elf' in x and 'r-xp' in x)]})
v={'run':str(run),'stage':stage,'qemu_exit':receipt['qemu_exit'],'process_reaped':receipt['process_reaped'],'host_pid_absent':absent,'inputs_unchanged':receipt['inputs_unchanged'],'missing_markers':[k for k,v in receipt['markers'].items() if not v],'host_observer_error':receipt['host_observer_error'],'locks':locks,'snapshots':snapshots,'im_alive_last_snapshot':bool(snapshots[-1]['im_process']),'symbol_errors':matches('symbol lookup error'),'icrypt':matches('FX3_ICRYPT_HAS'),'imdb_crypt':matches('FX3_IMDB_LOAD name=libInfraCrypt.so'),'adf':matches('FX3_ADF_MUTED'),'gpe':matches('FX3_GPE_CMD'),'uniform':matches('FX3_GPE_UNIFORM'),'post_11a_timeline':timeline}
p=R/f'{stage.lower()}-review.json';p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');state.update(phase=stage+'_REVIEWED',missing_markers=v['missing_markers'],latest_stage_summary=str(p),im_alive_last_snapshot=v['im_alive_last_snapshot']);
if len(sys.argv)<=2:(R/'STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v[k] for k in ['run','qemu_exit','process_reaped','host_pid_absent','inputs_unchanged','missing_markers','im_alive_last_snapshot','symbol_errors','icrypt','imdb_crypt']},ensure_ascii=False,indent=2))
