#!/usr/bin/env python3
"""Extract only two regular files from pinned official images, without mounting."""
from pathlib import Path
import datetime,hashlib,json,plistlib,subprocess,sys,zlib
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
SOURCE=BASE/'stage2/extraction'
sys.path.insert(0,str(SOURCE));from read_filesystems import Ext2,FAT16
def digest(p):
    h=hashlib.sha256();crc=0
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b);crc=zlib.crc32(b,crc)
    return h.hexdigest(),hex(crc)
def volume():
    j=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert j['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and j['Writable']
def main():
    volume();assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    manifests=json.loads((SOURCE/'partition-carve-manifest.json').read_text())
    official=json.loads((SOURCE/'official-partition-verification.json').read_text())
    out=[]
    for part,name,local in [('15','/kmod/dmm.ko','dmm.ko'),('8','/DmmCfg.bin','DmmCfg.bin')]:
        src=SOURCE/('nflasha'+part+'.img');m=next(x for x in manifests if x['source_member'].endswith('/nflasha'+part))
        h,crc=digest(src);assert h==m['sha256'] and crc==m['crc32'] and src.stat().st_size==m['size']
        o=next(x for x in official if x['partition']=='nflasha'+part)
        assert o['size_matches_official'] and o['crc32_matches_official'] and crc==o['crc32']
        fs=Ext2(src) if part=='15' else FAT16(src)
        try:
            entries=[x for x in fs.walk() if x['path']==name];assert len(entries)==1
            e=entries[0];assert e['type']==0x8000
            raw=fs.data(e['inode']) if part=='15' else fs.data(e['cluster'],e['size'])
            assert len(raw)==e['size'];p=STAGE/'inputs'/local
            with p.open('xb') as f:f.write(raw)
            out.append({'original_partition':str(src.relative_to(ROOT)),'partition_sha256':h,'partition_crc32':crc,
                'partition_official_size_crc_matched':True,'regular_file_entry':e,
                'output':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'first64':raw[:64].hex()})
        finally:fs.b.close();fs.f.close()
    j={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':out,
        'source_reader':str((SOURCE/'read_filesystems.py').relative_to(ROOT)),'source_reader_sha256':digest(SOURCE/'read_filesystems.py')[0],
        'source_images_opened_read_only':True,'mount_host_loader_or_camera_execution':False}
    with (STAGE/'input-receipt.json').open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
