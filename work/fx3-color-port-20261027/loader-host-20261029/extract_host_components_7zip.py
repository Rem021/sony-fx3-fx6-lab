#!/usr/bin/env python3
"""Use official CAB reader; compare completed prior outputs and never overwrite them."""
import hashlib,json,re,subprocess
from pathlib import Path,PureWindowsPath
HERE=Path(__file__).resolve().parent
TOKENS=['BinaryPackProperty','ProductCodeVersion','DATA23213','multiversion','PackageType','enctype','BinaryPack']
def main():
    out=HERE/'host-component-review.json';assert not out.exists()
    rec=json.loads((HERE/'msi-streams.json').read_text());cab=rec['cabinets'][0];src=HERE/cab['output']
    assert hashlib.sha256(src.read_bytes()).hexdigest()==cab['sha256']
    tool=HERE/'tools/7zz';assert hashlib.sha256(tool.read_bytes()).hexdigest()=='8e495531e1b2b8cb169ca583493922d4ab386007756418c15b95f07f642c35fb'
    selected=[n for n in cab['members'] if re.match(r'(snc|sony|rcpp4|libeay32|ssleay32)',n,re.I) and n.lower().endswith(('.exe','.dll','.svu','.pak'))]
    root=HERE/'host-components';assert root.is_dir();rows=[]
    for name in selected:
        q=PureWindowsPath(name);assert not q.is_absolute() and len(q.parts)==1
        p=subprocess.run([str(tool),'x','-so','-bsp0',str(src),name],capture_output=True,timeout=25,check=False)
        assert p.returncode==0,(name,p.stderr)
        b=p.stdout;assert len(b)<=160*1024*1024
        dest=root/name;existed=dest.exists()
        if existed:assert dest.read_bytes()==b
        else:dest.write_bytes(b)
        hits=[]
        for token in TOKENS:
            for enc in ['ascii','utf-16-le','utf-16-be']:
                needle=token.encode(enc);at=0
                while (at:=b.find(needle,at))>=0:
                    hits.append(dict(token=token,encoding=enc,file_offset=at));at+=len(needle)
        rows.append(dict(name=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),output=str(dest.relative_to(HERE)),first32=b[:32].hex(),
            matched_preserved_bsdtar_output=existed,wrapper_marker_hits=hits))
    result=dict(CAB_source=cab['output'],CAB_sha256=cab['sha256'],selected_files=len(rows),scanned_bytes=sum(r['bytes'] for r in rows),
        extractor='Official 7-Zip 26.05; task-local binary pinned by SHA',markers=TOKENS,encodings=['ascii','utf-16-le','utf-16-be'],files=rows,
        scope='Host archive data extraction and byte search only. No DLLs/native Sony instructions or MSI actions run; no discovery, device authentication, firmware signing or flashing. Marker hits are leads, not parser/format compatibility proof.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(selected_files=len(rows),bytes=result['scanned_bytes'],matching_files=[r for r in rows if r['wrapper_marker_hits']]),ensure_ascii=False))
if __name__=='__main__':main()
