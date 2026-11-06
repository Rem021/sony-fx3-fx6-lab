#!/usr/bin/env python3
"""Replace only one newc member in the fixed FX3 CPIO; preserve everything else and pad to the fixed length."""
import hashlib, json, sys
from pathlib import Path

SOURCE = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/guest-hybrid-fx6kernel-capid-grmreal41.cpio')
NEW_KO = Path(__file__).resolve().parent / 'grm-fbinit' / 'upm-callsite-skip.ko'
OUT = Path(__file__).resolve().parent / 'guest-hybrid-fx6kernel-capid-grmreal46.cpio'
TARGET = b'usr/kmod/upm.ko'
FIXED_BYTES = 453184500


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def members(path):
    with Path(path).open('rb') as f:
        while True:
            header = f.read(110)
            if len(header) != 110:
                raise ValueError('short header')
            if header[:6] != b'070701':
                raise ValueError('not newc: ' + header[:6].decode('ascii', 'replace'))
            namesize = int(header[94:102], 16)
            filesize = int(header[54:62], 16)
            name = f.read(namesize).rstrip(b'\0')
            f.read((4 - (110 + namesize) % 4) % 4)
            payload_offset = f.tell()
            payload = f.read(filesize)
            if len(payload) != filesize:
                raise ValueError('short payload ' + name.decode('ascii', 'replace'))
            f.read((4 - filesize % 4) % 4)
            yield name, header, payload, payload_offset
            if name == b'TRAILER!!!':
                return


def main():
    new_ko = NEW_KO.read_bytes()
    out = OUT
    if out.exists():
        raise SystemExit('refusing to overwrite ' + str(out))
    found = 0
    written = 0
    target_info = None
    with SOURCE.open('rb') as src, out.open('wb') as dst:
        while True:
            header = src.read(110)
            if len(header) != 110:
                raise ValueError('short header')
            if header[:6] != b'070701':
                raise ValueError('not newc')
            namesize = int(header[94:102], 16)
            filesize = int(header[54:62], 16)
            name = src.read(namesize).rstrip(b'\0')
            name_pad = (4 - (110 + namesize) % 4) % 4
            src.read(name_pad)
            payload = src.read(filesize)
            if len(payload) != filesize:
                raise ValueError('short payload')
            payload_pad = (4 - filesize % 4) % 4
            src.read(payload_pad)
            if name == TARGET:
                found += 1
                target_info = {'name': name.decode(), 'old_bytes': filesize,
                               'old_sha256': hashlib.sha256(payload).hexdigest(),
                               'new_bytes': len(new_ko), 'new_sha256': hashlib.sha256(new_ko).hexdigest()}
                header = bytearray(header)
                header[54:62] = f'{len(new_ko):08x}'.encode()
                if header[102:110] != b'00000000':
                    raise ValueError('unexpected newc check field')
                payload = new_ko
                filesize = len(new_ko)
                payload_pad = (4 - filesize % 4) % 4
            name_blob = name + b'\0' * ((namesize - len(name)) if namesize >= len(name) else 1)
            for blob in (header, name_blob, b'\0' * name_pad, payload, b'\0' * payload_pad):
                dst.write(blob)
                written += len(blob)
            if name == b'TRAILER!!!':
                break
        if found != 1:
            raise ValueError('target member count ' + str(found))
        remaining = FIXED_BYTES - written
        if remaining < 0:
            raise ValueError('new CPIO exceeds fixed length by ' + str(-remaining))
        dst.write(b'\0' * remaining)
        written += remaining
        dst.flush()
    info = {'schema': 'fx6-hybrid-upmcallsite-cpio-v1', 'source': str(SOURCE),
            'source_sha256': sha(SOURCE), 'output': str(out), 'output_sha256': sha(out),
            'fixed_bytes': FIXED_BYTES, 'output_bytes': written,
            'target': target_info, 'replaced_member_count': found,
            'scope': 'Only the named CPIO member payload/header size changed; all other member bytes copied; trailing padding zeros to fixed length.'}
    (out.parent / 'UPMCALLSITE-CPIO-BUILD.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
