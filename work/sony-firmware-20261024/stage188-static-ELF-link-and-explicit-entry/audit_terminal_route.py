"""Read-only extraction and static terminal route audit. No firmware execution."""
from pathlib import Path
from hashlib import sha256
import importlib.util,io,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
spec=importlib.util.spec_from_file_location('fixed_fx3_static_reader',BASE/'stage7-entry/firmware/static_service.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
blob,path=m.read('/usr/lib/libpro00.so')
assert sha256(blob).hexdigest()=='771749c2397c48e9a3444a7562a8f8e2773abf59a262276c2b225cc415ac9403'
elf=ELFFile(io.BytesIO(blob));symbols={s.name:s for s in elf.get_section_by_name('.dynsym').iter_symbols() if s.name}
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def read(elf,raw,at,n):
 s=next(s for s in elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=at and at+n<=s['p_vaddr']+s['p_filesz'])
 return raw[s['p_offset']+at-s['p_vaddr']:s['p_offset']+at-s['p_vaddr']+n]
s=symbols['command00F1'];code=read(elf,blob,s['st_value'],s['st_size'])
assert code.hex()=='20008052c0035fd6'
meta=BASE/'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/libsencore.so-metadata.json'
d=json.loads(meta.read_text());raw=Path(d['path']).read_bytes();assert sha256(raw).hexdigest()==d['sha256']=='a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
e=ELFFile(io.BytesIO(raw));flag=next(x for x in d['symbols'] if x['name']=='terminal_change_function_is_disabled')
assert read(e,raw,flag['va'],1)==b'\x01'
for address,name in [(0x6aeb0,'terminal_change_function_is_disabled'),(0x6ae60,'_ZTV8NoAction')]:
 assert next(x for x in d['relocations'] if x['va']==address)['name']==name
assert read(e,raw,0xc14c,12).hex()=='e2079f1a215847f922000039'
assert read(e,raw,0xd4e8,16).hex()=='00404039202c0039000080d2c0035fd6'
# TERM_MODE appears in command-table records; preserve exact destination only.
rows=[]
for name_at in [0x265ac,0x45094]:
 record=read(e,raw,name_at-8,72);mid,family,command=struct.unpack_from('<IHH',record)
 rows.append({'record_VA':name_at-8,'message_destination':hex(mid),'family':hex(family),'command':hex(command),'original_hex':record.hex()})
report={'status':'STATIC_TERMINAL_FACTORY_AUDIT_NOT_CHANNEL_PROOF',
 'core_library_sha256':d['sha256'],'plugin_sha256':sha256(blob).hexdigest(),'plugin_image_path':path,
 'product_info_handler':{'VA':0xeabc,'bytes':236,'source_sha256':sha256(read(e,raw,0xeabc,236)).hexdigest()},
 'default_terminal_disabled_byte':1,
 'auth_onComplete_level3_clears_disabled_flag':{'VA':0xc108,'bytes':124,'source_sha256':sha256(read(e,raw,0xc108,124)).hexdigest(),
    'not_claiming_runtime_flag_stays_disabled':True},
 'disabled_branch_NoAction_response':{'value':1,'DoExecute_VA':0xd4e8,'bytes':16,'source_hex':read(e,raw,0xd4e8,16).hex()},
 'enabled_branch_plugin_command00F1':{'VA':s['st_value'],'bytes':s['st_size'],'original_hex':code.hex(),
    'instructions':[i.mnemonic+' '+i.op_str for i in md.disasm(code,s['st_value'])],'returns_response_one_with_no_other_instructions':True},
 'adjust_TERM_MODE_records':rows,'adjust_downstream_effect_or_AP_shell_not_proven':True,
 'real_USB_terminal_endpoint_or_prompt_observed':False,'original_Sony_code_loaded_or_executed':False,'new_camera_operations':0}
with (HERE/'terminal-route-review.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'command00F1_only_returns_one':True,'level3_can_clear_flag':True,'adjust_TERM_MODE':rows[0]['message_destination'],'no_shell_proof':True,'new_camera_operations':0}))
