from pathlib import Path
import ast,json
O=Path(__file__).resolve().parents[1];result=[]
for name in ['deadline_cli.py','recovery_tools.py','review_snapshot_cli.py','planned_navigation_click.py','postkey_observation.py']:
 p=O/'operator-helpers'/name;t=ast.parse(p.read_text());guards=[n for n in t.body if isinstance(n,ast.If) and '__name__' in ast.unparse(n.test)];assert len(guards)==1
 functions={n.name:n for n in t.body if isinstance(n,ast.FunctionDef)};body=guards[0].body
 if any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='main' for node in body for n in ast.walk(node)):body=functions['main'].body
 idx=next(i for i,n in enumerate(body) if any(isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='parse_args' for c in ast.walk(n)))
 calls=[ast.unparse(c.func) for n in body[:idx] for c in ast.walk(n) if isinstance(c,ast.Call)];assert not any(c.startswith(('subprocess.','browser','call','operate','snapshot','capture','live','run_live')) for c in calls)
 result.append({'path':str(p),'__main___guard_line':guards[0].lineno,'parse_args_statement_line':body[idx].lineno,'preparse_calls':calls,'help_exits_before_native_browser_actions':True})
(O/'HELP-SIDE-EFFECT-AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print('audited help main guards and preparse expressions PASS')
