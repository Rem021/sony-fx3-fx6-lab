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
  img.putdata(rgba);out=run/'ap90-QMP-logical-fmt0.png';assert not out.exists();img.save(out);px['PNG']=str(out);px['PNG_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
v['QMP_pixel_readback']=px
v['original_UUD_decision']=[{'LF_line':i+1,'text':x} for i,x in enumerate(lines) if 'FX3_AP89_UUD_DECISION' in x]
p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'run':name,'GPE_groups':stats['groups'],'classes':stats['actual_classes'],'resources':len(v['resource_registrations']),'pixels':px},ensure_ascii=False))
