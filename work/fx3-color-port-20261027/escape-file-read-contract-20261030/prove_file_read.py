#!/usr/bin/env python3
"""Original reference FAT fragments using the unchanged FX3 p8 image."""
import datetime, hashlib, importlib.util, json, struct, sys
from pathlib import Path
sys.dont_write_bytecode=True
from unicorn import UC_HOOK_CODE, UC_PROT_READ
from unicorn import arm64_const as R
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
PROJECT=HERE.parents[2]
FW=PROJECT/'work/sony-firmware-20261024'
ROOT=0x100500000
FAT=0x100600000


def sha(b): return hashlib.sha256(b).hexdigest()
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def main():
    assert not (HERE/'file-read-proof.json').exists()
    prev=TASK/'AP-staging-record-routing-20261030'
    raw=(prev/'final-receipt.json').read_bytes()
    assert sha(raw)=='6bd744f39317d8a8761f74e7a86093a460a46397ac6e236d33670e21bf767ff7'
    previous=json.loads(raw)
    for f in previous['files']:
        b=(prev/f['path']).read_bytes();assert len(b)==f['bytes'] and sha(b)==f['sha256']
    H=load_module('pinned_owned_RAM_harness',prev/'prove_staging.py')
    ap=(FW/'stage204-public-AP-boot-reference/reference/emmc_boot/esram_0xfe040000.bin').read_bytes()
    assert sha(ap)==H.PINS['AP']
    banks=[(TASK/f'dmm-backup-20261029/original-records/canonical-bank{n}.bin').read_bytes() for n in [0,1]]
    for n,b in enumerate(banks):assert sha(b)==H.PINS[f'bank{n}']
    reader=FW/'stage2/extraction/read_filesystems.py'
    assert sha(reader.read_bytes())=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    fs_module=load_module('pinned_FS_reader',reader)
    image=FW/'stage2/extraction/nflasha8.img'
    assert sha(image.read_bytes())=='3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b'
    fs=fs_module.FAT16(image)
    entries={x['path']:x for x in fs.walk()}
    assert (fs.ss,fs.spc,fs.bits,fs.root,fs.dataoff)==(512,32,12,49152,65536)
    fat_bytes=bytes(fs.b[fs.res*fs.ss:(fs.res+fs.spf)*fs.ss])
    root_bytes=bytes(fs.b[fs.root:fs.root+fs.nr*32])

    class FileRAM(H.RAM):
        def __init__(self):
            super().__init__(ap,banks)
            self.mutable += [(0xfe06a018,0xfe06a020),(0xfe06ac18,0xfe06ac28)]
            self.map(ROOT,root_bytes,UC_PROT_READ);self.sources.append((ROOT,ROOT+len(root_bytes)))
            self.map(FAT,fat_bytes,UC_PROT_READ);self.sources.append((FAT,FAT+len(fat_bytes)))
            # Original p8 BPB/root/FAT bytes; mount and hardware are not run.
            self.seed(0xfe06aa00,bytes(fs.b[:512]))
            self.seed(0xfe06ac00,H.packed(ROOT))
            self.seed(0xfe06a9e0,H.packed(FAT))
            for address,value in [(0xfe06a330,fs.ss*fs.spc),(0xfe06a334,fs.bits),
                                  (0xfe06a338,8),(0xfe06a340,fs.dataoff//fs.ss)]:
                self.seed(address,struct.pack('<I',value))

        def code(self,u,pc,size,unused):
            if pc==H.RETURN:self.stop('original_function_return');return
            if pc in self.ends:self.stop(self.ends[pc]);return
            if pc==0xfe055530:self.stop('before_original_diagnostic');return
            if pc==0xfe058b54:self.stop('before_original_block_dispatch');return
            windows=[(0xfe04a0e8,0xfe04a104),(0xfe04a520,0xfe04a57c),
                     (0xfe04b1a0,0xfe04b29c),(0xfe04b2c4,0xfe04b34c),
                     (0xfe04b58c,0xfe04b5a0),(0xfe04c2d0,0xfe04c2d8),
                     (0xfe062f0c,0xfe062f48),(0xfe04e224,0xfe04e3dc),
                     (0xfe05a354,0xfe05a3b4),(0xfe05a610,0xfe05a674),
                     (0xfe05a674,0xfe05a84c),(0xfe04e424,0xfe04e580),
                     (0xfe04b444,0xfe04b470),(0xfe04c0fc,0xfe04c244)]
            if not any(a<=pc<z for a,z in windows):self.stop('before_outside_scoped_original_code');return
            i=next(H.MD.disasm(ap[pc-H.AP_BASE:pc-H.AP_BASE+4],pc),None)
            if i is None or i.mnemonic in ['mrs','msr','sys','dc','ic','tlbi','eret','svc','hvc','smc']:
                self.stop('before_privileged_or_undecoded_instruction');return
            self.trace.append(pc)

        def query_root(self,name):
            # Execute the original libc ctype initializer, not a toupper stub.
            init=self.run(0xfe04a0e8,ends={0xfe04a104:'before_original_initializer_epilogue'})
            assert init['boundary']['reason']=='before_original_initializer_epilogue'
            assert self.qword(0xfe06a018)==0xfe06901d
            self.seed(H.OUT,name.encode()+b'\0'*8)
            q=self.run(0xfe05a354,registers={'X20':H.OUT,'X23':0xfe06ac08,'X24':0xfe06a000,'W22':0},
                       ends={0xfe05a640:'before_original_query_epilogue'})
            assert q['boundary']['reason']=='before_original_query_epilogue',q
            value=int(q['X0'],16)&0xffffffff
            signed=value if value<0x80000000 else value-0x100000000
            matched=entries.get('/'+name)
            assert signed==(matched['size'] if matched else -408)
            return dict(name=name,ctype_initializer=init,query_fragment=q,returned_size_or_error=signed,
                        file_metadata=dict(cluster=struct.unpack('<I',self.u.mem_read(0xfe06ac20,4))[0],
                                           remaining_bytes=struct.unpack('<I',self.u.mem_read(0xfe06ac24,4))[0]) if matched else None)

    cases=[]
    for name in ['DmmCfg.bin','cpImg.dat','OldAmtCL.bin','SysSound.bin','bonobo.bin','defdet.bin','psd.bin','lensfile.bin']:
        ram=FileRAM();cases.append(ram.query_root(name))
    dmm=entries['/DmmCfg.bin'];assert (dmm['cluster'],dmm['size'])==(5,43320)
    ram=FileRAM();query=ram.query_root('DmmCfg.bin')
    # The original lookup writes cluster/remaining bytes at C20/C24, which is
    # exactly the state used by the original read routine at A674.
    assert query['file_metadata']==dict(cluster=5,remaining_bytes=43320)
    dest=0x4132d8e00
    read_prefix=ram.run(0xfe05a674,[dest,dmm['size']])
    assert read_prefix['boundary']['reason']=='before_original_block_dispatch',read_prefix
    assert [int(read_prefix[x],16) for x in ['X0','X1','X2','X3']]==[8,dest,224,84]
    assert struct.unpack('<II',ram.u.mem_read(0xfe06ac20,8))==(7,0)
    # Independent fragment after a possible full-sector read: no block-reader
    # return is supplied and no block operation is executed.
    tail_request=FileRAM()
    tail_call=tail_request.run(0xfe04e4f4,registers={'W19':43320,'W21':5,'W22':84,'W24':312,'W25':32,'X20':dest})
    assert tail_call['boundary']['reason']=='before_original_block_dispatch'
    assert [int(tail_call[x],16) for x in ['X0','X1','X2','X3']]==[8,0xfe06bf00,308,1]
    original_sector=bytes(fs.b[308*512:309*512])
    original_file=fs.data(dmm['cluster'],dmm['size'])
    assert original_sector[:312]==original_file[43008:43320]
    tail=FileRAM();slot_bytes=102400;page=dest&~4095
    tail.u.mem_map(page,((dest-page+slot_bytes+4095)//4096)*4096)
    tail.mutable.append((dest,dest+slot_bytes))
    tail.seed(dest,b'\xa5'*slot_bytes)
    tail.seed(0xfe06bf00,original_sector)
    copy=tail.run(0xfe04e54c,registers={'W19':43320,'W24':312,'X20':dest},
                  ends={0xfe04e568:'before_original_cluster_read_epilogue'})
    assert copy['boundary']['reason']=='before_original_cluster_read_epilogue',copy
    output=bytes(tail.u.mem_read(dest,slot_bytes))
    assert output==b'\xa5'*43008+original_file[43008:]+b'\xa5'*(slot_bytes-43320)
    changed=[x for x in tail.writes if dest<=int(x['address'],16)<dest+slot_bytes]
    assert sum(x['bytes'] for x in changed)==312
    listing=HERE/'listings';listing.mkdir(exist_ok=False);cuts=[]
    for label,lo,hi in [
        ('reference-escape-loader-whole',0xfe0520d4,0xfe05231c),
        ('reference-file-load-wrapper',0xfe059e20,0xfe059e94),
        ('reference-FAT-file-read',0xfe05a674,0xfe05a84c),
        ('reference-FAT-cluster-read',0xfe04e424,0xfe04e580),
        ('reference-FAT-root-lookup',0xfe05a354,0xfe05a3b4),
        ('reference-FAT-open-result',0xfe05a610,0xfe05a674),
        ('reference-ctype-init-fragment',0xfe04a0e8,0xfe04a104),
        ('reference-ctype-table-helper',0xfe062f0c,0xfe062f48)]:
        b=ap[lo-H.AP_BASE:hi-H.AP_BASE]
        f=listing/(label+'.txt');f.write_text('\n'.join(f'{i.address:#x}: {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in H.MD.disasm(b,lo))+'\n')
        cuts.append(dict(label=label,begin=hex(lo),end_exclusive=hex(hi),original_bytes_sha256=sha(b),listing=str(f.relative_to(HERE))))
    proof=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        previous_receipt_sha256=sha(raw),previous_files_reverified=len(previous['files']),
        AP_reference=dict(sha256=sha(ap),model='A7 IV v2.00; not current FX3 AP boot'),
        original_FX3_p8=dict(path=str(image),sha256=sha(image.read_bytes()),BPB=fs.meta,
            BPB_sector_sha256=sha(bytes(fs.b[:512])),root_directory_sha256=sha(root_bytes),FAT_copy0_sha256=sha(fat_bytes)),
        fixture='Original FX3 p8 BPB, FAT and root bytes mapped into declared RAM locations. Partition index 8 comes from the default class5 descriptor; actual mounting/selection is not asserted.',
        root_lookup_fragments=cases,DmmCfg_lookup_for_read=query,DmmCfg_original_read_prefix=read_prefix,
        DmmCfg_after_full_sector_read_independent_fragment=tail_call,
        DmmCfg_after_tail_sector_read_independent_fragment=dict(result=copy,sector=308,original_sector_sha256=sha(original_sector),
            output_bytes_written=312,original_final_file_bytes_sha256=sha(original_file[43008:]),
            slot_bytes=slot_bytes,slot_tail_bytes=slot_bytes-43320,slot_tail_sentinel_unchanged=True,
            whole_file_read_executed=False,actual_tail_read_reply_supplied=False),
        static_contract=dict(file_load_queries_then_requests_file_size=True,slot_capacity_passed_to_wrapper=False,
            read_count_equality_checked_by_wrapper=False,nonnegative_read_count_returns_prior_query_size=True,
            wrapper_open_failure_status=-408,wrapper_read_failure_propagated_after_diagnostic=True,
            escape_loader_selected_file_result_only_logged=True,escape_loader_post_file_call_has_no_result_branch=True,
            escape_loader_ordinary_tail_sets_zero=True,these_selected_file_routines_zero_fill_slot_tail=False,
            any_prior_whole_boot_staging_initialization_proved=False),
        source_windows=cuts,boundaries=dict(physical_actions=0,native_Sony_tools_run=False,original_file_block_io_executed=False,
            block_helper_success_returns_supplied=False,ctype_helper_substituted=False,originals_modified=False,other_owner_files_written=False,
            FX3_AP_boot_or_current_Backup_obtained=False,CMOS_RAW_full_ISP_or_flashable_modified_firmware_produced=False,goal_complete=False))
    (HERE/'file-read-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(root_lookup_cases=len(cases),sizes=[(x['name'],x['returned_size_or_error']) for x in cases],
        DmmCfg_read_request=read_prefix['boundary'],tail_sector=308,tail_bytes_copied=312,
        slot_tail_bytes_untouched=59080,whole_goal_proved=False)))


if __name__=='__main__':main()
