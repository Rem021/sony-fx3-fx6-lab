#!/usr/bin/env python3
"""Original error/cleanup instructions with an explicit LSDA-selected runtime
provider. This is not the Sony unwinder or a physical filesystem test.
"""
from pathlib import Path
from hashlib import sha256
import copy
import json
import struct
import sys
import traceback
import lsda_audit as EH

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
PRIOR=BASE/'stage157-original-whole-file-read-length-and-status'
ROOT=BASE.parents[1]
raw=(PRIOR/'final-receipt.json').read_bytes()
assert sha256(raw).hexdigest()=='84392cd9213b4aa001c4167c566a707a9275f5c91e9a7d33a4ee0259944d506b'
pins={m['path']:m for m in json.loads(raw)['files']}
for name in ['reader_guest.py','linked_posix_guest.py']:
    p=PRIOR/name;assert sha256(p.read_bytes()).hexdigest()==pins[p.relative_to(ROOT).as_posix()]['sha256']
sys.path.insert(0,str(PRIOR))
import reader_guest as R
import linked_posix_guest as L


class ErrorGuest(L.LinkedGuest):
    def __init__(self,image,metadata,options):
        self.metadata=metadata;self.decoded=[metadata.decode(n) for n in EH.FUNCTIONS]
        self.declared_options=copy.deepcopy(options);self.exceptions={};self.tokens={};self.catch_stack=[]
        self.throws=[];self.objects=[];self.system_call_counts={};self.allocation_index=0
        super().__init__(image,copy.deepcopy(options))
        self.local_links=[]
        for at,r in metadata.relocations.items():
            if r['type'] in [257,1025] and r['defined']:
                value=r['value']+r['addend'];self.u.mem_write(at,struct.pack('<Q',value))
                self.local_links.append({'slot':hex(at),'symbol':r['symbol'],'target':hex(value)})
        # These declared root slots are independent fixtures, not loader facts.
        self.u.mem_write(0x467c8,bytes(8))
        self.u.mem_write(0x46bd8,struct.pack('<Q',R.ROOTPTR))

    def record_runtime(self,pc,name,args,**extra):
        self.pcs.append(hex(pc));self.calls.append({'PLT':hex(pc),'name':name,'args':args,
            'explicit_runtime_provider_not_actual_GCC_execution':True,**extra})

    def code(self,u,pc,n,user):
        if pc in self.image.plt:
            name=self.image.plt[pc];args=[self.x(i) for i in range(4)]
            if name=='_ZN11CFileAccessC1Ev':self.objects.append(args[0])
            if name=='__cxa_allocate_exception':
                self.record_runtime(pc,name,args)
                assert args[0]==24 and self.allocation_index<32
                obj=R.S+0xa000+128*self.allocation_index;self.allocation_index+=1
                self.exceptions[obj]={'size':24};u.mem_write(obj,bytes(24));self.ret(obj);return
            if name=='_ZNSt13runtime_errorC2EPKc':
                assert args[0] in self.exceptions
                self.record_runtime(pc,name,args,declared_constructor_returns_normally=True)
                self.ret(args[0]);return
            if name=='__cxa_throw':
                self.record_runtime(pc,name,args)
                assert args[0] in self.exceptions
                thrown=self.metadata.by_address.get(args[1]);assert thrown=='_ZTI19FileAccessException',thrown
                return_ip=u.reg_read(R.reg('lr'))
                function=next(f for f in self.decoded if int(f['start'],16)<=return_ip-1<int(f['end_exclusive'],16))
                choice=self.metadata.choose_exact(function,return_ip,thrown)
                assert choice['kind']=='handler' and choice['filter']==1,choice
                fde=self.metadata.frames[int(function['start'],16)]
                row=max((row for row in fde.get_decoded().table if row['pc']<=return_ip-1),key=lambda r:r['pc'])
                cfa=row['cfa'];assert cfa.expr is None and cfa.reg in [29,31]
                base=u.reg_read(R.reg('sp' if cfa.reg==31 else 'x29'))+cfa.offset
                lr_rule=row[30];assert lr_rule.type=='OFFSET'
                saved_return=struct.unpack('<Q',u.mem_read(base+lr_rule.arg,8))[0]
                assert 0x9e74<=saved_return<0xa29c or 0xe220<=saved_return<0xe610,saved_return
                token=args[0]+32;self.tokens[token]=args[0]
                self.throws.append({'origin_function':function['function'],'throw_return_ip':hex(return_ip),
                    'thrown_RTTI':thrown,'exception_errno':struct.unpack('<I',u.mem_read(args[0]+16,4))[0],
                    'selection':choice,'CFI_CFA':hex(base),'CFI_saved_return':hex(saved_return),
                    'context_install_is_declared_runtime_provider':True,'stack_and_FP_not_synthesized_or_reset':True})
                # Original frame and saved registers remain as executed. Only
                # the runtime's exception registers and IP are supplied.
                u.reg_write(R.reg('x0'),token);u.reg_write(R.reg('x1'),choice['filter'])
                u.reg_write(R.reg('pc'),int(choice['landing_pad'],16));return
            if name=='__cxa_begin_catch':
                assert args[0] in self.tokens
                obj=self.tokens[args[0]];self.catch_stack.append(obj)
                self.record_runtime(pc,name,args);self.ret(obj);return
            if name=='__cxa_end_catch':
                assert self.catch_stack;self.catch_stack.pop()
                self.record_runtime(pc,name,args,declared_normal_catch_release=True);self.ret();return
            if name in ['close','fsync']:
                count=self.system_call_counts.get(name,0);self.system_call_counts[name]=count+1
                sequence=self.options.get(name+'_returns')
                if sequence is not None:
                    assert count<len(sequence)
                    old=self.options.get(name+'_result');present=name+'_result' in self.options
                    self.options[name+'_result']=sequence[count]
                    try:super().code(u,pc,n,user)
                    finally:
                        if present:self.options[name+'_result']=old
                        else:self.options.pop(name+'_result')
                    return
        super().code(u,pc,n,user)

    def run(self):
        # The inherited method permits the old fence, but this provider must
        # select handlers and reach the actual outer function's return.
        result=super().run();assert result['service_function_returned'] and not self.catch_stack
        objects=[]
        for address in sorted(set(self.objects)):
            objects.append({'guest_address':hex(address),'POSIX_fd_field':struct.unpack('<i',self.u.mem_read(address+12,4))[0],
                'open_flag':struct.unpack('<I',self.u.mem_read(address+16,4))[0],
                'fields_are_not_proof_of_actual_kernel_descriptor_liveness':True})
        result.update(declared=self.declared_options,LSDA_selected_runtime_provider=True,throws=self.throws,
            original_file_object_fields_after_outer_return=objects,local_defined_relocation_count=len(self.local_links),
            external_personality_unwinder_allocator_type_match_and_catch_release_executed=False,
            actual_kernel_file_descriptor_liveness_or_camera_recovery_proven=False)
        return result


def main():
    out=HERE/'run-LSDA-selected-errors';out.mkdir(exist_ok=False)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    image=R.Image();metadata=EH.Metadata();cases=[]
    trials=[('normal',{'stat_size':32}),('short_read',{'stat_size':32,'read_return':31}),
        ('read_error',{'stat_size':32,'read_return':-1}),('open_error',{'stat_size':32,'open_result':-1}),
        ('stat_error',{'stat_size':32,'stat_result':-1}),('fsync_errors',{'stat_size':32,'fsync_result':-1}),
        ('close_errors',{'stat_size':32,'close_result':-1}),
        ('first_close_error_second_success',{'stat_size':32,'close_returns':[-1,0]}),
        ('read_and_close_errors',{'stat_size':32,'read_return':-1,'close_result':-1}),
        ('fsync_and_close_errors',{'stat_size':32,'fsync_result':-1,'close_result':-1}),
        ('near4GiB_read_error_alias',{'stat_size':0xffffffff,'read_return':-1}),
        ('short_read_and_close_errors',{'stat_size':32,'read_return':31,'close_result':-1})]
    result={'status':'RUNNING','original_library_sha256':R.LIB_SHA,'cases':cases,'actual_camera_or_native_Sony_runtime_executed':False}
    try:
        for name,options in trials:
            guest=ErrorGuest(image,metadata,options)
            try:r=guest.run();r['name']=name;cases.append(r)
            finally:guest.close()
        by={c['name']:c for c in cases}
        for c in cases:assert c['function_return_w0']==0
        for name in ['normal','fsync_errors','close_errors','first_close_error_second_success','fsync_and_close_errors']:
            assert by[name]['reply_status']=='0x0' and by[name]['reply_length']==36
        for name in ['short_read','read_error','read_and_close_errors','short_read_and_close_errors']:
            assert by[name]['reply_status']=='0x1000000a'
        assert by['open_error']['reply_status']=='0x10000008'
        assert by['stat_error']['reply_status']=='0x10000006'
        for name in ['close_errors','read_and_close_errors','fsync_and_close_errors','short_read_and_close_errors']:
            assert len(by[name]['events_by_name']['close'])==2
            assert by[name]['original_file_object_fields_after_outer_return'][0]['open_flag']==1
        assert by['first_close_error_second_success']['original_file_object_fields_after_outer_return'][0]['open_flag']==0
        assert by['normal']['original_file_object_fields_after_outer_return'][0]['POSIX_fd_field']==-1
        assert len(by['fsync_errors']['throws'])==2 and len(by['fsync_and_close_errors']['throws'])==5
        assert by['near4GiB_read_error_alias']['reply_status']=='0x0' and by['near4GiB_read_error_alias']['reply_length']==3
        assert by['near4GiB_read_error_alias']['events_by_name']['read'][0]['args'][2]==0xffffffff
        result.update(status='PASS_ORIGINAL_ERROR_HANDLERS_WITH_LSDA_SELECTED_PROVIDER_NOT_ACTUAL_UNWINDER_OR_BACKUP',
            case_count=len(cases),instruction_entries=sum(c['original_instruction_entries'] for c in cases),
            modeled_exception_selections=sum(len(c['throws']) for c in cases),
            external_runtime_and_POSIX_providers_are_declared_not_physical_success=True)
        R.put(out/'results.json',result)
        (out/'metadata-parser-executed.py').write_bytes((HERE/'lsda_audit.py').read_bytes())
        print(json.dumps({'cases':len(cases),'instruction_entries':result['instruction_entries'],
            'LSDA_selected_provider_contexts':result['modeled_exception_selections'],'actual_runtime_or_IO':False}))
    except BaseException:
        result.update(status='FAILED_NO_PASSING_RESULT',error=traceback.format_exc());R.put(out/'attempt-failure.json',result);raise


if __name__=='__main__':main()
