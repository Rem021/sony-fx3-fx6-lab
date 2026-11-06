#!/usr/bin/env python3
"""Verify configuration checkpoint and append/seal it once, without old reruns."""
import datetime,fcntl,hashlib,json,os,plistlib,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];TASK=HERE.parent
EXPECTED_VOLUME='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    volume=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']==EXPECTED_VOLUME
    previous=TASK/'dmm-service-20261029/final-receipt.json'
    assert sha(previous.read_bytes())=='73fe9a2d770beb5481e6a2d48daeefb970c65cc11641b9ffd3b454dac53c6022'
    for row in json.loads(previous.read_text())['files']:
        b=(previous.parent/row['path']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
    extraction=json.loads((HERE/'original-files.json').read_text())
    partition=Path(extraction['partition']).read_bytes();assert sha(partition)==extraction['partition_sha256']
    assert extraction['metadata']['kind']=='FAT12'
    for r in extraction['files']:
        b=(HERE/r['output']).read_bytes();assert len(b)==r['size'] and sha(b)==r['sha256']
        pieces=[partition[int(c['partition_offset'],16):int(c['partition_offset'],16)+c['bytes']] for c in r['cluster_chain']]
        assert b==b''.join(pieces)[:r['size']]
    review=json.loads((HERE/'configuration-review.json').read_text());oracle=review['independent_oracle']
    assert [oracle[k] for k in ['original_group_headers_matched','original_records_matched','all_original_units_matched','consumed_bytes']]==[165,1052,348,43320]
    assert sha((HERE/'host-decoder-source.txt').read_bytes())==oracle['decoder_source_sha256']
    for r in review['source_pins']:
        b=Path(r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    source=PROJECT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
    cp=source.read_bytes();assert sha(cp)==review['CP_sha256']
    for r in review['source_fragments']:
        a=int(r['va'],16)-0x108000;assert sha(cp[a:a+r['bytes']])==r['sha256']
    guest=json.loads((HERE/'config-guest-results.json').read_text())
    assert guest['parsed_bytes']==43320 and guest['trailing_bytes']==0 and len(guest['all_units'])==348
    assert guest['selected_unit']['extent_IDs']==['0x62a']
    assert guest['selected_unit_lookup']['boundary']['pc']=='0xab9a5c'
    assert guest['missing_unit_lookup']['returned'] and guest['missing_unit_lookup']['raw_r0']=='0xfffffffd'
    for r in guest['file_reads']:
        b=(HERE/'original-files/DmmCfg.bin').read_bytes();at=int(r['file_offset'],16)
        assert sha(b[at:at+r['bytes']])==r['sha256'] and r['adapter']
    extent=json.loads((HERE/'extent-config-results.json').read_text());maps=extent['extents'][0]['mappings']
    assert len(maps)==1 and maps[0]['region_index']==1
    assert len(maps[0]['matching_extent_records'])==2
    assert all(r['raw_wordC']=='0x25b480' for r in maps[0]['matching_extent_records'])
    assert review['domain_separation']['WBI_sections_covering_candidate']==0
    assert not review['normal_CP_boot_filename_parameter_binding_proven'] and not review['unit_slot_or_image_allocation_executed']
    validation=dict(status='PASS_ORIGINAL_CP_CONFIG_PARSER_AND_UNIT_EXTENT_ASSOCIATION',previous_sealed_files_verified=41,
        original_files_verified=2,original_CP_group_headers_matched=165,original_CP_config_records_matched=1052,
        original_CP_units_matched=348,whole_CP_config_bytes_consumed=43320,unconsumed_CP_config_bytes=0,
        selected_CP_unit='0x4af',selected_extent_ID='0x62a',selected_rule_records=2,
        original_lookup_stopped_before_slot_allocation=True,explicit_original_file_read_adapter=True,
        normal_CP_boot_parameter_or_file_binding_proven=False,AP_CP_domain_separation_kept=True,
        old_guest_mains_rerun=False,device_actions=0,native_Sony_programs_executed=0,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='progress: original queue/callback binding and static configuration dependency',
        current_turn='progress: original CP config parsing/lookup, complete-file cross-oracle and unit0x4af to extent0x62a association',
        reused_prior_work='stage128 host decode and stage129 AP/CP separation reused read-only; not counted as new extraction/discovery',
        repeated_impasse=False,persistent_goal_status='active',goal_complete=False,
        next_step='Trace normal CP BK4 loading and parameter0xfa0182 producer; continue original unit/extent allocation dependencies.'),indent=2)+'\n')
    addition='\n- [2026-10-29 FX3 原 CP DMM 配置与 NRV 单位](<work/fx3-color-port-20261027/dmm-config-20261029/README.md>)：原解析器消费完整43320B，165组头／1052记录／348单位与独立参照一致；0x4af对应0x62a两条配置记录。正常CP装载、真实缓冲／MAIN及可刷包未证，无设备动作。\n'.encode()
    index=PROJECT/'README.md'
    with index.open('a+b') as file:
        fcntl.flock(file.fileno(),fcntl.LOCK_EX);file.seek(0);before=file.read();assert addition not in before
        file.seek(0,os.SEEK_END);file.write(addition);file.flush();os.fsync(file.fileno());file.seek(0);after=file.read()
        assert after==before+addition;fcntl.flock(file.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before),before_sha256=sha(before),prefix_unchanged=True,
        appended_bytes=len(addition),append_sha256=sha(addition),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path==final:continue
        b=path.read_bytes();files.append(dict(path=str(path.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,
        volume_uuid=EXPECTED_VOLUME,files=files,validation=validation,device_actions=0,private_signing_material_read_or_derived=False,
        full_modified_firmware_emitted=False,flashable_package_produced=False,persistent_goal_status='active',goal_complete=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))

if __name__=='__main__':main()
