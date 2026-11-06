#!/usr/bin/env python3
"""Small binding-only host checks. All action mains, process launch and sockets blocked on import."""
from pathlib import Path
import argparse,ast,contextlib,datetime,hashlib,importlib.util,json,os,subprocess,sys,types
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;D=O.parent;S=D/'r39-cleanup-evidence-candidate';P=D/'r42-command-timing-package'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def js(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def observe(paths,name,basis):
 js(name,dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),basis=basis,files={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in dict.fromkeys(paths)}))
def process(name,args,env=None):
 r=subprocess.run(args,capture_output=True,env=env,timeout=60)
 (O/'receipts'/f'{name}.stdout').write_bytes(r.stdout);(O/'receipts'/f'{name}.stderr').write_bytes(r.stderr)
 js('receipts/'+name+'.process.json',dict(argv=args,returncode=r.returncode,target_runner_main_started=False))
 assert r.returncode==0,(name,r.stderr[-1500:]);return r.stdout
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
@contextlib.contextmanager
def patch(m,**values):
 old={k:getattr(m,k) for k in values}
 for k,v in values.items():setattr(m,k,v)
 try:yield
 finally:
  for k,v in old.items():setattr(m,k,v)
def main():
 source=json.loads((O/'SOURCE-FREEZE.json').read_text());old=json.loads((S/'SOURCE-FREEZE.json').read_text())
 assert len(source)==43
 for n,h in source.items():assert sha(O/n)==h
 for n,h in old.items():assert sha(S/n)==h
 # Only four runtime text files differ, plus the generated core manifest.
 changed=[n for n in source if sha(S/n)!=sha(O/n)]
 assert set(changed)=={'r35_package_selection.py','run_trial_r24_review_snapshot.py','runtime-wrapper/preflight.py','return-tools/return_adapter.py','CORE-SOURCE-FREEZE.json'}
 runner=(O/'run_trial_r24_review_snapshot.py').read_text()
 assert runner.replace('仅另行授权时选择固定r42 command入口计时包；须snapshot-tail/N64','仅另行授权时选择固定r36包；须snapshot-tail/N64')==(S/'run_trial_r24_review_snapshot.py').read_text()
 q=(O/'runtime-wrapper/preflight.py').read_text().replace("group('r42_local_core'","group('r39_local_core'").replace("run_name='r42_import_only'","run_name='r39_import_only'").replace("run('r42-import-only'","run('r39-import-only'")
 assert q==(S/'runtime-wrapper/preflight.py').read_text()
 q=(O/'return-tools/return_adapter.py').read_text().replace(sha(O/'CORE-SOURCE-FREEZE.json'),sha(S/'CORE-SOURCE-FREEZE.json'))
 assert q==(S/'return-tools/return_adapter.py').read_text()
 # Selector AST: only declared bindings, pins, explanatory text and error labels may differ.
 def normalized(s):
  tree=ast.parse(s)
  class Normalize(ast.NodeTransformer):
   def visit_Expr(self,n):
    if isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):return ast.Pass()
    if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='PINS' and n.value.func.attr=='update':return ast.Pass()
    return self.generic_visit(n)
   def visit_Assign(self,n):
    if any(isinstance(t,ast.Name) and t.id in {'APPROVED_HOST','PACKAGE','CANDIDATE_SHA','CPIO_SHA','PROFILE','LABEL','PINS'} for t in n.targets):n.value=ast.Constant('DECLARED_BINDING')
    return self.generic_visit(n)
   def visit_Constant(self,n):
    if isinstance(n.value,str):
     n.value=n.value.replace('r42 regular','r39 regular').replace('r42 exclusive','r39 exclusive').replace('r42 frozen','r39 frozen').replace('r42 manifest','r36 manifest').replace('r42 CPIO','r36 CPIO')
    return n
  tree=Normalize().visit(tree)
  # Number of PINS.update declarations is allowed to increase; their contents independently frozen.
  tree.body=[n for n in tree.body if not isinstance(n,ast.Pass)]
  return ast.dump(tree,include_attributes=False)
 assert normalized((O/'r35_package_selection.py').read_text())==normalized((S/'r35_package_selection.py').read_text())
 js('EQUIVALENCE.json',dict(passed=True,byte_identical_files=[n for n in source if n not in changed],changed=changed,unchanged_file_count=len(source)-len(changed),runner_whole_file_inverse_equal=True,preflight_inverse_equal=True,return_adapter_inverse_equal=True,selector_binding_normalized_AST_equal=True,scope='no action, ready, server, cleanup, timing or resource policy change'))
 m=load('r42_selector_test',O/'r35_package_selection.py')
 F=D/'v25-r21-recovery-integration'
 # Preserve old protocol but do not invoke its broad historical hash scan/main again.
 observe([D/n for n in m.PINS]+[F/'SOURCE-FREEZE.json',Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/manifest.json')], 'INPUTS-ADDITIONAL-2.json','later first-observed input pins, before selector/import/planned-argv checks; no inherited 1398-item scan')
 run=O/'run-inputs/preflight-926a20c9ff87';run.parent.mkdir()
 prepare_args=[sys.executable,'-B',str(O/'prepare_run.py'),'--run-dir',str(run),'--task-id','task_926a20c9ff87','--dispatch-id','ctx_d991d9f90265','--session','fx3-deadline-r42-offline-926a20c9ff87']
 prep=json.loads(process('prepare',prepare_args));assert prep['status']=='prepared_only_no_process_started' and prep['config']['runner_profile']=='r41-entry-timing-r42'
 receipt=m.verify_package(run);assert receipt['profile']=='r41-entry-timing-r42' and receipt['package_root']==str(P) and receipt['label']=='v41timing-n64-r42'
 js('PACKAGE-SELECTION.json',receipt)
 tests=[]
 def reject(name,fn):
  try:fn()
  except (ValueError,AssertionError,FileNotFoundError) as e:tests.append(dict(name=name,rejected=True,reason=str(e)))
  else:raise AssertionError('unexpected accept '+name)
 base=dict(r35_diagnostic_package=True,snapshot_tail=True,gate_publish_interval=64,review_procdiag_r4e=False,internal_hoststep=False)
 m.options(types.SimpleNamespace(**base))
 for k,v in [('snapshot_tail',False),('gate_publish_interval',1),('review_procdiag_r4e',True),('internal_hoststep',True)]:reject('wrong_options_'+k,lambda k=k,v=v:m.options(types.SimpleNamespace(**{**base,k:v})))
 # The selector is a pure no-side-effect module; production pins are restored after each fault.
 with patch(m,CANDIDATE_SHA='0'*64):reject('wrong_candidate_hash',lambda:m.verify_package(run))
 with patch(m,CPIO_SHA='0'*64):reject('wrong_CPIO_hash_field',lambda:m.verify_package(run))
 with patch(m,CPIO_BYTES=1):reject('wrong_CPIO_size',lambda:m.verify_package(run))
 with patch(m,PACKAGE=D/'r36-fixed-slot-package'):reject('old_package_path_no_fallback',lambda:m.verify_package(run))
 with patch(m,PACKAGE=P/'missing'):reject('missing_new_package_no_fallback',lambda:m.verify_package(run))
 with patch(m,APPROVED_HOST=S):reject('wrong_host_identity',lambda:m.output_root(run))
 reject('foreign_output',lambda:m.output_root(S/'run-inputs/preflight-926a20c9ff87'))
 reject('traversing_output',lambda:m.output_root(O/'run-inputs/..'/'preflight-926a20c9ff87'))
 original_sha=m.sha
 with patch(m,sha=lambda p:'0'*64 if Path(p)==P/'guest.cpio' else original_sha(p)):reject('actual_CPIO_hash_mismatch',lambda:m.verify_package(run))
 # Simulate a correctly-read manifest resolving an unapproved path/platform: production digest still independently fixed.
 c=json.loads((P/'candidate.json').read_text());original_loads=m.json.loads
 for name,alter in [('initrd_path',{'initrd':{**c['initrd'],'path':str(D/'r36-fixed-slot-package/guest.cpio')}}),('dtb_path',{'dtb':{**c['dtb'],'path':str(P/'guest.cpio')}}),('memory',{'memory_mib':2048}),('load_address',{'initrd_load_address':'0x440000004'})]:
  with patch(m.json,loads=lambda s,alter=alter:{**c,**alter}):reject('manifest_'+name,lambda:m.verify_package(run))
 assert m.json.loads is original_loads
 js('SELECTOR-TESTS.json',dict(passed=True,positive_exact_package=receipt,negative_cases=tests,count=len(tests),scope='actual selector functions; controlled in-memory fault injection; no processes launched by selector'))
 # Inspect every local Python top level before imports. The runner main is never called.
 local_py=[O/n for n in source if n.endswith('.py')]
 for p in local_py:ast.parse(p.read_text())
 code=r'''import sys,runpy,json,hashlib,os
from pathlib import Path
r=Path(sys.argv[1]);sys.path.insert(0,str(r));sys.path.insert(1,str(r/'runtime-wrapper'))
blocked=[]
def audit(event,args):
 if event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','socket.__new__','os.mkdir','os.remove','os.rename','os.rmdir','os.chmod'):
  blocked.append(event);raise RuntimeError('forbidden import side effect:'+event)
 if event=='open' and isinstance(args[0],(str,bytes)) and ((args[1] and any(c in args[1] for c in 'wax+')) or args[2]&0x603):
  blocked.append('open-write');raise RuntimeError('import write')
sys.addaudithook(audit)
g=runpy.run_path(str(r/'run_trial_r24_review_snapshot.py'),run_name='r42_import_only')
assert g['ACTIVE_GUARD'] is None and g['ACTIVE_STARTUP_OBSERVATION'] is None
assert g['R35_PACKAGE']==r.parent/'r42-command-timing-package'
assert g['R35_MANIFEST_SHA']==hashlib.sha256((r.parent/'r42-command-timing-package/candidate.json').read_bytes()).hexdigest()
assert g['R35_LABEL']=='v41timing-n64-r42'
import common,cleanup,operate,audit_after,cleanup_evidence,preflight,launch_prepare,start_and_wait,later_capture
runpy.run_path(str(r/'return-tools/return_adapter.py'),run_name='r42_adapter_import_only')
mods={n:{'path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for n,m in sys.modules.items() if getattr(m,'__file__',None) and Path(m.__file__).is_file() and '/Volumes/KAFU2T/AI/Projects/Mac/' in str(m.__file__)}
for n in ('startup_observation','trial_ring_cached','trial_log_v4_mss','trial_web_r24_review_snapshot','r35_package_selection'):assert Path(mods[n]['path']).parent==r
for n in ('common','cleanup','operate','audit_after','cleanup_evidence','preflight','launch_prepare','start_and_wait','later_capture'):assert Path(mods[n]['path']).parent==r/'runtime-wrapper'
for n in ('qmp_line_transport','gate_input_usability','runtime_resource_guard'):assert Path(mods[n]['path']).parent==r.parent/'v25-r21-recovery-integration'
print(json.dumps({'mode':'actual imports; action mains never called','modules':mods,'blocked_attempts':blocked,'runner':str(r/'run_trial_r24_review_snapshot.py'),'adapter':str(r/'return-tools/return_adapter.py')}))
'''
 binding=json.loads(process('actual-import-only',[sys.executable,'-B','-c',code,str(O)],{**os.environ,'PYTHONDONTWRITEBYTECODE':'1','FX3_NAV_RUN_DIR':str(run)}))
 assert not binding['blocked_attempts']
 allowed={str(O/n):h for n,h in source.items()};allowed.update({str(F/n):h for n,h in json.loads((F/'SOURCE-FREEZE.json').read_text()).items()})
 for n,v in binding['modules'].items():assert allowed.get(v['path'])==v['sha256'],(n,v)
 js('IMPORT-BINDING.json',binding)
 observe([Path(x['path']) for x in binding['modules'].values()], 'INPUTS-IMPORT-OBSERVED.json','actual loaded modules hashed immediately after guarded import; first-observed post-read pins, not task-start snapshots')
 # Execute ONLY original AST command-list construction and pure option/selector expressions.
 tree=ast.parse(runner);main_ast=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
 start=next(i for i,n in enumerate(main_ast.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='args' for t in n.targets))
 end=next(i for i,n in enumerate(main_ast.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in n.targets))
 command_nodes=main_ast.body[start:end+1]
 assert all(not isinstance(n,(ast.With,ast.Try,ast.While,ast.For)) for n in command_nodes)
 baseline=json.loads(Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/manifest.json').read_text())
 files=[Path(c['qemu']['path']),Path(c['dtb']['path']),Path(baseline['kernel']['path'])]
 observe(files,'INPUTS-PLATFORM.json','later observed platform file hashes before planned command-only construction; no launch')
 assert sha(files[0])=='bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d'
 assert sha(files[1])=='5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b'
 assert sha(files[2])=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
 def plan(candidate,root):
  ns=types.SimpleNamespace(tcg_thread='multi',smp=4,icount_shift=None,trace_seconds=0,seconds=480)
  g=dict(os=os,ns=ns,candidate=candidate,qemu=files[0],run=run/'PLAN-ONLY-NO-NATIVE-RUN',baseline=baseline,initrd=Path(candidate['initrd']['path']),dtb=files[1],candidate_path=root/'candidate.json',digest=sha,snapshots=[])
  exec(compile(ast.Module(body=command_nodes,type_ignores=[]),'<actual runner command AST only>','exec'),g)
  return g['command']
 newcmd=plan(c,P);oldcmd=plan(json.loads((D/'r36-fixed-slot-package/candidate.json').read_text()),D/'r36-fixed-slot-package')
 aa=[a.replace(str(P/'guest.cpio'),'<EXACT-INITRD>') for a in newcmd['args']];bb=[a.replace(str(D/'r36-fixed-slot-package/guest.cpio'),'<EXACT-INITRD>') for a in oldcmd['args']]
 assert aa==bb and newcmd['model_env']==oldcmd['model_env']
 assert '-icount' not in newcmd['args'] and newcmd['smp']==4 and newcmd['tcg_thread']=='multi'
 js('PLANNED-ARGV.json',dict(mode='unexecuted; actual AST list/env construction only, not main',launch_wrapper_argv=['python3','-B',str(O/'run_trial_r24_review_snapshot.py'),'--port','0','--max-minutes','8','--max-steps','32','--snapshot-tail','--gate-publish-interval','64','--pre-input-snapshot-step','2','--r35-diagnostic-package'],label=m.LABEL,profile=m.PROFILE,package_selection=receipt,command=newcmd,previous_package_command=oldcmd,platform_args_equal_after_only_initrd_path_normalization=True,model_env_equal=True,run_path_placeholder=True,snapshots_list_empty_for_plan_only=True,actual_snapshot_policy_unchanged=True))
 # Actual Node adapter imports with side effects guarded before dynamic import; no action executed.
 node_code=r'''import cp from 'node:child_process';import fs from 'node:fs';import net from 'node:net';import {syncBuiltinESMExports} from 'node:module';import {pathToFileURL} from 'node:url';
const deny=()=>{throw Error('r42 import side effect blocked')};
for(const n of ['exec','execFile','execSync','execFileSync','spawn','spawnSync','fork'])cp[n]=deny;
for(const n of ['writeFile','writeFileSync','appendFile','appendFileSync','mkdir','mkdirSync','rename','renameSync','unlink','unlinkSync'])fs[n]=deny;
net.createServer=deny;net.connect=deny;net.createConnection=deny;syncBuiltinESMExports();
const root=process.argv[1];const mods={};for(const n of ['show_result.mjs','tool_call.mjs','short_tool.mjs'])mods[n]=Object.keys(await import(pathToFileURL(root+'/return-tools/'+n)));
console.log(JSON.stringify({mode:'guarded dynamic imports only; no bind/action called',root,modules:mods}));'''
 node=json.loads(process('node-import-only',['node','--input-type=module','-e',node_code,str(O)]));js('NODE-BINDING.json',node)
 js('HOST-CHECKS.json',dict(passed=True,selector_negative_count=len(tests),actual_prepare=prep,import_modules=len(binding['modules']),source_count=len(source),core_count=len(json.loads((O/'CORE-SOURCE-FREEZE.json').read_text())),no_target_main_called=True,no_VM=True,no_browser=True,no_service=True,no_QMP=True,no_deployment=True,historical_tests_reused_not_rerun=['r39 cleanup40/boundaries6/Node5; coordinator accepted','r41 actual-source host5/parser18/ELF/cost; coordinator accepted']))
 print(json.dumps({'passed':True,'selector_negative_count':len(tests),'actual_import_modules':len(binding['modules']),'run_dir':str(run)}))
if __name__=='__main__':main()
