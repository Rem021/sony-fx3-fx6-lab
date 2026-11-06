"""Original End first; classify alarm explicitly, preserve HAR/close, await final exit."""
import socket
from common import *

def _cleanup_once(c,output):
 errors=[];event('cleanup_entry_End_first')
 try:
  ev('End-original-button','(()=>{if(location.href!=='+json.dumps(c['url'])+'||lastStatus.launch_request_id!=='+json.dumps(c.get('launch_id'))+')throw Error("owned_page_identity");if(!finished&&!endButton.disabled){endButton.click();return {End_invoked:true}}return {End_invoked:false,finished,ending}})()')
 except Exception as e:errors.append('End: '+repr(e))
 limit=time.monotonic()+65
 while time.monotonic()<limit:
  if (Path(c['run'])/'trial-web-final-receipt.json').exists():break
  time.sleep(.2)
 else:errors.append('final browser ACK receipt absent within cleanup wait')
 try:
  ended=ev('ended-state','({lastStatus,finished,ending,url:location.href,document_time_origin:performance.timeOrigin,document_id:reviewDocumentId,alarm:window.__fx3InteractionDeadlineV1?.status?.()})');write('ENDED-STATE.json',ended)
  browser('ended-page',['screenshot',str(output/'ended-page.png')],timeout=10)
 except Exception as e:errors.append('ended document capture: '+repr(e))
 disposition='unknown_status_fetch_failed';alarm_sha=None
 try:
  alarm=dl('deadline-after-End','status');write('deadline-after-End.json',alarm)
  alarm_sha=evidence.digest(output/'deadline-after-End.json')
  disposition=evidence.classify_alarm(alarm,c)
  if disposition=='valid_armed_do_not_cancel_or_dispose':
   current=alarm['current']
   write('dispose-not-invoked.json',{'reason':disposition,
    'alarm_cleanup':'no cancel/no dispose; owned document closes below',
    'alarm_sha256':alarm_sha,'alarm':alarm,
    'version':alarm['version'],'deadline_ms':alarm['deadline_ms'],
    'expectedURL':alarm['expectedURL'],'expectedLaunchId':alarm['expectedLaunchId'],
    'documentTimeOrigin':alarm['documentTimeOrigin'],'sealed':alarm['sealed'],
    'nonce':current['nonce'],'state':current['state'],'armed_ms':current['armed_ms'],
    'due_ms':current['due_ms'],'current_deadline_ms':current['deadline_ms']})
  elif disposition in ('valid_null_never_armed','valid_nonarmed'):
   write('deadline-dispose.json',dl('deadline-dispose','dispose'))
  else:
   # Keep a negative record only; certify refuses every non-armed/unknown disposition.
   write('dispose-not-invoked.json',{'reason':disposition,
    'alarm_cleanup':'no cancel/no dispose; owned document closes below',
    'alarm_sha256':alarm_sha,'alarm':alarm})
 except Exception as e:errors.append('alarm status/dispose: '+repr(e))
 write('ALARM-DISPOSITION.json',{'classification':disposition,'forced_cancel':False,
  'dispose_invoked':disposition in ('valid_null_never_armed','valid_nonarmed'),
  'alarm_sha256':alarm_sha})
 try:browser('HAR-stop',['network','har','stop',str(output/'traffic.har')],timeout=15)
 except Exception as e:errors.append('HAR: '+repr(e))
 try:browser('browser-before-close',['session','info','--json'])
 except Exception as e:errors.append('browser before-close info: '+repr(e))
 try:browser('browser-close',['close'])
 except Exception as e:errors.append('browser close: '+repr(e))
 try:browser('browser-after-close',['session','info','--json'])
 except Exception as e:errors.append('browser after-close info: '+repr(e))
 def alive(pid):
  try:os.kill(pid,0);return True
  except ProcessLookupError:return False
 port=int(c['url'].split(':')[-1].strip('/'))
 def portclosed():
  s=socket.socket();s.settimeout(.3)
  try:return s.connect_ex(('127.0.0.1',port))!=0
  finally:s.close()
 limit=time.monotonic()+5
 while True:
  running=alive(c['runner_pid']);closed=portclosed()
  if (not running and closed) or time.monotonic()>=limit:break
  time.sleep(.05)
 if running or not closed:errors.append('final runner PID/port not closed within bounded wait')
 value={'errors':errors,'alarm_disposition':disposition,'runner_pid':c['runner_pid'],'runner_alive':running,'port_closed':closed,'bounded_final_recheck_seconds':5,**stamp()};write('body-result.json',value);return value



def cleanup():
 """Explicit invocation: immutable evidence and one kernel-lock owner per run."""
 import contextlib,io
 c=identity();call=evidence.invocation(HERE);fd=None;token=None
 value={'schema':evidence.SCHEMA,'call_id':call.name,'status':'unknown','errors':[],
        'receipt_path':str(call/'result.json'),'usable_only_with_verified_manifest_reference':True,'original_action_outcome':'unchanged',**stamp()}
 state={'dir':call,'write_errors':[]};owner=False
 try:
  fd=evidence.acquire(HERE);owner=fd is not None
  current=evidence.binding(HERE,c,CFG);value['binding']=current
  try:evidence.put(call/'invocation.json',{'schema':evidence.SCHEMA,'call_id':call.name,'binding':current,'owner':owner,**stamp()})
  except Exception as e:state['write_errors'].append('invocation: '+repr(e))
  def stream(name):
   try:return (call/name).open('x')
   except Exception as e:
    state['write_errors'].append(name+': '+repr(e));return io.StringIO()
  with stream('stdout.txt') as stdout,stream('stderr.txt') as stderr,contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
   token=evidence.ACTIVE.set(state)
   try:
    if not owner:
     value.update(status='busy',errors=['cleanup owner active; no wait, no second End/browser/dispose'])
    else:
     needs_cleanup=True
     if (HERE/'CLEANUP-COMPLETED.json').exists() or (HERE/'CLEANUP-COMPLETED.json').is_symlink():
      try:
       ref=evidence.load(HERE/'CLEANUP-COMPLETED.json');proof=evidence.revalidate(HERE,ref,current,c,CFG)
       write('revalidation.json',proof);value.update(status='already-cleaned',original_receipt=ref,resources=proof['resources']);needs_cleanup=False
      except Exception as invalid:
       # Preserve even malformed bytes. The bad index is neither permission to
       # skip a live run's End nor permission to act on an unowned page/PID.
       raw=evidence.regular(HERE/'CLEANUP-COMPLETED.json').read_bytes()
       with (call/'invalid-completed-index.bin').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
       superseded={'path':str(call/'invalid-completed-index.bin'),'sha256':evidence.digest(call/'invalid-completed-index.bin'),'reason':repr(invalid)}
       write('invalid-completion.json',superseded)
       current_live=evidence.owned_live_candidate(HERE,c,CFG);write('current-live-precheck.json',current_live)
       if current_live['state']!='live_candidate_requires_owned_page':raise ValueError('invalid completion evidence; current resources closed; no browser revisit')
       if not isinstance(c.get('launch_id'),str) or not c['launch_id']:raise ValueError('current_launch_unestablished_End_required')
       owned=ev('owned-current-before-recleanup','(()=>{if(location.href!=='+json.dumps(c['url'])+'||lastStatus.launch_request_id!=='+json.dumps(c['launch_id'])+'||finished||ending||lastStatus.phase==="finished"||!lastStatus.run_incarnation)throw Error("current_owned_lifecycle_unknown");return {url:location.href,launch_id:lastStatus.launch_request_id,document_id:reviewDocumentId,document_time_origin:performance.timeOrigin,run_incarnation:lastStatus.run_incarnation}})()')
       if owned.get('url')!=c['url'] or owned.get('launch_id')!=c['launch_id'] or not owned.get('document_id') or not owned.get('run_incarnation'):raise ValueError('current_owned_page_identity')
       if (HERE/'current-attempt.json').exists():
        attempt=read('current-attempt.json').get('postkey_binding')
        if attempt and any(owned.get(k)!=attempt.get(k) for k in ('document_id','document_time_origin','run_incarnation')):raise ValueError('current_document_changed_End_required')
       write('owned-current-page.json',owned);value['superseded_invalid_completion']=superseded
     if needs_cleanup:
      body=_cleanup_once(c,call);value.update(body)
      if state['write_errors']:raise OSError('cleanup evidence writes failed: '+repr(state['write_errors']))
      proof=evidence.certify(call,c,CFG,body);write('proof.json',proof)
      if state['write_errors']:raise OSError('cleanup proof persistence failed')
      value.update(status='completed',resources=proof['resources'])
   except BaseException as e:
    value['status']='unknown';value['End_required']=True;value['errors']=[*value['errors'],'cleanup incomplete: '+repr(e)]
   finally:
    evidence.ACTIVE.reset(token);token=None
   print(json.dumps(value,ensure_ascii=False));stdout.flush();stderr.flush()
   for f in (stdout,stderr):
    if not isinstance(f,io.StringIO):os.fsync(f.fileno())
  evidence.put(call/'result.json',value);ref=evidence.seal(call)
  if owner:evidence.publish(HERE,ref,value)
  value={**value,'receipt_reference':ref}
 except BaseException as e:
  value.update(status='unknown',errors=[*value['errors'],'cleanup persistence/identity/lock failure: '+repr(e)],End_required=True)
 finally:
  if token is not None:evidence.ACTIVE.reset(token)
  if fd is not None:os.close(fd) # close releases lease even if receipt/index failed
 # This sidecar is the exact public CLI stdout, separate from the sealed body
 # streams (the public reference cannot include its own hash). Never overwrite.
 public=json.dumps(value,ensure_ascii=False)+'\n'
 try:
  with (call/'return.stdout.txt').open('x') as f:f.write(public);f.flush();os.fsync(f.fileno())
  evidence.put(call/'RETURN-HASH.json',{'sha256':evidence.digest(call/'return.stdout.txt'),'bytes':len(public.encode()),'scope':'exact public stdout; no self-hash in output'})
 except BaseException as e:
  value.update(status='unknown',errors=[*value['errors'],'public return persistence failure: '+repr(e)],End_required=True);public=json.dumps(value,ensure_ascii=False)+'\n'
 sys.stdout.write(public);return value
if __name__=='__main__':
 try:result=cleanup()
 except BaseException as e:
  result={'schema':evidence.SCHEMA,'status':'unknown','errors':['cleanup allocation/identity failure: '+repr(e)],'End_required':True};print(json.dumps(result))
 raise SystemExit(0 if result['status'] in ('completed','already-cleaned') else 2)
