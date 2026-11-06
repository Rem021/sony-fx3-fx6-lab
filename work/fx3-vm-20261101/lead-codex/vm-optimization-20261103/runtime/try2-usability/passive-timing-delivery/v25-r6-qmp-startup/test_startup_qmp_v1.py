import fcntl
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from qmp_line_transport import QmpDeadline, QmpLineTransport
from startup_qmp_v1 import startup_handshake, is_proven_prelaunch
import run_trial_v25_diag_r3 as runner
from runtime_resource_guard import RuntimeResourceGuard

class StubGuard:
    def __init__(self): self.qmp = None
    def set_qmp(self, qmp): self.qmp = qmp

def peer_line(sock):
    raw = bytearray()
    while not raw.endswith(b'\n'):
        chunk = sock.recv(4096)
        if not chunk: raise EOFError('peer closed')
        raw.extend(chunk)
    return json.loads(raw)

def socket_case(mode, delay=.0, budget=.2):
    client, peer = socket.socketpair()
    requests = []
    def server():
        try:
            peer.sendall(b'{"QMP":{"version":{},"capabilities":[]}}\n')
            req = peer_line(peer)
            requests.append(req)
            assert req == {'execute':'qmp_capabilities','id':1}
            if mode == 'eof': return
            if mode == 'late':
                time.sleep(delay)
                peer.sendall(b'{"event":"BOOT","data":{}}\n{"return":')
                time.sleep(.02)
                peer.sendall(b'{},"id":1}\n')
            elif mode == 'partial_timeout':
                peer.sendall(b'{"return":')
                time.sleep(delay)
            elif mode == 'event':
                peer.sendall(b'{"event":"BOOT","data":{}}\n{"return":{},"id":1}\n')
            elif mode == 'error':
                peer.sendall(b'{"error":{"class":"GenericError"},"id":1}\n')
        finally: peer.close()
    thread = threading.Thread(target=server)
    thread.start()
    with tempfile.TemporaryDirectory() as tmp:
        journal=[]
        transport=QmpLineTransport(client,journal,started=time.monotonic())
        guard=StubGuard()
        def qmp(name,arguments=None,*,timeout=None):
            return transport.command(name,arguments,timeout=timeout)
        outcome='success'
        try:
            startup_handshake(transport,qmp,guard,Path(tmp),journal,budget_seconds=budget)
        except Exception as exc:
            outcome=type(exc).__name__
        record=json.loads((Path(tmp)/'startup-qmp-timing.json').read_text())
        assert len(requests)==1 and transport.sequence==1
        assert record['capabilities_request_id']==1
        assert record['send_unknown'] is False
        if mode in ('late','event'):
            assert outcome=='success' and record['matched_success']
            assert record['capabilities_response_id']==1
        elif mode=='partial_timeout':
            assert outcome=='QmpDeadline' and record['buffered_bytes']>0
        elif mode=='eof':
            assert outcome=='EOFError' and not record['matched_success']
        else:
            assert outcome=='QmpProtocolError' and not record['matched_success']
    client.close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def pretransport_error_case(kind):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); run=root/'run'; run.mkdir()
        held={}
        def main():
            guard=RuntimeResourceGuard(run)
            runner.ACTIVE_GUARD=guard
            lock=(root/'lock').open('a+b')
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            guard.add_lock(lock)
            held.update(guard=guard,lock=lock)
            try:
                if kind=='connect':
                    child=subprocess.Popen(['/bin/sleep','30'],start_new_session=True)
                    guard.set_process(child); held['child']=child
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
                        sock.connect(guard.alias.path('q'))
                else:
                    subprocess.Popen(['/path/does/not/exist/r6-test-qemu'],start_new_session=True)
            except Exception as exc:
                runner.write_host_first_exception(run,[],exc,None)
                raise
        try:
            assert runner.execute_runner(main,guard_retry_seconds=.01,reap_wait=.05)==2
            record=json.loads((run/'host-first-exception.json').read_text())
            assert record['type']=='FileNotFoundError'
            assert record['qmp_send_unknown'] is None and record['qmp_buffered_bytes'] is None
            assert 'FileNotFoundError' in record['traceback']
            assert held['guard'].closed and held['lock'].closed
            if kind=='connect': assert held['child'].poll() is not None
        finally:
            runner.ACTIVE_GUARD=None


def unknown_send_case():
    class Transport:
        started=0
        sequence=0
        buffer=bytearray()
        send_unknown=False
        def read_json(self,**kw): return {'QMP':{}}
        def command(self,*args,**kw):
            self.sequence+=1; self.send_unknown=True
            raise QmpDeadline('send result unknown')
    t=Transport(); guard=StubGuard(); journal=[]
    with tempfile.TemporaryDirectory() as tmp:
        try:
            startup_handshake(t,t.command,guard,Path(tmp),journal,budget_seconds=.2)
        except QmpDeadline: pass
        else: raise AssertionError('unknown send accepted')
        r=json.loads((Path(tmp)/'startup-qmp-timing.json').read_text())
        assert t.sequence==1 and r['send_unknown'] and not r['matched_success']

if __name__=='__main__':
    socket_case('late',delay=4.1,budget=12.0)
    socket_case('partial_timeout',delay=.2,budget=.08)
    socket_case('event',budget=.2)
    socket_case('eof',budget=.2)
    socket_case('error',budget=.2)
    unknown_send_case()
    pretransport_error_case('connect')
    pretransport_error_case('popen')
    assert is_proven_prelaunch({'return':{'status':'prelaunch','running':False}})
    assert not is_proven_prelaunch({'return':{'status':'paused','running':False}})
    assert not is_proven_prelaunch({'return':{'status':'prelaunch','running':True}})
    print('delayed matched id, partial/event/EOF/error/unknown-send, pretransport and prelaunch PASS')
