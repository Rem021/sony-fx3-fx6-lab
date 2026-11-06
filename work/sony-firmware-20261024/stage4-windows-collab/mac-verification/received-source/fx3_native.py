from pathlib import Path
import io,json,struct,sys,hashlib
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'work/python-packages'))
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
INV=json.loads((ROOT/'outputs/config-analysis/filesystem-usr.json').read_text(encoding='utf-8'))
class Native:
    def __init__(self,name):
        self.record=next(e for e in INV['entries'] if e['path']==name)
        self.path=ROOT/self.record['physical_path'];self.blob=self.path.read_bytes()
        if hashlib.sha256(self.blob).hexdigest()!=self.record['sha256']:raise RuntimeError('Native source differs from extraction inventory: '+name)
        self.elf=ELFFile(io.BytesIO(self.blob))
        self.sections=[(s['sh_addr'],s['sh_addr']+s['sh_size'],s['sh_offset'],s.name) for s in self.elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_flags']&2]
        self.text=self.elf.get_section_by_name('.text');self.code=self.text.data();self.base=self.text['sh_addr']
        self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    def read(self,va,n):
        for a,z,o,name in self.sections:
            if a<=va and va+n<=z:return self.blob[o+va-a:o+va-a+n]
        raise ValueError(f'Unmapped file bytes {va:x}+{n:x}')
    def cstr(self,va,limit=1200):
        for a,z,o,name in self.sections:
            if a<=va<z:
                raw=self.blob[o+va-a:o+min(z,va+limit)-a].split(b'\0',1)[0]
                try:
                    text=raw.decode('utf-8')
                    return text if text and all(c.isprintable() or c in '\n\t' for c in text) else None
                except UnicodeError:return None
        return None
    def instructions(self,start,end):return list(self.md.disasm(self.read(start,end-start),start))
    def disasm(self,start,end):return [f'{i.address:08x}: {i.mnemonic:8} {i.op_str}' for i in self.instructions(start,end)]
    def callers(self,targets):
        result=[]
        for n,(w,) in enumerate(struct.iter_unpack('<I',self.code[:len(self.code)//4*4])):
            if w&0x7c000000!=0x14000000:continue
            imm=w&0x3ffffff
            if imm&0x2000000:imm-=0x4000000
            pc=self.base+n*4;target=pc+imm*4
            if target in targets:result.append((pc,target))
        return result
    def symbols(self):
        section=self.elf.get_section_by_name('.dynsym')
        return [] if section is None else [{'name':s.name,'VA':hex(s['st_value']),'size':s['st_size'],'type':s['st_info']['type'],'defined':s['st_shndx']!='SHN_UNDEF'} for s in section.iter_symbols()]
    def plt(self):
        sec=self.elf.get_section_by_name('.plt');rel=self.elf.get_section_by_name('.rela.plt');sym=self.elf.get_section_by_name('.dynsym')
        if not sec or not rel:return {}
        return {sec['sh_addr']+32+16*i:sym.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
    def string_references(self,targets):
        regs={};refs=[]
        for n,(w,) in enumerate(struct.iter_unpack('<I',self.code[:len(self.code)//4*4])):
            pc=self.base+n*4
            if w&0x9f000000==0x90000000:
                imm=(((w>>5)&0x7ffff)<<2)|((w>>29)&3)
                if imm&0x100000:imm-=0x200000
                regs[w&31]=((pc&~4095)+(imm<<12),n)
            elif w&0xff800000==0x91000000:
                rn=(w>>5)&31
                if rn not in regs or n-regs[rn][1]>6:continue
                v=regs[rn][0]+(((w>>10)&4095)<<(12 if w&(1<<22) else 0))
                if v in targets:refs.append((pc,v))
        return refs
