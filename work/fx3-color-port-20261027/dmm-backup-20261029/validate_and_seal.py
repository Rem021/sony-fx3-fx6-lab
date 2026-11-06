#!/usr/bin/env python3
"""Read back BK4/default/query evidence, append shared index and seal once."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
VOLUME='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']==VOLUME
    prev=TASK/'dmm-config-20261029/final-receipt.json'
    assert sha(prev.read_bytes())=='de2a4e5c86324321bd2fe766e51231cf84193746daa8352610280a4f34f6a168'
    old=json.loads(prev.read_text())['files']
    for r in old:
        b=(prev.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    source=json.loads((HERE/'public-template-parameters.json').read_text());templates=source['templates']
    assert len(templates)==22 and sum(len(t['records']) for t in templates)==44
    signatures=set()
    for t in templates:
        assert t['official_size_crc_verified'] and t['provenance']['tar_header_checksum_verified']
        values=[]
        for r in t['records']:
            assert r['checksum_verified']
            assert [p['bytes'] for p in r['parameters']]==[8,8,4]
            values.append(tuple(p['value_hex'] for p in r['parameters']))
        signatures.add(tuple(values))
    assert len(signatures)==1
    canonical=next(t for t in templates if t['member']==source['canonical_template'])
    for r in canonical['records']:
        b=(HERE/r['saved_original']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
        offset,size,checksum=struct.unpack_from('<3I',b,24);assert offset+size==len(b)
        assert (sum(b[:32])+sum(b[36:]))&0xffffffff==checksum
        for p in r['parameters']:
            at=int(p['data_offset'],16);assert b[at:at+p['bytes']].hex()==p['value_hex']
    query=json.loads((HERE/'backup-query-results.json').read_text());cases=query['cases'];assert len(cases)==4
    for c in cases:
        assert c['initialization']['returned'] and c['initialization']['raw_r0']=='0x0'
        assert c['original_size_lookup']['raw_r0']=='0x8' and c['sequential_file_adapter_calls']==0
        if c['adapted_backup_mutex']:
            assert len(c['declared_mutex_adapters'])==2 and all(a['declared_return']==0 for a in c['declared_mutex_adapters'])
            assert len(c['original_query_returns'])==1
            value=c['original_query_returns'][0]
            assert int(value['value_low'],16)|(int(value['value_high'],16)<<32)==int(c['original_parameter_value'],16)
            want='0x1500c0' if c['bank_index']==0 else '0x53894c'
            assert c['DMM_source_prefix']['boundary']['pc']==want
        else:
            assert not c['declared_mutex_adapters'] and not c['original_query_returns']
            assert c['DMM_source_prefix']['boundary']['pc']=='0x52ee34'
    review=json.loads((HERE/'backup-source-review.json').read_text())
    cp=(PROJECT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin').read_bytes()
    assert sha(cp)==review['CP_sha256']
    for r in review['source_fragments']:
        at=int(r['va'],16)-0x108000;assert sha(cp[at:at+r['bytes']])==r['sha256']
    assert sha((HERE/'tomco.txt').read_bytes())==source['tomco_source']['sha256']
    layout=review['candidate_layout'];assert int(layout['candidate_CP_logical_address'],16)+int(layout['adjacent_parameter_0xfa0183'],16)==int(layout['original_tomco_snapshotdbg_addr'],16)
    assert not review['normal_selection_and_load']['selected_bank_proven'] and not review['real_configuration_copy_completed']
    validation=dict(status='PASS_ORIGINAL_DEFAULT_BK4_QUERY_AND_DMM_SOURCE_RANGE_PREFIX',previous_files_verified=len(old),
        public_templates_size_CRC_verified=22,BK4_records_checksum_verified=44,original_guest_cases=4,
        strict_backup_mutex_boundaries=2,adapted_original_parameter_queries=2,
        first_record_no_CP_range_diagnostic_boundary=1,second_record_memory_attribute_boundary=1,
        sequential_file_adapter_calls=0,normal_boot_bank_selection_or_config_loading_proven=False,
        real_configuration_copy_or_image_allocation_completed=False,native_Sony_programs_executed=0,device_actions=0,
        full_modified_firmware_emitted=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='progress: original CP config parse and unit0x4af/extent0x62a association',
        current_turn='progress: two original default BK4 records, target parameter values across22 templates, original pointer/range query and next MMU gate',
        repeated_impasse=False,persistent_goal_status='active',goal_complete=False,
        next_step='Trace normal backup record selection/copy and original MMU-table initialization before candidate configuration reads; continue allocation chain without provider replies.'),indent=2)+'\n')
    addition='\n- [2026-10-29 FX3 DMM 默认备份参数与原换算](<work/fx3-color-port-20261027/dmm-backup-20261029/README.md>)：22模板／44段校验通过，原查询从第二段导出配置源候选0x09a08e00；4组严格／适配前缀停在锁或映射边界，无文件读取适配器。正常装载／真实缓冲及可刷包仍缺，无设备动作。\n'.encode()
    index=PROJECT/'README.md'
    with index.open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before=f.read();assert addition not in before
        f.seek(0,os.SEEK_END);f.write(addition);f.flush();os.fsync(f.fileno());f.seek(0);after=f.read()
        assert after==before+addition;fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before),before_sha256=sha(before),
        prefix_unchanged=True,appended_bytes=len(addition),append_sha256=sha(addition),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p==final:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,
        volume_uuid=VOLUME,files=files,validation=validation,private_key_search_or_derivation=False,device_actions=0,
        full_modified_firmware_emitted=False,flashable_package_produced=False,persistent_goal_status='active',goal_complete=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),goal_complete=False)))

if __name__=='__main__':main()
