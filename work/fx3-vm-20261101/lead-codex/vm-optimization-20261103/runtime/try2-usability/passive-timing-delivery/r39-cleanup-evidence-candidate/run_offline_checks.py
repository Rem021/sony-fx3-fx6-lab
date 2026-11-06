"""Only offline r39 checks. Every child waited; no runner/start/browser/QMP allowed."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
O=Path(__file__).resolve().parent
steps=[('help-audit',[sys.executable,'-B',str(O/'tests/check_help_sources.py')]),('prepare-preflight-import',[sys.executable,'-B',str(O/'tests/check_binding.py')]),('wrapper-imports',[sys.executable,'-B',str(O/'tests/check_wrapper_imports.py')]),('equivalence',[sys.executable,'-B',str(O/'tests/check_equivalence.py')]),('cleanup',[sys.executable,'-B',str(O/'tests/test_cleanup.py')]),('return',[sys.executable,'-B',str(O/'tests/test_return.py')]),('return-node',['node',str(O/'tests/test_return_node.mjs')]),('node-import',['node',str(O/'tests/check_node.mjs')]),('source-lineage',[sys.executable,'-B',str(O/'implement.py')]),('binding-boundaries',[sys.executable,'-B',str(O/'tests/test_boundaries.py')])]
rows=[];suffix=str(time.time_ns())
for name,argv in steps:
 start=time.time_ns();p=subprocess.run(argv,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=120)
 prefix=O/'receipts'/('final-'+name+'-'+suffix)
 for ext,data in [('stdout',p.stdout),('stderr',p.stderr)]:Path(str(prefix)+'.'+ext).write_bytes(data)
 row={'step':name,'argv':argv,'script_sha256':hashlib.sha256(Path(argv[-1]).read_bytes()).hexdigest(),'exit':p.returncode,'start_ns':start,'end_ns':time.time_ns(),'stdout_path':str(prefix)+'.stdout','stderr_path':str(prefix)+'.stderr'};rows.append(row)
 (O/'OFFLINE-CHECKS.json').write_text(json.dumps({'checks':rows,'passed':all(x['exit']==0 for x in rows),'scope':'host only, all native/visual/process/port replies mocked except read-only preflight/import and real APFS files/flock'},indent=2)+'\n')
 print(name,p.returncode,flush=True)
 if p.returncode:raise SystemExit(2)
