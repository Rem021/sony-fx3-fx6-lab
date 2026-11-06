#!/usr/bin/env python3
"""Pinned original current-AP ELF function views, no loader or code execution."""
from pathlib import Path
import hashlib,io,json,subprocess
from elftools.elf.elffile import ELFFile
from elftools.dwarf.callframe import FDE
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN

HERE=Path(__file__).resolve().parent

class View:
    def __init__(self,path,pin):
        self.path=Path(path);self.raw=self.path.read_bytes();assert hashlib.sha256(self.raw).hexdigest()==pin
        self.elf=ELFFile(io.BytesIO(self.raw));assert self.elf['e_machine']=='EM_AARCH64'
        dyn=self.elf.get_section_by_name('.dynsym');self.symbols=list(dyn.iter_symbols())
        pretty=subprocess.check_output(['c++filt'],input='\n'.join(s.name for s in self.symbols),text=True).splitlines()
        self.names=dict(zip([s.name for s in self.symbols],pretty))
        self.labels={s['st_value']:n for s,n in zip(self.symbols,pretty) if s['st_shndx']!='SHN_UNDEF' and s['st_size'] and s['st_info']['type']=='STT_FUNC'}
        self.sizes={s['st_value']:s['st_size'] for s in self.symbols if s['st_shndx']!='SHN_UNDEF' and s['st_size'] and s['st_info']['type']=='STT_FUNC'}
        self.plt={};plt=self.elf.get_section_by_name('.plt');rels=self.elf.get_section_by_name('.rela.plt')
        if plt and rels:
            self.plt={plt['sh_addr']+32+16*i:pretty[r['r_info_sym']] for i,r in enumerate(rels.iter_relocations())}
        self.labels.update(self.plt)
        self.unwind={x['initial_location']:x['address_range'] for x in self.elf.get_dwarf_info().EH_CFI_entries() if isinstance(x,FDE)}

    def read(self,va,n):
        for seg in self.elf.iter_segments():
            if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=va and va+n<=seg['p_vaddr']+seg['p_filesz']:
                off=seg['p_offset']+va-seg['p_vaddr'];return self.raw[off:off+n]
        raise ValueError((self.path.name,hex(va),n))

    def function(self,va):
        n=self.sizes.get(va,self.unwind.get(va));assert n,(self.path.name,hex(va),'unbounded')
        return self.read(va,n)

    def listing(self,va):
        lines=[];calls=[]
        for ins in Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(self.function(va),va):
            note=''
            if ins.mnemonic in ['bl','b'] and ins.op_str.startswith('#'):
                dst=int(ins.op_str[1:],0)
                if dst in self.labels:note=' ; '+self.labels[dst].split('(')[0]
                calls.append(dict(site=hex(ins.address),target=hex(dst),label=self.labels.get(dst)))
            lines.append(f'{ins.address:08x} {ins.mnemonic:10} {ins.op_str}{note}')
        return '\n'.join(lines)+'\n',calls

def sources():
    rows=[];inventory=json.loads((HERE.parent/'package-20261028/verifier-library-inventory.json').read_text())
    for r in inventory['libraries']:
        if Path(r['source_path']).name in ['libupdaterufp.so','libcryptfileinputupdaterapi.so','libfileinputupdaterapi.so','libupdatercorecommon.so','libupdatertalk.so']:
            rows.append(dict(path=str(HERE.parent/'package-20261028'/r['output']),sha256=r['sha256'],original_path=r['source_path']))
    c=json.loads((HERE/'crypter-source.json').read_text());rows.append(dict(path=str(HERE/'original-members/crypter.elf'),sha256=c['sha256'],original_path=c['path']))
    additional=HERE/'additional-source-members.json'
    if additional.exists():
        for source in json.loads(additional.read_text()):
            if source['original_path']=='/lib/libupdatercommon.so':
                rows.append(dict(path=str(HERE/source['output']),sha256=source['sha256'],original_path=source['original_path']))
    return rows

def main():
    out=HERE/'disassembly';out.mkdir(exist_ok=True);rows=[]
    for source in sources():
        view=View(source['path'],source['sha256']);funcs=[]
        for va in sorted(set(view.sizes)|set(view.unwind)):
            if va==0:continue
            name=view.labels.get(va,f'unwind_function_{va:x}')
            code=view.function(va);text,calls=view.listing(va)
            output=out/(view.path.name+'-'+hex(va)[2:]+'.txt');output.write_text(text)
            funcs.append(dict(va=hex(va),bytes=len(code),label=name,sha256=hashlib.sha256(code).hexdigest(),calls=calls,disassembly=str(output.relative_to(HERE))))
        rows.append(dict(**source,functions=funcs))
    (HERE/'current-static-results.json').write_text(json.dumps(dict(sources=rows,scope='Only file-backed original function slices bounded by ELF symbol sizes or unwind FDE ranges; static disassembly, no Sony program execution.'),indent=2)+'\n')
    print(json.dumps({'sources':len(rows),'functions':sum(len(r['functions']) for r in rows)}))

if __name__=='__main__':main()
