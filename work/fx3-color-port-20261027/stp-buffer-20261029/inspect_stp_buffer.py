#!/usr/bin/env python3
"""Pin original STP allocation/MMIO and image-query producer source windows."""
import hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN

def main():
    previous=TASK/'frame-route-20261029';receipt=previous/'final-receipt.json'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()=='ab686ac5273122b91557a076c7e382ecfd41cb581599e321e8fcd52ed70e2539'
    manifest=json.loads(receipt.read_text())
    for row in manifest['files']:
        body=(previous/row['path']).read_bytes();assert len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256']
    raw=image();md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);dest=HERE/'source-fragments';dest.mkdir(exist_ok=True);fragments=[]
    windows=[(0x37b078,0x37b1e0,'stp-allocator'),(0x37b250,0x37b292,'stp-lock-wrapper'),(0x93fdcc,0x93fe10,'stp-unlock-wrapper'),
             (0x37c8c0,0x37c8e4,'quiet-log-entry'),(0x37c994,0x37c9a2,'quiet-log-return'),(0x93fb88,0x93fbf0,'stp-initialization'),
             (0x36c024,0x36c03c,'register-dispatch-entry'),(0x36c306,0x36c34c,'selected-register-writes'),
             (0x300242,0x300252,'mode-input-producer'),(0x300282,0x30028a,'query-selector-producer'),
             (0x303746,0x303764,'buffer-kind-producer'),(0x303184,0x30319a,'buffer-kind-three-producer'),(0x307040,0x30706e,'buffer-kind-four-producer'),
             (0x597a1a,0x597a52,'mode-default-wrapper'),(0x149fa4,0x14a17e,'mode-default-dispatch'),
             (0x320438,0x3205a8,'image-query-branch'),(0x3205c4,0x320608,'image-query-wrapper')]
    for lo,hi,label in windows:
        body=raw[lo:hi];p=dest/(label+'.txt');p.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(body,BASE+lo))+'\n')
        fragments.append(dict(file_offset=hex(lo),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),label=label,listing=str(p.relative_to(HERE)),bounds='explicit source window; embedded switch data is not instruction-execution evidence'))
    tables=[]
    for va,n,width in [(0x47403c,144,2),(0x473458,144,2),(0x252094,5,1)]:
        body=raw[va-BASE:va-BASE+n]
        entry=dict(va=hex(va),bytes=n,sha256=hashlib.sha256(body).hexdigest(),element_bytes=width)
        if width==2:entry['selected_targets']={hex(i):hex(va+2*struct.unpack_from('<H',body,2*i)[0]) for i in [0x22,0x23,0x24,0x25]}
        else:entry['targets']=[hex(va+2*x) for x in body]
        tables.append(entry)
    assert tables[0]['selected_targets']['0x22']=='0x474306'
    candidates=[]
    for at in range(0,0x9c0000,2):
        a,z=struct.unpack_from('<HH',raw,at)
        if a&0xfbf0!=0xf240 or z&0x8000:continue
        imm=((a&15)<<12)|((a&0x400)<<1)|((z&0x7000)>>4)|(z&255)
        if imm!=0x15d8:continue
        ins=next(md.disasm(raw[at:at+4],BASE+at,count=1),None)
        if ins and ins.mnemonic=='movw':candidates.append(dict(file_offset=hex(at),instruction=ins.mnemonic+' '+ins.op_str))
    at=0xd9cfde-BASE;text=raw[at:raw.index(0,at)]
    result=dict(cp_sha256=PIN,previous_files_verified=len(manifest['files']),source_fragments=fragments,switch_tables=tables,field_15d8_candidates=candidates,
                source_diagnostic=dict(va='0xd9cfde',value=text.decode(),sha256=hashlib.sha256(text+b'\0').hexdigest()),
                scope='Read-only original source windows, explicit switch data and immediate candidates. Runtime MMIO values, locks, physical STP ownership, normal input modes and image buffers are not supplied by static source.')
    (HERE/'stp-buffer-source-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(previous_files_verified=len(manifest['files']),source_fragments=len(fragments),switch_tables=len(tables),field_candidates=len(candidates))))

if __name__=='__main__':main()
