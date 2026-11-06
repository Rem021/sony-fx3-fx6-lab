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
import re
assert hashlib.sha256(a).hexdigest()=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
assert hashlib.sha256(b).hexdigest()=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
blocks={'AP':[(0x2b6096c,0x2b61798-0x2b6096c),(0x2b61798,0x464),(0x2dee8b8,0x150),(0x2dd1054,0x80),(0x2de70a8,0x29c),(0x2b60208,0x5d0),(0x2dec778,0x250),(0x2b61efc,0x52c),(0x2b6353c,0x148),(0x2b67a60,0x20)],'CP':[(0x1abf98,0xa0),(0x1b17b4,0x230),(0x1b1d08,0xa0),(0x5ca1c6,0x52),(0x5ca2bc,0x52),(0x5b0080,0x23a),(0x18693c,0x98),(0x1869e0,0x88),(0x5b0606,0x22),(0x186c24,0x54),(0x186c98,0x88)]}
p={'scope':'Offline static read only; no runtime writes, QEMU, device access or firmware mutation','sources':{k:{'path':str(f),'sha256':hashlib.sha256(buf).hexdigest()} for k,f,buf in [('AP',AP,a),('CP',CP,b)]},'blocks':{k:{hex(v):dis(k.lower(),v,n) for v,n in rs} for k,rs in blocks.items()}}
checks=[('AP',0x2dee8e8,'mov w1, #0x327'),('AP',0x2dee96c,'bl #0x2de70a8'),('AP',0x2dee9b8,'mov w1, #0x32a'),('AP',0x2dee9ec,'bl #0x2de70a8'),('AP',0x2b61df0,'cmp w20, #0xd'),('AP',0x2b6153c,'add x2, x2, x25'),('CP',0x1b17cc,'movt r0, #0x201'),('CP',0x1b1d14,'mov.w r1, #0x204'),('CP',0x1869f2,'movw r0, #0x8201'),('CP',0x186caa,'movw r0, #0x8204'),('CP',0x5ca1e4,'movw r0, #0x1327'),('CP',0x5ca2da,'movw r0, #0x132a')]
for k,v,s in checks:
 got=dis(k.lower(),v,4)[0]['instruction']; assert got==s,(hex(v),got,s)
p['checked_instructions']=[{'image':k,'VA':hex(v),'instruction':s} for k,v,s in checks]
regs={};stack={};rows=[]
for i in dis('ap',0x2b61a90,0x2dc):
 op=i['instruction']
 m=re.fullmatch(r'mov ([wx]\d+), #(0x[0-9a-f]+|\d+)',op)
 if m:regs[int(m[1][1:])]=int(m[2],0)
 m=re.fullmatch(r'mov [wx](\d+), [wx](\d+)',op)
 if m:regs[int(m[1])]=regs.get(int(m[2]))
 m=re.fullmatch(r'adrp x(\d+), #(0x[0-9a-f]+)',op)
 if m:regs[int(m[1])]=int(m[2],16)
 m=re.fullmatch(r'add x(\d+), x(\d+), #(0x[0-9a-f]+)',op)
 if m and isinstance(regs.get(int(m[2])),int):regs[int(m[1])]=regs[int(m[2])]+int(m[3],16)
 if op=='stp xzr, xzr, [sp]':stack[0]=0
 m=re.fullmatch(r'stp x(\d+), xzr, \[sp\]',op)
 if m:stack[0]=regs.get(int(m[1]))
 m=re.fullmatch(r'ldrb w4, \[x(?:0|19), #(0x[0-9a-f]+)\]',op)
 if m:regs[4]='sequence_boot+'+m[1]
 m=re.fullmatch(r'str x0, \[sp, #0x18\]',op)
 if m:stack[24]=regs.get(0)
 if op=='bl #0x2b61798':
  idx=regs[1];row={'index':idx,'kind':regs[3],'priority':regs[2],'volume_source':regs[4],'cont_length':regs[5],'cont_first_length':regs[6],'size':regs[7],'offset':stack[0],'constructor_call_VA':i['va'],'wait':True,'commands':['0x327/40B','0x32a/10B']}
  if idx>=9:
   v=stack[24];row['file']=read('ap',v,128).split(b'\0')[0].decode();row['physical']='remote DMM returned phys64 at AP 0x2b61354';row['size']='fread returned byte count at 0x2b60f58..0x2b60f68 ->0x2b6134c..0x2b61350'
  else:row['physical']=hex(0x41da00000+row['offset'])
  row['register_predicate']='0 only if sequence_boot+0x1e4==1 AND index==6, otherwise1; AP0x2b61378..0x2b6139c'
  rows.append(row)
assert len(rows)==13
assert [r['kind'] for r in rows]==[1,2,3,8,7,9,4,5,6,10,11,12,13]
assert max(r['offset']+r['size'] for r in rows[:9])==0x8480
p['normal_sequence']=rows
raw=bytes.fromhex('0d202703280001800000a01d04000000000100000106010000000000000000000000000000000000')
assert len(raw)==40
p['captured_327']={'raw':raw.hex(),'type':hex(struct.unpack_from('<H',raw)[0]),'command':'0x327','length':40,'flags':'0x8001','phys64':hex(struct.unpack_from('<Q',raw,8)[0]),'size_u32':struct.unpack_from('<I',raw,16)[0],'kind_u8':raw[20],'priority_u8':raw[21],'register_u8':raw[22],'format_u8':raw[23],'continuous_u8':raw[24],'reserved_25_27':raw[25:28].hex(),'cont_length_u32':struct.unpack_from('<I',raw,28)[0],'cont_first_length_u32':struct.unpack_from('<I',raw,32)[0],'reserved_36_39':raw[36:40].hex()}
assert p['captured_327']['phys64']==rows[0]['physical']
p['field_names']={hex(v):read('cp',v,64).split(b'\0')[0].decode() for v in [0xd87499,0xd874b9,0xd874cf,0xd874e5,0x1b1a00,0x1b1a1c,0x1b1a40,0x1b1a58,0x1b1a70]}
p['contracts']={'327':{'legacy':'2004/0201/40B/0001 same body offsets +8..+35; tail zero','reply':'0d2027130c00018000000000','legacy_reply':'042001820c00010000000000','AP_construct':'0x2dee8b8..0x2dee98c','CP_bridge':'0x1abf98..0x1abfba ->0x1b17b4; reply0x5ca1c6','CP_execute':'0x5b00c2 ->0x5b01f6 ->0x18693c ->0x1869e0','behavior':'Store descriptor in 20-slot table; physical range translation via 4 map descriptors at0xb54eb0, no sound-data loads/header/format/CRC validation. Kind already present with equal descriptor succeeds (0x5b0266 return3); changed descriptor returns status0xe004. Bad register operation returns0xe004. Unregister searches kind, missing kind also status0. Full table returns without completion at0x186958 (not synthetic success).','zero_content':'No failure status induced by zero backing in this registration path; bytes are not read. Address outside map logs and stores local address0 but still status0 at0x1869aa..0x1869ce. Silent model must instead validate its own backing ownership/ranges.','minimal':'Save descriptor by kind, validate boot values and backing lifetime; return status0 once to exact source. No playback.'},'32a':{'legacy':'2004/0204/12B/0001, +8 volume_u8,+9 kind_u8,+10..11zero','reply':'0d202a130c00018000000000','legacy_reply':'042004820c00010000000000','AP_construct':'0x2dee990..0x2deea04','CP_bridge':'0x1ac010 ->0x1b1d08; reply0x5ca2bc','CP_execute':'0x5b0606 ->0x186c24 ->0x186c98','behavior':'volume<8 saved per kind (kind0 all); kind missing still succeeds; volume>=8 helper returns0xe002, caller normalizes any error to status0xe002. No physical buffer access.','zero_content':'No content dependency or content error status','minimal':'Save per-kind volume in0..7; return status0 once to exact source. No playback.'}}
p['error_sequences']={'table_error':'0x2b613f8 ->0x2b61548: same kind unregister327 (only kind, all other body zero), then retry original327; retry success continues32a; retry failure fatal0x2b61690 ->0x2b60c38..0x2b60c50','volume_error':'0x2b61468 ->0x2b61698: unregister327 all fields zero except kind; then DMM release if file and fatal0x2b61794 ->0x2b61680 ->0x2b60c38..0x2b60c50','non_ADF_file_prerequisites':'Four files use DMM open/mmap/fread/interchip_transfer/unmap/free; failures fatal before next327; these require separate modeling and cannot be solved by ADF success replies','normal_total_after_033d':26,'loop':'0x2b61dcc..0x2b61df4 indices0..12. All327 and32a waits timeout=-1 via0x2de72fc.'}
p['runtime']={}
for prefix in ['ap71','ap72']:
 runs=sorted((ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/runs').glob(prefix+'*'),key=lambda f:f.stat().st_mtime)
 f=runs[-1]/'serial.log';data=f.read_bytes();lines=data.decode(errors='replace').splitlines()
 hits=[{'line':i+1,'text':s} for i,s in enumerate(lines) if any(t in s for t in ['FX3_ADF_MUTED','command=0x33d','command=0x32e','raw=0d202703','raw=0d202503','raw=0d202513','relative=0x2b61de4','relative=0x2b613f4'])]
 p['runtime'][prefix]={'path':str(f),'sha256':hashlib.sha256(data).hexdigest(),'bytes_snapshot':len(data),'evidence':hits,'325_request_count':sum('raw=0d202503' in s for s in lines),'325_reply_count':sum('raw=0d202513' in s for s in lines)}
p['barrier_verdict']={'volume':'AP72 commit and native-free support reply consumption; worker completion queue not directly instrumented','beep':'AP72 reached first327, not completed. Finishing26 ADF calls only sufficient if file DMM/fread/transfer succeed; 033d alone insufficient.','license_get_i':'UNPROVEN: no named or completion-handle evidence in AP71/AP72 serial; absence is not completion','adf_get_func_i':'UNPROVEN: AP0x2b60264 ->0x2dec778 sends325/8B expects1325/28B, no captured325 request/reply in AP71/AP72 serial. 32d is HDMI format and not get_func. Other non-ADF calls in task remain outside this audit.','barrier':'0x2b67a6c ->0x2b6353c requires4 matched completions; cannot declare barrier done from these captures'}
p['unproven']=['Real playback or waveform format (priority6 is not an encoding identifier)','Four file remote addresses, fread sizes and volume values are runtime dependent','CP map descriptors values and original buffers lifetime','license and adf_get_func completion or four matched barrier completions in AP71/AP72','Live consumption of proposed327/32a replies and menu output']
(OUT/'adf-beep-regist-proof.json').write_text(json.dumps(p,indent=2,ensure_ascii=False)+'\n')
print('PASS: pinned images; 12 instruction checks; 13 rows / 26 normal ADF sends; 40-byte request decoded; proof rebuilt')
