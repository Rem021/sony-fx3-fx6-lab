from pathlib import Path
import ast,json,sys,types,unittest.mock as mock,argparse,contextlib,io,os,subprocess,hashlib
O=Path(__file__).resolve().parents[1];S=O.parent/'r30-startup-observation-candidate';sys.path.insert(0,str(O));import r35_package_selection as sel
out=Path(json.loads((O/'PREPARE-PREFLIGHT.json').read_text())['run_dir']);results=[]
def record(name,**kw):results.append({'case':name,**kw})
# Extract actual argument/selection prefix, stopping before diskutil/read or any
# run directory/guard/server. No runner main/launch entry is ever called.
def prefix(path):
 s=path.read_text();t=ast.parse(s);f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='main');nodes=[]
 for n in f.body:
  if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='vol' for v in n.targets):break
  if not isinstance(n,ast.Global):nodes.append(n)
 return nodes
def parse(path,args):
 ns={'argparse':argparse,'HERE':path.parent,'DATA_ROOT':out,'valid_command':lambda *a:True,'R35_PACKAGE':sel.PACKAGE,'R35_MANIFEST_SHA':sel.CANDIDATE_SHA,'R35_LABEL':sel.LABEL,'r35_options':sel.options,'verify_r35_package':lambda p:{'test':'already independently verified'}}
 with mock.patch.object(sys,'argv',[str(path),*args]),mock.patch.object(subprocess,'Popen',side_effect=AssertionError('process forbidden')):
  exec(compile(ast.Module(prefix(path),[]),str(path),'exec'),ns)
 return ns
old=S/'run_trial_r24_review_snapshot.py';new=O/old.name
modes=[[],['--review-procdiag-r4e'],['--snapshot-tail','--gate-publish-interval','1'],['--snapshot-tail','--gate-publish-interval','64'],['--snapshot-tail']]
for a in modes:
 x=parse(old,a);y=parse(new,a)
 for k in ['selected_root']:assert x[k]==y[k]
 for k in ['candidate','label','seconds','smp','tcg_thread','icount_shift','trace_seconds']:assert getattr(x['ns'],k)==getattr(y['ns'],k)
 record('old-selection-preserved',argv=a,root=str(y['selected_root']),label=y['ns'].label)
valid=['--snapshot-tail','--gate-publish-interval','64','--r35-diagnostic-package'];v=parse(new,valid);assert v['selected_root']==sel.PACKAGE and v['ns'].label==sel.LABEL
for a in [['--r35-diagnostic-package'],['--r35-diagnostic-package','--snapshot-tail'],['--r35-diagnostic-package','--snapshot-tail','--gate-publish-interval','1'],valid+['--review-procdiag-r4e'],valid+['--internal-hoststep'],valid+['--candidate','/tmp/unreviewed'],valid+['--unknown-package']]:
 with contextlib.redirect_stderr(io.StringIO()):
  try:parse(new,a);raise AssertionError('invalid args accepted')
  except SystemExit as e:assert e.code==2
 record('invalid-args-before-any-process',argv=a)
# Actual strict fixed-root/pins/CPIO size/hash, read only. No guest/frame simulation.
r=sel.verify_package(out);assert r['candidate_sha256']==sel.CANDIDATE_SHA;record('actual-package-verified',selection=r)
original_sha=sel.sha
for label,target in [('manifest',sel.PACKAGE/'candidate.json'),('cpio',sel.PACKAGE/'guest.cpio'),('r36-freeze',sel.PACKAGE/'SHA256SUMS')]:
 with mock.patch.object(sel,'sha',side_effect=lambda p: '0'*64 if Path(p)==target else original_sha(p)):
  try:sel.verify_package(out);raise AssertionError(label)
  except ValueError:pass
 record('injected-'+label+'-identity-rejection',zero_processes=True)
with mock.patch.object(sel,'CPIO_BYTES',453213883):
 try:sel.verify_package(out);raise AssertionError('size')
 except ValueError:pass
record('CPIO-size-rejection')
for absent in [sel.PACKAGE/'candidate.json',sel.PACKAGE/'guest.cpio']:
 old_regular=sel.exact_regular
 with mock.patch.object(sel,'exact_regular',side_effect=lambda p: (_ for _ in ()).throw(ValueError('missing fixed package')) if Path(p)==absent else old_regular(p)):
  try:sel.verify_package(out);raise AssertionError('implicit fallback')
  except ValueError:pass
 record('fixed-r36-member-missing-no-N64-fallback',path=str(absent))
for p in [O.parent/'r30-startup-observation-candidate',Path('/tmp/out'),O/'run-inputs',Path('relative'),O/'run-inputs/a/child']:
 try:sel.output_root(p);raise AssertionError(p)
 except ValueError:pass
link=O/'tests/output-link';link.symlink_to(out,target_is_directory=True)
try:
 try:sel.output_root(link);raise AssertionError('symlink')
 except ValueError:pass
finally:link.unlink()
record('output-boundary-and-symlink-rejection')
# Read original command constructor AST directly, no execution of preceding run,
# locks, observer copies, guard, server, QMP or launch_prepare.
def command(path,mode):
 t=ast.parse(path.read_text());f=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='main');body=f.body
 start=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='qemu' for v in n.targets));end=next(i for i,n in enumerate(body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='write_text' and "'command.json'" in ast.unparse(n));nodes=body[start:end]
 selected=sel.PACKAGE if mode else O.parent/'r16-fixed-slot-guests/guest-N64';candidate_path=selected/'candidate.json';c=json.loads(candidate_path.read_text());baseline=json.loads(Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/manifest.json').read_text());ns=types.SimpleNamespace(tcg_thread='multi',smp=4,icount_shift=None,trace_seconds=0,seconds=480,r35_diagnostic_package=mode)
 g={'FROZEN':Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm'),'ROOT':Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime'),'candidate':c,'baseline':baseline,'input_check':lambda x:Path(x['path']),'checks':[],'ns':ns,'run':out/'PLANNED-NOT-CREATED','initrd':Path(c['initrd']['path']),'dtb':Path(c['dtb']['path']),'os':os,'candidate_path':candidate_path,'digest':original_sha,'snapshots':[],'r35_selection_receipt':r}
 with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('process forbidden')):exec(compile(ast.Module(nodes,[]),str(path),'exec'),g)
 return g['command']
x=command(old,False);y=command(new,True);a=x['args'];b=y['args'];changes=[(i,u,z) for i,(u,z) in enumerate(zip(a,b)) if u!=z];assert len(a)==len(b) and len(changes)==1;assert changes[0][1].startswith('loader,file=') and changes[0][2]=='loader,file='+str(sel.PACKAGE/'guest.cpio')+',addr=0x440000000,force-raw=on'
for k in set(x)-{'args','candidate','candidate_sha256'}:assert x[k]==y[k],k
assert b[b.index('-cpu')+1]=='cortex-a35' and b[b.index('-smp')+1]=='4' and b[b.index('-m')+1]=='5120' and b[b.index('-accel')+1]=='tcg,thread=multi' and '-icount' not in b
(O/'PLANNED-ARGV.json').write_text(json.dumps({'basis':'actual constructor AST only; not runner/main/launch execution','old_N64':x,'new_r36':y,'argv_changed_items':changes,'run_label':sel.LABEL,'load_addresses':{'DTB':'0x400002000','CPIO':'0x440000000'},'model_env_identical':x['model_env']==y['model_env']},indent=2)+'\n');record('actual-argv-constructor-platform-identical-only-loader-path-changed')
(O/'SELECTION-TESTS.json').write_text(json.dumps({'cases':results,'count':len(results),'no_process_or_service_started_by_selection_tests':True},indent=2)+'\n');print('selector/old modes/faults/actual argv AST checks PASS',len(results))
