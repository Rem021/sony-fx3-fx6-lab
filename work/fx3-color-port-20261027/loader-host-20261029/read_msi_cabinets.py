#!/usr/bin/env python3
"""Read-only MSI compound-file streams, export cabinets without MSI custom actions."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE/'reference/olefile'))
import olefile
def main():
    out=HERE/'msi-streams.json';assert not out.exists()
    rec=json.loads((HERE/'setup-stream-unpack.json').read_text())
    msirec=next(r for r in rec['members'] if r['name']=='SNC toolbox.msi');src=HERE/msirec['output']
    raw=src.read_bytes();assert len(raw)==msirec['bytes'] and hashlib.sha256(raw).hexdigest()==msirec['sha256']
    folder=HERE/'msi-cabinets';folder.mkdir();rows=[];cabinets=[]
    with olefile.OleFileIO(str(src),write_mode=False,raise_defects=olefile.DEFECT_INCORRECT) as ole:
        for index,name in enumerate(ole.listdir(streams=True,storages=False)):
            size=ole.get_size(name);assert size<=160*1024*1024
            data=ole.openstream(name).read();assert len(data)==size
            row=dict(index=index,name=name,bytes=size,sha256=hashlib.sha256(data).hexdigest(),first16=data[:16].hex())
            rows.append(row)
            if data[:4]==b'MSCF':
                dest=folder/f'cabinet-{index:03d}.cab';dest.write_bytes(data)
                p=subprocess.run(['/usr/bin/bsdtar','-tf',str(dest)],capture_output=True,timeout=20,check=False)
                cabinet=dict(**row,output=str(dest.relative_to(HERE)),list_exit=p.returncode,
                    list_stderr=p.stderr.decode('utf-8','replace'),members=p.stdout.decode('utf-8','strict').splitlines())
                cabinets.append(cabinet)
        defects=[(str(k),str(v)) for k,v in ole.parsing_issues]
    out.write_text(json.dumps(dict(MSI_source=str(src.relative_to(HERE)),MSI_sha256=msirec['sha256'],olefile_version=olefile.__version__,
        streams=rows,cabinets=cabinets,parse_issues=defects,
        scope='Read-only CFB and CAB extraction/listing. No MSI engine, actions, registry changes, native vendor programs or devices.'),indent=2)+'\n')
    print(json.dumps(dict(streams=len(rows),parse_issues=defects,cabinets=[{k:r[k] for k in ['index','bytes','list_exit','members','list_stderr']} for r in cabinets]),ensure_ascii=False))
if __name__=='__main__':main()
