#!/usr/bin/env python3
"""Seal a file-only audit tool; keep absent Windows evidence UNKNOWN."""
from pathlib import Path
import datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(STAGE));import audit_saved_arguments as auditor
sys.path.insert(0,str(BASE/'stage98-native-trace-buffer-origin-and-recovery-scope'));import trace_origin as prev
im=prev.im
PRIOR_SHA='8141fded71fdb61a80a208f276c8a3c723572bf7404ec862929df91f0ec9cf37'


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage98-native-trace-buffer-origin-and-recovery-scope/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    pj=json.loads(prior.read_text())
    for f in pj['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    tests=json.loads((STAGE/'synthetic-test-results.json').read_text())
    assert tests['tests_run']==18 and tests['failures']==tests['errors']==0
    assert tests['synthetic_inputs_only'] and not tests['device_queries_or_child_processes']
    source_receipt={}
    for name in ('audit_saved_arguments.py','test_saved_arguments.py'):
        p=STAGE/name;assert p.stat().st_mtime_ns<=(STAGE/'synthetic-test-results.json').stat().st_mtime_ns
        source_receipt[name]={'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
    # Anchor old public records through receipt hashes only, not a re-run or
    # rehash of every historical output/firmware emulation result.
    expected=PRIOR_SHA;chain=[]
    for number in range(98,67,-1):
        matches=list(BASE.glob('stage'+str(number)+'-*'));assert len(matches)==1
        p=matches[0]/'final-receipt.json';raw=p.read_bytes();assert im.sha(raw)==expected
        receipt=json.loads(raw);chain.append({'stage':number,'manifest_sha256':expected})
        expected=receipt['previous_manifest_sha256']
    cache=BASE/'stage68-current-USB-associations';cm=json.loads((cache/'final-receipt.json').read_text())
    public=cache/'from-windows-presence';inspected=[]
    for name in ('receipt.json','nodes.json','commands.json','summary.txt','private-sha256.json'):
        p=public/name;raw=p.read_bytes();entry=next(f for f in cm['files'] if f['path']==str(p.relative_to(ROOT)))
        assert len(raw)==entry['bytes'] and im.sha(raw)==entry['sha256']
        inspected.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    assert (cache/'from-windows-root-review').is_dir() and list((cache/'from-windows-root-review').iterdir())==[]
    commands=json.loads((public/'commands.json').read_text());nodes=json.loads((public/'nodes.json').read_text())
    unknown=auditor.audit(None,None,commands['commands'][0]);assert unknown['status']=='UNKNOWN_MISSING_NATIVE_ARGV_OR_SOURCE'
    assert not unknown['actual_native_process_argv_independently_observed_here']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    im.write_json(STAGE/'available-records-review.json',{'created_utc':now,'status':'UNKNOWN_MISSING_PRIVATE_SOURCE_AND_NATIVE_ARGV',
        'inspected_public_records':inspected,'source_manifest_chain':chain,
        'reported_cim_observation_utc':nodes['captured_utc'],
        'known_historical_usb_vid_pid':['054C','0DA1'],
        'reported_usb_root_node_hash':nodes['prior_fx3_root_sha256'],
        'reported_related_nodes':4,'physical_camera_count':'UNKNOWN',
        'Mac_root_review_directory_files':0,
        'missing_evidence_roles':['decoded raw CIM instance-ID source','current private root selection','observed final native argv or complete final commandline evidence','raw stdout/stderr and encoding for latest exact-root query'],
        'public_record_only_audit':unknown,
        'zero_match_cause':'UNKNOWN','current_connection_state':'UNKNOWN',
        'deferred_windows_task':str((BASE/'stage69-native-16M-callpath/WINDOWS_ARGUMENT_AUDIT.txt').relative_to(ROOT)),
        'new_device_queries_or_Windows_UU_access':False})
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)=='15e75a9732e2f9904ada1c919c631dac0da57e605ce3daa4c6fb2ebe98982b5b'
    pairs=[]
    for p in range(0,0x200000,4):
        w=int.from_bytes(blob[p:p+4],'little')
        if w>>26==15 and w&0xffff==0xbe00:
            rt=(w>>16)&31
            for q in range(p+4,min(p+36,0x200000),4):
                x=int.from_bytes(blob[q:q+4],'little')
                if x>>26==35 and (x>>21)&31==rt and x&0xffff==0xac:
                    pairs.append({'lui_file_offset':hex(p),'lw_file_offset':hex(q)});break
    assert len(pairs)==307
    im.write_json(STAGE/'timer-research-scope.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'method':'LUI immediatebe00, followed within8 instructions by LWac using same base-register encoding. No full register-liveness/control-flow validation.',
        'first_code_bytes_scanned':0x200000,'candidate_pairs_count':307,'candidate_pairs':pairs,
        'primary_spec_search_queries':['"0xbe0000ac"','"CXD90057" "timer"','"vcd_firmware_imola2"','"0x1e0000ac" on github.com/oss.sony.net','"be000000" "Sony" "timer" on github.com/oss.sony.net','"CXD90057" "VCD" on github.com/oss.sony.net'],
        'applicable_primary_register_spec_found_in_this_search':False,
        'unrelated_search_results_not_used_for_register_semantics':True,
        'timer_frequency_unit_register_liveness_or_actual_access_count_proven':False,
        'MMIO_or_counter_value_injected':False})
    im.write_json(STAGE/'validation-source-receipt.json',{'created_utc':now,'sources':source_receipt,
        'test_result_sha256':im.sha((STAGE/'synthetic-test-results.json').read_bytes()),
        'method':'Same-agent observed execution of current source; files unchanged after test (mtime check and hashes). Source hashes/file seals are integrity evidence, not independent runtime attestation.',
        'platform':'Existing Mac Python environment; Windows execution not performed',
        'official_parameter_reference':'https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/pnputil-command-syntax',
        'enum_devicetree_version_gate':'Windows11 23H2; user exact version not verified',
        'planned_commands_equal_observed_native_argv':False})
    review={'status':'PASS_OFFLINE_ARGUMENT_AUDITOR_SYNTHETIC_BOUNDARIES_ACTUAL_WINDOWS_CAUSE_UNKNOWN',
        'created_utc':now,'prior_sealed_files_verified':len(pj['files']),'historical_manifest_hashes_anchored':len(chain),
        'historical_public_files_checked':len(inspected),'synthetic_tests_passed':18,
        'same_body_identity_argument_cause_or_current_presence_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_saved_argument_auditor_and_missing_Windows_evidence_scope_review'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
        'basis':['stage98封存17件/canonical复核，旧public源通过98到68的manifest链锚定及5件文件核对；未重询设备或访问Windows/UU。',
            '实现仅现存JSON参数审计：JSON只解码一次、ASCII uppercase UTF8 hash合同，非ASCII/无真实argv/显示WQL等UNKNOWN；硬件ID与实例ID、tree位置参数分开，输出不泄露原ID。18项合成边界及普通文件路径/不覆盖测试通过，非Windows实机验收。',
            '现有public记录保留历史VID/PID和17:15快照，但Mac缺最新private root/原生argv/stdout，不能解释零匹配或证明当前连接；原计划格式与微软文档一致不等于实际argv证明。Windows任务继续延后，不要求传话或新查询。',
            '计时精确检索未得到适用原始寄存器规范；307个短窗口指令对仅启发式候选，未据其它设备资料推断频率或注入MMIO。',
            '全部16项状态/授权保持；实际目标HEVC、声音长录冷启动及同机备份恢复/独立救砖未验收。'],
        'completion_not_claimed':True}
    availability=rel+'/available-records-review.json'
    g['latest_stage_evidence']['stage99_saved_argument_auditor']={'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json',
        'tool':rel+'/audit_saved_arguments.py','tests':rel+'/synthetic-test-results.json','available_records':availability,
        'scope':'Portable existing-file-only string audit,18 synthetic boundary tests. Actual current private IDs/argv/stdout absent; connection/zero-match cause UNKNOWN. No Windows/device execution.',
        'authorization_unchanged':True,'goal_complete':False}
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Public JSON/WQL escape rendering or planned command text cannot establish actual native argv. Added explicit offline record comparison that refuses unsupported/missing evidence; old Present snapshot and VID/PID are historical, not current physical binding.',
        'actual_argv_target_identity_or_current_connection_proven':False})
    for req in g['requirements']:
        if req['id']=='G01':
            req['evidence'].append(availability)
            req['stage99_scope']='Mac仅public缓存回执，缺最新private root/argv/stdout；仅现存JSON参数工具18项合成测试通过，实际零匹配原因/当前连接/同机身份未证，Windows延后。'
    g['next_safe_offline_actions'].append('stage99已有现存JSON参数审计工具，不应重复按JSON文本斜杠或手写命令猜Windows错误。私有CIM/root/最终argv/stdout仍只在不可用Windows，保持延后不访问UU/Windows/设备、不要求传话。可继续真实mode消息生产和原运行上下文研究；307计时指令对不是寄存器规范/频率证据，不注入MMIO求通过。所有主录/同机恢复验收保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies','current_guest_adapter_prototype','next_authorized_cached_metadata_action'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 现存缓存参数离线审计工具](<'+rel+'/README.md>)：18项合成边界通过，区分JSON/WQL/原生argv、实例与硬件ID及tree参数；Mac缺私有源，真实零匹配/当前连接仍UNKNOWN。无新设备查询，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            raw=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage99-offline-saved-argument-auditor/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
