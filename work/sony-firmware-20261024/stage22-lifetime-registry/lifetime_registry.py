#!/usr/bin/env python3
"""Serialized reference protocol and bounded lifecycle scheduling model.

This Python model is not a native camera gate, thread implementation, or
authorization to restore/free code. Firmware guest fragments are separate.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import deque
import argparse
import copy
import datetime
import hashlib
import json
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'stage21-admission-boundary'))
import admission_boundary as a

q, w, pp, qp, APP, reg = a.q, a.w, a.pp, a.qp, a.APP, a.reg


@dataclass(frozen=True, order=True)
class Ticket:
    serial: int
    epoch: int
    producer: str


@dataclass(frozen=True, order=True)
class ObjectKey:
    address: int
    generation: int


class Registry:
    """All method actions assume one verified serialization domain.

    There is no mutex or atomic implementation here. Real entry/close,
    publication, retirement and memory ordering must implement that contract.
    Faults latch; this model cannot clear one or reopen a closed session.
    """
    def __init__(self, capacity=8, max_serial=(1 << 64) - 1):
        self.open, self.epoch, self.next_serial = True, 1, 1
        self.capacity, self.max_serial = capacity, max_serial
        self.pending, self.objects, self.inputs = {}, {}, {}
        self.fault = None

    def fail(self, reason):
        if self.fault is None: self.fault = reason
        return None

    def enter(self, producer):
        if not self.open or self.fault: return None
        if self.next_serial > self.max_serial: return self.fail('ticket space exhausted; no wrap')
        if len(self.pending) >= self.capacity: return self.fail('producer capacity exhausted')
        t = Ticket(self.next_serial, self.epoch, producer)
        self.next_serial += 1
        self.pending[t.serial] = {'ticket': t, 'recorded': False}
        return t

    def close(self): self.open = False

    def register(self, ticket, address, request_token):
        p = self.pending.get(ticket.serial)
        if p is None or p['ticket'] != ticket: return self.fail('unreserved producer ticket')
        key = ObjectKey(address, ticket.serial)
        if key in self.objects: return self.fail('duplicate object generation')
        if len(self.objects) >= self.capacity: return self.fail('object registry capacity exhausted')
        self.objects[key] = {'epoch': ticket.epoch, 'ticket': ticket.serial,
                             'request_token': request_token, 'phase': 'prepared'}
        p['recorded'] = True
        return key

    def finish_producer(self, ticket, *, unmarked=False):
        p = self.pending.get(ticket.serial)
        if p is None or p['ticket'] != ticket: return self.fail('unknown producer finish')
        if not p['recorded'] and not unmarked: return self.fail('unaccounted experimental output')
        del self.pending[ticket.serial]
        return True

    def transition(self, key, phase):
        entry = self.objects.get(key)
        if entry is None: return self.fail('unknown object generation')
        allowed = {'prepared': {'queued', 'retiring'}, 'queued': {'running', 'retiring'},
                   'running': {'retiring'}, 'retiring': set()}
        if phase not in allowed[entry['phase']]: return self.fail('invalid lifecycle transition')
        entry['phase'] = phase
        return True

    def begin_retire(self, key): return self.transition(key, 'retiring')

    def complete_retire(self, key):
        entry = self.objects.get(key)
        if entry is None or entry['phase'] != 'retiring': return self.fail('unmatched retirement completion')
        del self.objects[key]
        return True

    def retain_input(self, key, label):
        entry = self.objects.get(key)
        if entry is None: return self.fail('input source generation unknown')
        identity = (label, key.generation)
        if identity in self.inputs: return self.fail('duplicate input identity')
        self.inputs[identity] = entry['epoch']
        return identity

    def release_input(self, identity):
        if identity not in self.inputs: return self.fail('unknown input release')
        del self.inputs[identity]
        return True

    def tracked_data_drained(self):
        return not self.open and not self.fault and not self.pending and not self.objects and not self.inputs

    def snapshot(self):
        return {'open': self.open, 'epoch': self.epoch, 'next_serial': self.next_serial,
                'fault': self.fault,
                'pending': [{'ticket': asdict(v['ticket']), 'recorded': v['recorded']}
                            for _, v in sorted(self.pending.items())],
                'objects': [{'key': asdict(k), **v} for k,v in sorted(self.objects.items())],
                'inputs': [{'label': k[0], 'generation': k[1], 'epoch': v}
                           for k,v in sorted(self.inputs.items())],
                'tracked_data_drained': self.tracked_data_drained(),
                'native_restore_or_code_reclamation_authorized': False}


class LateReservation(Registry):
    """Deliberately wrong candidate: entry checks activation before reserving."""
    def enter(self, producer):
        t = super().enter(producer)
        if t is not None: del self.pending[t.serial]
        return t

    def register(self, ticket, address, request_token):
        self.pending[ticket.serial] = {'ticket': ticket, 'recorded': False}
        return super().register(ticket, address, request_token)


class EarlyRetirement(Registry):
    """Deliberately wrong candidate: object is forgotten at destructor entry."""
    def begin_retire(self, key):
        if super().begin_retire(key): del self.objects[key]
        return True

    def complete_retire(self, key):
        # The deliberately wrong protocol has no remaining completion
        # bookkeeping. This is an abstract mutation, not a firmware stub.
        return True


def bounded_schedules(registry_type):
    """Two producers, one FIFO worker, a closer; independent truth oracle.

    Producers: 0 before entry, 1 reserved, 2 prepared, 3 queued, 4 left data
    accounting but still in trampoline, 5 outside; 6 denied but still in
    trampoline, 7 denied/outside. Truth object phases: 0 absent, 1 prepared,
    2 queued, 3 running, 4 destroying, 5 destruction/free returned.
    """
    initial = (registry_type(), (0,0), (0,0), (0,0), (), None, False)
    queue = deque([(initial, [])]); seen = set(); observations = 0; drained_inside_code = 0
    def identity(state):
        r,p,t,truth,pending,current,tail = state
        return (json.dumps(r.snapshot(),sort_keys=True),p,t,truth,pending,current,tail)
    while queue:
        state, path = queue.popleft(); signature = identity(state)
        if signature in seen: continue
        seen.add(signature)
        r,p,t,truth,pending,current,tail = state
        assert r.fault is None
        registry_empty = r.tracked_data_drained()
        scope_empty = registry_empty and not pending and current is None
        # This oracle does not consult the registry's object/pending records.
        truth_hazard = any(v in (1,2,3,4) for v in truth) or any(v in (1,2,3) for v in p)
        code_active = tail or any(v in (1,2,3,4,6) for v in p)
        observations += 1
        if registry_empty and truth_hazard:
            return {'candidate':registry_type.__name__, 'data_invariant_holds_within_bound':False,
                    'states_visited':len(seen),'observations':observations,'counterexample':path,
                    'registry':r.snapshot(),'independent_truth':list(truth),'producer_phases':list(p),
                    'queue_still_nonempty':bool(pending),'current_pointer_still_present':current is not None,
                    'scope':'False-empty registry claim; other pool guards can still block unpatch. This is not a full unsafe-unload trace.'}
        if scope_empty and code_active: drained_inside_code += 1
        children = []
        if r.open:
            nr=copy.deepcopy(r);nr.close();children.append(((nr,p,t,truth,pending,current,tail),'close experimental admission'))
        for i in range(2):
            nr=copy.deepcopy(r);np,nt,ntruth=list(p),list(t),list(truth)
            ticket=Ticket(t[i],1,'P'+str(i));key=ObjectKey(0x2000+i*0x1000,t[i])
            label=None;newpending=pending
            if p[i]==0:
                accepted=nr.enter('P'+str(i));np[i]=1 if accepted else 6
                nt[i]=accepted.serial if accepted else 0;label='P%d enter%s'%(i,'' if accepted else ' denied')
            elif p[i]==1:
                assert nr.register(ticket,key.address,7)==key
                np[i]=2;ntruth[i]=1;label='P%d register prepared object'%i
            elif p[i]==2:
                assert nr.transition(key,'queued');np[i]=3;ntruth[i]=2
                newpending=pending+(i,);label='P%d publish to queue'%i
            elif p[i]==3:
                assert nr.finish_producer(ticket);np[i]=4;label='P%d finish producer accounting'%i
            elif p[i] in (4,6):
                np[i]=5 if p[i]==4 else 7;label='P%d leave trampoline'%i
            if label:children.append(((nr,tuple(np),tuple(nt),tuple(ntruth),newpending,current,tail),label))
        if current is None and pending and not tail:
            i=pending[0];nr=copy.deepcopy(r);nt=list(truth)
            assert nr.transition(ObjectKey(0x2000+i*0x1000,t[i]),'running');nt[i]=3
            children.append(((nr,p,t,tuple(nt),pending[1:],i,False),'worker start P%d'%i))
        if current is not None:
            i=current;key=ObjectKey(0x2000+i*0x1000,t[i]);nr=copy.deepcopy(r);nt=list(truth)
            if truth[i]==3:
                assert nr.begin_retire(key);nt[i]=4;label='worker enter destructor P%d'%i
            elif truth[i]==4:
                assert nr.complete_retire(key);nt[i]=5;label='worker destructor/free returned P%d'%i
            else:label=None
            if label:children.append(((nr,p,t,tuple(nt),pending,current,tail),label))
            if truth[i]==5:
                children.append(((copy.deepcopy(r),p,t,truth,pending,None,True),'worker clear current pointer'))
        if tail:children.append(((copy.deepcopy(r),p,t,truth,pending,current,False),'worker leave retirement trampoline'))
        queue.extend((child,path+[label]) for child,label in children)
    return {'candidate':registry_type.__name__, 'data_invariant_holds_within_bound':True,
            'states_visited':len(seen),'observations':observations,'counterexample':None,
            'states_with_data_drained_but_code_still_active':drained_inside_code,
            'scope':'Serialized API actions, two producers, one worker, one close. Not weak-memory, native locking, exceptions, all consumers, or executable-code grace proof.'}


def protocol_controls():
    rows=[]
    r=Registry();t=r.enter('old');old=r.register(t,0x2000,7);r.finish_producer(t)
    r.begin_retire(old)  # Old free may have returned while its bookkeeping continuation is pending.
    n=r.enter('reuse');new=r.register(n,0x2000,7);r.finish_producer(n);r.close()
    assert old!=new and old.address==new.address
    r.complete_retire(old);assert new in r.objects and not r.tracked_data_drained()
    rows.append({'case':'same address and token, distinct generation','old':asdict(old),'new':asdict(new),'after_old_completion':r.snapshot()})
    r.begin_retire(new);r.complete_retire(new);assert r.tracked_data_drained()
    rows[-1]['after_both_completions']=r.snapshot()
    r=Registry();t=r.enter('cache');key=r.register(t,0x2000,7);r.finish_producer(t)
    packet=r.retain_input(key,'query packet');r.close();r.begin_retire(key);r.complete_retire(key)
    assert not r.objects and not r.tracked_data_drained();before=r.snapshot()
    r.release_input(packet);assert r.tracked_data_drained()
    rows.append({'case':'derived input survives object retirement','before_input_release':before,'after':r.snapshot()})
    for kind in ('capacity','serial','unknown_completion','duplicate_registration'):
        r=Registry(capacity=1,max_serial=1)
        t=r.enter('first');key=r.register(t,0x2000,7);r.finish_producer(t)
        if kind=='capacity':
            r.max_serial=9;n=r.enter('second');assert n is not None
            assert r.register(n,0x3000,7) is None
            r.finish_producer(n,unmarked=True)
        elif kind=='serial':assert r.enter('second') is None
        elif kind=='unknown_completion':assert r.complete_retire(ObjectKey(0x2000,99)) is None
        else:
            n=r.enter('second');assert n is None  # Exhaustion is separately latched before an unsafe new identity.
            r=Registry();t=r.enter('first');key=r.register(t,0x2000,7)
            assert r.register(t,0x2000,7) is None;r.finish_producer(t)
        r.close();r.begin_retire(key);r.complete_retire(key)
        assert not r.tracked_data_drained() and r.fault
        rows.append({'case':'sticky fault: '+kind,'after_known_cleanup':r.snapshot()})
    r=Registry();t=r.enter('unmarked mode');r.finish_producer(t,unmarked=True);r.close()
    assert r.tracked_data_drained() and r.enter('after close') is None
    rows.append({'case':'unmarked producer and denied late admission','after':r.snapshot()})
    return rows


def destructor_fragment(marker):
    m=q.BoundaryMicro(APP,[(0x2bb0390,0x2bb03a4),(0x28443a0,0x28443c4)],end=0x28443c4)
    m.uc.mem_write(w.OLD,q.object_bytes(q.KIND,w.TOKEN,marker))
    r=m.run(0x2bb0390,[w.OLD]);assert r['reason']=='conversion block complete'
    base_vptr=w.read_file64(0x47528e8)+0x10
    assert w.read64(m.uc,w.OLD)==base_vptr and base_vptr!=q.VIRTUAL_TABLE
    assert a.cr.a.read32(m.uc,w.OLD+0x388)==marker
    r.update(marker_fixture=marker,original_cache_vptr=hex(q.VIRTUAL_TABLE),base_vptr_after=hex(base_vptr),
             marker_unchanged=True,dependency_CV_container_cleanup_or_free_executed=False,
             scope='Original destructor header changes vptr before remaining base cleanup. Synthetic object and prefix only.')
    return r


def sized_delete_fragment(marker):
    m=q.BoundaryMicro(APP,[(0x2bb03b8,0x2bb03cc)])
    m.uc.mem_write(w.OLD,q.object_bytes(q.KIND,w.TOKEN,marker));w.putregs(m,x19=w.OLD)
    r=m.run(0x2bb03b8);assert r['reason']=='unapproved PLT _ZdlPvm'
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0)==w.OLD and m.uc.reg_read(reg.UC_ARM64_REG_X1)==0x4d8
    r.update(marker_fixture=marker,object_pointer=hex(w.OLD),size=0x4d8,original_free_executed=False,
             scope='Independent post-base-destructor precondition; original tail-call arguments only. No actual destructor completion or free.')
    return r


def run(out):
    sources=[APP.path,a.cr.MPR.path]+[Path(m.__file__) for m in (a,w,q,a.cr,a.cr.cp,a.cr.ss,pp,qp,a.cr.a)]
    sources += [Path(sys.modules[pp.Image.__module__].__file__),BASE/'stage4-windows-collab/mac-verification/offline_verify.py']
    hashes={str(p.relative_to(ROOT)):qp.sha(p) for p in sources}
    previous=BASE/'stage21-admission-boundary/final-receipt.json'
    assert all(qp.sha(ROOT/f['path'])==f['sha256'] for f in json.loads(previous.read_text())['files'])
    good=bounded_schedules(Registry);late=bounded_schedules(LateReservation);early=bounded_schedules(EarlyRetirement)
    assert good['data_invariant_holds_within_bound'] and good['states_with_data_drained_but_code_still_active']>0
    assert not late['data_invariant_holds_within_bound'] and not early['data_invariant_holds_within_bound']
    controls=protocol_controls();destructors=[destructor_fragment(v) for v in (0,2)]
    frees=[sized_delete_fragment(v) for v in (0,2)];im=pp.Image()
    assert hashes=={str(p.relative_to(ROOT)):qp.sha(p) for p in sources}
    proof={'status':'PASS_SERIALIZED_REFERENCE_MODEL_AND_ORIGINAL_DTOR_FRAGMENTS_ONLY',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':qp.sha(APP.path),'previous_manifest_sha256':qp.sha(previous),
        'model_scope':{'assumptions':['One serialized domain for enter/reserve, close, register and lifecycle accounting','All modeled experimental producers enter before activation capture; marking follows successful registration','Input dependencies are explicitly retained/released','Native queue/current observations and actual thread PC grace are additional requirements'],
            'bounds':'Two producers, one FIFO worker, one close, one object per producer; no exceptions or weak-memory reorder model',
            'implemented_in_firmware':False,'all_consumer_coverage_proven':False,'native_serialization_proven':False},
        'reference_bounded_schedule':good,'deliberately_wrong_candidates':[late,early],
        'protocol_control_cases':controls,'original_destructor_header_cases':destructors,'original_sized_delete_argument_cases':frees,
        'static_regions':[{'name':n,'start':hex(s),'end_exclusive':hex(e),'instructions':im.dump(s,e)} for n,s,e in [
            ('cache_destructors',0x2bb0390,0x2bb03cc),('base_destructor_cleanup',0x28443a0,0x2844420),
            ('replacement_capture_before_old_delete',0x2c3ddb4,0x2c3de14),('worker_delete_before_current_clear',0x2bd7750,0x2bd7788)]],
        'requirements_from_evidence':[
            'Reserve producer identity before reading/acting on experimental activation, in the same serialization domain as close.',
            'Register each object before it can carry a marked value; do not defer registration until a later request token is assigned.',
            'Use a private ticket/generation and explicit configuration epoch; original request token is not unique configuration identity, and allocation addresses can be reused.',
            'Keep retirement counted until all scoped cleanup has returned; reading a live-class vptr at a generic free site is insufficient because the original destructor changes it earlier.',
            'Retain derived packets and other dependent consumers independently when they can outlive the source object; verify actual ownership paths before choosing release sites.',
            'Registry exhaustion, identity mismatch or wrap must block clean-exit claims; this model does not supply a safe native error-return or fallback policy.',
            'Tracked data drained is separate from queue/current idle and code no longer executing. No code restore/reclamation is authorized by this model; verified detachment, PC grace, instruction publication and all-consumer coverage remain missing.'],
        'native_mutex_allocator_free_destructor_cleanup_wait_or_thread_executed':False,
        'firmware_hook_patch_or_runtime_registry_exported':False,'native_restore_or_code_reclamation_authorized':False,
        'camera_interface_auth_driver_files_module_WBI_or_write':False,'new_remote_attempts':False,
        'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'reference_model_states':good['states_visited'],
        'reference_data_invariant_within_bound':True,'wrong_candidates_with_counterexamples':2,
        'data_drained_but_code_active_states':good['states_with_data_drained_but_code_still_active'],
        'protocol_controls':len(controls),'original_destructor_header_cases':len(destructors),
        'original_sized_delete_argument_cases':len(frees),'native_gate_or_full_consumer_coverage_verified':False,
        'actual_restore_or_code_reclamation_authorized':False,'goal_complete':False,'persistent_write_release':False}
    qp.write_json(out/'lifetime-registry-results.json',proof);qp.write_json(out/'summary.json',summary)
    qp.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
        'script_sha256':qp.sha(Path(__file__)),'inputs':hashes,
        'results_sha256':qp.sha(out/'lifetime-registry-results.json'),'summary_sha256':qp.sha(out/'summary.json'),
        'previous_manifest_sha256':qp.sha(previous),'volume_uuid':qp.EXPECTED_VOLUME})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();qp.verify_volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as f:f.write(Path(__file__).read_bytes())
        qp.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
