import sys
sys.dont_write_bytecode=True
from extract import *
import struct
prior={}
for d,manifest,field in [(B,'delivery-manifest.json','files'),(B/'callback-contracts','receipt.json','artifacts')]:
 m=json.loads((d/manifest).read_text())
 for f,v in m[field].items():assert sha((d/f).read_bytes())==v['sha256'],str(d/f)
 prior[str(d)]={'verified_files':len(m[field]),'manifest_sha256':sha((d/manifest).read_bytes())}
words={}
for f in H.glob('*.txt'):
 k=next((k for k in E if f.name.startswith(k)),None)
 if f.name=='mpr-event-1026-survey.txt':k='fx3_mpr'
 if k is None:continue
 arr=[]
 for line in f.read_text().splitlines():
  m=re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+',line)
  if not m:continue
  x=E[k].mapping(int(m[1],16));assert int.from_bytes(bytes.fromhex(x['bytes_le']),'little')==int(m[2],16),(f,line)
  arr.append(x)
 words[f.name]={'binary':k,'words':arr}
rtti=[]
for k,vas in [('fx6_ap',[0x2ec30e0,0x2ec30f0,0x2ec3140]),('fx3_ap',[0x46e8a40,0x46e8a50,0x46e8aa0])]:
 for a in vas:
  ptr=int.from_bytes(bytes.fromhex(E[k].mapping(a+8,8)['bytes_le']),'little');off=int(E[k].mapping(ptr)['fileoff'],16);name=E[k].b[off:E[k].b.index(b'\0',off)].decode();rtti.append({'binary':k,'typeinfo_name_pointer':E[k].mapping(a+8,8),'name':name,'name_bytes':E[k].mapping(ptr,len(name)+1)})
for f in H.glob('*.json'):json.loads(f.read_text())
for f in H.glob('*.py'):compile(f.read_text(),str(f),'exec')
files={f.name:{'sha256':sha(f.read_bytes()),'size':f.stat().st_size} for f in sorted(H.iterdir()) if f.is_file() and f.name!='receipt.json'}
r={'status':'LOCAL_POWERON_EVENT_CONTRACT_PROVEN_OFFLINE_RUNTIME_UNTESTED','fixed_inputs':{k:{'path':str(P[k]),'sha256':sha(e.b)} for k,e in E.items()},'old_deliveries_unchanged':prior,'word_mappings':words,'RTTI':rtti,'result_tables':{'fx3':E['fx3_ap'].mapping(0x39899b0,12),'fx6':E['fx6_ap'].mapping(0x2622138,18)},'artifacts':files,'contract':{'source_event':'0x1026','destination_event':'0x102d','length':12,'echo':'u32 copied unchanged, compared to pending request','result':'only producer-generated zero accepted','callback_object_offsets':['0x3e4','0x8'],'runtime_observation':False,'firmware_patch':False}}
(H/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print({'verified_old_files':sum(v['verified_files'] for v in prior.values()),'verified_words':sum(len(v['words']) for v in words.values()),'artifacts':len(files),'result_tables':r['result_tables']})
