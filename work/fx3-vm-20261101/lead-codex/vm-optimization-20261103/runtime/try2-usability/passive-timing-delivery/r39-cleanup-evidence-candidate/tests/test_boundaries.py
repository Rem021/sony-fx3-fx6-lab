"""Actual common and adapter CLI reject old source/profile/freeze before action dispatch."""
from pathlib import Path
import ast,json,os,subprocess,sys,uuid,hashlib
O=Path(__file__).resolve().parents[1]
t=ast.parse((O/'tests/test_cleanup.py').read_text());exec(compile(ast.Module([n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in ('sha','put','make')],type_ignores=[]),'fixture-factory-only','exec'))
rows=[]
for case in ('old-source','old-profile','missing-local-freeze'):
 h=make('boundary-'+case);cfg=json.loads((h/'config.json').read_text())
 if case=='old-source':cfg['candidate_source_root']=str(O.parent/'r37-diagnostic-runner-candidate');put(h/'config.json',cfg)
 elif case=='old-profile':cfg['runner_profile']='r35-diagnostic-r36-n64';put(h/'config.json',cfg)
 else:
  v=json.loads((h/'LOCAL-SOURCE-FREEZE.json').read_text());v.pop(str(O/'runtime-wrapper/cleanup_evidence.py'));put(h/'LOCAL-SOURCE-FREEZE.json',v)
 env={**os.environ,'FX3_NAV_RUN_DIR':str(h),'PYTHONDONTWRITEBYTECODE':'1'}
 for mode in ('common','adapter'):
  code='''import runpy,sys
from pathlib import Path
r=Path(sys.argv[1]);mode=sys.argv[2];out=Path(sys.argv[3]);sys.path.insert(0,str(r/'runtime-wrapper'))
def audit(event,args):
 if event in ('socket.__new__','os.system','os.fork','os.posix_spawn'):raise RuntimeError('FORBIDDEN action:'+event)
 if event=='subprocess.Popen' and args[1]!=['diskutil','info','-plist','/Volumes/KAFU2T']:raise RuntimeError('FORBIDDEN child:'+str(args[1]))
sys.addaudithook(audit)
if mode=='common':import common
else:
 sys.argv=[str(r/'return-tools/return_adapter.py'),'--run-dir',str(out.parent),'--output-dir',str(out),'--','pin','fixture rejection only']
 runpy.run_path(str(r/'return-tools/return_adapter.py'),run_name='__main__')
'''
  out=h/('must-not-create-'+mode);argv=[sys.executable,'-B','-c',code,str(O),mode,str(out)];p=subprocess.run(argv,env=env,capture_output=True)
  prefix=O/'receipts'/('boundary-'+case+'-'+mode)
  Path(str(prefix)+'.stdout').write_bytes(p.stdout);Path(str(prefix)+'.stderr').write_bytes(p.stderr)
  assert p.returncode!=0 and not out.exists() and b'AssertionError' in p.stderr and b'FORBIDDEN' not in p.stderr,(case,mode,p.stderr)
  rows.append({'case':case,'entry':mode,'exit':p.returncode,'output_not_created':True,'no_action_dispatch':True,'stdout':str(prefix)+'.stdout','stderr':str(prefix)+'.stderr'})
(O/'BOUNDARY-TESTS.json').write_text(json.dumps({'passed':True,'fixture_only':True,'cases':rows},indent=2)+'\n');print('PASS 6 actual root/profile/local-freeze boundary rejections')
