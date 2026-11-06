#!/usr/bin/env python3
"""Separate public initial-MSC reference checks from original service guest checks."""
from pathlib import Path
from hashlib import sha1,sha256
import ast
import copy
import importlib.util
import json
import struct
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def fixed(directory,digest,names):
    raw=(directory/'final-receipt.json').read_bytes();assert sha256(raw).hexdigest()==digest
    records=json.loads(raw)['files']
    for name in names:
        path=directory/name;record=next(x for x in records if x['path']==path.relative_to(ROOT).as_posix())
        assert sha256(path.read_bytes()).hexdigest()==record['sha256'] and path.stat().st_size==record['bytes']


def main():
    prior=BASE/'stage141-public-auth-digest-and-original-verifier'
    fixed(prior,'2800a952e5a4a960ba9c98463048cdebf6e4f27a0c1ae8b48fe6be3cae162866',
          ['test_provider_with_original.py','audit_original_digest.py','upstream/crypto.py','public_digest_provider.py'])
    source=BASE/'stage134-backup-reader-scope-and-service-extension'
    fixed(source,'5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d',['upstream/sony.py','audit_readers.py'])
    control=BASE/'stage140-bounded-service-session-controller'
    fixed(control,'5cc7e18aea8ae5d407bdf075bd9d8e4031ecf838fac84fa76b870b362ca19816',['session_controller.py'])
    p=load('mode_provider_under_test',HERE/'mode_digest_provider.py')
    s=load('fixed_mode_controller',control/'session_controller.py')
    original=load('fixed_service_verifier',prior/'test_provider_with_original.py')
    audit=load('fixed_service_audit',prior/'audit_original_digest.py')
    image=audit.reader().Image('libsencore.so','a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    verifier=original.OriginalVerifier(image)
    tree=ast.parse((source/'upstream/sony.py').read_text())
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='SonySenserAuthDevice')
    auth=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='authenticate')
    branch=next(x.value for x in ast.walk(auth) if isinstance(x,ast.Assign) and isinstance(x.value,ast.IfExp)
                and any(isinstance(t,ast.Name) and t.id=='data' for t in x.targets))
    assert ast.unparse(branch)=='data + keys[i] if self.driver.getId()[1] == 822 else data[:4]'
    crypto=ast.parse((prior/'upstream/crypto.py').read_text())
    faulty=next(x for x in crypto.body if isinstance(x,ast.FunctionDef) and x.name=='sha1_faulty')
    returned=next(x.value for x in faulty.body if isinstance(x,ast.Return))
    assert ast.unparse(returned)=='sha1(message, len(message) & 31)' and 4&31==4
    provider=p.ModeDigestProvider();msc=p.Profile('MSC',0x054c,0x0da1);service=p.Profile('SERVICE',0x054c,0x0336)
    challenges=[b'\x01'+bytes(511),b'\x01'+b'\xff'*511,bytes(n%256 for n in range(512))]
    challenges += [(sha256(('bounded-fixture'+str(n)).encode()).digest()*16) for n in range(5)]
    msc_results=[]
    for family in (2,8):
        for index in range(3):
            for n,ch in enumerate(challenges):
                want=(sha1 if family==2 else sha256)(ch[:4]).digest()
                got=provider.compute(msc,family,index,ch);assert got==want
                changed=ch[:4]+bytes(x^0xff for x in ch[4:])
                assert provider.compute(msc,family,index,changed)==got
                assert provider.compute(msc,family,(index+1)%3,ch)==got
                msc_results.append({'family':family,'round_index':index,'fixture':n,'digest_bytes':len(got),
                    'digest_fingerprint':sha256(got).hexdigest(),'tail_and_round_material_not_used':True,
                    'initial_FX3_native_verifier_or_device_acceptance_proven':False})
    def packet(code,data=b'',salt=0):return struct.pack('>HH',(~(code+salt))&0xffff,salt)+data.ljust(512,b'\0')
    native=[]
    for index in range(3):
        for n,ch in enumerate(challenges[:4]):
            for label,digest,want in [('service',provider.compute(service,8,index,ch),0),
                                    ('MSC_reference_wrong_for_service',provider.compute(msc,8,index,ch),-2)]:
                row=verifier.run(s.auth_packet(3,b'\x01'+digest),packet(8,ch,3),index+1)
                assert row['original_return']==want
                native.append({'label':label,'round_index':index,'fixture':n,'expected':want,**row})
    invalid=[(p.Profile('MSC',0x054c,0x0336),8,0,challenges[0]),
             (p.Profile('SERVICE',0x054c,0x0da1),8,0,challenges[0]),
             (p.Profile('MSC',0x1234,0x0da1),8,0,challenges[0]),
             (p.Profile([],0x054c,0x0da1),8,0,challenges[0]),
             (msc,True,0,challenges[0]),(msc,8,True,challenges[0]),(msc,8,3,challenges[0]),
             (msc,8,0,bytearray(challenges[0])),(msc,8,0,challenges[0][:-1]),
             (service,2,0,challenges[0]),(msc,9,0,challenges[0])]
    for args in invalid:
        try:provider.compute(*args)
        except p.UnsupportedInput:pass
        else:raise AssertionError('unsupported profile/input accepted')
    integrations=[];bindings=[]
    for msc_family in (2,8):
        prov=p.ModeDigestProvider();tag,port='inert-body-fixture','inert-port-fixture'
        def device(mode,driver):return s.Device(tag,port,mode,0x054c,0x0da1 if mode=='MSC' else 0x0336,8 if mode=='MSC' else 255,True,driver)
        ctl=s.SessionController(s.Target(tag,port),s.Snapshot(0,(device('MSC',True),)),s.Limits(60,3,8,0.05,4))
        mode,driver,now='MSC',True,0.0;rounds={'MSC':0,'SERVICE':0};active={};checks=[]
        for unused in range(100):
            if ctl.phase=='WAIT_PHYSICAL':ctl.confirm_physical(tag,True,True,now);break
            action=ctl.next_inert_action(now);assert action is not None
            if action.kind=='OBSERVE_CACHE':receipt=s.Receipt(action.token,snapshot=s.Snapshot(now,(device(mode,driver),)))
            elif action.phase=='CAPTURE':driver=False;receipt=s.Receipt(action.token,effect_observed=True)
            elif action.phase=='DERIVE_DIGEST':
                task=prov.bind_inert_task(ctl,action)
                if mode=='MSC' and rounds[mode]==0:
                    for label,change in [('mode',('mode','SERVICE')),('resume',('auth_resume','AUTH_SERVICE')),('time',('last_now',action.deadline+1))]:
                        field,value=change;before=getattr(ctl,field);setattr(ctl,field,value)
                        try:prov.bind_inert_task(ctl,action)
                        except p.UnsupportedInput:bindings.append({'family':msc_family,'rejected':label})
                        else:raise AssertionError('binding '+label+' accepted')
                        setattr(ctl,field,before)
                    try:prov.bind_inert_task(ctl,copy.copy(action))
                    except p.UnsupportedInput:bindings.append({'family':msc_family,'rejected':'nonpending action copy'})
                    else:raise AssertionError('copied action accepted')
                digest=prov.compute_bound_task(task)
                try:prov.compute_bound_task(task)
                except p.UnsupportedInput:bindings.append({'family':msc_family,'rejected':'duplicate task'})
                else:raise AssertionError('duplicate digest task accepted')
                receipt=s.Receipt(action.token,wire=digest)
            elif action.phase.startswith('AUTH_'):
                side=action.phase[5:];command=(~struct.unpack('>H',action.wire[:2])[0])&0xffff
                if command==1:
                    challenge=challenges[rounds[side]+(0 if side=='MSC' else 3)]
                    active[side]=(challenge,packet(msc_family if side=='MSC' else 8,challenge,3))
                    receipt=s.Receipt(action.token,wire=active[side][1])
                elif command==3:
                    ch,wire=active[side]
                    if side=='MSC':
                        expected=(sha1 if msc_family==2 else sha256)(ch[:4]).digest()
                        assert action.wire[4:5]==b'\x01' and action.wire[5:5+len(expected)]==expected
                        checks.append({'mode':side,'round':rounds[side]+1,'reference_only':True,'family':msc_family})
                    else:
                        row=verifier.run(action.wire,wire,rounds[side]+1);assert row['original_return']==0
                        checks.append({'mode':side,'round':rounds[side]+1,'reference_only':False,**row})
                    rounds[side]+=1;receipt=s.Receipt(action.token,wire=packet(4))
                else:
                    assert command==5 and rounds[side]==3
                    receipt=s.Receipt(action.token,wire=packet(6,b'\x01'))
                    if side=='MSC':mode='SERVICE'
            else:
                receipt=s.Receipt(action.token,effect_observed=True)
                if action.phase=='STOP':mode,driver='MSC',False
                elif action.phase=='RESTORE':driver=True
            now+=0.02;ctl.accept(receipt,now)
        else:raise AssertionError('inert flow did not end')
        assert ctl.phase=='FLOW_FINISHED' and rounds=={'MSC':3,'SERVICE':3} and len(prov.used_tokens)==6
        integrations.append({'MSC_reference_family':msc_family,'rounds':checks,'controller_result':ctl.report(),
            'all_device_identity_capture_driver_mode_final_acceptance_and_physical_values_are_fixtures':True})
    out=HERE/'run-mode-tests';out.mkdir(exist_ok=False)
    (out/'provider-executed.py').write_bytes((HERE/'mode_digest_provider.py').read_bytes())
    (out/'test-executed.py').write_bytes(Path(__file__).read_bytes())
    entries=sum(x['original_function_entries'] for x in native)
    entries+=sum(x['original_function_entries'] for flow in integrations for x in flow['rounds'] if x['mode']=='SERVICE')
    result={'status':'PASS_EXPLICIT_MODE_PROVIDER_MSC_PUBLIC_REFERENCE_AND_ORIGINAL_SERVICE_GUEST_NOT_INITIAL_MSC_NATIVE_OR_DEVICE_AUTH',
        'MSC_reference_cases':msc_results,'MSC_reference_case_count':len(msc_results),'native_service_cases':native,
        'native_service_case_count':len(native),'invalid_input_cases':len(invalid),'binding_rejections':bindings,
        'inert_integrations':integrations,'original_guest_function_entries':entries,
        'source_branch_AST':ast.unparse(branch),'legacy_faulty_SHA1_four_byte_length_equivalence':True,
        'downloaded_source_executed':False,'new_USB_or_camera_driver_operations':0,
        'initial_FX3_MSC_verifier_located_or_actual_authentication_proven':False,
        'provider_sha256':sha256((HERE/'mode_digest_provider.py').read_bytes()).hexdigest(),
        'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'goal_complete':False,'persistent_write_release':False}
    with (out/'results.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'MSC_reference_cases':len(msc_results),'native_service_cases':len(native),
        'invalid_inputs':len(invalid),'binding_rejections':len(bindings),'inert_flows':len(integrations),
        'original_guest_function_entries':entries,'USB_operations':0}))


if __name__=='__main__':main()
