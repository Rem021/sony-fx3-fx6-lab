#!/usr/bin/env python3
"""Test descriptor ABI/policy with own libSystem-only fixture DSOs, never real libusb."""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import importlib.util
import json
import os
import subprocess
import unittest.mock as mock

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'work/libusb-1.0.30'


def main():
    spec=importlib.util.spec_from_file_location('local_descriptor_transport',HERE/'descriptor_transport.py')
    t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
    build=json.loads((HERE/'native-build-receipt.json').read_text())
    assert t.layout()==build['probe_header_layout']
    env=dict(os.environ);env['TMPDIR']=str(HERE/'work-tmp')
    fixture=HERE/'artifacts/fake-libusb.dylib'
    command=['/usr/bin/clang','-dynamiclib','-std=c11','-Wall','-Wextra','-Werror',
             '-I'+str(SOURCE/'libusb'),str(HERE/'fake_libusb.c'),'-o',str(fixture)]
    subprocess.run(command,env=env,check=True,capture_output=True,timeout=60)
    deps=subprocess.check_output(['/usr/bin/otool','-L',str(fixture)],text=True)
    assert all('IOKit' not in line and '/libusb' not in line for line in deps.splitlines()[1:])
    lib=C.CDLL(str(fixture));lib.fixture_reset.argtypes=[C.c_int];lib.fixture_reset.restype=None
    lib.fixture_count.argtypes=[C.c_int];lib.fixture_count.restype=C.c_int
    abi=t.Bindings(lib);results=[]
    for scenario in range(33):
        lib.fixture_reset(scenario);success=False;error=None
        try:
            report=t.query_descriptors(abi,0x12340000,0x0336 if scenario==25 else 0x0da1)
            success=True
        except t.TransportError as exc:error=str(exc)
        assert success==(scenario in (0,25)),(scenario,success,error)
        counts=[lib.fixture_count(n) for n in range(8)]
        if scenario==20:assert counts[1]==0
        elif scenario in (18,19):assert counts[7]==0
        else:assert counts[7]==1
        if scenario in (2,3,27):assert counts[3]==0
        if scenario==32:assert counts[5]==0
        if scenario in (0,25):
            assert counts[5:]==[1,1,1]
            assert not report['device_or_interface_open_claim_driver_change_vendor_auth_or_media_operation']
            assert not report['authentication_or_service_endpoint_roles_proven']
        results.append({'scenario':scenario,'accepted':success,'error':error,'ABI_call_counts':counts,
                        'report':report if success else None})
    gate_results=[]
    with mock.patch.object(C,'CDLL',side_effect=AssertionError('real library loader must not be reached')):
        try:t.load_live(0x12340000)
        except t.TransportError:gate_results.append('current authority rejects before CDLL')
        else:raise AssertionError('current cache-only authority admitted native descriptor probe')
        fake_goal={'authorization':{'Mac_active_USB_descriptor_read_authorized':True,
                    'Mac_active_USB_descriptor_target':{'locationID':0x12340000,'VID':0x054c,'PID':0x0da1}},
                   'prepared_first_device_trial':{'Mac_descriptor_probe_released':True}}
        with mock.patch.object(Path,'read_text',return_value=json.dumps(fake_goal)):
            try:t.load_live(0x56780000)
            except t.TransportError:gate_results.append('mismatched location rejected before CDLL')
            else:raise AssertionError('target scope ignored')

    # Compile the EXACT private predicate/cache functions with a CPU-only IOKit shim.
    raw=(SOURCE/'libusb/os/darwin_usb.c').read_text()
    patch=json.loads((HERE/'private-source-patch.json').read_text())
    assert sha256(raw.encode()).hexdigest()==patch['patched_sha256']
    start=raw.index('static enum libusb_error darwin_cache_device_descriptor (')
    end=raw.index('/* Returns 1 on success, 0 on failure. */\nstatic bool get_device_port',start)
    cache=raw[start:end]
    start=raw.index('static UInt32 fx3_selected_location = 0;')
    end=raw.index('static enum libusb_error darwin_get_cached_device(',start)
    predicate=raw[start:end]
    cached_start=raw.index('static enum libusb_error darwin_get_cached_device(struct libusb_context *ctx, io_service_t service, struct darwin_cached_device **cached_out,\n                                                  UInt64 *old_session_id) {')
    client_call=raw.index('darwin_device_from_service',cached_start)
    guard=raw.index('if (!fx3_service_matches(service))',cached_start)
    assert guard<client_call
    assert not any(x in cache for x in ['USBDeviceOpenSeize','SetConfiguration','USBDeviceSuspend','nanosleep'])
    preamble=r'''
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include "libusb.h"
typedef uint32_t UInt32; typedef int IOReturn; typedef int io_service_t;
#define API_EXPORTED
#define UNUSED(x) (void)(x)
#define CFSTR(x) x
#define kCFNumberSInt32Type 0
#define kIOReturnSuccess 0
#define kIOReturnOverrun 1
#define kUSBDeviceDesc 1
static int init_count, requests, response_status;
static UInt32 loc,vid,pid;
struct darwin_cached_device {int can_enumerate; void *device; struct libusb_device_descriptor dev_descriptor;};
static bool get_ioregistry_value_number(io_service_t s,const char *key,int type,UInt32 *out) {
 (void)s;(void)type;*out=!strcmp(key,"locationID")?loc:!strcmp(key,"idVendor")?vid:pid;return true;
}
static enum libusb_error darwin_to_libusb(IOReturn r){(void)r;return LIBUSB_ERROR_IO;}
static IOReturn darwin_request_descriptor(void *d,int type,int index,void *out,size_t n){
 (void)d;(void)type;(void)index;requests++;memset(out,0,n);struct libusb_device_descriptor *p=out;
 p->bLength=18;p->bDescriptorType=1;p->idVendor=vid;p->idProduct=pid;p->bcdUSB=0x300;p->bNumConfigurations=1;
 return response_status;
}
'''.replace('\\"','"')
    suffix=r'''
int fixture_policy(int scenario);
int fixture_requests(void);
int fixture_policy(int scenario){
 struct darwin_cached_device dev={0};requests=0;init_count=0;fx3_selected_location=0;
 loc=0x12340000;vid=0x054c;pid=0x0da1;response_status=0;
 if(scenario==0)return fx3_service_matches(1)?99:0;
 if(libusb_fx3_set_target(loc)!=0)return 98;
 if(scenario==1)loc++;if(scenario==2)vid=0x1234;if(scenario==3)pid=0x1111;
 if(scenario==5)pid=0x0336;if(scenario==6)response_status=2;
 if(scenario==7){init_count=1;return libusb_fx3_set_target(0x23450000);}
 if(scenario==8)return libusb_fx3_set_target(0);
 if(scenario==9)response_status=kIOReturnOverrun;
 if(!fx3_service_matches(1))return LIBUSB_ERROR_NOT_FOUND;
 return darwin_cache_device_descriptor(0,&dev);
}
int fixture_requests(void){return requests;}
'''
    harness=HERE/'work/private-policy-harness.c';harness.write_text(preamble+cache+predicate+suffix)
    policy=HERE/'artifacts/private-policy-fixture.dylib'
    subprocess.run(['/usr/bin/clang','-dynamiclib','-std=c11','-Wall','-Wextra','-Werror','-I'+str(SOURCE/'libusb'),str(harness),'-o',str(policy)],env=env,check=True,capture_output=True,timeout=60)
    module=C.CDLL(str(policy));module.fixture_policy.argtypes=[C.c_int];module.fixture_policy.restype=C.c_int
    module.fixture_requests.restype=C.c_int
    policy_cases=[]
    expected=[0,-5,-5,-5,0,0,-1,-6,-2,0]
    for n,want in enumerate(expected):
        got=module.fixture_policy(n);reads=module.fixture_requests()
        assert got==want,(n,got,want)
        assert reads==(1 if n in (4,5,6,9) else 0),(n,reads)
        policy_cases.append({'scenario':n,'return':got,'standard_descriptor_read_calls':reads})
    out=HERE/'run-transport-tests';out.mkdir(exist_ok=False)
    for name,p in [('transport-executed.py',HERE/'descriptor_transport.py'),('test-executed.py',Path(__file__))]:
        (out/name).write_bytes(p.read_bytes())
    result={'status':'PASS_MAC_DESCRIPTOR_ABI_AND_PRIVATE_POLICY_FIXTURES_NOT_REAL_USB_INITIALIZATION',
        'transport_sha256':sha256((HERE/'descriptor_transport.py').read_bytes()).hexdigest(),
        'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'C_ctypes_layout':t.layout(),
        'descriptor_scenarios':results,'descriptor_scenario_count':33,'gate_cases':gate_results,
        'private_source_policy_cases':policy_cases,'exact_cache_and_predicate_functions_compiled_with_mock_IOKit':True,
        'guard_precedes_native_device_user_client_creation':True,'fixture_dependencies':deps,
        'real_private_libusb_loaded_or_initialized':False,'camera_or_driver_operations':0,
        'goal_complete':False,'persistent_write_release':False}
    with (out/'results.json').open('x') as h:json.dump(result,h,ensure_ascii=False,indent=2);h.write('\n')
    print(json.dumps({'status':result['status'],'descriptor_cases':33,'gate_cases':2,'policy_cases':10,'real_USB_operations':0}))


if __name__=='__main__':main()
