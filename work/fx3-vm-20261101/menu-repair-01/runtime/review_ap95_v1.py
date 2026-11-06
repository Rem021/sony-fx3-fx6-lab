from pathlib import Path
import json,re,sys,hashlib,os,fcntl,collections,datetime,subprocess
R=Path(__file__).resolve().parent;run=R/'runs'/sys.argv[1];p=run/'receipt.json';r=json.loads(p.read_text());serial=(run/'serial.log').read_text(errors='replace');lines=serial.split('\n');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
try:os.kill(r['qemu_pid'],0);absent=False
except ProcessLookupError:absent=True
locks=[]
for p in [R/'.run.lock',R.parents[3]/'outputs/fx3-vm/.run.lock']:
 with p.open('rb') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True;fcntl.flock(f,fcntl.LOCK_UN)
  except BlockingIOError:free=False
 locks.append({'path':str(p),'free_at_review':free})
inputs=[{'path':x['path'],'matches':sha(Path(x['path']))==x['sha256']} for x in r['input_checks']]
end=[]
for m in re.finditer(r'FX3_AP_IM_ENDMAPS_(\d+)_BEGIN\r?\n(.*?)FX3_AP_IM_ENDMAPS_\1_END',serial,re.S):
 maps=[l for l in m[2].splitlines() if '/usr/bin/im.elf' in l]
 if len(maps)==3:
  t=re.search(r'(\d+\.\d+) \d+\.\d+',m[2]);end.append({'pid':int(m[1]),'uptime':float(t[1]) if t else None,'LF_line':serial[:m.start()].count('\n')+1,'maps':maps})
def records(marker):
 out=[]
 for i,l in enumerate(lines):
  if marker in l:out.append({'LF_line':i+1,'fields':dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',l[l.index(marker):])),'text':l})
 return out
keys=records('FX3_SYNTH_KEY ');recvs=records('FX3_KEY_INPUT_RECV ');done=records('FX3_KEY95_STEP_DONE ');gate=json.loads((run/'ap95-host-input-gate.json').read_text());steps=json.loads((run/'ap95-step-readbacks.json').read_text());captures=[]
for s in steps:
 captures.append({'step':s['step'],'key':s['key'],'PNG':s.get('PNG'),'error':s.get('error'),'raw_sha_matches':sha(Path(s['raw']))==s['raw_sha256'] if s.get('raw') else False,'png_sha_matches':sha(Path(s['PNG']))==s['PNG_sha256'] if s.get('PNG') else False,'native_ring_matches':s.get('matches_committed_ring'),'sequence':s.get('latest_native_committed_sequence')})
allocs=records('FX3_RM_ALLOC ');frees=records('FX3_RM_NATIVE_FREE ');leases=[]
for a in allocs:
 lease=a['fields'].get('lease');f=[x for x in frees if x['fields'].get('lease')==lease];leases.append({'lease':lease,'allocation':a,'frees':f,'once_free0':len(f)==1 and f[0]['fields'].get('result')=='0'})
gpe=[];incomplete=[]
for i,l in enumerate(lines):
 if 'FX3_GPE_CMD ' not in l:continue
 f=dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',l[l.index('FX3_GPE_CMD '):]))
 try:
  for key in ['seq','result','reason']:f[key]=int(f[key],0)
 except (ValueError,KeyError):incomplete.append({'LF_line':i+1,'text':l});continue
 gpe.append({'LF_line':i+1,'fields':f})
rejected=[x for x in gpe if x['fields']['result']];fatal=[x for x in ['Kernel panic','Entering exception monitor.','Unhandled fault:','symbol lookup error:'] if x in serial]
health=r['qemu_exit']==0 and r['process_reaped'] and absent and all(x['free_at_review'] for x in locks) and all(x['matches'] for x in inputs) and not r['host_observer_error'] and not fatal and all(r['markers'].values()) and bool(end)
raw20=[]
for x in records('FX3_RM_RAW '):
 if x['fields'].get('tag')=='SYNTH_KEY20':raw20.append(x)
output={'run':str(run),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'health_pass':health,'duration_seconds':r['duration_seconds'],'requested_seconds':r['requested_seconds'],'qemu_exit':r['qemu_exit'],'process_reaped':r['process_reaped'],'PID_absent':absent,'locks':locks,'input_SHA_reverified':inputs,'missing_markers':[k for k,v in r['markers'].items() if not v],'fatal_markers':fatal,'early_stop_reason':r['early_stop_reason'],'im_alive_last_complete_maps':end[-1] if end else None,'host_gate_commands':len(gate),'guest_done_steps':len(done),'sent_events':len(keys),'received_events':len(recvs),'keys':keys,'key_receipts':recvs,'done':done,'raw20':raw20,'leases':leases,'all_leases_native_free_once0':bool(leases) and all(x['once_free0'] for x in leases),'captures':captures,'capture_count':len(captures),'GPE_complete_records':len(gpe),'GPE_incomplete_records':incomplete,'GPE_nonzero_records':rejected,'screens':records('FX3_AP89_SCREEN_OPEN_ENTER '),'RM_native_branches':records('FX3_MEDIA_START_BRANCH '),'RM_native_notifications':records('FX3_MEDIA_NOTIFY '),'RM_mount_count':len(records('FX3_MEDIA_MOUNT_ENTER ')),'RM_timeout_count':len(records('FX3_MEDIA_INIT_TIMEOUT ')),'host_command_not_proven_sent':[g for g in gate if not any(x['fields'].get('step')==str(g['step']) for x in keys)],'standby_verified':False,'menu_verified':False,'scope':'Independent read-only review; no changes inside completed runs; raw LF interleaving retained, not global lossless proof'}
p=R/(run.name+'-ap95-review.json');p.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:output[k] for k in ['health_pass','duration_seconds','qemu_exit','PID_absent','missing_markers','guest_done_steps','sent_events','received_events','capture_count','GPE_complete_records','all_leases_native_free_once0']},indent=2));print(p)
