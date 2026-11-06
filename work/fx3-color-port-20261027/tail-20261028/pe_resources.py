#!/usr/bin/env python3
"""Bounded PE resource listing; never load or execute the original installer."""
from pathlib import Path
from hashlib import file_digest,sha256
import json,struct,mmap

HERE=Path(__file__).resolve().parent


def main():
    source=HERE/'official-interim/01_Update_ILMEFX3V20x.exe'
    receipt=json.loads((source.parent/'member-receipt.json').read_bytes())
    with source.open('rb') as f:assert file_digest(f,'sha256').hexdigest()==receipt['exe_sha256']
    with source.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as b:
        def read(o,n):
            assert 0<=o<=len(b) and 0<=n<=len(b)-o,(o,n,len(b))
            return b[o:o+n]
        assert read(0,2)==b'MZ';pe=struct.unpack('<I',read(0x3c,4))[0];assert read(pe,4)==b'PE\0\0'
        coff=struct.unpack('<HHIIIHH',read(pe+4,20));opt=pe+24;assert struct.unpack('<H',read(opt,2))[0]==0x10b
        num=coff[1];section_at=opt+coff[5];sections=[]
        for i in range(num):
            raw=read(section_at+i*40,40);name=raw[:8].rstrip(b'\0').decode('ascii','replace')
            vs,va,size,off=struct.unpack_from('<4I',raw,8)
            sections.append(dict(name=name,virtual_size=vs,rva=va,file_bytes=size,file_offset=off))
        def physical(rva,n):
            s=next(s for s in sections if s['rva']<=rva and rva+n<=s['rva']+s['file_bytes'])
            return s['file_offset']+rva-s['rva']
        root,size=struct.unpack('<II',read(opt+96+2*8,8));base=physical(root,size)
        rows=[]
        def relative(o,n):assert 0<=o and o+n<=size;return read(base+o,n)
        def walk(o,path=(),anc=()):
            assert o not in anc and len(path)<=5
            h=struct.unpack('<IIHHHH',relative(o,16));count=h[4]+h[5]
            assert count<10000
            for i in range(count):
                a,z=struct.unpack('<II',relative(o+16+i*8,8))
                if a&0x80000000:
                    p=a&0x7fffffff;n=struct.unpack('<H',relative(p,2))[0]
                    label=relative(p+2,n*2).decode('utf-16-le')
                else:label=a
                if z&0x80000000:walk(z&0x7fffffff,path+(label,),anc+(o,))
                else:
                    rva,length,cp,reserved=struct.unpack('<4I',relative(z,16));off=physical(rva,length)
                    rows.append(dict(path=list(path+(label,)),rva=hex(rva),file_offset=off,bytes=length,
                                     codepage=cp,first32_hex=read(off,min(32,length)).hex()))
        walk(0)
        end=max(s['file_offset']+s['file_bytes'] for s in sections)
        result=dict(status='PASS_ORIGINAL_INSTALLER_PE_RESOURCE_INDEX',source=str(source.relative_to(HERE)),source_sha256=receipt['exe_sha256'],
                    resource_root_rva=hex(root),resource_bytes=size,sections=sections,resources=rows,
                    overlay_file_offset=end,overlay_bytes=len(b)-end,
                    overlay_first32=read(end,min(32,len(b)-end)).hex(),
                    scope='Original PE resource directory and raw ranges only. Magic bytes are candidate identities; no installer or extracted firmware is executed.')
    (HERE/'pe-resource-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'resources',len(rows),'overlay bytes',result['overlay_bytes'])
    for r in rows:
        if r['bytes']>100000:print(r)


if __name__=='__main__':main()
