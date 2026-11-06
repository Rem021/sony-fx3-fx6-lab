#!/usr/bin/env python3
"""Fully enumerate and extract regular original initrd files, without mounting or execution."""
from pathlib import Path
from hashlib import sha256
import json,os,re
from read_squashfs4_gzip import SquashFS

HERE=Path(__file__).resolve().parent


def main():
    oracle=json.loads((HERE/'squashfs-reader-oracle-results.json').read_bytes());assert oracle['status']=='PASS_INDEPENDENT_SQUASHFS_ORACLE_702' and oracle['entries']==65
    packages=json.loads((HERE/'updater-fat-extraction-results.json').read_bytes())['packages'];results=[]
    for package in packages:
        member=next(m for m in package['files'] if m['path']=='/boot/initrd.img');data=(HERE/member['output']).read_bytes()
        assert sha256(data).hexdigest()==member['sha256']
        image=SquashFS(data);rows=[];total=0;out=HERE/'engine-rootfs'/package['version'];assert not out.exists();out.mkdir(parents=True)
        for entry in image.walk():
            row=dict(entry)
            if entry['type']=='file':
                assert entry['size']<=32*1024*1024
                raw=image.contents(entry);total+=len(raw);assert total<=128*1024*1024
                dest=out/entry['path'].lstrip('/');assert dest.resolve().is_relative_to(out.resolve());dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as f:os.chmod(dest,0o600);f.write(raw)
                row.update(sha256=sha256(raw).hexdigest(),output=str(dest.relative_to(HERE)),elf=raw[:4]==b'\x7fELF')
                tokens=[]
                for token in [b'sdfileinput',b'libInfraSKD',b'BODYDATA',b'FDAT',b'SKD_Verify',b'SKD_Sign']:
                    offsets=[];pos=0
                    while (pos:=raw.find(token,pos))!=-1:offsets.append(hex(pos));pos+=1
                    if offsets:tokens.append(dict(token=token.decode(),offsets=offsets))
                if tokens:row['input_verifier_tokens']=tokens
            rows.append(row)
        result=dict(version=package['version'],source=member['output'],source_sha256=member['sha256'],
            filesystem_header=image.header,entries=rows,total_regular_bytes=total,ordinary_files=sum(e['type']=='file' for e in rows))
        results.append(result);print('ORIGINAL_INITRD_COMPLETE',package['version'],'entries',len(rows),'regular_bytes',total,flush=True)
        for row in rows:
            if row.get('input_verifier_tokens') or re.search(r'sdfile|updater|crypt|skd',row['path'],re.I):print(row['path'],row['type'],row['size'],row.get('input_verifier_tokens',[]),flush=True)
    (HERE/'original-initrd-inventory.json').write_text(json.dumps(dict(status='PASS_ORIGINAL_INITRD_FULL_REGULAR_EXTRACTION',
        parser_source='read_squashfs4_gzip.py',parser_sha256=sha256((HERE/'read_squashfs4_gzip.py').read_bytes()).hexdigest(),packages=results,
        scope='Original SquashFS4/gzip images parsed without mount. All ordinary files extracted as non-executable data; symlinks/devices/special objects recorded only, never created. No Sony program, kernel, updater, signing code or device execution.'),indent=2)+'\n')


if __name__=='__main__':main()
