#!/usr/bin/env python3
"""Connect GET_FILE2 to six original CFileAccess methods, stopping at C++
exception allocation. POSIX/DMM/mount/crypto remain declared own providers.
"""
from pathlib import Path
import json
import struct
import traceback
import reader_guest as R

HERE=Path(__file__).resolve().parent
ERRNO=R.S+0x9000
LINKED=['_ZN11CFileAccessC1Ev','_ZN11CFileAccess4statEPKcP13tag_FILE_INFO',
    '_ZN11CFileAccess4openEPKci','_ZN11CFileAccess4readEPvm',
    '_ZN11CFileAccess5fsyncEv','_ZN11CFileAccess5closeEv']


class LinkedGuest(R.Guest):
    def __init__(self,image,options):
        self.linked={n:image.symbols[n]['st_value'] for n in LINKED}
        self.ranges=[(image.symbols[n]['st_value'],image.symbols[n]['st_value']+image.symbols[n]['st_size']) for n in LINKED]
        super().__init__(image,options)

    def code(self,u,pc,n,user):
        if pc in self.image.plt:
            name=self.image.plt[pc];args=[self.x(i) for i in range(4)]
            if name in self.linked:
                self.pcs.append(hex(pc));self.calls.append({'PLT':hex(pc),'name':name,'args':args,'original_function_executed':True})
                u.reg_write(R.reg('pc'),self.linked[name]);return
            if name=='__cxa_allocate_exception':
                self.pcs.append(hex(pc));self.calls.append({'PLT':hex(pc),'name':name,'args':args,'stopped_before_exception_allocation_or_unwind':True})
                self.reason='before_exception_allocation_no_service_completion_claim';u.emu_stop();return
            if name in ['open','read','fsync','close','__errno_location','__xstat','__xstat64','strncmp']:
                self.pcs.append(hex(pc));entry={'PLT':hex(pc),'name':name,'args':args,'no_actual_syscall':True};self.calls.append(entry)
                if name=='__errno_location':self.ret(ERRNO);return
                if name=='strncmp':
                    a=self.cstr(args[0]).encode()[:args[2]];b=self.cstr(args[1]).encode()[:args[2]]
                    self.ret(0 if a==b else -1 if a<b else 1);return
                if name in ['__xstat','__xstat64']:
                    entry['path']=self.cstr(args[1]);entry['declared_stat_size64']=self.options['stat_size']
                    u.mem_write(args[2]+0x30,struct.pack('<Q',self.options['stat_size']))
                    value=self.options.get('stat_result',0)
                elif name=='open':entry.update(path=self.cstr(args[0]),flags=args[1]);value=self.options.get('open_result',3)
                elif name=='read':
                    value=self.options.get('read_return',args[2]);entry['declared_return']=value
                    if 0<value<=4096 and args[2]<=4096:u.mem_write(args[1],bytes([0x71])*min(value,args[2]))
                else:value=self.options.get(name+'_result',0)
                if value<0:u.mem_write(ERRNO,struct.pack('<I',5))
                self.ret(value);return
        elif any(a<=pc<z for a,z in self.ranges) or 0x11ac8<=pc<0x11ad8:
            self.pcs.append(hex(pc));return
        super().code(u,pc,n,user)

    def run(self):
        self.u.reg_write(R.reg('sp'),R.SP);self.u.reg_write(R.reg('lr'),R.HALT)
        for i,v in enumerate([R.REQ,R.MGR,R.OUTLEN]):self.u.reg_write(R.reg('x'+str(i)),v)
        self.u.emu_start(0x9e74,0,count=10000,timeout=2000000)
        assert self.reason in ['original_function_returned','before_exception_allocation_no_service_completion_claim']
        returned=self.reason=='original_function_returned'
        if returned:assert self.u.reg_read(R.reg('sp'))==R.SP
        events={n:[c for c in self.calls if c['name']==n] for n in sorted({c['name'] for c in self.calls})}
        return {'declared':self.options,'reason':self.reason,'service_function_returned':returned,
            'function_return_w0':self.x(0)&0xffffffff if returned else None,
            'reply_status':hex(struct.unpack('<I',self.u.mem_read(R.BUFFER,4))[0]) if returned else None,
            'reply_prefix_before_completion_not_success':hex(struct.unpack('<I',self.u.mem_read(R.BUFFER,4))[0]) if not returned else None,
            'reply_length':struct.unpack('<I',self.u.mem_read(R.OUTLEN,4))[0] if returned else None,
            'events_by_name':events,'calls':self.calls,'pcs':self.pcs,'original_instruction_entries':len(self.pcs),
            'original_stores':self.stores,'six_CFileAccess_methods_are_original_instructions':True,
            'actual_stat_open_read_sync_close_DMM_mount_crypto_or_error_unwind_executed':False}


def main():
    out=HERE/'run-linked-original-POSIX';out.mkdir(exist_ok=False)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    image=R.Image();cases=[]
    trials=[('linked_small_complete',{'stat_size':32}),('linked_short_read',{'stat_size':32,'read_return':31}),
        ('linked_EOF_short',{'stat_size':32,'read_return':0}),('linked_empty_size',{'stat_size':0}),
        ('linked_app_plain',{'stat_size':79015712}),('linked_4GiB_plus16',{'stat_size':0x100000010}),
        ('linked_read_error_fenced',{'stat_size':32,'read_return':-1}),
        ('linked_open_error_fenced',{'stat_size':32,'open_result':-1}),
        ('linked_stat_error_fenced',{'stat_size':32,'stat_result':-1}),
        ('linked_fsync_error_fenced',{'stat_size':32,'fsync_result':-1})]
    result={'status':'RUNNING','original_library_sha256':R.LIB_SHA,'cases':cases,'no_actual_device_or_native_Sony_IO':True}
    try:
        for name,options in trials:
            g=LinkedGuest(image,options)
            try:r=g.run();r['name']=name;cases.append(r)
            finally:g.close()
        by={c['name']:c for c in cases}
        for c in cases:
            if c['name'].endswith('_fenced'):
                assert not c['service_function_returned'] and c['reply_status'] is None
                assert len(c['events_by_name']['__cxa_allocate_exception'])==1
            else:
                assert c['service_function_returned'] and c['function_return_w0']==0
                assert len(c['events_by_name']['open'])==len(c['events_by_name']['read'])==len(c['events_by_name']['close'])==1
                assert len(c['events_by_name']['fsync'])==2
                assert c['events_by_name']['open'][0]['flags']==0
        assert by['linked_small_complete']['reply_status']=='0x0' and by['linked_small_complete']['reply_length']==36
        assert by['linked_short_read']['reply_status']==by['linked_EOF_short']['reply_status']=='0x1000000a'
        assert by['linked_4GiB_plus16']['reply_status']=='0x0' and by['linked_4GiB_plus16']['reply_length']==20
        assert by['linked_4GiB_plus16']['events_by_name']['read'][0]['args'][2]==16
        assert by['linked_app_plain']['events_by_name']['read'][0]['args'][2]==79015712
        assert by['linked_empty_size']['events_by_name']['read'][0]['args'][2]==0
        result.update(status='PASS_LINKED_ORIGINAL_POSIX_BRANCH_AND_SHORT_READ_NOT_ACTUAL_BACKUP',case_count=len(cases),
            instruction_entries=sum(c['original_instruction_entries'] for c in cases),
            negative_errors_stop_before_exception_unwind_and_do_not_prove_the_declared_wrapper_error_returns=True)
        R.put(out/'results.json',result)
        R.put(HERE/'linked-original-functions.json',{'original_library_sha256':R.LIB_SHA,'functions':[image.function(n) for n in LINKED],
            'stat_thunk_bytes':image.read(0x11ac8,16).hex(),'stat_thunk_PLT':image.plt[0x6690]})
        print(json.dumps({'linked_original_cases':len(cases),'instruction_entries':result['instruction_entries'],'actual_IO':False}))
    except BaseException:
        result.update(status='FAILED_NO_PASSING_RESULT',error=traceback.format_exc());R.put(out/'attempt-failure.json',result);raise


if __name__=='__main__':main()
