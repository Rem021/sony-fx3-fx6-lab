#!/usr/bin/env python3
"""Review original manager pointer origin and distinguish routing from scheduling."""
from pathlib import Path
import datetime,json,struct,sys
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import manager_routing as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage95-native-gop-controller-construction-and-dispatch/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    pj=json.loads(prior.read_text())
    for f in pj['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-initial-20261027';j=json.loads((run/'manager-routing-results.json').read_text())
    assert j['status']=='PASS_NATIVE_BOOT_ITERATOR_PREFIX_FACTORY_SUFFIX_SELECTORS_AND_FRAME_ROUTING_WITH_EXPLICIT_GAPS'
    assert not (run/'failed-attempt.json').exists()
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'manager_routing.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'manager_routing.py').read_bytes()
    assert j['source_receipt']['prior_manifest_sha256']==a.PRIOR_SHA
    source=prior.parent/'run-corrected-geometry-argument-20261027/controller-dispatch-results.json'
    assert j['source_receipt']['stage95_result_sha256']==im.sha(source.read_bytes())
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(path.relative_to(BASE))]
    assert len(j['cases'])==18 and j['bounded_phases']==62
    targets=[0xa054,0x61f3c,0x93cc,0xa05c,0xd5b4,0xa320,0xd530]
    records=[struct.unpack_from('<III',blob,0x2130a0+i*12) for i in range(7)]
    assert records==[(0,0,a.IMAGE+t) for t in targets]
    allocations=[{'request':n,'aligned':aligned,'header':hex(a.prev.HEAP+h),'result':hex(a.prev.HEAP+h+0x10)}
        for n,aligned,h in ((0x18,0x20,0),(0xc4,0xd0,0x30),(0x1c2c,0x1c30,0x110),(0x524,0x530,0x1d50))]
    events=[];boots=0;bound=0;valid=0;invalid=0;cases=set()
    c4,c524,pc4,p524=[a.prev.HEAP+x for x in (0x10,0x120,0x40,0x1d60)]
    for c in j['cases']:
        seed,kind,selector,value,length_ok=c['seed'],c['kind'],c['selector'],c['declared_selector_byte'],c['valid_message_length']
        cases.add((seed,kind,selector,value,length_ok));es=c['events'];events+=es
        p={int(k,16):bytes.fromhex(v) for k,v in c['final_regions'].items()}
        heap=p[a.prev.HEAP_PA];mgr=p[a.MGR_PA];msg=p[a.MSG_PA]
        assert len(heap)==0x10000 and len(mgr)==len(msg)==4096
        assert len(p[a.old.INSTANCE_PA])==8192 and p[a.old.FRAME_PA]==bytes([0x73])*4096
        assert a.old.word(mgr,8)==a.old.SRC and struct.unpack_from('<II',mgr,0x10)==(a.old.OWNER,0)
        assert c['factory_prefix_owner_callback_config_and_heap_arena_declared']
        assert not c['mode_callback_completion_and_valid_scheduling_order_proven']
        assert c['frame_routing_is_independent_declared_entry_not_mode_transition_completion']
        assert not c['actual_MAIN_HEVC_hardware_RTOS_boot_or_recovery_proven']
        if kind=='boot_prefix':
            boots+=1;assert len(es)==1 and c['native_allocations']==[] and c['objects']=={}
            assert heap==bytes([seed])*0x10000
            assert es[0]['entry']==hex(a.IMAGE+0x5c49c) and es[0]['PC']==hex(a.IMAGE+0x61f3c)
            assert es[0]['SP']==hex(a.SP_BOOT-0x20) and es[0]['S0']=='0x4' and es[0]['S1']==hex(a.IMAGE+0x2130ac)
            assert [x['target'] for x in es[0]['indirect_calls']]==[hex(a.IMAGE+0xa054),hex(a.IMAGE+0x61f3c)]
            assert [x['S1'] for x in es[0]['indirect_calls']]==[hex(a.IMAGE+0x2130a0),hex(a.IMAGE+0x2130ac)]
            assert hex(a.IMAGE+0xa058) in es[0]['CODE_observed_PCs']
            assert not any(hex(a.IMAGE+t) in es[0]['CODE_observed_PCs'] for t in targets[2:])
        elif kind=='bound_factory':
            bound+=1;assert len(es)==3 and c['heap_callbacks_bound'] and c['native_allocations']==[] and c['objects']=={}
            assert es[-1]['PC']==hex(a.IMAGE+0xd4b8)
            assert es[-1]['indirect_calls'][0]['target']==hex(a.IMAGE+0xd4b8)
            expected=bytearray([seed])*0x10000;struct.pack_into('<III',expected,0,0xfff1,0,0)
            assert heap==bytes(expected)
        else:
            assert kind=='routing' and not c['heap_callbacks_bound']
            assert c['native_allocations']==allocations and c['objects']=={'ringC4':hex(c4),'ring524':hex(c524)}
            assert es[1]['entry']==hex(a.IMAGE+0x7a304) and es[1]['PC']==hex(a.IMAGE+0x7a35c)
            assert es[1]['SP']==hex(a.SP_FACTORY)
            assert all(hex(a.IMAGE+x) in es[1]['CODE_observed_PCs'] for x in
                (0x1447a8,0x145300,0x1f8a1c,0x1f8a64,0x7a328,0x7a350,0x7a358))
            # Validate all native block headers and links, plus private/owner bindings.
            for i,rec in enumerate(allocations):
                off=int(rec['header'],16)-a.prev.HEAP
                previous=int(allocations[i-1]['header'],16) if i else 0
                following=int(allocations[i+1]['header'],16) if i<3 else a.prev.HEAP+0x2290
                assert struct.unpack_from('<III',heap,off)==(rec['aligned'],previous,following)
                assert heap[off+0xc:off+0x10]==bytes([seed])*4
            assert struct.unpack_from('<III',heap,0x2290)==(0xdd61,a.prev.HEAP+0x1d50,0)
            assert heap[0x229c:]==bytes([seed])*(0x10000-0x229c)
            for obj,private,vt in ((c4,pc4,0x2422b4),(c524,p524,0x242264)):
                at=obj-a.prev.HEAP
                assert struct.unpack_from('<III',heap,at)==(a.IMAGE+vt,a.old.OWNER,0)
                assert struct.unpack_from('<II',heap,at+0x10)==(0,private)
                assert heap[at+0xe:at+0x10]==bytes([seed])*2
                assert a.old.word(blob,vt+0x10)==a.IMAGE+0x143f98
            assert struct.unpack_from('<II',heap,pc4-a.prev.HEAP+0x78)==(pc4,pc4)
            assert struct.unpack_from('<II',heap,pc4-a.prev.HEAP+0xb0)==(pc4+0x88,pc4+0x88)
            assert heap[pc4-a.prev.HEAP+0xc0]==0
            assert struct.unpack_from('<II',heap,p524-a.prev.HEAP+0x3c0)==(p524,p524)
            assert struct.unpack_from('<II',heap,p524-a.prev.HEAP+0x510)==(p524+0x3d0,p524+0x3d0)
            assert heap[p524-a.prev.HEAP+0x520]==0
            for at,target in ((0x84c,c524+0x18),(0x1ae0,c524+0x85c),(0x1c1c,c524+0x1af0)):
                assert struct.unpack_from('<II',heap,c524-a.prev.HEAP+at)==(target,target)
            assert struct.unpack_from('<II',mgr,0x18)==(c4,c524)
            assert struct.unpack_from('<H',msg,6)[0]==(0x70 if selector==1 else 0xe0)-(0 if length_ok else 1)
            assert msg[0x23 if selector==1 else 0x36]==value
            selected=c524 if (value==1 if selector==1 else value!=0) and length_ok else c4
            assert a.old.word(mgr,0x20)==selected and c['current_manager_pointer']==hex(selected)
            if length_ok:
                valid+=1;assert len(es)==4
                assert es[2]['PC']==hex(a.IMAGE+(0x7af58 if selector==1 else 0x7b74c))
                assert es[-1]['entry']==hex(a.IMAGE+0x7b08c) and es[-1]['PC']==hex(a.IMAGE+0x143fc0)
                assert es[-1]['native_entries']==[{'point':'original_frame_parent_entry','a0':hex(selected),
                    'a1':hex(a.FRAME_MSG+8),'sp':hex(a.SP_EVENT-0x70),'ra':hex(a.IMAGE+0x7b104)}]
                assert es[-1]['SP']==hex(a.SP_EVENT-0xd0)
                assert not es[2]['indirect_calls']
            else:
                invalid+=1;assert len(es)==3 and es[-1]['PC']==hex(a.IMAGE+0x1a9a84)
                assert not es[-1]['indirect_calls'] and not es[-1]['native_entries']
                assert not any(hex(a.IMAGE+x) in es[-1]['CODE_observed_PCs'] for x in (0x7af48,0x7b73c))
        if kind!='routing':assert mgr[0x18:0x24]==bytes([seed])*12
        assert c['current_manager_pointer']==hex(a.old.word(mgr,0x20))
    expected={(seed,'boot_prefix',1,0,True) for seed in (165,195)}
    expected|={(seed,'bound_factory',1,0,True) for seed in (165,195)}
    expected|={(seed,'routing',s,v,True) for seed in (165,195) for s,vs in ((1,(0,1,2)),(2,(0,1,255))) for v in vs}
    expected|={(165,'routing',s,1,False) for s in (1,2)}
    assert cases==expected and (boots,bound,valid,invalid)==(2,2,12,2) and len(events)==62
    for e in events:
        assert e['image_all_regions_and_entire_stack_exact_poststate_checked']
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots'] and not e['MMIO_instruction_patch_or_fake_return']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    offsets={0x5c49c:'original bootstrap table iterator caller',0x5c794:'native ROM table pointer',
        0x5c79c:'native loop initial6 means7 entries',0x5c7a0:'native entry function pointer load',
        0x5c7c8:'original table indirect call',0x5c7cc:'native ROM entry argument load',
        0x9e54:'unexecuted earlier CP0 status read',0x9e68:'unexecuted earlier CP0 status write',
        0xa064:'unexecuted initialization-table hardware MMIO write',0x9e00:'unexecuted RTOS IRQ helper CP0 status read',
        0x7a308:'native outer object request18',0x7a31c:'native actual C4 constructor variant call',
        0x7a330:'native outer object request1c2c',0x7a344:'native actual524 constructor variant call',
        0x7a358:'native default current object store',0x7af34:'selector1 payload1b byte read',
        0x7af3c:'selector1 equality-to1 branch',0x7af48:'native selector1 current store',
        0x7b72c:'selector2 payload2e byte read',0x7b730:'selector2 zero test',0x7b73c:'native selector2 current store',
        0x7af58:'unexecuted selector1 mode callback',0x7b74c:'unexecuted selector2 mode callback',
        0x7b0ec:'native manager current-object load',0x7b0f8:'native selected-object slot10 load',
        0x7b0fc:'executed common frame parent virtual call',0x143fc0:'unexecuted GP lock-ID read'}
    instructions=[]
    for off,meaning in offsets.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off),None)
        instructions.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str if ins else 'not decoded','meaning':meaning})
    sourcepath=blob[0x217db0:].split(bytes([0]),1)[0].decode();assert sourcepath.endswith('ctrl/video/enc/common/gop_vbb_mng.cxx')
    im.write_json(STAGE/'native-provenance-and-boundaries.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'instructions':instructions,'original_source_path':sourcepath,
        'bootstrap_table':[{'index':i,'file_offset':hex(0x2130a0+i*12),'words':[hex(w) for w in r],
            'execution_scope':'original first callback returned' if i==0 else 'stopped at original entry' if i==1 else 'static order only'} for i,r in enumerate(records)],
        'actual_manager_constructor_call_variants':['0x1447a8','0x145300'],
        'complete_boot_factory_prefix_mode_callback_scheduling_MAIN_or_hardware_proven':False,
        'frame_handler_is_independent_routing_entry':True,'original_CP0_RTOS_lock_semantics_unexecuted':True})
    review={'status':'PASS_NATIVE_FACTORY_OBJECT_ORIGIN_SELECTION_AND_BOOT_TABLE_PREFIX_WITH_SCOPE_GAPS',
        'created_utc':now,'prior_sealed_files_verified':len(pj['files']),'cases':18,'formal_phases':62,
        'native_factory_suffix_completions':14,'native_heap_allocations':56,'valid_selector_and_frame_routes':12,
        'length_mismatch_diagnostic_stops':2,'bound_allocator_lock_stops':2,'original_boot_table_prefixes':2,
        'failed_attempts':0,'full_boot_or_mode_transition_or_MAIN_acceptance':False,
        'review_scope':'Same-agent original-byte/source and saved-output review of pointers, all block headers/links and relevant private structures; harness checks entire image/all regions/full stack. Not independent engine or physical acceptance.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_bootstrap_table_prefix_manager_factory_suffix_and_message_control_selection'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
        'basis':['stage95封存11件和canonical复核；Mac-only，16项/授权保持。',
            '原5c49c→原表循环实际执行第一空函数并到第二初始化入口；原ROM7项顺序把锁回调绑定列第7，但其它初始化/CPU/硬件未执行，不等于正常启动完成。',
            '改由原manager后半段调用原堆申请对象18/1c2c和私有c4/524，原构造变体及原18/1c/20字段保存，默认小对象；前半段/回调来源/完整校验与正常同步仍声明或缺失。',
            '18场景62阶段；两原selector分别字段==1与!=0切换，12合法组经独立原frame入口读取当前对象并进入143f98后停GP锁前；模式回调未完成，独立路由不代表调度。2长度错停诊断，2原绑定锁对照第一申请即停。',
            '真实MAIN/HEVC主录、声音长录冷启动、同机备份及独立救砖未验收；不把前置未绑定回调当正常运行。'],
        'completion_not_claimed':True}
    result=rel+'/run-initial-20261027/manager-routing-results.json'
    g['latest_stage_evidence']['stage96_bootstrap_manager_routing']={'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result,
        'scope':'Original boot iterator prefix; original manager suffix allocates both classes/privates and defaults current pointer; original selectors and independent frame routing. Not full mode callback, valid scheduling, runtime locks, full boot or target MAIN.',
        'authorization_unchanged':True,'goal_complete':False}
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Callback binding has an original seven-entry iterator/caller, but only first callback returned. Candidate classes now allocated/stored by original manager suffix; message selectors differ: payload1b==1 versus payload2e!=0. Independent frame routing consumes selected pointer without proving pending mode callback or target MAIN selection.',
        'actual_MAIN_or_mode_transition_completion_proven':False})
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].append(result)
            req['stage96_scope']='18场景62段：原boot表前缀、原manager后半段分配双类/私有及默认当前；selector两个不同字节判定原切换并经独立frame路由到143f98锁前。模式回调/合法调度、初始化其余项、正常RTOS与目标MAIN硬件未证。'
    g['next_safe_offline_actions'].append('stage96后追真实消息payload1b和payload2e生产及原selector模式回调所需owner动态表；勿重复对象地址/selector路由。原boot7项只执行第一空函数至第二入口，其余初始化与CP0/RTOS/硬件未证；原管理器前半段owner/回调及MAIN实例来源仍缺。独立frame入口不能当模式完成后的调度。仅Mac，全部实机和同机恢复验收保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原初始化表、管理器对象与选择路由](<'+rel+'/README.md>)：18场景62阶段；原manager后半段分配双类，两个原消息字段选择并独立路由至frame锁前。原boot表前缀有界执行；模式回调/正常启动/MAIN硬件未证，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            raw=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage96-native-bootstrap-manager-routing/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
