#!/usr/bin/env python3
"""Index the original Sony installer CAB through its byte-complement container encoding."""
from pathlib import Path
import json,struct

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'official-interim/01_Update_ILMEFX3V20x.exe'
CAB_START=0x6ef5a
TABLE=bytes.maketrans(bytes(range(256)),bytes(i^255 for i in range(256)))


class Cabinet:
    def __init__(self,path=SOURCE):self.f=path.open('rb');self.size=1539537813
    def read(self,offset,length):
        assert 0<=offset and 0<=length and offset+length<=self.size
        self.f.seek(CAB_START+offset);b=self.f.read(length);assert len(b)==length
        return b.translate(TABLE)
    def close(self):self.f.close()


def main():
    c=Cabinet();b=c.read(0,36);h=struct.unpack('<4s5IBB5H',b)
    assert h[0]==b'MSCF' and h[2]==c.size and h[6:8]==(3,1)
    files_at,folder_count,file_count,flags=h[4],h[8],h[9],h[10]
    assert flags==0 # This pinned cabinet has no optional reserve/previous/next headers.
    folders=[]
    for i in range(folder_count):
        a,n,kind=struct.unpack('<IHH',c.read(36+i*8,8))
        folders.append(dict(index=i,data_offset=a,block_count=n,compression_raw=hex(kind),compression_kind=kind&15))
    assert files_at==36+8*folder_count
    cursor=files_at;files=[]
    for i in range(file_count):
        length,off,folder,date,time,attrs=struct.unpack('<II4H',c.read(cursor,16));cursor+=16
        name=bytearray()
        while True:
            ch=c.read(cursor,1);cursor+=1
            if ch==b'\0':break
            name.extend(ch);assert len(name)<1024
        assert folder<folder_count
        files.append(dict(name=name.decode('utf-8' if attrs&0x80 else 'cp1252'),bytes=length,
                          offset_in_folder=off,folder=folder,attributes_raw=hex(attrs)))
    assert cursor<=min(f['data_offset'] for f in folders)
    result=dict(status='PASS_ORIGINAL_INSTALLER_COMPLEMENT_CAB_INDEX',source=str(SOURCE.relative_to(HERE)),
                source_sha256=json.loads((SOURCE.parent/'member-receipt.json').read_bytes())['exe_sha256'],
                cab_file_offset=hex(CAB_START),cab_bytes=c.size,container_transform='byte xor 0xff',
                files=files,folders=folders,file_table_end=cursor,
                scope='Bounded static indexing of Microsoft Cabinet header, folder descriptors and member table after byte complement. No installer execution, no firmware modification. Host Settings.ini digital-signature options do not establish camera firmware verification policy.')
    (HERE/'cab-index-results.json').write_text(json.dumps(result,indent=2)+'\n');c.close()
    print(result['status'],'folders',folder_count,'files',file_count)
    for folder in folders:print('folder',folder)
    for f in files:print(f['folder'],f['offset_in_folder'],f['bytes'],f['name'])


if __name__=='__main__':main()
