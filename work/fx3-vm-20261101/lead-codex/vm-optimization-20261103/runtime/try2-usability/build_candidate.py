#!/usr/bin/env python3
"""Derive long-session input guest from the frozen TRY2 CPIO, without touching it."""
from pathlib import Path
import hashlib, importlib.util, json, plistlib, struct, subprocess, sys

HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parents[3]/'menu-repair-01/runtime'
BASE=HERE.parent/'try2-delivery/vmopt-20261103-try2-v1/candidate.json'
NEW=HERE/'vmopt-20261103-try2-long-v1'
sys.path.insert(0,str(RUNTIME))
from cpio_audit import parse,audit

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def add(out,name,fields,body,i):
    fields=fields.copy();filename=name.encode()+b'\0';fields[0]=i;fields[6]=len(body);fields[11]=len(filename)
    out.extend(b'070701'+''.join(f'{v:08x}' for v in fields).encode()+filename)
    out.extend(b'\0'*(-len(out)%4));out.extend(body);out.extend(b'\0'*(-len(out)%4))

def main():
    assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    assert not NEW.exists()
    v=json.loads(BASE.read_text());old=Path(v['initrd']['path']);assert sha(old)==v['initrd']['sha256']
    source=HERE/'src/fx3-rm-empty-provider-v8-long-use.so';build=json.loads((HERE/'src/guest-build.json').read_text());assert sha(source)==build['output_sha256']
    data=old.read_bytes();off=0;entries=[];target='simulation/fx3-rm-empty-provider-v3-setup.so';changed=0
    while True:
        f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)]
        name=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3
        body=data[off:off+f[6]];off=(off+f[6]+3)&~3
        if name=='TRAILER!!!':break
        if name==target:
            assert hashlib.sha256(body).hexdigest()=='a9bab6e22798e3f7cffddc7cb9ae4c8f9712552b2c6aa96bfb455f88a1de8c93'
            body=source.read_bytes();changed+=1
        entries.append((name,f,body))
    assert changed==1
    NEW.mkdir();out=bytearray()
    for i,(name,f,body) in enumerate(entries,1):add(out,name,f,body,i)
    add(out,'TRAILER!!!',[0]*13,b'',len(entries)+1)
    cpio=NEW/'guest.cpio';cpio.write_bytes(out)
    spec=importlib.util.spec_from_file_location('fdt',RUNTIME.parents[1]/'fx3-audit/prepare_virt_dtb.py');fdt=importlib.util.module_from_spec(spec);spec.loader.exec_module(fdt)
    tree,_,res,meta=fdt.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen')
    chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']]
    dtb=NEW/'guest.dtb';dtb.write_bytes(fdt.encode(tree,res,meta))
    v['initrd']={'path':str(cpio),'sha256':sha(cpio)};v['dtb']={'path':str(dtb),'sha256':sha(dtb)}
    v['host_step_contract']['max_steps']=4096
    v['try2_usability_contract']={'base':str(BASE),'base_sha256':sha(BASE),'only_changed_CPIO_member':target,'old_sha256':'a9bab6e22798e3f7cffddc7cb9ae4c8f9712552b2c6aa96bfb455f88a1de8c93','new_sha256':sha(source),'guest_max_steps':4096,'control_page_single_slot':True,'native_input_queue_and_message_schema_unchanged':True,'original_receive_budget_ms':5000,'original_seed_unchanged':True,'dtb_only_initrd_end':True,'source_build':str(HERE/'src/guest-build.json')}
    manifest=NEW/'candidate.json';manifest.write_text(json.dumps(v,indent=2)+'\n')
    _,before=parse(old);_,after=parse(cpio)
    assert set(before)==set(after) and [n for n in before if before[n]!=after[n]]==[target]
    result=audit(cpio,Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio'))
    assert result['safe_to_unpack'];(NEW/'cpio-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    receipt={'candidate':str(manifest),'candidate_sha256':sha(manifest),'base':str(BASE),'base_sha256':sha(BASE),'changed_member':target,'all_other_members_unchanged':True,'old_member_sha256':v['try2_usability_contract']['old_sha256'],'new_member_sha256':sha(source),'dtb_only_initrd_end':True,'init_script_unchanged':True,'seed_unchanged':True}
    (NEW/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
