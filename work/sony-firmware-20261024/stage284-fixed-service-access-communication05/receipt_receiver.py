"""Receive private owner results from a previously identified AF_UNIX peer.

No spawn, sudo, device API, cache query, signal, reset, file repair or retry.
SHA256 detects damaged records; identity comes from the kernel-bound socket
and a helper incarnation verified while alive, never from a report file.
"""
from dataclasses import dataclass
from hashlib import sha256
import array
import ctypes as C
import os
import select
import socket
import struct
import time

BYTES=1024
RESULT_BYTES=728
GRANT_ID='fx3-702-service-access-communication-20261101-05'
LIVE_PATH='/private/var/root/fx3-owner-trials/'+GRANT_ID+'/helper'

class Rejected(ValueError):pass

@dataclass(frozen=True)
class Identity:
    uid:int
    pid:int
    sec:int
    usec:int
    path:str
    image_sha256:str

@dataclass(frozen=True)
class VerifiedHelper:
    identity:Identity
    mode:str
    expected_image_sha256:str=''

def capture_helper(pid,expected_uid,expected_path,expected_sha256,probe,*,mode='live'):
    if mode not in ('live','fixture') or (mode=='live' and (expected_uid!=0 or expected_path!=LIVE_PATH)):
        raise Rejected('fixed native UID/path required')
    if mode=='fixture' and not (expected_uid==os.getuid()==os.geteuid()!=0):
        raise Rejected('fixture must be this unprivileged user')
    if len(expected_sha256)!=64 or any(c not in '0123456789abcdef' for c in expected_sha256):
        raise Rejected('binary digest shape')
    actual=probe(pid) # None only for an absent PID; errors must raise.
    if actual is None or actual.pid!=pid or actual.uid!=expected_uid or actual.path!=expected_path or \
        (actual.image_sha256!=expected_sha256 and not (mode=='live' and actual.image_sha256=='')) or actual.sec<=0 or not 0<=actual.usec<1_000_000:
        raise Rejected('helper kernel incarnation or executable differs')
    return VerifiedHelper(actual,mode,expected_sha256)

def decode_hello(data,verified,nonce):
    if len(data)!=160 or data[:8]!=b'FX3HEL01' or struct.unpack_from('<II',data,8)!=(1,160):raise Rejected('helper HELLO framing')
    i=verified.identity
    if struct.unpack_from('<IIQQ',data,16)!=(i.uid,i.pid,i.sec,i.usec):raise Rejected('helper HELLO incarnation')
    if data[40:56]!=nonce or data[56:88]!=sha256(GRANT_ID.encode('ascii')).digest():raise Rejected('helper HELLO nonce/grant')
    if data[88:120].hex()!=(verified.expected_image_sha256 or i.image_sha256):raise Rejected('helper HELLO image digest')
    if any(data[120:128]) or sha256(data[:128]).digest()!=data[128:]:raise Rejected('helper HELLO integrity')
    return {'image_sha256':data[88:120].hex(),'kernel_peer_and_self_image_checked':True}

def socket_peer(conn):
    if conn.family!=socket.AF_UNIX or conn.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_STREAM:
        raise Rejected('AF_UNIX stream required')
    libc=C.CDLL(None,use_errno=True)
    getpeereid=libc.getpeereid;getpeereid.restype=C.c_int
    getpeereid.argtypes=[C.c_int,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
    uid=C.c_uint32();gid=C.c_uint32()
    if getpeereid(conn.fileno(),C.byref(uid),C.byref(gid)):
        raise OSError(C.get_errno(),'getpeereid')
    # Darwin SDK sys/un.h: SOL_LOCAL=0, LOCAL_PEERPID=2.
    raw=conn.getsockopt(0,2,4)
    if len(raw)!=4:raise Rejected('kernel peer PID size')
    pid=struct.unpack('=i',raw)[0]
    if pid<=0:raise Rejected('kernel peer PID absent')
    return uid.value,pid

def decode_record(data,identity,nonce,grant_id=GRANT_ID):
    """Pure format check. This function alone proves no transport identity."""
    if len(data)!=BYTES or data[:8]!=b'FX3RCPT5':raise Rejected('receipt size or magic')
    version,phase,size,abi,uid,pid=struct.unpack_from('<6I',data,8)
    sec,usec=struct.unpack_from('<QQ',data,32)
    if (version,size,abi)!=(5,BYTES,4) or phase not in (1,2,3):raise Rejected('receipt version or phase')
    if (uid,pid,sec,usec)!=(identity.uid,identity.pid,identity.sec,identity.usec):raise Rejected('receipt incarnation')
    if len(nonce)!=16 or data[48:64]!=nonce:raise Rejected('receipt nonce')
    if data[64:96]!=sha256(grant_id.encode('ascii')).digest():raise Rejected('receipt grant')
    count,native,guard,frame_failed,ran,reserved=struct.unpack_from('<IiiIII',data,96)
    if count!=RESULT_BYTES or native not in range(5) or guard not in range(6) or frame_failed not in (0,1) or ran not in (0,1):
        raise Rejected('receipt outcome bounds')
    if reserved or any(data[152:160]):raise Rejected('receipt reserved bytes')
    if sha256(data[:992]).digest()!=data[992:]:raise Rejected('receipt envelope digest')
    result=data[160:888]
    if sha256(result).digest()!=data[120:152]:raise Rejected('private result digest')
    values=struct.unpack_from('<14I',result)
    names=('abi','status','event_count','capture_attempted','claim_attempted','interface_claimed','clock_invalid',
           'cleanup_error','active_call_pending','persistent_camera_or_vendor_commands','owner_retained',
           'session_state','wire_pending','vendor_attempted')
    r=dict(zip(names,values))
    if r['abi']!=4 or r['status'] not in range(4) or r['event_count']>64 or r['session_state']>4:
        raise Rejected('private result ABI/status/count')
    for key in ('capture_attempted','claim_attempted','interface_claimed','clock_invalid','cleanup_error',
                'persistent_camera_or_vendor_commands','owner_retained','vendor_attempted'):
        if r[key] not in (0,1):raise Rejected('private result flag')
    used=216+r['event_count']*8
    if any(result[used:]):raise Rejected('unused private events')
    for at in range(216,used,8):
        # Native claim tracing emits 101..109 (109 once per endpoint).
        # These are host API substeps, not additional camera operations.
        event_phase=struct.unpack_from('<I',result,at)[0]
        if event_phase not in range(1,14) and event_phase not in range(101,110):
            raise Rejected('private event phase')
    if phase==2:
        if (native,r['status'],ran,r['owner_retained'],guard)!=(4,2,1,1,0):raise Rejected('held outcome inconsistent')
    elif phase==3:
        if (native,r['status'],ran,r['owner_retained'])!=(4,2,1,1) or any(r[k] for k in
            ('active_call_pending','wire_pending','clock_invalid','cleanup_error')):
            raise Rejected('idle-held exit still has unresolved host calls')
        if any(r[k]!=1 for k in ('capture_attempted','claim_attempted','interface_claimed','vendor_attempted')):
            raise Rejected('idle-held exit lacks captured source scope')
    elif native!=r['status'] or native==4 or r['owner_retained'] or r['active_call_pending'] or r['wire_pending']:
        raise Rejected('terminal record still owns a pending/vendor session')
    if not ran and (native!=3 or any(result[8:])):raise Rejected('no-run result inconsistent')
    if phase==1 and native in (0,1) and (guard or r['cleanup_error'] or r['clock_invalid']):
        raise Rejected('clean outcome inconsistent')
    recovery={'schema':0,'stage':0}
    if any(data[888:992]):
        schema,stage=struct.unpack_from('<II',data,888)
        source,physical,location,zero,before=struct.unpack_from('<QQIIQ',data,960)
        if schema!=1 or stage not in (1,2) or zero or not source or not physical or not location or not before or before>2045:
            raise Rejected('manual recovery stamp bounds')
        if not any(data[896:928]) or not any(data[928:960]) or data[896:928]==data[928:960]:
            raise Rejected('manual recovery chain hashes')
        if stage==1 and (ran or native!=3 or phase!=1 or r['event_count']):
            raise Rejected('recovery tail without OWNED cannot run owner')
        recovery=dict(schema=schema,stage=stage,prior_tail_hash=data[896:928].hex(),
                      recovered_hash=data[928:960].hex(),source_node=source,physical_port=physical,
                      location=location,before_count=before)
    return {'phase':{1:'COMPLETE',2:'HELD',3:'IDLE_HELD_EXIT'}[phase],'native_return':native,'global_guard_result':guard,
            'frame_io_failed':bool(frame_failed),'owner_ran':bool(ran),'result':r,'result_bytes':result,
            'result_sha256':data[120:152].hex(),'record_sha256':sha256(data).hexdigest(),
            'transport_peer_verified':False,'physical_camera_acceptance':False,'manual_recovery':recovery}

class Receiver:
    """One final record per accepted connection; helper may exit after sending.

    Verify the actual helper before acknowledging its entry. At accept, the
    socket's immutable kernel UID/PID must match that captured incarnation.
    The private header then binds the same birth, nonce and fixed grant.
    """
    def __init__(self,conn,verified,nonce):
        if not isinstance(verified,VerifiedHelper):raise Rejected('pre-ACK verified helper required')
        self.conn=conn;self.verified=verified;self.nonce=bytes(nonce);self.used=False;self.acknowledged=False;self.image_verified=False
        expected=verified.identity
        if socket_peer(conn)!=(expected.uid,expected.pid):raise Rejected('accepted kernel peer differs')
        self.kernel_peer=(expected.uid,expected.pid)

    def acknowledge(self):
        """Release only the connection handshake; no operation request here."""
        if not self.image_verified or self.acknowledged or self.used:raise Rejected('image HELLO required before one connection ACK')
        self.acknowledged=True
        self.conn.sendall(b'FX3ACK01'+self.nonce)

    def accept_hello(self,data):
        if self.image_verified or self.used:raise Rejected('HELLO already consumed')
        value=decode_hello(data,self.verified,self.nonce);self.image_verified=True
        return value

    def _exact(self,count,deadline):
        out=bytearray()
        while len(out)<count:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('receipt deadline; owner state unresolved')
            ready,_,_=select.select([self.conn],[],[],min(.02,remaining))
            if not ready:continue
            # As in the owner request receiver: collect every externalized FD,
            # reject ancillary data, close only newly received duplicates.
            try:data,anc,flags,_=self.conn.recvmsg(1,socket.CMSG_SPACE(512*4),socket.MSG_DONTWAIT)
            except (BlockingIOError,InterruptedError):continue
            for level,kind,raw in anc:
                if level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS:
                    fds=array.array('i');fds.frombytes(raw[:len(raw)//fds.itemsize*fds.itemsize])
                    for fd in fds:
                        if fd>=0:os.close(fd)
            if anc or flags&(socket.MSG_CTRUNC|socket.MSG_TRUNC):raise Rejected('receipt ancillary data rejected')
            if not data:raise EOFError('incomplete final receipt; owner state unresolved')
            out.extend(data)
        return bytes(out)

    def receive(self,deadline):
        if self.used or not self.image_verified:raise Rejected('HELLO required; final receipt already consumed or failed')
        self.used=True
        # The accepted stream stays with this receiver. LOCAL_PEERPID can be
        # ENOTCONN after a legitimate peer sent the record and exited. The
        # pre-ACK kernel proof is retained; bytes cannot be imported from a
        # report file or a reconnected socket.
        if struct.unpack('<I',self._exact(4,deadline))[0]!=BYTES:raise Rejected('final frame length')
        raw=self._exact(BYTES,deadline)
        value=decode_record(raw,self.verified.identity,self.nonce)
        value['transport_peer_verified']=True
        return raw,value

def observe_completion(receipt,verified,probe):
    """No wait/spawn/retry. Process absence is separate from private return."""
    value={'status':'UNKNOWN','helper_terminal_observed':False,'physical_camera_acceptance':False,
           'automatic_retry':False,'new_trial_authorized':False}
    if not receipt.get('transport_peer_verified'):return value
    if receipt['phase']=='HELD':return dict(value,status='OWNER_RETAINED')
    try:current=probe(verified.identity.pid)
    except OSError:return dict(value,status='UNKNOWN_PROCESS_OBSERVATION_ERROR')
    if current==verified.identity:
        return dict(value,status='IDLE_HELD_RECEIPT_PROCESS_STILL_PRESENT' if receipt['phase']=='IDLE_HELD_EXIT' else 'COMPLETE_RECEIPT_PROCESS_STILL_PRESENT')
    # None means ESRCH; a different birth proves the old incarnation is gone.
    if current is not None and (current.pid!=verified.identity.pid or
        (current.sec,current.usec)==(verified.identity.sec,verified.identity.usec)):
        return dict(value,status='UNKNOWN_PROCESS_IDENTITY_CHANGE')
    native=receipt['native_return'];r=receipt['result']
    if receipt['phase']=='IDLE_HELD_EXIT':
        return dict(value,status='HOST_IDLE_EXIT_CAMERA_STATE_UNKNOWN' if receipt['global_guard_result']==0 and not receipt['frame_io_failed'] else 'HOST_IDLE_EXIT_GUARD_OR_RECORD_UNKNOWN',helper_terminal_observed=True)
    status='OWNER_OPERATION_UNKNOWN'
    if native in (0,1) and receipt['global_guard_result']==0 and not r['cleanup_error'] and not r['clock_invalid']:
        status='HOST_RETURN_CAMERA_STATE_UNVERIFIED' if r['vendor_attempted'] else ('HOST_RETURN_OBSERVED' if native==0 else 'HOST_ABORT_RETURN_OBSERVED')
    elif native==3 and r['event_count']==0:
        status='DENIED_OWNER_NOT_STARTED_RECOVERY_TAIL_RETAINED' if receipt.get('manual_recovery',{}).get('stage')==1 else 'DENIED_BEFORE_OWNER_ACTIONS'
    return dict(value,status=status,helper_terminal_observed=True)
