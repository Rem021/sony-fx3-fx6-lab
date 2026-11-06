#!/usr/bin/env python3
"""Final byte/source/path verification only; no action helper or runner main."""
import ast,datetime,hashlib,importlib.util,json,re,runpy,sys
from pathlib import Path
R=Path(__file__).resolve().parent;B=R.parent/'r28-first-observation-candidate'
sys.dont_write_bytecode=True
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
full=json.loads((R/'SOURCE-FREEZE.json').read_text());core=json.loads((R/'CORE-SOURCE-FREEZE.json').read_text())
assert len(full)==41 and len(core)==36
for n,h in full.items():assert sha(R/n)==h,n
prep=R/'evidence/prepared-6540dfe4e72f'
local=json.loads((prep/'LOCAL-SOURCE-FREEZE.json').read_text())
assert {str(R/n) for n in full}==set(local)
for n,h in local.items():assert sha(n)==h
assert json.loads((prep/'PREFLIGHT-RESULT.json').read_text())['passed']
binding=json.loads((prep/'ACTUAL-DEPENDENCY-BINDING.json').read_text())
for n in ('startup_observation','trial_ring_cached','trial_log_v4_mss'):assert Path(binding['modules'][n])==R/(n+'.py')
# Import return adapter without its __main__; actual __file__ resolves new r30.
a=runpy.run_path(str(R/'return-tools/return_adapter.py'),run_name='r30_adapter_import_only')
assert a['FROZEN']==R and a['OPERATE']==R/'runtime-wrapper/operate.py'
assert a['CORE_FREEZE_SHA']==sha(R/'CORE-SOURCE-FREEZE.json') and a['OPERATE_SHA']==sha(a['OPERATE'])
old=ast.parse((B/'return-tools/return_adapter.py').read_text());new=ast.parse((R/'return-tools/return_adapter.py').read_text())
for tree in (old,new):
 for row in tree.body:
  if isinstance(row,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='CORE_FREEZE_SHA' for n in row.targets):row.value=ast.Constant(value='new_core_pin_only')
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
for name in ('short_tool.mjs','show_result.mjs','tool_call.mjs'):assert sha(R/'return-tools'/name)==sha(B/'return-tools'/name)
sp=importlib.util.spec_from_file_location('r30_web_import_only',R/'trial_web_r24_review_snapshot.py');web=importlib.util.module_from_spec(sp);sp.loader.exec_module(web)
assert web.PAGE_SCRIPT_SHA=='852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b'
assert sha(R/'NAVIGATION-PLAN.json')=='4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f'
rows=[];pool=json.loads((R/'INPUTS-BEFORE.json').read_text())['files']+json.loads((R/'DEPENDENCY-INPUT-SUPPLEMENT.json').read_text())['files']+json.loads((R/'evidence/OFFLINE-RESULT.json').read_text())['historical_inputs']
unique={x['path']:x for x in pool}
for p,row in unique.items():
 match=sha(p)==row['sha256'] and Path(p).stat().st_size==row['bytes'];assert match,p
 rows.append({'path':p,'bytes':row['bytes'],'sha256':row['sha256'],'unchanged':match})
(R/'INPUTS-AFTER.json').write_text(json.dumps({'captured_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'count':len(rows),'files':rows,
 'timing_boundary':'initial source hashes before derivation; replay hashes before each replay; dependency supplement explicitly later sampled against sealed pins; no claim all were sampled pre-task'},indent=2)+'\n')
reuse=[]
for n,h in full.items():
 if (B/n).exists():reuse.append({'file':n,'same_as_r28':sha(B/n)==h,'r28_sha256':sha(B/n),'r30_sha256':h})
(R/'SOURCE-REUSE.json').write_text(json.dumps(reuse,indent=2)+'\n')
out={'outcome':'offline_candidate_passed_runtime_unverified','core_files':36,'production_files':41,'actual_prepare_local_freeze_files':len(local),
 'actual_import_binding':binding,'actual_adapter_binding':{'FROZEN':str(a['FROZEN']),'OPERATE':str(a['OPERATE']),'CORE_FREEZE_SHA':a['CORE_FREEZE_SHA'],
 'adapter_AST_unchanged_except_core_pin':True,'relative_JS_modules_byte_identical_to_r28':True},
 'PAGE_canonical_script_SHA':web.PAGE_SCRIPT_SHA,'original_inputs_unchanged':len(rows),
 'same_byte_production_files_from_r28':sum(x['same_as_r28'] for x in reuse),'scope':'prepare/preflight/import only; no launch_prepare/start_and_wait/operate main, browser, service or VM',
 'cleanup':'all fixture temp exports used TemporaryDirectory inside r30 and were removed; no owned long-lived processes/ports/browser created'}
(R/'evidence/FINAL-VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('actual_import_binding',)},indent=2))
