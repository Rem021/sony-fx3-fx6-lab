#!/usr/bin/env python3
import os,sys,json,hashlib,subprocess,datetime
from pathlib import Path
D=Path(__file__).resolve().parent
R=D.parents[2]/'menu-repair-01/runtime'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,env=None):
 p=subprocess.run(list(map(str,args)),cwd=D,env=env,text=True,capture_output=True)
 return dict(args=list(map(str,args)),exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
# Verify target volume before any writes.
p=run(['diskutil','info','-plist','/Volumes/KAFU2T'])
import plistlib
assert p['exit']==0 and plistlib.loads(p['stdout'].encode())['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
B=D/'build';B.mkdir(exist_ok=True)
sources=['fx3-gpe-observe-v13.c','fx3-gpe-backend.c','fx3-gpe-backend.h','check-adapter.c','build_and_test.py','make_source.py','adapter.inc','compat/string.h']
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':{n:sha(D/n) for n in sources},'v12_sha256':sha(R/'helpers/fx3-gpe-observe-v12.c')}
a=json.loads((R/'helpers/fx3-gpe-observe-v12-build.json').read_text())['args']
a=[str(D/'fx3-gpe-observe-v13.c') if x.endswith('/fx3-gpe-observe-v12.c') else str(D/'fx3-gpe-observe-v13.so') if x.endswith('/fx3-gpe-observe-v12.so') else '-Wl,-soname,fx3-gpe-observe-v13.so' if x.startswith('-Wl,-soname,') else x for x in a]
a[2:2]=['-I',str(D/'compat')]
a.insert(a.index(str(D/'fx3-gpe-observe-v13.c'))+1,str(D/'fx3-gpe-backend.c'))
env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(D/'zig-cache/global');env['ZIG_LOCAL_CACHE_DIR']=str(D/'zig-cache/local');env['TMPDIR']=str(B)
receipt['cross']=run(a,env)
if receipt['cross']['exit']==0:
 receipt['output_sha256']=sha(D/'fx3-gpe-observe-v13.so');receipt['file']=run(['file',D/'fx3-gpe-observe-v13.so'])
 assert 'ARM aarch64' in receipt['file']['stdout'] and 'shared object' in receipt['file']['stdout']
receipt['host']=run(['clang','-std=c11','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-Wall','-Wextra','-Werror','check-adapter.c','fx3-gpe-backend.c','-o',B/'check-adapter'])
(D/'fx3-gpe-observe-v13-build.json').write_text(json.dumps(receipt,indent=2)+'\n')
if receipt['cross']['exit'] or receipt['host']['exit']:
 print(json.dumps(receipt,indent=2));sys.exit(1)
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
t=run([B/'check-adapter'],env);t['sanitizers']=['address','undefined'];(B/'test.json').write_text(json.dumps(t,indent=2)+'\n');(B/'host-test.log').write_text(t['stdout']+t['stderr'])
print(t['stdout'][-700:]);print(t['stderr']);print(receipt['file']['stdout'].strip());print(receipt['output_sha256']);sys.exit(t['exit'])
