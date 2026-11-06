#!/usr/bin/env python3
"""Strict offline map-block parser candidate (no VM/RSP/guest access).

The frozen r6 producer source has two distinct map writers:

  EARLY_MAPS: echo BEGIN; cat /proc/uptime /proc/<pid>/maps; echo END
  IM_ENDMAPS: echo BEGIN; cat /proc/uptime; grep '/usr/bin/im.elf' /proc/<pid>/maps; echo END

Thus an official IM_ENDMAPS body is im.elf only.  AppFw/lib rows occurring
between its BEGIN/END are foreign/interleaved output and must not be combined
with that block.  A future producer that prints the full /proc/<pid>/maps under
IM_ENDMAPS can be admitted only with an explicit full_proc_maps contract.
"""
import argparse,hashlib,json,re,struct,sys
from pathlib import Path

AP_PATH=b'/usr/lib/appFw.so'
IMELF_PATH=b'/usr/bin/im.elf'
APP_ELF=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/grm-fbinit/appFw-future-skip.so')
APPFW_SHA256='b1fe2274e19d50b6d7ee12886dc233a742358772383f5cf79523de15cf0b55be'
PAGE=4096
KEYS=(
 {'name':'0x02cf0214','key':0x02cf0214,'thunk_va':0x2169784,'return_va':0x11f67d4,'thunk_word':'e10300aa','return_word':'a0e30291'},
 {'name':'0x02cf0218','key':0x02cf0218,'thunk_va':0x21697d4,'return_va':0x11f67f4,'thunk_word':'e10300aa','return_word':'a0230391'},
)
MAP=re.compile(rb'^([0-9a-f]+)-([0-9a-f]+) ([rwxp-]{4}) ([0-9a-f]+) [0-9a-f]+:[0-9a-f]+ (\d+)\s+(/\S+)$')
BEGIN=re.compile(rb'^FX3_AP_(EARLY_MAPS|IM_ENDMAPS)_(\d+)(?:_(\d+))?_BEGIN$')
END=re.compile(rb'^FX3_AP_(EARLY_MAPS|IM_ENDMAPS)_(\d+)(?:_(\d+))?_END$')
TID=re.compile(rb'FX3_UIPC_RECV_BEGIN tid=(\d+) name=AppFw ')

class MapParserError(ValueError):
    def __init__(self,code,message,block=None,diagnostics=None):
        super().__init__(message);self.code=code;self.message=message;self.block=block;self.diagnostics=diagnostics or {}
    def as_dict(self):
        return {'code':self.code,'message':self.message,'block':_public_block(self.block) if self.block else None,'diagnostics':self.diagnostics}

def _public_block(b):
    if b is None:return None
    return {k:v for k,v in b.items() if k!='rows'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def elf_loads(path):
    b=Path(path).read_bytes();head=b[:64]
    if head[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',head,18)[0]!=183:raise MapParserError('bad_elf','original not AArch64 ELF64 LE')
    phoff=struct.unpack_from('<Q',head,32)[0];es,n=struct.unpack_from('<HH',head,54)
    if not 0<n<=64 or es!=56 or phoff+es*n>len(b):raise MapParserError('bad_phdr','bad PHDR bounds')
    out=[]
    for i in range(n):
        q=phoff+i*es;typ,flags=struct.unpack_from('<II',b,q)
        if typ!=1:continue
        fo,va,pa,fs,ms,al=struct.unpack_from('<QQQQQQ',b,q+8)
        out.append({'fileoff':fo,'va':va,'filesz':fs,'memsz':ms,'align':al,'flags':flags})
    if not out:raise MapParserError('no_pt_load','no PT_LOAD')
    return out

def word_at(path,va):
    loads=elf_loads(path);b=Path(path).read_bytes()
    seg=[s for s in loads if s['va']<=va and va+4<=s['va']+s['filesz']]
    if len(seg)!=1:raise MapParserError('word_va','VA not in one file-backed PT_LOAD')
    fo=seg[0]['fileoff']+va-seg[0]['va'];return b[fo:fo+4]

def parse_map_blocks(data):
    """Return blocks in completion order; nested markers use a stack.

    Rows belong only to the innermost active block.  A nested block is never
    merged into its parent; the parent's own rows before/after the nested range
    remain its rows.  A missing/different END never closes an outer block.
    """
    lines=data.splitlines(keepends=True);blocks=[];stack=[];stray=[]
    for lineno,raw in enumerate(lines,1):
        s=raw.strip();bm=BEGIN.fullmatch(s);em=END.fullmatch(s)
        if bm:
            kind=bm.group(1).decode();pid=int(bm.group(2));epoch=int(bm.group(3)) if bm.group(3) else None
            block={'kind':kind,'pid':pid,'epoch':epoch,'begin_line':lineno,'end_line':None,'rows':[],'complete':False,'depth':len(stack),'nested_under':None,'nested_children':0,'overlap_with_previous':bool(stack),'overlap_with_next':False}
            if stack:
                parent=stack[-1];parent['nested_children']+=1;parent['overlap_with_next']=True;block['nested_under']={'kind':parent['kind'],'pid':parent['pid'],'begin_line':parent['begin_line']}
            stack.append(block)
        elif em:
            want=(em.group(1).decode(),int(em.group(2)),int(em.group(3)) if em.group(3) else None)
            matches=[i for i,b in enumerate(stack) if (b['kind'],b['pid'],b['epoch'])==want]
            if not matches:
                stray.append({'line':lineno,'raw':s.decode('utf-8','replace')});continue
            idx=matches[-1]
            # Any still-open inner block is incomplete and must not be folded into the matched block.
            for b in stack[idx+1:]:
                b['complete']=False;b['end_line']=None;b['cut_by_outer_end']=True;blocks.append(b)
            b=stack[idx];b['complete']=True;b['end_line']=lineno;blocks.append(b);del stack[idx:]
        elif stack:
            m=MAP.match(s)
            if m:
                stack[-1]['rows'].append({'line':lineno,'start':int(m.group(1),16),'end':int(m.group(2),16),'perms':m.group(3).decode(),'offset':int(m.group(4),16),'inode':int(m.group(5)),'path':m.group(6).decode('utf-8','replace')})
    for b in stack:
        b['complete']=False;b['end_line']=None;blocks.append(b)
    return blocks,stray

def map_bias(rows,path,loads):
    present=[r for r in rows if r['path']==path]
    if not present:raise MapParserError('missing_appfw','no appFw rows in selected block')
    if len({r['inode'] for r in present})!=1:raise MapParserError('mixed_inode','appFw rows have mixed inodes')
    if any(r['end']-r['start']<PAGE for r in present):raise MapParserError('short_row','appFw map row shorter than a page')
    valid=[];saw_gap=False
    for bias in {r['start']-seg['va']//PAGE*PAGE for r in present for seg in loads if r['offset']==seg['fileoff']//PAGE*PAGE}:
        good=True
        for seg in loads:
            pageva=seg['va']//PAGE*PAGE;pageoff=seg['fileoff']//PAGE*PAGE
            need=bias+pageva+max(PAGE,(seg['filesz']//PAGE)*PAGE)
            rr=[r for r in present if r['offset']>=pageoff and r['offset']<pageoff+seg['filesz'] and r['start']>=bias+pageva and r['start']<need]
            if not rr or min(r['start'] for r in rr)!=bias+pageva:good=False;break
            if any(r['start']-bias-pageva != r['offset']-pageoff for r in rr):good=False;break
            covered=sorted((r['start'],r['end']) for r in rr);cursor=bias+pageva
            for lo,hi in covered:
                if lo>cursor:
                    good=False;saw_gap=True;break
                cursor=max(cursor,hi)
            if not good or cursor<need:
                good=False;break
            if (seg['flags']&1) and not any('x' in r['perms'] for r in rr):good=False;break
            if (seg['flags']&2) and not any('w' in r['perms'] for r in rr):good=False;break
        if good:valid.append(bias)
    if len(valid)!=1:
        if saw_gap:raise MapParserError('coverage_gap','appFw map rows leave an interval gap')
        raise MapParserError('bad_bias','ambiguous/incomplete appFw bias '+repr(valid))
    return {'bias':valid[0],'inode':present[0]['inode'],'rows':present}

def select_appfw(data,elf_path=APP_ELF,producer_contract='official_im_elf'):
    if producer_contract not in ('official_im_elf','full_proc_maps'):raise MapParserError('bad_contract','unknown producer contract')
    blocks,stray=parse_map_blocks(data)
    if not blocks:raise MapParserError('no_map_block','no EARLY/IM map block')
    # Only a top-level block can be the selected current map. Nested diagnostics
    # are parsed but cannot replace their parent or be spliced into it.
    tops=[b for b in blocks if b.get('depth',0)==0]
    if not tops:raise MapParserError('no_top_block','no top-level map block',None,{'stray_end_count':len(stray)})
    last=max(tops,key=lambda b:b['begin_line'])
    children=[b for b in blocks if b.get('nested_under') and b['nested_under']['begin_line']==last['begin_line']]
    if any(b.get('pid')!=last.get('pid') for b in children):raise MapParserError('cross_pid_overlap','nested block pid differs from selected pid',last,{'stray_end_count':len(stray)})
    if any(not b['complete'] for b in children):raise MapParserError('nested_block_incomplete','a nested map block is incomplete',last,{'stray_end_count':len(stray)})
    if not last['complete']:raise MapParserError('newest_block_incomplete','newest top-level map block has no matching END',last,{'stray_end_count':len(stray)})
    if last['kind']=='IM_ENDMAPS' and producer_contract=='official_im_elf':
        foreign=[r for r in last['rows'] if r['path']!=IMELF_PATH.decode()]
        if foreign:raise MapParserError('im_endmaps_source_is_imelf_only','official IM_ENDMAPS producer greps only /usr/bin/im.elf; %d foreign row(s), including appFw, cannot be credited to this block'%len(foreign),last,{'foreign_rows':len(foreign),'appfw_rows':sum(1 for r in last['rows'] if r['path']==AP_PATH.decode()),'sample':[r['path'] for r in foreign[:5]]})
    app=[r for r in last['rows'] if r['path']==AP_PATH.decode()]
    if not app:raise MapParserError('no_appfw','selected complete block has no appFw rows',last)
    if sha(elf_path)!=APPFW_SHA256:raise MapParserError('elf_hash','APP_ELF hash mismatch')
    loads=elf_loads(elf_path)
    ap=map_bias(last['rows'],AP_PATH.decode(),loads)
    b=Path(elf_path).read_bytes();phoff=struct.unpack_from('<Q',b,32)[0];es,n=struct.unpack_from('<HH',b,54)
    checks=[('header',0,64,False),('phdr',phoff,es*n,False)]+[('code',k['thunk_va'],4,True) for k in KEYS]+[('code',k['return_va'],4,True) for k in KEYS]
    for name,va,size,needx in checks:
        addr=ap['bias']+va;hits=[r for r in last['rows'] if r['path']==AP_PATH.decode() and r['start']<=addr and addr+size<=r['end']]
        if not hits:raise MapParserError('unmapped_'+name,'unmapped %s %s'%(name,hex(va)),last)
        if 'r' not in hits[0]['perms']:raise MapParserError('unreadable_'+name,'unreadable %s'%name,last)
        if needx and 'x' not in hits[0]['perms']:raise MapParserError('nonexec_'+name,'non-executable code %s'%hex(va),last)
    words=[]
    for k in KEYS:
        for va,w in ((k['thunk_va'],k['thunk_word']),(k['return_va'],k['return_word'])):
            got=word_at(elf_path,va).hex()
            if got!=w:raise MapParserError('static_word','static target word mismatch '+hex(va),last,{'expected':w,'got':got})
            words.append({'va':hex(va),'word':got})
    return {'pid':last['pid'],'epoch':last['epoch'],'block':_public_block(last),'ap':ap,'appfw_tids':sorted({x.decode() for x in TID.findall(data)}),'producer_contract':producer_contract,'static_words':words,'block_span':[last['begin_line'],last['end_line']],'source_guarantee':'official_im_elf' if producer_contract=='official_im_elf' else 'explicit_full_proc_maps_contract','diagnostics':{'rows':len(last['rows']),'appfw_rows':len(app),'map_blocks':len(blocks),'stray_ends':len(stray)}}

class MappingProvider:
    def __init__(self,elf_path=APP_ELF,producer_contract='official_im_elf'):
        self.elf_path=elf_path;self.producer_contract=producer_contract;self.last_rejection=None;self.last_accept=None
    def select(self,serial):
        try:
            self.last_accept=select_appfw(serial,self.elf_path,self.producer_contract);self.last_rejection=None;return self.last_accept
        except MapParserError as e:
            self.last_rejection=e.as_dict();raise

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--serial',required=True);ap.add_argument('--elf',default=str(APP_ELF));ap.add_argument('--output',required=True);ap.add_argument('--producer-contract',choices=('official_im_elf','full_proc_maps'),default='official_im_elf');a=ap.parse_args(argv)
    data=Path(a.serial).read_bytes();provider=MappingProvider(a.elf,a.producer_contract)
    try:
        out={'status':'accepted','mapping':provider.select(data)}
        rc=0
    except MapParserError as e:
        out={'status':'blocked','rejection':e.as_dict()};rc=1
    Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'reason':(out.get('rejection') or {}).get('code'),'output':str(a.output)}));return rc
if __name__=='__main__':sys.exit(main())
