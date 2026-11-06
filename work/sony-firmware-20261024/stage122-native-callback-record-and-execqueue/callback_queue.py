#!/usr/bin/env python3
"""Native callback-record initialization and execqueue pointer lifetime scope."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage121-native-Start-caller-and-return'));import start_caller as prev
pp,r,im,MPR,SP,reg=prev.pp,prev.r,prev.im,prev.MPR,prev.SP,prev.reg
S=pp.SCRATCH;OWNER=S+0xb000;SOURCE=S+0x1000;QUEUE=S+0xe000;MAP=S+0xf000
EXTRA=0x60000000;OLD=EXTRA;NEW=EXTRA+0xa000;N=0x8ea0
PRIOR=BASE/'stage121-native-Start-caller-and-return/final-receipt.json'
PRIOR_SHA='f1e1f7df3ed41b175707ed7849fafffab5e7dcc8de0de2c8a0c7d373738ff963'
def sha(b):return hashlib.sha256(b).hexdigest()
def pq(m,a,v):m.uc.mem_write(a,struct.pack('<Q',v))
def rq(m,a):return struct.unpack('<Q',bytes(m.uc.mem_read(a,8)))[0]

class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0xfbf84,0xfbff8),(0xfc074,0xfc168),(0xfbff8,0xfc074),
            (0xd63a4,0xd6444),(0xd6444,0xd6464),(0xd64e4,0xd6530),(0xdbf94,0xdc090)])
        self.boundaries.update({0x7dfa0:'before_original_record_lock',0x819a0:'before_original_record_malloc',
            0x7f520:'before_original_queue_new_block',0x81d30:'before_original_queue_condition_signal',
            0x7f190:'before_original_queue_block_delete',0x7d630:'before_original_record_free',
            0xdc018:'before_original_worker_indirect_call',0x804c0:'before_original_worker_delay'})
        self.uc.mem_map(EXTRA,0x14000,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
        data=bytes([seed^0x66])*0x14000;self.uc.mem_write(EXTRA,data);self.images.append((EXTRA,data))

def initialize(m,seed):
    ss=prev.saved(m);ev=[m.phase('original callback-record allocation wrapper before lock',0xfbf84,sp=SP,x30=pp.STOP)]
    assert ev[-1]['reason']=='boundary: before_original_record_lock'
    ev.append(m.phase('independent post-lock original malloc size',0xfbf9c))
    assert ev[-1]['reason']=='boundary: before_original_record_malloc' and m.uc.reg_read(reg('x0'))==384
    before=bytes(m.uc.mem_read(OWNER,384))
    ev.append(m.phase('independent declared malloc buffer; original four-record initialization before unlock',0xfbfa4,
        outputs=[(OWNER,OWNER+384)],x0=OWNER))
    assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
    after=bytes(m.uc.mem_read(OWNER,384));unwritten=[]
    for i in range(4):
        for o in range(96):
            a=i*96+o
            if o in (1,2,3,12,13,14,15):assert after[a]==before[a];unwritten.append(a)
            else:assert after[a]==0
    ev.append(m.phase('independent post-unlock original allocation wrapper return',0xfbfe8))
    assert ev[-1]['reason']=='returned' and m.uc.reg_read(reg('x0'))==OWNER and prev.restored(m,ss)
    return {'seed':seed,'events':ev,'native384':after.hex(),'unwritten_padding_offsets':[hex(x) for x in unwritten],
        'actual_malloc_lock_or_healthy_owner_proven':False}

def lookup(m,key,create):
    ss=prev.saved(m);old=bytes(m.uc.mem_read(OWNER,384))
    ev=[m.phase('original callback-record lookup/create before lock',0xfc074,sp=SP,x30=pp.STOP,x0=OWNER,x1=key,x2=int(create))]
    assert ev[-1]['reason']=='boundary: before_original_record_lock'
    ev.append(m.phase('independent post-lock original lookup/create loop',0xfc0ec,outputs=[(OWNER,OWNER+384)]))
    assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
    ev.append(m.phase('independent post-unlock original record return',0xfc150))
    assert ev[-1]['reason']=='returned' and prev.restored(m,ss)
    result=m.uc.reg_read(reg('x0'));after=bytes(m.uc.mem_read(OWNER,384))
    if create:
        assert result==OWNER and after[0]==1 and struct.unpack_from('<I',after,4)[0]==key
        expected=bytearray(old);expected[0]=1;struct.pack_into('<I',expected,4,key);assert after==bytes(expected)
    else:assert result==0 and after==old
    return {'key':key,'create_input':create,'native_return':hex(result),'events':ev,
        'actual_record_key_identity_lock_and_registration_lifetime_proven':False}

def queue(m,seed):
    raw=bytearray(((i*31+seed)&255) for i in range(N))
    ref=BASE/'stage121-native-Start-caller-and-return/run-native-Start-caller-20261027/start-caller-results.json'
    prefix=bytes.fromhex(json.loads(ref.read_text())['producer_cases'][0]['declared_exec56']);raw[:56]=prefix
    pq(m,MAP+0x10,OLD);m.uc.mem_write(SOURCE,bytes(raw));pq(m,SOURCE+0x30,OWNER);pq(m,SOURCE+0x8e98,0xca6e4)
    raw=bytes(m.uc.mem_read(SOURCE,N));m.uc.mem_write(QUEUE,bytes(0xc0))
    for off,v in ((8,MAP),(0x10,8),(0x18,OLD),(0x20,OLD),(0x28,OLD+N),(0x30,MAP+0x10),
        (0x38,OLD),(0x40,OLD),(0x48,OLD+N),(0x50,MAP+0x10)):pq(m,QUEUE+off,v)
    m.uc.mem_write(QUEUE+0xbc,b'\1');owner=bytes(m.uc.mem_read(OWNER,384));ss=prev.saved(m)
    ev=[m.phase('original execqueue enqueue prologue before mutex',0xd63a4,sp=SP,x30=pp.STOP,x0=QUEUE,x1=SOURCE)]
    assert ev[-1]['reason']=='boundary: before_original_setter_mutex'
    ev.append(m.phase('independent post-lock original single-element deque block path before new allocation',0xd63d8))
    assert ev[-1]['reason']=='boundary: before_original_queue_new_block' and m.uc.reg_read(reg('x0'))==N
    ev.append(m.phase('independent new-block buffer; original descriptor memcpy and finish iterator update before signal',0xd64f0,
        outputs=[(MAP+0x18,MAP+0x20),(QUEUE+0x38,QUEUE+0x58)],image_outputs=[(OLD,OLD+N)],x0=NEW))
    assert ev[-1]['reason']=='boundary: before_original_queue_condition_signal'
    assert bytes(m.uc.mem_read(OLD,N))==raw and rq(m,OLD+0x30)==OWNER and rq(m,OLD+0x8e98)==0xca6e4
    assert rq(m,QUEUE+0x38)==NEW and rq(m,QUEUE+0x50)==MAP+0x18
    ev.append(m.phase('independent post-signal original enqueue before mutex unlock',0xd641c))
    assert ev[-1]['reason']=='boundary: before_original_sender_mutex_unlock'
    ev.append(m.phase('independent post-unlock original enqueue epilogue',0xd6424))
    assert ev[-1]['reason']=='returned' and m.uc.reg_read(reg('w0'))==0 and prev.restored(m,ss)
    ev.append(m.phase('original worker prologue before mutex',0xdbf94,sp=SP,x30=pp.STOP,x0=QUEUE))
    assert ev[-1]['reason']=='boundary: before_original_setter_mutex'
    ev.append(m.phase('independent post-lock original worker selects front descriptor before unlock',0xdbfd4))
    assert ev[-1]['reason']=='boundary: before_original_sender_mutex_unlock' and m.uc.reg_read(reg('x20'))==OLD
    ev.append(m.phase('independent post-unlock original worker loads copied function pointer before indirect call',0xdbffc))
    assert ev[-1]['reason']=='boundary: before_original_worker_indirect_call'
    assert m.uc.reg_read(reg('x0'))==OLD and m.uc.reg_read(reg('x1'))==0xca6e4
    frame={n:m.uc.reg_read(reg(n)) for n in ['sp','x29']+['x'+str(i) for i in range(19,29)]}
    m.boundaries.pop(0xdc018)
    ev.append(m.phase('original worker BLR enters original ExecEncStart prologue before diagnostic',0xdc018))
    assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic' and m.uc.reg_read(reg('x19'))==OLD
    assert rq(m,OLD+0x30)==OWNER
    ev.append(m.phase('independent post-job frame, not a completed Start: original worker before pop lock',0xdc01c,**frame))
    assert ev[-1]['reason']=='boundary: before_original_setter_mutex'
    ev.append(m.phase('independent post-lock original worker before old deque block delete',0xdc028))
    assert ev[-1]['reason']=='boundary: before_original_queue_block_delete' and m.uc.reg_read(reg('x0'))==OLD
    ev.append(m.phase('independent post-delete original iterator advance before unlock',0xdc058,
        outputs=[(QUEUE+0x18,QUEUE+0x38)]))
    assert ev[-1]['reason']=='boundary: before_original_sender_mutex_unlock'
    assert rq(m,QUEUE+0x18)==rq(m,QUEUE+0x38)==NEW
    assert bytes(m.uc.mem_read(OWNER,384))==owner and bytes(m.uc.mem_read(SOURCE,N))==raw
    return {'seed':seed,'events':ev,'descriptor_bytes':N,'descriptor_sha256':sha(raw),
        'native_copied_callback_pointer':hex(OWNER),'native_indirect_target':'0xca6e4','native_worker_argument':hex(OLD),
        'declared_owner_bytes_unchanged_through_native_copy_dispatch_and_pop_slices':True,
        'all_real_allocation_thread_services_complete_Start_and_delete_unexecuted':True,
        'post_job_and_post_delete_frames_not_proof_of_completion_or_free':True,
        'no_actual_owner_lifetime_all_async_consumers_or_safe_rollback_proven':True}

def free_boundary(seed,owner):
    m=Guest(seed)
    try:
        m.uc.mem_write(OWNER,owner)
        ev=[m.phase('independent original nonnull callback-record release prologue before lock',0xfbff8,sp=SP,x30=pp.STOP,x0=OWNER)]
        assert ev[-1]['reason']=='boundary: before_original_record_lock'
        ev.append(m.phase('independent post-lock original free argument before allocator',0xfc060))
        assert ev[-1]['reason']=='boundary: before_original_record_free' and m.uc.reg_read(reg('x0'))==OWNER
        assert bytes(m.uc.mem_read(OWNER,384))==owner
        return {'seed':seed,'events':ev,'original_free_pointer':hex(OWNER),'actual_free_release_order_or_safe_owner_reclamation_proven':False}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(Path(__file__).read_bytes()),
        'initializers':[],'lookups':[],'queues':[],'release_boundaries':[],'goal_complete':False,'persistent_write_release':False,
        'camera_Windows_UU_operations':False,'actual_MAIN_hardware_instance_recovery_or_lifetime_proven':False}
    try:
        for seed in (0xa5,0xc3):
            m=Guest(seed)
            try:
                j['initializers'].append(initialize(m,seed))
                for key,create in ((17,False),(17,True),(17,True)):j['lookups'].append(lookup(m,key,create))
                j['queues'].append(queue(m,seed));owner=bytes(m.uc.mem_read(OWNER,384))
            finally:m.close()
            j['release_boundaries'].append(free_boundary(seed,owner))
        j['bounded_phases']=sum(len(c['events']) for k in ('initializers','lookups','queues','release_boundaries') for c in j[k])
        j['status']='PASS_NATIVE_CALLBACK_RECORD_AND_QUEUE_POINTER_LIFETIME_SCOPE_NOT_RUNTIME_ACCEPTANCE'
        (out/'callback-queue-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
