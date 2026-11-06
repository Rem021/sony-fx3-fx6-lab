#!/usr/bin/env python3
"""Offline, read-only SKD/AP80c audit. Writes only the sibling proof JSON.

Run with the existing capstone venv. No QEMU, dlopen, target code execution,
device access, ROM/OTP access, key derivation, signing, or network dependency.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from hashlib import sha256, sha1
from io import BytesIO
import bisect
import importlib.util
import json
import mmap
import plistlib
import re
import struct
import subprocess
import tarfile
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT = Path(__file__).resolve().parent
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/skd-ffffb000'
vol = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
assert vol['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
VM = ROOT/'work/fx3-vm-20261101/menu-repair-01'
PROJ = VM/'original-uipc/ap-projection'
LIB = PROJ/'regular-files/usr/lib'
TAIL = ROOT/'work/fx3-color-port-20261027/tail-20261028'
SONY = ROOT/'work/sony-firmware-20261024'
PUB = SONY/'stage204-public-AP-boot-reference'
inputs = {}

def source(p, pin=None):
    p = Path(p)
    b = p.read_bytes()
    h = sha256(b).hexdigest()
    if pin is not None:
        assert h == pin, (str(p), h, pin)
    inputs[str(p.relative_to(ROOT))] = {'bytes': len(b), 'sha256': h}
    return b

def load_module(p, name):
    source(p)
    spec = importlib.util.spec_from_file_location(name, p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

skd = source(LIB/'libInfraSKD.so', '7d1fbd9a53794def916ca3ff2fc3a00f295268bb0f4ea7c07d0e8356d2840f9b')
se = ELFFile(BytesIO(skd))
app = source(LIB/'appFw.so')
ae = ELFFile(BytesIO(app))
osal = source(LIB/'libosal_uipc.so')
oe = ELFFile(BytesIO(osal))
cp = source(SONY/'stage2/extraction/files/nflasha8/cpapp-b.bin')
map_path = TAIL/'wbi2-map-results.json'
mapping = json.loads(source(map_path))
wbi_path = ROOT/mapping['source']
source(wbi_path, 'ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1')
source(TAIL/'skd-snapshot-code-results.json')
sections = sorted((s for s in mapping['sections'] if s['stored_bytes']), key=lambda s:int(s['physical_address'],16))
starts = [int(s['physical_address'],16) for s in sections]
wf = wbi_path.open('rb')
wb = mmap.mmap(wf.fileno(), 0, access=mmap.ACCESS_READ)
WROOT, SBASE = 0x40867a000, 0x7f73ef9000

def physical(pa, n):
    i = bisect.bisect_right(starts, pa)-1
    if i < 0:
        raise ValueError('physical address not stored')
    s, a = sections[i], starts[i]
    if pa+n > a+s['stored_bytes']:
        raise ValueError('physical span not fully stored')
    off = int(s['data_file_offset'],16)+pa-a
    return wb[off:off+n], off

def translate(va):
    table, steps = WROOT, []
    for shift in (30,21,12):
        ix = (va>>shift)&511
        b, off = physical(table+ix*8,8)
        v = struct.unpack('<Q',b)[0]
        steps.append({'table_pa':hex(table),'index':ix,'descriptor':hex(v),'file_offset':hex(off)})
        if not v&1:
            raise ValueError('invalid descriptor')
        if shift != 12 and v&3 == 1:
            mask = (1<<shift)-1
            return (v&0x0000fffffffff000&~mask)+(va&mask), steps
        assert v&3 == 3
        table = v&0x0000fffffffff000
    return table+(va&4095), steps

def sr(a,n, provenance=False):
    chunks, receipts = [], []
    while n:
        count = min(n,4096-((SBASE+a)&4095))
        pa, walk = translate(SBASE+a)
        b, off = physical(pa,count)
        chunks.append(b)
        receipts.append({'relative_va':hex(a),'snapshot_va':hex(SBASE+a),'pa':hex(pa),
                         'file_offset':hex(off),'bytes':count,'walk':walk})
        a += count
        n -= count
    return (b''.join(chunks),receipts) if provenance else b''.join(chunks)

def er(elf,b,a,n):
    for s in elf.iter_segments():
        if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a<a+n<=s['p_vaddr']+s['p_filesz']:
            off = s['p_offset']+a-s['p_vaddr']
            return b[off:off+n]
    raise ValueError(hex(a))

def plt(elf):
    sym, p, r = (elf.get_section_by_name(n) for n in ('.dynsym','.plt','.rela.plt'))
    return {p['sh_addr']+32+16*i:sym.get_symbol(x['r_info_sym']).name for i,x in enumerate(r.iter_relocations())}

cs = Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def dis(b,a,pm=None):
    ins = list(cs.disasm(b,a))
    assert sum(i.size for i in ins)==len(b), ('incomplete decode',hex(a))
    out = []
    for i in ins:
        row = {'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
        if i.mnemonic in ('b','bl') and pm:
            t = int(i.op_str.lstrip('#'),16)
            if t in pm:
                row['plt_symbol'] = pm[t]
        out.append(row)
    return out

identity = []
for label,a,expected in [
    ('ELF_header',0,skd[:0x150]),('GNU_hash',0x158,skd[0x158:0x194]),
    ('original_144_dynsym',0x198,se.get_section_by_name('.dynsym').data()[:144*24]),
    ('original_dynstr_prefix',0xf18,se.get_section_by_name('.dynstr').data()[:1024]),
    ('SONAME',0x14dc,b'libInfraSKD.so\0')]:
    actual,receipt = sr(a,len(expected),True)
    assert actual==expected,label
    identity.append({'name':label,'relative_va':hex(a),'bytes':len(expected),
                     'sha256':sha256(actual).hexdigest(),'matches_original_metadata':True,'provenance':receipt})

sb = {}
for label,a,n in [('read_source_byte',0x63f98,0x50),('descriptor_gather',0x6402c,0x108),
                  ('sync_callback',0x64134,0x434),('SKData_Init',0x64568,0x190),
                  ('SKData_Exit',0x646f8,0xd4),('error_drain',0x63fe8,0x44),
                  ('cipher_selector0',0x6f130,0x10),('cipher_selector1',0x6f1c0,0x10)]:
    b, receipt = sr(a,n,True)
    sb[label]={'start':hex(a),'bytes':n,'sha256':sha256(b).hexdigest(),
               'provenance':receipt,'instructions':dis(b,a,plt(se))}
assert sb['read_source_byte']['instructions'][10]['va']=='0x63fc0'
assert sb['read_source_byte']['instructions'][10]['asm']=='ldrb w0, [x1, x0]'

ab = {}
app_ranges = [('SKD_send_wrapper',0x2ea9bb0,0x94),('SKD_pack_message',0x2ea9c44,0x154),
              ('SKD_CipherInit',0x2ea9d98,0x5c),('data_encryption',0x2eaa030,0x270),
              ('infra_wrapper_data_encryption',0x2de27e4,0x40),
              ('auth_encrypt_pair',0x279efbc,0x114),('auth_command_1d39',0x279f0d0,0xc0),
              ('sequence_init_access_authentication_run',0x2bcc0a4,0x4a4)]
for label,a,n in app_ranges:
    b=er(ae,app,a,n)
    ab[label]={'start':hex(a),'bytes':n,'sha256':sha256(b).hexdigest(),'instructions':dis(b,a,plt(ae))}

strings = {}
for blocks,reader in [(ab,lambda a,n:er(ae,app,a,n)),(sb,lambda a,n:sr(a,n))]:
    for block in blocks.values():
        regs={}
        for i in block['instructions']:
            m=re.match(r'adrp (x\d+), #(0x[0-9a-f]+)',i['asm'])
            if m: regs[m[1]]=int(m[2],16)
            m=re.match(r'add (x\d+), (x\d+), #(0x[0-9a-f]+)',i['asm'])
            if m and m[2] in regs:
                a=regs[m[2]]+int(m[3],16);regs[m[1]]=a
                try: raw=reader(a,240).split(b'\0')[0]
                except ValueError:continue
                if 3<=len(raw)<=220 and all(x in (9,10,13) or 32<=x<127 for x in raw):
                    strings[hex(a)]=raw.decode()
                    i['referenced_string_va']=hex(a)
for a in [0x399e282,0x399e29e,0x399e2dd,0x399e2fb,0x399e321,0x399e33d,0x399e3e8,0x392df10]:
    strings[hex(a)]=er(ae,app,a,220).split(b'\0')[0].decode()
strings['SKD:0x206c70']=sr(0x206c70,9).decode().rstrip('\0')

descriptors=[]
for k in range(31):
    ptr,n=struct.unpack('<QQ',sr(0x279eb8+k*16,16));a=ptr-SBASE
    assert 0<=n<=2048
    assert n or ptr==0
    raw=sr(a,n*4) if n else b''
    pairs=[struct.unpack_from('<HH',raw,i*4) for i in range(n)]
    assert all((t==0 and x<=1023) or (t==1 and x<=31) for t,x in pairs)
    descriptors.append({'index':k,'table_relative_va':hex(0x279eb8+k*16),
                        'array_relative_va':hex(a),'entries':n,'sha256':sha256(raw).hexdigest(),
                        'output_bytes':n if k<=18 else n//4,
                        'source_offset_pairs':[[t,hex(x)] for t,x in pairs]})
assert descriptors[9]['array_relative_va']=='0x206ca0'
assert descriptors[9]['source_offset_pairs'][0]==[0,'0xeb']
all0=sorted({int(o,16) for d in descriptors for t,o in d['source_offset_pairs'] if t==0})
all1=sorted({int(o,16) for d in descriptors for t,o in d['source_offset_pairs'] if t==1})
assert all0==list(range(1024)) and all1==list(range(32))
ciphers=[]
for selector,a,nid in [(0,0x27b0b0,427),(1,0x27b9b0,901)]:
    b,receipt=sr(a,16,True)
    fields=struct.unpack('<IIII',b)
    assert fields[0]==nid and fields[2]==32
    ciphers.append({'selector':selector,'descriptor_va':hex(a),'first16_hex':b.hex(),
                    'nid':fields[0],'block_bytes':fields[1],'key_bytes':fields[2],'iv_bytes':fields[3],
                    'name':{427:'AES-256-CBC',901:'AES-256-GCM'}[nid],'provenance':receipt,
                    'NID_source':'https://raw.githubusercontent.com/openssl/openssl/OpenSSL_1_0_2u/crypto/objects/obj_mac.h'})

runtime_path=VM/'runtime/ap80c-review.json'
review=json.loads(source(runtime_path))
serial_path=VM/'runtime/runs/ap80cpanel-5dd371e5/serial.log'
serial=source(serial_path).decode(errors='replace').splitlines()
command=json.loads(source(serial_path.parent/'command.json'))
maps=[]
for row in review['exception_context']:
    m=re.match(r'([0-9a-f]+)-([0-9a-f]+) ([-rwx]+) 0x([0-9a-f]+) (.*)',row['text'])
    if m:maps.append((int(m[1],16),int(m[2],16),int(m[4],16),m[5]))
def locate(a):
    return [{'module':name,'relative':hex(a-start+off)} for start,end,off,name in maps if start<=a<end]
stack_chain=[0x7fb6085248,0x7fb76f6b1c,0x7fb76f9394,0x7f65b95be8,
             0x7f65b95d10,0x7f65b95de0,0x7f65b960a4,0x7f65ace810,
             0x7f6548b050,0x7f6548b15c,0x7f658b81a0,0x7f658c36fc,0x7f65c5dba0]
runtime={
    'fault':review['fault'],'actual_call_chain_return_addresses':[{'runtime_va':hex(a),'mapping':locate(a)} for a in stack_chain],
    'selected_serial':[{'line':i+1,'text':l} for i,l in enumerate(serial) if
        ('ffffb000' in l or 'f340f000' in l or 'f13b8000' in l or
         'FX3_BOOT_UI_FUTURE' in l or 'FX3_BOOT_NOTIFY' in l or
         'synchronous external abort' in l or 'r0: 0x0000000000000800' in l or
         'r4: 0x0000000000000000' in l)],
    'qemu_args':command['args'],'model_env':command['model_env'],
    'scope':'Pre-existing AP80c evidence only; no new run. Stack-frame return-address matches plus original BL sites, not a synthetic backtrace.'}

rom_path=PUB/'reference/bootrom/CXD90057_Mira_0xFFFF0000.bin'
rom=source(rom_path,'f93eaef410a47ec65f3487cd1edf63e1982df77163f3461206118ba5d6ee3fc3')
page=rom[0xb000:0xc000]
assert len(rom)==0xc000 and len(page)==0x1000 and page[0x8eb]==0x16
assert sha256(page).hexdigest()=='f2bcb4103c039ef6fdc258fd4abc08487f4c7c70e568034da9f04261c78651a2'
capture=json.loads(source(PUB/'source-capture.json'))
tree=json.loads(source(PUB/'upstream-tree.json'))
tree_entry=next(x for x in tree['tree'] if x['path']=='bootrom/CXD90057_Mira_0xFFFF0000.bin')
git_blob=sha1(b'blob '+str(len(rom)).encode()+b'\0'+rom).hexdigest()
assert git_blob==tree_entry['sha']=='c7d37785caddd0bc1b5d7ae4dde1a9d66a0c2194'
source(PUB/'reference/bootrom/README.md')
source(PUB/'reference/scripts/parse_emmc_boot0.py')
rom_proposal={
    'rank':1,'status':'BOUNDED_REFERENCE_ROM_MODEL_CANDIDATE_NOT_INTEGRATED_OR_RUN',
    'physical_address':'0xffffb000','bytes':4096,'read_only':True,
    'exact_contents_hex':page.hex(),'sha256':sha256(page).hexdigest(),
    'source_file':str(rom_path.relative_to(ROOT)),'source_file_offset':'0xb000',
    'source_blob_sha1':git_blob,'upstream_commit':'e85e137fc3b88b7cb26e69faa9f1304184678ff7',
    'url':'https://raw.githubusercontent.com/DavidBuchanan314/ILCE-7M4-RE/e85e137fc3b88b7cb26e69faa9f1304184678ff7/bootrom/CXD90057_Mira_0xFFFF0000.bin',
    'live_fetch_receipt':'Audit author fetched this immutable URL during the audit; 49152 bytes, identical SHA256 and byte equality. Rebuild is intentionally offline.',
    'provenance_label':'Public A7 IV reference Mira CXD90057 BootROM; FX3 same mask-ROM revision/bytes NOT proven.',
    'fault_byte_physical':'0xffffb8eb','fault_byte_hex':'16',
    'remaining':['0xf340f000: 32 source bytes are still absent and used by table 9 after 16 ROM bytes.',
                 '0xf13b8000: 12-byte source consumed by other cipher key selectors; no honest values bound.',
                 'Do not map 0xffffc000 or claim an FX3 ROM dump, OTP identity, successful crypto or UI acceptance.']}

def fdt(b):
    magic,total,os,ostr,omem,version,last,cpu,ss,sz=struct.unpack_from('>10I',b)
    assert magic==0xd00dfeed
    strings=b[ostr:ostr+ss];at=os;stack=[];rows=[]
    while at<os+sz:
        tag=struct.unpack_from('>I',b,at)[0];at+=4
        if tag==1:
            end=b.index(b'\0',at);stack.append(b[at:end].decode());at=(end+4)&~3
        elif tag==2:stack.pop()
        elif tag==3:
            n,no=struct.unpack_from('>II',b,at);at+=8;v=b[at:at+n];at=(at+n+3)&~3
            name=strings[no:strings.index(b'\0',no)].decode();node='/'.join(stack) or '/'
            if (name in ('reg','phys','size','virt','device_type','compatible','ranges','memtype') or 'reserved' in node):
                row={'node':node,'property':name,'hex':v.hex()}
                if len(v)%4==0:row['cells']=[hex(x) for x in struct.unpack('>'+'I'*(len(v)//4),v)]
                if v.endswith(b'\0') and all(x==0 or 32<=x<127 for x in v):row['text']=v.rstrip(b'\0').decode().replace('\0',' | ')
                rows.append(row)
        elif tag==4:pass
        elif tag==9:break
        else:raise ValueError(tag)
    reserves=[];at=omem
    while True:
        a,n=struct.unpack_from('>QQ',b,at);at+=16
        if a==n==0:break
        reserves.append({'address':hex(a),'bytes':hex(n)})
    return {'memreserve':reserves,'properties':rows}

dtb_path=PROJ/'regular-files/setting/cxd90057.dtb'
dtb=fdt(source(dtb_path))
kmod=load_module(SONY/'stage146-original-kernel-symbol-and-vendor-route/kernel_symbols.py','skd_kernel_symbols')
kernel=kmod.KernelSymbols()
source(kmod.KERNEL,kmod.KERNEL_SHA256)
kernel_blocks={}
for name in ['valid_phys_addr_range','phys_mem_access_prot','mmap_mem']:
    a,z=kernel.span(name);kernel_blocks[name]={'start_va':hex(kmod.K+a),'file_offset':hex(a),
        'span_rule':'next distinct kallsyms address, not ELF size','instructions':dis(kernel.raw[a:z],kmod.K+a)}
targets=[0xffffb000,0xffffb800,0xffff0000,0xf340f000,0xf13b8000]
def literal_scan(b):
    result={}
    for value in targets:
        matches=[m.start() for m in re.finditer(re.escape(struct.pack('<I',value)),b)]
        result[hex(value)]={'count':len(matches),'aligned4_count':sum(x%4==0 for x in matches),
                            'first_offsets':[hex(x) for x in matches[:12]]}
    return result
manifest=json.loads(source(PROJ/'full-v5/projection-manifest-full-v5.json'))
module_scan=[]
for row in manifest['members']:
    if not row['guest_path'].endswith('.ko'):continue
    p=Path(row['local_file']);b=p.read_bytes();assert sha256(b).hexdigest()==row['sha256']
    hits=literal_scan(b)
    module_scan.append({'guest_path':row['guest_path'],'path':str(p.relative_to(ROOT)),
                        'bytes':len(b),'sha256':row['sha256'],'literal_search':hits})
    if row['guest_path']=='/usr/kmod/wlan.ko':
        offsets=hits['0xffffb000']['first_offsets']
        assert len(offsets)==1
        off=int(offsets[0],16)
        elf=ELFFile(BytesIO(b))
        section=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_offset']<=off<s['sh_offset']+s['sh_size'])
        module_scan[-1]['ffffb000_collision']={'file_offset':hex(off),'section':section.name,'aligned4':off%4==0,
                                               'context_hex':b[off-16:off+20].hex(),
                                               'interpretation':'Unaligned four-byte overlap in .data; not an established physical-address reference.'}
gpl_path=SONY/'stage65-windows-cache-and-runtime-readiness/work/vendor-source-reference/range-resume-20261026/linux-kernel.complete.tar.gz'
source(gpl_path)
gpl_results=[];gpl_count=0
pat=re.compile(rb'(ffffb[08]00|ffff0000|f340f000|f13b8000|boot.?rom|\bOTP\b|efuse)',re.I)
with tarfile.open(gpl_path,'r:gz') as archive:
    for member in archive:
        if not member.isfile() or member.size>3000000:continue
        if not ('cxd' in member.name.lower() or '/arm64/' in member.name and any(x in member.name for x in ['include','mm/','mach'])):continue
        b=archive.extractfile(member).read();gpl_count+=1
        hits=[{'line':i+1,'text':l.decode(errors='replace')} for i,l in enumerate(b.splitlines()) if pat.search(l)]
        if hits:gpl_results.append({'member':member.name,'sha256':sha256(b).hexdigest(),'hits':hits})
gpl_dtsi=SONY/'stage133-FX5-source-availability-and-portability/fx3-gpl-reference/linux-kernel/arch/arm64/boot/dts/cxd/cxd90057.dtsi'
gpl_text=source(gpl_dtsi).decode()
gpl_iomap=[{'line':i+1,'text':l} for i,l in enumerate(gpl_text.splitlines()) if 59<=i+1<=84]

# CP scan is explicitly bounded: literal collisions and immediate candidates
# cannot establish that data tables execute or that no indirect writer exists.
thumb=Cs(CS_ARCH_ARM,CS_MODE_THUMB);thumb.skipdata=True
cp_candidates=[]
for a,n,m,o in thumb.disasm_lite(cp[:0xa00000],0x108000):
    if m in ('movw','movt','mov.w','mvn','mvn.w') and any(x in o for x in ['#0xb800','#0x47ff','#0xf340','#0xf13b']):
        data=cp[a-0x108000:a-0x108000+24]
        context=[{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in thumb.disasm(data,a)]
        cp_candidates.append({'va':hex(a),'asm':m+' '+o,'following_24_bytes':context})
partition_search=[]
for p in sorted((SONY/'stage2/extraction').glob('nflasha*.img')):
    b=source(p)
    partition_search.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),
        'public_mira_page_exact_match_offsets':[hex(m.start()) for m in re.finditer(re.escape(page),b)],
        'note':'Exact public reference-page match search only; a negative result cannot rule out compressed/encrypted/other ROM revisions.'})
unknown_physical={}
for a in [0xffffb000,0xf340f000,0xf13b8000]:
    try:b,off=physical(a,4096);unknown_physical[hex(a)]={'stored':True,'file_offset':hex(off),'sha256':sha256(b).hexdigest()}
    except ValueError as ex:unknown_physical[hex(a)]={'stored':False,'reason':str(ex)}

qemu_path=VM/'runtime/qemu-display-build/sources/qemu-11.1.2/hw/arm/virt.c'
qemu=source(qemu_path).decode().splitlines()
qemu_evidence=[{'line':i+1,'text':l} for i,l in enumerate(qemu) if 3158<=i+1<=3208]

proof={
    'status':'PASS_OFFLINE_SKD_SOURCE_FAULT_AND_REFERENCE_ROM_PROOF',
    'scope':'Static audit only. No QEMU, target execution, original mutation, device/OTP access or crypto operation.',
    'inputs':inputs,'wbi_identity':identity,'snapshot_root_pa':hex(WROOT),'snapshot_SKD_base':hex(SBASE),
    'skd_blocks':sb,'app_blocks':ab,'strings':strings,
    'osal_blocks':{label:dis(er(oe,osal,a,n),a,plt(oe)) for label,a,n in
                   [('u_osal_snd_sync_msg',0x3a98,0x13c),('__osal_snd_sync_msg',0x61e8,0x270)]},
    'source_maps':[{'selector':0,'physical_requested':'0xffffb800','mmap_offset':'0xffffb000','in_page_offset':'0x800',
                   'valid_descriptor_offsets':'0..0x3ff','protection':1,'flags':1,'bytes':4096},
                  {'selector':1,'physical_requested':'0xf340f000','mmap_offset':'0xf340f000','in_page_offset':'0',
                   'valid_descriptor_offsets':'0..0x1f','protection':1,'flags':1,'bytes':4096},
                  {'selector':'extra cipher material','physical_requested':'0xf13b8000','mmap_offset':'0xf13b8000',
                   'in_page_offset':'0','bytes_read_by_0x6436c':12,'protection':1,'flags':1,'bytes':4096}],
    'descriptor_table':descriptors,'cipher_descriptors':ciphers,
    'descriptor_source_coverage':{'selector0_offsets':len(all0),'selector1_offsets':len(all1)},
    'runtime':runtime,'device_tree':dtb,'kernel_blocks':kernel_blocks,
    'kernel_literal_search':literal_scan(kernel.raw),'kernel_module_scan':module_scan,
    'gpl_archive_scan':{'scanned_files':gpl_count,'filter':'cxd in name, or arm64 include/mm/mach, file <=3MB',
                        'matches':gpl_results,'cxd90057_dtsi_iomap_lines':gpl_iomap},
    'cp_search':{'raw_literals':literal_scan(cp),'immediate_scan_bytes':0xa00000,'immediate_candidates':cp_candidates,
                 'conclusion':'No demonstrated CP writer to 0xffffb000. Unaligned FFFFB800 collisions lie in data, not established address literals. Bounded scan does not exclude indirect/constructed addresses or boot ROM accesses.'},
    'partition_exact_public_page_search':partition_search,'wbi_physical_page_availability':unknown_physical,
    'qemu_model_source_lines':qemu_evidence,'rom_model_candidate':rom_proposal,
    'alternatives':[
        {'rank':2,'name':'explicit unavailable hardware / original mapping failure path',
         'proposal':'Only in VM model, deny the exact SKD /dev/mem mmap tuple (offset ffffb000, len1000, prot1, shared1) with MAP_FAILED/ENODEV, instead of allowing a dangling mapping. Do not fake success or a key.',
         'evidence':'SKData_Init 646cc closes fd and returns before callback registration; app SKD_send_wrapper preserves nonzero OSAL result; data_encryption writes result.status=2 and returns; auth caller ignores that status.',
         'content_bytes':0,'mapped_size':0,'scope':'Static nonfatal caller path only; OSAL no-provider exact result, startup/refcount cleanup, retry and UI survival require a Lead-run receipt.'},
        {'rank':3,'name':'complete same-revision ROM plus source1/source2 hardware model',
         'proposal':'Bind actual authorized pre-existing same-SoC ROM revision and documented register semantics; implement only exact resources, without importing another camera identity or derived secret.',
         'content_bytes':None,'scope':'Missing provenance for f340f000/f13b8000, no honest complete bytes available in this audit.'},
        {'rank':'rejected','name':'zero/ff/random ROM, catch-all MMIO, force crypto success',
         'reason':'read_source_byte and descriptor_gather have no blank-value or unconfigured check; zeros are returned as successful key material, including zero-derived IVs. No original nonfatal unconfigured branch proven.'}],
    'unproven':[
        'FX3 physical mask ROM revision and exact equality to the public A7 IV Mira dump.',
        'Official fine-grained name/semantics for f340f000 and f13b8000 (OTP/eFuse/chip-ID not established).',
        'An original /proc/iomem fine-grained resource name: DT only gives a broad iomap, no board readout was performed.',
        'Full CP indirect-writer exclusion; static candidate scans are bounded.',
        'Menu drawing/UI survival after the proposed memory model or unavailable-hardware fallback.',
        'Any physical-camera crypto, identity, recording, deployment or recovery acceptance.']}
wb.close();wf.close()
dest=OUT/'skd-ffffb000-proof.json'
dest.write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':proof['status'],'SKD_blocks':len(sb),'app_blocks':len(ab),'descriptor_rows':len(descriptors),
                  'modules_scanned':len(module_scan),'page_sha256':sha256(page).hexdigest(),
                  'fault_instruction':'ldrb w0, [x1, x0]','proof':str(dest)},ensure_ascii=False))
