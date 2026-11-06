"""Read-only closing checks and evidence export; no extra experiment or source repair."""
from common import *
from preflight import verify
import fcntl,socket,shutil,base64
c=identity();R=Path(c['run']);verify('INPUTS-AFTER.json')
local={f:sha(HERE/f) for f in read('LOCAL-SOURCE-FREEZE.json')};assert local==read('LOCAL-SOURCE-FREEZE.json');write('LOCAL-SOURCE-AFTER.json',local)
r=json.loads((R/'receipt.json').read_text());cleanup=json.loads((R/'trial-cleanup-phase.json').read_text());web=json.loads((R/'trial-web-final-receipt.json').read_text());qmp=json.loads((R/'qmp.json').read_text())
quit_req=next(x for x in reversed(qmp) if x.get('request',{}).get('execute')=='quit');qid=quit_req['request']['id'];quit_ack=next(x for x in qmp if x.get('response',{}).get('id')==qid and 'return' in x['response'])
locks=[]
for x in r['locks']:
 with Path(x['path']).open('rb') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
 locks.append({**x,'free_at_postcheck':True})
pids={}
for label,pid in [('runner',c['runner_pid']),('qemu',r['qemu_pid'])]:
 try:os.kill(pid,0);absent=False
 except ProcessLookupError:absent=True
 pids[label]={'pid':pid,'absent':absent}
s=socket.socket();s.settimeout(.3);port=int(c['url'].split(':')[-1].strip('/'));closed=s.connect_ex(('127.0.0.1',port))!=0;s.close();assert closed and all(x['absent'] for x in pids.values())
final={'processes':pids,'port_closed':closed,'locks':locks,'qmp_quit_request':quit_req,'qmp_quit_ack':quit_ack,'browser_session_inactive':json.loads(read('browser-after-close-process.json')['stdout'])['data']['active'] is False,'web_final_ACK':web,'cleanup_errors':read('CLEANUP.json')['errors'],**stamp()};assert final['browser_session_inactive'] and web['acknowledged'] and not final['cleanup_errors'];write('FINAL-CLEANUP-VERIFICATION.json',final)
# Before/after byte copies of only the authorized candidate-local runtime outputs.
allowed=['preflight-aaf006610b0d2b6e.json','STATE-v24.json.tmp','STATE-v25-r3.json'];dest=R/'authorized-runner-outputs';dest.mkdir();(dest/'before').mkdir();(dest/'after').mkdir();outputs=[]
for f in allowed:
 p=FROZEN/f;assert not p.is_symlink();row={'path':str(p),'exists_after':p.exists(),'symlink':False}
 before=HERE/'authorized-outputs-before'/f
 if before.exists():shutil.copyfile(before,dest/'before'/f);row['before_sha256']=sha(before)
 if p.exists():shutil.copyfile(p,dest/'after'/f);row.update(after_sha256=sha(p),bytes=p.stat().st_size)
 outputs.append(row)
new={p.name for p in FROZEN.iterdir()}-set(read('INPUTS-BEFORE.json')['candidate_directory_files']);assert new<=set(allowed),new;write('OUTPUT-BOUNDARY-AFTER.json',{'allowed':outputs,'new_directory_entries':sorted(new),'unexpected_new_entries':[]})
# Raw HTTP bodies from recorded browser HAR, not request replays or reserialized JSON.
http=HERE/'raw-http';http.mkdir();har=json.loads((HERE/'traffic.har').read_text());posts=[e for e in har['log']['entries'] if e['request']['method']=='POST'];idx=[]
for n,e in enumerate(posts,1):
 path=e['request']['url'].split(c['url'].rstrip('/'))[-1];stem='%02d-%s'%(n,path.replace('/','-').strip('-'));req=e['request'].get('postData',{}).get('text','').encode();content=e['response']['content'];body=content.get('text','');resp=base64.b64decode(body) if content.get('encoding')=='base64' else body.encode();a=http/(stem+'-request.body');a.write_bytes(req);b=http/(stem+'-response.body');b.write_bytes(resp);idx.append({'method':'POST','path':path,'status':e['response']['status'],'HAR_startedDateTime':e['startedDateTime'],'HAR_time_ms':e['time'],'request_body':str(a),'request_sha256':sha(a),'response_body':str(b),'response_sha256':sha(b),'request_headers':e['request']['headers'],'response_headers':e['response']['headers']})
keyposts=[x for x in idx if x['path']=='/api/key'];confirm_posts=[x for x in idx if x['path']=='/api/confirm-visual'];assert len([x for x in idx if x['path']=='/api/start'])==1 and not keyposts and not confirm_posts
write('HTTP-INDEX.json',{'posts':idx,'key_POST_count':len(keyposts),'confirm_POST_count':len(confirm_posts),'HAR_sha256':sha(HERE/'traffic.har'),'browser_ready_capture':'HAR began after browser-ready and before Start'})
shutil.copyfile(R/'web-key-rejections.json',HERE/'web-key-rejections.raw.json');rej=json.loads((R/'web-key-rejections.json').read_text());assert rej['total']==0 and sha(R/'web-key-rejections.json')==r['web_key_rejections_export']['sha256']
click=read('step-01-attempt-01-click-process.json');(HERE/'OPERATOR-CLICK.stdout.txt').write_text(click['stdout']);(HERE/'OPERATOR-CLICK.stderr.txt').write_text(click['stderr']);receipt=json.loads((HERE/'step-01-attempt-01/click-receipt.json').read_text());ledger=read('ledger.json');assert receipt['status']=='unknown' and len(ledger['attempts'])==1 and not ledger['recoveries']
write('ACTUAL-CLI-RESULT.json',{'outer_argv':['python3','-B','operate.py','click','1','已亲看NO CARD待机完整图；明确按一次MENU，目标完整Setup > Area/Date，橙色Area/Date/Time Setting'],'outer_exit':1,'outer_evidence':'exec tool chunk d3612d; actual guarded path called cleanup','inner_process':click,'inner_stdout_sha256':sha(HERE/'OPERATOR-CLICK.stdout.txt'),'inner_stderr_sha256':sha(HERE/'OPERATOR-CLICK.stderr.txt'),'outcome':'unknown preserved; no recovery','guard_cleanup':read('FAILURE-CLEANUP-DISPATCH.json')})
initial=read('initial-standby/capture-result.json');shotproc=read('initial-standby-screenshot-process.json');initialstamp=initial['host_ns'];evalstart=receipt['host_start_ns'];evalend=receipt['host_end_ns'];beforeGET=[];afterGET=[]
for e in har['log']['entries']:
 if e['request']['url'].endswith('/api/status'):
  try:v=json.loads(e['response']['content']['text'])
  except (KeyError,json.JSONDecodeError):continue
  if v.get('frame'):
   row={'HAR_startedDateTime':e['startedDateTime'],'HAR_duration_ms':e['time'],'server_phase':v['phase'],'server_ready':v['ready'],'busy':v['busy'],'review_required':v['review_required'],'steps':v['steps'],'frame':{k:v['frame'][k] for k in ('sequence','content_generation','PNG_sha256')}}
   (beforeGET if e['startedDateTime']<'2026-11-05T00:17:31.063Z' else afterGET).append(row)
timing={'host_same_clock':{'screenshot_command_return_ns':shotproc['end']['host_ns'],'qualified_image_return_prepared_ns':initialstamp,'click_helper_before_eval_ns':evalstart,'click_helper_after_error_ns':evalend,'image_return_prepared_to_click_helper_ms':(evalstart-initialstamp)/1e6,'screenshot_command_return_to_click_helper_ms':(evalstart-shotproc['end']['host_ns'])/1e6,'ledger_reservation_ns':ledger['attempts'][0]['host_ns']},'model_receive_time':'unknown','model_review_complete_time':'unknown','not_pure_model_thinking_interval':True,'reviewed_identity':initial['firmware'],'nearest_server_GET_before_arm':beforeGET[-3:],'first_server_GET_after_error':afterGET[:2],'eval_atomic_DOM_snapshot':None,'exact_failing_predicate':'unknown; helper throws one merged preflight error before b.click','inference':'nearby server GET gen20/SHAe014 differs from reviewed gen9/SHA2914; supports freshness mismatch, not an atomic eval-time DOM proof'};write('TIMING-IDENTITY.json',timing)
end=json.loads(read('ended-state-process.json')['stdout']);assert end['lastStatus']['steps']==0 and read('ALARM-DISPOSITION.json')['classification']=='valid_armed_do_not_cancel_or_dispose';events=end['alarm']['events'];assert len([x for x in events if x['event']=='armed'])==1 and not any(x['event']=='cancelled' for x in events)
firstclock=read('FIRST-FRAME-CLOCK.json');elapsed=read('FIRST-FRAME-PASS.json')['host_ns']/1e9-firstclock['start_monotonic'];assert elapsed<180
# Preserve the actual guest serial key lines, including an empty result when no key was delivered.
serial=(R/'serial.log').read_bytes();lines=[x for x in serial.splitlines(keepends=True) if b'FX3_KEY_INPUT' in x];(HERE/'NATIVE-KEY-LINES.raw').write_bytes(b''.join(lines));assert not lines
res={'outcome':'failed','task_id':CFG['task_id'],'dispatch_id':CFG['dispatch_id'],'run':str(R),'preparation':{'actual_CLI_host_checks_passed':True,'checks':read('HOST-CLI-RESULT.json')['checks'],'sys_imports_fixed_in_both_direct_modules':True,'cleanup_null_armed_unknown_flow_fixed':True,'runtime_proof_from_host_checks':False},'real_VM':{'starts':1,'startup_health_pass':r['health_pass'],'standby_ready':r['standby_ready'],'first_qualified_return_seconds_from_Start_entry':elapsed,'first_frame_limit_seconds':180,'arm_calls':1,'operator_helper_invocations':1,'ledger_reservations':1,'ledger_unknown':True,'PAGE_attempt_UUID_created':False,'actual_button_clicks':0,'key_POSTs':0,'accepted_keys':0,'guest_steps':0,'native_key_lines':0,'recoveries':0,'confirmations':0,'eight_key_acceptance':False,'partial_key_success':False,'failure':'frozen operator_click_preflight merged condition threw before b.click; CLI unknown, exact predicate not instrumented'},'steps':[dict(x,status='not_executed',native_down=None,native_up=None,native_done=None,visual_confirm=None) for x in CFG['steps']],'timing_identity':timing,'cleanup':{'passed':True,'errors':[],'API16_restored':cleanup['API16_restored'],'restore_ACK_and_original_bytes_verified':cleanup['restore103']['passed'],'restore_timeout_seconds':cleanup['restore103']['timeout_seconds'],'restore_elapsed_seconds':cleanup['restore103']['elapsed_seconds'],'qmp_quit_ACK':True,'qemu_exit':r['qemu_exit'],'qemu_reaped':r['process_reaped'],'processes_absent':True,'locks_free':True,'port_closed':True,'web_final_ACK':web['acknowledged'],'own_browser_closed':True,'alarm_disposition':read('ALARM-DISPOSITION.json')['classification'],'armed_not_cancelled_or_disposed':True,'timer_termination':'owned document closed before original due; no deadline extension'},'hashes':{'frozen40':True,'delivery145':True,'fixed14':True,'actual_qemu':True,'local_preStart_sources_unchanged':True,'raw_rejection_sha256':sha(R/'web-key-rejections.json')},'diagnostic_tail':{'status':cleanup['snapshot_tail_v15']['status'],'snapshot_is_end_state':False,'post_snapshot_event_counts':'unknown','protocol':5},'scope':'FX3 software OSD VM; no deployment, FX6, camera/USB/SD/flashing','left':'8-key semantics still wholly untested; separate attributable preflight/freshness work needed; no retry in this task',**stamp()};write('RESULT.json',res)
report=f'''# r21c CLI 修复及八键真实 VM：failed

纯 host 接线修复通过，真实 VM 八键 **0/8**，本轮只启动一次。两个模块均直接导入 sys；17项独立子进程用实际源码 `runpy(...,run_name='__main__')` 覆盖 click1–8、confirm、recovery_cancel、异常入口、later_capture argv及cleanup null/nonarmed/armed/malformed/异常；未向被测globals注入sys、common替身不导出sys，无browser fixture或guest副作用。这些只证明CLI接线。

- 本任务 `{CFG['task_id']} / {CFG['dispatch_id']}`；run `{R.name}`。旧29e7c98f失败原件与冻结r21/r10均未改。差分和本地源冻结在 `MINIMAL-WRAPPER.diff` / `LOCAL-SOURCE-FREEZE.json`。
- 实际固定命令与执行中argv保存在 `RUNNER-LAUNCH.json` / `ACTUAL-RUNNING-ARGV.json`；4×cortex-a35、5120MiB、MTTCG、noicount、原kernel/DTB/N64；实际QEMU SHA256 `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`。唯一tab 1280×1200。
- 启动健康通过，Start工具入口至合格待机图返回 **{elapsed:.3f}秒**（上限180）。亲看NO CARD待机完整图；不是菜单验收。
- 首次实际CLI进入run_action、arm成功，随后原冻结operator_click在 `b.click()` 前抛出合并的 `operator_click_preflight`，helper exit2、外层exit1；ledger保留1个unknown reservation，没有PAGE attempt UUID。实际按钮点击0、key POST0、accepted0、guest step0、native down/up/done无记录、恢复0、confirm0；八项语义全未执行。实际异常入口立即原End，没有恢复或重试。
- 身份与时间：已审图gen9/seq38/SHA2914275c…；图已准备返回边界到click helper前eval边界 **{(evalstart-initialstamp)/1e6:.3f}ms**。这是同host时钟工具边界间隔，不是纯模型思考；模型接图/看完时刻unknown。紧邻的HAR GET `00:17:30.901103872Z` 为ready、steps0、busy=false、review_required=false，gen20/seq146/SHAe0140ea1…；`00:17:31.305347072Z`已stopping。这支持freshness失配推测，**没有eval当刻原子DOM快照，无法确认具体哪条前置条件触发**；GET不构成原子权限。详见 `TIMING-IDENTITY.json` 与原HAR。
- 完整收尾通过：API16 ACK与原字节核回，原20秒预算内用时 {cleanup['restore103']['elapsed_seconds']:.6f}秒；QMP quit id{qid} return ACK、exit0/reap、runner/QEMU PID absent、双锁free、端口关闭、网页finalACK、自有browser关闭均核实。cleanup errors=[]；alarm仍armed时正确不取消/不dispose，以原End及关闭自有文档结束，无延长20秒窗口。
- 真实HTTP仅Start202、Stop202、finalACK200，原始HAR及body/hash见 `HTTP-INDEX.json` / `raw-http/`；browser-ready发生在HAR开始前。原始拒绝导出304B、total0，SHA256 `{sha(R/'web-key-rejections.json')}`；原字节副本 `web-key-rejections.raw.json`，零拒绝不充发键成功。v5 tail明确非事务结束快照，尾后事件计数unknown。
- 前后40源码、145交付、14固定输入、实际QEMU及pre-Start本地源全部匹配。仅允许三项非冻结运行输出自然更新，前后原字节复制到run的 `authorized-runner-outputs/before|after/`；冻结manifest未改，无其他候选目录新增文件。

未部署、未操作FX6/物理相机/USB/SD/刷写。八键语义仍全未验；后续应独立处理可归因前置拒绝或预审图时效，本任务不再试跑。
'''
(HERE/'REPORT.md').write_text(report);(HERE/'README.md').write_text('# r21c 独立任务交付\n\n真实VM failed，1arm/1unknown reservation/0accepted；纯host修复17项通过。入口：[REPORT.md](REPORT.md)、[RESULT.json](RESULT.json)、[SHA256SUMS](SHA256SUMS)，runner原件见runtime.json。\n')
shutil.copyfile(HERE/'REPORT.md',R/'R21C-REPORT.md');shutil.copyfile(HERE/'RESULT.json',R/'R21C-RESULT.json')
files=sorted(p for p in R.rglob('*') if p.is_file() and p.name!='R21C-SHA256SUMS');(R/'R21C-SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(R))+'\n' for p in files))
prep=sorted(p for p in HERE.rglob('*') if p.is_file() and p.name!='SHA256SUMS');(HERE/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(HERE))+'\n' for p in prep))
print(json.dumps({'outcome':'failed','report':str(HERE/'REPORT.md'),'report_sha256':sha(HERE/'REPORT.md'),'result_sha256':sha(HERE/'RESULT.json'),'source_freeze_sha256':sha(HERE/'LOCAL-SOURCE-FREEZE.json'),'prep_manifest_sha256':sha(HERE/'SHA256SUMS'),'prep_files':len(prep),'run_manifest_sha256':sha(R/'R21C-SHA256SUMS'),'run_files':len(files)}))
