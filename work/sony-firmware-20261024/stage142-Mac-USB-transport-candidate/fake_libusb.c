/* Fixture ABI only. It is linked only with libSystem, never IOKit/libusb. */
#include <stdint.h>
#include <string.h>
#include "libusb.h"
struct libusb_context { int marker; };
struct libusb_device { int marker; };
static struct libusb_context context;
static struct libusb_device device;
static libusb_device *devices[3];
static struct libusb_endpoint_descriptor endpoints[4];
static struct libusb_interface_descriptor alternate;
static struct libusb_interface interface;
static struct libusb_config_descriptor config;
static int scenario, counts[8], selected;
void fixture_reset(int value);
int fixture_count(int which);
int LIBUSB_CALL libusb_fx3_set_target(uint32_t location);
void fixture_reset(int value) {
  scenario=value;memset(counts,0,sizeof(counts));selected=0;
  memset(&alternate,0,sizeof(alternate));memset(&config,0,sizeof(config));memset(endpoints,0,sizeof(endpoints));
  devices[0]=&device;devices[1]=0;devices[2]=0;
  for(int i=0;i<4;i++){endpoints[i].bLength=7;endpoints[i].bDescriptorType=5;endpoints[i].bEndpointAddress=(i%2?0x80:0)|(i/2+1);endpoints[i].bmAttributes=2;endpoints[i].wMaxPacketSize=512;}
  alternate.bLength=9;alternate.bDescriptorType=4;alternate.bNumEndpoints=2;alternate.bInterfaceClass=8;
  alternate.bInterfaceSubClass=6;alternate.bInterfaceProtocol=80;alternate.endpoint=endpoints;
  interface.altsetting=&alternate;interface.num_altsetting=1;
  config.bLength=9;config.bDescriptorType=2;config.wTotalLength=32;config.bNumInterfaces=1;
  config.bConfigurationValue=1;config.interface=&interface;
}
int fixture_count(int which){return which>=0&&which<8?counts[which]:-1;}
int LIBUSB_CALL libusb_fx3_set_target(uint32_t location){counts[0]++;if(!location||scenario==20)return -2;selected=1;return 0;}
int LIBUSB_CALL libusb_init(libusb_context **ctx){counts[1]++;if(!selected)return -3;if(scenario==18)return -1;*ctx=scenario==19?0:&context;return 0;}
void LIBUSB_CALL libusb_exit(libusb_context *ctx){(void)ctx;counts[7]++;}
ssize_t LIBUSB_CALL libusb_get_device_list(libusb_context *ctx,libusb_device ***list){
  (void)ctx;counts[2]++;if(scenario==1)return -1;*list=devices;
  if(scenario==2)return 0;if(scenario==3){devices[1]=&device;return 2;}if(scenario==27)devices[0]=0;return 1;
}
void LIBUSB_CALL libusb_free_device_list(libusb_device **list,int unref){(void)list;(void)unref;counts[6]++;}
int LIBUSB_CALL libusb_get_device_descriptor(libusb_device *d,struct libusb_device_descriptor *out){
  (void)d;counts[3]++;memset(out,0,sizeof(*out));out->bLength=18;out->bDescriptorType=1;out->bcdUSB=0x300;
  out->idVendor=scenario==4?0x1234:0x054c;out->idProduct=scenario==25?0x0336:0x0da1;
  out->bNumConfigurations=1;if(scenario==21)out->idProduct=0x1111;if(scenario==26)return -1;return 0;
}
int LIBUSB_CALL libusb_get_active_config_descriptor(libusb_device *d,struct libusb_config_descriptor **out){
  (void)d;counts[4]++;if(scenario==5)return -1;if(scenario==6){*out=0;return 0;}*out=&config;
  if(scenario==32)return -1;
  if(scenario==7)config.bNumInterfaces=9;if(scenario==8)config.interface=0;
  if(scenario==9)interface.num_altsetting=5;if(scenario==10)interface.altsetting=0;
  if(scenario==11)alternate.bNumEndpoints=9;if(scenario==12)alternate.endpoint=0;
  if(scenario==13)endpoints[1].bEndpointAddress=endpoints[0].bEndpointAddress;
  if(scenario==14)endpoints[0].wMaxPacketSize=0;if(scenario==15)config.bDescriptorType=3;
  if(scenario==16)alternate.bLength=8;if(scenario==17)config.extra_length=-1;
  if(scenario==22)config.extra_length=4097;if(scenario==23)endpoints[0].bLength=6;
  if(scenario==24)endpoints[0].bEndpointAddress=0x71;
  if(scenario==25){alternate.bNumEndpoints=4;alternate.bInterfaceClass=255;alternate.bInterfaceSubClass=0;alternate.bInterfaceProtocol=0;config.wTotalLength=46;}
  if(scenario==28)interface.num_altsetting=0;if(scenario==29)config.extra_length=1;
  if(scenario==30)alternate.extra_length=-1;if(scenario==31)config.wTotalLength=9;return 0;
}
void LIBUSB_CALL libusb_free_config_descriptor(struct libusb_config_descriptor *cfg){(void)cfg;counts[5]++;}
