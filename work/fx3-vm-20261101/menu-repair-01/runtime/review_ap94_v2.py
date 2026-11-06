from pathlib import Path
import json,re,sys,subprocess,hashlib,collections
R=Path(__file__).resolve().parent;name=sys.argv[1];run=R/'runs'/name;subprocess.run([sys.executable,str(R/'review_cp88.py'),name],check=True);p=R/(name+'-review.json');v=json.loads(p.read_text());serial=(run/'serial.log').read_bytes().decode(errors='replace');lines=serial.split('\n');receipt=json.loads((run/'receipt.json').read_text());markers=[]
for i,line in enumerate(lines):
 if any(k in line for k in ['FX3_RM_','FX3_MEDIA_','FX3_SYNTH_KEY','FX3_KEY_INPUT_RECV','FX3_KEY93_','FX3_KEY_CACHE']):
  m=re.search(r'(FX3_[A-Z0-9_]+) ',line)
  if m:markers.append({'LF_line':i+1,'marker':m[1],'fields':dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',line[m.start():])),'text':line.rstrip('\r')})
by=collections.defaultdict(list)
for x in markers:by[x['marker']].append(x)
raw=[x for x in markers if x['marker'] in ['FX3_RM_RAW','FX3_MEDIA_RAW','FX3_MEDIA_OWNED_RAW']];cfg=json.loads((R.parents[1]/'lead-claude/audits/rm-media-service/rm-media-proof.json').read_text())['configuration_projection']['payload_hex'];native_replies=[x for x in raw if x['fields'].get('tag')=='RM_NATIVE_REPLY_BEFORE_FREE'];requests=[x for x in raw if x['marker']=='FX3_RM_RAW' and x['fields'].get('tag')=='REQUEST'];replybytes=[x for x in raw if x['marker']=='FX3_RM_RAW' and x['fields'].get('tag')=='REPLY'];checks=[]
invalid_raw=[]
def decoded(record):
 try:
  value=bytes.fromhex(record['fields']['raw']);assert len(value)==int(record['fields']['bytes'],0);return value
 except (ValueError,KeyError,AssertionError):
  invalid_raw.append({'LF_line':record['LF_line'],'marker':record['marker'],'tag':record['fields'].get('tag'),'declared_bytes':record['fields'].get('bytes'),'raw':record['fields'].get('raw'),'scope':'corrupt/truncated/interleaved serialized record, not repaired'});return None
for req in requests:
 a=decoded(req)
 if a is None:continue
 matched=None;b=None
 for reply in native_replies+replybytes:
  candidate=decoded(reply)
  if candidate is not None and a[:6]==candidate[:6] and a[8:12]==candidate[8:12] and a[16:24]==candidate[16:24]:matched=reply;b=candidate;break
 if matched is None:
  checks.append({'request_LF_line':req['LF_line'],'matching_complete_reply_found':False});continue
 cmd=int.from_bytes(a[:4],'little');checks.append({'command':cmd,'request_LF_line':req['LF_line'],'reply_LF_line':matched['LF_line'],'reply_evidence_marker':matched['marker'],'reply_tag':matched['fields'].get('tag'),'request_bytes':len(a),'reply_bytes':len(b),'same_header_except_length_and_status':a[:6]==b[:6] and a[8:12]==b[8:12] and a[16:24]==b[16:24],'reply_queue_current_request':hex(int.from_bytes(b[8:12],'little')),'status':hex(int.from_bytes(b[12:16],'little')),'payload_matches':b[24:].hex()==cfg if cmd==9 else b[24:]==a[24:]})

branches=[x for x in by['FX3_MEDIA_START_BRANCH']];notifies=by['FX3_MEDIA_NOTIFY'];mounts=by['FX3_MEDIA_MOUNT_ENTER'];timeout=by['FX3_MEDIA_INIT_TIMEOUT'];keys=by['FX3_SYNTH_KEY'];rm_unknown=by['FX3_RM_UNKNOWN'];newreject=[x for x in markers if 'REJECT' in x['marker']];params={}
for x in by['FX3_MEDIA_PARAM']:params.setdefault(x['fields']['id'],[]).append(x)
allocs={x['fields']['lease']:x for x in by['FX3_RM_ALLOC']};frees=collections.defaultdict(list)
for x in by['FX3_RM_NATIVE_FREE']:frees[x['fields']['lease']].append(x)
ledger=[{'lease':k,'alloc':a,'native_free':frees[k],'exactly_once_free0':len(frees[k])==1 and frees[k][0]['fields'].get('result')=='0'} for k,a in allocs.items()]
obs={'invalid_raw_records_not_repaired':invalid_raw,'counts':dict(collections.Counter(x['marker'] for x in markers)),'markers':markers,'request_reply_checks':checks,'native_replies_before_free':native_replies,'actual_FRONT':by['FX3_MEDIA_FRONT'],'front_body_records':[x for x in raw if x['fields'].get('tag')=='FRONT_FULL_BODY'],'native_Start_records':[x for x in raw if x['fields'].get('tag')=='START_INITIAL_RECORD'],'native_Start_branches':branches,'native_notifications':notifies,'mount_attempts':mounts,'init_timeouts':timeout,'unknown_RM':rm_unknown,'new_rejections':newreject,'parameters':params,'synthetic_key_events':keys,'input_received':by['FX3_KEY_INPUT_RECV'],'allocation_native_free_ledger':ledger,'all_allocated_leases_native_free_once0':bool(ledger) and all(x['exactly_once_free0'] for x in ledger),'stageA':json.loads((run/'ap94-phaseA.json').read_text()) if (run/'ap94-phaseA.json').exists() else None,'host_gate_writes':json.loads((run/'ap93-host-input-gate.json').read_text()) if (run/'ap93-host-input-gate.json').exists() else [],'step_readbacks':json.loads((run/'ap94-step-readbacks.json').read_text()) if (run/'ap94-step-readbacks.json').exists() else [],'no_card_pixels_verified':False,'shooting_standby_verified':False,'MENU_verified':False};op=R/(name+'-rm-input-observation.json');op.write_text(json.dumps(obs,ensure_ascii=False,indent=2)+'\n')
gpe=[];incomplete=[]
for i,line in enumerate(lines):
 if 'FX3_GPE_CMD op=' not in line:continue
 f=dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',line[line.index('FX3_GPE_CMD'):]))
 if not all(k in f for k in ['op','seq','fmt','src_fmt','flags','dst_phys','src_phys','result','reason']):incomplete.append({'LF_line':i+1,'text':line});continue
 try:
  for k in ['seq','fmt','src_fmt','flags','dst_phys','src_phys','result','reason']:f[k]=int(f[k],0)
 except ValueError:
  incomplete.append({'LF_line':i+1,'text':line,'numeric_field_invalid_serial_interleaving':True});continue
 if f['src_fmt'] not in [0,1,2] or f['fmt'] not in [0,1]:
  incomplete.append({'LF_line':i+1,'text':line,'unsupported_numeric_format_due_to_serial_interleaving':True});continue
 f['LF_line']=i+1;f['dst_in_545']=0x43feb5000<=f['dst_phys']<0x43fff5000;f['src_in_545']=0x43feb5000<=f['src_phys']<0x43fff5000;gpe.append(f)
groups=collections.Counter((f['op'],f['fmt'],f['src_fmt'],f['flags'],f['dst_in_545'],f['src_in_545'],f['result']) for f in gpe);gs={'complete':len(gpe),'incomplete':incomplete,'records':gpe,'groups':[dict(zip(['op','dst_fmt','src_fmt','flags','dst_in_545','src_in_545','result','count'],[*k,n])) for k,n in sorted(groups.items())]};gp=R/(name+'-gpe-statistics.json');gp.write_text(json.dumps(gs,indent=2)+'\n');pixels={};bp=run/'gpe-surface-545.bin'
if bp.exists():
 data=bp.read_bytes()[0x100:0x100+640*480*2];unique=len({data[j:j+2] for j in range(0,len(data),2)});pixels={'physical':'0x43feb5100','bytes':len(data),'geometry':[640,480],'logical_fmt':0,'unique_pixels':unique,'sha256':hashlib.sha256(data).hexdigest(),'independent_QMP':True}
 if unique>1:
  from PIL import Image
  rgba=[tuple(((int.from_bytes(data[j:j+2],'little')>>k)&15)*17 for k in [12,8,4,0]) for j in range(0,len(data),2)];img=Image.new('RGBA',(640,480));img.putdata(rgba);png=run/'ap94-legacy545-QMP-logical-fmt0.png';assert not png.exists();img.save(png);pixels['PNG']=str(png)
v.update(AP94_executed=True,AP89_boot_executed=True,symbol_lookup_error='symbol lookup error:' in serial,RM_input_observation=str(op),GPE_statistics=str(gp),QMP_readback=pixels,original_menu_verified=False,no_card_or_standby_pixels_verified=False,synthetic_key_events=len(keys),native_init_timeout_count=len(timeout),native_Mount_count=len(mounts),RM_unknown_count=len(rm_unknown));p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'run':name,'receipt':{k:v[k] for k in ['duration_seconds','qemu_exit','process_reaped','PID_absent','inputs_unchanged','missing_markers_combined_serial_and_printk','im_alive_last_complete_maps','early_stop_reason']},'request_reply_checks':checks,'native_Start_branches':[(x['LF_line'],x['fields']['state']) for x in branches],'notifications':[x['fields'] for x in notifies],'native_Mount_count':len(mounts),'native_timeouts':len(timeout),'all_leases_free_once0':obs['all_allocated_leases_native_free_once0'],'key_events':len(keys),'gpe':gs['groups'],'pixels':pixels},ensure_ascii=False,indent=2))
