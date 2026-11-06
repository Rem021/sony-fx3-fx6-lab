#!/usr/bin/env python3
"""Pin appFw crypto call sites; names alone do not identify a firmware gate."""
from pathlib import Path
import array,bisect,hashlib,io,json,struct,sys
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
from elftools.dwarf.callframe import FDE

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
PATH=PROJECT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so'
PIN='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'

def main():
    HERE.mkdir(exist_ok=True);raw=PATH.read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
    e=ELFFile(io.BytesIO(raw));dyn=e.get_section_by_name('.dynsym');symbols=list(dyn.iter_symbols())
    plt=e.get_section_by_name('.plt');rels=e.get_section_by_name('.rela.plt')
    labels={plt['sh_addr']+32+16*i:symbols[r['r_info_sym']].name for i,r in enumerate(rels.iter_relocations())}
    wanted={a:n for a,n in labels.items() if n.startswith('iCrypt_')}
    frame_entries=e.get_dwarf_info().EH_CFI_entries();ranges=sorted((r['initial_location'],r['address_range']) for r in frame_entries if isinstance(r,FDE));starts=[a for a,n in ranges]
    text=e.get_section_by_name('.text');data=text.data();base=text['sh_addr'];words=array.array('I');words.frombytes(data)
    if sys.byteorder!='little':words.byteswap()
    sites=[]
    for index,word in enumerate(words):
        if word&0xfc000000 not in [0x94000000,0x14000000]:continue
        displacement=word&0x3ffffff
        if displacement&0x2000000:displacement-=0x4000000
        site=base+4*index;target=site+4*displacement
        if target in wanted:sites.append((site,target))
    out=HERE/'app-crypto-fragments';out.mkdir(exist_ok=True);md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);rows=[]
    for site,target in sites:
        index=bisect.bisect_right(starts,site)-1;fde=ranges[index] if index>=0 and ranges[index][0]<=site<sum(ranges[index]) else None
        if fde and fde[1]<=4000:start,n=fde;scope='Original unwind FDE range'
        else:start=max(base,site-160);n=min(base+len(data)-start,400);scope='Bounded instruction window; no whole-function boundary asserted'
        code=data[start-base:start-base+n];lines=[];calls=[]
        for ins in md.disasm(code,start):
            note=''
            if ins.mnemonic in ['b','bl'] and ins.op_str.startswith('#'):
                dst=int(ins.op_str[1:],0)
                if dst in labels:note=' ; '+labels[dst]
                calls.append(dict(site=hex(ins.address),target=hex(dst),symbol=labels.get(dst)))
            lines.append(f'{ins.address:08x} {ins.mnemonic:10} {ins.op_str}{note}')
        f=out/f'{site:x}-{wanted[target]}.txt';f.write_text('\n'.join(lines)+'\n')
        rows.append(dict(site=hex(site),plt_target=hex(target),symbol=wanted[target],range_start=hex(start),bytes=n,scope=scope,sha256=hashlib.sha256(code).hexdigest(),calls=calls,disassembly=str(f.relative_to(HERE))))
    result=dict(source=str(PATH),source_sha256=PIN,text_va=hex(base),text_bytes=len(data),unwind_ranges=len(ranges),imported_crypto_functions={hex(a):n for a,n in wanted.items()},call_sites=rows,
                scope='Static direct branch references to iCrypt imports only. No claim these are firmware verification, no private key access or vendor code execution, and no indirect-call coverage.')
    (HERE/'app-crypto-call-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'direct_call_sites':len(rows),'functions':sorted({r['symbol'] for r in rows}),'unwind_ranges':len(ranges)}))

if __name__=='__main__':main()
