#!/usr/bin/env python3
"""Seal free-path evidence with all device and recovery requirements intact."""
from pathlib import Path
import datetime
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume();im=h.im;s=STAGE;assert not (s/'final-receipt.json').exists()
    canonical=h.BASE/'GOAL_STATUS.json';before=(s/'goal-status-before.json').read_bytes()
    prior=s.parent/'stage72-native-manager-teardown/final-receipt.json'
    assert im.sha(prior.read_bytes())=='1bad5c4cfba82600385e96df861374652103168d6cef7091d0d6beca3aa8a8aa'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((h.ROOT/row['path']).read_bytes())==row['sha256']
    review=json.loads((s/'completed-evidence-review.json').read_text())
    result_path=s/'run-original-sparse-lookup-20261026/free-message-results.json'
    result=json.loads(result_path.read_text())
    assert review['request_cases']==4 and review['independent_decoder_cases']==7 and review['total_bounded_fragments']==55
    assert review['all_requests_stop_before_original_kernel_lock']
    assert review['independent_supplied_ack_not_injected_into_pending_transport']
    assert not review['physical_release_main_recording_or_recovery_proven']
    assert result['source_receipt']['script_sha256']==im.sha((s/'free_message_path.py').read_bytes())
    assert (result_path.parent/'executed-source.py').read_bytes()==(s/'free_message_path.py').read_bytes()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    observation={'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage72 sealed14 files and canonical verified; original local exit/cache branches and static reference lineage.',
        'latest_user_instruction':'Windows unavailable; use Mac for now.',
        'Windows_UU_actions_this_turn':0,'camera_operations':False,
        'new_scope':'Original pending last-reference free entry continued through original message construction and LIRO-bound OSAL; separate local supplied-ACK decoder entries.',
        'native_requests':4,'independent_decoder_cases':7,'bounded_fragments':55,
        'new_dependency':'Handle bit15 sets command bit28. Flagged path first enters diagnostic message allocation using original sparse client lookup and another lock.',
        'no_false_completion':'Both actual request paths stop before original kernel IRQ-lock body; independent supplied ACKs are not replies to the pending calls.',
        'retained_attempts':'Observer counted boundary/resume twice as one; then high-ID original lookup was outside permitted range. Only observation and original code coverage corrected; no Sony bytes or returns changed.',
        'full_goal_requirements_retained':16,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'coordinator-observations.json',observation)
    summary={'created_utc':now,'status':'MAC_ONLY_ORIGINAL_FREE_MESSAGE_AND_INDEPENDENT_ACK_SCOPE',
        'native_request_cases':4,'independent_decoder_cases':7,'bounded_fragments':55,
        'free_request216':'Original tag23/declared handle/1111/mode2; native inline state2,size216,source806800f3.',
        'handle_bit15_route':'0 -> main allocation client3c,size216,wait1; 1 -> first diagnostic allocation client13a,size52,wait0.',
        'high_client_lookup':'Original read-only sparse lookup executed; null in ELF initial state, followed by another original lock.',
        'both_paths_stop_before_kernel_lock_body':True,
        'local_decoder_results':{'status0':0,'positive_status':2,'negative_status_or_bad_magic':1,
                                 'supplied8byte_header_with_unrelated_kind':0},
        'eight_byte_ACK_protocol_legality_full_correlation_and_physical_completion':'UNKNOWN_NOT_A_VULNERABILITY_CLAIM',
        'real_send_reply_physical_release_or_main_recording':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_original_free_message_LIRO_OSAL_dependency_and_independent_local_ACK_semantics'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage72封存14件/canonical复核；另核对stage64封存23件、stage69封存50件。原释放4例与独立回复片段7例合计55段，不伪造原代码返回、内核服务、client或传输回复。',
                 '同一原释放现场继续：原元数据202条和216字节tag23/handle/1111/mode2消息构造；声明句柄不是成功分配。两分支到原LIRO-OSAL申请/原锁后均停于真实内核锁第一条前，没有物理释放或回复。',
                 '句柄bit15置命令bit28；标志分支先走诊断52字节/client13a/等待0申请，原高ID稀疏查找及另一把锁；普通分支本消息216字节/client3c/等待1。未初始化ELF空值不是相机故障或可伪造真实驱动状态。',
                 '独立原回复片段本地检查标记/有符号状态，8字节且首字段无关的明确输入亦可形成0，但不证明该确认不合法、端到端缺少关联或漏洞，更不证明真实释放。完整16项和Mac-only保持，Windows/UU/相机操作0。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage73_native_free_message_path']={
        'readme':rel+'/README.md','summary':rel+'/summary.json','review':rel+'/completed-evidence-review.json',
        'result':rel+'/run-original-sparse-lookup-20261026/free-message-results.json',
        'sparse_lookup_and_ack_audit':rel+'/sparse-client-and-ack-audit.json',
        'scope':'Declared original last-reference requests to unexecuted kernel lock; independent supplied local ACK decoder, no injected reply or physical release.',
        'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G16'):
            req['evidence'].extend([rel+'/run-original-sparse-lookup-20261026/free-message-results.json',
                                    rel+'/sparse-client-and-ack-audit.json'])
            req['stage73_scope']='Mac原释放调用4例、独立本地回复7例共55段；原216字节释放消息及真实LIRO-OSAL申请到未执行内核锁，标志路径先依赖诊断消息/高ID稀疏查找/另一把锁。原驱动、同步发送/回复/实际释放未证；8字节局部确认形成0不证明协议非法、关联缺失或漏洞，也不是实际完成。主录/消费者/同机恢复与全部16项保持。'
    g['next_safe_offline_actions'][0]+=' stage73释放消息bit15/bit28分支先依赖诊断client13a（52字节/等待0）与高ID稀疏查找/另一把锁，继续核对该原client/诊断初始化和失败/等待路径；不能只覆盖主client3c或伪造稀疏表/IRQ状态。'
    g['next_safe_offline_actions'][4]+=' stage73已把原释放消息接到原OSAL申请但未发送/回复；独立8字节本地确认可形成0，先查合法ACK长度/类型/关联与完成语义，不擅自要求回复等于216字节请求长度、不当作漏洞或硬件释放证明。继续原传输/完成/诊断依赖及全部消费者退出。'
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint'):
        assert g[key]==old[key]
    assert g['external_dependencies']==old['external_dependencies']
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3 原释放消息与回复检查](<work/sony-firmware-20261024/stage73-native-free-message-path/README.md>)：Mac离线原释放4例、独立回复7例共55段；标志路径先依赖诊断消息和高ID稀疏查找，两分支均停在原内核锁前。局部确认不等于物理释放，主录/同机恢复未证；Windows延后。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage73-Mac-only-original-free-and-local-ACK-scope/1',
        'created_utc':now,'volume_uuid':im.VOLUME,'files':files,
        'previous_manifest_sha256':im.sha(prior.read_bytes()),
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'Mac_only':True,'goal_complete':False}))


if __name__=='__main__':main()
