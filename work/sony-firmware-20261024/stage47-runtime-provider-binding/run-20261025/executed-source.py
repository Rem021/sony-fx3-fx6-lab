#!/usr/bin/env python3
"""Bind original LIRO loader imports to av-cam ABI; bounded fragments only.

Original loader header checks/copy-argument setup and uninitialized av-cam
veneers execute in a guest. Local ABS64 literal relocations use declared section
bases. No kernel service/log/memcpy, module init, binding injection or fake output.
"""
from pathlib import Path
import argparse
import datetime
import io
import json
import struct
import sys
import traceback

from elftools.elf.elffile import ELFFile

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/sony-firmware-20261024'
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'stage26-mc-open-routing'))
import mc_open_routing as r
im,V=r.im,r.V
CODE=0x14000000
STRINGS=0x14010000
INITDATA=0x14020000
CONTEXT=r.ARENA+0x1000
HEADER=r.ARENA+0x300000
IMPORTS=[(0x2ef4c,0x388,'osal_wai_sem_tmo','x2'),(0x2ef60,0x390,'osal_sig_sem','x1'),
 (0x2f604,0x698,'pciatu_unmap','x1'),(0x2f67c,0x6b8,'memset','x3')]


def module_facts(raw):
    elf=ELFFile(io.BytesIO(raw));assert elf['e_type']=='ET_REL' and elf['e_machine']=='EM_AARCH64'
    syms=elf.get_section_by_name('.symtab')
    table=elf.get_section_by_name('.init.data');assert table['sh_size']==0x698
    providers={}
    for rel in elf.get_section_by_name('.rela.init.data').iter_relocations():
        assert rel['r_info_type']==257
        sym=syms.get_symbol(rel['r_info_sym'])
        providers[rel['r_offset']]={'symbol':sym.name,'symbol_section':sym['st_shndx'],
          'symbol_value':hex(sym['st_value']),'addend':hex(rel['r_addend']),'relocation_type':257}
    for _,slot,name,_ in IMPORTS:assert providers[slot-0x48]['symbol']==name
    text=bytearray(elf.get_section_by_name('.init.text').data());original=bytes(text)
    literals=[]
    relocs={rel['r_offset']:rel for rel in elf.get_section_by_name('.rela.init.text').iter_relocations()}
    for at in (0x570,0x578,0x580,0x598):
        rel=relocs[at];assert rel['r_info_type']==257;sym=syms.get_symbol(rel['r_info_sym'])
        section=elf.get_section(sym['st_shndx']).name
        assert section in ('.rodata.str1.8','.init.data')
        base=STRINGS if section=='.rodata.str1.8' else INITDATA
        value=base+sym['st_value']+rel['r_addend'];struct.pack_into('<Q',text,at,value)
        literals.append({'section_offset':hex(at),'target_section':section,'addend':hex(rel['r_addend']),
          'relocated_fixture_value':hex(value),'relocation_type':257})
    changes={i for i,(a,b) in enumerate(zip(original,text)) if a!=b}
    assert changes<={i for at in (0x570,0x578,0x580,0x598) for i in range(at,at+8)}
    assert original[0x338:0x38c]==text[0x338:0x38c] and original[0x4b0:0x4c8]==text[0x4b0:0x4c8]
    return elf,bytes(text),providers,literals


class Guest(r.RawGuest):
    def __init__(self,blob,module):
        super().__init__(blob,[],{})
        elf,text,self.providers,self.literal_relocations=module_facts(module)
        self.ranges.extend([(CODE+0x338,CODE+0x38c),(CODE+0x4b0,CODE+0x4c8)])
        self.boundaries.update({CODE+0x354:'before_magic_mismatch_diagnostic',
          CODE+0x370:'before_version_mismatch_diagnostic',CODE+0x388:'after_header_acceptance_before_diagnostic',
          CODE+0x4c4:'before_unexecuted_kernel_memcpy'})
        for at,_,name,_ in IMPORTS:
            self.ranges.append((V+at,V+at+20));self.boundaries[V+at+16]='before_unbound_indirect_'+name
        for address,data in ((CODE,text),(STRINGS,elf.get_section_by_name('.rodata.str1.8').data()),
          (INITDATA,elf.get_section_by_name('.init.data').data())):
            self.uc.mem_map(address,(len(data)+4095)&~4095,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
            self.uc.mem_write(address,data)


def phase(m,label,address,**regs):
    m.reason=None;m.pcs=[];m.writes=[];m.regs(sp=r.SP,x30=r.STOP);m.regs(**regs)
    m.uc.emu_start(address,0,count=2000,timeout=100000)
    assert m.reason is not None
    return {'label':label,'start_pc':hex(address),'stop_pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
      'reason':m.reason,'pcs':[hex(pc) for pc in m.pcs],'writes':m.writes,
      'x0_to_x5':[hex(m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in range(6)],
      'native_output_or_runtime_adapter':False}


def header_cases(blob,module):
    cases=[]
    for name,magic,version,end in [('original',0x4c49524f,5,'after_header_acceptance_before_diagnostic'),
      ('bad_magic',0,5,'before_magic_mismatch_diagnostic'),('bad_version',0x4c49524f,6,'before_version_mismatch_diagnostic')]:
        m=Guest(blob,module);header=bytearray(blob[:0x58]);struct.pack_into('<II',header,8,magic,version)
        m.uc.mem_write(HEADER,bytes(header));m.uc.mem_write(CONTEXT+0x50,r.p64(HEADER))
        event=phase(m,'original loader header-check fragment '+name,CODE+0x338,x19=CONTEXT)
        assert event['reason']=='boundary: '+end
        assert im.sha(m.read(V,len(blob)))==im.sha(blob)
        cases.append({'case':name,'magic_u32':hex(magic),'version_u32':version,'original_fragment':event,
          'scope':'Independent loader fragment0x338 with declared module-context/header fixture; diagnostics/full cleanup/loading not executed.'})
    return cases


def copy_arguments(blob,module):
    m=Guest(blob,module);m.uc.mem_write(CONTEXT+0x50,r.p64(V))
    event=phase(m,'original loader import-vector copy argument setup',CODE+0x4b0,x19=CONTEXT)
    assert event['reason']=='boundary: before_unexecuted_kernel_memcpy'
    assert event['x0_to_x5'][:3]==[hex(V+0x1ec),hex(INITDATA),'0x698']
    assert m.read(V+0x1ec,0x698)==bytes(0x698)
    assert im.sha(m.read(V,len(blob)))==im.sha(blob)
    return {'original_fragment':event,'source_section':'.init.data','destination':'av-cam header[0x20]+0x48',
      'length':0x698,'slot_count':0x698//8,'avcam_destination_unchanged':True,
      'source_function_addresses_unresolved':True,'actual_memcpy_or_runtime_binding_executed':False,
      'literal_relocations':m.literal_relocations}


def veneer_cases(blob,module):
    cases=[]
    for at,slot,name,target in IMPORTS:
        m=Guest(blob,module);event=phase(m,'original av-cam uninitialized veneer '+name,V+at,
          x0=r.ARENA+0x10000,x1=0,x2=0x58)
        assert event['reason']=='boundary: before_unbound_indirect_'+name
        assert m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_'+target.upper()))==0
        assert m.read(V+0x1a4+slot,8)==bytes(8)
        provider=m.providers[slot-0x48]
        cases.append({'veneer_offset':hex(at),'API_offset':hex(slot),'raw_file_slot_offset':hex(0x1a4+slot),
          'loader_vector_offset':hex(slot-0x48),'provider_relocation':provider,'branch_register':target,
          'original_fragment':event,'uninitialized_target':0,
          'actual_runtime_service_address_or_effect_unverified':True})
    return cases


def run(out):
    prior=BASE/'stage46-upstream-restore-audit/final-receipt.json'
    assert im.sha(prior.read_bytes())=='ed3e73134be9b4da9b7a6c035c52c1043e11e69396340e2426405eb0d5f679b6'
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    for row in json.loads((STAGE/'official-extraction-receipt.json').read_text())['files']:
        assert im.sha(Path(row['output']).read_bytes())==row['sha256']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    elf,text,providers,literals=module_facts(module)
    heads=header_cases(blob,module);copy=copy_arguments(blob,module);veneers=veneer_cases(blob,module)
    code=elf.get_section_by_name('.init.text').data()
    source_regions=[{'name':name,'instructions':im.dump(code,lo,hi,0)} for name,lo,hi in (
      ('original magic and version checks',0x338,0x38c),('original vector-copy and app entry order',0x4b0,0x4e4))]
    # Validate the call/literal relocation evidence, not merely opcode labels.
    syms=elf.get_section_by_name('.symtab');relocs={rel['r_offset']:rel for rel in elf.get_section_by_name('.rela.init.text').iter_relocations()}
    assert syms.get_symbol(relocs[0x4c4]['r_info_sym']).name=='memcpy'
    assert syms.get_symbol(relocs[0x598]['r_info_sym'])['st_shndx']==25
    assert relocs[0x4c4]['r_info_type']==283 and relocs[0x598]['r_info_type']==257
    traces=[x['original_fragment'] for x in heads]+[copy['original_fragment']]+[x['original_fragment'] for x in veneers]
    proof={'status':'PASS_ORIGINAL_LIRO_HEADER_AND_IMPORT_PROVIDER_BINDING_WITHIN_OFFLINE_FRAGMENT_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'header_cases':heads,
      'loader_copy_arguments':copy,'veneer_cases':veneers,'source_regions':source_regions,
      'loader_init_data_relocations':[{'offset':hex(k),**v} for k,v in sorted(providers.items())],
      'kernel_module_vermagic':elf.get_section_by_name('.modinfo').data().split(b'vermagic=')[1].split(b'\0')[0].decode(),
      'original_fragments':len(traces),'original_guest_store_count':sum(len(x['writes']) for x in traces),
      'raw_clear_slot_correct_offset':'0x85c','instruction_literals_relocated_only_at':[x['section_offset'] for x in literals],
      'loader_version_field5_bound_not_inferred_segment_count':True,
      'kernel_symbol_implementation_addresses_full_runtime_init_or_lock_semantics_bound':False,
      'no_substitute_memset_or_mock_service_return':True,'camera_or_remote_operation':False,
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'provider-binding-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'image_sha256':im.sha(blob),'liro_module_sha256':im.sha(module),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME,
      'proof_sha256':im.sha((out/'provider-binding-results.json').read_bytes())})
    print(json.dumps({k:proof[k] for k in ('status','original_fragments','original_guest_store_count',
      'kernel_symbol_implementation_addresses_full_runtime_init_or_lock_semantics_bound','goal_complete','persistent_write_release')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
