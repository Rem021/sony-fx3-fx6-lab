#!/usr/bin/env python3
"""Public historical Sony host-tool HTML; archived availability is not current availability."""
import concurrent.futures,datetime,hashlib,json,re,urllib.parse,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
TARGETS=[('snc-japan','https://www.sony.jp/snc/download/service/snc_toolbox.html'),
 ('snc-global','https://www.sony.net/Products/CameraSystem/CA/Utility_Software/')]
def get(item):
    name,target=item;url='https://archive.org/wayback/available?'+urllib.parse.urlencode(dict(url=target,timestamp='20190720'))
    rec=dict(name=name,target_url=target,metadata_url=url,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        with urllib.request.urlopen(url,timeout=20) as r:
            b=r.read(256*1024);j=json.loads(b);rec.update(metadata_status=r.status,metadata=j)
        (HERE/(name+'-archive-metadata.raw.json')).write_bytes(b)
        c=j.get('archived_snapshots',{}).get('closest',{})
        if c.get('available') and c.get('status')=='200':
            u=c['url'].replace('http://','https://',1);assert u.startswith('https://web.archive.org/web/')
            rec['capture_requested_url']=u
            with urllib.request.urlopen(u,timeout=20) as r:
                b=r.read(3*1024*1024+1);assert len(b)<=3*1024*1024
                rec.update(capture_status=r.status,capture_final_url=r.url,capture_headers=dict(r.headers),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
            (HERE/(name+'-archived.html')).write_bytes(b)
            s=b.decode('cp932' if re.search(rb'shift[_-]jis',b,re.I) else 'utf-8','replace')
            rec['matching_lines']=[x[:2500] for x in s.splitlines() if re.search(r'\.zip|\.exe|download\.pro|action=',x,re.I)]
    except Exception as e:rec['error']=type(e).__name__+': '+str(e)
    return rec
def main():
    out=HERE/'host-archive-pages.json';assert not out.exists()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:rows=list(p.map(get,TARGETS))
    out.write_text(json.dumps(dict(pages=rows),indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['name','metadata_status','capture_status','bytes','error','matching_lines'] if k in r} for r in rows],ensure_ascii=False))
if __name__=='__main__':main()
