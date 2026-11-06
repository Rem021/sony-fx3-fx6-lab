#!/usr/bin/env python3
"""Strict framed serial -> appFw mapping; no legacy raw-maps fallback."""
import hashlib,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import decode_snapshot as D
import mapping_parser as M
NEW_CPIO_SHA='9d4f255b0a3995b0e056e210ae4d27c8129e2c853b35904a688b6ffe149529ae'
NEW_CPIO_BYTES=453306948
class FramedProvider:
    def __init__(self,elf_path=M.APP_ELF,cpio_path=None,cpio_sha=NEW_CPIO_SHA):self.elf_path=elf_path;self.cpio_path=cpio_path;self.cpio_sha=cpio_sha;self.last=None;self._cpio_checked=False
    def _check_cpio(self):
        if self.cpio_path and not self._cpio_checked:
            b=Path(self.cpio_path).read_bytes()
            if len(b)!=NEW_CPIO_BYTES or hashlib.sha256(b).hexdigest()!=self.cpio_sha:raise ValueError('new CPIO binding mismatch')
            self._cpio_checked=True
    def select(self,serial_text):
        self._check_cpio()
        d=D.decode(serial_text)
        rows=[]
        for line in d['maps_text'].splitlines():
            m=M.MAP.fullmatch(line.encode()) if False else None
            # reuse parser MAP via bytes line
            mm=M.MAP.match(line.encode())
            if mm:rows.append({'line':None,'start':int(mm.group(1),16),'end':int(mm.group(2),16),'perms':mm.group(3).decode(),'offset':int(mm.group(4),16),'inode':int(mm.group(5)),'path':mm.group(6).decode()})
        app=[r for r in rows if r['path']==M.AP_PATH.decode()]
        if not app:raise ValueError('framed payload has no appFw rows')
        ap=M.map_bias(rows,M.AP_PATH.decode(),M.elf_loads(self.elf_path))
        b=Path(self.elf_path).read_bytes();phoff=int.from_bytes(b[32:40],'little');es=int.from_bytes(b[54:56],'little');n=int.from_bytes(b[56:58],'little')
        for name,va,size,needx in [('header',0,64,False),('phdr',phoff,es*n,False)]+[('code',k['thunk_va'],4,True) for k in M.KEYS]+[('code',k['return_va'],4,True) for k in M.KEYS]:
            addr=ap['bias']+va;hits=[r for r in app if r['start']<=addr and addr+size<=r['end']]
            if not hits:raise ValueError('unmapped '+name)
            if 'r' not in hits[0]['perms']:raise ValueError('unreadable '+name)
            if needx and 'x' not in hits[0]['perms']:raise ValueError('nonexec '+name)
        for k in M.KEYS:
            for va,w in ((k['thunk_va'],k['thunk_word']),(k['return_va'],k['return_word'])):
                if M.word_at(self.elf_path,va).hex()!=w:raise ValueError('static word mismatch')
        self.last={'pid':d['pid'],'seq':d['selected_seq'],'bias':ap['bias'],'frames':d['frame_count'],'data_reads':d['data_reads'],'eof_probe':d['eof_probe'],'cpio_sha256':self.cpio_sha}
        return {'pid':d['pid'],'epoch':None,'ap':ap,'appfw_tids':[],'block_byte_range':[0,0],'framed':True,'frame_seq':d['selected_seq'],'frame_count':d['frame_count'],'cpio_sha256':self.cpio_sha}
