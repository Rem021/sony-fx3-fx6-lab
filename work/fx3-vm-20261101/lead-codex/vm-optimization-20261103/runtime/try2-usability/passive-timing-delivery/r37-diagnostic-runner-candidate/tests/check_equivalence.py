from pathlib import Path
import ast,copy,json,hashlib
O=Path(__file__).resolve().parents[1];S=O.parent/'r30-startup-observation-candidate';a=(S/'run_trial_r24_review_snapshot.py').read_text();b=(O/'run_trial_r24_review_snapshot.py').read_text()
# The whole real startup/ready/input/End/recovery/restore/reap/finalACK portion,
# including __main__ error cleanup, must be byte-identical.
anchor='    journal = ACTIVE_HOST_JOURNAL\n';assert a[a.index(anchor):]==b[b.index(anchor):]
class Normalize(ast.NodeTransformer):
 def visit_ImportFrom(self,n):return None if n.module=='r35_package_selection' else n
 def visit_Expr(self,n):
  if isinstance(n.value,ast.Call) and n.value.args and isinstance(n.value.args[0],ast.Constant) and n.value.args[0].value=='--r35-diagnostic-package':return None
  return self.generic_visit(n)
 def visit_Try(self,n):
  if any(isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='r35_options' for x in n.body):return None
  return self.generic_visit(n)
 def visit_If(self,n):
  if ast.unparse(n.test)=='ns.r35_diagnostic_package':return None
  return self.generic_visit(n)
 def visit_IfExp(self,n):
  if ast.unparse(n.test)=='ns.r35_diagnostic_package':return self.visit(n.orelse)
  return self.generic_visit(n)
 def visit_BinOp(self,n):
  if isinstance(n.op,ast.Add) and isinstance(n.right,ast.IfExp) and ast.unparse(n.right.test)=='ns.r35_diagnostic_package':return self.visit(n.left)
  return self.generic_visit(n)
old=ast.parse(a);new=Normalize().visit(ast.parse(b));assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
unchanged=[];changed=[]
for name in json.loads((S/'SOURCE-FREEZE.json').read_text()):
 if name=='CORE-SOURCE-FREEZE.json':continue
 same=(S/name).read_bytes()==(O/name).read_bytes();(unchanged if same else changed).append(name)
assert set(changed)=={'run_trial_r24_review_snapshot.py','prepare_run.py','runtime-wrapper/common.py','runtime-wrapper/preflight.py','runtime-wrapper/launch_prepare.py','return-tools/return_adapter.py'}
# Actual wrapper planned argv, never call launch_prepare.
t=ast.parse((O/'runtime-wrapper/launch_prepare.py').read_text());f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='main');n=next(n for n in f.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='argv' for x in n.targets));g={'SOURCE':O/'runtime-wrapper'};exec(compile(ast.Module([n],[]),'planned-wrapper-argv','exec'),g);assert g['argv'][2]==str(O/'run_trial_r24_review_snapshot.py') and '--r35-diagnostic-package' in g['argv']
# Node production dispatch resolves the local adapter; no execFile invoked here.
assert (O/'return-tools/tool_call.mjs').read_bytes()==(S/'return-tools/tool_call.mjs').read_bytes();assert "new URL('./return_adapter.py',import.meta.url)" in (O/'return-tools/tool_call.mjs').read_text()
core=json.loads((O/'CORE-SOURCE-FREEZE.json').read_text());assert all(hashlib.sha256((O/n).read_bytes()).hexdigest()==h for n,h in core.items());ad=(O/'return-tools/return_adapter.py').read_text();assert "CORE_FREEZE_SHA='"+hashlib.sha256((O/'CORE-SOURCE-FREEZE.json').read_bytes()).hexdigest()+"'" in ad
(O/'EQUIVALENCE.json').write_text(json.dumps({'whole_main_AST_equal_after_exact_selector_provenance_removal':True,'startup_input_ready_Stop_End_cleanup_suffix_byte_identical':True,'unchanged_files':unchanged,'changed_files':changed,'planned_wrapper_argv':g['argv'],'Node_adapter_relative_resolution':'local return_adapter.py under this r37, unchanged tool_call.mjs','launch_prepare_or_start_called':False},indent=2)+'\n');print('AST/control suffix and wrapper/Node/freeze binding PASS')
