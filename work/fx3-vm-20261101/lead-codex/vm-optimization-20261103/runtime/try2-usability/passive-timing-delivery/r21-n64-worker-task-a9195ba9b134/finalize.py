"""Finalize this failed single VM; read-only verification, no browser/tests/guest."""
from common import *
from preflight import verify
import fcntl,socket,shutil,base64

c=identity();R=Path(c['run']);verify('INPUTS-AFTER.json')
source_after={f:sha(HERE/f) for f in read('LOCAL-SOURCE-FREEZE.json')};assert source_after==read('LOCAL-SOURCE-FREEZE.json');write('LOCAL-SOURCE-AFTER.json',source_after)
r=json.loads((R/'receipt.json').read_text());cleanup=json.loads((R/'trial-cleanup-phase.json').read_text());web=json.loads((R/'trial-web-final-receipt.json').read_text());qmp=json.loads((R/'qmp.json').read_text())
quit_request=next(x for x in reversed(qmp) if x.get('request',{}).get('execute')=='quit');qid=quit_request['request']['id'];quit_ack=next(x for x in qmp if x.get('response',{}).get('id')==qid and 'return' in x['response'])
locks=[]
for x in r['locks']:
 with Path(x['path']).open('rb') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
 locks.append({**x,'free_at_independent_postcheck':True})
pids={}
for label,pid in [('runner',c['runner_pid']),('qemu',r['qemu_pid'])]:
 try:os.kill(pid,0);absent=False
 except ProcessLookupError:absent=True
 pids[label]={'pid':pid,'absent':absent}
s=socket.socket();s.settimeout(.5);port=int(c['url'].split(':')[-1].strip('/'));port_closed=s.connect_ex(('127.0.0.1',port))!=0;s.close();assert port_closed and all(x['absent'] for x in pids.values())
post={'processes':pids,'port':port,'port_closed':port_closed,'locks':locks,'qmp_quit_request':quit_request,'qmp_quit_ack':quit_ack,'browser_session_inactive':json.loads(read('browser-after-close-process.json')['stdout'])['data']['active'] is False,'web_final_ack':web,**stamp()};write('FINAL-CLEANUP-VERIFICATION.json',post)
allowed=['preflight-aaf006610b0d2b6e.json','STATE-v24.json.tmp','STATE-v25-r3.json'];dest=R/'authorized-runner-outputs';dest.mkdir();boundary=[]
for f in allowed:
 p=FROZEN/f;assert not p.is_symlink();row={'path':str(p),'exists':p.exists(),'symlink':False}
 if p.exists():
  shutil.copyfile(p,dest/f);row.update(sha256=sha(p),bytes=p.stat().st_size,copied_to=str(dest/f))
 boundary.append(row)
before=set(read('INPUTS-BEFORE.json')['candidate_directory_files']);after={p.name for p in FROZEN.iterdir()};assert after-before<=set(allowed),(after-before);write('OUTPUT-BOUNDARY-AFTER.json',{'authorized_by':'msg_82796ff62714','outputs':boundary,'new_directory_entries':sorted(after-before),'unexpected_new_entries':[]})
# Exact combined terminal output from actual tool result. It was not redirected by the failed wrapper.
error='''Traceback (most recent call last):
  File "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r21-n64-worker-task-a9195ba9b134/operate.py", line 67, in <module>
    if __name__=='__main__':run_action(sys.argv[1])
                                       ^^^
NameError: name 'sys' is not defined. Did you forget to import 'sys'?
'''
(HERE/'OPERATOR-CLI-FAILURE.combined.txt').write_text(error)
write('OPERATOR-CLI-FAILURE.json',{'argv':['python3','-B','operate.py','click','1','已亲看当前NO CARD待机完整图；明确按一次MENU，目标完整Setup > Area/Date及橙色Area/Date/Time Setting'],'cwd':str(HERE),'exit_code':1,'combined_output_file':'OPERATOR-CLI-FAILURE.combined.txt','combined_output_sha256':sha(HERE/'OPERATOR-CLI-FAILURE.combined.txt'),'evidence_origin':'exact combined output copied from exec tool result chunk cc82bb; no separate stdout/stderr stream was captured','operation_entered':False,'arm_calls':0,'operator_click_calls':0,'confirm_calls':0,'cause':'sys.argv evaluated at real __main__ before guarded run_action; sys missing from operate globals','additional_unexecuted_site':'later_capture.py uses sys.argv without importing sys','host_check_gap':'imported-function guard check exercised only operate.run_action; it never executed either real __main__ path','coordinator_independent_messages':['msg_5ddb3c4cab2c','msg_2425b11bf72d']})
# Keep HAR raw and extract actual HTTP body bytes as supplied by HAR, without JSON reserialization.
httpdir=HERE/'raw-http';httpdir.mkdir();har=json.loads((HERE/'traffic.har').read_text());posts=[e for e in har['log']['entries'] if e['request']['method']=='POST'];index=[]
for i,e in enumerate(posts,1):
 path=e['request']['url'].split(c['url'].rstrip('/'))[-1];stem='%02d-%s'%(i,path.replace('/','-').strip('-'));req=e['request'].get('postData',{}).get('text','').encode();content=e['response'].get('content',{});body=content.get('text','');resp=base64.b64decode(body) if content.get('encoding')=='base64' else body.encode();p=httpdir/(stem+'-request.body');p.write_bytes(req);z=httpdir/(stem+'-response.body');z.write_bytes(resp)
 index.append({'method':'POST','path':path,'status':e['response']['status'],'startedDateTime':e['startedDateTime'],'HAR_time_ms':e['time'],'request_body':str(p),'request_sha256':sha(p),'response_body':str(z),'response_sha256':sha(z),'request_headers':e['request']['headers'],'response_headers':e['response']['headers']})
assert len([x for x in index if x['path']=='/api/start'])==1 and not any(x['path'] in ('/api/key','/api/confirm-visual') for x in index)
write('HTTP-INDEX.json',{'HAR_sha256':sha(HERE/'traffic.har'),'scope':'browser CDP HAR; exact stored text bodies exported as UTF-8, no direct HTTP mutation','posts':index,'key_POST_count':0,'visual_confirm_POST_count':0,'browser_ready_raw_capture':'not included; HAR started after initial page load, before Start'})
rej=json.loads((R/'web-key-rejections.json').read_text());assert rej['total']==0 and rej['records']==[] and sha(R/'web-key-rejections.json')==r['web_key_rejections_export']['sha256'];shutil.copyfile(R/'web-key-rejections.json',HERE/'web-key-rejections.raw.json')
end_state=json.loads(read('ended-state-process.json')['stdout']);assert end_state['alarm']['current'] is None and [x['event'] for x in end_state['alarm']['events']]==['installed'] and end_state['lastStatus']['steps']==0
clock=read('FIRST-FRAME-CLOCK.json');first=read('FIRST-FRAME-PASS.json');elapsed=first['host_ns']/1e9-clock['start_monotonic'];assert elapsed<180
result={'outcome':'failed','reason':'local wrapper CLI NameError before run_action, arm, or guest key','run':str(R),'task_id':'task_a9195ba9b134','dispatch_id':'ctx_03724bb404e1','vm_starts':1,'first_frame':{'passed':True,'operator_saw':'complete NO CARD standby icons','qualified_return_elapsed_seconds_from_Start_tool_entry':elapsed,'maximum_seconds':180,'firmware':read('initial-standby/capture-result.json')['firmware']},'runner_health_pass':r['health_pass'],'eight_key_acceptance':False,'partial_key_success':False,'accepted_keys':0,'actual_operator_clicks':0,'CLI_click_invocations':1,'arm_calls':0,'recovery_calls':0,'confirm_calls':0,'attempt_ledger':{'created':False,'reason':'real CLI entry failed before guarded action; no arm/attempt reservation occurred','do_not_treat_as_used_ledger':True},'steps':[dict(x,status='not_executed',native_down=None,native_up=None,native_done=None,visual_confirm=None) for x in CFG['steps']],'native_shutdown':{'passed':r['lifecycle_pass'],'api16_original_restored':cleanup['API16_restored'],'restore_timeout_seconds':cleanup['restore103']['timeout_seconds'],'restore_elapsed_seconds':cleanup['restore103']['elapsed_seconds'],'restore_ACK_and_original_bytes_verified':cleanup['restore103']['passed'],'qmp_quit_acknowledged':True,'qemu_exit':r['qemu_exit'],'qemu_reaped':r['process_reaped'],'qemu_absent':pids['qemu']['absent'],'runner_absent':pids['runner']['absent'],'locks_free':True,'port_closed':port_closed,'web_final_ACK':web['acknowledged'],'own_browser_closed':post['browser_session_inactive']},'cleanup_wrapper_limitations':{'error':read('CLEANUP.json')['errors'],'alarm_never_armed':True,'deadline_dispose_not_called':'cleanup used None.get after successful status retrieval; owned document closed; no armed timer','initial_pid_port_status':'CLEANUP.json observed runner alive/port open immediately before its normal exit; FINAL-CLEANUP-VERIFICATION.json proves eventual closure'},'rejections':{'total':0,'raw_bytes':(R/'web-key-rejections.json').stat().st_size,'sha256':sha(R/'web-key-rejections.json')},'source_and_input_checks':{'frozen_source40':True,'frozen_delivery145':True,'fixed14':True,'actual_qemu':True,'local_prestart_sources_unchanged':True,'runner_inputs_unchanged':r['inputs_unchanged']},'tail':{'status':cleanup['snapshot_tail_v15']['status'],'protocol':5,'snapshot_is_end_state':False,'post_snapshot_event_counts':'unknown'},'scope':'FX3 software-OSD VM only; no physical camera/USB/SD/flashing/FX6 evidence','left':['separate corrected wrapper preparation must fix direct sys imports in operate.py and later_capture.py','real CLI smoke checks without browser/guest effects required before any future Start','none of eight key navigation semantics exercised; new VM requires separate assignment'],**stamp()}
write('RESULT.json',result)
report=f'''# r21/N64 八键真实 VM 验收：failed

唯一一次 VM 已运行；**实际 accepted 0/8、显式按钮点击 0、arm 0、恢复 0、确认 0**。本轮本地 wrapper 的 `operate.py:67` 在 `run_action` 之前引用未导入的 `sys.argv`，真实 CLI exit=1；随即执行原 End，没有补键或再次启动。失败原因在本轮操作工具，未得到 r21 菜单行为结论。

- run：`{R.name}`；真正源码是冻结 r21，目录标签 r17 不作版本依据。
- 固定命令和实际 argv：`RUNNER-LAUNCH.json`、`ACTUAL-ARGV-PREPARED.json`、`ACTUAL-RUNNING-ARGV.json`。实际 QEMU 为 `qemu-gpio5-bf4d46481998b8fb`，SHA256 `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`；4×cortex-a35、5120 MiB、tcg,thread=multi、noicount，kernel/DTB/N64 CPIO 未变。
- 启动健康：runner `health_pass=true`、`standby_ready=true`；从 Start 工具入口至合格待机图返回约 **{elapsed:.3f} 秒**，小于180秒。操作员亲看 NO CARD、HD/Fixed-59.94fps 与待机图标；不是八键通过。看图接收/完成的模型时钟无仪器，仍记 unknown。
- 八项固定语义全部未执行，无 down/up/done、确认或逐键截图可交付；未建立 attempt/nonce/ledger。`RESULT.json` 逐项标 not_executed，不能用零拒绝或 HTTP202 冒充发键成功。
- 原始失败：`OPERATOR-CLI-FAILURE.json` 与 `.combined.txt` 保存实际 argv、exit1及工具返回的完整合并终端输出；没有单独重定向 stderr。`later_capture.py` 也有同类缺失导入，尚未执行；此前 host 检查调用导入后的 `run_action`，未覆盖实际 `__main__`。本轮失败源码保持冻结，没有修后重跑。
- End与回收：API16 原字节及 ACK 已核，原20秒恢复预算内用时 {cleanup['restore103']['elapsed_seconds']:.6f}秒；QMP quit id={qid} 有 return ACK，exit0/reaped/双锁free/runner与QEMU PID absent/端口closed、网页finalACK、自有browser关闭均有证据。见 `FINAL-CLEANUP-VERIFICATION.json` 和 run 原始回执。
- 清理 wrapper 另有 None.get 记录：deadline从未armed，status.current=null；读取后误用 `.get`，未调用dispose，随后仍保存HAR并关闭自有browser。首次CLEANUP在runner最后正常退出前一瞬采样为alive/open，独立最终检查已确认关闭；保留两份原始记录，不覆盖。
- HTTP原件在 `traffic.har`，Start202/Stop202/finalACK200各一次，key/confirm POST均零；`HTTP-INDEX.json` 与 `raw-http/` 保存HAR中的原始body字节及hash。browser-ready发生在HAR开始前，其原始HTTP不在本轮HAR中。
- 原字节零拒绝导出304B，SHA256 `{sha(R/'web-key-rejections.json')}`；`web-key-rejections.raw.json` 与run原件一致。v5尾段为 `valid_nontransactional_tail_checkpoint`，明确不是事务结束快照，尾后事件计数unknown。
- 前后核回40项源码、145项交付、14项固定输入和实际QEMU；本地pre-Start源也未变。协调员 `msg_82796ff62714` 允许的preflight/STATE输出已记录生成状态并原字节复制到run的 `authorized-runner-outputs/`；无其他候选目录新增文件，冻结清单未改。

后续需单独派发修正两个CLI模块的直接导入并验证真实CLI入口；八键语义、连续菜单与恢复行为仍未验。本轮无物理相机、USB、SD、刷写或FX6操作。
'''
(HERE/'REPORT.md').write_text(report);(HERE/'README.md').write_text('# r21/N64 单次验收证据\n\n结论 failed，唯一VM、零键；入口见 [REPORT.md](REPORT.md)、[RESULT.json](RESULT.json)，原始runner目录见 runtime.json；所有原始证据hash见SHA256SUMS。\n')
shutil.copyfile(HERE/'REPORT.md',R/'R21-N64-REPORT.md');shutil.copyfile(HERE/'RESULT.json',R/'R21-N64-RESULT.json')
# Two manifests avoid including either manifest's own changing bytes.
runfiles=sorted(p for p in R.rglob('*') if p.is_file() and p.name!='R21-N64-SHA256SUMS');(R/'R21-N64-SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(R))+'\n' for p in runfiles))
files=sorted(p for p in HERE.rglob('*') if p.is_file() and p.name!='SHA256SUMS');(HERE/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(HERE))+'\n' for p in files))
print(json.dumps({'outcome':'failed','report':str(HERE/'REPORT.md'),'report_sha256':sha(HERE/'REPORT.md'),'result_sha256':sha(HERE/'RESULT.json'),'preparation_manifest_sha256':sha(HERE/'SHA256SUMS'),'preparation_files':len(files),'run_manifest_sha256':sha(R/'R21-N64-SHA256SUMS'),'run_files':len(runfiles),'accepted_keys':0,'vm_starts':1,'native_exit_healthy':True}))
