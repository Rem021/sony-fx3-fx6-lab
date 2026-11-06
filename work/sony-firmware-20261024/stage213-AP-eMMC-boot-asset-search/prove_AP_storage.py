"""Pin current package AP storage device/geometry and read-dispatch evidence.

Host ELF/data parsing only. No Sony code, guest, USB, root or device I/O.
"""
from pathlib import Path
from hashlib import sha256
import ast,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
def dump(name,x):(H/name).open('x').write(json.dumps(x,indent=2)+'\n')
captures=[]
for name in ['driver-source-capture.json','devno-source-capture.json']:
    cap=json.loads((H/name).read_text());assert sha256((R/cap['source_image']).read_bytes()).hexdigest()==cap['source_sha256']
    for row in cap['files']:
        raw=(R/row['output']).read_bytes();assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256'];captures.append(row)
rel=json.loads((H/'driver-relocations-detailed.json').read_text())
rlookup={(r['section'],r['offset']):r for r in rel};cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM);pins=[]
emmc=H/'originals/current-p3-initrd/kmod/emmc.ko';devno=H/'originals/current-p3-initrd/kmod/devno.ko'
def pin(label,path,section,lo,hi,note):
    with path.open('rb') as f:
        e=ELFFile(f);s=e.get_section_by_name(section);assert 0<=lo<hi<=s['sh_size']
        raw=s.data()[lo:hi];fo=s['sh_offset']+lo
    p=H/'pins'/f'{label}.bin';p.parent.mkdir(exist_ok=True);p.open('xb').write(raw)
    item=dict(label=label,source=str(path.relative_to(R)),source_sha256=sha256(path.read_bytes()).hexdigest(),
        section=section,section_offset=lo,end_exclusive=hi,file_offset=fo,bytes=len(raw),
        sha256=sha256(raw).hexdigest(),raw=str(p.relative_to(R)),note=note)
    if path==emmc:
        item['relocations']=[r for r in rel if r['section']==section and lo<=r['offset']<hi]
    pins.append(item);return raw
pin('boot-device-table',devno,'.data',0,64,'Four node descriptors: raw user, B0, B1 and crypt user; names relocated separately.')
pin('boot-node-names',devno,'.rodata.str1.8',0,64,'Original current7.02 node names; not copied from GPL table.')
pin('descriptor-base-and-boot-selection',emmc,'.init.text',0x600,0x61c,'Loop record index x23, 0xe0 stride.')
pin('boot-descriptor-kind-and-no-callback',emmc,'.init.text',0x754,0x7d8,'Index1 sets type1, other selected boot branch sets2; clears callback pointer+c8, calls common init.')
pin('boot-node-pointer-relocations',emmc,'.init.text',0x908,0x918,'udif_devnodes+16 and+32 are B0 and B1 descriptors.')
pin('common-node-and-offset-init',emmc,'.init.text',0x388,0x488,'Copies descriptor name and u16 major/minors; clears sector offset+88.')
pin('capacity-kind-dispatch',emmc,'.text',0x7f40,0x7fb8,'Kinds1/2 call get_boot_capacity then subtract start_sector<<9.')
pin('boot-capacity-getter-and-pointer',emmc,'.text',0x145a0,0x145b8,'u8 state+dc <<17; pointer relocation to.bss+5c0, not a fixed4MiB constant.')
pin('generic-read-callback-or-sequence',emmc,'.text',0x7cd8,0x7d84,'If callback+c8 absent, passes kind and null optional argument to emmc_seq_read.')
pin('seq-read-partition-and-data-call',emmc,'.text',0x12f4c,0x12f84,'Read compares/switches partition before data helper; optional value preserved into x4. Lower data/crypto helper not closed here.')
pin('gendisk-name-major-minor-capacity',emmc,'.init.text',0x17a0,0x1820,'Copies major/first_minor/name and byte_capacity>>9 to gendisk before device_add_disk.')

# Independently resolve the relocated current node table, rather than trusting
# the already exported locator metadata or the different GPL platform table.
with devno.open('rb') as f:
    e=ELFFile(f);table=e.get_section_by_name('.data');data=table.data();sec=e.get_section_by_name('.rela.data');sy=e.get_section(sec['sh_link']);rows=[]
    for off,expected in [(0,'pnflasha'),(16,'nflashaB0'),(32,'nflashaB1'),(48,'cnflasha')]:
        r=next(r for r in sec.iter_relocations() if r['r_offset']==off)
        s=sy.get_symbol(r['r_info_sym']);ss=e.get_section(s['st_shndx']);pos=s['st_value']+r['r_addend']
        name=ss.data()[pos:].split(b'\0',1)[0].decode();assert name==expected
        kind,major,first_minor,nr_minor=struct.unpack_from('<4H',data,off+8)
        rows.append(dict(index=off//16,name=name,type=kind,major=major,first_minor=first_minor,nr_minor=nr_minor))
    assert [(x['name'],x['type'],x['major'],x['first_minor'],x['nr_minor']) for x in rows]==[
        ('pnflasha',1,252,0,32),('nflashaB0',1,252,126,1),('nflashaB1',1,252,127,1),('cnflasha',1,252,128,32)]
with emmc.open('rb') as f:
    e=ELFFile(f)
    def word(section,offset):return struct.unpack_from('<I',e.get_section_by_name(section).data(),offset)[0]
    assert word('.text',0x145a4)==0x39437000   # ldrb w0,[x0,#dc]
    w=word('.text',0x145a8);assert (w>>16)&63==47 and (w>>10)&63==7  # ubfiz64 shift17,width8
    w=word('.init.text',0x7c4);assert (w&31)==31 and ((w>>5)&31)==20 and ((w>>10)&4095)*8==0xc8
    assert word('.text',0x7d6c)==0xd2800003    # mov x3,#0
    assert rlookup[('.text',0x7d78)]['symbol']=='emmc_seq_read'
    assert rlookup[('.init.text',0x908)]['symbol']=='udif_devnodes' and rlookup[('.init.text',0x908)]['addend']==16
    assert rlookup[('.init.text',0x910)]['symbol']=='udif_devnodes' and rlookup[('.init.text',0x910)]['addend']==32
lines=[]
for p,terms in [('GPL/include/linux/udif/devnode.h',['UDIF_TYPE_CDEV','UDIF_TYPE_BDEV','struct UDIF_DEVNODE','*name','short type','short major','short first_minor','short nr_minor']),
                ('GPL/include/linux/genhd.h',['struct gendisk {','int major;','int first_minor;','int minors;','char disk_name']),
                ('originals/current-p3-initrd/sbin/initrc/insmod_drv1',['insmod /kmod/devno.ko','insmod /kmod/crypt-emmc.ko','insmod /kmod/emmc.ko'])]:
    for i,text in enumerate((H/p).read_text().splitlines(),1):
        if any(t in text for t in terms):lines.append(dict(path=p,line=i,text=text))
proof=dict(status='CURRENT_PACKAGE_AP_BOOT_DEVICES_GEOMETRY_AND_READ_DISPATCH_BOUND',
    current_source='official7.02 main p3 initrd; actual installed current-body p1 identity not obtained',
    captures=captures,raw_ranges=pins,source_lines=lines,nodes=rows,
    boot0_node='/dev/nflashaB0',boot1_node='/dev/nflashaB1',
    boot0_public_main_driver_rdev=[252,126],boot1_public_main_driver_rdev=[252,127],
    boot_capacity_expression='unsigned byte state+0xdc * 131072; boot descriptor start sector is0 in selected init route',
    boot_capacity_runtime_value=None,boot_capacity_fixed_4MiB_proven=False,
    formatter_2MiB_map_not_complete_boot_capacity=True,
    boot_descriptors_software_crypt_callback_cleared=True,
    direct_read_passes_partition_type_and_null_optional_arg=True,
    lower_transfer_crypto_or_whole_boot_rawness_closed=False,
    current_body_readability_geometry_backup_or_independent_restore_proven=False,
    GPL_layout_only_not_matching_platform_table=True,
    limits=['Do not use public-main module identity as installed p1 identity.',
        'No claim full boot contents are plaintext; per-component format/encryption remains separate.',
        'GPT/boot backup data are not present just because device descriptors exist.',
        'Numeric geometry must be observed in a specifically authorized same-body capture, without4MiB fallback.',
        'GPL header gives shared layout only; its platform node table differs from current binary.'],
    independent_word_checks=4,independent_relocation_checks=3,
    Sony_code_or_guest_execution=False,root_or_device_operations=0,persistent_write_release=False)
dump('AP-storage-contract-proof.json',proof)
plan=dict(schema='fx3-AP-boot-capture-data-only-v1',target='classic ILME-FX3 7.02',
    evidence='AP-storage-contract-proof.json',candidate_targets=[
        dict(path='/dev/nflashaB0',public_main_rdev=[252,126],role='boot0 hardware region',actual_geometry_bytes=None),
        dict(path='/dev/nflashaB1',public_main_rdev=[252,127],role='boot1 hardware region; content/use unknown',actual_geometry_bytes=None)],
    conditions=['Actual execution-environment module identity and same-body identity must be checked before using this candidate.',
        'Obtain the whole reported region size; reject missing/zero/inconsistent geometry; never substitute publicA7IV4MiB or formatter2MiB.',
        'Record read view, driver identity, full-region hash and bounded chunk checks; lower crypto path must be clarified.',
        'Node metadata and a completed read do not themselves prove independent entry, restore or cold boot.'],
    executable_payload=False,new_device_backend=False,camera_operation_authorized=False,
    device_read_or_write_performed=False,persistent_write_release=False)
dump('AP-boot-capture-contract-candidate.json',plan)
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
print(json.dumps(dict(raw_ranges=len(pins),source_lines=len(lines),boot_nodes=rows[1:3],
    independent_word_checks=4,independent_relocation_checks=3,actual_geometry_measured=False,actual_device_operations=0)))
