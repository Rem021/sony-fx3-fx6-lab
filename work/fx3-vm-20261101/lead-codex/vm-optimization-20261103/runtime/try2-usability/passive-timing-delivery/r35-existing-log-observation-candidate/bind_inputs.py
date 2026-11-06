#!/usr/bin/env python3
"""Read exact CPIO headers/members and actual kernel table. No runner imports."""
from pathlib import Path
import struct,json,hashlib,subprocess,plistlib
O=Path(__file__).resolve().parent;D=O.parent;R=D.parents[5]
ROOT=next(p for p in O.parents if p.name=='Mac'); RT=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda b:hashlib.sha256(b).hexdigest()
def section(b,name):
 shoff=struct.unpack_from('<Q',b,40)[0];ss,n,names=struct.unpack_from('<HHH',b,58);headers=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*ss) for i in range(n)];s=headers[names];strings=b[s[4]:s[4]+s[5]]
 for s in headers:
  a=s[0];nm=strings[a:strings.find(b'\0',a)].decode()
  if nm==name:return {'vaddr':s[3],'bytes':s[5],'sha256':sha(b[s[4]:s[4]+s[5]])}
 raise KeyError(name)
want=['init','lib/libc-2.25.so','lib/libpthread-2.25.so','simulation/fx3-ui-gate-v1.so','simulation/fx3-osd-headless-v5.so'];meta={v['path']:v for v in json.loads((D/'r33-causal-observation-candidate/ACTUAL-MEMBERS.json').read_text())};found={};data={};count=0
cpio=D/'r16-fixed-slot-guests/guest-N64/guest.cpio'
with cpio.open('rb') as f:
 while True:
  at=f.tell();h=f.read(110);assert len(h)==110 and h[:6] in (b'070701',b'070702');v=[int(h[6+i*8:14+i*8],16) for i in range(13)];name=f.read(v[11]).rstrip(b'\0').decode();f.seek((f.tell()+3)&~3);off=f.tell();size=v[6];count+=1
  if name=='TRAILER!!!':break
  if name in want:
   b=f.read(size);assert len(b)==size;expect=meta[name];assert off==expect['data_offset'] and size==expect['bytes'] and sha(b)==expect['sha256'];found[name]={'header_offset':at,'data_offset':off,'bytes':size,'sha256':sha(b)};data[name]=b
  f.seek((off+size+3)&~3)
assert set(found)==set(want)
(O/'actual-init.txt').write_bytes(data['init']);init=data['init'].decode();launch=[x for x in init.splitlines() if 'LD_PRELOAD=' in x and '/usr/bin/bootin.elf' in x];assert len(launch)==1
line=launch[0];assert '/simulation/fx3-osd-headless-v5.so:' in line and '/simulation/fx3-ui-gate-v1.so:' in line
for member,sdk in [('lib/libc-2.25.so','libc-2.25.so'),('lib/libpthread-2.25.so','libpthread-2.25.so')]:assert data[member]==(RT/'guest-sdk/lib'/sdk).read_bytes()
# Source -> original compiled text -> actual member. Source/build inputs separately pinned.
ui=(D/'v25-r15-snapshot-tail/fx3-ui-gate-v15-n64.so').read_bytes();osd=(D/'v25-menu-osd-diagnostic-r3/build/fx3-osd-headless-v25-r3.so').read_bytes()
texts={}
for tag,b,m in [('ui',ui,'simulation/fx3-ui-gate-v1.so'),('osd',osd,'simulation/fx3-osd-headless-v5.so')]:
 a=section(b,'.text');c=section(data[m],'.text');assert a==c;texts[tag]={'frozen_compiled_text':a,'actual_CPIO_text':c,'equal':True}
# Actual kernel table values, with symbol catalog bound to accepted Image hash.
image=ROOT/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin';b=image.read_bytes();assert sha(b)=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
syms=json.loads((ROOT/'work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json').read_text());by={x['name']:x for x in syms};tab=by['sys_call_table'];entries={}
for n,name in [(172,'sys_getpid'),(178,'sys_gettid')]:
 at=tab['file_offset']+8*n;addr=struct.unpack_from('<Q',b,at)[0];assert addr==by[name]['address'];s=by[name];code=b[s['file_offset']:s['file_offset']+40];entries[str(n)]={'name':name,'table_file_offset':at,'target':hex(addr),'code_file_offset':s['file_offset'],'first40_raw_hex':code.hex()}
receipt={'cpio':str(cpio),'cpio_sha256':sha(cpio.read_bytes()),'headers_walked':count,'members':found,'actual_launch_line':line,'same_preload_line':True,'SDK_byte_identical_actual_members':True,'text_bindings':texts,'kernel_syscalls':entries,'kernel_sha256':sha(b)}
(O/'ACTUAL-BINDING.json').write_text(json.dumps(receipt,indent=2)+'\n');print('actual CPIO/header/helper/preload/SDK/kernel syscall bindings PASS')
