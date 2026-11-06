#!/usr/bin/env python3
"""Independent IORegistry-cache observer. No USB library or user client."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import argparse
import hmac
import json
import os
import plistlib
import secrets
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
TARGET={'VID':0x054c,'PID':0x0da1,'locationID':0x02100000,'model':'ILME-FX3'}


def sanitize(raw,target,key):
    if type(key) is not bytes or len(key)!=32:raise ValueError('per-job privacy key must be32 bytes')
    if len(raw)>8*1024*1024:raise ValueError('cached tree exceeds bound')
    tree=plistlib.loads(raw);roots=tree if isinstance(tree,list) else [tree]
    selected=[];count=0
    def walk(nodes,depth=0):
        nonlocal count
        if type(nodes) is not list or depth>64:raise ValueError('cached tree shape invalid')
        for node in nodes:
            count+=1
            if count>10000 or type(node) is not dict:raise ValueError('cached node bound/shape invalid')
            match=node.get('IOObjectClass')=='IOUSBHostDevice' and \
                (node.get('idVendor'),node.get('idProduct'),node.get('locationID'))==(target['VID'],target['PID'],target['locationID'])
            if match:
                product=node.get('USB Product Name');serial=node.get('USB Serial Number')
                encoded=serial.encode('utf-8') if type(serial) is str else b''
                usable=1<=len(encoded)<=255 and b'\0' not in encoded
                tag=hmac.new(key,encoded,'sha256').hexdigest() if usable else None
                rows=[];classes=set()
                def children(items,d=0):
                    if type(items) is not list or d>64:raise ValueError('child tree invalid')
                    for child in items:
                        if type(child) is not dict:raise ValueError('child shape invalid')
                        row={k:child[k] for k in ('bInterfaceNumber','bInterfaceClass','bInterfaceSubClass','bInterfaceProtocol')
                            if type(child.get(k)) is int and 0<=child[k]<=255}
                        if row and row not in rows:rows.append(row)
                        label=child.get('IOObjectClass',child.get('IOClass',''))
                        if type(label) is str and len(label)<=100 and any(s in label for s in ['MassStorage','SCSI','StorageDriver']):classes.add(label)
                        children(child.get('IORegistryEntryChildren',[]),d+1)
                children(node.get('IORegistryEntryChildren',[]))
                correct_interface=any(all(r.get(k)==v for k,v in {'bInterfaceNumber':0,'bInterfaceClass':8,'bInterfaceSubClass':6,'bInterfaceProtocol':80}.items()) for r in rows)
                selected.append({'VID':target['VID'],'PID':target['PID'],'locationID':target['locationID'],
                    'model_matches':product==target['model'],'body_tag':tag,'cached_identity_usable':usable and product==target['model'],
                    'MSC_interface0_observed':correct_interface,'interfaces':rows,'storage_driver_classes':sorted(classes)})
            walk(node.get('IORegistryEntryChildren',[]),depth+1)
    walk(roots)
    return {'selected_count':len(selected),'selected':selected,'cached_only':True,
        'raw_tree_serial_or_privacy_key_saved':False,'same_program_firmware_health_or_recording_proven':False}


def compare(before,after,native_before_tag,native_after_tag):
    reasons=[]
    if before.get('selected_count')!=1 or after.get('selected_count')!=1:reasons.append('missing_or_ambiguous_cached_target')
    if not reasons:
        b,a=before['selected'][0],after['selected'][0]
        if not b['cached_identity_usable'] or not a['cached_identity_usable']:reasons.append('cached_identity_unusable')
        if not b['MSC_interface0_observed'] or not a['MSC_interface0_observed']:reasons.append('MSC_interface_missing')
        if not b['body_tag'] or not (b['body_tag']==a['body_tag']==native_before_tag==native_after_tag):reasons.append('body_tags_differ_or_missing')
        if not any('MassStorage' in c for c in b['storage_driver_classes']):reasons.append('baseline_storage_driver_unconfirmed')
        if not set(b['storage_driver_classes']).issubset(set(a['storage_driver_classes'])):reasons.append('baseline_driver_classes_not_all_back')
        if (b['VID'],b['PID'],b['locationID'])!=(a['VID'],a['PID'],a['locationID']):reasons.append('port_or_identity_changed')
    return {'same_cached_body_and_driver_association_observed':not reasons,'reasons':reasons,
        'evidence_scope':'Independent cached association only; not functional IO, camera health, backup, recording or rescue',
        'actual_driver_IO_or_camera_acceptance':False}


def collect(target,key,goal):
    if goal['authorization'].get('Mac_cached_USB_metadata_authorized') is not True:raise ValueError('Mac cached USB query not authorized')
    # Timeout applies only to the cache-reading ioreg process. It never governs
    # an owner, capture, user client or native I/O worker.
    raw=subprocess.run(['/usr/sbin/ioreg','-a','-r','-c','IOUSBHostDevice','-l','-w','0'],
        capture_output=True,check=True,timeout=15).stdout
    result=sanitize(raw,target,key)
    result.update(created_utc=datetime.now(timezone.utc).isoformat(),collector_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        no_USB_library_or_camera_protocol_called=True)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--collect-cache',action='store_true');parser.add_argument('--output')
    args=parser.parse_args()
    if not args.collect_cache:
        print(json.dumps({'mode':'PLAN_ONLY','target':TARGET,'USB_user_client_or_active_IO':False}));return
    if not args.output:raise ValueError('new output path required')
    out=Path(args.output)
    if out.exists():raise ValueError('output exists; no cache query repeated')
    goal=json.loads((BASE/'GOAL_STATUS.json').read_text())
    key=secrets.token_bytes(32)
    result=collect(TARGET,key,goal)
    fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'selected_count':result['selected_count'],'cached_only':True,'saved':str(out),'active_camera_operations':0}))


if __name__=='__main__':main()
