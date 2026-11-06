"""Read-only ELF evidence extraction. All outputs stay beside this script."""
import sys
sys.dont_write_bytecode = True
from trace import *

def symbols(e):
 s=e.named['.dynsym'];st=e.sections[s[6]];names=e.b[st[4]:st[4]+st[5]];result=[]
 for off in range(s[4],s[4]+s[5],s[9]):
  n,info,other,sh,v,z=struct.unpack_from('<IBBHQQ',e.b,off)
  result.append({'name':names[n:].split(b'\0')[0].decode(),'value':hex(v),'size':z})
 return result

def relocations(k,locations):
 e=E[k];sy=symbols(e);result=[]
 for s in e.sections:
  if s[1]!=4:continue
  for off in range(s[4],s[4]+s[5],24):
   va,info,add=struct.unpack_from('<QQq',e.b,off)
   if va in locations:
    result.append({'location':e.mapping(va,8),'rela_fileoff':hex(off),'rela_raw':e.b[off:off+24].hex(),'type':info&0xffffffff,'addend':hex(add),'symbol':sy[info>>32]})
 return result

if __name__=='__main__':
 for k,a,z in [('fx6_mpr',0x12bd30,0x12bd48),('fx3_ap',0x2e58ee4,0x2e58eec),('fx6_ap',0x212f498,0x212f4a0),('fx3_mpr',0x11d15c,0x11d180),('fx6_mpr',0x1b44c0,0x1b44e8),('fx6_mpr',0x198420,0x198478)]:dis(k,a,z)
 rows={};excerpts={}
 for f in sorted(H.glob('*.txt')):
  if f.name.endswith('-full.txt'):continue
  k=next((k for k in E if f.name.startswith(k+'-')),None)
  if k is None:continue
  for line in f.read_text().splitlines():
   m=re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.*)',line)
   if m:
    va=int(m[1],16);r=E[k].mapping(va);assert struct.unpack('<I',bytes.fromhex(r['bytes_le']))[0]==int(m[2],16)
    rows[k+':'+hex(va)]={'binary':k,**r,'word':m[2],'disassembly':m[3]}
  excerpts[f.name]=sha(f.read_bytes())
 rels={
  'fx3_mpr':relocations('fx3_mpr',[0x2fa3a0,0x2f4710,0x2f9308,0x2f9990,0x2f9390,0x2fae90]),
  'fx6_mpr':relocations('fx6_mpr',[0x108de78,0x108e420,0xf26048,0xf25f10,0x108e708,0x108d408,0x108c070])}
 data={'recordableTime_label':E['fx6_mpr'].mapping(0xcc9eb9,20),'fx6_event5_jump_entry':E['fx6_mpr'].mapping(0xcc9b54,2),'fx3_frame_rate_jump_table':E['fx3_mpr'].mapping(0x2e0a54,12),'fx6_frame_rate_jump_table':E['fx6_mpr'].mapping(0xec0cac,12)}
 assert bytes.fromhex(data['recordableTime_label']['bytes_le']).startswith(b'recordableTime: %u\n\0')
 assert 0x15d7c8+4*struct.unpack('<h',bytes.fromhex(data['fx6_event5_jump_entry']['bytes_le']))[0]==0x15d8c4
 obj={'inputs':{k:{'path':str(P[k]),'sha256':sha(e.b)} for k,e in E.items()},'instructions':rows,'relocations':rels,'data':data,'excerpt_hashes':excerpts,'warning':'Symbol+offset headings are nearest exported symbol, not inferred function names; VA mappings use PT_LOAD. RELATIVE pointers require runtime bias; GLOB_DAT binding is static only.'}
 (H/'instruction-evidence.json').write_text(json.dumps(obj,indent=2)+'\n')
 print(json.dumps({'instructions_verified':len(rows),'excerpt_count':len(excerpts),'fixed_inputs':len(E),'event5_target':'0x15d8c4'}))
