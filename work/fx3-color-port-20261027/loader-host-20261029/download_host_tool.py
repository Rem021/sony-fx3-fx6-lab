#!/usr/bin/env python3
"""Only download the host-tool ZIP URL retained in archived official Sony HTML."""
import datetime,hashlib,json,re,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    out=HERE/'host-tool-download.json';assert not out.exists()
    page=HERE/'snc-japan-archived.html';b=page.read_bytes();s=b.decode('cp932')
    urls=set(re.findall(r'https://contents\.sony\.jp/[^"<>\s]+\.zip',s))
    assert urls=={'https://contents.sony.jp/professional/snc/SNCToolboxV1.6.1.0.zip'},urls
    url=urls.pop();folder=HERE/'originals';folder.mkdir();dest=folder/url.rsplit('/',1)[1]
    rec=dict(requested_url=url,source_page=page.name,source_page_sha256=hashlib.sha256(b).hexdigest(),
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),path=str(dest.relative_to(HERE)),
        scope='Download for static package-reader research only; no installation, Windows execution, real network-camera discovery or device operation.')
    try:
        with urllib.request.urlopen(url,timeout=30) as r,dest.open('xb') as f:
            rec.update(status=r.status,final_url=r.url,headers=dict(r.headers));h=hashlib.sha256();n=0
            while True:
                data=r.read(1024*1024)
                if not data:break
                n+=len(data);assert n<=160*1024*1024;h.update(data);f.write(data)
        if rec['headers'].get('Content-Length'):assert n==int(rec['headers']['Content-Length'])
        rec.update(bytes=n,sha256=h.hexdigest(),complete=True)
    except Exception as e:rec.update(error=type(e).__name__+': '+str(e),complete=False)
    out.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({k:rec[k] for k in ['status','bytes','sha256','complete','error'] if k in rec}))
if __name__=='__main__':main()
