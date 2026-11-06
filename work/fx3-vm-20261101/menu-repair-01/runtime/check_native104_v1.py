import socket,tempfile,select
from gdb_native104_v1 import InputGate
def frame(s):b=s.encode();return b'$'+b+b'#'+f'{sum(b)%256:02x}'.encode()
with tempfile.TemporaryDirectory(prefix='fx3-native104-')as td:
 a,b=socket.socketpair();a.settimeout(1);g=InputGate(td);g.sock=a
 b.sendall(b'+'+frame('T05thread:03;')+frame('1234'));assert g.packet('g')=='1234'and g.native_thread=='03';wire=b.recv(4096);assert b'$g#'in wire
 b.sendall(frame('OK')+frame('OK'));g.bind_native_stop();wire=b.recv(4096);assert b'$Hg03#'in wire and b'$Hc03#'in wire and b'qC'not in wire
 b.sendall(b'+'+frame('T05thread:03;'));assert g.packet('s').startswith('T05');wire=b.recv(4096);assert b'$vCont;s:03#'in wire and b'$s#'not in wire
 g.continue_all();wire=b.recv(4096);assert b'$vCont;c#'in wire and g.native_thread is None
 b.sendall(b'+');assert not g.wait_native_stop(.01);assert not select.select([b],[],[],0)[0]
 b.sendall(frame('T05thread:04;'));assert g.wait_native_stop(.1)and g.native_thread=='04';b.recv(4096)
 a.close();b.close()
print('AP104_NATIVE_T05_CHECKSUM_CPU_BIND_SINGLE_THREAD_VCONT_ACK_ONLY_ASYNC_PASS')
