#!/usr/bin/env python3
"""Compile/run an own C ABI fixture only; real native USB loading is forbidden."""
from pathlib import Path
from hashlib import sha256
from dataclasses import replace
from types import SimpleNamespace
import ctypes as C
import importlib.util
import json
import os
import struct
import subprocess
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


def fixed(directory,want,names):
    data=(directory/'final-receipt.json').read_bytes();assert sha256(data).hexdigest()==want
    records=json.loads(data)['files']
    for name in names:
        path=directory/name;rec=next(x for x in records if x['path']==path.relative_to(ROOT).as_posix())
        assert path.stat().st_size==rec['bytes'] and sha256(path.read_bytes()).hexdigest()==rec['sha256']


def main():
    control=BASE/'stage140-bounded-service-session-controller'
    fixed(control,'5cc7e18aea8ae5d407bdf075bd9d8e4031ecf838fac84fa76b870b362ca19816',['session_controller.py'])
    provider_dir=BASE/'stage145-initial-MSC-native-route'
    fixed(provider_dir,'2aeee45831cca4cfa09c2e4c20500ff0dfbc56cb752fde928998e0223b5f002d',['mode_digest_provider.py'])
    s=load('fixed_wire_controller',control/'session_controller.py')
    p=load('fixed_mode_provider_for_wire',provider_dir/'mode_digest_provider.py')
    w=load('bounded_wire_under_test',HERE/'bounded_wire.py')
    source=json.loads((HERE/'source-and-scope.json').read_text());header=ROOT/source['libusb_header']['path']
    assert sha256(header.read_bytes()).hexdigest()==source['libusb_header']['sha256']
    library_path=HERE/'artifacts/fake-wire.dylib';env=dict(os.environ);env['TMPDIR']=str(HERE/'work-tmp')
    command=['/usr/bin/clang','-dynamiclib','-std=c11','-Wall','-Wextra','-Werror','-I'+str(header.parent),str(HERE/'fake_wire.c'),'-o',str(library_path)]
    subprocess.run(command,env=env,capture_output=True,check=True,timeout=60)
    dependencies=subprocess.check_output(['/usr/bin/otool','-L',str(library_path)],text=True)
    assert all('IOKit' not in line and '/libusb' not in line for line in dependencies.splitlines()[1:])
    library=C.CDLL(str(library_path))
    library.fixture_reset.argtypes=[C.c_int];library.fixture_reset.restype=None
    library.fixture_stat.argtypes=[C.c_int];library.fixture_stat.restype=C.c_int
    library.fixture_set_reply.argtypes=[C.POINTER(C.c_ubyte),C.c_int];library.fixture_set_reply.restype=C.c_int
    library.fixture_copy_out.argtypes=[C.POINTER(C.c_ubyte),C.c_int];library.fixture_copy_out.restype=C.c_int
    def stats():return [library.fixture_stat(n) for n in range(16)]
    def set_reply(value):
        data=(C.c_ubyte*len(value)).from_buffer_copy(value);assert library.fixture_set_reply(data,len(value))==0
    def sent():
        data=(C.c_ubyte*516)();assert library.fixture_copy_out(data,516)==0;return bytes(data)
    def packet(code,data=b''):return struct.pack('>HH',(~code)&0xffff,0)+data.ljust(512,b'\0')
    class Clock:
        def __init__(self):self.now=0.02;self.late_out=False;self.late_control=False;self.invalid=None
        def __call__(self):
            if self.invalid is not None:return self.invalid
            if self.late_out and library.fixture_stat(1):return self.now+4
            if self.late_control and library.fixture_stat(0):return self.now+4
            return self.now
    def binding(mode='MSC'):
        return w.Binding(mode,0x054c,0x0da1 if mode=='MSC' else 0x0336,0x12340000,
            'fixture-body-0001','fixture-port-0001','fixture-owner-'+mode,'fixture-connect-'+mode,
            0x1234 if mode=='MSC' else 0x2345,0x81 if mode=='MSC' else 0x83,2 if mode=='MSC' else 4,512,True,True)
    def observation(b,clock):return w.Observation(clock.now,b.mode,b.identity_tag,b.port_tag,b.owner_generation,b.connection_tag,True,True)
    def device(mode='MSC',driver=False):
        b=binding(mode);return s.Device(b.identity_tag,b.port_tag,mode,b.vid,b.pid,8 if mode=='MSC' else 255,True,driver)
    def setup():
        library.fixture_reset(0);clock=Clock();b=binding();budget=w.SessionBudget(60)
        wire=w.from_fixture(library,b,budget,clock)
        ctl=s.SessionController(s.Target(b.identity_tag,b.port_tag),s.Snapshot(0,(device(driver=True),)),s.Limits(60,3,2,0.01,4))
        first=ctl.next_inert_action(0);ctl.accept(s.Receipt(first.token,effect_observed=True),0.01)
        observed=ctl.next_inert_action(0.01);ctl.accept(s.Receipt(observed.token,snapshot=s.Snapshot(0.01,(device(),))),0.02)
        wire.observe(observation(b,clock));action=ctl.next_inert_action(clock.now)
        assert action.phase=='START_MSC'
        return clock,b,budget,wire,ctl,action
    def auth_setup():
        clock,b,budget,wire,ctl,start=setup();result=wire.execute(ctl,start);assert result.status=='CONTROL_OK'
        ctl.accept(s.Receipt(start.token,raw_return=0),clock.now)
        wire.observe(observation(b,clock));wire.arm_authentication_after_start()
        action=ctl.next_inert_action(clock.now);assert action.phase=='AUTH_MSC'
        return clock,b,budget,wire,ctl,action
    cases=[]
    for scenario,want in [(0,'CONTROL_OK'),(1,'CONTROL_STALL'),(2,'CONTROL_TIMEOUT'),(3,'CONTROL_DISCONNECTED'),
                          (4,'INVALID_CONTROL_LENGTH'),(5,'CONTROL_ERROR')]:
        clock,b,budget,wire,ctl,action=setup();library.fixture_reset(scenario)
        result=wire.execute(ctl,action);assert result.status==want and result.backend_finished
        count=stats();assert count[:3]==[1,0,0] and count[5]==0 and count[6:11]==[0x43,1,0x37ff,0xd7aa,0]
        assert budget.starts['MSC']==1 and not result.device_effect_or_queue_worker_completion_proven
        if scenario in (0,1):
            try:wire.arm_authentication_after_start()
            except w.Rejected:pass
            else:raise AssertionError('pre-start observation armed authentication')
            wire.observe(observation(b,clock));wire.arm_authentication_after_start()
        try:wire.execute(ctl,action)
        except w.Rejected:pass
        else:raise AssertionError('replayed control accepted')
        assert stats()[:3]==[1,0,0]
        cases.append({'name':'control-'+str(scenario),'result':result.public(),'no_automatic_auth_or_replay':True})
    faults=[(10,'SHORT_TRANSFER',1),(11,'BULK_TIMEOUT',1),(12,'BULK_STALL',1),(13,'BULK_DISCONNECTED',1),
            (14,'INVALID_NATIVE_COUNT_OR_STATUS',1),(15,'BUFFER_OR_OUTBOUND_MUTATION',1),
            (16,'BUFFER_OR_OUTBOUND_MUTATION',1),(17,'INVALID_NATIVE_COUNT_OR_STATUS',1),
            (18,'INVALID_NATIVE_COUNT_OR_STATUS',1),(20,'SHORT_TRANSFER',2),(21,'BULK_TIMEOUT',2),
            (22,'BULK_STALL',2),(23,'BULK_DISCONNECTED',2),(24,'INVALID_NATIVE_COUNT_OR_STATUS',2),
            (25,'BUFFER_OR_OUTBOUND_MUTATION',2),(26,'INVALID_NATIVE_COUNT_OR_STATUS',2),(27,'INVALID_NATIVE_COUNT_OR_STATUS',2)]
    for scenario,want,native_calls in faults:
        clock,b,budget,wire,ctl,action=auth_setup();library.fixture_reset(scenario)
        result=wire.execute(ctl,action);assert result.status==want,(scenario,result.public())
        count=stats();assert count[:3]==[0,1,native_calls-1] and count[5]==0 and len(result.calls)==native_calls
        assert budget.failed and budget.exchanges['MSC']==1
        try:wire.execute(ctl,action)
        except w.Rejected:pass
        else:raise AssertionError('failed packet replayed')
        assert stats()[:3]==count[:3]
        cases.append({'name':'bulk-fault-'+str(scenario),'result':result.public(),'counts':count[:6]})
    for code,want in [(8,'AUTH_REPLY_VALID'),(2,'AUTH_REPLY_VALID'),(9,'UNREVIEWED_CHALLENGE')]:
        clock,b,budget,wire,ctl,action=auth_setup();set_reply(packet(code,b'\x01'+b'PRIVATE_FIXTURE_NOT_FOR_LOGGING'.ljust(511,b'x')))
        result=wire.execute(ctl,action);assert result.status==want
        assert sent()==action.wire and 'PRIVATE_FIXTURE_NOT_FOR_LOGGING' not in json.dumps(result.public())
        assert result.protocol_reply_accepted==(code in (2,8))
        cases.append({'name':'reply-family-'+str(code),'result':result.public()})
    for scenario in (0,16):
        clock,b,budget,wire,ctl,action=auth_setup();library.fixture_reset(scenario);clock.late_out=True
        result=wire.execute(ctl,action);want='LATE_RETURN' if scenario==0 else 'BUFFER_OR_OUTBOUND_MUTATION'
        assert result.status==want and stats()[:3]==[0,1,0] and result.backend_finished
        assert budget.hard_unknown==(scenario==16)
        cases.append({'name':'late-write-'+str(scenario),'result':result.public()})
    clock,b,budget,wire,ctl,action=setup();clock.late_control=True
    result=wire.execute(ctl,action);assert result.status=='LATE_RETURN' and stats()[:3]==[1,0,0]
    cases.append({'name':'late-control','result':result.public()})
    clock,b,budget,wire,ctl,action=setup();action=replace(action,deadline=clock.now+0.0004);ctl.pending=action
    result=wire.execute(ctl,action);assert result.status=='CONTROL_OK' and stats()[3]==1 and stats()[5]==0
    cases.append({'name':'submillisecond-is-one-not-unlimited','result':result.public()})
    invalid_bindings=[{'authentication_endpoint_roles_reviewed':False},{'exclusive_ownership_confirmed':False},
        {'pid':0x0336},{'handle':False},{'location_id':0},{'ep_in':0x91},{'ep_out':0x82},
        {'owner_generation':'short'},{'mode':[]}]
    for change in invalid_bindings:
        library.fixture_reset(0)
        try:w.from_fixture(library,replace(binding(),**change),w.SessionBudget(60),Clock())
        except w.Rejected:pass
        else:raise AssertionError('invalid binding accepted')
        assert stats()[:3]==[0,0,0];cases.append({'name':'binding-rejected-'+next(iter(change))})
    invalid_observations=[{'at':-3},{'at':3},{'owner_generation':'different-owner'},
                          {'connection_tag':'different-USB-session'},{'present':False},{'exclusive_owner_alive':False}]
    for change in invalid_observations:
        clock,b,budget,wire,ctl,action=setup()
        try:wire.observe(replace(observation(b,clock),**change))
        except w.Rejected:pass
        else:raise AssertionError('invalid observation accepted')
        assert stats()[:3]==[0,0,0];cases.append({'name':'observation-rejected-'+next(iter(change))})
    clock,b,budget,wire,ctl,action=setup();wire.invalidate()
    try:wire.execute(ctl,action)
    except w.Rejected:pass
    else:raise AssertionError('invalidated handle used')
    assert stats()[:3]==[0,0,0];cases.append({'name':'invalidated handle rejected'})
    class NoNativeLookup:
        def __getattr__(self,name):raise AssertionError('live gate must precede native lookup: '+name)
    with patch.object(C,'CDLL',side_effect=AssertionError('no real native loader')):
        try:w.from_live(NoNativeLookup(),binding(),w.SessionBudget(60),Clock())
        except w.Rejected:pass
        else:raise AssertionError('cache-only authority admitted live wire')
        cases.append({'name':'current live authorization rejected before native binding or load'})
        fake_goal={'authorization':{'service_auth_mode_or_stop':True,'driver_change':True,
            'Mac_limited_service_pilot_authorized':True,'Mac_limited_service_pilot_target':{'wrong':'target'}},
            'prepared_first_device_trial':{'Mac_limited_service_pilot_released':True}}
        with patch.object(Path,'read_text',return_value=json.dumps(fake_goal)):
            try:w.from_live(NoNativeLookup(),binding(),w.SessionBudget(60),Clock())
            except w.Rejected:pass
            else:raise AssertionError('wrong live target passed the native binding gate')
        cases.append({'name':'wrong target under synthetic allowed flags rejected before native binding'})
    packet_changes=[('unknown auth command',lambda a:replace(a,wire=s.auth_packet(0xff01))),
        ('challenge nonzero payload',lambda a:replace(a,wire=s.auth_packet(1,b'\x01'))),
        ('request salt',lambda a:replace(a,wire=a.wire[:2]+b'\x00\x01'+a.wire[4:])),
        ('short auth frame',lambda a:replace(a,wire=a.wire[:-1])),
        ('mutable auth frame',lambda a:replace(a,wire=bytearray(a.wire))),
        ('kind mismatch',lambda a:replace(a,kind='CAPTURE'))]
    for label,change in packet_changes:
        clock,b,budget,wire,ctl,action=auth_setup();library.fixture_reset(0)
        invalid=change(action);ctl.pending=invalid
        try:wire.execute(ctl,invalid)
        except w.Rejected:pass
        else:raise AssertionError(label+' reached native wire')
        assert stats()[:3]==[0,0,0];cases.append({'name':'packet rejected '+label})
    for label,change in [('control setup changed',lambda a:replace(a,wire=a.wire[:2]+b'\x00'+a.wire[3:])),
                         ('non-wire operation',lambda a:replace(a,phase='CAPTURE',kind='CAPTURE',wire=b'')),
                         ('invalid token',lambda a:replace(a,token='bad'))]:
        clock,b,budget,wire,ctl,action=setup();invalid=change(action);ctl.pending=invalid;ctl.phase=invalid.phase
        try:wire.execute(ctl,invalid)
        except w.Rejected:pass
        else:raise AssertionError(label+' reached native wire')
        assert stats()[:3]==[0,0,0];cases.append({'name':label+' rejected'})
    for label,clock_value in [('expired',3.02),('stale ownership',3.0),('backwards',0.01)]:
        clock,b,budget,wire,ctl,action=setup();clock.now=clock_value
        try:wire.execute(ctl,action)
        except (w.Rejected,w.WireFault):pass
        else:raise AssertionError(label+' clock/state reached native wire')
        assert stats()[:3]==[0,0,0];cases.append({'name':label+' before IO rejected'})
    for label,value in [('NaN',float('nan')),('infinite',float('inf')),('bool',True)]:
        clock,b,budget,wire,ctl,action=setup();clock.invalid=value
        try:wire.execute(ctl,action)
        except w.WireFault:pass
        else:raise AssertionError('invalid clock accepted')
        assert budget.hard_unknown and stats()[:3]==[0,0,0];cases.append({'name':'invalid '+label+' clock before IO'})
    clock,b,budget,wire,ctl,action=setup()
    try:w.from_fixture(library,b,budget,clock)
    except w.Rejected:pass
    else:raise AssertionError('automatic reopen of same mode accepted')
    try:w.from_fixture(library,replace(binding('SERVICE'),identity_tag='another-body-0001'),budget,clock)
    except w.Rejected:pass
    else:raise AssertionError('shared session budget moved to another body')
    assert stats()[:3]==[0,0,0];cases.append({'name':'duplicate owner and different body rejected'})
    result=wire.execute(ctl,action);new_action=replace(action,token=action.token+'-new');ctl.pending=new_action
    try:wire.execute(ctl,new_action)
    except w.Rejected:pass
    else:raise AssertionError('new token bypassed start budget')
    assert stats()[:3]==[1,0,0];cases.append({'name':'new token cannot bypass single start'})
    clock,b,budget,wire,ctl,action=auth_setup();library.fixture_reset(0);budget.exchanges['MSC']=7
    try:wire.execute(ctl,action)
    except w.Rejected:pass
    else:raise AssertionError('authentication exchange budget bypassed')
    assert stats()[:3]==[0,0,0];cases.append({'name':'eighth auth exchange refused before IO'})
    clock,b,budget,wire,ctl,action=auth_setup();library.fixture_reset(0)
    def native_exception(*args):raise RuntimeError('own Python call boundary fixture')
    wire.api.libusb_bulk_transfer=native_exception
    result=wire.execute(ctl,action)
    assert result.status=='NATIVE_CALL_EXCEPTION' and not result.backend_finished and budget.hard_unknown
    ctl.accept(s.Receipt(action.token,outcome='pending',operation_finished=False),clock.now)
    assert ctl.phase=='UNKNOWN' and ctl.next_inert_action(clock.now) is None and stats()[:3]==[0,0,0]
    cases.append({'name':'native-call boundary exception keeps controller UNKNOWN','result':result.public()})
    clock,b,budget,wire,ctl,action=auth_setup();library.fixture_reset(0)
    calls_after_out=[0]
    def expires_between_calls():
        if library.fixture_stat(1):
            calls_after_out[0]+=1
            if calls_after_out[0]>=2:return clock.now+4
        return clock.now
    wire.clock=expires_between_calls
    result=wire.execute(ctl,action)
    assert result.status=='DEADLINE_BEFORE_NEXT_IO' and stats()[:3]==[0,1,0]
    cases.append({'name':'deadline between write and read does not issue read','result':result.public()})
    # One completed timeout may admit only the single cleanup STOP after a NEW
    # matching owner observation. No auth or packet retry occurs.
    clock,b,budget,wire,ctl,action=auth_setup();library.fixture_reset(11)
    result=wire.execute(ctl,action);assert result.status=='BULK_TIMEOUT'
    ctl.accept(s.Receipt(action.token,outcome='error',raw_return=-7),clock.now)
    check=ctl.next_inert_action(clock.now);assert check.kind=='OBSERVE_CACHE'
    ctl.accept(s.Receipt(check.token,snapshot=s.Snapshot(clock.now,(device(),))),clock.now)
    stop=ctl.next_inert_action(clock.now);assert stop.phase=='STOP'
    try:wire.execute(ctl,stop)
    except w.Rejected:pass
    else:raise AssertionError('old equal-time observation admitted cleanup')
    wire.observe(observation(b,clock));library.fixture_reset(0)
    cleanup=wire.execute(ctl,stop);assert cleanup.status=='CONTROL_OK' and budget.stop and stats()[:3]==[1,0,0]
    assert stats()[8:10]==[0xc800,0x2855]
    repeated=replace(stop,token=stop.token+'-another');ctl.pending=repeated
    try:wire.execute(ctl,repeated)
    except w.Rejected:pass
    else:raise AssertionError('new token bypassed sole STOP')
    assert stats()[:3]==[1,0,0]
    cases.append({'name':'completed timeout cleanup after new same-time owner observation','result':cleanup.public()})
    # Two complete controller flows use own fixture device/driver observations.
    flows=[]
    for family in (2,8):
        library.fixture_reset(0);clock=Clock();clock.now=0.0;budget=w.SessionBudget(60);provider=p.ModeDigestProvider()
        ctl=s.SessionController(s.Target(binding().identity_tag,binding().port_tag),s.Snapshot(0,(device(driver=True),)),s.Limits(60,3,2,0.01,4))
        mode,driver='MSC',True;wires={};wire_actions=[];rounds={'MSC':0,'SERVICE':0}
        for unused in range(120):
            if ctl.phase=='WAIT_PHYSICAL':ctl.confirm_physical(binding().identity_tag,True,True,clock.now);break
            action=ctl.next_inert_action(clock.now);assert action is not None
            if action.kind=='OBSERVE_CACHE':receipt=s.Receipt(action.token,snapshot=s.Snapshot(clock.now,(device(mode,driver),)))
            elif action.phase=='CAPTURE':
                driver=False;b=binding(mode);wires[mode]=w.from_fixture(library,b,budget,clock)
                receipt=s.Receipt(action.token,effect_observed=True)
            elif action.phase=='CLOSE_STALE':wires['MSC'].invalidate();receipt=s.Receipt(action.token,effect_observed=True)
            elif action.phase=='OPEN_SERVICE':
                b=binding(mode);wires[mode]=w.from_fixture(library,b,budget,clock);receipt=s.Receipt(action.token,effect_observed=True)
            elif action.phase=='DERIVE_DIGEST':receipt=s.Receipt(action.token,wire=provider.compute_bound_task(provider.bind_inert_task(ctl,action)))
            elif action.phase.startswith(('START_','AUTH_')) or action.phase=='STOP':
                wire=wires[mode];wire.observe(observation(binding(mode),clock))
                if action.phase.startswith('AUTH_'):
                    command=(~struct.unpack('>H',action.wire[:2])[0])&0xffff
                    if command==1:set_reply(packet(family if mode=='MSC' else 8,b'\x01'+bytes([rounds[mode]+7])*511))
                    elif command==3:set_reply(packet(4));rounds[mode]+=1
                    else:assert command==5;set_reply(packet(6,b'\x01'))
                result=wire.execute(ctl,action);assert result.status in ('CONTROL_OK','AUTH_REPLY_VALID'),result.public()
                if action.phase.startswith('AUTH_'):assert sent()==action.wire
                wire_actions.append({'phase':action.phase,**result.public()})
                receipt=s.Receipt(action.token,wire=result.reply,raw_return=result.calls[-1]['raw_return'])
                if action.phase.startswith('START_'):
                    wire.observe(observation(binding(mode),clock));wire.arm_authentication_after_start()
                if action.phase=='AUTH_MSC' and budget.auth['MSC']['complete']:mode='SERVICE'
                if action.phase=='STOP':mode,driver='MSC',False
            else:
                if action.phase=='RESTORE':driver=True
                if action.phase=='DISPOSE':wires['SERVICE'].invalidate()
                receipt=s.Receipt(action.token,effect_observed=True)
            clock.now+=0.01;ctl.accept(receipt,clock.now)
        else:raise AssertionError('fixture flow did not finish')
        assert ctl.phase=='FLOW_FINISHED' and budget.starts=={'MSC':1,'SERVICE':1} and budget.exchanges=={'MSC':7,'SERVICE':7} and budget.stop
        assert stats()[:3]==[3,14,14] and stats()[5]==0 and len(budget.tokens)==17
        flows.append({'MSC_reference_family':family,'wire_actions':wire_actions,'native_fixture_call_counts':stats()[:6],
            'controller_result':ctl.report(),'all_hardware_identity_owner_capture_driver_mode_auth_replies_and_physical_acceptance_are_fixtures':True})
    out=HERE/'run-wire-tests';out.mkdir(exist_ok=False)
    for name,file in [('wire-executed.py','bounded_wire.py'),('test-executed.py','test_bounded_wire.py'),('fixture-executed.c','fake_wire.c')]:
        (out/name).write_bytes((HERE/file).read_bytes())
    report={'status':'PASS_OWNED_HANDLE_WIRE_ABI_FAULTS_AND_INERT_CONTROLLER_FLOWS_NO_REAL_USB',
        'case_count':len(cases),'cases':cases,'inert_flows':flows,'flow_count':len(flows),
        'compile_argv':command,'fixture_dependencies':dependencies,'fixture_library':{
            'path':library_path.relative_to(ROOT).as_posix(),'bytes':library_path.stat().st_size,'sha256':sha256(library_path.read_bytes()).hexdigest()},
        'wire_sha256':sha256((HERE/'bounded_wire.py').read_bytes()).hexdigest(),
        'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'real_USB_library_loaded_initialized_device_interface_claim_or_driver_operations':0,
        'live_factory_currently_rejects_before_native_binding':True,'goal_complete':False,'persistent_write_release':False}
    with (out/'results.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':report['status'],'cases':len(cases),'inert_flows':len(flows),
                      'fixture_counts_per_flow':[x['native_fixture_call_counts'][:3] for x in flows],
                      'real_USB_operations':0}))


if __name__=='__main__':main()
