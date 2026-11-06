#!/usr/bin/env python3
"""Verify original-source bounds and conditional guest results, then seal once."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
PREVIOUS=TASK/'config-producer-20261029';UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
NOR_PIN='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):return json.loads((HERE/n).read_text())
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    volume=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']==UUID and volume['MountPoint']=='/Volumes/KAFU2T'
    receipt=PREVIOUS/'final-receipt.json';assert sha(receipt.read_bytes())=='581d993c194df656a3327c80090320dcaf1408daeee48d7f2037aa1a338bf9b8'
    previous=json.loads(receipt.read_text());assert len(previous['files'])==39
    for r in previous['files']:
        b=(PREVIOUS/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
    raw=(PREVIOUS/'original-files/loader_nor.bin').read_bytes();assert len(raw)==101888 and sha(raw)==NOR_PIN
    source=read('backup-and-file-open-source-review.json');assert source['NOR_sha256']==NOR_PIN
    assert len(source['source_fragments'])==13 and len(source['official_header_facts'])==44
    assert all(x['byte8']==0 and x['word4']=='0xaaaaaaaa' and x['marker_hex']=='424b3400' for x in source['official_header_facts'])
    f=open(HERE/'original-files/CP-template-header.bin','rb');header=f.read();f.close();assert len(header)==256
    assert sha(header) in {x['header_sha256'] for x in source['official_header_facts']}
    assert header[8]==0 and struct.unpack_from('<I',header,4)[0]==0xaaaaaaaa
    ctype=(HERE/'original-files/NOR-character-class-table.bin').read_bytes();assert len(ctype)==256
    assert sha(ctype)==source['declared_ctype_source']['sha256'] and ctype==raw[0xfe06147d-0xfe049000:0xfe06147d-0xfe049000+256]
    assert all(ctype[x]&8 for x in range(97,123)) and all(not(ctype[x]&8) for x in range(65,91))
    handoff=read('handoff-boundaries.json');assert handoff['NOR_sha256']==NOR_PIN and len(handoff['source_fragments'])==3
    for r in source['source_fragments']+handoff['source_fragments']:
        lo=int(r['VA'],16);hi=int(r['end_exclusive'],16)
        assert hi-lo==r['bytes'] and sha(raw[lo-0xfe049000:hi-0xfe049000])==r['original_bytes_sha256']
        assert (HERE/r['listing']).is_file()
    cfg=source['file_open_control_flow'];assert cfg['entry']=='0xfe057fa0' and cfg['instructions']==cfg['reachable_instructions']==118
    assert cfg['return_addresses']==['0xfe058174'] and cfg['return_assignment']['PC']=='0xfe05816c'
    assert cfg['return_assignment']['signed_W0']==-408 and cfg['assignment_dominates_all_ordinary_returns']
    file_bytes=raw[0xfe057fa0-0xfe049000:0xfe058178-0xfe049000]
    words=struct.unpack('<118I',file_bytes);assert sum(x==0xd65f03c0 for x in words)==1
    assert words[-1]==0xd65f03c0 and words[-3]==0x128032e0
    assert not cfg['original_byte_stream_reader_called'] and all(x['target']!='0xfe058178' for x in cfg['ordinary_call_targets'])
    result=read('backup-selection-state-results.json');assert result['NOR_sha256']==NOR_PIN
    assert result['original_header']==dict(word4='0xaaaaaaaa',byte8=0,word2c=0)
    assert result['header_checker']['registers'][0]=='0xfffffffa'
    assert result['strict_file_header_choice']['registers'][0]==result['no_headers']['registers'][0]=='0xffffffff'
    assert result['relaxed_helper_choice']['registers'][0]=='0x2'
    for key in ['header_checker','strict_file_header_choice','no_headers','relaxed_helper_choice']:
        assert result[key]['boundary']['reason']=='returned'
    assert result['strict_whole_configuration_without_state']['boundary']['address']=='0xfe26c300'
    assert result['original_state_initializer_prefix']['boundary']['address']=='0xfe040110'
    assert result['initializer_prefix_state_words']==[0,0,0] and result['original_RAM_reuse_state_words']==[3,0,0]
    assert result['independent_original_RAM_reuse_fragment']['boundary']['PC']=='0xfe058dfc'
    assert result['original_helper_returns']==[dict(PC='0xfe058d48',X0='0xfffffffa'),dict(PC='0xfe058d50',X0='0x0')]
    query=result['original_wrapped_parameter_query'];assert query['boundary']['reason']=='returned' and query['registers'][0]=='0x2400'
    expected=(PREVIOUS/'original-files/bank1-fa0080.bin').read_bytes();assert len(expected)==9216
    assert result['copied_original_table_bytes']==9216 and result['copied_original_table_sha256']==sha(expected)
    assert result['load_buffer_tail_unknown_bytes_not_claimed']==3072
    assert result['original_configuration_entry_after_fragment']['boundary']['PC']=='0xfe0561b4'
    opened=read('file-open-original-results.json');assert opened['NOR_sha256']==NOR_PIN and len(opened['cases'])==3
    assert [c['path'] for c in opened['cases']]==['\\DmmCfg.bin','\\NoSuch.bin','\\updater\\mode']
    for c in opened['cases']:
        assert c['result']['boundary']['reason']=='returned' and c['result']['registers'][0]=='0xfffffe68'
        assert c['file_query_or_block_data_reply_supplied'] is False and c['original_byte_stream_reader_entered'] is False
        assert '0xfe058178' not in c['original_function_entries']
    failure=read('attempts/file-open-fixture-first-boundary.json')
    assert failure['status']=='INITIAL_FIXTURE_DID_NOT_REACH_RETURN' and failure['result']['boundary']['address']=='0xfe061e18'
    assert len(handoff['cases'])==2
    assert [c['result']['boundary']['address'] for c in handoff['cases']]==['0x800107f20','0x800107f30']
    assert all(c['completion_marker_supplied'] is False for c in handoff['cases'])
    for x in handoff['original_log_strings']:
        at=int(x['VA'],16)-0xfe049000;assert raw[at:raw.index(b'\0',at)].decode()==x['text']
    validation=dict(status='PASS_ORIGINAL_SELECTION_AND_NOR_FIXED_FILE_FAILURE_BOUNDARY',
        previous_sealed_files_verified=39,official_default_BK4_headers=44,original_source_fragments=16,
        original_header_check_cases=4,default_byte8_zero=True,normal_file_selection_proved=False,
        explicit_RAM_reuse_fragment_writes_state3=True,whole_normal_backup_initialization_completed=False,
        original_wrapped_table_query_bytes=9216,original_configuration_table_copy_bytes=9216,
        unknown_load_buffer_tail_bytes_not_claimed=3072,
        pinned_file_open_instructions=118,ordinary_return_paths_assign_minus408=True,original_file_open_cases=3,
        original_byte_stream_reader_entered=False,strict_handoff_marker_stops=2,handoff_markers_supplied=False,
        actual_configuration_file_load_completed=False,configuration_bytes_at_DMM_target_obtained=False,
        normal_boot_or_live_state_verified=False,physical_buffer_or_RAW_pixels_obtained=False,whole_ISP_recovered=False,
        native_Sony_programs_executed=0,device_actions=0,other_owner_files_written=False,
        modified_firmware_produced=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='Progress: official DMM file descriptors and original NOR query/prefix,39 files reverified.',
        current_turn='Progress: separate strict file selection from RAM reuse; original state3 producer can expose original table in a declared RAM fragment, but this NOR file-open ordinary returns are fixed-408. Locate separate Cetus marker consumers; switch next research from assumed FAT success to handoff producers.',
        same_impasse_repeated_consecutive_goal_turns=0,persistent_goal_status='active',goal_complete=False,
        next_step='Trace boot metadata/full-record source and Cetus handoff sender/payload to determine actual DmmCfg population. Preserve donor/ISP, modified-package admission and normal boot/recovery gates.'),indent=2)+'\n')
    delta='\n- [2026-10-29 FX3原备份选择与NOR文件入口固定失败](<work/fx3-color-port-20261027/nor-backup-selection-20261029/README.md>)：44原模板头与选择模式分开；原RAM复用片段写状态3并复制9216B装载表。原文件打开118条指令的普通返回均-408，三组原执行一致；转查Cetus交接，完成标志／配置内容／可刷包未证，无设备动作。\n'.encode()
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
