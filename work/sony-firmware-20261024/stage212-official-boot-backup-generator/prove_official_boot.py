"""Static official boot-writer contract and host-only BK4 layout comparison.

No Sony program/script is run. No USB, root, subprocess, mount, writable image,
BKSB output, firmware modification or device backend exists here.
"""
from pathlib import Path
from hashlib import sha256
import ast, importlib.util, io, json, re, struct, sys, types
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

H=Path(__file__).resolve().parent; B=H.parent; R=H.parents[2]
def dump(name,value):
    (H/name).open('x').write(json.dumps(value,indent=2)+'\n')
cap=json.loads((H/'source-capture.json').read_text())
for row in cap['files']:
    data=(R/row['output']).read_bytes()
    assert len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256']
cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
ranges=[]
def pin(label,name,lo,hi,note):
    fpath=H/'originals/bin'/name
    with fpath.open('rb') as f:
        elf=ELFFile(f)
        segments=[p for p in elf.iter_segments() if p['p_type']=='PT_LOAD'
                  and p['p_vaddr']<=lo and hi<=p['p_vaddr']+p['p_filesz']]
        assert len(segments)==1
        p=segments[0]; off=p['p_offset']+lo-p['p_vaddr']
        f.seek(off); data=f.read(hi-lo); assert len(data)==hi-lo
    dest=H/'pins'/f'{label}.bin';dest.parent.mkdir(exist_ok=True)
    dest.open('xb').write(data)
    lines=[]
    for at in range(0,len(data),4):
        ins=list(cs.disasm(data[at:at+4],lo+at,count=1))
        lines.append(f'{lo+at:08x}: {data[at:at+4].hex()} '+
                     (f'{ins[0].mnemonic} {ins[0].op_str}' if ins else '.word'))
    (dest.with_suffix('.txt')).open('x').write('\n'.join(lines)+'\n')
    ranges.append(dict(label=label,source=str(fpath.relative_to(R)),
        source_sha256=sha256(fpath.read_bytes()).hexdigest(),VA_start=hex(lo),
        VA_end_exclusive=hex(hi),file_offset=off,bytes=len(data),sha256=sha256(data).hexdigest(),
        raw=str(dest.relative_to(R)),disassembly=str(dest.with_suffix('.txt').relative_to(R)),note=note))
    return data

pin('bksb-main-options','bksb.elf',0x400fd4,0x4010b4,
    '-m writes output slot0 at frame+B0; -c slot1 at+B8, optional argument handling retained.')
pin('bksb-output-slot-record-selection','bksb.elf',0x4011c0,0x4011e4,
    'Loops output slots x24=0,1; skips null output paths.')
pin('bksb-selected-record-call','bksb.elf',0x4012b4,0x4012ec,
    'Passes loaded Backup base and output index to402998; then Data_init4020E0.')
pin('bksb-record-selector','bksb.elf',0x402998,0x402a68,
    'index0 returns base; index1 advances by align_up(u32[18]+u32[1C],4096), checks next revision.')
pin('bksb-input-open-readonly','bksb.elf',0x402d6c,0x402e78,
    'Input open flags0, stat/allocate/read/close; this helper is static, not executed.')
pin('bksb-header-offset-sizing','bksb.elf',0x4012ec,0x4013e0,
    '8+12*N first data offset; stores ID,offset,size; advances each size aligned4.')
pin('bksb-magic-table-write','bksb.elf',0x4013e0,0x401458,
    'fopen output; fwrite BKSB4, count4, N entries of12; checks counts.')
pin('bksb-data-offset-and-write','bksb.elf',0x40146c,0x401518,
    'Read property, compare expected size and ftell, write property bytes.')
pin('bksb-data-padding','bksb.elf',0x401560,0x4015c4,
    'Pads non4byte property lengths to4; not a full Backup or rescue package.')
magic=pin('bksb-magic-constant','bksb.elf',0x40317b,0x40317f,'BKSB literal')
assert magic==b'BKSB'
pin('pformat-main-discard-write-return','pformat.elf',0x4093c4,0x4093dc,
    'Sets w19=0; calls409D2C; branches4090DC without transferring helper return to w19.')
pin('pformat-main-return','pformat.elf',0x4090dc,0x4090fc,
    'Restores registers then returns w19; conditional selected write-call path discards helper status.')
pin('pformat-open-map-boot-device','pformat.elf',0x409d2c,0x409dd8,
    'open caller device flags0x101002; mmap length0x200000,prot3,flags1,offset0; returned errors distinct.')
pin('pformat-header-struct-writes','pformat.elf',0x409df8,0x409e88,
    'Writes header/config-derived words to shared writable mapping; not a read-only probe.')
pin('pformat-component-copy','pformat.elf',0x40a108,0x40a168,
    'Selected component branch copies into mapping or calls encryption helper; config-derived sectors; readback not shown.')

linepins=[]
needles={
    'loader_writer.sh':['LOADER_TAR=','mount -t','cp /setting/Backup.bin','umount ',
        'bksb.elf ','$PFORMAT_COMMAND /dev/nflashaB0','ud_get_mem2file.elf ',
        'dd if=${DDRTRAIN_BIN}','local retval=','write_trainingdata'],
    'nor_loader_writer.sh':['LOADER_TAR=','mount ','cp /setting/Backup.bin',
        'bksb.elf ','PFORMAT_COMMAND=','SPICOMBOOT_COMMAND=', 'CPFIRMUP_COMMAND=',
        'BACKUP_FILE','/backup/','LdrBkup.bin','loader_spi.bin','ENTRY','nor_ldr.img',
        '$CPFIRMUP_COMMAND','LSINUM_MIRA_CETUS','BOOTDEVICE','BOOTEXT'],
}
for name,terms in needles.items():
    fpath=H/'originals/bin'/name
    for i,line in enumerate(fpath.read_text().splitlines(),1):
        if any(t in line for t in terms):
            linepins.append(dict(source=str(fpath.relative_to(R)),line=i,text=line))

nor=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members'
listdata=(nor/'LdrBkupList.txt').read_bytes()
assert sha256(listdata).hexdigest()=='ae537183ecce42fbe9589c01f7ee4a19929fa2fc1cb09e48eda9ef2ab6f5dd88'
ids=[int(x,16) for x in re.findall(rb'0x[0-9A-Fa-f]+',listdata)]
assert len(ids)==len(set(ids))==65
config=(nor/'pformat_config.txt').read_bytes()
list_capture=dict(path=str((nor/'LdrBkupList.txt').relative_to(R)),bytes=len(listdata),
    sha256=sha256(listdata).hexdigest(),IDs=[hex(x) for x in ids],
    config_path=str((nor/'pformat_config.txt').relative_to(R)),config_sha256=sha256(config).hexdigest(),
    role='current package CP NOR list; AP loader_emmc list not acquired')

# Validate complete BK4 records with previously reviewed original host parser,
# then compare independently decoded selected properties against pinned PMCA.
ref=B/'stage207-Backup-template-and-GPIO-config'
src=(ref/'read_template_fields.py').read_bytes()
node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='read_record')
ns=dict(struct=struct,sha256=sha256,TARGETS=[])
exec(compile(ast.Module(body=[node],type_ignores=[]),'<reviewed host read_record>','exec'),ns)
pcap=json.loads((ref/'format-source-capture.json').read_text())
for r in pcap['files']:assert sha256((R/r['output']).read_bytes()).hexdigest()==r['sha256']
pkgname='fx3_bksb212'; pkgroot=ref/'reference/pmca/pmca'
pkg=types.ModuleType(pkgname);pkg.__path__=[str(pkgroot)];sys.modules[pkgname]=pkg
spec=importlib.util.spec_from_file_location(pkgname+'.backup',pkgroot/'backup/__init__.py',
    submodule_search_locations=[str(pkgroot/'backup')])
pmca=importlib.util.module_from_spec(spec);sys.modules[pkgname+'.backup']=pmca;spec.loader.exec_module(pmca)
def own_property(raw,base,ident):
    ns_,=struct.unpack_from('<I',raw,base+0x10)
    sid=ident>>16; unit=ident&65535
    if sid>=ns_:return None
    count,index=struct.unpack_from('<HI',raw,base+256+6*sid)
    if unit>=count:return None
    attr,ptr=struct.unpack_from('<HI',raw,base+256+6*ns_+6*(index+unit))
    if ptr==0xffffffff:return None
    length=ptr>>24;off=base+(ptr&0xffffff)
    if length==255:length,=struct.unpack_from('<H',raw,off);off+=2
    elif length==0:length,_maximum=struct.unpack_from('<HH',raw,off);off+=4
    return attr,raw[off:off+length]

templates=json.loads((ref/'template-source-capture.json').read_text())
layouts=[]; checks=0
for tr in templates['files']:
    raw=(R/tr['output']).read_bytes()
    assert len(raw)==tr['size'] and sha256(raw).hexdigest()==tr['sha256']
    first,end=ns['read_record'](raw,0); second_start=(end+4095)&~4095
    second,last=ns['read_record'](raw,second_start)
    assert last==len(raw)
    for index,record in enumerate([first,second]):
        base=record['offset']; view=io.BufferedReader(io.BytesIO(raw[base:base+record['record_bytes']]))
        assert not view.writable(); bk=pmca.BackupFile(view)
        entries=[];offset=8+12*len(ids);missing=[]
        for ident in ids:
            own=own_property(raw,base,ident)
            if own is None:
                missing.append(hex(ident));continue
            prop=bk.getProperty(ident)
            assert own==(prop.attr,prop.data)
            attr,data=own; size=len(data)
            entries.append(dict(id=hex(ident),bytes=size,output_offset=offset,
                attr=attr,data_sha256=sha256(data).hexdigest()))
            offset+=(size+3)&~3;checks+=1
        layouts.append(dict(template=tr['name'],source_sha256=tr['sha256'],record_index=index,
            record_offset=base,list_source='CP NOR list applied as host-only comparison to both records',
            entries=entries,missing_ids=missing,all65_present=not missing,
            predicted_BKSB_bytes=offset if not missing else None,
            fits_CP_config_2048_bytes=(offset<=2048) if not missing else None,
            actual_generated_BKSB=False,AP_list_equivalence_proven=False))
        view.close()
dump('default-BKSB-layout-comparison.json',dict(status='HOST_ONLY_LAYOUT_AND_INDEPENDENT_PROPERTY_COMPARISON',
    list=list_capture,record_count=len(layouts),property_checks=checks,layouts=layouts,
    PMCA_commit=pcap['commit'],reviewed_record_parser_sha256=sha256(src).hexdigest(),
    Sony_or_guest_execution=False,device_operations=0,generated_Sony_binary_files=0,
    current_body_properties_read=False,not_same_body_backup=True))

proof=dict(status='STATIC_CURRENT_PACKAGE_BOOT_WRITER_CONTRACT',capture='source-capture.json',
    ranges=ranges,script_lines=linepins,list_capture=list_capture,
    findings={
        'm_selects_record':0,'c_selects_record':1,
        'second_record_advance':'align_up(data_offset@0x18 + data_bytes@0x1c,4096)',
        'BKSB_header':'magic BKSB(4), little-endian count(4), count*(ID,offset,size) each12, data padded4',
        'BKSB_is_subset_not_full_same_body_backup':True,
        'AP_script_archive':'loader_emmc.tar','AP_script_device':'/dev/nflashaB0',
        'AP_script_Backup_source':'/setting/Backup.bin from mounted P2; -m',
        'AP_formatter_selected_path_maps_writable_shared_boot_window_bytes':2097152,
        'AP_formatter_selected_main_path_discards_writer_return':True,
        'CP_script_archive':'loader_nor.tar','CP_script_Backup_option':'-c',
        'CP_script_can_use_package_Backup_instead_of_installed_setting':True,
        'CP_script_uses_SPI_then_CP_updater_for_NOR_route':True,
        'current_NOR_is_not_independent_AP_boot_proof':True,
        'actual_current_body_boot0_p1_or_healthy_Backup_available':False,
        'AP_loader_emmc_archive_or_its_property_list_acquired':False,
        'independent_AP_entry_or_same_body_restore_tested':False,
    },
    limits=['Static selected script and instruction paths; no actual boot selection or hardware population attestation.',
        'Writable shared mapping length is not a claim every byte is written.',
        'No AP loader archive/config: exact AP component footprint not inferred from CP config.',
        '65-ID comparison uses CP list on public defaults; it does not invent an AP list or same-body BKSB.',
        'A7IV public AP image and FX3 CP component share code patterns, not proof of interchangeable images.'],
    Sony_code_or_guest_execution=False,root_or_device_operations=0,persistent_write_release=False)
dump('official-boot-writer-proof.json',proof)
print(json.dumps(dict(raw_ranges=len(ranges),source_lines=len(linepins),records=len(layouts),
    compared_properties=checks,missing_records=sum(bool(x['missing_ids']) for x in layouts),
    predicted_sizes=sorted({x['predicted_BKSB_bytes'] for x in layouts if x['predicted_BKSB_bytes'] is not None}),
    actual_camera_operations=0)))
