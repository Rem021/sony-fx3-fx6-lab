#!/usr/bin/env python3
"""Read Apple gzip/odc component archives; links and installer scripts stay inert."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import stat
import subprocess
import zlib

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE / 'payload-inventory.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    archive = json.loads((HERE / 'XAR-structure.json').read_text())
    packages = []
    for source in archive['entries']:
        if not source.get('saved_path','').endswith('/Payload'):
            continue
        compressed = (HERE / source['saved_path']).read_bytes()
        assert hashlib.sha256(compressed).hexdigest() == source['sha256']
        decoder = zlib.decompressobj(31)
        data = decoder.decompress(compressed,128*1024*1024+1)
        assert len(data) <= 128*1024*1024 and decoder.eof and not decoder.unused_data
        package = PurePosixPath(source['path']).parent.name
        cursor = 0
        rows = []
        seen = set()
        while True:
            assert cursor + 76 <= len(data)
            origin = cursor
            header = data[cursor:cursor+76]
            assert header[:6] == b'070707'
            fields = [int(header[a:b],8) for a,b in [(6,12),(12,18),(18,24),(24,30),(30,36),(36,42),(42,48),(48,59),(59,65),(65,76)]]
            dev, inode, mode, uid, gid, links, rdev, mtime, name_size, size = fields
            cursor += 76
            assert 1 <= name_size < 4096 and 0 <= size < 64*1024*1024
            name = data[cursor:cursor+name_size]
            assert len(name) == name_size and name[-1:] == b'\0' and b'\0' not in name[:-1]
            text = name[:-1].decode('utf-8')
            cursor += name_size
            if text == 'TRAILER!!!':
                assert size == 0 and not any(data[cursor:])
                break
            path = PurePosixPath(text)
            assert not path.is_absolute() and '..' not in path.parts
            normalized = str(path)
            assert normalized not in seen
            seen.add(normalized)
            payload = data[cursor:cursor+size]
            assert len(payload) == size
            cursor += size
            row = {'path':normalized, 'mode_octal':oct(mode), 'inode':inode, 'links':links,
                   'bytes':size, 'cpio_header_offset':origin,'data_offset':cursor-size}
            if stat.S_ISREG(mode):
                target = HERE / 'payload-files' / package / Path(normalized)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as out:
                    out.write(payload)
                row.update(type='file', sha256=hashlib.sha256(payload).hexdigest(), saved_path=str(target.relative_to(HERE)))
            elif stat.S_ISDIR(mode):
                row['type'] = 'directory'
            elif stat.S_ISLNK(mode):
                row.update(type='symlink_not_created',target=payload.decode('utf-8'))
            else:
                row['type'] = 'special_not_created'
            rows.append(row)
        packages.append({'component':package,'source':source['saved_path'],'source_sha256':source['sha256'],
                         'gzip_CRC_verified':True,'uncompressed_bytes':len(data),'uncompressed_sha256':hashlib.sha256(data).hexdigest(),
                         'cpio_consumed_through_trailer':cursor,'zero_padding_bytes':len(data)-cursor,'entries':rows})
    result = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'packages':packages,
              'total_regular_files':sum(r['type']=='file' for p in packages for r in p['entries']),
              'symlinks_or_specials_created':False,'scripts_run':False,'vendor_execution':False,'device_actions':0}
    (HERE / 'payload-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'components':len(packages),'regular_files':result['total_regular_files']}))
    for package in packages:
        print(package['component'])
        for row in package['entries']:
            if row['type']=='file' and (package['component']=='Firmware.pkg' or '/MacOS/' in row['path'] or row['path'].endswith(('.dylib','.bin'))):
                print(' ',row['path'],row['bytes'])


if __name__ == '__main__':
    main()
