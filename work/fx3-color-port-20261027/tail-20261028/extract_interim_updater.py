#!/usr/bin/env python3
"""Extract only original interim update-engine/config members; no mounts or execution."""
from pathlib import Path
from hashlib import sha256
import json,os,zlib
from read_original_fdat import HERE,FDAT,public_keys

SELECT = ('0400_updater/dev/nflasha1','0401_updater_sum/updater.sum',
          '0300_partconf/partinf.conf','0100_config/mount.conf')


def main():
    meta=json.loads((HERE/'interim-fdat-inventory.json').read_bytes());keys=public_keys();rows=[]
    for pkg in meta['packages']:
        fdat=FDAT(HERE/pkg['source'],keys,pkg['source_sha256']);version=pkg['header']['firmware_version'];items=[]
        destdir=HERE/'interim-update-engine'/version;destdir.mkdir(parents=True,exist_ok=True)
        for name in SELECT:
            entry=next(x for x in pkg['tar_members'] if x['name']==name);dest=destdir/Path(name).name
            assert not dest.exists();h=sha256();crc=0;written=0
            with dest.open('xb') as out:
                os.chmod(dest,0o600)
                while written<entry['size']:
                    n=min(4*1024*1020,entry['size']-written)
                    data=fdat.read(pkg['header']['firmware_offset']+entry['data_offset_in_tar']+written,n)
                    out.write(data);h.update(data);crc=zlib.crc32(data,crc);written+=len(data)
                out.flush();os.fsync(out.fileno())
            items.append(dict(member=name,bytes=written,sha256=h.hexdigest(),crc32=f'{crc:08x}',output=str(dest.relative_to(HERE))))
        # Original updater.sum provides the separate CRC32 receipt for nflasha1.
        sums=(destdir/'updater.sum').read_text();image=next(x for x in items if x['member'].endswith('nflasha1'))
        assert image['crc32'] in sums.lower(),sums
        rows.append(dict(version=version,source=fdat.summary(),members=items,original_updater_sum=sums,updater_crc32_matches=True));fdat.close()
        print('ORIGINAL_UPDATE_ENGINE',version,image,flush=True)
    assert len(rows)==2
    result=dict(status='PASS_ORIGINAL_INTERIM_UPDATE_ENGINE_EXTRACTED',packages=rows,
        images_identical=rows[0]['members'][0]['sha256']==rows[1]['members'][0]['sha256'],
        scope='Only original member data extracted, all read CBC blocks checked and original updater CRC32 matched. No updater, installer, firmware or device execution.')
    (HERE/'interim-update-engine-results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
