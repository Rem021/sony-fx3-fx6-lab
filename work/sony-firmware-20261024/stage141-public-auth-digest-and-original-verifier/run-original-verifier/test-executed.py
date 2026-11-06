#!/usr/bin/env python3
"""CPU provider -> bounded original AArch64 verifier; no native camera or USB code."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import struct
import sys
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_INTR
from unicorn import arm64_const as reg

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
LOAD, DATA, STACK, RETURN = 0x10000000, 0x40000000, 0x50000000, 0x60000000
CLIENT, CHALLENGE, CONTEXT, ALGORITHM = DATA+0x1000, DATA+0x2000, DATA+0x8000, DATA+0x9000
SP = STACK+0xf000


def load_module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


class OriginalVerifier:
    def __init__(self, image):
        self.image=image
        self.functions=[image.function(n) for n in ['_Z6xxstepPhS_i','_Z9CmdDecodePtPh','SEN_SSL_GenerateDigestData']]
        self.by_name={f['name']:f for f in self.functions}
        self.plt={LOAD+a:n for a,n in image.plt.items()}
        self.code_ranges=[(LOAD+int(f['VA'],16),LOAD+int(f['VA'],16)+f['bytes']) for f in self.functions]

    def run(self, client_packet, challenge_packet, native_round):
        assert len(client_packet)==len(challenge_packet)==516
        uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        pages=sorted({a for s in self.image.loads for a in range((LOAD+s['p_vaddr'])&~0xfff,
                        (LOAD+s['p_vaddr']+s['p_memsz']+0xfff)&~0xfff,0x1000)})
        for address in pages:uc.mem_map(address,0x1000)
        for segment in self.image.loads:uc.mem_write(LOAD+segment['p_vaddr'],segment.data())
        uc.mem_map(DATA,0x10000);uc.mem_map(STACK,0x10000);uc.mem_map(RETURN,0x1000)
        uc.mem_write(STACK,bytes([0xa7])*0x10000)
        guard=bytes([0xd6])*32
        uc.mem_write(CLIENT-32,guard+client_packet+guard)
        uc.mem_write(CHALLENGE-32,guard+challenge_packet+guard)
        uc.reg_write(reg.UC_ARM64_REG_SP,SP);uc.reg_write(reg.UC_ARM64_REG_X30,RETURN)
        uc.reg_write(reg.UC_ARM64_REG_X0,CLIENT);uc.reg_write(reg.UC_ARM64_REG_X1,CHALLENGE)
        uc.reg_write(reg.UC_ARM64_REG_X2,native_round)
        saved={}
        for n in range(19,30):
            saved[n]=0xabcd0000+n;uc.reg_write(getattr(reg,'UC_ARM64_REG_X'+str(n)),saved[n])
        calls,writes,entered,hash_inputs,comparisons=[],[],[],[],[]
        hash_context=None
        def checked_write(address,data,origin):
            assert SP-0x3000<=address and address+len(data)<=SP,(hex(address),len(data),origin)
            writes.append({'address':hex(address),'bytes':len(data),'origin':origin})
            if origin!='native':uc.mem_write(address,data)
        def native_write(machine,access,address,size,value,unused):
            checked_write(address,bytes(size),'native')
        def interrupt(machine,number,unused):
            raise AssertionError(('Guest interrupt/syscall denied',number))
        def code(machine,pc,size,unused):
            nonlocal hash_context
            for f in self.functions:
                if pc==LOAD+int(f['VA'],16):entered.append(f['name'])
            if pc not in self.plt:
                assert any(lo<=pc<hi for lo,hi in self.code_ranges),('unreviewed guest code',hex(pc))
                return
            name=self.plt[pc]
            args=[machine.reg_read(getattr(reg,'UC_ARM64_REG_X'+str(n))) for n in range(6)]
            calls.append(name)
            if name in self.by_name:
                machine.reg_write(reg.UC_ARM64_REG_PC,LOAD+int(self.by_name[name]['VA'],16))
                return
            if name=='memset':
                assert args[2]<=1024
                checked_write(args[0],bytes([args[1]&255])*args[2],'CPU_memset_bridge');answer=args[0]
            elif name=='memcpy':
                assert args[2]<=1024
                checked_write(args[0],bytes(machine.mem_read(args[1],args[2])),'CPU_memcpy_bridge');answer=args[0]
            elif name=='memcmp':
                assert args[2]==32
                a=bytes(machine.mem_read(args[0],32));b=bytes(machine.mem_read(args[1],32))
                answer=0 if a==b else (-1 if a<b else 1)
                comparisons.append({'bytes':32,'equal':a==b,'left_fingerprint':sha256(a).hexdigest(),
                                    'right_fingerprint':sha256(b).hexdigest()})
            elif name=='EVP_sha256':answer=ALGORITHM
            elif name=='EVP_MD_CTX_new':hash_context=sha256();answer=CONTEXT
            elif name=='EVP_DigestInit_ex':
                assert args[0]==CONTEXT and args[1]==ALGORITHM
                hash_context=sha256();answer=1
            elif name=='EVP_DigestUpdate':
                assert args[0]==CONTEXT and args[2]==1024
                value=bytes(machine.mem_read(args[1],args[2]));hash_context.update(value)
                hash_inputs.append({'bytes':len(value),'fingerprint':sha256(value).hexdigest()});answer=1
            elif name=='EVP_DigestFinal_ex':
                assert args[0]==CONTEXT
                checked_write(args[1],hash_context.digest(),'CPU_EVP_final_bridge')
                checked_write(args[2],struct.pack('<I',32),'CPU_EVP_length_bridge');answer=1
            elif name=='EVP_MD_CTX_free':
                assert args[0]==CONTEXT;answer=0
            else:raise AssertionError(('unreviewed external call',name))
            machine.reg_write(reg.UC_ARM64_REG_X0,answer&0xffffffffffffffff)
            machine.reg_write(reg.UC_ARM64_REG_PC,machine.reg_read(reg.UC_ARM64_REG_X30))
        uc.hook_add(UC_HOOK_MEM_WRITE,native_write);uc.hook_add(UC_HOOK_CODE,code);uc.hook_add(UC_HOOK_INTR,interrupt)
        uc.emu_start(LOAD+int(self.functions[0]['VA'],16),RETURN,timeout=2000000,count=20000)
        assert uc.reg_read(reg.UC_ARM64_REG_PC)==RETURN
        answer=uc.reg_read(reg.UC_ARM64_REG_X0)&0xffffffff
        if answer>=0x80000000:answer-=0x100000000
        assert bytes(uc.mem_read(CLIENT,516))==client_packet and bytes(uc.mem_read(CHALLENGE,516))==challenge_packet
        for address in (CLIENT-32,CLIENT+516,CHALLENGE-32,CHALLENGE+516):assert bytes(uc.mem_read(address,32))==guard
        assert uc.reg_read(reg.UC_ARM64_REG_SP)==SP and bytes(uc.mem_read(SP,32))==bytes([0xa7])*32
        for n,v in saved.items():assert uc.reg_read(getattr(reg,'UC_ARM64_REG_X'+str(n)))==v
        return {'original_return':answer,'original_function_entries':len(entered),
                'entered':entered,'calls':calls,'hash_inputs':hash_inputs,'comparisons':comparisons,
                'write_count':len(writes),'write_bounds_checked':True,'guards_callee_saved_SP_and_return_checked':True}


def main():
    audit=load_module('local_digest_audit',HERE/'audit_original_digest.py')
    p=audit.provider_module();provider=p.FX3PublicDigestProvider()
    image=audit.reader().Image('libsencore.so','a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    verifier=OriginalVerifier(image)
    core_dir=BASE/'stage140-bounded-service-session-controller'
    manifest=core_dir/'final-receipt.json'
    assert sha256(manifest.read_bytes()).hexdigest()=='5cc7e18aea8ae5d407bdf075bd9d8e4031ecf838fac84fa76b870b362ca19816'
    pin=next(x for x in json.loads(manifest.read_text())['files'] if x['path']==(core_dir/'session_controller.py').relative_to(ROOT).as_posix())
    assert sha256((core_dir/'session_controller.py').read_bytes()).hexdigest()==pin['sha256']
    s=load_module('fixed_inert_session',core_dir/'session_controller.py')
    def packet(code,data=b'',salt=0):
        return struct.pack('>HH',(~(code+salt))&0xffff,salt)+data.ljust(512,b'\0')
    patterns=[b'\0'*511,b'\xff'*511,bytes(i%256 for i in range(511))]
    patterns += [(sha256(('fixture'+str(n)).encode()).digest()*16)[:511] for n in range(5)]
    challenges=[b'\x01'+x for x in patterns]
    assert len(challenges)==8 and all(len(x)==512 for x in challenges)
    output=HERE/'run-original-verifier';output.mkdir(exist_ok=False)
    for name,path in [('test-executed.py',Path(__file__)),('provider-executed.py',HERE/'public_digest_provider.py')]:
        (output/name).write_bytes(path.read_bytes())
    results=[]
    def check(name,client,challenge,round_value,expected):
        result=verifier.run(client,challenge,round_value)
        assert result['original_return']==expected,(name,result['original_return'],expected)
        results.append({'name':name,'native_round':round_value,'expected':expected,**result})
    for index in range(3):
        for n,ch in enumerate(challenges):
            digest=provider.compute(8,index,ch)
            check('accept_round'+str(index+1)+'_challenge'+str(n),s.auth_packet(3,b'\x01'+digest),packet(8,ch,3),index+1,0)
        ch=challenges[2];digest=provider.compute(8,index,ch)
        flipped=bytes([digest[0]^1])+digest[1:]
        check('reject_digest_bitflip_round'+str(index+1),s.auth_packet(3,b'\x01'+flipped),packet(8,ch,3),index+1,-2)
        check('reject_wrong_material_round'+str(index+1),s.auth_packet(3,b'\x01'+provider.compute(8,(index+1)%3,ch)),packet(8,ch,3),index+1,-2)
        altered=ch[:17]+bytes([ch[17]^1])+ch[18:]
        check('reject_changed_challenge_round'+str(index+1),s.auth_packet(3,b'\x01'+digest),packet(8,altered,3),index+1,-2)
    ch=challenges[2];client=s.auth_packet(3,b'\x01'+provider.compute(8,0,ch))
    for r in (0,4):check('reject_native_round'+str(r),client,packet(8,ch),r,-3)
    check('reject_legacy_challenge2',client,packet(2,ch),1,-1)
    check('reject_client_command1',s.auth_packet(1),packet(8,ch),1,-1)
    wrong_salt=bytearray(packet(8,ch,3));wrong_salt[3]=4
    check('reject_inconsistent_response_salt',client,bytes(wrong_salt),1,-1)
    assert len(results)==38
    invalid=[(2,0,ch),(8,-1,ch),(8,3,ch),(8,True,ch),(8,0,ch[:-1]),(8,0,ch+b'x'),(8,0,bytearray(ch))]
    for args in invalid:
        try:provider.compute(*args)
        except p.UnsupportedInput:pass
        else:raise AssertionError('provider accepted unsupported input')
    try:p.parse_sha256_material(b"senserKeysSha256 = __import__('os').system('THIS_MUST_NOT_EXECUTE')")
    except (ValueError,p.UnsupportedInput):pass
    else:raise AssertionError('upstream code was not rejected as nonliteral')

    # Controller -> real public digest -> original verifier, all device-side state is declared fixture.
    tag,port='offline-fixture-body','offline-fixture-port'
    target=s.Target(tag,port);limits=s.Limits(60,3,8,0.05,4)
    def dev(mode,driver):return s.Device(tag,port,mode,0x054c,0x0da1 if mode=='MSC' else 0x0336,8 if mode=='MSC' else 255,True,driver)
    session=s.SessionController(target,s.Snapshot(0,(dev('MSC',True),)),limits)
    mode,driver,now='MSC',True,0.0
    current_challenge={};rounds={'MSC':0,'SERVICE':0};integration=[]
    for unused in range(100):
        if session.phase=='WAIT_PHYSICAL':
            session.confirm_physical(tag,True,True,now);break
        action=session.next_inert_action(now)
        assert action is not None and action.inert_only
        if action.kind=='OBSERVE_CACHE':receipt=s.Receipt(action.token,snapshot=s.Snapshot(now,(dev(mode,driver),)))
        elif action.phase=='CAPTURE':
            driver=False;receipt=s.Receipt(action.token,effect_observed=True)
        elif action.phase=='DERIVE_DIGEST':receipt=s.Receipt(action.token,wire=provider.compute_inert_task(action))
        elif action.phase.startswith('AUTH_'):
            side=action.phase[5:];cmd=(~struct.unpack('>H',action.wire[:2])[0])&0xffff
            if cmd==1:
                challenge=challenges[rounds[side]+(0 if side=='MSC' else 3)]
                current_challenge[side]=packet(8,challenge,3)
                receipt=s.Receipt(action.token,wire=current_challenge[side])
            elif cmd==3:
                original=verifier.run(action.wire,current_challenge[side],rounds[side]+1)
                assert original['original_return']==0
                integration.append({'mode':side,'round':rounds[side]+1,**original})
                rounds[side]+=1;receipt=s.Receipt(action.token,wire=packet(4))
            else:
                assert cmd==5 and rounds[side]==3
                if side=='MSC':mode='SERVICE'
                receipt=s.Receipt(action.token,wire=packet(6,b'\x01'))
        else:
            if action.phase=='STOP':mode,driver='MSC',False
            elif action.phase=='RESTORE':driver=True
            receipt=s.Receipt(action.token,effect_observed=True)
        session.accept(receipt,now+0.001);now+=0.01
    else:raise AssertionError('inert integration did not finish')
    assert session.phase=='FLOW_FINISHED' and rounds=={'MSC':3,'SERVICE':3} and len(integration)==6
    assert session.report()['actual_hardware_acceptance'] is False
    result={'status':'PASS_PUBLIC_PROVIDER_WITH_ORIGINAL_FX3_VERIFIER_AND_INERT_CONTROLLER_NOT_LIVE_AUTH',
        'provider_sha256':sha256((HERE/'public_digest_provider.py').read_bytes()).hexdigest(),
        'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'original_core_sha256':sha256(image.raw).hexdigest(),
        'original_function_pins':[{k:f[k] for k in ('name','VA','bytes','sha256')} for f in verifier.functions],
        'native_verifier_cases':results,'native_verifier_case_count':38,'provider_invalid_input_cases':7,'AST_nonliteral_rejected':True,
        'inert_controller_integration':{'original_verifier_rounds':integration,'round_count':6,
            'controller_source_pin':pin,'report':session.report(),
            'challenge_generation_final_auth_acceptance_mode_driver_and_physical_receipts_are_fixtures':True},
        'original_guest_function_entries':sum(x['original_function_entries'] for x in results+integration),
        'original_guest_AArch64_executed':True,
        'EVP_SHA256_and_C_memory_operations_are_CPU_bridges_not_original_camera_OpenSSL_execution':True,
        'no_original_full_NinThread_or_live_authentication_executed':True,
        'raw_public_material_not_printed':True,'Sony_native_host_camera_or_driver_operations':0,
        'goal_complete':False,'persistent_write_release':False}
    with (output/'results.json').open('x') as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(json.dumps({'status':result['status'],'native_cases':38,'positive':24,'negative':14,
                      'integration_original_rounds':6,'original_guest_function_entries':result['original_guest_function_entries'],
                      'actual_camera_operations':0}))


if __name__=='__main__':
    main()
