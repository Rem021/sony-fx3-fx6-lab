#!/usr/bin/env python3
"""Find structural AArch64 4 KiB translation-table candidates in original WBI.

No snapshot execution, physical memory access, firmware modification or device I/O.
Candidate chains remain hypotheses until separate metadata reads agree.
"""
from pathlib import Path
import bisect,json,mmap,struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
MASK=0x0000fffffffff000


class Snapshot:
    def __init__(self):
        self.meta=json.loads((HERE/'wbi2-map-results.json').read_bytes())
        self.f=(ROOT/self.meta['source']).open('rb');self.data=mmap.mmap(self.f.fileno(),0,access=mmap.ACCESS_READ)
        self.sections=sorted([s for s in self.meta['sections'] if s['stored_bytes']],key=lambda s:int(s['physical_address'],16))
        self.starts=[int(s['physical_address'],16) for s in self.sections]
        self.by_file=sorted(self.sections,key=lambda s:int(s['data_file_offset'],16))
        self.file_starts=[int(s['data_file_offset'],16) for s in self.by_file]
    def physical(self,pa,n):
        i=bisect.bisect_right(self.starts,pa)-1
        if i<0:raise ValueError('physical address not stored')
        s=self.sections[i];start=self.starts[i]
        if pa+n>start+s['stored_bytes']:raise ValueError('physical span crosses stored section')
        off=int(s['data_file_offset'],16)+pa-start
        return self.data[off:off+n]
    def location(self,off,n=8):
        i=bisect.bisect_right(self.file_starts,off)-1
        if i<0:return None
        s=self.by_file[i];start=self.file_starts[i]
        if off+n>start+s['stored_bytes']:return None
        return int(s['physical_address'],16)+off-start
    def references(self,pa):
        assert pa&4095==0
        needle=struct.pack('<Q',pa)[2:6];off=self.meta['data_start'];end=off+self.meta['data_bytes'];hits=[]
        while (off:=self.data.find(needle,off,end))!=-1:
            pos=off-2;off+=1
            if pos<0 or (pos-self.meta['data_start'])%8:continue
            value=struct.unpack_from('<Q',self.data,pos)[0]
            if value&MASK!=pa or value&3!=3:continue
            address=self.location(pos)
            if address is None:continue
            hits.append(dict(descriptor_physical_address=hex(address),table_physical_address=hex(address&~4095),
                index=(address&4095)//8,value=hex(value),file_offset=hex(pos)))
        return hits
    def translate(self,root,va):
        assert root&4095==0 and 0<=va<1<<39
        table=root;steps=[]
        for shift in (30,21,12):
            index=(va>>shift)&511
            value=struct.unpack('<Q',self.physical(table+index*8,8))[0]
            steps.append(dict(table=hex(table),index=index,value=hex(value),shift=shift))
            if value&1==0:raise ValueError('invalid descriptor')
            if shift!=12 and value&3==1:
                mask=(1<<shift)-1;return (value&MASK&~mask)+(va&mask),steps
            if value&3!=3:raise ValueError('unexpected descriptor type')
            table=value&MASK
        return table+(va&4095),steps
    def virtual(self,root,va,n):
        result=[]
        while n:
            count=min(n,4096-(va&4095));pa,_=self.translate(root,va)
            result.append(self.physical(pa,count));va+=count;n-=count
        return b''.join(result)
    def close(self):self.data.close();self.f.close()


def main():
    snapshot=Snapshot();target=0x40ece2000;chains=[];leaves=snapshot.references(target)
    print('leaf descriptor candidates',len(leaves),flush=True)
    for leaf in leaves:
        middle=snapshot.references(int(leaf['table_physical_address'],16))
        for mid in middle:
            roots=snapshot.references(int(mid['table_physical_address'],16))
            for root in roots:
                va=(root['index']<<30)|(mid['index']<<21)|(leaf['index']<<12)
                root_pa=int(root['table_physical_address'],16)
                try:
                    got=snapshot.virtual(root_pa,va,128)
                    ok=got==snapshot.physical(target,128)
                except ValueError:ok=False
                chains.append(dict(leaf=leaf,middle=mid,root=root,root_physical_address=hex(root_pa),
                    userspace_va_candidate=hex(va),header_roundtrip_matches=ok))
    output=dict(status='STRUCTURAL_AARCH64_39BIT_PAGE_TABLE_CANDIDATES',target_physical_address=hex(target),
        source_sha256=snapshot.meta['source_sha256'],leaf_candidates=leaves,chains=chains,
        scope='Original stored WBI2 data, 4 KiB granule and 39-bit VA hypotheses. A recursive descriptor shape and header roundtrip alone do not establish process identity, active TTBR, correct non-header mappings, decrypted SKD code or update verification.')
    (HERE/'wbi-page-table-candidates.json').write_text(json.dumps(output,indent=2)+'\n');snapshot.close()
    print('candidate chains',len(chains),[(c['root_physical_address'],c['userspace_va_candidate'],c['header_roundtrip_matches']) for c in chains],flush=True)


if __name__=='__main__':main()
