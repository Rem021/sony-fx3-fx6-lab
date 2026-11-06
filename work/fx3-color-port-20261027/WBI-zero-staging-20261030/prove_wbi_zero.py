#!/usr/bin/env python3
"""Tie original WBI records to the reference zero-fill branch without restoring RAM."""
import datetime,hashlib,importlib.util,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from unicorn import arm64_const as R
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;FW=HERE.parents[2]/'work/sony-firmware-20261024'
TABLE_PAGE=0xfe06d000;SCRATCH=0xfe06c100
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);h=importlib.util.module_from_spec(s);s.loader.exec_module(h);return h


def main():
    assert not (HERE/'WBI-zero-proof.json').exists()
    prev=TASK/'escape-file-read-contract-20261030';seal=(prev/'final-receipt.json').read_bytes()
    assert sha(seal)=='8b87f71b12bd74f998be1c8bc4f45131bc246346a7543570356fdf5011590748'
    previous=json.loads(seal)
    for x in previous['files']:
        b=(prev/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256']
    parent=TASK/'AP-staging-record-routing-20261030';pins=json.loads((parent/'final-receipt.json').read_text());hp=parent/'prove_staging.py'
    assert sha(hp.read_bytes())==next(x for x in pins['files'] if x['path']==hp.name)['sha256']
    H=module('pinned_RAM_harness',hp)
    ap=(FW/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin').read_bytes();assert sha(ap)==H.PINS['AP']
    banks=[(TASK/f'dmm-backup-20261029/original-records/canonical-bank{n}.bin').read_bytes() for n in [0,1]]
    for n,b in enumerate(banks):assert sha(b)==H.PINS[f'bank{n}']
    source=FW/'stage2/extraction/nflasha5.img';raw=source.read_bytes()
    assert sha(raw)=='ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1'
    h=struct.unpack_from('<11Q',raw);assert h[0]==int.from_bytes(b'WBI2','little') and h[1]==1399 and h[2]==0 and h[5]==512
    table=h[5]+h[6];end=table+h[1]*64;assert end<=len(raw)
    cursor=512;rows=[]
    for i in range(h[1]):
        off=table+i*64;entry=raw[off:off+64];v=struct.unpack('<8Q',entry)
        address,rlen,cksum,flag,olen,virt,meta,padding=v
        assert flag in [0,1] and olen>0 and olen%4096==0 and address%4096==0 and padding==0
        assert (flag==0 and rlen==olen) or (flag==1 and rlen==0)
        assert cksum==0x0f0f0f0f and cursor+rlen<=table
        xor=0x0f0f0f0f
        for word in v[:6]:xor^=word
        assert xor==meta
        assert virt==0xffffffc000000000+address-0x400000000
        rows.append(dict(index=i,record_file_offset=hex(off),record_sha256=sha(entry),physical_start=hex(address),
            physical_end_exclusive=hex(address+olen),stored_bytes=rlen,original_bytes=olen,flag=flag,
            stored_file_offset=hex(cursor) if rlen else None,metadata_xor_verified=True))
        cursor+=rlen
    assert cursor==table and sum(x['original_bytes'] for x in rows)==h[10]
    assert sum(x['flag']==1 for x in rows)==82
    ordered=sorted(rows,key=lambda x:int(x['physical_start'],16))
    assert all(int(a['physical_end_exclusive'],16)<=int(b['physical_start'],16) for a,b in zip(ordered,ordered[1:]))
    # Reuse original-default bindings sealed in the preceding address stage.
    context=json.loads((parent/'staging-proof.json').read_text())['independent_original_fragments']
    a=int(context['AP_context_fields']['0x38'],16);cap=int(context['AP_context_fields']['0x40'],16)
    b=int(context['AP_context_fields']['0x48'],16);n=int(context['CP_context_fields']['0x220'],16);m=int(context['CP_context_fields']['0x230'],16)
    queries=[]
    for label,start,length in [('AP_primary_declared_staging',a,cap),('AP_primary_actual_transfer_projection',a,n),
                                ('AP_secondary_source_projection',b,m)]:
        hits=[x['index'] for x in rows if int(x['physical_start'],16)<start+length and start<int(x['physical_end_exclusive'],16)]
        assert not hits
        queries.append(dict(name=label,start=hex(start),end_exclusive=hex(start+length),bytes=length,
                            overlapping_any_WBI_records=hits,overlapping_zero_records=[]))
    left=max((x for x in rows if int(x['physical_end_exclusive'],16)<=a),key=lambda x:int(x['physical_end_exclusive'],16))
    right=min((x for x in rows if int(x['physical_start'],16)>=b+m),key=lambda x:int(x['physical_start'],16))
    assert int(left['physical_end_exclusive'],16)==0x4110c4000 and int(right['physical_start'],16)==0x41a000000
    # Original Sony 7.00 reference source, never imported or executed.
    src=FW/'stage203-WBI-layout-and-early-memory';capture=json.loads((src/'reference-source-capture.json').read_text())
    expected={'linux-kernel/include/linux/warmboot.h':'ccd4d6b7b1e73ebab557dc0c99bf454aea20da5b31a6975c7605483f2bcaf5a1',
              'linux-kernel/kernel/power/wbi_raw.c':'7e3e7c718fa285aba18115aa7b663860cc848432030db38acb2c0718db0ee1e8'}
    source_cuts=[]
    for name,pin in expected.items():
        item=next(x for x in capture['captures'] if x['member']==name);p=Path(item['output']);text=p.read_text()
        assert sha(p.read_bytes())==pin==item['sha256'];lines=text.splitlines()
        lo,hi=(80,90) if name.endswith('warmboot.h') else (101,111)
        source_cuts.append(dict(path=str(p),sha256=pin,source_label=capture['source_label'],line_start=lo,line_end=hi,
                                text='\n'.join(lines[lo-1:hi])))

    class WbiRAM(H.RAM):
        def __init__(self):
            super().__init__(ap,banks);self.mutable.append((SCRATCH,SCRATCH+64))
        def code(self,u,pc,size,unused):
            if pc in self.ends:self.stop(self.ends[pc]);return
            if pc==0xfe056298:self.stop('before_original_DMA_init_helper');return
            if pc==0xfe055530:self.stop('before_original_diagnostic');return
            windows=[(0xfe0597d0,0xfe0597f4),(0xfe059804,0xfe059838),(0xfe059908,0xfe059940),
                     (0xfe04b444,0xfe04b470),(0xfe04c0fc,0xfe04c244)]
            if not any(lo<=pc<hi for lo,hi in windows):self.stop('before_outside_scoped_original_code');return
            i=next(H.MD.disasm(ap[pc-H.AP_BASE:pc-H.AP_BASE+4],pc),None)
            if i is None or i.mnemonic in ['mrs','msr','sys','dc','ic','tlbi','eret','svc','hvc','smc']:
                self.stop('before_privileged_or_undecoded_instruction');return
            self.trace.append(pc)

    fragments=[]
    for index in [1,44]:
        r=rows[index];record=raw[table+64*index:table+64*(index+1)]
        page=raw[table+(index//8)*512:table+(index//8+1)*512];assert len(page)==512
        ram=WbiRAM();ram.seed(TABLE_PAGE,page)
        result=ram.run(0xfe0597d0,registers={'X20':index,'X21':0xfe06a000,'X24':SCRATCH},
                       ends={0xfe059834:'before_original_stored_record_diagnostic',0xfe059924:'before_original_zero_record_diagnostic'})
        assert bytes(ram.u.mem_read(SCRATCH,64))==record
        assert result['boundary']['reason']==('before_original_zero_record_diagnostic' if r['flag'] else 'before_original_stored_record_diagnostic')
        if r['flag']:
            assert int(result['X2'],16)==int(r['physical_start'],16)
            assert int(result['X3'],16)==int(r['physical_end_exclusive'],16)-1
        fragments.append(dict(record=r,metadata_source_page_sha256=sha(page),prefix_after_unexecuted_metadata_read=result,
            original_64B_record_copy_exact=True,metadata_read_success_reply_supplied=False))
    late=WbiRAM();zero=rows[44];record=raw[table+44*64:table+45*64];late.seed(SCRATCH,record)
    after=late.run(0xfe059928,registers={'X24':SCRATCH})
    assert after['boundary']['reason']=='before_original_DMA_init_helper'
    assert late.u.reg_read(R.UC_ARM64_REG_X23)==int(zero['physical_start'],16) and late.u.reg_read(R.UC_ARM64_REG_X24)==zero['original_bytes']
    after.update(destination=zero['physical_start'],original_bytes=zero['original_bytes'],DMA_init_executed=False,
                 scope='Independent entry after unresolved diagnostic; no diagnostic reply or DMA success is supplied.')
    cuts=[];listing=HERE/'listings';listing.mkdir(exist_ok=False)
    for label,lo,hi in [('reference-WBI-table-copy-and-flag-dispatch',0xfe0597d0,0xfe059844),
                         ('reference-WBI-zero-fill-branch',0xfe059908,0xfe0599d0),
                         ('reference-WBI-table-read-loop',0xfe059728,0xfe0597d0),
                         ('reference-WBI-load-entry',0xfe0596e4,0xfe059728)]:
        x=ap[lo-H.AP_BASE:hi-H.AP_BASE];p=listing/(label+'.txt')
        p.write_text('\n'.join(f'{i.address:#x}: {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in H.MD.disasm(x,lo))+'\n')
        cuts.append(dict(begin=hex(lo),end_exclusive=hex(hi),original_bytes_sha256=sha(x),listing=str(p.relative_to(HERE))))
    (HERE/'WBI-record-inventory.json').write_text(json.dumps(dict(source=str(source),source_sha256=sha(raw),
        header_raw_u64=[hex(x) for x in h],metadata_start=hex(table),metadata_end_exclusive=hex(end),
        record_count=len(rows),zero_records=82,metadata_sha256=sha(raw[table:end]),records=rows,
        rows_are_declared_restoration_not_observed_RAM=True,omitted_bytes_synthesized=False),indent=2)+'\n')
    proof=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),previous_receipt_sha256=sha(seal),
        previous_files_reverified=len(previous['files']),AP_reference_sha256=sha(ap),AP_reference_model='A7 IV v2.00, not current FX3 AP boot',
        original_FX3_WBI_sha256=sha(raw),section_queries=queries,nearest_WBI_neighbors=dict(left=left,right=right),
        no_record_gap=dict(start=left['physical_end_exclusive'],end_exclusive=right['physical_start'],
                          bytes=int(right['physical_start'],16)-int(left['physical_end_exclusive'],16)),
        original_reference_fragments=fragments,independent_after_diagnostic_fragment=after,official_reference_source_cuts=source_cuts,
        source_windows=cuts,selected_flag1_semantics='Official WBI_SH_ZERO=1; no stored section data, reference AP routes bit0 to its zero-fill-labelled DMA branch.',
        any_staging_initialization_by_this_WBI_proved=False,any_earlier_whole_boot_initialization_ruled_out=False,
        boundaries=dict(WBI_restored=False,zero_RAM_synthesized=False,metadata_block_read_or_DMA_executed=False,
            helper_substitutions_or_fake_success_replies=0,device_operations=0,originals_modified=False,other_owner_files_written=False,
            current_FX3_AP_or_Backup_obtained=False,full_private_ISP_RAW_or_flashable_modified_package_produced=False,goal_complete=False))
    (HERE/'WBI-zero-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(sections=len(rows),zero_records=82,staging_overlaps=[q['overlapping_any_WBI_records'] for q in queries],
                         original_fragments=[x['prefix_after_unexecuted_metadata_read']['boundary'] for x in fragments],
                         late_fragment=after['boundary'],actual_DMA_or_restore=False,goal_complete=False)))


if __name__=='__main__':main()
