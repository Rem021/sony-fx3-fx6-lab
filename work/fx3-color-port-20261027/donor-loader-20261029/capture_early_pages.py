#!/usr/bin/env python3
"""Read observed official Sony support URLs; do not execute downloaded material."""
import concurrent.futures, datetime, hashlib, json, re, urllib.request, urllib.error
from html.parser import HTMLParser
from pathlib import Path
HERE=Path(__file__).resolve().parent
URLS=[
 ('sg-v210','https://www.sony.com.sg/electronics/support/software/mpenhk00000740'),
 ('asia-v201','https://www.sony-asia.com/electronics/support/professional-cameras-digital-cinema-cameras/mpc-3610/software/mpenhk00000708'),
 ('vn-v201','https://www.sony.com.vn/electronics/support/software/mpenhk00000708'),
]
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.text=[];self.hide=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ['script','style']:self.hide+=1
        for k,v in a.items():
            if k in ['href','src','action','data-url','data-href','data-download-url']:self.links.append(dict(tag=tag,attribute=k,value=v))
    def handle_endtag(self,tag):
        if tag in ['script','style']:self.hide=max(0,self.hide-1)
    def handle_data(self,s):
        if not self.hide and s.strip():self.text.append(s.strip())
def get(item):
    name,url=item
    rec=dict(name=name,url=url,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=18) as r:
            b=r.read(4*1024*1024+1);assert len(b)<=4*1024*1024
            rec.update(status=r.status,final_url=r.url,headers=dict(r.headers),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
        (HERE/(name+'.html')).write_bytes(b)
        s=b.decode('utf-8','replace');p=Page();p.feed(s)
        (HERE/(name+'.text.txt')).write_text('\n'.join(p.text)+'\n')
        rec.update(links=p.links,download_lines=[x for x in s.splitlines() if re.search(r'V210|V201|downloadUrl|downloadURL|download\.pro|data-download|\.zip',x,re.I)])
    except Exception as e:
        rec['error']=type(e).__name__+': '+str(e)
        if isinstance(e,urllib.error.HTTPError):
            rec['status']=e.code
    return rec
def main():
    out=HERE/'early-pages.json';assert not out.exists()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:recs=list(pool.map(get,URLS))
    out.write_text(json.dumps(dict(scope='Public anonymous HTML GET; failures are access gaps, not package absence.',pages=recs),indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['name','status','bytes','error','download_lines'] if k in r} for r in recs],ensure_ascii=False))
if __name__=='__main__':main()
