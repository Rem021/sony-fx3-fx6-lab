#!/usr/bin/env python3
"""Post-trial IORegistry cache only. Do not import any USB transport library."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json
import plistlib
import subprocess

HERE=Path(__file__).resolve().parent


def sanitize(raw,target):
    if len(raw)>8*1024*1024:raise ValueError('cache tree too large')
    tree=plistlib.loads(raw)
    roots=tree if isinstance(tree,list) else [tree]
    selected=[];visited=0
    def walk(nodes,depth=0):
        nonlocal visited
        if not isinstance(nodes,list) or depth>64:raise ValueError('invalid cache tree')
        for node in nodes:
            visited+=1
            if visited>10000 or not isinstance(node,dict):raise ValueError('invalid cache node')
            if node.get('IOObjectClass')=='IOUSBHostDevice' and (node.get('idVendor'),node.get('idProduct'),node.get('locationID'))==\
               (target['VID'],target['PID'],target['locationID']):
                rows=[];classes=set()
                def children(items,d=0):
                    if d>64 or not isinstance(items,list):raise ValueError('invalid child tree')
                    for child in items:
                        if not isinstance(child,dict):raise ValueError('invalid child')
                        row={k:child[k] for k in ('bInterfaceNumber','bInterfaceClass','bInterfaceSubClass','bInterfaceProtocol')
                             if type(child.get(k)) is int and 0<=child[k]<=255}
                        if row:rows.append(row)
                        label=child.get('IOObjectClass',child.get('IOClass',''))
                        if isinstance(label,str) and len(label)<=100 and any(x in label for x in ('MassStorage','SCSI','StorageDriver')):
                            classes.add(label)
                        children(child.get('IORegistryEntryChildren',[]),d+1)
                children(node.get('IORegistryEntryChildren',[]))
                selected.append({'VID':target['VID'],'PID':target['PID'],'locationID':target['locationID'],
                                 'interfaces':rows,'storage_driver_classes':sorted(classes)})
            walk(node.get('IORegistryEntryChildren',[]),depth+1)
    walk(roots)
    return {'selected_count':len(selected),'selected':selected,'raw_tree_or_serial_saved':False,
            'source_is_IORegistry_cache_not_active_USB':True,'physical_health_or_same_body_proven':False}


def main():
    permission=json.loads((HERE/'explicit-permission-and-preflight.json').read_text());target=permission['target']
    fixture=[dict(idVendor=target['VID'],idProduct=target['PID'],locationID=target['locationID'],IOObjectClass='IOUSBHostDevice',
                  **{'USB Serial Number':'DO_NOT_SAVE_THIS','IORegistryEntryChildren':[
                      {'bInterfaceNumber':0,'bInterfaceClass':8,'IOObjectClass':'AppleUSBMassStorageInterfaceNub',
                       'IORegistryEntryChildren':[{'IOClass':'IOSCSIPeripheralDeviceNub'}]}]})]
    test=sanitize(plistlib.dumps(fixture),target)
    assert test['selected_count']==1 and 'DO_NOT_SAVE_THIS' not in json.dumps(test)
    assert sanitize(plistlib.dumps([]),target)['selected_count']==0
    assert sanitize(plistlib.dumps(fixture+fixture),target)['selected_count']==2
    nested=dict(fixture[0]);nested['IOObjectClass']='IOUSBMassStorageDriver'
    nested['IORegistryEntryChildren']=[]
    fixture[0]['IORegistryEntryChildren'].append(nested)
    assert sanitize(plistlib.dumps(fixture),target)['selected_count']==1
    raw=subprocess.run(['/usr/sbin/ioreg','-a','-r','-c','IOUSBHostDevice','-l','-w','0'],
                       check=True,capture_output=True,timeout=15).stdout
    result=sanitize(raw,target)
    result.update({'created_utc':datetime.now(timezone.utc).isoformat(),'offline_sanitization_cases':4,
                   'collector_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
                   'no_USB_library_loaded_or_camera_protocol_called':True})
    with (HERE/'post-trial-cache-reviewed.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
