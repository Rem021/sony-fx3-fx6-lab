"""Source-bound AP sender/ABI checks; no extracted code or device is executed."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json,struct
from capstone import Cs,CS_ARCH_ARM64,CS_ARCH_ARM,CS_MODE_LITTLE_ENDIAN,CS_MODE_THUMB,CS_MODE_MCLASS
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent
AP=H/'originals/official7.02-Ubody/bin/ud_darwin_firmup.elf'
OLD=H/'originals/historical2.05-p1/usr/bin/ud_darwin_init.elf'
MOD=H/'originals/historical2.05-p1/usr/kmod/sio.ko'
MCU=B/'stage198-AP-CP-loaders-and-partition-selection/originals/darwin_core.bin'
def digest(p):return sha256(p.read_bytes()).hexdigest()
assert digest(AP)=='f0b0fd8fd1fd3c2c348744faeb9b0267668b99ebf5875560ef2fd7dddb424ea8'
assert digest(OLD)=='c943c7462e4d94b834b891555a2224c4a2c34d722204368e66d6d97d3eca91ad'
assert digest(MCU)=='ac3fe4cb9d7122b196d33ca3514d0eb4e2d3abbed882926d4e08d5b26b76afe0'
def elfreader(path):
    d=path.read_bytes();e=ELFFile(BytesIO(d))
    def get(a,n):
        for s in e.iter_segments():
            if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']:
                off=s['p_offset']+a-s['p_vaddr'];return d[off:off+n]
        raise AssertionError(hex(a))
    return e,get
ae,ar=elfreader(AP);oe,orr=elfreader(OLD)
me=ELFFile(BytesIO(MOD.read_bytes()));mt=me.get_section_by_name('.text').data()
md=MCU.read_bytes()
def aw(a):return int.from_bytes(ar(a,4),'little')
def ow(a):return int.from_bytes(orr(a,4),'little')
def mw(a):return struct.unpack_from('<I',mt,a)[0]
def sign(x,b):return x-(1<<b) if x&(1<<(b-1)) else x
def bl(word,pc):
    assert word&0xfc000000==0x94000000
    return pc+sign(word&0x3ffffff,26)*4
def adrp(word,pc,rd):
    assert word&0x9f00001f==0x90000000|rd
    return (pc&~4095)+(sign((((word>>5)&0x7ffff)<<2)|((word>>29)&3),21)<<12)
def movpart(word,rd,keep=False,is64=False):
    wanted=(0xf2800000 if keep else 0xd2800000) if is64 else (0x72800000 if keep else 0x52800000)
    assert word&0xff80001f==wanted|rd
    return ((word>>5)&65535)<<(16*((word>>21)&3))
assert adrp(aw(0x400df8),0x400df8,23)==0x44f000
assert aw(0x400e00)==0x910502f6
assert movpart(aw(0x400e18),0)==17 and aw(0x400e1c)==0x390502e0
assert movpart(aw(0x400e20),0)==4 and aw(0x400e28)==0x390006c0
assert adrp(aw(0x401550),0x401550,20)==0x44f000 and aw(0x401554)==0x91050294
assert aw(0x401568)==0x7900fe80
request=movpart(aw(0x4015a4),1,is64=True)|movpart(aw(0x4015b4),1,keep=True,is64=True)
assert request==0x40046740
assert bl(aw(0x400e84),0x400e84)==0x401544
assert bl(aw(0x4015cc),0x4015cc)==0x400b50
imports=json.loads((H/'helper-disassembly.json').read_text())['helpers']
apimports=next(x for x in imports if x['label']=='official7.02-firmup')['PLT']
assert apimports['0x400b50']['name']=='ioctl'
assert apimports['0x400b60']['name']=='UdtrGpioWrite'
assert apimports['0x400ba0']['name']=='UdtrGpioOpen'

# Current helper argument block: two64bit pointers, length32, final zero64;
# reference module copies32bytes, clamps >256; copy success returns requested length.
assert aw(0x4015ac)==0xb90043a0 and movpart(aw(0x40159c),0)==128
assert aw(0x4015b8)==0xf9001bb4 and aw(0x4015c8)==0xf9001fb4
assert aw(0x4015c0)==0xf90027bf
module_request=movpart(mw(0x1240),2)|movpart(mw(0x1244),2,True)
assert module_request==request
assert movpart(mw(0x12cc),2,is64=True)==32
assert mw(0x1380)==0xb94012a1 and mw(0x1384)==0x7104003f
assert mw(0x1654)==0xb94012b4 and mw(0x168c)==0x1a800294
assert mw(0x15cc)==0x2a1403e0
rel=me.get_section_by_name('.rela.text');sy=me.get_section(rel['sh_link'])
relocations={r['r_offset']:{'symbol':sy.get_symbol(r['r_info_sym']).name,'addend':r['r_addend']} for r in rel.iter_relocations()}
assert relocations[0x1374]['symbol']=='__arch_copy_from_user'
assert relocations[0x1488]['symbol']=='sio_master_transfer'
assert relocations[0x16a8]['symbol']=='__arch_copy_to_user'

# A narrow historical result counterexample: last saved status0, response !=4,
# subsequent timer comparison expired. The local fallthrough still returns0.
assert ow(0x400f90)==0x7100101f and ow(0x400fb4)==0x35fff9d3
assert ow(0x400fb0)&0xff00001f==0x54000009  # B.LS, taken only if within budget
assert ow(0x400fc8)==0x2a1303e0 and ow(0x400fe4)==0xd65f03c0
script=H/'originals/historical2.05-p1/usr/bin/us_darwin_init.sh'
text=script.read_text()
assert text=='#!/bin/sh\n\n#. /usr/bin/common.src\n\nud_darwin_init.elf\n\necho "Darwin init --- OK"\n\nexit 0\n'

# The MCU CRC routine is peripheral-driven; no guessed hardware model is run.
crc_peripheral=struct.unpack_from('<I',md,0xbdfc-0x4200)[0]
assert crc_peripheral==0x40039000
assert md[0xbda4-0x4200:0xbdcc-0x4200].hex().endswith('d86880b210bd')

selected=[]
cs64=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
cs32=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS)
ranges=[('official-frame-template',AP,ar,0x400df8,0x400e40),
        ('official-SIO-wrapper',AP,ar,0x401544,0x401670),
        ('official-device-init',AP,ar,0x4012c8,0x401400),
        ('official-state-wait',AP,ar,0x400e48,0x400ec0),
        ('official-CRC-software',AP,ar,0x4014f8,0x401544),
        ('reference-init-frame',OLD,orr,0x401068,0x4010a4),
        ('reference-init-timeout-result',OLD,orr,0x400f80,0x400fe8),
        ('reference-GPIO-prefix',OLD,orr,0x400c4c,0x400d10),
        ('reference-SIO-configuration',OLD,orr,0x400d38,0x400e58),
        ('reference-sio-dispatch',MOD,lambda a,n:mt[a:a+n],0x1200,0x12e0),
        ('reference-sio-length',MOD,lambda a,n:mt[a:a+n],0x1370,0x139c),
        ('reference-sio-submit',MOD,lambda a,n:mt[a:a+n],0x1458,0x1494),
        ('reference-sio-success',MOD,lambda a,n:mt[a:a+n],0x1648,0x16c4),
        ('MCU-CRC-peripheral',MCU,lambda a,n:md[a-0x4200:a-0x4200+n],0xbda4,0xbdcc)]
for name,path,get,a,z in ranges:
    raw=get(a,z-a);cs=cs32 if path==MCU else cs64;ins=list(cs.disasm(raw,a))
    assert sum(x.size for x in ins)==len(raw),name
    with (H/(name+'.txt')).open('x') as f:
        f.write('# Original source address; module uses.text offsets, MCU uses layout0x4200. No execution.\n')
        for x in ins:
            note=''
            if path==MOD and x.address in relocations:note=' ; relocation '+json.dumps(relocations[x.address])
            f.write(f'{x.address:#x} {x.bytes.hex()} {x.mnemonic:8} {x.op_str}{note}\n')
    selected.append({'name':name,'source':str(path),'source_sha256':digest(path),
        'address_kind':'text_section_offset' if path==MOD else 'source_layout_VA' if path==MCU else 'ELF_VA',
        'start':hex(a),'end_exclusive':hex(z),'bytes':len(raw),'sha256':sha256(raw).hexdigest()})

# Full historical SIO bytes differ only inside the GNU build-id note.
m04=H/'originals/historical2.04-p1/usr/kmod/sio.ko'
d04=m04.read_bytes();d05=MOD.read_bytes();e04=ELFFile(BytesIO(d04));note=e04.get_section_by_name('.note.gnu.build-id')
lo,hi=note['sh_offset'],note['sh_offset']+note['sh_size']
changed=[k for k,(a,b) in enumerate(zip(d04,d05)) if a!=b]
assert len(d04)==len(d05) and changed and all(lo<=k<hi for k in changed)
n04=d04[:lo]+bytes(hi-lo)+d04[hi:];n05=d05[:lo]+bytes(hi-lo)+d05[hi:]
assert n04==n05
result={
 'official_sender':{'source_sha256':digest(AP),'packet_address':'0x44f140','first_bytes':[17,4],
   'frame_bytes':128,'CRC_offset':126,'called_transport':'0x401544',
   'dependencies':['camera Linux SIO device','UdtrGpio provider','Backup service','dynamic runtime libraries'],
   'actual_device_execution_or_current_p1_identity':False},
 'reference_SIO_contract':{'module_sha256':digest(MOD),'request':hex(request),'argument_copy_bytes':32,
   'tx_pointer_offset':0,'rx_pointer_offset':8,'length_offset':16,'helper_length':128,'driver_positive_clamp':256,
   'selected_copy_success_return':128,'scope':'selected status0/copy-complete path, not physical completion proof or all module errors'},
 'historical_module_identity':{'v204_sha256':digest(m04),'v205_sha256':digest(MOD),
   'different_bytes_only_within_build_id_note':True,'changed_bytes':len(changed),'note_range':[lo,hi],
   'normalized_sha256':sha256(n04).hexdigest(),'actual_current_p1_module_verified':False},
 'historical_init_result_limit':{'source_sha256':digest(OLD),'conditional_path':['last w19 status0','response state byte !=4','timer comparison no longer within budget','ordinary close/ABI returns'],
   'local_return':0,'target_state4_not_implied_by_exit0':True,
   'script_sha256':digest(script),'script_ordinary_shell_sequence':'does not check helper status; echo OK then explicit exit0',
   'script_or_helper_executed':False},
 'MCU_CRC_limit':{'source_sha256':digest(MCU),'routine':'0xbda4','peripheral_base':hex(crc_peripheral),
   'hardware_result_equivalence_to_AP_software_CRC_verified':False,'no_guessed_hardware_model_executed':True},
 'selected_original_ranges':selected,'source_or_guest_execution':False,'root_or_device_operations':0,
 'AP_p1_bootstrap_or_independent_restore_proven':False}
with (H/'official-sender-proof.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'official7.02_frame':[17,4],'reference_ioctl':hex(request),'argument_bytes':32,
    'selected_reference_success_return':128,'slices':len(selected),'no_device_or_guest_execution':True}))
