#!/usr/bin/env python3
"""FX3 original OSD completion, read-only input audit; only adjacent proof is written."""
import hashlib, json, struct, sys, subprocess, plistlib, re
from pathlib import Path
from capstone import *
from elftools.elf.elffile import ELFFile
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'work/sony-firmware-20261024').is_dir())
LIB=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib'
CP=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'].upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
class Image:
 def __init__(self,name):
  self.name=name;self.p=CP if name=='cp' else LIB/name;self.b=self.p.read_bytes();self.plt={}
  if name!='cp':
   self.f=self.p.open('rb');self.e=ELFFile(self.f);self.segs=[s for s in self.e.iter_segments() if s['p_type']=='PT_LOAD']
   r=self.e.get_section_by_name('.rela.plt')
   if r:
    sy=self.e.get_section(r['sh_link']);pv=self.e.get_section_by_name('.plt')['sh_addr'];self.plt={pv+32+16*n:sy.get_symbol(x['r_info_sym']).name for n,x in enumerate(r.iter_relocations())}
  self.cs=Cs(CS_ARCH_ARM if name=='cp' else CS_ARCH_ARM64, CS_MODE_THUMB if name=='cp' else CS_MODE_ARM)
 def read(self,v,n):
  if self.name=='cp':o=v-0x108000
  else:
   s=next(s for s in self.segs if s['p_vaddr']<=v and v+n<=s['p_vaddr']+s['p_filesz']);o=s['p_offset']+v-s['p_vaddr']
  assert o>=0 and o+n<=len(self.b)
  return self.b[o:o+n]
 def dis(self,v,n):
  return [{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,**({'symbol':self.plt[int(i.op_str[1:],16)]} if i.mnemonic in ('bl','b') and i.op_str.startswith('#') and int(i.op_str[1:],16) in self.plt else {})} for i in self.cs.disasm(self.read(v,n),v)]
if len(sys.argv)>1:
 im=Image(sys.argv[1]);mode=sys.argv[2]
 if mode=='find':
  needle=bytes.fromhex(sys.argv[3]);off=im.b.find(needle)
  while off>=0:
   print(hex(off+0x108000 if im.name=='cp' else off));off=im.b.find(needle,off+1)
 else:
  for r in im.dis(int(mode,16),int(sys.argv[3],16)):print(r['va'],r['asm'],r.get('symbol',''))
 sys.exit(0)

proof={'scope':'Static original-byte audit only; no QEMU, guest, device, runtime, lock or Git mutation.',
 'verdict':'PARTIAL: AP publication/lease/receive semantics proven; original CP 6003/6005 sender and byte schema NOT proven; no ACK implementation authorized by this proof.',
 'sources':{},'blocks':{},'checks':[]}
images={n:Image(n) for n in ('cp','libObj.so')}
for n,im in images.items():
 proof['sources'][str(im.p.relative_to(ROOT))]={'bytes':len(im.b),'sha256':hashlib.sha256(im.b).hexdigest()}
windows={
 'cp':[(0x4b3628,0xb4),(0x4b36fc,0x180),(0xa902b0,0x6c),(0x49fa28,0x16)],
 'libObj.so':[(0xf1d04,0x8c),(0xf1d90,0x118),(0xf2210,0x12c),(0xf2428,0x148),(0xf25f4,0x1e4),
 (0xf2820,0x120),(0xf2fa0,0x10c),(0xf30ac,0x120),(0xf3244,0x110),(0xf3354,0xc8),(0xfd344,0x7c),
 (0xf12b4,0xd0),(0xf09dc,0xbc),(0xf0c80,0x38),(0xf0f04,0x64),(0xf1010,0x164),(0xf1174,0x140),
 (0xeed80,0x78),(0xeee78,0xa0),(0xfb594,0xa0),(0xfb790,0x14),(0xef36c,0x64),
 (0x102718,0xb4),(0x102f58,0xd8),(0x102b98,0x38),(0x103194,0x10)]}
flat={}
for n,ws in windows.items():
 im=images[n];proof['blocks'][n]={};flat[n]={}
 for v,z in ws:
  rows=im.dis(v,z)
  # All selected windows are instruction ranges; never silently accept a decode gap.
  assert sum(len(bytes.fromhex(x['bytes'])) for x in rows)==z,(n,hex(v),'decode gap')
  proof['blocks'][n][hex(v)]={'bytes':im.read(v,z).hex(),'instructions':rows}
  flat[n].update({int(x['va'],16):x for x in rows})
def check(n,v,asm):
 r=flat[n][v];assert r['asm']==asm,(n,hex(v),r['asm'],asm)
 proof['checks'].append({'image':n,'va':hex(v),'bytes':r['bytes'],'expected_asm':asm})
for v,a in {
 0xf1d9c:'mov w2, #0xc',0xf1e28:'mov w2, #0x24',0xf2690:'str w1, [x0, #8]',
 0xf26ec:'str w1, [x0, #8]',0xf26f4:'str w1, [x0, #0xc]',0xf2708:'strh w1, [x0, #0x10]',
 0xf2718:'strh w2, [x0, #0x14]',0xf274c:'str w1, [x0, #0x20]',0xf2760:'bl #0x55fd0',
 0xf26ac:'bl #0xf2238',0xf2790:'bl #0xf22b0',0xf227c:'bl #0xfd384',0xf22cc:'bl #0xfd384',
 0xf22f0:'ldrh w2, [x1]',0xf2250:'add x1, x29, #0x30',0xf3378:'ldr w0, [x0, #0x10]',
 0xf3174:'bl #0x102718',0xf3194:'add x1, x1, x22',0xf3198:'stur x1, [x19, #-0x10]',
 0x102bb4:'cmp x1, x4',0x102bc4:'add x2, x1, x2',
 0xf3390:'add x0, x0, #0x88',0xf3398:'add x0, x19, #0x78',
 0xf33ec:'ldp x0, x1, [x19, #0x60]',0xf33f0:'stp x1, x0, [x19, #0x60]',
 0xf11dc:'add w0, w0, #1',0xf11e0:'str w0, [x19, #0x2c]',
 0xf1084:'ldr w0, [x19, #0x2c]',0xf113c:'str w0, [x19, #0x34]',
 0xf0f28:'str w0, [x19, #0x2c]',0xf0ca4:'str w0, [x19, #0x28]',
 0xfd348:'mov w1, #-1',0xfd354:'bl #0x55670',0xfd390:'bl #0x57bb0'
}.items():check('libObj.so',v,a)
for v,a in {
 0x4b363a:'movw r0, #0x1003',0x4b3648:'movw r0, #0x1005',0x4b3694:'bl #0x49f9b0',
 0x4b36a2:'bl #0x4b36fc',0x4b36aa:'bl #0x49f908',0x4b371e:'cmp.w r0, #0x2000',
 0x4b3724:'movw r1, #0x2001',0x4b372c:'movw r1, #0x2002',0x4b3732:'bne.w #0x4b3874',
 0xa9030c:'bl #0x4b3628',0x49fa2e:'str.w r0, [sb]'
}.items():check('cp',v,a)
# Resolve the actual concrete bitmap vtable through ELF relocation addends.
im=images['libObj.so'];rr={r['r_offset']:r for r in im.e.get_section_by_name('.rela.dyn').iter_relocations()}
vptr=rr[0x261c50]['r_addend']+16
expected={0x30:0xf0e0c,0x50:0xf0a3c,0x60:0xf0a64,0x88:0xf1174,0x90:0xf0f04,0x98:0xf1010,0xa0:0xf0f68,0xa8:0xf0c80,0xb0:0xf1928,0xc8:0xef478}
assert vptr==0x252670
proof['bitmap_vtable']={'GOT':'0x261c50','vptr':hex(vptr),'slots':{hex(k):hex(rr[vptr+k]['r_addend']) for k in expected}}
assert all(rr[vptr+k]['r_addend']==v for k,v in expected.items())
# Field coverage: these cover every byte and intentionally do not invent a generation/bank.
proof['wire']={
 '1002':{'size':12,'destination':'0x8280074d','source':'0x8288076c','fields':[
 [0,2,'LE16 command=1002','Obj f1e08..0c'],[2,6,'zero','Obj f1ddc..1dec'],[8,4,'LE32 next=1003 or1005','Obj f268c..2690/f2770..2774']],
 'full_frame_hex':'021000000000000003100000','metadata_hex':'021000000000000005100000'},
 '1003':{'size':36,'destination':'0x8280084d','source':'0x8288076c','fields':[
 [0,2,'LE16 command=1003','Obj f1e94..98'],[2,6,'zero','Obj f1e68..78'],
 [8,4,'LE32 metadata physical-address low32 token (NOT generation)','Obj f3374..7c;f30ac..31a0;f26e4..ec'],
 [12,4,'LE32 constant1','Obj f26f0..f4'],[16,2,'LE16 (framebuffer format enum ==2)','Obj f26f8..2708'],
 [18,2,'zero','Obj f1e68..78'],[20,2,'LE16 canvas width','Obj f3024..3034;f2718'],
 [22,2,'LE16 canvas height','Obj f3030..3038;f271c'],[24,2,'LE16 region x','Obj f3050;f2734'],
 [26,2,'LE16 region y','Obj f3054;f2738'],[28,2,'LE16 region width','Obj f3044;f273c'],
 [30,2,'LE16 region height','Obj f303c;f2740'],[32,4,'LE32 diagnostic/context word, zero in normal branch; NOT completion status','Obj f24d0..24f4;f2544..2554;f2744..4c']],
 'not_inline':['pixel physical64','stride','true pixel format enum','generation counter','bank number'],
 'symbolic_full_frame_fmt0_640x480':'0310000000000000TTTTTTTT01000000000000008002e001000000008002e001DDDDDDDD'},
 '1005':{'size':8,'destination':'0x8280084e','source':'0x8288076c','fields':[[0,2,'LE16 command=1005','Obj f1d04..1d8c'],[2,6,'zero; no new pixels/token/geometry','Obj f1d04..1d8c']]},
 '6003':{'size':None,'factory_fields':None,'factory_sender':None,'AP_required_prefix_hex':'0360','AP_payload_validation':False},
 '6005':{'size':None,'factory_fields':None,'factory_sender':None,'AP_required_prefix_hex':'0560','AP_payload_validation':False}}
for k in ['1002','1003','1005']:
 d=proof['wire'][k];coverage=[]
 for off,z,_,_ in d['fields']:coverage.extend(range(off,off+z))
 assert sorted(coverage)==list(range(d['size'])) and len(set(coverage))==d['size']
assert bytes.fromhex(proof['wire']['1002']['full_frame_hex'])==struct.pack('<HHII',0x1002,0,0,0x1003)
# No callback reads incoming message x1. 6003 overwrites x1 with stack address;
# 6005 never uses x1 at all. f22f0 is the only payload read on these paths.
a64=images['libObj.so'];assert not any(re.search(r'\bx1\b',r['asm']) for r in a64.dis(0xf22b0,0x40))
assert all(not r['asm'].startswith(('ldr','ldur','ldp')) or '[x1' not in r['asm'] for r in a64.dis(0xf2238,0x18))
proof['AP_completion']={'source_gate':'Obj f28d0..28e8 requires source8280074d before f22f0 (full dispatch in blocks)',
 'dispatch':'f22f0 reads only LE16 at0;6003=>f2238;6005=>f22b0;unknown=>assert',
 '6003':'No frame ID/generation/status/length read; trace/timing cleanup then unconditionally signal ExternalOSDIF+48 and optional callback+50, clear callback',
 '6005':'No frame ID/generation/status/length read; signal same semaphore and optional callback+50, clear callback',
 'risk':'A duplicate, stale or foreign-epoch completion from correct source can signal same gate; native receiver does not provide deduplication.'}
proof['CP_boundary']={'function':'osdTrans::OsdTransferMsgCtrl::WaitAndExecuteUpdateExec @4b3628; assertion string@e156c8, filename@4b36dc',
 'receipt':'select84d for1003 or84e for1005; wait(-1); call4b36fc; free request',
 'dispatch_result':'4b36fc only branches2000/2001/2002; exact1003/1005 falls through4b3732 to4b3874, no scan/ACK in this selected path',
 'transport':'49fa28..3c returns buffer body+18 without changing body ID in that dequeue path',
 'control_wrapper':'a902b0 iterates Dataflow bodies;1002 body +8 selects4b3628. Registration and native74d-to-wrapper mapping unresolved.',
 'do_not_infer':'This bounded negative path does NOT prove no other bridge or consumer exists in FX3 firmware.'}
proof['identity_and_lease']={
 'framebuffer':'manager+8 -> FB; Obj f2d58/f3368. FB+60=current/on entry;FB+68=other;entries FB+18/FB+38; swap f33ec..f0',
 'bank_entry':{'+0':'bitmap object pointer','+8':'u32 allocation handle (f3128)','+10':'u64 translated physical metadata address+caller offset (f3140..3198)','+18':'u64 pixel physical supplied to bitmap creation(f32e4..32e8)'},
 'generation':'No on-wire generation found; require consumer-local epoch plus allocation/object identity checks. A local sequence is never a recovered native field.',
 'FB_locks':'f3380 waits FB+88 then FB+78;f33a8 releases reverse;OSAL IDs atFB+90/FB+80. f33d0 swap and f3244 format re-create obey FB+88.',
 'bitmap':'Concrete vptr252670;ReadLock(timeout0)->f1174 increments+2c if no writers/pending writers at+30/+34;WriteLock f1010 refuses while+2c!=0;ReadUnlock f0f04 decrements+broadcast;AddRef f0c80;Release f1928.',
 'limitations':'Native helper f3380 waits forever: bounded consumer must use the resolved actual OSAL IDs with bounded polls, not invoke helper blindly. Bitmap lock does not prove exclusion of physical aliases or current software GPE writers; bind their shared raster guard before enabling ACK.'}
# Existing local upstream reference: not fetched into the task, not executed.
A7=ROOT/'work/fx3-vm-20261101/menu-repair-01/success-cases/source/runtime/analysis/headless-osd.c'
b=A7.read_bytes();proof['sources'][str(A7.relative_to(ROOT))]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
assert hashlib.sha256(b).hexdigest()=='55c695ba7c85c719a0d0789d19c54cf45d411c54508c81e9df9c8ed020c7d582'
proof['A7C2_reference']={'commit_from_existing_receipt':'b3d7c1fed349f1d918acc4259f1d2b3a7c52a500','source_lines':{'identity':'105..119','lease':'149..226','pair_and_ack':'284..365'},
 'same':'serial1002->1003/1005;lease/snapshot/retained metadata;release;completion to76c source74d',
 'different':'A7 hardcoded format1,FB+68/+70 and private manager/vtable offsets;FX3 proven fmt0 branch,FB+60/+68,vptr252670. A7 8B zero-padded replies are software choice, NOT factory FX3 schema.',
 'online':'Capstone official Python API fetched; pinned GitHub blob fetch failed(cache miss); local reference only.'}
proof['headless_contract']={'status':'DESIGN ONLY, NOT READY TO EMIT FACTORY ACK',
 'sequence':['claim exclusive queue ownership and new epoch; record pending queues before consuming',
 'freeze GUI config on source76c1002/12B;read exact selected84d36B or84e8B matching source/ID;bounded pair deadline',
 'bounded acquire FB+88 thenFB+78;resolve entry token,bitmap,extent physical64;AddRef;ReadLock(timeout0);acquire all writer/raster guards',
 'validate dimensions/format/stride and nonwrapping row spans in live extent;copy at most configured span into owned snapshot;retain descriptor/config',
 'release raster,ReadUnlock,Release,FB+78,FB+88 on every acquired path;release request ownership;persist frozen bytes/identity then PNG outside native locks',
 'only if factory completion schema/source/size/fields proven and all phases succeed: send exactly one matching completion to8288076c source8280074d',
 'reject,timeout,unknown schema,unsupported format,partial snapshot,unlock/release/persist/send failure: NO success ACK;retain failure/pending ledger;never force semaphore'],
 'known_extent_example':{'type_handle':545,'base':'0x43feb5000','size':'0x140000','observed_pixel_physical':'0x43feb5100','fmt':0,'width':640,'height':480,'stride_pixels':640,'span_bytes':614400,'provenance':'prior VDF0147 and post-clear audits; live identity not revalidated here'},
 'bounds':'bpp supported0=>2,1=>4 only after actual bitmap format verification;span=((height-1)*stride_pixels+width)*bpp;address+span must be inside same live extent;PNG component names/alpha remain separate calibration',
 'cadence':'No original VSYNC-to6003 edge proved. Event-driven completion after own snapshot is closest proven ownership semantic. Fixed60/30Hz is an optional labelled software presentation policy, not an established native rate.'}
proof['open_items']=['8280074d registration and native control1002 handler','bridge mapping bare1003/1005 to CP200x or alternate consumer',
 'original6003/6005 sender, length, all bytes and any status constants','native scanout/compositor and VSYNC/fence-to-completion edge',
 'live native frame token and bitmap/DMM extent identity; generation reuse and bank lifecycle','all current GPE/physical-alias writers obey shared read lease',
 'same sem object/LR/source/raw/size dynamic readback;two consecutive frames;menu/input acceptance']
for p in [OUT.parent/'post-clear-idle/README.md',OUT.parent/'vdf0147-plane-scanout/README.md',OUT.parent/'libobj-frame-handshake/README.md']:
 b=p.read_bytes();proof['sources'][str(p.relative_to(ROOT))]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'role':'prior static/runtime evidence with explicit limits'}
(OUT/'osd-completion-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print('PASS: rebuilt osd-completion-proof.json;',len(proof['checks']),'instruction assertions; factory ACK schema remains UNPROVEN')
