#!/usr/bin/env python3
"""Task-local 7-Zip from link observed on official download page; no system install."""
import datetime,hashlib,io,json,os,subprocess,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
URL='https://github.com/ip7z/7zip/releases/download/26.05/7z2605-mac.tar.xz'
def main():
    out=HERE/'archive-tool-receipt.json';assert not out.exists();folder=HERE/'tools';folder.mkdir()
    archive=folder/'7z2605-mac.tar.xz';assert not archive.exists()
    p=subprocess.run(['curl','--fail','--location','--silent','--show-error','--connect-timeout','10','--max-time','30','--output',str(archive),URL],capture_output=True,timeout=35)
    rec=dict(source_page='https://www.7-zip.org/download.html',download_url=URL,curl_exit=p.returncode,curl_stderr=p.stderr.decode(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if p.returncode==0:
        b=archive.read_bytes();assert len(b)<32*1024*1024;rec.update(archive_bytes=len(b),archive_sha256=hashlib.sha256(b).hexdigest())
        files=[]
        with tarfile.open(fileobj=io.BytesIO(b),mode='r:xz') as t:
            for m in t:
                if not m.isfile():continue
                if Path(m.name).name in ['7zz','License.txt','readme.txt']:
                    raw=t.extractfile(m).read();dest=folder/Path(m.name).name;assert not dest.exists();dest.write_bytes(raw)
                    if dest.name=='7zz':os.chmod(dest,0o755)
                    files.append(dict(member=m.name,output=str(dest.relative_to(HERE)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        assert any(r['output']=='tools/7zz' for r in files);rec['files']=files
        rec['scope']='Official archive utility, local task path only. No Sony installer/updater or device run; no system installation or existing permissions changed.'
    out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
if __name__=='__main__':main()
