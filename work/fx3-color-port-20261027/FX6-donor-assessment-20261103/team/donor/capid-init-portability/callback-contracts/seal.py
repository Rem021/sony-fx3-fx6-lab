from pathlib import Path
import json,re,hashlib
H=Path(__file__).resolve().parent;B=H.parent
ns={'__file__':str(B/'analyze.py')};exec((B/'analyze.py').read_text().split('E={k:ELF')[0],ns)
E={k:ns['ELF'](p) for k,p in ns['P'].items()};sha=lambda b:hashlib.sha256(b).hexdigest()
parent=json.loads((B/'delivery-manifest.json').read_text())
for n,v in parent['files'].items():assert sha((B/n).read_bytes())==v['sha256'],n
inputs=json.loads((H/'inputs.json').read_text())
for k,e in E.items():assert sha(e.b)==inputs['hashes'][k],k
words={}
for f in H.glob('*.txt'):
 key=next((k for k in E if f.name.startswith(k)),None)
 if key is None and f.name.startswith(('fx3-','dispatch-')):key='fx3_mpr'
 if key is None:continue
 arr=[]
 for line in f.read_text().splitlines():
  m=re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+',line)
  if m:
   mp=E[key].mapping(int(m[1],16));assert int.from_bytes(bytes.fromhex(mp['bytes_le']),'little')==int(m[2],16),(f,line)
   arr.append(mp)
 words[f.name]={'binary':key,'words':arr}
for f in H.glob('*.json'):json.loads(f.read_text())
for f in H.glob('*.py'):compile(f.read_text(),str(f),'exec')
files={f.name:{'sha256':sha(f.read_bytes()),'size':f.stat().st_size} for f in sorted(H.iterdir()) if f.is_file() and f.name!='receipt.json'}
r={'status':'STATIC_COVERAGE_DELIVERED_ADAPTER_BLOCKED','fixed_sha256':inputs['hashes'],'parent_delivery_all_files_unchanged':True,'machine_words_verified':words,'artifacts':files,'full_callback_contracts_passed':0,'coverage':{'shared':57,'fx6_nonzero_targets':46,'fx6_original_zero_slots':11,'zero_slots_with_dispatch_null_guard':9,'zero_slots_consumer_unknown':2,'ret_only_leaf':4,'event_symbols_located':54,'sync_exported_functions_depth5':85,'unresolved_frontier':233},'no_vm_no_firmware_patch':True}
(H/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print({'verified_original_parent_files':len(parent['files']),'verified_instruction_words':sum(len(v['words']) for v in words.values()),'artifacts':len(files)})
