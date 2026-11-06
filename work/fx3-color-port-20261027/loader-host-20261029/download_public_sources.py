#!/usr/bin/env python3
"""Download two observed GPL source RPMs; list archives without install/build/script execution."""
import concurrent.futures,datetime,hashlib,json,re,subprocess,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
def download(url):
    name=url.rsplit('/',1)[1];dest=HERE/'OSS'/name;assert not dest.exists()
    rec=dict(url=url,path=str(dest.relative_to(HERE)),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        with urllib.request.urlopen(url,timeout=25) as r:
            b=r.read(32*1024*1024+1);assert len(b)<=32*1024*1024
            rec.update(status=r.status,final_url=r.url,headers=dict(r.headers),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
        assert b[:4]==b'\xed\xab\xee\xdb';dest.write_bytes(b)
        p=subprocess.run(['/usr/bin/bsdtar','-tf',str(dest)],capture_output=True,timeout=20,check=False)
        rec.update(list_exit=p.returncode,list_stderr=p.stderr.decode('utf-8','replace'),members=p.stdout.decode('utf-8','strict').splitlines())
    except Exception as e:rec['error']=type(e).__name__+': '+str(e)
    return rec
def main():
    out=HERE/'public-source-rpms.json';assert not out.exists();(HERE/'OSS').mkdir()
    src=HERE.parent/'donor-venice1-20261029/OSS-source-page.html';b=src.read_bytes()
    urls=[u for u in re.findall(r'href="([^"]+)"',b.decode()) if re.search(r'dev-(busybox|rpm)-',u)]
    assert len(urls)==2 and all(u.startswith('https://prodgpl.blob.core.windows.net/') for u in urls)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(download,urls))
    out.write_text(json.dumps(dict(source_page=str(src),source_page_sha256=hashlib.sha256(b).hexdigest(),packages=rows,
        scope='Host archive listing only. No RPM installation, scriptlet, compiler, vendor program or device action.'),indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['path','status','bytes','list_exit','members','error'] if k in r} for r in rows],ensure_ascii=False))
if __name__=='__main__':main()
