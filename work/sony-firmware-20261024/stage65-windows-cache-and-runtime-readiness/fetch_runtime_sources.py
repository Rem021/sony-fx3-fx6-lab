#!/usr/bin/env python3
"""Read-only public GPL archives; list names without extracting or executing."""
import base64
import datetime
import hashlib
import json
import tarfile
import urllib.request
import prepare_handoff as h

FILES = {
    'linux-kernel.tar.gz': (109987145, 'YDFQucyXKvK/A5CHlRB/LA=='),
    'elpspacc.tar.gz': (43358, '9aHG28OfRwq9OzaVRo9gLw=='),
}
PREFIX = 'https://prodgpl.blob.core.windows.net/download/B2B/ILME-FX3_Ver.7.00/'


def main():
    h.im.volume()
    out = h.STAGE / 'work/vendor-source-reference'
    assert not out.exists()
    out.mkdir(parents=True)
    rows = []
    for name, (size, md5) in FILES.items():
        url = PREFIX + name
        path = out / name
        with urllib.request.urlopen(url, timeout=30) as response:
            headers = dict(response.headers.items())
            assert response.status == 200 and int(response.headers['Content-Length']) == size
            with path.open('xb') as dest:
                total = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    assert total <= size
                    dest.write(block)
        raw = path.read_bytes()
        assert len(raw) == size
        assert base64.b64encode(hashlib.md5(raw).digest()).decode() == md5
        with tarfile.open(path, 'r:gz') as archive:
            members = archive.getmembers()
            selected = [x for x in members if any(k in x.name.lower() for k in
                ('thread_info.h', 'current.h', '/head.s', 'udif', 'osal', 'uipc', 'cxd90057', 'config'))]
            row = {
                'url': url, 'headers': headers, 'bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest(), 'official_content_md5_verified': True,
                'archive_members': len(members),
                'first_twenty_names': [x.name for x in members[:20]],
                'relevant_members': [{'name': x.name, 'bytes': x.size, 'regular_file': x.isfile()} for x in selected],
                'source_version_label': 'ILME-FX3 Ver.7.00, not a verified 7.02 source match',
                'source_code_or_installer_executed': False, 'archive_extracted': False,
            }
            rows.append(row)
        print(json.dumps({key: row[key] for key in ('url', 'bytes', 'sha256', 'archive_members', 'first_twenty_names')}), flush=True)
    h.im.write_json(h.STAGE / 'runtime-source-downloads.json', {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_script_sha256': h.im.sha(__file__ and h.STAGE.joinpath('fetch_runtime_sources.py').read_bytes()),
        'official_model_page': 'https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html',
        'notice_read': 'https://oss.sony.net/Products/Linux/notice.html',
        'purpose': 'Review vendor current-context, driver and allocator dependencies; no build or load',
        'files': rows,
    })


if __name__ == '__main__':
    main()
