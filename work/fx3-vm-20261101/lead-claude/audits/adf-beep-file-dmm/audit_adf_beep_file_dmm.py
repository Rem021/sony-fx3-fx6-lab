from pathlib import Path
import sys,json,hashlib,struct
from capstone import *
from elftools.elf.elffile import ELFFile
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac');OUT=Path(__file__).resolve().parent
PROJ=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection'
FILES={'ap':PROJ/'regular-files/usr/lib/appFw.so','cp':ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin','icdt':PROJ/'regular-files/usr/lib/libInfraInterchipDatatrans.so'}
def load(k):
 p=FILES[k];data=p.read_bytes();return data,None if k=='cp' else ELFFile(p.open('rb'))
def read(k,v,n):
 data,e=load(k)
 if k=='cp':return data[v-0x108000:v-0x108000+n]
 s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v<s['p_vaddr']+s['p_filesz']);o=s['p_offset']+v-s['p_vaddr'];return data[o:o+n]
def dis(k,v,n):
 c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if k=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in c.disasm(read(k,v,n),v)]
if len(sys.argv)>1:
 k=sys.argv[1]
 if sys.argv[2]=='symbols':
  _,e=load(k)
  for s in e.get_section_by_name('.dynsym').iter_symbols():
   if s['st_value']:print(hex(s['st_value']),s.name)
 elif sys.argv[2]=='find':
  d,e=load(k);needle=bytes.fromhex(sys.argv[3]);pos=0
  while (pos:=d.find(needle,pos))>=0:
   v=pos+0x108000 if e is None else next((pos-s['p_offset']+s['p_vaddr'] for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_offset']<=pos<s['p_offset']+s['p_filesz']),pos)
   print(hex(v),d[max(0,pos-16):pos+64].hex());pos+=1
 else:
  for spec in sys.argv[2:]:
   v,n=map(lambda x:int(x,16),spec.split(':'))
   for i in dis(k,v,n):print(i['va'],i['instruction'])
 sys.exit()
def decode_cfg(raw):
 at=0
 def take(n):
  nonlocal at
  assert at+n<=len(raw);v=at;at+=n;return v,raw[v:at]
 result={}
 for phase in ['roots','rules']:
  rows=[]
  while True:
   o,h=take(80);typ,sel=struct.unpack_from('<II',h,8)
   if typ==0xffffffff:break
   rr=[]
   while True:
    p,d=take(20);w=struct.unpack('<5I',d)
    if w[2]==0xffffffff:break
    rr.append({'offset':hex(p),'words':w})
   rows.append({'offset':hex(o),'type':typ,'selector':sel,'header':h.hex(),'rows':rr})
  result[phase]=rows
 units=[]
 while True:
  o,d=take(8);unit,attr=struct.unpack('<II',d)
  if unit==0xffffffff:break
  refs=[]
  while True:
   _,d=take(4);v=int.from_bytes(d,'little')
   if v==0xffffffff:break
   refs.append(v)
  units.append({'offset':hex(o),'unit':unit,'attribute':attr,'extents':refs})
 _,d=take(44);assert at==len(raw);result['version']=d.decode();result['units']=units;return result
p={'scope':'STATIC ONLY; no QEMU/runtime mutation/device access','sources':{},'blocks':{}}
for k,f in FILES.items():
 p['sources'][k]={'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
assert p['sources']['ap']['sha256']=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
assert p['sources']['cp']['sha256']=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
for k,rs in {'ap':[(0x2b6096c,0x1030),(0x2e4efb8,0x2c8),(0x2e4f280,0x1f8),(0x2e50150,0x2f8),(0x2e15a18,0x378),(0x2e1574c,0x140),(0x2dee8b8,0x150),(0x2b616d8,0x24)],'cp':[(0x5a9d54,0x10),(0x18693c,0x98),(0x1b17b4,0x230)],'icdt':[(0x940,0x12c)]}.items():
 p['blocks'][k]={hex(v):dis(k,v,n) for v,n in rs}
checks=[('ap',0x2b60a48,'bl #0x2dda3b4'),('ap',0x2b60aa8,'bl #0x2dda3b4'),('ap',0x2b60fb0,'bl #0x2dd4734'),('ap',0x2e15b7c,'bl #0x1591b30'),('icdt',0x9e8,'bl #0x800'),('icdt',0x97c,'blr x2'),('ap',0x2e4f354,'mov w1, #0x23')]
for k,v,s in checks:assert dis(k,v,4)[0]['instruction']==s
p['checked_instructions']=[{'image':k,'VA':hex(v),'instruction':s} for k,v,s in checks]
# Relocatable kernel addresses are section offsets, NOT runtime VA.
ko=PROJ/'full-v4/regular-files/usr/kmod/icdt.ko';e=ELFFile(ko.open('rb'));sym=e.get_section_by_name('.symtab');rel={x['r_offset']:sym.get_symbol(x['r_info_sym']).name for x in e.get_section_by_name('.rela.text').iter_relocations()}
p['sources']['icdt.ko']={'path':str(ko),'sha256':hashlib.sha256(ko.read_bytes()).hexdigest()}
p['icdt_kernel_text']=[{'text_offset':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'relocation':rel.get(i.address)} for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(e.get_section_by_name('.text').data()[:0x1038],0)]
assert rel[0xd90]=='pcidma_transfer_async' and rel[0x374]=='osal_snd_msg'
p['configurations']={}
for kind,f in [('AP',PROJ/'regular-files/setting/DmmCfg.bin'),('CP',ROOT/'work/sony-firmware-20261024/stage128-DMM-provider-and-config/inputs/DmmCfg.bin')]:
 data=f.read_bytes();cfg=decode_cfg(data);units=[u for u in cfg['units'] if u['unit'] in [0x70817,0x63a]];assert len(units)==2
 rules=[dict(g,rows=[r for r in g['rows'] if r['words'][2] in [231,1792]]) for g in cfg['rules'] if any(r['words'][2] in [231,1792] for r in g['rows'])]
 sizes=[r['words'][3] for g in rules for r in g['rows'] if r['words'][2]==231];assert sizes==[51200]*6
 p['configurations'][kind]={'path':str(f),'sha256':hashlib.sha256(data).hexdigest(),'units':units,'rules':rules,'version':cfg['version'],'conclusion':'unit70817 -> extent231 six50KiB rows; row flags0x10f alignment bit semantics unproven; current branch selection unproven'}
rows=json.loads((OUT.parent/'adf-beep-regist/adf-beep-regist-proof.json').read_text())['normal_sequence'][9:]
manifest=json.loads((PROJ/'full-v5/projection-manifest-full-v5.json').read_text())
def entries(x):
 if isinstance(x,dict):
  if 'guest_path' in x:yield x
  for v in x.values():yield from entries(v)
 elif isinstance(x,list):
  for v in x:yield from entries(v)
es=list(entries(manifest));p['files']=[]
for row in rows:
 entry=next(x for x in es if x.get('guest_path')==row['file']);f=Path(entry['local_file']);d=f.read_bytes();assert hashlib.sha256(d).hexdigest()==entry['sha256']
 p['files'].append({'index':row['index'],'kind':row['kind'],'guest_path':row['file'],'payload':str(f),'bytes':len(d),'sha256':entry['sha256'],'first64':d[:64].hex(),'header_classification':'not RIFF/WAVE; raw proprietary .bin encoding unproven'})
assert [x['bytes'] for x in p['files']]==[2752,2752,9600,12160]
raw=bytes.fromhex('200000001708070000000000ffffffff000000000000010000000000000000000000000000000000');assert len(raw)==40
p['request20']={'raw':raw.hex(),'fields':{'0_u16_op':32,'2_s16_status':0,'4_u32_unit':hex(struct.unpack_from('<I',raw,4)[0]),'8_u32_handle':0,'12_u32_invalid_output_handle':hex(struct.unpack_from('<I',raw,12)[0]),'16_u32':0,'20_u16_correlation':0,'22_u16_open_option':1,'24_39_zero':raw[24:].hex()},'constructor':'AP0x2e4f0a8..0x2e4f0e0','unit_semantics':'opaque unit type0x70817; maps extent0xe7; CPAdfMemMgrCtrl lists it atCP0xb6edcc along with0x72317. High/low name bit semantics unproven.'}
def reply(op,h,addr=0,unit=0,count=0,length=0,corr=0):
 d=bytearray(40);struct.pack_into('<HhHHHHII',d,0,op|0x8000,0,0,corr,count,0,h,unit);struct.pack_into('<QI',d,24,addr,length);return d.hex()
p['model_contract']={'proposal_not_original_CP_physical':'reserve AP0x41db00000/0x60000, six64KiB strides, each advertised0xc800; CPdomain0x1db00000+i*0x10000; do not overlap prior reservations. Verify FDT/kernelreservation before integration.','allocation':'share remote handle namespace; indices2..7 in this proposal to avoid existing63a0..1; bit15 remote, generation1..31; retain4destination slots until unregister/shutdown; local scratch existingDMM freed each round','replies':[]}
for i in range(4):
 h=0x8402+i;addr=0x1db00000+i*0x10000
 p['model_contract']['replies'].append({'kind':10+i,'remote_handle':hex(h),'CPphysical':hex(addr),'APbacking':hex(addr+0x400000000),'8020_40B_corr0':reply(0x20,h,addr,0x70817,1,0xc800),'802a_40B':reply(0x2a,h,addr,0,1,0xc800),'8023_40B_corr0':reply(0x23,h)})
p['model_contract']['transfer']={'request_destination':'0x02820746','request48B_layout':'+0 sourceDesc64 ptr; +8 dstDesc64 ptr; +16 length32; +20 mode32=1; +24 callback64; +32 context64; +40 result32; +44padding','desc8B':'handle32, offset32; current source/dest offsets0 fromAP0x2b60f8c/0x2b60f9c','request_result':'write LE00000000 at+40 before return tolib0x9f0; preserve other fields','completion_destination':'0x0282078f','completion24B':'LE64(original request callback) || LE64(original request context) || 00000000 || 00000000','numeric_completion':'runtime callback/contextASLR values cannot be statically hardcoded; exact bytes must echo captured fields','semantics':'validate distinct domains/live handles/offset+length bounds; record transfer metadata; under explicit mute can zero destination and callbacksuccess once; no CRC/header parsing in pinned DMA path; no PCM/codec/playback','optional_original_driver_path':'If retainingicdt.ko: must reply remote802a query then model pcidma completion; remoteop20success alone insufficient.'}
p['model_contract']['ADF']={'1327':'0d2027130c00018000000000','132a':'0d202a130c00018000000000','327phys':'raw remote DMM+24 copied atAP0x2b61354..358; DO NOT blindly add0x400000000. APbacking and CPphysical domains differ.','size':'freadbyte count; not advertisedslotcapacity'}
p['runtime']={}
for f in sorted((ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/runs').glob('ap74beep-*/serial.log')):
 d=f.read_bytes();ls=d.decode(errors='replace').splitlines();hits=[{'line':i+1,'text':s} for i,s in enumerate(ls) if any(t in s for t in ['raw='+raw.hex(),'FX3_REMOTE_DMM_COMMIT op=0x20','relative=0x2b60c54','relative=0x2b61de4'])]
 p['runtime'][str(f)]={'sha256':hashlib.sha256(d).hexdigest(),'bytes':len(d),'evidence':hits}
p['unproven']=['Native alignment and flags0x10f decoding; physical region selection and originalCP runtime config branch','Mnemonic/unit bitfield naming beyond opaque0x70817 and extent mapping','Guest runtime file availability/open/fread despite verifiedprojectionpayloads','Integration oftransfer service/callback interception and runtime accepted completion','Realwaveformencoding, playback, all4taskbarrier, menu output']
(OUT/'adf-beep-file-dmm-proof.json').write_text(json.dumps(p,indent=2,ensure_ascii=False)+'\n')
print('PASS: images pinned; 7 instruction checks; AP/CP six50KiB config rows; four payloadhashes; kernel DMA/callback chain; reply templates rebuilt')
