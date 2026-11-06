#!/usr/bin/env python3
"""Read-only original provider/LIRO relocation/provider-symbol provenance."""
import datetime
import io
import json
import struct
from elftools.elf.elffile import ELFFile
import manager_factory as f


def main():
    f.im.volume();out=f.STAGE/'provider-source-audit.json';assert not out.exists()
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert f.im.sha(blob)==f.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    base=struct.unpack_from('<Q',blob,0x20)[0];assert base==f.V+0x1a4
    liro=f.n.STAGE/'official-files/nflasha15/kmod/liro.ko'
    elf=ELFFile(io.BytesIO(liro.read_bytes()));sy=elf.get_section_by_name('.symtab')
    rels={x['r_offset']:x for x in elf.get_section_by_name('.rela.init.data').iter_relocations()}
    table=[(0x2f028,0x3e0,'osal_valloc_msg_wait'),(0x2efb0,0x3b0,'osal_snd_sync_msg'),
      (0x2f03c,0x3e8,'osal_free_msg'),(0x2f0a0,0x410,'osal_set_msg_src')]
    imports=[]
    for veneer,disp,name in table:
        off=base+disp-(f.V+0x1ec);rel=rels[off];symbol=sy.get_symbol(rel['r_info_sym'])
        assert rel['r_info_type']==257 and rel['r_addend']==0 and symbol.name==name
        imports.append({'veneer_offset':hex(veneer),'table_displacement':hex(disp),
          'actual_guest_import_slot':hex(base+disp),'LIRO_init_data_relocation_offset':hex(off),
          'symbol':name,'instructions':f.im.dump(blob,veneer,veneer+20,f.V),
          'runtime_binding_or_execution_in_current_model':False})
    provider=f.n.STAGE/'official-files/nflasha15/kmod/osal_uipc.ko'
    old=json.loads((f.n.STAGE/'final-receipt.json').read_text())
    relpath=str(provider.relative_to(f.ROOT));sha=f.im.sha(provider.read_bytes())
    assert any(x['path']==relpath and x['sha256']==sha for x in old['files'])
    mod=ELFFile(io.BytesIO(provider.read_bytes()));definitions=[]
    for symbol in mod.get_section_by_name('.symtab').iter_symbols():
        if symbol.name not in {x[2] for x in table} or symbol['st_shndx']=='SHN_UNDEF':continue
        sec=mod.get_section(symbol['st_shndx']);assert sec.name=='.text'
        definitions.append({'symbol':symbol.name,'section':sec.name,
          'section_value':hex(symbol['st_value']),'size':symbol['st_size'],
          'not_a_runtime_loaded_address':True})
    assert len(definitions)==4
    regions=[('resource provider, unexecuted',0x27bdb4,0x27bec8),
      ('message wrapper, unexecuted',0x27bec8,0x27bf90),
      ('message dispatcher body, unexecuted',0x99004,0x99288),
      ('actual singleton constructor relation, unexecuted',0x22a680,0x22a6c4)]
    f.im.write_json(out,{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'STATIC_RESOURCE_PROVIDER_TO_OSAL_MESSAGE_IMPORTS_ONLY',
      'avcam_sha256':f.im.sha(blob),'LIRO_sha256':f.im.sha(liro.read_bytes()),
      'provider_module':relpath,'provider_module_sha256':sha,'table_base_from_original_header':hex(base),
      'slot_calculation':'Original header table base+veneer displacement minus copied-vector start1ec; do not equate veneer displacement with LIRO relocation offset.',
      'imports':imports,'provider_definitions':definitions,
      'regions':[{'name':name,'instructions':f.im.dump(blob,a,z,f.V)} for name,a,z in regions],
      'executed_actual_provider_OSAL_threads_memory_allocator_sync_message_or_Hal':False,
      'next_scope':'Resolve actual original osal_uipc module relocations and dependency/initialization boundary. No fabricated allocation, reply, thread or current-task state.'})
    print(json.dumps({'status':'STATIC_RESOURCE_PROVIDER_TO_OSAL_MESSAGE_IMPORTS_ONLY','imports':4,'definitions':4}))


if __name__=='__main__':main()
