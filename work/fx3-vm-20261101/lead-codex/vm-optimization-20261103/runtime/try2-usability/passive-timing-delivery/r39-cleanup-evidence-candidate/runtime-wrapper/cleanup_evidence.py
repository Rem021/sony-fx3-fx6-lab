"""r39 cleanup-only evidence/lease helpers. No launch, browser, QMP or guest API."""
import contextvars,errno,fcntl,hashlib,json,os,socket,stat,subprocess,time,uuid
from pathlib import Path
ACTIVE=contextvars.ContextVar('r39_cleanup_output',default=None)
ROOT=Path(__file__).resolve().parents[1]
RUNS=ROOT.parent.parent/'runs'
LOCKS=[Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/.run.lock'),Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/.run.lock')]
SCHEMA='fx3-cleanup-r39-v1'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encoded(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def regular(p):
 p=Path(p)
 if not p.is_absolute() or p.resolve()!=p or any(x.is_symlink() for x in (p,*p.parents)) or not p.is_file():raise ValueError('exact_regular_file:'+str(p))
 return p
def put(p,v):
 p=Path(p)
 with p.open('xb') as f:f.write(encoded(v));f.flush();os.fsync(f.fileno())
def load(p):return json.loads(regular(p).read_bytes())
def atomic_index(p,v):
 p=Path(p)
 if p.is_symlink():raise ValueError('symlink_index')
 tmp=p.with_name(p.name+'.'+str(uuid.uuid4())+'.tmp');put(tmp,v);os.replace(tmp,p)
 fd=os.open(p.parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def invocation(here,kind='cleanup-calls'):
 parent=Path(here)/kind;parent.mkdir(exist_ok=True)
 if parent.is_symlink() or parent.resolve()!=parent:raise ValueError('call_parent_identity')
 call=parent/str(uuid.uuid4());call.mkdir();return call
def acquire(here):
 # The persistent inode is never unlinked. Existence says nothing about liveness.
 p=Path(here)/'.cleanup-owner.lock'
 fd=os.open(p,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:raise ValueError('owner_lock_inode')
  try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:os.close(fd);return None
  return fd
 except BaseException:os.close(fd);raise

def binding(here,c,cfg):
 from r35_package_selection import PROFILE,LABEL
 here=Path(here);run=Path(c['run'])
 if (run.parent!=RUNS or not run.name.startswith(LABEL+'-') or run.resolve()!=run or any(x.is_symlink() for x in (run,*run.parents))):raise ValueError('native_run_boundary')
 if (type(c.get('runner_pid')) is not int or c['runner_pid']<=1 or (c.get('launch_id') is not None and (not isinstance(c['launch_id'],str) or not c['launch_id']))):raise ValueError('launched_runtime_identity_required')
 if cfg['candidate_source_root']!=str(ROOT) or cfg['runner_profile']!=PROFILE:raise ValueError('cleanup_source_profile')
 expected={str(ROOT/n):h for n,h in load(ROOT/'SOURCE-FREEZE.json').items()}
 if load(here/'LOCAL-SOURCE-FREEZE.json')!=expected or any(digest(n)!=h for n,h in expected.items()):raise ValueError('cleanup_source_freeze')
 return {'candidate_run_dir':str(here),'session':cfg['session'],'task_id':cfg['task_id'],'dispatch_id':cfg['dispatch_id'],'source_root':str(ROOT),'profile':PROFILE,'source_sha256':digest(ROOT/'SOURCE-FREEZE.json'),'core_sha256':digest(ROOT/'CORE-SOURCE-FREEZE.json'),'config_sha256':digest(here/'config.json'),'runtime_sha256':digest(here/'runtime.json'),'local_freeze_sha256':digest(here/'LOCAL-SOURCE-FREEZE.json'),'runtime':c}

def routed_write(name,data):
 state=ACTIVE.get()
 if state is None:raise RuntimeError('cleanup_context_required')
 try:put(state['dir']/name,data)
 except Exception as e:state['write_errors'].append(name+': '+repr(e))
def run_capture(name,args,source,timeout,env,stamp,event):
 state=ACTIVE.get();start=stamp();event(name+'_enter',argv=args);p=None;exc=None
 try:p=subprocess.run(args,input=source,text=True,capture_output=True,timeout=timeout,env=env)
 except BaseException as e:exc=e
 def text(v):return v.decode(errors='replace') if isinstance(v,bytes) else (v or '')
 out=text(p.stdout if p else getattr(exc,'stdout',None));err=text(p.stderr if p else getattr(exc,'stderr',None))
 record={'argv':args,'start':start,'end':stamp(),'returncode':p.returncode if p else None,'stdout':out,'stderr':err,'transport_error':repr(exc) if exc else None}
 for suffix,data in [('-stdout.txt',out.encode()),('-stderr.txt',err.encode())]:
  try:
   with (state['dir']/(name+suffix)).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  except Exception as e:state['write_errors'].append(name+suffix+': '+repr(e))
 routed_write(name+'-process.json',record);event(name+'_exit',returncode=record['returncode'],transport_error=record['transport_error'])
 if exc:raise exc
 if p.returncode:raise RuntimeError(name+' failed: '+out[-1000:]+err[-500:])
 return out

def native_evidence(c,folder=None):
 from r35_package_selection import PACKAGE,CANDIDATE_SHA,PROFILE
 run=Path(c['run']);names=['command.json','trial-session.json','receipt.json','trial-web-final-receipt.json','resource-guard-receipt.json']
 values={};refs={}
 if folder:folder.mkdir()
 for name in names:
  p=regular(run/name);raw=p.read_bytes();v=json.loads(raw);values[name]=v;refs[name]={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  if folder:
   with (folder/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 cmd=values['command.json'];ses=values['trial-session.json'];r=values['receipt.json'];ack=values['trial-web-final-receipt.json'];guard=values['resource-guard-receipt.json']
 if ses['run']!=str(run) or ses['observer_pid']!=c['runner_pid'] or ses['url'].rstrip('/')!=c['url'].rstrip('/') or not ses['host_launch_uuid']:raise ValueError('native_session_identity')
 qpid=ses['qemu_pid']
 if type(qpid) is not int or qpid<=1 or qpid==c['runner_pid']:raise ValueError('native_qemu_identity')
 if cmd['cwd']!=str(run) or cmd['candidate']!=str(PACKAGE/'candidate.json') or cmd['candidate_sha256']!=CANDIDATE_SHA or cmd['r35_diagnostic_selection']['profile']!=PROFILE:raise ValueError('native_command_identity')
 if (r['run']!=str(run) or r['candidate']!=cmd['candidate'] or r['candidate_sha256']!=CANDIDATE_SHA or r['qemu_pid']!=qpid or r['process_reaped'] is not True or r['PID_absent'] is not True or type(r['qemu_exit']) is not int):raise ValueError('native_receipt_reap_or_identity')
 expected={x.name:digest(x) for x in [ROOT/'run_trial_r24_review_snapshot.py',ROOT/'r35_package_selection.py',ROOT/'trial_web_r24_review_snapshot.py',ROOT/'startup_observation.py']}
 seen={x['name']:x['sha256'] for x in r['observer_source_snapshot']}
 if any(seen.get(n)!=h for n,h in expected.items()):raise ValueError('native_observer_source')
 if (len(r['locks'])!=2 or {x['path'] for x in r['locks']}!={str(p) for p in LOCKS} or any(x['free_at_close'] is not True for x in r['locks'])):raise ValueError('native_locks')
 if r['cleanup']['API16_restored'] is not True or r['cleanup']['quit_sent'] is not True:raise ValueError('native_restore_quit_unproven')
 if guard['process_reaped'] is not True or guard['locks_released_after_reap'] is not True or not any(x.get('event')=='process_reaped' and x.get('pid')==qpid for x in guard['events']):raise ValueError('guard_reap')
 if ack['acknowledged'] is not True or ack['end_reason']!='browser_ack' or ack['scope']!='browser_receipt_delivery_only' or ack['maximum_wait_seconds']!=30:raise ValueError('final_ACK_unproven')
 return {'files':refs,'qemu_pid':qpid,'host_launch_uuid':ses['host_launch_uuid'],'locks':[str(p) for p in LOCKS],'scope':'finalACK is bound by this run directory/session/command/native receipt and captured finished page; not globally atomic'}

def resource_check(c,qpid):
 result={'runner_pid':c['runner_pid'],'qemu_pid':qpid,'runner_absent':False,'qemu_absent':False,'port_closed':False,'locks':[],'errors':[],'checked_wall_ns':time.time_ns()}
 for key,pid in [('runner_absent',c['runner_pid']),('qemu_absent',qpid)]:
  try:os.kill(pid,0)
  except ProcessLookupError:result[key]=True
  except Exception as e:result['errors'].append(key+': '+repr(e))
 try:
  from urllib.parse import urlsplit
  u=urlsplit(c['url'])
  if u.hostname!='127.0.0.1' or u.scheme!='http' or not u.port:raise ValueError('owned_loopback_URL')
  with socket.socket() as s:s.settimeout(.3);rc=s.connect_ex(('127.0.0.1',u.port))
  result['port_connect_errno']=rc;result['port_closed']=rc==errno.ECONNREFUSED
  if rc not in (0,errno.ECONNREFUSED):result['errors'].append('port_state_unknown:'+str(rc))
 except Exception as e:result['errors'].append('port: '+repr(e))
 for path in LOCKS:
  try:
   with regular(path).open('rb') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
   result['locks'].append({'path':str(path),'free_at_probe':True})
  except Exception as e:result['errors'].append('lock: '+repr(e))
 result['resources_closed']=bool(not result['errors'] and result['runner_absent'] and result['qemu_absent'] and result['port_closed'] and len(result['locks'])==2)
 return result

def certify(call,c,cfg,body,probe=resource_check,copy_native=True):
 if not isinstance(c.get('launch_id'),str) or not c['launch_id']:raise ValueError('launch_not_yet_established_no_completion_certificate')
 if body['errors'] or body['runner_alive'] is not False or body['port_closed'] is not True or body['alarm_disposition'] not in ('valid_null_never_armed','valid_nonarmed'):raise ValueError('cleanup_body_incomplete')
 state=load(call/'ENDED-STATE.json');status=state['lastStatus'];alarm=load(call/'deadline-after-End.json')
 if (state['finished'] is not True or status['phase']!='finished' or status['launch_request_id']!=c['launch_id'] or not status['run_incarnation'] or state['url']!=c['url'] or not state['document_id'] or state['document_time_origin']!=alarm['documentTimeOrigin']):raise ValueError('finished_page_launch_document_binding')
 after=json.loads(load(call/'browser-after-close-process.json')['stdout'])
 if after.get('success') is not True or after['data']['session']!=cfg['session'] or after['data']['active'] is not False or after['data']['pid'] is not None:raise ValueError('browser_close_unproven')
 for name in ['End-original-button','ended-state','ended-page','deadline-after-End','deadline-dispose','HAR-stop','browser-before-close','browser-close','browser-after-close']:
  if load(call/(name+'-process.json'))['returncode']!=0:raise ValueError('incomplete_stage:'+name)
 if not regular(call/'ended-page.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('cleanup_PNG_missing')
 har=load(call/'traffic.har')
 if not isinstance(har.get('log',{}).get('entries'),list):raise ValueError('cleanup_HAR_missing')
 native=native_evidence(c,call/'native' if copy_native else None);resources=probe(c,native['qemu_pid'])
 if resources.get('resources_closed') is not True:raise ValueError('current_resources_unproven:'+json.dumps(resources))
 return {'native':native,'resources':resources,'run_incarnation':status['run_incarnation'],'document_id':state['document_id'],'scope':'cleanup completion only; original action/menu outcome unchanged'}

def seal(call):
 files={}
 for p in sorted(call.rglob('*')):
  if p.is_file():regular(p);files[str(p.relative_to(call))]={'sha256':digest(p),'bytes':p.stat().st_size}
 put(call/'MANIFEST.json',{'schema':SCHEMA,'call_id':call.name,'files':files})
 return {'call_id':call.name,'receipt_path':str(call/'result.json'),'receipt_sha256':digest(call/'result.json'),'manifest_path':str(call/'MANIFEST.json'),'manifest_sha256':digest(call/'MANIFEST.json')}

def validate_reference(here,ref):
 call=Path(ref['receipt_path']).parent
 if call.parent!=Path(here)/'cleanup-calls' or call.name!=ref['call_id'] or Path(ref['manifest_path'])!=call/'MANIFEST.json':raise ValueError('receipt_call_boundary')
 if digest(regular(call/'result.json'))!=ref['receipt_sha256'] or digest(regular(call/'MANIFEST.json'))!=ref['manifest_sha256']:raise ValueError('receipt_reference_hash')
 manifest=load(call/'MANIFEST.json')
 if manifest['schema']!=SCHEMA or manifest['call_id']!=call.name:raise ValueError('manifest_identity')
 for name,v in manifest['files'].items():
  p=call/name
  if p.resolve()!=p or not p.is_relative_to(call) or digest(regular(p))!=v['sha256'] or p.stat().st_size!=v['bytes']:raise ValueError('artifact_integrity:'+name)
 required={'invocation.json','result.json','body-result.json','proof.json','stdout.txt','stderr.txt','ENDED-STATE.json','traffic.har','ended-page.png','deadline-after-End.json','ALARM-DISPOSITION.json'}
 required|={'native/'+n for n in ('command.json','trial-session.json','receipt.json','trial-web-final-receipt.json','resource-guard-receipt.json')}
 if not required.issubset(manifest['files']):raise ValueError('incomplete_manifest')
 public=load(call/'RETURN-HASH.json');raw=regular(call/'return.stdout.txt')
 if digest(raw)!=public['sha256'] or raw.stat().st_size!=public['bytes']:raise ValueError('public_stdout_integrity')
 published=load(raw)
 value=load(call/'result.json')
 if published.get('status')!='completed' or published.get('call_id')!=call.name or published.get('binding')!=value.get('binding'):raise ValueError('public_stdout_identity')
 if value['schema']!=SCHEMA or value['call_id']!=call.name or value['status']!='completed' or value['errors']:raise ValueError('not_a_completed_receipt')
 return call,value

def revalidate(here,ref,current,c,cfg,probe=resource_check):
 call,value=validate_reference(here,ref)
 if value['binding']!=current or load(call/'invocation.json')['binding']!=current:raise ValueError('stale_or_cross_run_session_launch_source')
 # Re-run semantic proof against immutable captured native evidence, then require
 # originals still match. Do not infer validity from errors=[] or a file name.
 proof=load(call/'proof.json');now_native=native_evidence(c)
 if now_native!=proof['native']:raise ValueError('original_native_evidence_changed')
 body=load(call/'body-result.json')
 fresh=certify(call,c,cfg,body,probe,copy_native=False)
 if any(fresh[k]!=proof[k] for k in ('native','run_incarnation','document_id')):raise ValueError('original_semantic_proof_changed')
 resources=fresh['resources']
 return {'original_receipt':ref,'resources':resources,'original_completed_call':call.name,'scope':'prior bound completion plus current point probes; not global End atomicity'}

def publish(here,ref,value):
 first=Path(here)/'CLEANUP-FIRST.json'
 if not first.exists():put(first,ref)
 completed=Path(here)/'CLEANUP-COMPLETED.json'
 if value['status']=='completed':
  if completed.exists():
   old=value.get('superseded_invalid_completion')
   if not old or digest(regular(completed))!=old['sha256'] or digest(regular(old['path']))!=old['sha256']:raise ValueError('cannot_replace_unarchived_completion_index')
   atomic_index(completed,ref) # immutable archived invalid index remains in this call
  else:put(completed,ref)
 atomic_index(Path(here)/'CLEANUP.json',{'schema':SCHEMA,'kind':'compatibility_index_only','first_invocation':load(first),'latest_invocation':ref,'latest_status':value['status'],'completed_invocation':load(completed) if completed.exists() else None,'superseded_invalid_completion':value.get('superseded_invalid_completion'),'action_outcome':'unchanged; cleanup is separate'})

def dispatch_cleanup(source,here,env):
 """One original 100s subprocess; raw failure cleanup streams never overwritten."""
 out=invocation(here,'cleanup-dispatches');argv=['python3','-B',str(source/'cleanup.py')];value={'dispatch_id':out.name,'argv':argv,'returncode':None,'stdout_path':str(out/'stdout.txt'),'stderr_path':str(out/'stderr.txt'),'status':'unknown','original_action_failed':True,'schema':SCHEMA,'return_call_id':env.get('FX3_RETURN_CALL_ID'),'binding':binding(here,load(Path(here)/'runtime.json'),load(Path(here)/'config.json'))}
 try:
  with (out/'stdout.txt').open('xb') as stdout,(out/'stderr.txt').open('xb') as stderr:
   p=subprocess.run(argv,env=env,stdout=stdout,stderr=stderr,timeout=100)
   stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
  value.update(returncode=p.returncode,stdout=(out/'stdout.txt').read_text(),stderr=(out/'stderr.txt').read_text())
  if p.returncode==0:
   receipt=json.loads(value['stdout']);value.update(status=receipt['status'],cleanup_receipt=receipt)
 except BaseException as e:value['error']=repr(e)
 value['stdout_sha256']=digest(out/'stdout.txt');value['stderr_sha256']=digest(out/'stderr.txt')
 put(out/'dispatch.json',value)
 # Separate namespace/lock not needed: each action owns one dispatch; the shared
 # compatibility index is read-only provenance to the FIRST dispatch, never replaced.
 try:put(Path(here)/'FAILURE-CLEANUP-DISPATCH.json',{'schema':SCHEMA,'kind':'first_dispatch_reference','dispatch':str(out/'dispatch.json'),'sha256':digest(out/'dispatch.json'),'original_action_failed':True})
 except FileExistsError:pass
 return value

def record_event(value):
 state=ACTIVE.get()
 try:
  with (state['dir']/'tool-timeline.jsonl').open('a') as f:f.write(json.dumps(value,ensure_ascii=False)+'\n')
 except Exception as e:state['write_errors'].append('timeline: '+repr(e))

def failure_status(here,return_call_id):
 """Readonly report from this exact adapter child, never from an old current-return."""
 unknown={'reported_status':'unknown','scope':'cleanup separate from failed original action'}
 try:
  matches=[]
  for p in (Path(here)/'cleanup-dispatches').glob('*/dispatch.json'):
   v=load(p)
   if v.get('return_call_id')==return_call_id:matches.append((p,v))
  if len(matches)!=1:return unknown
  p,v=matches[0]
  if v['schema']!=SCHEMA or v['original_action_failed'] is not True or v['binding']!=binding(here,load(Path(here)/'runtime.json'),load(Path(here)/'config.json')):return unknown
  if Path(v['stdout_path'])!=p.parent/'stdout.txt' or Path(v['stderr_path'])!=p.parent/'stderr.txt' or digest(regular(v['stdout_path']))!=v['stdout_sha256'] or digest(regular(v['stderr_path']))!=v['stderr_sha256']:return unknown
  status=v['status'] if v['status'] in ('completed','already-cleaned','busy','unknown') else 'unknown'
  return {'reported_status':status,'dispatch_receipt':str(p),'dispatch_sha256':digest(p),'scope':'this exact failed action child reports cleanup separately; audit still required'}
 except Exception:return unknown

def owned_live_candidate(here,c,cfg):
 """Independent current-run precheck after an unusable completion index.

 No process is signalled except kill(0). A positive PID is insufficient: match
 current command/parent edges and stored run/session/package, then the caller
 must independently read-check the exact live document before original End.
 """
 from r35_package_selection import PACKAGE,CANDIDATE_SHA,PROFILE
 import shlex
 run=Path(c['run']);cmd=load(run/'command.json');ses=load(run/'trial-session.json');launch=load(Path(here)/'RUNNER-LAUNCH.json')
 if (ses['run']!=str(run) or ses['observer_pid']!=c['runner_pid'] or ses['url'].rstrip('/')!=c['url'].rstrip('/') or not ses['host_launch_uuid'] or launch['pid']!=c['runner_pid']):raise ValueError('current_native_run_identity_unknown')
 if cmd['cwd']!=str(run) or cmd['candidate']!=str(PACKAGE/'candidate.json') or cmd['candidate_sha256']!=CANDIDATE_SHA or cmd['r35_diagnostic_selection']['profile']!=PROFILE:raise ValueError('current_package_identity_unknown')
 qpid=ses['qemu_pid']
 if type(qpid) is not int or qpid<=1 or qpid==c['runner_pid']:raise ValueError('current_qemu_identity_unknown')
 resources=resource_check(c,qpid)
 if resources['resources_closed']:return {'state':'resources_closed','resources':resources}
 # Both exact processes and an accepting port are required before even a readonly
 # owned-page query. Probe errors/ambiguous PID state cannot authorize it.
 if resources['runner_absent'] or resources['qemu_absent'] or resources.get('port_connect_errno')!=0 or any(not e.startswith('lock: BlockingIOError') for e in resources['errors']):raise ValueError('current_resources_not_proven_live')
 expected=launch['argv'];script=str(ROOT/'run_trial_r24_review_snapshot.py')
 if len(expected)<3 or expected[:2]!=['python3','-B'] or expected[2]!=script:raise ValueError('current_runner_launch_source')
 actual=subprocess.check_output(['ps','-p',str(c['runner_pid']),'-o','command='],text=True,timeout=2).strip();words=shlex.split(actual)
 if not words or not Path(words[0]).name.lower().startswith('python') or words[1:]!=expected[1:]:raise ValueError('current_runner_command_mismatch')
 ppid=int(subprocess.check_output(['ps','-p',str(qpid),'-o','ppid='],text=True,timeout=2).strip())
 qexe=subprocess.check_output(['ps','-p',str(qpid),'-o','comm='],text=True,timeout=2).strip()
 if ppid!=c['runner_pid'] or qexe!=cmd['args'][0]:raise ValueError('current_QEMU_parent_or_executable_mismatch')
 return {'state':'live_candidate_requires_owned_page','resources':resources,'run':str(run),'qemu_pid':qpid,'host_launch_uuid':ses['host_launch_uuid'],'runner_source':script,'launch_record_sha256':digest(Path(here)/'RUNNER-LAUNCH.json'),'no_process_signals_or_QMP':True}
