#!/usr/bin/env python3
"""Correlate selected vendor USB source and original7.02 module/template data."""
from pathlib import Path
import datetime
import io
import json
import sys
import tarfile
from elftools.elf.elffile import ELFFile

STAGE = Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume()
    extraction = json.loads((STAGE/'usb-original-extraction.json').read_text())
    for row in extraction['files']:
        assert h.im.sha((h.ROOT/row['output']).read_bytes()) == row['sha256']
    package = STAGE/'official-files/nflasha15'
    raw = (package/'lib/libInfraUsbCmn.so').read_bytes()
    elf = ELFFile(io.BytesIO(raw))
    syms = elf.get_section_by_name('.dynsym')
    symbols = {s.name:s for s in syms.iter_symbols() if s.name.startswith('INQUIRY_DATA_')}
    assert len(symbols) == 8
    def data(symbol):
        va,size = symbol['st_value'],symbol['st_size']
        seg = [s for s in elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+size<=s['p_vaddr']+s['p_filesz']]
        assert len(seg)==1
        off = seg[0]['p_offset']+va-seg[0]['p_vaddr']
        return raw[off:off+size]
    tables,aliases = [],[]
    for name,symbol in symbols.items():
        blob = data(symbol)
        if len(blob)==8:
            rows = [(sec,r) for sec in elf.iter_sections() if sec['sh_type']=='SHT_RELA'
                    for r in sec.iter_relocations() if r['r_offset']==symbol['st_value']]
            assert len(rows)==1 and rows[0][1]['r_info_type']==257 and rows[0][1]['r_addend']==0
            target = syms.get_symbol(rows[0][1]['r_info_sym'])
            assert target.name=='INQUIRY_DATA_DEFAULT'
            aliases.append({'name':name,'size':8,'initial_bytes':blob.hex(),'relocation':'R_AARCH64_ABS64',
                            'static_ELF_target':target.name,'runtime_interposition_not_observed':True})
        else:
            assert len(blob)>=36 and blob[0]==0 and blob[8:16]==b'Sony    ' and blob[16:32]==b' '*16 and blob[32:36]==b'1.00'
            tables.append({'name':name,'ELF_symbol_value':hex(symbol['st_value']),'bytes':len(blob),
                           'sha256':h.im.sha(blob),'peripheral_type':blob[0]&31,
                           'additional_length':blob[4],'vendor':'Sony','initial_product':'blank spaces',
                           'initial_revision':'1.00','actual_runtime_reply_not_observed':True})
    assert len(tables)==3 and len(aliases)==5
    module_raw = (package/'kmod/usbg_storage.ko').read_bytes()
    module = ELFFile(io.BytesIO(module_raw))
    symtab = module.get_section_by_name('.symtab')
    functions = []
    for name,size,called in (('inquiry_std',632,['memcpy']),('checkExtCommand',152,['storage_detect_ExtCommand']),
                             ('storage_detect_ExtCommand',80,['usb_event_add_queue'])):
        candidates = [s for s in symtab.iter_symbols() if s.name==name]
        assert len(candidates)==1
        symbol = candidates[0]
        assert symbol['st_size']==size
        rels = [r for sec in module.iter_sections() if sec['sh_type']=='SHT_RELA' and sec['sh_info']==symbol['st_shndx']
                for r in sec.iter_relocations() if symbol['st_value']<=r['r_offset']<symbol['st_value']+size and r['r_info_type']==283]
        calls = [{'offset':hex(r['r_offset']),'symbol':symtab.get_symbol(r['r_info_sym']).name,'addend':r['r_addend']} for r in rels]
        assert [x['symbol'] for x in calls]==called
        instructions = module.get_section(symbol['st_shndx']).data()[symbol['st_value']:symbol['st_value']+size]
        functions.append({'name':name,'section':module.get_section(symbol['st_shndx']).name,
                          'section_offset':hex(symbol['st_value']),'bytes':size,'sha256':h.im.sha(instructions),
                          'CALL26_relocations':calls,'executed':False})
    archive = h.STAGE/'work/vendor-source-reference/range-resume-20261026/linux-kernel.complete.tar.gz'
    assert h.im.sha(archive.read_bytes())=='bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
    selected = {
        'include/uapi/linux/usb/specific_gadget/usbg_storage.h':[(33,64),(89,92)],
        'drivers/usb/gadget/specific_gadget/usbg_storage/usbg_storage_cmd_std.c':[(313,356),(3093,3119)],
    }
    sources = []
    with tarfile.open(archive,'r:gz') as tar:
        for name,ranges in selected.items():
            info = tar.getmember('linux-kernel/'+name)
            assert info.isfile() and info.size<200000
            blob = tar.extractfile(info).read()
            lines = blob.splitlines()
            # Japanese comments are not assumed UTF8. Preserve exact member hash;
            # ASCII identifiers are read losslessly, other bytes rendered as escapes.
            excerpts = [[i+1,lines[i].decode('ascii',errors='backslashreplace')]
                        for lo,hi in ranges for i in range(lo-1,hi)]
            sources.append({'member':name,'bytes':len(blob),'sha256':h.im.sha(blob),'excerpts':excerpts})
    result = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'script_sha256':h.im.sha(Path(__file__).read_bytes()),
              'original_components':str((STAGE/'usb-original-extraction.json').relative_to(h.ROOT)),
              'static_inquiry_templates':tables,'static_pointer_aliases':aliases,'original_functions':functions,
              'public_source_label':'FX3 7.00; selected correspondence only, not exact7.02 build proof',
              'source_archive_sha256':h.im.sha(archive.read_bytes()),'selected_source':sources,
              'correlations':[
                  'Reference standard EVPD0 INQUIRY copies bounded per-drive configured inquiryData; original7.02 inquiry_std has one CALL26 relocation to memcpy.',
                  'Three initial byte-array templates have revision1.00 and blank product; five eight-byte data symbols are ABS64 aliases to DEFAULT, not five extra response headers.',
                  'Reference init structure supplies num and per-drive information, and extension event explicitly carries lun. One USB parent does not specify a unique logical-unit endpoint.',
              ],
              'next_action_constraints':[
                  'Do not interpret a standard INQUIRY revision as proof of firmware7.02 or a same-body program hash.',
                  'Do not choose one among multiple current disk interfaces from common vendor/product/revision data alone.',
                  'Current active driver, dynamic initialization/product data, target LUN and actual reply remain unverified.',
              ],
              'camera_interface_auth_mode_driver_media_or_firmware_access':False,
              'downloaded_source_original_modules_or_kernel_executed':False,
              'goal_complete':False,'persistent_write_release':False}
    h.im.write_json(STAGE/'usb-inquiry-source-correlation.json',result)
    print(json.dumps({'templates':len(tables),'pointer_aliases':len(aliases),'original_functions':len(functions),
                      'initial_revision':'1.00','actual_driver_or_reply_observed':False,'camera_operations':False}))


if __name__=='__main__':
    main()
