from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';v=json.loads((H/'fx3-gpe-observe-v15-earlybind-build.json').read_text());args=v['args'];args=[a.replace('fx3-gpe-observe-v15-earlybind','fx3-gpe-observe-v16r2-mallocparent') for a in args];old=next(a for a in args if a.endswith('/fx3-gpe-backend-v2.c'));args[args.index(old)]=str(H/'fx3-gpe-backend-v3.c');args[2:2]=['-I',str(H)];p=subprocess.run(args,capture_output=True,text=True);doc={'args':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr};
for n in ['fx3-gpe-observe-v16r2-mallocparent.c','fx3-gpe-backend-v3.c','fx3-gpe-backend-v3.h','fx3-gpe-resource-v2.inc','fx3-gpe-screen-v1.inc']:
 doc[n]=hashlib.sha256((H/n).read_bytes()).hexdigest()
if not p.returncode:doc['output_sha256']=hashlib.sha256((H/'fx3-gpe-observe-v16r2-mallocparent.so').read_bytes()).hexdigest()
(H/'fx3-gpe-observe-v16r2-mallocparent-build.json').write_text(json.dumps(doc,indent=2)+'\n');print(p.stderr);print('exit',p.returncode);raise SystemExit(p.returncode)
