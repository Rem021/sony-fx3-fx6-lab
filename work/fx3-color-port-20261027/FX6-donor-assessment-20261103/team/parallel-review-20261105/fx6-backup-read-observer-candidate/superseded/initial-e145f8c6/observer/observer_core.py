#!/usr/bin/env python3
"""Host-testable, default-disabled two-key AppFw Backup_nread observer core.

Future run only: this module never starts QEMU and never writes guest state.
Allowed RSP operations are H/g/p/m, Z1/z1, mode 0/1, register XML; no Z0,
no M/G/P, no continue-with-single-step, no patch/stub/veneer.
"""
import hashlib,json,re,select,struct,time
from pathlib import Path

AP_PATH=b'/usr/lib/appFw.so'
APP_ELF=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/grm-fbinit/appFw-future-skip.so')
PAGE=4096
APPFW_SHA256='b1fe2274e19d50b6d7ee12886dc233a742358772383f5cf79523de15cf0b55be'
TARGET_CPIO_SHA256='3a08f89d89cfc6db8b12158a0a1147410e42d98713c445c3c38c07eefad8d03b'
TARGET_SERIAL_SHA256='377142e9dcee7f4f7728db6e9fcb822a9f3e501e61da7f719761d4d506f5050e'
KEYS=(
 {'name':'0x02cf0214','key':0x02cf0214,'thunk_va':0x2169784,'return_va':0x11f67d4,'slot_off':0xb4,
  'thunk_word':'e10300aa','return_word':'a0e30291'},
 {'name':'0x02cf0218','key':0x02cf0218,'thunk_va':0x21697d4,'return_va':0x11f67f4,'slot_off':0xc4,
  'thunk_word':'e10300aa','return_word':'a0230391'},
)
MAX_ENTRY_HITS=2; MAX_RETURN_HITS=2; MAX_STOPS=8; MAX_READS=16; MAX_READ_BYTES=4; MAX_SECONDS=150
MAP=re.compile(rb'^([0-9a-f]+)-([0-9a-f]+) ([rwxp-]{4}) ([0-9a-f]+) [0-9a-f]+:[0-9a-f]+ (\d+)\s+(/\S+)$')
EARLY_BEGIN=re.compile(rb'FX3_AP_EARLY_MAPS_(\d+)_(\d+)_BEGIN'); EARLY_END=re.compile(rb'FX3_AP_EARLY_MAPS_(\d+)_(\d+)_END')
APPFW_TID=re.compile(rb'FX3_UIPC_RECV_BEGIN tid=(\d+) name=AppFw ')
REQ=re.compile(rb'FX3_PROVIDER_REQUEST [^\r\n]*')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def elf_loads(path):
    b=Path(path).read_bytes(); head=b[:64]
    if head[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',head,18)[0]!=183:
        raise ValueError('original not AArch64 ELF64 LE')
    phoff=struct.unpack_from('<Q',head,32)[0]; es,n=struct.unpack_from('<HH',head,54)
    if not 0<n<=64 or es!=56 or phoff+es*n>len(b):raise ValueError('bad PHDR bounds')
    out=[]
    for i in range(n):
        p=phoff+i*es; typ,flags=struct.unpack_from('<II',b,p)
        if typ!=1:continue
        fo,va,pa,fs,ms,al=struct.unpack_from('<QQQQQQ',b,p+8)
        out.append({'fileoff':fo,'va':va,'filesz':fs,'memsz':ms,'align':al,'flags':flags})
    if not out:raise ValueError('no PT_LOAD')
    return out

def word_at(path,va):
    loads=elf_loads(path); b=Path(path).read_bytes()
    seg=[s for s in loads if s['va']<=va and va+4<=s['va']+s['filesz']]
    if len(seg)!=1:raise ValueError('VA not in one file-backed PT_LOAD')
    fo=seg[0]['fileoff']+va-seg[0]['va']
    return b[fo:fo+4]

def parse_maps(serial):
    blocks=[];active=None;pos=0
    for line in serial.splitlines(keepends=True):
        stripped=line.strip(); begin=EARLY_BEGIN.fullmatch(stripped); end=EARLY_END.fullmatch(stripped)
        if begin:
            if active:blocks.append(active)
            active={'pid':int(begin[1]),'epoch':int(begin[2]),'rows':[],'complete':False,'byte_start':pos,'byte_end':None}
        elif active is not None:
            if end and int(end[1])==active['pid'] and int(end[2])==active['epoch']:
                active['complete']=True;active['byte_end']=pos+len(line);blocks.append(active);active=None
            else:
                m=MAP.match(stripped)
                if m:active['rows'].append({'start':int(m[1],16),'end':int(m[2],16),'perms':m[3].decode(),'offset':int(m[4],16),'inode':int(m[5]),'path':m[6]})
        pos+=len(line)
    if active:blocks.append(active)
    return blocks

def map_bias(rows,path,loads):
    present=[r for r in rows if r['path']==path]
    if not present or len({r['inode'] for r in present})!=1:raise ValueError('missing/mixed inode')
    valid=[]
    for bias in {r['start']-s['va']//PAGE*PAGE for r in present for s in loads if r['offset']==s['fileoff']//PAGE*PAGE}:
        if all(any(r['start']==bias+s['va']//PAGE*PAGE and r['offset']==s['fileoff']//PAGE*PAGE for r in present) for s in loads):valid.append(bias)
    if len(valid)!=1:raise ValueError('ambiguous appFw bias '+repr(valid))
    return {'bias':valid[0],'inode':present[0]['inode'],'rows':[{k:(v.decode() if isinstance(v,bytes) else v) for k,v in r.items()} for r in present]}

def choose_appfw(serial,elf_path):
    """Latest COMPLETE early map block with all appFw PT_LOAD rows; never a late/historical guess."""
    for block in reversed([b for b in parse_maps(serial) if b['complete']]):
        try:ap=map_bias(block['rows'],AP_PATH,elf_loads(elf_path))
        except ValueError:continue
        tids=sorted({int(x) for x in APPFW_TID.findall(serial)})
        return {'pid':block['pid'],'epoch':block['epoch'],'ap':ap,'appfw_tids':tids,
                'block_byte_range':[block['byte_start'],block['byte_end']]}
    raise ValueError('no complete current appFw map block')

def _read_chunks(rsp,addr,size):
    if not 0<size<=8192 or size%4:raise ValueError('bad identity read')
    out=b''
    for i in range(0,size,4):out+=rsp.virtual_read(addr+i,4)
    return out

def verify_live_identity(rsp,bias,elf_path):
    """Current vCPU memory must equal pinned appFw ELF header/PHDR and all four machine words."""
    b=Path(elf_path).read_bytes(); head=b[:64]
    if b[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',b,18)[0]!=183:raise ValueError('original not AArch64')
    phoff=struct.unpack_from('<Q',b,32)[0]; es,n=struct.unpack_from('<HH',b,54)
    if es!=56 or not 0<n<=64 or phoff+es*n>8192:raise ValueError('original PHDR bounds')
    expected=[(k['thunk_va'],k['thunk_word']) for k in KEYS]+[(k['return_va'],k['return_word']) for k in KEYS]
    if _read_chunks(rsp,bias,64)!=head:raise ValueError('live ELF header mismatch')
    if _read_chunks(rsp,bias+phoff,es*n)!=b[phoff:phoff+es*n]:raise ValueError('live PHDR mismatch')
    words=[]
    for va,w in expected:
        got=rsp.virtual_read(bias+va,4)
        if got!=bytes.fromhex(w):raise ValueError('live machine word mismatch '+hex(va))
        words.append({'va':hex(va),'word':got.hex()})
    return {'bias':hex(bias),'elf_sha256':hashlib.sha256(head).hexdigest(),'phdr_sha256':hashlib.sha256(b[phoff:phoff+es*n]).hexdigest(),'words':words,'pid':None}

class RSP:
    """Minimal read-only RSP transport; no writes or software steps."""
    ALLOWED=re.compile(r'(?:Qqemu\.PhyMemMode:[01]|qqemu\.PhyMemMode|Hg(?:p[0-9a-f]+\.)?[0-9a-f]+|Hc(?:p[0-9a-f]+\.)?[0-9a-f]+|g|m[0-9a-f]+,[0-9a-f]+|Z1,[0-9a-f]+,4|z1,[0-9a-f]+,4)',re.I)
    def __init__(self,sock):self.sock=sock;self.stops=[];self.buf=b''
    @classmethod
    def connect(cls,run):
        import os,socket
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);old=Path.cwd()
        try:os.chdir(run);s.connect('g')
        finally:os.chdir(old)
        return cls(s)
    def _packet(self,payload):
        raw=payload.encode();return b'$'+raw+b'#'+f'{sum(raw)&255:02x}'.encode()
    def command(self,payload,timeout=2.0):
        assert self.ALLOWED.fullmatch(payload),payload
        self.sock.sendall(self._packet(payload));self.sock.settimeout(timeout);end=time.monotonic()+timeout;raw=b''
        while b'#' not in raw:
            if time.monotonic()>end:raise TimeoutError('RSP timeout')
            chunk=self.sock.recv(4096)
            if not chunk:raise ConnectionError('RSP closed')
            raw+=chunk
            if b'+' in raw:raw=raw.split(b'+',1)[1]
        body,rest=raw.split(b'#',1)
        if body.startswith(b'$'):body=body[1:]
        self.sock.sendall(b'+')
        return body.decode('ascii','replace')
    def select_thread(self,stop):
        if not stop.startswith('T05') or not stop.endswith(';'):raise ValueError('non-T05 stop')
        tid=None
        for f in stop[3:-1].split(';'):
            if f.startswith('thread:'):tid=f[7:]
        if not tid:raise ValueError('T05 without thread')
        if self.command('Hg'+tid)!='OK' or self.command('Hc'+tid)!='OK':raise ValueError('thread select failed')
        return tid
    def regs(self):
        v=self.command('g');
        if not re.fullmatch(r'[0-9a-fA-F]+',v):raise ValueError('nonhex regs')
        b=bytes.fromhex(v)
        if len(b)<264:raise ValueError('short regs')
        return struct.unpack_from('<33Q',b)
    def virtual_read(self,addr,size):
        if not 0<size<=4:raise ValueError('observer read budget')
        if self.command('Qqemu.PhyMemMode:0')!='OK':raise ValueError('virtual mode rejected')
        try:
            v=self.command(f'm{addr:x},{size:x}')
            if v.startswith('E') or not re.fullmatch(r'[0-9a-fA-F]+',v):raise ValueError('read failed')
            b=bytes.fromhex(v)
            if len(b)!=size:raise ValueError('short read')
            return b
        finally:
            if self.command('Qqemu.PhyMemMode:1')!='OK':raise ValueError('physical mode restore failed')
    def close(self):self.sock.close()

class Observer:
    def __init__(self,mapping,rsp,tls_reader=None):
        if not callable(tls_reader):raise ValueError('TLS reader required; no TLS means unknown')
        self.m=mapping;self.rsp=rsp;self.tls_reader=tls_reader;self.bp=set();self.records=[];self.entry=None;self.done=set();self.stops=0;self.reads=0;self.t0=time.monotonic();self.unknown=None;self.identity=None
    def budget(self):
        if time.monotonic()-self.t0>MAX_SECONDS:raise TimeoutError('observation budget')
        if self.stops>MAX_STOPS or self.reads>MAX_READS:raise RuntimeError('hit/read budget exceeded')
    def read(self,addr,n=4):
        if n!=MAX_READ_BYTES:raise ValueError('only 4-byte reads')
        self.reads+=1;self.budget();return self.rsp.virtual_read(addr,n)
    def arm(self):
        for k in KEYS:
            a=self.m['ap']['bias']+k['thunk_va']
            if self.rsp.command(f'Z1,{a:x},4')!='OK':raise RuntimeError('Z1 rejected '+hex(a))
            self.bp.add(a)
    def _key_for_pc(self,pc):
        for k in KEYS:
            if pc==self.m['ap']['bias']+k['thunk_va']:return k
        return None
    def on_stop(self,stop):
        self.stops+=1;self.budget();tid=self.rsp.select_thread(stop);r=self.rsp.regs();pc=r[32]
        if self.entry is None:
            k=self._key_for_pc(pc)
            if not k:raise ValueError('unknown entry PC '+hex(pc))
            if k['name'] in self.done:raise ValueError('duplicate key '+k['name'])
            if self.identity is None:
                self.identity=verify_live_identity(self.rsp,self.m['ap']['bias'],APP_ELF)
            got=self.read(pc);exp=bytes.fromhex(k['thunk_word'])
            if got!=exp:raise ValueError('entry machine word mismatch '+hex(pc))
            buffer,fp,lr=int(r[0]),int(r[29]),int(r[30]);expect_ret=self.m['ap']['bias']+k['return_va'];expect_buf=fp+k['slot_off']
            if buffer!=expect_buf:raise ValueError('entry buffer != frame slot')
            if lr!=expect_ret:raise ValueError('entry LR != key return')
            tls=self.tls_reader()
            if tls is None:raise ValueError('TLS unavailable')
            before=self.read(buffer)
            # replace this thunk with its exact return site; other thunk remains
            if self.rsp.command(f'z1,{pc:x},4')!='OK':raise RuntimeError('entry z1 failed')
            self.bp.discard(pc)
            if self.rsp.command(f'Z1,{expect_ret:x},4')!='OK':raise RuntimeError('return Z1 rejected')
            self.bp.add(expect_ret)
            self.entry={'key':k,'tid':tid,'tls':tls,'fp':fp,'buffer':buffer,'before':before,'return':expect_ret,'pc':pc}
            return {'stage':'entry','key':k['name'],'tid':tid,'pc':hex(pc),'buffer':hex(buffer),'before':before.hex()}
        e=self.entry;k=e['key'];expect_ret=e['return']
        if pc!=expect_ret:raise ValueError('return PC mismatch')
        if int(tid)!=int(e['tid']):raise ValueError('return TID mismatch')
        if int(r[29])!=e['fp']:raise ValueError('return frame mismatch')
        if self.tls_reader()!=e['tls']:raise ValueError('return TLS mismatch')
        if self.read(pc)!=bytes.fromhex(k['return_word']):raise ValueError('return machine word mismatch')
        w0=int(r[0]);after=self.read(e['buffer'])
        row={'key':k['name'],'key_id':hex(k['key']),'pid':self.m['pid'],'tid':e['tid'],'tls':hex(e['tls']),
             'entry_pc':hex(e['pc']),'return_pc':hex(pc),'buffer':hex(e['buffer']),'capacity':4,
             'before_hex':e['before'].hex(),'after_hex':after.hex(),'return_w0_signed32':int.from_bytes(w0.to_bytes(8,'little')[:4],'little',signed=True),
             'return_w0_hex':hex(w0 & 0xffffffff),'return_raw':r[0],'frame':hex(e['fp'])}
        self.records.append(row)
        if self.rsp.command(f'z1,{pc:x},4')!='OK':raise RuntimeError('return z1 failed')
        self.bp.discard(pc);self.done.add(k['name']);self.entry=None
        return {'stage':'return','record':row}
    def cleanup(self):
        res=[]
        for a in sorted(self.bp):
            try:r=self.rsp.command(f'z1,{a:x},4')
            except Exception as e:r=repr(e)
            res.append({'addr':hex(a),'reply':r})
            if r=='OK':self.bp.discard(a)
        return {'all_removed':not self.bp,'results':res,'residual':[hex(a) for a in sorted(self.bp)],'guest_resumed':False,'writes_issued':False}
