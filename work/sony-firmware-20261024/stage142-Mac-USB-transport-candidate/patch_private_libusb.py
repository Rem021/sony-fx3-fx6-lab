#!/usr/bin/env python3
"""Create a task-private fail-closed Darwin build; does not load or initialize libusb."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'work/libusb-1.0.30/libusb/os/darwin_usb.c'


def main():
    inputs=json.loads((HERE/'source-inputs.json').read_text())
    pin=next(x for x in inputs['source_files'] if x['path'].endswith('/libusb/os/darwin_usb.c'))
    raw=SOURCE.read_bytes();assert sha256(raw).hexdigest()==pin['sha256']
    (HERE/'darwin_usb-upstream.c').write_bytes(raw)
    text=raw.decode()
    begin=text.index('static enum libusb_error darwin_cache_device_descriptor (')
    end=text.index('/* Returns 1 on success, 0 on failure. */\nstatic bool get_device_port',begin)
    replacement='''/* FX3 private build: exactly one standard read; never open/seize, reset,
 * reconfigure, suspend/resume or retry while caching a descriptor. */
static enum libusb_error darwin_cache_device_descriptor (struct libusb_context *ctx, struct darwin_cached_device *dev) {
  IOReturn ret;
  UNUSED(ctx);
  dev->can_enumerate = 0;
  ret = darwin_request_descriptor(dev->device, kUSBDeviceDesc, 0,
                                  &dev->dev_descriptor, sizeof(dev->dev_descriptor));
  if (ret != kIOReturnSuccess && ret != kIOReturnOverrun)
    return darwin_to_libusb(ret);
  if (dev->dev_descriptor.bLength != sizeof(dev->dev_descriptor) ||
      dev->dev_descriptor.bDescriptorType != kUSBDeviceDesc ||
      dev->dev_descriptor.bNumConfigurations == 0 ||
      libusb_le16_to_cpu(dev->dev_descriptor.bcdUSB) == 0 ||
      libusb_le16_to_cpu(dev->dev_descriptor.idVendor) != 0x054c ||
      (libusb_le16_to_cpu(dev->dev_descriptor.idProduct) != 0x0da1 &&
       libusb_le16_to_cpu(dev->dev_descriptor.idProduct) != 0x0336))
    return LIBUSB_ERROR_NO_DEVICE;
  dev->can_enumerate = 1;
  return LIBUSB_SUCCESS;
}

'''
    text=text[:begin]+replacement+text[end:]
    marker='static enum libusb_error darwin_get_cached_device(struct libusb_context *ctx, io_service_t service, struct darwin_cached_device **cached_out,\n                                                  UInt64 *old_session_id) {'
    assert text.count(marker)==1
    addition='''/* FX3 private build: unset target means no USB user clients or requests.
 * Location selection is immutable while any context exists in this private DSO. */
static UInt32 fx3_selected_location = 0;
int API_EXPORTED libusb_fx3_set_target(uint32_t location) {
  if (init_count != 0) return LIBUSB_ERROR_BUSY;
  if (location == 0) return LIBUSB_ERROR_INVALID_PARAM;
  fx3_selected_location = location;
  return LIBUSB_SUCCESS;
}
static bool fx3_service_matches(io_service_t service) {
  UInt32 location = 0, vendor = 0, product = 0;
  if (fx3_selected_location == 0) return false;
  if (!get_ioregistry_value_number(service, CFSTR("locationID"), kCFNumberSInt32Type, &location) ||
      !get_ioregistry_value_number(service, CFSTR("idVendor"), kCFNumberSInt32Type, &vendor) ||
      !get_ioregistry_value_number(service, CFSTR("idProduct"), kCFNumberSInt32Type, &product)) return false;
  return location == fx3_selected_location && vendor == 0x054c && (product == 0x0da1 || product == 0x0336);
}

'''
    text=text.replace(marker,addition+marker,1)
    marker2='  *cached_out = NULL;\n\n  /* get some info from the io registry */'
    assert text.count(marker2)==1
    text=text.replace(marker2,'  *cached_out = NULL;\n\n  if (!fx3_service_matches(service)) return LIBUSB_ERROR_NOT_FOUND;\n\n  /* get some info from the io registry */',1)
    before,after=raw.decode()[begin:end],replacement
    assert 'USBDeviceOpenSeize' in before and 'SetConfiguration' in before and 'USBDeviceSuspend' in before
    assert not any(x in after for x in ('USBDeviceOpenSeize','SetConfiguration','USBDeviceSuspend','nanosleep'))
    SOURCE.write_text(text)
    result={'status':'PATCHED_PRIVATE_SOURCE_ONLY_NOT_NATIVE_INITIALIZATION',
        'upstream_sha256':sha256(raw).hexdigest(),'patched_sha256':sha256(text.encode()).hexdigest(),
        'unset_target_denies_all':True,'selector_before_device_user_client_creation':True,
        'fixed_VID':'054C','fixed_PIDs':['0DA1','0336'],'selector_requires_nonzero_exact_location':True,
        'descriptor_cache_single_standard_read_no_open_reset_suspend_or_retry':True,
        'public_capture_API_still_exists_but_not_used_by_descriptor_probe':True,
        'private_source_not_claimed_upstream_release':True,'device_or_driver_operations':0}
    with (HERE/'private-source-patch.json').open('x') as h:json.dump(result,h,ensure_ascii=False,indent=2);h.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
