#!/usr/bin/env python3
"""Strict read-only RSP transport used by the observer adapter.

Handles fragmented/merged packets, leading ACK, exact two-hex checksum,
console O packets, asynchronous T05 stops, timeout/EOF, and only
Qqemu.PhyMemMode/Hg/Hc/g/m/Z1/z1.  No guest write or software step command.
"""
import os,re,select,socket,struct,time
from pathlib import Path

class RSP:
    ALLOWED=re.compile(r'(?:Qqemu\.PhyMemMode:[01]|qqemu\.PhyMemMode|Hg(?:p[0-9a-f]+\.)?[0-9a-f]+|Hc(?:p[0-9a-f]+\.)?[0-9a-f]+|g|m[0-9a-f]+,[0-9a-f]+|c|p[0-9a-f]+|qXfer:features:read:[A-Za-z0-9_.-]+:[0-9a-f]+,[0-9a-f]+|Z1,[0-9a-f]+,4|z1,[0-9a-f]+,4)',re.I)
    def __init__(self,sock,deadline=None):
        self.sock=sock;self.deadline=deadline;self.sock.settimeout(1.0);self.stops=[];self._pending=b''
    def _remaining(self,default=2.0):
        if self.deadline is None:return default
        try:return max(.001,self.deadline.remaining_total())
        except Exception:return default
    @classmethod
    def connect(cls,run,deadline=None):
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        old=Path.cwd()
        try:
            os.chdir(run);s.settimeout(.25);import time
            while True:
                try:s.connect('g');break
                except (BlockingIOError,ConnectionRefusedError):
                    if deadline is not None and deadline.remaining_total()<=0:raise TimeoutError('RSP connect deadline')
                    time.sleep(.02)
        finally:os.chdir(old)
        return cls(s,deadline)
    def _exact(self,n,deadline):
        out=b''
        while len(out)<n:
            if time.monotonic()>deadline:raise TimeoutError('RSP checksum timeout')
            self.sock.settimeout(min(.1,max(.001,deadline-time.monotonic())))
            try:c=self.sock.recv(n-len(out))
            except socket.timeout:continue
            if not c:raise ConnectionError('RSP truncated checksum')
            out+=c
        return out
    def _one(self,deadline):
        while True:
            if time.monotonic()>deadline:raise TimeoutError('RSP packet timeout')
            self.sock.settimeout(min(.1,max(.001,deadline-time.monotonic())))
            try:c=self.sock.recv(1)
            except socket.timeout:continue
            if not c:raise ConnectionError('RSP socket closed')
            if c==b'-':raise ValueError('RSP outgoing checksum rejected')
            if c in (b'+',b'\n',b'\r'):continue
            if c!=b'$':raise ValueError('unexpected RSP framing '+repr(c))
            raw=bytearray()
            while True:
                if time.monotonic()>deadline:raise TimeoutError('RSP payload timeout')
                try:c=self.sock.recv(1)
                except socket.timeout:continue
                if not c:raise ConnectionError('RSP truncated payload')
                if c==b'#':break
                raw.extend(c)
                if len(raw)>65536:raise ValueError('RSP payload too long')
            # Exactly two checksum hex digits; never accept "+$OK#" or "+$OK#0".
            tail=self._exact(2,deadline)
            if not re.fullmatch(rb'[0-9a-fA-F]{2}',tail):raise ValueError('RSP checksum digits invalid')
            got=int(tail,16)
            if got!=sum(raw)&255:
                self.sock.sendall(b'-');raise ValueError('RSP incoming checksum mismatch')
            self.sock.sendall(b'+')
            un=bytearray();i=0
            while i<len(raw):
                if raw[i]==0x7d:
                    i+=1
                    if i==len(raw):raise ValueError('RSP dangling escape')
                    un.append(raw[i]^0x20)
                else:un.append(raw[i])
                i+=1
            return un.decode('ascii')
    def command(self,payload,timeout=None):
        if timeout is None:timeout=self._remaining(2.0)
        if not self.ALLOWED.fullmatch(payload):raise ValueError('prohibited RSP command '+payload[:24])
        raw=payload.encode();self.sock.sendall(b'$'+raw+b'#'+f'{sum(raw)&255:02x}'.encode())
        end=time.monotonic()+timeout
        while True:
            response=self._one(end)
            if response.startswith(('T','S')):
                self.stops.append(response);continue
            if response.startswith('O') and response!='OK' and re.fullmatch(r'O(?:[0-9a-fA-F]{2})+',response):
                continue
            return response
    def _get_byte(self,deadline):
        if self._pending:
            b=self._pending[:1];self._pending=self._pending[1:];return b
        while True:
            if time.monotonic()>deadline:raise TimeoutError('RSP byte timeout')
            self.sock.settimeout(max(.001,min(.1,deadline-time.monotonic())))
            try:b=self.sock.recv(1)
            except socket.timeout:continue
            if not b:raise ConnectionError('RSP EOF')
            return b
    def send_continue(self,timeout=2.0):
        """Addressless c: consume only ACK; keep immediately following T05 bytes."""
        self.sock.sendall(b'$c#63');end=time.monotonic()+min(timeout,self._remaining(timeout))
        while True:
            b=self._get_byte(end)
            if b==b'-':raise ValueError('continue checksum rejected')
            if b==b'+':return {'command':'c','ack':'+'}
            if b in (b'\n',b'\r'):continue
            # Any non-ACK byte would be a lost stop; retain it for poll_stop.
            self._pending=b+self._pending
            raise ValueError('unexpected non-ACK before continue')
    packet=command
    def poll_stop(self,timeout=.05):
        if self.deadline is not None:timeout=max(.001,min(timeout,self.deadline.remaining_total()))
        if self.stops:return self.stops.pop(0)
        if not select.select([self.sock],[],[],timeout)[0]:return None
        v=self._one(time.monotonic()+1.0)
        if v.startswith(('T','S')):return v
        if v.startswith('O') and v!='OK':return None
        raise ValueError('unexpected asynchronous RSP '+v[:40])
    def select_thread(self,stop):
        # T05 only; exactly one thread field.  The value is a GDB CPU thread id,
        # hex and optional pPID.TID; it is NOT a guest OS TID and is not int()'d.
        if not stop.startswith('T05') or not stop.endswith(';') or len(stop)>1024:
            raise ValueError('unknown CPU stop '+stop[:80])
        fields=stop[3:-1].split(';');tids=[]
        for field in fields:
            if ':' not in field:raise ValueError('malformed CPU stop field '+field[:40])
            key,value=field.split(':',1)
            if not re.fullmatch(r'[A-Za-z0-9_]+',key) or not value:raise ValueError('malformed CPU stop field '+field[:40])
            if key=='thread':tids.append(value)
        if len(tids)!=1:raise ValueError('T05 must have exactly one thread field')
        tid=tids[0]
        if not re.fullmatch(r'(?:p[0-9a-f]+\.)?[0-9a-f]+',tid,re.I):raise ValueError('nonhex GDB CPU thread '+tid)
        if self.command('Hg'+tid)!='OK' or self.command('Hc'+tid)!='OK':raise ValueError('CPU selection failed')
        return tid
    def regs(self):
        v=self.command('g')
        if not re.fullmatch(r'[0-9a-fA-F]+',v):raise ValueError('nonhex AArch64 register response')
        b=bytes.fromhex(v)
        if len(b)<264:raise ValueError('short AArch64 register response')
        return struct.unpack_from('<33Q',b)
    def virtual_read(self,addr,size):
        if not 0<size<=64:raise ValueError('unbounded RSP memory read')
        if self.command('Qqemu.PhyMemMode:0',timeout=self._remaining())!='OK':raise ValueError('virtual memory mode rejected')
        try:
            v=self.command(f'm{addr:x},{size:x}',timeout=self._remaining())
            if v.startswith('E'):raise ValueError('virtual address unavailable '+hex(addr))
            if not re.fullmatch(r'[0-9a-fA-F]+',v):raise ValueError('nonhex RSP memory')
            data=bytes.fromhex(v)
            if len(data)!=size:raise ValueError('short RSP memory read')
            return data
        finally:
            if self.command('Qqemu.PhyMemMode:1',timeout=self._remaining())!='OK':raise ValueError('physical mode restoration failed')
    def close(self):self.sock.close()
