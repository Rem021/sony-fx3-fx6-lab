#!/usr/bin/env python3
"""Seal correct official AP bindings and prepared, unexecuted Mac cache step."""
from pathlib import Path
import copy,datetime,difflib,hashlib,importlib.util,json,sys,zlib
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import ap_config_audit as t
BASE,ROOT=t.BASE,t.ROOT
PRIOR=BASE/'stage128-DMM-provider-and-config/final-receipt.json'
PRIOR_SHA='328ea683205c2e65792617680cebac051de8d1aa8383cd612a2314b86d495ed1'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    t.shared_volume_check();assert not (STAGE/'final-receipt.json').exists()
    assert digest(PRIOR)==PRIOR_SHA;prior=json.loads(PRIOR.read_text())
    for f in prior['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(PRIOR.parent/'goal-status-after.json').read_bytes()
    out=STAGE/'run-explicit-shared-volume-check-20261027';result=out/'AP-config-results.json';j=json.loads(result.read_text())
    assert j['status']=='PASS_OFFICIAL_AP_CONFIG_BOOT_SOURCE_AND_20_UNIT_BINDINGS_NOT_DEVICE_ACCEPTANCE'
    assert j['source_sha256']==digest(STAGE/'ap_config_audit.py')==digest(out/'executed-source.py')
    firstdir=STAGE/'run-official-AP-binding-20261027';first=json.loads((firstdir/'AP-config-results.json').read_text())
    assert first['status']==j['status'] and first['source_sha256']==digest(firstdir/'executed-source.py')
    assert len(j['config_checks'])==6 and j['config_checks'][0]['result']['offline_fixed_package_configuration_accepted']
    assert all(not c['result']['offline_fixed_package_configuration_accepted'] for c in j['config_checks'][1:])
    for k in ('scripts_camera_Windows_UU_or_host_services_executed','goal_complete','persistent_write_release'):assert not j[k]
    assert j['new_native_execution_cases']==0 and j['actual_fallback_file_exists_or_loaded_hash_unproven']
    inputs=json.loads((STAGE/'input-receipt.json').read_text());assert len(inputs['files'])==6 and inputs['official_size_crc_match']
    for f in inputs['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    assert digest(t.AP)==t.AP_SHA and zlib.crc32(t.AP.read_bytes())==int(inputs['AP_config_official_sum_row'][1],16)==0xf5d46b2d
    cfg=json.loads((STAGE/'AP-DmmCfg-decoded.json').read_text());assert cfg==t.p.decode_cfg(t.AP.read_bytes())
    assert len(cfg['roots'])==1 and len(cfg['rules'])==290 and len(cfg['units'])==603
    units={u['unit_type']:u for u in cfg['units']};assert max(len(u['extent_types']) for u in units.values())==8
    assert all(len(units[u]['extent_types'])==1 for u in t.TARGET)
    assert len(j['mode_unit_bindings'])==4 and sum(len(m['rows']) for m in j['mode_unit_bindings'])==49
    assert len(j['unit_extent_candidate_definitions'])==20
    for c in j['unit_extent_candidate_definitions']:
        assert c['extent_types']==units[c['unit_type']]['extent_types'] and c['candidate_definition_rows']
        assert all(x['raw_words'][2] in c['extent_types'] for x in c['candidate_definition_rows'])
        assert c['actual_active_rule_address_size_and_owner_unproven']
    cp=j['config_checks'][1]['result'];assert cp['unit_count']==348 and cp['target_matches']==0
    test=json.loads((STAGE/'mac-cache-offline-tests.json').read_text());cache=STAGE/'mac_cached_usb_inventory.py'
    assert test['source_sha256']==digest(cache) and test['status']=='PASS_OFFLINE_CACHE_SANITIZATION_AND_PARENT_CHILD_SCOPE'
    assert not test['ioreg_diskutil_camera_or_other_host_query_executed_by_self_test'] and not test['live_device_acceptance']
    # Independent invocation with an execution guard. Only in-memory fixtures run.
    spec=importlib.util.spec_from_file_location('stage129_cache_guarded_review',cache);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    original=m.subprocess.run
    def forbidden(*a,**kw):raise AssertionError('self-test requested a host query')
    m.subprocess.run=forbidden
    try:assert m.self_test()==test
    finally:m.subprocess.run=original
    plan=(STAGE/'DEVICE_TRIAL_PLAN.md').read_text()
    assert all(x in plan for x in ('/setting/DmmCfg.bin','/setting/DmmConfig.bin','独立救援','同机健康备份','临时内存试验','持久部署/刷写','不是相机操作授权'))
    old=json.loads(before)
    for f in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/f['path'])==f['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json';assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for f in json.loads(p117.read_text())['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(result.relative_to(ROOT))
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'input_receipt_sha256':digest(STAGE/'input-receipt.json'),
        'AP_config_sha256':t.AP_SHA,'CP_negative_control_sha256':digest(t.CP),'startup_source_excerpts':j['startup_source_excerpts'],
        'native_layout_source':str((PRIOR.parent/'provider_audit.py').relative_to(ROOT)),
        'native_layout_source_sha256':digest(PRIOR.parent/'provider_audit.py'),
        'host_parser_scope':'Native initializer-supported layout decoded in host with full bounds/sentinels and complete consumption; not full native parser or runtime execution.',
        'official_AP_source_binding_not_same_body_loaded_hash':True,'target_MPR_unit_types':list(t.TARGET),
        'target_matches':20,'target_extent_list_max':1,'whole_official_AP_extent_list_max':8,
        'runtime_rule_addresses_sizes_and_owner_unproven':True,
        'prepared_cache_collector_sha256':digest(cache),'cache_self_test_host_query_forced_failure_guard_passed':True,
        'cache_live_path_only_explicit_query_flag_and_not_executed':True,
        'first_to_formal_source_diff':list(difflib.unified_diff((firstdir/'executed-source.py').read_text().splitlines(),
            (out/'executed-source.py').read_text().splitlines(),fromfile='first',tofile='formal',lineterm='')),
        'first_and_formal_results_preserved':True,'no_added_native_or_physical_camera_test_claimed':True})
    contract=json.loads((PRIOR.parent/'diagnostic-contract.json').read_text());contract['schema']='fx3-offline-status-diagnostic-candidate/11';contract['refined_in_stage']=STAGE.name
    contract['official_AP_DMM_config']={'preferred_path':'/setting/DmmCfg.bin','fallback_path':'/setting/DmmConfig.bin',
        'startup_module_parameter':'DmmConfig','setting_partition':'nflasha2','CP_partition':'nflasha8',
        'official_member':'0800_appli/setting/DmmCfg.bin','bytes':66796,'crc32':'f5d46b2d','sha256':t.AP_SHA,
        'version':t.AP_VERSION,'units':603,'all_file_extent_list_max':8,'target_units':20,'target_units_all_matched':True,
        'target_extent_list_max':1,'MPR_layout_limit8_supported_only_within_this_official_sample':True,
        'actual_loaded_file_identity_fallback_WBI_or_unit_runtime_invariants_proven':False,
        'candidate_rule_rows_not_active_allocation_address_size_or_ownership':True}
    contract['prepared_first_device_step']={'kind':'Mac IORegistry cache metadata only','collector':rel+'/mac_cached_usb_inventory.py',
        'offline_self_test_passed':True,'actual_query_executed':False,'new_Mac_cache_query_authorization_granted':False,
        'opens_camera_interface_or_reads_media':False,'proves_device_firmware_backup_or_rescue':False}
    contract['next_runtime_acceptance_requirements'].append('After corresponding scope approval, collect current system-cache identity; before active camera access complete protocol/exit audit and approval, then attest same-body AP config/backup. Official AP max8 and target one-extent mappings do not authorize RAM or persistent use.')
    put(STAGE/'diagnostic-contract.json',contract)
    review={'status':j['status'],'created_utc':now,'AP_units':603,'target_matches':20,'original_mode_rows':49,
        'local_config_checks':6,'cache_offline_self_test_passed':True,'new_native_cases':0,
        'actual_Mac_cache_camera_Windows_or_service_query':False,'formal_source_matches_executed_copy':True,
        'same_agent_review_not_independent_engine':True,'stage117_frontend_and_stage75_backend_unchanged':True,
        'goal_complete':False,'persistent_write_release':False,'previous_manifest_members_verified':len(prior['files'])}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_correct_official_AP_DMM_boot_source_and_target_unit_bindings_with_concrete_device_trial_plan_and_unexecuted_cache_collector'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段128封存20件/canonical核验；原启动脚本的setting首选/回退及挂载对应，转取官方appli成员而非CP文件。',
            '官方FDAT/所选tar头、appli.sum长度CRC重验；正确AP文件603单位、目标20全匹配且各1extent，全文件最大8，绑定原4模式49行。',
            '6组离线配置身份/畸形对照拒绝CP/改动/截断/追加；规则行仍不充实际选择/地址/大小/所有权，机身加载哈希未验。',
            '按用户何时能试刷的追问，完成具体上机/备份/恢复/临时试验/持久部署门槛清单，并备好Mac缓存采集器；隐私/父子关系自测在禁止宿主查询条件下通过，真实查询尚未授权或执行。',
            '16项状态、现有权限及旧前后端保持，不能给可靠试刷日期或以离线计数代替实机验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage129_AP_config_and_trial_plan']={'readme':rel+'/README.md','result':rr,
        'inputs':rel+'/input-receipt.json','source_audit':rel+'/source-and-scope-audit.json','trial_plan':rel+'/DEVICE_TRIAL_PLAN.md',
        'prepared_cache_collector':rel+'/mac_cached_usb_inventory.py','offline_cache_tests':rel+'/mac-cache-offline-tests.json',
        'contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'Correct official AP config/startup source,20 target units matched,49 mode rows; explicit trial gates and prepared sanitized cache collector. No actual device/cache query, backup, RAM or persistent deployment.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    g['prepared_first_device_trial']={'plan':rel+'/DEVICE_TRIAL_PLAN.md','first_cache_collector':rel+'/mac_cached_usb_inventory.py',
        'offline_self_test':rel+'/mac-cache-offline-tests.json','live_Mac_cache_query_executed':False,
        'new_Mac_cache_query_authorized':False,'active_camera_protocol_backup_RAM_and_flash_ready':False,
        'exact_flash_date_established':False,'scope':'Prepared only; Windows cache authorization remains unchanged.'}
    for req in g['requirements']:
        if req['id'] in ('G01','G02','G07','G08','G11','G15','G16'):
            req['evidence'].extend([rel+'/DEVICE_TRIAL_PLAN.md',rel+'/diagnostic-contract.json'])
            if req['id'] in ('G02','G08','G11'):req['evidence'].extend([rr,rel+'/source-and-scope-audit.json'])
            req['stage129_scope']='正确官方AP源/目标20单位匹配与具体上机前置方案；Mac缓存工具仅离线自测，未作实际身份/备份/恢复/编码验收，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':PRIOR.parent.name,
        'finding':'Official boot scripts select setting/AP config (nflasha2), not CP config (nflasha8). Official AP file matches all20 target MPR units with one extent each, whole file max8. Actual loaded file/runtime mapping remains unproven; first-device plan/collector prepared only.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段129后优先执行可审核的首次上机准备：Mac系统USB缓存采集须取得对应范围授权；主动接口/备份需另完成请求及退出审计和对应授权。离线可继续核对WBI内配置缓存、20个extent规则选择/大小/所有权及恢复依赖，不把CP配置或官方原件当同机备份。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3正确AP配置与首次上机准备](<'+rel+'/README.md>)：官方AP603单位、目标20全匹配且各1块；上机放行清单/Mac缓存工具离线自测完成，实际查询、备份/编码/恢复和刷写未验未放行。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.shared_volume_check();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage129-AP-config-and-device-trial/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':digest(canonical)},
        'readme_index_before_sha256':hashlib.sha256(ib).hexdigest(),'readme_index_after_sha256':digest(index),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'target_matches':20,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
