#!/usr/bin/env python3
from pathlib import Path
import subprocess,json
O=Path(__file__).resolve().parent;D=O.parent;H=D.parents[4]/'menu-repair-01/runtime/helpers';receipt={}
for tag,file,extra in [('baseline',D/'v25-menu-osd-diagnostic-r3/src/fx3-osd-headless-v25-r3.c',[]),('candidate',O/'src/fx3-osd-r35.c',['-DCANDIDATE=1'])]:
 args=['/usr/bin/clang','-O2','-Wno-incompatible-library-redeclaration','-I'+str(H),'-I'+str(O/'src'),'-DSOURCE_FILE="'+str(file)+'"','-DBENCH=1',*extra,str(O/'tests/wrapper_fixture.c'),str(O/'tests/host_real_cost.c'),'-o',str(O/'build'/('host-cost-'+tag))];c=subprocess.run(args,capture_output=True);(O/'receipts'/('cost-'+tag+'-compile.stderr')).write_bytes(c.stderr);assert not c.returncode,c.stderr.decode()
 samples=[]
 for n in range(3):
  r=subprocess.run([args[-1]],capture_output=True);assert not r.returncode,r.stdout.decode();samples.append({'exit':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()})
 receipt[tag]={'argv':args,'compile_exit':c.returncode,'samples':samples}
(O/'HOST-COST.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v['samples'] for k,v in receipt.items()},indent=2))
