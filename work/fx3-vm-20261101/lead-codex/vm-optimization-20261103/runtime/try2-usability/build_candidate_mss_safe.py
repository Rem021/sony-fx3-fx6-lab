#!/usr/bin/env python3
"""Derive an original-app MSS read-only probe from the power-observe candidate."""
from pathlib import Path
import hashlib, importlib.util, json, plistlib, struct, subprocess, sys

HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parents[3]/'menu-repair-01/runtime'
BASE=HERE/'vmopt-20261103-try2-power-observe-v1/candidate.json'
NEW=HERE/'vmopt-20261103-try2-mss-safe-v2'
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
    source=HERE/'src/fx3-media-observe-v7-mss-safe.so';build=json.loads((HERE/'src/fx3-media-observe-v7-mss-safe-build.json').read_text());assert sha(source)==build['output_sha256']
    data=old.read_bytes();off=0;entries=[];target='simulation/fx3-media-observe-v3-uipc.so';changed=0
    while True:
        f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)]
        name=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3
        body=data[off:off+f[6]];off=(off+f[6]+3)&~3
        if name=='TRAILER!!!':break
        if name==target:
            assert hashlib.sha256(body).hexdigest()=='0fd9fdfcd7309a2d87b6c4690048cd7ffccfee8825e578b6c286d9fdca146197'
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
    v['mss_passive_contract']={'base':str(BASE),'base_sha256':sha(BASE),'only_changed_CPIO_member':target,'old_sha256':'0fd9fdfcd7309a2d87b6c4690048cd7ffccfee8825e578b6c286d9fdca146197','new_sha256':sha(source),'original_appFw_sha256':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f','observed_original_instruction_words':{'0x2d35168':'0xa9bc7bfd','0x2eb4f58':'0x72b01240','0x2eaf294':'0xa9ba7bfd','0x2eaf308':'0x7100001f'},'bounded_ring_records':256,'power_observer_unchanged':True,'original_power_state_and_timeout_unchanged':True,'source_build':str(HERE/'src/fx3-media-observe-v7-mss-safe-build.json')}
    v['required_markers'].append('FX3_MSS_OBSERVER_BOUND')
    manifest=NEW/'candidate.json';manifest.write_text(json.dumps(v,indent=2)+'\n')
    _,before=parse(old);_,after=parse(cpio)
    assert set(before)==set(after) and [n for n in before if before[n]!=after[n]]==[target]
    result=audit(cpio,Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio'))
    assert result['safe_to_unpack'];(NEW/'cpio-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    receipt={'candidate':str(manifest),'candidate_sha256':sha(manifest),'base':str(BASE),'base_sha256':sha(BASE),'changed_member':target,'all_other_members_unchanged':True,'old_member_sha256':v['mss_passive_contract']['old_sha256'],'new_member_sha256':sha(source),'dtb_only_initrd_end':True,'init_script_unchanged':True,'seed_unchanged':True}
    (NEW/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
