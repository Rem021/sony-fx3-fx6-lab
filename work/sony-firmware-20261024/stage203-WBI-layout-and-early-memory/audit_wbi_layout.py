"""Read stock WBI2 as data. No mounting, guest execution, or device access."""
from pathlib import Path
from hashlib import sha256
import json,struct,mmap,re
H=Path(__file__).resolve().parent;B=H.parent
SRC=B/'stage2/extraction/nflasha5.img';EXPECTED='ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1'
prior=json.loads((B/'stage9-protocol/wbi/wbi2-section-map.json').read_text())
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
with SRC.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
    assert sha256(raw).hexdigest()==EXPECTED
    magic,padding,*v=struct.unpack_from('<4sI10Q',raw)
    fields=['sections','flag','resume_vector','dVersion','sector_size','r_data_size','kern_start','kern_size','kern_cksum','o_data_size']
    header=dict(zip(fields,v));assert magic==b'WBI2' and padding==0 and header['flag']==0 and header['sector_size']==512
    n=header['sections'];assert n==1399
    table=512+header['r_data_size'];end=table+64*n;assert end<=len(raw)
    sections=[];at=512
    for index in range(n):
        q=struct.unpack_from('<8Q',raw,table+64*index)
        row=dict(zip(['addr','rlen','cksum','flag','olen','virt','meta_cksum','padding'],q));row.update(index=index,file_offset=at)
        assert row['addr']%4096==0 and row['olen']>0 and row['olen']%4096==0 and row['flag'] in [0,1] and row['padding']==0
        assert (row['flag']==0 and row['rlen']==row['olen']) or (row['flag']==1 and row['rlen']==0)
        assert row['addr']+row['olen']<1<<64 and at+row['rlen']<=table
        check=0x0f0f0f0f
        for x in q[:6]:check^=x
        assert check==row['meta_cksum']
        assert row['virt']==row['addr']-0x400000000+0xffffffc000000000
        assert row['cksum']==0x0f0f0f0f # header flag lacks WBI_CKSUM; not a data-integrity result
        row['stored_sha256']=sha256(raw[at:at+row['rlen']]).hexdigest() if row['rlen'] else None
        sections.append(row);at+=row['rlen']
    assert at==table and sum(s['olen'] for s in sections)==header['o_data_size']
    ordered=sorted(sections,key=lambda s:s['addr']);assert all(a['addr']+a['olen']<=b['addr'] for a,b in zip(ordered,ordered[1:]))
    # Source descriptor order is intentionally retained. Do not assume it is physical order.
    transitions=[dict(after=a['index'],next=b['index']) for a,b in zip(sections,sections[1:]) if a['addr']+a['olen']>b['addr']]
    for new,old in zip(sections,prior['sections']):
        assert (new['addr'],new['rlen'],new['olen'],new['file_offset'],new['flag'],new['virt'])==(old['phys'],old['stored_size'],old['original_size'],old['file_offset'],old['flags'],old['virt'])
    assert len(sections)==len(prior['sections'])
    low=min(s['addr'] for s in sections);high=max(s['addr']+s['olen'] for s in sections)
    assert low==0x400001000 and high==0x420000000
    queries=[]
    for name,a,z in [('all_physical_below4GiB',0,0x100000000),('configured_current_NOR_load_region',0xfe049000,0xfe049000+101888)]:
        match=[s['index'] for s in sections if s['addr']<z and a<s['addr']+s['olen']]
        assert not match;queries.append(dict(name=name,start=hex(a),end_exclusive=hex(z),overlapping_declared_sections=match,scope='address coverage only, not actual chip/bootloader identity'))
    rv=header['resume_vector'];owner=[s for s in sections if s['addr']<=rv and rv+64<=s['addr']+s['rlen']];assert len(owner)==1
    s=owner[0];off=s['file_offset']+rv-s['addr'];resume=bytes(raw[off:off+64]);kernel=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/p3-main/vmlinux.bin';k=kernel.read_bytes()
    assert sha256(k).hexdigest()=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
    # Compare using observed source-layout base0x400000000 (16GiB) plus Image text_offset0x80000.
    # The address base is not a claim about total RAM capacity; retain all64 address bits.
    ram_base=0x400000000;text_offset=struct.unpack_from('<Q',k,8)[0];assert text_offset==0x80000
    image_phys=ram_base+text_offset;ko=rv-image_phys;assert ko==0x4267f0 and resume==k[ko:ko+64]
    tail=bytes(raw[end:]);tail_info=dict(offset=end,bytes=len(tail),nonzero_bytes=sum(x!=0 for x in tail),sha256=sha256(tail).hexdigest(),
        RBUF_offsets=[end+m.start() for m in re.finditer(b'RBUF',tail)],SUBS_offsets=[end+m.start() for m in re.finditer(b'SUBS',tail)],
        full_trailer_format_interpreted=False,not_counted_as_declared_restore_sections=True)
    assert len(tail)==261632 and tail_info['nonzero_bytes']==2298
    loader_matches=[]
    for name,p,expected in [('NOR',B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin','4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'),
      ('SPI',B/'stage198-AP-CP-loaders-and-partition-selection/originals/loader_spi.bin','314d372d0d2b9883c3b9dc04b40389edb3100e6d5ef529633cc427c3d0cab72e')]:
        b=p.read_bytes();assert sha256(b).hexdigest()==expected
        full=raw.find(b);anchors=[]
        for a in range(0,len(b)-127,4096):
            x=bytes(b[a:a+128]);hit=raw.find(x);anchors.append(dict(source_offset=a,matched=hit>=0,first_image_offset=hit if hit>=0 else None))
        loader_matches.append(dict(name=name,source=str(p),sha256=expected,bytes=len(b),exact_full_copy_offset=full if full>=0 else None,anchors128=anchors,absence_proves_only='no identical saved loader byte sequence at tested offsets, not absence of other/relocated/changed boot code'))
    put('WBI-layout-audit.json',dict(source=str(SRC),source_sha256=EXPECTED,source_bytes=len(raw),
      reference_layout='FX3Ver7.00 warmboot.h unsigned-long64 header88B/section64B plus wbi_raw.c and warm.c; shape and metadata XOR verified on stock7.02',
      header=header,header_bytes=88,table_offset=table,table_end_exclusive=end,metadata_xor_checked=n,source_order_not_sorted=transitions,
      sorted_physical_overlaps=0,stored_bytes=sum(s['rlen'] for s in sections),original_bytes=sum(s['olen'] for s in sections),zero_sections=sum(s['flag']==1 for s in sections),
      restored_phys_min=hex(low),restored_phys_end_exclusive=hex(high),machine_RAM_capacity_inferred=False,address_queries=queries,
      earlier_stage9_map_reverified=True,sections=sections,trailer=tail_info,
      resume=dict(physical=hex(rv),section=s['index'],file_offset=hex(off),bytes=64,sha256=sha256(resume).hexdigest(),
        matching_p3_kernel_source=str(kernel),kernel_sha256=sha256(k).hexdigest(),comparison_image_phys_base=hex(image_phys),kernel_file_offset=hex(ko),exact64B_equal=True,actual_runtime_entry_observed=False),
      exact_loader_copy_search=loader_matches,unknown_trailer_bytes_preserved=True,independent_AP_loader_or_boot0_recovered=False,
      limits=['declared restore addresses only; trailer not fully interpreted, and other boot-code copies/versions are not ruled out',
        'static official snapshot not current body RAM or backup; checksum XOR does not attest safe boot or actual restored state',
        'source-compatible7.00 layout is not complete7.02 build identity or bootloader implementation proof'],
      original_or_guest_execution=False,root_or_device_operations=0))
    put('resume-source-slice.json',dict(source_WBI=str(SRC),WBI_SHA256=EXPECTED,physical=hex(rv),file_offset=hex(off),bytes_hex=resume.hex(),sha256=sha256(resume).hexdigest(),comparison_kernel_offset=hex(ko),exact_match=True,execution=False))
    print(json.dumps(dict(sections=n,metadata_checks=n,zero_sections=sum(s['flag']==1 for s in sections),physical_span=[hex(low),hex(high)],resume_kernel_match=True,trailer_bytes=len(tail),trailer_nonzero=tail_info['nonzero_bytes'],loader_full_copies=[(r['name'],r['exact_full_copy_offset']) for r in loader_matches],anchor_hits=[(r['name'],sum(a['matched'] for a in r['anchors128'])) for r in loader_matches],device_operations=0)))
