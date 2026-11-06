#!/usr/bin/env python3
"""Repack one newc member, preserving all other records and the initrd extent."""
import hashlib
import json
import os
import plistlib
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DONOR = HERE.parent
MAC = HERE.parents[5]
SOURCE = DONOR / 'hybrid-entry-candidate/guest-two-entry.cpio'
AP = DONOR / 'nflasha15-files/lib/appFw.so'
OUT = HERE / 'guest-three-entry.cpio'
PINS = {
    SOURCE: 'ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40',
    AP: 'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
}
TARGET = 'usr/lib/appFw.so'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def records(stream):
    offset = 0
    while True:
        stream.seek(offset)
        header = stream.read(110)
        if len(header) != 110 or header[:6] != b'070701':
            raise ValueError(f'invalid newc header at {offset}')
        size, nsize = int(header[54:62], 16), int(header[94:102], 16)
        if not 1 <= nsize <= 4096:
            raise ValueError('name size')
        raw_name = stream.read(nsize)
        if not raw_name.endswith(b'\0'):
            raise ValueError('unterminated name')
        name = raw_name[:-1].decode('utf-8')
        data = (offset + 110 + nsize + 3) & ~3
        end = (data + size + 3) & ~3
        yield name, offset, data, end, header
        if name == 'TRAILER!!!':
            break
        offset = end


def copy_range(src, dst, start, length):
    src.seek(start)
    while length:
        data = src.read(min(length, 1 << 20))
        if not data:
            raise ValueError('truncated source')
        dst.write(data)
        length -= len(data)


def main():
    disk = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert disk['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    for path, expected in PINS.items():
        assert sha(path) == expected, path
    assert SOURCE.stat().st_size == 453184500 and AP.stat().st_size == 50520424
    if OUT.exists():
        raise FileExistsError(f'preserve existing candidate: {OUT}')
    temp = OUT.with_suffix('.cpio.partial')
    if temp.exists():
        raise FileExistsError(f'preserve partial: {temp}')
    changed = 0
    count = 0
    try:
        with SOURCE.open('rb') as source, AP.open('rb') as ap, temp.open('xb') as target:
            for name, offset, data, end, header in records(source):
                if name == TARGET:
                    assert int(header[54:62], 16) == 79015712
                    altered = header[:54] + f'{AP.stat().st_size:08x}'.encode() + header[62:]
                    target.write(altered)
                    copy_range(source, target, offset + 110, data - offset - 110)
                    target.write(ap.read())
                    target.write(b'\0' * ((-target.tell()) & 3))
                    changed += 1
                else:
                    copy_range(source, target, offset, end - offset)
                count += name != 'TRAILER!!!'
            assert changed == 1 and count == 1140
            assert target.tell() < SOURCE.stat().st_size
            padding = SOURCE.stat().st_size - target.tell()
            assert padding == 28495288
            chunk = b'\0' * (1 << 20)
            while padding:
                n = min(padding, len(chunk))
                target.write(chunk[:n])
                padding -= n
            target.flush()
            os.fsync(target.fileno())
        assert temp.stat().st_size == SOURCE.stat().st_size
        temp.rename(OUT)
    except Exception:
        if temp.exists():
            temp.unlink()
        raise
    print(json.dumps({'candidate': str(OUT), 'sha256': sha(OUT), 'bytes': OUT.stat().st_size,
                      'changed_member': TARGET, 'members': count, 'status': 'BUILT_STATIC_ONLY'}, indent=2))


if __name__ == '__main__':
    main()
