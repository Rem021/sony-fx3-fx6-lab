#!/usr/bin/env python3
"""Two-stage, read-only guest image identity proof; never trusts old ASLR."""
import hashlib
import re
import struct
from pathlib import Path
from readonly_probe import AP_PATH, CAP_PATH, PAGE, elf_loads, map_bias, parse_maps

REQUEST=b'0d202d030a0001800000'
PROFILE_BEGIN=re.compile(rb'FX3_PROFILE_STACK_BEGIN destination=0x92840747 header=0x32d200d tid=(\d+) frame=(0x[0-9a-f]+)')
PROFILE_END=b'FX3_PROFILE_STACK_END destination=0x92840747'
PROFILE_FRAME=re.compile(rb'FX3_PROFILE_FRAME depth=(\d+) fp=(0x[0-9a-f]+) lr=(0x[0-9a-f]+) module=/usr/lib/appFw\.so relative=(0x[0-9a-f]+)')
REQ=re.compile(rb'FX3_PROVIDER_REQUEST destination=0x92840747 bytes=10 source=(0x[0-9a-f]+) caller=(0x[0-9a-f]+) raw=(0d202d030a0001800000) dispatch_pending=1')

def choose_early_cap(serial,cap_elf):
    """Only complete early /proc/<im_pid>/maps and all CAP PT_LOAD rows."""
    complete=[x for x in parse_maps(serial) if x['kind']=='early' and x['complete'] and x['byte_end'] is not None]
    if len({x['pid'] for x in complete})!=1:return None
    for block in reversed(complete):
        im=[x for x in block['rows'] if x['path']==b'/usr/bin/im.elf']
        if len(im)<2 or len({x['inode'] for x in im})!=1:continue
        try:cap=map_bias(block['rows'],CAP_PATH,elf_loads(cap_elf))
        except ValueError:continue
        return {'pid':block['pid'],'cap':cap,'ap':None,'snapshot_kind':'early',
                'snapshot_epoch':block['epoch'],'snapshot_byte_range':[block['byte_start'],block['byte_end']],
                'snapshot_first_uptime':block['first_uptime'],'early_snapshot_count':len(complete),
                'im_inode':im[0]['inode'],
                'ap_identity_status':'not_checked_until_CAP_stop'}
    return None

def target_profile(serial,native,ap_elf):
    """Bound the native dladdr evidence to this TID/source/request sequence."""
    requests=[m for m in REQ.finditer(serial) if int(m[1],16)==native['source']]
    if len(requests)!=1:raise ValueError('target request absent or repeated')
    req=requests[0]
    candidates=[]
    for begin in PROFILE_BEGIN.finditer(serial[:req.start()]):
        if int(begin[1])!=native['tid']:continue
        tail=serial.find(PROFILE_END,begin.end(),req.start())
        if tail<0 or PROFILE_BEGIN.search(serial,begin.end(),tail):continue
        stop=tail+len(PROFILE_END)
        frames=[];loads=elf_loads(ap_elf)
        for m in PROFILE_FRAME.finditer(serial[begin.end():tail]):
            lr=int(m[3],16);va=int(m[4],16)
            if not any(s['flags']&1 and s['va']<=va<s['va']+s['filesz'] for s in loads):
                raise ValueError('dladdr relative not in original executable PT_LOAD')
            frames.append({'depth':int(m[1]),'fp':m[2].decode(),'lr':hex(lr),
                           'relative':hex(va),'base':lr-va})
        if len(frames)<2:continue
        bases={f['base'] for f in frames}
        if len(bases)!=1 or next(iter(bases))%PAGE:raise ValueError('mixed or unaligned AP dladdr base')
        candidates.append((begin,stop,frames))
    if not candidates:raise ValueError('no same-TID completed AP dladdr profile')
    begin,stop,frames=candidates[-1]
    if PROFILE_BEGIN.search(serial[stop:req.start()]):raise ValueError('intervening target profile')
    base=frames[0]['base']
    if int(req[2],16)!=base+0x20ef7a0:raise ValueError('request caller differs from AP original return VA')
    return {'bias':base,'tid':native['tid'],'source':hex(native['source']),
            'profile_byte_range':[begin.start(),stop],
            'request_byte_range':[req.start(),req.end()],
            'request_raw':req[3].decode(),'frame_count':len(frames),
            'frames':[{**f,'base':hex(f['base'])} for f in frames],
            'provenance':'native CAPID helper dladdr frames in target request TID; /proc AP VMA not emitted'}

def _read_chunks(rsp,addr,size):
    if not 0<size<=8192:raise ValueError('unbounded guest ELF identity read')
    return b''.join(rsp.virtual_read(addr+i,min(64,size-i)) for i in range(0,size,64))

def _file_offset(loads,va,size):
    segments=[s for s in loads if s['va']<=va and va+size<=s['va']+s['filesz']]
    if len(segments)!=1:raise ValueError('VA not uniquely in original file-backed PT_LOAD')
    return segments[0]['fileoff']+va-segments[0]['va']

def read_current_identity(rsp,bias,elf,code_vas):
    """Compare current vCPU virtual ELF header, PHDR and original code words."""
    path=Path(elf)
    with path.open('rb') as f:
        head=f.read(64)
        if head[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',head,18)[0]!=183:
            raise ValueError('original not AArch64 ELF64 LE')
        phoff=struct.unpack_from('<Q',head,32)[0]
        entsize,count=struct.unpack_from('<HH',head,54)
        if not 0<count<=64 or entsize!=56 or phoff+entsize*count>8192:
            raise ValueError('original PHDR bounds')
        f.seek(phoff);phdr=f.read(entsize*count)
        if len(phdr)!=entsize*count:raise ValueError('short original PHDR')
        loads=elf_loads(path)
        expected=[]
        for va in code_vas:
            fileoff=_file_offset(loads,va,4)
            f.seek(fileoff);word=f.read(4)
            if len(word)!=4:raise ValueError('short original code word')
            expected.append((va,fileoff,word))
    current_head=_read_chunks(rsp,bias,64)
    if current_head!=head:raise ValueError('current CPU ELF header differs from pinned original')
    current_phdr=_read_chunks(rsp,bias+phoff,len(phdr))
    if current_phdr!=phdr:raise ValueError('current CPU PT_LOAD/PHDR differs from pinned original')
    words=[]
    for va,fileoff,word in expected:
        current=rsp.virtual_read(bias+va,4)
        if current!=word:raise ValueError('current CPU original code word mismatch '+hex(va))
        words.append({'va':hex(va),'file_offset':hex(fileoff),'word_le':word.hex()})
    return {'bias':hex(bias),'elf_header_sha256':hashlib.sha256(current_head).hexdigest(),
            'program_headers_sha256':hashlib.sha256(current_phdr).hexdigest(),
            'program_header_bytes':len(current_phdr),'machine':'AArch64','original_code_words':words}
