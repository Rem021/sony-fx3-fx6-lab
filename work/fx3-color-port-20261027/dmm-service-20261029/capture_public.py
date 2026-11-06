#!/usr/bin/env python3
"""Bounded anonymous GET readback; inaccessible pages never imply absence."""
import concurrent.futures, datetime, hashlib, json, re, urllib.request
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
URLS = {
    'fx5-jp-support': 'https://support.sony.jp/electronics/support/products/ilme-fx5',
    'fx5-jp-downloads': 'https://support.sony.jp/electronics/support/products/ilme-fx5/downloads',
    'fx5b-jp-support': 'https://support.sony.jp/electronics/support/products/ilme-fx5b',
    'fx5-oss': 'https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html',
    'fx5-jp-product': 'https://www.sony.jp/pro-cam/products/ILME-FX5/',
    'venice2-jp-update': 'https://www.sony.jp/ls-camera/update/VENICE_2.html',
}

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.text=[]; self.links=[]; self.hide=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.hide+=1
        if tag=='a':
            href=dict(attrs).get('href')
            if href:self.links.append(href)
    def handle_endtag(self, tag):
        if tag in ('script','style'):self.hide=max(0,self.hide-1)
    def handle_data(self, text):
        if not self.hide and text.strip():self.text.append(text.strip())

def fetch(item):
    name,url=item; row=dict(name=name,url=url,requested_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; bounded public firmware research)'})
        with urllib.request.urlopen(request,timeout=20) as response:
            raw=response.read(3*1024*1024+1)
            assert len(raw)<=3*1024*1024,'Response exceeds page-only bound'
            row.update(status=response.status,final_url=response.url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        parser=Page();parser.feed(raw.decode('utf-8',errors='replace'))
        page=HERE/'public-pages'/f'{name}.html';page.write_bytes(raw)
        text='\n'.join(parser.text)+'\n'; txt=page.with_suffix('.text.txt');txt.write_text(text)
        row.update(file=str(page.relative_to(HERE)),text_file=str(txt.relative_to(HERE)),
                   text_sha256=hashlib.sha256(txt.read_bytes()).hexdigest(),
                   download_or_package_links=[u for u in parser.links if re.search(r'download|\.bin|\.dat|\.zip|\.tar|\.xz',u,re.I)],
                   relevant_lines=[line for line in parser.text if re.search(r'アップデート|ダウンロード|提供|Ver\.|2026|11月20日|ソフトウェア|Package|ILME-FX5',line)][:100])
    except Exception as error:
        row.update(error_type=type(error).__name__,error=str(error),absence_inferred=False)
    return row

def main():
    target=HERE/'public-source-readback.json';assert not target.exists()
    (HERE/'public-pages').mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,URLS.items()))
    target.write_text(json.dumps(dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),records=rows,
        scope='Anonymous bounded official page GET only. No package redownload, credentials, forms, device action or absence conclusion from errors.'),ensure_ascii=False,indent=2)+'\n')
    for row in rows:print(json.dumps({k:row.get(k) for k in ('name','status','bytes','error','relevant_lines')},ensure_ascii=False))

if __name__=='__main__':main()
