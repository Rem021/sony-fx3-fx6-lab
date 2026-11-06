#!/usr/bin/env python3
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import importlib.util,json,struct,hashlib,plistlib,subprocess,gzip,stat
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT=ROOT/'work/fx3-vm-20261101/fx3-audit'
vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert vol['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
SRC=ROOT/'work/sony-firmware-20261024/stage2/extraction'
reader=SRC/'read_filesystems.py';spec=importlib.util.spec_from_file_location('existing_readonly_fs',reader);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda b:hashlib.sha256(b).hexdigest()
def elf(b):
 if b[:4]!=b'\x7fELF':return {'elf':False}
 assert b[4:6]==b'\x02\x01'
 et,em=struct.unpack_from('<HH',b,16);entry,po=struct.unpack_from('<QQ',b,24);pe,pn=struct.unpack_from('<HH',b,54)
 ps=[];interp=None;dyn=[]
 for i in range(pn):
  t,fl,off,va,pa,sz,ms,al=struct.unpack_from('<IIQQQQQQ',b,po+i*pe);ps.append((t,off,va,sz))
  if t==3:interp=b[off:off+sz].rstrip(b'\0').decode()
  if t==2:
   for j in range(off,off+sz,16):
    tag,val=struct.unpack_from('<qQ',b,j)
    if tag==0:break
    dyn.append((tag,val))
 st=next((v for t,v in dyn if t==5),None);needed=[]
 if st is not None:
  soff=next(off+st-va for t,off,va,sz in ps if t==1 and va<=st<va+sz)
  for t,v in dyn:
   if t==1:
    s=soff+v;needed.append(b[s:b.index(b'\0',s)].decode())
 return {'elf':True,'class':64,'endianness':'little','type':et,'machine':em,'entry':hex(entry),'interpreter':interp,'needed':needed}
def fdt(b):
 h=struct.unpack_from('>10I',b);assert h[0]==0xd00dfeed
 total,os,ostr,omem,ver,last,cpuid,ss,sz=h[1:];strings=b[ostr:ostr+ss];o=os;stack=[];rows=[]
 while o<os+sz:
  tag=struct.unpack_from('>I',b,o)[0];o+=4
  if tag==1:
   end=b.index(b'\0',o);name=b[o:end].decode();stack.append(name);o=(end+4)&~3
  elif tag==2:stack.pop()
  elif tag==3:
   ln,no=struct.unpack_from('>II',b,o);o+=8;value=b[o:o+ln];o=(o+ln+3)&~3
   name=strings[no:strings.index(b'\0',no)].decode();node='/'.join(stack) or '/'
   if any(k in node for k in ['memory','chosen','cpus','interrupt-controller','uart','serial','timer','reserved']) or name in ['compatible','model','bootargs','stdout-path']:
    val={'hex':value.hex()}
    if value and value[-1]==0 and all(c in [0,9,10,13] or 32<=c<127 for c in value):val['text']=value.rstrip(b'\0').decode().replace('\0',' | ')
    if len(value)%4==0:val['cells']=[hex(x) for x in struct.unpack('>'+'I'*(len(value)//4),value)]
    rows.append({'node':node,'property':name,**val})
  elif tag==4:pass
  elif tag==9:break
  else:raise ValueError(tag)
 rsv=[];o=omem
 while True:
  a,s=struct.unpack_from('>QQ',b,o);o+=16
  if a==s==0:break
  rsv.append({'address':hex(a),'size':hex(s)})
 return {'header':{'totalsize':total,'version':ver,'boot_cpuid_phys':cpuid},'memreserve':rsv,'selected_properties':rows}
manifest={'volume_uuid':vol['VolumeUUID'],'images':[],'files':[],'symlinks':[],'scope':'Read-only existing original partition members; no mount or original init/updater execution'}
all_data={};selected7={'/bin/busybox','/lib/libc-2.25.so','/lib/ld-2.25.so','/lib/libpthread-2.25.so','/lib/libdl-2.25.so','/lib/librt-2.25.so','/lib/libm-2.25.so','/lib/libgcc_s.so.1','/lib/libstdc++.so.6.0.22','/sbin/init','/sbin/init2','/sbin/initrc/fstab','/sbin/initrc/fstab.root','/sbin/initrc/insmod_drv1','/sbin/initrc/insmod_drv2','/sbin/initrc/setup_nflash','/root/chassis'}
selected15={'/bin/im.elf','/bin/bootin.elf','/lib/appFw.so','/lib/libObj.so','/lib/libbootin.so','/lib/libosal.so','/lib/libosal_uipc.so','/lib/libuipc.so','/lib/libDataflow.so'}
for num,sel in [(7,selected7),(15,selected15)]:
 image=SRC/f'nflasha{num}.img';fs=m.Ext2(image);entries=json.loads((SRC/f'nflasha{num}-files.json').read_text())['files'];idx={x['path']:x for x in entries}
 manifest['images'].append({'path':str(image),'bytes':image.stat().st_size,'sha256':sha(image.read_bytes()),'filesystem':fs.meta,'entries':len(entries),'modules':len([x for x in entries if x['path'].endswith('.ko')])})
 for e in entries:
  if e['type']==0xa000:
   manifest['symlinks'].append({'partition':num,'path':e['path'],'target':fs.data(e['inode']).decode()})
 for path in sorted(sel):
  if path not in idx:continue
  e=idx[path];b=fs.data(e['inode']);assert len(b)==e['size'];all_data[(num,path)]=b
  dest=OUT/'original-members'/f'nflasha{num}'/path.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(b)
  manifest['files'].append({'partition':num,'path':path,'original_inode':e['inode'],'mode':e['mode'],'bytes':len(b),'sha256':sha(b),'output':str(dest),**elf(b)})
kernel=ROOT/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin';kb=kernel.read_bytes();assert sha(kb)=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
manifest['kernel']={'path':str(kernel),'sha256':sha(kb),'bytes':len(kb),'text_offset':hex(struct.unpack_from('<Q',kb,8)[0]),'image_size':hex(struct.unpack_from('<Q',kb,16)[0]),'flags':hex(struct.unpack_from('<Q',kb,24)[0]),'linux_banner':kb[kb.index(b'Linux version '):kb.index(b'\0',kb.index(b'Linux version '))].decode()}
dtb=ROOT/'work/sony-firmware-20261024/stage205-FX3-hardware-profile-differences/originals/7.02-setting-cxd90057.dtb';db=dtb.read_bytes();manifest['dtb']={'path':str(dtb),'sha256':sha(db),'bytes':len(db),**fdt(db)}
# Minimal initramfs contains original Sony busybox/libc/loader, not original boot scripts.
# The custom /init only emits uname and ELF execution evidence, no module/device/block operations.
files={'bin':(b'',stat.S_IFDIR|0o755),'lib':(b'',stat.S_IFDIR|0o755),'dev':(b'',stat.S_IFDIR|0o755),'proc':(b'',stat.S_IFDIR|0o755),'sys':(b'',stat.S_IFDIR|0o755)}
for path in ['/bin/busybox','/lib/libc-2.25.so','/lib/ld-2.25.so']:
 files[path.lstrip('/')]=(all_data[(7,path)],stat.S_IFREG|0o755)
for path,target in [('lib/ld-linux-aarch64.so.1','ld-2.25.so'),('lib/libc.so.6','libc-2.25.so'),('bin/sh','busybox')]:files[path]=(target.encode(),stat.S_IFLNK|0o777)
files['init']=(b'#!/bin/busybox sh\necho FX3_ORIGINAL_BUSYBOX_REACHED\n/bin/busybox uname -a\n/bin/busybox echo FX3_VM_PROBE_END\nwhile true; do /bin/busybox sleep 1; done\n',stat.S_IFREG|0o755)
files['dev/console']=(b'',stat.S_IFCHR|0o600)
def ent(name,data,mode,ino):
 nb=name.encode()+b'\0';v=[ino,mode,0,0,1,0,len(data),0,0,5 if name=='dev/console' else 0,1 if name=='dev/console' else 0,len(nb),0]
 raw=b'070701'+''.join(f'{x:08x}' for x in v).encode()+nb;raw+=b'\0'*((-len(raw))%4);raw+=data;raw+=b'\0'*((-len(raw))%4);return raw
cpio=b''.join(ent(n,d,m,i+1) for i,(n,(d,m)) in enumerate(files.items()))+ent('TRAILER!!!',b'',0,999)
initrd=OUT/'fx3-minimal-original-userspace.cpio.gz';initrd.write_bytes(gzip.compress(cpio,mtime=0))
manifest['probe_initramfs']={'path':str(initrd),'bytes':initrd.stat().st_size,'sha256':sha(initrd.read_bytes()),'custom_init':files['init'][0].decode(),'members':[{'path':n,'mode':oct(m),'bytes':len(d),'sha256':sha(d)} for n,(d,m) in files.items()],'not_full_sony_init':True}
(OUT/'asset-audit.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'kernel':manifest['kernel'],'dtb':{k:manifest['dtb'][k] for k in ['path','sha256','bytes','memreserve']},'probe_initramfs':str(initrd),'files':len(manifest['files']),'elf':[{k:x.get(k) for k in ['path','machine','interpreter','needed']} for x in manifest['files'] if x.get('elf')]} ,ensure_ascii=False,indent=2))
