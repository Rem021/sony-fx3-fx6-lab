#!/usr/bin/env python3
"""Original constructor/callback/IO/NIN up to a declared checkpoint, CPU fixtures."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_INTR
from unicorn import arm64_const as R

HERE=Path(__file__).resolve().parent
O,C,D,S,RET,B=0x10000000,0x20000000,0x40000000,0x50000000,0x60000000,0x61000000
SP=S+0xf000
TABLE,RSRC,MSG,RESOURCE,LOADER,CTX,ALGO=D+0x1000,D+0x7000,D+0x8000,D+0x6000,D+0x9000,D+0xa000,D+0xb000
READ,WRITE=B,B+0x100


def load():
    path=HERE/'normal_cooperator.py'
    assert path.read_bytes()==(HERE/'static-executed.py').read_bytes()
    spec=importlib.util.spec_from_file_location('normal_checkpoint_sources',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def packet(code,payload=b''):
    assert len(payload)<=512
    return struct.pack('>HH',(~code)&0xffff,0)+payload.ljust(512,b'\0')


def signed(value):
    value&=0xffffffff;return value-0x100000000 if value&0x80000000 else value


def run(module,review,style,pattern,resource_result=0):
    obj,core=module.images();uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    modules=[(O,obj,review['object_functions']),(C,core,review['core_functions'])]
    ranges=[];entry_names={};plts={};named={}
    for base,img,funcs in modules:
        pages=sorted({page for seg in img.loads for page in range((base+seg['p_vaddr'])&~0xfff,
            (base+seg['p_vaddr']+seg['p_memsz']+0xfff)&~0xfff,0x1000)})
        for page in pages:uc.mem_map(page,0x1000)
        for seg in img.loads:uc.mem_write(base+seg['p_vaddr'],seg.data())
        for f in funcs:
            start=int(f['VA'],16);assert sha256(img.read(start,f['bytes'])).hexdigest()==f['sha256']
            ranges.append((base+start,base+start+f['bytes']))
            label=f.get('name',hex(start));entry_names[base+start]=label
            if base==C and 'name' in f:named[label]=base+start
        plts.update({base+va:(base,name) for va,name in img.plt.items()})
    # Only original selected local relocations needed by this fixture are applied.
    selected={0x261d48,0x261fc0,0x262c38,0x262f58,*range(0x252340,0x252378,8)}
    relocated=[]
    for rel in obj.elf.get_section_by_name('.rela.dyn').iter_relocations():
        if rel['r_offset'] in selected:
            assert rel['r_info_type']==1027 and rel['r_info_sym']==0
            uc.mem_write(O+rel['r_offset'],struct.pack('<Q',O+rel['r_addend']))
            relocated.append(rel['r_offset'])
    assert set(relocated)==selected
    uc.mem_map(D,0x10000);uc.mem_map(S,0x10000);uc.mem_map(RET,0x1000);uc.mem_map(B,0x1000)
    uc.mem_write(S,bytes([0xa7])*0x10000)
    uc.mem_write(TABLE,struct.pack('<QQ',READ,WRITE))
    uc.mem_write(RESOURCE,struct.pack('<QQ',RSRC,MSG)+struct.pack('<I',0))
    uc.mem_write(O+0x2ce0b0,struct.pack('<Q',RESOURCE));uc.mem_write(O+0x2ce0ac,struct.pack('<I',1))
    case={'digest_style':style,'pattern':pattern,'resource_result_fixture':resource_result,
          'original_entries':[],'driver_fixture_calls':[],'native_verifier_rounds':[],
          'native_verifier_returns':[],'native_comparisons':[],'public_response_codes':[],
          'normal_callback_levels':[],'resource_requests':[],'bridges':[]}
    state={'phase':'construct','requests':0,'last_challenge':None,'round':0,'hash':None,
           'thread_arg':None,'thread_entry':None,'checkpoint':False,'random_calls':0}
    writes=[];original_snapshots=[(lo,bytes(uc.mem_read(lo,hi-lo))) for lo,hi in ranges]

    def reg(n):return uc.reg_read(getattr(R,'UC_ARM64_REG_X'+str(n)))
    def u64(a):return struct.unpack('<Q',bytes(uc.mem_read(a,8)))[0]
    def cstring(a):return bytes(uc.mem_read(a,128)).split(b'\0',1)[0].decode()
    def wr(a,data,origin):
        assert S<=a and a+len(data)<=S+0x10000 or O+0x2ce100<=a and a+len(data)<=O+0x2ce168 or \
            O+0x2ce0ac<=a and a+len(data)<=O+0x2ce0b0,(origin,hex(a),len(data))
        writes.append((origin,a,len(data)))
        if origin!='original':uc.mem_write(a,data)
    def on_write(machine,access,a,size,value,unused):wr(a,bytes(size),'original')
    def interrupt(machine,number,unused):raise AssertionError(('guest syscall/interrupt denied',number))
    def returned(value):
        uc.reg_write(R.UC_ARM64_REG_X0,value&0xffffffffffffffff)
        uc.reg_write(R.UC_ARM64_REG_PC,reg(30))
    def digest_for_last():
        ch=state['last_challenge'];assert ch is not None and len(ch)==512
        if style=='public_MSC_prefix4':return sha256(ch[:4]).digest()
        native_round=state['requests']//2+1
        material_va={1:0x55780,2:0x55580,3:0x55380}[native_round]
        return sha256(ch+core.read(material_va,512)).digest()
    def code(machine,pc,size,unused):
        if pc==RET:return
        if pc in entry_names:case['original_entries'].append(entry_names[pc])
        if pc==C+0x15c1c:case['native_verifier_rounds'].append(reg(2))
        if pc==C+0xbd68:case['native_verifier_returns'].append(signed(reg(0)))
        if pc==O+0xea6b0:case['normal_callback_levels'].append(signed(reg(1)))
        if pc==C+0xbf30:
            state['checkpoint']=True;uc.emu_stop();return
        if pc in (O+0xea070,O+0xea2b0):
            case['bridges'].append('CPU_fixture_libObj_local_logging_helper')
            returned(0);return
        if pc in (READ,WRITE):
            assert reg(0)==O+0x2ce168 and reg(2)==516
            buf=reg(1);assert S<=buf<buf+516<=SP
            if pc==READ:
                n=state['requests'];assert 0<=n<7
                if n==6:payload=packet(5)
                elif n%2==0:payload=packet(1)
                else:payload=packet(3,b'\x01'+digest_for_last())
                wr(buf,payload,'CPU_fixture_receive');state['requests']+=1
                case['driver_fixture_calls'].append('READ516')
            else:
                payload=bytes(uc.mem_read(buf,516));encoded,salt=struct.unpack('>HH',payload[:4]);cmd=((~encoded)&0xffff)-salt
                assert cmd in (8,4,6),(cmd,salt)
                case['public_response_codes'].append(cmd)
                if cmd==8:state['last_challenge']=payload[4:]
                if cmd==6:case['final_reply_first_byte']=payload[4]
                case['driver_fixture_calls'].append('WRITE516')
            returned(516);return
        if pc not in plts:
            assert any(lo<=pc<hi for lo,hi in ranges),('unreviewed original code',hex(pc))
            return
        base,name=plts[pc]
        if base==C and name in named:
            uc.reg_write(R.UC_ARM64_REG_PC,named[name]);return
        a=[reg(n) for n in range(6)];case['bridges'].append(name)
        if name=='pthread_mutex_init':assert a[0]==O+0x2ce118;answer=0
        elif name in ('pthread_mutex_lock','pthread_mutex_unlock'):assert a[0]==O+0x2ce118;answer=0
        elif name=='__cxa_atexit':answer=0
        elif name=='dlopen':assert cstring(a[0])=='libsencore.so';answer=LOADER
        elif name=='dlsym':assert a[0]==LOADER and cstring(a[1])=='NinThread';answer=C+0xbbfc
        elif name=='pthread_create':
            assert a[2]==C+0xbbfc and a[3]==O+0x2ce108
            state['thread_arg'],state['thread_entry']=a[3],a[2]
            wr(a[0],struct.pack('<Q',0x71),'CPU_fixture_thread_token');answer=0
        elif name=='pthread_setcancelstate':
            assert a[0] in (0,1)
            if a[1]:wr(a[1],struct.pack('<I',0),'CPU_fixture_cancel_state')
            answer=0
        elif name=='pthread_testcancel':answer=0
        elif name=='getpid':answer=1234
        elif name.startswith('_Z10cpp_logrec'):answer=0
        elif name in ('_Z13tlog_set_haspi','_Z15tlog_set_pcdatePh','_Z16tlog_set_apptypeh','_Z17tlog_set_userinfoPh'):
            answer=0  # Declared logging bridges, no actual history/log IO.
        elif name=='memset':
            assert a[2]<=2048;wr(a[0],bytes([a[1]&255])*a[2],'CPU_memset');answer=a[0]
        elif name=='memcpy':
            assert a[2]<=2048;wr(a[0],bytes(uc.mem_read(a[1],a[2])),'CPU_memcpy');answer=a[0]
        elif name=='memcmp':
            assert a[2]==32;x=bytes(uc.mem_read(a[0],32));y=bytes(uc.mem_read(a[1],32))
            case['native_comparisons'].append(x==y);answer=0 if x==y else -1 if x<y else 1
        elif name=='RAND_bytes':
            assert a[1] in (8,512);state['random_calls']+=1
            data=bytes(8) if a[1]==8 else bytes((i*17+pattern*31+state['random_calls'])%256 for i in range(512))
            wr(a[0],data,'CPU_fixture_RAND_bytes');answer=1
        elif name=='EVP_sha256':answer=ALGO
        elif name=='EVP_MD_CTX_new':state['hash']=sha256();answer=CTX
        elif name=='EVP_DigestInit_ex':assert a[0]==CTX and a[1]==ALGO;state['hash']=sha256();answer=1
        elif name=='EVP_DigestUpdate':
            assert a[0]==CTX and a[2]==1024;state['hash'].update(bytes(uc.mem_read(a[1],a[2])));answer=1
        elif name=='EVP_DigestFinal_ex':
            assert a[0]==CTX;wr(a[1],state['hash'].digest(),'CPU_EVP_digest');wr(a[2],struct.pack('<I',32),'CPU_EVP_length');answer=1
        elif name=='EVP_MD_CTX_free':assert a[0]==CTX;answer=0
        elif name=='_ZN3MWF8RsrcAcsr7AcquireEPNS_6ObjMsgENS0_8AcqAct_tE':
            assert a[:3]==[RSRC,MSG,1];case['resource_requests'].append({'action':a[2],'returned_fixture':resource_result});answer=resource_result
        else:raise AssertionError(('unreviewed bridge',name,hex(pc)))
        returned(answer)

    uc.hook_add(UC_HOOK_CODE,code);uc.hook_add(UC_HOOK_MEM_WRITE,on_write);uc.hook_add(UC_HOOK_INTR,interrupt)
    def invoke(pc,args):
        uc.reg_write(R.UC_ARM64_REG_SP,SP);uc.reg_write(R.UC_ARM64_REG_X30,RET)
        for n in range(8):uc.reg_write(getattr(R,'UC_ARM64_REG_X'+str(n)),args[n] if n<len(args) else 0)
        try:uc.emu_start(pc,RET,timeout=10000000,count=500000)
        except Exception as error:
            raise AssertionError({'phase':state['phase'],'pc':hex(uc.reg_read(R.UC_ARM64_REG_PC)),
                'recent_entries':case['original_entries'][-8:],'requests':state['requests']}) from error
    invoke(O+0x57fec,[])
    assert uc.reg_read(R.UC_ARM64_REG_PC)==RET and uc.reg_read(R.UC_ARM64_REG_SP)==SP
    assert u64(O+0x2ce108)==O+0x252340 and u64(O+0x2ce150)==0xffffffffffffffff
    state['phase']='event_callback';invoke(O+0xea128,[1,TABLE,0,0])
    assert uc.reg_read(R.UC_ARM64_REG_PC)==RET and uc.reg_read(R.UC_ARM64_REG_SP)==SP
    assert u64(O+0x2ce100)==TABLE and u64(O+0x2ce150)==0x71
    assert state['thread_entry']==C+0xbbfc and state['thread_arg']==O+0x2ce108
    state['phase']='NIN';invoke(state['thread_entry'],[state['thread_arg']])
    assert state['checkpoint'] and uc.reg_read(R.UC_ARM64_REG_PC)==C+0xbf30
    assert uc.reg_read(R.UC_ARM64_REG_SP)==SP-0x6d0
    assert state['requests']==7 and case['public_response_codes']==[8,4,8,4,8,4,6]
    assert case['final_reply_first_byte']==1 and len(case['resource_requests'])==1
    assert struct.unpack('<I',bytes(uc.mem_read(O+0x2ce0ac,4)))[0]==2
    assert bytes(uc.mem_read(O+0x2ce158,1))==b'\0'
    want=style=='service_full512_plus_material'
    assert case['native_comparisons']==[want]*3
    assert case['native_verifier_returns']==[0 if want else -2]*3
    assert case['native_verifier_rounds']==([1,2,3] if want else [1,1,1])
    assert case['normal_callback_levels']==[3 if want else -1]
    assert bytes(uc.mem_read(SP,32))==bytes([0xa7])*32
    for start,value in original_snapshots:assert bytes(uc.mem_read(start,len(value)))==value
    case.update({'status':'PASS_ORIGINAL_TO_NORMAL_CALLBACK_CHECKPOINT_NOT_THREAD_OR_MODE_COMPLETION',
        'constructor_vtable_and_event_payload_binding_checked':True,'same_original_callback_despite_digest_failure':not want,
        'original_entry_count':len(case['original_entries']),'original_object_state_after_callback':2,
        'stack_above_entry_guard_and_original_code_unchanged':True,'all_guest_writes_bounded':True,'guest_write_count':len(writes),
        'stopped_before_original_tlog_file_check':True,'thread_completion_proven':False,
        'actual_MSC_USB_state_resource_acquisition_or_no_persistent_effects_proven':False,
        'all_transport_loader_thread_mutex_RAND_EVP_logging_and_resource_calls_use_declared_CPU_fixtures':True})
    return case


def main():
    module=load();review=json.loads((HERE/'normal-cooperator-static.json').read_text())
    cases=[run(module,review,style,pattern) for style in ('service_full512_plus_material','public_MSC_prefix4') for pattern in (0,1)]
    cases.append(run(module,review,'public_MSC_prefix4',2,-5))
    output=HERE/'run-original-checkpoint';output.mkdir(exist_ok=False)
    (output/'test-executed.py').write_bytes(Path(__file__).read_bytes())
    (output/'static-reader-executed.py').write_bytes((HERE/'normal_cooperator.py').read_bytes())
    report={'status':'PASS_ORIGINAL_NORMAL_COOPERATOR_NIN_CHECKPOINT_NOT_REAL_AUTH_MODE_OR_THREAD_EXIT',
        'case_count':len(cases),'cases':cases,'original_function_entries':sum(x['original_entry_count'] for x in cases),
        'new_host_USB_camera_driver_or_Windows_operations':0,'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'initial_MSC_digest_algorithm_proven':False,'resource_request_not_physical_mode_success':True,
        'normal_callback_can_follow_failed_digest_comparisons_in_declared_guest':True,
        'full_NinThread_exit_history_or_cleanup_executed':False,'goal_complete':False,'persistent_write_release':False}
    with (output/'results.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':report['status'],'cases':len(cases),'original_entries':report['original_function_entries'],
        'normal_callback_levels':[x['normal_callback_levels'] for x in cases],'new_device_operations':0}))


if __name__=='__main__':main()
