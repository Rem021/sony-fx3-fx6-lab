#!/usr/bin/env python3
"""Pin the installed updater image and identify marker references in current AP."""
from pathlib import Path
import hashlib,json,sys
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from assemble_body_guest import HERE,AP,View,sources

def main():
    root=HERE.parents[2]/'work/sony-firmware-20261024/stage2/extraction';sys.path.insert(0,str(root));from read_filesystems import Ext2
    partition=root/'nflasha15.img';pin='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    with partition.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==pin
    fs=Ext2(partition);hits=[];installed=None;count=0;tokens=[b'IAMUPDATER',b'udtrbody.bin']
    for item in fs.walk():
        if item['type']!=0x8000:continue
        count+=1;raw=fs.data(item['inode'])
        if item['path']=='/bin/udtrbody.bin':installed=dict(path=item['path'],inode=item['inode'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        for token in tokens:
            at=raw.find(token)
            if at<0:continue
            occurrences=[]
            while at>=0:
                occurrences.append(dict(offset=hex(at),context=raw[max(0,at-32):at+len(token)+64].decode('utf-8',errors='replace')))
                at=raw.find(token,at+len(token))
            hits.append(dict(path=item['path'],token=token.decode(),source_sha256=hashlib.sha256(raw).hexdigest(),occurrences=occurrences))
    prior=json.loads((HERE.parent/'package-20261028/updater-inventory.json').read_text());assert installed['bytes']==prior['filesystem_bytes'] and installed['sha256']==prior['filesystem_sha256']
    fragments=[];out=HERE/'fragments';out.mkdir(exist_ok=True)
    for source in sources():
        view=View(source['path'],source['sha256'])
        targets={'libupdatercorecommon.so':[(0x9064,0x98),(0xc1a8,16)],'libfileinputupdaterapi.so':[(0x3e64,0x100)]}.get(view.path.name,[])
        for va,size in targets:
            raw=view.read(va,size);lines=[]
            for ins in Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(raw,va):
                note=''
                if ins.mnemonic in ['b','bl'] and ins.op_str.startswith('#'):
                    label=view.labels.get(int(ins.op_str[1:],0))
                    if label:note=' ; '+label
                lines.append(f'{ins.address:08x} {ins.mnemonic:10} {ins.op_str}{note}')
            dest=out/f'{view.path.name}-{va:x}.txt';dest.write_text('\n'.join(lines)+'\n')
            fragments.append(dict(library=view.path.name,source_sha256=source['sha256'],va=hex(va),bytes=size,sha256=hashlib.sha256(raw).hexdigest(),output=str(dest.relative_to(HERE))))
    result=dict(partition_sha256=pin,regular_files_read=count,preinstalled_updater_image=installed,installed_image_matches_official_embedded_updater=True,marker_references=hits,selected_fragments=fragments,
                scope='AP ext2 regular files and original instruction fragments only. The runtime selection literal is /usr/bin/udtrbody.bin; the file is /bin/udtrbody.bin relative to the AP partition. This scan does not enumerate the complete Linux runtime root, prove /root/IAMUPDATER presence/absence, identify every possible writer, or establish camera loading policy. No binary is run or mounted.')
    (HERE/'image-origin-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(regular_files=count,installed=installed,reference_paths=sorted({r['path'] for r in hits}))))

if __name__=='__main__':main()
