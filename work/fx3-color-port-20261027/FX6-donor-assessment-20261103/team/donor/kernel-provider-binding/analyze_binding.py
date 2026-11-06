#!/usr/bin/env python3
"""Pin original FX6 AP/kernel/LIRO/module relocation chain into ORIL API slots."""
from hashlib import sha256
import json
from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

from kernel_symbols import HERE, IMAGE, KernelSymbols

DONOR=HERE.parent
MAC=HERE.parents[5]
FILES={
 'fx6_kernel':(IMAGE,'bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9'),
 'fx6_av':(DONOR/'fat-files/nflasha3/av-cam.bin','56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf'),
 'fx6_im':(DONOR/'nflasha15-files/bin/im.elf','87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec'),
 'liro':(DONOR/'nflasha15-files/kmod/liro.ko','8a7cfcaef07ad18ca2a97847d44d31bb9152f57c0fcbccd96056ad683649f2e1'),
 'osal_uipc':(DONOR/'nflasha15-files/kmod/osal_uipc.ko','07bafe9c7cf0cba42de4e7c8f62229d298881552b144e0ee43ff3b404ca379ee'),
 'backup':(DONOR/'nflasha15-files/kmod/backup.ko','0fe57e43eb9b868f7011c4ea02ad002f0860d9d10fc2a644c772a074fc7532e6'),
 'fx3_liro':(MAC/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha15/kmod/liro.ko',
             'b4bd80cc614751e0092ee19e89cb90632db580bc01f23f1a1df23544e9b10186'),
 'fx3_osal_uipc':(MAC/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha15/kmod/osal_uipc.ko',
                  '6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38'),
 'fx3_backup':(MAC/'work/sony-firmware-20261024/stage208-Backup-record-routing/originals/kmod/backup.ko',
                '8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d'),
}
BASE_AV=0xffffffc001000000


def pinned(key):
    path,digest=FILES[key];data=path.read_bytes()
    assert sha256(data).hexdigest()==digest,(key,sha256(data).hexdigest())
    return data


def insns(data,off,size,va_base=0):
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    return [{'file_or_section_offset':hex(i.address-va_base),'va_or_section_address':hex(i.address),
             'original_bytes':i.bytes.hex(),'asm':(i.mnemonic+' '+i.op_str).strip()}
            for i in md.disasm(data[off:off+size],va_base+off)]


def section_reloc(elf,reloc_section,offset):
    sec=elf.get_section_by_name(reloc_section);symtab=elf.get_section(sec['sh_link'])
    hits=[r for r in sec.iter_relocations() if r['r_offset']==offset]
    assert len(hits)==1,(reloc_section,hex(offset),len(hits))
    r=hits[0];s=symtab.get_symbol(r['r_info_sym'])
    target_section=elf.get_section(s['st_shndx']).name if isinstance(s['st_shndx'],int) else None
    return {'relocation_offset_in_target_section':hex(offset),'type_number':r['r_info_type'],
            'symbol':s.name or target_section,'symbol_section':target_section,
            'symbol_value':hex(s['st_value']),'addend':hex(r['r_addend'] & ((1<<64)-1)),
            'target_section':reloc_section.removeprefix('.rela')}


def defined_export(path,name):
    with path.open('rb') as f:
        elf=ELFFile(f);sym=elf.get_section_by_name('.symtab')
        rows=[s for s in sym.iter_symbols() if s.name==name and s['st_shndx']!='SHN_UNDEF']
        assert len(rows)==1,(path,name)
        row=rows[0];sec=elf.get_section(row['st_shndx'])
        assert sec.name=='.text'
        exports=[]
        for relsec in elf.iter_sections():
            if relsec.name.startswith('.rela__ksymtab'):
                for r in relsec.iter_relocations():
                    target=sym.get_symbol(r['r_info_sym'])
                    if target.name==name:
                        exports.append({'section':relsec.name,'entry_relocation_offset':hex(r['r_offset']),
                                        'type_number':r['r_info_type'],'addend':r['r_addend']})
        assert len(exports)==1,(path,name,exports)
        original=sec.data()[row['st_value']:row['st_value']+row['st_size']]
        return {'symbol':name,'elf_section':sec.name,'section_offset':hex(row['st_value']),
                'file_offset':hex(sec['sh_offset']+row['st_value']),
                'byte_length':row['st_size'],'original_bytes_sha256':sha256(original).hexdigest(),
                'export_relocation':exports[0]}


def kernel_chain(image):
    targets=['SyS_init_module','load_module','resolve_symbol.isra.32',
             'each_symbol_section','apply_relocate_add','do_init_module']
    found={n:image.unique(n) for n in targets}
    edges=[('SyS_init_module',0x94d64,'load_module'),
           ('load_module',0x93c2c,'resolve_symbol.isra.32'),
           ('load_module',0x9445c,'resolve_symbol.isra.32'),
           ('resolve_symbol.isra.32',0x9210c,'each_symbol_section'),
           ('load_module',0x94524,'apply_relocate_add'),
           ('load_module',0x94a18,'do_init_module')]
    result=[]
    for src,off,dst in edges:
        word=struct.unpack_from('<I',image.raw,off)[0]
        assert word>>26==0x25
        imm=word&0x3ffffff
        if imm&0x2000000:imm-=0x4000000
        target=off+4*imm
        assert target==found[dst]['file_offset'],(src,off,dst,hex(target))
        result.append({'caller_symbol':src,'call_file_offset':hex(off),
                       'call_va':hex(image.base+off),'original_word_le':image.raw[off:off+4].hex(),
                       'target_symbol':dst,'target_file_offset':hex(target),'target_va':hex(image.base+target)})
    elf_magic_off=0x524b88
    assert image.raw[elf_magic_off:elf_magic_off+4]==b'\x7fELF'
    return {'edges':result,'load_module_elf_header_check':{
                'file_offset':'0x92bd4..0x92c04','elf_magic_file_offset':hex(elf_magic_off),
                'magic_bytes':image.raw[elf_magic_off:elf_magic_off+4].hex(),
                'original_instructions':insns(image.raw,0x92bd4,0x34,image.base),
                'interpretation':'four-byte ELF magic, AArch64 ET_REL and 64-byte section-header checks before module relocation'},
            'scope':'original FX6 kernel symbol VA and direct BL edges; runtime module load success/order not observed'}


def main():
    data={k:pinned(k) for k in FILES}
    image=KernelSymbols()
    av=data['fx6_av']
    assert av[8:12]==b'ORIL' and struct.unpack_from('<Q',av,0x20)[0]==BASE_AV+0x1a4
    assert struct.unpack_from('<Q',av,0x1a4)[0]==0
    assert av[0x1ec:0x1ec+0x698]==bytes(0x698)
    with FILES['liro'][0].open('rb') as f:
        liro=ELFFile(f)
        assert liro.header['e_machine']=='EM_AARCH64' and liro.header['e_type']=='ET_REL'
        init=liro.get_section_by_name('.init.text');table=liro.get_section_by_name('.init.data')
        assert init['sh_offset']==0x9e90 and table['sh_offset']==0xc130 and table['sh_size']==0x698
        init_bytes=init.data();table_bytes=table.data()
        magic=insns(init_bytes,0x338,0x40)
        copy=insns(init_bytes,0x4b0,0x38)
        assert 'mov w2, #0x524f' in magic[1]['asm'] and 'movk w2, #0x4c49' in magic[2]['asm']
        assert any('cmp w1, #5' in i['asm'] for i in magic)
        assert [i['asm'] for i in copy[:6]]==[
            'ldr x20, [x19, #0x50]','ldr x1, #0x598','mov x2, #0x698',
            'ldr x0, [x20, #0x20]','add x0, x0, #0x48','bl #0x4c4']
        assert section_reloc(liro,'.rela.init.text',0x598)['symbol']=='.init.data'
        assert section_reloc(liro,'.rela.init.text',0x4c4)['symbol']=='memcpy'
        slots={}
        for slot in (0x3c0,0x3e8,0x4c0):
            src=slot-0x48
            r=section_reloc(liro,'.rela.init.data',src)
            assert r['type_number']==257 and src+8<=table['sh_size']
            slots[hex(slot)]={'source_section_offset':hex(src),
                              'source_file_offset':hex(table['sh_offset']+src),
                              'original_unrelocated_qword':hex(struct.unpack_from('<Q',table_bytes,src)[0]),
                              'relocation':r,
                              'av_destination_file_offset':hex(0x1a4+slot),
                              'av_destination_va':hex(BASE_AV+0x1a4+slot)}
        assert slots['0x3c0']['relocation']['symbol']=='.text' and slots['0x3c0']['relocation']['addend']=='0xc28'
        assert slots['0x3e8']['relocation']['symbol']=='osal_free_msg'
        assert slots['0x4c0']['relocation']['symbol']=='Backup_nread'
        wrapper=liro.get_section_by_name('.text').data()[0xc28:0xc74]
        assert section_reloc(liro,'.rela.text',0xc54)['symbol']=='osal_rcv_msg_tmo'
        liro_evidence={'module_sha256':FILES['liro'][1],
            'modinfo_parameter_bytes':{k:hex(data['liro'].find(k.encode())) for k in
                                       ('parmtype=fn:string','parmtype=load:int','parmtype=debug:int')},
            'init_section_file_offset':hex(init['sh_offset']),
            'firmware_file_load':{'section_range':'0x200..0x338',
                'file_range':f"{hex(init['sh_offset']+0x200)}..{hex(init['sh_offset']+0x338)}",
                'original_bytes_sha256':sha256(init_bytes[0x200:0x338]).hexdigest(),
                'original_instructions':insns(init_bytes,0x200,0x138),
                'call_relocations':{hex(o):section_reloc(liro,'.rela.init.text',o)
                                    for o in (0x294,0x2cc,0x314,0x324)},
                'scope':'liro original code opens fn path, reads into configured memory, closes and flushes instruction cache; runtime filename/load address not observed'},
            'ORIL_version_check':{'section_offset':'0x338','file_offset':hex(init['sh_offset']+0x338),
                                  'original_instructions':magic},
            'provider_table_copy':{'section_offset':'0x4b0','file_offset':hex(init['sh_offset']+0x4b0),
                'original_instructions':copy,'source_literal_relocation':section_reloc(liro,'.rela.init.text',0x598),
                'memcpy_call_relocation':section_reloc(liro,'.rela.init.text',0x4c4),
                'source_section':'.init.data','source_file_offset':hex(table['sh_offset']),
                'length':0x698,'destination':'*(loaded_AV_base+0x20)+0x48',
                'post_copy_entry':'0x4d4 loads [AV+0x10], 0x4e0 BLR x1'},
            'slots':slots,'event_wrapper':{'section_offset':'0xc28','file_offset':hex(liro.get_section_by_name('.text')['sh_offset']+0xc28),
                'bytes_sha256':sha256(wrapper).hexdigest(),
                'original_instructions':insns(liro.get_section_by_name('.text').data(),0xc28,0x4c),
                'call_relocations':{hex(o):section_reloc(liro,'.rela.text',o) for o in (0xc44,0xc54,0xc5c)}}}
    assert all(v>=0 for v in [int(x,16) for x in liro_evidence['modinfo_parameter_bytes'].values()])
    with FILES['fx6_im'][0].open('rb') as f:
        elf=ELFFile(f)
        assert elf.header['e_machine']=='EM_AARCH64' and elf.header['e_type']=='ET_EXEC'
    assert data['fx6_im'][0x7df6:0x7df6+len(b'fn=/system/av-cam.bin load=1 debug=1')]==b'fn=/system/av-cam.bin load=1 debug=1'
    im={'file_sha256':FILES['fx6_im'][1],
        'parameter_literal_file_offset':'0x7df6','parameter_literal_elf_va':'0x407df6',
        'wrapper_argument_flow':insns(data['fx6_im'],0x6134,0xb4,0x400000),
        'type_dispatch':insns(data['fx6_im'],0x61ec,0x78,0x400000),
        'module_load':insns(data['fx6_im'],0x6040,0xf4,0x400000),
        'interpretation':'0x406134 receives x0 module pathname and x1 parameter string; snprintf includes av-cam fn literal, then 0x406040 passes mapped module bytes to syscall(105) with parameter string, not av-cam as module image'}
    exported={
        'osal_rcv_msg_tmo':defined_export(FILES['osal_uipc'][0],'osal_rcv_msg_tmo'),
        'osal_free_msg':defined_export(FILES['osal_uipc'][0],'osal_free_msg'),
        'Backup_nread':defined_export(FILES['backup'][0],'Backup_nread')}
    fx3_exported={
        'osal_rcv_msg_tmo':defined_export(FILES['fx3_osal_uipc'][0],'osal_rcv_msg_tmo'),
        'osal_free_msg':defined_export(FILES['fx3_osal_uipc'][0],'osal_free_msg'),
        'Backup_nread':defined_export(FILES['fx3_backup'][0],'Backup_nread')}
    assert exported['osal_rcv_msg_tmo']['original_bytes_sha256']==fx3_exported['osal_rcv_msg_tmo']['original_bytes_sha256']
    assert exported['osal_free_msg']['original_bytes_sha256']==fx3_exported['osal_free_msg']['original_bytes_sha256']
    assert exported['Backup_nread']['original_bytes_sha256']!=fx3_exported['Backup_nread']['original_bytes_sha256']
    with FILES['fx3_liro'][0].open('rb') as f:
        old=ELFFile(f)
        assert old.header['e_machine']=='EM_AARCH64' and old.header['e_type']=='ET_REL'
        old_init=old.get_section_by_name('.init.text').data()
        old_text=old.get_section_by_name('.text').data()
        old_data=old.get_section_by_name('.init.data').data()
        assert old_init[0x338:0x380]==init_bytes[0x338:0x380]
        assert old_init[0x4b0:0x4e4]==init_bytes[0x4b0:0x4e4]
        assert old_text[0xc28:0xc74]==wrapper and old_data==table_bytes
        for off in (0x378,0x3a0,0x478):
            assert section_reloc(old,'.rela.init.data',off)==slots[hex(off+0x48)]['relocation']
        fx3_comparison={'fx3_liro_sha256':FILES['fx3_liro'][1],
            'same_ORIL_check_bytes_sha256':sha256(old_init[0x338:0x380]).hexdigest(),
            'same_provider_copy_bytes_sha256':sha256(old_init[0x4b0:0x4e4]).hexdigest(),
            'same_receive_wrapper_bytes_sha256':sha256(old_text[0xc28:0xc74]).hexdigest(),
            'same_unrelocated_init_data_sha256':sha256(old_data).hexdigest(),
            'same_three_relocation_target_symbols':True,
            'scope':'same source ABI implementation bytes and target symbol names; runtime module addresses/load order and Backup data remain model-local'}
    with FILES['backup'][0].open('rb') as f:
        backup_elf=ELFFile(f);backup_text=backup_elf.get_section_by_name('.text')
        backup_calls={hex(off):section_reloc(backup_elf,'.rela.text',off)
                      for off in (0x1cd8,0x1cf8,0x728,0x734,0x75c,0x790)}
        assert backup_calls['0x728']['symbol']=='Data_SearchId'
        assert backup_calls['0x734']['symbol']=='Data_GetSize'
        assert backup_calls['0x75c']['symbol']=='Data_GetDataPt'
        backup_flow={'nread_entry':{'section_offset':'0x1ca8',
                       'file_offset':hex(backup_text['sh_offset']+0x1ca8),
                       'original_instructions':insns(backup_text.data(),0x1ca8,0x68)},
                     'internal_read_entry':{'section_offset':'0x700',
                       'file_offset':hex(backup_text['sh_offset']+0x700),
                       'original_instructions':insns(backup_text.data(),0x700,0xe0)},
                     'call_relocations':backup_calls,
                     'scope':'Backup_nread takes read lock and calls local read path; Data_SearchId/GetSize/GetDataPt are original backup module functions; value for 0x2ae0000 remains runtime data'}
    output={'pins':{k:v[1] for k,v in FILES.items()},'fx6_av':{
        'base':hex(BASE_AV),'ORIL_magic_file_offset':'0x8','header_provider_qword_file_offset':'0x20',
        'header_original_provider_va':hex(BASE_AV+0x1a4),
        'provider_copy_destination_file_offset':'0x1ec','provider_copy_target_original_zeros':True},
        'kernel':kernel_chain(image),'im':im,'liro':liro_evidence,
        'provider_function_definitions_and_exports':exported,
        'fx3_liro_field_comparison':fx3_comparison,
        'fx3_provider_function_comparison':{'fx3_pins':{k:FILES[k][1] for k in ('fx3_osal_uipc','fx3_backup')},
            'definitions_and_exports':fx3_exported,
            'osal_receive_and_free_original_function_bytes_identical':True,
            'backup_nread_original_function_bytes_identical':False,
            'scope':'same callback slot and exported name ABI; backup read code/data and runtime state are model-specific'},
        'backup_word_read_flow':backup_flow,
        'runtime_module_addresses':'unknown; ET_REL sections relocated at load, section offsets are not runtime VA',
        'scope':'static original code/data/relocation chain; no module loaded, no natural event or Backup result observed'}
    (HERE/'binding-evidence.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':'STATIC_PROVIDER_CHAIN_CLOSED','slots':{
        k:v['relocation']['symbol'] for k,v in slots.items()},'kernel_symbols':image.count,
        'runtime_module_addresses_known':False}))


if __name__=='__main__':main()
