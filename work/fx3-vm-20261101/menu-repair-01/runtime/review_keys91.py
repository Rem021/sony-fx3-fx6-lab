from pathlib import Path
import json,re,sys,hashlib,collections,subprocess
R=Path(__file__).resolve().parent;name=sys.argv[1];run=R/'runs'/name
subprocess.run([sys.executable,str(R/'review_cp88.py'),name],check=True)
p=R/(name+'-review.json');v=json.loads(p.read_text());serial=(run/'serial.log').read_bytes().decode(errors='replace');kernel=(run/'printk-decoded.txt').read_text();lines=serial.split('\n');v['AP89_boot_executed']=True;v['AP90_executed']=True
v['symbol_lookup_error']='symbol lookup error:' in serial+'\n'+kernel
v['resource_registrations']=[{'LF_line':i+1,'text':x} for i,x in enumerate(lines) if 'FX3_GPE_RESOURCE_REGISTER ' in x]
v['resource_parent_rejects']=[{'LF_line':i+1,'text':x} for i,x in enumerate(lines) if 'FX3_GPE_RESOURCE_PARENT_REJECT ' in x]
v['GPE_scope']=[{'LF_line':i+1,'text':x} for i,x in enumerate(lines) if 'FX3_GPE_SCOPE ' in x]
v['subblock_or_compaction_changes_observed']=[x for x in v['GPE_scope'] if 'compaction_or_subblock_change_during_draw=1' in x['text']]
v['subblock_lifetime_compaction_queued_ABA_covered']=False
records=[];incomplete=[]
for i,x in enumerate(lines):
 if 'FX3_GPE_CMD op=' not in x:continue
 fields=dict(re.findall(r'([a-zA-Z_][a-zA-Z_0-9]*)=([^\s]+)',x[x.index('FX3_GPE_CMD'):]))
 if not all(k in fields for k in ['op','seq','fmt','flags','dst_phys','src_phys','result','reason','src_fmt']):incomplete.append({'LF_line':i+1,'text':x});continue
 for k in ['seq','fmt','flags','dst_phys','src_phys','result','reason','src_fmt']:
  try:fields[k]=int(fields[k],0)
  except ValueError:fields[k]=int(fields[k],16)
 for k in ['dst','src']:fields[k+'_address_in_screen_extent']=0x43feb5000<=fields[k+'_phys']<0x43fff5000
 fields['LF_line']=i+1;records.append(fields)
groups=collections.Counter((x['op'],x['fmt'],x['src_fmt'],x['flags'],x['dst_address_in_screen_extent'],x['src_address_in_screen_extent'],x['result'],x['reason']) for x in records)
stats={'scope':'Every complete bound-adapter CMD marker; address columns only, full spans require SCOPE and registry','records':records,'complete':len(records),'incomplete':incomplete,'groups':[dict(zip(['op','dst_fmt','src_fmt','flags','dst_in_screen','src_in_screen','result','reason','count'],[*k,n])) for k,n in sorted(groups.items())]}
raw=[]
for i,x in enumerate(lines):
 m=re.search(r'FX3_GPE_RAW_PARAMS op=BitBlit seq=(\d+) read=1 len=144 raw_hex=([0-9a-f]{288})(?![0-9a-f])',x)
 if m:
  b=bytes.fromhex(m[2]);kind='fmt2_generic' if int.from_bytes(b[92:96],'little')==2 else 'fmt0_stretch' if b[16:24]!=b[72:80] else 'fmt0_generic';raw.append({'LF_line':i+1,'sequence':int(m[1]),'kind':kind,'raw_hex':m[2]})
stats['full_raw']=raw;stats['actual_classes']=dict(collections.Counter(x['kind'] for x in raw));stats['classes_result']=dict(collections.Counter(x['kind']+':'+str(next((r['result'] for r in records if r['seq']==x['sequence']),None)) for x in raw))
statpath=R/(name+'-gpe-statistics.json');statpath.write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n');v['GPE_statistics']=str(statpath)
if (run/'ap89-host-input-readback.json').exists():v['backup_preAP_QMP_input']=json.loads((run/'ap89-host-input-readback.json').read_text())
binfile=run/'gpe-surface-545.bin';px={}
if binfile.exists():
 data=binfile.read_bytes()[0x100:0x100+640*480*2];unique=len({int.from_bytes(data[x:x+2],'little') for x in range(0,len(data),2)});px={'path':str(binfile),'bytes':len(data),'physical':'0x43feb5100','format':0,'geometry':[640,480],'stride_pixels':640,'unique_pixels':unique,'sha256':hashlib.sha256(data).hexdigest(),'independent_QMP_physical_readback':True,'original_menu_input_verified':False}
 if unique>1:
  from PIL import Image
  img=Image.new('RGBA',(640,480));rgba=[]
  for x in range(0,len(data),2):
   n=int.from_bytes(data[x:x+2],'little');rgba.append(tuple(((n>>k)&15)*17 for k in [12,8,4,0]))
  img.putdata(rgba);out=run/'ap91-QMP-logical-fmt0.png';assert not out.exists();img.save(out);px['PNG']=str(out);px['PNG_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
v['QMP_pixel_readback']=px
v['original_UUD_decision']=[{'LF_line':i+1,'text':x} for i,x in enumerate(lines) if 'FX3_AP89_UUD_DECISION' in x]
p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'run':name,'GPE_groups':stats['groups'],'classes':stats['actual_classes'],'resources':len(v['resource_registrations']),'pixels':px},ensure_ascii=False))

# AP91 original input receipts and per-step physical pixels.
import struct
v=json.loads(p.read_text());v['AP91_executed']=True
kinds=['FX3_SYNTH_KEY step=','FX3_KEY_INPUT_RECV ','FX3_KEY_INTERNAL_SEND ','FX3_KEY_EVENT_THREAD_RECV ','FX3_KEY_CACHE ']
key_records=[]
for i,line in enumerate(lines):
 for kind in kinds:
  if kind in line:
   fields=dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',line[line.index(kind):]));key_records.append({'LF_line':i+1,'kind':kind.strip(),'fields':fields,'text':line});break
steps=[]
for step in range(1,7):
 allstep=[x for x in key_records if int(x['fields'].get('step','0'),0)==step];sent=[x for x in allstep if x['kind']=='FX3_SYNTH_KEY step='];phys=[x for x in allstep if x['kind']=='FX3_KEY_INPUT_RECV'];internal=[x for x in allstep if x['kind']=='FX3_KEY_INTERNAL_SEND'];event=[x for x in allstep if x['kind']=='FX3_KEY_EVENT_THREAD_RECV'];cache=[x for x in allstep if x['kind']=='FX3_KEY_CACHE'];row={'step':step,'sent':sent,'physical_receipts':phys,'native_internal_sends':internal,'EventThread_receipts':event,'cache':cache,'application_callback_execution_proven':False}
 if len(sent)==2:
  down=next(x['fields'] for x in sent if x['fields']['status']=='1');up=next(x['fields'] for x in sent if x['fields']['status']=='0');key=int(down['key'],0);row.update(key=hex(key),hold_ms=(int(up['monotonic_ns'])-int(down['monotonic_ns']))/1e6,down_ns=int(down['monotonic_ns']),up_ns=int(up['monotonic_ns']))
  row['all_physical_bytes_match_sent']=len(phys)==2 and all(x['fields'].get('source') in ['0x410025','0x00410025'] and x['fields']['raw_hex']==struct.pack('<5I',key,0,int(x['fields']['status']),0,1).hex() for x in phys)
 steps.append(row)
for j in range(1,len(steps)):
 if 'down_ns' in steps[j] and 'up_ns' in steps[j-1]:steps[j]['gap_from_previous_up_ms']=(steps[j]['down_ns']-steps[j-1]['up_ns'])/1e6
readbacks=json.loads((run/'ap91-step-readbacks.json').read_text()) if (run/'ap91-step-readbacks.json').exists() else []
key_first=min((x['LF_line'] for x in key_records if x['kind']=='FX3_SYNTH_KEY step='),default=10**9)
extra={'scope':'Synthetic originalOSALphysicalkeys; nativephysical/internal/EventThreadreceive observed, actualapplicationcallbackentrynotinstrumented','steps':steps,'records':key_records,'step_readbacks':readbacks,'native_input_errors':[{'LF_line':i+1,'text':line} for i,line in enumerate(lines) if re.search(r'unknown\s+key|invalid\s+from_type',line,re.I)],'screen_records_after_first_key':[x for x in v['screen_records'] if x['LF_line']>key_first],'GPE_commands_after_first_key':[x for x in stats['records'] if x['LF_line']>key_first],'menu_input_feedback_verified':False}
keypath=R/(name+'-key-review.json');keypath.write_text(json.dumps(extra,ensure_ascii=False,indent=2)+'\n');v['AP91_key_review']=str(keypath);v['synthetic_input']=True;v['original_cp_key_detection']=False;v['application_callback_execution_proven']=False;v['input_menu_feedback_verified']=False;p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'key_counts':[{'step':x['step'],'sent':len(x['sent']),'physical':len(x['physical_receipts']),'internal':len(x['native_internal_sends']),'EventThread':len(x['EventThread_receipts']),'hold_ms':x.get('hold_ms')} for x in steps],'step_pngs':len(readbacks),'native_input_errors':len(extra['native_input_errors']),'new_screens':len(extra['screen_records_after_first_key']),'new_GPE':len(extra['GPE_commands_after_first_key'])},ensure_ascii=False))
