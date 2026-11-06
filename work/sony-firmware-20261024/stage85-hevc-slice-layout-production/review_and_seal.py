#!/usr/bin/env python3
"""Review native slice production, bounded GOP construction and preserved gates."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import slice_layout as p
im,BASE,ROOT=p.im,p.BASE,p.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage84-hevc-native-config-body/final-receipt.json'
    assert im.sha(prior.read_bytes())==p.PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    formal=STAGE/'run-full-gop-20261026';j=json.loads((formal/'slice-layout-results.json').read_text())
    assert j['status']=='PASS_NATIVE_SLICE_LAYOUT_AND_COMPLETE_DECLARED_GOP_CONSTRUCTION'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'slice_layout.py').read_bytes())
    assert (formal/'executed-source.py').read_bytes()==(STAGE/'slice_layout.py').read_bytes()
    assert j['source_receipt']['prior_runner_sha256']==im.sha((p.a.STAGE/'native_body.py').read_bytes())
    blob=p.a.prev.p.a.v.VCD_PATH.read_bytes()
    assert j['source_receipt']['VCD_sha256']==im.sha(blob)==im.PINS[str(p.a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    source_name=blob[0x23a7c4:].split(b'\0',1)[0].decode()
    assert j['original_source_name']==source_name
    assert source_name.endswith('/slice_split_line_calculator/slice_split_line_calculator.cxx')
    assert im.sha(p.a.prev.SOURCE.read_bytes())==j['source_receipt']['stage50_result_sha256']==p.a.prev.SOURCE_SHA
    sources=json.loads(p.a.prev.SOURCE.read_text())['cases'][:3]
    assert len(j['cases'])==10 and j['bounded_phases']==80
    events=[];expected_layout=[16,18,16,18,0,0,0,0,2,0,0,0,0,0,0,0]
    for c in j['cases']:
        src=next(s for s in sources if s['label']==c['source_label'])
        original=bytes.fromhex(src['codec_hex']);codec=bytes.fromhex(c['codec_input_hex'])
        assert c['common_input_hex']==src['common_hex']
        allowed=set(range(0x2c,0x30)) if c['kind']=='target20M' else set()
        assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(original,codec)))
        assert c['declared_request']['5']==0 and c['declared_request']['6']==int(c['kind']=='request6_1')
        es=c['events'];assert len(es)==8;events.extend(es)
        assert [e['stop'] for e in es]==[
          'before_app_stack_or_startup','returned','returned','before_unresolved_output_address_MFLO',
          'before_timing_stack_and_multiply','before_unresolved_slice_output_MFLO',
          'after_native_type2_slice_return_before_parent_epilogue','returned']
        body=bytes.fromhex(c['config_before_slice_hex']);after=bytes.fromhex(c['config_after_slice_hex'])
        assert len(body)==len(after)==0xe0
        assert body[0xb0:0xd0]==bytes([c['seed']])*32
        assert body[:0xb0]==after[:0xb0] and body[0xd0:]==after[0xd0:]==bytes(16)
        assert es[4]['config_after_hex']==body.hex() and es[5]['config_after_hex']==body.hex()
        assert es[6]['config_after_hex']==after.hex()==es[7]['config_after_hex']
        assert list(struct.unpack_from('<16H',after,0xb0))==c['slice_layout_u16']==c['reference_layout_u16']==expected_layout
        descriptor=struct.unpack('<10I',bytes.fromhex(c['native_descriptor_after_return_hex']))
        assert descriptor==(0,67,4,0,0,0,68,0,4,0)
        # Independent inclusive-range reference, including zero-count second
        # descriptor's deterministic leading value. No guest output substituted.
        for group,(first,last,count) in enumerate((descriptor[:3],descriptor[3:6])):
            length=last-first+1;parts=[(length+1)//2]
            if count>=2:
                for _ in range(count.bit_length()-1):
                    parts=[v for n in parts for v in (n//2,n-n//2)]
            want=[2*v for v in parts]+[0]*(8-len(parts))
            assert c['slice_layout_u16'][8*group:8*group+8]==want
        assert c['descriptor_group_counts']==[4,0]
        assert c['group0_u16_sum']==68 and c['group1_u16_sum']==2
        assert c['zero_count_group_template_not_added_to_first_range_coverage']
        assert c['native_callee_saved_registers_preserved']
        assert c['native_full_GOP_constructor_return_and_saved_registers_preserved']
        assert not c['GOP_frame_update_gate_bit0']
        assert c['source_builder_and_request_are_fixtures_not_camera_capture']
        assert not c['actual_runtime_dispatch_address_translation_complete_timing_MAIN_or_encoding']
        want=bytearray([0xb6])*4096;want[0x78:0x114]=after[0x34:0xd0]
        want[0x174:0x184]=bytes(16)
        want[0x118]=after[0x14]&1;want[0x119]=(after[0x14]>>1)&1
        want[0x158]=after[0x22];want[0x15a:0x15c]=after[0xb0:0xb2]
        assert c['GOP_after_hex']==want.hex()
        assert p.a.get32(want,0xc8)==p.a.get32(codec,0x2c)
        assert want[0xf4:0x114]==after[0xb0:0xd0]
        assert p.a.prev.p.a.decode(p.a.get32(want,0xc8))==(20000000 if c['kind']=='target20M' else 16000000)
        assert all(hex(p.IMAGE+x) in es[7]['CODE_observed_PCs'] for x in (0xd866c,0x137420,0x1384e8,0x137588,0xd872c))
    for e in events:
        assert e['whole_original_image_and_input_unchanged'] and e['all_other_channel_and_manager_bytes_unchanged']
        assert e['stack_outside_declared_scratch_window_unchanged'] and not e['memory_read_write_hooks_installed']
        assert not e['code_MMIO_or_return_adapter'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots']
        assert e['SP_after']==hex(p.a.SP)
    for pair in j['old_seed_dependency_pairs']:
        assert pair['native_slice32_equal_across_seeds']
        assert not pair['all_other_bits_initialized_or_hardware_validity_proven']
        deps=pair['remaining_GOP_block_old_seed_dependency'];assert len(deps)==7
        assert {x['offset'] for x in deps}=={'0x76','0x77','0x90','0x91','0x96','0x97','0xa4'}
    initial=STAGE/'run-20261026';oldrun=json.loads((initial/'slice-layout-results.json').read_text())
    assert oldrun['status']=='PASS_NATIVE_TYPE2_SLICE_PRODUCTION_CLEARS_32BYTE_OLD_SEED_DEPENDENCY'
    assert im.sha((initial/'executed-source.py').read_bytes())==oldrun['source_receipt']['script_sha256']
    assert len(oldrun['cases'])==10 and oldrun['bounded_phases']==80
    assert all(c['events'][-1]['stop']=='before_GOP_base_helper' for c in oldrun['cases'])
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    review={'status':'PASS_NATIVE_SLICE32_AND_COMPLETE_ZERO_MODE_GOP_CONSTRUCTION',
      'created_utc':now,'prior_sealed_files_verified':17,'formal_cases':10,'formal_bounded_phases':80,
      'native_slice32_no_A5_C3_old_seed_dependency':True,
      'native_second_zero_count_group_has_leading2_not_extra_row_coverage':True,
      'reference_failure_sources_and_initial_partial_GOP_result_retained':True,
      'complete_GOP_constructor_returns_on_native_zero_mode_words':True,
      'GOP_frame_gate_still_clear_not_hardware_handoff':True,
      'remaining_GOP_block_old_seed_dependency_bytes':7,
      'full_address_translation_actual_Start_timing_MAIN_hardware_or_recovery':False,
      'review_scope':'Same-agent source/whole-region/returned-state and independent integer partition review; no independent emulator or camera acceptance.',
      'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_slice_layout_and_complete_zero_mode_GOP_constructor'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
      'basis':['stage84封存17件/canonical复核；原固件、授权和全部16项保持，仅Mac。',
               '原slice_split_line_calculator路径与类型2分派：原18ed04/1a279c/1a2920/递归分割真正调用返回，产32字节。第二零计数组首字2由含端点区间计算，修正独立预期而非原输出，失败源码保留。',
               '10例80阶段，A5/C3的32字节旧值依赖消除，GOP块剩7字节或部分位。构造器原生零模式块下，完整d866c/base助手/模式谓词自然返回，SP与保存寄存器保持；旧部分结果保留。',
               'GOP帧gate仍0，未手动开gate或拼接成真实提交；未知地址/真实request/完整时序/MAIN/硬件及全部实机与同机恢复仍缺。'],
      'completion_not_claimed':True}
    result=rel+'/run-full-gop-20261026/slice-layout-results.json'
    g['latest_stage_evidence']['stage85_hevc_slice_layout']={
      'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result,
      'scope':'Fresh fixture body and native slice dispatch after explicit address gaps; full GOP constructor only with native zero modes, gate remains0. No actual MAIN/hardware proof.',
      'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage85_scope']='原分行32字节消除A5/C3依赖，第二零计数模板首字2不累加覆盖行。原生零模式下完整GOP构造自然返回，帧gate仍0；10例80阶段，剩7字节或位。地址/真实request/完整时序/MAIN/硬件/恢复未证，16项保持。'
    g['next_safe_offline_actions'].append('stage85继续原profile18d62c对config90/91相关位的来源/转换，分类76/77、96/97、a4剩余旧值，并追GOP帧gate生产者与命令消费者。零模式GOP构造返回不代表gate更新或硬件提交；不得手动开gate拼接实机结果。原地址/真实request/时序/MAIN/硬件和全部同机恢复门禁保留。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-26 FX3 HEVC分行布局与完整GOP构造](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：原32字节布局生成、零模式完整构造自然返回，10例80阶段；GOP块旧值依赖39降7、帧gate仍0，非硬件提交，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{
      'schema':'fx3-stage85-slice-and-zero-mode-GOP/1','created_utc':now,
      'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
      'previous_manifest_sha256':p.PRIOR_SHA,'operations':review,
      'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
      'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
      'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
                      'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
