#!/usr/bin/env python3
"""Public official HTML evidence for a possible shared host-side package reader."""
import concurrent.futures,datetime,hashlib,json,re,urllib.request
from html.parser import HTMLParser
from pathlib import Path
HERE=Path(__file__).resolve().parent
URLS=[('snc-index','https://www.sony.jp/snc/download/'),
 ('srg-update','https://www.sony.jp/remote-camera/support/download/srg-300se/')]
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,t,attrs):
        for k,v in attrs:
            if k in ['href','src','action']:self.links.append(dict(tag=t,attribute=k,value=v))
def get(item):
    name,url=item;rec=dict(name=name,requested_url=url,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        with urllib.request.urlopen(url,timeout=20) as r:
            b=r.read(3*1024*1024+1);assert len(b)<=3*1024*1024
            rec.update(status=r.status,final_url=r.url,headers=dict(r.headers),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
        (HERE/(name+'.html')).write_bytes(b)
        s=b.decode('cp932' if re.search(rb'charset\s*=\s*["\']?shift[_-]jis',b,re.I) else 'utf-8','replace')
        p=Page();p.feed(s);rec['links']=p.links
        rec['matching_lines']=[x[:2000] for x in s.splitlines() if re.search(r'\.zip|\.exe|download\.pro|toolbox|tool_box|snctool',x,re.I)]
    except Exception as e:rec['error']=type(e).__name__+': '+str(e)
    return rec
def main():
    out=HERE/'host-source-pages.json';assert not out.exists()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:rows=list(p.map(get,URLS))
    out.write_text(json.dumps(dict(pages=rows,scope='Public HTML only. SNC/SRG is investigated solely as a possible common package-reader reference, not a substitute donor or permission to connect a device.'),indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['name','status','error','matching_lines'] if k in r} for r in rows],ensure_ascii=False))
if __name__=='__main__':main()
