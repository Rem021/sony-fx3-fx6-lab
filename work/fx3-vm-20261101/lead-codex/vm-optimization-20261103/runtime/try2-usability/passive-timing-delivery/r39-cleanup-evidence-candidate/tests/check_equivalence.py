"""Finite source/AST proof: original first-cleanup core, all runner and navigation remain."""
from pathlib import Path
import ast,copy,hashlib,json
O=Path(__file__).resolve().parents[1];S=O.parent/'r37-diagnostic-runner-candidate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def funcs(p):return {n.name:n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
def same(a,b):return ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
source=json.loads((S/'SOURCE-FREEZE.json').read_text());unchanged=[];changed=[]
for n in source:
 if n=='CORE-SOURCE-FREEZE.json':continue
 (unchanged if (S/n).read_bytes()==(O/n).read_bytes() else changed).append(n)
assert set(changed)=={'r35_package_selection.py','runtime-wrapper/common.py','runtime-wrapper/cleanup.py','runtime-wrapper/operate.py','runtime-wrapper/audit_after.py','runtime-wrapper/preflight.py','return-tools/return_adapter.py','return-tools/show_result.mjs','return-tools/short_tool.mjs'},changed
for n in ['run_trial_r24_review_snapshot.py','trial_web_r24_review_snapshot.py','startup_observation.py','runtime-wrapper/launch_prepare.py','runtime-wrapper/start_and_wait.py','runtime-wrapper/postkey_flow.py','prepare_run.py','NAVIGATION-PLAN.json','PAGE-IDENTITY.json']:
 assert n in unchanged,n
# All original alarm admissibility expressions, no cancel while armed.
a=funcs(S/'runtime-wrapper/cleanup.py');b=funcs(O/'runtime-wrapper/cleanup.py');assert same(a['alarm_disposition'],b['alarm_disposition'])
old=copy.deepcopy(a['cleanup'].body);new=copy.deepcopy(b['_cleanup_once'].body)
# Exact admitted instrumentation: c is supplied by the wrapper, output locations
# route to the new call directory, and immutable ended-page metadata is saved.
assert isinstance(old[0],ast.Assign) and ast.unparse(old[0])=='c = identity()';old.pop(0)
old=[n for n in old if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='print')]
class Core(ast.NodeTransformer):
 def visit_Name(self,n):
  if n.id=='output':n.id='HERE'
  return n
 def visit_Expr(self,n):
  if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='write' and n.value.args and isinstance(n.value.args[0],ast.Constant) and n.value.args[0].value=='ENDED-STATE.json':return None
  return self.generic_visit(n)
 def visit_Assign(self,n):
  if len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='ended':
   n.value.args[1]=ast.Constant('({lastStatus,finished,ending,alarm:window.__fx3InteractionDeadlineV1?.status?.()})');return ast.Expr(n.value)
  return self.generic_visit(n)
 def visit_Constant(self,n):
  if n.value=='body-result.json':n.value='CLEANUP.json'
  return n
new=Core().visit(ast.Module(body=new,type_ignores=[])).body
assert same(ast.Module(body=old,type_ignores=[]),ast.Module(body=new,type_ignores=[]))
# New cleanup dispatch is confined to the exception guard; every real input,
# observe/pin/confirm/recovery action is byte/AST-identical to r37.
a=funcs(S/'runtime-wrapper/operate.py');b=funcs(O/'runtime-wrapper/operate.py')
for name in a.keys()-{'failcleanup','run_action'}:assert same(a[name],b[name]),name
old=copy.deepcopy(a['run_action']);new=copy.deepcopy(b['run_action'])
class Dispatch(ast.NodeTransformer):
 def visit_Expr(self,n):
  if ast.unparse(n)=="write('FAILURE-CLEANUP-DISPATCH.json', failcleanup())":return ast.Expr(ast.Call(ast.Name('failcleanup',ast.Load()),[],[]))
  return self.generic_visit(n)
assert same(Dispatch().visit(old),new)
# Outside an active cleanup context, common's original implementations are intact.
a=funcs(S/'runtime-wrapper/common.py');b=funcs(O/'runtime-wrapper/common.py')
for name in a:
 x=copy.deepcopy(b[name])
 if name in ('write','event','run'):
  assert isinstance(x.body[0],ast.If) and 'evidence.ACTIVE.get()' in ast.unparse(x.body[0].test);x.body.pop(0)
 assert same(a[name],x),name
# Positive return action parsing/image copies and normal Node successful result
# path remain byte-identical. The new Python failure branch has no action API.
a=(S/'return-tools/return_adapter.py').read_text();b=(O/'return-tools/return_adapter.py').read_text();start='  value=json.loads';end=' except BaseException as e:'
assert a[a.index(start):a.index(end)]==b[b.index(start):b.index(end)]
a=(S/'return-tools/show_result.mjs').read_text();b=(O/'return-tools/show_result.mjs').read_text();start=" const file=path.join(callDir,'summary.json')";assert a[a.index(start):]==b[b.index(start):]
assert (O/'return-tools/tool_call.mjs').read_bytes()==(S/'return-tools/tool_call.mjs').read_bytes()
# Actual fixed wrapper argv constructor only, never main/launch.
t=funcs(O/'runtime-wrapper/launch_prepare.py')['main'];n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='argv' for x in n.targets));env={'SOURCE':O/'runtime-wrapper'};exec(compile(ast.Module([n],[]),'actual-planned-argv','exec'),env)
assert env['argv'][2]==str(O/'run_trial_r24_review_snapshot.py')
result={'passed':True,'runner_entire_file_byte_identical':True,'first_cleanup_core_AST_identical_after_listed_output_metadata_instrumentation':True,'alarm_disposition_AST_identical':True,'all_navigation_action_AST_identical':True,'normal_common_functions_AST_identical':True,'positive_return_branch_byte_identical':True,'changed_original_files':changed,'unchanged_original_files':unchanged,'new_runtime_files':['runtime-wrapper/cleanup_evidence.py'],'planned_wrapper_argv':env['argv'],'VM_or_launch_called':False}
(O/'EQUIVALENCE.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS original core/runner/input/positive-return equivalence and exact change boundary')
