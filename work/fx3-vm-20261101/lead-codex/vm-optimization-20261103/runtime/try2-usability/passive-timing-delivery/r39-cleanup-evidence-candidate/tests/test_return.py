"""Actual adapter single-child execution + exact failed-child cleanup report, no old return read."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,subprocess,sys,time,uuid,contextlib,io
O=Path(__file__).resolve().parents[1]
# Use only the existing pure fixture factory definitions; do not run that suite.
t=ast.parse((O/'tests/test_cleanup.py').read_text());names={'sha','put','make'}
exec(compile(ast.Module([n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'fixture-factory-only','exec'))
h=make('return-failed-action');sys.path.insert(0,str(O/'runtime-wrapper'));import cleanup_evidence as E
E.RUNS=h/'native-runs';E.LOCKS=[h/'platform-lock-1',h/'platform-lock-2']
spec=importlib.util.spec_from_file_location('actual_return_adapter',O/'return-tools/return_adapter.py');ad=importlib.util.module_from_spec(spec);spec.loader.exec_module(ad)
env={**os.environ,'FX3_NAV_RUN_DIR':str(h),'PYTHONDONTWRITEBYTECODE':'1','FX3_RETURN_FIXTURE_ONLY':'1'};out=h/'return-current-action';stdout=io.StringIO()
with contextlib.redirect_stdout(stdout):code=ad._execute_once([sys.executable,'-B',str(O/'tests/fixture_cli.py'),'success','operate-fail'],'pin',h,out,env)
value=json.loads((out/'summary.json').read_text());assert code==2 and value['ok'] is False and value['status']=='return_failed' and value['image'] is None and value['cleanup']['reported_status']=='completed',value
assert value['End_required'] is True and value['child_returncode']==19 and not (out/'returned.png').exists()
assert json.loads((out/'process.json').read_text())['returncode']==19
# A failed child with no cleanup dispatch must not read an older successful one.
out2=h/'return-no-cleanup'
with contextlib.redirect_stdout(io.StringIO()):code2=ad._execute_once([sys.executable,'-B','-c','raise SystemExit(23)'],'pin',h,out2,env)
v2=json.loads((out2/'summary.json').read_text());assert code2==2 and v2['cleanup']['reported_status']=='unknown' and v2['image'] is None
# Save exact actual adapter result for the actual Node reader test.
put(O/'RETURN-TESTS.json',{'fixture_only':True,'passed':True,'run_dir':str(h),'adapter_output':str(out),'adapter_no_cleanup_output':str(out2),'original_action_exit':19,'adapter_exit':2,'original_action_still_failed':True,'cleanup_reported_status':value['cleanup']['reported_status'],'no_image':True,'no_old_dispatch_fallback':True,'adapter_actual_path':str(O/'return-tools/return_adapter.py'),'adapter_actual_sha256':sha(O/'return-tools/return_adapter.py')})
(O/'receipts/adapter-current.stdout').write_text(stdout.getvalue());print('actual single-child adapter failure+cleanup isolation PASS')
