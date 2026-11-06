#!/usr/bin/env python3
"""Review gate transitions and keep parent-record/runtime requirements intact."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import gate_event as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage87-native-frame-state-command-bit/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-20261026';j=json.loads((run/'gate-event-results.json').read_text())
    assert j['status']=='PASS_NATIVE_PARENT_PUBLICATION_HEVC_GATE_SET_AND_GATED_COPY_CLEAR'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'gate_event.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'gate_event.py').read_bytes()
    src=BASE/'stage86-hevc-vui-mode-conversion/run-20261026/vui-mode-results.json'
    assert im.sha(src.read_bytes())==j['source_receipt']['stage86_result_sha256']
    sources=json.loads(src.read_text())['cases']
    blob=a.old.prev.a.prev.p.a.v.VCD_PATH.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(a.old.prev.a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    assert len(j['cases'])==12 and j['bounded_phases']==32
    events=[];success=0
    for c in j['cases']:
        source=next(s for s in sources if s['seed']==c['seed'] and s['kind']==c['source_kind'] and s['source_label']==c['source_label'])
        gop=bytearray.fromhex(source['GOP_after_hex']);assert c['source_GOP_hex']==gop.hex() and a.word(gop,0xe8)&1==0
        event=c['declared_parent_event_byte'];kind=c['kind'];assert event in (0,0x10)
        m=bytearray(48);m[:4]=gop[0x7c:0x80];m[5]=(a.word(gop,0x84)>>15)&1;m[6]=gop[0x8b]
        m[8:12]=gop[0xe0:0xe4];m[12]=a.word(gop,0xd8)&15;m[16:48]=gop[0xf4:0x114]
        assert c['declared_metadata48_hex']==m.hex()
        iframe=bytearray([0x91])*4096;iframe[0x4c4]=0
        struct.pack_into('<I',iframe,0x4c8,a.HANDLE+4 if kind!='missing_input_handle' else 0)
        struct.pack_into('<H',iframe,0xe0,0x1234)
        if event:iframe[0x4c4]|=0x10
        oframe=bytearray([0x92])*4096;oframe[0x4c4]=0
        struct.pack_into('<I',oframe,0x4c8,a.HANDLE+8 if kind!='missing_output_handle' else 0)
        ipack=bytearray([0xb6])*4096;opack=bytearray([0xc4])*4096
        es=c['events'];events.extend(es)
        if kind=='missing_input_handle':
            assert len(es)==1 and es[0]['stop']=='before_unknown_GP_input_buffer_allocation'
            assert c['GOP_before_pack_hex'] is None and c['decoded_output_target'] is None
            assert len(c['snapshots'])==1 and c['snapshots'][0]['input_frame_flag4']
            assert not c['snapshots'][0]['input_payload_copied']
        else:
            assert len(es)==3
            if event:
                assert es[0]['stop']=='after_native_parent_payload_copy_before_other_work'
                assert es[1]['stop']=='native_GOP_gate_set_before_unexecuted_virtual_predicate'
                ipack[0xec:0x11c]=m
                gop[0xbf4:0xc24]=m;gop[0x7c:0x80]=m[:4]
                struct.pack_into('<I',gop,0x84,(a.word(gop,0x84)&~(1<<15))|((m[5]&1)<<15))
                gop[0x8b]=m[6];gop[0xe0:0xe4]=m[8:12]
                struct.pack_into('<I',gop,0xd8,(a.word(gop,0xd8)&~15)|(m[12]&15))
                struct.pack_into('<I',gop,0xe8,a.word(gop,0xe8)|1);gop[0xf4:0x114]=m[16:48]
            else:
                assert es[0]['stop']=='parent_event_bit4_off_before_other_work'
                assert es[1]['stop']=='input_frame_bit4_off_before_other_backend_updates'
            assert c['GOP_before_pack_hex']==gop.hex()
            if event and kind=='normal':
                success+=1
                assert es[2]['stop']=='after_gated_copy_publication_and_source_gate_clear_before_epilogue'
                opack[0x14:0xb0]=gop[0x78:0x114];opack[0xec:0x11c]=gop[0xbf4:0xc24]
                oframe[0x4c4]|=0x10
                assert a.word(opack,0x84)&1==1
                struct.pack_into('<I',gop,0xe8,a.word(gop,0xe8)&~1)
                assert c['decoded_output_target']==(20000000 if c['source_kind']=='target20M' else 16000000)
                assert [s['GOP_gate'] for s in c['snapshots']]==[False,True,False]
            elif event:
                assert kind=='missing_output_handle' and es[2]['stop']=='before_unknown_GP_output_buffer_allocation'
                assert c['decoded_output_target'] is None
                assert [s['GOP_gate'] for s in c['snapshots']]==[False,True,True]
            else:
                assert es[2]['stop']=='closed_GOP_gate_before_outer_epilogue' and c['decoded_output_target'] is None
                assert [s['GOP_gate'] for s in c['snapshots']]==[False,False,False]
        assert c['GOP_after_hex']==gop.hex() and c['input_frame_after_hex']==iframe.hex()
        assert c['input_packet_after_hex']==ipack.hex() and c['output_frame_after_hex']==oframe.hex() and c['output_packet_after_hex']==opack.hex()
        assert c['native_gates_not_host_set_on_GOP_or_frames']
        assert not c['actual_parent_record_production_common_and_virtual_callbacks_lifetime_dispatch_or_MAIN']
        assert not c['real_allocation_ownership_ACK_hardware_or_recovery']
        assert all(hex(a.IMAGE+x) in es[0]['CODE_observed_PCs'] for x in (0x141128,0x19a890,0x141234))
    assert success==4 and len(events)==32
    for e in events:
        assert e['original_image_and_all_declared_parent_inputs_unchanged'] and e['entire_declared_stack_unchanged']
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots'] and not e['MMIO_code_replacement_or_fake_return']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    review={'status':'PASS_NATIVE_DECLARED_PARENT_EVENT_GATE_OPEN_CHECK_COPY_CLEAR',
      'created_utc':now,'prior_sealed_files_verified':8,'formal_cases':12,'formal_bounded_phases':32,
      'native_gate_0_1_0_success_cases':4,'event_off_native_skip_checked':True,
      'missing_input_handle_flag_set_before_allocation_not_copy_completion':True,
      'missing_output_handle_keeps_gate1_before_allocation':True,
      'record_payload_handles_declared_not_real_module_reply':True,
      'common_virtual_ownership_scheduling_MAIN_hardware_or_recovery_proven':False,
      'review_scope':'Same-agent source/full-region/state-transition review; no independent engine or camera acceptance.',
      'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_parent_publication_HEVC_gate_set_and_gated_output_copy'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
      'basis':['stage87封存8件/canonical复核；仅Mac，官方与全部授权/16项保持。',
               '原141128后台空状态谓词/记录bit4检查，原置输入帧flag并拷48；原HEVC d9000吸收元数据并置GOPgate1，原d95a4检查真实执行再拷156+48并清gate0。未由host设置GOP/帧gate。',
               '12例32阶段，4组成功gate0→1→0；事件off全跳过。缺输入句柄在分配前frameflag已1但未拷；缺输出句柄gate1保留、未拷。未执行分配/失败处理，不称实机缺陷或完成。',
               '源记录/payload48/句柄和两个帧为声明输入；真实事件生成/ACK/所有权、公共回调/虚谓词/调度/MAIN/硬件与全部同机恢复仍缺。日期进入10-27，已生成run目录保留。'],
      'completion_not_claimed':True}
    result=rel+'/run-20261026/gate-event-results.json'
    g['latest_stage_evidence']['stage88_parent_publication_GOP_gate']={
      'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result,
      'scope':'Declared parent event + constructed metadata48; native publisher/gate writer/check/copy/clear. Entries omit common/virtual/ownership paths; no actual record/dispatch/MAIN/hardware.',
      'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage88_scope']='声明上游记录经原发布→HEVCgate置1→原门控拷156+48清0，12例32阶段。缺句柄停GP分配前，flag不是完成证明。真实记录/ACK/所有权/公共虚回调/调度/MAIN/硬件和恢复未证，16项保持。'
    g['next_safe_offline_actions'].append('stage88优先追manager+c90上游记录bit4及payload+ec48的真实生产/接收/确认与所有权，核对公共回调/虚谓词/调度和MAIN绑定。不得以声明模块回复替代实机响应，不以frameflag或GOPgate单独判断复制/分配/硬件完成；缺句柄停点未执行实际失败处理。前轮4差异字节和全部主录/恢复要求保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 上游发布与GOP门控](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：声明事件经原发布/置gate/门控复制清位，12例32阶段；缺句柄停分配前。真实记录/公共虚回调/调度/MAIN与硬件仍未证，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{
      'schema':'fx3-stage88-native-parent-event-GOP-gate/1','created_utc':now,
      'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
      'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
      'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
      'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
      'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
                      'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
