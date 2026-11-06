#!/usr/bin/env python3
"""Resume a bounded original Sony ZIP member range, validate and inflate data without execution."""
from pathlib import Path
from hashlib import sha256,file_digest
from datetime import datetime,timezone
import urllib.request,struct,json,os,shutil,zlib,plistlib,subprocess

HERE=Path(__file__).resolve().parent
OUT=HERE/'official-interim'


def main():
    vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert vol['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    meta=json.loads((HERE/'interim-zip-range-receipt.json').read_bytes())
    entry=meta['entries'][0];url=meta['url'];expected_etag=meta['requests'][0]['etag']
    assert entry['compression']==8 and entry['flags']==0 and entry['bytes']==1540002320
    req=urllib.request.Request(url,headers={'Range':'bytes=0-4095','Accept-Encoding':'identity'})
    with urllib.request.urlopen(req,timeout=30) as r:
        assert r.status==206 and r.headers['ETag']==expected_etag
        header=r.read(4097);assert len(header)==4096
    h=struct.unpack_from('<4s5H3I2H',header)
    assert h[0]==b'PK\x03\x04' and h[3]==8
    start=30+h[-2]+h[-1];name=header[30:30+h[-2]].decode()
    assert name==entry['name'] and h[6]==int(entry['crc32'],16) and h[7]==entry['compressed_bytes'] and h[8]==entry['bytes']
    OUT.mkdir(exist_ok=True)
    compressed=OUT/'interim-installer.deflate';partial=compressed.with_suffix('.deflate.part')
    target=OUT/'01_Update_ILMEFX3V20x.exe';target_partial=target.with_suffix('.exe.part')
    state=OUT/'download-state.json'
    if target.exists():
        done=json.loads((OUT/'member-receipt.json').read_bytes())
        with target.open('rb') as f:assert file_digest(f,'sha256').hexdigest()==done['exe_sha256']
        print('ALREADY_VERIFIED_ORIGINAL_MEMBER',target.name,flush=True);return
    if not compressed.exists():
        have=partial.stat().st_size if partial.exists() else 0
        assert not partial.is_symlink() and have<=entry['compressed_bytes']
        remaining=entry['compressed_bytes']-have
        assert shutil.disk_usage(OUT).free>=remaining+entry['bytes']+1024**3
        info=dict(url=url,etag=expected_etag,source_member=name,compressed_start=start,
                  compressed_bytes=entry['compressed_bytes'],downloaded=have,status='downloading',
                  camera_actions=0,installer_executed=False)
        state.write_text(json.dumps(info,indent=2)+'\n')
        if remaining:
            a=start+have;z=start+entry['compressed_bytes']-1
            req=urllib.request.Request(url,headers={'Range':f'bytes={a}-{z}','If-Range':expected_etag,'Accept-Encoding':'identity'})
            with urllib.request.urlopen(req,timeout=45) as r:
                assert r.status==206 and r.headers['ETag']==expected_etag
                assert r.headers['Content-Range']==f'bytes {a}-{z}/{meta["archive_bytes"]}'
                mode='ab' if have else 'xb';last=have
                with partial.open(mode) as out:
                    while have<entry['compressed_bytes']:
                        block=r.read(min(1024*1024,entry['compressed_bytes']-have));assert block,'short HTTP range'
                        out.write(block);have+=len(block)
                        if have-last>=32*1024*1024:
                            out.flush();info['downloaded']=have;state.write_text(json.dumps(info,indent=2)+'\n')
                            print('DOWNLOADED',have,'/',entry['compressed_bytes'],flush=True);last=have
                    out.flush();os.fsync(out.fileno())
                assert not r.read(1)
        assert partial.stat().st_size==entry['compressed_bytes'];partial.rename(compressed)
    assert compressed.stat().st_size==entry['compressed_bytes']
    # Existing partial inflation is preserved for inspection instead of silently overwritten.
    assert not target_partial.exists(),'Retained incomplete inflation requires review before retry.'
    d=zlib.decompressobj(-15);crc=0;size=0;hash_plain=sha256();hash_compressed=sha256()
    with compressed.open('rb') as inp,target_partial.open('xb') as out:
        os.chmod(target_partial,0o600)
        while block:=inp.read(4*1024*1024):
            hash_compressed.update(block);data=d.decompress(block);size+=len(data)
            assert size<=entry['bytes'];crc=zlib.crc32(data,crc);hash_plain.update(data);out.write(data)
        data=d.flush();size+=len(data);crc=zlib.crc32(data,crc);hash_plain.update(data);out.write(data)
        out.flush();os.fsync(out.fileno())
    assert d.eof and not d.unused_data and not d.unconsumed_tail
    assert size==entry['bytes'] and crc==int(entry['crc32'],16)
    target_partial.rename(target)
    receipt=dict(status='PASS_ORIGINAL_INTERIM_MEMBER_CRC_AND_SIZE',created_utc=datetime.now(timezone.utc).isoformat(),
                 source_page=meta['source_page'],url=url,etag=expected_etag,source_member=name,
                 compressed_range=[start,start+entry['compressed_bytes']-1],compressed_sha256=hash_compressed.hexdigest(),
                 exe_sha256=hash_plain.hexdigest(),exe_bytes=size,zip_crc32=hex(crc),
                 scope='Original official installer member downloaded as data and raw-deflate inflated. No Windows installer, firmware, USB or camera code executed.')
    (OUT/'member-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    state.write_text(json.dumps(dict(status='complete',downloaded=entry['compressed_bytes'],receipt='member-receipt.json'),indent=2)+'\n')
    print(receipt['status'],'bytes',size,'sha256',receipt['exe_sha256'],flush=True)


if __name__=='__main__':main()
