#!/usr/bin/env python3
"""Publish static normal-mode route evidence; preserve every live device gate."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import copy
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage147-bounded-owned-handle-wire'
PRIOR_SHA='9103fecb7eb88cf7b2f1c76a48a580eaedd527bcdd762bf70025cca6d261827c'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    raw=(HELPER/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    pin=next(x for x in json.loads(raw)['files'] if x['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==pin['sha256']
    spec=importlib.util.spec_from_file_location('fixed_static_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();count=helper.check_previous();assert count==35
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=(HERE/'goal-status-before.json').read_bytes(),(HERE/'readme-before.md').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    assert index.read_bytes()==index_before
    old=json.loads(before);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['authorization']['service_auth_mode_or_stop'] and not old['authorization']['driver_change']
    assert not old['prepared_first_device_trial']['Mac_descriptor_probe_released']
    for name,saved in [('inventory_handlers.py','inventory-executed.py'),('audit_normal_entry.py','normal-entry-executed.py'),
                       ('audit_dynamic_nin.py','dynamic-NIN-executed.py')]:
        assert (HERE/name).read_bytes()==(HERE/saved).read_bytes()
    inventory=json.loads((HERE/'AP-handler-inventory.json').read_text())
    assert inventory['regular_entries']==797 and inventory['unique_ELF_inodes']==len(inventory['ELF_records'])==532
    assert inventory['unique_non_ELF_regular_files']==265 and inventory['matched_ELF_files']==54
    assert len({x['inode'] for x in inventory['ELF_records']})==532
    assert sum(bool(x['matching_symbols']) for x in inventory['ELF_records'])==54
    assert helper.digest(ROOT/inventory['source_image'])==inventory['source_image_sha256']=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    assert helper.digest(BASE/'stage2/extraction/read_filesystems.py')==inventory['reader_sha256']=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    normal=json.loads((HERE/'normal-entry-review.json').read_text());assert len(normal['functions'])==4
    original=ROOT/normal['original']['path']
    assert original.stat().st_size==normal['original']['bytes'] and helper.digest(original)==normal['original']['sha256']
    origin=next(x for x in inventory['ELF_records'] if '/lib/libObj.so' in x['image_paths'])
    assert origin['sha256']==normal['original']['sha256'] and origin['bytes']==normal['original']['bytes']
    route=json.loads((HERE/'dynamic-NIN-route-review.json').read_text())
    assert route['input_SHA256']==normal['original']['sha256']
    assert len(route['functions'])==12 and route['asserted_local_instruction_facts']==24
    assert len(route['callback_table_relocations'])==3 and route['dynamic_symbol_strings']['0x1dc248']=='libsencore.so'
    assert not route['initial_MSC_hash_input_algorithm_proven'] and route['no_auto_change_to_stage145_MSC_digest_selection']
    assert not route['current_MSC_driver_USB_transport_or_cooperator_vtable_binding_proven']
    assert route['new_host_USB_camera_driver_or_Windows_operations']==0 and not route['original_code_executed']
    public=json.loads((HERE/'public-source-review.json').read_text())
    search=json.loads((HERE/'public-issue-refresh/FX3-search.json').read_text())
    source=json.loads((HERE/'public-issue-refresh/source.json').read_text())
    assert helper.digest(HERE/'public-issue-refresh/FX3-search.json')==source['sha256']
    assert search['total_count']==len(search['items'])==public['GitHub_search']['total']==16
    assert not public['API_comment_fetch_failures']['714_comments_claimed_reviewed']
    assert not public['downloaded_instructions_or_camera_commands_executed']
    now=datetime.now(timezone.utc).isoformat()
    put('completed-local-review.json',{
        'created_utc':now,'shipped_AP_ELF_files':532,'matching_named_symbol_files':54,
        'libObj_exported_entry_functions':4,'libObj_FDE_bounded_dynamic_route_functions':12,
        'exact_instruction_facts':24,'original_callback_relocations':3,
        'named_symbol_absence_not_absence_of_implementation':True,
        'normal_application_callback_and_dynamic_NinThread_start_statically_linked':True,
        'requested_library_basename_not_actual_loaded_path_or_module_identity':True,
        'initial_MSC_digest_selection_and_transport_binding_remain_unproven':True,
        'new_device_operations_or_Sony_code_execution':0,'same_agent_local_review_only':True})
    new=copy.deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Inventoried532 shipped AP ELFs; original normal-app event callback to dynamic NIN loader traced statically'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段148重验147全部35成员与6固定原型；上一轮78项C夹具检查/两流程和收发实现封存为实际进展。',
        '固定官方镜像797普通文件中532个ELF完成命名符号/导入及依赖盘点，54文件命中；名称缺失不作实现缺失或初始认证不存在证明。',
        '新提取原libObj.so为数据，4导出入口及12个原eh_frame边界局部函数连接普通应用注册/事件1回调与libsencore.so basename的NinThread动态查找及pthread_create封装；24指令事实/3重定位检查。',
        '运行时实际模块/协作者虚表与MSC收发对象尚未绑定，不擅自将原服务512B摘要改作初始MSC算法。公开16条issue刷新及715/504完整相关后续仍不提供经典FX3 7.02互刷/救砖验收。',
        '没有执行Sony代码、相机、USB或Windows步骤，一次描述符授权保持关闭；完整HEVC MAIN/同机完整健康备份恢复/独立救援及全部16要求不变。'])
    new['latest_stage_evidence']['stage148_normal_application_dynamic_NIN_route']={
        'readme':REL+'/README.md','AP_inventory':REL+'/AP-handler-inventory.json',
        'normal_entry':REL+'/normal-entry-review.json','dynamic_NIN_route':REL+'/dynamic-NIN-route-review.json',
        'public_refresh':REL+'/public-source-review.json','shipped_ELFs_inventoried':532,
        'original_local_FDE_functions':12,'instruction_facts':24,'callback_relocations':3,
        'actual_MSC_transport_cooperator_or_hash_algorithm_proven':False,
        'new_device_operations':0,'authorization_unchanged':True}
    new['prepared_first_device_trial']['original_normal_application_NIN_loader_static_receipt']=REL+'/dynamic-NIN-route-review.json'
    new['prepared_first_device_trial']['normal_application_NIN_loader_not_MSC_transport_or_hash_proof']=True
    new['next_safe_offline_actions'].append(
        '阶段148已定位普通应用libObj的senif_init(1)回调ea128，经eb900动态查找libsencore.so的NinThread。后续追回调保存对象及2ce108协作者构造/虚表与收发函数，区分普通dispatcher模式0支路；未确认实际MSC绑定前不改前4B/完整512B算法选择。受限owner及驱动归还、STALL适配和worker结束仍需补齐；不重跑已消耗描述符试验，完整主录/恢复要求保持。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ('prepared_first_device_trial','latest_stage_evidence'):
        for k,v in old[section].items():assert new[section][k]==v
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    marker='## 相机与固件研究\n';text=index_before.decode()
    entry='- [2026-10-27 FX3普通应用NIN动态入口](<'+REL+'/README.md>)：532个AP ELF盘点，原libObj回调接NinThread动态加载的12函数/24指令事实/3重定位；实际MSC协作者/摘要和恢复未验，无新增相机操作。'
    assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-final.tmp'),(index,index_after,'.index-final.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    helper.check_previous()
    put('completed-evidence-review.json',{
        'status':'PASS_STATIC_AP_INVENTORY_AND_NORMAL_DYNAMIC_NIN_ROUTE_NOT_MSC_AUTH_OR_CAMERA_ACCEPTANCE',
        'created_utc':now,'previous_manifest_members_verified':count,'original_ELF_files_inventoried':532,
        'original_normal_route_functions':12,'new_device_operations':0,
        'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'goal_complete':False,'persistent_write_release':False})
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage148-static-normal-NIN-inventory/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
            'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
