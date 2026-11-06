#!/usr/bin/env python3
"""Validate original record/dispatch bytes and strict RAM boundaries; seal once."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
FW=PROJECT/'work/sony-firmware-20261024';UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(n):return json.loads((HERE/n).read_text())
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']==UUID and v['MountPoint']=='/Volumes/KAFU2T'
    prior=TASK/'boot-info-source-20261029/final-receipt.json'
    assert sha(prior.read_bytes())=='0c73200e4484ea05dc88443eca123ff0a552b123580cbee5afda20924def1dfc'
    old=json.loads(prior.read_text());assert len(old['files'])==23
    for r in old['files']:
        b=(prior.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
    context=read('DGU-MIS-context-review.json');raw=FW/'stage198-AP-CP-loaders-and-partition-selection/originals'
    dgu=(raw/'DGU.bin').read_bytes();mis=(raw/'MIS.bin').read_bytes()
    assert sha(dgu)==context['source_pins']['DGU']=='39eeb6d572a060149194463507800ed66b866a20dceb8ed49b01a04eb6fb2ba7'
    assert sha(mis)==context['source_pins']['MIS']=='4cd3e9bc3a0a4aec4793bff77e7ca4dccdba8637212cd632cdc5ecbe550daf98'
    inventory=read('MIS-record-prefix-inventory.json')
    assert inventory['framing_records_total']==5654
    assert [x['framing_records'] for x in inventory['scripts']]==[2337,1464,1853]
    assert [x['stop_file_offset'] for x in inventory['scripts']]==['0xba48','0x123a4','0x1bb6c']
    for s in inventory['scripts']:
        pos=int(s['first_record_offset'],16)
        for r in s['records']:
            assert int(r['file_offset'],16)==pos
            flags,words,opcode=struct.unpack_from('<HBB',mis,pos)
            assert flags==int(r['raw_flags_u16'],16) and words==r['word_count'] and opcode==int(r['opcode'],16)
            assert 1<=words<=21 and mis[pos+4:pos+words*4].hex()==r['payload_hex'];pos+=words*4
        assert pos==int(s['stop_file_offset'],16) and mis[pos:pos+4]==b'\0'*4
        for r in s['comments']:
            at=int(r['file_offset'],16);assert mis[at+3]==0x25
            words=mis[at+2];assert mis[at+4:at+words*4].split(b'\0',1)[0].decode('ascii',errors='replace')==r['text']
    assert any('DDR Reset' in r['text'] for r in inventory['scripts'][0]['comments'])
    assert any('Nanya' in r['text'] for r in inventory['scripts'][1]['comments'])
    assert len(context['observed_opcode_dispatch_entries'])==18 and len(context['source_fragments'])==7
    dispatch={r['opcode']:r for r in context['observed_opcode_dispatch_entries']}
    for r in dispatch.values():
        at=int(r['table_VA'],16)-0xfe040800;b=dgu[at:at+16]
        assert b.hex()==r['raw16_hex'] and b[0]==int(r['opcode'],16) and struct.unpack_from('<Q',b,8)[0]==int(r['handler'],16)
    for r in context['source_fragments']:
        lo=int(r['VA'],16);hi=int(r['end_exclusive'],16)
        assert hi-lo==r['bytes'] and sha(dgu[lo-0xfe040800:hi-0xfe040800])==r['original_bytes_sha256']
        assert (HERE/r['listing']).stat().st_size>0
    strict=read('DGU-MIS-prefix-results.json');enhanced=read('DGU-MIS-with-NOR-results.json')
    assert len(strict['cases'])==len(enhanced['cases'])==3
    assert [x['result']['original_instructions'] for x in strict['cases']]==[1120,750,750]
    assert [x['result']['original_instructions'] for x in enhanced['cases']]==[2302,1352,1352]
    for x in strict['cases']:
        b=x['result']['boundary'];assert b['reason']=='unmapped_external_state' and b['PC']=='0xfe04472c' and b['address']=='0xfe05fe48' and b['bytes']==8
    for x,expected in zip(enhanced['cases'],[['0x25','0x10','0x11'],['0x10','0x11'],['0x10','0x11']]):
        r=x['result'];assert r['boundary']==dict(reason='before_outside_model_write',PC='0xfe045918',address='0xf1020024',bytes=4,value='0x1')
        assert [d['opcode'] for d in r['original_dispatches']]==expected
    for group in [strict,enhanced]:
        assert group['CPU_or_hardware_operations_executed']==group['device_actions']==0
        for x in group['cases']:
            r=x['result'];assert not r['hardware_state_or_reply_supplied'] and not r['function_returns_replaced']
            assert not r['whole_DGU_or_real_boot_proved']
            for d in r['original_dispatches']:
                assert dispatch[d['opcode']]['handler']==d['handler']
                at=int(d['cursor'],16)-0xfe080000;flags,words,op=struct.unpack_from('<HBB',mis,at)
                assert flags==int(d['raw_flags_u16'],16) and words==d['word_count'] and op==int(d['opcode'],16)
                assert mis[at+4:at+words*4].hex()==d['decoded_payload_hex']
    assert enhanced['helper']['sha256']==sha((HERE/enhanced['helper']['path']).read_bytes())
    nor=Path(enhanced['added_original_NOR']['path']).read_bytes()
    assert sha(nor)==enhanced['source_pins']['NOR']=='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
    word=struct.unpack_from('<Q',nor,0xfe05fe48-0xfe049000)[0]
    assert word==int(enhanced['added_original_NOR']['word_at_probe'],16) and word!=0x59634649cafec0da
    gpl=context['model_GPL_UART_reference'];assert sha(Path(gpl['path']).read_bytes())==gpl['sha256']=='4c7a16829a732d24cd21b8fc2a481e15d56cbfe0371c81c7562765ca266a1663'
    assert sha(Path(gpl['receipt']).read_bytes())==gpl['receipt_sha256']=='07d96d5c8c1dc4f9a49157b8fe375dfccf898607f8524a877cedb014c17b9f0f'
    assert len(gpl['PL011_nodes'])==5 and gpl['PL011_nodes'][0]['reg_u32']==[0,0xf1000000,0,0x1000]
    assert not context['current_package_lookup']['assumed_standalone_DTB_present']
    assert context['current_package_lookup']['plain_FDT_magic_candidates']==0
    assert (HERE/'attempts/MIS-record-prefix-inventory-before-DTB-member-fix.json').read_bytes()==(HERE/'MIS-record-prefix-inventory.json').read_bytes()
    failure=read('attempts/DTB-member-lookup-failure.json');assert failure['error']=='StopIteration'
    assert failure['program_sha256']==sha((HERE/'attempts/capture_context_review-before-DTB-member-fix.py').read_bytes())
    validation=dict(status='PASS_ORIGINAL_MIS_FRAMING_AND_DGU_HARDWARE_BOUNDARIES',previous_sealed_files_verified=23,
        sequential_valid_framing_records=5654,original_control_flow_or_complete_script_semantics_proved=False,
        observed_opcode_dispatch_entries=18,original_static_windows=7,original_DGU_only_cases=3,original_NOR_context_cases=3,
        instruction_counts_are_entries_and_include_guarded_last_memory_instruction=True,
        normal_boot_or_DDR_initialization_completed=False,actual_fitted_RAM_vendor_or_capacity_proved=False,
        current7_02_DTB_or_active_nodes_proved=False,model_GPL_UART_reference_pinned=True,
        physical_buffer_or_RAW_or_ISP_recovered=False,CPU_or_hardware_operations_executed=0,
        native_Sony_programs_executed=0,device_actions=0,other_owner_files_written=False,
        modified_firmware_produced=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='Progress: original EXBL comparison and MIS three-entry reader established;23 files reverified.',
        current_turn='Progress: original MIS framing and18 observed dispatch mappings recovered;5654 sequential records inventoried. Three raw-source parser bodies stop at original diagnostic probe; adding adjacent original NOR bytes changes the boundary to original UART-associated hardware setup in all three. DDR/Nanya comments located without inferring actual fitted chip or pixels.',
        same_impasse_repeated_consecutive_goal_turns=0,persistent_goal_status='active',goal_complete=False,
        next_step='Relate original MIS memory read/write handlers and address operands to CP memory regions and DMM allocation, without bypassing unknown hardware. Full donor/ISP, RAW/MAIN binding, modified-package admission, real boot and independent recovery remain open.'),indent=2)+'\n')
    delta='\n- [2026-10-29 FX3 DGU参数解释与串口硬件边界](<work/fx3-color-port-20261027/dgu-mis-consumer-20261029/README.md>)：5654条连续格式记录／18种原分派，六组原前缀区分缺失NOR上下文与串口相关硬件写点；DDR/Nanya注释不充实装芯片证明，未初始化DDR／恢复RAW或可刷包，无设备动作。\n'.encode()
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
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,
        volume_uuid=UUID,files=files,validation=validation,persistent_goal_status='active',goal_complete=False,
        device_actions=0,flashable_package_produced=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))
if __name__=='__main__':main()
