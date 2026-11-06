#!/usr/bin/env python3
"""Capture official first-generation VENICE donor page; no device/program run."""
import datetime,hashlib,json,re,urllib.request
from html.parser import HTMLParser
from pathlib import Path
HERE=Path(__file__).resolve().parent
URL='https://www.sony.jp/ls-camera/update/VENICE.html'
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.text=[];self.hide=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        for k in ['href','src','onclick','data-url']:
            if k in attrs:self.links.append(dict(tag=tag,attribute=k,value=attrs[k]))
        if tag in ['script','style']:self.hide+=1
    def handle_endtag(self,tag):
        if tag in ['script','style']:self.hide=max(0,self.hide-1)
    def handle_data(self,data):
        if not self.hide and data.strip():self.text.append(data.strip())
def main():
    out=HERE/'official-source-page.json';assert not out.exists()
    with urllib.request.urlopen(URL,timeout=25) as response:
        raw=response.read(2*1024*1024+1);assert len(raw)<=2*1024*1024
        metadata=dict(status=response.status,final_url=response.url,headers=dict(response.headers))
    charset='cp932' if re.search(rb'charset\s*=\s*["\']?shift[_-]jis',raw,re.I) else 'utf-8'
    text=raw.decode(charset);p=Page();p.feed(text)
    (HERE/'official-source-page.html').write_bytes(raw)
    (HERE/'official-source-page.text.txt').write_text('\n'.join(p.text)+'\n')
    links=[x for x in p.links if re.search(r'download|\.zip|\.bin|\.js',x['value'],re.I)]
    URLs=re.findall(r'https?://[^\s"\'<>]+',text)
    out.write_text(json.dumps(dict(requested_url=URL,checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **metadata,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),decoded_charset=charset,links=links,
        embedded_download_URLs=[u for u in URLs if re.search(r'\.zip|download\.pro',u,re.I)],
        scope='Anonymous official HTML GET only; no software installed or executed, no device action.'),indent=2)+'\n')
    print(json.dumps(dict(relevant_links=links,matching_lines=[line for line in text.splitlines() if re.search(r'\.zip|\.bin|download\.pro|download_file',line,re.I)]),ensure_ascii=False))
if __name__=='__main__':main()
