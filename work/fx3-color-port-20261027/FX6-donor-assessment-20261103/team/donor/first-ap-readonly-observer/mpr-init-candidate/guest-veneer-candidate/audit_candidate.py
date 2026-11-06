#!/usr/bin/env python3
"""Independent streaming newc comparison and fixed platform hash check; no VM."""
import hashlib
import json
import plistlib
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
MAC=HERE.parents[7]
OLD=HERE.parents[2]/'hybrid-ap-candidate/guest-three-entry.cpio'
NEW=HERE/'guest-veneer.cpio'
AP=HERE/'appFw-bridge.so'
BRIDGE=HERE/'libfx6diag.so'
OLD_PIN='bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02'
AP_PIN='c31bc293816db5d63cc5acf6b019bd69c9dd7b940ae0ece1ea6977ff9b944db1'
BASE=HERE.parents[2]/'hybrid-ap-candidate'

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def members(path):
    out=[];off=0
    with path.open('rb') as f:
        while True:
            f.seek(off);header=f.read(110)
            if len(header)!=110 or header[:6]!=b'070701':raise ValueError('newc header '+hex(off))
            fields=[int(header[6+i*8:14+i*8],16) for i in range(13)]
            size,namesize=fields[6],fields[11]
            if not 1<=namesize<=4096 or size>100000000:raise ValueError('member bounds')
            name=f.read(namesize)
            if not name.endswith(b'\0'):raise ValueError('name')
            head_end=(off+110+namesize+3)&~3
            f.seek(off+110+namesize)
            namepad=f.read(head_end-(off+110+namesize))
            if namepad.strip(b'\0'):raise ValueError('name padding')
            f.seek(head_end)
            h=hashlib.sha256();remaining=size
            while remaining:
                b=f.read(min(1<<20,remaining))
                if not b:raise ValueError('truncated payload')
                h.update(b);remaining-=len(b)
            end=(head_end+size+3)&~3
            datapad=f.read(end-(head_end+size))
            if datapad.strip(b'\0'):raise ValueError('data padding')
            row={'name':name[:-1].decode('ascii'),'header':header.hex(),
                 'headpad':namepad.hex(),'datapad':datapad.hex(),
                 'size':size,'payload_sha256':h.hexdigest(),
                 'header_start':off,'payload_start':head_end,'end':end}
            out.append(row)
            if name==b'TRAILER!!!\0':break
            off=end
        f.seek(end)
        while b:=f.read(1<<20):
            if b.strip(b'\0'):raise ValueError('nonzero trailing bytes')
    return out

def main():
    vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    if vol.get('VolumeUUID')!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise ValueError('volume UUID')
    if sha(OLD)!=OLD_PIN or sha(AP)!=AP_PIN:raise ValueError('fixed input drift')
    if NEW.stat().st_size!=453184500 or OLD.stat().st_size!=453184500:
        raise ValueError('initrd byte extent')
    old=members(OLD);new=members(NEW)
    bridge_name='usr/lib/libfx6diag.so';ap_name='usr/lib/appFw.so'
    old_names=[x['name'] for x in old];new_names=[x['name'] for x in new]
    ix=old_names.index(ap_name)
    if new_names!=old_names[:ix+1]+[bridge_name]+old_names[ix+1:]:raise ValueError('order/insertion')
    differences=[]
    j=0
    for a in old:
        if a['name']==bridge_name:raise ValueError('bridge pre-exists')
        if new[j]['name']==bridge_name:j+=1
        b=new[j];j+=1
        if a['name']!=b['name']:raise ValueError('name drift')
        keys=('header','headpad','datapad','size','payload_sha256')
        changed=[k for k in keys if a[k]!=b[k]]
        if changed:
            if a['name']!=ap_name or changed!=['payload_sha256']:
                raise ValueError('unallowlisted member/header/payload change '+a['name']+' '+repr(changed))
            if b['payload_sha256']!=AP_PIN:raise ValueError('patched AP SHA')
            differences.append({'name':a['name'],'changed_fields':changed,
                                'source_sha256':a['payload_sha256'],
                                'candidate_sha256':b['payload_sha256']})
    added=new[ix+1]
    if added['payload_sha256']!=sha(BRIDGE) or added['size']!=BRIDGE.stat().st_size:
        raise ValueError('bridge member drift')
    if len(old)!=1141 or len(new)!=1142 or len(differences)!=1:raise ValueError('member counts')
    original_ap=HERE.parents[2]/'nflasha15-files/lib/appFw.so'
    if sha(original_ap)!=differences[0]['source_sha256']:raise ValueError('original FX6 AP drift')
    patched=AP.read_bytes();original=original_ap.read_bytes()
    changed_offsets=[i for i,(a,b) in enumerate(zip(original,patched)) if a!=b]
    patch=json.loads((HERE/'ap-patch.json').read_text())
    allowed={i for r in patch['patched_ranges'] for i in range(r['offset'],r['offset']+r['length'])}
    if len(original)!=len(patched) or len(changed_offsets)!=75 or not set(changed_offsets)<=allowed:
        raise ValueError('AP patch outside three bounded ranges')
    # The source CPIO contains the unchanged FX3 kernel-facing init/17 helper members.
    fixed_platform=json.loads((BASE/'manifest.json').read_text())
    parent_receipt=json.loads((BASE/'receipt.json').read_text())
    result={'status':'STATIC_VERIFIED_NOT_RUN','source_sha256':OLD_PIN,
        'candidate_sha256':sha(NEW),'candidate_bytes':NEW.stat().st_size,
        'source_member_count':len(old)-1,'candidate_member_count':len(new)-1,
        'existing_changes':differences,'added_member':{'name':bridge_name,'sha256':sha(BRIDGE),
            'bytes':added['size'],'header':added['header']},
        'bridge_sha256':sha(BRIDGE),'ap_sha256':AP_PIN,
        'bootin_im_members_unchanged':all(next(x for x in old if x['name']==n)['payload_sha256']==
            next(x for x in new if x['name']==n)['payload_sha256'] for n in ('usr/bin/bootin.elf','usr/bin/im.elf')),
        'trailer_source_end':old[-1]['end'],'trailer_candidate_end':new[-1]['end'],
        'zero_tail_bytes':NEW.stat().st_size-new[-1]['end'],
        'frozen_manifest_sha256':sha(BASE/'manifest.json'),
        'frozen_parent_receipt_sha256':sha(BASE/'receipt.json'),
        'frozen_manifest_keys':sorted(fixed_platform),
        'frozen_parent_status':parent_receipt.get('status'),
        'builder_platform_paths_written':False,
        'ap_byte_differences':len(changed_offsets),
        'ap_difference_ranges':patch['patched_ranges'],
        'fx3_baseline_three_ELF_only_expected_identity_exceptions':[
            'usr/bin/bootin.elf','usr/bin/im.elf','usr/lib/appFw.so'],
        'bsdtar_listing':None}
    # bsdtar is an independent parser; compare its names, not merely exit status.
    tar=subprocess.run(['bsdtar','-tf',str(NEW)],capture_output=True,check=True,text=True)
    listed=[x.removeprefix('./') for x in tar.stdout.splitlines()]
    if listed!=new_names[:-1]:raise ValueError('bsdtar name/order mismatch')
    result['bsdtar_listing']={'count':len(listed),'same_order':True}
    (HERE/'static-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
