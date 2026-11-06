"""Bind WBI handoff address to shipped initialization/module metadata; no I/O."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
H=Path(__file__).resolve().parent
image=json.loads((H/'WBI-layout-audit.json').read_text());capture=json.loads((H/'emmc-provider-capture.json').read_text())
row=next(x for x in capture if x['path']=='/kmod/emmc.ko');p=Path(row['output']);raw=p.read_bytes();assert sha256(raw).hexdigest()==row['sha256'];e=ELFFile(BytesIO(raw))
script_path=Path(next(x for x in capture if x['path']=='/sbin/initrc/insmod_drv1')['output']);script=script_path.read_text()
assert 'insmod /kmod/emmc.ko tbl=0xFFFFFFC003E00000 tune_en=0' in script
target=0xffffffc003e00000;region=[s for s in image['sections'] if s['virt']<=target<s['virt']+s['olen']];assert len(region)==1;region=region[0]
assert region['index']==1379 and region['virt']==target and region['addr']==0x403e00000 and region['rlen']==0x22000
def relocs(name):
    rs=e.get_section_by_name(name);st=e.get_section(rs['sh_link']);rows={}
    for r in rs.iter_relocations():
        s=st.get_symbol(r['r_info_sym']);ix=s['st_shndx'];sec=e.get_section(ix) if isinstance(ix,int) else None
        rows[r['r_offset']]=dict(symbol=s.name,target_section=sec.name if sec else ix,target_offset=s['st_value']+r['r_addend'],type=r['r_info_type'])
    return rows
params=relocs('.rela__param');code_rels=relocs('.rela.init.text')
assert params[0x28]['target_section']=='.rodata' and e.get_section_by_name('.rodata').data()[params[0x28]['target_offset']:].split(b'\0',1)[0]==b'tbl'
assert params[0x38]['symbol']=='param_ops_ulong' and params[0x48]['target_section']=='.bss' and params[0x48]['target_offset']==0x528
assert code_rels[0x928]['target_section']=='.bss' and code_rels[0x928]['target_offset']==0x1b8
text=e.get_section_by_name('.init.text').data();w=lambda a:struct.unpack_from('<I',text,a)[0]
assert w(0x494)&0xff00001f==0x58000016
word=w(0x530);assert word&0xffc003ff==0xf94002c4 and ((word>>10)&0xfff)*8==0x370
assert 0x1b8+0x370==0x528
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.skipdata=True;cuts=[]
for a,z,label,code in [(0x488,0x4b4,'tbl-base',True),(0x530,0x58c,'tbl-field-consumer',True),(0x824,0x84c,'tbl-validation-tail',True),(0x928,0x930,'tbl-base-relocation',False)]:
    data=text[a:z];lines=[]
    if code:
        for i in md.disasm(data,a):
            extra=' ; '+str(code_rels[i.address]) if i.address in code_rels else ''
            if i.mnemonic=='ldr' and '[' not in i.op_str and '#' in i.op_str:
                lit=int(i.op_str.split('#')[-1],16)
                if lit in code_rels:extra+=' ; literal '+str(code_rels[lit])
            lines.append(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}{extra}')
    else:lines=[hex(a)+' DATA '+data.hex()+' ; '+str(code_rels.get(a))]
    out=H/'pins'/(label+'.txt');out.parent.mkdir(exist_ok=True);out.open('x').write('\n'.join(lines)+'\n')
    cuts.append(dict(source=str(p),source_sha256=sha256(raw).hexdigest(),section='.init.text',start=hex(a),end_exclusive=hex(z),bytes=len(data),sha256=sha256(data).hexdigest(),data_not_code=not code,output=str(out)))
result=dict(status='SHIPPED_INIT_ARGUMENT_AND_DRIVER_SLOT_MATCH_WBI_SECTION1379',source_module=str(p),module_sha256=sha256(raw).hexdigest(),script=str(script_path),script_sha256=sha256(script_path.read_bytes()).hexdigest(),
    tbl_argument=hex(target),parameter_descriptor=hex(0x28),parameter_storage='.bss+0x528',consumer_base='.bss+0x1b8',consumer_field_offset=hex(0x370),
    WBI_section=1379,WBI_physical=hex(region['addr']),WBI_stored_bytes=region['rlen'],WBI_stored_sha256=region['stored_sha256'],
    source_consumer='emmc_blk_plat_init checks supplied pointer, tests metadata fields, and passes selected fields into emmc_seq_init/set_cid/set_csd',
    independent_bootloader_code_recovered=False,same_body_partition_backup=False,full_handoff_format_or_partition_geometry_decoded=False,
    selected_module_ranges=cuts,proof_checks=['exact init argument matches WBI virtual start','module-param name and ulong ops identified through actual section relocations','param storage.bss528 equals init literal.bss1b8 plus load370','record1379 is stored data, not zero-fill'],
    limits=['static address and consumer match only, not observed runtime pointer or validated contents on current body',
      'full record includes additional data not decoded; not reclassified as whole boot0/p1 image or partition table'],original_or_guest_execution=False,root_or_device_operations=0)
(H/'emmc-handoff-proof.json').open('x').write(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(section=1379,physical=hex(region['addr']),stored_bytes=region['rlen'],source_ranges=len(cuts),bootloader_recovered=False,device_operations=0)))
