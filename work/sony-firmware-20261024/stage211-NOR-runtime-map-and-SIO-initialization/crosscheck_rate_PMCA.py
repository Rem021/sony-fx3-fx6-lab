"""Pinned host-only BK4 parser crosscheck on read-only memory, no USB modules."""
from pathlib import Path
from hashlib import sha256
import importlib.util,io,json,sys,types
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];ref=B/'stage207-Backup-template-and-GPIO-config'
cap=json.loads((ref/'format-source-capture.json').read_text())
for row in cap['files']:assert sha256((R/row['output']).read_bytes()).hexdigest()==row['sha256']
root=ref/'reference/pmca/pmca';name='fx3_rate211';pkg=types.ModuleType(name);pkg.__path__=[str(root)];sys.modules[name]=pkg
spec=importlib.util.spec_from_file_location(name+'.backup',root/'backup/__init__.py',submodule_search_locations=[str(root/'backup')]);m=importlib.util.module_from_spec(spec);sys.modules[name+'.backup']=m;spec.loader.exec_module(m)
results=json.loads((H/'SIO-Backup-property-results.json').read_text());checks=[]
for t in results['templates']:
 raw=(R/t['source_path']).read_bytes();assert sha256(raw).hexdigest()==t['source_sha256']
 for rec in t['records']:
  a=rec['offset'];f=io.BufferedReader(io.BytesIO(raw[a:a+rec['record_bytes']]))
  assert not f.writable();bk=m.BackupFile(f)
  for p in rec['selected_properties']:
   assert p['present'];v=bk.getProperty(int(p['id'],16));assert len(v.data)==4 and int.from_bytes(v.data,'little')==p['value_u32'] and v.attr==p['attribute']
   checks.append(dict(template=Path(t['template']).name,record_offset=a,ID=p['id'],match=True))
  f.close()
assert len(checks)==154
out=dict(status='PASS_PINNED_PMCA_READONLY_154_PROPERTY_CROSSCHECK',source_commit=cap['commit'],records=22,cases=len(checks),checks=checks,host_parser_modules_executed=['pmca.backup','pmca.util'],buffers_readonly=True,USB_modules_loaded=False,source_files_modified=False,Sony_code_or_guest_execution=False,root_or_device_operations=0)
(H/'PMCA-rate-crosscheck.json').open('x').write(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(records=22,property_cases=len(checks),all_match=True,actual_device_operations=0)))
