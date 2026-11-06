#!/usr/bin/env python3
"""Fetch a pinned pure-Python OLE reader wheel from PyPI into task-local reference."""
import datetime,hashlib,io,json,urllib.request,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    folder=HERE/'reference/olefile';folder.mkdir();receipt=folder/'dependency-receipt.json'
    url='https://pypi.org/pypi/olefile/0.47/json'
    with urllib.request.urlopen(url,timeout=20) as r:meta=json.load(r)
    wheels=[r for r in meta['urls'] if r['filename'].endswith('py2.py3-none-any.whl')];assert len(wheels)==1
    w=wheels[0]
    with urllib.request.urlopen(w['url'],timeout=20) as r:b=r.read(1024*1024+1);assert len(b)<=1024*1024
    assert hashlib.sha256(b).hexdigest()==w['digests']['sha256']
    wheel=folder/w['filename'];wheel.write_bytes(b);files=[]
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.startswith('olefile/') and name.endswith('.py') or name.endswith(('LICENSE.txt','LICENSE')):
                dest=folder/name;assert dest.resolve().is_relative_to(folder.resolve());dest.parent.mkdir(parents=True,exist_ok=True)
                data=z.read(name);dest.write_bytes(data);files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    receipt.write_text(json.dumps(dict(package='olefile',version='0.47',metadata_url=url,wheel_url=w['url'],wheel_filename=w['filename'],
        wheel_sha256=w['digests']['sha256'],files=files,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Task-local pure Python data-reader dependency only. No system/venv install, build hooks or vendor code execution.'),indent=2)+'\n')
    print(json.dumps(dict(package='olefile',version='0.47',wheel_sha256=w['digests']['sha256'],files=len(files))))
if __name__=='__main__':main()
