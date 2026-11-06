#!/usr/bin/env python3
"""Extract EXE bytes from original ZIP, inspect format only; never run installer."""
import hashlib,json,re,struct,subprocess,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def positions(b,t):
    a=[];o=0
    while (o:=b.find(t,o))>=0:a.append(o);o+=len(t)
    return a
def main():
    out=HERE/'host-installer-structure.json';assert not out.exists()
    src=HERE/'originals/SNCToolboxV1.6.1.0.zip';b=src.read_bytes()
    assert hashlib.sha256(b).hexdigest()=='ec18e66965423093fab8edf535446524b8b6df49a51300e2a0382fdd3f867b2e'
    with zipfile.ZipFile(src) as z:raw=z.read('SncToolbox_Setup.exe')
    dest=HERE/'originals/SncToolbox_Setup.exe';assert not dest.exists();dest.write_bytes(raw)
    assert raw[:2]==b'MZ';pe=struct.unpack_from('<I',raw,0x3c)[0];assert raw[pe:pe+4]==b'PE\0\0'
    p=subprocess.run(['/usr/bin/bsdtar','-tf',str(dest)],capture_output=True,timeout=20,check=False)
    matches=[]
    for m in re.finditer(rb'[ -~]{8,}',raw):
        s=m.group().decode('ascii')
        if re.search(r'InstallShield|Wise Installer|Nullsoft|Inno Setup|\.msi\b|\.cab\b|MSCF|ISSetup|7-Zip|7z Setup',s,re.I):
            matches.append(dict(offset=m.start(),text=s[:300]))
    rec=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),PE_offset=pe,machine=hex(struct.unpack_from('<H',raw,pe+4)[0]),
        archive_list_exit=p.returncode,archive_list_stdout=p.stdout.decode('utf-8','replace')[:20000],archive_list_stderr=p.stderr.decode('utf-8','replace')[:3000],
        format_magic_offsets={n:positions(raw,t) for n,t in [('CAB_MSCF',b'MSCF'),('7z',b'7z\xbc\xaf\x27\x1c'),('ZIP',b'PK\3\4'),('NSIS',b'NullsoftInst'),('OLE',bytes.fromhex('d0cf11e0a1b11ae1')),('InstallShield_CAB',b'ISc(')]},
        strings=matches,scope='Host data parsing only; installer/updater not run, imported or installed, and no network/device discovery.')
    out.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,ensure_ascii=False))
if __name__=='__main__':main()
