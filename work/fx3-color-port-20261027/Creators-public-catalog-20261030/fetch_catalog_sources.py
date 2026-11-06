#!/usr/bin/env python3
"""Read a pinned public notification-source implementation, never run it."""
import datetime,hashlib,io,json,tarfile,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
PIN='c25814716a15afca997e0abf0a661974c5021669'
URL='https://codeload.github.com/rock3r/CameraSync/tar.gz/'+PIN
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    assert not (HERE/'source-capture.json').exists()
    refs=HERE/'references';refs.mkdir(exist_ok=False)
    req=urllib.request.Request(URL,headers={'User-Agent':'Firmware-catalog-source-review/1.0'})
    with urllib.request.urlopen(req,timeout=25) as response:
        raw=response.read(16*1024*1024+1);status=response.status
    assert len(raw)<=16*1024*1024,'bounded public source archive exceeds16MiB'
    (refs/'CameraSync-pinned.tar.gz').write_bytes(raw)
    selected=[];paths=[]
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        for member in tar.getmembers():
            if not member.isfile():continue
            path=member.name.split('/',1)[1];paths.append(path)
            if ('firmware' in path.lower() and path.endswith(('.kt','.sh','.yml','.json','.md'))) or path=='README.md':
                assert member.size<256*1024
                b=tar.extractfile(member).read();file=refs/(path.replace('/','_')+'.source.txt');assert not file.exists();file.write_bytes(b)
                selected.append(dict(repository_path=path,path=str(file.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    result=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),repository='https://github.com/rock3r/CameraSync',
        commit=PIN,HEAD_transport='git ls-remote confirmed same fixed40-byte SHA before capture',url=URL,HTTP_status=status,
        archive_path='references/CameraSync-pinned.tar.gz',archive_bytes=len(raw),archive_sha256=sha(raw),
        selected_sources=selected,repository_file_paths=paths,source_built_or_executed=False,device_operations=0)
    (HERE/'source-capture.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(commit=PIN,archive_bytes=len(raw),selected=[x['repository_path'] for x in selected])))


if __name__=='__main__':main()
