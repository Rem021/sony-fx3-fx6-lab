#!/usr/bin/env python3
"""Pin embedded descriptor and dump only initialized guest table bytes, no full-memory fabrication."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from bootstrap_guest import Guest,SOURCE,PIN,BASE
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    target=HERE/'boot-state-evidence.json';assert not target.exists();raw=SOURCE.read_bytes();assert sha(raw)==PIN
    original=HERE/'original-files';original.mkdir();descriptor=raw[0x20000:0x2017c];(original/'CP-boot-descriptor.bin').write_bytes(descriptor)
    assert raw[0xda0:0xda0+380]==bytes(380)
    assert sha(descriptor)=='543e6e57aa6ebb26257a96e3a28c59068cbd5eb9fef26c67ed8684c7fc05f50b'
    fields={hex(i):hex(struct.unpack_from('<I',descriptor,i)[0]) for i in range(0,len(descriptor),4)}
    fragments=[];folder=HERE/'source-fragments';folder.mkdir()
    for a,z in [(0x108398,0x108768),(0x108768,0x108974),(0x108974,0x108998),(0x1089e4,0x108a04),
        (0x108a04,0x108d98),(0x553d48,0x553fb8),(0x54bbd0,0x54bbf4),(0x554ebc,0x555010),(0x53894c,0x53898c)]:
        b=raw[a-BASE:z-BASE];dest=folder/f'{a:08x}-{z:08x}.txt'
        dest.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in Cs(CS_ARCH_ARM,CS_MODE_ARM).disasm(b,a))+'\n')
        fragments.append(dict(start_VA=hex(a),end_VA=hex(z),bytes=len(b),original_bytes_SHA256=sha(b),listing=str(dest.relative_to(HERE))))
    g=Guest(raw,0);r=g.call(0x1083a4,stops={0x108728:'before_CPU_setup_call'});assert r['boundary']['PC']=='0x108728'
    l1=g.words(0x108f1c,1)[0];l2=g.words(0x108d98,1)[0];meta=g.words(0x1007000,6)
    assert l1==int(fields['0x15c'],16)==0x14e8000 and l2==int(fields['0x168'],16)==0x14ec000
    state=HERE/'guest-state';state.mkdir();dumps=[]
    def dump(at,n,name):
        assert n>0 and all(g.init[at-BASE:at-BASE+n])
        b=bytes(g.u.mem_read(at,n));dest=state/name;dest.write_bytes(b)
        dumps.append(dict(address=hex(at),bytes=n,sha256=sha(b),path=str(dest.relative_to(HERE)),all_bytes_initialized_by_original_RAM_code=True))
        return b
    l1bytes=dump(l1,0x4000,'L1-before-CPU-setup-flag0.bin');l1words=struct.unpack('<4096I',l1bytes)
    mask=g.init[l2-BASE:l2-BASE+0x8000];i=0;l2_ranges=[]
    while i<len(mask):
        if not mask[i]:i+=1;continue
        start=i
        while i<len(mask) and mask[i]:i+=1
        l2_ranges.append(dict(offset=hex(start),bytes=i-start));dump(l2+start,i-start,f'L2-initialized-{start:04x}-{i:04x}.bin')
    dump(0x1007000,24,'boot-metadata-before-CPU-setup.bin')
    assert sum(r['bytes'] for r in l2_ranges)==meta[2]*1024
    result=dict(CP_source=str(SOURCE),CP_sha256=PIN,embedded_descriptor=dict(VA='0x128000',file_offset='0x20000',bytes=380,
        sha256=sha(descriptor),path='original-files/CP-boot-descriptor.bin',fields_u32_le=fields),
        original_local_copy_target=dict(VA='0x108da0',bytes=380,source_original_all_zero=True,
            copied_equals_embedded_descriptor=bytes(g.u.mem_read(0x108da0,380))==descriptor),
        source_fragments=fragments,guest_prefix=r,table_addresses=dict(L1=hex(l1),L2=hex(l2)),
        bootstrap_metadata=[hex(x) for x in meta],L1_entry_type_counts={str(k):sum(w&3==k for w in l1words) for k in range(4)},
        L2_initialized_ranges=l2_ranges,L2_unused_bytes_not_dumped=0x8000-sum(r['bytes'] for r in l2_ranges),dumps=dumps,
        DMM_candidate_initial_L1_entry=dict(address='0x09a08e00',L1_index=0x9a,raw_descriptor=hex(l1words[0x9a])),
        scope='Original CP embedded data and original guest producer. Optional hardware flag0 is a declared fixture and initial real poll is not run. No CPU/TLB setup or actual device acceptance; unspecified L2 RAM bytes are omitted, never treated as recovered zeros. No image buffer or RAW pixels.')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(descriptor_bytes=380,L1=hex(l1),L2=hex(l2),L1_entries=len(l1words),L2_initialized_bytes=sum(r['bytes'] for r in l2_ranges),L2_unknown_bytes_omitted=result['L2_unused_bytes_not_dumped'],candidate_descriptor=result['DMM_candidate_initial_L1_entry']['raw_descriptor'])))
if __name__=='__main__':main()
