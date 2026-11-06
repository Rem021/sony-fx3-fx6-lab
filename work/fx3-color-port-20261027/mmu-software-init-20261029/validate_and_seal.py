#!/usr/bin/env python3
"""Validate original byte provenance and scoped RAM results, then seal once."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
PIN='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):return json.loads((HERE/n).read_text())
def compare_files(parent,files):
    for r in files:
        b=(parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
def query_cases(snapshot):
    return snapshot['cases']
def validate_queries(cases):
    assert len(cases)==7
    for x in cases:
        assert x['attribute_call']['boundary']['reason']=='returned'
        assert x['pointer_call']['boundary']['reason']=='returned'
    return {int(x['address'],16):x for x in cases}
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']==UUID and v['MountPoint']=='/Volumes/KAFU2T'
    prior=TASK/'cp-bootstrap-20261029/final-receipt.json'
    assert sha(prior.read_bytes())=='fda864f2790d2a32761f41a257f47b3b53f762c656dbc263a64123c4389a95a1'
    previous=json.loads(prior.read_text());compare_files(prior.parent,previous['files'])
    source=read('source-review.json');raw=(PROJECT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin').read_bytes()
    assert len(raw)==15980568 and sha(raw)==source['CP_sha256']==PIN
    assert len(source['source_fragments'])==13
    for x in source['source_fragments']:
        lo=int(x['VA'],16);hi=int(x['end_exclusive'],16)
        assert hi-lo==x['bytes'] and sha(raw[lo-0x108000:hi-0x108000])==x['original_bytes_sha256']
        assert (HERE/x['listing']).is_file()
    table=source['original_region_table'];data=(HERE/'original-files/CP-region-table.bin').read_bytes()
    assert len(data)==table['bytes']==380 and sha(data)==table['sha256'] and data==raw[0xd22a84-0x108000:0xd22a84-0x108000+380]
    assert table['record_stride']==20 and table['record_count']==19
    for i,x in enumerate(table['records']):
        words=struct.unpack_from('<5I',data,i*20);assert list(map(hex,words))==x['words']
        at=words[3]-0x108000;assert raw[at:raw.index(b'\0',at)].decode('ascii')==x['original_name']
    assert table['records'][10]['original_name']=='Rsv_C1'
    assert table['records'][10]['words']==['0x4000000','0xc4000000','0x0','0xe26c65','0x4000000']
    assert source['following_optional_table_provider']['original_return_pointer']==source['following_optional_table_provider']['original_return_count']==0
    assert len(source['original_region_mapping_calls'])==15
    region_match=[x for x in source['original_region_mapping_calls'] if x['register_arguments'][1]=='0x4000000']
    assert len(region_match)==1 and region_match[0]['register_arguments']==['0x14007c8','0x4000000','0xc4000000','0x4000000']
    assert region_match[0]['stack_arguments']==['0xc','0x0','0xffffffff']
    init=read('software-init-results.json');assert init['CP_sha256']==PIN
    assert init['strict_init']['boundary']['PC']=='0x5541e4'
    r=init['software_initializer'];assert r['boundary']['reason']=='returned' and r['original_instructions']==116936 and r['original_RAM_writes']==4806
    assert len(init['modeled_DSB_events'])==28 and len(init['original_mapping_calls'])==28
    assert len(init['L1_changed_entries'])==4065
    assert all(x['arguments'][3]=='0x0' and x['context_word']=='0xffffffff' for x in init['original_mapping_calls'])
    before=validate_queries(init['snapshots'][0]['cases']);cleared=validate_queries(init['snapshots'][1]['cases'])
    assert before[0x9a08e00]['attribute_call']['registers'][0]=='0x0' and before[0x9a08e00]['pointer_call']['registers'][0]=='0x9a08e00'
    assert cleared[0x9a08e00]['attribute_call']['registers'][0]=='0xffffffe6' and cleared[0x9a08e00]['pointer_call']['registers'][0]=='0x0'
    region=read('region-list-results.json');assert region['CP_sha256']==PIN
    assert region['strict_original_entry']['boundary']['PC']=='0x555d34' and region['strict_original_entry']['boundary']['instruction'].startswith('mrc ')
    assert region['original_free_pool_fragment']['boundary']['PC']=='0x54ae54'
    assert region['original_post_mutex_region_fragment']['boundary']['PC']=='0x54b3b4'
    assert region['original_post_mutex_region_fragment']['original_instructions']==162722
    mapped=validate_queries(region['snapshot']['cases'])
    assert mapped[0x9a08e00]['attributes']=='0xc' and mapped[0x9a08e00]['pointer_call']['registers'][0]=='0x0'
    tomco=read('tomco-request-results.json');assert tomco['CP_sha256']==PIN
    original_tomco=Path(tomco['TOMCO_source']).read_bytes();assert sha(original_tomco)==tomco['TOMCO_sha256']
    assert original_tomco.splitlines().count(tomco['original_line'].encode())==1
    assert tomco['observed_original_SetAttr_arguments']==['0x9000000','0x7000000','0x20']
    assert tomco['original_value_fragment']['boundary']['PC']=='0x546c9c'
    assert tomco['strict_original_SetAttr']['boundary']==dict(reason='before_uninitialized_RAM_read',PC='0x556204',address='0x1400728',bytes=4)
    assert tomco['software_projection_arguments']==['0x9000000','0x7000000','0x20000020']
    assert tomco['software_projection']['boundary']['reason']=='returned'
    projected=validate_queries(tomco['snapshot']['cases'])
    assert projected[0x9a08e00]['attributes']=='0x20' and projected[0x9a08e00]['pointer_call']['registers'][0]=='0x9a08e00'
    assert projected[0xfffffff]['attributes']=='0x20' and projected[0xfffffff]['pointer_call']['registers'][0]=='0xfffffff'
    assert projected[0x10000000]['attributes']=='0xc' and projected[0x10000000]['pointer_call']['registers'][0]=='0x0'
    assert projected[0x128000]['attributes']=='0xf' and projected[0x128000]['pointer_call']['registers'][0]=='0x0'
    assert projected[0]['attribute_call']['registers'][0]=='0xffffffe6'
    assert all(x['PC'] in ['0x5541e4','0x5548dc','0x555374'] for x in tomco['modeled_DSB_events'])
    assert len(tomco['modeled_DSB_events'])==44
    snapshots=source['software_L1_snapshots'];assert len(snapshots)==4
    candidate=[next(x['descriptor'] for x in s['entries'] if x['index']=='0x9a') for s in snapshots]
    assert candidate==['0x9a10c12','0x0','0x9a1041e','0x9a11412']
    failure=read('attempts/region-global-write-guard.json');assert failure['status']=='SELF_WRITTEN_GUARD_SCOPE_TOO_NARROW'
    assert failure['original_write_address']=='0xff430c' and failure['not_Sony_firmware_failure']
    validation=dict(status='PASS_ORIGINAL_SOFTWARE_INIT_REGION_AND_CONDITIONAL_ATTRIBUTE_CHAIN',
        previous_sealed_files_verified=len(previous['files']),source_fragments=13,original_region_records=19,
        original_region_map_calls=15,software_initializer_returned=True,software_initializer_L1_changes=4065,
        original_attribute_query_cases=28,original_query_and_pointer_returns=56,
        original_TOMCO_value_parsed=True,strict_SetAttr_cache_geometry_unknown=True,
        CPU_disabled_argument_is_explicit_projection=True,normal_TOMCO_SetAttr_completed=False,
        actual_CPU_cache_TLB_or_barrier_state_verified=False,actual_startup_poll_verified=False,
        DmmCfg_loaded_at_candidate=False,physical_buffer_or_RAW_pixels_obtained=False,whole_ISP_recovered=False,
        native_Sony_programs_executed=0,device_actions=0,other_owner_files_written=False,
        modified_firmware_produced=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(
        previous_checkpoint='Original embedded CP bootstrap descriptor and partial table initialization; all 27 sealed files read back.',
        current_progress='Original software initializer clears the transient accepted candidate; original region list rebuilds cached mapping; original TOMCO parser requests UC attributes; strict hardware state remains unknown, separate explicit CPU-disabled projection changes only RAM descriptors.',
        same_impasse_repeated_consecutive_goal_turns=0,persistent_goal_status='active',goal_complete=False,
        next_step='Find normal cache initialization and actual TOMCO/config loading producer, then DMM slots and extent allocation. Keep complete donor/ISP and modified-package admission gates open.'),indent=2)+'\n')
    delta='\n- [2026-10-29 FX3原区域重建与未缓存配置链](<work/fx3-color-port-20261027/mmu-software-init-20261029/README.md>)：原软件初始化清除中间候选映射，19项原区域表／15次映射再建缓存属性；原memcfg解析请求0x20，严格路径仍缺缓存几何。明确关闭CPU维护的独立RAM投影才通过指针门，无配置内容／像素／可刷包，无设备动作。\n'.encode()
    with (PROJECT/'README.md').open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before_index=f.read();assert delta not in before_index
        f.seek(0,os.SEEK_END);f.write(delta);f.flush();os.fsync(f.fileno());f.seek(0);after_index=f.read()
        assert after_index==before_index+delta
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before_index),before_sha256=sha(before_index),
        prefix_unchanged=True,append_bytes=len(delta),append_sha256=sha(delta),after_sha256=sha(after_index)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or p==final or '__pycache__' in p.parts:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,
        volume_uuid=UUID,files=files,validation=validation,persistent_goal_status='active',goal_complete=False,
        flashable_package_produced=False,device_actions=0),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))
if __name__=='__main__':main()
