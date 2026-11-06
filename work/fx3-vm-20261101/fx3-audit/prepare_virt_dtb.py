#!/usr/bin/env python3
"""Rebuild a generated QEMU virt FDT with explicit guest-only bootargs/initrd.
No firmware patches, guest execution, real device, mount or updater calls.
"""
from pathlib import Path
import argparse,struct,hashlib,json,plistlib,subprocess
BASE=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit').resolve()
def parse(b):
 assert len(b)>=40
 h=struct.unpack_from('>10I',b);magic,total,os,ostr,om,ver,last,cpu,ss,sz=h
 assert magic==0xd00dfeed and total<=len(b)<=2*1024*1024
 assert os+sz<=total and ostr+ss<=total
 strings=b[ostr:ostr+ss];o=os;stack=[];root=None;props={};nodes=0
 while o<os+sz:
  tag=struct.unpack_from('>I',b,o)[0];o+=4
  if tag==1:
   z=b.index(b'\0',o,os+sz);name=b[o:z].decode();o=(z+4)&~3
   node={'name':name,'items':[]};nodes+=1
   if stack:stack[-1]['items'].append(('node',node))
   else:assert root is None;root=node
   stack.append(node)
  elif tag==2:assert stack;stack.pop()
  elif tag==3:
   assert stack;ln,no=struct.unpack_from('>II',b,o);o+=8;assert o+ln<=os+sz and no<ss
   name=strings[no:strings.index(b'\0',no)].decode();v=b[o:o+ln];o=(o+ln+3)&~3
   path='/'.join(n['name'] for n in stack) or '/';key=(path,name);assert key not in props
   props[key]=v;stack[-1]['items'].append(('prop',(name,v)))
  elif tag==4:pass
  elif tag==9:assert not stack;break
  else:raise ValueError(tag)
 assert root is not None
 o=om
 while True:
  a,s=struct.unpack_from('>QQ',b,o);o+=16
  if a==s==0:break
  assert o<=total
 return root,props,b[om:o],{'version':ver,'last_comp_version':last,'boot_cpuid_phys':cpu,'nodes':nodes}
def encode(root,reserve,meta):
 names={};strings=bytearray();out=bytearray()
 def word(v):out.extend(struct.pack('>I',v))
 def pad():out.extend(b'\0'*((-len(out))%4))
 def node(n):
  word(1);out.extend(n['name'].encode()+b'\0');pad()
  for kind,item in n['items']:
   if kind=='node':node(item)
   else:
    name,v=item
    if name not in names:names[name]=len(strings);strings.extend(name.encode()+b'\0')
    word(3);word(len(v));word(names[name]);out.extend(v);pad()
  word(2)
 node(root);word(9)
 om=40;os=om+len(reserve);ostr=os+len(out);total=ostr+len(strings)
 h=struct.pack('>10I',0xd00dfeed,total,os,ostr,om,meta['version'],meta['last_comp_version'],meta['boot_cpuid_phys'],len(strings),len(out))
 return h+reserve+out+strings

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--bootargs',required=True);ap.add_argument('--initrd-start',type=lambda s:int(s,0),required=True);ap.add_argument('--initrd-size',type=lambda s:int(s,0),required=True);ap.add_argument('--stdout-path');a=ap.parse_args()
 v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 dest=a.output.resolve();assert dest.is_relative_to(BASE) and not dest.exists();assert a.input.is_file() and not a.input.is_symlink()
 assert '\0' not in a.bootargs and 0<a.initrd_size<128*1024*1024 and 0<=a.initrd_start<a.initrd_start+a.initrd_size<2**64
 b=a.input.read_bytes();root,before,reserve,meta=parse(b)
 chosen=next((item for kind,item in root['items'] if kind=='node' and item['name']=='chosen'),None)
 if chosen is None:chosen={'name':'chosen','items':[]};root['items'].append(('node',chosen))
 replacements={'bootargs':a.bootargs.encode()+b'\0','linux,initrd-start':struct.pack('>Q',a.initrd_start),'linux,initrd-end':struct.pack('>Q',a.initrd_start+a.initrd_size)}
 if a.stdout_path:replacements['stdout-path']=a.stdout_path.encode()+b'\0'
 chosen['items']=[(k,it) for k,it in chosen['items'] if not(k=='prop' and it[0] in replacements)]
 chosen['items'].extend(('prop',(k,v)) for k,v in replacements.items())
 out=encode(root,reserve,meta);_,after,r2,m2=parse(out)
 allowed={('/chosen',k) for k in replacements};diff={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
 assert diff<=allowed and all(after[('/chosen',k)]==v for k,v in replacements.items()) and reserve==r2
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(out);sha=lambda q:hashlib.sha256(q).hexdigest()
 rec={'input':str(a.input.resolve()),'input_sha256':sha(b),'output':str(dest),'output_sha256':sha(out),'bytes':len(out),'only_changed_properties':[list(k) for k in sorted(diff)],'bootargs':a.bootargs,'initrd_start':hex(a.initrd_start),'initrd_end':hex(a.initrd_start+a.initrd_size),'reserve_map_unchanged':True,'nodes_before':meta['nodes'],'nodes_after':m2['nodes'],'original_fx3_kernel_changed':False}
 dest.with_suffix(dest.suffix+'.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
if __name__=='__main__':main()
