from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers'
for old,new,extra in [('fx3-preset-context-v2-screen','fx3-media-observe-v1',['fx3-media-probes-v1.S']),('fx3-capid-v44','fx3-capid-v47-media',[])]:
 args=json.loads((H/(old+'-build.json')).read_text())['args'];args=[a.replace(old,new) for a in args];args=[a for a in args if not a.endswith('/fx3-display-probes-v1.S')];i=args.index(str(H/(new+'.c')))+1;args[i:i]=[str(H/n) for n in extra];p=subprocess.run(args,capture_output=True,text=True);v={'args':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'source_sha256':hashlib.sha256((H/(new+'.c')).read_bytes()).hexdigest()};print(new,p.returncode,p.stderr)
 if not p.returncode:v['output_sha256']=hashlib.sha256((H/(new+'.so')).read_bytes()).hexdigest()
 (H/(new+'-build.json')).write_text(json.dumps(v,indent=2)+'\n')
 if p.returncode:raise SystemExit(p.returncode)
