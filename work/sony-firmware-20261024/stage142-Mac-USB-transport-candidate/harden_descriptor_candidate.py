#!/usr/bin/env python3
"""Narrow the private metadata build to MSC and one explicit descriptor request."""
from pathlib import Path
from hashlib import sha256
import json
import shutil

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'work/libusb-1.0.30/libusb/os/darwin_usb.c'


def main():
    patch=json.loads((HERE/'private-source-patch.json').read_text())
    raw=SOURCE.read_bytes()
    assert sha256(raw).hexdigest()==patch['patched_sha256']=='a11147e536e8ed86f052a096282b67d1c7605b4026c84f3beff8794ca5e3dd62'
    saved=HERE/'attempt-before-MSC-budget';saved.mkdir(exist_ok=False)
    for name in ('private-source-patch.json','native-build-receipt.json','descriptor_transport.py',
                 'test_descriptor_transport.py','build-step0.log','build-step1.log','build-step2.log'):
        shutil.copy2(HERE/name,saved/name)
    (saved/'darwin_usb.c').write_bytes(raw)
    for name in ('fake-libusb.dylib','private-policy-fixture.dylib'):
        shutil.copy2(HERE/'artifacts'/name,saved/name)
    (HERE/'work/native-build').rename(HERE/'work/native-build-before-budget')
    (HERE/'artifacts/private-libusb').rename(saved/'private-libusb')
    (HERE/'run-transport-tests').rename(HERE/'run-transport-tests-before-budget')
    for name in ('native-build-receipt.json','build-step0.log','build-step1.log','build-step2.log'):
        (HERE/name).unlink()  # Exact bytes preserved above; prepare exclusive new receipts.
    text=raw.decode()
    marker='static enum libusb_error darwin_cache_device_descriptor ('
    assert text.count(marker)==1
    text=text.replace(marker,'static atomic_int fx3_descriptor_budget_used = 0;\n'+marker,1)
    marker='  dev->can_enumerate = 0;\n  ret = darwin_request_descriptor'
    assert text.count(marker)==1
    text=text.replace(marker,'  dev->can_enumerate = 0;\n  if (atomic_exchange(&fx3_descriptor_budget_used, 1))\n    return LIBUSB_ERROR_ACCESS;\n  ret = darwin_request_descriptor',1)
    text=text.replace('dev->dev_descriptor.bNumConfigurations == 0 ||','dev->dev_descriptor.bNumConfigurations != 1 ||',1)
    marker='  fx3_selected_location = location;'
    text=text.replace(marker,'  atomic_store(&fx3_descriptor_budget_used, 0);\n'+marker,1)
    marker='return location == fx3_selected_location && vendor == 0x054c && (product == 0x0da1 || product == 0x0336);'
    assert text.count(marker)==1
    text=text.replace(marker,'return location == fx3_selected_location && vendor == 0x054c && product == 0x0da1;',1)
    marker='    if (ret < 0 || !cached_device->can_enumerate) {\n      continue;\n    }'
    assert text.count(marker)==2
    text=text.replace(marker,'    if (ret < 0 || !cached_device->can_enumerate) {\n      IOObjectRelease(service);\n      continue;\n    }')
    SOURCE.write_text(text)
    patch.update({'patched_sha256':sha256(text.encode()).hexdigest(),
        'previous_built_source_preserved_sha256':sha256(raw).hexdigest(),
        'fixed_PIDs':['0DA1'],'service_PID_0336_rejected_before_user_client':True,
        'explicit_device_descriptor_requests_per_initialized_process_at_most':1,
        'descriptor_error_consumes_budget_no_retry':True,
        'multiple_configurations_rejected_before_GetConfiguration':True,
        'two_rejected_service_IOObjects_released':True,
        'OS_configuration_metadata_API_wire_activity_not_counted_or_guaranteed':True})
    (HERE/'private-source-patch.json').write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'MSC_ONLY_AND_SINGLE_EXPLICIT_READ_SOURCE_READY_NOT_LOADED',
                      'patched_sha256':patch['patched_sha256'],'real_USB_operations':0}))


if __name__=='__main__':main()
