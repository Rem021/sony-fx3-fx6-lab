#!/usr/bin/env python3
"""Review declared object graph and native bit flow; keep all dispatch gaps."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import frame_command as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage86-hevc-vui-mode-conversion/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-20261026';j=json.loads((run/'frame-command-results.json').read_text())
    assert j['status']=='PASS_NATIVE_FRAME_BOOLEAN_TO_PARAMETER_OVERRIDE_AND_COMMAND_BIT'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'frame_command.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'frame_command.py').read_bytes()
    source_path=prior.parent/'run-20261026/vui-mode-results.json'
    assert im.sha(source_path.read_bytes())==j['source_receipt']['prior_result_sha256']
    sources=json.loads(source_path.read_text())['cases']
    blob=a.prev.a.prev.p.a.v.VCD_PATH.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(a.prev.a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    assert len(j['cases'])==20 and j['bounded_phases']==100
    events=[]
    for c in j['cases']:
        src=next(s for s in sources if s['seed']==c['seed'] and s['kind']==c['source_kind'] and s['source_label']==c['source_label'])
        gop=bytes.fromhex(c['GOP_source_hex']);assert gop.hex()==src['GOP_after_hex']
        assert a.word(gop,0xe8)&1==0 and c['GOP_gate_and_frame_publication_remain_zero']
        flag=int(c['raw_owner36_fixture']!=0);legacy=c['legacy_command_u16_68_fixture']
        assert c['normalized_frame4da']==flag and legacy in (0,0x220)
        frame=bytearray([0x91])*4096;frame[0x4c4]=0;struct.pack_into('<I',frame,0x4c8,a.HANDLE+4);frame[0x4da]=flag
        assert c['frame_after_hex']==frame.hex()
        owner=bytearray([0x72])*4096;owner[0x36]=c['raw_owner36_fixture']
        struct.pack_into('<IIIII',owner,0x80,0xd7d7d701,0x01020304,0x05060708,0x090a0b0c,0)
        assert c['owner_after_hex']==owner.hex()
        packet=bytearray([0xb6])*4096;packet[0x14:0xb0]=gop[0x78:0x114]
        assert c['packet_before_overwrite_hex']==packet.hex()
        struct.pack_into('<I',packet,0x84,(a.word(packet,0x84)&~2)|(flag<<1))
        assert c['packet_after_hex']==packet.hex()
        assert a.word(packet,0x64)==a.word(gop,0xc8)
        assert c['decoded_target']==(20000000 if c['source_kind']=='target20M' else 16000000)
        command=bytearray([c['seed']])*0x9000;struct.pack_into('<H',command,4+0x68,legacy)
        old=bytes(command);command[0x2c04:0x5804]=old[4:0x2c04]
        struct.pack_into('<I',command,0,a.DATA)
        assert c['command_before_leaf_hex']==command.hex()
        final=bytes.fromhex(c['command_after_hex'])
        allowed=set(range(0x2c04+0x778,0x2c04+0x790))
        assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(command,final)))
        expected=bool(flag) or legacy==0x220
        assert c['command_bit13_after']==expected==bool(a.word(final,0x2c04+0x780)&0x2000)
        assert c['producer_original_saved_frame_preserved_during_independent_command_entries']
        assert not c['actual_source_owner36_producer_real_dispatch_or_complete_command_validity']
        assert not c['hardware_recording_or_recovery_proven']
        es=c['events'];events.extend(es);assert len(es)==5
        assert [e['stop'] for e in es]==[
          'native_frame_handle_resolved_before_other_header_work','after_native_frame_boolean_store_before_other_work',
          'after_copy156_before_other_frame_metadata','native_command_frame_and_buffer_links_before_unexecuted_middle',
          'after_native_command_leaf_return_before_other_helpers']
        assert [e['SP_after'] for e in es]==[hex(a.PRODUCER_SP-0x80),hex(a.PRODUCER_SP-0x80),
                                            hex(a.COMMAND_SP),hex(a.COMMAND_SP-0x50),hex(a.COMMAND_SP-0x50)]
        assert hex(a.IMAGE+0x1351b8) in es[0]['CODE_observed_PCs']
        assert hex(a.IMAGE+0x131af8) in es[1]['CODE_observed_PCs']
        assert all(hex(a.IMAGE+x) in es[4]['CODE_observed_PCs'] for x in (0x15d7c0,0x15d7c8,0x15d7cc,0x15e360))
    for seed in (0xa5,0xc3):
        for legacy in (0,0x220):
            pair=[next(c for c in j['cases'] if c['seed']==seed and c['source_kind']=='captured'
                       and c['raw_owner36_fixture']==raw and c['legacy_command_u16_68_fixture']==legacy) for raw in (0,1,2,255)]
            aa,bb=(bytes.fromhex(c['packet_after_hex']) for c in pair[:2])
            assert {i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y}=={0x84} and aa[0x84]^bb[0x84]==2
            aa,bb=(bytes.fromhex(c['command_after_hex']) for c in pair[:2])
            delta={i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y}
            if legacy==0:assert delta=={0x3385} and aa[0x3385]^bb[0x3385]==0x20
            else:assert not delta
            for c in pair[2:]:
                assert c['packet_after_hex']==pair[1]['packet_after_hex']
                assert c['command_after_hex']==pair[1]['command_after_hex']
    assert len(events)==100
    for e in events:
        assert e['original_image_GOP_metadata_handles_unchanged'] and e['stack_outside_this_entry_scratch_window_unchanged']
        assert not e['memory_read_write_hooks_installed'] and not e['MMIO_code_replacement_or_fake_return']
        assert not e['native_interrupts'] and e['PC_observation_may_include_annulled_delay_slots']
    for pair in j['packet_old_seed_dependencies']:
        assert pair['remaining_packet_seed_dependency_offsets']==['0x56','0x57','0x76','0x77']
        assert not pair['entire_request_or_other_bits_proven_initialized']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    review={'status':'PASS_DECLARED_NATIVE_FRAME_FLAG_TO_PARAMETER_AND_COMMAND_BIT',
      'created_utc':now,'prior_sealed_files_verified':13,'formal_cases':20,'formal_bounded_phases':100,
      'native_prefixes_resolve_declared_frame_and_packet_handles':True,
      'native_bool_normalization_not_raw_lowbit_copy':True,
      'native_override_and_complete_leaf_return_with_paired_command_bit13':True,
      'analysis_packet_old_seed_difference_bytes_after_override':4,
      'source_GOP_unchanged_gate0_and_frame_publication0':True,
      'post_gate_copy_and_partial_command_entries_do_not_prove_real_dispatch':True,
      'whole_producer_source_owner_init_command_middle_MAIN_hardware_or_recovery':False,
      'review_scope':'Same-agent source, full-protected-region, native pointer/frame and paired-control output review; not independent engine or camera acceptance.',
      'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_declared_frame_state_to_parameter_override_and_command_bit'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
      'basis':['stage86封存13件/canonical复核，仅Mac；官方、授权与16项保持。',
               '原wrapper/producer前缀在声明句柄图中解析Frame/S0与Owner/S1，原36真假转换进Frame4da；原命令前缀保存同一Frame并解析参数缓冲。20例100阶段，无伪返回/MMIO。',
               '命令原覆盖bit1后真正调用15e360并回原调用点，0与非零/legacy220分支有成对命令bit13差异。分析副本旧差异5降4，原GOP仍不变。',
               '源GOPgate/帧发布仍0；复制在未执行gate之后独立进入，命令中段未执行，不能推真实分派。源Owner36初始化/完整生产者、MAIN/硬件及全部同机恢复仍缺。'],
      'completion_not_claimed':True}
    result=rel+'/run-20261026/frame-command-results.json'
    g['latest_stage_evidence']['stage87_frame_state_command_bit']={
      'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result,
      'scope':'Declared object graph/native field normalization and command leaf. Post-gate copy and command middle gaps; source gate/publication remain0, no real dispatch/hardware.',
      'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage87_scope']='声明句柄图原36→Frame4da→参数bit1→命令bit13，20例100阶段，副本旧差异降4而源GOP不变。gate/发布仍0，门后复制及命令中段独立入口不证明真实分派；源初始化/MAIN/硬件/恢复缺，16项保持。'
    g['next_safe_offline_actions'].append('stage87继续控制对象36初始化与真实Frame/MAIN绑定、GOP gate及帧发布/正常命令分派；不可把门后独立复制当更新成功。分类配置76/77/96/97（参数副本56/57/76/77）的实际读取/掩码，不凭对齐叫padding；源GOP未被命令覆盖改写，旧值域与副本分别保留。全部实际主录/恢复门禁保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-26 FX3 帧状态与命令位消费](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：声明句柄图原36→Frame4da→参数覆盖→原命令叶函数；20例100阶段，分析副本旧差异5降4。源gate/发布仍0，非正常分派/硬件，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{
      'schema':'fx3-stage87-native-frame-command-bit/1','created_utc':now,
      'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
      'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
      'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
      'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
      'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
                      'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
