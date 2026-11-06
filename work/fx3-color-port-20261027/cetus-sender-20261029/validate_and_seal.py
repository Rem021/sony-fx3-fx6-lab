#!/usr/bin/env python3
"""Verify bounded search coverage and original reader gates, then seal once."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';NOR_PIN='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):return json.loads((HERE/n).read_text())
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    volume=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']==UUID and volume['MountPoint']=='/Volumes/KAFU2T'
    prior=TASK/'nor-backup-selection-20261029/final-receipt.json'
    assert sha(prior.read_bytes())=='4e1dceb5d8bf1a148e0dcd959fb020432b7f997bb8b6644c3200cbadaef44301'
    previous=json.loads(prior.read_text());assert len(previous['files'])==33
    for r in previous['files']:
        b=(prior.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
    markers=read('handoff-marker-scan.json');assert [x['regular_files'] for x in markers['images']]==[797,50,10]
    assert [x['scanned_bytes'] for x in markers['images']]==[435648400,4598505,18192220]
    construction=read('marker-construction-scan.json')
    assert [x['A64_ELF_files'] for x in construction['images']]==[532,33]
    assert [x['executable_bytes'] for x in construction['images']]==[66283528,2333400]
    assert all(not r['hits'] for image in construction['images'] for r in image['files'])
    assert not construction['original_kernel']['hits']
    assert {x['final_VA'] for x in construction['original_NOR_positive_controls']}>={'0xfe052e8c','0xfe052e08'}
    rawscan=read('raw-marker-construction-scan.json')
    assert not rawscan['AV']['A64_hits'] and not rawscan['CP']['ARM_Thumb_marker_hits']
    assert any(0x7bc08<=int(x['first_file_offset'],16)<0x7bc20 for x in rawscan['positive_controls']['Thumb2'])
    assert any(0x553d48<=int(x['construction'][0]['VA'],16)<0x553d70 for x in rawscan['positive_controls']['ARM'])
    source=read('sender-source-review.json');raw=(TASK/'config-producer-20261029/original-files/loader_nor.bin').read_bytes()
    assert sha(raw)==source['NOR_sha256']==NOR_PIN and len(source['source_fragments'])==6
    for r in source['source_fragments']:
        lo=int(r['VA'],16);hi=int(r['end_exclusive'],16)
        assert hi-lo==r['bytes'] and sha(raw[lo-0xfe049000:hi-0xfe049000])==r['original_bytes_sha256']
        assert (HERE/r['listing']).is_file()
    for x in source['original_bulk_load_strings']:
        at=int(x['VA'],16)-0xfe049000;assert raw[at-1]==0 and raw[at:raw.index(b'\0',at)].decode()==x['text']
    assert len(source['candidate_string_contexts'])==4
    contexts={x['path']:x for x in source['candidate_string_contexts']}
    assert all('beep_idx' in x['text'] for x in contexts['/lib/appFw.so']['strings'])
    assert [x['text'] for x in contexts['/kmod/wlan.ko']['strings']]==['COEX_MWS_CP_ESCAPE']
    assert source['interpretation']['sender_located'] is False and source['interpretation']['full_AP_or_boot_source_absence_proved'] is False
    catalog=source['reused_kernel_navigation'];b=Path(catalog['catalog']).read_bytes()
    assert len(b)==catalog['catalog_bytes'] and sha(b)==catalog['catalog_sha256']=='b37c6b7d4315f65234cd6b64c3be4a3d7c6e0d2cca66204e27cb5c575000a51e'
    prior_catalog_manifest=Path(catalog['prior_manifest']).read_bytes()
    assert sha(prior_catalog_manifest)==catalog['prior_manifest_sha256']
    assert any(x['path'].endswith('/work/kernel-symbol-catalog.json') and x['sha256']==catalog['catalog_sha256'] for x in json.loads(prior_catalog_manifest)['files'])
    assert catalog['symbol_count']==41269 and catalog['first_symbol']['address']==0xffffff8008080000
    assert construction['original_kernel']['provisional_VA_base']=='0xffffff8008080000'
    prefixes=read('bulk-loader-prefix-results.json');assert prefixes['NOR_sha256']==NOR_PIN and len(prefixes['cases'])==2
    for x in prefixes['cases']:
        assert x['result']['boundary']==dict(reason='unmapped_external_state',PC='0xfe05885c',address='0xfe040140',bytes=4)
        assert x['boot_metadata_supplied'] is False and x['flash_or_file_data_reply_supplied'] is False
        assert x['result']['nonstack_RAM_writes']==0
    guards=read('NOR-reader-guard-results.json');assert guards['NOR_sha256']==NOR_PIN and len(guards['cases'])==4
    for x in guards['cases']:
        assert x['result']['nonstack_RAM_writes']==0 and x['controller_or_flash_data_supplied'] is False
    for x in guards['cases'][:2]:assert x['result']['boundary']['reason']=='returned' and x['result']['registers'][0]=='0x3'
    assert guards['cases'][2]['result']['boundary']['reason']=='returned' and guards['cases'][2]['result']['registers'][0]=='0x0'
    assert guards['cases'][3]['result']['boundary']==dict(reason='before_unknown_RAM_read',PC='0xfe04faf0',address='0xfe061eea',bytes=1)
    bounds=source['original_bulk_contract'];assert bounds['slot5_fields']==['0xfe040140','0xfe040144','0xfe040150']
    assert bounds['read_wrapper']=='0xfe05a56c' and bounds['lower_reader']=='0xfe04fab0'
    assert bounds['metadata_values_supplied'] is False and bounds['block_read_success_obtained'] is False
    original_attempt=read('attempts/source-review-interior-string.json')
    assert original_attempt['original_bulk_load_strings'][1]['VA']=='0xfe05fdb9'
    correction=read('attempts/string-offset-review.json');assert correction['corrected_VA']=='0xfe05fdc8'
    assert correction['functional_guest_or_scan_results_changed'] is False
    fsroot=PROJECT/'work/sony-firmware-20261024/stage2/extraction';sys.path.insert(0,str(fsroot))
    from read_filesystems import FAT16
    fs=FAT16(fsroot/'nflasha3.img');e=next(x for x in fs.walk() if x['path']=='/vmlinux.bin');kernel=fs.data(e['cluster'],e['size'])
    av=(fsroot/'files/nflasha3/av-cam.bin').read_bytes()
    assert sha(kernel)=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
    assert sha(av)=='0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'
    literal=read('raw-literal-marker-check.json');assert len(literal['checks'])==4
    for x in literal['checks']:
        b=kernel if x['file']=='vmlinux.bin' else av;assert sha(b)==x['sha256'] and len(b)==x['bytes']
        assert x['file_offsets']==[] and bytes.fromhex(x['marker_bytes']) not in b
    validation=dict(status='PASS_BOUNDED_SENDER_SEARCH_AND_ORIGINAL_NOR_BLOCK_READER_GATES',
        previous_sealed_files_verified=33,regular_files_literal_searched=857,A64_ELF_files_scanned=565,
        A64_ELF_executable_bytes_scanned=68616928,raw_kernel_AV_CP_additional_scans=True,
        known_NOR_marker_controls=2,known_CP_ARM_and_Thumb_controls_found=True,
        sender_found=False,global_sender_absence_proved=False,original_source_fragments=6,
        strict_bulk_loader_metadata_stops=2,original_low_level_reader_cases=4,
        zero_length_return0_has_no_data_transfer=True,valid_nonzero_request_completed=False,
        original_flash_or_DMM_data_obtained=False,actual_boot_metadata_obtained=False,
        physical_buffer_or_RAW_pixels_obtained=False,whole_ISP_recovered=False,
        native_Sony_programs_executed=0,device_actions=0,other_owner_files_written=False,
        modified_firmware_produced=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='Progress: pinned NOR file-open ordinary returns fixed-408 and strict Cetus marker checks;33 files reverified.',
        current_turn='Progress: scoped sender search excludes specific name-only candidates and known wide-constant forms in565 ELFs plus raw images. Original configuration branch maps to CPAPP-B NOR block loaders; strict metadata and lower-reader argument/controller gates are identified and executed without supplied hardware state.',
        same_impasse_repeated_consecutive_goal_turns=0,persistent_goal_status='active',goal_complete=False,
        next_step='Trace boot-load information/NOR layout producer and the handoff payload source; determine actual DmmCfg population. Keep complete donor/ISP, modified-package admission and real boot/recovery gates open.'),indent=2)+'\n')
    delta='\n- [2026-10-29 FX3 Cetus发送端范围与原NOR块读边界](<work/fx3-color-port-20261027/cetus-sender-20261029/README.md>)：857普通文件／565 A64 ELF及原始映像的限定搜索未定位发送者；区分提示音DMM／共存同名。原CPAPP-B两块加载入口停在引导表，底层四组边界区分零长0与有效请求未知，无配置数据／像素／可刷包，无设备动作。\n'.encode()
    with (PROJECT/'README.md').open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before=f.read();assert delta not in before
        f.seek(0,os.SEEK_END);f.write(delta);f.flush();os.fsync(f.fileno());f.seek(0);after=f.read();assert after==before+delta
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before),before_sha256=sha(before),prefix_unchanged=True,
        append_bytes=len(delta),append_sha256=sha(delta),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or p==final or '__pycache__' in p.parts:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,volume_uuid=UUID,
        files=files,validation=validation,persistent_goal_status='active',goal_complete=False,device_actions=0,
        flashable_package_produced=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))
if __name__=='__main__':main()
