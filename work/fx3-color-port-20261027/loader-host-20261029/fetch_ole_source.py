#!/usr/bin/env python3
"""Fetch only pinned maintainer source for task-local read-only compound-file parsing."""
import concurrent.futures,datetime,hashlib,json,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
COMMIT='ae8e110e90965f2648052b29f1b3da2c39465001'
def main():
    folder=HERE/'reference/olefile';folder.mkdir(exist_ok=True);receipt=folder/'dependency-receipt.json';assert not receipt.exists()
    def get(name):
        url=f'https://raw.githubusercontent.com/decalage2/olefile/{COMMIT}/{name}'
        with urllib.request.urlopen(url,timeout=20) as r:b=r.read(1024*1024+1);assert len(b)<=1024*1024;status=r.status
        p=folder/name;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        return dict(url=url,path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),status=status)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(get,['olefile/__init__.py','olefile/olefile.py','LICENSE.txt']))
    rec=dict(package='olefile',version='0.47',repository='https://github.com/decalage2/olefile',tag='v0.47',commit=COMMIT,
        files=rows,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Task-local data-reader source only; no pip/venv/system install, setup.py, build scripts or vendor code execution.')
    receipt.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(dict(package='olefile',version='0.47',commit=COMMIT,files=len(rows))))
if __name__=='__main__':main()
