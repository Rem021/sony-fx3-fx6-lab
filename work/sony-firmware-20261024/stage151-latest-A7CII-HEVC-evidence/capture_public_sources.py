#!/usr/bin/env python3
"""Fetch pinned public source as text data; never execute downloaded code."""
from pathlib import Path,PurePosixPath
from hashlib import sha256
from datetime import datetime,timezone
import io
import json
import sys
import tarfile
import urllib.request

HERE=Path(__file__).resolve().parent
SOURCES={
    'camera-tools':('YuuLuo/a7c2-camera-tools','f124d87c26110a82db54775bfa64a0843ff21410'),
    'fl23':('QAQLeonard/a7c2-fl23-research','ef7db116e13e37be91e9af20360dc9bba8d64a9b'),
    'service-preload':('YuuLuo/a7c2-service-preload','1619f938663a36d41e72302a8cfee89a0f6acd1a')}


def main():
    label=sys.argv[1];repo,commit=SOURCES[label]
    out=HERE/'work/public-sources'/label;out.mkdir(parents=True,exist_ok=False)
    url='https://codeload.github.com/'+repo+'/tar.gz/'+commit
    request=urllib.request.Request(url,headers={'User-Agent':'FX3-offline-source-review'})
    with urllib.request.urlopen(request,timeout=30) as response:
        raw=response.read(32*1024*1024+1)
    assert len(raw)<=32*1024*1024,'reference archive exceeds bounded download'
    records=[];skipped=[]
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        for member in archive:
            parts=PurePosixPath(member.name).parts
            assert len(parts)>0 and not PurePosixPath(member.name).is_absolute() and '..' not in parts
            rel=PurePosixPath(*parts[1:])
            if not member.isfile() or not rel.parts:continue
            keep=rel.suffix.lower() in {'.md','.py','.c','.h','.cc','.cpp','.json','.txt','.toml','.yml','.yaml','.ini','.sh','.command','.bat'} or rel.name in {'LICENSE','LICENSE.txt','LICENSE.md'}
            if not keep or member.size>2*1024*1024 or any(x in {'node_modules','.venv','.git'} for x in rel.parts):
                skipped.append({'path':str(rel),'bytes':member.size});continue
            data=archive.extractfile(member).read();assert len(data)==member.size
            path=out/str(rel);path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f:f.write(data)
            records.append({'path':str(rel),'bytes':len(data),'sha256':sha256(data).hexdigest()})
    report={'repo':repo,'commit':commit,'URL':url,'fetched_utc':datetime.now(timezone.utc).isoformat(),
        'archive_bytes':len(raw),'archive_sha256':sha256(raw).hexdigest(),'text_files':records,'skipped_members':skipped,
        'scope':'Public source text only; no drivers, executable artifacts, firmware or code run.',
        'downloaded_code_executed':False,'camera_or_USB_operations':0}
    with (out/'source-capture.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'label':label,'repo':repo,'commit':commit,'text_files':len(records),'skipped':len(skipped),'archive_bytes':len(raw)}))


if __name__=='__main__':main()
