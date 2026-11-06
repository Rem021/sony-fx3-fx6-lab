#!/usr/bin/env python3
"""Extract regular original FAT12 boot members, deduplicating identical bytes."""
from pathlib import Path
from hashlib import sha256,file_digest
import importlib.util,json,os,zlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
READER=ROOT/'work/sony-firmware-20261024/stage2/extraction/read_filesystems.py'


def main():
    parser=READER.read_bytes();spec=importlib.util.spec_from_file_location('bounded_fat',READER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    packages=json.loads((HERE/'original-update-engine-results.json').read_bytes())['packages'];results=[]
    out=HERE/'fat-members';out.mkdir(exist_ok=True)
    for package in packages:
        source=next(m for m in package['members'] if m['member'].endswith('/nflasha1'));path=HERE/source['output']
        with path.open('rb') as f:assert file_digest(f,'sha256').hexdigest()==source['sha256']
        fs=module.FAT16(path);assert fs.meta['kind']=='FAT12';files=[]
        for entry in fs.walk():
            if entry['type']!=0x8000:continue
            assert 0<=entry['size']<=10*1024*1024
            data=fs.data(entry['cluster'],entry['size']);assert len(data)==entry['size']
            digest=sha256(data).hexdigest();dest=out/(digest+'-'+Path(entry['path']).name)
            if dest.exists():assert dest.read_bytes()==data
            else:
                with dest.open('xb') as f:os.chmod(dest,0o600);f.write(data)
            files.append(dict(**entry,sha256=digest,crc32=f'{zlib.crc32(data):08x}',output=str(dest.relative_to(HERE))))
        results.append(dict(version=package['version'],source_sha256=source['sha256'],metadata=fs.meta,files=files))
        fs.b.close();fs.f.close()
        print('ORIGINAL_FAT_MEMBERS',package['version'],len(files),flush=True)
    assert READER.read_bytes()==parser
    comparison=[]
    for a in results[0]['files']:
        b=next(r for r in results[1]['files'] if r['path']==a['path'])
        comparison.append(dict(path=a['path'],same=a['sha256']==b['sha256'],bytes=a['size']))
    result=dict(status='PASS_ORIGINAL_FAT12_BOOT_MEMBERS_EXTRACTED',reader_source=str(READER.relative_to(ROOT)),
        reader_source_sha256=sha256(parser).hexdigest(),packages=results,comparison=comparison,
        scope='Read-only original FAT12 parsing and ordinary-file extraction. Byte-identical members share one output; directories, links or devices are not created from image records, and no extracted boot code is executed.')
    (HERE/'updater-fat-extraction-results.json').write_text(json.dumps(result,indent=2)+'\n')
    for row in comparison:print(row,flush=True)


if __name__=='__main__':main()
