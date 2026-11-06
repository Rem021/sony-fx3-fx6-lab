#!/usr/bin/env python3
"""Download only the ZIP URL observed in Sony's VENICE page."""
import datetime,hashlib,json,os,urllib.parse,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
LIMIT=350*1024*1024
def main():
    manifest=HERE/'download-receipt.json';assert not manifest.exists()
    page=json.loads((HERE/'official-source-page.json').read_text())
    urls=[u for u in page['embedded_download_URLs'] if u.endswith('/MPC-3610_V630.zip')]
    assert len(set(urls))==1;url=urls[0]
    assert urllib.parse.urlparse(url).hostname=='download.pro.sony'
    assert os.statvfs(HERE).f_bavail*os.statvfs(HERE).f_frsize>1024*1024*1024
    folder=HERE/'originals';folder.mkdir(exist_ok=True);output=folder/'MPC-3610_V630.zip';partial=output.with_suffix('.zip.part')
    assert not output.exists() and not partial.exists();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    digest=hashlib.sha256();total=0
    with urllib.request.urlopen(url,timeout=30) as response:
        assert response.status==200;headers=dict(response.headers);expected=response.headers.get('Content-Length')
        if expected:assert int(expected)<=LIMIT
        with partial.open('xb') as file:
            while block:=response.read(1024*1024):
                total+=len(block);assert total<=LIMIT;file.write(block);digest.update(block)
            file.flush();os.fsync(file.fileno())
    if expected:assert total==int(expected)
    assert total>1024;partial.rename(output)
    record=dict(source_page='https://www.sony.jp/ls-camera/update/VENICE.html',url=url,
        source_URL_observed_in_official_HTML=True,output=str(output.relative_to(HERE)),bytes=total,sha256=digest.hexdigest(),
        headers=headers,started_utc=started,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Official public package downloaded to local research directory; no install script, firmware updater, device or flash operation.')
    manifest.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
if __name__=='__main__':main()
