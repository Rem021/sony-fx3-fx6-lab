#!/usr/bin/env python3
"""Record the original AP file-input virtual contracts and loader literals."""
from pathlib import Path
import json,struct,subprocess
from current_static import View,sources,HERE
import hashlib
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN

def cstring(view,va):
    if not va:return None
    result=bytearray()
    for i in range(256):
        byte=view.read(va+i,1)
        if byte==b'\0':return result.decode('ascii')
        result+=byte
    raise AssertionError(('unbounded literal',hex(va)))

def relocation(view,va):
    r=next(r for r in view.elf.get_section_by_name('.rela.dyn').iter_relocations() if r['r_offset']==va)
    symbol=view.symbols[r['r_info_sym']]
    typ=r['r_info_type'];assert typ in [257,1025,1027]
    value=r['r_addend'] if typ==1027 else symbol['st_value']+r['r_addend']
    return value,symbol.name,typ

def main():
    views={Path(s['path']).name:View(s['path'],s['sha256']) for s in sources()}
    contracts=[]
    for name,table,slots in [('libcryptfileinputupdaterapi.so','_ZTVN7Updater28CryptFileInputUpdaterManagerE',[0x10,0x18,0x20]),('libfileinputupdaterapi.so','_ZTVN7Updater25FileInputBodyLoaderModuleE',[0x98,0xa0,0xa8,0xb0])]:
        view=views[name];symbol=next(s for s in view.symbols if s.name==table)
        for offset in slots:
            address=symbol['st_value']+16+offset;assert address+8<=symbol['st_value']+symbol['st_size']
            value,label,typ=relocation(view,address)
            pretty=subprocess.check_output(['c++filt',label],text=True).strip()
            contracts.append(dict(library=name,table=table,vptr_offset=16,virtual_offset=hex(offset),slot=hex(address),relocation_type=typ,target_symbol=label,demangled=pretty,target_va_in_this_file=hex(value)))
    ufp=views['libupdaterufp.so'];argv=[]
    for i in range(4):
        items=[]
        for j in range(3):
            slot=0x15188+24*i+8*j
            raw=struct.unpack('<Q',ufp.read(slot,8))[0]
            try:value,_,_=relocation(ufp,slot)
            except StopIteration:value=raw
            items.append(cstring(ufp,value))
        argv.append(dict(table_va=hex(0x15188+24*i),argv=items))
    core=views['libupdatercorecommon.so'];literals=[]
    for va in [0xc299,0xc2b6,0xc2cc,0xc2dd,0xc2f9,0xc32f,0xc337]:literals.append(dict(library='libupdatercorecommon.so',va=hex(va),text=cstring(core,va)))
    section=ufp.elf.get_section_by_name('.text');lines=[]
    for ins in Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(section.data(),section['sh_addr']):
        note=''
        if ins.mnemonic in ['b','bl'] and ins.op_str.startswith('#'):
            target=int(ins.op_str[1:],0)
            if target in ufp.labels:note=' ; '+ufp.labels[target].split('(')[0]
        lines.append(f'{ins.address:08x} {ins.mnemonic:10} {ins.op_str}{note}')
    (HERE/'updaterufp-text-section.txt').write_text('\n'.join(lines)+'\n')
    result=dict(virtual_contracts=contracts,original_process_argv_tables=argv,body_loader_literals=literals,
                ufp_text_section=dict(va=hex(section['sh_addr']),bytes=section['sh_size'],sha256=hashlib.sha256(section.data()).hexdigest(),listing='updaterufp-text-section.txt',scope='Whole bounded .text section; private function boundaries are not asserted.'),
                osal_registration_static=[dict(service=hex(a),callback_relative_va=hex(b)) for a,b in [(0x004b8290,0x27c4),(0x004b0233,0x3034),(0x004b024e,0x3174),(0x804b0998,0x2e6c)]],
                scope='Original ELF relocations and literal references. Vptr +16 is corroborated by saved constructors. No process launched, OSAL request sent, filesystem mounted, library loaded or device operated; runtime dispatch and native loader policy remain unverified.')
    (HERE/'current-loader-contract-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'virtual_slots':len(contracts),'argv_tables':len(argv),'loader_literals':len(literals)}))

if __name__=='__main__':main()
