#!/usr/bin/env python3
"""Read bounded public BK4 template parameters from the pinned official FDAT."""
import datetime,hashlib,json,struct,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
FW=TASK.parent/'sony-firmware-20261024'
FDAT_PIN='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
CANONICAL='0110_backup/SYSIPSX-DSLR/ALCIN/CX95900_ALLLANG.bin'
def sha(b):return hashlib.sha256(b).hexdigest()

def take_member(raw,manifest,row):
    at=manifest['firmware_tar_offset']+row['data_offset_in_tar'];n=row['size'];assert row['type']=='0'
    h=raw[at-512:at];assert len(h)==512
    stored=int(h[148:156].rstrip(b'\0 ').lstrip(b' ') or b'0',8)
    assert sum(h[:148])+8*32+sum(h[156:])==stored
    name=h[:100].split(b'\0')[0];prefix=h[345:500].split(b'\0')[0]
    if prefix:name=prefix+b'/'+name
    assert name.decode()==row['name'] and int(h[124:136].rstrip(b'\0 ').lstrip(b' ') or b'0',8)==n
    assert 0<=at and n<=len(raw)-at
    return raw[at:at+n],dict(data_offset=at,bytes=n,tar_header_sha256=sha(h),tar_header_checksum_verified=True)

def property_at(record,key):
    subs,props,dataoff,datasize=struct.unpack_from('<4I',record,16)
    group,index=key>>16,key&0xffff;assert group<subs
    count,first=struct.unpack_from('<HI',record,256+group*6)
    assert index<count and first+count<=props
    entry=256+subs*6+(first+index)*6;attr,value=struct.unpack_from('<HI',record,entry)
    assert value!=0xffffffff;size=value>>24;at=value&0xffffff;maximum=size;prefix=0
    if size==0xff:size=maximum=struct.unpack_from('<H',record,at)[0];prefix=2
    elif size==0:size,maximum=struct.unpack_from('<HH',record,at);prefix=4
    assert at>=dataoff and size<=maximum and at+prefix+maximum<=dataoff+datasize
    value_bytes=record[at+prefix:at+prefix+size]
    return dict(key=hex(key),group_count=count,entry_offset=hex(entry),attribute=hex(attr),
        packed_pointer=hex(value),data_offset=hex(at+prefix),bytes=size,value_hex=value_bytes.hex(),
        u64=hex(int.from_bytes(value_bytes,'little')) if size==8 else None)

def records(raw):
    at=0;out=[]
    while at<len(raw):
        assert at+256<=len(raw) and raw[at+12:at+16]==b'BK4\0'
        dataoff,datasize,checksum=struct.unpack_from('<3I',raw,at+24);n=dataoff+datasize
        assert n>=256 and at+n<=len(raw)
        record=raw[at:at+n]
        assert (sum(record[:32])+sum(record[36:]))&0xffffffff==checksum
        out.append((at,record));end=at+n
        if end==len(raw):break
        at=(end+0xfff)&~0xfff
    assert out and out[-1][0]+len(out[-1][1])==len(raw)
    return out

def main():
    target=HERE/'public-template-parameters.json';assert not target.exists()
    source=FW/'fx3-7.02-decrypted.fdat';raw=source.read_bytes();assert len(raw)==808704512 and sha(raw)==FDAT_PIN
    manifest=json.loads((FW/'fx3-7.02-offline-manifest.json').read_text())
    sumrow=next(r for r in manifest['tar_members'] if r['name']=='0111_backup_sum/backup.sum')
    sums,sum_source=take_member(raw,manifest,sumrow);official={}
    for line in sums.decode().splitlines():
        fields=line.split(',')
        if fields[0]=='0':official['0110_backup/'+fields[10]]=(int(fields[1],16),int(fields[2],16))
    (HERE/'backup.sum').write_bytes(sums)
    dest=HERE/'original-records';dest.mkdir(exist_ok=True);templates=[]
    for row in manifest['tar_members']:
        if not(row['type']=='0' and row['name'].startswith('0110_backup/') and row['name'].endswith('.bin')):continue
        b,provenance=take_member(raw,manifest,row);crc,size=official[row['name']]
        assert len(b)==size and zlib.crc32(b)&0xffffffff==crc
        found=records(b);assert len(found)==2;items=[]
        for i,(at,record) in enumerate(found):
            params=[property_at(record,key) for key in [0xfa0182,0xfa0183,0xfa0184]]
            assert [p['bytes'] for p in params]==[8,8,4]
            item=dict(index=i,file_offset=hex(at),bytes=len(record),sha256=sha(record),checksum_verified=True,
                      parameters=params)
            if row['name']==CANONICAL:
                file=dest/f'canonical-bank{i}.bin';assert not file.exists();file.write_bytes(record)
                item['saved_original']=str(file.relative_to(HERE))
            items.append(item)
        templates.append(dict(member=row['name'],sha256=sha(b),official_crc32=hex(crc),official_size_crc_verified=True,
                              provenance=provenance,records=items))
    assert len(templates)==22
    signatures={tuple(p['value_hex'] for r in t['records'] for p in r['parameters']) for t in templates}
    assert len(signatures)==1
    sys.path.insert(0,str(FW/'stage2/extraction'));from read_filesystems import FAT16
    partition=FW/'stage2/extraction/nflasha8.img'
    assert sha(partition.read_bytes())=='3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b'
    fs=FAT16(partition);row=next(r for r in fs.walk() if r['path']=='/tomco.txt')
    tomco=fs.data(row['cluster'],row['size']);assert len(tomco)==710
    (HERE/'tomco.txt').write_bytes(tomco)
    out=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),official_FDAT_sha256=FDAT_PIN,
        official_backup_sum_sha256=sha(sums),backup_sum_provenance=sum_source,templates=templates,
        canonical_template=CANONICAL,canonical_is_body_selection=False,
        exact_parameter_IDs_read=['0xfa0182','0xfa0183','0xfa0184'],records_total=44,
        both_record_parameter_triples_identical_across_all_templates=True,
        tomco_source=dict(partition_sha256='3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b',
                          file=row,sha256=sha(tomco)),
        scope='Public official defaults, not user-body backup or active boot state. Both records retained; no automatic AP/CP label or bank selection. No signing-key search, modification, sync, device or native Sony execution.')
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(templates=len(templates),checksummed_records=44,record_parameters=templates[0]['records'],device_actions=0)))

if __name__=='__main__':main()
