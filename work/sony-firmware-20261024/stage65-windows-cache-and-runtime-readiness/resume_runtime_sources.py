#!/usr/bin/env python3
"""Resume verified public-source transfer from a preserved prefix using ranges."""
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import hashlib
import json
import tarfile
import urllib.request
import prepare_handoff as h
import fetch_runtime_sources as original

ETAG = '0x8DDE3A03584AAA2'
SIZE, MD5 = original.FILES['linux-kernel.tar.gz']
URL = original.PREFIX + 'linux-kernel.tar.gz'


def fetch_range(out, start, end):
    path = out / ('range-%012d-%012d.bin' % (start, end))
    request = urllib.request.Request(URL, headers={
        'Range': 'bytes=%d-%d' % (start, end), 'If-Match': ETAG})
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 206 and response.headers['ETag'] == ETAG
        assert response.headers['Content-Range'] == 'bytes %d-%d/%d' % (start, end, SIZE)
        with path.open('xb') as stream:
            count = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                count += len(block)
                assert count <= end - start + 1
                stream.write(block)
    assert count == end - start + 1
    print(json.dumps({'completed_range': [start, end], 'bytes': count}), flush=True)
    return start, end, path


def describe(path, url, md5, expected_size):
    raw = path.read_bytes()
    assert len(raw) == expected_size
    assert base64.b64encode(hashlib.md5(raw).digest()).decode() == md5
    with tarfile.open(path, 'r:gz') as archive:
        members = archive.getmembers()
    selected = [x for x in members if any(k in x.name.lower() for k in
        ('thread_info.h', 'current.h', '/head.s', 'udif', 'osal', 'uipc', 'cxd90057'))]
    return {'url': url, 'path': str(path.relative_to(h.ROOT)), 'bytes': len(raw),
        'sha256': h.im.sha(raw), 'official_content_md5_verified': True,
        'archive_members': len(members),
        'relevant_members': [{'name': x.name, 'bytes': x.size, 'regular_file': x.isfile()} for x in selected],
        'source_version_label': 'ILME-FX3 Ver.7.00; not a verified 7.02 source match',
        'source_executed': False, 'archive_extracted': False}


def main():
    h.im.volume()
    folder = h.STAGE / 'work/vendor-source-reference'
    prefix = folder / 'linux-kernel.tar.gz'
    out = folder / 'range-resume-20261026'
    assert not out.exists() and not (h.STAGE / 'runtime-source-downloads.json').exists()
    out.mkdir()
    prefix_raw = prefix.read_bytes()
    start = len(prefix_raw)
    assert 0 < start < SIZE
    with urllib.request.urlopen(urllib.request.Request(URL, method='HEAD'), timeout=20) as response:
        assert response.status == 200 and int(response.headers['Content-Length']) == SIZE
        assert response.headers['Content-MD5'] == MD5 and response.headers['ETag'] == ETAG
    switch = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'old_download_session': 96544, 'old_PID': 43149, 'old_terminal_exit_code': 130,
        'why': 'Authoritatively live transfer was about 50KB/s; intentional SIGINT preserves completed prefix and resumes only remaining ranges',
        'first_PID_guard_rejected_without_signal': 'Python executable basename is Python, not python; corrected exact script argument/identity guard before SIGINT',
        'old_executed_source_sha256': h.im.sha(h.STAGE.joinpath('fetch_runtime_sources.py').read_bytes()),
        'preserved_prefix_bytes': start, 'preserved_prefix_sha256': h.im.sha(prefix_raw),
        'official_ETag_reverified': ETAG, 'prefix_redownloaded': False,
        'new_source_sha256': h.im.sha(h.STAGE.joinpath('resume_runtime_sources.py').read_bytes())}
    h.im.write_json(h.STAGE / 'runtime-download-switch.json', switch)
    ranges = []
    for at in range(start, SIZE, 8 * 1024 * 1024):
        ranges.append((at, min(SIZE - 1, at + 8 * 1024 * 1024 - 1)))
    done = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = [pool.submit(fetch_range, out, lo, hi) for lo, hi in ranges]
        for future in as_completed(jobs):
            done.append(future.result())
    merged = out / 'linux-kernel.complete.tar.gz'
    assert len(done) == len(ranges)
    with merged.open('xb') as stream:
        stream.write(prefix_raw)
        cursor = start
        for lo, hi, chunk in sorted(done):
            assert lo == cursor and chunk.stat().st_size == hi - lo + 1
            stream.write(chunk.read_bytes())
            cursor = hi + 1
        assert cursor == SIZE
    assert prefix.read_bytes() == prefix_raw
    kernel = describe(merged, URL, MD5, SIZE)
    name = 'elpspacc.tar.gz'
    count, expected_md5 = original.FILES[name]
    path = folder / name
    with urllib.request.urlopen(original.PREFIX + name, timeout=30) as response:
        raw = response.read(count + 1)
    assert len(raw) == count
    with path.open('xb') as stream:
        stream.write(raw)
    small = describe(path, original.PREFIX + name, expected_md5, count)
    h.im.write_json(h.STAGE / 'runtime-source-downloads.json', {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'schema': 'fx3-public-gpl-reference-download/2',
        'source_script_sha256': switch['new_source_sha256'],
        'official_model_page': 'https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html',
        'notice_read': 'https://oss.sony.net/Products/Linux/notice.html',
        'resume_prefix_preserved_and_all_ranges_exact': True,
        'camera_or_downloaded_code_execution': False, 'files': [kernel, small]})
    print(json.dumps({'completed': True, 'files': [{key: x[key] for key in
        ('path', 'bytes', 'sha256', 'archive_members')} for x in (kernel, small)]}), flush=True)


if __name__ == '__main__':
    main()
