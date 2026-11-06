#!/usr/bin/env python3
"""Compile exact frozen source/flags to isolated audit objects; never execute ELF."""
from pathlib import Path
import os,subprocess,json,hashlib,struct
O=Path(__file__).resolve().parent;D=O.parent
osd=json.loads((D/'v25-menu-osd-diagnostic-r3/build/compile-r3.command.json').read_text());ui=json.loads((D/'v25-r15-snapshot-tail/BUILD.json').read_text())['variants']['N64']['command'];env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(O/'build/cache-global'),ZIG_LOCAL_CACHE_DIR=str(O/'build/cache-local'))
def text(b):
 sh=struct.unpack_from('<Q',b,40)[0];sz,n,ni=struct.unpack_from('<HHH',b,58);ss=[struct.unpack_from('<IIQQQQIIQQ',b,sh+i*sz) for i in range(n)];ns=ss[ni];names=b[ns[4]:ns[4]+ns[5]]
 for s in ss:
  a=s[0]
  if names[a:names.find(b'\0',a)]==b'.text':return hashlib.sha256(b[s[4]:s[4]+s[5]]).hexdigest()
r={}
for tag,argv,original in [('osd',osd,D/'v25-menu-osd-diagnostic-r3/build/fx3-osd-headless-v25-r3.so'),('ui',ui,D/'v25-r15-snapshot-tail/fx3-ui-gate-v15-n64.so')]:
 argv=argv.copy();argv[-1]=str(O/'build'/('baseline-'+tag+'.so'));p=subprocess.run(argv,capture_output=True,env=env)
 for k,b in [('stdout',p.stdout),('stderr',p.stderr)]:(O/'receipts'/('baseline-cross-'+tag+'.'+k)).write_bytes(b)
 assert p.returncode==0,p.stderr.decode();h=text(Path(argv[-1]).read_bytes());expected=text(original.read_bytes());assert h==expected
 r[tag]={'argv':argv,'exit':p.returncode,'recompiled_text_sha256':h,'frozen_text_sha256':expected,'equal':True}
(O/'BASELINE-REBUILD.json').write_text(json.dumps(r,indent=2)+'\n');print('source -> exact recompiled .text -> frozen object -> actual CPIO PASS')
