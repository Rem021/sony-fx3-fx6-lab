#!/usr/bin/env python3
"""Sanitized Mac IORegistry cache inventory; no camera/interface/file protocols.

Live cache query is explicit, never used by --self-test. Raw source stays in
memory. Permission for this Mac cache step must be obtained before agent use.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,plistlib,stat,subprocess
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent
MAX_BYTES=8*1024*1024
INT_FIELDS=('idVendor','idProduct','bDeviceClass','bDeviceSubClass','bDeviceProtocol',
    'bInterfaceClass','bInterfaceSubClass','bInterfaceProtocol','bInterfaceNumber')
TEXT_FIELDS=('USB Product Name','USB Vendor Name','IOObjectClass')
def sanitize(raw):
    if len(raw)>MAX_BYTES:raise ValueError('cache_snapshot_too_large')
    try:roots=plistlib.loads(raw)
    except Exception:raise ValueError('invalid_cache_plist') from None
    if isinstance(roots,dict):roots=[roots]
    if not isinstance(roots,list):raise ValueError('invalid_cache_root')
    candidates=[];visited=0
    def node_fields(node,path):
        result={'tree_index_path':path}
        for key in INT_FIELDS:
            val=node.get(key)
            if type(val) is int and 0<=val<=0xffff:result[key]=val
        for key in TEXT_FIELDS:
            val=node.get(key)
            if isinstance(val,str):result[key]=val[:120]
        return result
    def walk(nodes,path,owner=None,depth=0):
        nonlocal visited
        if depth>64:raise ValueError('cache_depth_limit')
        if not isinstance(nodes,list):raise ValueError('invalid_children')
        for i,n in enumerate(nodes):
            visited+=1
            if visited>10000:raise ValueError('cache_node_limit')
            if not isinstance(n,dict):raise ValueError('invalid_cache_node')
            here=path+[i];current=owner
            if type(n.get('idVendor')) is int and n['idVendor']==0x054c:
                current={'device':node_fields(n,here),'descendants':[],
                    'camera_identity_firmware_version_or_interface_access_proven':False}
                candidates.append(current)
            elif current is not None:current['descendants'].append(node_fields(n,here))
            walk(n.get('IORegistryEntryChildren',[]),here,current,depth+1)
    walk(roots,[])
    return {'sony_registry_candidates':candidates,'candidate_count':len(candidates),
        'only_whitelisted_fields_serial_numbers_and_raw_source_not_saved':True,
        'USB_interfaces_opened_camera_commands_or_media_reads':False,
        'identity_version_authorization_and_active_connection_health_proven':False}
def read_regular(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size>MAX_BYTES:raise ValueError('bounded_regular_plist_required')
        raw=b''
        while len(raw)<st.st_size:
            part=os.read(fd,st.st_size-len(raw))
            if not part:raise ValueError('short_cache_read')
            raw+=part
        if os.fstat(fd).st_size!=st.st_size:raise ValueError('cache_file_changed')
        return raw
    finally:os.close(fd)
def volume():
    result=subprocess.run(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T'],capture_output=True,check=True,timeout=15)
    v=plistlib.loads(result.stdout)
    if v['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' or not v['Writable']:raise ValueError('wrong_or_unwritable_volume')
def self_test():
    secret='TEST_PRIVATE_SERIAL_MUST_NOT_APPEAR'
    fixture=[{'idVendor':0x05ac,'USB Product Name':'Other device','USB Serial Number':secret,
        'IORegistryEntryChildren':[{'idVendor':0x054c,'idProduct':0x1234,'USB Product Name':'ILME-FX3',
            'USB Serial Number':secret,'IORegistryEntryID':123456789,'Extra Private Property':secret,
            'IORegistryEntryChildren':[{'bInterfaceClass':8,'bInterfaceSubClass':6,'bInterfaceProtocol':80,
                'bInterfaceNumber':0,'IOUSBSerialNumberString':secret}]}]}]
    r=sanitize(plistlib.dumps(fixture));text=json.dumps(r)
    assert r['candidate_count']==1 and secret not in text and 'Other device' not in text and '123456789' not in text
    c=r['sony_registry_candidates'][0];assert c['device']['tree_index_path']==[0,0]
    assert c['descendants'][0]['tree_index_path']==[0,0,0] and c['descendants'][0]['bInterfaceClass']==8
    assert not r['identity_version_authorization_and_active_connection_health_proven']
    none=sanitize(plistlib.dumps([{'idVendor':0x05ac,'USB Serial Number':secret}]))
    assert none['candidate_count']==0
    rejections=[]
    for name,raw in [('malformed',b'not plist'),('wrong_root',plistlib.dumps('text')),
            ('wrong_child_shape',plistlib.dumps([{'IORegistryEntryChildren':'bad'}]))]:
        try:sanitize(raw)
        except ValueError as ex:rejections.append({'case':name,'error':str(ex)})
        else:raise AssertionError('invalid cache input accepted')
    return {'status':'PASS_OFFLINE_CACHE_SANITIZATION_AND_PARENT_CHILD_SCOPE',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'checks':['Sony VID filter','serial and private properties omitted','parent/child index paths preserved',
            'interface class retained','empty result supported','malformed/root/child shapes rejected'],
        'rejections':rejections,'ioreg_diskutil_camera_or_other_host_query_executed_by_self_test':False,
        'live_device_acceptance':False}
def main():
    a=argparse.ArgumentParser();g=a.add_mutually_exclusive_group(required=True)
    g.add_argument('--self-test',action='store_true');g.add_argument('--input-plist',type=Path);g.add_argument('--query-mac-cache',action='store_true')
    a.add_argument('--out',type=Path);v=a.parse_args()
    if v.self_test:print(json.dumps(self_test(),ensure_ascii=False,indent=2));return
    if v.out is None:a.error('--out required for a cache receipt')
    if not v.out.resolve().is_relative_to(BASE.resolve()):a.error('output must remain within existing firmware task')
    if v.query_mac_cache:
        # This is the only live inventory path. No libusb, diskutil mount,
        # disk/media handle, network, camera authentication or vendor command.
        command=['/usr/sbin/ioreg','-a','-p','IOUSB','-l','-w','0']
        try:result=subprocess.run(command,capture_output=True,check=True,timeout=15)
        except Exception:raise SystemExit('IORegistry cache query failed; raw output not saved') from None
        raw=result.stdout;source='explicit_mac_IORegistry_cache_query'
    else:raw=read_regular(v.input_plist);source='provided_offline_cache_plist'
    report=sanitize(raw);report.update({'source':source,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'collector_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'raw_source_saved':False})
    volume();v.out.mkdir()
    with (v.out/'sanitized-cache-receipt.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'candidate_count':report['candidate_count'],'receipt':str(v.out/'sanitized-cache-receipt.json'),
        'camera_interface_access':False},ensure_ascii=False))
if __name__=='__main__':main()
