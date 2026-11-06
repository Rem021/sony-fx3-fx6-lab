#!/usr/bin/env python3
"""Preserve original loading contract and bounded ARM64 source listings."""
import hashlib,io,json,sys,tarfile
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
HERE=Path(__file__).resolve().parent
BASE=0xfe049000;PIN='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    out=HERE/'NOR-load-contract-review.json';assert not out.exists()
    b=(HERE/'original-files/loader_nor.bin').read_bytes();assert sha(b)==PIN
    source=json.loads((HERE/'load-descriptor-sources.json').read_text())
    tarrow=next(x for x in source['original_member_provenance'] if x['member']=='0750_nor_loader/loader_nor.tar')
    with Path(source['FDAT_source']).open('rb') as f:
        f.seek(tarrow['FDAT_offset']-512);header=f.read(512);assert sha(header)==tarrow['header_sha256']
        ti=tarfile.TarInfo.frombuf(header,'utf-8','strict');assert ti.name==tarrow['member'] and ti.size==tarrow['bytes']
        packed=f.read(ti.size);assert sha(packed)==tarrow['sha256']
    with tarfile.open(fileobj=io.BytesIO(packed),mode='r:') as tf:
        e=next(x for x in tf if x.isfile() and x.name=='LdrBkupList.txt');small=tf.extractfile(e).read()
    assert sha(small)=='ae537183ecce42fbe9589c01f7ee4a19929fa2fc1cb09e48eda9ef2ab6f5dd88'
    f=HERE/'original-files/LdrBkupList.txt';assert not f.exists();f.write_bytes(small)
    rows=[];folder=HERE/'source-fragments';folder.mkdir(exist_ok=True)
    cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);cs.skipdata=True
    for lo,hi in [(0xfe0545dc,0xfe054a18),(0xfe04d63c,0xfe04d69c),
        (0xfe04d51c,0xfe04d584),(0xfe04d44c,0xfe04d484),(0xfe04d4c0,0xfe04d4e8),
        (0xfe04c7b4,0xfe04c808),(0xfe04b45c,0xfe04b4cc),
        (0xfe057e98,0xfe057f0c),(0xfe057f0c,0xfe057fa0),(0xfe057fa0,0xfe058178),
        (0xfe058a64,0xfe058a7c),(0xfe058b7c,0xfe058c98),(0xfe0530b0,0xfe053134),
        (0xfe053a1c,0xfe053a70)]:
        data=b[lo-BASE:hi-BASE];f=folder/f'{lo:08x}-{hi:08x}.txt';assert not f.exists()
        f.write_text('\n'.join(f'{x.address:08x} {x.bytes.hex()} {x.mnemonic:8} {x.op_str}' for x in cs.disasm(data,lo))+'\n')
        rows.append(dict(VA=hex(lo),end_exclusive=hex(hi),bytes=len(data),original_bytes_sha256=sha(data),listing=str(f.relative_to(HERE))))
    descriptors=[]
    for template in source['templates']:
        item=[e for e in template['banks'][1]['entries'] if e['path']=='\\DmmCfg.bin'];assert len(item)==1
        descriptors.append(item[0])
    assert len(descriptors)==22 and len({json.dumps(x,sort_keys=True) for x in descriptors})==1
    cp=HERE.parent/'dmm-config-20261029/original-files/DmmCfg.bin';data=cp.read_bytes()
    assert len(data)==43320 and sha(data)=='820dc02b6a001636b93fff51d90baaced1ba75cf9bbaa90600dfc7fd7a705166'
    d=descriptors[0];start=int(d['start'],16);end=int(d['end'],16)
    result=dict(NOR_sha256=PIN,source_fragments=rows,
        base_source='Original pformat_config.txt: file_param path loader_nor.bin load 0xFE049000',
        descriptor_reader=dict(configuration_entry='0xfe0545dc',query_key='0xfa0080',key_build=['0xfe054614','0xfe054620'],
            original_query_call='0xfe05462c',original_query_output_address='0xfe208000',descriptor_stride_instruction='0xfe0549c0: add x27,x27,#0x90',
            first_pair_load='0xfe054730',partition_mode_pair_load='0xfe054758',filename_pointer='descriptor+0x18',
            pre_load_partition_selection='0xfe054794..0xfe05479c',file_loader_call='0xfe054834 ->0xfe057e98',
            original_file_open='0xfe057ea8 ->0xfe057fa0',original_byte_read='0xfe057ebc ->0xfe058178',
            inclusive_limit_calculation='0xfe054850..0xfe054854',size_comparison_after_file_helper='0xfe05485c'),
        direct_callers=[dict(PC='0xfe0530e0',mode_argument='0xc000000',context='x19'),
            dict(PC='0xfe053108',mode_argument='0x9000000',context='x19')],
        descriptor_in_all_22_second_records=d,
        filename_capacity_binding=dict(CP_configuration_source=str(cp),bytes=len(data),sha256=sha(data),
            partition=8,start=hex(start),inclusive_limit=hex(end),reserved_capacity=end-start+1,
            file_fits_reserved_capacity=len(data)<=end-start+1,computed_file_last_byte=hex(start+len(data)-1),
            parameter_fa0182_matches_start=True,parameter_fa0183_matches_capacity=True),
        scope='Original static contract plus separately recorded bounded original query/prefix executions. Neither source descriptors nor a fitting file prove normal record selection, mount/read success, real memory contents, a target firmware port or flash admission.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(source_fragments=len(rows),all_second_record_DMM_descriptors_identical=len(descriptors),
        loader_backup_list=small.decode(),binding=result['filename_capacity_binding'])))
if __name__=='__main__':main()
