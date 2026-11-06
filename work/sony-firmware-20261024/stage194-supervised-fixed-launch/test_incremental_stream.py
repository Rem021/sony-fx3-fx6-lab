"""One actual local-stream check: partial HELLO survives observation timeout.

Same-user socket peer, explicit synthetic HELLO based on a captured fake-owner
record. No helper launch, root, camera, process kill or replacement connection.
"""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import json,os,secrets,socket,struct
import controller_ipc as I
import receipt_receiver as R
import supervisor as S
HERE=S.HERE
assert os.getuid()==os.geteuid()!=0
ipc=I.IPC();identity=ipc.probe(os.getpid());assert identity
proof=R.capture_helper(os.getpid(),os.getuid(),identity.path,identity.image_sha256,ipc.probe,mode='fixture')
saved=json.loads((HERE/'template-hello-proof.json').read_text());nonce=bytes.fromhex(saved['nonce'])
data=bytearray((HERE/'template-hello.bin').read_bytes())
struct.pack_into('<IIQQ',data,16,identity.uid,identity.pid,identity.sec,identity.usec)
data[88:120]=bytes.fromhex(identity.image_sha256);data[128:]=sha256(data[:128]).digest()
packet=struct.pack('<I',160)+data
directory=S.SOCKET_ROOT/('partial-'+secrets.token_hex(4));directory.mkdir(mode=0o700);path=directory/'s'
server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);conn=None
try:
    server.bind(str(path));os.chmod(path,0o600);server.listen(1);client.connect(str(path));conn,_=server.accept();conn.setblocking(False)
    j=S.Job.__new__(S.Job);j.conn=conn;j.server=server;j.verified=proof;j.frame=SimpleNamespace(nonce=nonce)
    j.receiver=R.Receiver(conn,proof,nonce);j.buffer=bytearray();j.total_bytes=0;j.hello=None;j.receipt=None;j.stream_eof=False
    def take_hello(payload):j.hello=j.receiver.accept_hello(payload)
    j._hello=take_hello
    original_fd=conn.fileno();client.sendall(packet[:7]);j._network(.02)
    assert bytes(j.buffer)==packet[:7] and j.hello is None and conn.fileno()==original_fd
    j._network(.01) # observation expires; no new connection/nonce/PID or ACK
    assert bytes(j.buffer)==packet[:7] and conn.fileno()==original_fd and not j.receiver.acknowledged
    client.sendall(packet[7:]);j._network(.05)
    assert not j.buffer and j.hello['kernel_peer_and_self_image_checked'] and conn.fileno()==original_fd
    assert not j.receiver.acknowledged # format/identity receipt alone is not an operation release
finally:
    if conn:conn.close()
    client.close();server.close()
    if path.exists():path.unlink()
    directory.rmdir()
report={'status':'PASS_INCREMENTAL_SAME_STREAM','tests_run':1,'actual_same_UID_kernel_peer':True,
        'synthetic_HELLO_explicit':True,'observation_timeout_preserves_partial_bytes_and_fd':True,
        'new_root_camera_or_helper_operations':0,'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'supervisor_source_sha256':sha256((HERE/'supervisor.py').read_bytes()).hexdigest(),
        'receiver_source_sha256':sha256((HERE/'receipt_receiver.py').read_bytes()).hexdigest()}
S.put(HERE/'incremental-stream-result.json',report);print(json.dumps(report))
