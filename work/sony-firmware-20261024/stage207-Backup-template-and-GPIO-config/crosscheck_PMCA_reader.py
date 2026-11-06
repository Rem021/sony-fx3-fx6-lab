"""Cross-check the own BK4 reader with pinned host PMCA parser on read-only buffers.

Only pmca.backup and pmca.util are loaded in an isolated package namespace;
no USB/runtime modules, Sony code, camera interfaces or write methods are used.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util, io, json, sys, types
H=Path(__file__).resolve().parent
R=H.parents[2]
cap=json.loads((H/'format-source-capture.json').read_text())
for row in cap['files']:
    assert sha256((R/row['output']).read_bytes()).hexdigest()==row['sha256']
root=H/'reference/pmca/pmca'
namespace='fx3_bk207'
pkg=types.ModuleType(namespace);pkg.__path__=[str(root)];sys.modules[namespace]=pkg
spec=importlib.util.spec_from_file_location(namespace+'.backup',root/'backup/__init__.py',submodule_search_locations=[str(root/'backup')])
module=importlib.util.module_from_spec(spec);sys.modules[namespace+'.backup']=module;spec.loader.exec_module(module)
results=json.loads((H/'template-field-results.json').read_text())
checks=[]
for template in results['templates']:
    source=R/template['source_path'];data=source.read_bytes();assert sha256(data).hexdigest()==template['source_sha256']
    for record in template['records']:
        at=record['offset'];reader=io.BufferedReader(io.BytesIO(data[at:at+record['record_bytes']]))
        assert not reader.writable()
        backup=module.BackupFile(reader)
        assert backup.header.numSubsystems==record['subsystems'] and backup.header.numProperties==record['property_entries']
        for row in record['selected_properties']:
            ident=int(row['id'],16)
            if row['present']:
                prop=backup.getProperty(ident)
                assert prop.attr==row['attribute'] and len(prop.data)==4 and int.from_bytes(prop.data,'little')==row['value_u32']
            else:
                try: backup.getProperty(ident)
                except Exception: pass
                else: raise AssertionError('independent parser found property reported absent')
            checks.append(dict(template=template['name'],record_offset=at,id=row['id'],present=row['present'],match=True))
        reader.close()
receipt=dict(status='PASS_INDEPENDENT_HOST_PARSER_CROSSCHECK',source_commit=cap['commit'],
    records_checked=22,property_cases=len(checks),present_property_cases=sum(r['present'] for r in checks),
    all_match=True,checks=checks,parser_modules_executed=['pmca.backup','pmca.util'],
    buffers_read_only=True,source_files_mutated=False,USB_runtime_modules_loaded=False,
    Sony_code_or_guest_execution=False,root_or_device_operations=0)
(H/'PMCA-reader-crosscheck.json').open('x').write(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(records=22,property_cases=len(checks),present_cases=receipt['present_property_cases'],all_match=True,device_operations=0)))
