/* Restricted software GPIO bank5, source-defined data/set/clear registers only.
 * No input signal, interrupt or Bluetooth radio model; input reads reject. */
#include "qemu/osdep.h"
#include "hw/core/sysbus.h"
#include "qemu/module.h"
#include "qemu/error-report.h"
#define TYPE_FX3_SCU_REQUEST "fx3-gpio-bank5"
OBJECT_DECLARE_SIMPLE_TYPE(FX3SCURequest, FX3_SCU_REQUEST)
struct FX3SCURequest { SysBusDevice parent_obj; MemoryRegion mmio; uint32_t registers[5]; unsigned int events; };

static void note(FX3SCURequest *s,const char *op,hwaddr off,uint32_t v){if(s->events++<128)error_report("FX3_GPIO_BANK5 op=%s off=%#lx value=%#x",op,(unsigned long)off,v);}
static MemTxResult request_read(void *opaque,hwaddr off,uint64_t *value,unsigned size,MemTxAttrs attrs){
 FX3SCURequest *s=opaque;if(size!=4||off>0x40||off%0x10 || off==0x10){note(s,"unsupported_read",off,0);return MEMTX_ERROR;}
 *value=s->registers[off/16];note(s,"read",off,*value);return MEMTX_OK;
}
static MemTxResult request_write(void *opaque,hwaddr off,uint64_t value,unsigned size,MemTxAttrs attrs){
 FX3SCURequest *s=opaque;unsigned group=off/16,action=off%16;
 if(size!=4||group>4||group==1||(action!=0&&action!=4&&action!=8)){note(s,"unsupported_write",off,value);return MEMTX_ERROR;}
 if(action==0)s->registers[group]=value;else if(action==4)s->registers[group]|=value;else s->registers[group]&=~value;
 note(s,"write",off,value);return MEMTX_OK;
}
static const MemoryRegionOps request_ops={.read_with_attrs=request_read,.write_with_attrs=request_write,.endianness=DEVICE_LITTLE_ENDIAN,.valid.min_access_size=4,.valid.max_access_size=4};
static void request_realize(DeviceState *dev,Error **errp){FX3SCURequest *s=FX3_SCU_REQUEST(dev);memory_region_init_io(&s->mmio,OBJECT(dev),&request_ops,s,TYPE_FX3_SCU_REQUEST,0x4c);sysbus_init_mmio(SYS_BUS_DEVICE(dev),&s->mmio);}
static void request_class(ObjectClass *c,const void *data){DEVICE_CLASS(c)->realize=request_realize;}
static const TypeInfo request_type={.name=TYPE_FX3_SCU_REQUEST,.parent=TYPE_SYS_BUS_DEVICE,.instance_size=sizeof(FX3SCURequest),.class_init=request_class};
static void request_register(void){type_register_static(&request_type);}type_init(request_register)
