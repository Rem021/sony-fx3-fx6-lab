#!/usr/bin/env python3
"""Seal original HEVC frame-parameter handoff without hardware claims."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import frame_handoff as a
im,BASE,ROOT,IMAGE=a.im,a.BASE,a.ROOT,a.IMAGE


def main():
    im.volume();s=STAGE;assert not (s/'final-receipt.json').exists()
    prior=BASE/'stage81-hevc-qos-consumer-and-release/final-receipt.json'
    assert im.sha(prior.read_bytes())=='26f40c19ae81f315d2656a9bf7f6ab066205703409871b07d5a870f6f3acfd5e'
    rows=json.loads(prior.read_text())['files'];assert len(rows)==10
    for row in rows:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    before=(s/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    formal=s/'run-poststate-checks-20261026';j=json.loads((formal/'frame-handoff-results.json').read_text())
    assert j['status']=='PASS_NATIVE_HEVC_FRAME_PARAMETER_COPY_AND_DECLARED_PACKET_LIFETIME'
    assert j['source_receipt']['script_sha256']==im.sha((s/'frame_handoff.py').read_bytes())
    assert (formal/'executed-source.py').read_bytes()==(s/'frame_handoff.py').read_bytes()
    assert j['source_receipt']['prior_runner_sha256']==im.sha((a.q.STAGE/'hevc_consumer.py').read_bytes())
    src81=prior.parent/'run-20261026/hevc-consumer-results.json'
    src80=BASE/'stage80-vcd-pending-and-timing/run-final-observer-20261026/pending-timing-results.json'
    assert j['source_receipt']['stage81_result_sha256']==im.sha(src81.read_bytes())
    assert j['source_receipt']['stage80_result_sha256']==im.sha(src80.read_bytes())
    original_gops=json.loads(src81.read_text())['target_cases']
    blob=a.p.a.v.VCD_PATH.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(a.p.a.v.VCD_PATH.relative_to(BASE))]
    assert len(j['cases'])==8 and len(j['sequences'])==2 and j['bounded_phases']==14
    events=[]
    for x in j['cases']:
        assert not x['full_callback_current_MAIN_driver_or_hardware_recording_proven']
        assert len(x['steps'])==1
        z=x['steps'][0];events.append(z['event'])
        g=next(t for t in original_gops if t['seed']==x['seed'] and t['source_label']==x['source_label'] and t['declared_control'] is None)
        expected_source=bytearray.fromhex(g['GOP_after_hex'])
        if x['kind']=='closed_gate':
            struct.pack_into('<I',expected_source,0xe8,struct.unpack_from('<I',expected_source,0xe8)[0]&~1)
        assert z['source_GOP_before_hex']==expected_source.hex()
        b=bytes.fromhex(z['source_GOP_before_hex']);after=bytes.fromhex(z['source_GOP_after_hex'])
        packet=bytes.fromhex(z['packet_after_hex'])
        if x['kind']=='normal':
            assert z['copied156_and48'] and z['source_gate_before'] and not z['source_gate_after']
            assert z['frame_parameter_bit10_after'] and z['copied_source_gate_word_bit0']
            assert packet[0x14:0xb0]==b[0x78:0x114] and packet[0xec:0x11c]==b[0xbf4:0xc24]
            assert z['decoded_packet_target']==g['decoded_GOP_target_after']
            assert b[:0xe8]==after[:0xe8] and b[0xec:]==after[0xec:]
            guard=bytearray([0xb6])*4096
            guard[0x14:0xb0]=b[0x78:0x114];guard[0xec:0x11c]=b[0xbf4:0xc24]
            assert packet==bytes(guard)
        else:
            assert not z['copied156_and48'] and b==after
            assert packet.hex()==z['packet_before_hex'] and z['frame_after_hex']==z['frame_before_hex']
            expected='closed_gate_before_outer_epilogue' if x['kind']=='closed_gate' else 'before_unknown_GP_frame_allocation_state'
            assert z['event']['reason']=='boundary: '+expected
        assert z['unclassified_copied_bytes_not_a_complete_valid_hardware_request']
    for x in j['sequences']:
        assert x['new_GOP_target']==20000000 and x['old_packet_target']==16000000
        assert x['old_packet_and_frame_metadata_unchanged']
        assert not x['natural_runtime_order_legal_reentry_bug_or_hardware_observation_proven']
        assert x['first_handoff']['copied156_and48'] and not x['reentry']['copied156_and48']
        assert x['reentry']['packet_after_hex']==x['first_handoff']['packet_after_hex']
        assert x['native_update']['reason']=='boundary: after_target_before_other_fields'
        events.extend([x['first_handoff']['event'],x['native_update'],x['reentry']['event']])
    assert len(events)==14
    for e in events:
        assert not e['memory_read_write_hooks_installed'] and e['memory_read_write_access_trace'] is None
        assert e['original_image_input_and_declared_handle_unchanged']
        assert e['stack_outside_declared_0x200byte_frame_window_unchanged']
        assert not e['native_output_PC_or_service_return_adapter']
    initial=json.loads((s/'run-20261026/frame-handoff-results.json').read_text())
    assert im.sha((s/'run-20261026/executed-source.py').read_bytes())==initial['source_receipt']['script_sha256']
    assert not j['Windows_UU_camera_operations'] and not j['goal_complete'] and not j['persistent_write_release']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(ROOT))
    review={
        'created_utc':now,'status':'PASS_NATIVE_HEVC_FRAME_HANDOFF_AND_DECLARED_OLD_PACKET_RETENTION',
        'prior_sealed_files_verified':10,'ordinary_cases':8,'declared_sequential_cases':2,'bounded_phases':14,
        'native_copy156_and48_target_lands_at_buffer64':True,
        'source_gate_cleared_frame_bit_and_copy_persist':True,
        'native20M_source_update_preserves_prepared16M_packet_in_declared_order':True,
        'original_predicate_full_callback_actual_order_hardware_rate_control_recording_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False,
        'review_scope':'Same agent source/PC/whole-region review; no independent emulator or camera acceptance.',
    }
    im.write_json(s/'completed-evidence-review.json',review);im.write_json(s/'summary.json',review)
    im.write_json(s/'coordinator-observations.json',{
        'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage81 sealed10 files/canonical verified; target reaches declared HEVC GOP field.',
        'new_evidence':'Original gated HEVC copy carries target into separate frame parameters, clears only source gate. Declared later native20M update leaves old16M copy. Rate-control arithmetic was not reached; follow command consumers next.',
        'Windows_UU_actions_this_turn':0,'camera_operations':False,
        'requirements_retained':16,'goal_complete':False,'persistent_write_release':False,
    })
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_native_HEVC_frame_parameter_handoff_and_declared_old_packet_retention'
    g['progress_audit']={
        'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':[
            'stage81封存10件/canonical复核；沿用CODE-only/完整内存前后检查，官方/C原型/授权不变。',
            '原d95a4门控及已有帧句柄检查进入156+48字节复制，GOP+c8目标进缓冲64；帧位10置位、源GOPe8bit0清零、已复制84字的旧bit0保持，句柄/缓冲不回收。闭门不写、缺句柄GP前停。',
            '明确旧GOP16/后端20待处理的顺序对照中，先复制16M，再原HEVC段更新GOP20M，旧副本/帧元数据保持；源gate仍0时重入不复制。未证明自然运行顺序/合法重入或实机缺陷。',
            '8普通/2顺序14阶段核对。原虚调用谓词/完整回调/真实MAIN/配置代次/码率控制计算/硬件及全部实机与同机恢复仍缺；本轮闭合参数打包，不将它说成码率算法。',
        ],'completion_not_claimed':True,
    }
    g['latest_stage_evidence']['stage82_hevc_frame_parameter_handoff']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json',
        'result':rel+'/run-poststate-checks-20261026/frame-handoff-results.json',
        'scope':'Independent post-predicate HEVC handoff, captured trial GOP/backend plus declared frame/handle. Sequential counterexample is not natural runtime/concurrency proof.',
        'authorization_unchanged':True,'goal_complete':False,
    }
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G16'):
            req['evidence'].append(rel+'/run-poststate-checks-20261026/frame-handoff-results.json')
            req['stage82_scope']='原156+48字节HEVC帧参数交接传递目标、清源gate并留帧位/句柄/副本；声明顺序后源GOP20与旧包16可并存，非实际调度/合法重入/硬件缺陷。8普通2顺序14阶段；虚谓词/完整回调/真实MAIN/码率计算/硬件与恢复未证。'
    g['next_safe_offline_actions'].append(
        'stage82继续HEVC帧参数缓冲64目标字的命令层/实际编码消费者、真实GOP/帧构造和MAIN绑定、可信配置代次及旧副本完成/归还。源gate0/源查询20不代表已复制旧16参数结束；顺序试验不可当实机竞态或原更新缺陷。原虚谓词/全回调/码率计算、硬件与全部实机/同机恢复要求保留。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3 HEVC帧参数交接与旧副本](<work/sony-firmware-20261024/stage82-hevc-frame-parameter-handoff/README.md>)：目标字经原156+48字节交接进独立缓冲，源gate清零而副本保留；8普通/2顺序14阶段。非实际调度/码率算法/硬件或恢复证据，仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={
        'schema':'fx3-stage82-hevc-frame-handoff/1','created_utc':now,'volume_uuid':im.VOLUME,
        'files':files,'previous_manifest_sha256':im.sha(prior.read_bytes()),
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':review,'requirements_retained':16,'authorization_unchanged':True,
    }
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((ROOT/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'hardware_recording_or_recovery_proven':False,'goal_complete':False}))


if __name__=='__main__':main()
