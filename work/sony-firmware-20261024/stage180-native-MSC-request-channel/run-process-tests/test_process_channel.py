"""Exercise a real C child process over private datagrams, using fake USB only."""
from pathlib import Path
from hashlib import sha256
import json
import os
import select
import socket
import struct
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
MAGIC,RESPONSE=0x31385146,0x52385146
NONCE=bytes([0xa5])*16
START=bytes.fromhex('4301ff37aad70000')
STOP=bytes.fromhex('430100c855280000')
FMT='<IIQQQII16s516s'
assert struct.calcsize(FMT)==572


def request(seq,op,payload=b'',generation=17,nonce=NONCE,deadline=4000000000):
    return struct.pack(FMT,MAGIC,1,seq,generation,deadline,op,len(payload),nonce,payload.ljust(516,b'\0'))


def decode(data):
    assert len(data)==676 and struct.unpack_from('<II',data)==(RESPONSE,1)
    status,flags,exchanges,requests,pending,n=struct.unpack_from('<6I',data,16)
    assert data[48:64]==NONCE and struct.unpack_from('<I',data,40)[0]==0
    native=[]
    for at in (64,112):
        fields=struct.unpack_from('<8Ii3I',data,at)
        native.append(dict(zip(('abi','status','op','requested','actual_known','reported_count',
                                'timeout','returned','raw','buffer_ok','owner_ok','body_proof'),fields)))
    return {'id':struct.unpack_from('<Q',data,8)[0],'status':status,'flags':flags,'exchanges':exchanges,
            'requests':requests,'pending':pending,'bytes':n,'native':native,'reply':data[160:160+n]}


def auth(command,data=b''):
    return struct.pack('>HH',(~command)&0xffff,0)+data.ljust(512,b'\0')


def main():
    out=HERE/(sys.argv[1] if len(sys.argv)>1 else 'run-process-tests')
    out.mkdir(mode=0o700,exist_ok=False)
    build=json.loads((HERE/'build-receipt-v4.json').read_text())
    exe=Path(build['process_fixture']['argv'][-1])
    assert sha256(exe.read_bytes()).hexdigest()==build['process_fixture']['sha256']
    for name,want in build['sources'].items():assert sha256((HERE/name).read_bytes()).hexdigest()==want
    for name in ('native_session.h','native_session.c','process_fixture.c','test_process_channel.py'):
        (out/name).write_bytes((HERE/name).read_bytes())
    cases=[]
    report={'status':'RUNNING','cases':cases,'actual_root_or_USB_operations':0,'real_root_bootstrap_or_peer_credential_verification':False}
    def done(name,**fields):cases.append({'name':name,**fields})
    def public(r):return {k:v for k,v in r.items() if k!='reply'}
    class Peer:
        def __init__(self,name,op=0,fault=0,family=8):
            self.name=name;self.a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
            gate_r,self.gate=os.pipe();self.audit,audit_w=os.pipe()
            self.stdout=(out/(name+'.stdout.json')).open('wb');self.stderr=(out/(name+'.stderr')).open('wb')
            self.p=subprocess.Popen([str(exe),str(b.fileno()),str(op),str(fault),str(gate_r),str(audit_w),str(family)],
                pass_fds=(b.fileno(),gate_r,audit_w),stdout=self.stdout,stderr=self.stderr)
            b.close();os.close(gate_r);os.close(audit_w);self.seq=0;self.last=None
        def receive(self):
            assert select.select([self.a],[],[],2)[0], 'fixture response timeout; preserve process, no kill'
            result=decode(self.a.recv(677));self.last=result;self.seq=result['requests'];return result
        def call(self,op,payload=b'',raw=None,**fields):
            wire=raw if raw is not None else request(self.seq+1,op,payload,**fields)
            self.a.send(wire);return self.receive()
        def observe(self):assert self.call(1)['status']==0
        def begin(self):
            self.observe();assert self.call(2,START)['status']==0;self.observe()
        def finish(self):
            if self.p.poll() is None:
                r=self.call(5);assert r['status'] in (0,4)
                assert r['pending']==0
            self.p.wait(timeout=2);assert self.p.returncode==0
            self.stdout.close();self.stderr.close();self.a.close();os.close(self.gate);os.close(self.audit)
            result=json.loads((out/(self.name+'.stdout.json')).read_text())
            assert result['host_idle'] and not result['native_pending'] and not result['body_completion_proven'] and not result['automatic_STOP']
            return result
    try:
        for family in (2,8):
            p=Peer('flow-'+str(family),family=family);p.begin()
            for round_index in range(3):
                p.observe();r=p.call(3,auth(1));assert r['status']==0 and r['bytes']==516
                assert not r['native'][0]['actual_known'] and r['native'][1]['actual_known']
                p.observe();r=p.call(3,auth(3,b'\x01'+bytes(20 if family==2 else 32)));assert r['status']==0
            p.observe();assert p.call(3,auth(5))['status']==0
            assert p.call(3,auth(1))['status']==1
            assert p.call(2,START)['status']==1
            p.observe();assert p.call(4,STOP)['status']==0
            assert p.call(4,STOP)['status']==1
            result=p.finish();assert result['calls']==[2,7,7]
            done('native-MSC-budget-grammar-and-single-STOP-family-'+str(family),summary=result)
        for label,wire in [('short',request(1,1)[:-1]),('oversized',request(1,1)+b'x'),
                           ('bad-magic',bytes(4)+request(1,1)[4:]),('bad-version',request(1,1)[:4]+struct.pack('<I',2)+request(1,1)[8:])]:
            p=Peer('frame-'+label);r=p.call(1,raw=wire);assert r['status']==2
            assert p.finish()['calls']==[0,0,0];done('one-datagram-reject-'+label)
        for label,kw in [('foreign-generation',{'generation':18}),('wrong-session-nonce',{'nonce':bytes(16)})]:
            p=Peer(label);assert p.call(1,**kw)['status']==1
            assert p.finish()['calls']==[0,0,0];done(label)
        p=Peer('replay');p.observe();assert p.call(2,START)['status']==0
        assert p.call(2,START,raw=request(p.seq,2,START))['status']==1
        assert p.finish()['calls']==[1,0,0];done('replayed-ID-cannot-resend-START')
        p=Peer('missing-new-observation');p.observe();assert p.call(2,START)['status']==0
        assert p.call(3,auth(1))['status']==5
        p.observe();assert p.call(3,auth(1))['status']==1
        assert p.finish()['calls']==[1,0,0];done('pre-START-observation-cannot-arm-and-no-retry-after-denial')
        p=Peer('bad-commands');p.begin()
        for value in (auth(3,b'\x01'+bytes(32)),auth(1,b'\x01'),auth(0xff01),auth(1)[:-1]):
            assert p.call(3,value)['status'] in (1,2)
        assert p.finish()['calls']==[1,0,0];done('native-grammar-refuses-skipped-or-nonzero-challenge-and-bad-length')
        for op,fault,want,hard in [(2,1,3,False),(2,2,4,True),(3,5,7,False),(3,6,8,True),(2,7,9,True),(2,17,10,True)]:
            p=Peer('native-fault-'+str(op)+'-'+str(fault),op,fault);p.begin()
            r=p.call(3,auth(1));assert r['status']==5 and r['native'][op-2]['status']==want
            assert bool(r['flags']&8)==hard and r['pending']==0 and r['bytes']==0
            if not hard:
                assert p.call(4,STOP)['status']==5
                # Failed stale cleanup consumes its sole STOP; never automatically re-send.
                p.observe();assert p.call(4,STOP)['status']==1
            else:
                p.observe();assert p.call(4,STOP)['status']==1
            summary=p.finish();assert summary['calls']==[1,1,int(op==3)]
            done('native-failure-no-retry-'+str(op)+'-'+str(fault),result=public(r),summary=summary)
        p=Peer('explicit-fresh-STOP',2,1);p.begin();assert p.call(3,auth(1))['status']==5
        p.observe();assert p.call(4,STOP)['status']==0
        assert p.finish()['calls']==[2,1,0];done('fresh-observation-admits-only-explicit-one-STOP')
        p=Peer('blocked-return',2,12);p.begin()
        p.a.send(request(p.seq+1,3,auth(1)))
        assert select.select([p.audit],[],[],2)[0] and os.read(p.audit,1)==b'B'
        assert p.p.poll() is None and not select.select([p.a],[],[],0.05)[0]
        os.write(p.gate,b'R');r=p.receive();assert r['status']==0 and not r['pending']
        assert p.finish()['calls']==[1,1,1];done('real-child-remains-pending-until-explicit-fake-gate-release')

        # A real intermediate controller exits while its C child is in a fake native call.
        # Grandparent retains the datagram and explicit fixture gate, never kills the child.
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
        gate_r,gate_w=os.pipe();audit_r,audit_w=os.pipe();ready_r,ready_w=os.pipe()
        stdout=(out/'parent-exit.stdout.json').open('wb');stderr=(out/'parent-exit.stderr').open('wb')
        controller=os.fork()
        if controller==0:
            try:
                child=subprocess.Popen([str(exe),str(b.fileno()),'2','12',str(gate_r),str(audit_w),'8'],
                    pass_fds=(b.fileno(),gate_r,audit_w),stdout=stdout,stderr=stderr)
                b.close();os.close(audit_w);os.close(gate_r)
                for seq,op,value in ((1,1,b''),(2,2,START),(3,1,b'')):
                    a.send(request(seq,op,value));assert decode(a.recv(677))['status']==0
                a.send(request(4,3,auth(1)))
                assert select.select([audit_r],[],[],2)[0] and os.read(audit_r,1)==b'B'
                os.write(ready_w,str(child.pid).encode())
                os._exit(0)
            except BaseException:
                os._exit(90)
        b.close();os.close(gate_r);os.close(audit_w);os.close(ready_w)
        assert select.select([ready_r],[],[],3)[0]
        child_pid=int(os.read(ready_r,32));os.close(ready_r)
        assert os.waitpid(controller,0)[1]==0
        assert select.select([audit_r],[],[],2)[0] and os.read(audit_r,1)==b'P'
        os.kill(child_pid,0)  # Existence query only, signal0.
        assert not select.select([a],[],[],0.05)[0]
        os.write(gate_w,b'R')
        assert select.select([a],[],[],2)[0]
        r=decode(a.recv(677));assert r['status']==5 and r['native'][0]['status']==17 and r['pending']==0
        deadline=time.monotonic()+2
        while (out/'parent-exit.stdout.json').stat().st_size==0 and time.monotonic()<deadline:time.sleep(0.005)
        stdout.close();stderr.close();summary=json.loads((out/'parent-exit.stdout.json').read_text())
        assert not summary['peer_alive'] and summary['calls']==[1,1,0] and not summary['automatic_STOP'] and summary['host_idle']
        a.close();os.close(gate_w);os.close(audit_r)
        done('actual-controller-exit-sets-cancel-retains-pending-no-IN-or-automatic-STOP',result=public(r),summary=summary)
        report['status']='PASS_NATIVE_MSC_DISPATCH_AND_REAL_PROCESS_FIXTURES_NO_USB'
    except BaseException as error:
        report['status']='FAIL';report['error']={'type':type(error).__name__,'text':str(error),'traceback':traceback.format_exc()}
        raise
    finally:
        report['case_count']=len(cases)
        report['source_sha256']={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.c'))+sorted(out.glob('*.h'))+[out/'test_process_channel.py']}
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'cases':len(cases),'real_USB_or_root':0}))


if __name__=='__main__':main()
