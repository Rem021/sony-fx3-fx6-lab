"""Offline tests execute the candidate helper and the runner's cleanup excerpt."""
import hashlib, json, re, struct, tempfile, textwrap, types, unittest
from pathlib import Path
from unittest.mock import patch
import snapshot_tail_v15 as tail
from gate_input_usability import InputGate


class Clock:
    def __init__(self): self.t=100.0;self.on_sleep=None
    def __call__(self): return self.t
    def sleep(self,n):
        self.t+=max(n,.02)
        if self.on_sleep:self.on_sleep()


class Transport:
    send_unknown=False


class Sock:
    def __init__(self): self.timeout=3;self.closed=False
    def gettimeout(self):return self.timeout
    def settimeout(self,x):self.timeout=x
    def close(self):self.closed=True


class Gate:
    def __init__(self):self.sock=Sock()


class FakeWire:
    instance=None
    def __init__(self,gate,clock):
        self.gate=gate;self.clock=clock;self.unknown=False;self.request=bytearray(64)
        self.original_timeout=gate.sock.gettimeout();FakeWire.instance=self
        self.fail_write=False
    def connect(self,deadline):pass
    def read(self,addr,length,deadline):
        if addr==tail.BASE:return struct.pack('<8Q',tail.UI_MAGIC,2,0,0,321,0,0,0)
        if addr==tail.ACK:
            w=[0]*48;w[0]=tail.READY_MAGIC;w[1]=5;w[2]=0xc0;w[3]=321
            w[4]=0x1234;w[6]=0x310
            return struct.pack('<48I',*w)
        if addr==tail.REQ:return bytes(self.request[:length])
        raise AssertionError(addr)
    def write(self,addr,data,deadline):
        if self.fail_write:raise TimeoutError('write_unknown')
        off=addr-tail.REQ;self.request[off:off+len(data)]=data
    def release(self):self.gate.sock.settimeout(self.original_timeout)


class QMP:
    def __init__(self,run,serial,clock,wire,transport,**flags):
        self.run=run;self.serial=serial;self.clock=clock;self.wire=wire
        self.flags=flags;self.transport=transport;self.running=False;self.calls=[];self.slot_reads=0
    def slot(self):
        if self.flags.get('no_probe'):return bytes(tail.SLOT_BYTES)
        w=struct.unpack('<16I',self.wire().request);tag=w[4]|(w[5]<<32);nonce=w[6]|(w[7]<<32)
        payload=bytes(0x310);h=[0]*48
        h[0]=tail.ACK_MAGIC;h[1]=5;h[2]=0xc0;h[3]=321
        h[4]=w[4];h[5]=w[5];h[6]=w[6];h[7]=w[7];h[8]=0x1234
        h[10]=9;h[11]=42;h[12]=1;h[14]=2;h[16]=0x310
        h[17]=tail.fnv32(payload);h[18]=1;h[19]=tail.ACK_COMMIT
        if self.flags.get('wrong_slot_nonce'):h[6]^=1
        if self.flags.get('half_commit'):h[19]=0
        raw=struct.pack('<48I',*h)+payload
        if self.flags.get('partial_slot'):raw=raw[:100]
        if self.flags.get('changing_slot') and self.slot_reads==2:raw=raw[:-1]+bytes([raw[-1]^1])
        return raw
    def __call__(self,name,args=None,*,timeout=None):
        self.calls.append(name)
        if name=='query-status':return {'return':{'running':self.running,'status':'running' if self.running else 'paused'}}
        if name=='cont':
            self.running=True
            if not self.flags.get('no_ack'):
                w=struct.unpack('<16I',self.wire().request)
                tag=w[4]|(w[5]<<32);nonce=w[6]|(w[7]<<32)
                line=f'FX3_UI_GATE_SNAPSHOT_ACK pid=321 tag={tag:#x} nonce={nonce:#x} probe=9\n'
                if self.flags.get('wrong_ack'):line=line.replace('nonce=', 'nonce=0x0 wrong=')
                if self.flags.get('half_ack'):line=line.rstrip('\n')
                elif self.flags.get('crlf_ack'):line=line.rstrip('\n')+'\r\n'
                elif self.flags.get('split_crlf_ack'):line=line.rstrip('\n')+'\r'
                self.serial.write_bytes(line.encode())
            if self.flags.get('send_unknown_cont'):
                self.transport.send_unknown=True;raise TimeoutError('cont_send_unknown')
            if self.flags.get('lost_cont_reply'):raise TimeoutError('lost_cont_reply')
            return {'return':{}}
        if name=='stop':self.running=False;return {'return':{}}
        if name=='human-monitor-command':
            cmd=args['command-line'];m=re.search(r'"([^"]+)"$',cmd);assert m
            self.slot_reads+=1
            Path(m[1]).write_bytes(self.slot())
            if self.flags.get('late_slot'):self.clock.t+=6
            return {'return':''}
        raise AssertionError(name)


class TailTests(unittest.TestCase):
    def run_case(self,wire_class=FakeWire,transport_unknown=False,**flags):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        run=Path(tmp.name);serial=run/'serial.log';serial.write_bytes(b'')
        clock=Clock();gate=Gate();transport=Transport();transport.send_unknown=transport_unknown
        qmp=QMP(run,serial,clock,lambda:FakeWire.instance,transport,**flags)
        if flags.get('split_crlf_ack'):
            def finish_line():
                clock.on_sleep=None
                with serial.open('ab') as out:out.write(b'\n')
            clock.on_sleep=finish_line
        with patch.object(tail,'GateWire',wire_class):
            rec=tail.capture(qmp,transport,gate,serial,run,'launch-uuid',
                [{'name':'ui-gate-counters.bin','address':tail.BASE,'size':0x10000}],
                clock=clock,sleep=clock.sleep,nonce_factory=lambda:0x12345678)
        self.assertEqual(gate.sock.gettimeout(),3)
        self.assertTrue((run/'snapshot-tail-receipt.json').is_file())
        return rec,qmp
    def test_valid_and_identity(self):
        rec,qmp=self.run_case()
        self.assertEqual(rec['status'],'valid_nontransactional_tail_checkpoint')
        self.assertTrue(rec['pause_proven_at_return']);self.assertEqual(rec['object_mismatch'],0)
        self.assertEqual(qmp.calls.count('cont'),1);self.assertEqual(qmp.calls.count('human-monitor-command'),2)
    def test_lost_cont_reply_is_stopped_but_unknown(self):
        rec,qmp=self.run_case(lost_cont_reply=True)
        self.assertTrue(rec['qmp_cont_attempted']);self.assertTrue(rec['pause_proven_at_return'])
        self.assertIn('stop',qmp.calls);self.assertNotEqual(rec['status'],'valid_nontransactional_tail_checkpoint')
    def test_unknown_cont_send_is_not_retried(self):
        rec,qmp=self.run_case(send_unknown_cont=True)
        self.assertEqual(qmp.calls.count('cont'),1)
        self.assertNotIn('stop',qmp.calls)
        self.assertFalse(rec['pause_proven_at_return'])
        self.assertNotEqual(rec['status'],'valid_nontransactional_tail_checkpoint')
    def test_wrong_missing_and_half_ack(self):
        for flag in ('wrong_ack','no_ack','half_ack'):
            with self.subTest(flag=flag):
                rec,_=self.run_case(**{flag:True})
                self.assertNotEqual(rec['status'],'valid_nontransactional_tail_checkpoint')
                self.assertTrue(rec['pause_proven_at_return'])
    def test_crlf_and_split_crlf_require_complete_line(self):
        for flag in ('crlf_ack','split_crlf_ack'):
            with self.subTest(flag=flag):
                rec,_=self.run_case(**{flag:True})
                self.assertEqual(rec['status'],'valid_nontransactional_tail_checkpoint')
                self.assertTrue(rec['serial_ack_line'].endswith('\r\n'))
    def test_slot_failures_and_deadline(self):
        for flag in ('partial_slot','changing_slot','late_slot','wrong_slot_nonce','half_commit','no_probe'):
            with self.subTest(flag=flag):
                rec,_=self.run_case(**{flag:True})
                self.assertNotEqual(rec['status'],'valid_nontransactional_tail_checkpoint')
                self.assertTrue(rec['pause_proven_at_return'])
    def test_request_failure_never_continues(self):
        class FailWrite(FakeWire):
            def __init__(self,*a):super().__init__(*a);self.fail_write=True
        rec,qmp=self.run_case(wire_class=FailWrite)
        self.assertNotIn('cont',qmp.calls)
        self.assertEqual(rec['status'],'unknown')
        self.assertTrue(rec['pause_proven_at_return'])
    def test_request_commit_after_deadline_never_continues(self):
        class SlowCommit(FakeWire):
            def write(self,addr,data,deadline):
                super().write(addr,data,deadline)
                if addr==tail.REQ+60:self.clock.t+=3
        rec,qmp=self.run_case(wire_class=SlowCommit)
        self.assertNotIn('cont',qmp.calls)
        self.assertTrue(rec['capture_deadline_expired'])
    def test_qmp_unknown_never_reads_or_continues(self):
        rec,qmp=self.run_case(transport_unknown=True)
        self.assertEqual(qmp.calls,[])
        self.assertEqual(rec['status'],'unknown')
    def test_uncertain_gdb_stream_is_closed_not_reused(self):
        class LateSock(Sock):
            def sendall(self,b):pass
            def recv(self,n):raise TimeoutError('delayed GDB reply')
        gate=Gate();gate.sock=LateSock();clock=Clock()
        wire=tail.GateWire(gate,clock)
        with self.assertRaises(TimeoutError):wire.packet('m41dc00000,40',clock()+1)
        wire.release()
        self.assertIsNone(gate.sock)
        self.assertTrue(wire.original_sock.closed)
        gate=Gate();wire=tail.GateWire(gate,clock)
        gate.sock.settimeout(.001);wire.release()
        self.assertEqual(gate.sock.gettimeout(),3)
        class FreshSock(Sock):
            def __init__(self):super().__init__();self.incoming=bytearray(b'+$OK#9a+$1#31');self.sent=[]
            def connect(self,path):self.path=path
            def sendall(self,b):self.sent.append(b)
            def recv(self,n):
                if not self.incoming:raise AssertionError('unexpected GDB read')
                out=bytes(self.incoming[:n]);del self.incoming[:n];return out
        old=LateSock();actual=InputGate('/tmp',socket_path='/tmp/owned-gdb.sock');actual.sock=old
        wire=tail.GateWire(actual,clock)
        with self.assertRaises(TimeoutError):wire.packet('m41dc00000,40',clock()+1)
        wire.release();fresh=FreshSock()
        with patch('gate_input_usability.socket.socket',return_value=fresh):actual.connect()
        self.assertTrue(old.closed);self.assertIs(actual.sock,fresh)
        self.assertEqual(fresh.sent[0][:1],b'$')
    def test_unproved_new_gdb_mode_is_discarded(self):
        class BadModeSock(Sock):
            def __init__(self):super().__init__();self.incoming=bytearray(b'+$E01#a6')
            def connect(self,path):pass
            def sendall(self,b):pass
            def recv(self,n):
                out=bytes(self.incoming[:n]);del self.incoming[:n];return out
        gate=InputGate('/tmp',socket_path='/tmp/owned-gdb.sock')
        bad=BadModeSock();wire=tail.GateWire(gate,Clock())
        with patch('snapshot_tail_v15.socket.socket',return_value=bad):
            with self.assertRaises(tail.TailError):wire.connect(101)
        wire.release();self.assertTrue(bad.closed);self.assertIsNone(gate.sock)
    def test_default_runner_and_cleanup_excerpt(self):
        src=Path(__file__).with_name('run_trial_v25_diag_r3.py').read_text()
        self.assertIn("if ns.snapshot_tail and ring_complete:",src)
        self.assertIn("elif ns.snapshot_tail:",src)
        self.assertIn("tail_pause_unproven_no_safe_native_restore",src)
        start=src.index('                    if ns.snapshot_tail and ring_complete:')
        end=src.index("                try:\n                    qmp('quit')",start)
        code=compile(textwrap.dedent(src[start:end]),'<actual-runner-cleanup>','exec')
        for enabled,ring_complete,pause in ((False,True,False),(True,True,True),(True,True,False),(True,False,False)):
            calls=[];transport=Transport();status={'return':{'running':False,'status':'paused'}}
            env={'ns':types.SimpleNamespace(snapshot_tail=enabled),'ring_complete':ring_complete,
                 'shutdown':{'diag_snapshot':{'consistent':False,'readback_complete':True}},'transport':transport,
                 'qmp':lambda *a,**k:(calls.append(a[0]),status)[1],
                 'input_gate':None,'run':Path('/tmp'),'launch_uuid':'uuid','snapshots':[],
                 'capture_snapshot_tail':lambda *a,**k:(calls.append('capture'),{'pause_proven_at_return':pause,'status':'test'})[1],
                 'restore_native_api':lambda *a,**k:(calls.append('restore'),{'passed':True,'reason':'already_original_no_request_no_resume'})[1]}
            exec(code,env)
            self.assertIn('restore',calls)
            self.assertEqual(calls.count('capture'),int(enabled and ring_complete))
            self.assertEqual(calls.count('query-status'),int(enabled and not pause))
            if enabled and not ring_complete:self.assertEqual(env['shutdown']['snapshot_tail_v15']['status'],'not_attempted')
        # A lost pause proof cannot call restore; quit/reap live outside this excerpt.
        calls=[];transport=Transport()
        env.update({'ns':types.SimpleNamespace(snapshot_tail=True),'ring_complete':True,'shutdown':{},
                    'qmp':lambda *a,**k:(calls.append(a[0]),{'error':'unknown'})[1],
                    'capture_snapshot_tail':lambda *a,**k:{'pause_proven_at_return':False}})
        exec(code,env);self.assertNotIn('restore',calls)
        self.assertEqual(env['shutdown']['restore_error'],'tail_pause_unproven_no_safe_native_restore')


if __name__=='__main__':unittest.main()
