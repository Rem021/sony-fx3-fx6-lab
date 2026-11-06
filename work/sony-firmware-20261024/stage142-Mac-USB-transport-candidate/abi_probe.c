#include <stdio.h>
#include <stddef.h>
#include "libusb.h"
/* Header/layout probe only: this program is NOT linked with libusb. */
int main(void) {
  printf("{\"device_size\":%zu,\"endpoint_size\":%zu,\"interface_desc_size\":%zu,\"interface_size\":%zu,\"config_size\":%zu,",
    sizeof(struct libusb_device_descriptor),sizeof(struct libusb_endpoint_descriptor),
    sizeof(struct libusb_interface_descriptor),sizeof(struct libusb_interface),sizeof(struct libusb_config_descriptor));
  printf("\"endpoint_extra\":%zu,\"interface_endpoint\":%zu,\"config_interface\":%zu}\n",
    offsetof(struct libusb_endpoint_descriptor,extra),offsetof(struct libusb_interface_descriptor,endpoint),
    offsetof(struct libusb_config_descriptor,interface));
  return 0;
}
