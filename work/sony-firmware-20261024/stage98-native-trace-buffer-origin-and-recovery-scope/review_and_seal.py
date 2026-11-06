#!/usr/bin/env python3
"""Review native log-state provenance and keep device/recovery gates unchanged."""
from pathlib import Path
import datetime,difflib,json,struct,sys
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import trace_origin as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage97-native-owner-construction-and-mode-dispatch/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    pj=json.loads(prior.read_text())
    for f in pj['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-corrected-native-buffer-block-20261027';j=json.loads((run/'trace-origin-results.json').read_text())
    assert j['status']=='PASS_NATIVE_TRACE_DESCRIPTOR_INITIALIZATION_AND_MODE_LOG_PATH_TO_ACTUAL_MMIO_BOUNDARY'
    assert not (run/'failed-attempt.json').exists()
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'trace_origin.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'trace_origin.py').read_bytes()
    assert j['source_receipt']['prior_manifest_sha256']==a.PRIOR_SHA
    source=prior.parent/'run-corrected-resume-boundary-20261027/owner-mode-results.json'
    assert j['source_receipt']['stage97_result_sha256']==im.sha(source.read_bytes())
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(path.relative_to(BASE))]
    rows=[struct.unpack_from('<10I',blob,a.TABLE+i*40) for i in range(69)]
    nulls=[i for i,r in enumerate(rows) if not r[1]];assert nulls==[11,12,13,14,16,17,18]
    nonnull=[(i,r) for i,r in enumerate(rows) if r[1]];assert len(nonnull)==62
    assert rows[53][:6]==(53,a.TRACE_CONTROL,24,128,2,1)
    intervals=[(r[1],r[1]+(16 if i==0 else r[2]*r[3]+8)) for i,r in nonnull]
    assert intervals[0][0]==0x80a72100 and intervals[-1][1]==0x80aac284
    assert sum(y-x for x,y in intervals)==237956
    assert all(x1==y0 for (_,x1),(y0,_) in zip(intervals,intervals[1:]))
    failures=[]
    paths=['run-initial-20261027','run-corrected-null-descriptors-20261027','run-corrected-current-entry-stop-20261027']
    explanations=['Non-null assertion incorrectly excluded original null descriptors; corrected to original skip branch.',
        'Inherited current-entry stop caused immediate pause at80061f3c; diagnostic reproduction showed one CODE observation and original boot-table boundary.',
        'Allowed-code list omitted pure RAM auxiliary block62090..620bc; original code disassembled and range added, no instructions patched.']
    for name,explanation in zip(paths,explanations):
        failed=STAGE/name;f=json.loads((failed/'failed-attempt.json').read_text());assert f['completed_cases']==0
        failures.append({'directory':name,'source_sha256':im.sha((failed/'executed-source.py').read_bytes()),
            'failure_sha256':im.sha((failed/'failed-attempt.json').read_bytes()),'classification':'harness_error','explanation':explanation})
    snapshots=[STAGE/x/'executed-source.py' for x in paths]+[STAGE/'trace_origin.py']
    diffs=[list(difflib.unified_diff(x.read_text().splitlines(),y.read_text().splitlines())) for x,y in zip(snapshots,snapshots[1:])]
    assert len(j['cases'])==12 and j['bounded_phases']==84
    events=[];cases=set();trace_hashes=set()
    for c in j['cases']:
        seed,sel,e,ten=c['seed'],c['declared_selector_byte'],c['declared_mode_payload0e'],c['declared_mode_payload10']
        cases.add((seed,sel,e,ten));es=c['events'];events+=es;assert len(es)==7
        pages={int(k,16):bytes.fromhex(v) for k,v in c['final_regions'].items()}
        expected=bytearray([seed])*a.BSS_SIZE
        for i,r in nonnull:
            at=r[1]-a.IMAGE-a.BSS_PA;n=16 if i==0 else r[2]*r[3]+8
            expected[at:at+n]=bytes(n)
            if i==0:expected[at:at+12]=blob[0x247380:0x247388]+blob[0x24738c:0x247390]
            else:struct.pack_into('<I',expected,at,r[1]+8)
        assert pages[a.BSS_PA]==bytes(expected)
        assert pages[a.BSS_PA][:0x100]==bytes([seed])*0x100
        assert pages[a.BSS_PA][0x3a284:]==bytes([seed])*(a.BSS_SIZE-0x3a284)
        at=a.TRACE_CONTROL-a.IMAGE-a.BSS_PA
        assert struct.unpack_from('<I',pages[a.BSS_PA],at)[0]==a.TRACE_CONTROL+8
        assert pages[a.BSS_PA][at+4:at+8]==bytes(4)
        assert c['native_trace_cursor']==hex(a.TRACE_CONTROL+8) and c['native_trace_flag4']==c['native_trace_wrap5']==0
        first=es[0]
        assert first['entry']==hex(a.IMAGE+0x61f3c) and first['PC']==hex(a.IMAGE+0x61ffc)
        assert first['SP']==hex(a.SP_TRACE-0x40)
        assert first['CODE_trace_compressed_to_unique_PCs'] and len(first['CODE_observed_PCs'])==91
        assert first['CODE_total_observations']==sum(first['CODE_pc_counts'].values())==240818
        assert first['CODE_pc_counts'][hex(a.IMAGE+0x67f08)]==62
        assert first['CODE_pc_counts'][hex(a.IMAGE+0x620b0)]==61
        assert first['CODE_pc_counts'][hex(a.IMAGE+0x61ffc)]==1
        trace_hashes.add(first['CODE_ordered_trace_sha256'])
        assert all(int(p,16)<a.IMAGE+0x62000 or int(p,16)>=a.IMAGE+0x62090 for p in first['CODE_observed_PCs'])
        assert [int(x['entry'],16)-a.IMAGE for x in es]==[0x61f3c,0x67d34,0x7a2ac,0x7a304,0x7aed4,0x7af58,0x12f84c]
        assert es[-2]['PC']==es[-1]['entry'] and es[-1]['PC']==hex(a.IMAGE+0x12f880)
        assert es[-1]['SP']==es[-2]['SP']==hex(a.prev.prev.SP_SELECT-0xf0)
        assert [es[-1][k] for k in ('A1','A2','V1','T0')]==[hex(a.TRACE_CONTROL+12),hex(a.TRACE_CONTROL+8),hex(a.TRACE_CONTROL+0x20),hex(a.TRACE_END)]
        assert all(hex(a.IMAGE+x) in es[-1]['CODE_observed_PCs'] for x in (0x12f84c,0x12f850,0x12f85c,0x12f87c,0x12f880))
        assert hex(a.IMAGE+0x12f90c) not in es[-1]['CODE_observed_PCs']
        assert not es[-1]['indirect_calls'] and c['trace_initializer_CACHE_and_tail_unexecuted']
        assert not c['trace_disable_or_timer_value_injected'] and not c['complete_boot_mode_MAIN_video_or_recovery_proven']
        assert c['native_owner']==hex(a.prev.prev.prev.HEAP+0x10)
        h=pages[a.prev.prev.prev.HEAP_PA];owner=0x10
        assert a.old.word(h,owner+4)==0 and a.old.word(h,owner+0x80)==0xd7d7d701
    assert len(trace_hashes)==1 and len(events)==84
    assert cases=={(s,v,e,t) for s in (165,195) for v in (0,1) for e,t in ((0,0),(1,0),(1,1))}
    for event in events:
        assert event['image_all_regions_and_entire_stack_exact_poststate_checked']
        assert not event['memory_read_write_hooks_installed'] and not event['native_interrupts']
        assert event['PC_observation_may_include_annulled_delay_slots'] and not event['MMIO_instruction_patch_or_fake_return']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    public=json.loads((STAGE/'public-source-check.json').read_text());assert len(public['sources'])==3
    assert not public['third_party_code_or_payload_executed'] and not public['FX3_recovery_or_goal_complete']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    im.write_json(STAGE/'attempt-corrections.json',{'created_utc':now,'preserved_failed_attempts':failures,
        'source_diffs':diffs,'formal_result':str((run/'trace-origin-results.json').relative_to(ROOT)),
        'no_firmware_instruction_trace_disable_or_timer_input_change':True,'firmware_defect_or_device_brick_claimed':False})
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    offsets={0x61f54:'original descriptor table base',0x61fd4:'native null-buffer test',
        0x62090:'original classified RAM auxiliary block',0x620a0:'original per-buffer memset call',
        0x620b0:'native initial cursor store',0x61ffc:'unexecuted CACHE boundary',
        0x12f84c:'original flag byte now read from native initialization',0x12f850:'native trace branch not suppressed',
        0x12f85c:'native initialized cursor load',0x12f868:'native available-space comparison',
        0x12f870:'wrap flag store not taken for first initialized record',0x12f87c:'original MMIO address preparation',
        0x12f880:'unexecuted actual MMIO read',0x12f888:'later cursor advance not executed'}
    instructions=[]
    for off,meaning in offsets.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off),None)
        instructions.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str if ins else 'not decoded','meaning':meaning})
    im.write_json(STAGE/'native-provenance-and-boundaries.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'instructions':instructions,'descriptor_table_file_offset':hex(a.TABLE),'descriptor_count':69,
        'nonnull_buffer_count':62,'null_descriptor_indices':nulls,'initialized_span_bytes':237956,
        'descriptors':[{'index':i,'words':[hex(x) for x in r]} for i,r in enumerate(rows)],
        'mode_trace_control_descriptor_index':53,'native_trace_flag4_zero_and_cursor_from_original_init':True,
        'actual_timer_MMIO_address':'0xbe0000ac','actual_timer_unit_or_hardware_behavior_proven':False,
        'CACHE_complete_boot_mode_return_MAIN_or_recovery_proven':False})
    review={'status':'PASS_NATIVE_TRACE_STATE_ORIGIN_AND_UNEXECUTED_MMIO_BOUNDARY',
        'created_utc':now,'prior_sealed_files_verified':len(pj['files']),'cases':12,'formal_phases':84,
        'native_descriptor_entries_per_init':69,'native_buffers_cleared_per_init':62,
        'native_memset_calls_total':744,'native_cursor_stores_total':732,
        'CODE_observations_per_trace_init':240818,'same_ordered_trace_hash_in_all_cases':True,
        'actual_mode_timer_boundary_stops':12,'preserved_failed_attempts':3,'public_primary_sources_checked':3,
        'review_scope':'Same-agent source and stored-output review; entire BSS/guards and original descriptor mapping checked. Harness validates whole image/all regions/full stack. No independent engine or physical hardware/recovery acceptance.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_trace_buffer_initialization_to_real_mode_timer_boundary_and_public_recovery_scope_refresh'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
        'basis':['stage97封存12件和canonical复核；Mac-only、16项/授权保持。',
            '原69项描述表含62非空/7空项，原初始化62次memset和61游标存储逐字节建立trace状态，停CACHE前；当前控制字节0和cursor来自原代码而非关日志fixture。',
            '12例84段，同一mode从12f84c续读实际trace状态并走到12f880 MMIO读前；不注入计时、不跳过日志/CACHE，完整boot/mode/MAIN仍缺。',
            '重读公开primary：A7CII最新3.0.3及服务退出说明；A7IV fastboot主分支2328d18文档明列机型和boot0 crypto例外，无FX3兼容保证。当前缓存PnP授权未扩大。',
            '3个测试框架错误（空项/入口停止点/漏列RAM块）保留，依原代码修正后通过，非机身失败或砖。实际编码/声音长录冷启动、同机备份恢复和独立救砖全部未验收。'],
        'completion_not_claimed':True}
    result=rel+'/run-corrected-native-buffer-block-20261027/trace-origin-results.json'
    g['latest_stage_evidence']['stage98_trace_origin_recovery_scope']={'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result,
        'public_sources':rel+'/public-source-check.json',
        'scope':'Original69-entry trace table initializes62 buffers to unexecuted CACHE; original mode consumes native zero flags/cursor and stops before actual timer MMIO. Public A7CII/A7IV claims scoped, not FX3 recovery proof.',
        'authorization_unchanged':True,'goal_complete':False}
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Previously unbound trace flag/cursor now have original initializer provenance; initialized flag0 naturally takes hardware-timer path, so it cannot be treated as logging disabled. CACHE/timer/mode completion remain unexecuted. Public fastboot crypto boot0 exception and model-specific docs prevent a whole-body FX3 recovery claim.',
        'actual_MAIN_hardware_or_independent_recovery_proven':False})
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].append(result)
            req['stage98_scope']='原69项/62缓冲trace初始化至CACHE前，原mode消费原生0标志/cursor到MMIO前；12例84段。不禁日志/伪造timer，完整mode/boot/MAIN硬件未证。'
        if req['id'] in ('G04','G05','G15','G16'):
            req['evidence'].append(rel+'/public-source-check.json')
            req['stage98_public_scope']='A7CII3.0.3作者服务退出/续接说明和A7IV2328d18 fastboot文档重新核对；read-only不等缓存PnP权限，boot0 crypto例外/FX3独立入口与完整恢复仍未验。'
    g['next_safe_offline_actions'].append('stage98已接原trace RAM来源并证明原0标志走MMIO，不得禁日志/注timer或称CACHE完成。继续查be0000ac计时语义与可验证上下文、原初始化尾部/真实mode消息生产及回调工厂。恢复须区分A7CII应用回滚、A7IV bootROM fastboot及FX3未证入口/格式/覆盖，不能以Mac+Win主机或分区dump命令代替同机恢复回读。仅Mac，16项实机要求保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原日志缓冲、实际MMIO边界及恢复范围](<'+rel+'/README.md>)：12场景84阶段；原69项/62缓冲初始化，mode实际消费trace状态到计时MMIO前，CACHE未执行。公开A7CII/A7IV恢复范围核对，非FX3保证；仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            raw=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage98-trace-origin-recovery-scope/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
