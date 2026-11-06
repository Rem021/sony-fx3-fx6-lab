#!/usr/bin/env python3
"""Cross-build v14 and test frozen v13 plus v14/v2, writing only here."""
import datetime,hashlib,json,os,plistlib,struct,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,env=None):
 p=subprocess.run(list(map(str,args)),cwd=D,env=env,text=True,capture_output=True)
 return dict(args=list(map(str,args)),exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
# Do not create directories or update receipts until the required disk matches.
v=run(['diskutil','info','-plist','/Volumes/KAFU2T'])
assert v['exit']==0 and plistlib.loads(v['stdout'].encode())['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','wrong or absent target volume'
B=D/'build';B.mkdir(exist_ok=True)
env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(D/'zig-cache/global'),ZIG_LOCAL_CACHE_DIR=str(D/'zig-cache/local'),TMPDIR=str(B),PYTHONDONTWRITEBYTECODE='1')
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'running','scope':'host ASan/UBSan + aarch64 ELF build; no guest/QEMU/device execution','volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','commands':[]}
def save():
 (D/'fx3-gpe-observe-v14-build.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (B/'test.json').write_text(json.dumps(receipt,indent=2)+'\n')
def step(name,args,runenv=env):
 r=run(args,runenv);receipt['commands'].append({'name':name,**r});save()
 if r['exit']:
  receipt['result']='failed';save();print(name,r['stderr'],r['stdout'][-3000:]);sys.exit(1)
 return r
# Snapshot external-input comparisons for review, without requiring the live
# Lead plan to stay frozen. Rebuilds use our local frozen v13 reference.
receipt['external_inputs_unchanged']={p:sha(Path(p))==h for p,h in json.loads((D/'provenance.json').read_text()).items()}
original=(D/'reference-v13/check-adapter.c').read_text()
assert (D/'check-adapter-v13-regression.c').read_text()==original.replace('"fx3-gpe-observe-v13.c"','"fx3-gpe-observe-v14.c"')
step('source_reconstruction',[sys.executable,D/'make_source.py','--check'])
step('rational_oracle',[sys.executable,D/'make_vectors.py'])
receipt['source_sha256']={str(p.relative_to(D)):sha(p) for p in sorted(D.rglob('*')) if p.is_file() and ('build' not in p.relative_to(D).parts and 'zig-cache' not in p.relative_to(D).parts and p.suffix in ['.c','.h','.py','.inc'])}
step('cross',json.loads((D/'cross-args.json').read_text()))
so=D/'fx3-gpe-observe-v14.so';receipt['output_sha256']=sha(so)
receipt['file']=step('file',['file',so])['stdout'].strip()
assert 'ARM aarch64' in receipt['file'] and 'shared object' in receipt['file']
# Read ELF64 dynamic entries directly, including SONAME and DT_NEEDED.
data=so.read_bytes();assert data[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',data,18)[0]==183
phoff=struct.unpack_from('<Q',data,32)[0];phsz,phnum=struct.unpack_from('<HH',data,54)
ph=[struct.unpack_from('<IIQQQQQQ',data,phoff+i*phsz) for i in range(phnum)]
dyn=next(p for p in ph if p[0]==2);entries=[]
for off in range(dyn[2],dyn[2]+dyn[5],16):
 t,val=struct.unpack_from('<qQ',data,off)
 if t==0:break
 entries.append((t,val))
strva=next(v for t,v in entries if t==5);seg=next(p for p in ph if p[0]==1 and p[3]<=strva<p[3]+p[5]);stroff=seg[2]+strva-seg[3]
def ds(v):return data[stroff+v:data.index(b'\0',stroff+v)].decode()
receipt['soname']=next(ds(v) for t,v in entries if t==14)
receipt['needed']=[ds(v) for t,v in entries if t==1]
assert receipt['soname']=='fx3-gpe-observe-v14.so'
flags=['clang','-std=c11','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-Wall','-Wextra','-Werror']
tenv=dict(env,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
suites=[('v13-original','reference-v13/check-adapter.c','reference-v13/fx3-gpe-backend.c'),('v14-v13-regression','check-adapter-v13-regression.c','fx3-gpe-backend-v2.c'),('backend-v2','check-approx-backend.c','fx3-gpe-backend-v2.c'),('adapter-v14','check-approx-adapter.c','fx3-gpe-backend-v2.c')]
for name,src,backend in suites:
 step('build-'+name,flags+[src,backend,'-o',B/name])
 r=step('test-'+name,[B/name],tenv)
 (B/(name+'.log')).write_text(r['stdout']+r['stderr'])
 assert 'PASS' in r['stdout'] and not r['stderr'],name+' must print PASS without sanitizer diagnostics'
 print(r['stdout'].splitlines()[-1])
receipt['sanitizers']=['address','undefined'];receipt['result']='passed';save()
print(receipt['file']);print('SONAME',receipt['soname']);print('SHA256',receipt['output_sha256'])
