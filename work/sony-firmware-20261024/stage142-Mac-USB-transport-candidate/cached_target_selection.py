#!/usr/bin/env python3
"""Read only already-authorized IORegistry USB cache; no libusb imports or USB API."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json
import plistlib
import subprocess

HERE=Path(__file__).resolve().parent


def sanitize(raw):
    if len(raw)>8*1024*1024:raise ValueError('cache too large')
    roots=plistlib.loads(raw)
    if isinstance(roots,dict):roots=[roots]
    if not isinstance(roots,list):raise ValueError('invalid cache roots')
    candidates=[];visited=0
    def walk(nodes,depth=0):
        nonlocal visited
        if not isinstance(nodes,list) or depth>64:raise ValueError('invalid cache tree')
        for node in nodes:
            visited+=1
            if visited>10000 or not isinstance(node,dict):raise ValueError('invalid cache node count/shape')
            if node.get('idVendor')==0x054c and node.get('idProduct')==0x0da1 and 'bInterfaceNumber' not in node:
                location=node.get('locationID')
                location=location if type(location) is int and 0<location<=0xffffffff else None
                interfaces=[]
                def interface_fields(children):
                    for child in children:
                        if not isinstance(child,dict):raise ValueError('invalid child')
                        row={k:child[k] for k in ('bInterfaceNumber','bInterfaceClass','bInterfaceSubClass','bInterfaceProtocol',
                             'bEndpointAddress','wMaxPacketSize','bmAttributes') if type(child.get(k)) is int and 0<=child[k]<=0xffff}
                        if row:interfaces.append(row)
                        descendants=child.get('IORegistryEntryChildren',[])
                        if not isinstance(descendants,list):raise ValueError('invalid descendants')
                        interface_fields(descendants)
                interface_fields(node.get('IORegistryEntryChildren',[]))
                props=[{'name':k,'bytes':len(value),'sha256':sha256(value).hexdigest()} for k,value in node.items()
                       if isinstance(k,str) and 'descriptor' in k.lower() and isinstance(value,bytes) and len(value)<=65535]
                candidates.append({'VID':0x054c,'PID':0x0da1,'locationID':location,
                    'product_name':str(node.get('USB Product Name',''))[:120],
                    'interfaces_and_endpoint_cache':interfaces,'cached_binary_descriptor_properties':props})
            walk(node.get('IORegistryEntryChildren',[]),depth+1)
    walk(roots)
    selector=candidates[0]['locationID'] if len(candidates)==1 else None
    return {'candidate_count':len(candidates),'candidates':candidates,'unique_target_location':selector,
        'raw_tree_or_serial_saved':False,'USB_interface_or_camera_protocol_access':False,
        'active_connection_firmware_version_or_same_body_binding_proven':False}


def main():
    secret='PRIVATE_TEST_SERIAL_MUST_NOT_APPEAR'
    fake=[{'idVendor':0x054c,'idProduct':0x0da1,'locationID':0x12340000,'USB Product Name':'ILME-FX3',
           'USB Serial Number':secret,'IORegistryEntryChildren':[{'bInterfaceNumber':0,'bInterfaceClass':8,
           'bInterfaceSubClass':6,'bInterfaceProtocol':80,'Secret':secret}]}]
    test=sanitize(plistlib.dumps(fake));assert test['unique_target_location']==0x12340000 and secret not in json.dumps(test)
    assert sanitize(plistlib.dumps(fake+fake))['unique_target_location'] is None
    assert sanitize(plistlib.dumps([]))['candidate_count']==0
    cmd=['/usr/sbin/ioreg','-a','-p','IOUSB','-l','-w','0']
    data=subprocess.run(cmd,capture_output=True,check=True,timeout=15).stdout
    report=sanitize(data)
    report.update({'created_utc':datetime.now(timezone.utc).isoformat(),
        'source':'already_authorized_Mac_IORegistry_USB_cache','collector_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'cache_source_raw_saved':False,'offline_sanitization_cases':3,'real_libusb_initialized':False})
    v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and v['WritableVolume']
    with (HERE/'current-cache-target.json').open('x') as h:json.dump(report,h,ensure_ascii=False,indent=2);h.write('\n')
    print(json.dumps({'cache_candidate_count':report['candidate_count'],'unique_location_available':report['unique_target_location'] is not None,
                      'interfaces':[x['interfaces_and_endpoint_cache'] for x in report['candidates']],
                      'binary_descriptor_cache_counts':[len(x['cached_binary_descriptor_properties']) for x in report['candidates']],
                      'camera_or_USB_interface_access':False}))


if __name__=='__main__':main()
