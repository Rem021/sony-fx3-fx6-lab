from pathlib import Path
import sys,json,hashlib,struct
from capstone import *
from elftools.elf.elffile import ELFFile
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac'); OUT=Path(__file__).resolve().parent
AP=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
CP=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
a=AP.read_bytes(); b=CP.read_bytes(); ef=ELFFile(AP.open('rb'))
def read(kind,va,n):
 if kind=='cp': return b[va-0x108000:va-0x108000+n]
 s=next(s for s in ef.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va<s['p_vaddr']+s['p_filesz']); o=s['p_offset']+va-s['p_vaddr']; return a[o:o+n]
def dis(kind,va,n):
 c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if kind=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in c.disasm(read(kind,va,n),va)]
if len(sys.argv)>1:
 kind=sys.argv[1]
 for spec in sys.argv[2:]:
  va,n=(int(x,16) for x in spec.split(':'))
  for i in dis(kind,va,n): print(i['va'],i['instruction'])
 sys.exit()
# No guest execution, no input mutation. Fail closed on changed original images.
assert hashlib.sha256(a).hexdigest()=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
assert hashlib.sha256(b).hexdigest()=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
ap_blocks=[(0x2ded154,0x1b0),(0x2deea08,0x78),(0x2dd0ed4,0x40),(0x2dd0fd4,0x40),(0x2de70a8,0x29c),(0x2de4574,0x168),(0x2b5fae4,0x15c),(0x2b61a90,0x458),(0x2b61798,0x2f8),(0x2b6096c,0xbdc),(0x2b638b8,0x50),(0x2b66dc8,0x40),(0x2b6765c,0x20),(0x2b67a60,0x48),(0x2b6353c,0x148),(0x2b63224,0xf8),(0x2dcb994,0x74),(0x2b60208,0x60),(0x2dd0c94,0x40),(0x2dec778,0xa0),(0x2b61efc,0x44),(0x2e50378,0xd0),(0x2dda3b4,0x40),(0x2dda5b4,0xc0),(0x2dd4734,0x40),(0x2e15a18,0x18c)]
cp_blocks=[(0x1b2574,0x80),(0x1b35e4,0x50),(0x1ac0ae,0x26),(0x1ac312,0x28),(0x5ca404,0x52),(0x5ca880,0x86),(0x596cce,0xa4),(0x162834,0x70),(0x5ad776,0x128),(0x5a90a6,0x78),(0x5a9154,0x80),(0x5daac2,0x64),(0x5dab34,0x80)]
proof={'scope':'Read-only offline audit; only own script/proof/README written; no QEMU, runtime edits or camera access','sources':{'AP':{'path':str(AP),'sha256':hashlib.sha256(a).hexdigest()},'CP':{'path':str(CP),'sha256':hashlib.sha256(b).hexdigest()}},'blocks':{'AP':{hex(v):dis('ap',v,n) for v,n in ap_blocks},'CP':{hex(v):dis('cp',v,n) for v,n in cp_blocks}}}
def ins(kind,v):
 return next(i['instruction'] for block in proof['blocks'][kind].values() for i in block if i['va']==hex(v))
checks=[('AP',0x2ded1f4,'bl #0x2de70a8'),('AP',0x2deea5c,'bl #0x2de70a8'),('AP',0x2de72fc,'mov w2, #-1'),('AP',0x2b67a6c,'bl #0x2b6353c'),('AP',0x2b6153c,'add x2, x2, x25'),('CP',0x5ca8a2,'movw r0, #0x133d'),('CP',0x5ca422,'movw r0, #0x132e'),('CP',0x596d08,'movw r0, #0x8311'),('CP',0x5ad81a,'movt r0, #0x820a')]
for k,v,s in checks: assert ins(k,v)==s,(k,hex(v),ins(k,v),s)
proof['checked_instructions']=[{'image':k,'VA':hex(v),'expected':s} for k,v,s in checks]
proof['strings']={}
for kind,vs in [('ap',[0x391a590,0x391a5c0,0x391a5f0,0x391a620,0x391a678,0x391a718,0x3917e31,0x39184f4,0x3918523,0x39184bf]),('cp',[0x1b25f4,0x1b3634,0xb3b730,0xb38890,0xd7dc95])]:
 for v in vs:proof['strings'][kind+':'+hex(v)]=read(kind,v,220).split(b'\0')[0].decode(errors='replace')
ptrs={0x472c3c0:0x2b61efc,0x472b2d0:0x2b5fae4,0x474f098:0x2b61a90,0x47a6698:0x2b60208}
for v,w in ptrs.items():assert struct.unpack('<Q',read('ap',v,8))[0]==w
proof['boot_tasks']=[{'handle_stack_offset':hex(s),'GOT_VA':hex(v),'entry':hex(ptrs[v]),'name':name} for s,v,name in [(0x70,0x472c3c0,'license_get_i'),(0x6c,0x472b2d0,'adf_set_volume_i'),(0x68,0x474f098,'regist_beep_signals_i'),(0x64,0x47a6698,'adf_get_func_i')]]
proof['barrier']={'VA':'0x2b67a60..0x2b67a6c','join':'0x2b6353c','predicate':'four matching completions; condition wait 0x2b635d0; decrements 0x2b63648, repeats until zero 0x2b63678','verdict':'033d blocks normal boot barrier; 032e likewise; direct menu-render dependency not traced; no VDF011a in this four-task group'}
# Extract builtin ranges by evaluating only immediate moves and first stack argument at calls to regist helper.
regs={}; stack={}; rows=[]
for i in dis('ap',0x2b61a90,0x2dc):
 op=i['instruction']; mt=__import__('re').fullmatch(r'mov ([wx]\d+), #(0x[0-9a-f]+|\d+)',op)
 if mt:regs[int(mt[1][1:])]=int(mt[2],0)
 if op=='stp xzr, xzr, [sp]':stack[0]=0
 mt=__import__('re').fullmatch(r'stp x(\d+), xzr, \[sp\]',op)
 if mt:stack[0]=regs.get(int(mt[1]))
 if op=='bl #0x2b61798':rows.append({'index':regs.get(1),'length':regs.get(7),'offset':stack.get(0),'call_VA':i['va']})
proof["all_sound_registration_rows"]=rows
rows=[r for r in rows if r["length"]]
assert len(rows)==9,rows
assert max(r['offset']+r['length'] for r in rows)==0x8480
proof['builtin_buffer']={'ranges':rows,'minimum_extent_hex':'0x8480','rounded_4KiB_hex':'0x9000','proposed_reservation_bytes':65536,'proposed_alignment_bytes':65536,'content':'Original CP builtin sound bytes at the nine offsets, or separately declared no-playback model; zero-filled region is not native sound fidelity','native_encoding':'UNPROVEN (sample rate/channel count/bit depth/codec)','native_allocation_extent':'UNPROVEN; AP observed extent is a lower bound','writer':'Not AP boot for builtin ranges: AP uses base+offset at 0x2b61538. CP/platform producer and original asset provenance not traced. File-backed sounds use separate DMM allocations.'}
proof['CP_resource']={'table_VA':'0xb6eccc','bytes':read('cp',0xb6eccc,12).hex(),'resource_id':'0xfa01a0','parameter_offset':'0x12','parameter_size':8,'parameter_base_BSS':'0x1438cdd','physical_address_value':'UNPROVEN: runtime parameter contents outside cpapp file','lookup':'0x5a90a6 ->0x5a9154 ->0x5a90ea; 0x5ad786 reads 8 LE bytes or returns 0xefff'}
proof['wire_contract']={'032e':{'request':'0d202e030a0001800800','AP_reply':'0d202e130c00018000000000','legacy_request':'2004/0311/12B/0001, u8 volume at +8','legacy_reply':'2004/8311/12B/0001, status32 +8=0','semantics':'0x596cde ->0x162834 maps wire 1..16 to internal 0..15; 0 mute, >16 clamp15; wire8 becomes7; completion does not prove audible hardware output'},'033d':{'request':'0d203d0308000180','AP_reply':'200d/133d/24B/8001, status32+8=0; reserved32+12=0; phys64LE+16','legacy_request':'2004/020a/8B/0001','legacy_reply':'2004/820a/24B/0001, phys64LE+8, status32+16; trailing32 cleared','semantics':'Read configured builtin system sound base; success0, lookup failure0xefff; bridge copies physical only for old command820a'}}
run=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap69audio-1cbbef9f/serial.log'; lines=run.read_text(errors='replace').splitlines()
proof['runtime']={'path':str(run),'sha256':hashlib.sha256(run.read_bytes()).hexdigest(),'stacks':{},'requests':[],'reservations':[]}
for h in ['0x32e200d','0x33d200d']:
 ix=next(i for i,l in enumerate(lines) if 'FX3_PROFILE_STACK_BEGIN' in l and 'header='+h in l);end=next(i for i in range(ix,len(lines)) if 'FX3_PROFILE_STACK_END' in lines[i]);proof['runtime']['stacks'][h]=[{'line':i+1,'text':lines[i]} for i in range(ix,end+1)]
for i,l in enumerate(lines):
 if 'FX3_PROVIDER_REQUEST' in l and any(x in l for x in ['raw=0d202e030a0001800800','raw=0d203d0308000180']):proof['runtime']['requests'].append({'line':i+1,'text':l})
 if 'memrsv:' in l and ('41d800000' in l or '41d900000' in l):proof['runtime']['reservations'].append({'line':i+1,'text':l})
assert len(proof['runtime']['requests'])==2
proof['minimal_model']={'volume':'Exact boot request only, retain wire8/internal7; route a single status0 completion to captured source. No hardware-audio claim.','address':'Do not enable success until reserved nonoverlapping guest RAM and backing contents are owned and ready. Proposed 64KiB at 64KiB alignment, e.g. 0x41da00000 only after independent map check, new memrsv, and lifetime binding. This is proposal, not deployed allocation.','builtin_content_gate':'Original builtin bytes not located; native-compatible success remains gated. A deliberately silent software-only backend can use zero storage only if playback is disabled and semantics declared.','file_sounds':'Separate local and remote DMM, mmap/fread/interchip transfer/unmap/free and ADF set_table/set_volume require independent models; 033d reply does not satisfy these.'}
proof['reject_set']=['wrong destination/type/command/header/declared or actual length','032e volume other than8 or nonzero padding in boot-only profile','033d payload or nonzero reserved bytes','unbound requester/source or duplicate completion','zero/truncated/unreserved/overlapping/out-of-guest-RAM physical address','unknown asset bytes offered as native-compatible sound','buffer smaller than0x8480, overflowing base+offset+length, mapping alignment violation','reservation absent, owner/lifetime unbound, inaccessible backing','claiming DMM/file-transfer/playback/menu success from reply construction alone']
proof['unproven']=['CP builtin data producer and original bytes, waveform format and native full extent/alignment','Direct menu-render notification downstream of boot barrier','Runtime consumption of proposed replies, DMM/file-sound continuation and visual acceptance','Strict original reply command/length verification inside AP UIPC transport beyond shown wrapper (wrapper copies fixed count and consumes status)']
(OUT/'adf-032e-033d-proof.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
print('PASS: pinned AP/CP images, 9 instruction checks, 4 boot-task pointers, 9 builtin ranges, 2 captured requests; proof rebuilt')
