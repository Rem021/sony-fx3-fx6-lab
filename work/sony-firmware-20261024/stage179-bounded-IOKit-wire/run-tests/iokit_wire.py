"""Bounded IOKit650 wire policy for our typed same-process fixture context.

No loader, enumeration, open/claim, detach/attach, reset, halt-clear, file API or
module command exists here. Real construction remains behind separate live gates.
All body identity, connection and ownership evidence must come from a future owner.
"""
from dataclasses import dataclass,field
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
import iokit_fixture_api as native
import json
import math
import struct
import threading

BASE=Path(__file__).resolve().parent.parent
START=bytes.fromhex('4301ff37aad70000')
STOP=bytes.fromhex('430100c855280000')
GUARD=bytes([0xc7])*32
N=516


class Rejected(ValueError):pass


class WireFault(RuntimeError):
    def __init__(self,status,hard=False):self.status,self.hard=status,hard


@dataclass(frozen=True)
class Binding:
    mode:str
    vid:int
    pid:int
    location_id:int
    identity_tag:str=field(repr=False)
    port_tag:str=field(repr=False)
    owner_generation:str=field(repr=False)
    connection_tag:str=field(repr=False)
    handle:native.ContextRef=field(repr=False)
    ep_in:int
    ep_out:int
    max_packet:int
    exclusive_ownership_confirmed:bool=False
    authentication_endpoint_roles_reviewed:bool=False


@dataclass(frozen=True)
class Observation:
    at:float
    mode:str
    identity_tag:str=field(repr=False)
    port_tag:str=field(repr=False)
    owner_generation:str=field(repr=False)
    connection_tag:str=field(repr=False)
    present:bool=True
    exclusive_owner_alive:bool=False


@dataclass(frozen=True)
class WireResult:
    token:str
    status:str
    backend_finished:bool
    calls:tuple
    reply:bytes=field(default=b'',repr=False)
    protocol_reply_accepted:bool=False
    device_effect_or_queue_worker_completion_proven:bool=field(default=False,init=False)

    def public(self):
        return {'token':self.token,'status':self.status,'backend_finished':self.backend_finished,
                'calls':list(self.calls),'response_bytes':len(self.reply),
                'protocol_reply_accepted':self.protocol_reply_accepted,
                'device_effect_or_queue_worker_completion_proven':False}


class SessionBudget:
    def __init__(self,session_deadline):
        if type(session_deadline) not in (int,float) or not math.isfinite(session_deadline):raise Rejected('invalid session deadline')
        self.deadline=session_deadline;self.last_time=None;self.tokens=set();self.owners={};self.target=None
        self.starts={'MSC':0,'SERVICE':0};self.exchanges={'MSC':0,'SERVICE':0};self.stop=False
        self.failed=False;self.hard_unknown=False;self.last_fault=None
        self.auth={m:{'next':1,'round':0,'family':None,'complete':False} for m in self.starts}
        self.guard=threading.Lock()


@contextmanager
def _exclusive(budget):
    if not budget.guard.acquire(blocking=False):raise Rejected('another session operation is active; no wait or native retry')
    try:yield
    finally:budget.guard.release()


def _serialized(method):
    @wraps(method)
    def invoke(self,*args,**kwargs):
        with _exclusive(self.budget):return method(self,*args,**kwargs)
    return invoke


def live_authority(binding):
    goal=json.loads((BASE/'GOAL_STATUS.json').read_text());a=goal['authorization'];p=goal['prepared_first_device_trial']
    if a.get('service_auth_mode_or_stop') is not True or a.get('driver_change') is not True or \
       a.get('Mac_limited_service_pilot_authorized') is not True or p.get('Mac_limited_service_pilot_released') is not True:
        raise Rejected('owned-handle service wire has no separately reviewed live authorization')
    target=a.get('Mac_limited_service_pilot_target',{})
    if target!={'identity_tag':binding.identity_tag,'port_tag':binding.port_tag,'locationID':binding.location_id,
               'model':'ILME-FX3','firmware':'7.02'}:
        raise Rejected('live target differs from the single reviewed body')


def from_live(library,binding,budget,clock):
    live_authority(binding)  # Before even looking up a native transfer function.
    raise Rejected('real owner IPC and same-process native integration are not implemented; no live pointer import')


def from_fixture(library,binding,budget,clock):
    return OwnedWire(library,binding,budget,clock,live=False)


class OwnedWire:
    def __init__(self,library,binding,budget,clock,*,live):
        if live:raise Rejected('live owner integration is unavailable')
        if type(library) is not native.FixtureLibrary:raise Rejected('typed marked IOKit fixture API required')
        if type(binding) is not Binding or type(budget) is not SessionBudget:raise Rejected('typed binding and shared session budget required')
        b=binding
        if type(b.mode) is not str or (b.mode,b.vid,b.pid) not in {('MSC',0x054c,0x0da1),('SERVICE',0x054c,0x0336)}:raise Rejected('unsupported mode/identity')
        if any(type(v) is not int for v in (b.vid,b.pid,b.location_id,b.ep_in,b.ep_out,b.max_packet)):
            raise Rejected('binding integer types required')
        if not 0<b.location_id<=0xffffffff:raise Rejected('invalid location')
        try:library.validate(b.handle,b.mode)
        except native.Rejected as error:raise Rejected(str(error)) from None
        if any(type(v) is not str or not 8<=len(v)<=128 for v in (b.identity_tag,b.port_tag,b.owner_generation,b.connection_tag)):
            raise Rejected('missing identity or connection/ownership generation')
        if (b.ep_in,b.ep_out,b.max_packet)!=( (0x81,2,512) if b.mode=='MSC' else (0x83,4,512) ):
            raise Rejected('invalid reviewed bulk endpoint profile')
        if b.exclusive_ownership_confirmed is not True or b.authentication_endpoint_roles_reviewed is not True:
            raise Rejected('a descriptor alone proves neither ownership nor authentication roles')
        with _exclusive(budget):
            target=(b.identity_tag,b.port_tag,b.location_id)
            if budget.target is not None and budget.target!=target:raise Rejected('shared budget cannot move to another body')
            if b.mode in budget.owners:raise Rejected('one owned wire per mode; no automatic reopen')
            self.api=library;self.binding=b;self.budget=budget;self.clock=clock;self.live=live
            self.observed_at=None;self.start_return=None;self.start_at=None;self.armed=False;self.busy=False;self.closed=False
            self.observation_version=0;self.start_observation_version=None;self.fault_observation_version=-1
            budget.target=target;budget.owners[b.mode]=(b.owner_generation,b.connection_tag)

    def _time(self):
        now=self.clock()
        if type(now) not in (int,float) or not math.isfinite(now) or self.budget.last_time is not None and now<self.budget.last_time:
            self.budget.hard_unknown=True;raise WireFault('CLOCK_INVALID',True)
        self.budget.last_time=now;return now

    @_serialized
    def observe(self,observation):
        if self.busy or self.closed:raise Rejected('cannot rebind a pending or invalidated handle')
        now=self._time();b=self.binding;o=observation
        if type(o) is not Observation or type(o.at) not in (int,float) or not math.isfinite(o.at) or not 0<=now-o.at<=2:
            raise Rejected('fresh owner observation required')
        if (o.mode,o.identity_tag,o.port_tag,o.owner_generation,o.connection_tag)!=(b.mode,b.identity_tag,b.port_tag,b.owner_generation,b.connection_tag) \
           or o.present is not True or o.exclusive_owner_alive is not True:
            raise Rejected('same connection, body or exclusive owner not confirmed')
        if self.api.refresh(b.handle)!=0:raise Rejected('same-process owner generation refresh failed')
        self.observed_at=o.at
        self.observation_version+=1

    @_serialized
    def arm_authentication_after_start(self):
        now=self._time()
        if self.closed or self.budget.failed or self.budget.hard_unknown or self.start_return not in ('CONTROL_OK','CONTROL_STALL') or \
           self.start_at is None or self.observed_at is None or not self.start_at<=self.observed_at<=now or now-self.observed_at>2:
            raise Rejected('completed start and new matching owner observation required; no automatic authentication')
        if self.start_observation_version is None or self.observation_version<=self.start_observation_version:
            raise Rejected('an observation made before start cannot arm authentication')
        self.armed=True

    @_serialized
    def invalidate(self):
        if self.busy:raise Rejected('owner must not invalidate a handle while native work may be pending')
        if self.api.invalidate(self.binding.handle)!=0:raise Rejected('native context is still pending or invalid')
        self.closed=True;self.armed=False

    def _remaining(self,action):
        now=self._time()
        if now>=min(action.deadline,self.budget.deadline):raise WireFault('DEADLINE_BEFORE_NEXT_IO')
        return max(1,min(1000,math.ceil((min(action.deadline,self.budget.deadline)-now)*1000)))

    def _validate(self,controller,action):
        b=self.binding;now=self._time()
        if self.live:live_authority(b)
        if self.busy or self.closed or self.budget.hard_unknown:raise Rejected('active, invalidated or unresolved backend state')
        if controller.pending is not action or controller.phase!=action.phase or action.inert_only is not True or action.kind!=action.phase:
            raise Rejected('only the current pending controller intent may be dispatched')
        if controller.mode!=b.mode or controller.target.identity_tag!=b.identity_tag or controller.target.port_tag!=b.port_tag or \
           controller.target.model!='ILME-FX3' or controller.target.firmware!='7.02' or controller.handle is not True or controller.captured is not True:
            raise Rejected('controller target or owned handle differs')
        if type(action.token) is not str or not 8<=len(action.token)<=128 or action.token in self.budget.tokens:raise Rejected('invalid or replayed intent')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (action.issued_at,action.deadline)) or not action.issued_at<=now<action.deadline<=self.budget.deadline:
            raise Rejected('invalid or expired action deadline')
        if self.observed_at is None or not 0<=now-self.observed_at<=2:raise Rejected('ownership observation is stale')
        if type(action.wire) is not bytes:raise Rejected('immutable wire required')
        phase=action.phase
        if phase=='START_'+b.mode:
            if action.wire!=START or self.budget.starts[b.mode] or self.budget.failed or self.budget.stop:raise Rejected('start shape, sequence or budget rejected')
        elif phase=='AUTH_'+b.mode:
            state=self.budget.auth[b.mode]
            if not self.armed or self.budget.failed or self.budget.stop or self.budget.exchanges[b.mode]>=7 or state['complete'] or len(action.wire)!=N:
                raise Rejected('authentication is not admitted')
            cmd,salt=struct.unpack('>HH',action.wire[:4]);cmd=(~cmd)&0xffff
            if salt or cmd!=state['next']:raise Rejected('unexpected authentication command sequence')
            payload=action.wire[4:]
            if cmd in (1,5) and any(payload):raise Rejected('challenge/final requests must have zero payload')
            if cmd==3:
                size=20 if state['family']==2 else 32
                if payload[0]!=1 or any(payload[1+size:]):raise Rejected('only the declared digest payload is admitted')
        elif phase=='STOP':
            if action.wire!=STOP or self.budget.stop or not any(self.budget.starts.values()):raise Rejected('stop shape or single-use budget rejected')
            if self.budget.last_fault is not None and self.observed_at<self.budget.last_fault:raise Rejected('cleanup needs observation after the last failure')
            if self.budget.failed and self.observation_version<=self.fault_observation_version:raise Rejected('cleanup needs a new observation, even at an equal timestamp')
        else:raise Rejected('wire layer has no such operation')

    def _native(self,action,label,calls,payload):
        timeout=self._remaining(action)
        try:
            result,reply=self.api.transfer(self.binding.handle,label,payload,
                min(action.deadline,self.budget.deadline),timeout)
        except Exception:
            self.budget.hard_unknown=True;raise WireFault('NATIVE_CALL_EXCEPTION',True)
        calls.append({'operation':label,**result})
        now=self._time()
        status=result['status']
        if status not in (0,3):
            name=result['adapter_status']
            mapping={'GONE':'DISCONNECTED','SHORT':'SHORT_TRANSFER','BUFFER':'BUFFER_OR_OUTBOUND_MUTATION',
                'BAD_COUNT':'INVALID_NATIVE_COUNT','LATE':'LATE_RETURN','CLOCK':'CLOCK_INVALID',
                'OWNER':'OWNER_LOST','CANCEL':'CANCEL_REQUESTED'}
            message=mapping.get(name,('CONTROL_' if label=='CONTROL' else 'BULK_')+name)
            # Unknown progress after a timeout/error remains unresolved; no automatic STOP/retry.
            raise WireFault(message,status in native.HARD)
        if now>action.deadline or now>self.budget.deadline:raise WireFault('LATE_RETURN',True)
        return status,reply,now

    def _bulk(self,action,incoming,calls):
        label='BULK_IN' if incoming else 'BULK_OUT'
        status,reply,unused=self._native(action,label,calls,bytes(N) if incoming else action.wire)
        if status==3:raise WireFault('BULK_STALL')
        # WritePipeTO has no actual byte count. rc0 is request return, not body completion.
        if incoming and (not calls[-1]['actual_count_known'] or calls[-1]['transferred']!=N or len(reply)!=N):
            raise WireFault('INVALID_NATIVE_COUNT',True)
        return reply

    def _accept_reply(self,wire):
        state=self.budget.auth[self.binding.mode];cmd=state['next']
        encoded,salt=struct.unpack('>HH',wire[:4]);code=((~encoded)&0xffff)-salt
        if not 0<=code<=0xffff:raise WireFault('INVALID_AUTH_REPLY')
        if cmd==1:
            if code not in ((2,8) if self.binding.mode=='MSC' else (8,)):raise WireFault('UNREVIEWED_CHALLENGE')
            state['family']=code;state['next']=3
        elif cmd==3:
            if code!=4:raise WireFault('DIGEST_NOT_ACCEPTED')
            state['round']+=1;state['next']=5 if state['round']==3 else 1
        else:
            if code!=6 or wire[4]!=1:raise WireFault('FINAL_AUTH_NOT_ACCEPTED')
            state['complete']=True;state['next']=None

    @_serialized
    def execute(self,controller,action):
        self._validate(controller,action)
        self.budget.tokens.add(action.token);self.busy=True;calls=[]
        try:
            if action.phase.startswith('AUTH_'):
                self.budget.exchanges[self.binding.mode]+=1
                self._bulk(action,False,calls);reply=self._bulk(action,True,calls);self._accept_reply(reply)
                return WireResult(action.token,'AUTH_REPLY_VALID',True,tuple(calls),reply,True)
            is_start=action.phase.startswith('START_')
            if is_start:self.budget.starts[self.binding.mode]+=1
            else:self.budget.stop=True
            rc,unused,now=self._native(action,'CONTROL',calls,action.wire)
            status='CONTROL_OK' if rc==0 else 'CONTROL_STALL'
            if is_start:
                self.start_return,self.start_at=status,now;self.start_observation_version=self.observation_version
            return WireResult(action.token,status,True,tuple(calls))
        except WireFault as error:
            self.budget.failed=True;self.budget.hard_unknown|=error.hard
            self.budget.last_fault=self.budget.last_time
            self.fault_observation_version=self.observation_version
            return WireResult(action.token,error.status,error.status!='NATIVE_CALL_EXCEPTION',tuple(calls))
        finally:self.busy=False
