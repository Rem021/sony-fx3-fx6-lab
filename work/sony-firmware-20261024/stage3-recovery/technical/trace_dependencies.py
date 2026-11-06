#!/usr/bin/env python3
"""Read-only DT_NEEDED closure from original ext2 images. Never loads ELF code."""
import sys, pathlib, json, struct, hashlib, posixpath, importlib.util
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).resolve().parent
SRC=OUT.parents[1]/'stage2'/'extraction'
spec=importlib.util.spec_from_file_location('fs_reader',SRC/'read_filesystems.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
images={str(p):module.Ext2(SRC/f'nflasha{p}.img') for p in (15,7)}
entries={}
for part,fs in images.items():
 for e in fs.walk(): entries[('/usr' if part=='15' else '')+e['path']]=(part,e)
def read(path,chain=()):
 path=posixpath.normpath(path)
 if path not in entries:return None,None
 assert path not in chain
 part,e=entries[path];b=images[part].data(e['inode'])
 if e['type']==0xa000:
  target=b.decode('utf8');target=target if target.startswith('/') else posixpath.join(posixpath.dirname(path),target)
  return read(target,chain+(path,))
 if e['type']!=0x8000:return None,None
 return b,path
def elf(b):
 assert b[:6]==b'\x7fELF\x02\x01'
 phoff=struct.unpack_from('<Q',b,32)[0];entsz,num=struct.unpack_from('<HH',b,54)
 ph=[struct.unpack_from('<IIQQQQQQ',b,phoff+i*entsz) for i in range(num)]
 def off(va):
  for p in ph:
   if p[0]==1 and p[3]<=va<p[3]+p[5]:return p[2]+va-p[3]
  raise ValueError(hex(va))
 dyn=[]
 for p in ph:
  if p[0]==2:
   for o in range(p[2],p[2]+p[5],16):
    t,v=struct.unpack_from('<QQ',b,o)
    if t==0:break
    dyn.append((t,v))
 if not dyn:return {'needed':[],'imports':[]}
 d=dict(dyn);st=off(d[5]);ss=d[10]
 def string(i):
  assert i<ss
  end=b.index(b'\0',st+i,st+ss)
  return b[st+i:end].decode('utf8',errors='replace')
 needed=[string(v) for t,v in dyn if t==1]
 # Symbol count from section table, rather than unbounded GNU hash traversal.
 imports=[];shoff=struct.unpack_from('<Q',b,40)[0];shsz,shnum=struct.unpack_from('<HH',b,58)
 for i in range(shnum):
  h=struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*shsz)
  if h[1]==11:
   for o in range(h[4],h[4]+h[5],h[9]):
    n,info,other,index,val,size=struct.unpack_from('<IBBHQQ',b,o)
    if n and index==0:imports.append(string(n))
 return {'needed':needed,'imports':imports}
roots=['/usr/bin/sen.elf','/usr/bin/bootin.elf','/usr/lib/libsencore.so','/usr/lib/libpro00.so']
nodes={};pending=roots[:]
while pending:
 path=pending.pop(0)
 if path in nodes:continue
 b,resolved=read(path)
 if b is None:nodes[path]={'missing':True};continue
 if b[:4]!=b'\x7fELF':nodes[path]={'not_elf':True,'resolved':resolved};continue
 info=elf(b);deps=[]
 for name in info['needed']:
  found=None
  for prefix in ['/usr/lib','/lib','/usr/lib64','/lib64']:
   candidate=prefix+'/'+name
   if candidate in entries:found=candidate;break
  deps.append({'name':name,'path':found})
  if found and found not in nodes:pending.append(found)
 # Preserve bounded textual runtime loader/plugin hints as separate evidence.
 import re
 strings=[m.group().decode('ascii') for m in re.finditer(rb'[ -~]{5,}',b)]
 hints=[x for x in strings if any(k in x for k in ('appFw','libpro','libsencore','dlopen','senser_usb_mode','bootin','sen/smode'))]
 nodes[path]={'resolved':resolved,'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'dependencies':deps,
              'dynamic_loading_imports':[x for x in info['imports'] if x in ('dlopen','dlsym','dlclose','__libc_dlopen_mode')],
              'runtime_hints':hints[:40]}
def closure(root):
 seen=set();todo=[root]
 while todo:
  p=todo.pop()
  if p in seen:continue
  seen.add(p)
  todo.extend(d['path'] for d in nodes.get(p,{}).get('dependencies',[]) if d['path'])
 return sorted(seen)
result={'method':'read-only original ext2 data, ELF DT_NEEDED; no code execution or native loading',
        'roots':roots,'nodes':nodes,'static_closures':{r:closure(r) for r in roots},
        'limitations':['DT_NEEDED only: dynamic dlopen plugins, runtime registration, IPC and startup triggering are not proven by this graph']}
(OUT/'dependency-closure.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'node_count':len(nodes),'roots':{r:len(closure(r)) for r in roots},
                  'appFw_static_paths':[p for p in nodes if 'appFw' in p],
                  'dynamic_loading':{p:v['runtime_hints'] for p,v in nodes.items() if v.get('dynamic_loading_imports')}} ,ensure_ascii=False,indent=2))
