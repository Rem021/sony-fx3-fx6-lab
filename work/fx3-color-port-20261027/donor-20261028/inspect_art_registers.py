#!/usr/bin/env python3
"""Static original ARM64 function slices and call labels, never dlopen."""
from pathlib import Path
import hashlib,json,subprocess
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from macho_static import MachO

HERE=Path(__file__).resolve().parent

def main():
    source=json.loads((HERE/'art-generator-source.json').read_text())
    m=MachO(source['path']);assert hashlib.sha256(m.file).hexdigest()==source['sha256']
    named={s['va']:s['name'] for s in m.symbols if s['section']==1}
    all_names={**named,**m.stubs}
    addresses=sorted(all_names)
    pretty=subprocess.check_output(['c++filt'],input='\n'.join(all_names[a][1:] for a in addresses),text=True).splitlines()
    labels=dict(zip(addresses,pretty));assert len(labels)==len(addresses)
    targets=[(a,n.split('(')[0]) for a,n in labels.items()
             if n.startswith('Venice_regaddres::') or
             n.split('(')[0] in ['Matrix_Process::LMX_data2byte','Image_Setting::Mtx_bunkai',
                                'Matrix_Process::getGamutTransformMatrix','Image_Setting::Binary_frame',
                                'Matrix_Process::Mtx_one2one','Matrix_Process::Matrix_set',
                                'Image_Setting::SET_MTX_data','Basic_Info::dec2hexa_keta',
                                'ArtModeController::generateModeTable','ArtModeController::setParamData',
                                'ArtColorConverter::converterInit']]
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    out=HERE/'register-disassembly';out.mkdir(exist_ok=True)
    rows=[]
    for address,label in targets:
        code=m.function(address);calls=[];lines=[]
        for i in md.disasm(code,address):
            note=''
            if i.mnemonic in ['b','bl'] and i.op_str.startswith('#'):
                target=int(i.op_str[1:],0)
                if target in labels:
                    note=' ; '+labels[target].split('(')[0]
                    calls.append({'site':hex(i.address),'target':hex(target),'symbol':labels[target]})
            lines.append(f'{i.address:08x} {i.mnemonic:10} {i.op_str}{note}')
        name=label.replace('::','-')+'-'+hex(address)[2:]+'.txt'
        (out/name).write_text('\n'.join(lines)+'\n')
        rows.append(dict(va=hex(address),label=label,bytes=len(code),sha256=hashlib.sha256(code).hexdigest(),calls=calls,disassembly=str((out/name).relative_to(HERE))))
    result=dict(source_sha256=source['sha256'],functions=rows,
                scope='Static source ARM64 instruction slices and import labels only. Register strings are serializer labels, not writes to hardware.')
    (HERE/'venice-register-static-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'functions':len(rows),'import_assign':m.stubs[0x6de208]}))

if __name__=='__main__':main()
