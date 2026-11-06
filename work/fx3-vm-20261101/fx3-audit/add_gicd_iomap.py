#!/usr/bin/env python3
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import importlib.util,struct,json,hashlib,argparse,plistlib,subprocess
BASE=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit').resolve()
spec=importlib.util.spec_from_file_location('dtb_codec',BASE/'prepare_virt_dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
p=a.output.resolve();assert p.is_relative_to(BASE) and not p.exists()
b=a.input.read_bytes();root,before,reserve,meta=m.parse(b);name='fx3-qemu-gicd-fixed-va';assert not any(k=='node' and x['name']==name for k,x in root['items'])
props={'device_type':b'iomap\0','phys':struct.pack('>Q',0x08000000),'virt':struct.pack('>Q',0xfffffffff13a1000),'size':struct.pack('>Q',0x1000),'memtype':struct.pack('>I',1)}
root['items'].append(('node',{'name':name,'items':[('prop',(k,v)) for k,v in props.items()]}));raw=m.encode(root,reserve,meta);_,after,r2,m2=m.parse(raw)
expected={('/'+name,k):v for k,v in props.items()};assert all(after[k]==v for k,v in before.items());assert {k:v for k,v in after.items() if k not in before}==expected and reserve==r2
p.write_bytes(raw);sha=lambda b:hashlib.sha256(b).hexdigest();rec={'input':str(a.input.resolve()),'input_sha256':sha(b),'output':str(p),'output_sha256':sha(raw),'bytes':len(raw),'unchanged_prior_properties':len(before),'added_node':'/'+name,'device_type':'iomap','phys':'0x08000000','virt':'0xfffffffff13a1000','size':'0x1000','memtype':1,'nodes_before':meta['nodes'],'nodes_after':m2['nodes'],'scope':'Guest virtual-address mapping to actual existing QEMU GICD physical model; no new QEMU MMIO backend, no page-table forging and no kernel patch. Properties verified against original FX3 map_io consumer. Not claimed as original setting DTB node.'}
p.with_suffix(p.suffix+'.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
