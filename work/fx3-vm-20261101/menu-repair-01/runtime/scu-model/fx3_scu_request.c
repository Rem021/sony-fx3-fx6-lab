/* Restricted virtual AP request bank inferred from SHA-bound FX3 UPM accesses.
 * Not a full SCU or physical-power model. No CP IRQ, ACK, ready, or clock stub.
 * bit8 can never be fabricated by the AP model; absent peer stays absent.
 * SPDX-License-Identifier: GPL-2.0-or-later
 */
#include "qemu/osdep.h"
#include "hw/core/sysbus.h"
#include "qemu/module.h"
#include "qemu/error-report.h"
#define TYPE_FX3_SCU_REQUEST "fx3-scu-request"
OBJECT_DECLARE_SIMPLE_TYPE(FX3SCURequest, FX3_SCU_REQUEST)
struct FX3SCURequest { SysBusDevice parent_obj; MemoryRegion mmio; uint32_t enable, request; unsigned int events; };
static void note(FX3SCURequest *s, const char *op, hwaddr off, uint32_t value) {
 if(s->events++<64) error_report("FX3_SCU_REQUEST op=%s off=0x%" HWADDR_PRIx " value=%#x enable=%#x request=%#x cp_ack=0 inferred_profile=1",op,off,value,s->enable,s->request);
}
static MemTxResult request_read(void *opaque, hwaddr off, uint64_t *value, unsigned size, MemTxAttrs attrs) {
 FX3SCURequest *s=opaque;
 if(size!=4 || off!=0x10) { note(s,"unsupported_read",off,0); return MEMTX_ERROR; }
 *value=s->request; note(s,"status",off,*value); return MEMTX_OK;
}
static MemTxResult request_write(void *opaque, hwaddr off, uint64_t value, unsigned size, MemTxAttrs attrs) {
 FX3SCURequest *s=opaque;
 if(size!=4 || value&~0x101U) {note(s,"unsupported_write",off,value);return MEMTX_ERROR;}
 switch(off) {
 case 0: s->enable|=value; break;
 case 4: s->enable&=~value; break;
 case 8:
   if(value&0x100){note(s,"rejected_fake_peer",off,value);return MEMTX_ERROR;}
   s->request|=value; break;
 case 12:s->request&=~value;break;
 default:note(s,"unsupported_write",off,value);return MEMTX_ERROR;
 }
 note(s,"write",off,value);return MEMTX_OK;
}
static const MemoryRegionOps request_ops={.read_with_attrs=request_read,.write_with_attrs=request_write,.endianness=DEVICE_LITTLE_ENDIAN,.valid.min_access_size=4,.valid.max_access_size=4};
static void request_realize(DeviceState *dev, Error **errp) {
 FX3SCURequest *s=FX3_SCU_REQUEST(dev);
 memory_region_init_io(&s->mmio,OBJECT(dev),&request_ops,s,TYPE_FX3_SCU_REQUEST,0x14);
 sysbus_init_mmio(SYS_BUS_DEVICE(dev),&s->mmio);
}
static void request_class(ObjectClass *c,const void *data){DEVICE_CLASS(c)->realize=request_realize;}
static const TypeInfo request_type={.name=TYPE_FX3_SCU_REQUEST,.parent=TYPE_SYS_BUS_DEVICE,.instance_size=sizeof(FX3SCURequest),.class_init=request_class};
static void request_register(void){type_register_static(&request_type);}type_init(request_register)
