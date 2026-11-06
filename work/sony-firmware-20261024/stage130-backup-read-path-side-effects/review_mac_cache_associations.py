#!/usr/bin/env python3
"""Normalize inherited Sony properties in saved cache; no new host/device query."""
from pathlib import Path
import datetime,hashlib,json
STAGE=Path(__file__).resolve().parent
def main():
    a=STAGE/'mac-cache-20261027T183151Z/sanitized-cache-receipt.json'
    b=STAGE/'mac-service-cache-20261027T1834Z/sanitized-service-cache-receipt.json'
    usb=json.loads(a.read_text());service=json.loads(b.read_text());nodes={}
    assert usb['candidate_count']==1 and service['candidate_count']==4
    for c in service['sony_registry_candidates']:
        for n in [c['device']]+c['descendants']:
            key=tuple(n['tree_index_path'])
            if key in nodes:assert nodes[key]==n
            nodes[key]=n
    devices=[n for n in nodes.values() if n.get('IOObjectClass')=='IOUSBHostDevice' and n.get('idVendor')==0x054c]
    assert len(devices)==1;dev=devices[0];root=tuple(dev['tree_index_path'])
    children=[n for k,n in nodes.items() if len(k)>len(root) and k[:len(root)]==root]
    interfaces=[n for n in children if n.get('IOObjectClass')=='IOUSBHostInterface']
    assert len(interfaces)==1;iface=interfaces[0]
    assert [iface.get(k) for k in ('bInterfaceNumber','bInterfaceClass','bInterfaceSubClass','bInterfaceProtocol')]==[0,8,6,0x50]
    assert dev['idProduct']==0x0da1 and dev['USB Product Name']=='ILME-FX3'
    udev=usb['sony_registry_candidates'][0]['device']
    assert all(dev[k]==udev[k] for k in ('idVendor','idProduct','USB Product Name','USB Vendor Name'))
    classes=sorted({n['IOObjectClass'] for n in children if 'IOObjectClass' in n})
    assert 'IOUSBMassStorageDriver' in classes and 'IOUSBMassStorageInterfaceNub' in classes
    assert all(not j['raw_source_saved'] and not j['USB_interfaces_opened_camera_commands_or_media_reads'] for j in (usb,service))
    j={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Only normalize saved sanitized cache, no I/O queries',
        'source_files':[{'path':str(p.relative_to(STAGE)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (a,b)],
        'raw_Sony_identifier_records_in_service_cache':4,'physical_USB_device_roots_in_cache':1,
        'count4_is_inherited_properties_not_four_cameras':True,'device':dev,'interface':iface,'cached_descendant_classes':classes,
        'VID_hex':'054C','PID_hex':'0DA1','interface_class_subclass_protocol_hex':['08','06','50'],
        'interface_interpretation':'Mass Storage / SCSI transparent / Bulk-Only',
        'same_identifiers_as_historical_Windows_cache':True,
        'device_firmware_hash_health_backup_authentication_or_rescue_proven':False,
        'camera_interface_or_media_files_accessed':False,'live_device_commands_sent':False}
    with (STAGE/'mac-cache-association-review.json').open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'device':dev['USB Product Name'],'VID':'054C','PID':'0DA1','physical_device_roots':1,
        'interface_number':0,'class_subclass_protocol':['08','06','50'],'driver_class':'IOUSBMassStorageDriver',
        'new_query_or_camera_file_access':False},ensure_ascii=False))
if __name__=='__main__':main()
