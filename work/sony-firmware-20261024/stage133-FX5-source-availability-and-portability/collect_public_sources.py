#!/usr/bin/env python3
"""Capture anonymous public Sony pages as evidence; never opens camera devices."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import json
import plistlib
import subprocess
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
SOURCES = {
    'fx5-jp-support': 'https://support.sony.jp/electronics/support/products/ilme-fx5',
    'fx5-us-downloads': 'https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads',
    'fx5-sg-downloads': 'https://www.sony.com.sg/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads',
    'fx5-cn-product': 'https://www.sonystyle.com.cn/products/professional-video-cameras/ilme_fx5/ilme_fx5_feature.html',
    'fx5-jp-spec': 'https://www.sony.jp/pro-cam/products/ILME-FX5/spec.html',
    'fx5-jp-announcement': 'https://www.sony.jp/CorporateCruise/Press/202607/26-0722B/',
    'fx3-jp-spec': 'https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html',
    'fx5-guide-index': 'https://helpguide.sony.net/ilc/2630/v1/en/index.html',
    'fx5-license': 'https://helpguide.sony.net/ilc/2630/v1/en/contents/license.html',
    'sony-oss-root': 'https://oss.sony.net/Products/Linux/',
}
MAX_BYTES = 8 * 1024 * 1024


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ('href', 'src'):
            if key in a:
                self.links.append({'tag': tag, 'attribute': key, 'value': a[key]})

    def handle_data(self, text):
        if text.strip():
            self.text.append(text.strip())


def capture(item):
    name, url = item
    record = {'name': name, 'url': url, 'requested_utc': datetime.now(timezone.utc).isoformat()}
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; OfflineFirmwareResearch/1.0)'})
    try:
        try:
            response = urllib.request.urlopen(request, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(MAX_BYTES + 1)
            assert len(data) <= MAX_BYTES, 'Public page exceeded capture limit'
            record.update({'status': response.status, 'final_url': response.geturl(),
                           'content_type': response.headers.get('Content-Type', '')})
        destination = HERE / 'public-pages' / (name + '.html')
        destination.write_bytes(data)
        parser = Links()
        parser.feed(data.decode('utf-8', errors='replace'))
        record.update({'file': destination.relative_to(HERE).as_posix(), 'bytes': len(data),
                       'sha256': sha256(data).hexdigest(), 'links': parser.links})
        (HERE / 'public-pages' / (name + '.text.txt')).write_text('\n'.join(parser.text) + '\n')
    except Exception as error:
        record['error'] = str(error)
    return record


def main():
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and volume['WritableVolume']
    assert (HERE / 'preflight-verification.json').is_file()
    (HERE / 'public-pages').mkdir()
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(capture, SOURCES.items()))
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'public_anonymous_HTTP_only': True,
              'no_forms_credentials_or_camera_interfaces': True, 'records': records,
              'absence_claim_scope': 'Only fetched official pages; HTTP failures are not evidence of absence.'}
    (HERE / 'public-source-captures.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps([{'name': r['name'], 'status': r.get('status'), 'bytes': r.get('bytes'),
                       'error': r.get('error')} for r in records], ensure_ascii=False))


if __name__ == '__main__':
    main()
