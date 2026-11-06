#!/usr/bin/env python3
"""Seal range-primitive inventory and prefix guest without device release."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import copy
import difflib
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage160-LSDA-selected-read-error-and-close-review'
PRIOR_SHA='8ec514290369f25c88db89341255be1ba4ea8f00dd116af7a5c7af1476c0162a'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    raw=(HELPER/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    m=next(m for m in json.loads(raw)['files'] if m['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==m['sha256']
    spec=importlib.util.spec_from_file_location('range_inventory_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();previous=helper.check_previous();assert previous==27
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before=(HERE/'goal-status-before.json').read_bytes();assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    original=(HERE/'readme-before.md').read_bytes();index_before=index.read_bytes()
    assert all(line in index_before.decode().splitlines() for line in original.decode().splitlines() if 'work/sony-firmware-20261024/' in line)
    (HERE/'readme-rebased-before.md').write_bytes(index_before)
    put('index-rebase-review.json',{'original_sha256':sha256(original).hexdigest(),'rebased_sha256':sha256(index_before).hexdigest(),
        'diff':list(difflib.unified_diff(original.decode().splitlines(),index_before.decode().splitlines(),lineterm=''))})
    old=json.loads(before);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert old['authorization']['Mac_owner_trial_authorized'] and not old['prepared_first_device_trial']['Mac_owner_trial_released']
    assert not old['authorization']['camera_file_access'] and not old['authorization']['service_auth_mode_or_stop']
    bundle=BASE/'stage156-hardened-owner-launch-and-ack/release-bundle.json'
    assert helper.digest(bundle)==old['authorization']['Mac_owner_trial_bundle_sha256']=='e099d58b73261c076491fc0c08c9b1b4b72f5a844fe3af22b3d8060110a956a4'
    for m in json.loads(bundle.read_text())['files']:assert helper.digest(bundle.parent/m['path'])==m['sha256']
    assert not (bundle.parent/'physical-grant-attempt.claim').exists()
    assert not Path('/private/tmp/fx3-702-msc-owner-20261028-01').exists()
    assert (HERE/'inventory_readers.py').read_bytes()==(HERE/'inventory-executed.py').read_bytes()
    assert (HERE/'audit_read_routes.py').read_bytes()==(HERE/'route-audit-executed.py').read_bytes()==(HERE/'run-original-prefix-read/static-image-source.py').read_bytes()
    assert (HERE/'prefix_reader_guest.py').read_bytes()==(HERE/'run-original-prefix-read/executed-source.py').read_bytes()
    inventory=json.loads((HERE/'AP-range-read-inventory.json').read_text())
    assert inventory['ELF_count']==len(inventory['ELF_records'])==532 and inventory['matching_ELF_count']==168
    assert inventory['source_image_sha256']=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    assert helper.digest(ROOT/inventory['source_image'])==inventory['source_image_sha256']
    prior=json.loads((BASE/'stage148-initial-MSC-handler-inventory/AP-handler-inventory.json').read_text())
    prior_records={m['inode']:m for m in prior['ELF_records']}
    for m in inventory['ELF_records']:
        p=prior_records[m['inode']];assert m['sha256']==p['sha256'] and m['bytes']==p['bytes']
    stream=[r for r in inventory['ELF_records'] if any('ReadDeviceData' in s['name'] for s in r['symbols'])]
    assert len(stream)==1 and stream[0]['image_paths']==['/lib/libsencore.so']
    assert not any(s['name'] in ['pread','pread64'] for r in inventory['ELF_records'] for s in r['symbols'])
    route=json.loads((HERE/'original-read-route-review.json').read_text())
    assert len(route['functions'])==14 and route['anonymous_file_helper']['bytes']==936 and not route['direct_constructor_calls']
    assert route['no_direct_lseek_callers_in_this_text'] and route['helper_operation_jump_table'][1]['VA']=='0x10ae4'
    assert route['stream_class_semantics']['factory_packet_binding_or_runtime_instantiation_proven'] is False
    core=BASE/'stage2/extraction/files/nflasha15/lib/libsencore.so'
    assert helper.digest(core)==route['original_library_sha256']=='a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
    ownspec=importlib.util.spec_from_file_location('reviewed_static_core_image',HERE/'audit_read_routes.py')
    own=importlib.util.module_from_spec(ownspec);ownspec.loader.exec_module(own);image=own.Image()
    assert not any('ReadDeviceDataC1' in n or 'ReadDeviceDataC2' in n for n in image.plt.values())
    assert image.read(0x167c8,16).hex()=='e20301aae103002a00008052cbcdff17'
    guest=json.loads((HERE/'run-original-prefix-read/results.json').read_text())
    assert guest['case_count']==len(guest['cases'])==11 and guest['instruction_entries']==1920 and not guest['actual_IO_or_Sony_native_execution']
    cases={c['name']:c for c in guest['cases']}
    assert all(c['function_return_w0']==0 and not c['complete_file_backup_or_service_reachability_proven'] for c in guest['cases'])
    assert cases['read_error']['read_return']==-1 and cases['read_error']['buffer_all_zero']
    assert cases['short_read']['read_return']==31 and cases['short_read']['zero_padding_after_short_read']
    assert cases['prefix_64KiB_of_79MB']['read_count']==65536 and cases['size_above4GiB']['read_count']==32
    assert cases['block_size_query_error']['read_count']==0
    review=json.loads((HERE/'bounded-read-scope-review.json').read_text())
    assert review['AP_ELF_count']==532 and review['prefix_guest_cases']==11 and review['new_root_or_active_USB_or_camera_file_operations']==0
    assert review['owner_trial_authorization_retained'] and not review['one_shot_consumed']
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='All532 AP ELFs inventoried for range/stream read primitives;14 original core functions and internal prefix helper reviewed,11 prefix guest cases/1920 entries;no service route or full backup proven'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段161重验160全部27成员和156固定运行包；上一轮异常路径及12guest为进展，本轮转查可实际用于有界备份的现有读取组件，未只重复旧检查。',
        '从固定原AP分区重验532 ELF逐inode哈希；扩展stdio/Fsys及ReadDeviceData后168个文件匹配。此前较窄153盘点保留。AP命名符号未见pread，不能排除syscall/其它分区/ROM/动态实现。',
        'ReadDeviceData仅本库定义，具有缓冲耗尽后再读逻辑，但无本库直接构造调用或其它AP命名导入；vtable候选仅构造/析构。存在组件不充服务协议可达或已实例化。14原函数及直接引用固定，FirmwareUpdateFunc此回调直接NULL不推广为官方升级器无能力。',
        '原匿名文件辅助函数operation1读取min(请求uint32,64位size)，先memset全请求长度；需另证目的容量，64KiB仅本guest上限。11原指令guest/1920进入确认读取短缺/错误仍return0，零填充可掩盖失败；没有offset或seek且每次重开，不能直接续成完整文件。',
        '原DeviceIo.size普通文件大小64位、块设备ioctl1260扇区乘512；查询错误也可归0，实际驱动未测。ReadDeviceData构造/接口绑定、真实读取/清理及恢复仍缺，未发布新服务命令。',
        '所有原指令仅Unicorn，系统调用/数据/容量/日志为显式提供者。156授权保留，仍待手动推出相机卷，root/接管次数未耗；完整16要求/旧候选/所有权限不变，未执行认证/相机文件/模块/刷写。'])
    new['latest_stage_evidence']['stage161_bounded_read_primitives_and_prefix_limits']={
        'readme':REL+'/README.md','inventory':REL+'/AP-range-read-inventory.json','original_routes':REL+'/original-read-route-review.json',
        'guest':REL+'/run-original-prefix-read/results.json','review':REL+'/bounded-read-scope-review.json',
        'AP_ELFs':532,'matched_files':168,'original_functions':14,'guest_cases':11,'instruction_entries':1920,
        'actual_packet_binding_or_backup':False,'new_root_or_active_device_operations':0}
    new['next_safe_offline_actions'].append('161已确认原AP存在ReadDeviceData续读组件但仅自身定义，当前无实例化/协议绑定证明；内部限量读辅助函数只读开头且吞短读/错误，不可直接拼完整备份。继续追有界组件的动态入口、缓冲所有权、完整计数和清理可观测性；532命名扫描不充整机API不存在。156授权与编号/SHA保持，仍等手动推出FX3所有卷，满足前置条件才放行一次，不重新请求授权。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for k,v in old['latest_stage_evidence'].items():assert new['latest_stage_evidence'][k]==v
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    marker='## 相机与固件研究\n'
    entry='- [2026-10-28 FX3有界读取组件与服务入口盘点](<'+REL+'/README.md>)：532 ELF/168匹配文件、14原函数及11组前缀读guest；组件存在但可达续读未证，内部前缀读吞错误，无新增主动设备操作。'
    text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal.tmp'),(index,index_after,'.index.tmp')]:
        tmp=HERE/name
        with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after;helper.check_previous()
    put('completed-evidence-review.json',{'status':'PASS_ORIGINAL_RANGE_PRIMITIVE_SCOPE_NOT_PACKET_OR_BACKUP_ACCEPTANCE','created_utc':now,
        'previous_manifest_members_verified':previous,'AP_ELFs':532,'matched_files':168,'original_functions':14,'guest_cases':11,'instruction_entries':1920,
        '16_requirements_authorization_and_all_prepared_values_preserved':True,'fixed_guest_front_backend_pins':fixed,
        'current_grant_authorized':True,'runtime_release':False,'physical_attempt_consumed':False,'goal_complete':False,'persistent_write_release':False})
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage161-range-primitive-inventory/1','created_utc':now,'volume_uuid':helper.UUID,
        'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,'allowed_goal_keys_changed':sorted(allowed),
        'mutable_heads_excluded':True,'canonical_after_sha256':sha256(encoded).hexdigest()})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'runtime_release':False,'attempt_consumed':False}))


if __name__=='__main__':main()
