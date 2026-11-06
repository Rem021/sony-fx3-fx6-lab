"""Seal completed offline work. No rebuild, fixture replay or USB query."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import difflib, json, os, plistlib, subprocess

H=Path(__file__).resolve().parent; B=H.parent; R=B.parents[1]
P=B/'stage256-root-service-flow-and-private-receipts'
assert not (H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def encode(x): return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
    data=x if isinstance(x,bytes) else encode(x)
    fd=os.open(H/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f: f.write(data)
previous=(P/'final-receipt.json').read_bytes()
assert sha256(previous).hexdigest()=='0de9662ae2bb90a1649f90a3ef9c8fb553814577286844a9317fa647103e41e0'
for m in json.loads(previous)['files']:
    data=(R/m['path']).read_bytes()
    assert len(data)==m['bytes'] and sha256(data).hexdigest()==m['sha256'],m['path']
build=json.loads((H/'build-receipt.json').read_text())
for m in build['sources']: assert sha256((H/m['path']).read_bytes()).hexdigest()==m['sha256']
for m in build['builds'].values(): assert sha256(Path(m['path']).read_bytes()).hexdigest()==m['sha256']
tests=json.loads((H/'discovery-test-receipt.json').read_text())
assert tests['checks']==5 and all(m['status']=='PASS' for m in tests['rows'])
analysis=json.loads((H/'analysis-receipt.json').read_text()); assert analysis['diagnostics']==0
changes=[]
for m in json.loads((H/'source-copy-receipt.json').read_text())['files']:
    old=(R/m['source']).read_bytes(); assert sha256(old).hexdigest()==m['sha256']
    new=(H/m['destination']).read_bytes()
    if old!=new:
        changes.extend(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),m['source'],H.name+'/'+m['destination']))
put('source-changes.diff',''.join(changes).encode())
decision=dict(status='SERVICE_DISCOVERY_AND_CONTROL_ONLY_EXIT_IMPLEMENTED_OFFLINE',
    native_helper_sha256=build['builds']['native']['sha256'],actual_root_or_IOKit_execution=False,
    descriptor_policy='single active config; one vendor interface alt0; two or four unique bulk endpoints; packet512; raw config max128B; primary first IN/OUT in descriptor order',
    mismatch_branch='no SERVICE START, authentication or read; one experimental control STOP then observe fresh MSC',
    mismatch_exit_proven_on_camera=False,fixture_checks=5,analyzer_units=6,
    scope='schema5 SVC3 FX3FLOW2 FX3RCPT3; old status grants not reused',
    live_entry_released=False,new_fixed_live_package_ready=False,
    cached_camera_online=True,cached_camera_mounted_volume_count=1,
    real_Sony_authentication_or_mode_commands=0,milestone2_complete=False,
    persistent_write_release=False,global_camera_state_remains_UNKNOWN=True)
put('admission-decision.json',decision)
put('README.md','''# FX3 SERVICE描述符识别与控制退出分支

2026年10月31日。补齐了上一阶段的SERVICE配置发现与不匹配分支，原生候选编译和五组有针对性的离线检查完成；没有运行管理员程序或实际USB后端，没有发送Sony命令。

[描述符策略](descriptor_policy.c)只支持单配置、单个vendor接口、alt0、2或4个唯一bulk端点及512B包长。最多保存128B配置；从实际描述符顺序选择首个IN/OUT，再核对IOKit接口和管道，未填写猜测端点，未改配置或alternate setting。

[原生发现](iokit_adapter.c)先核对新SERVICE节点的同机HMAC标签，再访问设备对象。符合策略才继续固定通信；不匹配时不发送SERVICE START、认证或读取，改走一次独立控制STOP，然后观察MSC。API失败或超时保留UNKNOWN，不以策略不匹配掩盖调用错误。[控制退出原码检查](control-exit-source-review.json)只支持将其列为试验候选：没有证明真机在未START时一定可退出，也没有证明线程完成或能救砖。

[验证回执](discovery-test-receipt.json)覆盖原生解析器的截断与变异、匹配分支、不匹配分支、SERVICE失败及认证中途停止。完整人工分支收到80帧，不匹配分支44帧且没有SERVICE认证/读取；失败保留原实例。实际运行的是普通用户自写子进程和人工USB回调，不能充作相机模拟成功。[静态检查](analysis-receipt.json)六个单元无诊断。新协议为schema5/SVC3、FX3FLOW2和FX3RCPT3；原12号授权未复用。

[Mac缓存](current-host-storage-cache.json)曾看到经典FX3在0x01100000、MSC驱动和一个挂载卷。查询只读系统缓存与挂载表，没有打开设备或媒体；缓存有时效性，不是新鲜上机前置，也不证明机身健康。没有推出卷。

下一步是固定新目标、nonce、隐私材料和单次许可，形成完整Sony通信诊断包。目前native入口与渲染仍关闭。用户新增“持续研究，不要停止，我全部同意”的整体继续授权已记录；不复用任何消耗过的单次许可。首次诊断应明示认证可能更新历史、模式及机内文件，不能称为零写入或单纯USB查询。固件写入仍未放行。

真实SERVICE端点、跨模式身份连续性、认证接受、机内线程退出与恢复仍未验证。完整同机备份、独立恢复、MAIN1080p H.265及持久化准入也未完成。全部G01至G16保持，[实施路线](../../../outputs/fx3-recovery-adapter/ROADMAP.md)仍处于第2项。

[差异](source-changes.diff) · [构建](build-receipt.json) · [准入结论](admission-decision.json)。公开参考为[固定PMCA维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L890)与[Apple IOUSBLib](https://github.com/apple-oss-distributions/IOUSBFamily/blob/main/IOUSBFamily/Headers/IOUSBLib.h)。公开实现不等于FX3 7.02实机兼容。
'''.encode())
gp=B/'GOAL_STATUS.json'; gb=gp.read_bytes(); assert gb==(P/'goal-status-after.json').read_bytes()
g=json.loads(gb); req=g['requirements']; assert len(req)==16
now=datetime.now(timezone.utc).isoformat()
g.update(updated_utc=now,latest_stage=H.name,
 research_activity='SERVICE bounded descriptor discovery, real pipe validation and separate experimental control-only STOP branch implemented. Five completed offline checks and six static analyses pass. No actual root/IOKit/Sony commands; cached camera observed mounted. Next fixed live diagnostic package, not additional equivalent fixture tests.')
g['current_continuation_context']=dict(user_quote='持续研究，不要停止，我全部同意',native_goal_status='active',
    objective='持续研究，不要停止，我全部同意',source='explicit user goal and current native goal readback',
    previous_goal_turn_classification='progress',current_goal_turn_classification='progress',
    new_general_research_authorization=True,old_single_use_grants_reactivated=False,
    historical_goal_cleared_records_preserved=True,firmware_write_release=False,
    system_native_authentication_by_user_only=True,Windows_deferred=True)
g['recovery_service_descriptor_control_exit']=dict(readme=str((H/'README.md').relative_to(R)),
    decision=str((H/'admission-decision.json').relative_to(R)),build=str((H/'build-receipt.json').relative_to(R)),
    tests=str((H/'discovery-test-receipt.json').relative_to(R)),**decision)
g['next_safe_offline_actions']=[
    'SERVICE发现和不匹配控制退出的实现与有针对性的离线验证已完成，不重复同一测试。制作新的固定真机通信诊断包，核对身份连续性和分支的实机退出风险。',
    '用户整体继续授权保留；新构建使用独立grant/nonce/许可和当前缓存节点，不复用12号等已消耗单次许可。准备实际范围、失败处置和主机管理员启动。',
    '任何实际接管前重新验证唯一同机节点、原端口和相机卷全部推出；当前缓存曾有一个挂载卷，不据此直接启动。',
    'Sony认证可能改变历史/模式/机内文件；不充零写入、RAM功能或安全恢复。G01至G16及MAIN目标不变，首刷仍需完整备份、独立恢复和功能验证。']
assert g['requirements']==req and not g['goal_complete'] and not g['persistent_write_release']
ga=encode(g)
rp=R/'README.md';rb=rp.read_bytes();rt=rb.decode();entry='- [2026-10-31 FX3 SERVICE描述符识别与控制退出分支](<work/sony-firmware-20261024/stage257-service-descriptor-discovery-and-control-exit/README.md>)：配置发现、管道核对和不匹配时仅控制退出已实现；五组离线检查通过，真机退出仍待验证。缓存曾见相机在线且一卷挂载；下一步制作固定Sony通信诊断包，未发送相机命令。'
anchor=next(x for x in rt.splitlines() if x.startswith('- [FX3实施路线与当前进度]'))
assert H.name not in rt;ra=rt.replace(anchor,anchor+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();mt=mb.decode()
assert '最新研究证据为第256阶段。' in mt;mt=mt.replace('最新研究证据为第256阶段。','最新研究证据为第257阶段。',1)
a=mt.index('最新进展：');z=mt.index('\n\n下面8项',a)
mt=mt[:a]+'最新进展：12号实机Mac接管归还子步骤通过，11号UNKNOWN保留。257已实现SERVICE有界描述符发现、真实管道核对及不匹配时独立控制退出；五组普通用户自写子进程/人工管道检查及六单元静态检查通过。未运行实际root/IOKit或Sony通信，不匹配退出仍是未实测候选。下一步固定新的完整诊断包；缓存曾见相机在线且一卷挂载，不能直接接管。[最新代码和证据](../../work/sony-firmware-20261024/stage257-service-descriptor-discovery-and-control-exit/README.md)。'+mt[z:]
a=mt.index('Mac接管归还子步骤已由251实测关闭',mt.index('## 下一批工作的交付边界'));z=mt.index('\n\n这一批应交付',a)
mt=mt[:a]+'Mac接管归还子步骤已由251实测关闭，不重复。257补齐SERVICE描述符发现、管道核对和不匹配控制退出的代码及限定离线检查，真实SERVICE身份/配置与退出仍待验证。下一批固定新鲜目标、nonce、隐私材料和单次许可，形成实际通信诊断包。用户新增整体继续授权已保留，不复用旧单次许可；管理员验证由用户完成。上机前必须确认相机全部卷已推出。认证可能更新历史/模式/机内文件，限定88B读取与退出也需写进方案，不能称为零写入。主机USB返回与机内线程完成仍分别判断。'+mt[z:]
ma=mt.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]: put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,previous_manifest_sha256=sha256(previous).hexdigest(),previous_members_reverified=566,
    native_sha256=build['builds']['native']['sha256'],completed_offline_checks=5,analyzer_diagnostics=0,
    requirements_preserved=16,real_root_or_USB_interface_or_Sony_commands=0,cache_queries_only=True,
    new_live_package_ready=False,goal_complete=False,persistent_write_release=False,
    heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
members=[]
for p in sorted(H.rglob('*')):
    if p.is_file():
        data=p.read_bytes();members.append(dict(path=str(p.relative_to(R)),bytes=len(data),sha256=sha256(data).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage257-descriptor-control-exit-v1',member_count=len(members),files=members,**receipt))
print(json.dumps(dict(status='SEALED_NO_REPLAY',members=len(members),manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest())))
