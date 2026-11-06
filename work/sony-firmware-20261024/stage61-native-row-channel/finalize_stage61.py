#!/usr/bin/env python3
"""Seal verified row/channel receipts, no execution replay or camera access."""
import ast
import collections
import datetime
import json
from pathlib import Path
import row_channel as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    assert not (stage/'final-receipt.json').exists()
    prior=f.last.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((root/row['path']).read_bytes())==row['sha256']
    run=stage/'run-two-object-bounds-20261026';proof=run/'row-channel-results.json'
    d=json.loads(proof.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    assert im.sha((stage/'row_channel.py').read_bytes())==receipt['script_sha256']==im.sha((run/'executed-source.py').read_bytes())
    for node in ast.walk(ast.parse((stage/'row_channel.py').read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','store'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==receipt['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    obj=f.prev.prev.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    wobj=f.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o'
    assert im.sha(obj.read_bytes())==receipt['match_wrapper_object_sha256']
    assert im.sha(wobj.read_bytes())==receipt['writer_object_sha256']
    for path,key in ((f.n.STAGE/'official-files/nflasha15/kmod/liro.ko','LIRO_sha256'),
      (f.n.STAGE/'official-files/nflasha3/vmlinux.bin','kernel_sha256')):
        assert im.sha(path.read_bytes())==receipt[key]
    assert d['status']=='PASS_CONTIGUOUS_NATIVE_ROW_AND_CHANNEL_BOUNDARY'
    cases=d['cases'];assert len(cases)==5 and [c['native_row'] for c in cases]==[386,386,386,431,-1]
    assert [c['seed'] for c in cases]==[0xa5,0xc3,0xc3,0xc3,0xc3]
    events=[e for c in cases for e in c['events']]
    counts=collections.Counter(e['reason'] for e in events)
    assert len(events)==d['bounded_fragments']==30
    assert counts=={'boundary: after_original_kernel_memcpy_before_next_diagnostic':5,'returned':16,
      'boundary: before_original_buffer_channel_preparation':4,
      'boundary: before_unexecuted_channel_acquisition':4,
      'boundary: before_original_no_resource_row_error':1}
    assert sum(len(c['original_diagnostic_calls']) for c in cases)==17
    for i,c in enumerate(cases):
        assert c['source_and_common_remain_original_descriptor'] and c['same_guest_no_post_log_copy_or_return_adapter']
        assert not c['real_logger_state_constructor_channel_provider_Hal_recording_or_recovery']
        assert c['actual_native_matcher_returns'][0]['W0']==c['native_row']&0xffffffff
        prefix=c['events'][3];pcs=prefix['pcs']
        seq=[f.V+0x22f34c,f.V+0x229808,f.V+0x21ecf4,f.prev.prev.BRIDGE,
          f.V+0x225eb8,f.prev.prev.SITE+4]
        positions=[pcs.index(hex(x)) for x in seq];assert positions==sorted(positions)
        assert prefix['SP_before']==hex(f.r.SP) and not prefix['native_output_or_PC_return_adapter']
        assert all(int(x['SP'],16)%16==0 for x in c['original_diagnostic_calls'])
        if i==4:
            assert prefix['stop_pc']==hex(f.V+0x21efc4) and c['original_channel_preparation'] is None
            continue
        for at in (0x21ed78,0x21ed90,0x21edc4,0x21edc8,0x21ee98,0x2261a4,0x21eeb4,0x21dd54):
            assert hex(f.V+at) in pcs
        cont=c['events'][4];assert not cont['independent_entry_fixture']
        assert prefix['stop_pc']==cont['start_pc']==hex(f.V+0x21dd54)
        assert prefix['SP_after']==cont['SP_before']=='0x10007ac0'
        assert cont['stop_pc']==hex(f.V+0x22d394) and cont['SP_after']=='0x10007a30'
        for at in (0x27b988,0x21dee4,0x21df14):assert hex(f.V+at) in cont['pcs']
        ch=c['original_channel_preparation'];acq=ch['acquisition']
        assert acq['x0_x4']==['0x0','0x61003c','0x470','0x806800f3',hex(f.p.COMMON+0x1060)]
        assert acq['LR']==hex(f.V+0x21df18) and not acq['body_executed'] and not acq['acquisition_return_adapter']
        assert c['native_rows'][0]['row']==hex(f.V+0x395108+c['native_row']*0x90)
        slots=bytes.fromhex(c['original_diagnostic_calls'][3]['spill80_hex'])
        vals=[int.from_bytes(slots[j:j+8],'little') for j in range(0,56,8)]
        expected=[2,2073600,62208000,1920,1080,30] if i<3 else [2,8294400,497664000,3840,2160,60]
        assert [vals[1]&0xffffffff,vals[2],vals[3],*(x&0xffffffff for x in vals[4:])]==expected
        private=c['independent_private_writer']
        if i<2:
            assert private['query_before']==24498176 and private['query_after']==16000000
            assert private['independent_guest_call'] and not private['actual_native_callsite_hook_installed']
            assert private['control']['live']==1 and private['control']['phase']==1
        else:assert private is None
    audit=json.loads((stage/'channel-binding-audit.json').read_text())
    assert audit['avcam_sha256']==im.sha(blob) and not audit['native_binding_constructor_factory_manager_or_allocation_provider_executed_here']
    assert audit['aligned_direct_BL_scan_candidates']==[hex(f.V+0x226e84),hex(f.V+0x226eb8)]
    for group in (d['original_regions'],audit['regions']):
        for region in group:
            for ins in region['instructions']:
                at=int(ins['va'],16)-f.V;assert blob[at:at+4].hex()==ins['bytes']
    failure=json.loads((stage/'run-20261026/attempt-failure.json').read_text())
    assert not failure['passing_result'] and "CODE+len(m.code_bytes)" in failure['traceback']
    assert (stage/'run-20261026/attempt-source.py').is_file()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(stage.relative_to(root));ev=str(proof.relative_to(root))
    summary={'created_utc':now,'status':d['status'],'bounded_fragments':30,'stop_counts':dict(counts),
      'native_rows':[386,386,386,431,-1],'native_muted_diagnostic_calls':17,
      'channel_manager_bound_or_acquisition_body_executed':False,
      'independent_target_query_before_after':[24498176,16000000],
      'actual_private_writer_hook':False,'goal_complete':False,'persistent_write_release':False,
      'proof_sha256':im.sha(proof.read_bytes())}
    review={'created_utc':now,'reviewer':'Same-agent source/trace/original-byte/hash review; no independent or physical replay.',
      'prior14files_and_canonical_verified':True,'native_row_selection_and_channel_sizing_same_guest':True,
      'paused_entry_resumed_without_supplied_registers_or_copy':True,
      'only_explicit_initialized_logger_fixture_and_original_mute_setter':True,
      'null_manager_is_partial_fixture_not_camera_defect':True,
      'two_objects_have_separate_execution_bounds_and_original_bytes_checked':True,
      'initial_host_object_length_assertion_failure_preserved':True,
      'independent_writer_not_native_callsite_install':True,
      'static_setter_factory_source_is_not_executed_manager_binding':True,
      'UU_Windows_or_camera_operations':False,'outcome':'PASS_BOUNDED_NATIVE_PREFIX_WITH_PROVIDER_AND_PHYSICAL_GAPS'}
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.last.STAGE/'goal-status-after.json').read_bytes()
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress','basis':[
      '重启后复核stage60全部14件和canonical，不重跑已完成任务；Orca信箱为空。',
      '同客体原queued Open经原静音诊断/真正匹配器返回/行复制/完整预置选择，继续到原通道尺寸准备及22d394申请入口，未补行号或诊断/申请成功。',
      '目标A5/C3行386，人工FF386、UHD431及代理−1对照；30段，17次原静音诊断返回，源FH/common保持。',
      '目标原状态上独立编译writer及原查询从24498176到16000000，不是Sony调用点hook；其lease/锁域/代次和完成通知仍是模型输入。',
      '申请X0为部分fixture中的0，未执行其体；静态发现22c99c setter和factory六加二绑定循环，后续追实际manager及原申请依赖，不能把零值称为相机故障。',
      '保留首次双编译对象长度复核断言失败；所有16要求/授权/硬件时间及成片/同机恢复门槛不变，未操作UU或Windows。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage61_native_row_channel']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json',
      'binding_source':rel+'/channel-binding-audit.json','bounded_fragments':30,
      'scope':'Same partial guest original muted queued-to-row and channel-size prefix, stops before unbound acquisition body. Independent private writer/query only; static factory binding source not executed.',
      'goal_complete':False,'authorization_unchanged':True}
    addition=' stage61在同一部分客体内接通queued→原静音诊断/匹配返回→行复制/完整预置选择→原通道尺寸准备，30段五对照通过；申请22d394入口X0尚未绑定且体未执行。目标原状态上的独立writer/原查询得到16M，不是实际Sony hook。静态定位22c99c和factory六加二绑定循环；真实manager/全局初始化/时钟/同步/硬件与同机恢复仍缺。'
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/channel-binding-audit.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='沿原22c99c setter及factory226e70..226edc六加二绑定循环，追factory首指针/通道管理对象及构造、22d394→22de54/原申请提供者；不插任意非零对象或成功返回。继续核对实际writer调用接合、共享锁/owner代次/生产消费完成、日志时间与输出寿命，全部主录/同机备份恢复门槛不变。'
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    index=root/'README.md';idxbefore=index.read_bytes();text=idxbefore.decode()
    entry='- [2026-10-26 FX3 原行选择到通道申请边界](<work/sony-firmware-20261024/stage61-native-row-channel/README.md>)：同客体queued/原静音诊断/匹配/预置和尺寸准备30段通过，目标独立查询16M；管理对象尚未绑定，未执行申请、主录或恢复。'
    assert entry not in text and text.count('## 相机与固件研究\n')==1
    idxafter=text.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    im.write_json(stage/'summary.json',summary);im.write_json(stage/'coordinator-observations.json',review)
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before and index.read_bytes()==idxbefore
    canonical.write_bytes(after);index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    manifest={'schema':'fx3-stage61-native-row-channel/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':f.PRIOR_SHA,
      'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_firmware_unchanged':True,'Sony_loadable_payload_exported':False,
        'UU_Windows_camera_interface_auth_mode_driver_files_module_WBI_flash':False,
        'actual_acquisition_Hal_recording_backup_restore_or_independent_rescue':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',manifest)
    assert all(im.sha((root/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'bounded_fragments':30,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
