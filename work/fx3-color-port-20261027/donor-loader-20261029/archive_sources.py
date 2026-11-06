#!/usr/bin/env python3
"""Query public Wayback metadata and read public archived Sony HTML only."""
import concurrent.futures,datetime,hashlib,json,re,urllib.parse,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
URLS=[
 ('us-v201','https://www.sony.com/electronics/support/professional-cameras-digital-cinema-cameras/mpc-3610/software/mpueus00000921'),
 ('us-v210','https://www.sony.com/electronics/support/software/mpueus00000952'),
]
def metadata(item):
    name,target=item
    url='https://archive.org/wayback/available?'+urllib.parse.urlencode(dict(url=target,timestamp='20181107'))
    out=dict(name=name,target_url=target,query_url=url,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        with urllib.request.urlopen(url,timeout=20) as r:
            b=r.read(128*1024);out.update(status=r.status,headers=dict(r.headers),result=json.loads(b))
        (HERE/(name+'-archive-metadata.raw.json')).write_bytes(b)
    except Exception as e:out['error']=type(e).__name__+': '+str(e)
    return out
def capture(name,url):
    out=dict(name=name,requested_url=url,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        with urllib.request.urlopen(url,timeout=20) as r:
            b=r.read(3*1024*1024+1);assert len(b)<=3*1024*1024
            out.update(status=r.status,final_url=r.url,headers=dict(r.headers),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
        (HERE/(name+'-archived.html')).write_bytes(b)
        s=b.decode('cp932' if b'shift_jis' in b.lower() else 'utf-8','replace')
        out['matching_lines']=[x for x in s.splitlines() if re.search(r'download\.pro|\.zip|V201|V210|\.bin',x,re.I)]
    except Exception as e:out['error']=type(e).__name__+': '+str(e)
    return out
def main():
    out=HERE/'archive-sources.json';assert not out.exists()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        fs=[pool.submit(metadata,x) for x in URLS]
        known=pool.submit(capture,'jp-20200930','https://web.archive.org/web/20200930025941id_/https://www.sony.jp/ls-camera/update/VENICE.html')
        ms=[f.result() for f in fs];cs=[known.result()]
    for m in ms:
        closest=m.get('result',{}).get('archived_snapshots',{}).get('closest',{})
        if closest.get('available') and closest.get('status')=='200':
            u=closest['url'];assert u.startswith(('http://web.archive.org/','https://web.archive.org/'))
            cs.append(capture(m['name'],u.replace('http://','https://',1)))
    out.write_text(json.dumps(dict(scope='Archived public Sony page copies, not proof of current package availability; no programs/device actions.',metadata=ms,captures=cs),indent=2)+'\n')
    print(json.dumps(dict(metadata=[{k:r[k] for k in ['name','status','error'] if k in r} for r in ms],
        captures=[{k:r[k] for k in ['name','status','bytes','error'] if k in r} for r in cs]),ensure_ascii=False))
if __name__=='__main__':main()
