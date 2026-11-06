#!/usr/bin/env python3
"""Run original FX3 GET_FILE2 and size-class instructions in Unicorn only.

All file, DMM, mount, crypto, libc and logging dependencies are explicitly
declared own providers. Large buffers are not allocated or filled. This proves
native arithmetic/control flow for declared results, not actual file backup.
"""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import io
import json
import struct
import traceback
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
import unicorn as U
from unicorn import arm64_const as A

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
LIB=BASE/'stage2/extraction/files/nflasha15/lib/libJiritsu.so'
LIB_SHA='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
S=0x11000000;REQ=S+0x100;MGR=S+0x1000;INNER=S+0x2000;OUTLEN=S+0x800
ROOTPTR=S+0x3000;STATE=S+0x4000;LOGPATH=S+0x8000;BUFFER=S+0x10000
SP=0x10030000;HALT=0x21000000


def reg(name):return getattr(A,'UC_ARM64_REG_'+name.upper())
def put(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


class Image:
    def __init__(self):
        self.raw=LIB.read_bytes();assert sha256(self.raw).hexdigest()==LIB_SHA
        self.elf=ELFFile(io.BytesIO(self.raw));assert self.elf['e_machine']=='EM_AARCH64'
        self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        sy=self.elf.get_section_by_name('.dynsym');self.symbols={s.name:s for s in sy.iter_symbols() if s.name}
        p=self.elf.get_section_by_name('.plt')['sh_addr']
        self.plt={p+32+i*16:sy.get_symbol(r['r_info_sym']).name for i,r in enumerate(self.elf.get_section_by_name('.rela.plt').iter_relocations())}
        self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)

    def read(self,address,length):
        s=next(s for s in self.segments if s['p_vaddr']<=address and address+length<=s['p_vaddr']+s['p_filesz'])
        return s.data()[address-s['p_vaddr']:address-s['p_vaddr']+length]

    def function(self,name):
        s=self.symbols[name];a=s['st_value'];n=s['st_size']
        return {'name':name,'VA':hex(a),'bytes':n,'sha256':sha256(self.read(a,n)).hexdigest(),
            'instructions':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,
                'PLT_symbol':self.plt.get(int(i.op_str[1:],16)) if i.mnemonic in ['b','bl'] and i.op_str.startswith('#0x') else None}
                for i in self.md.disasm(self.read(a,n),a)]}


class Guest:
    def __init__(self,image,options):
        self.image=image;self.options=options;self.u=U.Uc(U.UC_ARCH_ARM64,U.UC_MODE_ARM)
        pages={}
        for s in image.segments:
            permissions=(U.UC_PROT_READ if s['p_flags']&4 else 0)|(U.UC_PROT_WRITE if s['p_flags']&2 else 0)|(U.UC_PROT_EXEC if s['p_flags']&1 else 0)
            assert not permissions&U.UC_PROT_WRITE or not permissions&U.UC_PROT_EXEC
            for address in range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096):pages[address]=permissions
        for address,permissions in sorted(pages.items()):self.u.mem_map(address,4096,permissions)
        for s in image.segments:self.u.mem_write(s['p_vaddr'],s.data())
        self.u.mem_map(S,0x20000);self.u.mem_map(0x10000000,0x40000)
        self.u.mem_map(HALT,4096,U.UC_PROT_READ|U.UC_PROT_EXEC)
        self.u.mem_write(S,bytes([0xa5])*0x20000)
        self.u.mem_write(REQ,bytes(0x80));self.u.mem_write(REQ+0x28,bytes([0,options.get('selector',255),options.get('variant',0)]))
        self.u.mem_write(MGR,struct.pack('<Q',INNER));self.u.mem_write(INNER+8,struct.pack('<Q',BUFFER))
        self.u.mem_write(OUTLEN,bytes(8));self.u.mem_write(0x467c8,bytes(8))
        self.u.mem_write(0x46bd8,struct.pack('<Q',ROOTPTR));self.u.mem_write(ROOTPTR,struct.pack('<Q',STATE))
        self.u.mem_write(STATE+0x1828,struct.pack('<Q',S+0x7000 if options.get('pending',0) else 0))
        self.u.mem_write(STATE+0x1830,struct.pack('<Q',options.get('pending',0)))
        self.u.mem_write(STATE+0x1840,struct.pack('<Q',LOGPATH));self.u.mem_write(LOGPATH,b'/tmp/jiritsu/jit.log\0')
        self.calls=[];self.pcs=[];self.stores=[];self.reason=None
        self.hooks=[self.u.hook_add(U.UC_HOOK_CODE,self.code),self.u.hook_add(U.UC_HOOK_MEM_WRITE,self.store)]

    def x(self,n):return self.u.reg_read(reg('x'+str(n)))
    def ret(self,value=0):
        self.u.reg_write(reg('x0'),value&0xffffffffffffffff);self.u.reg_write(reg('pc'),self.u.reg_read(reg('lr')))
    def cstr(self,address):
        out=bytearray()
        for n in range(1024):
            c=self.u.mem_read(address+n,1)[0]
            if not c:return out.decode('ascii')
            out.append(c)
        raise AssertionError('guest string exceeds bound')
    def store(self,u,access,address,size,value,user):
        self.stores.append({'pc':hex(u.reg_read(reg('pc'))),'address':hex(address),'bytes':size})
    def code(self,u,pc,n,user):
        self.pcs.append(hex(pc))
        if pc==HALT:self.reason='original_function_returned';u.emu_stop();return
        if pc not in self.image.plt:
            assert 0x9e74<=pc<0xa29c or 0x6b8c<=pc<0x6bec,hex(pc)
            return
        name=self.image.plt[pc];args=[self.x(i) for i in range(4)]
        entry={'PLT':hex(pc),'name':name,'args':args};self.calls.append(entry)
        if name=='_ZN6DmmMgr13CheckUnitTypeEm':
            entry['original_function_executed']=True;u.reg_write(reg('pc'),0x6b8c);return
        if name=='_ZN11CFileAccessC1Ev':
            u.mem_write(args[0],bytes(0x14));self.ret();return
        if name=='memset':
            entry['large_modelled_buffer_not_allocated_or_filled']=args[2]>4096
            if args[2]<=4096:u.mem_write(args[0],bytes([args[1]&255])*args[2])
            self.ret(args[0]);return
        if name in ['sys_mount','sys_media_mount']:
            entry['declared_no_real_mount']=True;self.ret(self.options.get('mount_result',0));return
        if name=='get_access_filename':
            path=self.options.get('resolved_path','/usr/lib/appFw.so');entry['declared_path_result']=path
            u.mem_write(args[2],path.encode()+b'\0');self.ret();return
        if name=='_ZN11CFileAccess4statEPKcP13tag_FILE_INFO':
            entry['path']=self.cstr(args[0]);entry['declared_stat_size64']=self.options['stat_size']
            u.mem_write(args[1]+0x820,struct.pack('<Q',self.options['stat_size']))
            self.ret(self.options.get('stat_result',0));return
        if name=='_ZN6DmmMgr9dmm_allocEj':
            entry['declared_DMM_result_not_actual_allocation']=True
            self.ret(self.options.get('allocation_result',1 if args[1]==0xffffffff else 0));return
        if name=='_ZN11CFileAccess4openEPKci':
            entry['path']=self.cstr(args[1]);entry['flags']=args[2]
            self.ret(self.options.get('log_open_result',3) if args[2]==0x441 else self.options.get('open_result',3));return
        if name=='_ZN11CFileAccess4readEPvm':
            result=self.options.get('read_return',args[2]);entry['declared_read_return']=result
            if 0<result<=4096 and args[2]<=4096:u.mem_write(args[1],bytes([0x71])*min(result,args[2]))
            self.ret(result);return
        if name=='_ZN11CFileAccess5writeEPKvm':
            entry['declared_log_write_not_host_or_camera_write']=True
            self.ret(self.options.get('log_write_return',args[2]));return
        if name in ['_ZN11CFileAccess5fsyncEv','_ZN11CFileAccess5closeEv','sync']:
            self.ret();return
        if name=='strlen':self.ret(len(self.cstr(args[0])));return
        if name in ['_Z22jiritsu_cppdump_logrechPKcPhj','_Z18jiritsu_cpp_logrechPKcj']:
            entry['no_logging_executed']=True;self.ret();return
        if name=='snprintf':
            fmt=self.cstr(args[2]);assert fmt=='%s',fmt
            value=self.cstr(args[3]);u.mem_write(args[0],value.encode()[:args[1]-1]+b'\0');self.ret(len(value));return
        if name=='libCommuTalk':entry['no_crypto_executed']=True;self.ret();return
        raise AssertionError(('unmodelled original import',name,hex(pc)))

    def run(self):
        self.u.reg_write(reg('sp'),SP);self.u.reg_write(reg('lr'),HALT)
        for index,value in enumerate([REQ,MGR,OUTLEN]):self.u.reg_write(reg('x'+str(index)),value)
        self.u.emu_start(0x9e74,0,count=5000,timeout=2000000)
        assert self.reason=='original_function_returned' and self.u.reg_read(reg('sp'))==SP
        status=struct.unpack('<I',self.u.mem_read(BUFFER,4))[0]
        length=struct.unpack('<I',self.u.mem_read(OUTLEN,4))[0]
        events={name:[c for c in self.calls if c['name']==name] for name in sorted({c['name'] for c in self.calls})}
        return {'declared':self.options,'function_return_w0':self.x(0)&0xffffffff,'reply_status':hex(status),
            'reply_length':length,'request_data_length_word':struct.unpack('<I',self.u.mem_read(REQ+0x18,4))[0],
            'pending_log_bytes_after':struct.unpack('<Q',self.u.mem_read(STATE+0x1830,8))[0],
            'calls':self.calls,'events_by_name':events,'original_instruction_entries':len(self.pcs),'pcs':self.pcs,
            'original_stores':self.stores,'file_DMM_mount_crypto_and_log_providers_are_declared_fixtures':True,
            'actual_read_bytes_backup_or_error_unwind_proven':False,'actual_camera_or_host_IO':False}
    def close(self):
        for h in self.hooks:self.u.hook_del(h)


def main():
    out=HERE/'run-original-GET_FILE2';out.mkdir(exist_ok=False)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    image=Image();cases=[]
    trials=[('small_complete',{'stat_size':32}),('small_short',{'stat_size':32,'read_return':31}),
        ('small_EOF',{'stat_size':32,'read_return':0}),('declared_wrapper_error_return',{'stat_size':32,'read_return':-1}),
        ('empty_stat_size',{'stat_size':0}),('stat_error',{'stat_size':32,'stat_result':-1}),
        ('open_error',{'stat_size':32,'open_result':-1}),('allocation_error',{'stat_size':32,'allocation_result':1}),
        ('official_app_reference_plain',{'stat_size':79015712}),('official_app_reference_variant1',{'stat_size':79015712,'variant':1}),
        ('over_4GiB_low32_complete',{'stat_size':0x100000010}),
        ('near_4GiB_add4_wrap',{'stat_size':0xfffffffc,'read_return':0x7ffff000}),
        ('near_4GiB_declared_wrapper_error_alias',{'stat_size':0xffffffff,'read_return':-1}),
        ('pending_log_full',{'stat_size':7,'selector':3,'pending':7}),
        ('pending_log_short_write',{'stat_size':7,'selector':3,'pending':7,'log_write_return':6}),
        ('pending_log_open_failure',{'stat_size':32,'selector':3,'pending':7,'log_open_result':-1})]
    result={'status':'RUNNING','original_library_sha256':LIB_SHA,'cases':cases,'no_native_Sony_or_device_code_executed':True}
    try:
        for name,options in trials:
            guest=Guest(image,options)
            try:r=guest.run();r['name']=name;cases.append(r)
            finally:guest.close()
        by={c['name']:c for c in cases}
        for c in cases:assert c['function_return_w0']==0
        for name in ['small_complete','empty_stat_size','official_app_reference_plain','over_4GiB_low32_complete','near_4GiB_declared_wrapper_error_alias']:
            assert by[name]['reply_status']=='0x0'
        for name in ['small_short','small_EOF','declared_wrapper_error_return','near_4GiB_add4_wrap']:
            assert by[name]['reply_status']=='0x1000000a' and by[name]['reply_length']==4
        assert by['stat_error']['reply_status']=='0x10000006'
        assert by['open_error']['reply_status']=='0x10000008'
        assert by['allocation_error']['reply_status']==by['official_app_reference_variant1']['reply_status']=='0x10000015'
        assert by['over_4GiB_low32_complete']['reply_length']==20
        assert by['near_4GiB_declared_wrapper_error_alias']['reply_length']==3
        assert by['pending_log_full']['pending_log_bytes_after']==0
        assert by['pending_log_short_write']['pending_log_bytes_after']==7
        assert by['pending_log_full']['events_by_name']['_ZN11CFileAccess4statEPKcP13tag_FILE_INFO'][0]['path']=='/tmp/jiritsu/jit.log'
        assert by['pending_log_short_write']['events_by_name']['_ZN11CFileAccess4statEPKcP13tag_FILE_INFO'][0]['path']=='/tmp/jiritsu/jit.log'
        assert by['pending_log_open_failure']['events_by_name']['_ZN11CFileAccess4statEPKcP13tag_FILE_INFO'][0]['path']=='/usr/lib/appFw.so'
        functions=[image.function(n) for n in ['adj_cmd_get_file2','_ZN6DmmMgr13CheckUnitTypeEm','_ZN11CFileAccess4statEPKcP13tag_FILE_INFO',
            '_ZN11CFileAccess4readEPvm','_ZN11CFileAccess5closeEv','_ZN11CFileAccess4seekEii']]
        put(HERE/'original-functions.json',{'original_library_sha256':LIB_SHA,'functions':functions})
        result.update(status='PASS_ORIGINAL_WHOLE_FILE_ARITHMETIC_AND_STATUS_FOR_DECLARED_DEPENDENCIES_NOT_BACKUP',
            case_count=len(cases),instruction_entries=sum(c['original_instruction_entries'] for c in cases),
            actual_IO_or_file_read_or_DMM_allocation=False,negative_wrapper_returns_are_declared_not_actual_unwind=True)
        put(out/'results.json',result)
        print(json.dumps({'original_cases':len(cases),'instruction_entries':result['instruction_entries'],'actual_IO':False}))
    except BaseException:
        result.update(status='FAILED_NO_PASSING_RESULT',error=traceback.format_exc());put(out/'attempt-failure.json',result);raise


if __name__=='__main__':main()
