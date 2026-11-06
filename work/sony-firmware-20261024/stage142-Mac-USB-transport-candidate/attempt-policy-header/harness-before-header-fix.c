
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
#define libusb_le16_to_cpu(x) (x)
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

static UInt32 fx3_selected_location = 0;
int API_EXPORTED libusb_fx3_set_target(uint32_t location);
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
