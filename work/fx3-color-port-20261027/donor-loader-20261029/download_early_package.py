#!/usr/bin/env python3
"""Download only the official package URL observed in archived official HTML."""
import datetime,hashlib,json,re,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    receipt=HERE/'early-download.json';assert not receipt.exists()
    page=HERE/'us-v201-archived.html';raw=page.read_bytes()
    s=raw.decode('utf-8').replace('\\/','/')
    urls=set(re.findall(r'https://download\.pro\.sony/[^"<>\s]+\.zip',s))
    assert urls=={'https://download.pro.sony/FNGP/watcha/MPC-3610_V201.zip'},urls
    url=urls.pop();folder=HERE/'originals';folder.mkdir(exist_ok=True)
    dest=folder/'MPC-3610_V201.zip';assert not dest.exists()
    rec=dict(url=url,source_page=page.name,source_page_sha256=hashlib.sha256(raw).hexdigest(),
        archive_capture='20251030193220',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Current official server download via URL observed in archived official Sony HTML; no installer, updater, firmware program or device execution.')
    try:
        with urllib.request.urlopen(url,timeout=30) as r, dest.open('xb') as f:
            rec.update(status=r.status,final_url=r.url,headers=dict(r.headers))
            digest=hashlib.sha256();size=0;last=0
            while True:
                b=r.read(1024*1024)
                if not b:break
                size+=len(b);assert size<250*1024*1024
                digest.update(b);f.write(b)
                if size-last>=32*1024*1024:print('downloaded_bytes',size,flush=True);last=size
        if rec['headers'].get('Content-Length'):assert size==int(rec['headers']['Content-Length'])
        rec.update(bytes=size,sha256=digest.hexdigest(),complete=True,path=str(dest))
    except Exception as e:
        rec.update(error=type(e).__name__+': '+str(e),complete=False)
    receipt.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({k:rec[k] for k in ['status','bytes','sha256','complete','error'] if k in rec}),flush=True)
if __name__=='__main__':main()
