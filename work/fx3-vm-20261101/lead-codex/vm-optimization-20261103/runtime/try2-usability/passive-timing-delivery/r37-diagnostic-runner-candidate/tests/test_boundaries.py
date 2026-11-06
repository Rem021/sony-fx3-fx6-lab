from pathlib import Path
import json,subprocess,sys,os,shutil,time
O=Path(__file__).resolve().parents[1];good=Path(json.loads((O/'PREPARE-PREFLIGHT.json').read_text())['run_dir']);results=[]
# Execute real common/adapter validation paths. Only diskutil is permitted as
# an auxiliary child; a launch of operate/browser or any socket is a test failure.
guard='''import sys,runpy
from pathlib import Path
root=Path(sys.argv[1]);script=sys.argv[2];sys.argv=[script,*sys.argv[3:]]
def audit(event,args):
 if event in ('socket.__new__','os.system','os.fork','os.posix_spawn'):raise RuntimeError('forbidden:'+event)
 if event=='subprocess.Popen' and list(args[1][:3])!=['diskutil','info','-plist']:raise RuntimeError('forbidden child:'+str(args[1]))
 if event=='open' and isinstance(args[0],(str,bytes)) and ((args[1] and any(c in args[1] for c in 'wax+')) or args[2]&0x603):raise RuntimeError('unexpected write')
sys.addaudithook(audit);sys.path.insert(0,str(root/'runtime-wrapper'));runpy.run_path(script,run_name='__main__')
'''
basecfg=json.loads((good/'config.json').read_text());basefreeze=json.loads((good/'LOCAL-SOURCE-FREEZE.json').read_text())
for name in ['wrong-profile','old-source-root','missing-local-freeze-entry','outside-output']:
 d=O/'run-inputs'/('boundary-'+name+'-'+str(time.time_ns()));d.mkdir();cfg=dict(basecfg);freeze=dict(basefreeze)
 if name=='wrong-profile':cfg['runner_profile']='old-N64'
 if name=='old-source-root':cfg['candidate_source_root']=str(O.parent/'r30-startup-observation-candidate')
 if name=='missing-local-freeze-entry':freeze.pop(next(iter(freeze)))
 for f,v in [('config.json',cfg),('LOCAL-SOURCE-FREEZE.json',freeze),('runtime.json',{'fixture':True})]:(d/f).write_text(json.dumps(v))
 env={**os.environ,'FX3_NAV_RUN_DIR':str(d),'PYTHONDONTWRITEBYTECODE':'1'}
 for script in ([O/'runtime-wrapper/common.py',O/'return-tools/return_adapter.py'] if name!='outside-output' else [O/'return-tools/return_adapter.py']):
  op=['--run-dir',str(d),'--output-dir',str(O/'tests/outside-return'),'--','confirm','fixture-no-review'] if script.name=='return_adapter.py' else []
  args=[sys.executable,'-B','-c',guard,str(O),str(script),*op];p=subprocess.run(args,capture_output=True,env=env);assert p.returncode and b'forbidden child:' not in p.stderr and b'unexpected write' not in p.stderr,p.stderr.decode();assert not (O/'tests/outside-return').exists();results.append({'case':name,'script':str(script),'argv':args,'exit':p.returncode,'stderr':p.stderr.decode()})
# Invalid prepare directory/session and duplicate exclusive mkdir cannot write originals.
for name,run,session in [('outside',str(O.parent/'r30-startup-observation-candidate'),'fx3-deadline-test'),('relative','relative','fx3-deadline-test'),('bad-session',str(O/'run-inputs/r37-ad037a8848b5-bad'),'default'),('duplicate',str(good),'fx3-deadline-test')]:
 a=[sys.executable,'-B',str(O/'prepare_run.py'),'--run-dir',run,'--task-id','task_ad037a8848b5','--dispatch-id','ctx_f0cb9c6c63e5','--session',session];p=subprocess.run(a,capture_output=True);assert p.returncode;results.append({'case':'prepare-'+name,'argv':a,'exit':p.returncode,'stderr':p.stderr.decode()})
(O/'BOUNDARY-TESTS.json').write_text(json.dumps({'cases':results,'count':len(results),'operator_browser_QMP_never_invoked':True,'fixture_configs_not_runtime_evidence':True},indent=2)+'\n');print('actual prepare/common/adapter refusal paths PASS',len(results))
