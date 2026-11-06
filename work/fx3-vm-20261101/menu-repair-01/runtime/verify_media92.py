from pathlib import Path
import json,hashlib
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM
from unicorn.arm64_const import UC_ARM64_REG_X0
R=Path(__file__).resolve().parent;P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';proof=json.loads((R/'ap92-passive-original-proof.json').read_text());xrefs=json.loads((R/'ap92-parameter-xrefs.json').read_text())
def read(name,va,n):
 with (P/name).open('rb') as f:
  e=ELFFile(f);s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']);return s.data()[va-s['p_vaddr']:va-s['p_vaddr']+n]
for name,want in proof['source_SHA256'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==want
for tag,name in [('D','libInfraMediaDetect.so'),('M','libInfraMediaMount.so')]:
 for point in proof['points'][tag]:assert read(name,int(point['va'],16),4).hex()==point['bytes']
for p in proof['parameters']:
 for label in ['current','shadow']:
  q=p[label];addr=int(q['getter'],16);b=read('appFw.so',addr,20);assert b.hex()==q['code']
  for base in [0,0x7f12345000]:
   u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map((base+addr)&~4095,4096);u.mem_write(base+addr,b);u.emu_start(base+addr,base+addr+16,count=4);assert u.reg_read(UC_ARM64_REG_X0)-base==int(q['address_relative'],16)
 assert p['identity_setter_xrefs']
 for h in p['identity_setter_xrefs']:
  assert any(i['asm']=='bl #'+q for q in [p['current']['getter']] for i in h['window'])
  for i in h['window']:assert read('appFw.so',int(i['va'],16),4).hex()==i['bytes']
for new in ['fx3-media-observe-v1','fx3-capid-v47-media']:
 v=json.loads((R/'helpers'/(new+'-build.json')).read_text());assert hashlib.sha256((R/'helpers'/(new+'.c')).read_bytes()).hexdigest()==v['source_sha256'];assert hashlib.sha256((R/'helpers'/(new+'.so')).read_bytes()).hexdigest()==v['output_sha256']
v={'original_hashes_match':3,'original_points_match':36,'getter_codes_match':20,'Unicorn_ASLR_reference_addresses_match':40,'parameter_setter_xrefs_match':20,'used_helper_source_binary_hashes_match':True,'proof_SHA256':hashlib.sha256((R/'ap92-passive-original-proof.json').read_bytes()).hexdigest()};(R/'ap92-static-replay-check.json').write_text(json.dumps(v,indent=2)+'\n');print(v)
