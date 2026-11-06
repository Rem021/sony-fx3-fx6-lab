#!/usr/bin/env python3
"""Extract one regular file from pinned official ext2 image, no mount/execute."""
import datetime
import sys
import resource_message as f


def main():
    f.im.volume()
    reader=f.BASE/'stage2/extraction/read_filesystems.py'
    assert f.im.sha(reader.read_bytes())=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    sys.path.insert(0,str(reader.parent));from read_filesystems import Ext2
    image=reader.parent/'nflasha15.img'
    assert f.im.sha(image.read_bytes())=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    out=f.STAGE/'official-files/nflasha15/kmod/devno.ko';assert not out.exists()
    fs=Ext2(image)
    try:
        matches=[x for x in fs.walk() if x['path']=='/kmod/devno.ko']
        assert len(matches)==1;entry=matches[0];assert entry['type']==0x8000
        data=fs.data(entry['inode']);assert len(data)==entry['size'] and data[:4]==b'\x7fELF'
    finally:fs.b.close();fs.f.close()
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as stream:stream.write(data)
    f.im.write_json(f.STAGE/'devno-extraction.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'partition':str(image.relative_to(f.ROOT)),'partition_sha256':f.im.sha(image.read_bytes()),
      'reader':str(reader.relative_to(f.ROOT)),'reader_sha256':f.im.sha(reader.read_bytes()),
      'entry':entry,'output':str(out.relative_to(f.ROOT)),'bytes':len(data),'sha256':f.im.sha(data),
      'mount_symlink_follow_module_load_or_payload_execution':False,'volume_uuid':f.im.VOLUME})
    print({'file':'devno.ko','bytes':len(data),'sha256':f.im.sha(data)})


if __name__=='__main__':main()
