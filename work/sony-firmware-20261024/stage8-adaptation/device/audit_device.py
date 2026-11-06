#!/usr/bin/env python3
"""Static ELF/byte audit only. Never load or execute supplied ELF/worker code."""
from pathlib import Path
import json,io,hashlib,struct,sys,importlib.util
from elftools.elf.elffile import ELFFile
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('service_static',P.parents[1]/'stage7-entry/firmware/static_service.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def info(blob):
 e=ELFFile(io.BytesIO(blob));dyn=e.get_section_by_name('.dynamic')
 tags=list(dyn.iter_tags()) if dyn else [];sec=e.get_section_by_name('.dynsym')
 syms=[{'name':s.name,'va':hex(s['st_value']),'size':s['st_size'],'defined':s['st_shndx']!='SHN_UNDEF'} for s in sec.iter_symbols() if s.name] if sec else []
 rel=[]
 for s in e.iter_sections():
  if s['sh_type']=='SHT_RELA':rel.extend(r['r_info_type'] for r in s.iter_relocations())
 return {'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),'machine':e['e_machine'],'type':e['e_type'],'bits':e.elfclass,'little_endian':e.little_endian,
         'entry':hex(e['e_entry']),'has_interpreter':any(s['p_type']=='PT_INTERP' for s in e.iter_segments()),
         'needed':[t.needed for t in tags if t.entry.d_tag=='DT_NEEDED'],
         'DT_INIT':[hex(t.entry.d_val) for t in tags if t.entry.d_tag=='DT_INIT'],
         'imports':[s['name'] for s in syms if not s['defined']],
         'exports':[s for s in syms if s['defined']],'relocation_types':sorted(set(rel)),
         'symbol_version_sections':[s.name for s in e.iter_sections() if 'gnu.version' in s.name],
         'svc0_instruction_count':sum(s.data().count(bytes.fromhex('010000d4')) for s in e.iter_sections() if s['sh_flags']&4)}
def main():
 rec=json.loads((P/'upstream-source-receipt.json').read_text());workers={}
 for a in rec['files']:
  if a['path'].endswith('.so'):
   b=Path(a['temporary']).read_bytes();assert hashlib.sha256(b).hexdigest()==a['sha256'];workers[a['path']]=info(b)
 jir=mod.Native('/usr/lib/libJiritsu.so');jinfo=info(jir.blob)
 assert jinfo['sha256']=='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
 old=json.loads((P.parents[1]/'stage2/write-audit/fx3-jiritsu-static.json').read_text())
 matches=[]
 for f in old['functions']:
  ok=all(jir.data(int(i['address'],16),len(bytes.fromhex(i['bytes']))).hex()==i['bytes'] for i in f['instructions'])
  matches.append({'symbol':f['symbol'],'va':f['address'],'size':f['size'],'all_recorded_instruction_bytes_match':ok})
 syms=[s for s in jir.syms if any(t in s['name'] for t in ['file','Commu','jit_thread','Jiritsu3run'])]
 # Exact packet handler symbol table entries and real branch targets are evidence;
 # calling convention or host acceptance beyond those entries is not emulated.
 funcs=[]
 for n in ['adj_cmd_set_file_path','adj_cmd_set_file2','adj_cmd_get_file2','cmd_file_delete','libCommuTalk','_ZN10IM_JIRITSU10CImJiritsu10jit_threadEPv']:
  s=next((s for s in jir.syms if s['name']==n and s['defined']),None)
  if s:
   rows=[]
   for i in jir.md.disasm(jir.data(s['va'],s['size']),s['va']):
    target=''
    if i.mnemonic in ('bl','b'):
     try:target=jir.plt.get(int(i.op_str[1:],16),'')
     except ValueError:pass
    rows.append({'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'branch_symbol':target})
   funcs.append({'symbol':n,'entry':hex(s['va']),'size':s['size'],'instructions':rows})
 mount=json.loads((P.parents[1]/'stage7-entry/firmware/runtime-static.json').read_text())['scripts']['/sbin/initrc/fstab']
 # Current binary's embedded A7CII baseline hash can be checked without source
 # preprocessor expansion or executing a worker.
 a7hash='2ea02f7ecbc5bb917316fe8ef4ce5ffd87eb66efaae78ba2ce11420552df539b'
 installer=(P/'temporary-upstream/installer.so').read_bytes()
 result={'method':'static-only ELF parsing; original FX3 bytes and upstream payload not loaded/executed',
         'worker_ELFs':workers,'FX3_Jiritsu_ELF':jinfo,'prior_FX3_instruction_receipt_reverified':matches,
         'Jiritsu_symbols':syms,'FX3_selected_functions':funcs,'FX3_usr_mount':mount,
         'installer_contains_known_A7CII_original_AP_SHA':a7hash,'known_hash_offset':installer.find(bytes.fromhex(a7hash)),
         'FX3_AP_SHA':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
         'not_performed':['native or Unicorn firmware execution','camera enumeration/auth','module upload','camera file read/write','WBI or mount changes']}
 (P/'device-abi-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'workers':workers,'FX3_Jiritsu':{k:jinfo[k] for k in ['sha256','type','machine','bits','little_endian','needed']},'prior_instruction_matches':matches,'upstream_A7CII_hash_offset':result['known_hash_offset']},indent=2))
if __name__=='__main__':main()
