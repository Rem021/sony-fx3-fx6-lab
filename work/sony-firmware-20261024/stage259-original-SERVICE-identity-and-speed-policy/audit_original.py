"""Read pinned7.02 ELF and GPL reference structures. Never execute Sony code."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,plistlib,struct,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(name,x):
    with(H/name).open('xb')as f:f.write(x if isinstance(x,bytes)else(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
reader=B/'stage134-backup-reader-scope-and-service-extension/audit_readers.py'
assert sha256(reader.read_bytes()).hexdigest()=='1bff3cd4993406760cda36356d4d2607ff7d3e0a0072a2214db34ea67090c40a'
spec=importlib.util.spec_from_file_location('pinned_static_reader259',reader);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=B/'stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/lib/libInfraUsbCmn.so'
pin=next(x for x in json.loads((B/'stage183-request-consumer-and-early-entry/final-receipt.json').read_text())['files']if x['path']==str(original.relative_to(R)))
assert original.stat().st_size==pin['bytes']and sha256(original.read_bytes()).hexdigest()==pin['sha256']=='6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396'
m.LIB=original.parent;im=m.Image(original.name,pin['sha256'])
rel={r['r_offset']:r for r in im.elf.get_section_by_name('.rela.dyn').iter_relocations()};used_rel={};spans={}
def read(a,n):
    raw=im.read(a,n);spans[a,n]=dict(VA=hex(a),bytes=n,raw_hex=raw.hex(),sha256=sha256(raw).hexdigest());return raw
def pointer(a):
    r=rel.get(a)
    if r is None:return struct.unpack('<Q',read(a,8))[0]
    if r['r_info_type']==1027 and not r['r_info_sym']:answer=r['r_addend'];symbol=None
    else:
        assert r['r_info_type']in (257,1025)
        s=im.dynsym.get_symbol(r['r_info_sym']);assert s['st_shndx']!='SHN_UNDEF'
        answer=s['st_value']+r['r_addend'];symbol=s.name
    used_rel[a]=dict(at=hex(a),type=r['r_info_type'],symbol=symbol,addend=r['r_addend'],resolved_VA=hex(answer))
    return answer
def sym(n):return im.symbols[n]['st_value']
def table(speed):
    a=sym('sen_speed_desc_'+speed);s=read(a,24);assert s[5]==1
    caddr=pointer(a+8);c=read(caddr,48);assert c[0:3]==bytes([0,1,1])and not pointer(caddr+24)and not c[32]
    ia=pointer(caddr+8);it=read(ia,16);assert it[0:2]==bytes([0,1]);ta=pointer(ia+8);t=read(ta,32)
    assert t[0:2]==bytes([0,4])and t[16:20]==bytes([255,0,0,0])and struct.unpack_from('<I',t,20)[0]==0
    ep=pointer(ta+8);pipes=[]
    for i in range(4):
        ea=ep+32*i;e=read(ea,32);comp=pointer(ea+24)
        assert e[0]in (0x81,2,0x83,4)and e[1]==2 and struct.unpack_from('<I',e,8)[0]==0
        cp=read(comp,4)if comp else None
        pipes.append(dict(address=e[0],attributes=e[1],packet=struct.unpack_from('<H',e,2)[0],interval=e[4],companion_hex=cp.hex()if cp else None))
    assert [p['address']for p in pipes]==[0x81,2,0x83,4]
    expected=dict(lsfs=64,hs=512,ss=1024)[speed];assert all(p['packet']==expected for p in pipes)
    assert all(p['companion_hex']==('00000000'if speed=='ss'else None)for p in pipes)
    wire=bytearray([9,2,0,0,1,1,0,c[17],c[18],9,4,0,0,4,255,0,0,0])
    for p in pipes:
        wire+=bytes([7,5,p['address'],2])+struct.pack('<H',p['packet'])+bytes([p['interval']])
        if p['companion_hex']is not None:wire+=bytes([6,0x30])+bytes.fromhex(p['companion_hex'])
    struct.pack_into('<H',wire,2,len(wire));put('derived-'+speed+'-config.bin',bytes(wire))
    return dict(speed=speed,internal_speed_table_VA=hex(a),config_VA=hex(caddr),interfaces=1,alternate=0,endpoint_count=4,
        pipes=pipes,derived_wire_bytes=len(wire),derived_wire_sha256=sha256(wire).hexdigest(),
        derived_wire_is_not_a_captured_USB_descriptor=True)
tables=[table(s)for s in ['lsfs','hs','ss']]
names=['_Z22make_gadget_desc_tablev','_ZN7CUsbSvc12createGadgetEP8CUSB_MES','_ZN7CUsbSvc19create_serialNumberEv','_ZN7CUsbSvc15setSerialNumberEPch','getUsbSerialNumAscii']
functions=[im.function(n)for n in names];ins={int(i['pc'],16):i for f in functions for i in f['instructions']}
expected={0xfaa8:'add x3, x0, #0x260',0xfaac:'ldr x2, [x2, #0xe30]',0xfab8:'stp x4, x5, [x3]',
    0xfac8:'ldr x2, [x2, #0xb68]',0xfae4:'ldr x2, [x2, #0xa30]',0xfb60:'ldr x2, [x2, #0xed0]',0xfb68:'strb w2, [x0, #0x2b1]',
    0xfd48:'add x4, x0, #0x390',0xfd50:'ldr x2, [x2, #0xec0]',0xfd5c:'stp x6, x7, [x4]',
    0x15998:'ldr w2, [x19, #0xe8]',0x1599c:'ldr x3, [x19, #0x1a8]',0x159b0:'stp x1, x3, [x29, #0x80]',
    0x159b4:'ldrb w3, [x19, #0x1b0]',0x159e0:'ldrb w0, [x0, #0x29]',0x159e4:'cbnz w0, #0x159f0',
    0x159e8:'strb wzr, [x29, #0x90]',0x159ec:'str xzr, [x29, #0x88]',
    0x15b64:'add x2, x29, #0x80',0x15b68:'mov x1, #0xe203',0x15b6c:'movk x1, #0x4018, lsl #16',
    0x15be8:'add x2, x29, #0x80',0x15bec:'mov x1, #0xe203',0x15bf0:'movk x1, #0x4018, lsl #16',
    0x1323c:'csel w2, w2, wzr, eq',0x12e88:'strb wzr, [x19, #0x1b0]',0x12e90:'str xzr, [x19, #0x1a8]'}
for at,asm in expected.items():assert ins[at]['asm']==asm,(hex(at),ins[at])
for a,n in [(0x33e30,'sen_speed_desc_hs'),(0x33b68,'sen_speed_desc_lsfs'),(0x33a30,'sen_speed_desc_ss'),(0x33ed0,'sen_serial_number_str'),(0x33ec0,'storage_speed_desc_hs')]:assert pointer(a)==sym(n)
base=pointer(0x33f18);assert base==sym('func_tbl')
pt=sym('ptbl_did');sen_entry=pointer(pt+13*8);storage_entry=pointer(pt)
assert pointer(sen_entry+24)==base+0x260 and pointer(storage_entry+24)==base+0x390
assert read(sen_entry+0x29,1)==b'\0'and read(storage_entry+0x29,1)==b'\1'
assert read(sym('sen_serial_number_str'),1)==b'\0'
assert read(sym('sen_id_product'),2)==bytes.fromhex('3603')and read(sym('sen_id_vender'),2)==bytes.fromhex('4c05')
assert pointer(sym('sen_bos_desc')+32)==0 and pointer(sym('storage_bos_desc')+32)==0
kernel=B/'stage145-initial-MSC-native-route/work/official-kernel-reference/linux-kernel/include/linux/usb/gcore/usb_gadgetcore.h'
kt=kernel.read_bytes();assert b'void *serial_string;'in kt and b'__u8 uc_serial_len;'in kt
native=B/'stage258-fixed-Sony-communication-diagnostic01/iokit_adapter.c';nt=native.read_text()
assert 'CFSTR("USB Serial Number")'in nt and '&& serial[0]'in nt and 'if(!ok || IORegistryEntryGetRegistryEntryID'in nt
put('original-functions.json',functions)
report=dict(status='ORIGINAL_SERVICE_SERIAL_SUPPRESSION_AND_THREE_SPEED_TABLES_FOUND',original_pin=pin,
    reader_pin=dict(path=str(reader.relative_to(R)),sha256=sha256(reader.read_bytes()).hexdigest()),
    reference_header=dict(path=str(kernel.relative_to(R)),sha256=sha256(kt).hexdigest(),version='Sony FX3 GPL7.00 reference layout, not exact7.02 kernel runtime'),
    checked_instructions=len(expected),relocations=list(used_rel.values()),data_spans=list(spans.values()),speed_tables=tables,
    SERVICE_DID=13,SERVICE_entry_VA=hex(sen_entry),SERVICE_descriptor_VA=hex(base+0x260),SERVICE_serial_enabled_byte=0,
    storage_DID=0,storage_serial_enabled_byte=1,
    common_CREATE_GADGET_branch='entry+0x29==0 clears serial pointer and length in START ioctl frame',
    SERVICE_default_iSerialNumber=0,SERVICE_and_storage_default_BOS_container_id_pointers=0,
    known_native_candidate_incompatibility='258 requires nonempty same cached serial on0336; source-backed default SERVICE path omits that serial. After successful MSC transition this could return SHAPE and retain before opening SERVICE or sending STOP.',
    no_guarantee_current_runtime_uses_unchanged_defaults=True,
    fallback_identity_not_silently_relaxed=True,
    next_identity_work='Review a separately labelled continuously observed physical-port transition and/or an independent device identity read. Do not label topology as serial identity or copy the MSC tag into an unverified SERVICE node.',
    original_Sony_instructions_executed=False,USB_or_root_operations=0)
put('original-service-descriptors-and-identity.json',report)
print(json.dumps(dict(status=report['status'],checked_instructions=len(expected),SERVICE_serial_enabled=0,speeds=[x['pipes'][0]['packet']for x in tables],original_code_executed=False)))
