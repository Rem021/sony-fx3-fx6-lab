#!/usr/bin/env python3
"""Review original body, calibrated observation and old-byte dependencies."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import native_body as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage83-hevc-initial-config-field-provenance/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for r in json.loads(prior.read_text())['files']:
        raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes'] and im.sha(raw)==r['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-20261026';j=json.loads((run/'native-body-results.json').read_text())
    assert j['status']=='PASS_NATIVE_HEVC_BODY_PURE_CALLEES_AND_ROM_TABLE_WITH_EXPLICIT_ADDRESS_GAP'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'native_body.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'native_body.py').read_bytes()
    blob=a.prev.p.a.v.VCD_PATH.read_bytes();assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    assert blob[0x930c:0x9314].hex()==j['GP_evidence']['two_instructions_hex']=='25801c3c58eb9c27'
    assert blob[0x248910:0x248915].hex()=='0001040203'
    assert im.sha(a.prev.SOURCE.read_bytes())==j['source_receipt']['stage50_result_sha256']==a.prev.SOURCE_SHA
    sources=json.loads(a.prev.SOURCE.read_text())['cases'][:3]
    assert len(j['cases'])==16 and j['bounded_phases']==94
    events=[]
    for c in j['cases']:
        src=next(s for s in sources if s['label']==c['source_label'])
        codec=bytes.fromhex(c['codec_input_hex']);original=bytes.fromhex(src['codec_hex'])
        assert im.sha(original)==c['source_codec_sha256']
        assert c['common_input_hex']==src['common_hex']
        allowed=set(range(0x2c,0x30)) if c['kind']=='target20M' else {0xe} if c['kind']=='table_index2' else set()
        assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(codec,original)))
        assert c['not_an_actual_Start_header_or_camera_memory_capture']
        assert c['unknown_old_bytes_and_preserved_bits_not_claimed_initialized']
        assert not c['full_converter_actual_address_translation_MAIN_or_hardware']
        es=c['events'];events.extend(es)
        assert [e['stop'] for e in es[:4]]==['before_app_stack_or_startup','returned','returned','before_unresolved_output_address_MFLO']
        # Independently check every original plain-constructor store, including
        # the gaps it intentionally leaves. No zero-filled type assumed.
        expected=bytearray([c['seed']])*0xe0
        for off,size,val in ((0,1,255),(0x21,1,1),(1,1,0),(2,2,0),(4,4,0),(8,4,0),
            (0x13,1,1),(0x15,1,1),(0x18,4,0),(0x1e,1,1),(0x28,4,0),(0x32,2,0),
            (0xd0,4,0),(0xd4,4,0),(0xd8,4,0),(0xdc,4,0)):
            expected[off:off+size]=val.to_bytes(size,'little')
        for off in (*range(0xc,0x13),0x14,0x1c,0x1d,0x1f,0x20,*range(0x22,0x26),*range(0x2c,0x31)):
            expected[off]=0
        assert es[1]['config_after_hex']==expected.hex()
        common=bytes.fromhex(c['common_input_hex'])
        for off,val in ((0,0),(0x15,1),(0xf,0),(0x14,0),(0x1c,0),
                        (0x1e,int(bool(common[0]))),(0x24,int(codec[3]==1)),(0x25,int(bool(codec[0x66])))):
            expected[off]=val
        assert es[2]['config_after_hex']==expected.hex()==es[3]['config_after_hex']==c['header_after_hex']
        body=bytes.fromhex(c['config_after_hex']);gop=bytes.fromhex(c['GOP_after_hex'])
        assert len(body)==0xe0 and body[0xd0:]==bytes(16)
        assert body.hex()==es[4]['config_after_hex']
        good=c['kind']!='request5_1_MMIO_boundary'
        assert c['continuous_body_reached_timing_boundary']==good
        want=bytearray([0xb6])*4096
        if good:
            assert len(es)==6 and es[4]['stop']=='before_timing_stack_and_multiply' and es[5]['stop']=='before_GOP_base_helper'
            assert struct.unpack_from('<HH',body,0x38)==(119,67)
            assert body[0x45]==0 and body[0x47]==4 and body[0x11]==2
            assert a.get32(body,0x84)==a.get32(codec,0x2c)
            assert c['decoded_config_target']==(20000000 if c['kind']=='target20M' else 16000000)
            assert body[0x75]==(4 if c['kind']=='table_index2' else 0)
            want[0x78:0x114]=body[0x34:0xd0]
            assert a.get32(want,0xc8)==a.get32(codec,0x2c)
        else:
            assert len(es)==5 and es[4]['stop']=='before_request1_MMIO_read'
            assert c['decoded_config_target'] is None
        assert gop==bytes(want)
    for seed in (0xa5,0xc3):
        baseline=next(c for c in j['cases'] if c['seed']==seed and c['kind']=='captured' and c['source_label']==sources[0]['label'])
        b=bytes.fromhex(baseline['config_after_hex'])
        for kind,allowed in (('target20M',set(range(0x84,0x88))),('table_index2',{0x75}),
                              ('request6_1',{0x22}),('request5_2',{0x94,0x9c})):
            c=next(c for c in j['cases'] if c['seed']==seed and c['kind']==kind)
            delta={i for i,(x,y) in enumerate(zip(b,bytes.fromhex(c['config_after_hex']))) if x!=y}
            assert delta and delta<=allowed,(kind,delta)
    assert len(events)==94
    for e in events:
        assert e['whole_original_image_and_input_unchanged'] and e['all_other_channel_and_manager_bytes_unchanged']
        assert e['stack_outside_declared_scratch_window_unchanged'] and not e['memory_read_write_hooks_installed']
        assert not e['code_MMIO_or_return_adapter'] and not e['native_interrupts']
        assert e['PCs_are_CODE_observations_may_include_annulled_delay_slots']
    pair=j['old_seed_dependency_pairs'][0];deps=pair['old_seed_dependency_xor_by_offset']
    assert len(deps)==44 and sum(0x34<=int(x['offset'],16)<0xd0 for x in deps)==39
    probe=STAGE/'annulled-delay-slot-three-sites-20261026';p=json.loads((probe/'probe-results.json').read_text())
    assert p['status']=='PASS_CODE_CALLBACK_CAN_OBSERVE_ANNULLED_BEQL_DELAY_BREAK'
    assert p['source_image_sha256']==im.sha(blob)
    assert (probe/'executed-source.py').read_bytes()==(STAGE/'probe_annulled_slots.py').read_bytes()
    assert im.sha((STAGE/'probe_annulled_slots.py').read_bytes())==p['source_script_sha256']
    assert len(p['cases'])==9
    for c in p['cases']:
        assert c['break_PC'] in c['pcs'] and c['original_image_unchanged']
        assert c['no_instruction_NOP_replacement_PC_write_or_fake_return']
        if c['declared_divisor']:
            assert c['stop']=='returned' and not c['interrupts'] and c['error'] is None
            assert c['result_v0']==10//c['declared_divisor']
        else:assert c['stop']=='native_interrupt' and c['interrupts']==[18]
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    review={'status':'PASS_NATIVE_HEVC_BODY_WITH_EXPLICIT_ADDRESS_GAP_AND_OBSERVER_CALIBRATION',
            'created_utc':now,'prior_sealed_files_verified':8,'cases':16,'bounded_phases':94,
            'separate_three_site_annulled_slot_probe_cases':9,
            'body_helpers_return_natively_GP_from_original_setup_ROM_table':True,
            'GOP_block39_bytes_show_old_seed_dependencies_not_valid_complete_request':True,
            'MFLO_address_gap_request_fixtures_and_full_timing_unresolved':True,
            'complete_runtime_MAIN_hardware_recording_or_recovery':False,
            'review_scope':'Same-agent original-store, PC-observation, full-protected-region, input-delta/output-delta and local positive/zero-trap review; not independent engine or camera acceptance.',
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_HEVC_body_ROM_table_and_branch_likely_observer_calibration'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
      'basis':['stage83的8件封存/canonical复核；仅Mac，官方与授权保持。',
               '原GP两指令与ROM表、参数构造器/common尾段和HEVC前缀；未执行MFLO后明确A0槽地址独立进入主体，原裁剪/格式/查表助手自然调用返回。16例94阶段，2例MMIO前停。',
               '3地址9组原DIVU/BEQL/BREAK正例与零陷阱校准：CODE观察可包含annulled延迟槽，不等于架构执行。3指定地址保留CPU判断，实际中断均拒绝；不NOP、不假返回。',
               'A5/C3见GOP复制块39字节或部分位保留旧值；原后续类型2助手18ed04将config+b0传为输出待追。完整初始化/实际调用MAIN/硬件/时序/恢复与16项验收未放宽。'],
      'completion_not_claimed':True}
    result=rel+'/run-20261026/native-body-results.json'
    g['latest_stage_evidence']['stage84_hevc_native_body']={
      'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result,
      'probe':rel+'/annulled-delay-slot-three-sites-20261026/probe-results.json',
      'scope':'Native pure body and helper returns; independent address gap and fixture request bytes. Old dependencies preserved, no complete request or hardware proof.',
      'authorization_unchanged':True,'goal_complete':False}
    assert isinstance(g['corrections_to_prior_stage'],dict)
    g['corrections_to_prior_stage']['MIPS_CODE_observation_annulled_delay_slots']={
      'recorded_in':rel+'/README.md','evidence':rel+'/annulled-delay-slot-three-sites-20261026/probe-results.json',
      'correction':'CODE callback presence may include annulled BEQL delay slots on current Unicorn2.1.4/MIPS32_24KC; not architecture effect/count proof. Retain existing native output/stack scope separately; no universal engine claim or blanket invalidation.',
      'original_instructions_replaced_or_exception_return_faked':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage84_scope']='原GP/ROM表及HEVC连续主体助手自然返回，16例94阶段，2例MMIO前停；输出GOP块39字节或位依赖旧值。地址gap/request fixture/时序/真实MAIN/硬件未证；3处9例校准CODE观察含取消的延迟槽，不等于指令已执行。全部验收保持。'
    g['next_safe_offline_actions'].append('stage84继续类型2原common后续18ed04及1a2920对config+b0参数生产，核对剩余39旧值依赖及后续profile字段，再进命令层。CODE观察不单作已执行/副作用次数证据；未知MFLO地址转换/实际request/时序/MAIN/硬件与全部同机恢复要求保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-26 FX3 HEVC主体与ROM查表](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：原裁剪/格式助手自然返回，16例94阶段；GOP块仍39字节或位依赖旧值。另9例校准CODE的取消延迟槽观察；非完整初始化/MAIN/硬件，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            raw=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{
      'schema':'fx3-stage84-native-hevc-body/1','created_utc':now,
      'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
      'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
      'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
      'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
      'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
                      'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
