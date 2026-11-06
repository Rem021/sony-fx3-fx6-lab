#!/usr/bin/env python3
from pathlib import Path
import copy
import json
import plistlib
import cache_observer as M

HERE=Path(__file__).resolve().parent


def main():
    key=bytes([0x71])*32
    node={'IOObjectClass':'IOUSBHostDevice','idVendor':0x054c,'idProduct':0x0da1,'locationID':0x02100000,
        'USB Product Name':'ILME-FX3','USB Serial Number':'FIXTURE-SERIAL-NEVER-SAVE',
        'IORegistryEntryChildren':[{'bInterfaceNumber':0,'bInterfaceClass':8,'bInterfaceSubClass':6,'bInterfaceProtocol':80,
            'IOObjectClass':'IOUSBMassStorageInterfaceNub','IORegistryEntryChildren':[{'IOObjectClass':'IOUSBMassStorageDriver'}]}]}
    def parse(n):return M.sanitize(plistlib.dumps(n),M.TARGET,key)
    before=parse([node]);tag=before['selected'][0]['body_tag'];checks=[]
    assert 'FIXTURE-SERIAL-NEVER-SAVE' not in json.dumps(before)
    checks.append('raw_serial_not_serialized')
    assert M.compare(before,before,tag,tag)['same_cached_body_and_driver_association_observed'];checks.append('matching_association')
    for name,nodes in [('missing',[]),('duplicate',[node,node])]:
        assert not M.compare(before,parse(nodes),tag,tag)['same_cached_body_and_driver_association_observed'];checks.append(name)
    for name,mutate in [
        ('serial_changed',lambda n:n.update({'USB Serial Number':'OTHER'})),
        ('serial_missing',lambda n:n.pop('USB Serial Number')),
        ('model_changed',lambda n:n.update({'USB Product Name':'OTHER'})),
        ('interface_changed',lambda n:n['IORegistryEntryChildren'][0].update({'bInterfaceClass':255})),
        ('driver_missing',lambda n:n.update({'IORegistryEntryChildren':[]}))]:
        other=copy.deepcopy(node);mutate(other)
        assert not M.compare(before,parse([other]),tag,tag)['same_cached_body_and_driver_association_observed'];checks.append(name)
    assert not M.compare(before,before,'00'*32,tag)['same_cached_body_and_driver_association_observed'];checks.append('native_tag_mismatch')
    for invalid in [b'',b'0'*31,b'0'*33]:
        try:M.sanitize(plistlib.dumps([node]),M.TARGET,invalid)
        except ValueError:checks.append('invalid_privacy_key_'+str(len(invalid)))
        else:raise AssertionError('invalid key accepted')
    nested=copy.deepcopy(node);nested['IOObjectClass']='IOUSBMassStorageDriver';nested['IORegistryEntryChildren']=[]
    modified=copy.deepcopy(node);modified['IORegistryEntryChildren'].append(nested)
    assert parse([modified])['selected_count']==1;checks.append('inherited_properties_not_second_device')
    with (HERE/'cache-observer-tests.json').open('x') as f:json.dump({'checks':checks,'count':len(checks),
        'real_cache_queried_by_test':False,'new_device_operations':0},f,indent=2)
    (HERE/'cache-test-executed.py').write_bytes(Path(__file__).read_bytes())
    (HERE/'cache-observer-tested.py').write_bytes((HERE/'cache_observer.py').read_bytes())
    print(json.dumps({'cache_fixture_checks':len(checks),'real_device_queries':0}))


if __name__=='__main__':main()
