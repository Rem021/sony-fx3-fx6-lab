#!/usr/bin/env python3
"""Quarantine the faulty guest caller and seal corrected result-buffer scope."""
from pathlib import Path
import datetime
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume();s=STAGE;im=h.im;assert not (s/'final-receipt.json').exists()
    canonical=h.BASE/'GOAL_STATUS.json';before=(s/'goal-status-before.json').read_bytes()
    prior=s.parent/'stage73-native-free-message-path/final-receipt.json'
    assert im.sha(prior.read_bytes())=='ad9808d60e977f22db80f43eedbbd9e8e8da263a231e8fe85fae35e499c418f7'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((h.ROOT/row['path']).read_bytes())==row['sha256']
    review=json.loads((s/'completed-evidence-review.json').read_text())
    proofpath=s/'run-20261026/rate-ABI-results.json';proof=json.loads(proofpath.read_text())
    assert review['total_bounded_fragments']==41 and review['old24_saved_LR_and_register_slots_corrupted']
    assert review['fixed56_all_saved_register_slots_unchanged'] and review['fixed56_all_original52_span_writes_contained']
    assert not review['channel_return_unwind_real_OSAL_hardware_main_recording_or_recovery_proven']
    assert proof['source_receipt']['script_sha256']==im.sha((s/'rate_abi_fix.py').read_bytes())
    assert (proofpath.parent/'executed-source.py').read_bytes()==(s/'rate_abi_fix.py').read_bytes()
    assert (proofpath.parent/'compiled-source.c').read_bytes()==(s/'channel_adapter.c').read_bytes()
    obj=proofpath.parent/'channel_adapter.a64.o';objsha=im.sha(obj.read_bytes())
    assert objsha==proof['source_receipt']['corrected_object_sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    correction={'recorded_utc':now,'status':'CONFIRMED_OLD_GUEST_CALLER_UNSAFE_QUARANTINED',
        'affected_stage':'stage69-native-16M-callpath','old_container_bytes':24,
        'original_write_span_bytes':52,'actual_written_bytes':50,'outside_old_container_bytes':26,
        'saved_return_address_and_register_slots_corrupted':True,
        'why_prior_boundary_was_insufficient':'Old checks read only24-byte prefix and paused inside the channel before adapter unwind. Correct numeric prefix/alignment did not prove saved frame safety.',
        'numeric_prefix_scope_retained':'Original trace/target/CPB bytes were actually observed; old adapter cannot support safe call/return/deployment claims.',
        'original_only_stages70_to73':'Compiled adapter mapped inert and never entered; original-only observations retain their own bounded scopes.',
        'old_artifacts_modified_or_deleted':False,'old_camera_use_permitted':False,
        'new_prototype':'56-byte guest-only result container, observed52-byte write span covered; saved slots unchanged in two target cases.',
        'new_object_sha256':objsha,'new_camera_use_permitted':False,
        'result':rel+'/run-20261026/rate-ABI-results.json'}
    im.write_json(s/'confirmed-quarantine-and-correction.json',correction)
    observation={'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage73 sealed18 files and canonical checked; original free-message paths and local ACK scope.',
        'new_evidence':'Old24 result declaration overwrites saved LR and register slots. New56 guest container covers original52-span and preserves entire remaining caller frame.',
        'verification':'OldA5/C3, fixedA5/C3, UHD control and closed-gate control;41 bounded fragments plus completed readback.',
        'review_process':'Former handle disappeared without review output. Reran only readback; fixed duplicate boundary/resume observer count and retained failed review source. Native tests not repeated.',
        'latest_user_instruction':'Windows unavailable; use Mac for now. User reaffirmed goal active.',
        'Windows_UU_actions_this_turn':0,'camera_operations':False,
        'full_goal_requirements_retained':16,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'coordinator-observations.json',observation)
    summary={'created_utc':now,'status':'MAC_ONLY_OLD_QUERY_ABI_QUARANTINED_FIXED_GUEST_RESULT_CONTAINER',
        'old_baseline_cases':2,'fixed_target_cases':2,'regression_controls':2,'bounded_fragments':41,
        'old_container24_saved_LR_corruption':True,'new_container56_saved_slots_preserved':True,
        'original_write_span':52,'written_bytes':50,'unwritten_inside_span':[46,47],
        'fixed_target_trace_target_CPB':[25999360,16000000,26000000],
        'native_channel_return_unwind_hardware_recording_or_recovery':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_confirmed_old_rate_result_stack_overwrite_and_corrected_guest_container'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage73封存18件/canonical及stage69封存50件复核；发现自编译适配器把原查询返回结构截为24字节。原写入50字节/跨度52，26字节越过旧对象，A5/C3均覆盖保存返回地址及寄存器。旧版明确隔离，历史原件保留。',
                 '只扩大结果容器到56及改编译断言；两组目标逐原指令记录写入，容器外整个帧与六个保存槽保持。原16M前三值、FH描述、通道实参保持，原消息/OSAL仍到未执行内核锁。',
                 '旧基线2例、新目标2例、UHD/关闭入口2对照合计41段。未通过模拟原通道返回或强制退栈证明修复；生产者live1仍保留，代码/数据未回收。',
                 '原Sony结构完整sizeof/尾字段语义、自然下游消费、原通道返回、硬件主录和恢复未证。旧阶段70至73适配器未执行的原函数证据仍各有限定范围；完整16项和Mac-only/缓存PnP授权保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage74_rate_result_ABI_fix']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'result':rel+'/run-20261026/rate-ABI-results.json',
        'confirmed_quarantine':rel+'/confirmed-quarantine-and-correction.json',
        'new_C_source':rel+'/channel_adapter.c','new_object':str(obj.relative_to(h.ROOT)),
        'new_object_sha256':objsha,'scope':'Old guest caller overwrite reproduced; fixed result container bounded in guest only, no actual Sony type/return/hardware or recovery proof.',
        'authorization_unchanged':True,'goal_complete':False}
    g['corrections_to_prior_stage']['stage69_rate_result_ABI_stack_corruption']=correction
    for key,evidence in g['latest_stage_evidence'].items():
        if key.lower().startswith('stage69_'):
            evidence['subsequent_result_ABI_correction']={'status':'OLD_GUEST_ADAPTER_QUARANTINED_SAVED_LR_OVERWRITE',
                'evidence':rel+'/confirmed-quarantine-and-correction.json',
                'prefix_numeric_observation_only_not_safe_call_or_return':True}
    g['current_guest_adapter_prototype']={'stage':s.name,'source':rel+'/channel_adapter.c',
        'object':str(obj.relative_to(h.ROOT)),'object_sha256':objsha,'container_size':56,
        'scope':'UNDEPLOYABLE_GUEST_ONLY; observed original52-byte write span contained, saved slots intact. Sony complete type/return/hardware not proven.',
        'older_stage69_object':'QUARANTINED_24BYTE_RESULT_OVERWRITES_SAVED_LR',
        'camera_or_persistent_use_permitted':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G16'):
            req['evidence'].extend([rel+'/run-20261026/rate-ABI-results.json',rel+'/confirmed-quarantine-and-correction.json'])
            req['stage74_scope']='发现旧stage69查询24字节声明越界26字节，覆盖保存LR/寄存器，旧客体适配器隔离。新56容器覆盖原52跨度，目标A5/C3保存槽/帧外字节不变，仍读16M并传原实参到原内核边界；原通道返回/完整退栈、Sony类型全部语义、硬件和同机恢复未证。完整16项状态不放宽。'
    g['next_safe_offline_actions'][0]+=' stage74旧stage69结果24字节声明已确认覆盖保存LR，严禁复用旧适配器；当前新56容器只覆盖原52字节写入span。后续原查询/thunk/参数消费者必须核对完整结果空间、保存槽和实际返回，不以三字段前缀/对齐或到达内核边界冒充调用安全。'
    g['next_safe_offline_actions'][1]+=' stage74要继续原自然下游消费者与完整返回ABI，未分类尾部/填充不擅自归零；生产者live1、实际消费者完成和真实共享同步要求仍保留。'
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint'):
        assert g[key]==old[key]
    assert g['external_dependencies']==old['external_dependencies']
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3 离线适配器返回结构修复](<work/sony-firmware-20261024/stage74-rate-result-ABI-fix/README.md>)：旧24字节声明覆盖保存返回地址，已隔离；新56容器覆盖原52字节跨度并保持保存槽，6例41段复核。仅客体修复，实际通道返回/主录/恢复未证；Windows延后。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage74-query-result-overwrite-quarantine-and-fix/1',
        'created_utc':now,'volume_uuid':im.VOLUME,'files':files,
        'previous_manifest_sha256':im.sha(prior.read_bytes()),
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'old_saved_LR_overwrite_confirmed':True,'fixed_guest_only':True,'goal_complete':False}))


if __name__=='__main__':main()
