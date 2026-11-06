#!/usr/bin/env python3
"""Verify original ZIP/MD5 and unpack bounded regular tar members, no execution."""
import hashlib,io,json,tarfile,zipfile,re
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    out=HERE/'early-unpack.json';assert not out.exists()
    src=HERE/'originals/MPC-3610_V201.zip';raw=src.read_bytes()
    assert sha(raw)=='c6f5a3ad1a71234af265430b50ef87b29c8c7bba16d5c2e8edd4fb58d47f00d7'
    files=[];extracted={}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        for i in z.infolist():
            row=dict(path=i.filename,bytes=i.file_size,compressed_bytes=i.compress_size,crc32=f'{i.CRC:08x}')
            name=PurePosixPath(i.filename);assert not name.is_absolute() and '..' not in name.parts
            if name.suffix.lower() in ['.bin','.md5','.txt']:
                b=z.read(i);assert len(b)==i.file_size
                dest=HERE/'originals'/name.name;assert not dest.exists();dest.write_bytes(b)
                row.update(sha256=sha(b),extracted_as=str(dest.relative_to(HERE)));extracted[name.suffix.lower()]=b
            else:row['scope']='CRC and metadata only; PDF contents not processed.'
            files.append(row)
    fw=extracted['.bin'];md5text=extracted['.md5'].decode('ascii');expected=re.search(r'\b[0-9a-fA-F]{32}\b',md5text).group().lower()
    assert hashlib.md5(fw).hexdigest()==expected
    members=[];outroot=HERE/'outer-members';outroot.mkdir()
    with tarfile.open(fileobj=io.BytesIO(fw),mode='r:') as t:
        for m in t:
            path=PurePosixPath(m.name);assert not path.is_absolute() and '..' not in path.parts
            row=dict(path=m.name,bytes=m.size,type=m.type.decode('ascii'),header_offset=m.offset,data_offset=m.offset_data)
            if m.isfile():
                assert m.size<=200*1024*1024
                b=t.extractfile(m).read();assert len(b)==m.size
                dest=outroot/str(path);assert dest.resolve().is_relative_to(outroot.resolve());dest.parent.mkdir(parents=True,exist_ok=True)
                assert not dest.exists();dest.write_bytes(b);row['sha256']=sha(b)
                if path.suffix=='.xml':row['xml']=b.decode('utf-8')
            else:assert m.isdir()
            members.append(row)
    result=dict(source_zip_bytes=len(raw),source_zip_sha256=sha(raw),ZIP_CRC_all_pass=True,zip_members=files,
        firmware_bytes=len(fw),firmware_sha256=sha(fw),MD5_same_package_matches=True,md5_file_text=md5text,
        outer_format='uncompressed tar',tar_members=members,
        scope='Only ZIP and tar are unpacked; private payload has not been decoded. No program/updater/firmware executed or device accessed.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(firmware_bytes=len(fw),firmware_sha256=sha(fw),tar_members=members),ensure_ascii=False))
if __name__=='__main__':main()
