#!/usr/bin/env python3
"""Review native pool/cache data evidence, retaining coherence and IRQ gaps."""
from pathlib import Path
import datetime
import difflib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import type4_cache as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage90-native-metadata-copy-and-caller/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-corrected-call-frame-20261027';j=json.loads((run/'type4-cache-results.json').read_text())
    assert not (run/'failed-attempt.json').exists()
    assert j['status']=='PASS_NATIVE_TYPE4_POOL_FIRST_CACHE_HANDLE_COPY_EXHAUSTION_AND_REUSE_WITH_EXPLICIT_GAPS'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'type4_cache.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'type4_cache.py').read_bytes()
    blob_path=a.prev.prev.old.old.prev.a.prev.p.a.v.VCD_PATH;blob=blob_path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(blob_path.relative_to(BASE))]
    src=BASE/'stage86-hevc-vui-mode-conversion/run-20261026/vui-mode-results.json'
    assert im.sha(src.read_bytes())==j['source_receipt']['stage86_result_sha256']
    assert struct.unpack_from('<4I',blob,0x2132c0)==(4,a.PHYSICAL_BASE,65536,128)
    assert a.word(blob,0x23c30c)==a.IMAGE+0x606d0 and a.word(blob,0x23c304)==a.IMAGE+0x60068
    assert len(j['observer_calibration'])==3
    for c in j['observer_calibration']:
        e=c['event'];divisor=c['declared_divisor']
        assert hex(a.IMAGE+0x6057c) in e['CODE_observed_PCs']
        if divisor:assert c['quotient']==65536//divisor and not e['native_interrupts']
        else:assert c['quotient'] is None and e['native_interrupts']==[18]
    assert len(j['cases'])==4 and j['bounded_phases']==164
    all_events=[];success_allocations=0;allocation_attempts=0
    for c in j['cases']:
        kind=c['kind'];seed=c['seed'];events=c['events'];all_events+=events
        assert not c['actual_runtime_sync_ownership_dispatch_MAIN_hardware_or_recovery_proven']
        assert not c['host_supplied_cache_handle_free_count_or_return_value']
        assert len(c['unexecuted_gaps'])==3 and c['native_registry_pointer']==a.REG
        pages={int(k,16):bytes.fromhex(v) for k,v in c['final_pages'].items()}
        assert set(pages)==set(a.SIZES) and all(len(pages[k])==a.SIZES[k] for k in pages)
        reg,arena,cache,record,pool=[pages[x] for x in (a.REG_PA,a.ARENA_PA,a.CACHE_PA,a.RECORD_PA,a.POOL_PA)]
        assert a.word(reg,0)==0x4d4d6772 and reg[4]==255
        assert (a.word(reg,0x14),a.word(reg,0x18),a.word(reg,0x1c))==(a.ARENA,a.ARENA_SIZE,0xe40)
        assert a.word(reg,0x30)==a.PROVIDER
        for offset in range(0x20,0x1d8,4):
            if offset!=0x30:assert a.word(reg,offset)==0
        assert a.word(arena,0)==a.VTABLE and a.word(arena,4)==4
        assert (a.word(arena,8),a.word(arena,0xc),a.word(arena,0x34))==(a.PHYSICAL_BASE,65536,512)
        assert struct.unpack_from('<H',arena,0x10)[0]==128
        assert arena[0x12]==0 and a.word(arena,0x2c)==0
        assert a.word(arena,0x14)==a.HANDLES
        free=struct.unpack_from('<H',arena,0x1c)[0];assert free==c['remaining_free_blocks']
        assert a.word(cache,0xc90)==a.CACHE_RECORD and struct.unpack_from('<H',cache,0xca0)[0]==0x1235
        assert a.word(cache,8)==0x28
        assert record[0x21:0x24]==bytes([seed])*3
        assert events[3]['entry']==hex(a.IMAGE+0x5d978) and events[3]['stop']==a.STOPS[0x5d304]
        assert events[4]['entry']==hex(a.IMAGE+0x5d318) and events[4]['stop']==a.STOPS[0x5d990]
        assert events[4]['SP']==hex(a.SP_FACTORY)
        expected_allocated=128 if kind=='exhausted' else (0 if kind=='event_off' else 1)
        for i in range(128):
            off=0x40+i*28;used=i<expected_allocated
            assert a.word(arena,off)==a.PHYSICAL_BASE+i*512
            assert a.word(arena,off+4)==(0x11c if used else 512)
            assert a.word(arena,off+8)==(1 if used else 0)
            assert a.word(arena,off+0xc)==a.PROVIDER
            assert a.word(arena,off+0x10)==(0 if used or i==127 else a.HANDLES+(i+1)*28)
            assert a.word(arena,off+0x14)==a.word(arena,off+0x18)==0
        assert a.word(arena,0x18)==(0 if kind=='exhausted' else a.HANDLES+(0 if kind=='event_off' else 28))
        copies=kind in ('normal','normal_reuse');wantpool=bytearray([seed])*a.POOL_MAP_SIZE
        if copies:
            assert free==127 and c['native_first_cache_handle']==a.HANDLES and c['native_allocation_status']==0
            assert a.word(record,0x24)==a.HANDLES and record[0x20]==0x10
            start=a.PHYSICAL_BASE-a.POOL_PA
            wantpool[start+0xec:start+0x11c]=bytes.fromhex(c['declared_metadata48_hex'])
            assert events[-1]['stop']==a.STOPS[0x140e64]
            if kind=='normal_reuse':
                assert c['native_reacquired_handle']==a.HANDLES and len(events)==11
                assert hex(a.IMAGE+0x140d7c) in events[-2]['CODE_observed_PCs']
                assert hex(a.IMAGE+0x60068) in events[-2]['CODE_observed_PCs']
                success_allocations+=2;allocation_attempts+=2
            else:
                assert c['native_reacquired_handle'] is None and len(events)==9
                success_allocations+=1;allocation_attempts+=1
        elif kind=='exhausted':
            assert free==0 and c['native_first_cache_handle']==0 and c['native_allocation_status']==0xb1020001
            assert record[0x20]==0x10 and a.word(record,0x24)==0
            assert c['exhausted_by_native_allocations']==[a.HANDLES+i*28 for i in range(128)]
            assert len(events)==137 and events[-1]['stop']==a.STOPS[0x141008]
            assert events[-2]['V0']=='0x0'
            assert all(e['stop']=='returned_via_original_jr_ra' for e in events[6:134])
            success_allocations+=128;allocation_attempts+=129
        else:
            assert kind=='event_off' and free==128 and c['native_first_cache_handle'] is None
            assert c['native_allocation_status'] is None and record[0x20]==0 and a.word(record,0x24)==0
            assert len(events)==7 and events[-1]['stop']==a.STOPS[0x140e64]
        assert pool==wantpool
        assert all(e['image_unchanged_except_native_registry_global'] and e['all_data_regions_and_full_stack_exact_poststate_checked'] for e in events)
    assert len(all_events)==164 and success_allocations==131 and allocation_attempts==132
    for e in all_events:
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots'] and not e['MMIO_instruction_patch_or_fake_return']
        for forbidden in (0x5d304,0x140d04,0x140da0):
            if hex(a.IMAGE+forbidden) in e['CODE_observed_PCs']:
                assert e['pc']==hex(a.IMAGE+forbidden)
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    attempts=[];names=['run-initial-20261027','run-corrected-entry-20261027','run-corrected-call-frame-20261027']
    for index,name in enumerate(names[:-1]):
        old=(STAGE/name/'executed-source.py').read_text();new=(STAGE/names[index+1]/'executed-source.py').read_text()
        f=json.loads((STAGE/name/'failed-attempt.json').read_text());assert f['completed_cases']==0
        delta=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=name,tofile=names[index+1]))
        attempts.append({'attempt':name,'source_sha256':im.sha(old.encode()),'error':f['traceback'],
            'next_attempt_source_diff':delta,'classification':'offline harness entry or expected-frame correction, not a firmware defect'})
    im.write_json(STAGE/'attempt-corrections.json',{'created_utc':now,'attempts':attempts,
        'formal_run':names[-1],'failed_sources_retained':True,'checks_not_weakened_or_instructions_patched':True})
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    offsets={0x5d49c:'original runtime registry pointer store',0x5d978:'original factory arena argument',
        0x5d980:'original factory call',0x5d988:'original returned provider binding',
        0x5d304:'unexecuted cache maintenance',0x5d318:'original post-cache load and tail',
        0x60570:'original pool size/count divide',0x6057c:'calibrated annulled BREAK or actual divide-zero trap',
        0x605a4:'native block size store',0x60610:'native physical backing address store',0x6062c:'native provider ownership pointer store',
        0x5ef98:'original verified allocation virtual call',0x606d0:'original fixed-pool allocator'}
    offsets.update({0x60028:'empty free-list branch',0x60034:'native free-count decrement',
        0x60730:'native allocated reference byte1',0x140d04:'unexecuted cache caller GP/IRQ acquire',
        0x140d54:'native existing-handle reference decrement',0x140d7c:'original verified free virtual call',
        0x140d88:'original cache request size11c',0x140d98:'original allocated handle store',
        0x140d9c:'original allocation status conditional clear',0x140da0:'unexecuted IRQ release prefix',
        0x140dd8:'original status branch to error or transfer',0x140e40:'original metadata copy store'})
    instructions=[]
    for off,meaning in offsets.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off))
        instructions.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str,'meaning':meaning})
    im.write_json(STAGE/'native-provenance-and-gaps.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'original_descriptor_hex':blob[0x2132c0:0x2132d0].hex(),'instructions':instructions,
        'explicit_unexecuted_intervals':['registration checks/IRQ before 5d978',
            '5d304 through 5d314 cache loop','140d04 through 140d3c GP/IRQ acquire',
            '140da0 through 140dd4 GP/IRQ release'],
        'initial_arena_RAM_source_frame_and_payload_declared':True,'coherence_or_actual_runtime_sync_proven':False})
    review={'status':'PASS_NATIVE_TYPE4_FIRST_BUFFER_DATA_FLOW_WITH_EXPLICIT_COHERENCE_IRQ_GAPS',
        'created_utc':now,'prior_sealed_files_verified':10,'formal_cases':4,'formal_phases':164,
        'observer_calibrations':3,'native_allocation_attempts':132,'native_successful_allocations':131,
        'pool_exhaustion_native_failure_cases':1,'native_free_and_reacquire_cases':1,
        'empty_cache_handle_generated_by_native_allocator':True,'physical_metadata_copy_checked':True,
        'failed_harness_attempts_retained':2,
        'review_scope':'Same-agent source/stored-data review plus exact full-region checks by execution harness. No independent engine or camera acceptance.',
        'actual_coherence_IRQ_sync_MAIN_hardware_or_recovery':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_type4_pool_first_cache_handle_exhaustion_and_reuse'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage90封存10件和canonical复核；仅Mac，16项/授权保持。',
            '原ROM类型4表：physicalc2c140/65536字节/128块，原构造得到512字节块及28字节句柄记录。原manager绑定/arena存储/工厂构造及post-cache原返回登记执行，缓存维护/注册IRQ明确未执行。',
            '原空8字节cache记录后，原分派虚调用生成首次句柄及引用1，原caller保存并拷48到原记录所指物理缓冲；两旧值对照。128次原分配耗尽后第129次空句柄/b1020001进入原错误诊断前停点；一次原引用1→0/free/reacquire复借同句柄。',
            '4例164阶段，132原申请/131成功、3原DIVU/BEQL/BREAK校准。两次离线入口/栈预期错误保留并修正，未改原指令或放宽全栈检查。',
            '原始源帧/48字节/可用RAM仍声明，注册前检查、CACHE/IRQ及全部同步/真实MAIN/硬件/视频/同机恢复未验收；池内归还不是设备救砖。'],
        'completion_not_claimed':True}
    result=rel+'/run-corrected-call-frame-20261027/type4-cache-results.json'
    g['latest_stage_evidence']['stage91_type4_first_cache_buffer']={'readme':rel+'/README.md',
        'review':rel+'/completed-evidence-review.json','result':result,
        'scope':'Native ROM-defined fixed pool, first cache handle/physical copy, exhaustion and local release/reacquire in declared RAM. Explicit registration, cache-maintenance and IRQ gaps remain; no actual synchronization/MAIN/hardware/recovery.',
        'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].append(result)
            req['stage91_scope']='原类型4 128×512池构造/首次cache句柄与48字节物理复制、耗尽错误及归还重借；4例164阶段。注册前/CACHE/IRQ明确未执行，源输入/RAM声明。真实同步/队列/MAIN/硬件和同机恢复不提升。'
    g['next_safe_offline_actions'].append('stage91后优先核对原类型4真实注册和CACHE/IRQ实现及全局引用/调度，追源帧参数真实生产/MAIN绑定；禁止把单实例RAM原生分配/耗尽/归还扩展成实机并发或恢复。原空cache首次句柄来源已在显式空缺范围内追通，后续不要重新预置成功cache句柄来隐藏初始化/所有权缺口；16项实机与恢复验收保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 类型4与首次缓存缓冲](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：原128×512池/首次句柄/物理48字节复制、耗尽错误与归还重借，4例164阶段；注册/CACHE/IRQ有显式空缺，真实同步/MAIN/硬件及恢复未验，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage91-native-type4-first-cache-buffer/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
