from pathlib import Path
import json,hashlib,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
R=Path(__file__).resolve().parent;M=R.parents[3];L=R.parents[1]/'lead-claude';P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';sha=lambda x:hashlib.sha256(x).hexdigest();out={'proofs':[],'source_checks':[],'block_checks':[],'extra_native_blocks':{},'scope':'Read-only original input revalidation, not factory completion schema closure'}
for rel,key in [('osd-completion-6003/osd-completion-proof.json','blocks'),('vdf0152-peaking/vdf0152-proof.json','code')]:
 p=L/'audits'/rel;d=json.loads(p.read_text());out['proofs'].append({'path':str(p),'sha256':sha(p.read_bytes())})
 for rel,q in d['sources'].items():
  b=(M/rel).read_bytes();actual=sha(b[:q['bytes']]);same=actual==q['sha256'];strict=rel.endswith(('.bin','.so','.c'));assert same or not strict,(rel,'original changed');out['source_checks'].append({'path':rel,'expected_prefix_bytes':q['bytes'],'prefix_match':same,'strict_original_or_reference':strict})
 blocks=d[key]
 for name,windows in blocks.items():
  name={"AP":"appFw.so","CP":"cp"}.get(name,name)
  path=M/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin' if name=='cp' else P/name
  if not isinstance(windows,dict):continue
  with path.open('rb') as f:
   ef=ELFFile(f) if name!='cp' else None
   for address,q in windows.items():
    if not isinstance(q,dict) or 'bytes' not in q:continue
    v=int(address,16);raw=bytes.fromhex(q['bytes']);off=v-0x108000 if name=='cp' else next(s['p_offset']+v-s['p_vaddr'] for s in ef.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v and v+len(raw)<=s['p_vaddr']+s['p_filesz']);f.seek(off);assert f.read(len(raw))==raw,(name,address);out['block_checks'].append({'image':name,'va':address,'bytes':len(raw),'match':True})
for name,windows in {'DataflowInfraFramework.so':[(0x33964,0x1a0),(0x321a0,0x90),(0x32210,0x88),(0x32070,0x110)],'libObj.so':[(0xf2210,0x80),(0xf22b0,0x40),(0xfd344,0x80),(0xeeebc,0x50),(0xeec14,0x50),(0xf2ab8,0x60)]}.items():
 p=P/name;b=p.read_bytes();out['extra_native_blocks'][name]={'sha256':sha(b),'blocks':{}}
 with p.open('rb') as f:
  ef=ELFFile(f);cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
  for v,n in windows:
   off=next(s['p_offset']+v-s['p_vaddr'] for s in ef.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v and v+n<=s['p_vaddr']+s['p_filesz']);raw=b[off:off+n];rows=[{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(raw,v)];out['extra_native_blocks'][name]['blocks'][hex(v)]={'bytes':raw.hex(),'instructions':rows}
out['completion_schema']={'length8':'Explicit software choice; native receive unconditionally reads bytes4..7 to inspect envelope. Does not assert native packet length.','prefix6003_6005':'Native ExternalOSDIF callbacks only read u16 prefix and require source74d; exact native sender unproven.','source':'0x8280074d','destination':'0x8288076c','direct_publish_semaphore_signaling':False};(R/'ap85-audit-input-check.json').write_text(json.dumps(out,indent=2)+'\n');print('AP85_AUDIT_REVALIDATED',len(out['block_checks']),'blocks',len(out['source_checks']),'sources')
