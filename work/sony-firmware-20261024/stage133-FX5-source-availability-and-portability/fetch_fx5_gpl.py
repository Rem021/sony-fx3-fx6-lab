#!/usr/bin/env python3
"""Download only selected GPL archives linked by Sony's captured FX5 model page."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256, md5
from pathlib import Path
from urllib.parse import urlparse
import base64
import importlib.util
import json
import plistlib
import subprocess
import urllib.request

HERE = Path(__file__).resolve().parent
WANTED = {'linux-kernel.tar.gz', 'cemmc-init.tar.gz', 'cryptoram.tar.gz', 'ldec.tar.gz', 'sio.tar.gz'}
LIMIT = 512 * 1024 * 1024


def fetch(url):
    destination = HERE / 'gpl-archives' / Path(urlparse(url).path).name
    record = {'url': url, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'path': destination.relative_to(HERE).as_posix()}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'OfflineFirmwareResearch/1.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            assert response.status == 200
            size = int(response.headers['Content-Length'])
            assert 0 < size <= LIMIT
            record.update({'expected_bytes': size, 'content_md5': response.headers.get('Content-MD5'),
                           'etag': response.headers.get('ETag'), 'last_modified': response.headers.get('Last-Modified')})
            total = 0
            digest, mdigest = sha256(), md5()
            with destination.open('xb') as output:
                while True:
                    chunk = response.read(2 * 1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    assert total <= LIMIT and total <= size
                    output.write(chunk)
                    digest.update(chunk)
                    mdigest.update(chunk)
            record.update({'bytes': total, 'sha256': digest.hexdigest()})
            assert total == size
            if record['content_md5']:
                assert base64.b64encode(mdigest.digest()).decode() == record['content_md5']
                record['official_content_md5_verified'] = True
            assert destination.open('rb').read(2) == b'\x1f\x8b'
            record['status'] = 'DOWNLOADED_NOT_EXECUTED'
    except Exception as error:
        record.update({'status': 'FAILED_PRESERVED', 'error': str(error)})
    print(json.dumps({'file': destination.name, 'status': record['status'], 'bytes': record.get('bytes'),
                      'error': record.get('error')}), flush=True)
    return record


def main():
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and volume['WritableVolume']
    source = json.loads((HERE / 'public-oss-captures.json').read_text())
    model = next(r for r in source['records'] if r['name'] == 'fx5-oss-model')
    assert model['status'] == 200
    assert sha256((HERE / model['file']).read_bytes()).hexdigest() == model['sha256']
    links = [l['value'] for l in model['links'] if Path(urlparse(l['value']).path).name in WANTED]
    assert len(links) == len(WANTED)
    assert all(u.startswith('https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/') for u in links)
    spec = importlib.util.spec_from_file_location('capture', HERE / 'collect_public_sources.py')
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    supplementary = [capture.capture(('sony-oss-notice', 'https://oss.sony.net/Products/Linux/notice.html')),
                     capture.capture(('fx3-oss-model', 'https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html'))]
    (HERE / 'public-oss-supplementary.json').write_text(json.dumps({'records': supplementary}, ensure_ascii=False, indent=2) + '\n')
    assert supplementary[0]['status'] == 200
    (HERE / 'gpl-archives').mkdir()
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, links))
    (HERE / 'fx5-gpl-download-receipt.json').write_text(json.dumps({
        'created_utc': datetime.now(timezone.utc).isoformat(), 'official_model_page': model['url'],
        'notice_read_before_download': supplementary[0]['url'], 'records': records,
        'source_code_only_not_device_update_package': True, 'downloaded_code_executed': False,
        'camera_or_Windows_access': False}, ensure_ascii=False, indent=2) + '\n')
    assert all(r['status'] == 'DOWNLOADED_NOT_EXECUTED' for r in records)


if __name__ == '__main__':
    main()
