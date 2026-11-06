#!/usr/bin/env python3
"""Acquire the exact public catalogue URL and inspect ZIP data, never run it."""
import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import subprocess
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE / 'AXS601-acquisition.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    catalogue = json.loads((HERE / 'AXS601-China-catalog.json').read_text())
    assert catalogue['http_status'] == 200 and catalogue['result'] and catalogue['code'] == '00'
    item = next(x for x in catalogue['response']['returnData']['Data'] if x['id'] == '00003229')
    assert item['modelName'] == ['AXS-R7'] and len(item['downloadPath']) == 1
    url = item['downloadPath'][0]
    assert url.startswith('https://download.pro.sony/') and url.endswith('/AXS-R7_V601.zip')
    result = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'official_catalogue_id': item['id'],
              'url': url, 'device_actions': 0, 'vendor_program_execution': False}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'FirmwareCatalogResearch/1.0', 'Accept-Encoding': 'identity'}), timeout=30) as response:
            assert response.code == 200
            data = response.read(40*1024*1024 + 1)
            assert len(data) <= 40*1024*1024
            result.update(http_status=response.code, final_url=response.url,
                          headers={k:v for k,v in response.headers.items() if k.lower() in ['content-length','content-type','etag','date']})
        target = HERE / 'AXS-R7_V601.zip'
        with target.open('xb') as out:
            out.write(data)
        result.update(path=target.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        output = HERE / 'AXS601-members'
        output.mkdir(exist_ok=False)
        members, saved = [], []
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.infolist()
            assert len(info) < 128 and sum(x.file_size for x in info) < 128*1024*1024
            for row in info:
                assert row.file_size < 64*1024*1024 and not row.flag_bits & 1
                member = {'name': row.filename, 'bytes': row.file_size, 'compression': row.compress_type, 'CRC32': f'{row.CRC:08x}'}
                if not row.is_dir():
                    payload = archive.read(row)
                    member.update(CRC32_verified=True, sha256=hashlib.sha256(payload).hexdigest())
                    if row.filename.lower().endswith(('.bin','.md5','.txt')):
                        name = PurePosixPath(row.filename).name
                        assert name and name not in saved
                        with (output / name).open('xb') as out:
                            out.write(payload)
                        saved.append(name)
                        member['saved_path'] = 'AXS601-members/' + name
                members.append(member)
        firmware_rows = [r for r in members if r.get('saved_path','').lower().endswith('.bin')]
        md5_rows = [r for r in members if r.get('saved_path','').lower().endswith('.md5')]
        assert len(firmware_rows) == len(md5_rows) == 1
        firmware = (HERE / firmware_rows[0]['saved_path']).read_bytes()
        text = (HERE / md5_rows[0]['saved_path']).read_text('ascii')
        lines = text.splitlines()
        assert len(lines) == 2 and lines[0] == PurePosixPath(firmware_rows[0]['saved_path']).name + ' MD5 Hush'
        expected = lines[1].strip().lower()
        actual = hashlib.md5(firmware, usedforsecurity=False).hexdigest()
        assert len(expected) == 32 and expected == actual
        result.update(result='COMPLETE_OFFICIAL_ZIP_CRC_AND_FIRMWARE_MD5_VERIFIED', members=members,
                      firmware_path=firmware_rows[0]['saved_path'], firmware_bytes=len(firmware),
                      firmware_sha256=hashlib.sha256(firmware).hexdigest(), firmware_md5=actual, adjacent_md5_text=text,
                      PDF_contents_read=False, decoded_private_loader_or_ISP=False)
    except Exception as error:
        result.update(result='ACQUISITION_OR_VALIDATION_GAP', error={'type':type(error).__name__, 'message':str(error)})
    (HERE / 'AXS601-acquisition.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k in ['result','http_status','bytes','firmware_bytes','firmware_sha256','error']},ensure_ascii=False))


if __name__ == '__main__':
    main()
