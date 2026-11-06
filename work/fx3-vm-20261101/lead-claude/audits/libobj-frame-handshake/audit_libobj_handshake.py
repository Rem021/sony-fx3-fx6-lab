#!/usr/bin/env python3
"""Offline original ELF/log audit; writes only adjacent proof JSON."""
import hashlib,json,re,sys,subprocess,plistlib
from pathlib import Path
from capstone import *
from elftools.elf.elffile import ELFFile
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'work/sony-firmware-20261024').is_dir())
RT=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime'
LIB=RT.parent/'original-uipc/ap-projection/regular-files/usr/lib'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'].upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
proof={'scope':'offline static/log evidence only; no QEMU or runtime modifications','sources':{},'blocks':{},'runs':{}}
def source(p):
 b=p.read_bytes();proof['sources'][str(p.relative_to(ROOT))]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
class Image:
 def __init__(self,name):
  self.name=name;self.p=LIB/name;self.b=source(self.p);self.f=self.p.open('rb');self.e=ELFFile(self.f);self.segs=[s for s in self.e.iter_segments() if s['p_type']=='PT_LOAD'];r=self.e.get_section_by_name('.rela.plt');sy=self.e.get_section(r['sh_link']);pv=self.e.get_section_by_name('.plt')['sh_addr'];self.plt={pv+32+16*n:sy.get_symbol(x['r_info_sym']).name for n,x in enumerate(r.iter_relocations())}
 def read(self,v,n):
  s=next(s for s in self.segs if s['p_vaddr']<=v<s['p_vaddr']+s['p_filesz']);o=s['p_offset']+v-s['p_vaddr'];return self.b[o:o+n]
 def dis(self,v,n):
  c=Cs(CS_ARCH_ARM64,CS_MODE_ARM);rows=[]
  for i in c.disasm(self.read(v,n),v):
   r={'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
   if i.mnemonic in ('bl','b') and i.op_str.startswith('#'):r['symbol']=self.plt.get(int(i.op_str[1:],16),'')
   rows.append(r)
  return rows
if __name__=='__main__' and len(sys.argv)>1:
 im=Image(sys.argv[1]);v=int(sys.argv[2],16);n=int(sys.argv[3],16)
 for r in im.dis(v,n):print(r['va'],r['asm'],r.get('symbol',''))
 sys.exit(0)
# Complete source-backed function windows, each instruction retains raw bytes.
windows={
 'appFw.so':[(0x16ee574,0x90),(0x16ee604,0x60),(0x16ee6f0,0x9c),(0x16ee790,0x38),(0x176fb4c,0xac),(0x2191d98,0x68)],
 'libObj.so':[(0xf1d90,0x118),(0xf1fbc,0x8c),(0xf233c,0x44),(0xf2428,0x148),(0xf25f4,0x1e4),(0xf2820,0x244),(0xf2fa0,0x10c),(0xf33d0,0x34),(0xf3bf4,0xac),(0x100c48,0xac),(0x1017ac,0x1c4),(0x1747e0,0x28),(0x176ab0,0xb4)],
 'libgpe.so':[(0xa430,0xe4),(0x9ba4,0x160),(0xd814,0x38)],
 'libosal_uipc.so':[(0x5e60,0x2ac),(0x6468,0x344),(0x75b8,0x730)]}
for name,ws in windows.items():
 im=Image(name);proof['blocks'][name]={}
 for v,n in ws:
  rows=im.dis(v,n);assert len(rows)*4==n,(name,hex(v));proof['blocks'][name][hex(v)]=rows
assert any(r['asm']=='strh w0, [x29, #0x50]' for r in proof['blocks']['appFw.so']['0x176fb4c'])
assert not any(r['asm'].startswith(('strh','str ')) and '#0x52]' in r['asm'] for r in proof['blocks']['appFw.so']['0x176fb4c'])
CP=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin';cp=source(CP);cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
proof['blocks']['cpapp']={}
for v,n in [(0x4b3628,0xb4),(0x4b36fc,0x11c)]:
 proof['blocks']['cpapp'][hex(v)]=[{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(cp[v-0x108000:v-0x108000+n],v)]
run_names=['ap60entries-5611350a','ap66lut-ed5764ad','ap70lcd-f61554d9','ap71crypt-68d9c419','ap72muted-f2a05842','ap73gpe240-6c2f3137']
for name in run_names:
 run=RT/'runs'/name;p=run/'serial.log';lines=source(p).decode(errors='replace').split('\n');d={'serial_lines':len(lines),'events':[],'snapshots':[],'printk':[]}
 # Exact event records; no binary-file early-stop behaviour (some serial logs contain NUL).
 for j,line in enumerate(lines):
  if any(s in line for s in ['target=0x8280074d ','target=0x8280084d ','target=0x8288076c ','target=0x80820884 ','FX3_GPE_UNIFORM_DONE','FX3_REMOTE_DMM_COMMIT','Skip snd to 0x74d','Skip snd to 0x84d','queue=0x8288076c ','name=grm_gpe ','name=MPGRM_GPE0 ']):d['events'].append({'line':j+1,'text':line})
  if re.search(r'Name:\s*(grm_gpe|grm_result|ExternalOSDIF|MPGRM_GPE0|AppFw)\s*$',line):
   end=next((k for k in range(j+1,min(j+240,len(lines))) if 'FX3_TASK_SNAPSHOT_' in lines[k] and '_END' in lines[k]),min(j+70,len(lines)))
   d['snapshots'].append({'line':j+1,'end_line':end+1,'text':lines[j:end+1]})
 q=run/'printk-decoded.txt'
 for j,line in enumerate(source(q).decode(errors='replace').split('\n')):
  if any(s in line for s in ['grm_ma','0x74d','0x84d','Skip snd']):d['printk'].append({'line':j+1,'text':line})
 d['handshake_context']=[]
 for ev in d['events']:
  if 'target=0x8280074d ' in ev['text'] and 'tag1=0x1001 ' in ev['text']:
   j=ev['line']-1;d['handshake_context'].append({'start_line':max(1,j-15),'lines':lines[max(0,j-16):j+26]})
 d['counts']={s:sum(s in line for line in lines) for s in ['FX3_GPE_UNIFORM_DONE','target=0x80820884 ','target=0x8280084d ','Skip snd to 0x74d','Skip snd to 0x84d']}
 proof['runs'][name]=d
proof['conclusions']={
 'confirmed_1004':'appFw 176fb4c gates on matching timer ID and WidgetBase::getTimerInfo success; sends 16B via16ee790->16ee598. This is not a reply to1001.',
 'confirmed_padding':'176fbcc writes u16 at stack+50; +52/+53 are not written in this function. tag1 high16 is padding; valid-field use of uninitialized bytes not established.',
 'confirmed_1001':'appFw16ee6f8 constructs 96B and sends asynchronously via16ee598; source9088076b destination8280074d. No receive wait in this sender.',
 'confirmed_local_queue':'libObj f293c receives8288076c as ExternalOSDIF; source8280074d dispatches6003/6005, not1001; f2638 emits1002 then1003 to8280084d.',
 'confirmed_cp_data_consumer':'cpapp4b3628 selects8280084d for1003 (and adjacent queue for1005), waits via49f9b0 then dispatches4b36fc.',
 'root_cause_status':'Exact run-dependent gate not observable in saved logs. Timer ID mismatch/missing record/callback not reached and independent render gating remain alternatives. Preload causality unproven.',
 'minimal_fix_status':'No runtime patch is justified solely by temporal adjacency; instrument timer registration/update and render branch, then preserve deferred update until timer registry ready if race is confirmed.'}
source(RT/'helpers/ioctl-trace-v10.c')
proof['unresolved']=['8280074d control receiver and1001 consumption implementation','full OSAL queue bitfield decomposition','AP71 callback entered vs ID mismatch vs getTimerInfo miss','causal connection from1004 omission to initial FillRect omission','deterministic runtime correction and verification (runtime prohibited)']
(OUT/'libobj-handshake-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
for name,d in proof['runs'].items():
 print(name,d['counts'])
 for ev in d['events']:
  if any(t in ev['text'] for t in ['target=0x8280074d ','target=0x8280084d ','target=0x8288076c ','target=0x80820884 ','FX3_GPE_UNIFORM_DONE']):print(ev['line'],ev['text'])
print('PASS: rebuilt libobj-handshake-proof.json (offline); unresolved gates retained explicitly')
