#!/usr/bin/env python3
"""Local registration only: existing-file hashes and progress snapshots; no camera/network API."""
from pathlib import Path
import copy, datetime, hashlib, json, os, plistlib, re, subprocess
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac'); BASE=ROOT/'work/sony-firmware-20261024'
STAGE=Path(__file__).resolve().parent; REL=STAGE.relative_to(ROOT).as_posix()
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
PRIOR=BASE/'stage130-backup-read-path-side-effects/final-receipt.json'
PRIOR_SHA='dfe86dc9e8238b7bc21c22cb2240c61e2ad4ebbfa7c83958a4111cee26424471'
GOAL_SHA='c5710da0244f5c671a32600c1b18097d4f7f8e0985d4743078c92a5908806517'
INDEX_SHA='1fff1144514241ab397829e4fb76bfc8424d48464a9d9cb2862990e6521b695b'
REPORT=ROOT/'reports/索尼 FX3 救砖与官方接口.md'
REPORT_SHA='656025dea2b82d1fe703d6378eee1206a1df59f0ea3202960edcda30b3ee6583'
NOTES=BASE/'research_notes/索尼 FX3 救砖与官方接口'
ARTIFACTS=[REPORT]+[NOTES/n for n in ('official_recovery.md','community_cases.md','service_interfaces.md')]
WIP=BASE/'stage131-stock-parser-filecontrol-availability'
P117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json'
P117_SHA='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
ALLOWED={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):return {'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
def put(name,value):
    with (STAGE/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def raw(name,value):
    with (STAGE/name).open('xb') as f:f.write(value)
def volume():
    d=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert d['VolumeUUID']==UUID and d['MountPoint']=='/Volumes/KAFU2T' and d['WritableVolume'] and os.access(STAGE,os.W_OK)
    return {'uuid':UUID,'mount_point':d['MountPoint'],'writable':True}
def previous():
    assert sha(PRIOR)==PRIOR_SHA
    m=json.loads(PRIOR.read_text());assert len(m['files'])==19
    for f in m['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256'],f['path']
    return m
def pins(g):
    out=[];bundle=g['current_guest_adapter_prototype']['bundle'];assert len(bundle)==4
    for f in bundle.values():
        p=ROOT/f['path'];assert sha(p)==f['sha256'];out.append(rec(p))
    assert sha(P117)==P117_SHA
    frontend=[f for f in json.loads(P117.read_text())['files'] if Path(f['path']).name in ('scoped_frontend.c','scoped_frontend.a64.o')]
    assert len(frontend)==2
    for f in frontend:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256'];out.append(rec(p))
    return out
def wip():
    assert WIP.is_dir() and not (WIP/'final-receipt.json').exists()
    assert not any(p.is_symlink() for p in WIP.rglob('*'))
    return {'path':WIP.relative_to(ROOT).as_posix(),'sealed':False,'used_as_evidence':False,
            'purpose':'Preservation inventory only; no WIP conclusions relied on.',
            'files':[rec(p) for p in sorted(WIP.rglob('*')) if p.is_file()]}
def atomic(target,data,name):
    p=STAGE/name
    with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(p,target)
def main():
    assert STAGE==BASE/'stage132-public-recovery-and-service-interfaces' and not (STAGE/'final-receipt.json').exists()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();v=volume();m=previous()
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md';before,ib=canonical.read_bytes(),index.read_bytes()
    assert sha(canonical)==GOAL_SHA and sha(index)==INDEX_SHA
    assert before==(PRIOR.parent/'goal-status-after.json').read_bytes()
    old=json.loads(before);assert old['latest_stage']=='stage130-backup-read-path-side-effects'
    assert len(old['requirements'])==16 and old['goal_complete'] is False and old['persistent_write_release'] is False
    fixed=pins(old);assert sha(REPORT)==REPORT_SHA;artifacts=[rec(p) for p in ARTIFACTS];wb=wip()
    raw('goal-status-before.json',before);raw('readme-before.md',ib);put('stage131-wip-inventory-before.json',wb)
    put('preflight-verification.json',{'created_utc':now,'volume':v,'stage130_manifest':rec(PRIOR),
        'stage130_members_rehashed':19,'canonical_equals_stage130_after':True,'canonical_before':rec(canonical),
        'readme_before':rec(index),'stage75_four_and_stage117_two_pins':fixed,'research_artifacts':artifacts,
        'no_analysis_or_simulation_rerun':True,'new_camera_USB_Windows_UI_API_calls':0})
    sources={}
    for p in ARTIFACTS:
        for url in re.findall(r'\]\((https?://[^\s)]+)\)',p.read_text()):
            sources.setdefault(url,[])
            where=p.relative_to(ROOT).as_posix()
            if where not in sources[url]:sources[url].append(where)
    conclusions=[
        '7.02卡更新指定失败重试/同版或旧版DAT拒绝，与USB十五分钟FAQ分支分开。',
        '旧FX3恢复和6.00/6.02换板均有一手后续；不外推7.02降级或芯片物理损坏。',
        'A7CII #31已出现模式切换恢复；不再记作已证必须换板，不迁移为FX3操作。',
        'Sony有维修技术资料体系，经典FX3具体工位工具和独立恢复适配仍未公开闭合。',
        'SDK/Command有常规远程更新记录；最新FX3逐API适配未核验，独立救砖/裸闪存备份未证。',
        'A7IV BootROM/RP2040/eMMC原始研究及boot0转换限制不等于FX3适配；fwtool解包不等于可安全重打包。',
        '仅复用既有Mac缓存与130读路径副作用证据；无新增设备、健康备份、目标成片或FX3救援闭环。']
    put('source-and-scope-audit.json',{'schema':'fx3-stage132-public-research-scope/1','created_utc':now,
        'target':'classic ILME-FX3 7.02; 1920x1080 30000/1001 HEVC42010 MAIN; exact30.000 separate',
        'research_artifacts':artifacts,'public_sources':[{'url':u,'referenced_by':sources[u]} for u in sorted(sources)],
        'research_cutoff':'2026-10-27','new_network_requests_downloads_submissions':0,'conclusions':conclusions,
        'source_difference':'Chinese7.02 same-position wording: version error; US/JP: target-model mismatch. Preserve complete actual prompt.',
        'open_evidence_gap':'Current FX3 SDK/Command per-API compatibility table not obtained.',
        'stage131_unsealed_unchanged_not_depended_on':True,'new_camera_USB_Windows_UI_API_calls':0,
        'authorization_expanded':False,'new_hardware_analysis_or_simulation':False,
        'safe_next_gates':['audited same-body healthy backup','model-specific independent entry and actual original-byte restore/readback',
                           'reversible RAM trial with real main-recording output/audio/timing/long-record validation','then assess persistent installation'],
        'goal_complete':False,'persistent_write_release':False})
    entry=('- [2026-10-27 FX3 救砖与官方接口](<reports/索尼 FX3 救砖与官方接口.md>)：官方失败分支、真实恢复/换板案例及维修/SDK/BootROM边界复核；双机仍无已验经典FX3独立救援，主动查询与持久写入未放行。[本轮登记](<'+REL+'/README.md>)。')
    marker='## 相机与固件研究\n';text=ib.decode();assert text.count(marker)==1 and entry not in text
    ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']+='; completed_public_recovery_cases_and_official_service_interface_research_only'
    g['progress_audit']['basis'].extend([
        '阶段132仅登记已完成公开研究；130固定manifest及19成员/canonical基线重验，131未封存原样保留且未依赖。',
        '官方限定重试/同版拒绝、旧FX3恢复/换板、A7CII#31模式恢复、SDK逐API未知与A7IV适配边界已入正式报告及三份笔记。',
        '未新增设备/USB/Windows/UU/UI/API操作或仿真；75 bundle四件/117 frontend两件固定哈希保持，16项状态与全部授权约束不变。',
        '双机仍无经典FX3 7.02自定义修改独立恢复闭环，健康备份/实际恢复/目标主录验收仍缺，goal_complete及persistent_write_release保持false。'])
    key='stage132_public_recovery_and_service_interfaces';assert key not in g['latest_stage_evidence']
    g['latest_stage_evidence'][key]={'readme':REL+'/README.md','report':REPORT.relative_to(ROOT).as_posix(),
        'report_sha256':REPORT_SHA,'notes':[p.relative_to(ROOT).as_posix() for p in ARTIFACTS[1:]],
        'source_audit':REL+'/source-and-scope-audit.json','review':REL+'/completed-evidence-review.json',
        'scope':'Completed public-source research and local registration only; no new device or recovery/output proof.',
        'stage131_unsealed_not_depended_on':True,'stage75_backend_changed':False,'stage117_frontend_changed':False,
        'authorization_unchanged':True,'goal_complete':False,'persistent_write_release':False}
    assert set(g)==set(old)
    for k in old:
        if k not in ALLOWED:assert g[k]==old[k],k
    for k,value in old['latest_stage_evidence'].items():assert g['latest_stage_evidence'][k]==value
    after=(json.dumps(g,ensure_ascii=False,indent=2)+'\n').encode()
    raw('goal-status-after.json',after);raw('readme-after.md',ia)
    raw('README.md',('''# FX3 公开救援与官方接口研究登记

2026-10-27。本阶段仅登记已验收的[正式研究报告](../../../reports/索尼%20FX3%20救砖与官方接口.md)与三份笔记，不新增研究、设备操作、硬件分析或仿真。官方限定恢复与真实案例的范围、Sony维修/SDK接口、A7IV独立入口及目标FX3缺口，见报告与[范围/来源清单](source-and-scope-audit.json)。当前Mac＋Intel/AMD Windows11没有经过验证的经典FX3 7.02自定义固件独立救援闭环。

130固定manifest及19成员已重哈希，更新前canonical等于130 after。131原样保留为未封存WIP，只有前后保全清单，不依赖其结论或当作硬件证据。75 bundle四件及117 frontend源/对象固定哈希保持。[登记前核验](preflight-verification.json)和[完成复核](completed-evidence-review.json)留存结果。

仅追加项目README报告入口与GOAL research_activity/progress_audit/latest_stage_evidence，将latest_stage登记为132。16项requirements整体、authorization、用户约束及其他非进度字段保持，goal_complete/persistent_write_release仍false。canonical/README写入前CAS检查，前后快照保留。本轮不扩主动查询、认证、机身文件、驱动、模块、WBI或flash权限。

登记脚本和全部132材料、报告/三份笔记以及当前README/canonical均列入[最终SHA/bytes清单](final-receipt.json)，路径显式相对Mac项目根；final-receipt不自纳入。封存后以另一段只读代码独立重哈希；这仍是同一代理复核，不声称另一引擎或实机验收。
''').encode())
    volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'CAS conflict'
    assert pins(old)==fixed and [rec(p) for p in ARTIFACTS]==artifacts and wip()==wb
    atomic(canonical,after,'.canonical-write.tmp');assert index.read_bytes()==ib
    atomic(index,ia,'.index-write.tmp');assert canonical.read_bytes()==after and index.read_bytes()==ia
    wa=wip();assert wa==wb;put('stage131-wip-inventory-after.json',wa)
    previous();assert pins(old)==fixed and [rec(p) for p in ARTIFACTS]==artifacts
    review={'status':'PASS_PUBLIC_RESEARCH_LOCAL_REGISTRATION_ONLY','created_utc':now,'stage130_members_rehashed':19,
        'canonical_before_equals_stage130_after':True,'canonical_after_equals_stage132_after':True,
        'canonical_and_readme_CAS_passed':True,'all16_requirements_and_statuses_unchanged':True,
        'old_research_activity_progress_basis_latest_stage_evidence_preserved':True,
        'authorization_user_constraints_and_all_other_GOAL_fields_unchanged':True,
        'stage75_bundle_pins':4,'stage117_frontend_pins':2,'report_and_three_notes_unchanged':True,
        'stage131_unchanged_unsealed_not_depended_on':True,'new_camera_USB_Windows_UI_API_calls':0,
        'analysis_or_simulation_rerun':False,'goal_complete':False,'persistent_write_release':False}
    put('completed-evidence-review.json',review)
    local=[p for p in sorted(STAGE.rglob('*')) if p.is_file()];assert all(p.name!='final-receipt.json' for p in local)
    members=sorted(local+ARTIFACTS+[canonical,index],key=lambda p:p.relative_to(ROOT).as_posix());files=[rec(p) for p in members]
    assert len({f['path'] for f in files})==len(files)
    put('final-receipt.json',{'schema':'fx3-stage132-public-recovery-and-service-interfaces/1','created_utc':now,
        'volume_uuid':UUID,'paths_relative_to':'Mac project root','files':files,'member_count':len(files),
        'stage132_member_count':len(local),'previous_manifest_sha256':PRIOR_SHA,'previous_sealed_stage':PRIOR.parent.name,
        'stage131_unsealed_not_depended_on':True,'operations':review,
        'mutable_progress':{'before_sha256':GOAL_SHA,'after_sha256':sha(canonical)},
        'readme_index_before_sha256':INDEX_SHA,'readme_index_after_sha256':sha(index),'readme_index_entry':entry,
        'allowed_goal_keys_changed':sorted(ALLOWED),'requirements_retained':16,'authorization_unchanged':True,
        'goal_complete':False,'persistent_write_release':False})
    print(json.dumps({'manifest_sha256':sha(STAGE/'final-receipt.json'),'member_count':len(files),
        'stage132_members':len(local),'canonical_equals_stage132_after':True,'new_camera_USB_Windows_UI_API_calls':0}))
if __name__=='__main__':main()
