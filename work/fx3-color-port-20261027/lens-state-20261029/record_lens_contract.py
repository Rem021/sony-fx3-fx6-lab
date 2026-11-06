#!/usr/bin/env python3
"""Source extracts and bounded AP/CP contracts; no target-native loading."""
import hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
from find_lens_service import HERE,FS
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources
sys.path.insert(0,str(HERE.parent/'entry-20261029'))
from inspect_entry_chain import listing
sys.path.insert(0,str(HERE.parent/'route-20261028'))
from cp_look_route import image,BASE,PIN

def main():
    location=json.loads((HERE/'service-location-results.json').read_text())
    sys.path.insert(0,str(FS));from read_filesystems import Ext2
    fs=Ext2(FS/'nflasha15.img');entries={r['path']:r for r in fs.walk()};out=HERE/'original-members';out.mkdir(exist_ok=True);members=[]
    for name in ['/lib/libInfraLensCommunicator.so','/lib/libInfraGetVersion.so']:
        row=entries[name];raw=fs.data(row['inode']);known=next(r['source_sha256'] for r in location['ap_mov_wide_matches'] if r['path']==name)
        assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==known
        p=out/Path(name).name
        if p.exists():assert p.read_bytes()==raw
        else:p.write_bytes(raw)
        members.append(dict(original_path=name,inode=row['inode'],bytes=len(raw),sha256=known,output=str(p.relative_to(HERE))))
    (HERE/'original-member-results.json').write_text(json.dumps(members,indent=2)+'\n')
    source=next(r for r in sources() if Path(r['path']).name=='libupdaterufp.so');ufp=View(source['path'],source['sha256'])
    fragments=[];dest=HERE/'contract-fragments';dest.mkdir(exist_ok=True)
    for va,n in [(0x184c,0xdc),(0x1928,0xd0),(0x1dbc,0x1a8),(0x2498,0x250),(0x26e8,0x40),(0x2f48,0xec),(0x3cd0,120)]:
        raw=ufp.read(va,n);text,literals,calls=listing(ufp,va,n);p=dest/f'AP-ufp-{va:x}.txt';p.write_text(text)
        fragments.append(dict(source=str(ufp.path),source_sha256=source['sha256'],architecture='AArch64',va=hex(va),bytes=n,sha256=hashlib.sha256(raw).hexdigest(),disassembly=str(p.relative_to(HERE)),literals=literals,calls=calls,bounds='original function' if va==0x3cd0 else 'explicit private window'))
    lens=View(HERE/members[0]['output'],members[0]['sha256'])
    symbol=next(s for s in lens.symbols if lens.names.get(s.name)=='LensCommunicator::GetMountedLensInfo(void*)')
    va=symbol['st_value'];raw=lens.function(va);text,literals,calls=listing(lens,va,len(raw));p=dest/'AP-GetMountedLensInfo.txt';p.write_text(text)
    fragments.append(dict(source=str(lens.path),source_sha256=members[0]['sha256'],architecture='AArch64',va=hex(va),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),label=lens.names[symbol.name],disassembly=str(p.relative_to(HERE)),literals=literals,calls=calls,bounds='original symbol/FDE function'))
    cp=image();md=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    ranges=[(0x391b54,0x391bb2),(0x38dddc,0x38ddf2),(0x38ddf8,0x38e0d0),(0x38e144,0x38e178),(0x391c60,0x391cb4),
            (0xa878d2,0xa878de),(0x94cfea,0x94cff6),(0x94aaa2,0x94aad6),(0x94e7fc,0x94e81e),(0x948538,0x948566),(0x9484c0,0x9484cc)]
    for lo,hi in ranges:
        raw=cp[lo-BASE:hi-BASE];assert len(raw)==hi-lo
        p=dest/f'CP-{lo:x}.txt';p.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(raw,lo))+'\n')
        fragments.append(dict(source=str(FS/'files/nflasha8/cpapp-b.bin'),source_sha256=PIN,architecture='Thumb',va=hex(lo),file_offset=hex(lo-BASE),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),disassembly=str(p.relative_to(HERE)),bounds='explicit CP code window, not ELF symbol identity'))
    switch=cp[0x38ddf2-BASE:0x38ddf7-BASE];sizes=cp[0x38e178-BASE:0x38e18c-BASE]
    data_tables=dict(command_switch=dict(va='0x38ddf2',bytes=5,sha256=hashlib.sha256(switch).hexdigest(),targets=[hex(0x38ddf2+2*b) for b in switch]),reply_bytes=dict(va='0x38e178',bytes=20,sha256=hashlib.sha256(sizes).hexdigest(),values=list(struct.unpack('<5I',sizes))))
    assert data_tables['command_switch']['targets']==['0x38ddf8','0x38de4e','0x38de6c','0x38de9c','0x38df1c']
    assert data_tables['reply_bytes']['values']==[20,12,40,8,8]
    (HERE/'lens-contract-results.json').write_text(json.dumps(dict(fragments=fragments,cp_data_tables=data_tables,scope='Original AP and CP bytes/pins, bounded code windows, explicit TBB/reply data tables, and source library method name. Tables are not disassembled as executed instructions. Runtime global inputs and OSAL bus remain synthetic; these sources do not prove actual device state, session, replies or firmware acceptance.'),indent=2)+'\n')
    print(json.dumps(dict(original_members=len(members),fragments=len(fragments),cp_reply_sizes=data_tables['reply_bytes']['values'])))

if __name__=='__main__':main()
