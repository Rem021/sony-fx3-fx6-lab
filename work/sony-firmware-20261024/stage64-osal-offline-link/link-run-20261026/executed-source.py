#!/usr/bin/env python3
"""Relocate original modules in declared guest RAM only; no ELF export/load.

Kernel exports are static original candidates with validated names/neighbors.
NOBITS zeros are ELF initial storage, not a running Linux service or task state.
"""
from pathlib import Path
import argparse
import collections
import datetime
import io
import json
import struct
import sys
from elftools.elf.elffile import ELFFile

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage63-resource-message-boundary'))
import resource_message as prev
import osal_dependency_audit as audit
r,im,V,n=prev.r,prev.im,prev.V,prev.n
PRIOR_SHA='00b90d920f98eea8277cfa5303d2bc8bbfb290e5aac6a771a97f340632b57282'
BLOCKS={'devno.ko':n.K+0x2000000,'osal_utm.ko':n.K+0x2100000,'osal_uipc.ko':n.K+0x2200000}


def align(value,alignment):
    assert alignment>0 and alignment&(alignment-1)==0
    return (value+alignment-1)&-alignment


class Module:
    def __init__(self,path):
        self.path=path;self.raw=path.read_bytes();self.elf=ELFFile(io.BytesIO(self.raw))
        assert self.elf['e_type']=='ET_REL' and self.elf['e_machine']=='EM_AARCH64'
        assert self.elf.elfclass==64 and self.elf.little_endian
        self.syms=self.elf.get_section_by_name('.symtab')
        self.block=BLOCKS[path.name];cursor=self.block;self.sections={}
        for index,sec in enumerate(self.elf.iter_sections()):
            if not sec['sh_flags']&2:continue
            cursor=align(cursor,max(4096,sec['sh_addralign'] or 1))
            assert sec['sh_type'] in ('SHT_PROGBITS','SHT_NOTE','SHT_NOBITS')
            size=sec['sh_size'];raw=bytes(size) if sec['sh_type']=='SHT_NOBITS' else sec.data()
            assert len(raw)==size
            self.sections[index]={'index':index,'name':sec.name,'base':cursor,'size':size,
              'mapped_size':align(size,4096) if size else 0,'flags':sec['sh_flags'],
              'type':sec['sh_type'],'original':raw,'data':bytearray(raw)}
            cursor+=align(size,4096)
        assert cursor<=self.block+0x100000
        self.exports={}
        for name,record in audit.exports(self.elf,self.syms).items():
            sym=[s for s in self.syms.iter_symbols() if s.name==name and isinstance(s['st_shndx'],int)]
            assert len(sym)==1 and sym[0]['st_shndx'] in self.sections
            self.exports[name]={'address':self.defined(sym[0]),'record':record}
        self.relocations=[];self.resolutions={}

    def defined(self,symbol):
        index=symbol['st_shndx'];value=symbol['st_value']
        if index=='SHN_ABS':return value
        assert isinstance(index,int) and index in self.sections,(symbol.name,index)
        section=self.sections[index]
        assert 0<=value<=section['size'] and value+symbol['st_size']<=section['size']
        return section['base']+value

    def address(self,name):
        symbols=[s for s in self.syms.iter_symbols() if s.name==name and isinstance(s['st_shndx'],int)]
        assert len(symbols)==1,name
        return self.defined(symbols[0])

    def section(self,name):
        sections=[s for s in self.sections.values() if s['name']==name]
        assert len(sections)==1;return sections[0]

    def relocate(self,resolve):
        used=collections.defaultdict(set)
        for relsec in self.elf.iter_sections():
            if relsec['sh_type']!='SHT_RELA':continue
            target_index=relsec['sh_info']
            assert target_index in self.sections,'No unmodeled relocation target section'
            target=self.sections[target_index]
            for rel in relsec.iter_relocations():
                sym=self.syms.get_symbol(rel['r_info_sym']);off=rel['r_offset'];kind=rel['r_info_type']
                addend=rel['r_addend'];place=target['base']+off
                if sym['st_shndx']=='SHN_UNDEF':
                    assert sym.name
                    resolution=resolve(sym.name);value=resolution['address']
                    self.resolutions[sym.name]=resolution
                else:value=self.defined(sym)
                absolute=value+addend;delta=absolute-place
                assert 0<=absolute<1<<64
                width=8 if kind==257 else 4
                assert kind in (257,261,283) and 0<=off and off+width<=target['size']
                assert not used[target_index]&set(range(off,off+width))
                used[target_index].update(range(off,off+width))
                original=bytes(target['data'][off:off+width])
                if kind==257:
                    new=struct.pack('<Q',absolute)
                    assert struct.unpack('<Q',new)[0]==absolute
                elif kind==261:
                    assert -(1<<31)<=delta<(1<<31)
                    new=struct.pack('<i',delta)
                    assert place+struct.unpack('<i',new)[0]==absolute
                else:
                    word=struct.unpack('<I',original)[0]
                    assert word&0xfc000000==0x94000000 and delta%4==0 and -(1<<27)<=delta<(1<<27)
                    new=struct.pack('<I',(word&0xfc000000)|((delta//4)&0x3ffffff))
                    encoded=struct.unpack('<I',new)[0]&0x3ffffff
                    if encoded&(1<<25):encoded-=1<<26
                    assert place+encoded*4==absolute
                target['data'][off:off+width]=new
                self.relocations.append({'section':target['name'],'offset':hex(off),'type':kind,
                  'symbol':sym.name,'symbol_section':sym['st_shndx'],'addend':addend,
                  'S':hex(value),'P':hex(place),'S_plus_A':hex(absolute),
                  'original_hex':original.hex(),'relocated_hex':new.hex()})
        for index,section in self.sections.items():
            assert {i for i,(a,b) in enumerate(zip(section['original'],section['data'])) if a!=b}<=used[index]

    def facts(self):
        return {'path':str(self.path.relative_to(ROOT)),'sha256':im.sha(self.raw),'block_fixture':hex(self.block),
          'sections':[{'index':s['index'],'name':s['name'],'base':hex(s['base']),'size':s['size'],
            'mapped_size':s['mapped_size'],'flags':s['flags'],'type':s['type'],
            'original_sha256':im.sha(s['original']),'relocated_sha256':im.sha(bytes(s['data']))}
            for s in self.sections.values()],
          'exports':{k:{'address':hex(v['address']),'record':v['record']} for k,v in self.exports.items()},
          'undefined_resolutions':{k:{**v,'address':hex(v['address'])} for k,v in self.resolutions.items()},
          'relocation_counts':dict(collections.Counter(x['type'] for x in self.relocations)),
          'relocations':self.relocations}


def build():
    prior=prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for x in json.loads(prior.read_text())['files']:assert im.sha((ROOT/x['path']).read_bytes())==x['sha256']
    paths=[prev.STAGE/'official-files/nflasha7/kmod/devno.ko',
      n.STAGE/'official-files/nflasha15/kmod/osal_utm.ko',n.STAGE/'official-files/nflasha15/kmod/osal_uipc.ko']
    oldfiles={x['path']:x['sha256'] for x in json.loads((n.STAGE/'final-receipt.json').read_text())['files']}
    ex=json.loads((prev.STAGE/'devno-extraction.json').read_text())
    for path in paths:
        expected=ex['sha256'] if path.name=='devno.ko' else oldfiles[str(path.relative_to(ROOT))]
        assert im.sha(path.read_bytes())==expected
    modules={p.name:Module(p) for p in paths}
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assert im.sha(kernel)==oldfiles[str((n.STAGE/'official-files/nflasha3/vmlinux.bin').relative_to(ROOT))]
    cache={}
    def resolve(name):
        if name in cache:return cache[name]
        mod=[(m,e) for m in modules.values() for label,e in m.exports.items() if label==name]
        candidates=audit.export_candidates(kernel,name)
        assert len(mod)+len(candidates)==1,('unresolved/ambiguous',name,len(mod),len(candidates))
        if mod:
            module,export=mod[0]
            value={'kind':'original_module_export','module':module.path.name,'address':export['address']}
        else:
            candidate=candidates[0]
            value={'kind':'original_kernel_export_candidate','address':int(candidate['value'],16),
              'candidate':candidate,'runtime_kernel_state_verified':False}
        cache[name]=value;return value
    for module in modules.values():module.relocate(resolve)
    return modules,cache,kernel


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
    args=ap.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    modules,cache,kernel=build()
    facts={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'PASS_OFFLINE_ORIGINAL_MODULE_RELOCATION_MATH_NOT_LINUX_LOAD',
      'modules':[m.facts() for m in modules.values()],
      'combined_relocation_counts':dict(collections.Counter(x['type'] for m in modules.values() for x in m.relocations)),
      'total_relocations':sum(len(m.relocations) for m in modules.values()),
      'unique_external_provider_names':len(cache),'kernel_sha256':im.sha(kernel),
      'module_layout_is_guest_fixture_not_actual_Linux_module_addresses':True,
      'NOBITS_zero_is_initial_storage_not_OS_init':True,
      'kernel_BSS_task_locks_threads_allocator_driver_or_real_Hal_state':False,
      'ELF_file_module_load_camera_or_persistent_write_exported':False}
    im.write_json(out/'module-relocation-results.json',facts)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'previous_manifest_sha256':PRIOR_SHA,'volume_uuid':im.VOLUME})
    print(json.dumps({'status':facts['status'],'relocations':facts['total_relocations'],
      'counts':facts['combined_relocation_counts'],'providers':len(cache)}))


if __name__=='__main__':main()
