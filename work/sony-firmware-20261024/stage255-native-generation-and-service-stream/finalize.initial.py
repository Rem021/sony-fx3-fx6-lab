"""Seal the compiled native component; does not stage or run camera code."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
P=B/'stage254-normal-resource-handoff-and-end-callback'
assert not(H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
    raw=x if isinstance(x,bytes)else enc(x)
    fd=os.open(H/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb')as f:f.write(raw)
previous=(P/'final-receipt.json').read_bytes()
assert sha256(previous).hexdigest()=='c47dcc0c495f0b948ce735f061e15ff8734d3c457fa9043ae4c17ad559ca6384'
for x in json.loads(previous)['files']:
    raw=(R/x['path']).read_bytes();assert len(raw)==x['bytes'] and sha256(raw).hexdigest()==x['sha256'],x['path']
build=json.loads((H/'final-build-receipt.json').read_text())
unit=json.loads((H/'unit-receipt-v5.json').read_text())
assert unit['returncode']==0 and 'PASS 9 native component checks' in unit['stdout']
assert build['analyzer_diagnostics']==0 and not build['native_library_executed']
for name,digest in build['source_hashes'].items():assert sha256((H/name).read_bytes()).hexdigest()==digest,name
assert sha256(Path(build['native_path']).read_bytes()).hexdigest()==build['native_sha256']
for name in ['stream-analysis.plist','iokit_adapter-analysis-final.plist']:
    assert plistlib.loads((H/name).read_bytes())['diagnostics']==[]
source=json.loads((H/'source-review.json').read_text())
assert source['native_SERVICE_profile_default'] is None
now=datetime.now(timezone.utc).isoformat()
decision=dict(status='NATIVE_COMPONENT_IMPLEMENTED_BUILT_NOT_COMPLETE_APPROVED_LIVE_PROGRAM',
    native_backend_implemented=True,mode_specific_native_digest_integrated=True,
    SERVICE_read_shape='17B fixed request;12B header then exactly88B body by positive progress',
    no_default_SERVICE_endpoint_profile=True,
    root_owner_and_IPC_lifecycle_integration_complete=False,
    real_SERVICE_profile_or_cross_mode_serial_continuity_verified=False,
    explicit_ReleaseDeviceMask_request_implemented_not_executed=True,
    per_call_results_must_be_archived_before_next_step_or_disposal=True,
    next_deliverables=[
        'Connect the fixed root owner/peer/one-shot permit and phase receipts to the new native adapter. Transfer the initial650 objects exactly once, replace stale outer cleanup, and save communication/cleanup raw results before later calls overwrite last_call.',
        'Fix SERVICE descriptor discovery/validation and mismatch-to-control-exit behavior in that complete program; no hard-coded fixture profile or port-only fallback. Then build/seal a new concrete trial package with explicit authentication/history/mode and optional.hasp read effects.'
    ],
    approved_or_deployable=False,new_camera_operations=0,milestone2_complete=False,
    full_backup_or_independent_restore_or_MAIN_HEVC_proven=False,persistent_write_release=False)
put('integration-decision.json',decision)

readme='''# FX3 原生跨代通信与SERVICE分段接收

2026年10月31日。**原生适配器组件、分模式摘要和受限读取已经写成C并编译；目前仍是待整合的组件，没有运行相机后端。** 这是对254“补原生发送器”的实际代码推进，不是再增加同一握手模型。

## 已实现的代码

| 组件 | 当前实现 | 限定 |
|---|---|---|
| [stream.c](stream.c) / [接口](stream.h) | MSC→新SERVICE→新MSC的代次与同机缓存标签绑定，拒绝旧节点/旧句柄和错误端口；原生固定七次交换 | 标签来自缓存串号HMAC，是一致性检查，不是固件真实性证明；实际跨模式串号连续性未验 |
| 分模式摘要 | MSC按公开参考取挑战前4字节，族2用SHA-1、族8用SHA-256；SERVICE族8取完整512B加该轮512B材料 | 与145策略保持一致；观察到6/1只记exchange_finished，不证明最高权限 |
| 固定read0 | 只发送ProductInfo001F参数0的17B请求；核对12B头，再接收合计88B数据，只返回长度和临时HMAC并清理局部载荷 | API不提供0x80重置参数或任意文件/固件请求；依旧只说明受限能力，非完整备份 |
| [iokit_adapter.c](iokit_adapter.c) / [接口](iokit_adapter.h) | 接收原接管端已经打开的MSC650对象，清空原指针避免重复关闭；新SERVICE对象重新查身份、开接口、核对实际管道 | 没有默认0336端点表，必须由完整固定方案提供经审查的配置；初始MSC不经此组件另行抢占 |
| 结束与归还 | 控制请求仅固定START/STOP；I/O与对象释放共用锁。未返回调用保持UNKNOWN，释放失败不重试；新MSC可显式申请一次SDK ReleaseDeviceMask | 没有Reset、备用模式或自动重试。归还API返回、驱动重新绑定和机身线程收尾是不同结果 |

SERVICE接收顺序按[PMCA固定维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L847)处理：先读包头，再按长度读数据。253的100B是完整逻辑帧，不能直接当作一次USB接收要求。本组件检查包头后才读88B内容，允许有正进度的部分读取，零进度即停止；没有把返回长度当成可无界分配的大小。[来源与SDK规则核对](source-review.json)。

## 已完成的验证

最终[原生构建回执](final-build-receipt.json)固定动态库SHA256为af72a8a714e4206b2b8c66c41b2cf67202b7a82ca2d00e50efea30731ab974ce。构建使用-Wall/-Wextra/-Werror；stream与IOKit适配器最终静态分析均无诊断。实际I/O动态库没有加载或调用。

[9项原生C检查](unit-receipt-v5.json)使用AddressSanitizer和UndefinedBehaviorSanitizer，测试二进制不链接IOKit。覆盖正常跨代流程、错误身份/旧句柄、12B头与分段88B体、错误/短包头、零进度、不允许在忙碌或未返回调用期间释放、时限、释放失败不重试、认证STALL不重放，以及原生摘要与固定Python参考一致。全部采用人工管道回调；不把这些测试称为USB硬件、认证接受或线程结束证明。

最初构建缺少CoreFoundation声明，已补齐；静态分析发现的一处无效赋值已移除，原失败记录和中间构建保留。最终只重编受影响的原生后端，9项检查链接的源码未变，因此没有重复运行同一套检查。[构建脚本](final_build.py)记录了该对应关系。公开常量以AST字面量读取，附[MIT许可](upstream-LICENSE.txt)，没有执行下载的相机代码或原Sony/Linux指令。

## 距离下一次真机通信还差什么

1. **整合完整root程序。** 当前250接管端仍是原来的状态范围，尚未链接本组件。需要把单次许可、同进程对象转交、主机IPC、每步原始回执与跨代清理一起接入；不能把新组件直接塞进旧的12号程序，也不能让原清理逻辑再使用已经转交的旧对象。组件的last_call会被下一调用更新，固定程序须先保存每次通信和清理结果。
2. **固定SERVICE配置与失败退出。** 真实0336接口、端点/包长及串号连续性尚未观测；现有假管道不是默认配置。完整程序需要明确怎样在匹配的新节点获取/核对描述符，配置不符时怎样停止数据发送并处理控制端退出，再固定新构建和具体申请范围。

这两项整合完成后提交的是“首次Sony通信诊断方案”，不是首次持久刷写。认证可能更新.hasp、历史或模式状态；若包含本次88B读取，它也属于机身服务文件读取，不能沿用“不读机身文件”的旧授权。/ramdsk后端仍未确认，整个会话不称只读或仅RAM。现在没有生成授权包、暂存管理员程序、打开Terminal、读取USB缓存或触碰相机。[机器可读整合结论](integration-decision.json)。

12号实际Mac接管归还通过、11号UNKNOWN和G01至G16保持；第2项仍进行中。完整同机备份、独立恢复、MAIN1080p H.265与最小持久化仍未通过，首刷未放行。[实施路线](../../../outputs/fx3-recovery-adapter/ROADMAP.md)。
'''
put('README.md',readme.encode())
gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();assert gb==(P/'goal-status-after.json').read_bytes()
g=json.loads(gb);assert len(g['requirements'])==16
untouched={k:x for k,x in g.items()if k not in ['updated_utc','latest_stage','research_activity','next_safe_offline_actions']}
g['updated_utc']=now;g['latest_stage']=H.name
g['research_activity']='Implemented and compiled own native C transition/stream component with actual IOKit650 SERVICE open/identity/profile/pipe operations, initial MSC object transfer, fixed mode-specific7-exchange digest,17B read0 and12B header+88B positive-progress body receive/HMAC, synchronized one-shot disposal and explicit fresh-MSC ReleaseDeviceMask request. Sanitized9 own C checks pass with synthetic callbacks; native linked backend never executed. Final analyzers0diagnostics. No defaultSERVICE profile or live root/IPC integration; unchanged250status helper not replaced. Next integrate fixed root lifecycle and SERVICE discovery/mismatch exit. All16/grants/12pass/11UNKNOWN retained; no device/cache/admin/Sony guest operations.'
g['recovery_native_generation_service_stream']=dict(
    readme=str((H/'README.md').relative_to(R)),
    stream=str((H/'stream.c').relative_to(R)),native_backend=str((H/'iokit_adapter.c').relative_to(R)),
    build=str((H/'final-build-receipt.json').relative_to(R)),tests=str((H/'unit-receipt-v5.json').relative_to(R)),
    decision=str((H/'integration-decision.json').relative_to(R)),
    native_sha256=build['native_sha256'],own_native_checks=9,final_analyzer_diagnostics=0,
    native_component_implemented=True,native_library_executed=False,
    SERVICE_profile_or_serial_continuity_observed=False,root_IPC_integration_complete=False,
    new_live_package_ready=False,new_device_operations=0,milestone2_complete=False)
g['next_safe_offline_actions']=[
    '255实际写成并编译原生跨代/服务I/O组件，分模式原生摘要已接固定七次交换，read0按12B头+88B体接收。9项自写C/人工管道检查与最终静态分析通过，真实IOKit后端未运行，不重复同一挑战/接管模型。',
    '下一项把完整固定root接管程序接到255组件：单次许可、初始650对象仅转交一次、跨代清理/驱动归还、主机IPC与逐调用原始回执一起整合；不得沿用250状态命令白名单或旧清理对象，不得复用12等消耗授权。',
    '固定新SERVICE节点的描述符获取/配置核对与不匹配时的控制退出分支；没有默认0336端点/串号连续性假设，不把人工83/04等夹具当真机配置。完整方案明确认证可能写历史/模式及可选.hasp88B读取，然后生成新的具体试验包。',
    '新固定程序与构建/失败处理齐全后才提交新范围。协议结束、能力读取、USB/驱动返回及机内线程完成分开记录；G01至G16、完整备份/独立恢复/MAIN HEVC/持久化准入不降低，首刷不放行。'
]
for k,x in untouched.items():assert g[k]==x,k
assert not g['goal_complete'] and not g['persistent_write_release'];ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();text=rb.decode();overview=next(x for x in text.splitlines()if x.startswith('- [FX3实施路线与当前进度]'))
assert H.name not in text
entry='- [2026-10-31 FX3原生跨代通信与SERVICE分段接收](<work/sony-firmware-20261024/stage255-native-generation-and-service-stream/README.md>)：原生IOKit组件、两模式摘要/固定交换、12B头+88B受限接收和显式归还请求已写成并编译；9项自写C人工管道检查、最终静态分析通过。尚缺完整root/IPC与真实SERVICE配置整合，无设备操作。'
ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();text=mb.decode();assert '最新研究证据为第254阶段。'in text
text=text.replace('最新研究证据为第254阶段。','最新研究证据为第255阶段。',1)
start=text.index('最新进展：');end=text.index('\n\n下面8项',start)
text=text[:start]+'最新进展：12号实机Mac接管归还子步骤通过，原始私有回执、程序退出、独立MSC缓存及用户屏幕均完成；11号UNKNOWN保留。[实际结果](../../work/sony-firmware-20261024/stage251-authorized-owner-status12/README.md)。255已将跨MSC/SERVICE的原生通信组件、两种模式的摘要、受限读取与归还请求写成C并编译，9项自写C检查和最终静态分析通过。IOKit后端未运行；完整root/IPC整合、真实SERVICE配置与失败退出固定方案仍待完成。[最新代码与剩余整合](../../work/sony-firmware-20261024/stage255-native-generation-and-service-stream/README.md)。'+text[end:]
start=text.index('Mac接管归还子步骤已由251实测关闭。',text.index('## 下一批工作的交付边界'));end=text.index('\n\n这一批应交付',start)
text=text[:start]+'Mac接管归还子步骤已由251实测关闭，不重复。255已实际完成原生组件及限定离线验证。下一批把完整固定root接管/单次许可/IPC/逐调用回执和跨代清理接到该组件，再固定新SERVICE描述符核对与不匹配时的控制退出；生产组件没有默认SERVICE配置。整合时必须保存每次结果再推进，不让原状态helper重复清理已转交对象。完整新方案齐全前不发送Sony命令，不复用旧授权；认证/历史/模式影响与可选88B机身文件读取需在新范围中明示。'+text[end:]
ma=text.encode()
for name,raw in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,raw)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,status='NATIVE_COMPONENT_BUILT_AND_OWN_UNIT9_PASS_NOT_LIVE_READY',
    previous_manifest_sha256=sha256(previous).hexdigest(),previous_members_reverified=14,
    own_native_component_checks=9,sanitizers='address,undefined',final_analyzer_diagnostics=0,
    native_library_sha256=build['native_sha256'],native_IOKit_library_executed=False,
    new_Sony_Linux_or_guest_code_executed=False,new_device_cache_admin_or_USB_operations=0,
    mode_specific_digest_and_fixed_read0_integrated_in_C=True,
    root_IPC_and_real_SERVICE_profile_integration_complete=False,
    last_call_must_be_saved_before_later_call=True,
    old12_pass_and_11_UNKNOWN_preserved=True,all16_and_authorizations_unchanged=True,
    live_package_ready=False,milestone2_complete=False,goal_complete=False,persistent_write_release=False,
    heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
members=[]
for path in sorted(H.rglob('*')):
    if path.is_file():
        raw=path.read_bytes();members.append(dict(path=str(path.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage255-native-generation-service-stream-v1',member_count=len(members),files=members,**receipt))
print(json.dumps(dict(status=receipt['status'],members=len(members),manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),native_executed=False)))
