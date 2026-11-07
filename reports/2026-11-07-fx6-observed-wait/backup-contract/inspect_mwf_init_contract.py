#!/usr/bin/env python3
"""Pinned read-only MWF entry and IM descriptor ABI inspection. No ELF execution."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files')
PINS={
 'lib/libMWF.so':'3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782',
 'bin/im.elf':'87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec',
 'lib/libIMDB.so':'a088ef303793497a443e89d6de4c8f12e07ec791c945f54e2dc1b52cd42db896',
 'lib/libInfraKikiLogGenerator.so':'be7abc37ceb019b203a3853eba633d5d703d86d9a24ec2a6081b74873dd71917',
}
class Image:
    def __init__(self,name):
        self.path=ROOT/name;self.blob=self.path.read_bytes()
        self.sha=hashlib.sha256(self.blob).hexdigest();assert self.sha==PINS[name]
        self.elf=ELFFile(BytesIO(self.blob));pl=self.elf.get_section_by_name('.plt')
        rel=self.elf.get_section_by_name('.rela.plt');sy=self.elf.get_section(rel['sh_link'])
        self.plt={pl['sh_addr']+32+16*i:sy.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
    def read(self,va,size):
        for s in self.elf.iter_segments():
            if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+size<=s['p_vaddr']+s['p_filesz']:
                off=s['p_offset']+va-s['p_vaddr'];return self.blob[off:off+size]
        raise ValueError(f'not file backed: {va:x}')
    def string(self,va):return self.read(va,100).split(b'\0')[0].decode()
    def dis(self,va,size):return list(Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(self.read(va,size),va))
    def check(self,items):
        result={}
        for va,expected in items.items():
            i=self.dis(va,4)[0];actual=f'{i.mnemonic} {i.op_str}'.rstrip()
            assert actual==expected,(hex(va),actual,expected);result[hex(va)]=actual
        return result
    def calls(self,va,size):
        return [{'va':hex(i.address),'kind':i.mnemonic,'target':i.op_str,
            'plt_symbol':self.plt.get(int(i.op_str[1:],16))} for i in self.dis(va,size)
            if i.mnemonic in ('b','bl') and i.op_str.startswith('#')]
    def receipt(self):return {'path':str(self.path),'bytes':len(self.blob),'sha256':self.sha}

def main():
    mwf,im,db,kiki=(Image(x) for x in PINS)
    mwf_checks=mwf.check({
        0x27e74:'b #0x22e80',0x27d68:'adrp x0, #0x65000',
        0x27d6c:'ldrb w1, [x0, #0xc89]',0x27d70:'cbnz w1, #0x27e08',
        0x27d80:'strb w1, [x0, #0xc89]',0x27dec:'b #0x21cf0',0x27e08:'ret',
    })
    assert mwf.plt[0x22e80]=='_ZN3MWF10InitializeEv'
    assert mwf.plt[0x21cf0]=='_ZN3MWF7InhInfo10InitializeEv'
    assert mwf.elf.get_section_by_name('.dynsym').get_symbol_by_name('MWF_Init')[0]['st_size']==4
    im_checks=im.check({
        0x405f0c:'bl #0x402080',0x405f34:'ldp x0, x1, [x22, #0x38]',
        0x405f3c:'csel x0, x0, x1, ne',0x405f44:'blr x20',
        0x405f50:'mov w20, #0',0x405f54:'str w0, [x19, #0x3c]',
        0x406004:'bl #0x402080',0x40602c:'blr x20',0x406030:'b #0x405fd8',
        0x405fd8:'mov w19, #0',0x405fdc:'str x21, [x22]',
        0x40626c:'bl #0x405f5c',0x406284:'bl #0x405e24',
        0x4064a0:'bl #0x4061ec',0x4064a4:'mov w22, w0',
        0x4064b8:'cbnz w22, #0x4064d4',0x4064c0:'str x0, [x19, #0x20]',
        0x4064c4:'mov w0, #2',0x4064c8:'str w0, [x19, #0x28]',
        0x4065f0:'bl #0x406374',0x40660c:'add x19, x19, #0x48',
    })
    assert im.plt[0x402080]=='dlsym'
    entries=[]
    for index,va in ((29,0x1f198),(32,0x1f270)):
        b=db.read(va,72);kind,flags,target=struct.unpack_from('<III',b)
        module,selector=struct.unpack_from('<HH',b,12)
        pointers={}
        for off in (16,24,32,40,48,56,64):
            pointer=struct.unpack_from('<Q',b,off)[0]
            pointers[hex(off)]={'va':hex(pointer),'string':db.string(pointer) if pointer else None}
        entries.append({'index':index,'va':hex(va),'entry_bytes':72,'kind':hex(kind),
            'flags':hex(flags),'target_mask':hex(target),'module_id_u16':module,
            'loader_selector_u16_at_0x0e':selector,'pointers':pointers})
    assert entries[1]['pointers']['0x18']['string']=='MWF_Init'
    assert entries[1]['kind']=='0x20000002'
    assert entries[1]['pointers']['0x38']['string']==entries[1]['pointers']['0x40']['string']==''
    kiki_checks=kiki.check({0x3a10:'mov w0, #1',0x3a18:'bl #0x1db0',0x3a20:'b #0x1f80',
        0x3924:'str w0, [x19, #0x2b0]',0x3928:'tbnz w0, #0x1f, #0x3948',
        0x3944:'bl #0x1ff0',0x397c:'bl #0x2210',0x39a4:'bl #0x2210',0x39e8:'bl #0x1f30'})
    needed=[x.needed for x in mwf.elf.get_section_by_name('.dynamic').iter_tags() if x.entry.d_tag=='DT_NEEDED']
    kiki_imports=[x.name for x in mwf.elf.get_section_by_name('.dynsym').iter_symbols()
        if x['st_shndx']=='SHN_UNDEF' and 'kiki' in x.name.lower()]
    result={'status':'PASS','scope':'pinned static ABI/descriptor facts, no ELF execution or guest test',
        'sources':{x:str(PINS[x]) for x in PINS},'source_receipts':[x.receipt() for x in (mwf,im,db,kiki)],
        'mwf_init':{'export_va':'0x27e74','export_bytes':4,'target':'MWF::Initialize() at 0x27d68 through PLT',
            'incoming_x0_read_before_overwrite':False,'first_instruction':'adrp x0, #0x65000',
            'meaningful_integer_success_return_proved':False,'fast_return_x0':'0x65000 + runtime load bias',
            'guard_va':'0x65c89','guard_set_before_initialization_calls':True,
            'instruction_checks':mwf_checks,'initializer_calls':mwf.calls(0x27d68,0xa4)},
        'im_dispatch':{'instruction_checks':im_checks,'descriptors':entries,
            'mwf_route':'0x20000002 -> 0x405f5c -> dlsym at 0x406004 -> blr at 0x40602c',
            'parameter_route':'0x20000004 -> 0x405e24 -> dlsym at 0x405f0c -> selected descriptor argument -> blr at 0x405f44',
            'integer_return':'loader-local 0/-1/-2; init result registers ignored',
            'completion_record':'new-state normal path stores handle at state+0x20 and numeric state 2 at state+0x28 after loader returns; signals per-module/global semaphores',
            'completion_limit':'does not prove asynchronous services or hardware functional readiness'},
        'kiki_evidence':{'instruction_checks':kiki_checks,'mwf_needed':needed,'mwf_kiki_named_imports':kiki_imports,
            'order':'same enabled/filtered startup table scan dispatches Kiki index29 before MWF index32; new-state path calls init synchronously before continuing scan',
            'completion_dependency':'Kiki functional readiness prerequisite for MWF not proved; no direct named import or readiness test identified',
            'error_limit':'Kiki init_proc continues after negative open and ignores ioctl/register return values in inspected branches; entry return is insufficient readiness evidence'},
        'source_drift':{'older_report':'reports/2026-11-07-fx6-native-lifecycle/deep-init/lifecycle-order.md',
            'older_im_sha256':'2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772',
            'current_im_sha256':im.sha,'resolution':'unresolved; new assertions deliberately bind current actual file, not older hash'},
        'limitations':['No original C/C++ header recovered; void-like return is binary/caller inference, not a recovered typedef.',
            'Do not generalize this fixed MWF entry to all IM init hooks or erase generic descriptor arguments.',
            'Guard byte is set on entry and is not an independently verified completed/ready flag.',
            'No VM, shim/source mutation, force-success, fake lock, or manual init performed.']}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
