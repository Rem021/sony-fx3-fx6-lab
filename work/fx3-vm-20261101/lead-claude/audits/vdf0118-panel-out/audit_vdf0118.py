#!/usr/bin/env python3
"""Read-only FX3 0118 audit; run using the existing capstone venv. No VM/device IO."""
from pathlib import Path
import hashlib, json, struct, subprocess
from capstone import Cs, CS_ARCH_ARM, CS_ARCH_ARM64, CS_MODE_THUMB, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
R = Path(__file__).resolve().parent
ROOT = next(p for p in R.parents if (p/'work/sony-firmware-20261024').is_dir())
info = subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T'])
import plistlib
assert plistlib.loads(info)['VolumeUUID'].upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
AP=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
CP=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
a,b=AP.read_bytes(),CP.read_bytes()
assert hashlib.sha256(a).hexdigest()=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
assert hashlib.sha256(b).hexdigest()=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
with AP.open('rb') as f:
    elf=ELFFile(f)
    segments=[dict(s.header) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
    rel=elf.get_section_by_name('.rela.plt');syms=elf.get_section(rel['sh_link']);pv=elf.get_section_by_name('.plt')['sh_addr']
    plt_symbols={hex(pv+32+16*n):syms.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations()) if pv+32+16*n in [0x1592f10,0x1592ec0,0x1594120,0x1591c40,0x1591e00]}
def apread(va,n):
    s=next(s for s in segments if s['p_vaddr']<=va<s['p_vaddr']+s['p_filesz'])
    o=s['p_offset']+va-s['p_vaddr']; return a[o:o+n]
def cpread(va,n): return b[va-0x108000:va-0x108000+n]
def block(va,n,cp=False):
    c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if cp else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    data=(cpread if cp else apread)(va,n)
    rows=[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in c.disasm(data,va)]
    assert rows and sum(len(bytes.fromhex(i['bytes'])) for i in rows)==n,(hex(va),n)
    return rows
def string(va,cp=False): return (cpread if cp else apread)(va,400).split(b'\0')[0].decode('utf-8','replace')
AP_BLOCKS=[(0x2df3d08,0x2f4),(0x2dd0094,0x40),(0x2de66f4,0x238),(0x2b8bb2c,0x1ac),(0x2b8bdbc,0xe0)]
CP_BLOCKS=[(0x1ac9c8,0x40),(0x1accf6,6),(0x1ad052,0x2c),(0x1a8a90,0xe0),(0x1a8ed4,0x42),(0x1a9e2a,0x14),(0x1aa5de,0x18),(0x194ee8,0x1c),(0x5c3a6c,0x2c),(0x1a1590,0x232),(0x1a17c4,0x1d8),(0x1a1a3c,0xee),(0x5f3514,0x260),(0x5f3772,0x98),(0x5f3bdc,0xbe),(0x1ad1a4,0x1c),(0x5c68de,0x12),(0x1ad222,0xe),(0x1ad4f2,6),(0x1ab3e0,0xe),(0x1aeb5c,0x64)]
proof={'scope':'Static original code; no QEMU, hardware or runtime modification','sources':{str(p.relative_to(ROOT)):{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for p,v in [(AP,a),(CP,b)]},'ap_blocks':{hex(v):block(v,n) for v,n in AP_BLOCKS},'cp_blocks':{hex(v):block(v,n,True) for v,n in CP_BLOCKS}}
proof['strings']={hex(v):string(v) for v in [0x3966f75,0x396a958,0x3968198,0x3922b20,0x391c861,0x391c881,0x391c8a4,0x3922679]}
proof['strings'].update({hex(v):string(v,True) for v in [0xb3d200,0x1a1a28,0xd81ad4,0xd81aa8,0xd81abf,0x1a19ac,0xd81a6c,0x1a19c8,0x1a19e4,0x1a1a08,0xd81a8a]})
# Exact TBH entries, preserving table bytes as data rather than disassembling them.
def tbh(pc,index):
    va=pc+4+index*2; raw=cpread(va,2);target=pc+4+2*int.from_bytes(raw,'little')
    return {'instruction_va':hex(pc),'index':index,'entry_va':hex(va),'bytes':raw.hex(),'target':hex(target)}
proof['plt_symbols']=plt_symbols
assert struct.unpack('<II',cpread(0xb71e14,8))==(0x118,0x1a8a91)
proof['request_parser_registration']={'va':'0xb71e14','bytes':cpread(0xb71e14,8).hex(),'command':'0x118','thumb_handler':'0x1a8a91'}
proof['dispatch']=[tbh(0x1aca04,0x118-0x100),tbh(0x1a8f12,0x73),tbh(0x1ad22c,0x118-0x100),tbh(0x1aab2c,0x274-0x200)]
assert [x['target'] for x in proof['dispatch']]==['0x1accf6','0x1a9e2a','0x1ad4f2','0x1ab3e0']
proof['class_rtti']={'name_va':'0xb3d200','typeinfo_va':'0xb7e188','vtable_address_point':'0xb7e170','vtable_bytes':cpread(0xb7e168,0x20).hex(),'get_command':'0x5f3514','activate':'0x5f3524'}
assert struct.unpack('<I',cpread(0xb7e17c,4))[0]==0x5f3515
assert struct.unpack('<I',cpread(0xb7e180,4))[0]==0x5f3525
request=bytes.fromhex('0d201801160001800301000000000000000000000100')
reply=struct.pack('<HHHHI',0x200d,0x1118,12,0x8001,0)
fields=[(8,'update_mask',3,None),(9,'panel',1,0x64c),(10,'evf',0,0x650),(11,'projector',0,0x654),(12,'reserved',0,None),(13,'lcd_color_mode',0,0x2a0),(14,'reserved',0,None),(15,'vf_color_mode',0,0x298),(16,'reserved',0,None),(17,'evf_framerate',0,0x658),(18,'power_save',0,0x65c),(19,'evf_fr_force_normal',0,0x660),(20,'evf_priority',1,0x664),(21,'evf_magnifier',0,0x668)]
assert all(request[o]==v for o,_,v,_ in fields)
proof['request']={'hex':request.hex(),'header_le16':list(struct.unpack('<4H',request[:8])),'fields':[{'offset':o,'name':name,'value':v,'cp_state_offset':hex(s) if s is not None else None} for o,name,v,s in fields]}
proof['response']={'hex':reply.hex(),'fields':{'0:2':'0x200d','2:4':'0x1118','4:6':12,'6:8':'0x8001','8:12':'status32 = 0'},'normal_success':0,'legacy_reply':'0x1100','legacy_status_1':'special/early completion, not selected for this model'}
# A bounded MODEL PROPOSAL, not a claim of firmware-wide accepted ranges.
def software_model(raw,state):
    if raw != request: raise ValueError('outside AP66 exact request profile')
    state.update({name:v for _,name,v,s in fields if s is not None})
    state['update_mask']=3; state['raw_request']=raw.hex(); state['physical_completion']=False
    return reply
state={};assert software_model(request,state)==reply
negatives=[request[:i]+bytes([request[i]^1])+request[i+1:] for i in range(len(request))]+[request[:-1],request+b'\0']
for raw in negatives:
    try:software_model(raw,{})
    except ValueError: pass
    else:raise AssertionError('invalid request accepted')
proof['software_model_proposal']={'accepted_request':request.hex(),'state':state,'reply':reply.hex(),'reject':'Every request outside this exact 22-byte AP66 profile; no success reply for rejected requests','tests':{'positive':1,'negative':len(negatives)},'warning':'Software-only acknowledgement; does not implement CP hardware sequencing or certify panel/frame completion'}
log=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap66lut-ed5764ad/serial.log'
lb=log.read_bytes();lines=lb.decode(errors='replace').splitlines();j=next(i for i,s in enumerate(lines) if 'FX3_PROFILE_STACK_BEGIN' in s and 'header=0x118200d' in s)
proof['runtime_input_receipt']={'path':str(log.relative_to(ROOT)),'sha256':hashlib.sha256(lb).hexdigest(),'start_line':j+1,'lines':lines[j:j+15]}
assert any('raw='+request.hex() in x for x in lines[j:j+15])
proof['unproven']=['Full CP external hardware completion and frame timing','All enum names/ranges beyond bounded observed values','AP-wide asynchronous consumer of 0x1118; this call has no receive','Physical meaning of evf_priority=1 beyond original diagnostic label','Global main-thread reply bookkeeping and all state-dependent legacy outcomes']
(R/'vdf0118-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(f'PASS: {len(AP_BLOCKS)} AP / {len(CP_BLOCKS)} CP blocks; 4 TBH mappings; exact request; 1 positive + {len(negatives)} negative model checks; regenerated vdf0118-proof.json')
