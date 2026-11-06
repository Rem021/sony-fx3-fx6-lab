#!/usr/bin/env python3
"""Resume local validation after a case-sensitive MD5 selector failed; no network."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE / 'AXS601-local-verification.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    prior = json.loads((HERE / 'AXS601-acquisition.json').read_text())
    assert prior['http_status'] == 200 and prior['result'] == 'ACQUISITION_OR_VALIDATION_GAP'
    path = HERE / prior['path']
    with path.open('rb') as source:
        assert hashlib.file_digest(source, 'sha256').hexdigest() == prior['sha256']
    assert path.stat().st_size == prior['bytes']
    members = []
    with zipfile.ZipFile(path) as archive:
        for row in archive.infolist():
            member = {'name': row.filename, 'bytes': row.file_size, 'CRC32': f'{row.CRC:08x}', 'compression': row.compress_type}
            if not row.is_dir():
                payload = archive.read(row)
                member.update(CRC32_verified=True, sha256=hashlib.sha256(payload).hexdigest())
                if row.filename.lower().endswith(('.bin','.md5','.txt')):
                    saved = HERE / 'AXS601-members' / PurePosixPath(row.filename).name
                    assert saved.read_bytes() == payload
                    member['saved_path'] = str(saved.relative_to(HERE))
            members.append(member)
    firmware = [r for r in members if r.get('saved_path','').lower().endswith('.bin')]
    md5 = [r for r in members if r.get('saved_path','').lower().endswith('.md5')]
    assert len(firmware) == len(md5) == 1
    data = (HERE / firmware[0]['saved_path']).read_bytes()
    text = (HERE / md5[0]['saved_path']).read_text('ascii')
    lines = text.splitlines()
    assert len(lines) == 2 and lines[0] == PurePosixPath(firmware[0]['saved_path']).name + ' MD5 Hush'
    expected = lines[1].strip().lower()
    actual = hashlib.md5(data, usedforsecurity=False).hexdigest()
    assert len(expected) == 32 and expected == actual
    result = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'result': 'COMPLETE_OFFICIAL_ZIP_CRC_AND_FIRMWARE_MD5_VERIFIED',
              'original_acquisition_receipt': 'AXS601-acquisition.json', 'ZIP_sha256': prior['sha256'],
              'development_failure': 'All ZIP members were read and selected files saved, but the initial final selector compared .md5 case-sensitively and missed .MD5. A first local check then assumed hash-first text; the actual text has a filename MD5 Hush line and a standalone hash line. Both parsing assumptions were corrected from the source text. Retained failed acquisition receipt; no repeated download.',
              'members': members, 'firmware_path': firmware[0]['saved_path'], 'firmware_bytes': len(data),
              'firmware_sha256': hashlib.sha256(data).hexdigest(), 'firmware_md5': actual,
              'adjacent_md5_text': text, 'network_requests': 0, 'PDF_contents_read': False,
              'vendor_execution': False, 'device_actions': 0, 'decoded_private_loader_or_ISP': False}
    (HERE / 'AXS601-local-verification.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k in ['result','firmware_bytes','firmware_sha256','network_requests']}))


if __name__ == '__main__':
    main()
