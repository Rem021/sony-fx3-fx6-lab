#!/usr/bin/env python3
"""Original core file primitives and direct callsites; no native Sony loads."""
from pathlib import Path
from hashlib import sha256
import io
import json
import re
import struct
from elftools.elf.elffile import ELFFile
from elftools.dwarf.callframe import FDE
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
LIB=BASE/'stage2/extraction/files/nflasha15/lib/libsencore.so'
LIB_SHA='a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'


class Image:
    def __init__(self):
        self.raw=LIB.read_bytes();assert sha256(self.raw).hexdigest()==LIB_SHA
        self.elf=ELFFile(io.BytesIO(self.raw));self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        sy=self.elf.get_section_by_name('.dynsym');self.symbols={s.name:s for s in sy.iter_symbols() if s.name}
        p=self.elf.get_section_by_name('.plt')['sh_addr']
        self.plt={p+32+i*16:sy.get_symbol(r['r_info_sym']).name for i,r in enumerate(self.elf.get_section_by_name('.rela.plt').iter_relocations())}
        self.frames=[f for f in self.elf.get_dwarf_info().EH_CFI_entries() if isinstance(f,FDE)]
        self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
        self.relocations=[{'slot':r['r_offset'],'type':r['r_info_type'],'addend':r['r_addend'],'symbol':sy.get_symbol(r['r_info_sym']).name,
            'defined':sy.get_symbol(r['r_info_sym'])['st_shndx']!='SHN_UNDEF','value':sy.get_symbol(r['r_info_sym'])['st_value']}
            for r in self.elf.get_section_by_name('.rela.dyn').iter_relocations()]
    def read(self,a,n):
        s=next(s for s in self.segments if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
        return s.data()[a-s['p_vaddr']:a-s['p_vaddr']+n]
    def function(self,name):
        s=self.symbols[name];return self.listing(s['st_value'],s['st_size'],name)
    def listing(self,a,n,name=None):
        return {'name':name,'VA':hex(a),'bytes':n,'sha256':sha256(self.read(a,n)).hexdigest(),
            'instructions':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,
                'PLT_symbol':self.plt.get(int(i.op_str[1:],16)) if i.mnemonic in ['b','bl'] and i.op_str.startswith('#0x') else None}
                for i in self.md.disasm(self.read(a,n),a)]}
    def frame(self,pc):
        f=next((f for f in self.frames if f['initial_location']<=pc<f['initial_location']+f['address_range']),None)
        return {'VA':hex(f['initial_location']),'bytes':f['address_range']} if f else None


def main():
    image=Image();section=image.elf.get_section_by_name('.text');instructions=list(image.md.disasm(section.data(),section['sh_addr']))
    names=['_ZN14ReadDeviceDataC1EPKcim','_ZN14ReadDeviceData7AdvanceEm','_ZNK14ReadDeviceData13GetBufferSizeEv',
        '_ZNK14ReadDeviceData7GetSizeEv','_ZNK14ReadDeviceData11GetCapacityEv','_ZN14ReadDeviceDataD1Ev',
        '_ZNK8DeviceIo4readEPvm','_ZNK8DeviceIo5lseekEli','_ZNK8DeviceIo4sizeEv','_ZN8DeviceIo5closeEv',
        '_ZN8DeviceIo4openEPKci','_ZN24HostCommunicationCommand9DoExecuteEP12SenserPacket',
        '_Z18FirmwareUpdateFuncPK12SenserPacket','_Z8TestModePK12SenserPacket']
    targets={image.symbols[n]['st_value']:n for n in names}
    targets.update({a:n for a,n in image.plt.items() if n in names});targets[0x10994]='anonymous_file_operation_helper'
    calls=[]
    for i in instructions:
        if i.mnemonic in ['b','bl'] and i.op_str.startswith('#0x') and int(i.op_str[1:],16) in targets:
            calls.append({'pc':hex(i.address),'callee':targets[int(i.op_str[1:],16)],'frame':image.frame(i.address)})
    ctor_calls=[c for c in calls if c['callee']=='_ZN14ReadDeviceDataC1EPKcim']
    # C2 aliases C1 at the same VA. No constructor PLT entry exists here.
    assert image.symbols['_ZN14ReadDeviceDataC1EPKcim']['st_value']==image.symbols['_ZN14ReadDeviceDataC2EPKcim']['st_value']
    assert not ctor_calls
    table=list(struct.unpack('<11h',image.read(0x36148,22)))
    branches=[{'operation':n,'VA':hex(0x109ec+4*offset)} for n,offset in enumerate(table)]
    assert branches[1]['VA']=='0x10ae4'
    helper=image.listing(0x10994,936,'anonymous_file_operation_helper')
    lookup={i['pc']:i for i in helper['instructions']}
    assert lookup['0x10cfc']['asm']=='mov w2, w21'
    assert lookup['0x10d18']['asm']=='cmp x19, x0'
    assert lookup['0x10b34']['PLT_symbol']=='_ZNK8DeviceIo4readEPvm'
    assert lookup['0x10b38']['asm']=='b #0x10a28' and lookup['0x10a28']['asm']=='mov w20, #0'
    vtable_slots=[r for r in image.relocations if r['symbol']=='_ZTV14ReadDeviceData']
    # Keep positive linear pointer references as candidates only. Dynamic and
    # indirect creation cannot be excluded by absence of direct callsites.
    candidates=[]
    for index,i in enumerate(instructions):
        match=re.fullmatch(r'x\d+, \[(x\d+), #(0x[0-9a-f]+)\]',i.op_str) if i.mnemonic=='ldr' else None
        if not match:continue
        base,offset=match.groups();offset=int(offset,16)
        for previous in reversed(instructions[max(0,index-6):index]):
            if previous.mnemonic=='adrp' and previous.op_str.startswith(base+', #'):
                slot=int(previous.op_str.split('#')[1],16)+offset
                if any(slot==r['slot'] for r in vtable_slots):candidates.append({'load_pc':hex(i.address),'ADRP_pc':hex(previous.address),'slot':hex(slot),'frame':image.frame(i.address)})
                break
    report={'status':'PASS_ORIGINAL_RANGE_PRIMITIVE_AND_DIRECT_ROUTE_REVIEW_NOT_SERVICE_READ_RELEASE',
        'original_library_sha256':LIB_SHA,'functions':[image.function(n) for n in names],'anonymous_file_helper':helper,
        'helper_operation_jump_table':branches,'direct_calls':calls,'direct_constructor_calls':ctor_calls,
        'ReadDeviceData_vtable_slots':vtable_slots,'linear_vtable_reference_candidates':candidates,
        'no_direct_lseek_callers_in_this_text':not any(c['callee']=='_ZNK8DeviceIo5lseekEli' for c in calls),
        'prefix_read_semantics':{'operation':1,'open_flags':'0x101000','count':'min(uint32 requested, DeviceIo.size())','offset':'new open then first read; no offset argument or seek in this branch',
            'read_return_handling':'unconditionally choose result0 after read; close result is not exposed by this helper'},
        'stream_class_semantics':{'constructor':'allocates caller-selected vector capacity then initial read','Advance':'partial consumption adjusts pointer/count; full consumption performs another capacity-sized read',
            'GetSize':'calls DeviceIo.size; regular file size64, block device ioctl0x1260 sectors shifted by9',
            'factory_packet_binding_or_runtime_instantiation_proven':False},
        'new_device_root_camera_file_or_Sony_execution':0}
    with (HERE/'original-read-route-review.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'route-audit-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'reviewed_functions':len(names),'prefix_helper_bytes':936,'direct_ReadDevice_constructor_calls':len(ctor_calls),
        'vtable_reference_candidates':candidates,'DeviceIo_lseek_no_direct_callers':report['no_direct_lseek_callers_in_this_text']}))


if __name__=='__main__':main()
