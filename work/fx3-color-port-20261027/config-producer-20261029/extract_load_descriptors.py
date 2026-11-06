#!/usr/bin/env python3
"""Pin original BK4 load descriptors and NOR loader from official FDAT bytes."""
import csv,hashlib,importlib.util,io,json,struct,sys,tarfile,zlib
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
FW=TASK.parent/'sony-firmware-20261024'
FDAT=FW/'fx3-7.02-decrypted.fdat'
FDAT_PIN='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
CANONICAL='0110_backup/SYSIPSX-DSLR/ALCIN/CX95900_ALLLANG.bin'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    out=HERE/'load-descriptor-sources.json';assert not out.exists()
    helper=TASK/'dmm-backup-20261029/extract_backup_parameters.py'
    previous=json.loads((helper.parent/'final-receipt.json').read_text())
    pin=next(x for x in previous['files'] if x['path']==helper.name)
    assert sha(helper.read_bytes())==pin['sha256']
    spec=importlib.util.spec_from_file_location('original_property_parser',helper)
    lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
    h=hashlib.sha256()
    with FDAT.open('rb') as f:
        while chunk:=f.read(8*1024*1024):h.update(chunk)
    assert FDAT.stat().st_size==808704512 and h.hexdigest()==FDAT_PIN
    manifest=json.loads((FW/'fx3-7.02-offline-manifest.json').read_text())
    rows={x['name']:x for x in manifest['tar_members']}
    provenance=[]
    def take(name):
        x=rows[name];assert x['type']=='0'
        at=manifest['firmware_tar_offset']+x['data_offset_in_tar']
        with FDAT.open('rb') as f:
            f.seek(at-512);header=f.read(512)
            ti=tarfile.TarInfo.frombuf(header,'utf-8','strict')
            assert ti.name==name and ti.size==x['size'] and ti.type==tarfile.REGTYPE
            data=f.read(ti.size);assert len(data)==ti.size
        provenance.append(dict(member=name,FDAT_offset=at,bytes=len(data),sha256=sha(data),header_sha256=sha(header)))
        return data
    sums=take('0111_backup_sum/backup.sum');checks={}
    for line in csv.reader(sums.decode().splitlines()):
        if line[0]=='0':checks['0110_backup/'+line[10]]=(int(line[1],16),int(line[2],16))
    original=HERE/'original-files';original.mkdir(exist_ok=True)
    templates=[]
    for name in rows:
        if not name.startswith('0110_backup/') or not name.endswith('.bin'):continue
        data=take(name);crc,size=checks[name];assert len(data)==size and zlib.crc32(data)&0xffffffff==crc
        banks=[]
        for bank,(offset,record) in enumerate(lib.records(data)):
            prop=lib.property_at(record,0xfa0080);payload=bytes.fromhex(prop.pop('value_hex'))
            assert len(payload)==9216 and len(payload)%144==0
            entries=[]
            for i in range(64):
                chunk=payload[i*144:(i+1)*144]
                if not any(chunk):continue
                begin,end,partition,mode=struct.unpack_from('<2Q2I',chunk)
                path=chunk[24:].split(b'\0',1)[0].decode('ascii')
                entries.append(dict(index=i,start=hex(begin),end=hex(end),partition=partition,mode=hex(mode),
                    path=path,record_offset=hex(i*144),original_record_sha256=sha(chunk)))
            item=dict(bank=bank,template_record_offset=hex(offset),record_sha256=sha(record),
                property=prop,payload_sha256=sha(payload),entries=entries,
                DMM_parameter_values=[lib.property_at(record,key) for key in [0xfa0182,0xfa0183,0xfa0184]])
            if name==CANONICAL:
                f=original/f'bank{bank}-fa0080.bin';assert not f.exists();f.write_bytes(payload)
                item['saved_payload']=str(f.relative_to(HERE))
            banks.append(item)
        assert len(banks)==2
        templates.append(dict(member=name,bytes=len(data),sha256=sha(data),official_CRC32=hex(crc),banks=banks))
    assert len(templates)==22
    canonical=next(t for t in templates if t['member']==CANONICAL)
    chosen=canonical['banks'][1];dmm=[x for x in chosen['entries'] if x['path']=='\\DmmCfg.bin'];assert len(dmm)==1
    dmm=dmm[0];assert dmm['start']=='0x809a08e00' and dmm['end']=='0x809a21dff' and dmm['partition']==8
    assert int(dmm['end'],16)-int(dmm['start'],16)+1==0x19000
    assert chosen['DMM_parameter_values'][0]['u64']==dmm['start']
    assert chosen['DMM_parameter_values'][1]['u64']=='0x19000'
    loader_tar=take('0750_nor_loader/loader_nor.tar');members=[]
    with tarfile.open(fileobj=io.BytesIO(loader_tar),mode='r:') as tf:
        for ti in tf:
            if not ti.isfile():continue
            data=tf.extractfile(ti).read();assert len(data)==ti.size
            members.append(dict(name=ti.name,bytes=len(data),sha256=sha(data)))
            if Path(ti.name).name in ['loader_nor.bin','pformat_config.txt']:
                f=original/Path(ti.name).name;assert not f.exists();f.write_bytes(data)
                members[-1]['saved_original']=str(f.relative_to(HERE))
    assert sha((original/'loader_nor.bin').read_bytes())=='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
    result=dict(FDAT_source=str(FDAT),FDAT_sha256=FDAT_PIN,canonical_template=CANONICAL,
        canonical_is_body_selection=False,record_stride_bytes=144,records_per_payload=64,templates=templates,
        original_member_provenance=provenance,loader_tar_members=members,
        binding=dict(bank1_DmmCfg_descriptor=dmm,parameter_fa0182_matches_start=True,
            inclusive_capacity_matches_fa0183=True,capacity_bytes=0x19000),
        scope='Official defaults and exact source records only. A loading descriptor is not actual boot execution or a live body backup. The NOR reader and normal record selection still require original-code tracing. No keys, native Sony process or device action.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(templates=len(templates),canonical_entries=[dict(bank=x['bank'],entries=x['entries']) for x in canonical['banks']],
        binding=result['binding'],loader_members=members)))
if __name__=='__main__':main()
