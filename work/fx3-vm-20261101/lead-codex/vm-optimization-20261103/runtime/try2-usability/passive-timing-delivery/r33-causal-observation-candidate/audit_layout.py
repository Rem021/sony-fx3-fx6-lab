#!/usr/bin/env python3
"""Read-only offline audit. Never imports runner or executes guest ELF."""
from pathlib import Path
import hashlib, json, re, struct
HERE=Path(__file__).resolve().parent
DEL=HERE.parent
ROOT=next(p for p in HERE.parents if (p/'README.md').exists() and p.name=='Mac')
CPIO=DEL/'r16-fixed-slot-guests/guest-N64/guest.cpio'
def sha(b):return hashlib.sha256(b).hexdigest()
def members(path):
 with path.open('rb') as f:
  while True:
   at=f.tell();h=f.read(110)
   if not h: return
   assert h[:6] in (b'070701',b'070702'),(at,h[:6])
   v=[int(h[6+i*8:14+i*8],16) for i in range(13)]
   name=f.read(v[11]);assert name[-1:]==b'\0'
   f.read((-f.tell())%4);data_at=f.tell();data=f.read(v[6]); assert len(data)==v[6]
   f.read((-f.tell())%4);name=name[:-1].decode()
   if name=='TRAILER!!!':return
   yield name,v,data_at,data

def symbols(data):
 if data[:6]!=b'\x7fELF\x02\x01':return []
 shoff=struct.unpack_from('<Q',data,40)[0];size,num=struct.unpack_from('<HH',data,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',data,shoff+i*size) for i in range(num)]
 out=[]
 for s in sections:
  if s[1] not in (2,11):continue
  st=sections[s[6]];strings=data[st[4]:st[4]+st[5]]
  for o in range(s[4],s[4]+s[5],s[9]):
   name,info,other,idx,val,n=struct.unpack_from('<IBBHQQ',data,o)
   out.append(dict(name=strings[name:strings.find(b'\0',name)].decode(errors='replace'),value=val,bytes=n,defined=idx!=0))
 return out

def main():
 audit=json.loads((DEL.parent/'runs/v25gate-n64-r17-77e949cd/cpio-audit.json').read_text())
 expected={m['path']:m for m in audit['members']}
 actual=[];hits=[];elf_symbols=[];selected={}
 for name,v,at,data in members(CPIO):
  assert name in expected,name
  assert sha(data)==expected[name]['sha256'],name
  actual.append(dict(path=name,bytes=len(data),sha256=sha(data),data_offset=at))
  # Finite discovery screen, NOT proof against computed/indirect addresses.
  pats=[b'41dc',b'fx3-ui-gate',struct.pack('<Q',0x41dc00000),struct.pack('<I',0x1dc0)]
  found={p.hex():[m.start() for m in re.finditer(re.escape(p),data)][:64] for p in pats if p in data}
  syms=symbols(data) if name.startswith('simulation/') else []
  if found:hits.append(dict(path=name,patterns=found))
  if name.startswith('simulation/') and data[:4]==b'\x7fELF':
   elf_symbols.append(dict(path=name,imports=[s['name'] for s in syms if not s['defined']],exports=[s for s in syms if s['defined'] and ('snapshot' in s['name'] or 'mmap' in s['name'])]))
  if name in ['simulation/fx3-ui-gate-v1.so','simulation/fx3-capid-v1.so']:
   # Only exact audit targets, no whole guest/runtime clone.
   out=HERE/('actual-'+Path(name).name);out.write_bytes(data);selected[name]=str(out)
  if name=='init':assert data.decode()==audit['init_text']
 assert len(actual)==len(expected)
 result=dict(scope='all CPIO members hash-matched; discovery screen is not a complete static alias proof',member_count=len(actual),archive_bytes=CPIO.stat().st_size,hits=hits,simulation_ELF=elf_symbols,selected=selected)
 (HERE/'CPIO-WRITER-SCREEN.json').write_text(json.dumps(result,indent=2)+'\n')
 (HERE/'ACTUAL-MEMBERS.json').write_text(json.dumps(actual,indent=2)+'\n')
 print(json.dumps(dict(member_count=len(actual),hits=[x['path'] for x in hits],ELF_simulation=len(elf_symbols),selected=selected),indent=2))
if __name__=='__main__':main()
