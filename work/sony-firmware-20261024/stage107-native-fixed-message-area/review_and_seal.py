#!/usr/bin/env python3
"""Seal fixed-area source/metadata observations, not runtime or recovery proof."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import fixed_area as t
BASE,ROOT=t.BASE,t.ROOT


def sha(d):return hashlib.sha256(d).hexdigest()


def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert sha(t.PRIOR.read_bytes())==t.PRIOR_SHA
    pm=json.loads(t.PRIOR.read_text())
    for f in pm['files']:
        d=(ROOT/f['path']).read_bytes();assert len(d)==f['bytes'] and sha(d)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-copy-argument-checkpoint-20261027';j=json.loads((run/'fixed-area-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'fixed_area.py').read_bytes()
    assert len(j['cases'])==6 and j['bounded_phases']==92
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    messages=[]
    for c in j['cases']:
        ev=[]
        if c['initializer']:ev+=c['initializer']['events']
        ev+=sum([a['events'] for a in c['area_getters']],[])
        for m in c['messages']:
            messages.append(m);ev+=m['events']
            assert m['header30_hex']==m['copied_header30_hex'] and m['pending_Codec_frame_preserved']
            assert m['native_ViewId_field1a']==m['declared_view']
            assert not m['actual_payload_copy_allocation_transport_or_valid_runtime_request_proven']
            assert m['native_payload_length']==m['count']*0x98
            assert m['native_message_ID']==(0x210 if m['count']==1 else 0x1610)
        for e in ev:
            assert e['whole_stack_outside_800_byte_declared_range_unchanged']
            assert e['whole_scratch_outside_declared_outputs_unchanged']
            assert e['whole_relocated_ELF_outside_original_fixed_records_unchanged']
            assert e['fixed_records_unchanged_or_original_initializer_only']
            assert not e['Mmap_OSAL_IO_logs_or_success_return_adapters_executed']
        if c['mode']=='normal_declared_mapping':
            assert [a['extent_word'] for a in c['area_getters']]==[0x8000,0x400,0x200,0x400,0x400,0]
            assert all(m['native_fixed_extent_local_not_header']==0x200 for m in c['messages'])
            assert [m['payload_fits_recorded_extent'] for m in c['messages']]==[True,True,True,False]
            assert len({m['native_virtual_pointer'] for m in c['messages']})==1
        elif c['mode']=='no_initializer':
            assert all(m['native_virtual_pointer']==m['native_physical_pointer']=='0x0' and m['native_fixed_extent_local_not_header']==0 for m in c['messages'])
        else:
            assert c['initializer']['declared_span']==0x100
            assert all(m['payload_fits_recorded_extent'] and not m['recorded_extent_inside_declared_mapping'] for m in c['messages'])
    assert len(messages)==12
    assert all(m['native_physical_pointer']==hex(t.PBASE) and m['native_virtual_pointer']==hex(t.VBASE)
        for c in j['cases'] if c['initializer'] for m in c['messages'])
    for dirname in ('run-initial-20261027','run-record-store-policy-20261027','run-native-pointer-domains-20261027'):
        assert not json.loads((STAGE/dirname/'attempt-failure.json').read_text())['passing_result']
    assert sha(t.MPR.path.read_bytes())==j['original_mpr_sha256']==t.prev.MPR_SHA
    assert sha((ROOT/j['source_profile']).read_bytes())==j['source_profile_sha256']
    mpr=t.MPR
    assert mpr.symbols['_ZN3mpr6memory14s_mprFixedAreaE']=={'va':t.RECORD,'size':0xa0}
    assert mpr.read(0x2e09f8,5).hex()=='070d001319'
    def listing(a,z):return {'library':mpr.path.name,'VA_range':[hex(a),hex(z)],
        'original_bytes_sha256':sha(mpr.read(a,z-a)),'original_disassembly':mpr.disasm(a,z)}
    bindings=[]
    for a in (0x81090,0x7e740,0x7dde0,0x7f570,0x7bae0,0x7e350,0x7b9d0):
        name=mpr.plt[a];s=mpr.symbols.get(name)
        bindings.append({'PLT':hex(a),'symbol':name,'local_definition':hex(s['va']) if s else None})
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    audit={'created_utc':now,'original_mpr_sha256':j['original_mpr_sha256'],
        'bindings':bindings,'backup_source':{'callsite':'0xb703c','base_key':'0xfa0028','span_key':'0xfa005d',
            'reads_not_executed_and_actual_values_not_known':True},
        'fixed_area_source':{'record_symbol_VA':hex(t.RECORD),'record_bytes':160,'initializer':'0x2c0be4',
            'post_Mmap_independent_entry':'0x2c0c04','getter':'0x2c0a44','original_jump_bytes':'070d001319',
            'type_to_record_offset_and_extent':{'0':[0,0x200,0x8000],'1':[2,0x8200,0x400],
                '2':[1,0,0x200],'3':[3,0x8600,0x400],'4':[4,0x8a00,0x400]}},
        'pointer_domain_refinement':{'earlier_stage':'stage23-encoder-boundary',
            'old_labels':'Earlier independent post-getter fixture called PayloadMpr+8 virtual and+28 physical.',
            'new_original_source':'init records Mmap result first, input base second; getter reverses them. CreateMessage stores first getter output at+8 and second at+28. Original payload memcpy loads+28.',
            'current_labels':{'PayloadMpr+08':'physical/device-domain input base','PayloadMpr+28':'mapped virtual base'},
            'actual_FX3_driver_mapping_and_live_addresses_not_verified':True,
            'old_sealed_files_preserved':True,'older_fixture_not_valid_deployment_packet':True},
        'field1a':{'source':'Ninth native argument ViewId from caller stack, not getter extent.',
            'getter_extent_temp':'CreateMessage FP+5c','not_used_for_capacity_admission_in_this_constructor':True},
        'new_execution_scope':'Native init prologue stops at Mmap. Independent declared mapped base feeds original descriptor body. Full getter/CreateMessage returns natively. Native payload-copy arguments checked but memcpy unexecuted. Header copy uses declared capture pointer, not OSAL allocation.',
        'capacity_scope':'Type2 extent512. Native metadata lengths152/304 fit,608 exceeds; no large copy run. Short declaredspan256 and uninitialized-zero controls are not actual startup states or Sony bug proof; caller constraints/real mapping/pages/locks unverified.',
        'ownership_scope':'Repeated headers carry same fixed-area pointers. Header copy is not private payload ownership; actual outer serialization or lifetime not proven, no camera race alleged.',
        'original_listings':[listing(a,z) for a,z in ((0xb7018,0xb7044),(0x2c0af8,0x2c0ce0),
            (0x2c0a44,0x2c0af8),(0x2829a4,0x282a10),(0x282cfc,0x282d00),
            (0x282d38,0x282d7c),(0x27deac,0x27df44),(0x27e0cc,0x27e168))],
        'public_sources':'public-source-notes.json','API_metadata_limit':'public-api-crosscheck.json preserves403; primary browser pages still read, exact current commit not claimed.',
        'failed_attempts':'Old observer rejected newly admitted original BSS stores; then wrong type ordering/domain expectation; then entry checkpoint stopped before first copy-argument instruction. All failures retained; only harness scope/expectations changed.',
        'actual_runtime_MAIN16M_protocol_hardware_backup_restore_or_rescue_proven':False}
    put(STAGE/'source-and-scope-audit.json',audit)
    review={'status':j['status'],'created_utc':now,'prior_files_verified':len(pm['files']),
        'guest_environments':6,'native_message_cases':12,'bounded_phases':92,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT));result_rel=str((run/'fixed-area-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_fixed_message_area_domains_capacity_and_recovery_scope_refresh'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage106的19件封存/canonical及目标卷核对；仅Mac。',
            '原Backup基址/长度来源、Mmap与固定描述符生成接到完整GetFixedArea/CreateMessage；映射后基址仍是独立声明输入，没有伪造Mmap/OSAL返回。',
            '纠正阶段23消息域标签：+8物理/设备域，+28映射虚拟域，原payload memcpy实际参数取+28；+1a来自第九参数ViewId，不是容量。',
            '类型2实际extent200，元数据长度98/130可落入，260控制超过；构造器不分配/不做该容量准入。零记录/短声明映射及固定指针复用均为范围对照，不是实机缺陷或竞态。92有界阶段。',
            '重新核对REA FX3讨论、A7CII发布/失败与应用模式回退报告、A7IVboot0例外。未建立FX3独立救援；REST限流回执保留，浏览主来源可读。',
            '完整消息/物理映射/实例同步、FH资源16M、目标成片与同机备份恢复仍缺；全部16项状态、权限及stage75不可部署原型保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage107_fixed_message_area_domains']={'readme':rel+'/README.md','result':result_rel,
        'source_audit':rel+'/source-and-scope-audit.json','public_sources':rel+'/public-source-notes.json',
        'review':rel+'/completed-evidence-review.json','scope':'92 native bounded phases correct fixed-area type2 extent512 and physical+8/virtual+28 source; mapping/OSAL/payload copy/runtime/hardware/recovery remain unproved.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].extend([result_rel,rel+'/source-and-scope-audit.json'])
            req['stage107_scope']='原固定区/Get/CreateMessage/复制参数揭示+8物理域、+28虚拟域与类型2长度200。完整映射/分配/拷贝/消息/硬件接受仍未证，不能提交本轮声明参数。状态保持。'
        if req['id'] in ('G15','G16'):
            req['evidence'].append(rel+'/public-source-notes.json')
            req['stage107_scope']='重读公开A7CII失败及依赖应用录像模式的恢复报告、A7IVBootROM方向及boot0例外；均非FX3主录改动后的同机受限回读或独立救援验收，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'earlier_stage_refined':'stage23-encoder-boundary',
        'finding':'Native fixed-area initialization/getter and full CreateMessage correct earlier post-getter domain labels: PayloadMpr+8 physical/device base, +28 mapped virtual; original payload memcpy uses+28. Type2 extent512 and ViewId at+1a are distinct. Declared mapping and header-only construction do not prove allocation, payload ownership, transport or runtime admission.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('stage107后按更正的PayloadMpr+8物理/设备域、+28虚拟域追原接收/地址交接；核对固定区初始化/真实映射长度与所有权/外层锁/回复寿命，不能把+1a ViewId当容量或复用旧域标签。保持stage105上游MAIN来源和FH/16M资源匹配缺口；公开A7CII应用模式回退及A7IVBootROM不是FX3独立救援验收。仅Mac离线，全部实录/同机恢复门槛保持。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 固定消息区与指针域更正](<'+rel+'/README.md>)：原类型2长度200、消息+8物理/+28虚拟、ViewId来源及容量前提92阶段；公开恢复证据复查仍未覆盖FX3，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            d=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(d),'sha256':sha(d)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage107-fixed-message-area/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':sha((STAGE/'final-receipt.json').read_bytes()),
        'bounded_phases':92,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
