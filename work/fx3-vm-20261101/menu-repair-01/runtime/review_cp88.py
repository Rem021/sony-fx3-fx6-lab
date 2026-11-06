from pathlib import Path
import json,re,hashlib,os,sys,fcntl,datetime
R=Path(__file__).resolve().parent;name=sys.argv[1];run=R/'runs'/name;r=json.loads((run/'receipt.json').read_text());serial=(run/'serial.log').read_bytes().decode(errors='replace');kernel=(run/'printk-decoded.txt').read_text();combined=serial+'\n'+kernel;c=json.loads(Path(r['candidate']).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
try:os.kill(r['qemu_pid'],0);absent=False
except ProcessLookupError:absent=True
locks=[]
for p in [Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/.run.lock'),R/'.run.lock']:
 with p.open('a+b') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True;fcntl.flock(f,fcntl.LOCK_UN)
  except BlockingIOError:free=False
 locks.append({'path':str(p),'free_at_review':free})
lines=serial.split('\n');klines=kernel.split('\n')
def records(pattern,text=lines):return [{'LF_line':i+1,'text':line} for i,line in enumerate(text) if re.search(pattern,line)]
end=[]
for m in re.finditer(r'FX3_AP_IM_ENDMAPS_(\d+)_BEGIN\r?\n(.*?)FX3_AP_IM_ENDMAPS_\1_END',serial,re.S):
 if '/usr/bin/im.elf' in m.group(2):
  uptime=re.search(r'(\d+\.\d+) \d+\.\d+',m.group(2));end.append({'pid':int(m.group(1)),'uptime':float(uptime.group(1)) if uptime else None,'byte_offset':m.start(),'im_maps_lines':[l for l in m.group(2).splitlines() if '/usr/bin/im.elf' in l]})
req=[];started=False
for i,line in enumerate(lines):
 if 'FX3_' in line and ('op=0x11a' in line or ('0d201a01' in line and 'REQUEST' in line)):started=True
 if started and any(k in line for k in ['REQUEST','Skip snd','BACKUP_CP_','BACKUP_NATIVE_RESET','BOOT_QUEUE_SEND','SCREEN_OPEN_ENTER','FX3_GPE_CMD','Fatal','REJECT','RETRY']):req.append({'LF_line':i+1,'text':line})
timeline=R/(name+'-post11a-requests.json');timeline.write_text(json.dumps({'run':name,'scope':'All matching savedrecords afterfirstcaptured11a; bounded upstream trace and serial interleaving are notgloballylossless','count':len(req),'records':req},ensure_ascii=False,indent=2)+'\n')
backup=run/'backup-after-shutdown.bin';snapshot={'path':str(backup),'exists':backup.exists(),'scope':'QuiescedreservedRAM; filenamealone isnotshutdowncompletion'}
if backup.exists():
 b=backup.read_bytes();snapshot.update(bytes=len(b),sha256=sha(backup),CP_second_bank_sha256=hashlib.sha256(b[0xd2000:0xd2000+1369580]).hexdigest(),CP_second_bank_matches_pinned_seed=hashlib.sha256(b[0xd2000:0xd2000+1369580]).hexdigest()=='5dc5883fb86d87d14c1c3d530d4d65d903361c189a64edabcd1f636df289f5b7')
out={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run':name,'receipt_sha256':sha(run/'receipt.json'),'duration_seconds':r['duration_seconds'],'qemu_exit':r['qemu_exit'],'process_reaped':r['process_reaped'],'PID_absent':absent,'inputs_unchanged':r['inputs_unchanged'],'host_observer_error':r['host_observer_error'],'locks':locks,'fatal_markers':r['guest_exception_markers'],'missing_markers_combined_serial_and_printk':[m for m in c['required_markers'] if m not in combined],'receipt_serial_only_missing':[m for m,v in r['markers'].items() if not v],'marker_evidence_scope':'Rawserial flags retained; kernelprintkring independentlyrecovers interleavedkernelmarkers, neverrewritesreceipt','im_alive_last_complete_maps':end[-1] if end else None,'im_complete_maps_samples':len(end),'CP_kernel_records':records(r'FX3_BACKUP_CP_',klines),'native_reset_API_records':records(r'FX3_BACKUP_NATIVE_RESET'),'screen_records':records(r'SCREEN_OPEN_ENTER|open screen:'),'native_power_event_records':records(r'BOOT_QUEUE_SEND.*raw=(2c|2d|2e|72|74|ad)000300'),'GPE_records':records(r'FX3_GPE_CMD '),'backup_snapshot':snapshot,'timeline':str(timeline),'original_menu_verified':False,'AP89_boot_executed':False,'early_stop_reason':r['early_stop_reason']}
path=R/(name+'-review.json');path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(path);print(json.dumps({k:out[k] for k in ['qemu_exit','process_reaped','PID_absent','inputs_unchanged','missing_markers_combined_serial_and_printk','receipt_serial_only_missing','im_alive_last_complete_maps','early_stop_reason']},ensure_ascii=False))
