#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,os,hashlib,plistlib
O=Path(__file__).resolve().parent;D=O.parent
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
osd=json.loads((D/'v25-menu-osd-diagnostic-r3/build/compile-r3.command.json').read_text())
ui=json.loads((D/'v25-r15-snapshot-tail/BUILD.json').read_text())['variants']['N64']['command']
cmds={}
for tag,args,name in [('osd',osd,'fx3-osd-r35.c'),('ui',ui,'fx3-ui-r35.c')]:
 args=args.copy()
 for i,v in enumerate(args):
  if v.endswith('.c'):args[i]=str(O/'src'/name)
  if v.startswith('-Wl,-soname,'):args[i]='-Wl,-soname,fx3-'+tag+'-r35.so'
 args[-1]=str(O/'build'/('fx3-'+tag+'-r35.so'));args.insert(-2,'-I'+str(O/'src'));cmds[tag]=args
pins=[]
for x in sorted({v for a in cmds.values() for v in a if Path(v).is_file() and not str(Path(v).resolve()).startswith(str(O))}):
 f=Path(x).resolve();b=f.read_bytes();pins.append({'path':str(f),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
pf=O/'BUILD-INPUTS-BEFORE.json'
if pf.exists():assert json.loads(pf.read_text())==pins
else:pf.write_text(json.dumps(pins,indent=2)+'\n')
env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(O/'build/cache-global'),ZIG_LOCAL_CACHE_DIR=str(O/'build/cache-local'))
receipt={}
for tag,a in cmds.items():
 p=subprocess.run(a,capture_output=True,env=env)
 for k,b in [('stdout',p.stdout),('stderr',p.stderr)]: (O/'receipts'/('cross-'+tag+'.'+k)).write_bytes(b)
 receipt[tag]={'argv':a,'exit':p.returncode,'stdout_file':'receipts/cross-'+tag+'.stdout','stderr_file':'receipts/cross-'+tag+'.stderr'}
 if not p.returncode:receipt[tag]['sha256']=hashlib.sha256(Path(a[-1]).read_bytes()).hexdigest()
(O/'BUILD.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:{x:y for x,y in v.items() if x in ['exit','sha256']} for k,v in receipt.items()}))
assert all(x['exit']==0 for x in receipt.values())
