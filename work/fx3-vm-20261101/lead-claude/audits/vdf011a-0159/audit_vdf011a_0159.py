#!/usr/bin/env python3
"""Read original AP/CP, validate instruction/RTTI bindings, emit static proof.
Run with stage4-windows-collab/mac-verification/.venv/bin/python.
No guest, camera, runtime file, or original binary is modified.
"""
from pathlib import Path
import hashlib, json, struct
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile
OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if p.name == 'Mac' and (p/'README.md').is_file())
AP = ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
CP = ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
LOG = ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap66lut-ed5764ad/serial.log'
a, b = AP.read_bytes(), CP.read_bytes()
with AP.open('rb') as f:
    elf=ELFFile(f)
    loads=[(s['p_vaddr'],s['p_offset'],s['p_filesz']) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
    plt=elf.get_section_by_name('.plt')['sh_addr']; rela=elf.get_section_by_name('.rela.plt'); syms=elf.get_section(rela['sh_link'])
    imports={hex(plt+32+16*i):syms.get_symbol(r['r_info_sym']).name for i,r in enumerate(rela.iter_relocations())}
def offset(va):
    for v,o,n in loads:
        if v<=va<v+n:return o+va-v
    raise ValueError(hex(va))
def cstring(data,o):return data[o:data.index(b'\0',o)].decode()
def block(kind,va,n):
    data,off,cs=(a,offset(va),Cs(CS_ARCH_ARM64,CS_MODE_ARM)) if kind=='AP' else (b,va-0x108000,Cs(CS_ARCH_ARM,CS_MODE_THUMB))
    ins=list(cs.disasm(data[off:off+n],va))
    assert ins and sum(i.size for i in ins)==n, (kind,hex(va),n)
    return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in ins]
APBLOCKS=[(0x2d8c34c,0x40),(0x2d8c42c,0x94),(0x2d8c664,0x30),(0x2dcfd94,0x40),(0x2dea1d8,0x288),(0x2de7070,0x38),(0x2de70a8,0x2a0),(0x2de83b4,0x24c),(0x2deb444,0xc0),(0x2dd0014,0x40),(0x2bb9280,0x70),(0x2db4ec8,0x80),(0x2de4574,0x120),(0x2de46cc,0x10)]
CPBLOCKS=[(0x1ab850,0x28),(0x1b41d8,0xc6),(0x1ae8bc,0x6c),(0x1ac628,0x14),(0x5f2dac,0x8c),(0x5f2e38,0x19c),(0x60f134,0x40),(0x1abbb6,0x8),(0x1abc14,0x1c),(0x5cbdd0,0xba),(0x5f5862,0xc0),(0x60f1b0,0x2e),(0x1ac9ee,0x1a),(0x1acd02,6),(0x1ace6e,6),(0x1ad050,0x24),(0x1ab68c,0x1a)]
proof={'scope':'offline static audit; no original edits or VM/device actions','sources':{str(p.relative_to(ROOT)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in (AP,CP,LOG)},'AP':{hex(v):block('AP',v,n) for v,n in APBLOCKS},'CP':{hex(v):block('CP',v,n) for v,n in CPBLOCKS}}
assert hashlib.sha256(b).hexdigest()=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
proof['strings']={hex(v):cstring(a,offset(v)) for v in (0x3952188,0x395215e,0x39694f8,0x396a298,0x3969f70,0x39226fe,0x392269d,0x395d860,0x392bacf)}
proof['imports']={hex(v):imports[hex(v)] for v in (0x1592de0,0x1592f10,0x1594120,0x15943d0)}
assert proof['imports']['0x1592de0']=='osal_rcv_msg_tmo'
assert proof['imports']['0x1592f10']=='osal_snd_msg'
# Re-derive RTTI -> vtable -> command ID / validate / execute slots.
proof['classes']={}
for name in ('N3VDF31VdfDisplayCmdSetPanelBrightnessE','N3VDF22VdfInputCmdSetOsdOnOffE'):
    pos=b.index(name.encode()+b'\0'); ptr=b.index(struct.pack('<I',pos+0x108000)); ti=ptr+0x108000-4
    vptr=b.index(struct.pack('<I',ti)); vt=vptr+0x108000+4
    slots={hex(k):hex(struct.unpack_from('<I',b,vptr+4+k)[0]) for k in (12,16,20)}
    proof['classes'][name]={'name_va':hex(pos+0x108000),'typeinfo':hex(ti),'vtable_address_point':hex(vt),'slots':slots}
assert proof['classes']['N3VDF31VdfDisplayCmdSetPanelBrightnessE']['slots']['0xc']=='0x5f2dad'
assert proof['classes']['N3VDF22VdfInputCmdSetOsdOnOffE']['slots']['0xc']=='0x5f5863'
proof['subsystem_slots']={hex(k):hex(struct.unpack_from('<I',b,0xb8120c+k-0x108000)[0]) for k in (0x15c,0x16c)}
# Ensure decisive instruction bindings do not silently drift.
checks=[('AP',0x2de72fc,'mov w2, #-1'),('AP',0x2de7300,'bl #0x1592de0'),('AP',0x2dea398,'bl #0x2de70a8'),('AP',0x2deb4f0,'bl #0x2de83b4'),('AP',0x2deb4f4,'str wzr, [x19]'),('CP',0x1ae8f4,'movw r0, #0x111a'),('CP',0x5cbdd8,'movw r2, #0x302'),('CP',0x5f58cc,'movt r0, #0xf030')]
for kind,va,want in checks:
    records=[x for arr in proof[kind].values() for x in arr if x['va']==hex(va)]
    assert records and records[0]['instruction']==want,(kind,hex(va),want,records)
proof['checked_instruction_count']=len(checks)
proof['dispatch_tables']=[]
for cmd,internal,handler in ((0x11a,0x20,0x1ab850),(0x159,0xa0,0x1abbb6)):
    wire_slot=0x1aca08+2*(cmd-0x100)
    wire_target=0x1aca08+2*struct.unpack_from('<H',b,wire_slot-0x108000)[0]
    internal_slot=0x1ab6a6+2*(internal-0x1f)
    internal_target=0x1ab6a6+2*struct.unpack_from('<H',b,internal_slot-0x108000)[0]
    assert internal_target==handler
    assert wire_target=={0x11a:0x1acd02,0x159:0x1ace6e}[cmd]
    proof['dispatch_tables'].append({'wire_command':hex(cmd),'wire_table_slot':hex(wire_slot),'wire_case':hex(wire_target),'internal_command':hex(internal),'internal_table_slot':hex(internal_slot),'handler':hex(handler)})
lines=LOG.read_text(errors='replace').splitlines()
proof['runtime_receipts']=[]
for i,line in enumerate(lines):
    if 'raw=0d201a010e000180010e000e0600' in line or 'raw=0d2059010a0001800700' in line:
        proof['runtime_receipts'].append({'next_receive':next(({'line':j+1,'text':lines[j]} for j in range(i+1,min(len(lines),i+150)) if 'FX3_UIPC_RECV_BEGIN' in lines[j] and ('queue=0x81cf61c1' in lines[j] if 'raw=0d201a01' in line else 'queue=0x81cf61c0' in lines[j])),None),'line':i+1,'context':[{'line':j+1,'text':lines[j]} for j in range(max(0,i-1),min(len(lines),i+15))]})
assert len(proof['runtime_receipts'])==2
# A deliberately bounded software contract, not hardware display completion.
P11A=bytes.fromhex('0d201a010e000180010e000e0600'); P159=bytes.fromhex('0d2059010a0001800700')
def minimum_model(packet,state):
    if packet==P11A:
        # Only captured LCD selector1/brightness6. Original other fields retained.
        state['lcd_brightness']={'selector':1,'level':6,'original_payload':packet[8:].hex(),'pending_hardware':True}
        return bytes.fromhex('0d201a110c00018000000000')
    if len(packet)==10 and packet[:8]==P159[:8] and packet[9]==0 and packet[8] in (3,7):
        mask=packet[8];state['osd_on_off']={'mask':mask,'legacy_payload':bytes([mask,0,0,0]).hex(),'pending_f030':True,'physical_osd':False}
        return None # No AP completion on original no-wait path.
    raise ValueError('outside proven minimal software profile')
s={};assert minimum_model(P11A,s)==bytes.fromhex('0d201a110c00018000000000');assert minimum_model(P159,s) is None
bad=[P11A[:-1],P11A[:12]+bytes([16,0]),P11A[:8]+bytes([0])+P11A[9:],P159+bytes([0]),P159[:8]+bytes([0x10,0]),P159[:8]+bytes([7,1])]
for p in bad:
    try:minimum_model(p,{})
    except ValueError:pass
    else:raise AssertionError('unsupported payload accepted')
proof['model']={'positive_cases':2,'rejected_cases':len(bad),'state':s,'011a_reply':'0d201a110c00018000000000','0159_reply':None,'scope':'shadow state plus explicit pending work only, no physical frame or real CP claim'}
proof['findings']={'011a':{'AP_sequence':'sequence_set_lcd_brightness::run @2d8c34c; other callers2b8b488/2d26b68 not fully traced','AP_wait':'osal_rcv_msg_tmo(queue,&reply,-1) @2de72f4; no bounded timeout in wrapper','AP_reply_check':'blind copies12B; status32 at+8 converted2de4574; no command/header validation in common wrapper','CP_legacy':'2001/0102, VdfDisplayCmdSetPanelBrightness','CP_completion':'legacy1102,status32 @+8; BB111a,12B,status0 after normalizing590000 to0','blocking':'yes for current SeqQueueDispSwi TID334; later sequence steps depend on return'},'0159':{'AP_callers':'2bb92cc and2db4f18 ->2dd0014 ->2deb444 ->send_no_wait_i2de83b4','meaning':'OSD output bitmask; value7 sets bits0/1/2, level is not brightness7','CP_legacy':'2001/0302 length12, version2, payload07000000; SetOsdOnOff','CP_completion':'none on traced path;1159 expectation unsupported and unsolicited reply should not be injected','CP_effect':'save four bytes state+14e then enqueuef030; no physical pixels proved','blocking':'no AP wait; log continues to014c on same source81cf61c0'}}
proof['unconfirmed']=['Exact per-bit device labels for OSD mask beyond original bit preservation','Exhaustive other AP011a sequences and dynamic stack proving unique originating sequence','Underlying OSAL implementation of timeout=-1, cancellation behavior, and unrelated queue message ordering','Full hardware panel completion, original downstream event delivery, active OSD pixels','All non-captured AP011a brightness modes and field enums; model intentionally rejects them','AP011a wrapper does not validate reply command/length; transport matching invariant not fully audited']
(OUT/'vdf011a-0159-proof.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
print('PASS: AP/CP instruction and RTTI bindings, 2 model cases, 6 rejects; proof regenerated')
