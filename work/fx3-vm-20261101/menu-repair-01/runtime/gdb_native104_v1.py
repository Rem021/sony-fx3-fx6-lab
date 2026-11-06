"""Native stop-packet CPU identity and single-vCPU stepping.
vCont;c is asynchronous; vCont;s:THREAD leaves every other vCPU stopped.
Hg/Hc bind only an actual checksum-verified T05 thread, never qC's first CPU.
"""
import re,select,time
from gate_input102_v4 import InputGate as FrozenInputGate
class InputGate(FrozenInputGate):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.native_stop=None;self.native_thread=None
    def _frame(self):
        data=bytearray()
        while True:
            c=self.sock.recv(1)
            if not c:raise RuntimeError('AP104 native GDB frame ended')
            if c==b'#':break
            data.extend(c)
        checksum=self.exact(2)
        if int(checksum,16)!=sum(data)%256:raise RuntimeError('AP104 native GDB checksum mismatch')
        self.sock.sendall(b'+');return data.decode()
    def _stop(self,response):
        if response.startswith('T05'):
            m=re.search(r'(?:^|;)thread:([^;]+)',response[3:])
            if not m:raise RuntimeError('AP104 native T05 lacks CPU thread identity')
            if not re.fullmatch(r'(?:p[0-9a-fA-F]+\.)?[0-9a-fA-F]+',m[1]):raise RuntimeError('Invalid native GDB CPU identity')
            self.native_stop=response;self.native_thread=m[1]
        self.debug_stops.append(response)
    def _send(self,payload):
        b=payload.encode();self.sock.sendall(b'$'+b+b'#'+f'{sum(b)%256:02x}'.encode())
    def packet(self,payload):
        step=payload=='s'
        if step:
            if self.native_thread is None:raise RuntimeError('Cannot step without native T05 CPU identity')
            requested=self.native_thread;wire='vCont;s:'+requested
        else:wire=payload
        self._send(wire)
        while True:
            c=self.sock.recv(1)
            if not c:raise RuntimeError('AP104 native GDB stream ended')
            if c==b'-':raise RuntimeError('AP104 outgoing GDB checksum rejected')
            if c!=b'$':continue
            r=self._frame()
            if r.startswith(('T','S')):
                self._stop(r)
                if step:
                    if not r.startswith('T05')or self.native_thread!=requested:raise RuntimeError('Single-vCPU step stopped on a different native CPU')
                    return r
                continue
            if r.startswith('O')and r!='OK':continue
            return r
    def wait_native_stop(self,timeout=.25):
        end=time.monotonic()+timeout
        while True:
            if not select.select([self.sock],[],[],max(0,end-time.monotonic()))[0]:return False
            c=self.sock.recv(1)
            if not c:raise RuntimeError('AP104 asynchronous GDB stream ended')
            if c==b'-':raise RuntimeError('AP104 asynchronous resume rejected')
            if c==b'$':
                r=self._frame()
                if r.startswith(('T','S')):
                    self._stop(r)
                    if r.startswith('T05'):return True
                elif not r.startswith('O'):raise RuntimeError('Unexpected asynchronous GDB response '+r)
            if time.monotonic()>=end:return False
    def continue_all(self):
        self.connect()
        # Consume any prior QMP-pause notification, without issuing a command
        # which would reset QEMU's allow_stop_reply flag for this continuation.
        self.wait_native_stop(0)
        self.native_stop=None;self.native_thread=None;self._send('vCont;c')
    def bind_native_stop(self):
        if self.native_thread is None:raise RuntimeError('No native stopped CPU to bind')
        for kind in ['Hg','Hc']:
            if self.packet(kind+self.native_thread)!='OK':raise RuntimeError('Cannot bind actual native stopped CPU')
