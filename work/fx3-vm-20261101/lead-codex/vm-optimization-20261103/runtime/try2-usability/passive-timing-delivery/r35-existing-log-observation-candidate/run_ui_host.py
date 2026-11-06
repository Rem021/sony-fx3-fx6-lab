#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,re
O=Path(__file__).resolve().parent;r={}
for tag,extra,block in [('baseline',[],'original-ui-selected.inc'),('candidate',['-DCANDIDATE=1'],'candidate-ui-selected.inc')]:
 a=['/usr/bin/clang','-O2','-I'+str(O/'src'),'-I'+str(O/'tests'),'-DBLOCK_FILE="'+block+'"',*extra,str(O/'tests/ui_selected_fixture.c'),'-o',str(O/'build'/('host-ui-'+tag))];c=subprocess.run(a,capture_output=True);(O/'receipts'/('ui-'+tag+'-compile.stderr')).write_bytes(c.stderr);assert c.returncode==0,c.stderr.decode();p=subprocess.run([a[-1]],capture_output=True)
 for k,b in [('stdout',p.stdout),('stderr',p.stderr)]:(O/'receipts'/('ui-'+tag+'.'+k)).write_bytes(b)
 r[tag]={'argv':a,'compile_exit':c.returncode,'run_exit':p.returncode,'metrics':p.stderr.decode()};assert p.returncode==0,p.stderr.decode()
b=(O/'receipts/ui-baseline.stdout').read_bytes();c=(O/'receipts/ui-candidate.stdout').read_bytes();stripped=re.sub(rb' r35v1=[0-9a-f]{176};',b'',c);assert b==stripped and len(c)-len(b)==184
r['original_fields_byte_identical_after_suffix_removal']=True;r['extra_bytes_this_fixture']=len(c)-len(b);(O/'HOST-UI.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v['metrics'] for k,v in r.items() if isinstance(v,dict)},indent=2))
