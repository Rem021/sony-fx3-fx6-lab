"""Adversarial local receipt/ACK tests; only our fake-owner and Python peers.

No native helper, root, USB, camera, Windows, GUI or privilege operation.
"""
from pathlib import Path
from hashlib import sha256
from dataclasses import replace
import array, contextlib, json, os, secrets, socket, struct, subprocess, sys, time, traceback
import test_integration as M
import receipt_receiver as R
HERE=M.HERE
results=[]
template=None
template_identity=None
template_nonce=None

def rejected(fn,kind=R.Rejected):
    try:fn()
    except kind:return
    raise AssertionError('invalid record/peer unexpectedly accepted')

def complete_after_shared_corruption():
    global template,template_identity,template_nonce
    with M.Job() as j:
        assert j.send(1)[0]==0 and j.send(5)[0]==0
        out,err=j.proc.communicate(timeout=3)
        assert j.proc.returncode==0 and b'Sanitizer' not in err
        (j.path/'fixture-only-stdout.txt').write_bytes(out)
        j.detach();os.ftruncate(j.frame_fd,0) # destroy public report after owner exited
        j.receive_receipt()
        assert R.observe_completion(j.receipt,j.verified,M.probe)['status']=='HOST_RETURN_OBSERVED'
        assert j.receipt['transport_peer_verified'] and not j.receipt['physical_camera_acceptance']
        template=(j.path/'private-receipt.bin').read_bytes();template_identity=j.verified.identity;template_nonce=j.nonce
        (HERE/'template-private-record.bin').write_bytes(template)
        (HERE/'template-identity.json').write_text(json.dumps({'identity':j.verified.identity.__dict__,'nonce':j.nonce.hex()},indent=2)+'\n')

def held_public_completion_forgery():
    with M.Job(option=4096) as j:
        assert j.send(1)[0]==0 and j.send(2,M.START)[0]==0 and j.send(5)[0]==4
        j.retain();j.grant.completed=1;j.grant.result=0
        M.C.memset(j.ptr+M.ipc_layout(1),0,M.layout(4));time.sleep(.06)
        assert j.proc.poll() is None and M.journal_states(j.guard_path)==[1]
        observed=R.observe_completion(j.receipt,j.verified,lambda p:None)
        assert observed['status']=='OWNER_RETAINED' and not observed['helper_terminal_observed']
        assert not observed['automatic_retry'] and not observed['new_trial_authorized']

def missing_receipt_pending_owner():
    with M.Job(option=4096,block=0x10000|(1<<8)|12) as j:
        assert j.send(1)[0]==0
        j.conn.sendall(struct.pack('<I',572)+j.packet(2,M.START))
        M.wait(lambda:M.value(j.ptr,8)==1 and M.value(j.ptr,4)==1)
        j.grant.completed=1;j.grant.result=0
        rejected(lambda:j.receiver.receive(time.monotonic()+.04),TimeoutError)
        rejected(lambda:j.receiver.receive(time.monotonic()+1))
        assert j.proc.poll() is None and M.journal_states(j.guard_path)==[1]
        assert M.value(j.ptr,4)==1
        j.held=True;j.expected_wire=[1,0,0] # fake gate in cleanup only; no real calls

def kernel_peer_rejections():
    with M.Job() as j:
        for identity in (replace(j.verified.identity,pid=os.getpid()),replace(j.verified.identity,uid=0)):
            rejected(lambda:R.Receiver(j.conn,R.VerifiedHelper(identity,'fixture'),j.nonce))
        rejected(j.receiver.acknowledge)
        assert j.send(5)[0]==0;j.finish()

def wrong_executable_digest():
    with M.Job() as j:
        rejected(lambda:R.capture_helper(j.proc.pid,os.getuid(),str(M.HELPER),'0'*64,M.probe,mode='fixture'))
        rejected(lambda:R.capture_helper(j.proc.pid,os.getuid(),str(M.HELPER),M.BUILD['builds']['fixture']['sha256'],M.probe,mode='live'))
        assert j.send(5)[0]==0;j.finish()

def invalid_ack(kind):
    with M.Job(peer_ack=kind) as j:
        r=j.finish(3)
        assert r['fixture_calls']==[0]*12 and r['wire_calls']==[0,0,0]
        assert not j.guard_path.exists() # no owner/global begin was reached
        if j.receipt:
            o=R.observe_completion(j.receipt,j.verified,M.probe)
            assert o['status']=='DENIED_BEFORE_OWNER_ACTIONS'

def rehash(data,*,body=False):
    data=bytearray(data)
    if body:data[120:152]=sha256(data[160:888]).digest()
    data[992:]=sha256(data[:992]).digest()
    return bytes(data)

def format_and_replay_rejections():
    assert template is not None
    for cut in (0,1,159,887,1023):rejected(lambda cut=cut:R.decode_record(template[:cut],template_identity,template_nonce))
    rejected(lambda:R.decode_record(template+b'X',template_identity,template_nonce))
    for offset,value in ((0,0),(8,2),(12,0),(16,2048),(20,3),(24,0),(28,1),(32,0),(40,1000000),
                         (64,99),(96,729),(108,2),(112,2),(116,1),(152,1),(888,1),(992,1)):
        data=bytearray(template)
        if offset in (0,64,152,888,992):data[offset]=value
        else:struct.pack_into('<I',data,offset,value)
        rejected(lambda data=data:R.decode_record(rehash(data),template_identity,template_nonce))
    rejected(lambda:R.decode_record(template,template_identity,b'Z'*16))
    rejected(lambda:R.decode_record(template,replace(template_identity,sec=template_identity.sec+1),template_nonce))
    rejected(lambda:R.decode_record(template,template_identity,template_nonce,'other-grant'))
    data=bytearray(template);data[120]^=1
    rejected(lambda:R.decode_record(rehash(data),template_identity,template_nonce))
    data=bytearray(template);data[160]^=1
    rejected(lambda:R.decode_record(rehash(data),template_identity,template_nonce))

def contradictory_terminal_rejections():
    # Recompute both digests to exercise semantic checks, not merely checksum.
    for offset,value in ((164,2),(168,65),(176,2),(184,1),(188,1),(192,7),(200,1),(204,5),(208,1),(212,1),(880,1)):
        data=bytearray(template);struct.pack_into('<I',data,offset,value)
        rejected(lambda data=data:R.decode_record(rehash(data,body=True),template_identity,template_nonce))
    for offset,value in ((12,2),(100,4),(104,3),(112,0)):
        data=bytearray(template);struct.pack_into('<I',data,offset,value)
        rejected(lambda data=data:R.decode_record(rehash(data),template_identity,template_nonce))

def process_observation_states():
    r=R.decode_record(template,template_identity,template_nonce)
    verified=R.VerifiedHelper(template_identity,'fixture')
    assert R.observe_completion(r,verified,lambda pid:None)['status']=='UNKNOWN'
    r['transport_peer_verified']=True
    # Explicit observation models; not additional real root/process tests.
    assert R.observe_completion(r,verified,lambda pid:template_identity)['status']=='COMPLETE_RECEIPT_PROCESS_STILL_PRESENT'
    def unreadable(pid):raise OSError('synthetic observation denied')
    assert R.observe_completion(r,verified,unreadable)['status']=='UNKNOWN_PROCESS_OBSERVATION_ERROR'
    assert R.observe_completion(r,verified,lambda pid:replace(template_identity,path='changed'))['status']=='UNKNOWN_PROCESS_IDENTITY_CHANGE'
    assert R.observe_completion(r,verified,lambda pid:replace(template_identity,sec=template_identity.sec+1))['status']=='HOST_RETURN_OBSERVED'
    assert R.observe_completion(r,verified,lambda pid:None)['status']=='HOST_RETURN_OBSERVED'

SENDER=r'''
from pathlib import Path
from hashlib import sha256
import array,json,os,socket,struct,sys,time
path,payload,mode=sys.argv[1:]
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.connect(path)
if s.recv(1)!=b'G':raise SystemExit(0)
data=Path(payload).read_bytes()
if mode=='fragment':
 for piece in (data[:1],data[1:3],data[3:51],data[51:]):s.sendall(piece);time.sleep(.002)
elif mode=='short':s.sendall(data[:601])
elif mode=='oversized':s.sendall(struct.pack('<I',0xffffffff))
elif mode=='silent':time.sleep(.15)
elif mode.startswith('rights'):
 fd=os.open('/dev/null',os.O_RDONLY)
 try:s.sendmsg([data],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]*int(mode[6:])))])
 finally:os.close(fd)
else:s.sendall(data)
s.close()
'''

def transport(mode):
    name='wire-'+secrets.token_hex(4);directory=HERE/'runs'/name;directory.mkdir(mode=0o700)
    socket_dir=M.SOCKET_ROOT/name;socket_dir.mkdir(mode=0o700);path=socket_dir/'s'
    server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(path));os.chmod(path,0o600);server.listen(1);server.settimeout(3)
    conn=None;child=None
    try:
        payload=directory/'synthetic-wire-record.bin'
        child=subprocess.Popen([sys.executable,'-B','-c',SENDER,str(path),str(payload),mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        conn,_=server.accept();identity=M.probe(child.pid)
        assert identity.uid==os.getuid()!=0
        proof=R.capture_helper(child.pid,os.getuid(),identity.path,identity.image_sha256,M.probe,mode='fixture')
        data=bytearray(template);struct.pack_into('<IIQQ',data,24,identity.uid,identity.pid,identity.sec,identity.usec)
        raw=rehash(data);payload.write_bytes(struct.pack('<I',1024)+raw)
        recv=R.Receiver(conn,proof,template_nonce);count_before=len(os.listdir('/dev/fd'))
        conn.sendall(b'G')
        if mode in ('normal','fragment'):
            record,value=recv.receive(time.monotonic()+1)
            assert record==raw and value['transport_peer_verified']
            rejected(lambda:recv.receive(time.monotonic()+1))
        else:
            kind=EOFError if mode=='short' else TimeoutError if mode=='silent' else R.Rejected
            rejected(lambda:recv.receive(time.monotonic()+(.04 if mode=='silent' else 1)),kind)
            rejected(lambda:recv.receive(time.monotonic()+1))
        assert len(os.listdir('/dev/fd'))==count_before,'received SCM_RIGHTS leak'
        out,err=child.communicate(timeout=3);assert child.returncode==0,(out,err)
        (directory/'sender-stdout.txt').write_bytes(out);(directory/'sender-stderr.txt').write_bytes(err)
    finally:
        if conn:conn.close()
        server.close()
        if child and child.poll() is None:
            out,err=child.communicate(timeout=3)
            assert child.returncode==0,(out,err)
        if path.exists():path.unlink()
        socket_dir.rmdir()

def case(name,fn):
    start=time.monotonic()
    try:fn();results.append({'name':name,'status':'PASS','seconds':time.monotonic()-start})
    except BaseException as error:
        results.append({'name':name,'status':'FAIL','error':repr(error),'traceback':traceback.format_exc()})
        (HERE/('receipt-failure-'+str(time.time_ns())+'.json')).write_text(json.dumps({'results':results},indent=2)+'\n')
        raise

if __name__=='__main__':
    case('private_complete_after_public_file_destroyed_and_peer_exit',complete_after_shared_corruption)
    case('held_private_result_defeats_public_completion_forgery',held_public_completion_forgery)
    case('missing_receipt_cannot_release_pending_owner',missing_receipt_pending_owner)
    case('actual_kernel_peer_PID_UID_and_duplicate_ACK_rejected',kernel_peer_rejections)
    case('captured_executable_digest_and_native_UID_path_policy',wrong_executable_digest)
    for mode in ('wrong_nonce','none','rights32','rights200'):case('pre_owner_ACK_'+mode,lambda mode=mode:invalid_ack(mode))
    case('format_identity_digest_and_replay_rejections',format_and_replay_rejections)
    case('contradictory_complete_and_held_outcomes_rejected',contradictory_terminal_rejections)
    case('completion_separates_private_result_from_process_observation',process_observation_states)
    for mode in ('normal','fragment','short','oversized','silent','rights32','rights200'):
        case('actual_unprivileged_stream_'+mode,lambda mode=mode:transport(mode))
    report={'status':'PASS_PRIVATE_OWNER_RECEIPTS','tests_run':len(results),'results':results,
            'actual_unprivileged_UID_PID_birth_and_executable_checks':True,'root_cross_UID_tested':False,
            'native_helper_executed':False,'administrator_or_camera_operations':0,'physical_recovery_proven':False,
            'synthetic_transport_records_explicit':True,'process_observation_models_explicit':True,
            'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'receiver_source_sha256':sha256((HERE/'receipt_receiver.py').read_bytes()).hexdigest(),
            'integration_source_sha256':sha256((HERE/'test_integration.py').read_bytes()).hexdigest(),
            'build_receipt_sha256':sha256((HERE/'build-receipt-v2.json').read_bytes()).hexdigest()}
    with (HERE/'receipt-results.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k!='results'}))
