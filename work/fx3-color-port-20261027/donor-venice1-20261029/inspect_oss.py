#!/usr/bin/env python3
"""Capture same-version Sony OSS and scan two kernel archives, without builds."""
import datetime,hashlib,json,re,tarfile,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
HERE=Path(__file__).resolve().parent
URL='https://oss.sony.net/Products/Linux/B2B/MPC-3610_V630.html'
TOKENS=[b'BinaryPackProperty',b'ProductCodeVersion',b'DATA23213',b'enctype="type3"',b'enctype="type4"']
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a' and 'href' in dict(attrs):self.links.append(dict(attrs)['href'])
def fetch(url,path,limit):
    assert not path.exists() and not path.with_suffix(path.suffix+'.part').exists()
    digest=hashlib.sha256();n=0;partial=path.with_suffix(path.suffix+'.part')
    with urllib.request.urlopen(url,timeout=30) as response,partial.open('xb') as out:
        assert response.status==200;headers=dict(response.headers)
        for b in iter(lambda:response.read(1048576),b''):
            n+=len(b);assert n<=limit;out.write(b);digest.update(b)
    expected=headers.get('Content-Length')
    if expected:assert n==int(expected)
    partial.rename(path);return dict(url=url,file=str(path.relative_to(HERE)),bytes=n,sha256=digest.hexdigest(),headers=headers)
def main():
    target=HERE/'OSS-kernel-review.json';assert not target.exists()
    with urllib.request.urlopen(URL,timeout=25) as response:raw=response.read(2*1048576+1);assert len(raw)<=2*1048576
    (HERE/'OSS-source-page.html').write_bytes(raw);parser=Page();parser.feed(raw.decode('utf-8'))
    links=[urllib.parse.urljoin(URL,u) for u in parser.links]
    archives=[u for u in links if u.rsplit('/',1)[-1] in ['linux-2.6.29-patched-arm.tar.gz','linux-2.6.29-patched-armv7a.tar.gz']]
    assert len(archives)==2;folder=HERE/'OSS';folder.mkdir(exist_ok=True);rows=[]
    for url in archives:
        assert urllib.parse.urlparse(url).hostname=='prodgpl.blob.core.windows.net'
        file=folder/url.rsplit('/',1)[-1];record=fetch(url,file,250*1048576)
        count=regular=text_files=bytes_scanned=0;hits=[];vendor_paths=[];makefiles=[];total=0
        with tarfile.open(file,mode='r|gz') as tar:
            for member in tar:
                count+=1;total+=member.size;assert count<200000 and total<2000*1048576
                if not member.isfile():continue
                regular+=1;name=member.name
                if re.search(r'cxd|sony|bionz|\/mach-(?:em|cel|cxd)',name,re.I):vendor_paths.append(name)
                if member.size>2*1048576 or not (re.search(r'\.(?:c|h|S|sh|py|pl|txt|mk)$',name) or name.rsplit('/',1)[-1] in ['Makefile','Kconfig']):continue
                stream=tar.extractfile(member);assert stream is not None;b=stream.read(member.size+1);assert len(b)==member.size
                bytes_scanned+=len(b);text_files+=1
                if name.count('/')<=1 and name.rsplit('/',1)[-1]=='Makefile':makefiles.append(dict(path=name,sha256=hashlib.sha256(b).hexdigest(),version_lines=[l.decode(errors='replace') for l in b.splitlines()[:12]]))
                found=[t.decode() for t in TOKENS if t in b]
                if found:hits.append(dict(path=name,sha256=hashlib.sha256(b).hexdigest(),markers=found))
        record.update(tar_members=count,regular_files=regular,text_files_scanned=text_files,text_bytes_scanned=bytes_scanned,
            exact_markers=[t.decode() for t in TOKENS],marker_hits=hits,vendor_named_paths=vendor_paths,top_makefiles=makefiles,
            scope='GPL kernel source only, no source build or execution. A negative exact-marker scan does not prove absence of any decrypter or all private code.')
        rows.append(record);print(json.dumps(dict(archive=file.name,bytes=record['bytes'],members=count,text_files=text_files,marker_hits=len(hits))),flush=True)
    target.write_text(json.dumps(dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_page=URL,
        source_page_sha256=hashlib.sha256(raw).hexdigest(),archive_links=archives,reviews=rows,
        scope='Public same-version source component search; no private firmware image is derived from GPL listings alone.'),indent=2)+'\n')
if __name__=='__main__':main()
