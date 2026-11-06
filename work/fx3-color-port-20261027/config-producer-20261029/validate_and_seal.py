#!/usr/bin/env python3
"""Validate byte provenance, original query/prefix scope, and seal this checkpoint."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
CP_PIN='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
NOR_PIN='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):return json.loads((HERE/n).read_text())
def verify_files(parent,rows):
    for r in rows:
        b=(parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']==UUID and v['MountPoint']=='/Volumes/KAFU2T'
    previous=TASK/'mmu-software-init-20261029/final-receipt.json'
    assert sha(previous.read_bytes())=='2fdae83cdddc2adf6a67d9e1da313411af66bb27c8c46514bd306b4d916a1ae9'
    prev=json.loads(previous.read_text());verify_files(previous.parent,prev['files']);assert len(prev['files'])==29
    backup=TASK/'dmm-backup-20261029/final-receipt.json'
    assert sha(backup.read_bytes())=='a192a5baf3b1442a7aaee7d46d769a8c44a0eac526b6e06c8f965ec4346c66a0'
    verify_files(backup.parent,json.loads(backup.read_text())['files'])
    source=read('load-descriptor-sources.json');assert source['FDAT_sha256']=='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
    assert source['record_stride_bytes']==144 and source['records_per_payload']==64 and len(source['templates'])==22
    canonical=next(t for t in source['templates'] if t['member']==source['canonical_template'])
    payloads=[]
    for bank in canonical['banks']:
        p=HERE/bank['saved_payload'];data=p.read_bytes();assert len(data)==9216 and sha(data)==bank['payload_sha256']
        assert bank['property']['key']=='0xfa0080' and bank['property']['bytes']==9216
        entries={e['index']:e for e in bank['entries']}
        for i in range(64):
            part=data[i*144:(i+1)*144]
            if i not in entries:assert not any(part);continue
            e=entries[i];start,end,partition,mode=struct.unpack_from('<2Q2I',part)
            assert sha(part)==e['original_record_sha256'] and [hex(start),hex(end),partition,hex(mode)]==[e['start'],e['end'],e['partition'],e['mode']]
            assert part[24:].split(b'\0',1)[0].decode()==e['path']
        payloads.append(data)
    for t in source['templates']:
        assert len(t['banks'])==2
        for index,bank in enumerate(t['banks']):assert bank['payload_sha256']==canonical['banks'][index]['payload_sha256']
        dmm=next(e for e in t['banks'][1]['entries'] if e['path']=='\\DmmCfg.bin')
        assert dmm['index']==3 and dmm['partition']==8 and dmm['start']=='0x809a08e00' and dmm['end']=='0x809a21dff'
        assert t['banks'][1]['DMM_parameter_values'][0]['u64']==dmm['start']
        assert t['banks'][1]['DMM_parameter_values'][1]['u64']=='0x19000'
    nor=(HERE/'original-files/loader_nor.bin').read_bytes();assert len(nor)==101888 and sha(nor)==NOR_PIN
    pformat=(HERE/'original-files/pformat_config.txt').read_bytes();assert sha(pformat)=='21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece'
    assert b'load    = 0xFE049000' in pformat
    q=read('NOR-descriptor-query-results.json');assert q['NOR_source_sha256']==NOR_PIN and len(q['cases'])==2
    for i,c in enumerate(q['cases']):
        assert c['bank']==i and c['original_initializer']['boundary']['reason']=='returned' and c['original_initializer']['registers'][0]=='0x0'
        assert c['original_query']['boundary']['reason']=='returned' and c['original_query']['registers'][0]=='0x2400'
        assert c['output_bytes']==9216 and c['output_sha256']==sha(payloads[i]) and c['exact_original_payload_equal'] and c['following_16_byte_canary_unchanged']
    assert q['strict_whole_configuration_entry']['boundary']==dict(reason='unmapped_external_state',PC='0xfe058a6c',address='0xfe26c300',bytes=4)
    prefix=read('NOR-load-prefix-results.json');assert prefix['NOR_source_sha256']==NOR_PIN
    assert prefix['original_path']=='\\DmmCfg.bin'
    assert prefix['original_consumer_fragment']['boundary']['reason']=='before_original_FAT_mount'
    assert prefix['original_consumer_fragment']['registers'][0]=='0x8'
    assert prefix['original_loaded_registers']==dict(start_X26='0x809a08e00',end_X25='0x809a21dff')
    assert prefix['separate_original_file_wrapper']['boundary']['reason']=='before_original_file_open'
    assert prefix['destination_preserved_in_X21']=='0x809a08e00'
    assert prefix['original_consumer_fragment']['boundary']['file_or_device_reply_supplied'] is False
    assert prefix['separate_original_file_wrapper']['boundary']['file_or_device_reply_supplied'] is False
    negative=read('NOR-negative-query-results.json');assert negative['NOR_sha256']==NOR_PIN and len(negative['checks'])==2
    for c in negative['checks']:assert c['result']['boundary']['reason']=='returned' and c['result']['registers'][0]=='0xffffffff'
    assert negative['checks'][0]['entire_output_canary_unchanged']
    contract=read('NOR-load-contract-review.json');assert contract['NOR_sha256']==NOR_PIN and len(contract['source_fragments'])==14
    for r in contract['source_fragments']:
        lo=int(r['VA'],16);hi=int(r['end_exclusive'],16)
        assert hi-lo==r['bytes'] and sha(nor[lo-0xfe049000:hi-0xfe049000])==r['original_bytes_sha256']
        assert (HERE/r['listing']).is_file()
    assert contract['filename_capacity_binding']['file_fits_reserved_capacity']
    assert contract['filename_capacity_binding']['reserved_capacity']==102400
    assert len(contract['direct_callers'])==2
    cp=read('CP-file-address-bindings.json');raw=Path(cp['CP_source']).read_bytes();assert sha(raw)==cp['CP_sha256']==CP_PIN
    table=raw[0xb54930-0x108000:0xb54930-0x108000+128];assert sha(table)==cp['original_range_table_sha256']
    assert cp['original_range_rows'][1]==['0x800000000','0x0','0x0','0x80000000']
    assert len(cp['bindings'])==3
    for x,expected in zip(cp['bindings'],['0x9a08e00','0x100000','0x108000']):
        b=Path(x['original_file']).read_bytes();assert len(b)==x['file_bytes'] and sha(b)==x['file_sha256']
        assert x['CP_constant_table_translation']==expected
        assert int(x['original_load_descriptor']['start'],16)-0x800000000==int(expected,16)
    scan=read('AP-initrd-config-marker-scan.json');assert [x['regular_files'] for x in scan['images']]==[797,50]
    assert [x['scanned_bytes'] for x in scan['images']]==[435648400,4598505]
    assert not scan['images'][0]['hits']
    assert {x['path'] for x in scan['images'][1]['hits']}=={'/sbin/initrc/insmod_drv2'}
    small=(HERE/'original-files/LdrBkupList.txt').read_bytes();assert sha(small)=='ae537183ecce42fbe9589c01f7ee4a19929fa2fc1cb09e48eda9ef2ab6f5dd88'
    assert b'0xFA0080' not in small
    validation=dict(status='PASS_ORIGINAL_BK4_FILE_DESCRIPTOR_AND_NOR_CONSUMER_PREFIX',
        previous_sealed_files_verified=29,backup_sealed_files_reverified=26,official_templates=22,checked_BK4_records=44,
        original_payload_bytes_per_record=9216,descriptor_stride=144,source_fragments=14,
        original_NOR_query_payloads_matched=2,negative_original_query_cases=2,original_consumer_prefixes=2,
        identical_DmmCfg_descriptors_in_second_records=22,CP_file_address_bindings=3,
        original_fa0182_start_binding=True,original_fa0183_value_matches_capacity=True,
        normal_record_selection_verified=False,normal_loader_ready_state_verified=False,
        actual_FAT_mount_or_file_read_completed=False,configuration_bytes_at_candidate_obtained=False,
        physical_buffer_or_RAW_pixels_obtained=False,whole_ISP_recovered=False,
        native_Sony_programs_executed=0,device_actions=0,other_owner_files_written=False,
        modified_firmware_produced=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(
        previous_turn='Progress: original software initialization, region mapping and conditional uncached attribute chain; previous 29 files verified.',
        current_turn='Progress: official FA0080 loading descriptor binds CP DmmCfg filename, partition, physical destination and inclusive capacity; original NOR reads both full tables and consumes CP row to FAT boundaries; three source files match original CP address table.',
        same_impasse_repeated_consecutive_goal_turns=0,persistent_goal_status='active',goal_complete=False,
        next_step='Trace normal complete BK4 selection/readiness and actual file-loading producer before DMM parsing/extent allocation; retain complete donor, ISP, package-admission and real boot/recovery gates.'),indent=2)+'\n')
    delta='\n- [2026-10-29 FX3原CP配置装载描述与NOR消费入口](<work/fx3-color-port-20261027/config-producer-20261029/README.md>)：22模板的FA0080表指定分区8的DmmCfg.bin及原地址／容量；原NOR两次读取9216B一致，消费到FAT挂载／打开边界，三文件与CP地址表对应。正常记录选择、实际读取／像素／可刷包仍未证，无设备动作。\n'.encode()
    with (PROJECT/'README.md').open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before=f.read();assert delta not in before
        f.seek(0,os.SEEK_END);f.write(delta);f.flush();os.fsync(f.fileno());f.seek(0);after=f.read();assert after==before+delta
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before),before_sha256=sha(before),
        prefix_unchanged=True,append_bytes=len(delta),append_sha256=sha(delta),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or p==final or '__pycache__' in p.parts:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,volume_uuid=UUID,
        files=files,validation=validation,persistent_goal_status='active',goal_complete=False,device_actions=0,
        flashable_package_produced=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))
if __name__=='__main__':main()
