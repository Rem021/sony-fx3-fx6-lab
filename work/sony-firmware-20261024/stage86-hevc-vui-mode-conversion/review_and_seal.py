#!/usr/bin/env python3
"""Seal VUI/caller/frame/core evidence without promoting it to real encoding."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import vui_mode as v
im,BASE,ROOT,a=v.im,v.BASE,v.ROOT,v.a


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage85-hevc-slice-layout-production/final-receipt.json'
    assert im.sha(prior.read_bytes())==v.PRIOR_SHA
    for r in json.loads(prior.read_text())['files']:
        raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes'] and im.sha(raw)==r['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    formal=STAGE/'run-20261026';j=json.loads((formal/'vui-mode-results.json').read_text())
    assert j['status']=='PASS_NATIVE_VUI_FLAG_TO_MODE_FRAME_RETURN_AND_GOP_COPY'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'vui_mode.py').read_bytes())
    assert (formal/'executed-source.py').read_bytes()==(STAGE/'vui_mode.py').read_bytes()
    assert j['source_receipt']['prior_runner_sha256']==im.sha((v.p.STAGE/'slice_layout.py').read_bytes())
    blob=a.prev.p.a.v.VCD_PATH.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    assert im.sha(a.prev.SOURCE.read_bytes())==j['source_receipt']['stage50_result_sha256']==a.prev.SOURCE_SHA
    sources=json.loads(a.prev.SOURCE.read_text())['cases'][:3]
    assert len(j['cases'])==14 and j['bounded_phases']==154
    # Resolve the native tables from their LUI plus signed ADDIU immediates.
    def table_offset(lui,addiu):
        high=struct.unpack_from('<I',blob,lui)[0]&65535
        low=struct.unpack_from('<h',blob,addiu)[0]
        return (high<<16)+low-v.IMAGE
    assert table_offset(0x18d6b8,0x18d6c0)==0x239234
    assert table_offset(0x18d834,0x18d83c)==0x239288
    for flag,off in ((0,0x239234),(1,0x239288)):
        targets=struct.unpack_from('<21I',blob,off)
        assert j['dispatch_table_evidence']['flag'+str(flag)+'_targets']==[hex(x) for x in targets]
        assert targets[0]==v.IMAGE+(0x18d7c4 if flag==0 else 0x18d89c)
        assert targets[19]==v.IMAGE+(0x18d7e8 if flag==0 else 0x18d8c0)
    events=[]
    for c in j['cases']:
        src=next(s for s in sources if s['label']==c['source_label'])
        original=bytes.fromhex(src['codec_hex']);codec=bytes.fromhex(c['codec_input_hex'])
        assert c['common_input_hex']==src['common_hex']
        kind=c['kind'];allowed=set(range(0x2c,0x30)) if kind=='target20M' else set(range(0x88,0x8c)) if kind=='VUI_source_bit8_clear' else {0x67} if kind=='source_enum0' else set()
        assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(codec,original)))
        assert c['declared_request']['5']==0 and c['declared_request']['6']==int(kind=='request6_1')
        es=c['events'];events.extend(es);assert len(es)==11
        assert [e['stop'] for e in es]==[
          'before_app_stack_or_startup','returned','returned','before_unresolved_output_address_MFLO',
          'before_timing_stack_and_multiply','before_unresolved_slice_output_MFLO',
          'after_native_type2_slice_return_before_parent_epilogue','returned',
          'before_mode_MMIO_address_prefix','native_mode_return_to_original_caller','returned']
        before_mode=bytes.fromhex(c['config_before_mode_hex']);after=bytes.fromhex(c['config_after_mode_hex'])
        parsed=bytes.fromhex(c['VUI_parameters_after_hex'])
        assert bytes.fromhex(c['VUI_parameters_before_hex'])==bytes([c['seed']])*292
        assert es[6]['config_after_hex']==es[7]['config_after_hex']==es[8]['config_after_hex']==before_mode.hex()
        assert es[7]['VUI_parameters_after_hex']==es[8]['VUI_parameters_after_hex']==es[9]['VUI_parameters_after_hex']==es[10]['VUI_parameters_after_hex']==parsed.hex()
        flag=(a.get32(codec,0x88)>>8)&1
        assert c['source_codec_VUI_bit8']==c['native_VUI_flag_bit23']==flag==((a.get32(parsed,4)>>23)&1)
        assert es[8]['SP_before']==hex(a.SP) and es[8]['SP_after']==hex(a.SP-0x20)
        assert es[9]['SP_before']==hex(a.SP-0x20) and es[9]['SP_after']==hex(a.SP)
        assert not es[8]['resume_native_frame_without_SP_RA_reset'] and es[9]['resume_native_frame_without_SP_RA_reset']
        saved=bytes.fromhex(c['mode_entry_original_saved_frame_hex']);assert len(saved)==32
        assert struct.unpack_from('<I',saved,0x1c)[0]==v.IMAGE+0x18bcac
        assert c['original_prologue_frame_kept_through_native_epilogue_return'] and c['native_callee_saved_registers_preserved']
        enum=19 if codec[0x67]==19 else 0;assert codec[0x67] in (0,19)
        expected=bytearray(before_mode)
        struct.pack_into('<I',expected,0x90,(a.get32(expected,0x90)&~0x3fc)|(enum<<2))
        if codec[0x67]==19:expected[0x1c]=1
        aux=(3 if flag else 1) if codec[0x67]==19 else (2 if flag else 0)
        if kind=='request6_1':aux=0
        expected[0x23]=aux
        assert after==bytes(expected) and c['output_packed_mode_enum']==enum and c['output_aux_byte23']==aux
        assert after.hex()==es[9]['config_after_hex']==es[10]['config_after_hex']
        assert a.get32(after,0x84)==a.get32(codec,0x2c)
        assert after[0xd0:]==bytes(16)
        want=bytearray([0xb6])*4096;want[0x78:0x114]=after[0x34:0xd0]
        want[0x174:0x184]=after[0xd0:0xe0]
        want[0x118]=after[0x14]&1;want[0x119]=(after[0x14]>>1)&1
        want[0x158]=after[0x22];want[0x15a:0x15c]=after[0xb0:0xb2]
        assert c['GOP_after_hex']==want.hex() and not c['GOP_update_gate_bit0']
        assert ((a.get32(want,0xd4)>>2)&255)==enum and a.get32(want,0xc8)==a.get32(codec,0x2c)
        assert c['source_builder_request_and_slot_are_fixtures_not_camera_capture']
        assert not c['full_original_address_translation_MADD_timing_MAIN_hardware_or_recovery']
    for seed in (0xa5,0xc3):
        baseline=next(c for c in j['cases'] if c['seed']==seed and c['kind']=='captured' and c['source_label']==sources[0]['label'])
        b=bytes.fromhex(baseline['config_after_mode_hex']);bp=bytes.fromhex(baseline['VUI_parameters_after_hex'])
        for kind,allowed in (('target20M',set(range(0x84,0x88))),('VUI_source_bit8_clear',{0x23}),
                              ('source_enum0',{0x1c,0x23,0x90}),('request6_1',{0x22,0x23})):
            c=next(c for c in j['cases'] if c['seed']==seed and c['kind']==kind)
            d=bytes.fromhex(c['config_after_mode_hex']);dp=bytes.fromhex(c['VUI_parameters_after_hex'])
            delta={i for i,(x,y) in enumerate(zip(b,d)) if x!=y};assert delta and delta<=allowed
            if kind=='VUI_source_bit8_clear':
                assert {i for i,(x,y) in enumerate(zip(bp,dp)) if x!=y}=={6}
                assert bp[6]^dp[6]==0x80
            else:assert bp==dp
    assert len(events)==154
    for e in events:
        assert e['whole_original_image_and_input_unchanged'] and e['all_slot_bytes_outside_explicit_config_or_VUI_windows_unchanged']
        assert e['stack_outside_declared_scratch_window_unchanged'] and not e['memory_read_write_hooks_installed']
        assert not e['code_MMIO_or_return_adapter'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots']
    for pair in j['old_seed_dependency_pairs']:
        deps=pair['remaining_GOP_block_old_seed_dependency'];assert len(deps)==5
        assert {x['offset'] for x in deps}=={'0x76','0x77','0x96','0x97','0xa4'}
        assert not pair['all_other_bits_initialized_or_hardware_validity_proven']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    md=v.p.a.cs.Cs(v.p.a.cs.CS_ARCH_MIPS,v.p.a.cs.CS_MODE_MIPS32|v.p.a.cs.CS_MODE_LITTLE_ENDIAN)
    contexts=[]
    for lo,hi in ((0x15d7b8,0x15d7d4),(0x131ac0,0x131b00)):
        for off in range(lo,hi,4):
            ins=list(md.disasm(blob[off:off+4],v.IMAGE+off))
            contexts.append({'file_offset':hex(off),'bytes':blob[off:off+4].hex(),
                             'text':' ; '.join(i.mnemonic+' '+i.op_str for i in ins) or 'UNDECODED'})
    direct=[off for off in range(0,0x200000,4) if (struct.unpack_from('<I',blob,off)[0]&0xfc00ffff)==0xa00004da]
    assert direct==[0x131af8]
    im.write_json(STAGE/'next-consumer-static.json',{
      'VCD_sha256':im.sha(blob),'instruction_contexts':contexts,
      'direct_SB_imm4da_hits_first2MiB':[hex(x) for x in direct],
      'candidate_flow':'other object byte36 -> boolean -> frame4da -> parameter source70 bit1 (configa4 bit1 under known copy offsets)',
      'producer_and_consumer_object_binding_full_control_flow_or_execution_proven':False,
      'scope':'Static candidate only; immediate SB scan is not exhaustive for adjusted bases, widths, aliases or code outside first2MiB.'})
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    review={'status':'PASS_NATIVE_VUI_FLAG_REAL_CALLER_AND_PRESERVED_MODE_FRAME',
      'created_utc':now,'prior_sealed_files_verified':14,'formal_cases':14,'formal_bounded_phases':154,
      'complete_VUI_leaf_and_original_caller_prologue_produce_mode_flag':True,
      'native_mode_frame_kept_across_explicit_address_gap_and_returns_to_original_caller':True,
      'mode90_91_old_seed_dependencies_removed_remaining_GOP_bytes':5,
      'input_enum0_reference_corrected_from_original_signed_address_ROM_tables':True,
      'frame4da_to_remaining_bit1_is_static_candidate_not_execution':True,
      'GOP_gate_still_clear_full_address_timing_MAIN_hardware_or_recovery':False,
      'review_scope':'Same-agent whole-region, original-frame, signed-ROM-table and paired-input/output review; no independent emulator or camera acceptance.',
      'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_VUI_to_mode_caller_frame_and_remaining_consumer_trace'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
      'basis':['stage85封存14件/canonical复核，仅Mac，原固件/授权及16项保持。',
               '完整原VUI叶函数生成bit23，原调用者load/JAL/前缀保存S1与真实返回帧；跨未执行地址/MMIO/MADD缺口只绑定槽/codec指针，保留SP/RA/保存槽，原尾声返回原调用点。14例154阶段。',
               '原ROM两表有符号地址239234/239288，枚举0走0、19走19；修正当前独立预期并留失败源，原输出未变。90/91旧值依赖消除，GOP块剩5。',
               '静态命令消费frame4da覆盖source70bit1及131af8候选写者留证，未执行对象绑定；GOPgate仍0，真实request/全地址/时序/MAIN/硬件及全部同机恢复仍缺。'],
      'completion_not_claimed':True}
    result=rel+'/run-20261026/vui-mode-results.json'
    g['latest_stage_evidence']['stage86_hevc_vui_mode']={
      'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result,
      'scope':'Original VUI/caller/mode frame with explicit address gap; declaration-only slot/request, no full initialization or hardware. Frame4da candidate static only.',
      'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage86_scope']='原VUI参数bit23经原caller/JAL/prologue保存，原帧跨地址缺口后自然返回；14例154阶段，90/91旧依赖消除，GOP块剩5，gate仍0。frame4da覆盖候选仅静态；真实地址/request/时序/MAIN/硬件/恢复未证，16项不放宽。'
    g['next_safe_offline_actions'].append('stage86优先核对131af8候选写者与frame4da对象绑定及15d7c0/7c8原覆盖：source70bit1对应configa4bit1，不能直接清旧位。分类76/77和96/97，追GOP帧gate与完整命令消费者。CODE观察不是副作用次数；真实地址/Start/时序/MAIN/硬件和全部同机恢复要求保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-26 FX3 VUI标志与模式转换原帧](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：原VUI→caller/JAL→保留原帧转换，14例154阶段；GOP块旧值依赖7降5、gate仍0。frame4da覆盖仅静态，非硬件或恢复，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{
      'schema':'fx3-stage86-vui-mode-original-frame/1','created_utc':now,
      'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
      'previous_manifest_sha256':v.PRIOR_SHA,'operations':review,
      'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
      'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
      'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
                      'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
