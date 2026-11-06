#!/usr/bin/env python3
"""Seal sequential reselection/packet evidence without hardware claims."""
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
    prior=s.parent/'stage75-private-preset-storage/final-receipt.json'
    assert im.sha(prior.read_bytes())=='e0cf1c37bc032542958e19b9a4c42ee50949a570d8cd80908c25274bd857b2df'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((h.ROOT/row['path']).read_bytes())==row['sha256']
    review=json.loads((s/'completed-evidence-review.json').read_text())
    proof=s/'run-explicit-packer-stop-20261026/reselection-results.json'
    result=json.loads(proof.read_text())
    assert review['total_bounded_fragments']==result['bounded_fragments']==29
    assert review['prepared16M_packet_retained_future_partial_packet_returns24498176']
    assert review['private_gate_closes_on_reentry_without_overwriting_external_selection_or_dropping_live_dependency']
    assert not review['real_reentrancy_concurrency_config_epoch_complete_Start_main_recording_or_recovery_proven']
    assert result['source_receipt']['script_sha256']==im.sha((s/'reselection.py').read_bytes())
    assert (proof.parent/'executed-source.py').read_bytes()==(s/'reselection.py').read_bytes()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    observation={'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage75 sealed24 files/canonical verified; dedicated guest storage and native workspace scope.',
        'new_evidence':'Sequential independent original selector restores default selection; prepared16M packet stays, new partial packet returns24498176. Private writer re-entry detects OWNER13 and retains live dependency.',
        'verification':'2reselection/1no-reselection cases,29 bounded fragments; separate independent stack and unchanged suspended request stack.',
        'natural_path_limit':'Known direct Open selector precedes publication. No later first-Start/indirect/runtime reselection or real concurrency proof.',
        'latest_user_operational_instruction':'Windows unavailable; use Mac for now.',
        'Windows_UU_actions_this_turn':0,'camera_operations':False,
        'full_goal_requirements_retained':16,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'coordinator-observations.json',observation)
    summary={'created_utc':now,'status':'MAC_ONLY_SEQUENTIAL_NATIVE_RESELECTION_PACKET_DIVERGENCE_AND_OWNER_GUARD',
        'reselection_cases':2,'no_reselection_control':1,'bounded_fragments':29,
        'first_prepared_partial_packet_target':16000000,'new_partial_packet_after_reselection_target':24498176,
        'private_copy_and_first_packet_and_pending_stack_preserved':True,
        'writer_reentry_after_foreign_selection':{'result':13,'private_gate':0,'fault':13,'live':1},
        'writer_reentry_without_reselection':{'result':0,'private_gate':1,'fault':0,'live':2},
        'actual_config_generation_shared_lock_full_Start_concurrency_or_recording':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_sequential_native_reselection_prepared_packet_lifetime_and_private_owner_guard'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage75封存24件/canonical复核。本轮不改C原型，原目标请求暂停于修正查询返回后；独立入口使用另一栈，未改原挂起栈或制造内核回复。',
                 '两组独立原选择器同ID/type2重选后，选择指针回原静态记录；原局部率打包新包target24498176，已复制旧包仍16M，私有副本/guard/FH缓存及ID/挂起结果保持，私有Control未随原选择器更新。',
                 '编译写者再入检测OWNER13，关自己的gate、保留live1及外部选择，不恢复指针、不丢引用。不重选对照仍16M并允许登记另一声明生产者live2；均不当作真实线程/消费者。3例29段复核。',
                 '当前直接候选21ee98在Open中先于发布调用，未证首次Start以后自然重选、间接调用覆盖、运行时合法重入/并发或配置代次。局部包不是完整Start/传输/成片。完整16项和Mac-only、原相机授权不变。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage76_native_reselection_and_packet_lifetime']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'result':rel+'/run-explicit-packer-stop-20261026/reselection-results.json',
        'caller_and_packet_scope':rel+'/selector-caller-and-packet-scope.json',
        'scope':'Sequential independent native selector/partial-packer entries; not real concurrency, legal reentrancy, complete Start or hardware proof.',
        'authorization_unchanged':True,'goal_complete':False}
    g['current_guest_adapter_prototype']['last_verified_in_stage']=s.name
    g['current_guest_adapter_prototype']['reselection_guard_scope']={
        'evidence':rel+'/run-explicit-packer-stop-20261026/reselection-results.json',
        'owner_guard_detects_native_reselection_on_declared_reentry':True,
        'private_gate_not_camera_stop_or_true_configuration_epoch':True,
        'prepared_packets_survive_current_pointer_change':True}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G16'):
            req['evidence'].extend([rel+'/run-explicit-packer-stop-20261026/reselection-results.json',rel+'/selector-caller-and-packet-scope.json'])
            req['stage76_scope']='两组顺序独立原重选让未来局部包回24498176，既有16M包/独立副本/挂起栈保持，Control代次不自动更新。写者再入OWNER13关私有gate且保留live1/外部选择；无重选对照仍16M/live2。3例29段，不证明真实并发/合法重入、首次Start自然覆盖、真实代次/全Start/硬件与恢复。'
    g['next_safe_offline_actions'][1]+=' stage76原重选后新局部包与既有旧包可不同，缓存FH/同ID/旧查询值和私有token均不够；继续实际Start/Close/重新Open及原共享同步/可信配置代次/所有旧包消费者，不能把私有gate0当相机停止或恢复完成。已知直接Open选择在发布前，不因此贸然迁移hook。'
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint'):
        assert g[key]==old[key]
    assert g['external_dependencies']==old['external_dependencies'] and len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3 原重选与参数包寿命](<work/sony-firmware-20261024/stage76-native-reselection-and-packet-lifetime/README.md>)：独立重选后新局部包回默认24498176，旧16M包保持；原型再入OWNER13关闭私有gate并保留引用，3例29段。非真实并发/完整Start/主录/恢复证据；仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    rows=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
          for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage76-sequential-reselection-and-packet-lifetime/1',
        'created_utc':now,'volume_uuid':im.VOLUME,'files':rows,'previous_manifest_sha256':im.sha(prior.read_bytes()),
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in rows)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(rows),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'actual_runtime_concurrency_proven':False,'goal_complete':False}))


if __name__=='__main__':main()
