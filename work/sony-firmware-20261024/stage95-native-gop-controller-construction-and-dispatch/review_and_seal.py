#!/usr/bin/env python3
"""Review constructor/dispatch evidence without promoting runtime acceptance."""
from pathlib import Path
import datetime
import difflib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import controller_dispatch as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage94-native-frame-allocation-to-construction/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    pj=json.loads(prior.read_text())
    for f in pj['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-corrected-geometry-argument-20261027'
    j=json.loads((run/'controller-dispatch-results.json').read_text())
    assert j['status']=='PASS_NATIVE_CONTROLLER_HEAP_CONSTRUCTION_AND_CLASS_SPECIFIC_DISPATCH_WITH_RUNTIME_CALLBACK_STOP'
    assert not (run/'failed-attempt.json').exists()
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'controller_dispatch.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'controller_dispatch.py').read_bytes()
    assert j['source_receipt']['prior_manifest_sha256']==a.PRIOR_SHA
    previous_result=prior.parent/'run-initial-20261027/frame-allocation-results.json'
    assert im.sha(previous_result.read_bytes())==j['source_receipt']['stage94_result_sha256']
    first=json.loads(previous_result.read_text())['cases'][0]
    savedpool=bytes.fromhex(first['final_regions'][hex(a.prev.POOL_PA)])
    start=a.prev.PHYS4-a.prev.POOL_PA+0xec;metadata=savedpool[start:start+48]
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(path.relative_to(BASE))]
    failed=STAGE/'run-initial-20261027';failure=json.loads((failed/'failed-attempt.json').read_text())
    assert failure['completed_cases']==0 and "missing 1 required positional argument: 'mode'" in failure['traceback']
    changes=list(difflib.unified_diff((failed/'executed-source.py').read_text().splitlines(),
                                    (STAGE/'controller_dispatch.py').read_text().splitlines()))
    substantive=[x for x in changes if x[:1] in ('+','-') and not x.startswith(('+++','---'))]
    assert len(substantive)==2 and 'prepare_geometry((120,68)))' in substantive[0]
    assert 'prepare_geometry((120,68),1))' in substantive[1]
    assert len(j['cases'])==14 and j['bounded_phases']==232
    events=[];complete=0;heap_success=0;bound_stops=0;dispatches=0;updates=0;base_returns=0
    observed_cases=set()
    for c in j['cases']:
        seed,kind,flag,bound=c['seed'],c['controller_kind'],c['declared_update_byte50'],c['native_callbacks_bound']
        observed_cases.add((seed,kind,flag,bound));spec=a.KINDS[kind];es=c['events'];events+=es
        assert seed in (165,195) and flag in (0,16)
        assert not bound or kind!='base' and flag==0
        assert len(es)==(14 if bound else 17 if flag else 18)
        assert c['native_vtable_VA']==hex(a.IMAGE+spec['vtable'])
        assert c['native_slot38_target']==hex(a.IMAGE+spec['slot38'])
        assert a.old.word(blob,spec['vtable']+0x10)==a.IMAGE+0x143f98
        assert a.old.word(blob,spec['vtable']+0x38)==a.IMAGE+spec['slot38']
        regions={int(k,16):bytes.fromhex(v) for k,v in c['final_regions'].items()}
        assert set(regions)==set(a.old.PAGES)|{a.prev.REG_PA,a.prev.ARENA_PA,a.prev.POOL_PA,a.HEAP_PA}
        assert len(regions[a.old.INSTANCE_PA])==8192 and len(regions[a.HEAP_PA])==a.HEAP_SIZE
        obj=bytearray([0x62])*8192;heap=bytearray([seed])*a.HEAP_SIZE
        struct.pack_into('<III',obj,0,a.IMAGE+spec['vtable'],a.old.OWNER,0)
        src=regions[a.old.SRC_PA]
        struct.pack_into('<H',obj,0xc,struct.unpack_from('<H',src,2)[0]);struct.pack_into('<I',obj,0x10,0)
        struct.pack_into('<III',heap,0,a.HEAP_SIZE-0x10|1,0,0)
        image_expected={a.prev.CELL:a.prev.REG,a.HEAP_HEAD:a.HEAP,
                        a.BEFORE_ALLOC:a.IMAGE+0xd4b8 if bound else 0,
                        a.AFTER_ALLOC:a.IMAGE+0xd4d8 if bound else 0}
        assert {int(k,16):int(v,16) for k,v in c['image_words'].items()}==image_expected
        arena=regions[a.prev.ARENA_PA]
        assert struct.unpack_from('<H',arena,a.prev.P4-a.prev.ARENA+0x1c)[0]==127
        assert arena[a.prev.H4-a.prev.ARENA+8]==1
        assert a.old.word(arena,a.prev.H4-a.prev.ARENA)==a.prev.PHYS4
        assert a.old.word(src,0x54)==a.prev.H4 and src[0x50]==flag
        expected_pool=bytearray([seed])*a.prev.POOL_SIZE
        expected_pool[start:start+48]=metadata
        constructor_events=[e for e in es if e['label'].startswith('original '+kind+' constructor')]
        assert len(constructor_events)==1;ctor=constructor_events[0]
        assert int(ctor['entry'],16)==a.IMAGE+spec['entry']
        assert not c['new_parameter_reference_completed']
        if bound:
            bound_stops+=1
            assert not c['controller_constructor_completed'] and not c['private_heap_allocation_completed']
            assert c['private_heap_buffer_VA'] is None and c['frame_after_hex'] is None
            assert not c['actual_slot38_dispatch_executed']
            assert ctor is es[-1] and ctor['PC']==hex(a.IMAGE+0xd4b8)
            assert ctor['SP']==hex(a.SP_OBJECT-0x80)
            assert all(hex(a.IMAGE+x) in ctor['CODE_observed_PCs'] for x in (0x69ca0,0x69d84,0x699d8,0x69adc))
            assert not any(hex(a.IMAGE+0x69a60) in e['CODE_observed_PCs'] for e in es)
            assert struct.unpack_from('<H',arena,a.prev.P5-a.prev.ARENA+0x1c)[0]==128
            assert arena[a.prev.H5-a.prev.ARENA+8]==0
        else:
            complete+=1
            assert c['controller_constructor_completed'] and ctor['PC']==hex(a.old.TRAP)
            assert ctor['SP']==hex(a.SP_OBJECT)
            assert c['zero_callbacks_are_pre_binding_image_state_not_normal_runtime']
            if kind!='base':
                heap_success+=1;ptr=a.HEAP+0x10;request=spec['request'];aligned=(request+15)&-16
                assert c['private_heap_request_bytes']==request and c['private_heap_allocation_completed']
                assert c['private_heap_buffer_VA']==hex(ptr)
                struct.pack_into('<I',obj,0x14,ptr)
                struct.pack_into('<I',heap,0,aligned);struct.pack_into('<I',heap,8,a.HEAP+aligned+0x10)
                struct.pack_into('<III',heap,aligned+0x10,(a.HEAP_SIZE-0x20-aligned)|1,a.HEAP,0)
                if kind=='ring524':
                    fields={0x3c8:0,0x3cc:0,0x3c0:ptr,0x3c4:ptr,0x51c:0,0x518:0,0x510:ptr+0x3d0,0x514:ptr+0x3d0}
                    object_fields={0x858:0,0x84c:a.old.INSTANCE+0x18,0x1aec:0,0x850:a.old.INSTANCE+0x18,
                        0x1c28:0,0x1ae0:a.old.INSTANCE+0x85c,0x854:0,0x1ae4:a.old.INSTANCE+0x85c,
                        0x1ae8:0,0x1c1c:a.old.INSTANCE+0x1af0,0x1c20:a.old.INSTANCE+0x1af0,0x1c24:0}
                    byte=0x520
                else:
                    fields={0x78:ptr,0x7c:ptr,0x80:0,0x84:0,0xb0:ptr+0x88,0xbc:0,0xb4:ptr+0x88,0xb8:0}
                    object_fields={};byte=0xc0
                for off,value in fields.items():struct.pack_into('<I',heap,0x10+off,value)
                heap[0x10+byte]=0
                for off,value in object_fields.items():struct.pack_into('<I',obj,off,value)
                assert all(hex(a.IMAGE+x) in ctor['CODE_observed_PCs'] for x in (0x67d34,)) is False
                assert all(hex(a.IMAGE+x) in ctor['CODE_observed_PCs'] for x in (0x699bc,0x699d8,0x69b24,0x69ca0))
            else:
                assert c['private_heap_buffer_VA'] is None and not c['private_heap_allocation_completed']
            assert struct.unpack_from('<H',arena,a.prev.P5-a.prev.ARENA+0x1c)[0]==127
            assert arena[a.prev.H5-a.prev.ARENA+8]==1
            f=bytes.fromhex(c['frame_after_hex']);assert len(f)==0x4f0
            at=a.prev.PHYS5-a.prev.POOL_PA;expected_pool[at:at+len(f)]=f
            assert struct.unpack_from('<HH',f,4)==(120,68) and struct.unpack_from('<HH',f,0x10)==(1920,1088)
            assert a.old.word(f,0x4c8)==(a.prev.H4 if flag else 0) and f[0x4c4]==flag
            if flag:
                updates+=1
                assert not c['actual_slot38_dispatch_executed'] and not es[-1]['dispatch_checkpoints']
                assert es[-1]['PC']==hex(a.IMAGE+0x131c20)
            else:
                dispatches+=1
                assert c['actual_slot38_dispatch_executed']
                assert es[-1]['entry']==hex(a.IMAGE+0x1441e4)
                expected_cp={'point':'native_slot38_receiver_entry','target':hex(a.IMAGE+spec['slot38']),
                    'a0':hex(a.old.INSTANCE),'a1':hex(a.prev.BODY_SP+0x10),'a2':hex(a.old.SRC),
                    'sp':hex(a.prev.BODY_SP),'ra':hex(a.IMAGE+0x1441f0)}
                assert es[-1]['dispatch_checkpoints']==[expected_cp]
                stop={'base':0x1441fc,'ring524':0x1465a4,'ringC4':0x134e6c}[kind]
                assert es[-1]['PC']==hex(a.IMAGE+stop)
                if kind=='base':
                    base_returns+=1
                    assert es[-1]['V0']==hex(a.IMAGE+0x1f87c0)
                    assert blob[0x1f87c0:0x1f87c8]==bytes.fromhex('0800e00300000000')
                if kind=='ring524':assert a.old.word(src,0x84)==0
        assert regions[a.old.INSTANCE_PA]==bytes(obj)
        assert regions[a.HEAP_PA]==bytes(heap) and regions[a.prev.POOL_PA]==bytes(expected_pool)
        assert regions[a.old.FRAME_PA]==bytes([0x73])*4096
        assert c['raw_metadata_owner_history_heap_arena_and_callback_A3_are_declared']
        assert not c['actual_RTOS_locks_MAIN_HEVC_video_audio_or_recovery_proven']
    expected_cases={(s,'base',0,False) for s in (165,195)}
    expected_cases|={(s,k,f,False) for s in (165,195) for k in ('ring524','ringC4') for f in (0,16)}
    expected_cases|={(s,k,0,True) for s in (165,195) for k in ('ring524','ringC4')}
    assert observed_cases==expected_cases
    assert (complete,heap_success,bound_stops,dispatches,updates,base_returns)==(10,8,4,6,4,2)
    assert len(events)==232
    for e in events:
        assert e['all_regions_and_entire_stack_exact_poststate_checked']
        assert e['image_unchanged_except_native_registry_and_heap_globals']
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots'] and not e['MMIO_instruction_patch_or_fake_return']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    offsets={0x143ea4:'original base vtable installation',0x145214:'original ring524 vtable installation',
        0x144710:'original ringC4 vtable installation',0x67d54:'original heap-head global store',
        0x69a74:'original heap split condition',0x69ab8:'original heap linked-list insertion',
        0xd540:'original allocator before-callback binding',0xd544:'original allocator after-callback binding',
        0x699f4:'original before-callback load',0x69adc:'original indirect call reaching lock wrapper in bound controls',
        0xd4c4:'unexecuted original lock wrapper call to RTOS',0xd4e0:'unexecuted unlock wrapper call to RTOS',
        0x1441e4:'original slot38 target load',0x1441e8:'executed original class-specific virtual dispatch',
        0x1f87c0:'base receiver is only original return',0x146508:'ring524 source RAW84 reference read',
        0x146598:'ring524 constructed-frame field2 read',0x1465a4:'unexecuted unclassified RAW geometry read',
        0x145104:'original ringC4 owner-forwarding call',0x134e6c:'unexecuted trace-global read',
        0x134ea4:'unexecuted trace timing MMIO read',0x131c20:'unexecuted new parameter reference boundary'}
    instructions=[]
    for off,meaning in offsets.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off),None)
        instructions.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str if ins else 'not decoded','meaning':meaning})
    opcode=0x0c000000|(((a.IMAGE+0xd530)>>2)&0x3ffffff)
    calls=[hex(p) for p in range(0,0x200000,4) if a.old.word(blob,p)==opcode]
    refs=[hex(p) for p in range(0x200000,len(blob)-3,4) if a.old.word(blob,p)==a.IMAGE+0xd530]
    assert calls==[] and refs==['0x2130f0']
    sourcepath=blob[0x2311e0:].split(bytes([0]),1)[0].decode()
    assert sourcepath.endswith('ctrl/video/enc/common/gop_vbb_ctrl.cxx')
    im.write_json(STAGE/'native-provenance-and-boundaries.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'instructions':instructions,'classes':a.KINDS,'original_source_path':sourcepath,
        'binding_function_direct_JAL_sites_first2MiB':calls,'binding_function_data_refs_after2MiB':refs,
        'normal_boot_initializer_table_order_and_target_MAIN_class_selection_proven':False,
        'heap_callbacks_zero_is_pre_binding_state_only':True,'bound_callback_controls_stop_before_RTOScall':True,
        'actual_IRQ_reference_lifetime_encoder_video_or_recovery_proven':False})
    review={'status':'PASS_ORIGINAL_CONTROLLER_VTABLE_HEAP_DISPATCH_AND_BOUND_CALLBACK_BOUNDARIES',
        'created_utc':now,'prior_sealed_files_verified':len(pj['files']),'cases':14,'formal_phases':232,
        'pre_binding_complete_constructors':10,'pre_binding_private_heap_allocations':8,
        'original_bound_callback_stops':4,'actual_slot38_dispatches':6,'base_noop_returns':2,
        'update_enabled_stops_before_reference_sharing':4,'normal_runtime_construction_or_MAIN_proven':False,
        'preserved_failed_attempts':1,'failed_attempt_classification':'Harness missing existing mode argument; one call corrected, no firmware/input semantics changed.',
        'review_scope':'Same-agent source and stored-output review with exact complete object/heap/pool checks; execution harness checks image, all regions, full stack. Not an independent engine or real-device acceptance.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_GOP_controller_construction_and_class_specific_virtual_dispatch_with_RTOS_boundary'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
        'basis':['stage94封存10件和canonical复核；仅Mac，16项和授权保持。',
            '三原vtable共享143f98但slot38不同，基类为空回调。原构造安装vtable，原分配器分割堆后完成派生私有及环形结构，原parent实际进入对应slot38；均限定为回调尚未绑定的前置状态。',
            '原d530绑定d4b8/d4d8后4对照在原malloc中进入RTOS锁包装，停前不伪造成功。初值回调0不是正常运行无锁证明；正常启动表调用顺序和目标MAIN选类仍未证。',
            '14场景232阶段；6个原虚分派含2基类空返回，4更新开启仍停GP引用前，源ref1；RAW几何/trace/MMIO/owner动态分派未越界。首次漏传mode的测试脚本错误保留，仅补既有mode1后正式通过。',
            '实际IRQ/完整运行、目标HEVC主录、音画长录冷启动与同机备份和独立救砖未验收。'],
        'completion_not_claimed':True}
    result=rel+'/run-corrected-geometry-argument-20261027/controller-dispatch-results.json'
    g['latest_stage_evidence']['stage95_native_controller_construction_dispatch']={'readme':rel+'/README.md',
        'review':rel+'/completed-evidence-review.json','result':result,
        'scope':'Original constructors install actual class vtables; native heap and private structures complete only in pre-callback image state. Original bound-callback controls stop at RTOS lock. Update-off frames dispatch to actual receivers; update-on stops before sharing. Not actual MAIN/runtime construction.',
        'authorization_unchanged':True,'goal_complete':False}
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'External slot38 is class dependent; base only returns. Native constructors and pre-binding native heap remove the host-vtable origin gap, but original callback binding routes malloc to an unexecuted RTOS lock, so pre-binding constructor completion is not normal runtime acceptance.',
        'target_MAIN_or_runtime_synchronization_proven':False})
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].append(result)
            req['stage95_scope']='14场景232阶段：原构造/堆和实际vtable分派仅前置未绑定回调状态；原绑定回调后停RTOS锁，更新开启仍停GP引用。基类仅空返回，目标MAIN选类/正常启动同步/RAW真实输入与HEVC硬件未证。'
    g['next_safe_offline_actions'].append('stage95勿重复原vtable和pre-binding构造。追2130f0所在初始化表与d530调用顺序、堆锁/引用RTOS上下文、GOP候选类在目标MAIN中的选取及RAW84图像参数生产者、owner回调。不能把未绑定回调的初始0当正常运行无锁、基类空返回或关更新回调当HEVC主录成功。全部实机及同机恢复保持，仅Mac。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原控制对象构造、虚分派与锁回调边界](<'+rel+'/README.md>)：14场景232阶段；原vtable与堆构造、按类实际分派只在前置回调状态通过，原绑定锁回调后停RTOS，更新停引用。基类仅返回，非实际MAIN/编码恢复，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage95-native-controller-construction-dispatch/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
