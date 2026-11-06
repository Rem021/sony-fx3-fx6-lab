#!/usr/bin/env python3
"""Strict read-only RSP and ELF/maps proof for the fixed FX6 AP observation."""
import collections
import hashlib
import re
import select
import socket
import struct
import time
from pathlib import Path

MAP = re.compile(rb'^([0-9a-f]+)-([0-9a-f]+) ([rwxp-]{4}) ([0-9a-f]+) [0-9a-f]+:[0-9a-f]+ (\d+)\s+(/\S+)$')
AP_PATH = b'/usr/lib/appFw.so'
CAP_PATH = b'/simulation/fx3-capid-v1.so'
PAGE = 4096
AP_WORD = {0x20ef79c: '61aaa897', 0x20ef7a0: 'e0000034'}
CAP_WORD = {0x1840c: 'c9180094', 0x1e730: 'ff8301d1', 0x1e754: '807f8012', 0x1e764: '08c14bb9'}

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def elf_loads(path):
    with Path(path).open('rb') as f:
        head=f.read(64)
        if head[:6]!=b'\x7fELF\x02\x01': raise ValueError('not ELF64 LE')
        off=struct.unpack_from('<Q',head,32)[0]
        size,count=struct.unpack_from('<HH',head,54)
        if not 0<count<=64 or not 56<=size<=128:raise ValueError('unbounded ELF phdr')
        f.seek(off);b=f.read(size*count)
    if len(b)!=size*count:raise ValueError('short ELF phdr')
    out=[]
    for i in range(count):
        p=i*size
        kind,flags=struct.unpack_from('<II',b,p)
        if kind!=1:continue
        fileoff,va,_,filesz,memsz,align=struct.unpack_from('<QQQQQQ',b,p+8)
        out.append(dict(fileoff=fileoff,va=va,filesz=filesz,memsz=memsz,align=align,flags=flags))
    return out

def parse_maps(serial):
    """Completed /init IM maps snapshots; old late and current early formats.

    Early maps come from `cat /proc/uptime /proc/$im_pid/maps` within matched
    markers. The concurrent IM_ENDMAPS observer prints only im.elf rows; it
    cannot supply an AP or CAP row. All PT_LOAD rows are still checked below.
    """
    blocks=[];active=None;pos=0
    for line in serial.splitlines(keepends=True):
        stripped=line.strip()
        early_begin=re.fullmatch(rb'FX3_AP_EARLY_MAPS_(\d+)_(\d+)_BEGIN',stripped)
        early_end=re.fullmatch(rb'FX3_AP_EARLY_MAPS_(\d+)_(\d+)_END',stripped)
        late_begin=re.fullmatch(rb'FX3_AP_IM_PROCESS=(\d+)',stripped)
        if early_begin or late_begin:
            if active:blocks.append(active)
            active={'pid':int((early_begin or late_begin)[1]),'epoch':int(early_begin[2]) if early_begin else None,
                    'kind':'early' if early_begin else 'late','rows':[],'complete':False,
                    'byte_start':pos,'byte_end':None,'first_uptime':None}
        elif active is not None:
            if early_end and active['kind']=='early':
                if int(early_end[1])==active['pid'] and int(early_end[2])==active['epoch']:
                    active['complete']=True;active['byte_end']=pos+len(line)
                blocks.append(active);active=None
            elif active['kind']=='late' and b'FX3_TASK_SNAPSHOT_' in line and b'_BEGIN' in line:
                active['complete']=True;active['byte_end']=pos+len(line)
                blocks.append(active);active=None
            else:
                if active['first_uptime'] is None and re.fullmatch(rb'\d+\.\d+ \d+\.\d+',stripped):
                    active['first_uptime']=stripped.decode()
                mm=MAP.match(stripped)
                if mm:
                    active['rows'].append(dict(start=int(mm[1],16),end=int(mm[2],16),
                        perms=mm[3].decode(),offset=int(mm[4],16),inode=int(mm[5]),path=mm[6]))
        pos+=len(line)
    if active:blocks.append(active)
    return blocks

def map_bias(rows, path, loads):
    present=[r for r in rows if r['path']==path]
    if not present or len({r['inode'] for r in present})!=1:raise ValueError('missing or mixed inode '+path.decode())
    # A PT_LOAD may split into r--/rw after RELRO, but at least one row must
    # match its page-aligned file offset and virtual address in the same bias.
    candidates=set()
    for r in present:
        for seg in loads:
            if r['offset']==seg['fileoff']//PAGE*PAGE:
                candidates.add(r['start']-seg['va']//PAGE*PAGE)
    valid=[]
    for bias in candidates:
        matched=[]
        for seg in loads:
            if not any(r['start']==bias+(seg['va']//PAGE*PAGE)
               and r['offset']==seg['fileoff']//PAGE*PAGE for r in present):break
            matched.append(seg)
        if len(matched)==len(loads):valid.append(bias)
    if len(valid)!=1:raise ValueError('PT_LOAD/map bias ambiguous '+path.decode()+': '+repr(valid))
    return dict(bias=valid[0],inode=present[0]['inode'],segments=loads,
                rows=[{k:v.decode() if isinstance(v,bytes) else v for k,v in r.items()} for r in present])

def choose_mapping(serial, ap_elf, cap_elf):
    for block in reversed(parse_maps(serial)):
        if not block['complete']:
            continue
        try:
            ap=map_bias(block['rows'],AP_PATH,elf_loads(ap_elf))
            cap=map_bias(block['rows'],CAP_PATH,elf_loads(cap_elf))
            return {'pid':block['pid'],'block_complete':block['complete'],
                    'snapshot_kind':block['kind'],'snapshot_epoch':block['epoch'],
                    'snapshot_byte_range':[block['byte_start'],block['byte_end']],
                    'snapshot_first_uptime':block['first_uptime'],'ap':ap,'cap':cap}
        except ValueError:continue
    return None

def rsp_packet(payload):
    raw=payload.encode('ascii')
    return b'$'+raw+b'#'+f'{sum(raw)&255:02x}'.encode('ascii')

class RSP:
    ALLOWED=(re.compile(r'(?:Qqemu\.PhyMemMode:[01]|qqemu\.PhyMemMode|Hg(?:p[0-9a-f]+\.)?[0-9a-f]+|Hc(?:p[0-9a-f]+\.)?[0-9a-f]+|g|p[0-9a-f]+|m[0-9a-f]+,[0-9a-f]+|qXfer:features:read:[A-Za-z0-9_.-]+:[0-9a-f]+,[0-9a-f]+|Z1,[0-9a-f]+,4|z1,[0-9a-f]+,4)',re.I))
    def __init__(self,sock):
        self.sock=sock;self.sock.settimeout(1.0);self.stops=collections.deque();self._pending=b''
    @classmethod
    def connect(cls,run):
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        # AF_UNIX absolute paths exceed macOS sockaddr_un; QEMU uses cwd/g.
        import os
        old=Path.cwd()
        try:os.chdir(run);s.connect('g')
        finally:os.chdir(old)
        return cls(s)
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
            tail=self._exact(2,deadline)
            try:got=int(tail,16)
            except ValueError:raise ValueError('RSP checksum digits invalid')
            if got!=sum(raw)&255:
                self.sock.sendall(b'-');raise ValueError('RSP incoming checksum mismatch')
            self.sock.sendall(b'+')
            # Escaping is part of RSP framing; no run-length expansion is
            # needed for the bounded hex registers/memory and ASCII stop set.
            un=bytearray();i=0
            while i<len(raw):
                if raw[i]==0x7d:
                    i+=1
                    if i==len(raw):raise ValueError('RSP dangling escape')
                    un.append(raw[i]^0x20)
                else:un.append(raw[i])
                i+=1
            return un.decode('ascii')
    def _exact(self,n,deadline):
        out=b''
        while len(out)<n:
            if time.monotonic()>deadline:raise TimeoutError('RSP checksum timeout')
            try:c=self.sock.recv(n-len(out))
            except socket.timeout:continue
            if not c:raise ConnectionError('RSP truncated checksum')
            out+=c
        return out
    def command(self,payload,timeout=2.0):
        if not self.ALLOWED.fullmatch(payload):raise ValueError('prohibited RSP command '+payload[:16])
        self.sock.sendall(rsp_packet(payload));end=time.monotonic()+timeout
        while True:
            response=self._one(end)
            if response.startswith(('T','S')):
                self.stops.append(response);continue
            if response.startswith('O') and response!='OK' and re.fullmatch(r'O(?:[0-9a-fA-F]{2})+',response):continue
            return response
    packet=command
    def send_continue(self,timeout=2.0):
        """Resume all CPUs with addressless `c`; ACK is not a stop reply.

        QEMU's pinned system gdbstub sets allow_stop_reply only while handling
        this command.  A stop packet may follow the ACK immediately or much
        later; leave it unread for poll_stop and the identity gates.
        """
        self.sock.sendall(rsp_packet('c'))
        deadline=time.monotonic()+timeout
        while True:
            if time.monotonic()>deadline:raise TimeoutError('RSP continue ACK timeout')
            self.sock.settimeout(min(.1,max(.001,deadline-time.monotonic())))
            try:c=self.sock.recv(1)
            except socket.timeout:continue
            if not c:raise ConnectionError('RSP closed before continue ACK')
            if c==b'+':return {'command':'c','ack':'+'}
            if c==b'-':raise ValueError('RSP continue checksum rejected')
            raise ValueError('RSP continue response before ACK '+repr(c))
    def poll_stop(self,timeout=.05):
        if self.stops:return self.stops.popleft()
        if not select.select([self.sock],[],[],timeout)[0]:return None
        v=self._one(time.monotonic()+1.0)
        if v.startswith(('T','S')):return v
        if v.startswith('O') and v!='OK':return None
        raise ValueError('unexpected asynchronous RSP '+v[:40])
    def select_thread(self,stop):
        # T05 is the signal header, immediately followed by n:r; fields.
        # QEMU's first field is normally `thread:02;` with no leading `;`.
        if not stop.startswith('T05') or not stop.endswith(';') or len(stop)>1024:
            raise ValueError('unknown CPU stop '+stop[:80])
        fields=stop[3:-1].split(';')
        parsed=[]
        for field in fields:
            if ':' not in field:raise ValueError('malformed CPU stop field '+field[:40])
            key,value=field.split(':',1)
            if not re.fullmatch(r'[A-Za-z0-9_]+',key) or not value:
                raise ValueError('malformed CPU stop field '+field[:40])
            parsed.append((key,value))
        tids=[value for key,value in parsed if key=='thread']
        if len(tids)!=1 or not re.fullmatch(r'(?:p[0-9a-f]+\.)?[0-9a-f]+',tids[0],re.I):
            raise ValueError('unknown CPU stop '+stop[:80])
        tid=tids[0]
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
        if self.command('Qqemu.PhyMemMode:0')!='OK':raise ValueError('virtual memory mode rejected')
        try:
            v=self.command(f'm{addr:x},{size:x}')
            if v.startswith('E'):raise ValueError('virtual address unavailable '+hex(addr))
            if not re.fullmatch(r'[0-9a-fA-F]+',v):raise ValueError('nonhex RSP memory')
            data=bytes.fromhex(v)
            if len(data)!=size:raise ValueError('short RSP memory read')
            return data
        finally:
            if self.command('Qqemu.PhyMemMode:1')!='OK':raise ValueError('physical mode restoration failed')
    def close(self):self.sock.close()

def confirm_hit(rsp,stop,mapping,expected,origin):
    tid=rsp.select_thread(stop);r=rsp.regs();pc=r[32]
    if pc!=expected:raise ValueError('unknown breakpoint PC '+hex(pc))
    bias=mapping[origin]['bias'];va=pc-bias
    table=AP_WORD if origin=='ap' else CAP_WORD
    if va not in table:raise ValueError('PC not an allowed original instruction')
    word=rsp.virtual_read(pc,4).hex()
    if word!=table[va]:raise ValueError('wrong current address space or modified original word')
    return {'vCPU':tid,'stop':stop,'pc':hex(pc),'va':hex(va),'word':word,
        'x0':hex(r[0]),'x1':hex(r[1]),'fp':hex(r[29]),'sp':hex(r[31]),'regs':r}
