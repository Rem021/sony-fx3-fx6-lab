#!/usr/bin/env python3
"""Extract selected CAB files to stdout, preserve originals, search exact wrapper markers."""
import hashlib,json,re,subprocess
from pathlib import Path,PureWindowsPath
HERE=Path(__file__).resolve().parent
TOKENS=['BinaryPackProperty','ProductCodeVersion','DATA23213','multiversion','PackageType','enctype','BinaryPack']
def main():
    out=HERE/'host-component-review.json';assert not out.exists()
    rec=json.loads((HERE/'msi-streams.json').read_text());assert len(rec['cabinets'])==1
    cab=rec['cabinets'][0];src=HERE/cab['output'];assert hashlib.sha256(src.read_bytes()).hexdigest()==cab['sha256']
    selected=[n for n in cab['members'] if re.match(r'(snc|sony|rcpp4|libeay32|ssleay32)',n,re.I) and n.lower().endswith(('.exe','.dll','.svu','.pak'))]
    root=HERE/'host-components';root.mkdir();rows=[]
    for name in selected:
        q=PureWindowsPath(name);assert not q.is_absolute() and len(q.parts)==1
        p=subprocess.run(['/usr/bin/bsdtar','-xOf',str(src),name],capture_output=True,timeout=25,check=False)
        assert p.returncode==0,(name,p.stderr)
        b=p.stdout;assert len(b)<=160*1024*1024
        dest=root/name;assert not dest.exists();dest.write_bytes(b)
        hits=[]
        for token in TOKENS:
            for enc in ['ascii','utf-16-le','utf-16-be']:
                needle=token.encode(enc);at=0
                while (at:=b.find(needle,at))>=0:
                    hits.append(dict(token=token,encoding=enc,file_offset=at));at+=len(needle)
        rows.append(dict(name=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),output=str(dest.relative_to(HERE)),first32=b[:32].hex(),wrapper_marker_hits=hits))
    result=dict(CAB_source=cab['output'],CAB_sha256=cab['sha256'],selected_files=len(rows),scanned_bytes=sum(r['bytes'] for r in rows),
        markers=TOKENS,encodings=['ascii','utf-16-le','utf-16-be'],files=rows,
        scope='Only host archive extraction and byte search. No DLL imports, native instructions, installers/updaters, discovery, authentication, network camera or FX3 action. A marker hit is a lead, not a recovered parser or firmware compatibility.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(selected_files=len(rows),bytes=result['scanned_bytes'],matching_files=[r for r in rows if r['wrapper_marker_hits']]),ensure_ascii=False))
if __name__=='__main__':main()
