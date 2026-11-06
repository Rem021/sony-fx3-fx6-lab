#!/usr/bin/env python3
"""Read stock WBI2 snapshot as data; no firmware, payload or device execution."""
from pathlib import Path
import mmap,struct,json,hashlib,sys,subprocess,plistlib
sys.dont_write_bytecode=True
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac')
BASE=ROOT/'work/sony-firmware-20261024'
sys.path.insert(0,str(BASE/'stage4-windows-collab/mac-verification/.venv/lib/python3.14/site-packages'))
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
OUT=Path(__file__).parent
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
SRC=BASE/'stage2/extraction/nflasha5.img'
with SRC.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as d:
 n=struct.unpack_from('<Q',d,8)[0];size=struct.unpack_from('<Q',d,0x30)[0];table=0x200+size
 assert d[:4]==b'WBI2' and n==1399 and table+n*64<=len(d)
 secs=[];at=0x200
 for i in range(n):
  q=struct.unpack_from('<8Q',d,table+i*64)
  assert q[0]%4096==0 and q[4]%4096==0
  assert (q[3]==0 and q[1]==q[4]) or (q[3]==1 and q[1]==0)
  secs.append(dict(index=i,phys=q[0],stored_size=q[1],original_size=q[4],file_offset=at,flags=q[3],virt=q[5],raw=d[table+i*64:table+(i+1)*64].hex()));at+=q[1]
 assert at==table
 def physical(o):
  s=next(s for s in secs if s['file_offset']<=o<s['file_offset']+s['stored_size'])
  return s['phys']+o-s['file_offset']
 def offset(v):
  p=v-0xffffff8008000000+0x400000000
  s=next(s for s in secs if s['phys']<=p<s['phys']+s['stored_size'])
  return s['file_offset']+p-s['phys']
 def kva(o):return physical(o)-0x400000000+0xffffff8008000000
 cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 result={'scope':'Static stock snapshot observations; not current body state or execution proof','source':{'path':str(SRC),'sha256':hashlib.sha256(d).hexdigest(),'bytes':len(d)},'section_validation':{'count':n,'data_size':size,'sum_stored_sizes':at-0x200,'table_offset':table,'omitted_zero_fill_records':sum(s['flags']==1 for s in secs)},'attributes':[],'snapshot_wbi4':[],'sections':secs}
 lines=[]
 for term in [b'image_dev',b'image_mode',b'image_drop',b'image_mem']:
  pos=d.find(term);v=kva(pos);ptr=struct.pack('<Q',v);a=d.find(ptr)
  assert a>=0
  hits=[]
  while a>=0:
   hits.append(a);a=d.find(ptr,a+8)
  candidates=[q for q in hits if struct.unpack_from('<Q',d,q+8)[0] in [0o644,0o444,0o200]]
  assert candidates
  a=candidates[0]
  name,mode,show,store=struct.unpack_from('<4Q',d,a)
  ent={'name':term.decode(),'string_offset':hex(pos),'string_va':hex(v),'attribute_offset':hex(a),'raw_attribute':d[a:a+32].hex(),'mode_octal':oct(mode),'show_va':hex(show),'store_va':hex(store),'handlers':{}}
  for kind,va in [('show',show),('store',store)]:
   o=offset(va);inst=list(cs.disasm(d[o:o+0x300],va))
   # stop at first RET, include whole bounded basic linear view; branch targets not necessarily covered
   stop=next((j+1 for j,i in enumerate(inst) if i.mnemonic=='ret'),len(inst));inst=inst[:stop]
   ent['handlers'][kind]={'file_offset':hex(o),'bounded_bytes':d[o:o+0x300].hex(),'instructions':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str} for i in inst]}
   lines.append('\n'+term.decode()+' '+kind+' '+hex(va)+' file '+hex(o))
   lines.extend(f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in inst)
  result['attributes'].append(ent)
 w=d.find(b'wbi4');assert d.find(b'wbi4',w+4)<0
 result['snapshot_wbi4']={'offset':hex(w),'physical':hex(physical(w)),'direct_map_va':hex(physical(w)-0x400000000+0xffffffc000000000),'bytes_around':d[w-160:w+176].hex(),'note':'Registered-looking in-memory object with callbacks; selected image_dev output not independently established'}
 def any_offset(v):
  if v>=0xffffffc000000000:p=v-0xffffffc000000000+0x400000000
  else:p=v-0xffffff8008000000+0x400000000
  z=next(z for z in secs if z['phys']<=p<z['phys']+z['stored_size'])
  return z['file_offset']+p-z['phys']
 def rawva(v,n):return d[any_offset(v):any_offset(v)+n]
 state=0xffffff80086e4178;selected=struct.unpack('<Q',rawva(state+0x40,8))[0]
 result['snapshot_state']={'mode_va':hex(state),'mode_offset':hex(any_offset(state)),'mode_value':struct.unpack('<I',rawva(state,4))[0],'selected_va':hex(selected),'format_bytes':repr(rawva(0xffffff80085e0958,16)),'unselected_marker':repr(rawva(0xffffff80085cd570,8)),'selected_marker':repr(rawva(0xffffff80085b7a38,8)),'evidence_level':'Static saved memory only; selected backend pointer not closed to wbi4'}
 result['drop_helpers']=[]
 for va in [0xffffff80080e3dc0,0xffffff80080e3ce8]:
  o=offset(va);ii=list(cs.disasm(d[o:o+0x120],va));lines.append('\ndrop helper '+hex(va));lines.extend(f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in ii)
  result['drop_helpers'].append({'va':hex(va),'offset':hex(o),'bytes':d[o:o+0x120].hex(),'instructions':[f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in ii]})
 print('SNAPSHOT_STATE',result['snapshot_state'])
 (OUT/'wbi2-section-map.json').write_text(json.dumps({'section_validation':result['section_validation'],'sections':secs},indent=2)+'\n')
 (OUT/'sysfs-attribute-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 (OUT/'sysfs-handler-disassembly.txt').write_text('\n'.join(lines)+'\n')
 print('\n'.join(lines))
 print('ATTRIBUTE_SUMMARY',[(x['name'],x['mode_octal'],x['show_va'],x['store_va']) for x in result['attributes']])
