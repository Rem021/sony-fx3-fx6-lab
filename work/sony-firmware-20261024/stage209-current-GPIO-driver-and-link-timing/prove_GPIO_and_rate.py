"""Bind current GPIO implementation and distinguish reference SIO timing values.

All reads are ordinary source/binary files. No original code or MMIO execution.
"""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json,struct,re
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
kcap=json.loads((H/'current-GPIO-function-capture.json').read_text());kp=R/kcap['kernel_source'];k=kp.read_bytes();assert sha256(k).hexdigest()==kcap['kernel_sha256']=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
w=lambda a:int.from_bytes(k[a:a+4],'little')
def bl(a):
    word=w(a);assert word&0xfc000000==0x94000000
    n=word&0x3ffffff;return a+4*(n-(1<<26) if n&(1<<25) else n)
# Current ioctl:16-byte struct; portid+4, bitnum+8, value+12.
assert w(0x2777bc)==0xd2800202 and w(0x2777cc)==0x3940d3a2
assert w(0x2777d0)==0x7100485f and w(0x277880)==0x3940e3a1 and w(0x277890)==0xb9403fa2
assert w(0x277814)==0x52972000 and w(0x277818)==0x72a7fde0
assert ((0xc0104702+0x3fefb900)&0xffffffff)==2
switch=k[0x4676a8:0x4676ac];target=0x277878+struct.unpack_from('<b',switch,2)[0]*4
assert target==0x277878 and bl(0x277898)==0x276520
# mode9 -> GPIO mux, input-enable, output-high, output direction.
for a,v in [(0x276520,0x12000443),(0x276528,0x7100047f),(0x27653c,0x7100205f),
 (0x276654,0x9100d0a5),(0x2765b8,0x91009042),(0x2765d8,0x91011084),(0x2766b4,0x91001000)]:assert w(a)==v
# The raw paths use STR of the supplied bitmask; no byte reversal between
# argument and these stores. Shadow persistence stores are separate.
assert w(0x276580)==0xb90000a1 and w(0x2765bc)==0xb9000041 and w(0x27669c)==0xb9000081 and w(0x2766b8)==0xb9000001
assert w(0x276a04)==0xf9400c04 and w(0x276a24)==0xf8216844
resources=[]
for port in range(19):
    a=0x63fd90+port*0x98;name=k[a:a+8].split(b'\0',1)[0].decode('ascii');physical,size,initial_va=struct.unpack_from('<QQQ',k,a+8)
    resources.append(dict(port=port,record_offset=a,name=name,physical=hex(physical),size=size,initial_virtual=hex(initial_va)))
assert resources[4]['physical']=='0xf1021000' and resources[4]['size']==0x1000
assert int(resources[4]['physical'],16)==0xf101d000+4*0x1000
fops=struct.unpack_from('<8Q',k,0x62c090);K=0xffffff8008080000
assert K+0x277738 in fops
# Original current library contract was bound in207; this driver recognizes
# that exact SET_MODE opcode and16-byte field layout.
previous=json.loads((B/'stage207-Backup-template-and-GPIO-config/GPIO-layout-proof.json').read_text());assert previous['ioctl']=='0xc0104702'
# Source-defined request values in the CURRENT official7.02 helper.
helper=B/'stage200-official-Darwin-updater-dependencies/originals/official7.02-Ubody/bin/ud_darwin_firmup.elf';hd=helper.read_bytes();assert sha256(hd).hexdigest()=='f0b0fd8fd1fd3c2c348744faeb9b0267668b99ebf5875560ef2fd7dddb424ea8';he=ELFFile(BytesIO(hd))
def elfpart(e,d,a,n):
    s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']);off=s['p_offset']+a-s['p_vaddr'];return d[off:off+n]
hw=lambda a:int.from_bytes(elfpart(he,hd,a,4),'little')
assert hw(0x401330)==0xd28ce841 and hw(0x401334)==0x52800262 and hw(0x401338)==0xf2a80081
assert hw(0x401378)==0xd28ce821 and hw(0x40137c)==0x52820002 and hw(0x401380)==0xf2a80081
rs=he.get_section_by_name('.rela.plt');sy=he.get_section(rs['sh_link']);pl=he.get_section_by_name('.plt')['sh_addr'];imports={pl+32+16*n:sy.get_symbol(r['r_info_sym']).name for n,r in enumerate(rs.iter_relocations())};assert imports[0x400b50]=='ioctl'
# Historical2.05 p1 module is a separately labeled reference, not attested7.02.
sio=B/'stage200-official-Darwin-updater-dependencies/originals/historical2.05-p1/usr/kmod/sio.ko';sd=sio.read_bytes();assert sha256(sd).hexdigest()=='a53bc267050ed81e3d81d99287a7ae541381ecea88d2f4f5948e29b45af02eb0';se=ELFFile(BytesIO(sd));st=se.get_section_by_name('.text').data();sw=lambda a:int.from_bytes(st[a:a+4],'little')
assert sw(0x1204)==0x528ce822 and sw(0x1208)==0x72a80082
assert sw(0x1230)==0x54000780 and sw(0x123c)==0x540005e0
assert sw(0x1300)==0xb9000e61 and sw(0x1328)==0x39002262 and sw(0x1334)==0x39002661
assert sw(0xaac)==sw(0xac8)==0xb9400e61 and sw(0xab8)==0x91005042 and sw(0xad4)==0x91006042
# Pinned reference payload source. It uses a different low rate byte.
pcap=json.loads((B/'stage205-FX3-hardware-profile-differences/payload-source-capture.json').read_text());ref=next(r for r in pcap['files'] if r['path']=='payloads/fastboot/src/darwin.c');rp=R/ref['output'];rd=rp.read_bytes();assert sha256(rd).hexdigest()==ref['sha256'];source=rd.decode()
assert re.search(r'#define\s+SIO_RATE\s+3u',source)
assert re.search(r'#define\s+SIO_RATE_LO\s+\(SIO_BASE \+ 0x14\)',source)
assert 'write32(SIO_RATE_LO, (SIO_RATE & 0xFFu) << 24)' in source
assert 'write32(SIO_RATE_HI, (SIO_RATE << 16) & 0xFF000000u)' in source
# Preserve source-bound cuts and distinguish raw table bytes from instructions.
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);pins=[];pd=H/'pins';pd.mkdir()
def pin(path,raw,a,z,label,layout,elf=None,kind='code'):
    part=raw[a:z] if layout=='kernel_file_offset' else (elf.get_section_by_name('.text').data()[a:z] if layout=='ELF_text_offset' else elfpart(elf,raw,a,z-a))
    assert len(part)==z-a
    lines=[part.hex()] if kind=='data' else [f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}' for i in md.disasm(part,a)]
    out=pd/(label+'.txt');out.open('x').write('\n'.join(lines)+'\n');pins.append(dict(source=str(path.relative_to(R)),source_sha256=sha256(raw).hexdigest(),start=a,end_exclusive=z,bytes=z-a,sha256=sha256(part).hexdigest(),layout=layout,kind=kind,output=str(out.relative_to(R))))
for a,z,n in [(0x63fd90,0x63fd90+19*0x98,'current-GPIO-resources'),(0x62b600,0x62b600+19*0x60,'current-GPIO-state-defaults'),(0x4676a8,0x4676ac,'current-GPIO-ioctl-switch'),(0x62c090,0x62c0d0,'current-GPIO-file-operations')]:pin(kp,k,a,z,n,'kernel_file_offset',kind='data')
for a,z,n in [(0x401330,0x401344,'current-helper-SIO-request42'),(0x401374,0x401388,'current-helper-SIO-request41')]:pin(helper,hd,a,z,n,'ELF_VA',he)
for a,z,n in [(0x1200,0x1240,'historical-SIO-config-dispatch'),(0x12f8,0x134c,'historical-SIO-config-storage'),(0xa84,0xae0,'historical-SIO-rate-register-writes')]:pin(sio,sd,a,z,n,'ELF_text_offset',se)
# Source line pins are byte-preserving, not compiled or executed.
linepins=[]
def linepin(path,start,end,label):
    raw=path.read_bytes();lines=raw.splitlines(keepends=True);part=b''.join(lines[start-1:end]);out=H/'source-pins'/(label+'.txt');out.parent.mkdir(exist_ok=True);out.open('xb').write(part)
    linepins.append(dict(source=str(path.relative_to(R)),source_sha256=sha256(raw).hexdigest(),start_line=start,end_line_inclusive=end,sha256=sha256(part).hexdigest(),output=str(out.relative_to(R))))
for path,first,last,label in [(rp,'#define SIO_CH','#define SIO_RATE        3u','reference-SIO-registers-and-rate'),(rp,'#define XCS_PORT','#define SIO_PINS','reference-GPIO-pins'),(rp,'void darwin_init(void)','int darwin_xfer','reference-GPIO-init')]:
    lines=path.read_text().splitlines();a=next(i+1 for i,x in enumerate(lines) if first in x);z=next(i+1 for i,x in enumerate(lines) if last in x);linepin(path,a,z-1 if last=='int darwin_xfer' else z,label)
for name in ['gpio-sn.c','gpio-sn.h']:
    path=H/'reference-source/linux-kernel/drivers/char'/name;lines=path.read_text().splitlines()
    if name.endswith('.c'):
        a=next(i+1 for i,x in enumerate(lines) if x.startswith('static UDIF_INT hw_gpio_set_mode_port('));z=next(i+1 for i,x in enumerate(lines[a:],a) if x.startswith('static UDIF_INT hw_gpio_get_mode_bit('));linepin(path,a,z-1,'GPL-mode-writes')
    else:linepin(path,32,60,'GPL-register-offsets')
path=H/'reference-source/linux-kernel/include/linux/gpio/gpio.h';linepin(path,31,44,'GPL-command-mode-values')
header_lines=path.read_text().splitlines();a=next(i+1 for i,x in enumerate(header_lines) if x.startswith('typedef struct gpio_ioctl_port'));z=next(i+1 for i,x in enumerate(header_lines) if x.startswith('}GPIO_PORT;'));linepin(path,a,z,'GPL-port-layout')
result=dict(status='CURRENT_GPIO_REGISTERS_AND_STATIC_SIO_RATE_DIFFERENCE_BOUND',current_kernel_sha256=sha256(k).hexdigest(),
 GPIO=dict(ioctl='0xc0104702',param_bytes=16,portid_offset=4,bitnum_offset=8,value_offset=12,current_mode9_write_order=['PORTSEL_SET+0x34','INEN_SET+0x24','WDATA_SET+0x44','DIR_SET+0x04'],bitmask=4,GPIO4_physical_base='0xf1021000',resources=resources,
 reference_init_write_order=['WDATA_SET+0x44','DIR_SET+0x04','PORTSEL_SET+0x34','PORTSEL_CLR+0x38 for SIO pins0,1,3'],reference_explicit_INEN_SET=False,
 modes_share_final_CS_mux_direction_high_intent=True,initial_state_or_transient_pin_levels_proven=False),
 SIO=dict(current7_02_helper_request42='0x40046742',current7_02_helper_request42_value=19,current7_02_helper_request41='0x40046741',current7_02_helper_request41_value=4096,
 historical2_05_request42_stores_at_channel_offset=12,historical2_05_request41_stores_low_high_at=[8,9],historical2_05_rate_register_offsets=[20,24],
 reference_payload_rate_index=3,reference_low_register_value='0x03000000',historical_path_given_current_request_low_value='0x13000000',
 same_effective_frequency_proven=False,current7_02_installed_p1_module_identity_proven=False,rate_is_not_assumed_Hz=True),
 additional_original_ranges=pins,source_line_pins=linepins,driver_GPIO_file_operations_pointer_bound=True,Sony_code_or_guest_execution=False,root_or_device_operations=0,
 limits=['Current GPIO evidence is package main kernel, not same-body installed p1 attestation','Reference GPIO init omits explicit input-enable and changes write order; prior pin state not observed','SIO register interpretation uses separately labeled historical2.05 module; current helper request19 is exact7.02','Different divider words do not prove different Hz without clock parents and hardware formula','No MCU transport, boot entry, backup/restore, modified flash or long-record acceptance'])
(H/'GPIO-and-SIO-contract-proof.json').open('x').write(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(GPIO4_base='0xf1021000',current_GPIO_mode9_stores=4,reference_INEN_SET=False,current_helper_SIO_word=19,reference_SIO_word=3,same_Hz_proven=False,new_original_ranges=len(pins),source_line_pins=len(linepins),device_operations=0)))
