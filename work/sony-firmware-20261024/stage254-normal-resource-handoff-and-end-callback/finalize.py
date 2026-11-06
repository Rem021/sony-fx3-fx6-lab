"""Seal the bounded original-file lifecycle audit; no device or privileged code."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
import os
import plistlib
import subprocess

H = Path(__file__).resolve().parent
B = H.parent
R = B.parents[1]
P = B / 'stage253-level-gated-read-and-stop-unblock'
assert not (H / 'final-receipt.json').exists()
volume = plistlib.loads(subprocess.check_output([
    '/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
assert volume.get('MountPoint') == '/Volumes/KAFU2T'
assert volume.get('VolumeUUID') == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()

def put(name, value):
    data = value if isinstance(value, bytes) else encoded(value)
    descriptor = os.open(H / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)

previous_raw = (P / 'final-receipt.json').read_bytes()
assert sha256(previous_raw).hexdigest() == '9cc67c655c412aa40c7b52a886ca0d9f8cd9591c4c6ac28314bc50346fdf6014'
previous = json.loads(previous_raw)
assert len(previous['files']) == 23
for member in previous['files']:
    raw = (R / member['path']).read_bytes()
    assert len(raw) == member['bytes'] and sha256(raw).hexdigest() == member['sha256'], member['path']

audit = json.loads((H / 'handoff-and-end-audit.json').read_text())
boot = json.loads((H / 'boot-script-scope.json').read_text())
assert len(audit['functions']) == 18 and audit['instruction_checks'] == 64
assert len(audit['relocation_bindings']) == 6 and len(audit['path_edges']) == 10
assert not audit['camera_threads_completion_proven']
assert audit['new_camera_cache_admin_operations'] == 0
assert len(boot['selected_files']) == 6 and boot['camera_accesses'] == 0
now = datetime.now(timezone.utc).isoformat()

recovery_scope = dict(
    checked_utc=now,
    official_source='https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000844060.html',
    source_title='ILME-FX3 Ver.2 or later Help Guide: Troubleshooting',
    method='Official page opened with web tool; factual paraphrase only, no live camera operation.',
    fact='Sony general troubleshooting suggests removing the battery, waiting about one minute, reinserting and powering on; it also lists settings initialization and authorized service as further options.',
    interpretation='This is a general troubleshooting instruction. It is not an independently verified FX3 service-session recovery test, firmware restore mechanism, boot-area repair or guarantee of recovery from a modified package.',
    not_a_current_power_cycle_or_settings_reset_instruction=True,
    pending_host_or_device_IO_must_not_be_reclassified_as_complete=True,
    full_backup_or_independent_recovery_proven=False)
put('official-restart-scope.json', recovery_scope)

contract = dict(
    schema='fx3-normal-lifecycle-design-v1',
    status='SOURCE_FLOW_BOUND_NATIVE_MULTI_IDENTITY_SENDER_NOT_IMPLEMENTED_OR_APPROVED',
    applicability='Saved classic ILME-FX3 7.02 official files; actual runtime registrations and resource delivery remain unmeasured.',
    lifecycle=[
        dict(step=1, action='Bind original MSC identity and owner',
             existing='12 proved one Mac ownership/return trial only.',
             remaining='A new sender must bind its own one-shot permit and current identity, not reuse grant12.'),
        dict(step=2, action='Complete the initial-MSC exchange and normal resource handoff',
             source='onComplete ea6b0 -> Acquire ea660 -> resource42 callback ea9b4 -> ea924 -> supervisor ea750 or resource semaphore post.',
             effect='START affects drivers/events; completing authentication can update service history and mode state.',
             digest_policy='Stage145 explicit MSC first4/reference versus SERVICE full512+round-material split is retained; no silent switch of MSC policy or claim of level3.'),
        dict(step=3, action='Account for initial NIN and bind the new service generation',
             source='Supervisor attempts NIN cancel/join at ea854/ea860, then starts service worker at ea884.',
             remaining='Native sender has no admitted fresh0336 binding/profile. Old MSC objects and endpoint assumptions must not be carried into a new generation.',
             observed_identity_is_not='Camera thread join success or authentication success.'),
        dict(step=4, action='If separately included, finish service exchange and make only the fixed capability read',
             existing='Stage253 fixes ProductInfo 001F arg0,17B request/max100B reply; arg80 reset is excluded.',
             remaining='Actual service descriptor/endpoint ownership, receiving path and private transient-HMAC handling are not integrated.',
             scope='A/B capability lower bound only, not level3, full backup or firmware identity.'),
        dict(step=5, action='Request normal service end once and record actual outcomes',
             source='Core internal event3 cd70 -> worker join attempts cd78 -> global end callback cd98 -> eac50 -> sem_post2ce0b8.',
             remaining='A returned STOP, STALL or internal notify does not expose aggregate join success; in-flight calls and partial effects need separate outcomes.',
             forbidden='No automatic START/STOP repeat, reset, force-kill or clearing local flags to claim device completion.'),
        dict(step=6, action='Return host ownership and inspect normal-camera state',
             source='Supervisor end wait ea8d8 -> service worker cancel/join ea3e0 -> resource Release ea71c -> state1 -> resource wait ea81c.',
             persistent_thread='The normal supervisor is intentionally long-lived until a separate shutdown state5.',
             evidence='Host calls returned, host helper exit, same-body MSC/driver return and user screen are individual observations. Camera session-thread completion stays unknown unless separately measured.')],
    result_dimensions={
        'exchange_finished':'A syntactically valid 6/1 only closes the observed exchange.',
        'capability_read':'A valid88B reply is a bounded capability observation under the stated stock-table assumptions.',
        'host_and_USB_return':'Actual host return/exit and reappearance are useful independent observations, not a per-thread camera receipt.',
        'camera_session_threads':'Specific NIN/service-worker completion needs separate evidence; reviewed callbacks have no per-trial status reply.',
        'normal_supervisor':'Still waiting can be normal and must not itself force a failure verdict.'},
    next_implementation_deliverables=[
        'Implement the host adapter across MSC0DA1 -> fresh SERVICE0336 -> returned MSC, with generation-specific ownership and actual descriptors; production iokit_wire currently refuses SERVICE mode.',
        'Connect the existing mode-specific digest provider and fixed read0 codec to that adapter, with explicit history/mode effects and immutable request limits.',
        'Build a fixed candidate and check normal transition plus every actual native failure boundary. Before any new launch, publish the complete program, digest, uncertainty handling and specific requested scope.'
    ],
    no_new_synthetic_replay_or_original_code_execution=True,
    new_live_package_ready=False, new_live_permission_requested=False,
    milestone2_complete=False, persistent_write_release=False)
put('full-lifecycle-contract.json', contract)

readme = '''# FX3 普通应用完整进入与结束路径

2026年10月31日。**完整资源交接和服务结束回调已绑定到原7.02函数；不再把正常常驻的监督线程误当作未退出。** 这是原文件静态结论，本轮未发送相机命令，尚未形成可执行的Sony诊断包。

## 本次解决的问题

普通应用完成回调会申请资源42，由资源回调创建或唤醒监督线程。监督线程尝试取消并等待初始NIN认证线程，然后启动服务工作线程。服务结束时，core内部事件3先尝试等待其工作线程，再调用注册的结束回调；该回调只向结束信号量发通知。监督线程醒来后，尝试回收服务工作线程、释放资源并回到等待。原函数、完整反汇编和6处重定位绑定见[原字节审查](handoff-and-end-audit.json)。

| 路径 | 原件定位 | 已确定的边界 |
|---|---|---|
| 完成与资源申请 | onComplete ea6b0 → Acquire ea660 | 不能以收到6/1证明资源申请或认证级别成功 |
| 资源回调与监督线程 | callback ea9b4 → ea924；start ea750 | 首次创建，之后发resource信号；创建返回未检查，started标志不是存活证据 |
| 初始认证线程回收 | ea854/ec458取消；ea860/ec4bc等待 | join包装器检查返回，上层未消费其成功/失败结果 |
| 服务结束通知 | core cd70 → cd78 → cd98 → Obj eac50 | 发生在等待尝试之后，不是逐线程成功回执；eac50只有sem_post，没有USB回复或试验编号 |
| 工作线程回收与正常等待 | ea8d8 → ea3e0 → ea71c → ea81c | 回收返回未检查；正常监督线程继续常驻，单凭它仍在不能判失败 |

两处sem_wait的返回同样未检查。推进到后续代码、内部结束通知和USB恢复，各自说明不同的事情，不能合并成“机内全部结束”。上述结论只覆盖已审查路径，没有声称相机不存在其它观察接口，也没有在真机制造或观察挂起。

## 下一次诊断如何落地

[完整生命周期执行合同](full-lifecycle-contract.json)把MSC绑定、初始交换、资源交接、新服务身份、可选固定读取、服务结束及归还分别列出。253的001F/read0候选保留，0x80重置分支仍排除；145的MSC与SERVICE摘要策略保持显式区分。不会继续推进缺少取消触发的“只取挑战”路线，也不重复已通过的12号接管试验。

目前具体缺的是**跨MSC 0DA1与新SERVICE 0336的原生发送适配及失败处理**：现有生产iokit_wire明确拒绝SERVICE模式，尚未接入真实服务描述符、端点和新一代所有权。下一批交付应是这个适配器的固定代码与构建，并接上既有摘要提供者和受限读取；需要把认证历史/模式影响写明，再提交具体试验范围。仅等待一份主机无法取得的逐线程回执，不能解决这个实现缺口；但也不能把未知改成已通过。

本次核对18个完整原函数、64处指令、6处重定位和10条路径连接；没有再跑同一组人工握手或原Sony/Linux指令。这些数量是审查范围，不是功能完成比例。

## 恢复能力仍需分开判断

Sony在[FX3通用故障排查](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000844060.html)中给出了取下电池、等待约一分钟后重新启动的处理办法。该说明可以支持一般故障处理，不能据此声称已经验证服务会话恢复、坏包回退或启动区救砖。本轮不要求用户断电或初始化设置，也不将仍在途的调用判为完成。[官方说明适用范围](official-restart-scope.json)。

另外，[6份原启动脚本核查](boot-script-scope.json)明确了/tmp来自nflasha10，/tmp_wbshd才单独挂为tmpfs；/setting/sen/smode的UU启动条件与认证尾部AA模式标记也不同。尚未在这组文件中解析出/ramdsk的实际运行时后端，所以不能仅凭目录名称把认证模式修改称为“仅RAM、断电必还原”。没有执行脚本、挂载镜像或触碰机身文件。

12号实际Mac接管归还通过、11号UNKNOWN及G01至G16保持。第2项真机入口仍进行中；同机完整备份、独立恢复、MAIN 1080p H.265与最小持久化准入尚未通过，首刷未放行。本轮没有新增设备、USB缓存、管理员、Sony认证或固件写入授权。[实施路线](../../../outputs/fx3-recovery-adapter/ROADMAP.md)。
'''
put('README.md', readme.encode())

goal_path = B / 'GOAL_STATUS.json'
goal_before = goal_path.read_bytes()
assert goal_before == (P / 'goal-status-after.json').read_bytes()
goal = json.loads(goal_before)
unchanged = {key: value for key, value in goal.items() if key not in {
    'updated_utc', 'latest_stage', 'research_activity', 'next_safe_offline_actions'}}
goal['updated_utc'] = now
goal['latest_stage'] = H.name
goal['research_activity'] = 'Offline bound18 original full functions/64words/6relocations/10edges for normal resource42 handoff, supervisor semaphore flow and service-end callback. NIN and service-worker joins are attempted but upper callers ignore status; core end callback is only an internal semaphore post without per-trial host receipt. Normal supervisor intentionally remains waiting; its presence alone is not exit failure. Six saved boot scripts distinguish flash /tmp, tmpfs /tmp_wbshd and UU startup flag; /ramdsk backing remains unresolved. Sony general restart guidance is not independent firmware rescue. Next deliverable is the actual native multi-identity sender, not another challenge-only model. No new live/guest operations;12pass/11UNKNOWN/all16/grants preserved.'
goal['recovery_normal_resource_handoff_and_end_callback'] = dict(
    readme=str((H / 'README.md').relative_to(R)),
    source_audit=str((H / 'handoff-and-end-audit.json').relative_to(R)),
    lifecycle_contract=str((H / 'full-lifecycle-contract.json').relative_to(R)),
    boot_script_scope=str((H / 'boot-script-scope.json').relative_to(R)),
    original_functions=18, instruction_checks=64, relocation_bindings=6,
    path_edges=10, long_lived_supervisor_distinguished=True,
    per_session_camera_thread_completion_proven=False,
    native_SERVICE_sender_integrated=False, new_live_operations=0,
    new_live_package_ready=False, milestone2_complete=False)
goal['next_safe_offline_actions'] = [
    '254已固定普通完成→资源42→监督线程→NIN取消/等待→服务工作线程→内部结束回调→资源释放/正常等待的原路径。监督线程正常常驻；本次NIN与服务工作线程完成、USB返回和握手结束分别记账，未知不转通过。',
    '下一项直接实现跨MSC0DA1→新SERVICE0336→返回MSC的原生主机适配器：绑定实际描述符/端点与各代所有权，处理完成STALL、消失、在途及返回失败；现有生产iokit_wire拒绝SERVICE，必须补代码，不再追加同一挑战/接管模型。',
    '将145显式模式摘要与253固定001F/read0编解码接入；是否包括受限读取须在固定方案中明确，禁止arg80重置。完整认证可能有历史/模式写入，/ramdsk后端未明，不称整个会话仅RAM或零写入。',
    '原生候选构建、调用范围及失败/归还处理固定后才提交新试验授权；12和其它单次许可不复用。官方一般重启不充独立救砖，G01至G16/备份/恢复/MAIN HEVC/持久化准入仍保持未通过。'
]
for key, value in unchanged.items():
    assert goal[key] == value, key
assert not goal['goal_complete'] and not goal['persistent_write_release']
goal_after = encoded(goal)

root_path = R / 'README.md'
root_before = root_path.read_bytes()
root_text = root_before.decode()
overview = next(line for line in root_text.splitlines() if line.startswith('- [FX3实施路线与当前进度]'))
assert H.name not in root_text
entry = '- [2026-10-31 FX3普通应用资源交接与服务结束](<work/sony-firmware-20261024/stage254-normal-resource-handoff-and-end-callback/README.md>)：完整原路径已接通到资源42、两条信号量和结束回调；区分常驻监督线程与本次认证/服务线程。回调不提供逐线程主机回执，下一项落实跨MSC/SERVICE原生发送器；无新设备操作。'
root_after = root_text.replace(overview, overview + '\n\n' + entry, 1).encode()

roadmap_path = R / 'outputs/fx3-recovery-adapter/ROADMAP.md'
roadmap_before = roadmap_path.read_bytes()
roadmap_text = roadmap_before.decode()
assert '最新研究证据为第253阶段。' in roadmap_text
roadmap_text = roadmap_text.replace('最新研究证据为第253阶段。', '最新研究证据为第254阶段。', 1)
start = roadmap_text.index('最新进展：')
end = roadmap_text.index('\n\n下面8项', start)
roadmap_text = roadmap_text[:start] + '最新进展：12号实机Mac接管归还子步骤通过，原始私有回执、程序退出、独立MSC缓存及用户屏幕均完成；11号UNKNOWN保留。[实际结果](../../work/sony-firmware-20261024/stage251-authorized-owner-status12/README.md)。随后已固定受限88B读取候选，并将普通应用完整资源交接、两条信号量及结束回调接到原函数。正常监督线程会常驻；本次认证/服务线程的等待返回未被上层完整检查，不能用USB返回代替。下一项具体缺口是跨MSC0DA1与新SERVICE0336的原生发送与归还适配，尚无可执行Sony诊断包。[最新完整路径与执行边界](../../work/sony-firmware-20261024/stage254-normal-resource-handoff-and-end-callback/README.md)。' + roadmap_text[end:]
start = roadmap_text.index('Mac接管归还子步骤已由251实测关闭。', roadmap_text.index('## 下一批工作的交付边界'))
end = roadmap_text.index('\n\n这一批应交付', start)
roadmap_text = roadmap_text[:start] + 'Mac接管归还子步骤已由251实测关闭，不重复。254已落实完整资源交接/服务结束的静态来源，并区分常驻监督线程和本次线程；不再停留于同一挑战模型。下一批直接实现跨MSC0DA1→新SERVICE0336→返回MSC的原生适配器，接上145显式模式摘要和253固定read0编解码，固定实际端点/所有权、在途与部分副作用处理、具体权限和停止范围。完整方案就绪前不发送Sony命令。内部通知、协议成功、USB返回和机内线程完成分别记录，不降低G01至G16；一般重启不代替独立救砖。' + roadmap_text[end:]
roadmap_after = roadmap_text.encode()

for name, raw in [
    ('goal-status-before.json', goal_before), ('goal-status-after.json', goal_after),
    ('root-readme-before.md', root_before), ('root-readme-after.md', root_after),
    ('roadmap-before.md', roadmap_before), ('roadmap-after.md', roadmap_after)]:
    put(name, raw)
assert goal_path.read_bytes() == goal_before
assert root_path.read_bytes() == root_before and roadmap_path.read_bytes() == roadmap_before
goal_path.write_bytes(goal_after)
root_path.write_bytes(root_after)
roadmap_path.write_bytes(roadmap_after)

receipt = dict(
    created_utc=now, status='OFFLINE_NORMAL_LIFECYCLE_BOUND_NATIVE_SENDER_REMAINS_UNIMPLEMENTED',
    previous_manifest_sha256=sha256(previous_raw).hexdigest(), previous_members_reverified=23,
    whole_original_functions=18, checked_instruction_words=64,
    relocation_bindings=6, path_edges=10, saved_boot_scripts=6,
    new_original_Sony_Linux_or_guest_instruction_execution=False,
    new_camera_USB_cache_admin_authentication_or_firmware_operations=0,
    normal_supervisor_lifetime_distinguished=True,
    session_thread_completion_proven=False,
    host12_pass_preserved=True, old11_unknown_preserved=True,
    all_previous_goal_fields_except_summary_and_next_actions_unchanged=True,
    all16_and_authorizations_unchanged=True,
    new_live_package_ready=False, new_live_scope_requested=False,
    milestone2_complete=False, goal_complete=False, persistent_write_release=False,
    heads_sha256=dict(goal=sha256(goal_after).hexdigest(),
                      root_readme=sha256(root_after).hexdigest(),
                      roadmap=sha256(roadmap_after).hexdigest()))
put('verification-receipt.json', receipt)
members = []
for path in sorted(H.rglob('*')):
    if path.is_file():
        raw = path.read_bytes()
        members.append(dict(path=str(path.relative_to(R)), bytes=len(raw), sha256=sha256(raw).hexdigest()))
put('final-receipt.json', dict(schema='fx3-stage254-normal-resource-lifecycle-v1',
                             member_count=len(members), files=members, **receipt))
print(json.dumps(dict(status=receipt['status'], members=len(members),
                      manifest_sha256=sha256((H / 'final-receipt.json').read_bytes()).hexdigest(),
                      live_operations=0)))
