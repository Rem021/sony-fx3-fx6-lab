#!/usr/bin/env python3
"""Read two regular files and their symlink metadata from pinned official ext2 images."""
from pathlib import Path
import datetime
import io
import json
import sys
from elftools.elf.elffile import ELFFile

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
sys.path.insert(0,str(BASE/'stage55-native-mux-identity'))
import mux_identity as prev
sys.path.insert(0,str(BASE/'stage2/extraction'))
import read_filesystems as fs


def main():
    im=prev.im;im.volume()
    assert im.sha(Path(fs.__file__).read_bytes())=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    rows=[]
    for part,pin,path,link,soname in (
      ('7','ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7',
       '/lib/libc-2.25.so','/lib/libc.so.6','libc.so.6'),
      ('15','df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',
       '/lib/libstdc++.so.6.0.22','/lib/libstdc++.so.6','libstdc++.so.6')):
        image=BASE/'stage2/extraction'/('nflasha'+part+'.img')
        assert im.sha(image.read_bytes())==pin
        reader=fs.Ext2(image);found={}
        for e in reader.walk():
            if e['path'] in (path,link):found[e['path']]=e
        assert set(found)=={path,link}
        assert found[path]['type']==0x8000 and found[link]['type']==0xa000
        target=reader.data(found[link]['inode']).decode()
        assert target==Path(path).name
        raw=reader.data(found[path]['inode']);assert len(raw)==found[path]['size']
        elf=ELFFile(io.BytesIO(raw));assert elf['e_machine']=='EM_AARCH64' and elf['e_type']=='ET_DYN'
        actual=[t.soname for sec in elf.iter_sections() if sec['sh_type']=='SHT_DYNAMIC'
          for t in sec.iter_tags() if t.entry.d_tag=='DT_SONAME']
        assert actual==[soname]
        out=STAGE/'official-files'/('nflasha'+part)/path.lstrip('/')
        assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
        rows.append({'partition':str(image.relative_to(prev.ROOT)),'partition_sha256':pin,
          'file_entry':found[path],'symlink_entry':found[link],'symlink_target_recorded_not_created':target,
          'output':str(out.relative_to(prev.ROOT)),'bytes':len(raw),'sha256':im.sha(raw),'SONAME':soname})
    im.write_json(STAGE/'official-extraction-receipt.json',{
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'reader_sha256':im.sha(Path(fs.__file__).read_bytes()),'files':rows,
      'mount_host_payload_execution_camera_or_network':False,'volume_uuid':im.VOLUME})
    print(json.dumps({'official_files':[{k:r[k] for k in ('output','bytes','sha256','SONAME')} for r in rows]}))


if __name__=='__main__':main()
