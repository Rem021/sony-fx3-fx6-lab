#!/usr/bin/env python3
"""Pinned CP scene-field store candidates; immediate offsets are not identities."""
import hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN
FIELDS={0x7d4,0x7d8,0x7dc,0x7e0,0x7e4,0x7e8,0x8fc,0x900,0x904,0x908,0x90c,0x910,0x914}

def main():
    parent=TASK/'body-state-20261029';receipt=parent/'final-receipt.json'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()=='55a132887d05e33101540709bd8660049a39aaedb8737d148363fa00111c377f'
    manifest=json.loads(receipt.read_text())
    for item in manifest['files']:
        raw=(parent/item['path']).read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    raw=image();md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);rows=[];reads=[]
    for at in range(0,min(len(raw)-4,0x9c0000),2):
        first,last=struct.unpack_from('<HH',raw,at)
        if first&0xfff0 not in [0xf8c0,0xf8d0] or last&0xfff not in FIELDS:continue
        ins=next(md.disasm(raw[at:at+4],BASE+at,count=1),None)
        if ins is None or ins.mnemonic not in ['str.w','ldr.w']:continue
        row=dict(file_offset=hex(at),va=hex(BASE+at),offset=hex(last&0xfff),instruction=ins.mnemonic+' '+ins.op_str)
        if ins.mnemonic=='ldr.w':reads.append(row);continue
        lo=max(0,at-48);hi=min(len(raw),at+96)
        row.update(span_file=hex(lo),span_bytes=hi-lo,span_sha256=hashlib.sha256(raw[lo:hi]).hexdigest(),listing=[f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(raw[lo:hi],BASE+lo)])
        rows.append(row)
    result=dict(cp_sha256=PIN,parent_files_verified=len(manifest['files']),scan_end_file='0x9c0000',store_candidates=rows,load_candidates=reads,
                scope='Halfword-aligned Thumb immediate LDR/STR candidates only. Embedded data or another structure can share these offsets. Object identity, callers and source bounds require separate review. No native code, IPC, USB, device or firmware writes.')
    (HERE/'scene-field-candidates.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(parent_files_verified=len(manifest['files']),store_candidates=len(rows),loads=len(reads),stores_900_908=[{k:r[k] for k in ['file_offset','instruction']} for r in rows if r['offset'] in ['0x900','0x908']])))

if __name__=='__main__':main()
