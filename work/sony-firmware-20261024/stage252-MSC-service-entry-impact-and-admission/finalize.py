"""Seal phase evidence and parser preparation; no native/camera execution."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,plistlib,subprocess

H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage251-authorized-owner-status12'
assert not (H/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
 raw=x if isinstance(x,bytes)else enc(x)
 fd=os.open(H/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb')as f:f.write(raw)
previous=json.loads((P/'final-receipt.json').read_text())
for x in previous['files']:
 raw=(R/x['path']).read_bytes();assert len(raw)==x['bytes'] and sha256(raw).hexdigest()==x['sha256'],x['path']
audit=json.loads((H/'phase-impact-audit.json').read_text());test=json.loads((H/'auth-observation-test-receipt.json').read_text())
assert audit['checked_instructions']==39 and len(audit['functions'])==4
assert test['status']=='PASS_ARCHIVED_COUNTEREXAMPLE_CLASSIFICATION' and test['archived_cases']==5 and test['malformed_transcript_rejections']==6
public=json.loads((H/'public-source-receipt.json').read_text());follow=json.loads((H/'public-api-followup.json').read_text())
success=[x for s in public['sources']for x in s['files']if 'error'not in x]+[x for x in follow['files']if 'error'not in x]
for x in success:
 raw=(H/x['local']).read_bytes();assert sha256(raw).hexdigest()==x['sha256'] and len(raw)==x['bytes']
pmca=H/'public/ma1co--Sony-PMCA-RE/pmca__usb__sony.py';old=B/'stage134-backup-reader-scope-and-service-extension/upstream/sony.py'
assert pmca.read_bytes()==old.read_bytes()
put('public-reconciliation.json',dict(downloaded_successes=len(success),heads=[dict(repository=s['repository'],commit=s.get('commit'),date=s.get('commit_date'))for s in public['sources']],PMCA_sony_source_matches_previously_fixed_bytes=True,QAQ_README_followup_failed_and_not_treated_as_source_change=True,first_network_failures_preserved=True,downloaded_code_executed=False))
decision=dict(status='SONY_CHALLENGE_PROBE_NOT_RELEASED_EXIT_PROOF_INCOMPLETE',host_ownership_prerequisite_passed=True,
 current_fixed_live_package_supports_only=['OBSERVE','STATUS','END'],new_live_package_prepared=False,new_live_authorization=False,
 ordinary_cmd1_path_avoids_completion_branch=True,no_persistent_effect_guarantee=False,
 commands5_and7_share_completion_branch=True,protocol_completion_alone_not_authentication=True,
 transfer_error_may_enter_camera_cancellation_wait_loop=True,STOP_or_MSC_query_alone_not_thread_exit_proof=True,
 needed_next=['Bind initial MSC receiver and service identity separately; retain existing145 mode-digest calculator rather than rewrite it.',
 'Locate an actually read-only command whose availability distinguishes the relevant service authorization level; protocol6/1 or ordinary ProductInfo alone is not assumed sufficient.',
 'Trace STOP to underlying receive callback unblocking and a host-observable completion condition; do not clear local started flags merely because STOP returned.'],
 new_USB_cache_admin_auth_upload_or_firmware_operations=0,old251_pass_not_revoked=True,old11_unknown_preserved=True,first_flash_released=False)
put('admission-decision.json',decision)
readme='''# FX3 Sony通信入口：阶段影响与退出准入

2026年10月31日。**12号Mac接管/归还实测仍通过；本轮没有新增真机验收。** 已补一份通信阶段影响清单和离线结果判定代码。Sony认证/挑战试验尚未形成可执行的完整退出方案，本轮不申请上机，也不把4次传输称为零副作用。

## 新增的原件核对

[静态审查器](audit_phase_effects.py)核对4个完整FX3 7.02原函数、39处指令和7项原跳表。原库SHA256为a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410；只解析文件，没有执行原指令。

1. 逻辑命令1进入挑战分支0xbce8；命令5和7都进入完成分支0xbe28。今后的“只取挑战”发送端必须是明确的命令1白名单，不能仅写成“不发命令5”。正常挑战分支没有直接跳到完成尾部，但这不排除其它线程或异常停止的影响。
2. Serialize在回调返回-6/-4、其它负值、零或超出剩余长度时，不是返回一个普通错误供NIN处理，而是进入pthread_testcancel/sched_yield循环。-6/-4分支先经0xb19c尝试释放属于当前线程的两项互斥锁；该helper不是关闭USB或恢复模式。正的短进度会继续累计至请求长度，函数自身没有截止时间。实际底层回调是否阻塞、如何被STOP解阻塞仍未证明。
3. 完成回复Serialize在0xbe6c；之后才是Hasp回调0xbea4、完成回调0xbf2c、条件日志更新0xbf4c和后续模式文件分支。已保存的136/149证据说明，最终6/1回复既不能证明摘要被接受，也早于后续条件写入与线程结束。

完整函数、原字与分阶段清单见[phase-impact-audit.json](phase-impact-audit.json)。初始审查将0xb19c暂称transport-state helper，完整FDE和pthread_self/mutex_unlock核对后改为条件互斥锁释放helper；初始代码/输出保留，未把它误列为实际USB清理。

## 本轮实际写出的代码

[auth_observation.py](auth_observation.py)是未来主机报告可复用的纯CPU判定器，没有USB、管理员或程序启动入口。它区分单次挑战、部分交换和交换结束；只凭返回码/最终字节，始终保留authentication、mode transition和camera thread exit为未验证。

[回归检查](test_auth_observation.py)直接消费149已保存的5组原函数CPU夹具记录，不重跑guest：正确摘要和错误摘要都曾得到8/4/8/4/8/4/6、最终字节1，现在均只标记EXCHANGE_FINISHED_AUTHENTICATION_UNVERIFIED。另检查3种合成帧格式场景、拒绝6种畸形或不一致输入。此代码尚未接入任何获准的原生发送包，不构成认证成功证据。

## 为什么仍不启动挑战试验

START/STOP已有原证据表明会影响驱动/异步队列；单次挑战避免了正常认证完成分支，却没有补上STOP后的接收解阻塞、取消等待及线程终止证据。现有250原生channel本来就只放行本机OBSERVE/STATUS/END；若曾发START，local started/start_sent未解除时会保留所有者。不能为让程序退出而擅自清这两个标志。

本轮也审查了GET_MAX_LUN一类标准MSC查询作为退出凭据的想法。Sony官方Ver700参考类请求分派按配置/接口调用类回调，不带NIN线程结束记录。它可作为接口就绪的辅助信息，不能单独证明Sony服务线程已结束；这里没有把Ver700源码当作精确7.02实机测量，也没有发送该查询。

下一步明确到两件事：在现有模式摘要工具基础上，绑定初始MSC与0336服务两段的实际处理者，寻找真正只读且受认证级别限制的验证指令；继续追STOP到底层接收回调的解阻塞及主机可观察完成条件。若没有这两项，就交付缺失条件，不再包装同一4传输候选或重复Mac接管测试。[机器可读准入结论](admission-decision.json)。

## 最新公开参考核对

本次API固定PMCA HEAD为a82f5ba（提交日期2022-08-18），Sony源码字节与既有固定参考一致；不是新的FX3实现。[维护者源码](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py)。

A7CII服务预加载仓库HEAD为1619f938（2026-10-15），[维护者协议](https://github.com/YuuLuo/a7c2-service-preload/blob/1619f938663a36d41e72302a8cfee89a0f6acd1a/PROTOCOL.zh-CN.md)仍说明其2.01机身先MSC、再0336二次认证；其临时代码执行和永久更新准入分开，不能据此证明FX3退出或救砖。

QAQ仓库取得HEAD ef7db116（2026-10-25），本次README内容下载失败；保留网络错误，不把失败说成仓库没有变化或恢复方法已验证。PMCA commands和Yuu协议在后续Contents API取得固定原文；所有下载材料只作文本读取。

同机完整备份、独立恢复、MAIN1080p H.265及最小持久化准入仍未通过。G01至G16保持；12号授权已消耗，11号UNKNOWN保留；没有USB缓存、管理员、Sony认证、上传、读卡、驱动或固件写入操作。
'''
put('README.md',readme.encode())
gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();g=json.loads(gb);assert gb==(P/'goal-status-after-final.json').read_bytes()
preserve={k:g[k]for k in ['requirements','authorization','authorization_consumption','prepared_owner_status12_trial','owner_status12_live_execution','prepared_root_host_trial','prepared_first_device_trial','research_priority']}
now=datetime.now(timezone.utc).isoformat();g['updated_utc']=now;g['latest_stage']=H.name
g['research_activity']='After251 actual status12 ownership-return pass, performed offline Sony entry phase audit:4 whole702 functions39instructions/7jump entries. Commands5/7 share completion branch; Serialize negative/zero/oversize callbacks enter cancellation/yield loops, not ordinary failure-return; helper0xb19c conditionally releases current-thread mutexes, not USB cleanup. Final6/1 precedes history/mode/thread completion. Added pure observation classifier consuming5 archived correct/incorrect digest counterexamples;3synthetic formats/6rejections, no guest rerun or live operations. Standard MSC class response not sole thread-exit proof. Live Sony scope remains closed; bind initial handler/read-only authorization-level capability and STOP receive-unblock/observable end next.251 pass/11UNKNOWN/all16 and grants unchanged.'
g['recovery_Sony_entry_phase_and_exit_admission']=dict(readme=str((H/'README.md').relative_to(R)),static_audit=str((H/'phase-impact-audit.json').relative_to(R)),classifier=str((H/'auth_observation.py').relative_to(R)),test_receipt=str((H/'auth-observation-test-receipt.json').relative_to(R)),decision=str((H/'admission-decision.json').relative_to(R)),whole_original_functions=4,instruction_checks=39,archived_counterexamples_consumed=5,guest_or_camera_tests_repeated=False,original_code_executed=False,live_operations=0,new_live_package_ready=False,new_live_scope_approved=False,host_status12_pass_preserved=True,milestone2_complete=False)
g['next_safe_offline_actions']=[
 '251的Mac接管/归还子步骤已通过，不重复。252明确挑战/完成分支及取消循环，纯CPU结果判定器拒绝把6/1视为认证或线程完成；无新实机验收。',
 '下一步复用145已有模式摘要工具，补初始MSC和0336服务实际处理者绑定，以及一个只读且受认证级别限制的验证指令；普通ProductInfo/新PID/6/1不自动作认证证明。',
 '沿STOP继续核对接收回调解阻塞、取消和主机可观察完成条件；不清started标志冒充退出，不将GET_MAX_LUN或缓存 alone作线程终止。完整固定发送与退出方案前不申请/执行Sony试验，不追加同一4传输模型。',
 '完整同机备份、独立恢复、目标MAIN HEVC和最小持久化准入仍未通过；已消耗授权不复用，首刷不放行。'
]
for k,x in preserve.items():assert g[k]==x,k
assert not g['goal_complete'] and not g['persistent_write_release'];ga=enc(g)
rp=R/'README.md';rb=rp.read_bytes();text=rb.decode();overview=next(x for x in text.splitlines()if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-31 FX3 Sony通信阶段影响与退出准入](<work/sony-firmware-20261024/stage252-MSC-service-entry-impact-and-admission/README.md>)：4原函数39指令/7跳项核对，明确5/7完成分支及传输异常取消循环；新增结果判定器消费5个既存反例，握手结束不充认证成功。251实测通过保留，无新设备操作；Sony试验退出方案未齐。'
assert H.name not in text;ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();text=mb.decode();text=text.replace('核对日期：2026年10月30日。','核对日期：2026年10月31日。',1);assert '最新研究证据为第251阶段。'in text;text=text.replace('最新研究证据为第251阶段。','最新研究证据为第252阶段。',1)
needle='第2项仍缺Sony认证/服务通信及机内RAM程序实际执行。';assert needle in text;text=text.replace(needle,needle+' 252已补通信阶段影响审查和握手结果判定器；发现的取消循环与完成分支均已原字核对，但退出方案尚未可执行，无新真机验收。[本轮结论](../../work/sony-firmware-20261024/stage252-MSC-service-entry-impact-and-admission/README.md)。',1)
old='Mac接管归还子步骤已由251实测关闭，不再重复这一项。第2项下一步准备Sony通信与机内RAM空任务入口，先核对初始MSC认证、服务模式及退出的影响（包括可能持久状态写入），形成具体固定方案前不发送Sony命令或上传。新范围另行提交；12号、11号、195与05均已消耗，不复用。完整备份、独立恢复及目标主录尚未通过。'
new='Mac接管归还子步骤已由251实测关闭。252的阶段影响及判定器已完成；下一步补初始MSC实际处理者与只读、受认证级别限制的验证指令，并追STOP到底层接收解阻塞和可观察完成条件。不重复接管或同一4传输模型，不以6/1、MSC类查询或清本地标志冒充认证/退出。完整固定发送与退出方案齐全后才提交新范围；已消耗授权不复用。'
assert old in text;text=text.replace(old,new,1);ma=text.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('root-readme-before.md',rb),('root-readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma)
receipt=dict(created_utc=now,status='OFFLINE_PHASE_AUDIT_AND_UNVERIFIED_PROTOCOL_CLASSIFIER_COMPLETE_LIVE_SONY_NOT_RELEASED',previous_manifest_sha256=sha256((P/'final-receipt.json').read_bytes()).hexdigest(),previous_members_reverified=len(previous['files']),whole_original_functions=4,instruction_checks=39,command_jump_entries=7,archived_original_counterexamples_consumed=5,synthetic_frame_format_cases=3,malformed_rejections=6,new_guest_tests=0,new_camera_USB_cache_admin_or_firmware_operations=0,downloaded_code_executed=False,original_instructions_executed=False,host_status12_pass_preserved=True,old11_unknown_preserved=True,all16_and_authorizations_unchanged=True,new_live_scope_approved=False,new_fixed_live_package_ready=False,goal_complete=False,persistent_write_release=False,heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
files=[]
for p in sorted(H.rglob('*')):
 if p.is_file():
  raw=p.read_bytes();files.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage252-Sony-entry-phase-admission-v1',member_count=len(files),files=files,**receipt))
print(json.dumps(dict(status=receipt['status'],members=len(files),manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),new_live_operations=0)))
