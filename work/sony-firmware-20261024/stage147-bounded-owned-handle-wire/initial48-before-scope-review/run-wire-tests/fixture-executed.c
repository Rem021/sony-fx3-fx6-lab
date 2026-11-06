/* Own ABI fixture only. No IOKit, USB driver, device API or real libusb linkage. */
#include <stdint.h>
#include <string.h>
#include "libusb.h"

uint32_t fx3_wire_fixture_marker(void);
void fixture_reset(int value);
int fixture_set_reply(const unsigned char *data,int length);
int fixture_copy_out(unsigned char *data,int length);
int fixture_stat(int index);
static int scenario,stats[16];
static unsigned char reply[516],sent[516];

uint32_t fx3_wire_fixture_marker(void){return 0x46495833U;}
void fixture_reset(int value){
  scenario=value;memset(stats,0,sizeof(stats));stats[3]=1000000;
  memset(sent,0,sizeof(sent));memset(reply,0,sizeof(reply));reply[0]=0xff;reply[1]=0xf7;reply[4]=1;
}
int fixture_set_reply(const unsigned char *data,int length){
  if(length!=516)return -1;memcpy(reply,data,516);return 0;
}
int fixture_copy_out(unsigned char *data,int length){
  if(length!=516)return -1;memcpy(data,sent,516);return 0;
}
int fixture_stat(int index){return index>=0 && index<16?stats[index]:-999;}
static void timeout_seen(unsigned int timeout){
  if(!timeout)stats[5]++;
  if(timeout<(unsigned int)stats[3])stats[3]=(int)timeout;
  if(timeout>(unsigned int)stats[4])stats[4]=(int)timeout;
}
int LIBUSB_CALL libusb_control_transfer(libusb_device_handle *handle,uint8_t type,uint8_t request,
 uint16_t value,uint16_t index,unsigned char *data,uint16_t length,unsigned int timeout){
  (void)handle;(void)data;stats[0]++;timeout_seen(timeout);
  stats[6]=type;stats[7]=request;stats[8]=value;stats[9]=index;stats[10]=length;
  switch(scenario){case 1:return -9;case 2:return -7;case 3:return -4;case 4:return 1;case 5:return -99;default:return 0;}
}
int LIBUSB_CALL libusb_bulk_transfer(libusb_device_handle *handle,unsigned char endpoint,
 unsigned char *data,int length,int *transferred,unsigned int timeout){
  (void)handle;timeout_seen(timeout);stats[11]=endpoint;
  if(length!=516 || !transferred)return -2;
  int result=0,count=516,incoming=(endpoint&0x80)!=0;
  if(incoming){
    stats[2]++;
    switch(scenario){case 20:count=515;break;case 21:result=-7;count=200;break;
      case 22:result=-9;count=0;break;case 23:result=-4;count=-1;break;case 24:result=1;break;
      case 26:count=517;break;case 27:count=-2;break;default:break;}
    if(count>0)memcpy(data,reply,(size_t)(count>length?length:count));
    if(scenario==25)data[length]^=1; /* Within the caller's allocated guard region. */
  }else{
    stats[1]++;memcpy(sent,data,516);
    switch(scenario){case 10:count=515;break;case 11:result=-7;count=200;break;
      case 12:result=-9;count=0;break;case 13:result=-4;count=-1;break;case 14:result=1;break;
      case 17:count=517;break;case 18:count=-2;break;default:break;}
    if(scenario==15)data[0]^=1;
    if(scenario==16)data[length]^=1; /* Inside the allocated guard, not an unsafe write. */
  }
  *transferred=count;return result;
}
