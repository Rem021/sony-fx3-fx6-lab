#!/usr/bin/env python3
"""Original app updater wrapper, caller and initializer fragments with literals."""
from pathlib import Path
import hashlib,json,sys
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_IMM,ARM64_OP_REG
from inspect_app_crypto_calls import PATH,PIN,HERE

sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources

def regno(md,reg):
    n=md.reg_name(reg)
    return int(n[1:]) if n.startswith(('w','x')) and n[1:].isdigit() else None

def listing(view,va,n):
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True
    readonly=[(s['sh_addr'],s['sh_addr']+s['sh_size']) for s in view.elf.iter_sections()
              if s['sh_flags']&2 and not s['sh_flags']&(1|4) and s['sh_type']!='SHT_NOBITS']
    known={};lines=[];literals=[];calls=[]
    for ins in md.disasm(view.read(va,n),va):
        op=ins.operands;value=None;rd=None
        if ins.mnemonic=='adrp' and len(op)==2:
            rd=regno(md,op[0].reg);value=op[1].imm
        elif ins.mnemonic=='add' and len(op)==3 and op[1].type==ARM64_OP_REG and op[2].type==ARM64_OP_IMM:
            rd=regno(md,op[0].reg);rn=regno(md,op[1].reg)
            if rn in known:value=known[rn]+op[2].imm
        elif ins.mnemonic=='mov' and len(op)==2 and op[1].type==ARM64_OP_REG:
            rd=regno(md,op[0].reg);value=known.get(regno(md,op[1].reg))
        for reg in ins.regs_access()[1]:known.pop(regno(md,reg),None)
        if rd is not None and value is not None:known[rd]=value
        note=''
        match=next(((low,high) for low,high in readonly if value is not None and low<=value<high),None)
        if match is not None:
            raw=view.read(value,min(512,match[1]-value)).split(b'\0',1)[0]
            if len(raw)>=4 and all(32<=b<127 or b in [9,10,13] for b in raw):
                text=raw.decode();note=' ; literal '+repr(text)
                literals.append(dict(site=hex(ins.address),va=hex(value),text=text))
        if ins.mnemonic in ['bl','b'] and ins.op_str.startswith('#'):
            target=int(ins.op_str[1:],0);label=view.labels.get(target)
            if label:note+=' ; '+label.split('(')[0]
            calls.append(dict(site=hex(ins.address),target=hex(target),label=label))
        lines.append(f'{ins.address:08x} {ins.mnemonic:10} {ins.op_str}{note}')
        if ins.mnemonic in ['bl','blr']:
            for register in range(19):known.pop(register,None)
        elif ins.mnemonic.startswith('b') or ins.mnemonic in ['cbz','cbnz','tbz','tbnz','ret']:known.clear()
    return '\n'.join(lines)+'\n',literals,calls

def main():
    app=View(PATH,PIN);other=next(r for r in sources() if Path(r['path']).name=='libupdaterufp.so');ufp=View(other['path'],other['sha256'])
    targets=[('app-execute-update',app,0x2eae880,0x270),('app-initialize-wrapper',app,0x2eadbb0,0x144),('app-initialize-rpc',app,0x2eadaec,0xc4),
             ('app-sync-rpc',app,0x2eacf18,0x158),('app-execute-update-caller',app,0x2ddfdd0,0x200),('app-public-key-extract-caller',app,0x2de2540,0x200),
             ('ufp-execute-callback',ufp,0x3034,0x140),('ufp-body-prepare',ufp,0x2728,0x9c),('ufp-lens-prepare',ufp,0x2f48,0xec)]
    out=HERE/'entry-fragments';out.mkdir(exist_ok=True);rows=[]
    for label,view,va,n in targets:
        text,literals,calls=listing(view,va,n);dest=out/(label+'.txt');dest.write_text(text)
        rows.append(dict(label=label,source_sha256=hashlib.sha256(view.raw).hexdigest(),va=hex(va),bytes=n,sha256=hashlib.sha256(view.read(va,n)).hexdigest(),literals=literals,calls=calls,disassembly=str(dest.relative_to(HERE))))
    (HERE/'entry-static-results.json').write_text(json.dumps(dict(fragments=rows,scope='Bounded static original instruction fragments and conservatively tracked read-only string addresses. No whole-program/normal UI admission or authentication claim; no code or device execution.'),indent=2)+'\n')
    print(json.dumps({'fragments':len(rows),'literals':sum(len(r['literals']) for r in rows)}))

if __name__=='__main__':main()
