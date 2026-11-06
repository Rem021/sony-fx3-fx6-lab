"""Read-only source/input/import audit; never runner main or VM."""
import ast,difflib,hashlib,importlib.util,json,os,runpy,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent;B=R.parent/'r26-postkey-observation-candidate';sys.dont_write_bytecode=True
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):(R/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
before=json.loads((R/'INPUTS-BEFORE.json').read_text());after={p:sha(p) for p in before};assert before==after;save('INPUTS-AFTER.json',after)
base=json.loads((B/'CANDIDATE-SOURCE-FREEZE.json').read_text());delta=[];diff=[]
for f,h in base.items():
 assert sha(B/f)==h;delta.append({'path':f,'baseline_sha256':h,'candidate_sha256':sha(R/f),'same_bytes':h==sha(R/f)})
 if h!=sha(R/f):diff.extend(difflib.unified_diff((B/f).read_text().splitlines(True),(R/f).read_text().splitlines(True),fromfile='r26/'+f,tofile='r28/'+f))
save('SOURCE-REUSE.json',delta);(R/'MINIMAL-CORE.diff').write_text(''.join(diff))
core=json.loads((R/'CORE-SOURCE-FREEZE.json').read_text());assert all(sha(R/f)==h for f,h in core.items())
production=[R/f for f in core]+[p for p in sorted((R/'return-tools').iterdir()) if p.is_file()]+[R/'CORE-SOURCE-FREEZE.json']
save('SOURCE-FREEZE.json',{str(p.relative_to(R)):sha(p) for p in production})
for p in [*production,*R.glob('*.py')]:
 if p.suffix=='.py':ast.parse(p.read_text())
for p in [*sorted((R/'operator-helpers').glob('*.js')),*sorted((R/'return-tools').glob('*.mjs')),R/'rehearsal_tools.mjs',R/'review_page_r24.js',R/'confirm_page_r24.js']:
 result=subprocess.run(['node','--check',str(p)],capture_output=True,text=True);assert result.returncode==0,(p,result.stderr)
ns=runpy.run_path(str(R/'run_trial_r24_review_snapshot.py'),run_name='r28_import_only')
imports=[]
for name in ('trial_ring_cached','gate_input_usability','restore_api103_v2','runtime_resource_guard','qmp_line_transport'):
 p=Path(sys.modules[name].__file__).resolve();assert p==R.parent/'v25-r21-recovery-integration'/p.name;imports.append({'module':name,'actual_file':str(p),'sha256':sha(p)})
import trial_web_r24_review_snapshot as web
assert web.PAGE_SCRIPT_SHA=='852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b'
assert sha(R/'NAVIGATION-PLAN.json')=='4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f'
for f in ('trial_web_r24_review_snapshot.py','run_trial_r24_review_snapshot.py','review_page_r24.js','confirm_page_r24.js','operator-helpers/deadline.js','operator-helpers/recovery_tools.py','operator-helpers/recovery_readonly.js','operator-helpers/recovery_cancel.js','operator-helpers/planned_navigation_click.py','operator-helpers/review_snapshot_cli.py','runtime-wrapper/operate.py'):
 assert sha(R/f)==sha(B/f),f
local=json.loads((R/'evidence/run-model1/LOCAL-SOURCE-FREEZE.json').read_text());assert all(sha(p)==h for p,h in local.items());assert all(str(R/f) in local for f in ('CORE-SOURCE-FREEZE.json','return-tools/return_adapter.py','return-tools/short_tool.mjs'))
spec=importlib.util.spec_from_file_location('r28_return_adapter',R/'return-tools/return_adapter.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter);assert adapter.FROZEN==R and adapter.OPERATE==R/'runtime-wrapper/operate.py' and adapter.sha(R/'CORE-SOURCE-FREEZE.json')==adapter.CORE_FREEZE_SHA and adapter.sha(adapter.OPERATE)==adapter.OPERATE_SHA
save('evidence/IMPORT-SOURCE-VERIFICATION.json',{'passed':True,'original_inputs_matched':len(before),'production_files':len(production),'local_prepare_frozen_files':len(local),'imports':imports,'sys_path_first_three':sys.path[:3],'PAGE_canonical_SHA':web.PAGE_SCRIPT_SHA,'return_OPERATE':str(adapter.OPERATE),'return_OPERATE_SHA':adapter.OPERATE_SHA,'CORE_FREEZE_SHA':adapter.CORE_FREEZE_SHA,'VM_starts':0})
print(json.dumps({'passed':True,'inputs_matched':len(before),'production_files':len(production),'core_modified':[x['path'] for x in delta if not x['same_bytes']]}))
