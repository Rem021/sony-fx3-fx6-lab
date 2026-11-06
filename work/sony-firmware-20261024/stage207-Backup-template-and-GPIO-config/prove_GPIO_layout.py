"""Bind GPIO library argument bytes to its own named structure diagnostics."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
import json, struct, importlib.util
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage200-official-Darwin-updater-dependencies/originals/official7.02-main-AP/lib/libul_GpioCtrl.so'
d=P.read_bytes();assert sha256(d).hexdigest()=='49904397517841f9be3ddda6c359d0391eb9ab726a02aa891ca1f97976550548'
e=ELFFile(BytesIO(d))
def read(elf,raw,a,n):
    s=next(s for s in elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
    off=s['p_offset']+a-s['p_vaddr'];return raw[off:off+n]
ar=lambda a,n:read(e,d,a,n)
w=lambda a:int.from_bytes(ar(a,4),'little')
def target(a):
    word=w(a);assert word&0xfc000000==0x94000000
    n=word&0x3ffffff
    return a+4*(n-(1<<26) if n&(1<<25) else n)
def cstr(a):
    segment=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a<s['p_vaddr']+s['p_filesz'])
    remaining=segment['p_vaddr']+segment['p_filesz']-a
    raw=ar(a,min(160,remaining))
    assert b'\0' in raw
    return raw.split(b'\0',1)[0].decode('ascii')
assert w(0xb14)==0x2a0103f6 and w(0xb18)==0x2a0203f4
assert w(0xb2c)==0x39003016 and w(0xb30)==0x39004014
assert w(0xb64)==0x91002261 and w(0xb68)==0xa9400c22
# Diagnostic function uses the very same16B port-layout offsets.
assert w(0xac0)==0x39401261 and w(0xad0)==0x39402261
assert 'port.portid' in cstr(0xe7a) and 'port.bitnum' in cstr(0xe91)
assert target(0xacc)==target(0xadc)==0x980
# Supplied open mode2 selects the named OUTPUT_H mode and control flag9.
assert w(0xbc8)==0x7100083f and w(0xbd0)==0x52800121
assert w(0xbd8)==0xb9004fa1 and target(0xbe4)==0x940
assert 'GPIOMODE_GPIO | GPIOMODE_OUTPUT_H' in cstr(0xdb4)
rel=e.get_section_by_name('.rela.plt');sy=e.get_section(rel['sh_link']);plt=e.get_section_by_name('.plt')['sh_addr']
imports={hex(plt+32+16*n):sy.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations())}
assert imports['0x940']=='ioctl' and imports['0x980']=='printf'

# Re-read the existing main-AP capture from its source image rather than
# substituting a historical p1 provider that happens to have similar symbols.
reader=B/'stage2/extraction/read_filesystems.py'
assert sha256(reader.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
spec=importlib.util.spec_from_file_location('bk207ext',reader);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
image=B/'stage2/extraction/nflasha15.img';fs=m.Ext2(image)
try:
    assert sha256(fs.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    row=next(r for r in fs.walk() if r['path']=='/lib/libul_GpioCtrl.so')
    assert fs.data(row['inode'])==d
finally:fs.b.close();fs.f.close()
oldrows=[]
for version in ['2.04','2.05']:
    p=B/('stage200-official-Darwin-updater-dependencies/originals/historical'+version+'-p1/usr/lib/libul_GpioCtrl.so')
    old=p.read_bytes();assert sha256(old).hexdigest()=='4c36648d884bb89d109bb1eda681683ec65e5995cd3d7fa4c1a5228fb41a6e2f'
    oe=ELFFile(BytesIO(old));diff=[i for i,(a,b) in enumerate(zip(old,d)) if a!=b]
    comment=e.get_section_by_name('.comment');lo=comment['sh_offset'];hi=lo+comment['sh_size']
    assert len(old)==len(d) and all(lo<=i<hi for i in diff)
    oldrows.append(dict(version=version,source=str(p.relative_to(R)),sha256=sha256(old).hexdigest(),
        bytes=len(old),text_equal=oe.get_section_by_name('.text').data()==e.get_section_by_name('.text').data(),
        rodata_equal=oe.get_section_by_name('.rodata').data()==e.get_section_by_name('.rodata').data(),
        differing_bytes=len(diff),differences_only_within_nonloaded_comment_section=True,
        current_body_p1_identity_proven=False))
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);cuts=[]
def pin(a,z,label,data=False,source=P,elf=e,raw=d):
    part=read(elf,raw,a,z-a);out=H/'pins'/(label+'.txt');out.parent.mkdir(exist_ok=True)
    lines=[hex(a)+' DATA '+part.hex()] if data else [f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}' for i in md.disasm(part,a)]
    out.open('x').write('\n'.join(lines)+'\n');cuts.append(dict(source=str(source.relative_to(R)),source_sha256=sha256(raw).hexdigest(),
        start=hex(a),end_exclusive=hex(z),bytes=len(part),sha256=sha256(part).hexdigest(),data_not_code=data,output=str(out.relative_to(R))))
for a,z,label,data in [(0xb00,0xb48,'GPIO-argument-storage',False),(0xb64,0xb7c,'GPIO-port-structure-copy',False),
    (0xbc8,0xc10,'GPIO-mode2-output-high',False),(0xaa0,0xaf8,'GPIO-named-field-diagnostic',False),
    (0xe62,0xec0,'GPIO-field-names',True),(0xdb4,0xe0b,'GPIO-output-high-name',True)]:pin(a,z,label,data)
backup=B/'stage182-boot-selector-and-recovery-admission/evidence/boot-request/originals/lib/libbackup.so'
raw=backup.read_bytes();assert sha256(raw).hexdigest()=='6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d'
be=ELFFile(BytesIO(raw));symbol=next(s for s in be.get_section_by_name('.dynsym').iter_symbols() if s.name=='Backup_read_4Byte')
pin(symbol['st_value'],symbol['st_value']+symbol['st_size'],'Backup-read4-wrapper',False,backup,be,raw)
names=[s.name for s in be.get_section_by_name('.dynsym').iter_symbols() if 'interchip' in s.name]
result=dict(status='GPIO_ARGUMENTS_NAMED_PORTID_BITNUM_AND_MODE2_OUTPUT_H_BOUND',
    current_main_provider=str(P.relative_to(R)),source_sha256=sha256(d).hexdigest(),
    main_provider_reverified_against_image=True,source_image_sha256='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',
    argument_mapping=dict(argument1='portid byte at handle+12 / ioctl port struct+4',argument2='bitnum byte at handle+16 / ioctl port struct+8',
        argument3='open mode;2 maps to named GPIOMODE_GPIO | GPIOMODE_OUTPUT_H with control9'),
    ioctl='0xc0104702',historical_provider_comparisons=oldrows,selected_ranges=cuts,
    Backup_wrapper_has_record_file_selection=False,available_interchip_API_names=names,
    record0_or_record1_mapping_to_actual_AP_read_proven=False,actual_pin_or_voltage_measured=False,
    limits=['named layout and defaults do not identify current-body active configuration',
        'current main provider and historical p1 code agreement do not attest installed7.02 updater provider',
        'ordinary Backup_read_4Byte forwards a service request; this wrapper does not parse/select a file record'],
    Sony_code_or_guest_execution=False,root_or_device_operations=0)
(H/'GPIO-layout-proof.json').open('x').write(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(portid_and_bitnum_fields_bound=True,mode2_named_output_high=True,source_ranges=len(cuts),
    previous_p1_text_equal=[r['text_equal'] for r in oldrows],record_selection_proven=False,actual_device_operations=0)))
