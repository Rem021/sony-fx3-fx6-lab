"""Bind bundled FX3 MCU read semantics and AP configuration inputs; no execution."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from capstone import Cs, CS_ARCH_ARM, CS_ARCH_ARM64, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
import json, struct
H = Path(__file__).resolve().parent
B = H.parent
R = H.parents[2]
MCU = B/'stage198-AP-CP-loaders-and-partition-selection/originals/darwin_core.bin'
AP = B/'stage200-official-Darwin-updater-dependencies/originals/official7.02-Ubody/bin/ud_darwin_firmup.elf'
d = MCU.read_bytes()
ap = AP.read_bytes()
assert sha256(d).hexdigest() == 'ac3fe4cb9d7122b196d33ca3514d0eb4e2d3abbed882926d4e08d5b26b76afe0'
assert sha256(ap).hexdigest() == 'f0b0fd8fd1fd3c2c348744faeb9b0267668b99ebf5875560ef2fd7dddb424ea8'
e = ELFFile(BytesIO(ap))
def ar(a, n):
    s = next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
    off = s['p_offset']+a-s['p_vaddr']
    return ap[off:off+n]
u16 = lambda a:struct.unpack_from('<H',d,a-0x4200)[0]
u32 = lambda a:struct.unpack_from('<I',d,a-0x4200)[0]
aw = lambda a:int.from_bytes(ar(a,4),'little')
def tbranch(a, call=True):
    x,y=u16(a),u16(a+2)
    assert x&0xf800==0xf000 and y&0xd000==(0xd000 if call else 0x9000)
    s=(x>>10)&1
    n=(s<<24)|((1^(((y>>13)&1)^s))<<23)|((1^(((y>>11)&1)^s))<<22)|((x&1023)<<12)|((y&2047)<<1)
    if s:n-=1<<25
    return a+4+n
def short_b(a):
    w=u16(a)
    assert w&0xf800==0xe000
    n=w&2047
    return a+4+2*(n-2048 if n&1024 else n)
def cond_b(a):
    w=u16(a)
    assert w&0xf000==0xd000 and (w>>8)&15<14
    n=w&255
    return a+4+2*(n-256 if n&128 else n)
def literal(a):
    w=u16(a)
    assert w&0xf800==0x4800
    at=((a+4)&~3)+(w&255)*4
    return at,u32(at)
def abl(a):
    w=aw(a)
    assert w&0xfc000000==0x94000000
    n=w&0x3ffffff
    return a+4*(n-(1<<26) if n&(1<<25) else n)
def movw(a, rd, keep=False):
    w=aw(a)
    assert w&0xff80001f==(0x72800000 if keep else 0x52800000)|rd
    return ((w>>5)&65535)<<(16*((w>>21)&3))

# Request envelope, CRC acceptance, then command dispatch.
assert u16(0x4ef0)==0x2080 and tbranch(0x4efc)==0x52a4
assert u16(0x4f1c)==0x217e and tbranch(0x4f20)==0xbda4
assert d[0x4f24-0x4200:0x4f28-0x4200].hex()=='bdf89220'
assert tbranch(0x4f6c)==0x6450 and u16(0x4f80)==0x2916
assert d[0x4f8a-0x4200:0x4f8e-0x4200].hex()=='0df1140a'
assert tbranch(0x4f90)==0x38784
assert d[0x4f94-0x4200:0x4f98-0x4200].hex()=='9df81940'
assert d[0x4f9a-0x4200:0x4f9e-0x4200].hex()=='04f07f00'
assert u16(0x4f9e)==0x2878 and cond_b(0x4fa0)==0x4fb4
assert u16(0x4fa2)==0x0620 and cond_b(0x4fa4)==0x50a4
assert short_b(0x50a4)==0x515e
# Read arm clears120 payload bytes, copies from the parsed address, then
# places the original128B request/reply buffer into the outgoing frame.
assert u16(0x515e)==0x2178 and tbranch(0x5162)==0x3868e
assert u16(0x5166)==0x4622 and u16(0x5168)==0x4639
assert tbranch(0x516c)==0x385f2 and u16(0x5170)==0x2001
assert u16(0x519a)==0x2280 and u16(0x519c)==0x4651
assert tbranch(0x51a0)==0x385f2
assert d[0x51a4-0x4200:0x51a8-0x4200].hex()=='4ff0160b'
# For command16 the serializer bypasses status rebuilding and only seals CRC.
assert u16(0x4c26)==0x2810 and cond_b(0x4c28)==0x4d28
assert short_b(0x4d28)==0x4e4a and u16(0x4e4a)==0x217e
assert tbranch(0x4e4e)==0xbda4 and u16(0x4e56)==0x0a00
assert d[0x4e52-0x4200:0x4e56-0x4200].hex()=='04f87e0f'
# CRC-valid commands have an MMIO write path before dispatch, regardless of
# whether command16 later selects its memory read arm.
assert literal(0x6450)==(0x65a8,0x40011000)
assert literal(0x6452)==(0x65a4,0x1acce551)
assert d[0x6454-0x4200:0x6458-0x4200].hex()=='c0f8001c'
assert u16(0x6460)==0x7201
assert literal(0xbdac)==(0xbdfc,0x40039000)

# Exact current AP configuration sources. Do not substitute another helper's PLT.
imports=json.loads((B/'stage200-official-Darwin-updater-dependencies/helper-disassembly.json').read_text())
symbols=next(x for x in imports['helpers'] if x['label']=='official7.02-firmup')['PLT']
assert symbols['0x400bd0']['name']=='Backup_read_4Byte' and symbols['0x400ba0']['name']=='UdtrGpioOpen'
ids=[]
for begin,call,kind in [(0x400c58,0x400c7c,'SIO path suffix'),(0x400c84,0x400c8c,'UdtrGpioOpen argument1'),(0x400c94,0x400c9c,'UdtrGpioOpen argument2')]:
    ident=movw(begin,0)|movw(begin+4,0,True)
    assert abl(call)==0x400bd0
    ids.append(dict(id=hex(ident),call=hex(call),use=kind))
assert [x['id'] for x in ids]==['0xf900d4','0xf900b1','0xf9006d']
assert ar(0x401920,9).rstrip(b'\0')==b'/dev/sio'
assert ar(0x401c96,16).split(b'\0',1)[0]==b'%d'
assert abl(0x400cb8)==0x400b40 and abl(0x400cc4)==0x400c10
assert abl(0x400cd4)==0x4012c8 and abl(0x4013cc)==0x400ba0
assert aw(0x400ccc)==0x2a1903e1 and aw(0x400cc8)==0x2a1a03e2
assert aw(0x4013bc)==0x2a1603e2 and aw(0x4013c0)==0x2a1503e1
# Official AP CRC seed/poly/length agree with the public reference software.
assert movw(0x4014fc,1)==65535 and movw(0x401500,6)==0x1021
assert aw(0x401534)==0xf101f87f

mdt=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_LITTLE_ENDIAN)
mda=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
cuts=[]
def save(a,z,label,APcode=False,data=False):
    part=ar(a,z-a) if APcode else d[a-0x4200:z-0x4200]
    out=H/'pins'/(label+'.txt');out.parent.mkdir(exist_ok=True)
    lines=[hex(a)+' DATA '+part.hex()] if data else [f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}' for i in (mda if APcode else mdt).disasm(part,a)]
    out.open('x').write('\n'.join(lines)+'\n')
    cuts.append(dict(source=str((AP if APcode else MCU).relative_to(R)),source_sha256=sha256(ap if APcode else d).hexdigest(),
        layout='ELF_VA' if APcode else 'flat_source_base4200',start=hex(a),end_exclusive=hex(z),bytes=len(part),sha256=sha256(part).hexdigest(),data_not_code=data,output=str(out.relative_to(R))))
for args in [
    (0x4ef0,0x4f2c,'MCU-frame-and-RX-CRC'),(0x4f6c,0x4fb8,'MCU-command16-dispatch'),
    (0x515e,0x5176,'MCU-read-copy'),(0x5194,0x51a8,'MCU-echo-buffer'),
    (0x4c20,0x4c2a,'MCU-serializer-gate'),(0x4d28,0x4d2a,'MCU-serializer-non10'),
    (0x4e4a,0x4e5c,'MCU-TX-CRC-seal'),(0x6450,0x6468,'MCU-pre-dispatch-MMIO'),
    (0x65a4,0x65ac,'MCU-MMIO-pools',False,True),
    (0xbda4,0xbdcc,'MCU-CRC-peripheral'),(0xbdfc,0xbe00,'MCU-CRC-base',False,True),
    (0x38784,0x3879a,'MCU-LE32-decode'),(0x385f2,0x3867e,'MCU-copy-function'),
    (0x3867e,0x38784,'MCU-fill-shared-zero'),
    (0x400c58,0x400ca4,'AP-Backup-inputs',True),
    (0x400ca4,0x400cd8,'AP-SIO-path-and-arguments',True),
    (0x4013b8,0x4013d4,'AP-GPIO-open-arguments',True),
    (0x4014f8,0x401544,'AP-software-CRC',True)]:
    save(*args)
result=dict(status='BUNDLED_FX3_INITCOM_READ_ARM_AND_AP_CONFIG_INPUTS_BOUND',
    MCU_source_sha256=sha256(d).hexdigest(),AP_source_sha256=sha256(ap).hexdigest(),
    source_identity='7.02 public package components, not a current-body ROM/MCU or p1 readback',
    handler=dict(function='0x4e5c',command='0x16',request_bytes=128,address_offset=1,address_encoding='LE32',length_offset=5,
        read_selector='bit7 clear',maximum_read_bytes=120,payload_offset=6,zero_fill_payload_bytes=120,
        response_preserves_request_header6=True,response_CRC_offset=126,response_CRC_encoding='LE16',
        checksum_valid_and_handler_runtime_state_required=True,actual_entry_or_read_observed=False),
    pre_dispatch_effect=dict(call='0x4f6c',target='0x6450',MMIO_base='0x40011000',
        writes=['base+0xc00 <- 0x1acce551','base+0xc00 <- complement','base+8 <- byte0','base+0xc00 <-0'],
        hardware_watchdog_refresh_interpretation='inference from adjacent load/control and unlock/clear pattern, not physical measurement',
        virtual_counter_table_reload_proven=False,whole_protocol_is_side_effect_free=False),
    CRC=dict(MCU_peripheral_base='0x40039000',input_bytes=126,hardware_algorithm_or_timing_proven=False,
        official_AP_software_seed=65535,official_AP_software_polynomial='0x1021',software_vs_reference_semantic_check='CRC-semantic-model-results.json'),
    AP_configuration=dict(Backup_inputs=ids,source_path_prefix='/dev/sio',suffix_format='%d',
        GPIO_argument_semantic_types_or_actual_values_proven=False,actual_body_configuration_read=False,
        reference_fixed_channel0_port4_bit2_validated=False),
    reply_freshness=dict(reference_matches='CRC plus first6 header bytes',request_nonce_echoed=False,
        identical_header_delayed_reply_excluded=False,strict_same_request_freshness_proven=False),
    selected_original_ranges=cuts,
    limits=['InitCom exists in bundled MCU; selected target MCU execution state and physical link are not observed',
        'read branch is memory copy, but common CRC and pre-dispatch MMIO/status logic have side effects',
        'read-only semantic comparison excludes command16 write branch; no write grammar is approved or implemented',
        '128B reply is prepared in the next loop; matching CRC/header cannot establish freshness for a repeated identical query',
        'no same-body backup, inverse write, independent rescue or target MAIN recording acceptance'],
    original_or_guest_execution=False,root_or_device_operations=0,goal_complete=False,persistent_write_release=False)
(H/'MCU-read-contract-proof.json').open('x').write(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(command='0x16',read_header_bytes=6,maximum_payload=120,selected_source_ranges=len(cuts),
    AP_configuration_ids=len(ids),pre_dispatch_MMIO_present=True,actual_device_operations=0)))
