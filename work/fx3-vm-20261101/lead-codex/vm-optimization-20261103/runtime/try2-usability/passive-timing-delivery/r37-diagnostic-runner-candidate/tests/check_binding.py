from pathlib import Path
import ast,json,subprocess,sys,os,hashlib,time
O=Path(__file__).resolve().parents[1];S=O.parent/'r30-startup-observation-candidate'
# Finite owning-source side-effect review: main is never called on runner import;
# no target/process/browser actions are allowed in this test even if code drifts.
for p in [O/'run_trial_r24_review_snapshot.py',O/'runtime-wrapper/preflight.py',O/'prepare_run.py',*sorted((O/'operator-helpers').glob('*.py'))]:ast.parse(p.read_text())
pre=(O/'runtime-wrapper/preflight.py').read_text();assert 'run_name=\'r37_import_only\'' in pre and "'socket.__new__'" in pre
for name in ['deadline_cli.py','recovery_tools.py','review_snapshot_cli.py','planned_navigation_click.py','postkey_observation.py']:
 text=(O/'operator-helpers'/name).read_text();assert "if __name__" in text and ('parse_args' in text or 'main()' in text)
# Wrapper command execution policy: only diskutil read, help after audited guards,
# and import-only python children. No launch_prepare/start/QEMU/browser/QMP.
guard='''import sys,os,runpy
from pathlib import Path
root=Path(sys.argv[1]).resolve()
def audit(event,args):
 if event in ('socket.__new__','os.system','os.fork','os.posix_spawn'):raise RuntimeError('forbidden offline event:'+event)
 if event=='subprocess.Popen':
  argv=args[1]
  safe=(list(argv[:3])==['diskutil','info','-plist'] or (Path(argv[0]).name.startswith('python') and ((len(argv)>3 and argv[2]=='-c' and "run_name='r37_import_only'" in argv[3]) or (len(argv)>3 and '--help' in argv and Path(argv[2]).parent==root/'operator-helpers'))))
  if not safe:raise RuntimeError('forbidden offline child:'+str(argv))
 if event=='open':
  p,mode,flags=args
  if isinstance(p,(str,bytes)) and ((mode and any(c in mode for c in 'wax+')) or flags&0x603):
   if not Path(p).resolve().is_relative_to(root):raise RuntimeError('outside write:'+str(p))
 if event=='os.mkdir' and not Path(args[0]).resolve().is_relative_to(root):raise RuntimeError('outside mkdir')
sys.addaudithook(audit)
sys.path.insert(0,str(root/'runtime-wrapper'))
sys.argv=[str(root/'runtime-wrapper/preflight.py')]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
# Deterministic identity; exclusive prior output is refused by prepare.
out=O/'run-inputs'/('r37-preflight-ad037a8848b5-'+str(time.time_ns()));env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
a=[sys.executable,'-B',str(O/'prepare_run.py'),'--run-dir',str(out),'--task-id','task_ad037a8848b5','--dispatch-id','ctx_f0cb9c6c63e5','--session','fx3-deadline-r37-offline'];p=subprocess.run(a,capture_output=True,env=env)
for k,b in [('stdout',p.stdout),('stderr',p.stderr)]:(O/'receipts'/('prepare.'+k)).write_bytes(b)
assert not p.returncode,p.stderr.decode();env['FX3_NAV_RUN_DIR']=str(out)
a=[sys.executable,'-B','-c',guard,str(O)];p=subprocess.run(a,capture_output=True,env=env)
for k,b in [('stdout',p.stdout),('stderr',p.stderr)]:(O/'receipts'/('preflight.'+k)).write_bytes(b)
(O/'PREPARE-PREFLIGHT.json').write_text(json.dumps({'run_dir':str(out),'argv':a,'exit':p.returncode,'audit_policy':guard,'prepare_exit':0,'forbidden_entrypoints_executed':[]},indent=2)+'\n');assert not p.returncode,p.stderr.decode()
# Import entire actual dependency graph under a deny-process/socket/write hook.
code='''import runpy,sys,json,hashlib
from pathlib import Path
r=Path(sys.argv[1]).resolve()
def audit(event,args):
 if event in ('subprocess.Popen','socket.__new__','os.system','os.fork','os.posix_spawn','os.mkdir'):raise RuntimeError(event)
 if event=='open' and isinstance(args[0],(str,bytes)) and ((args[1] and any(c in args[1] for c in 'wax+')) or args[2]&0x603):raise RuntimeError('import write')
sys.addaudithook(audit)
g=runpy.run_path(str(r/'run_trial_r24_review_snapshot.py'),run_name='r37_import_only')
assert g['ACTIVE_GUARD'] is None and g['ACTIVE_STARTUP_OBSERVATION'] is None
mods={n:{'path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for n,m in sys.modules.items() if getattr(m,'__file__',None) and Path(m.__file__).is_file() and '/Volumes/KAFU2T/AI/Projects/Mac/' in str(m.__file__)}
print(json.dumps(mods))
'''
a=[sys.executable,'-B','-c',code,str(O)];p=subprocess.run(a,capture_output=True,env=env);(O/'receipts/import-graph.stdout').write_bytes(p.stdout);(O/'receipts/import-graph.stderr').write_bytes(p.stderr);assert not p.returncode,p.stderr.decode();mods=json.loads(p.stdout)
for key in ['r35_package_selection','trial_web_r24_review_snapshot','trial_ring_cached','trial_log_v4_mss','startup_observation']:assert Path(mods[key]['path']).parent==O
for key in ['qmp_line_transport','runtime_resource_guard','snapshot_tail_v15']:assert Path(mods[key]['path']).parent==O.parent/'v25-r21-recovery-integration'
(O/'ACTUAL-IMPORT-GRAPH.json').write_text(json.dumps({'argv':a,'modules':mods,'side_effects':'audit denies process/socket/mkdir/file writes; main not called'},indent=2)+'\n')
print('actual prepare/preflight/import-only checks PASS')
