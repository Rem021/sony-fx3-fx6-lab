#!/usr/bin/env python3
"""Select Sony GPL USB core references as data; no kernel build or device calls."""
from pathlib import Path
from hashlib import sha256
import json
import re
import tarfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent


def main():
    archive=BASE/'stage65-windows-cache-and-runtime-readiness/work/vendor-source-reference/range-resume-20261026/linux-kernel.complete.tar.gz'
    assert sha256(archive.read_bytes()).hexdigest()=='bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
    records=[];hits=[]
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            if not member.isfile() or member.size>500000:continue
            if '/usb/gcore/' not in member.name:continue
            if not member.name.endswith(('.c','.h')):continue
            path=Path(member.name);assert not path.is_absolute() and '..' not in path.parts
            raw=source.extractfile(member).read();assert len(raw)==member.size
            target=HERE/'work/official-kernel-reference'/path
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as handle:handle.write(raw)
            records.append({'archive_member':member.name,'path':str(target.relative_to(HERE)),
                            'bytes':len(raw),'sha256':sha256(raw).hexdigest()})
            matches=[{'line':n+1,'text':line.decode('ascii',errors='replace')[:200]}
                     for n,line in enumerate(raw.splitlines())
                     if re.search(rb'sha256|37ff|d7aa|authentic|nin_|senser',line,re.I)]
            if matches:hits.append({'path':str(target.relative_to(HERE)),'matches':matches[:30],'match_count':len(matches)})
    result={'status':'OFFICIAL_GPL_REFERENCE_SELECTED_NOT_EXACT_702_RUNTIME_PROOF',
            'official_source_page':'https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html',
            'archive_sha256':'bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f',
            'records':records,'keyword_hits':hits,'kernel_built_loaded_or_device_operations':False}
    with (HERE/'official-gcore-reference.json').open('x') as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(json.dumps({'selected_files':len(records),'keyword_hits':hits}))


if __name__=='__main__':main()
