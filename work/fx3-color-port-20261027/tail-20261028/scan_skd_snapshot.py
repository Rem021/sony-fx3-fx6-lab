#!/usr/bin/env python3
"""Compare pinned protected SKD entry stubs with original WBI2 stored bytes."""
from pathlib import Path
from hashlib import sha256,file_digest
import json,mmap

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def main():
    meta=json.loads((HERE/'wbi2-map-results.json').read_bytes());source=ROOT/meta['source']
    original=(HERE/'libraries/libInfraSKD.so').read_bytes()
    libmeta=json.loads((HERE/'skd-library-inventory.json').read_bytes());assert sha256(original).hexdigest()==libmeta['sha256']
    sections=[s for s in meta['sections'] if s['stored_bytes']]
    candidates=[s for s in libmeta['symbols'] if s['type']=='STT_FUNC' and s['section']!='SHN_UNDEF' and s['bytes']>=8]
    results=[]
    with source.open('rb') as f:
        assert file_digest(f,'sha256').hexdigest()==meta['source_sha256']
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
            for symbol in candidates:
                va=int(symbol['va'],16);needle=original[va:va+8];pos=meta['data_start'];hits=[]
                while (pos:=data.find(needle,pos,meta['data_start']+meta['data_bytes']))!=-1:
                    owners=[s for s in sections if int(s['data_file_offset'],16)<=pos and pos+8<=int(s['data_file_offset'],16)+s['stored_bytes']]
                    if len(owners)!=1:pos+=1;continue
                    owner=owners[0];off=int(owner['data_file_offset'],16);n=min(symbol['bytes'],off+owner['stored_bytes']-pos)
                    sample=data[pos:pos+n];match=sample==original[va:va+n]
                    hits.append(dict(file_offset=hex(pos),physical_address=hex(int(owner['physical_address'],16)+pos-off),
                        wbi_section=owner['index'],compared_bytes=n,entire_compared_span_matches_file=match,
                        snapshot_span_sha256=sha256(sample).hexdigest()))
                    pos+=1
                results.append(dict(symbol=symbol,hits=hits))
    output=dict(status='PASS_ORIGINAL_SNAPSHOT_SKD_STUB_SCAN',wbi_source_sha256=meta['source_sha256'],
        library_sha256=libmeta['sha256'],results=results,
        scope='Exact first-eight-byte candidate scan over original stored WBI2 data only. Physical location does not establish a userspace mapping, runtime function identity, decryption, execution, tail validation or update admission. A missing exact stub also does not prove a function absent from the snapshot.')
    (HERE/'skd-snapshot-scan-results.json').write_text(json.dumps(output,indent=2)+'\n')
    for row in results:print(row['symbol']['name'],'hits',len(row['hits']),'changed_spans',sum(not h['entire_compared_span_matches_file'] for h in row['hits']))


if __name__=='__main__':main()
