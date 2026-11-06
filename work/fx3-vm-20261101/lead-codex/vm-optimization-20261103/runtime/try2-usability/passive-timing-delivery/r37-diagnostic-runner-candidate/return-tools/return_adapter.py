#!/usr/bin/env python3
"""Run one frozen operate action; retain full child streams and publish only this invocation."""
import argparse,hashlib,json,os,plistlib,shutil,subprocess,sys,time,uuid
from pathlib import Path
FROZEN=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(FROZEN))
from r35_package_selection import output_root,PROFILE
OPERATE=FROZEN/'runtime-wrapper/operate.py'
OPERATE_SHA='97e41bc5687fd6c9397fcca639355624c70e368761e1e24ad4329a85d9408741'
CORE_FREEZE_SHA='7752a6fd7cdb74def7a3cfa9659ed6a1a4f6ab23708a5aaaed5f345e7c46f303'
VOLUME='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
MAX_SUMMARY_BYTES=4096
ACTIONS={'click':3,'observe':2,'pin':2,'confirm':2,'standby_review':2,'recovery_review':2,'recovery_cancel':2,'reject':2}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def put(path,value):
 with Path(path).open('x') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n');f.flush();os.fsync(f.fileno())
def regular(path):
 p=Path(path)
 if not p.is_absolute() or p.is_symlink() or not p.is_file():raise ValueError('regular_absolute_file_required')
 return p

def _execute_once(argv,action,run_dir,out,env):
 """Private injection seam for offline tests; production argv is constructed below, never supplied by CLI."""
 run_dir=Path(run_dir).resolve();out=Path(out);out.mkdir() # exclusive invocation; no old result fallback
 out=out.resolve();started=time.time_ns();call_id=str(uuid.uuid4())
 put(out/'invocation.json',{'call_id':call_id,'action':action,'run_dir':str(run_dir),'argv':argv,'wall_start_ns':started,'fixture_only':env.get('FX3_RETURN_FIXTURE_ONLY')=='1'})
 result={'adapter_schema':'fx3-tool-return-v1','call_id':call_id,'action':action,'run_dir':str(run_dir),'status':'return_failed','ok':False,'receipt_path':str(out/'child.stdout.json'),'stderr_path':str(out/'child.stderr.txt'),'image':None,'fixture_only':env.get('FX3_RETURN_FIXTURE_ONLY')=='1'}
 code=2
 try:
  with (out/'child.stdout.json').open('xb') as stdout,(out/'child.stderr.txt').open('xb') as stderr:
   p=subprocess.run(argv,env=env,stdout=stdout,stderr=stderr,check=False) # no timeout/retry/extra action
   stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
  put(out/'process.json',{'returncode':p.returncode,'wall_start_ns':started,'wall_end_ns':time.time_ns(),'stdout_sha256':sha(out/'child.stdout.json'),'stderr_sha256':sha(out/'child.stderr.txt')})
  result['child_returncode']=p.returncode
  if p.returncode!=0:raise ValueError('original_child_nonzero_End_required_no_image')
  value=json.loads((out/'child.stdout.json').read_text()) # only the full current child file
  if type(value) is not dict:raise ValueError('child_result_not_object')
  status=value.get('status');image_kind=None
  if status=='qualified_unpinned_postkey_observation':
   if action not in ('click','observe') or value.get('schema')!='fx3-postkey-observation-r26-v1' or value.get('snapshot_pinned') is not False or value.get('postkey_confirmation') is not False:raise ValueError('observation_schema_or_action')
   image_kind='unpinned_postkey_observation';step=value['binding']['step'];attempt=value['binding']['attempt_id']
  elif status=='qualified_review_snapshot':
   if action!='pin' or value.get('capture_schema')!='fx3-r24-snapshot-capture-v1':raise ValueError('fixed_snapshot_schema_or_action')
   image_kind='fixed_postkey_snapshot';step=value['snapshot']['step'];attempt=value['snapshot']['attempt_id']
  elif status=='qualified_recovery_observation':
   if action!='click':raise ValueError('recovery_observation_action')
   image_kind='unqueued_recovery_observation';step=value['step'];attempt=value.get('attempt')
  elif status=='cancelled_unqueued_alarm_only':
   if action!='recovery_cancel' or value.get('observation_status')!='qualified_recovery_observation':raise ValueError('cancel_recovery_observation')
   image_kind='cancelled_recovery_observation';step=value.get('step');attempt=value.get('attempt')
  else:
   allowed={'confirm':'confirmed_and_cancelled','standby_review':'initial_standby_review_recorded','recovery_review':'explicit_recovery_image_reviewed'}
   if action not in allowed or allowed[action]!=status:raise ValueError('unexpected_status_no_fallback')
   step=value.get('step');attempt=value.get('attempt_id')
  if image_kind:
   source=regular(value['screenshot_path'])
   if not source.resolve().is_relative_to(run_dir) or source.stat().st_mtime_ns<started:raise ValueError('stale_or_outside_current_task_PNG')
   data=source.read_bytes();digest=hashlib.sha256(data).hexdigest()
   if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)>16*1024*1024 or digest!=value['screenshot_sha256']:raise ValueError('actual_PNG_hash_or_format')
   if image_kind=='fixed_postkey_snapshot' and (digest!=value['snapshot']['PNG_sha256'] or len(data)!=value['snapshot']['byte_length']):raise ValueError('fixed_PNG_binding')
   # A new immutable transport copy; no resize or image transformation.
   with (out/'returned.png').open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
   result['image']={'path':str(out/'returned.png'),'sha256':digest,'scope':image_kind}
  result.update(status=status,step=step,attempt=attempt,ok=True);code=0
 except BaseException as e:
  result.update(status='return_failed',ok=False,image=None,error_kind=type(e).__name__,reason=str(e)[:180],End_required=True)
 # This bounded file is read with filesystem APIs, never parsed from terminal screen text.
 encoded=json.dumps(result,ensure_ascii=False,separators=(',',':'))
 if len(encoded.encode())>MAX_SUMMARY_BYTES:
  result={'adapter_schema':'fx3-tool-return-v1','call_id':call_id,'action':action,'run_dir':str(run_dir),'ok':False,'status':'return_failed','image':None,'End_required':True,'reason':'summary_limit'};code=2
 put(out/'summary.json',result)
 print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 return code

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('operation',nargs=argparse.REMAINDER);a=p.parse_args()
 assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']==VOLUME
 assert sha(FROZEN/'CORE-SOURCE-FREEZE.json')==CORE_FREEZE_SHA and sha(OPERATE)==OPERATE_SHA
 for f,h in json.loads((FROZEN/'CORE-SOURCE-FREEZE.json').read_text()).items():assert sha(FROZEN/f)==h
 args=a.operation
 if args and args[0]=='--':args=args[1:]
 if not args or args[0] not in ACTIONS or len(args)!=ACTIONS[args[0]]:p.error('one exact original action and its arguments required')
 if args[0]=='click' and args[1] not in [str(x) for x in range(1,9)]:p.error('fixed plan step 1..8')
 run=output_root(Path(a.run_dir));out=Path(a.output_dir)
 cfg=json.loads((run/'config.json').read_text())
 assert cfg['candidate_source_root']==str(FROZEN) and cfg['runner_profile']==PROFILE
 expected={str(FROZEN/f):h for f,h in json.loads((FROZEN/'SOURCE-FREEZE.json').read_text()).items()}
 assert json.loads((run/'LOCAL-SOURCE-FREEZE.json').read_text())==expected
 if not run.is_dir() or not (run/'runtime.json').is_file() or not (run/'config.json').is_file():p.error('existing explicitly authorized run required')
 if not out.is_absolute() or out.exists() or not out.parent.is_dir() or not out.parent.resolve().is_relative_to(run):p.error('new output directory under current task run required')
 env={**os.environ,'FX3_NAV_RUN_DIR':str(run),'PYTHONDONTWRITEBYTECODE':'1'}
 env.pop('FX3_RETURN_FIXTURE_ONLY',None)
 return _execute_once(['python3','-B',str(OPERATE),*args],args[0],run,out,env)
if __name__=='__main__':raise SystemExit(main())
