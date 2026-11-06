#!/usr/bin/env python3
"""Read-only Sony UI start audit. Only adjacent proof JSON may be written."""
import sys, struct, json, hashlib, subprocess, plistlib, bisect, re
from pathlib import Path
from collections import defaultdict
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'work/sony-firmware-20261024').is_dir())
RT=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime'
LIB=RT.parent/'original-uipc/ap-projection/regular-files/usr/lib'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'].upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
class Image:
 def __init__(self,name):
  self.name=name; self.path=LIB/name;self.raw=self.path.read_bytes();self.f=self.path.open('rb');self.e=ELFFile(self.f)
  self.segs=[s for s in self.e.iter_segments() if s['p_type']=='PT_LOAD'];self.cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
  self.syms={s.name:(s['st_value'],s['st_size']) for s in self.e.get_section_by_name('.dynsym').iter_symbols()}
  self.plt={};rel=self.e.get_section_by_name('.rela.plt')
  if rel:
   sy=self.e.get_section(rel['sh_link']);pv=self.e.get_section_by_name('.plt')['sh_addr']
   self.plt={pv+32+16*n:sy.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations())}
  self.ptrs=defaultdict(list)
  for sec in self.e.iter_sections():
   if sec['sh_type']=='SHT_RELA':
    sy=self.e.get_section(sec['sh_link'])
    for r in sec.iter_relocations():
     idx=r['r_info_sym'];sym=sy.get_symbol(idx) if idx else None;val=(sym['st_value'] if sym else 0)+r['r_addend'];self.ptrs[val].append({'slot':hex(r['r_offset']),'symbol':sym.name if sym else '', 'type':r['r_info_type']})
  self.rev=None
 def read(self,v,n):
  s=next(s for s in self.segs if s['p_vaddr']<=v and v+n<=s['p_vaddr']+s['p_filesz']);o=s['p_offset']+v-s['p_vaddr'];return self.raw[o:o+n]
 def dis(self,v,n):
  rows=[]
  for i in self.cs.disasm(self.read(v,n),v):
   d={'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
   if i.mnemonic in ('b','bl') and i.op_str.startswith('#'):d['symbol']=self.plt.get(int(i.op_str[1:],16),'')
   rows.append(d)
  return rows
 def branches(self):
  if self.rev is None:
   self.rev=defaultdict(list)
   for sec in self.e.iter_sections():
    if not sec['sh_flags']&4:continue
    b=sec.data();base=sec['sh_addr']
    for k,(w,) in enumerate(struct.iter_unpack('<I',b[:len(b)//4*4])):
     if w&0x7c000000==0x14000000:
      imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm;v=base+k*4;self.rev[v+4*imm].append({'va':hex(v),'kind':'bl' if w>>31 else 'b'})
  return self.rev
 def xref(self,v):return {'target':hex(v),'branches':self.branches().get(v,[]),'relocations':self.ptrs.get(v,[])}
 def symbols(self,pat):return {n: {'va':hex(v),'size':hex(sz)} for n,(v,sz) in self.syms.items() if re.search(pat,n,re.I)}
def main():
 if len(sys.argv)>1:
  mode,name,*args=sys.argv[1:];im=Image(name)
  if mode=='dis':
   for r in im.dis(int(args[0],16),int(args[1],16)):print(r['va'],r['asm'],r.get('symbol',''))
  elif mode=='xref':
   for a in args:print(json.dumps(im.xref(int(a,16))))
  elif mode=='sym':print(json.dumps(im.symbols(args[0]),indent=2))
  elif mode=='sections':print([(s.name,hex(s['sh_addr']),hex(s['sh_size'])) for s in im.e.iter_sections()])
  return
 build_proof()

EXPECTED={'libosal_uipc.so':'09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3','appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f','libObj.so':'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae'}
WINDOWS={
'libosal_uipc.so':[(0x6b78,0x234),(0x3cd8,0x90),(0x4d38,0x4c)],
'appFw.so':[(0x16ee598,0x100),(0x16ee698,0x150),(0x16ee8d8,0x164),(0x176fb4c,0xac),(0x176fc2c,0x160),(0x176fdac,0x84),(0x176fe2c,0x21c),(0x177003c,0x24),(0x176d838,0x84),(0x177af28,0x520),(0x1726cf0,0x50),(0x2191c10,0x1f0),(0x16f1998,0xb0),(0x16f2220,0x484),(0x16f16bc,0x160),(0x16f1118,0x70),(0x16f1358,0xf0),(0x16f1c18,0xf0),(0x16f1d08,0x16c),(0x2172b40,0x54),(0x2bb0b28,0x54),(0x2bb2e94,0x54),(0x16f1a48,0x19c),(0x2b6353c,0x148),(0x2b67a60,0x11c),(0x2b61efc,0x1c0),(0x2b6241c,0x20),(0x2b60208,0x110),(0x2dec778,0x130),(0x2dcb9c0,0x48),(0x2dd1014,0x40),(0x2dee6f0,0x84),(0x2dd2194,0x40),(0x2dd4534,0x40)],
'libObj.so':[(0x17473c,0x3c),(0x17697c,0x134),(0x176ab0,0xb4),(0x177548,0x108),(0x177650,0x1a8),(0x177f20,0xf0),(0x176ba4,0x14),(0x132ad4,0x100),(0x1770fc,0x68),(0x1771f4,0x84),(0x16ea10,0xd4),(0x10f29c,0x7c),(0x10eae0,0x23c),(0x1528b8,0xa8),(0x1535e4,0x134),(0x1017ac,0x1c4),(0x1013a8,0xc8),(0x100b40,0xc4),(0xfc184,0xa0),(0xfbee4,0xac),(0x100cfc,0x74),(0x100c48,0xb4),(0x16daac,0x50),(0x16dc30,0xd4),(0x10dce4,0x68),(0x10daf8,0xc0),(0x10f29c,0x7c),(0x177fc8,0x48),(0x178190,0x50),(0x16dc30,0x1c)]}
TARGETS={'libosal_uipc.so':[0x6b78,0x3cd8,0x4d38],'appFw.so':[0x16ee6f8,0x16ee598,0x16ee664,0x16ee6f0,0x16ee8d8,0x176fb4c,0x176fefc,0x176ff74,0x176fdac,0x176fe88,0x16f1998,0x16f2220,0x177af28], 'libObj.so':[0x100c48,0x100cfc,0x100b40,0x1013a8,0x56090,0x10eae0,0x10f29c,0x177548,0x177f20,0x153708]}
def qword(im,v):return int.from_bytes(im.read(v,8),'little')
def cstr(im,v):return im.read(v,256).split(b'\0')[0].decode(errors='replace')
def vtable(im,slot):
 found=[]
 for v in range(slot-0x200,slot,8):
  if qword(im,v)!=0:continue
  ti=qword(im,v+8)
  if not ti:continue
  try:
   name=cstr(im,qword(im,ti+8))
   if name and len(name)<200 and name[0].isalnum(): found.append({'header':hex(v),'typeinfo':hex(ti),'rtti':name,'slot':hex(slot),'offset':hex(slot-v-16),'function':hex(qword(im,slot))})
  except StopIteration:pass
 return found[-1] if found else None

def address_materializations(im,target):
 """Conservative ADR/ADRP+ADD discovery; cannot solve arbitrary computed pointers."""
 hits=[]
 for sec in im.e.iter_sections():
  if not sec['sh_flags']&4:continue
  data=sec.data();base=sec['sh_addr']
  for k,(w,) in enumerate(struct.iter_unpack('<I',data[:len(data)//4*4])):
   if w&0x9f000000 not in (0x90000000,0x10000000):continue
   va=base+4*k;imm=(((w>>5)&0x7ffff)<<2)|((w>>29)&3);imm=imm-(1<<21) if imm&(1<<20) else imm
   if w&0x80000000:
    page=(va&~4095)+(imm<<12)
    if page!=target&~4095:continue
    reg=w&31
    for j in range(1,9):
     if k*4+j*4+4>len(data):break
     x=struct.unpack_from('<I',data,k*4+j*4)[0]
     if x&0xffc00000==0x91000000 and (x>>5)&31==reg and page+((x>>10)&0xfff)==target:
      hits.append({'adrp':hex(va),'add':hex(va+j*4),'bytes':data[k*4:k*4+j*4+4].hex(),'limitation':'candidate only; intervening register writes not symbolically evaluated'})
   elif va+imm==target:hits.append({'adr':hex(va),'bytes':struct.pack('<I',w).hex()})
 return hits

def build_proof():
 p={'scope':'Offline static and saved-log audit only; no QEMU, no patches, writes only adjacent JSON','evidence_levels':{'A':'original instruction/relocation or captured event','B':'inference from A with alternatives retained','U':'not established by saved inputs'},'sources':{},'blocks':{},'xrefs':{},'vtables':{},'runs':{}}
 def source(path):
  b=path.read_bytes();p['sources'][str(path.relative_to(ROOT))]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
 ims={n:Image(n) for n in WINDOWS}
 for n,im in ims.items():
  assert hashlib.sha256(source(im.path)).hexdigest()==EXPECTED[n],n
  p['blocks'][n]={}
  for v,ln in WINDOWS[n]:
   rows=im.dis(v,ln);assert len(rows)*4==ln,(n,hex(v),len(rows));p['blocks'][n][hex(v)]=rows
  p['xrefs'][n]={hex(v):im.xref(v) for v in TARGETS[n]}
  p['vtables'][n]=[vtable(im,int(r['slot'],16)) for target in ([0x176fb4c,0x176ff74] if n=='appFw.so' else [0x100cfc,0x10f29c]) for r in im.ptrs[target]]
 a=ims['appFw.so'];o=ims['libObj.so']
 p['1001_external_entries']=[{'target':hex(t),**r} for t,rs in a.branches().items() if 0x16ee6f8<=t<0x16ee790 for r in rs if not 0x16ee6f8<=int(r['va'],16)<0x16ee790]
 assert p['1001_external_entries']==[{'target':'0x16ee6f8','va':'0x2191df4','kind':'bl'}]
 p['1001_address_taken_scan']={'method':'all executable B/BL, all ELF RELA, all allocated raw qword matches, ADR and nearby ADRP+ADD candidates','limitation':'arbitrary pointer computation, writable runtime vtables and external dlopen/dlsym are not exhaustively solvable statically','address_materializations':address_materializations(a,0x16ee6f8),'raw_qword_matches':[]}
 needle=struct.pack('<Q',0x16ee6f8)
 for sec in a.e.iter_sections():
  if not sec['sh_flags']&2 or sec['sh_type']=='SHT_NOBITS':continue
  data=sec.data();start=0
  while (hit:=data.find(needle,start))>=0:
   p['1001_address_taken_scan']['raw_qword_matches'].append({'section':sec.name,'va':hex(sec['sh_addr']+hit)});start=hit+1
 assert a.xref(0x16ee6f8)['branches']==[{'va':'0x2191df4','kind':'bl'}]
 assert not a.ptrs[0x16ee6f8]
 assert a.read(0x176ff2c,4).hex()=='01d80379'
 p['data_bindings']={hex(v):hex(qword(a,v)) for v in [0x471f428,0x47c8908,0x472c8d8,0x47817f8]}
 p['data_bindings_note']='GOT entries with raw zero may be symbol relocations; this is not a runtime ID readback'
 p['sequence30170_rtti']=[vtable(a,int(r['slot'],16)) for t in [0x2bb0b28,0x2bb2e94] for r in a.ptrs[t]]
 assert any(r['va']=='0x16f247c' and r['asm']=='cmp w0, #2' for r in p['blocks']['appFw.so']['0x16f2220'])
 assert any(r['va']=='0x16f1d64' and r['asm']=='sub w0, w0, #1' for r in p['blocks']['appFw.so']['0x16f1d08'])
 p['timer_event_vtable']={'header':hex(qword(o,0x261358)),'execute_slot':hex(qword(o,0x261358)+0x20),'execute':hex(qword(o,qword(o,0x261358)+0x20))}
 names=['ap60entries-5611350a','ap66lut-ed5764ad','ap70lcd-f61554d9','ap71crypt-68d9c419','ap72muted-f2a05842','ap73gpe240-6c2f3137','ap75final1-a67fe198','ap75final2-4d01e9f8']
 for name in names:
  run=RT/'runs'/name;ls=source(run/'serial.log').decode(errors='replace').split('\n');d={'line_number_rule':'LF split; CR/NUL retained','events':[],'profiles':[],'counts':{}}
  keys=['FX3_TIMER_','FX3_UI_WIRE','FX3_UI_CONFIG','FX3_GPE_UNIFORM_DONE','FX3_ADF_','target=0x8280074d ','target=0x80820884 ','target=0x8280084d ','raw=0d202503','raw=0d202e03','raw=0d203d03','raw=0d202703','raw=0d202a03','header=0x325200d','name=AppFw ','Skip snd to 0x747','target=0x5503e0 ','target=0x910040 ']
  for j,l in enumerate(ls):
   if any(k in l for k in keys):d['events'].append({'line':j+1,'text':l})
   if 'FX3_PROFILE_STACK_BEGIN' in l:
    end=next((k for k in range(j+1,min(j+24,len(ls))) if 'FX3_PROFILE_STACK_END' in ls[k]),j)
    d['profiles'].append({'start_line':j+1,'end_line':end+1,'lines':ls[j:end+1]})
  for key in ['FX3_UI_WIRE','FX3_GPE_UNIFORM_DONE','FX3_UI_CONFIG_RETURN','FX3_TIMER_ENTRY','raw=0d202503','raw=0d202703']:
   d['counts'][key]=sum(key in l for l in ls)
  d['1001_wires']=[e for e in d['events'] if 'FX3_UI_WIRE' in e['text'] and 'target=0x8280074d ' in e['text'] and 'tag1=0x1001 ' in e['text']]
  wake=[e for e in d['events'] if 'target=0x5503e0 ' in e['text'] and 'tag1=0x150000 ' in e['text']]
  d['wake_sender_snapshots']=[]
  if wake:
   match=re.search(r'tid=(\d+)',wake[0]['text'])
   if match:
    tid=match[1]
    for j,l in enumerate(ls):
     if 'FX3_TASK_SNAPSHOT_'+tid+'_BEGIN' in l:
      end=next((k for k in range(j+1,min(j+100,len(ls))) if 'FX3_TASK_SNAPSHOT_'+tid+'_END' in ls[k]),j)
      d['wake_sender_snapshots'].append({'start_line':j+1,'end_line':end+1,'lines':ls[j:end+1]})
  d['1001_contexts']=[{'start_line':max(1,e['line']-5),'lines':ls[max(0,e['line']-6):e['line']+7]} for e in d['events'] if 'target=0x8280074d ' in e['text'] and 'tag1=0x1001 ' in e['text']][:8]
  if name.startswith('ap75final'):
   assert len(d['1001_wires'])==6,(name,len(d['1001_wires']))
   snaps=[e for e in d['events'] if 'FX3_TIMER_SNAPSHOT ' in e['text']];assert len(snaps)==6
   assert all('patch_mask=0xf ' in e['text'] and 'timer_entry=0 ' in e['text'] and 'config=0 ' in e['text'] and 'fill=0 ' in e['text'] for e in snaps)
   ends=[e for e in d['events'] if 'FX3_TIMER_OBSERVER_END ' in e['text']];assert ends and all('config=0 ' in e['text'] and 'timer_entry=0 ' in e['text'] and 'fill=0 ' in e['text'] for e in ends)
   assert d['counts']['FX3_GPE_UNIFORM_DONE']==0
   d['receipt']=json.loads(source(run/'receipt.json'));assert d['receipt']['requested_seconds']==240
   cp=Path(d['receipt']['candidate']);assert hashlib.sha256(source(cp)).hexdigest()==d['receipt']['candidate_sha256']
  p['runs'][name]=d
 for file in ['helpers/fx3-timer-observe-v3.c','helpers/ioctl-trace-v12.c']:
  path=RT/file;ls=source(path).decode(errors='replace').split('\n');p.setdefault('observer_sources',{})[file]=[{'line':j+1,'text':l} for j,l in enumerate(ls) if any(k in l for k in ['addresses[4]','FX3_UI_WIRE','FX3_TIMER_SNAPSHOT','FX3_TIMER_BOUND','config_hook'])]
 p['utimer_module']=module_proof(source)
 p['findings']=[
 {'level':'A','claim':'AP75 config=0 counts entry into16ee6f8 itself; six1001 wires therefore did not originate from16ee6f8 or2191df4','evidence':['observer_sources/helpers/fx3-timer-observe-v3.c','runs/ap75final1-a67fe198','runs/ap75final2-4d01e9f8']},
 {'level':'A','claim':'Other1001 constructors exist:176fefc writes persistent widget+1ec then16ee664;176fdac sends same record on state/mode change via16ee6f0;16ee8d8 constructs four records but sole direct caller2191dfc belongs config branch'},
 {'level':'B','claim':'AP75 six1001 are most consistent with monitor widget initialization/refresh, not config; individual six cannot be uniquely assigned without payload or stack'},
 {'level':'A','claim':'Widget timer registration176fe88 is shared refcount gated; first participant adds type1/156 with synchronization ID fromgenIDForSystem(f1ae2d31), storing runtime ID at7883db8'},
 {'level':'A','claim':'AppFw16f1998 drives both timer update177650->177548->177f20->widget vtable+f8 and draw16ea10. AppFw outer wake uses original utimer.ko910040 service and5503e0 message from uipc_proxy_0; no per-widget OSAL timer allocation in addTimer'},
 {'level':'A','claim':'GRM_gpermFillrect1017ac creates CmdFillrect via1013a8/100b40, queues viafc184/fbee4, virtual execute100cfc checks state1 then100c48'},
 {'level':'B','claim':'AP60/AP70 initial clear while ADF boot work not yet completed refutes exclusive dependence on normal four-task barrier; no proven edge from post2b67a70 to the first clear'},
 {'level':'B','claim':'A concrete timing candidate is backlog gating:16f1a48 increments a18,16f1d64 decrements on150000 consumption,16f247c..2488 skips UI when backlog>2 and a12=0; AP75 backlog was not sampled'},
 {'level':'U','claim':'The exact AppFw startup/wake/time/dirty gate differentiating runs, initial clear concrete high-level caller, and exact six1001 sender identities remain unobserved'},
 {'level':'A','claim':'AP75 has muted32e/33d model commits and next327 request; saved stream has no325 request, no13-registration completion, no four-handle completion receipt'},
 {'level':'U','claim':'license_get_i and adf_get_func_i current completion status; post-barrier model path/request/digital notify still need original replies'}]
 p['unresolved']=['Six1001 per-message caller/payload identification; excluded16ee6f8 is a firm result, positive assignment is inference','Exact startup call stack at first clear in AP60/AP70','Whether AP75 reached16f2220/16f16bc/16f2640 and original updateCurrentTime return/current clock/deadline','Kernel timer hardware tick and clock stability under current model; original utimer service and UIPC proxy wake delivery identified','Full virtual-call closure from post-barrier initialization or boot notification into AppFw UI state machine','Current four worker handles and matched completion count; license and325 cannot be called complete based on absent logs']
 target=OUT/'ui-start-gate-proof.json';target.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
 print('PASS: rebuilt ui-start-gate-proof.json; original hashes, complete selected disassembly, xrefs, vtables, AP75 six wires and zero hooks verified; unresolved gates retained')
 for n in names:print(n,p['runs'][n]['counts'])


def module_proof(source):
 path=RT.parent/'original-uipc/original-modules/utimer.ko';raw=source(path)
 with path.open('rb') as f:
  e=ELFFile(f);b=e.get_section_by_name('.text').data();rs=e.get_section_by_name('.rela.text');sy=e.get_section(rs['sh_link'])
  rel={}
  for r in rs.iter_relocations():
   sym=sy.get_symbol(r['r_info_sym']);idx=sym['st_shndx'];rel[r['r_offset']]={'symbol':sym.name,'section':e.get_section(idx).name if isinstance(idx,int) else idx,'addend':hex(r['r_addend'])}
  assert rel[0x1ed8]['section']=='.text' and rel[0x1ed8]['addend']=='0x1cb0'
  assert rel[0x1e48]['symbol']=='osal_reg_sync_msg_queue_cb'
  assert rel[0x5c0]['symbol']=='osal_snd_msg'
  d={'sha256':hashlib.sha256(raw).hexdigest(),'address_rule':'relocatable kernel module: offsets are .text+offset, NOT loaded VAs','literal_bindings':{hex(v):rel[v] for v in [0x1ec8,0x1ed8,0x1ee0,0x2278]},'blocks':{}}
  c=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
  for v,n in [(0x1e08,0xbc),(0x1cb0,0xd4),(0x520,0xa8),(0xb90,0x160),(0x2120,0x12c),(0x2520,0x38),(0x398,0xd8)]:
   d['blocks'][hex(v)]=[{'offset':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,**({'relocation':rel[i.address]} if i.address in rel else {})} for i in c.disasm(b[v:v+n],v)]
  return d
if __name__=='__main__':main()
