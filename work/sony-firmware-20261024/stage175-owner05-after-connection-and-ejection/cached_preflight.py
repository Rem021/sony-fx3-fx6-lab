"""One host cache/mount observation; no USB user client, root, or card IO."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
import plistlib
import re
import secrets
import subprocess
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
SOURCE=BASE/'stage173-Terminal-owner-launch-and-login-guard'
sys.path.insert(0,str(SOURCE))
import cache_observer as Cache

def main():
    output=HERE/'cached-preflight-result.json'
    if output.exists():raise ValueError('existing cache receipt retained; do not repeat')
    volume=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    if volume['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise ValueError('wrong volume')
    goal=json.loads((BASE/'GOAL_STATUS.json').read_text());a=goal['authorization']
    if a.get('Mac_cached_USB_metadata_authorized') is not True or a.get('Mac_owner_trial_grant_id')!='fx3-702-msc-owner-20261029-05':
        raise ValueError('cached preflight lacks current authority')
    bundle=(SOURCE/'release-bundle.json').read_bytes()
    if sha256(bundle).hexdigest()!='05f682bdfa825359d543a8c6f7f23028ccf00c01f9382520066898197b5ee125':
        raise ValueError('fixed source bundle differs')
    for m in json.loads(bundle)['files']:
        if sha256((SOURCE/m['path']).read_bytes()).hexdigest()!=m['sha256']:raise ValueError('fixed source member differs')
    raw=subprocess.run(['/usr/sbin/ioreg','-a','-r','-c','IOUSBHostDevice','-l','-w','0'],capture_output=True,check=True,timeout=15).stdout
    cached=Cache.sanitize(raw,Cache.TARGET,secrets.token_bytes(32))
    tree=plistlib.loads(raw);tree=tree if isinstance(tree,list) else [tree]
    target_media=[]
    def media(nodes):
        for node in nodes:
            if node.get('IOObjectClass')=='IOMedia':
                name=node.get('BSD Name')
                if type(name) is not str or not re.fullmatch(r'disk[0-9]+(?:s[0-9]+)*',name):
                    raise ValueError('target media identity unavailable')
                target_media.append({'BSD_Name':name,'whole':node.get('Whole'),'size':node.get('Size')})
            media(node.get('IORegistryEntryChildren',[]))
    def walk(nodes):
        for node in nodes:
            if node.get('IOObjectClass')=='IOUSBHostDevice' and (node.get('idVendor'),node.get('idProduct'),node.get('locationID'))==(1356,3489,34603008):
                media(node.get('IORegistryEntryChildren',[]))
            walk(node.get('IORegistryEntryChildren',[]))
    walk(tree)
    names={m['BSD_Name'] for m in target_media};mounted=[]
    mounts=subprocess.run(['/sbin/mount'],capture_output=True,text=True,check=True,timeout=15).stdout
    for line in mounts.splitlines():
        match=re.fullmatch(r'/dev/(disk[0-9]+(?:s[0-9]+)*) on (.+) \([^\n]*\)',line)
        if match and match[1] in names:mounted.append({'device':match[1],'mount_point':match[2]})
    processes=subprocess.run(['/bin/ps','-axo','pid=,comm='],capture_output=True,text=True,check=True,timeout=15).stdout
    existing=[]
    for line in processes.splitlines():
        pieces=line.strip().split(None,1)
        if len(pieces)==2 and (pieces[1].startswith('/private/var/root/fx3-owner-trials/') or pieces[1].startswith('/private/tmp/fx3-702-msc-owner-')):
            existing.append({'pid':int(pieces[0]),'executable':pieces[1]})
    absent=not os.path.lexists(SOURCE/'physical-grant-attempt.claim') and not os.path.lexists('/private/tmp/fx3-702-msc-owner-20261029-05')
    selected=cached['selected'][0] if cached['selected_count']==1 else {}
    passed=cached['selected_count']==1 and selected.get('cached_identity_usable') and selected.get('MSC_interface0_observed') and any('MassStorage' in c for c in selected.get('storage_driver_classes',[])) and not mounted and not existing and absent
    receipt={'created_utc':datetime.now(timezone.utc).isoformat(),'volume_uuid':volume['VolumeUUID'],'fixed_bundle_sha256':sha256(bundle).hexdigest(),'cached_identity':cached,'target_media':target_media,'target_mounted_volumes':mounted,'existing_owner_processes':existing,'new_claim_and_job_absent':absent,'single_attempt_release_preconditions_met':bool(passed),'active_USB_operations':0,'raw_tree_serial_privacy_key_or_unrelated_mount_process_data_saved':False}
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps({'selected_count':cached['selected_count'],'target_media':target_media,'target_mounted_volumes':mounted,'existing_owner_processes':existing,'new_claim_and_job_absent':absent,'single_attempt_release_preconditions_met':bool(passed),'active_USB_operations':0},ensure_ascii=False))

if __name__=='__main__':main()
