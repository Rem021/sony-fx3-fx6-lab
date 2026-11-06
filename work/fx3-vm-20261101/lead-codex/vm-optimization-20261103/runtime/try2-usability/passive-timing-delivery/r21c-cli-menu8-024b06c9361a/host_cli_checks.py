"""Focused actual __main__ subprocess checks only; no timed fixture."""
from common import *
import ast,difflib
modes=['operate-click-'+str(n) for n in range(1,9)]+['operate-confirm','operate-recovery_cancel','operate-failure','later-capture','cleanup-null','cleanup-nonarmed','cleanup-armed','cleanup-malformed','cleanup-exception']
results=[]
for mode in modes:
 p=subprocess.run(['python3','-B',str(HERE/'host_cli_case.py'),mode],env=ENV,capture_output=True,text=True,timeout=10)
 write('host-'+mode+'-process.json',{'argv':['python3','-B',str(HERE/'host_cli_case.py'),mode],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 assert p.returncode==0,(mode,p.stdout,p.stderr)
 r=json.loads((HERE/'host-cli-cases'/mode/'result.json').read_text());assert r['passed'];results.append(r)
for name in ('operate.py','later_capture.py'):
 tree=ast.parse((HERE/name).read_text());assert any(isinstance(x,ast.Import) and any(n.name=='sys' for n in x.names) for x in tree.body)
old=HERE.parent/'r21-n64-worker-task-a9195ba9b134';diff=''
for p in sorted(HERE.iterdir()):
 if p.suffix in ('.py','.js') and (old/p.name).exists():diff+=''.join(difflib.unified_diff((old/p.name).read_text().splitlines(True),p.read_text().splitlines(True),fromfile=str(old/p.name),tofile=str(p)))
(HERE/'MINIMAL-WRAPPER.diff').write_text(diff)
write('HOST-CLI-RESULT.json',{'passed':True,'checks':len(results),'modes':[r['mode'] for r in results],'scope':'CLI wiring and cleanup flow only, strict dependency doubles, no browser fixture/runtime proof','source_hashes':{n:sha(HERE/n) for n in ('operate.py','later_capture.py','cleanup.py')},'browser_HTTP_QEMU_processes_started':0,**stamp()});print(json.dumps({'passed':True,'checks':len(results)}))
