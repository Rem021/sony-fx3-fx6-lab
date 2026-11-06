#!/usr/bin/env python3
"""Build an equal-size two-member software delta; never launches QEMU."""
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DONOR = HERE.parent
MAC = HERE.parents[5]
BASE = MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability'
BASELINE = BASE/'fx3-platform-frozen-baseline.json'
CPIO = BASE/'vmopt-20261103-try2-long-media-gap-v2/guest.cpio'
OUTPUT = HERE/'guest-two-entry.cpio'
SOURCE_HASH = 'eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d'
REPLACEMENTS = {
    'usr/bin/bootin.elf': {'bytes':23960,'fx3':'dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2',
                         'fx6':'72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6'},
    'usr/bin/im.elf': {'bytes':40920,'fx3':'5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91',
                     'fx6':'87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec'},
}

def sha_file(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle,'sha256').hexdigest()

def hash_range(handle,start,size):
    handle.seek(start)
    digest = hashlib.sha256()
    while size:
        data = handle.read(min(size,1024*1024))
        if not data:
            raise ValueError('truncated member')
        digest.update(data)
        size -= len(data)
    return digest.hexdigest()

def members(path):
    result = {}
    with path.open('rb') as handle:
        offset = 0
        while True:
            handle.seek(offset)
            header = handle.read(110)
            assert len(header)==110 and header[:6]==b'070701'
            fields = [int(header[6+8*i:14+8*i],16) for i in range(13)]
            mode,size,namesz = fields[1],fields[6],fields[11]
            assert 0 < namesz < 4096
            rawname = handle.read(namesz)
            assert rawname[-1:] == b'\0'
            name = rawname[:-1].decode()
            start = (offset+110+namesz+3)&~3
            if name=='TRAILER!!!':
                break
            assert name not in result and not name.startswith('/') and '..' not in name.split('/')
            result[name] = {'header_offset':offset,'data_offset':start,'bytes':size,
                            'mode':oct(mode),'sha256':hash_range(handle,start,size)}
            offset = (start+size+3)&~3
    return result

def equal_range(a,b,start,size):
    a.seek(start);b.seek(start)
    digest = hashlib.sha256()
    while size:
        take = min(size,1024*1024)
        x,y = a.read(take),b.read(take)
        assert len(x)==take and x==y, ('unexpected byte delta',start)
        digest.update(x);size-=take;start+=take
    return digest.hexdigest()

def main():
    disk = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert disk.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    assert sha_file(BASELINE)=='854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669'
    frozen = json.loads(BASELINE.read_text())
    for key,item in frozen['sha256'].items():
        assert sha_file(Path(item['path']))==item['sha256'], key
    assert sha_file(CPIO)==SOURCE_HASH
    old = members(CPIO)
    assert len(old)==1140
    replacements = {}
    for name,pin in REPLACEMENTS.items():
        assert old[name]['sha256']==pin['fx3'] and old[name]['bytes']==pin['bytes']
        source = DONOR/'nflasha15-files/bin'/Path(name).name
        data = source.read_bytes()
        assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['fx6']
        replacements[name] = data
    if not OUTPUT.exists():
        temp = OUTPUT.with_suffix('.cpio.partial')
        with temp.open('xb') as dst, CPIO.open('rb') as src:
            shutil.copyfileobj(src,dst,1024*1024)
            for name,data in replacements.items():
                dst.seek(old[name]['data_offset']);dst.write(data)
            dst.flush();os.fsync(dst.fileno())
        temp.rename(OUTPUT)
    assert not OUTPUT.is_symlink() and OUTPUT.stat().st_size==CPIO.stat().st_size
    new = members(OUTPUT)
    assert new.keys()==old.keys()
    changed = []
    for name,before in old.items():
        after = new[name]
        assert all(before[k]==after[k] for k in ('header_offset','data_offset','bytes','mode'))
        if before['sha256']!=after['sha256']:
            assert name in REPLACEMENTS and after['sha256']==REPLACEMENTS[name]['fx6']
            changed.append({'name':name,'before':before,'after':after})
    assert {x['name'] for x in changed}==set(REPLACEMENTS)
    # Compare every byte outside the two payload ranges, including metadata,
    # symlinks, /init, all helper bytes, archive padding and trailer.
    unchanged_ranges = []
    with CPIO.open('rb') as a, OUTPUT.open('rb') as b:
        cursor = 0
        for item in sorted(changed,key=lambda x:x['before']['data_offset']):
            start = item['before']['data_offset']
            unchanged_ranges.append({'offset':cursor,'bytes':start-cursor,
                                     'sha256':equal_range(a,b,cursor,start-cursor)})
            cursor = start+item['before']['bytes']
        size = CPIO.stat().st_size-cursor
        unchanged_ranges.append({'offset':cursor,'bytes':size,'sha256':equal_range(a,b,cursor,size)})
    assert sha_file(CPIO)==SOURCE_HASH
    manifest = {'status':'BUILT_VERIFIED_NOT_EXECUTED','scope':'FX6 bootin/im on otherwise fixed FX3 guest; not full FX6 upper system',
        'source_cpio':str(CPIO),'source_cpio_sha256':SOURCE_HASH,
        'candidate_cpio':str(OUTPUT),'candidate_cpio_sha256':sha_file(OUTPUT),
        'source_and_candidate_bytes':OUTPUT.stat().st_size,'members':len(old),'changed_members':changed,
        'all_other_bytes_equal':True,'unchanged_ranges':unchanged_ranges,
        'frozen_platform':frozen['platform_parameters'],'fixed_artifacts':frozen['sha256'],
        'model_env':frozen['model_env'],'dtb_change_required':False,'init_change_required':False,
        'fx3_appFw_preserved':new['usr/lib/appFw.so'],'fx3_libObj_preserved':new['usr/lib/libObj.so'],
        'qemu_started':False,'camera_accessed':False,'default_entry_changed':False,
        'runtime_gates':['Use sole runtime owner after prior run reaped and both locks available',
            'Validate exact two-entry allowlist; old all-original-ELF gate will correctly flag these deliberate replacements',
            'Keep original DTB byte-for-byte; no initrd-end metadata adjustment needed',
            'Preserve original /init and helpers, report loader verify/list/BusyBox return codes separately',
            'No explicit FX6 AV/CP payload; retain FX3 appFw/libObj/Backup and all other members',
            'Stop at first genuine failure or after minimum entry evidence; no success fallback',
            'Fresh host logs/sockets only; never write to source-run paths in frozen command',
            'This manifest is not an executable launch command or runtime success receipt']}
    (HERE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':manifest['status'],'changed_members':[x['name'] for x in changed],
                      'bytes':manifest['source_and_candidate_bytes'],'candidate_sha256':manifest['candidate_cpio_sha256'],
                      'all_other_bytes_equal':True,'dtb_change_required':False},indent=2))

if __name__=='__main__':
    main()
