#!/usr/bin/env python3
"""Read back original CP sources, initialized table dumps and scoped results; seal new stage."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
PIN='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):return json.loads((HERE/n).read_text())
def check(p,n,h):
    b=p.read_bytes();assert len(b)==n and sha(b)==h;return b
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']==UUID
    previous=TASK/'loader-host-20261029/final-receipt.json';assert sha(previous.read_bytes())=='13dfb69b2e4693d37b5c963f175427eee6f556409be3942948a6e5dd84214393'
    old=json.loads(previous.read_text())['files']
    for r in old:check(previous.parent/r['path'],r['bytes'],r['sha256'])
    evidence=read('boot-state-evidence.json');raw=Path(evidence['CP_source']).read_bytes();assert sha(raw)==evidence['CP_sha256']==PIN
    descriptor=evidence['embedded_descriptor'];b=check(HERE/descriptor['path'],descriptor['bytes'],descriptor['sha256'])
    assert len(b)==380 and b==raw[0x20000:0x2017c] and descriptor['VA']=='0x128000'
    assert raw[0xda0:0xda0+380]==bytes(380)
    fields={hex(i):hex(struct.unpack_from('<I',b,i)[0]) for i in range(0,380,4)};assert fields==descriptor['fields_u32_le']
    assert fields['0x15c']=='0x14e8000' and fields['0x168']=='0x14ec000'
    assert int(fields['0x16c'],16)+int(fields['0x170'],16)==0x1007000
    for r in evidence['source_fragments']:
        a=int(r['start_VA'],16);assert sha(raw[a-0x108000:a-0x108000+r['bytes']])==r['original_bytes_SHA256']
        assert (HERE/r['listing']).is_file()
    assert len(evidence['source_fragments'])==9 and evidence['original_local_copy_target']['copied_equals_embedded_descriptor']
    dumps=[]
    for r in evidence['dumps']:
        assert r['all_bytes_initialized_by_original_RAM_code'];data=check(HERE/r['path'],r['bytes'],r['sha256']);dumps.append((r,data))
    l1=next(b for r,b in dumps if r['address']=='0x14e8000');assert len(l1)==16384
    words=struct.unpack('<4096I',l1);assert words[0x9a]==int(evidence['DMM_candidate_initial_L1_entry']['raw_descriptor'],16)==0x09a10c12
    assert evidence['L1_entry_type_counts']=={str(k):sum(w&3==k for w in words) for k in range(4)}
    assert sum(r['bytes'] for r in evidence['L2_initialized_ranges'])==6144 and evidence['L2_unused_bytes_not_dumped']==26624
    meta=next(b for r,b in dumps if r['address']=='0x1007000');assert list(map(hex,struct.unpack('<6I',meta)))==evidence['bootstrap_metadata']
    results=read('bootstrap-guest-results.json');assert results['CP_sha256']==PIN and len(results['cases'])==5
    cases={r['name']:r for r in results['cases']}
    assert cases['strict_full_entry']['boundary']['PC']=='0x10897c' and cases['strict_full_entry']['boundary']['address']=='0x3e42001'
    assert cases['strict_post_poll_fragment']['boundary']['PC']=='0x1089ec' and cases['strict_post_poll_fragment']['boundary']['address']=='0x3e42000'
    zero=cases['post_poll_declared_flag_0'];assert zero['boundary']['PC']=='0x108728' and zero['flag_reads']==1 and zero['original_copy_matches']
    assert zero['L1_pointer']=='0x14e8000' and zero['L2_pointer']=='0x14ec000' and zero['boot_metadata']==evidence['bootstrap_metadata']
    assert evidence['guest_prefix']['original_instructions']==zero['original_instructions']==66848
    assert evidence['guest_prefix']['original_RAM_writes']==zero['original_RAM_writes']==7299
    init=cases['original_software_MMU_init_after_flag0_prefix'];assert init['boundary']['PC']=='0x5541e4' and init['boundary']['instruction']=='dsb sy'
    assert init['ROOT_first3']==['0x14e8000','0x14ec000','0x20']
    assert cases['post_poll_declared_flag_1']['boundary']['PC']=='0x108434'
    query=read('generated-map-query.json');assert query['CP_sha256']==PIN and query['partial_MMU_init']['boundary']['PC']=='0x5541e4'
    assert len(query['cases'])==3
    expected=[('0x9a08e00','0x0','0x0','0x9a08e00'),('0x128000','0x0','0xf','0x0'),('0x0','0xffffffe6','0x0','0x0')]
    for r,(addr,status,attrs,pointer) in zip(query['cases'],expected):
        assert r['address']==addr and r['output_word']==attrs
        assert r['original_attribute_query']['boundary']['reason']==r['original_pointer_check']['boundary']['reason']=='returned'
        assert r['original_attribute_query']['registers'][0]==status and r['original_pointer_check']['registers'][0]==pointer
    guard=read('guard-review-results.json');assert len(guard['checks'])==3
    assert guard['checks'][0]['result']['boundary']['address']=='0x3e42001'
    assert guard['checks'][1]['result']['boundary']['address']=='0x3e42000'
    assert guard['checks'][2]['result']['boundary']['reason']=='outside_original_image_execution'
    failure=read('attempts/banked-stack-initialization.json');assert not failure['expected_boundary_reached'] and failure['result']['boundary']['address']=='0xffffffdc'
    validation=dict(status='PASS_ORIGINAL_CP_BOOT_DESCRIPTOR_AND_SCOPED_MMU_PRODUCER',previous_sealed_files_verified=len(old),
        original_descriptor_bytes=380,original_descriptor_SHA256=descriptor['sha256'],original_source_fragments=9,bootstrap_cases=5,
        flag0_prefix_original_instructions=66848,flag0_prefix_original_RAM_writes=7299,L1_entries=4096,L2_original_initialized_bytes=6144,
        L2_unknown_bytes_omitted=26624,query_cases=3,negative_guard_cases=3,synthetic_MMU_attribute_or_provider_reply=False,
        real_startup_poll_verified=False,real_optional_hardware_flag_verified=False,CPU_TLB_setup_completed=False,MMU_initialization_completed=False,
        DmmCfg_loaded_at_candidate=False,physical_buffer_or_RAW_pixels_obtained=False,whole_ISP_recovered=False,
        native_Sony_programs_executed=0,device_actions=0,other_owner_files_written=False,modified_firmware_produced=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='Progress: actual host-reader format boundary; no complete donor or flashable package.',
        current_turn='Progress: recovered embedded original CP boot descriptor and its original page-table producer, connected root initialization and original pointer predicate on declared pre-barrier snapshot.',
        same_impasse_repeated_consecutive_goal_turns=0,persistent_goal_status='active',goal_complete=False,
        next_step='Complete software MMU initialization/later mapping and identify normal DMM configuration population, then extent allocation. Preserve actual hardware-flag, pixel, donor and modified-package admission gates.'),indent=2)+'\n')
    delta='\n- [2026-10-29 FX3原CP启动描述块与页表生产链](<work/fx3-color-port-20261027/cp-bootstrap-20261029/README.md>)：取得原380B配置；明确标志0的RAM片段由原指令生成4096项L1及6144B L2，原属性／指针三组查询成立。真实启动、完整MMU、配置装入／像素／可刷包仍未证，无设备动作。\n'.encode()
    with (PROJECT/'README.md').open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before=f.read();assert delta not in before
        f.seek(0,os.SEEK_END);f.write(delta);f.flush();os.fsync(f.fileno());f.seek(0);after=f.read();assert after==before+delta
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before),before_sha256=sha(before),prefix_unchanged=True,
        append_bytes=len(delta),append_sha256=sha(delta),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p==final:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,volume_uuid=UUID,
        files=files,validation=validation,device_actions=0,full_modified_firmware_emitted=False,flashable_package_produced=False,
        persistent_goal_status='active',goal_complete=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))
if __name__=='__main__':main()
