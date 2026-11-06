#!/usr/bin/env python3
import subprocess,json
from pathlib import Path
O=Path(__file__).resolve().parent;D=O.parent;H=D.parents[4]/'menu-repair-01/runtime/helpers'
r={}
for tag,file,extra in [('baseline',D/'v25-menu-osd-diagnostic-r3/src/fx3-osd-headless-v25-r3.c',[]),('candidate',O/'src/fx3-osd-r35.c',['-DCANDIDATE=1'])]:
 a=['/usr/bin/clang','-O2','-Wno-incompatible-library-redeclaration','-Wno-deprecated-non-prototype','-I'+str(H),'-I'+str(O/'src'),'-DSOURCE_FILE="'+str(file)+'"',*extra,str(O/'tests/wrapper_fixture.c'),'-o',str(O/'build'/('host-'+tag))]
 p=subprocess.run(a,capture_output=True);(O/'receipts'/('host-'+tag+'-compile.stderr')).write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode()
 q=subprocess.run([a[-1]],capture_output=True);(O/'receipts'/('host-'+tag+'.stdout')).write_bytes(q.stdout);(O/'receipts'/('host-'+tag+'.stderr')).write_bytes(q.stderr);r[tag]={'argv':a,'compile_exit':p.returncode,'run_exit':q.returncode};assert q.returncode==0,q.stdout.decode()
a=(O/'receipts/host-baseline.stdout').read_bytes();b=(O/'receipts/host-candidate.stdout').read_bytes();assert a==b
r['equivalent_stdout']=True;(O/'HOST-WRAPPER.json').write_text(json.dumps(r,indent=2)+'\n');print(a.decode())
