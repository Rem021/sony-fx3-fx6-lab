#!/usr/bin/env python3
"""Download an observed official ZIP as data; no installer or device operations."""
import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import subprocess
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE / 'package-acquisition.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    discovery = json.loads((HERE / 'source-discovery.json').read_text())
    source = next(r for r in discovery['requests'] if r['name'] == '350-mac-derived-prefix')
    assert source['http_status'] == 206 and source['ZIP_local_header_prefix']
    result = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'url':source['url'],
              'URL_provenance':source['source_kind'], 'If_Match':source['headers']['ETag'],
              'vendor_execution':False,'device_actions':0}
    try:
        request = urllib.request.Request(source['url'],headers={'User-Agent':'FirmwareCatalogResearch/1.0','Accept-Encoding':'identity','If-Match':result['If_Match']})
        with urllib.request.urlopen(request,timeout=30) as response:
            assert response.code == 200 and response.headers.get('ETag') == result['If_Match']
            data = response.read(32*1024*1024+1)
            assert len(data) == int(source['headers']['Content-Range'].rsplit('/',1)[1]) <= 32*1024*1024
            assert data[:source['bytes']] == (HERE / source['path']).read_bytes()
            result.update(http_status=response.code, headers={k:v for k,v in response.headers.items() if k.lower() in ['content-length','etag','date','content-type']})
        filename = PurePosixPath(source['url']).name
        with (HERE / filename).open('xb') as out:
            out.write(data)
        result.update(path=filename,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),prefix_byte_identical=True)
        members = []
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.infolist()
            assert len(info)<128 and sum(x.file_size for x in info)<128*1024*1024
            for row in info:
                assert not row.flag_bits & 1
                item = {'name':row.filename,'bytes':row.file_size,'compression':row.compress_type,'CRC32':f'{row.CRC:08x}'}
                if not row.is_dir():
                    payload = archive.read(row)
                    item.update(CRC32_verified=True,sha256=hashlib.sha256(payload).hexdigest())
                    if row.filename.lower().endswith(('.dmg','.pkg','.txt')):
                        target = PurePosixPath(row.filename).name
                        with (HERE / target).open('xb') as out:
                            out.write(payload)
                        item['saved_path'] = target
                members.append(item)
        result.update(result='OFFICIAL_ZIP_CRC_VERIFIED_NOT_INSTALLED',members=members,PDF_contents_read=False)
    except Exception as error:
        result.update(result='DOWNLOAD_OR_ARCHIVE_GAP',error={'type':type(error).__name__,'message':str(error)})
    (HERE / 'package-acquisition.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ['result','http_status','bytes','error','members']},ensure_ascii=False))


if __name__ == '__main__':
    main()
