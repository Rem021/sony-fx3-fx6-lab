#!/usr/bin/env python3
"""Original kernel vendor arm -> original SEN callback, in declared guest memory.

This enters inside delayed_setup_thread after synthetic argument/lock setup.
IRQ helpers, driver stopping, queueing, halt and other-driver callbacks are
explicit bridges/fixtures. No Linux boot, real queue or physical USB is run.
"""
from pathlib import Path
from hashlib import sha256
from elftools.elf.elffile import ELFFile
import io
import json
import struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_INTR
from unicorn import arm64_const as reg
from kernel_symbols import KernelSymbols,K,KERNEL_SHA256

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
D=0x40000000
STACK=0x50000000
MOD=0x60000000
OWN=0x70000000
CORE,THIS,USER,COMMANDS,REQUEST,EP0=D+0x1000,D+0x2000,D+0x4000,D+0x4800,D+0x5000,D+0x6000
DRIVER=THIS+0x70
FRAME=STACK+0xf000
ENTRY,EXIT=K+0x2e7524,K+0x2e74d0


def q(uc,address,value):uc.mem_write(address,struct.pack('<Q',value))
def x(uc,n):return uc.reg_read(getattr(reg,'UC_ARM64_REG_X'+str(n)))


class Fixture:
    def __init__(self):
        self.kernel=KernelSymbols()
        module=BASE/'stage138-USB-stop-dispatch-and-Mac-ownership/original-components/kmod/usbg_sen.ko'
        raw=module.read_bytes();assert sha256(raw).hexdigest()=='1a7294dd9d3babde3f1e8cc2ac4aa12f54356f61995993bbc18ace095ed0cbf2'
        self.module_raw=raw;self.elf=ELFFile(io.BytesIO(raw));self.text=self.elf.get_section_by_name('.text').data()
        syms=self.elf.get_section_by_name('.symtab')
        self.relocs={r['r_offset']:(r,syms.get_symbol(r['r_info_sym'])) for r in self.elf.get_section_by_name('.rela.text').iter_relocations()
                     if r['r_offset']<0xe8}
        common=BASE/'stage2/extraction/files/nflasha15/lib/libInfraUsbCmn.so'
        raw=common.read_bytes();assert sha256(raw).hexdigest()=='6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396'
        e=ELFFile(io.BytesIO(raw));s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=0x1d460< s['p_vaddr']+s['p_filesz'])
        offset=s['p_offset']+0x1d460-s['p_vaddr'];self.headers=raw[offset:offset+16]
        assert self.headers==bytes.fromhex('4301ff37aad70000430100c855280000')

    def run(self,name,setup,order,queue_return=0,stop_return=0,missing_commands=False):
        uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        uc.mem_map(K,(len(self.kernel.raw)+4095)&~4095);uc.mem_write(K,self.kernel.raw)
        uc.mem_map(D,0x10000);uc.mem_map(STACK,0x10000);uc.mem_map(MOD,0x1000);uc.mem_map(OWN,0x1000)
        code=bytearray(self.text[:0xe8]);bridges={}
        for at,(r,sym) in self.relocs.items():
            if r['r_info_type']==283:
                assert sym['st_shndx']=='SHN_UNDEF'
                bridges[MOD+at]=sym.name
            else:
                assert r['r_info_type']==257 and isinstance(sym['st_shndx'],int)
                address=MOD+0x10000+sym['st_shndx']*0x10000
                section=self.elf.get_section(sym['st_shndx']);data=section.data()
                # Several literals share a section; allocate it once.
                if not any(region[0]<=address<=region[1] for region in uc.mem_regions()):
                    uc.mem_map(address,(len(data)+4095)&~4095);uc.mem_write(address,data)
                struct.pack_into('<Q',code,at,address+sym['st_value']+r['r_addend'])
        assert bytes(code[:0xc8])==self.text[:0xc8]
        uc.mem_write(MOD,bytes(code))
        q(uc,CORE+8,EP0);uc.mem_write(CORE+0x9b,b'\x01')
        q(uc,DRIVER+0x20,THIS);q(uc,DRIVER+0x70,MOD)
        q(uc,THIS+0x178,USER);q(uc,USER,0 if missing_commands else COMMANDS)
        q(uc,THIS,0x1234);q(uc,THIS+0x40,0x5678)
        uc.mem_write(COMMANDS,self.headers);uc.mem_write(REQUEST,struct.pack('<I',4)+setup)
        head=CORE+0x88;nodes=[];own_callbacks={}
        for n,item in enumerate(order):
            node=D+0x7000+n*0x100
            if item=='SEN':driver=DRIVER
            else:
                driver=D+0x8000+n*0x100;fn=OWN+n*0x100
                q(uc,driver+0x70,fn);own_callbacks[fn]=item
            q(uc,node,driver);nodes.append(node)
        q(uc,head,nodes[0]+8 if nodes else head);q(uc,head+8,nodes[-1]+8 if nodes else head)
        for n,node in enumerate(nodes):
            q(uc,node+8,nodes[n+1]+8 if n+1<len(nodes) else head)
            q(uc,node+16,nodes[n-1]+8 if n else head)
        uc.reg_write(reg.UC_ARM64_REG_SP,FRAME);uc.reg_write(reg.UC_ARM64_REG_X29,FRAME)
        for n,value in {20:CORE,21:CORE+0x64,22:REQUEST,24:REQUEST+4,26:0xa5,28:4}.items():
            uc.reg_write(getattr(reg,'UC_ARM64_REG_X'+str(n)),value)
        events=[];writes=[];entries={'kernel_vendor_arm':0,'original_SEN_callback':0}
        native_stubs={self.kernel.unique(n)['address']:n for n in (
            '_raw_spin_unlock_irq','_raw_spin_lock_irq','_raw_spin_unlock_irqrestore','usb_ep_set_halt','printk')}
        def native_write(machine,access,address,size,value,unused):
            assert FRAME-0x80<=address and address+size<=FRAME+0x90 or (address==CORE+0x9b and size==1),('unreviewed guest write',hex(address),size)
            writes.append({'address':hex(address),'bytes':size})
        def interrupted(machine,number,unused):raise AssertionError(('guest interrupt denied',number))
        def finish_call(machine,value,next_pc=None):
            machine.reg_write(reg.UC_ARM64_REG_X0,value&0xffffffffffffffff)
            machine.reg_write(reg.UC_ARM64_REG_PC,x(machine,30) if next_pc is None else next_pc)
        def hook(machine,pc,size,unused):
            if pc==ENTRY:entries['kernel_vendor_arm']+=1
            if pc==MOD:entries['original_SEN_callback']+=1
            if pc in bridges:
                label=bridges[pc]
                if label=='memcmp':
                    assert x(machine,2)==8
                    a=bytes(machine.mem_read(x(machine,0),8));b=bytes(machine.mem_read(x(machine,1),8))
                    result=0 if a==b else (-1 if a<b else 1)
                elif label=='usb_gadgetcore_stop_other_driver':
                    assert x(machine,0)==DRIVER;events.append({'bridge':label,'return':stop_return});result=stop_return
                elif label=='usb_event_add_queue':
                    assert [x(machine,n) for n in (0,1,2,3,4)]==[0,0x5678,0x1234,7,4]
                    command=struct.unpack('<I',bytes(machine.mem_read(x(machine,5),4)))[0]
                    assert command in (0,1)
                    events.append({'bridge':label,'command':command,'return':queue_return,'real_queue_admission_proven':False});result=queue_return
                elif label=='printk':events.append({'bridge':'module_printk'});result=0
                else:raise AssertionError(label)
                machine.reg_write(reg.UC_ARM64_REG_X30,pc+4)
                finish_call(machine,result,pc+4);return
            if pc in native_stubs:
                label=native_stubs[pc]
                if label=='usb_ep_set_halt':assert x(machine,0)==EP0;events.append({'bridge':label,'return':0})
                elif label.startswith('_raw_spin_'):assert x(machine,0)==CORE+0x64
                else:events.append({'bridge':label})
                finish_call(machine,0);return
            if pc in own_callbacks:
                value=own_callbacks[pc];events.append({'own_callback_fixture_return':value});finish_call(machine,value);return
            allowed=K+0x2e7524<=pc<K+0x2e7618 or K+0x2e79d0<=pc<K+0x2e79e8 or MOD<=pc<MOD+0xc8
            assert allowed,('unreviewed kernel/module path',hex(pc))
        uc.hook_add(UC_HOOK_CODE,hook);uc.hook_add(UC_HOOK_MEM_WRITE,native_write);uc.hook_add(UC_HOOK_INTR,interrupted)
        uc.emu_start(ENTRY,EXIT,timeout=1000000,count=50000)
        assert uc.reg_read(reg.UC_ARM64_REG_PC)==EXIT
        assert uc.reg_read(reg.UC_ARM64_REG_SP)==FRAME and uc.reg_read(reg.UC_ARM64_REG_X29)==FRAME
        assert bytes(uc.mem_read(REQUEST,12))==struct.pack('<I',4)+setup
        assert bytes(uc.mem_read(COMMANDS,16))==self.headers
        halt=sum(e.get('bridge')=='usb_ep_set_halt' for e in events)
        queue=[e for e in events if e.get('bridge')=='usb_event_add_queue']
        return {'name':name,'events':events,'entries':entries,'halt_bridge_calls':halt,'queue_attempts':len(queue),
                'internal_ep0_flag_after':bytes(uc.mem_read(CORE+0x9b,1))[0],
                'kernel_status_register_w19':x(uc,19)&0xffffffff,'guest_write_count':len(writes),
                'write_bounds_input_immutability_and_SP_frame_checked':True,
                'kernel_thread_prologue_queue_dequeue_scheduler_IRQ_driver_stop_and_hardware_not_executed':True}


def main():
    f=Fixture();start,stop=f.headers[:8],f.headers[8:];wrong=bytes([start[0]^1])+start[1:]
    cases=[('start_all_THRU',start,['SEN'],0,0,False,1,1,1),
           ('stop_all_THRU',stop,['SEN'],0,0,False,1,1,1),
           ('event_enqueue_failure_still_THRU',start,['SEN'],-12,0,False,1,1,1),
           ('stop_other_driver_failure_no_queue',start,['SEN'],0,-5,False,1,0,1),
           ('unmatched_setup_no_queue',wrong,['SEN'],0,0,False,1,0,1),
           ('later_handler_zero_after_SEN_queue',start,['SEN',0],0,0,False,0,1,0),
           ('later_handler_zero_after_failed_queue',start,['SEN',0],-12,0,False,0,1,0),
           ('earlier_STALL_skips_SEN',start,[1,'SEN'],0,0,False,1,0,1),
           ('earlier_zero_skips_SEN',start,[0,'SEN'],0,0,False,0,0,0),
           ('empty_driver_list',start,[],0,0,False,1,0,1),
           ('missing_SEN_commands',start,['SEN'],0,0,True,1,0,1)]
    rows=[]
    for name,setup,order,qr,sr,missing,halt,queue,flag in cases:
        row=f.run(name,setup,order,qr,sr,missing)
        assert (row['halt_bridge_calls'],row['queue_attempts'],row['internal_ep0_flag_after'])==(halt,queue,flag),row
        rows.append(row)
    out=HERE/'run-vendor-dispatch';out.mkdir(exist_ok=False)
    (out/'test-executed.py').write_bytes(Path(__file__).read_bytes())
    result={'status':'PASS_ORIGINAL_702_VENDOR_ARM_PLUS_ORIGINAL_SEN_CALLBACK_WITH_DECLARED_BRIDGES_NOT_USB_OR_KERNEL_RUNTIME',
        'original_kernel_sha256':KERNEL_SHA256,'original_module_sha256':sha256(f.module_raw).hexdigest(),
        'cases':rows,'case_count':len(rows),'original_kernel_vendor_arm_entries':sum(x['entries']['kernel_vendor_arm'] for x in rows),
        'original_module_callback_entries':sum(x['entries']['original_SEN_callback'] for x in rows),
        'guest_entry_is_inside_thread_after_synthetic_argument_and_lock_setup':True,
        'no_running_kernel_thread_registration_order_real_queue_or_physical_USB_proof':True,
        'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'new_host_USB_or_camera_operations':0}
    with (out/'results.json').open('x') as h:json.dump(result,h,ensure_ascii=False,indent=2);h.write('\n')
    print(json.dumps({'status':result['status'],'cases':len(rows),'kernel_arm_entries':result['original_kernel_vendor_arm_entries'],
                      'module_callback_entries':result['original_module_callback_entries'],'actual_USB_operations':0}))


if __name__=='__main__':main()
