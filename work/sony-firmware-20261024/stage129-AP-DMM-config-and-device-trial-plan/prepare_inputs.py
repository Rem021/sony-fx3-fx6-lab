#!/usr/bin/env python3
"""Read exact official AP config/sum and startup files; never execute scripts."""
from pathlib import Path
import csv,datetime,hashlib,json,plistlib,subprocess,sys,tarfile,zlib
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1];SOURCE=BASE/'stage2/extraction'
sys.path.insert(0,str(SOURCE));from read_filesystems import Ext2
FDAT=BASE/'fx3-7.02-decrypted.fdat';FDAT_SHA='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
IMAGE=SOURCE/'nflasha7.img';IMAGE_SHA='ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7'
def hashfile(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()
def volume():
    v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and v['Writable']
def main():
    volume();assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    m=json.loads((BASE/'fx3-7.02-offline-manifest.json').read_text())
    assert hashfile(FDAT)==FDAT_SHA==m['decrypted_fdat_sha256'] and m['all_block_checksums_match'] and m['outer_crc32_matches']
    records=[];data={}
    def save(name,raw,source):
        p=STAGE/'inputs'/name
        with p.open('xb') as f:f.write(raw)
        records.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'source':source})
        data[name]=raw
    with FDAT.open('rb') as f:
        for member,name in [('0800_appli/setting/DmmCfg.bin','AP-DmmCfg.bin'),('0801_appli_sum/appli.sum','appli.sum')]:
            e=next(x for x in m['tar_members'] if x['name']==member);assert e['type']=='0'
            at=m['firmware_tar_offset']+e['data_offset_in_tar'];assert 512<=at and 0<e['size']<=FDAT.stat().st_size-at
            f.seek(at-512);header=f.read(512);ti=tarfile.TarInfo.frombuf(header,'utf-8','strict')
            assert ti.name==member and ti.size==e['size'] and ti.type==tarfile.REGTYPE
            raw=f.read(e['size']);assert len(raw)==e['size']
            save(name,raw,{'container':str(FDAT.relative_to(ROOT)),'container_sha256':FDAT_SHA,'member':member,
                'offset':at,'tar_header_checksum_validated':True,'header_sha256':hashlib.sha256(header).hexdigest()})
    rows=list(csv.reader(data['appli.sum'].decode().splitlines()))
    row=next(x for x in rows if len(x)>10 and x[10]=='setting/DmmCfg.bin')
    assert row[0]=='0' and int(row[2],16)==len(data['AP-DmmCfg.bin'])==66796
    assert int(row[1],16)==zlib.crc32(data['AP-DmmCfg.bin'])==0xf5d46b2d
    assert hashlib.sha256(data['AP-DmmCfg.bin']).hexdigest()=='48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1'
    assert hashfile(IMAGE)==IMAGE_SHA;fs=Ext2(IMAGE)
    try:
        entries={x['path']:x for x in fs.walk()}
        for member,name in [('/sbin/initrc/insmod_drv2','insmod_drv2'),('/sbin/initrc/fstab','fstab'),('/sbin/init2','init2'),('/sbin/init','init')]:
            e=entries[member];assert e['type']==0x8000
            raw=fs.data(e['inode']);assert len(raw)==e['size']
            save(name,raw,{'image':str(IMAGE.relative_to(ROOT)),'image_sha256':IMAGE_SHA,'regular_file':e})
    finally:fs.b.close();fs.f.close()
    j={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':records,
        'AP_config_official_sum_row':row,'official_size_crc_match':True,'source_inputs_read_only':True,
        'scripts_executed_mount_or_camera_access':False}
    with (STAGE/'input-receipt.json').open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'extracted':len(records),'AP_config_bytes':66796,'official_crc32':'f5d46b2d','device_operations':False}))
if __name__=='__main__':main()
