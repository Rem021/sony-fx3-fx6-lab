#!/usr/bin/env python3
"""Original prefix-read helper plus DeviceIo wrappers in Unicorn only.

The filesystem, fstat/ioctl, logs and file bytes are explicitly modeled. No
actual file/device handle is opened. No service packet binding is assumed.
"""
from pathlib import Path
import json
import struct
import traceback
import unicorn as U
from unicorn import arm64_const as A
import audit_read_routes as S

HERE=Path(__file__).resolve().parent
SCRATCH=0x11000000;SOURCE=SCRATCH+0x100;PARENT=SCRATCH+0x500;BUFFER=SCRATCH+0x10000
SP=0x10030000;HALT=0x21000000
LINKED=['_ZN8DeviceIo4openEPKci','_ZN8DeviceIo5closeEv','_ZNK8DeviceIo4readEPvm','_ZNK8DeviceIo4sizeEv',
    '_ZNK8DeviceIo5fstatER4stat','_ZNK8DeviceIo5ioctlEiPKv']


def reg(n):return getattr(A,'UC_ARM64_REG_'+n.upper())
def put(path,obj):
    with path.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')


class Guest:
    def __init__(self,image,options):
        self.image=image;self.options=options;self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM)
        pages={}
        for s in image.segments:
            flags=(U.UC_PROT_READ if s['p_flags']&4 else 0)|(U.UC_PROT_WRITE if s['p_flags']&2 else 0)|(U.UC_PROT_EXEC if s['p_flags']&1 else 0)
            assert not flags&U.UC_PROT_WRITE or not flags&U.UC_PROT_EXEC
            for address in range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096):pages[address]=flags
        for address,flags in pages.items():self.u.mem_map(address,4096,flags)
        for s in image.segments:self.u.mem_write(s['p_vaddr'],s.data())
        self.u.mem_map(SCRATCH,0x30000);self.u.mem_map(0x10000000,0x40000);self.u.mem_map(HALT,4096,U.UC_PROT_READ|U.UC_PROT_EXEC)
        self.u.mem_write(SOURCE,b'/usr/lib/appFw.so\0');self.u.mem_write(PARENT,b'/usr/lib\0')
        self.u.mem_write(BUFFER,bytes([0xa5])*0x10000)
        self.linked={n:image.symbols[n]['st_value'] for n in LINKED}
        self.ranges=[(image.symbols[n]['st_value'],image.symbols[n]['st_value']+image.symbols[n]['st_size']) for n in LINKED]
        self.calls=[];self.pcs=[];self.stores=[];self.done=False
        self.hooks=[self.u.hook_add(U.UC_HOOK_CODE,self.code),self.u.hook_add(U.UC_HOOK_MEM_WRITE,self.store)]
    def x(self,n):return self.u.reg_read(reg('x'+str(n)))
    def ret(self,value=0):self.u.reg_write(reg('x0'),value&0xffffffffffffffff);self.u.reg_write(reg('pc'),self.u.reg_read(reg('lr')))
    def text(self,a):
        out=bytearray()
        for n in range(1024):
            b=self.u.mem_read(a+n,1)[0]
            if not b:return out.decode('ascii')
            out.append(b)
        raise AssertionError('fixture string exceeded bound')
    def store(self,u,access,address,size,value,user):self.stores.append({'pc':hex(u.reg_read(reg('pc'))),'address':hex(address),'bytes':size})
    def code(self,u,pc,n,user):
        self.pcs.append(hex(pc))
        if pc==HALT:self.done=True;u.emu_stop();return
        if pc==0x1503c:
            self.calls.append({'name':'DeviceIo_error_logger_boundary','no_actual_logging_executed':True});self.ret();return
        if pc not in self.image.plt:
            assert 0x10994<=pc<0x10d3c or any(a<=pc<z for a,z in self.ranges),hex(pc)
            return
        name=self.image.plt[pc];args=[self.x(i) for i in range(4)];event={'name':name,'PLT':hex(pc),'args':args};self.calls.append(event)
        if name in self.linked:event['original_wrapper_executed']=True;u.reg_write(reg('pc'),self.linked[name]);return
        if name=='access':event['path']=self.text(args[0]);self.ret();return
        if name=='open':event.update(path=self.text(args[0]),flags=args[1],declared_initial_offset=0);self.ret(3);return
        if name=='_ZN8DeviceIo5fcntlEii':event['no_actual_fcntl']=True;self.ret();return
        if name in ['__fxstat','__fxstat64']:
            event['declared_stat_type']=self.options.get('kind','regular');event['declared_size64']=self.options['size']
            self.u.mem_write(args[2],bytes(128))
            mode=0x6000 if self.options.get('kind')=='block' else 0x8000
            self.u.mem_write(args[2]+0x10,struct.pack('<I',mode));self.u.mem_write(args[2]+0x30,struct.pack('<Q',self.options['size']))
            self.ret();return
        if name=='ioctl':
            assert args[1]==0x1260
            event['declared_sector_count']=self.options.get('sectors',204800)
            self.u.mem_write(args[2],struct.pack('<Q',event['declared_sector_count']));self.ret(self.options.get('ioctl_result',0));return
        if name=='memset':
            assert args[0]==BUFFER and args[2]<=0x10000
            self.u.mem_write(args[0],bytes([args[1]&255])*args[2]);self.ret(args[0]);return
        if name=='read':
            result=self.options.get('read_return',args[2]);event['declared_return']=result
            if result>0:
                assert result<=args[2]<=0x10000
                self.u.mem_write(args[1],bytes((n%251 for n in range(result))))
            self.ret(result);return
        if name=='close':event['declared_return']=self.options.get('close_result',0);self.ret(event['declared_return']);return
        raise AssertionError(('unexpected original import',name,hex(pc)))
    def run(self):
        cap=self.options['cap'];assert 0<=cap<=0x10000
        self.u.reg_write(reg('sp'),SP);self.u.reg_write(reg('lr'),HALT)
        for n,v in enumerate([1,PARENT,SOURCE,BUFFER,cap]):self.u.reg_write(reg('x'+str(n)),v)
        self.u.emu_start(0x10994,0,count=2000,timeout=2000000)
        assert self.done and self.u.reg_read(reg('sp'))==SP
        data=bytes(self.u.mem_read(BUFFER,cap));reads=[c for c in self.calls if c['name']=='read']
        assert len(reads)==1 and reads[0]['args'][2]<=cap
        return {'declared':self.options,'function_return_w0':self.x(0)&0xffffffff,'read_count':reads[0]['args'][2],
            'read_return':reads[0]['declared_return'],'buffer_all_zero':not any(data),
            'zero_padding_after_short_read':all(v==0 for v in data[max(0,reads[0]['declared_return']):]),
            'original_instruction_entries':len(self.pcs),'calls':self.calls,'pcs':self.pcs,'original_stores':self.stores,
            'provided_stat_io_read_returns_and_log_boundary_are_not_actual_IO':True,'complete_file_backup_or_service_reachability_proven':False}
    def close(self):
        for h in self.hooks:self.u.hook_del(h)


def main():
    out=HERE/'run-original-prefix-read';out.mkdir(exist_ok=False);(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    image=S.Image();cases=[]
    trials=[('prefix_32_of_79MB',{'size':79015712,'cap':32}),('prefix_64KiB_of_79MB',{'size':79015712,'cap':65536}),
        ('file_smaller_than_cap',{'size':17,'cap':32}),('zero_stat_size',{'size':0,'cap':32}),
        ('short_read',{'size':32,'cap':32,'read_return':31}),('read_error',{'size':32,'cap':32,'read_return':-1}),
        ('zero_cap',{'size':79015712,'cap':0}),('block_capacity',{'size':0,'kind':'block','sectors':204800,'cap':32}),
        ('block_size_query_error',{'size':0,'kind':'block','ioctl_result':-1,'cap':32}),
        ('close_error',{'size':32,'cap':32,'close_result':-1}),('size_above4GiB',{'size':0x100000010,'cap':32})]
    result={'status':'RUNNING','original_core_sha256':S.LIB_SHA,'cases':cases,'actual_IO_or_Sony_native_execution':False}
    try:
        for name,options in trials:
            g=Guest(image,options)
            try:r=g.run();r['name']=name;cases.append(r)
            finally:g.close()
        by={c['name']:c for c in cases}
        assert all(c['function_return_w0']==0 for c in cases)
        assert by['file_smaller_than_cap']['read_count']==17
        assert by['prefix_64KiB_of_79MB']['read_count']==65536
        assert by['size_above4GiB']['read_count']==32
        assert by['read_error']['read_return']==-1 and by['read_error']['buffer_all_zero']
        assert by['short_read']['zero_padding_after_short_read']
        assert by['block_size_query_error']['read_count']==0
        result.update(status='PASS_ORIGINAL_PREFIX_CAP_AND_HIDDEN_READ_ERRORS_NOT_WHOLE_BACKUP_API',
            case_count=len(cases),instruction_entries=sum(c['original_instruction_entries'] for c in cases))
        put(out/'results.json',result);(out/'static-image-source.py').write_bytes((HERE/'audit_read_routes.py').read_bytes())
        print(json.dumps({'prefix_cases':len(cases),'instruction_entries':result['instruction_entries'],'actual_device_or_file_IO':False}))
    except BaseException:
        result.update(status='FAILED_NO_PASSING_RESULT',error=traceback.format_exc());put(out/'attempt-failure.json',result);raise


if __name__=='__main__':main()
