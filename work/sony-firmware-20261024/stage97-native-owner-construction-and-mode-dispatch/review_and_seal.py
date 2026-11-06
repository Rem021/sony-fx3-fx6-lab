#!/usr/bin/env python3
"""Review actual owner provenance and correct earlier initializer interpretation."""
from pathlib import Path
import datetime,difflib,json,struct,sys
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import owner_mode as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage96-native-bootstrap-and-manager-routing/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    pj=json.loads(prior.read_text())
    for f in pj['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-corrected-resume-boundary-20261027';j=json.loads((run/'owner-mode-results.json').read_text())
    assert j['status']=='PASS_ACTUAL_OWNER_CONSTRUCTOR_AND_NATIVE_ZERO_INDEX_MODE_DISPATCH_TO_TRACE_BOUNDARY'
    assert not (run/'failed-attempt.json').exists()
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'owner_mode.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'owner_mode.py').read_bytes()
    assert j['source_receipt']['prior_manifest_sha256']==a.PRIOR_SHA
    source=prior.parent/'run-initial-20261027/manager-routing-results.json'
    assert j['source_receipt']['stage96_result_sha256']==im.sha(source.read_bytes())
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(path.relative_to(BASE))]
    failed=STAGE/'run-initial-20261027';failure=json.loads((failed/'failed-attempt.json').read_text())
    assert failure['completed_cases']==0 and 'self.stack' in failure['traceback']
    diff=list(difflib.unified_diff((failed/'executed-source.py').read_text().splitlines(),(STAGE/'owner_mode.py').read_text().splitlines()))
    changed=[x for x in diff if x[:1] in ('+','-') and not x.startswith(('+++','---'))]
    assert len(changed)==6
    assert all(any(s in x for s in ('off in STOPS','off in self.stops','self.stops=dict(STOPS)',
        'entry==0x7af58:self.stops.pop','set(STOPS.values())','set(self.stops.values())')) for x in changed)
    assert len(j['cases'])==12 and j['bounded_phases']==60 and j['earlier1352f0_is_not_complete_GOP_owner_constructor']
    heap=a.prev.prev.HEAP;owner=heap+0x10;c4=heap+0xf50;pc4=heap+0xf80;c524=heap+0x1060;p524=heap+0x2ca0
    requests=[(0xf2c,0xf30,0),(0x18,0x20,0xf40),(0xc4,0xd0,0xf70),(0x1c2c,0x1c30,0x1050),(0x524,0x530,0x2c90)]
    allocs=[{'request':n,'aligned':al,'header':hex(heap+off),'result':hex(heap+off+0x10)} for n,al,off in requests]
    events=[];cases=set();set_flags=0
    for c in j['cases']:
        seed,selected,e,ten=c['seed'],c['declared_selector_byte'],c['declared_mode_payload0e'],c['declared_mode_payload10']
        cases.add((seed,selected,e,ten));es=c['events'];events+=es;assert len(es)==5
        assert c['native_allocations']==allocs and c['native_owner_VA']==hex(owner) and c['native_owner_index4']==0
        assert c['declared_constructor_ids']==([0,0] if seed==165 else [17,33])
        assert c['objects']=={'ringC4':hex(c4),'ring524':hex(c524)}
        expected_selected=c524 if selected==1 else c4
        assert c['current_manager_pointer']==hex(expected_selected)
        assert [int(x['entry'],16)-a.IMAGE for x in es]==[0x67d34,0x7a2ac,0x7a304,0x7aed4,0x7af58]
        assert es[1]['PC']==hex(a.IMAGE+0x7a2d4) and es[2]['PC']==hex(a.IMAGE+0x7a35c)
        assert es[3]['PC']==es[4]['entry'] and not es[3]['indirect_calls']
        assert all(hex(a.IMAGE+x) in es[1]['CODE_observed_PCs'] for x in (0x69ca0,0x12f21c,0x1f3858,0x7a2cc,0x7a2d0))
        assert all(hex(a.IMAGE+0x1352f0) not in event['CODE_observed_PCs'] for event in es)
        assert es[-1]['PC']==hex(a.IMAGE+0x12f84c) and es[-1]['SP']==hex(a.prev.SP_SELECT-0xf0)
        assert [x['target'] for x in es[-1]['indirect_calls']]==[hex(a.IMAGE+0x143f38),hex(a.IMAGE+0x12f7dc)]
        assert es[-1]['native_entries']==[{'point':'native_owner_mode_handler_entry','a0':hex(owner),
            'a1':hex(a.prev.MSG+8),'sp':hex(a.prev.SP_SELECT-0x90),'ra':hex(a.IMAGE+0x134db0)}]
        pages={int(k,16):bytes.fromhex(v) for k,v in c['final_regions'].items()}
        h=pages[a.prev.prev.HEAP_PA];mgr=pages[a.prev.MGR_PA];msg=pages[a.prev.MSG_PA]
        assert len(h)==0x10000 and len(mgr)==len(msg)==4096
        assert a.old.word(mgr,0x10)==owner and struct.unpack_from('<III',mgr,0x18)==(c4,c524,expected_selected)
        for i,(n,al,off) in enumerate(requests):
            previous=heap+requests[i-1][2] if i else 0
            following=heap+requests[i+1][2] if i<4 else heap+0x31d0
            assert struct.unpack_from('<III',h,off)==(al,previous,following)
        assert struct.unpack_from('<III',h,0x31d0)==(0xce21,heap+0x2c90,0)
        assert h[0x31dc:]==bytes([seed])*(0x10000-0x31dc)
        expected_owner=bytearray(a.owner_initial_bytes(seed,owner,*c['declared_constructor_ids']))
        snapshot=es[1]['owner_constructor_snapshot']
        assert snapshot=={'point':'native_owner_constructor_return_to_original_manager','owner':hex(owner),
            'sha256':im.sha(bytes(expected_owner)),'native_dispatch_index4':0}
        assert a.old.word(expected_owner,4)==0 and expected_owner[0x81:0x84]==bytes([seed])*3
        assert expected_owner[0x80]==0 and expected_owner[0x94]==1
        for off in (0x28,0x2a,0x31,0x32,0x35,0x36,0x37):assert expected_owner[off]==0
        assert expected_owner[0x10]==255 and expected_owner[0x1f:0x22]==bytes([1,1,6])
        assert [a.old.word(expected_owner,x) for x in (0x84,0x88,0x8c,0x90,0x98)]==[0]*5
        assert tuple(c['declared_history_words'])==struct.unpack_from('<3I',msg,0x30)
        assert msg[0x16]==e and msg[0x18]==ten and msg[0x23]==selected
        assert c['native_stored_history_flag_word']=='0xd7d7d701'
        struct.pack_into('<5I',expected_owner,0x80,0xd7d7d701,*c['declared_history_words'],0)
        assert bytes(expected_owner)==bytes.fromhex(c['owner_after_hex'])==h[0x10:0xf3c]
        flag=int(e==1 and ten==0);set_flags+=flag
        assert c['native_controller_flag10']==flag and a.old.word(h,expected_selected-heap+0x10)==flag
        for obj,private,vt in ((c4,pc4,0x2422b4),(c524,p524,0x242264)):
            assert struct.unpack_from('<III',h,obj-heap)==(a.IMAGE+vt,owner,0)
            assert a.old.word(h,obj-heap+0x14)==private and a.old.word(blob,vt+8)==a.IMAGE+0x143f38
        assert not c['normal_mode_callback_return_MAIN_video_hardware_or_recovery_proven']
        assert c['explicit_gaps']==['manager callback-object allocation/construction7a2d4..7a300',
            'normal boot and heap callback binding','first trace global/MMIO and remaining owner mode handler']
    assert cases=={(s,v,e,t) for s in (165,195) for v in (0,1) for e,t in ((0,0),(1,0),(1,1))}
    assert len(events)==60 and set_flags==4
    for event in events:
        assert event['image_all_regions_and_entire_stack_exact_poststate_checked']
        assert not event['memory_read_write_hooks_installed'] and not event['native_interrupts']
        assert event['PC_observation_may_include_annulled_delay_slots'] and not event['MMIO_instruction_patch_or_fake_return']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    im.write_json(STAGE/'attempt-correction.json',{'created_utc':now,'classification':'harness_resume_stop_not_removed',
        'first_attempt_source_sha256':im.sha((failed/'executed-source.py').read_bytes()),
        'formal_source_sha256':im.sha((STAGE/'owner_mode.py').read_bytes()),'source_diff':diff,
        'diagnostic_reproduction':'Same first case reproduced after failure: PC8007af58, original selector stop, no native owner-handler entry or indirect callback observed. Expected stack updates therefore had not occurred.',
        'correction':'Remove only current selector stop when resuming the same unexecuted JALR. No instruction/input/expected-state change.',
        'firmware_defect_claimed':False})
    offsets={0x7a2b4:'original manager mode-byte store during owner allocation',0x7a2c4:'actual owner constructor call',
        0x7a2d0:'native returned owner pointer store',0x12f224:'native owner dispatch index zero',
        0x12f270:'native embedded parameter constructor call',0x12f29c:'native single-byte owner80 initialization',
        0x12f2a0:'native owner98 initialization',0x1f3868:'native embedded first-byte ff default',
        0x1378fc:'earlier initializer original caller selects stack buffer',0x137920:'earlier1352f0 used on temporary parameter buffer',
        0x135324:'earlier initializer writes byte4, not whole owner dispatch index',
        0x135328:'earlier initializer writes byte5=1',0x13532c:'earlier initializer writes byte6=1',
        0x135300:'earlier initializer writes byte7=1',0x7af58:'resumed original selected mode virtual call',
        0x143f50:'native control-object local flag store',0x134d50:'native constructed owner index read',
        0x134da8:'actual original table-based owner handler call',0x12f7e4:'native one-byte scratch flag store',
        0x12f81c:'native entire scratch word load retains high padding',0x12f824:'native owner history flag-word store',
        0x12f828:'native payload28 to owner84',0x12f82c:'native payload2c to owner88',0x12f830:'native payload30 to owner8c',
        0x12f84c:'unexecuted first trace-global read',0x12f880:'unexecuted later trace timing MMIO read',
        0x12f910:'unexecuted later original mode/geometry classification call'}
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN);rows=[]
    for off,meaning in offsets.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off),None)
        rows.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str if ins else 'not decoded','meaning':meaning})
    pair_offset=a.old.GP-a.IMAGE-0x6a94
    assert pair_offset==0x2480c4 and struct.unpack_from('<II',blob,pair_offset)==(a.IMAGE+0x12f7dc,0)
    im.write_json(STAGE/'native-provenance-and-role-correction.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'instructions':rows,'mode_table_pair0':{'file_offset':hex(pair_offset),'function':hex(a.IMAGE+0x12f7dc),'adjustment_word':0},
        'role_correction':{'earlier_label':'1352f0 owner-default initializer',
            'corrected_scope':'Local parameter-structure initializer; original137920 uses a stack temporary. It is not proof of the complete GOP owner constructor.',
            'actual_owner_constructor':'12f21c called by original manager7a2c4 after nativef2c allocation',
            'earlier_initializer_if_applied_at_owner_base_word4':'0x01010100','actual_new_owner_native_word4':'0x0',
            'earlier_bounded_instruction_results_retained':True,'normal_runtime_claims_not_promoted':True},
        'actual_message_production_trace_hardware_mode_return_MAIN_or_recovery_proven':False})
    review={'status':'PASS_ACTUAL_OWNER_ORIGIN_AND_CONTINUOUS_NATIVE_MODE_DISPATCH_WITH_ROLE_REFINEMENT',
        'created_utc':now,'prior_sealed_files_verified':len(pj['files']),'cases':12,'formal_phases':60,
        'native_owner_allocations_and_complete_constructors':12,'total_native_heap_allocations':60,
        'continuous_selected_mode_and_ROM_table_dispatches':12,'local_control_flag_set_cases':4,
        'first_trace_global_stops':12,'preserved_failed_attempts':1,'earlier_owner_initializer_label_corrected':True,
        'review_scope':'Same-agent source and saved-output review; native constructor snapshots, entire owner and block headers/links checked. Harness checks entire image/all regions/full stack. No independent engine or actual camera acceptance.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_actual_GOP_owner_constructor_and_native_mode_handler_dispatch_with_initializer_role_correction'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
        'basis':['stage96封存9件和canonical复核；Mac-only、16项和授权保持。',
            '解释纠正：1352f0是局部参数结构初始化器（原137920用栈临时缓冲），此前称owner默认初始化过宽。实际manager7a2c4调用12f21c，原f2c分配及完整构造返回，索引4原生0；旧有界片段结果保留但不代表正常owner。',
            '12场景60阶段：原manager取得owner地址并绑定双类；从原selector暂停处连续执行模式wrapper及ROM索引0分派到12f7dc，原历史记录从声明payload28/2c/30写入。mode0e/10的三组控制核对对象flag10，未预设函数指针。',
            '停第一个trace全局读取；未关日志/伪造计时/跳过日志后继续。高3字节栈填充原样保留，不称缺陷或有效标志。callback对象工厂、正常启动/锁/真实消息生产及模式返回仍缺。',
            '首次续接未移除当前停止条件的harness错误保留，仅修停止点后通过。实际MAIN/HEVC、声音长录冷启动、同机备份与独立救砖仍未验收。'],
        'completion_not_claimed':True}
    result=rel+'/run-corrected-resume-boundary-20261027/owner-mode-results.json'
    g['latest_stage_evidence']['stage97_actual_owner_mode_dispatch']={'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result,
        'role_correction':rel+'/native-provenance-and-role-correction.json',
        'scope':'Actual manager owner allocation/constructor establishes index0 and defaults; continuous selected mode call uses original ROM table and writes declared history, stopping before trace global. Earlier1352f0 role narrowed to local parameters. Not mode completion or target MAIN.',
        'authorization_unchanged':True,'goal_complete':False}
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Correct earlier1352f0 owner-default label: original caller uses temporary parameter structure, whereas actual manager allocatesf2c and calls12f21c. Proper native owner index0 resolves ROM mode handler12f7dc; constructor defaults and declared message history now have native origins, but final mode geometry/state is not established before trace.',
        'mode_completion_MAIN_hardware_or_recovery_proven':False})
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].append(result)
            req['stage97_scope']='纠正旧1352f0完整owner默认初始化称谓；原managerf2c申请/12f21c实际owner构造索引0，原模式连续经ROM表到12f7dc历史记录后停trace。12例60段，真实消息/回调对象工厂/完整模式及MAIN硬件未证。'
    g['next_safe_offline_actions'].append('stage97已纠正owner构造来源并接原连续mode分派；不要重用1352f0作完整GOP owner，也不要把构造初值当模式应用最终值。追声明mode消息真实生产、trace缓冲/计时初始化和未执行131590模式几何链、7a2d4..7a300回调对象工厂/RTOS。不得禁日志或伪造MMIO求通过。全部实机和同机恢复保持，仅Mac。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 实际owner构造与原模式分派纠正](<'+rel+'/README.md>)：12场景60阶段；纠正1352f0完整owner称谓，原managerf2c申请/12f21c构造→ROM索引0模式处理及历史记录，停trace前；完整模式/MAIN硬件恢复未证，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            raw=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage97-native-owner-mode-dispatch/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
