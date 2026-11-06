#!/usr/bin/env python3
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,struct,stat,gzip,hashlib,posixpath,importlib.util,subprocess,plistlib
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac');OUT=ROOT/'work/fx3-vm-20261101/fx3-audit';SRC=ROOT/'work/sony-firmware-20261024/stage2/extraction'
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
spec=importlib.util.spec_from_file_location('read_fs',SRC/'read_filesystems.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fs={n:m.Ext2(SRC/f'nflasha{n}.img') for n in [7,15]};idx={}
for part in [7,15]:
 for row in json.loads((SRC/f'nflasha{part}-files.json').read_text())['files']:
  full=('/usr' if part==15 else '')+row['path'];idx[full]=(part,row)
def bytes_for(path):
 p,e=idx[path];return fs[p].data(e['inode'])
def resolve(path):
 seen=[]
 while idx[path][1]['type']==stat.S_IFLNK:
  assert path not in seen;seen.append(path);target=bytes_for(path).decode();path=posixpath.normpath(target if target.startswith('/') else posixpath.join(posixpath.dirname(path),target));assert path in idx,(seen,path)
 return path,seen
def needed(b):
 if b[:4]!=b'\x7fELF':return [],None
 assert b[4:6]==b'\x02\x01' and struct.unpack_from('<H',b,18)[0]==183
 po=struct.unpack_from('<Q',b,32)[0];pe,pn=struct.unpack_from('<HH',b,54);ps=[];ds=[];interp=None
 for i in range(pn):
  t,fl,o,va,pa,sz,ms,al=struct.unpack_from('<IIQQQQQQ',b,po+i*pe);ps.append((t,o,va,sz))
  if t==3:interp=b[o:o+sz].rstrip(b'\0').decode()
  if t==2:
   for j in range(o,o+sz,16):
    tag,val=struct.unpack_from('<qQ',b,j)
    if not tag:break
    ds.append((tag,val))
 st=next((v for t,v in ds if t==5),None);ns=[]
 if st is not None:
  so=next(o+st-va for t,o,va,sz in ps if t==1 and va<=st<va+sz)
  for t,v in ds:
   if t==1:ns.append(b[so+v:b.index(b'\0',so+v)].decode())
 return ns,interp
pending=['/bin/busybox','/usr/bin/bootin.elf','/usr/bin/im.elf'];payload={};records=[];edges=[];visited=set()
while pending:
 path=pending.pop(0)
 if path in visited:continue
 resolved,syms=resolve(path)
 for s in syms:
  if s not in payload:payload[s.lstrip('/')]=(bytes_for(s),stat.S_IFLNK|0o777)
 visited.add(path)
 if resolved in visited and resolved!=path:continue
 visited.add(resolved);b=bytes_for(resolved);payload[resolved.lstrip('/')]=(b,stat.S_IFREG|0o755)
 part,e=idx[resolved];ns,interp=needed(b);records.append({'guest_path':resolved,'source_partition':part,'inode':e['inode'],'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'needed':ns,'interpreter':interp})
 if interp:pending.append(interp)
 for n in ns:
  candidates=['/lib/'+n,'/usr/lib/'+n];target=next((x for x in candidates if x in idx),None);assert target,(resolved,n)
  edges.append({'from':resolved,'needed':n,'resolved_search':target});pending.append(target)
for n in ['bin','lib','usr','usr/bin','usr/lib','dev','proc','sys']:
 payload[n]=(b'',stat.S_IFDIR|0o755)
payload['dev/console']=(b'',stat.S_IFCHR|0o600)
init=b'''#!/bin/busybox sh
echo FX3_ORIGINAL_BUSYBOX_REACHED
/bin/busybox uname -a
for app in bootin im; do
 echo FX3_LD_VERIFY_BEGIN_$app
 /lib/ld-linux-aarch64.so.1 --verify /usr/bin/$app.elf
 rc=$?
 echo FX3_LD_VERIFY_RC_$app=$rc
 echo FX3_LD_LIST_BEGIN_$app
 /lib/ld-linux-aarch64.so.1 --library-path /lib:/usr/lib --list /usr/bin/$app.elf
 rc=$?
 echo FX3_LD_LIST_RC_$app=$rc
 done
echo FX3_APPLICATION_LOADER_PROBE_END
while true; do /bin/busybox sleep 1; done
'''
payload['init']=(init,stat.S_IFREG|0o755)
def ent(n,d,m,i):
 nb=n.encode()+b'\0';v=[i,m,0,0,1,0,len(d),0,0,5 if n=='dev/console' else 0,1 if n=='dev/console' else 0,len(nb),0];o=b'070701'+''.join(f'{x:08x}' for x in v).encode()+nb;o+=b'\0'*((-len(o))%4);o+=d;o+=b'\0'*((-len(o))%4);return o
# Parents before children; symlinks are serialized only inside guest cpio, never created on host.
order=sorted(payload,key=lambda n:(n.count('/'),0 if stat.S_ISDIR(payload[n][1]) else 1,n))
cpio=b''.join(ent(n,*payload[n],i+1) for i,n in enumerate(order))+ent('TRAILER!!!',b'',0,999)
p=OUT/'fx3-original-app-loader-probe.cpio.gz';assert not p.exists();p.write_bytes(gzip.compress(cpio,mtime=0))
rec={'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'original_elfs':records,'dependency_edges':edges,'guest_only_symlinks':[n for n in payload if stat.S_ISLNK(payload[n][1])],'custom_init':init.decode(),'scope':'Execute original ld-linux --verify/--list only; application entrypoints/constructors/init/services/updater are not intentionally executed; no camera/USB or real blocks. Application main/UI success is not claimed.'}
(OUT/'application-loader-probe.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':rec['sha256'],'original_elf_count':len(records),'dependency_edges':len(edges)},indent=2))
