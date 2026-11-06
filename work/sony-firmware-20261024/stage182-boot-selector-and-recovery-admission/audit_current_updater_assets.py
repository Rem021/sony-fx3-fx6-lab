#!/usr/bin/env python3
"""Read-only host audit of existing official FX3 7.02 container and boot assets.

No Sony code execution, mount, device access, decryption/repacking or source writes.
"""
from pathlib import Path
import hashlib, io, json, os, struct, subprocess, sys, tarfile, zlib

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
OUT = HERE / 'current-updater-evidence'
PINS = {
    'fx3-7.02-BODYDATA.DAT': 'f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854',
    'fx3-7.02-decrypted.fdat': '694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768',
}

def sha(data): return hashlib.sha256(data).hexdigest()

def save(name, raw):
    p = OUT / name
    assert p.resolve().is_relative_to(OUT.resolve())
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists(): assert p.read_bytes() == raw
    else:
        with p.open('xb') as f:
            os.chmod(p, 0o600)
            f.write(raw)
    return str(p)

def main():
    volume = subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T'])
    import plistlib
    vol = plistlib.loads(volume)
    assert vol['MountPoint'] == '/Volumes/KAFU2T' and vol['VolumeUUID'].upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    OUT.mkdir(parents=True, exist_ok=True)
    sources = []
    for name, pin in PINS.items():
        p = SOURCE / name
        with p.open('rb') as f: actual = hashlib.file_digest(f, 'sha256').hexdigest()
        assert actual == pin
        sources.append(dict(path=str(p), bytes=p.stat().st_size, sha256=actual))
    raw = (SOURCE / 'fx3-7.02-BODYDATA.DAT').read_bytes()
    assert raw[:8] == b'\x89UFU\r\n\x1a\n'
    chunks=[]; pos=8
    while pos<len(raw):
        length, kind=struct.unpack_from('>I4s',raw,pos)
        assert pos+8+length<=len(raw)
        chunks.append(dict(header_offset=pos,type=kind.decode('ascii'),payload_offset=pos+8,bytes=length))
        pos+=8+length
    assert pos==len(raw) and chunks[-1]['type']=='DEND' and chunks[-1]['bytes']==4
    assert zlib.crc32(raw[:-12])==struct.unpack('>I',raw[-4:])[0]
    uf = dict(bytes=len(raw),chunks=chunks,crc32=f'{zlib.crc32(raw[:-12]):08x}',exact_end=True)
    del raw
    plain=(SOURCE / 'fx3-7.02-decrypted.fdat').read_bytes()
    hdr=plain[:512]
    assert hdr[:8]==b'UDTRFIRM' and zlib.crc32(hdr[12:])==struct.unpack_from('<I',hdr,8)[0]
    count=struct.unpack_from('<I',hdr,56)[0]
    table=[]
    for i in range(28):
        row=hdr[64+16*i:80+16*i]
        mode=row[:1].decode('ascii'); start,length=struct.unpack_from('<II',row,4)
        assert start+length<=len(plain)
        table.append(dict(slot=i,mode=mode,offset=start,bytes=length,raw=row.hex()))
    assert count==2 and all(r['raw']=='00'*16 for r in table[count:])
    assert table[0]['mode']=='U' and table[0]['offset']==512
    assert table[1]['mode']=='P' and table[1]['bytes']==0
    firmoff,firmsize=struct.unpack_from('<II',hdr,48)
    assert 512+table[0]['bytes']==firmoff and firmoff+firmsize==len(plain)
    body=plain[512:firmoff]
    assert body[:4]==b'hsqs'
    save('original-members/udtrbody.squashfs',body)
    fd=dict(version=f'{hdr[33]:x}.{hdr[32]:02x}',model_id=hex(struct.unpack_from('<I',hdr,36)[0]),
            bytes=len(plain),header_crc32=f'{zlib.crc32(hdr[12:]):08x}',filesystem_count=count,filesystem_slots=table,
            firmware_offset=firmoff,firmware_bytes=firmsize,
            region_accounting=[dict(kind='header',offset=0,bytes=512),dict(kind='U body SquashFS',offset=512,bytes=len(body)),dict(kind='firmware TAR',offset=firmoff,bytes=firmsize)],
            exact_contiguous_coverage=True,body_sha256=sha(body))
    tarbytes=plain[firmoff:]; members=[]; pos=0
    while any(tarbytes[pos:pos+512]):
        header=tarbytes[pos:pos+512];assert len(header)==512
        checksum=int(header[148:156].strip(b' \0') or b'0',8)
        assert sum(header[:148])+8*32+sum(header[156:])==checksum
        name=header[:100].split(b'\0')[0].decode(); prefix=header[345:500].split(b'\0')[0].decode()
        if prefix:name=prefix+'/'+name
        size=int(header[124:136].strip(b' \0') or b'0',8)
        kind=header[156:157].decode();assert kind in ('0','2','5','\0'),(name,kind)
        if kind=='5':name=name.rstrip('/')
        raw=tarbytes[pos+512:pos+512+size];assert len(raw)==size
        rounded=(size+511)//512*512
        assert not any(tarbytes[pos+512+size:pos+512+rounded]),name
        r=dict(name=name,size=size,type=kind,tar_header_offset=pos,data_offset_in_tar=pos+512,fdat_data_offset=firmoff+pos+512,header_checksum_matches=True)
        if kind in ('0','\0'):
            r.update(sha256=sha(raw),crc32=f'{zlib.crc32(raw):08x}')
            if name.endswith(('partinf.conf','mount.conf','.sum','loader_nor.tar')) or name in ('0800_appli/setting/cxd90057.dtb','0800_appli/setting/kemco.txt'):
                r['output']=save('tar-selected/'+name,raw)
        members.append(r);pos+=512+rounded
    assert len(tarbytes)-pos>=1024 and not any(tarbytes[pos:])
    prior=json.loads((SOURCE/'fx3-7.02-offline-manifest.json').read_text())['tar_members']
    assert [dict(name=r['name'],size=r['size'],type=r['type'],data_offset_in_tar=r['data_offset_in_tar']) for r in members]==prior
    tarcheck=dict(entries=len(members),regular_files=sum(r['type']=='0' for r in members),all_header_checksums_match=True,
                  all_data_and_padding_bounded=True,end_markers_start=pos,trailing_zero_bytes=len(tarbytes)-pos,
                  matches_prior_full_manifest=True,members=members)
    sys.path.insert(0,str(SOURCE/'stage2/extraction'))
    from read_filesystems import FAT16,Ext2
    partitions=[]; boots=[]; rootfs=[]
    carve=json.loads((SOURCE/'stage2/extraction/partition-carve-manifest.json').read_text())
    for old in carve:
        row=next(r for r in members if r['name']==old['source_member'])
        assert row['sha256']==old['sha256'] and row['crc32']==old['crc32'].removeprefix('0x') and row['size']==old['size']
        p=Path(old['output'])
        with p.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==row['sha256']
        partitions.append(dict(member=row['name'],bytes=row['size'],sha256=row['sha256'],fdat_offset=row['fdat_data_offset'],crc32=row['crc32']))
        if p.name=='nflasha3.img':
            fs=FAT16(p)
            for e in fs.walk():
                if e['type']!=0x8000:continue
                data=fs.data(e['cluster'],e['size'])
                rec=dict(path=e['path'],bytes=len(data),sha256=sha(data),first64=data[:64].hex(),source_partition_sha256=row['sha256'])
                if e['path'] in ('/vmlinux.bin','/initrd.img'):
                    rec['output']=save('p3-main/'+e['path'].lstrip('/'),data)
                boots.append(rec)
    for label,p in [('p3-initrd',OUT/'p3-main/initrd.img'),('p7-rootfs',SOURCE/'stage2/extraction/nflasha7.img')]:
        fs=Ext2(p);items=[]
        for e in fs.walk():
            item=dict(e)
            if e['type']==0x8000:
                data=fs.data(e['inode']);item['sha256']=sha(data)
                if e['path'].startswith('/sbin/') and e['size']<16384 or e['path'] in ('/version.txt','/root/chassis','/root/IAMUPDATER','/root/common.src'):
                    item['output']=save(label+e['path'],data)
                    item['text']=data.decode('utf8',errors='replace')
            elif e['type']==0xa000:item['symlink_target']=fs.data(e['inode']).decode('utf8',errors='replace')
            items.append(item)
        rootfs.append(dict(label=label,path=str(p),metadata=fs.meta,entries=items,regular_files=sum(e['type']==0x8000 for e in items)))
    nested=[]
    outer=next(r for r in members if r['name']=='0750_nor_loader/loader_nor.tar')
    nestedraw=tarbytes[outer['data_offset_in_tar']:outer['data_offset_in_tar']+outer['size']]
    with tarfile.open(fileobj=io.BytesIO(nestedraw),mode='r:') as t:
        for m in t:
            r=dict(name=m.name,bytes=m.size,type=m.type.decode(),offset_data=m.offset_data)
            if m.isfile():
                data=t.extractfile(m).read();r.update(sha256=sha(data),output=save('nor-loader-members/'+m.name,data))
            nested.append(r)
    result=dict(status='PASS_CURRENT_702_CONTAINER_AND_BOOT_ASSET_COVERAGE',volume_uuid=vol['VolumeUUID'],sources=sources,
                ufu=uf,fdat=fd,tar=tarcheck,partition_payloads=partitions,p3_boot_files=boots,root_filesystems=rootfs,nor_loader_members=nested,
                absent_top_level_update_prefixes=[p for p in ('0200_loader/','0400_updater/','0401_updater_sum/') if not any(r['name'].startswith(p) for r in members)],
                scope='Official 7.02 host-only structural coverage, hashes, FAT/ext2 reading and selected copies. No extracted firmware code or script executed. No camera, USB, VM, firmware reconstruction, mutation or flash. Current package does not establish actual installed p1 identity.')
    save('current-updater-asset-audit.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(dict(status=result['status'],tar_entries=len(members),header_slots=count,absent_prefixes=result['absent_top_level_update_prefixes'],
        partitions=[r['member'] for r in partitions],p3_boot=[r for r in boots if r['path'] in ('/initrd.img','/vmlinux.bin')],
        roots=[dict(label=r['label'],entries=len(r['entries']),regular_files=r['regular_files']) for r in rootfs],nor_members=nested),indent=2))

if __name__=='__main__':main()
