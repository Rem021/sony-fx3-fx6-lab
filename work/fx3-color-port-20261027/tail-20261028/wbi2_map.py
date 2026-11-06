#!/usr/bin/env python3
"""Recover stored-section provenance from this pinned WBI2, retaining omitted sections as unknown."""
from pathlib import Path
from hashlib import sha256,file_digest
import json,struct,mmap,collections

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
IMAGE=ROOT/'work/sony-firmware-20261024/stage2/extraction/nflasha5.img'
PIN='ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1'


def parse(b):
    h=struct.unpack_from('<11Q',b);assert h[0]==int.from_bytes(b'WBI2','little')
    assert h[4]==0x20060224 and h[5]==512 and h[2]==0
    count,data_bytes=h[1],h[6];data_start=h[5];table=data_start+data_bytes
    assert count==1399 and table+count*64<=len(b)
    rows=[];cursor=data_start
    for i in range(count):
        v=struct.unpack_from('<8Q',b,table+i*64);physical,stored,check,flag,original,alias,raw6,raw7=v
        assert original>0 and physical%4096==0 and original%4096==0
        assert alias==0xffffffc000000000+(physical-0x400000000)
        assert check==0x0f0f0f0f and raw7==0
        assert (flag==0 and stored==original) or (flag==1 and stored==0)
        assert cursor+stored<=table
        row=dict(index=i,record_offset=hex(table+i*64),physical_address=hex(physical),
                 kernel_linear_alias=hex(alias),stored_bytes=stored,original_bytes=original,flag_raw=flag,
                 checksum_raw=hex(check),raw6=hex(raw6),raw7=hex(raw7),
                 data_file_offset=hex(cursor) if stored else None,
                 interpretation='stored bytes, directly bounded in original image' if stored else 'no stored bytes; restoration semantics unresolved; no zero bytes synthesized')
        if stored:row['stored_sha256']=sha256(b[cursor:cursor+stored]).hexdigest()
        rows.append(row);cursor+=stored
    assert cursor==table and sum(r['original_bytes'] for r in rows)==h[10]
    return h,table,rows


def main():
    with IMAGE.open('rb') as f:assert file_digest(f,'sha256').hexdigest()==PIN
    with IMAGE.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as b:
        h,table,rows=parse(b);candidates=[]
        for token in [b'sdfileinput',b'libInfraSKD',b'BODYDATA',b'FDAT']:
            start=0;hits=[]
            while (o:=b.find(token,start))>=0:
                start=o+len(token);match=None
                for row in rows:
                    if row['data_file_offset'] is None:continue
                    a=int(row['data_file_offset'],16)
                    if a<=o and o+len(token)<=a+row['stored_bytes']:
                        match=dict(section=row['index'],physical_address=hex(int(row['physical_address'],16)+o-a),
                                   kernel_linear_alias=hex(int(row['kernel_linear_alias'],16)+o-a));break
                hits.append(dict(file_offset=hex(o),stored_section_mapping=match))
            candidates.append(dict(token=token.decode(),hits=hits))
        physical_overlaps=[]
        ordered=sorted(rows,key=lambda r:int(r['physical_address'],16))
        for n,left in enumerate(ordered):
            a=int(left['physical_address'],16);z=a+left['original_bytes']
            for right in ordered[n+1:]:
                c=int(right['physical_address'],16);d=c+right['original_bytes']
                if c>=z:break
                physical_overlaps.append(dict(records=[left['index'],right['index']],
                                              physical_start=hex(max(a,c)),bytes=min(z,d)-max(a,c),
                                              flags=[left['flag_raw'],right['flag_raw']]))
        tail=table+len(rows)*64
        result=dict(status='PASS_PINNED_WBI2_STORED_SECTION_PROVENANCE',source=str(IMAGE.relative_to(ROOT)),source_sha256=PIN,
                    header_raw_u64=[hex(x) for x in h],data_start=512,data_bytes=h[6],metadata_start=hex(table),
                    metadata_end=hex(tail),trailing_bytes=len(b)-tail,trailing_sha256=sha256(b[tail:]).hexdigest(),
                    section_count=len(rows),stored_section_count=sum(bool(r['stored_bytes']) for r in rows),
                    omitted_section_count=sum(not r['stored_bytes'] for r in rows),sections=rows,string_candidates=candidates,
                    physical_overlaps=physical_overlaps,
                    scope='Format inference cross-checked against exact byte counts, metadata ranges, aligned physical regions and kernel linear aliases. Record order is not globally ascending; overlapping regions are retained explicitly and restore precedence is not assumed. Unknown flag-1 restoration and trailing bytes remain uninterpreted. No native WBI restore executed, no per-section checksum claim, no full RAM image or flashable WBI constructed. Kernel linear aliases are not userspace ELF virtual addresses.')
    (HERE/'wbi2-map-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'sections',len(rows),'stored',result['stored_section_count'],'omitted',result['omitted_section_count'])


if __name__=='__main__':main()
